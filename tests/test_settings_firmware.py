"""Execute the same C++ settings/store code used by ESP32 and compare P1 bytes."""
import json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from test_contracts import c
ROOT=Path(__file__).resolve().parents[1]
class FirmwareSettings(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  compiler=os.environ.get('R1_HOST_CXX') or shutil.which('g++')
  if not compiler and Path('C:/Qt/Tools/mingw1310_64/bin/g++.exe').exists():compiler='C:/Qt/Tools/mingw1310_64/bin/g++.exe'
  if not compiler:raise unittest.SkipTest('Set R1_HOST_CXX to a native C++ compiler')
  cls.compiler=compiler
  cls.tmp=tempfile.TemporaryDirectory();cls.exe=Path(cls.tmp.name)/'settings-test.exe'
  subprocess.run([compiler,'-std=c++11','-O2','-static','-Ifirmware/include','tests/settings_host.cpp','firmware/src/settings_core.cpp','-o',str(cls.exe)],cwd=ROOT,check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_transaction_fault_injection(self):
  result=subprocess.run([str(self.exe)],check=True,capture_output=True,text=True);self.assertIn('C++ PASS',result.stdout)
 def test_benchmark_rate_gate_is_explicit(self):
  exe=Path(self.tmp.name)/'settings-benchmark.exe'
  subprocess.run([self.compiler,'-std=c++11','-O2','-static','-DR1_BENCHMARK=1','-Ifirmware/include','tests/settings_host.cpp','firmware/src/settings_core.cpp','-o',str(exe)],cwd=ROOT,check=True,capture_output=True)
  result=subprocess.run([str(exe)],check=True,capture_output=True,text=True);self.assertIn('C++ PASS',result.stdout)
 def test_cpp_codec_matches_python(self):
  variants=[c.defaults()]
  changed=c.defaults();changed.update(polarity=-1,i_gain=1.015,u_gain=.995,calibration_note='Синтетична перевірка',calibration_utc='2024-02-29T00:00:00Z',calibration_valid=True);variants.append(changed)
  for values in variants:
   payload=Path(self.tmp.name)/'payload';image=Path(self.tmp.name)/'image';payload.write_bytes(c.encode_payload(values))
   subprocess.run([str(self.exe),'roundtrip',str(payload),str(image)],check=True)
   self.assertEqual(image.read_bytes(),c.encode_slot(values,1))
  self.assertEqual(c.encode_slot(c.defaults(),1),bytes.fromhex((ROOT/'tests/fixtures/config-default-slot.hex').read_text()))
 def test_generated_registry_is_current(self):
  paths=[ROOT/'firmware/include/config_fields.h',ROOT/'firmware/include/config_codec_generated.inc'];before=[p.read_bytes() for p in paths]
  subprocess.run([os.sys.executable,'tools/generate_config.py'],cwd=ROOT,check=True)
  self.assertEqual(before,[p.read_bytes() for p in paths])
