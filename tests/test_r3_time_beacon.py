"""Verify the current R3 beacon contract without Arduino, radio or hardware."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class R3TimeBeacon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = os.environ.get('R1_HOST_CXX') or shutil.which('g++')
        qt = Path('C:/Qt/Tools/mingw1310_64/bin/g++.exe')
        if not compiler and qt.exists():
            compiler = str(qt)
        if not compiler:
            raise unittest.SkipTest('Set R1_HOST_CXX to a native C++ compiler')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.exe = Path(cls.tmp.name) / 'r3-time-beacon-test.exe'
        result = subprocess.run([
            compiler, '-std=c++11', '-O2', '-static', '-Wall', '-Wextra', '-Werror',
            '-Ifirmware/include', 'tests/r3_time_beacon_host.cpp',
            'firmware/src/r3_time_beacon.cpp', '-o', str(cls.exe),
        ], cwd=ROOT, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

    def test_strict_current_emitter_contract(self):
        result = subprocess.run([str(self.exe), 'decoder'], check=True,
                                capture_output=True, text=True, timeout=10)
        self.assertIn('DECODER PASS', result.stdout)

    def test_observation_freshness_and_connection_segments(self):
        result = subprocess.run([str(self.exe), 'tracker'], check=True,
                                capture_output=True, text=True, timeout=10)
        self.assertIn('TRACKER PASS', result.stdout)
