"""Exercise actual HTTP streaming and corrupt/truncated serial replies without hardware."""
import binascii
import http.client
import importlib.util
import json
from pathlib import Path
import threading
import unittest
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sd_bridge',ROOT/'device_ui/bridge.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)

class DownloadTests(unittest.TestCase):
    def setUp(self):
        class Device:
            data=bytes(range(256))*17+b'\x00\xff\r\nlast'
            fault=None
            def __init__(self):self.commands=[]
            def request(self,cmd):
                self.commands.append(cmd);parts=cmd.split()
                if parts[1]=='OPEN':return dict(ok=True,session=123,size=len(self.data))
                if parts[1]=='CLOSE':return dict(ok=True)
                if parts[1]=='READ':
                    offset=int(parts[3]);data=self.data[offset:offset+2048]
                    r=dict(ok=True,session=123,size=len(self.data),offset=offset,hex=data.hex(),crc32=binascii.crc32(data))
                    if self.fault and offset==2048:
                        if self.fault=='crc':r['crc32']^=1
                        elif self.fault=='short':r['hex']=r['hex'][:-2]
                        elif self.fault=='offset':r['offset']+=1
                        elif self.fault=='session':r['session']+=1
                        elif self.fault=='size':r['size']+=1
                        elif self.fault=='disconnect':raise OSError('unplugged')
                    return r
                raise AssertionError(cmd)
        self.device=Device();self.server=bridge.PanelServer(('127.0.0.1',0),self.device,'test')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def test_binary_exact_and_attachment_unicode(self):
        path='/тест #1.csv'.encode().hex()
        with urllib.request.urlopen(self.url+'/api/download?token=test&path='+path) as r:
            self.assertEqual(r.read(),self.device.data)
            self.assertIn("filename*=UTF-8''%D1%82",r.headers['Content-Disposition'])
            self.assertEqual(r.headers['Content-Type'],'application/octet-stream')
        # Cleanup may run just after the last response byte reaches the client.
        with urllib.request.urlopen(self.url+'/?token=test') as r:r.read()
        self.assertIn('FILES CLOSE 123',self.device.commands)
    def test_zero_byte_file(self):
        self.device.data=b''
        with urllib.request.urlopen(self.url+'/api/download?token=test&path=2f656d707479') as r:
            self.assertEqual(r.headers['Content-Length'],'0');self.assertEqual(r.read(),b'')
    def test_mid_download_fault_never_returns_complete_file(self):
        for fault in ('crc','short','offset','session','size','disconnect'):
            with self.subTest(fault=fault):
                self.device.fault=fault
                with urllib.request.urlopen(self.url+'/api/download?token=test&path=2f74657374') as r:
                    with self.assertRaises(http.client.IncompleteRead) as cm:r.read()
                    self.assertEqual(cm.exception.partial,self.device.data[:2048])
    def test_paths_and_commands_rejected_before_serial(self):
        for raw in (b'../secret',b'/../secret',b'/a/./b',b'/a//b',b'/a\\b',b'/x\0y',b'/x\ny',b'/a/',b'/a:b'):
            with self.assertRaises(ValueError):bridge.file_path(raw.hex())
        for cmd in ('READ 1 -1','READ 1 4294967296','OPEN 2f00','LIST 2f\nEEPROM','CLOSE 1 extra',''):
            with self.assertRaises(ValueError):bridge.file_command(cmd)
        for query in ('path=2f2e2e2f78&token=test','path=2f74657374'):
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(self.url+'/api/download?'+query)
            self.assertIn(e.exception.code,(400,403))
        self.assertEqual(self.device.commands,[])

if __name__=='__main__':unittest.main()
