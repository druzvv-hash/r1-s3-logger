"""Firmware serializer -> independent contract and production viewer roundtrip."""
import hashlib
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
