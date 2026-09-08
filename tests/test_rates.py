"""Production range, forward protection, and cross-language quick profiles."""
import json, subprocess, unittest
from pathlib import Path
from test_contracts import c
ROOT=Path(__file__).resolve().parents[1]

class RateTests(unittest.TestCase):
    def test_all_integer_profiles_and_legacy_encoding(self):
        script="""
const {configForRate,RATE_PRESETS,previewDelivery}=require('./device_ui/rate_profile.js');
const {encodeConfig,exportProfile,importProfile}=require('./device_ui/codec.js');
const fields=require('./schemas/config-v1.json').fields;
const baseline=Object.fromEntries(fields.map(f=>[f.name,f.default]));
const assert=require('node:assert/strict');
assert.deepEqual(RATE_PRESETS,[1,5,10,25,50,100,150,200,250,300]);
assert.deepEqual(previewDelivery({newest:360,cursor:300},'wifi',300),{catchUp:true,resync:false});
assert.deepEqual(previewDelivery({newest:360,cursor:360},'wifi',300),{catchUp:false,resync:false});
assert.deepEqual(previewDelivery({newest:1000,cursor:200},'usb',300),{catchUp:false,resync:true});
assert.deepEqual(previewDelivery({newest:360,cursor:300},'usb',300),{catchUp:false,resync:false});
for(const invalid of [0,301,1.5,NaN,Infinity])assert.throws(()=>configForRate(baseline,invalid));
const result=[];
for(let hz=1;hz<=300;hz++){
 const config=configForRate(baseline,hz);const profile=exportProfile(config,fields);assert.deepEqual(importProfile(profile,fields),config);assert.throws(()=>importProfile({...profile,minor:2},fields));if(profile.minor)assert.throws(()=>importProfile({...profile,minor:0},fields));result.push({config,hex:encodeConfig(config,fields)});
}
process.stdout.write(JSON.stringify(result));
"""
        run=subprocess.run([r'C:\Program Files\nodejs\node.exe','-e',script],cwd=ROOT,check=True,capture_output=True,text=True)
        for item in json.loads(run.stdout):
            config=item['config'];hz=config['requested_rate_hz']
            self.assertEqual(item['hex'],c.encode_payload(config).hex())
            gen,decoded=c.decode_slot(c.encode_slot(config,42))
            self.assertEqual((gen,decoded),(42,config))
            self.assertGreaterEqual(config['max_gap_us'],2000000/hz)
            self.assertEqual(config['shunt_uohm'],150)
            self.assertEqual(config['adc_range'],0)
        self.assertEqual(c.encode_slot(c.defaults(),1)[6:8],b'\0\0')

    def test_new_values_have_forward_protection(self):
        config=c.defaults();config['requested_rate_hz']=37
        self.assertEqual(c.encode_slot(config,1)[6:8],b'\x01\0')
        for bad in [0,301,1.5,True]:
            config['requested_rate_hz']=bad
            with self.assertRaises(ValueError):c.encode_payload(config)

if __name__=='__main__':unittest.main()
