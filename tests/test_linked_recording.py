"""Exercise coordination failures independently of radio and SD hardware."""
from pathlib import Path
import shutil, subprocess, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1]
class LinkedRecording(unittest.TestCase):
    def test_coordination(self):
        compiler=shutil.which('g++') or 'C:/Qt/Tools/mingw1310_64/bin/g++.exe'
        if not Path(compiler).exists(): self.skipTest('Native C++ compiler unavailable')
        with tempfile.TemporaryDirectory() as directory:
            exe=Path(directory)/'linked.exe'
            subprocess.run([compiler,'-std=c++11','-static','-Ifirmware/include','tests/linked_recording_host.cpp','-o',str(exe)],cwd=ROOT,check=True,capture_output=True)
            result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
            self.assertIn('LINKED RECORDING PASS',result.stdout)
