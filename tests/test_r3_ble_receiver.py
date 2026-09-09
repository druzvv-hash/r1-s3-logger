"""Exercise the portable BLE receiver state used across authenticated links."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class R3BleReceiver(unittest.TestCase):
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
        cls.exe = Path(cls.tmp.name) / 'r3-ble-receiver-test.exe'
        result = subprocess.run([
            compiler, '-std=c++11', '-O2', '-static', '-Wall', '-Wextra', '-Werror',
            '-Ifirmware/include', 'tests/r3_ble_receiver_host.cpp',
            'firmware/src/r3_time_beacon.cpp', '-o', str(cls.exe),
        ], cwd=ROOT, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

    def run_mode(self, mode):
        result = subprocess.run([str(self.exe), mode], check=True,
                                capture_output=True, text=True, timeout=10)
        self.assertIn(mode.upper() + ' PASS', result.stdout)

    def test_selected_identity_boot_and_freshness(self):
        self.run_mode('binding')

    def test_revision_race_and_replay_cannot_reset_history(self):
        self.run_mode('revision')

    def test_invalid_utc_stays_revoked_until_new_valid_evidence(self):
        self.run_mode('utc')

    def test_sequence_wrap_and_reconnect_do_not_invent_gaps(self):
        self.run_mode('reconnect')


if __name__ == '__main__':
    unittest.main()
