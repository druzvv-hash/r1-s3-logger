"""Run firmware buffer code on host, including concurrent owners and storage faults."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RecordingBuffer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = os.environ.get('R1_HOST_CXX') or shutil.which('g++')
        qt = Path('C:/Qt/Tools/mingw1310_64/bin/g++.exe')
        if not compiler and qt.exists():
            compiler = str(qt)
        if not compiler:
            raise unittest.SkipTest('Set R1_HOST_CXX to a native C++ compiler')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = Path(cls.tmp.name) / 'buffer-test.exe'
        subprocess.run([
            compiler, '-std=c++11', '-O2', '-static', '-pthread',
            '-Ifirmware/include', '-Itests/fakes', 'tests/recording_buffer_host.cpp',
            'firmware/src/recording_buffer.cpp', 'firmware/src/recording_memory.cpp',
            'firmware/src/local_input.cpp', '-o', str(cls.exe),
        ], cwd=ROOT, check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fifo_and_block_faults(self):
        result = subprocess.run([str(self.exe)], check=True, capture_output=True,
                                text=True, timeout=45)
        self.assertIn('BUFFER C++ PASS', result.stdout)

    def test_memory_placement_and_failure(self):
        for mode in ('ready', 'psram-failure', 'dma-failure'):
            with self.subTest(mode=mode):
                result = subprocess.run([str(self.exe), mode], check=True,
                                        capture_output=True, text=True, timeout=10)
                self.assertIn('MEMORY PASS', result.stdout)
