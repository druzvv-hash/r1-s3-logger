import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import contracts as c
from make_contract_fixtures import metadata, samples
sys.path.insert(0, str(ROOT/'viewer'))
import core


def ecosystem_metadata(corrected=True, grouped=True):
    meta=metadata();meta['schema']=2
    meta['ecosystem']=dict(version=1,device_id='02:11:22:33:44:55',
        boot_id='123456789abcdef0',recording_id='1020304050607080',
        group_id='1122334455667788' if grouped else None,
        coordinator_id='02:AA:BB:CC:DD:EE' if grouped else None,
        coordinator_boot_id='8877665544332211' if grouped else None,
        rtc_correction=None)
    meta['time'].update(utc_anchor='2026-09-09T00:00:00.000000Z',source='DS3231/R3' if corrected else 'DS3231',uncertainty_us=None)
    if corrected:
        meta['ecosystem']['rtc_correction']=dict(authority_id='02:AA:BB:CC:DD:EE',
            authority_boot_id='8877665544332211',clock_revision=3,request_id='aabbccddeeff0011',
            unix_s=1788911999,received_local_us='9007199254741009',applied_local_us='9007199254991009',
            source_capture_us='18446744073709551615',source_read_age_ms=250,roundtrip_us=100000,
            uncertainty_us=None)
    return meta


def unchecked_empty_file(meta, magic=None, columns=None):
    """Valid byte integrity around deliberately bad semantics, bypassing the writer."""
    metaraw=b'# META '+c.canonical(meta)+b'\n'
    prefix=(magic or c.MAGICS.get(meta.get('schema'),b'# R1S3_LOG schema=99\n'))+metaraw
    prefix+=f'# META_CRC32 {c.crc(metaraw):08X}\n'.encode()
    prefix+=(columns or ','.join(c.COLUMNS)+'\n').encode()
    end=dict(rows=0,sha256=hashlib.sha256(prefix).hexdigest(),clean=True,reason='stop')
    return prefix+b'# END '+c.canonical(end)+b'\n'


