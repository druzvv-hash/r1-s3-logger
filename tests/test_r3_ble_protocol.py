"""Verify BLE S1 framing on a host, without Arduino, radio or hardware."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class R3BleProtocol(unittest.TestCase):
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
        cls.exe = Path(cls.tmp.name) / 'r3-ble-protocol-test.exe'
        result = subprocess.run([
            compiler, '-std=c++11', '-O2', '-static', '-Wall', '-Wextra', '-Werror',
            '-Ifirmware/include', 'tests/r3_ble_protocol_host.cpp', '-o', str(cls.exe),
        ], cwd=ROOT, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

    def run_mode(self, mode):
        result = subprocess.run([str(self.exe), mode], check=True,
                                capture_output=True, text=True, timeout=10)
        self.assertIn(mode.upper() + ' PASS', result.stdout)

    def test_independent_golden_frames_and_crc(self):
        self.run_mode('golden')

    def test_lengths_bit_errors_and_unsupported_semantics(self):
        self.run_mode('strict')

    def test_full_integer_ranges_and_invalid_utc_evidence(self):
        self.run_mode('boundary')

    def test_mtu_uuid_and_canonical_device_ids(self):
        self.run_mode('helper')


class R3BleSharedHeader(unittest.TestCase):
    def test_r3_and_r1_headers_are_identical(self):
        # Separate public repos: local integration checks both copies when R3
        # is checked out alongside R1-S3. R1-only CI has no sibling checkout.
        r3_root = Path(os.environ.get('R3_REPO', ROOT.parent / 'lily-logger-r3'))
        remote_header = r3_root / 'cc/include/r3_ble_protocol.h'
        if not remote_header.is_file():
            self.skipTest('Set R3_REPO to the R3 checkout for cross-repo comparison')
        local_header = ROOT / 'firmware/include/r3_ble_protocol.h'
        self.assertEqual(local_header.read_bytes(), remote_header.read_bytes())


if __name__ == '__main__':
    unittest.main()
