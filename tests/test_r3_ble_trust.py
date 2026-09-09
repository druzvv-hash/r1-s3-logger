"""Portable trust policy and fresh-time admission tests; no radio required."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TrustPolicy(unittest.TestCase):
    def test_policy_and_freshness_boundaries(self):
        compiler = os.environ.get('R1_HOST_CXX') or shutil.which('g++')
        qt = Path('C:/Qt/Tools/mingw1310_64/bin/g++.exe')
        if not compiler and qt.exists():
            compiler = str(qt)
        if not compiler:
            self.skipTest('Set R1_HOST_CXX to a native C++ compiler')
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'trust-test.exe'
            subprocess.run([compiler, '-std=c++11', '-O2', '-static', '-Wall', '-Wextra', '-Werror',
                            '-Ifirmware/include', 'tests/r3_ble_trust_host.cpp', '-o', str(exe)],
                           cwd=ROOT, check=True, timeout=60, capture_output=True)
            result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=10)
            self.assertIn('PASS versioned trust', result.stdout)

    def test_shared_ecosystem_protocol(self):
        r3 = Path(os.environ.get('R3_REPO', ROOT.parent / 'lily-logger-r3'))
        source = r3 / 'cc/include/ecosystem_protocol.h'
        if not source.is_file():
            self.skipTest('Sibling R3 checkout unavailable')
        self.assertEqual(source.read_bytes(), (ROOT / 'firmware/include/ecosystem_protocol.h').read_bytes())


if __name__ == '__main__':
    unittest.main()
