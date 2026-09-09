"""Firmware serializer -> independent contract and production viewer roundtrip."""
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import contracts
sys.path.insert(0,str(ROOT/'viewer'))
import core

class RecordingFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=os.environ.get('R1_HOST_CXX') or shutil.which('g++')
        qt=Path('C:/Qt/Tools/mingw1310_64/bin/g++.exe')
        if not compiler and qt.exists():compiler=str(qt)
        if not compiler:raise unittest.SkipTest('Native C++ compiler required')
        cls.tmp=tempfile.TemporaryDirectory();cls.folder=Path(cls.tmp.name)
        exe=cls.folder/'format.exe'
        command=[compiler,'-std=c++11','-O2','-static','-Ifirmware/include','tests/recording_format_host.cpp','firmware/src/recording_format.cpp','firmware/src/recording_buffer.cpp','firmware/src/settings_core.cpp','-o',str(exe)]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        subprocess.run([str(exe),str(cls.folder)],check=True,capture_output=True,text=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def read(self,name):return contracts.read_native((self.folder/name).read_bytes())
    def test_known_unknown_utc_and_signed_integration(self):
        for name in ('known.csv','unknown.csv'):
            with self.subTest(name=name):
                result=self.read(name)
                self.assertTrue(result['clean']);self.assertEqual(len(result['rows']),599)
                rows=result['rows'];self.assertTrue(rows[-1]['quality']&16)
                self.assertGreater(rows[-1]['Whc'],0);self.assertGreater(rows[-1]['Whd'],0)
                self.assertTrue(rows[300]['quality']&2)
                self.assertEqual(bool(rows[0]['quality']&8),name=='unknown.csv')
    def test_rotated_files_link_full_sha_and_keep_totals(self):
        first=self.read('part0.csv');second=self.read('part1.csv')
        self.assertEqual(second['metadata']['previous_part_sha256'],hashlib.sha256((self.folder/'part0.csv').read_bytes()).hexdigest())
        self.assertEqual(second['rows'][0]['seq'],first['rows'][-1]['seq']+1)
        self.assertGreater(second['rows'][0]['t_us'],first['rows'][-1]['t_us'])
        self.assertGreaterEqual(second['rows'][0]['Whd'],first['rows'][-1]['Whd'])
        contracts.parse_row((self.folder/'part1.csv').read_bytes().splitlines(keepends=True)[4],second['metadata'],first['rows'][-1])
    def test_empty_clean_and_interrupted_prefix(self):
        self.assertTrue(self.read('empty.csv')['clean']);self.assertFalse(self.read('empty.csv')['rows'])
        raw=(self.folder/'known.csv').read_bytes();pos=raw.index(b'# END ')
        interrupted=contracts.read_native(raw[:pos]);self.assertFalse(interrupted['clean']);self.assertEqual(len(interrupted['rows']),599)
        with self.assertRaises(ValueError):contracts.read_native(raw.replace(b'3,3,9',b'4,3,9',1))
    def test_ten_hz_gap_budget_keeps_real_integrals(self):
        result=self.read('ten-hz.csv')
        self.assertTrue(all(not row['quality']&2 for row in result['rows']))
        self.assertGreater(result['rows'][-1]['Whc'],0)
        self.assertGreater(result['rows'][-1]['Whd'],0)
    def test_production_viewer_reads_firmware_csv(self):
        with (self.folder/'known.csv').open('rb') as stream:
            session=core.load(stream,self.folder/'viewer.sqlite')
        try:
            self.assertEqual(session.summary['rows'],599)
        finally:session.db.close()
    def test_v2_real_serializer_keeps_local_and_remote_provenance_distinct(self):
        for name, grouped, corrected, known in (
            ('v2-local.csv',False,False,True), ('v2-remote.csv',True,True,True),
            ('v2-local-corrected.csv',False,True,True), ('v2-unknown.csv',False,True,False)):
            with self.subTest(name=name):
                parsed=self.read(name);meta=parsed['metadata'];eco=meta['ecosystem']
                self.assertTrue(parsed['clean']);self.assertEqual(meta['schema'],2)
                self.assertEqual(eco['device_id'],'02:11:22:33:44:55')
                self.assertEqual(eco['boot_id'],'123456789abcdef0')
                self.assertEqual(eco['recording_id'],'1020304050607080')
                self.assertEqual(eco['group_id'],'1122334455667788' if grouped else None)
                self.assertEqual(eco['coordinator_id'],'02:AA:BB:CC:DD:EE' if grouped else None)
                self.assertEqual(eco['coordinator_boot_id'],'8877665544332211' if grouped else None)
                self.assertEqual(meta['time']['source'],'DS3231/R3' if corrected and known else 'DS3231' if known else 'unknown')
                self.assertIsNone(meta['time']['uncertainty_us'])
                self.assertEqual(meta['time']['utc_anchor'] is not None,known)
                self.assertEqual(bool(parsed['rows'][0]['quality']&8),not known)
                if corrected:
                    correction=eco['rtc_correction']
                    self.assertEqual(correction['authority_boot_id'],'8877665544332211')
                    self.assertEqual(correction['source_capture_us'],'9007199254741009')
                    self.assertEqual(correction['received_local_us'],'500000')
                    self.assertEqual(correction['applied_local_us'],'800000')
                    self.assertEqual(correction['source_read_age_ms'],250)
                    self.assertEqual(correction['roundtrip_us'],100000)
                    self.assertIsNone(correction['uncertainty_us'])
                else:self.assertIsNone(eco['rtc_correction'])
                with (self.folder/name).open('rb') as stream:
                    session=core.load(stream,self.folder/(name+'.sqlite'))
                try:
                    self.assertEqual(session.summary['format'],'R1S3 CSV v2')
                    self.assertEqual(session.summary['metadata'],meta)
                    self.assertEqual(session.summary['rows'],30)
                    self.assertEqual(session.summary['integrity'],'verified clean')
                    self.assertEqual(any('accuracy is unknown' in item['message'] for item in session.summary['diagnostics']),known)
                finally:session.close()
    def test_v2_rotation_keeps_complete_frozen_evidence_and_monotonic_clock(self):
        first=self.read('v2-part0.csv');second=self.read('v2-part1.csv')
        self.assertEqual(first['metadata']['ecosystem'],second['metadata']['ecosystem'])
        self.assertEqual(first['metadata']['time'],second['metadata']['time'])
        self.assertEqual(second['metadata']['ecosystem']['rtc_correction']['clock_revision'],3)
        self.assertEqual(second['metadata']['previous_part_sha256'],hashlib.sha256((self.folder/'v2-part0.csv').read_bytes()).hexdigest())
        self.assertEqual(second['rows'][0]['seq'],first['rows'][-1]['seq']+1)
        self.assertEqual(second['rows'][0]['t_us']-first['rows'][-1]['t_us'],20000)
        contracts.parse_row((self.folder/'v2-part1.csv').read_bytes().splitlines(keepends=True)[4],second['metadata'],first['rows'][-1])
        with (self.folder/'v2-part1.csv').open('rb') as stream:
            session=core.load(stream,self.folder/'independent-v2-part.sqlite')
        try:
            self.assertEqual(session.summary['rows'],30)
            self.assertEqual(session.summary['metadata']['ecosystem'],second['metadata']['ecosystem'])
        finally:session.close()
    def test_v2_integrity_remains_required_even_with_valid_provenance(self):
        raw=(self.folder/'v2-remote.csv').read_bytes()
        prefix=raw[:raw.index(b'# END ')]
        self.assertFalse(contracts.read_native(prefix)['clean'])
        self.assertEqual(len(contracts.read_native(prefix)['rows']),30)
        broken=raw.replace(b'"clock_revision":3',b'"clock_revision":4',1)
        with self.assertRaisesRegex(ValueError,'CRC'):contracts.read_native(broken)
        with self.assertRaisesRegex(ValueError,'CRC'):core.load(io.BytesIO(broken),self.folder/'broken-v2.sqlite')
    def test_v1_firmware_files_keep_original_contract_and_known_bound(self):
        for name in ('known.csv','unknown.csv','part0.csv','part1.csv'):
            with self.subTest(name=name):
                raw=(self.folder/name).read_bytes();meta=contracts.read_native(raw)['metadata']
                self.assertTrue(raw.startswith(b'# R1S3_LOG schema=1\n'))
                self.assertNotIn('ecosystem',meta)
                self.assertEqual(meta['time']['uncertainty_us'],None if name=='unknown.csv' else 1100000)
