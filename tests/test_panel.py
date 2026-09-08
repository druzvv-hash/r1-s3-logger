"""Wire compatibility and loopback API boundaries; no physical hardware required."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import contracts

class CodecTests(unittest.TestCase):
    def test_js_matches_reference_and_rejects_damage(self):
        node=shutil.which('node') or r'C:\Program Files\nodejs\node.exe'
        subprocess.run([node,'--check','device_ui/app.js'],cwd=ROOT,check=True,capture_output=True)
        cases=[contracts.defaults()]
        changed=contracts.defaults();changed.update(polarity=-1,i_zero_uV=-12.3125,calibration_note='Еталон Ω / bench',queue_bytes=1048576)
        cases.append(changed)
        script=r"""
const fs=require('fs'),assert=require('node:assert/strict');
const {encodeConfig,decodeConfig}=require('./device_ui/codec.js');
const registry=require('./schemas/config-v1.json').fields;
for(const item of JSON.parse(fs.readFileSync(0,'utf8'))){
 assert.equal(encodeConfig(item.values,registry),item.hex);
 assert.deepEqual(decodeConfig(item.hex,registry),item.values);
 assert.throws(()=>decodeConfig(item.hex.slice(0,-2),registry));
 assert.throws(()=>decodeConfig('ffff'+item.hex.slice(4),registry));
 assert.throws(()=>decodeConfig(item.hex+'00',registry));
 assert.throws(()=>encodeConfig({...item.values,i_gain:NaN},registry));
 assert.throws(()=>encodeConfig({...item.values,calibration_note:'Ω'.repeat(257)},registry));
 assert.throws(()=>encodeConfig({...item.values,queue_bytes:1.5},registry));
}
"""
        subprocess.run([node,'-e',script],cwd=ROOT,input=json.dumps([dict(values=c,hex=contracts.encode_payload(c).hex()) for c in cases]),text=True,check=True,capture_output=True)
    def test_bundle_is_reproducible(self):
        spec=importlib.util.spec_from_file_location('build_panel',ROOT/'tools/build_panel.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        html=(ROOT/'device_ui/index.html').read_bytes();header=(ROOT/'firmware/include/panel_assets.h').read_bytes()
        module.build()
        self.assertEqual(html,(ROOT/'device_ui/index.html').read_bytes())
        self.assertEqual(header,(ROOT/'firmware/include/panel_assets.h').read_bytes())

class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            spec=importlib.util.spec_from_file_location('bridge',ROOT/'device_ui/bridge.py')
            cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(str(exc))
    def setUp(self):
        class Fake:
            def __init__(self):self.commands=[];self.stopped=False
            def stop(self):self.stopped=True
            def request(self,command):
                self.commands.append(command)
                return dict(ready=True,ok=True)
        self.device=Fake()
        self.server=self.module.PanelServer(('127.0.0.1',0),self.device,'test-token')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def call(self,path,body=None,**headers):
        req=urllib.request.Request(self.url+path,data=body,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=3) as r:return r.status,r.read()
        except urllib.error.HTTPError as e:return e.code,e.read()
    def test_auth_and_origin_do_not_touch_serial(self):
        self.assertEqual(self.call('/api/state')[0],403)
        self.assertEqual(self.call('/api/command?token=test-token',b'abc')[0],403)
        self.assertEqual(self.call('/api/command?token=test-token',b'abc',**{'X-R1-Panel':'1','Origin':'http://example.org'})[0],403)
        self.assertEqual(self.device.commands,[])
    def test_read_and_command_and_bounds(self):
        self.assertEqual(self.call('/api/state?token=test-token')[0],200)
        self.assertEqual(self.call('/api/command?token=test-token',b'abcd 1 SD',**{'X-R1-Panel':'1'})[0],200)
        self.assertEqual(self.device.commands,['STATE','DO abcd 1 SD'])
        self.assertEqual(self.call('/api/command?token=test-token',b'a'*3100,**{'X-R1-Panel':'1'})[0],413)
        self.assertEqual(self.call('/api/command?token=test-token',b'a\nCONFIG SAVE',**{'X-R1-Panel':'1'})[0],503)
        self.assertEqual(len(self.device.commands),2)
    def test_shutdown_closes_device_before_ack(self):
        code,body=self.call('/api/shutdown?token=test-token',b'',**{'X-R1-Panel':'1'})
        self.assertEqual(code,200)
        self.assertTrue(json.loads(body)['ok'])
        self.assertTrue(self.device.stopped)
if __name__=='__main__':unittest.main()
