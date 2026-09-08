"""Absolute acquisition deadlines: delay, missed slots, rate changes and long uptime."""
from pathlib import Path
import shutil,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class SampleClock(unittest.TestCase):
    def test_deadlines(self):
        compiler=shutil.which('g++') or 'C:/Qt/Tools/mingw1310_64/bin/g++.exe'
        if not Path(compiler).exists():self.skipTest('Native C++ compiler unavailable')
        with tempfile.TemporaryDirectory() as directory:
            exe=Path(directory)/'sample-clock.exe'
            subprocess.run([compiler,'-std=c++11','-static','-Ifirmware/include','tests/sample_clock_host.cpp','-o',str(exe)],cwd=ROOT,check=True,capture_output=True)
            result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
            self.assertIn('SAMPLE CLOCK PASS',result.stdout)