class Contracts(unittest.TestCase):
    def test_crc_known_vector(self):
        self.assertEqual(c.crc(b'123456789'), 0xCBF43926)

    def test_config_roundtrip_and_golden(self):
        slot = c.encode_slot(c.defaults(), 1)
        self.assertEqual(len(slot), 1536)
        self.assertEqual(slot, bytes.fromhex((ROOT/'tests/fixtures/config-default-slot.hex').read_text()))
        self.assertEqual(c.decode_slot(slot), (1, c.defaults()))

    def test_config_maximum_strings_fit(self):
        values = c.defaults()
        for f in c.REGISTRY:
            if f['type'] == 'utf8' and f['name'] != 'calibration_utc':
                values[f['name']] = 'x'*f['max_bytes']
        values['calibration_utc'] = '2026-09-07T00:00:00Z'
        self.assertLessEqual(len(c.encode_payload(values)), 1472)
        self.assertEqual(c.decode_slot(c.encode_slot(values, 2))[1], values)

    def test_bad_config_values(self):
        for key, bad in [('i_gain', float('nan')), ('shunt_uohm', 0), ('polarity', 0), ('requested_rate_hz', True), ('i_gain', True), ('calibration_id', 'я'*64), ('calibration_valid', True)]:
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                c.encode_payload(dict(c.defaults(), **{key:bad}))

    def test_torn_slot_keeps_old(self):
        old = c.encode_slot(c.defaults(), 1)
        new = c.encode_slot(dict(c.defaults(), i_gain=1.01), 2)
        # Model inactive erased slot interrupted at every byte, including commit.
        for cut in range(1536):
            torn = new[:cut] + b'\xff'*(1536-cut)
            self.assertEqual(c.select_slot(old, torn)[1], 'A', cut)
        self.assertEqual(c.select_slot(old, new)[1], 'B')

    def test_corruption_any_used_byte(self):
        raw = c.encode_slot(c.defaults(), 1)
        used = len(c.encode_payload(c.defaults()))
        for offset in list(range(32+used)) + list(range(1504,1536)):
            broken = bytearray(raw); broken[offset] ^= 1
            with self.assertRaises(ValueError):
                c.decode_slot(bytes(broken))

    def test_unknown_schema_tie_and_overflow(self):
        a = c.encode_slot(c.defaults(), 1)
        b = c.encode_slot(dict(c.defaults(), i_gain=1.01), 1)
        with self.assertRaises(ValueError): c.select_slot(a,b)
        unknown = bytearray(a)
        unknown[4:6] = b'\2\0'
        unknown[24:28] = bytes(4)
        checksum = struct.pack('<I', c.crc(unknown[:32] + unknown[32:32+len(c.encode_payload(c.defaults()))]))
        unknown[24:28] = checksum
        unknown[1516:1520] = checksum
        with self.assertRaises(c.Unsupported): c.select_slot(a, bytes(unknown))
        with self.assertRaises(ValueError): c.encode_slot(c.defaults(), 2**64)
        self.assertEqual(c.select_slot(a,a)[1], 'A')

    def test_nominal_physical_vectors(self):
        cfg = c.defaults()
        self.assertEqual(c.engineering(480, 25600, 3200, cfg), (1,5,5,25))
        self.assertEqual(c.engineering(-480, 25600, 3200, cfg), (-1,5,-5,25))
        self.assertEqual(c.engineering(1920, 25600, 3200, dict(cfg,adc_range=1)), (1,5,5,25))
        self.assertEqual(c.engineering(192000, 25600, 3200, cfg)[0], 400)

    def test_crossing_integral(self):
        positive, negative = c.split_integral(1,-1,2)
        self.assertAlmostEqual(positive, .5/3600)
        self.assertAlmostEqual(negative, .5/3600)

    def test_native_manifest(self):
        manifest = json.loads((ROOT/'tests/fixtures/manifest.json').read_text())
        for name, item in manifest['fixtures'].items():
            data = (ROOT/'tests/fixtures'/name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'], name)
            if not name.startswith('native-'): continue
            exp = item['expected']
            if 'error' in exp:
                with self.assertRaises(ValueError): c.read_native(data)
                continue
            result = c.read_native(data)
            self.assertEqual(len(result['rows']), exp['verified_rows'], name)
            self.assertEqual(result['clean'], exp['clean'], name)
            for key in ('Whc', 'Whd'):
                if key in exp: self.assertAlmostEqual(result['rows'][-1][key], exp[key])
            if 'unverified_rows' in exp: self.assertEqual(len(result['unverified_rows']), exp['unverified_rows'])
            if 'partial_line' in exp: self.assertEqual(result['partial_line'], exp['partial_line'])

    def test_invalid_never_zero_and_gap_not_integrated(self):
        data = c.read_native((ROOT/'tests/fixtures/native-gap.csv').read_bytes())
        self.assertIsNone(data['rows'][1]['I_A'])
        self.assertEqual(data['rows'][2]['Whd'], 0)
        self.assertEqual(data['rows'][-1]['quality'], 24)

    def test_bad_semantics_rejected_before_writer_output(self):
        meta = metadata()
        original = samples(meta, [(0,0,480),(1,20000,480)])
        for key, value in [('I_A',0), ('I_A',float('nan')), ('t_us',-1), ('quality',64), ('Whc',-1), ('vshunt_raw',999999), ('ms_from_start',999)]:
            rows = copy.deepcopy(original); rows[1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): c.write_native(meta,rows)

    def test_meta_and_end_tampering(self):
        data = (ROOT/'tests/fixtures/native-sign-crossing.csv').read_bytes()
        with self.assertRaises(ValueError): c.read_native(data.replace(b'Synthetic public', b'Synthetic privat',1))
        with self.assertRaises(ValueError): c.read_native(data.replace(b'"reason":"stop"',b'"reason":"bad!"',1))
        with self.assertRaises(ValueError): c.read_native(data+b'\n')
        with self.assertRaises(ValueError): c.strict_json('{"x":1,"x":2}')

    def test_checkpoint_crc_independent_of_semantics(self):
        data = (ROOT/'tests/fixtures/native-sign-crossing.csv').read_bytes()
        # Equivalent numeric formatting: sample semantics still pass, exact bytes do not.
        with self.assertRaisesRegex(ValueError, 'Checkpoint'):
            c.read_native(data.replace(b',1.0,5.0,5.0,', b',1.00,5.0,5.0,', 1))

    def test_utc_anchor_and_raw_rails(self):
        meta = metadata()
        rows = samples(meta, [(0,0,480),(1,20000,480)])
        meta['time'].update(utc_anchor='2026-09-07T00:00:00.000000Z', source='DS3231', uncertainty_us=1000000)
        for row, stamp in zip(rows, ['2026-09-07T00:00:00.000000Z', '2026-09-07T00:00:00.020000Z']):
            row['quality'] = 0; row['timestamp'] = stamp
        self.assertTrue(c.read_native(c.write_native(meta,rows))['clean'])
        rows[1]['timestamp'] = '2026-09-07T00:00:01.020000Z'
        with self.assertRaisesRegex(ValueError,'UTC anchor'): c.write_native(meta,rows)
        meta = metadata()
        rows = samples(meta, [(0,0,524287)])
        with self.assertRaisesRegex(ValueError,'rail'): c.write_native(meta,rows)

    def test_missing_metadata_and_incorrect_totals(self):
        meta = metadata(); rows = samples(meta, [(0,0,480),(1,20000,480)])
        broken = copy.deepcopy(meta); broken['hardware'].pop('topology')
        with self.assertRaises(ValueError): c.write_native(broken,rows)
        rows[1]['Whc'] = rows[1]['Wh_net'] = 0
        with self.assertRaisesRegex(ValueError,'Integration'): c.write_native(meta,rows)

    def assert_both_readers_reject(self,raw):
        with self.assertRaises(ValueError):c.read_native(raw)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):core.load(io.BytesIO(raw),Path(directory)/'rejected.sqlite')

    def test_v2_local_remote_and_unknown_clock_cross_reader_support(self):
        for corrected in (False,True):
            for grouped in (False,True):
                for known in (False,True):
                    with self.subTest(corrected=corrected,grouped=grouped,known=known):
                        meta=ecosystem_metadata(corrected,grouped)
                        if not known:meta['time'].update(utc_anchor=None,source='unknown')
                        raw=c.write_native(meta,[])
                        self.assertEqual(c.read_native(raw)['metadata'],meta)
                        with tempfile.TemporaryDirectory() as directory:
                            session=core.load(io.BytesIO(raw),Path(directory)/'accepted.sqlite')
                            try:
                                self.assertEqual(session.summary['metadata'],meta)
                                self.assertEqual(session.summary['format'],'R1S3 CSV v2')
                                self.assertEqual(session.summary['integrity'],'verified clean')
                            finally:session.close()

    def test_v2_bad_ecosystem_identity_and_version_rejected_with_valid_checksums(self):
        changes=[('version',2),('version',True),('device_id','02:11:22:33:44:5g'),
            ('device_id','00:00:00:00:00:00'),('device_id','02:aa:bb:cc:dd:ee'),
            ('boot_id','0000000000000000'),('boot_id','1234'),('boot_id',123),
            ('recording_id','FFFFFFFFFFFFFFFF'),('recording_id',None),
            ('group_id','0000000000000000'),('coordinator_id',None),('coordinator_boot_id',None)]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                meta=ecosystem_metadata();meta['ecosystem'][key]=value
                self.assert_both_readers_reject(unchecked_empty_file(meta))
        for missing in ('ecosystem','recording_id','rtc_correction'):
            with self.subTest(missing=missing):
                meta=ecosystem_metadata()
                (meta if missing=='ecosystem' else meta['ecosystem']).pop(missing)
                self.assert_both_readers_reject(unchecked_empty_file(meta))
        meta=ecosystem_metadata();meta['ecosystem']['unknown_extension']=1
        self.assert_both_readers_reject(unchecked_empty_file(meta))
        meta=ecosystem_metadata(grouped=False);meta['ecosystem']['coordinator_id']='02:AA:BB:CC:DD:EE'
        self.assert_both_readers_reject(unchecked_empty_file(meta))

    def test_v2_expired_or_malformed_clock_evidence_is_not_silently_accepted(self):
        changes=[('authority_id',''),('authority_boot_id','0000000000000000'),
            ('request_id','0000000000000000'),('clock_revision',-1),('clock_revision',True),
            ('clock_revision',2**32),('unix_s',946684799),('unix_s',4102444799),
            ('received_local_us','01'),('received_local_us','-1'),('received_local_us',123),
            ('received_local_us',str(2**64)),('applied_local_us','9007199254741008'),
            ('applied_local_us','9007199255741010'),('source_capture_us',str(2**64)),
            ('source_capture_us','01'),('source_capture_us',123),('source_capture_us','-1'),
            ('source_read_age_ms',1501),('source_read_age_ms',True),('source_read_age_ms',-1),
            ('roundtrip_us',1000001),('roundtrip_us',True),('roundtrip_us',-1),('uncertainty_us',0)]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                meta=ecosystem_metadata();meta['ecosystem']['rtc_correction'][key]=value
                self.assert_both_readers_reject(unchecked_empty_file(meta))
        for missing in ('authority_id','source_capture_us','source_read_age_ms'):
            with self.subTest(missing=missing):
                meta=ecosystem_metadata();meta['ecosystem']['rtc_correction'].pop(missing)
                self.assert_both_readers_reject(unchecked_empty_file(meta))
        # The boundaries are inclusive; IDs and large timestamp strings survive exactly.
        meta=ecosystem_metadata();correction=meta['ecosystem']['rtc_correction']
        correction.update(source_read_age_ms=1500,roundtrip_us=1000000,
            applied_local_us=str(int(correction['received_local_us'])+1000000))
        self.assertEqual(c.read_native(c.write_native(meta,[]))['metadata'],meta)

    def test_v2_coarse_time_never_claims_a_precision_bound_without_evidence(self):
        meta=ecosystem_metadata();meta['time']['uncertainty_us']=1100000
        self.assert_both_readers_reject(unchecked_empty_file(meta))
        meta=ecosystem_metadata();meta['time']['source']='DS3231'
        self.assert_both_readers_reject(unchecked_empty_file(meta))
        meta=ecosystem_metadata();meta['ecosystem']['rtc_correction']=None
        self.assert_both_readers_reject(unchecked_empty_file(meta))
        # v1's known UTC still requires its original explicit uncertainty contract.
        meta=metadata();meta['time'].update(utc_anchor='2026-09-09T00:00:00.000000Z',source='DS3231')
        self.assert_both_readers_reject(unchecked_empty_file(meta))

    def test_native_schema_and_column_mismatches_never_fall_back_to_legacy(self):
        v2=ecosystem_metadata()
        self.assert_both_readers_reject(unchecked_empty_file(v2,magic=c.MAGICS[1]))
        self.assert_both_readers_reject(unchecked_empty_file(metadata(),magic=c.MAGICS[2]))
        self.assert_both_readers_reject(unchecked_empty_file(v2,magic=b'# R1S3_LOG schema=3\n'))
        v2['schema']=3;self.assert_both_readers_reject(unchecked_empty_file(v2,magic=c.MAGICS[2]))
        v2=ecosystem_metadata()
        for columns in (c.COLUMNS[1:]+c.COLUMNS[:1],c.COLUMNS+['r3_time']):
            self.assert_both_readers_reject(unchecked_empty_file(v2,columns=','.join(columns)+'\n'))


if __name__ == '__main__':
    unittest.main()
