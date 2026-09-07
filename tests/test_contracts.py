import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import contracts as c
from make_contract_fixtures import metadata, samples


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


if __name__ == '__main__':
    unittest.main()
