"""Explicit R1 hardware OTA bench. Run only on an idle, user-authorized device.
Reads the existing panel password in memory; never prints or saves credentials.
"""
import base64,json,time,urllib.request,urllib.error
from pathlib import Path
BASE='http://192.168.0.149'
def call(path,body=None,headers=None):
    req=urllib.request.Request(BASE+path,data=body,headers=headers or {})
    try:
        with urllib.request.urlopen(req,timeout=60) as r:return r.status,r.read()
    except urllib.error.HTTPError as e:return e.code,e.read()
def state():return json.loads(call('/api/state')[1])
def run():
    before=state();assert before['recording_state']=='READY'
    auth={'Authorization':'Basic '+base64.b64encode(('admin:'+before['ap_password']).encode()).decode()}
    assert call('/update')[0]==401
    assert call('/update',headers=auth)[0]==200
    slot=json.loads(call('/api/ota',headers=auth)[1])['slot']
    def upload(data,size=None,origin=BASE):
        boundary='r1otabench'
        body=('--'+boundary+'\r\nContent-Disposition: form-data; name="firmware"; filename="firmware.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+data+('\r\n--'+boundary+'--\r\n').encode()
        return call('/update',body,{**auth,'Content-Type':'multipart/form-data; boundary='+boundary,'X-R1-Panel':'1','X-R1-Size':str(size if size is not None else len(data)),'Origin':origin})
    for label,data,size,origin in [('origin',b'x'*512,512,'http://other.invalid'),('header',b'x'*512,512,BASE)]:
        code,body=upload(data,size,origin);assert code==400,(code,body);print(label,'rejected')
    image=Path('.pio/build/esp32-s3-usb/firmware.bin').read_bytes()
    code,body=upload(image[:4096],len(image));assert code==400,(code,body)
    time.sleep(1)
    after=state();assert after['boot']==before['boot'];assert after['config_hex']==before['config_hex'];print('truncated rejected; owner resumed')
    code,body=upload(image);assert code==200,(code,body);print('OTA image accepted')
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        time.sleep(2)
        try:
            after=state()
            if after.get('ready') and after.get('boot')!=before['boot']:break
        except Exception:pass
    else:raise RuntimeError('No reboot after OTA')
    afterslot=json.loads(call('/api/ota',headers=auth)[1])['slot']
    assert slot!=afterslot,(slot,afterslot)
    assert after['config_hex']==before['config_hex'];assert after['generation']==before['generation']
    print('PASS',slot,'->',afterslot,after['firmware'],'config/generation preserved',after['recording_state'])
if __name__=='__main__':run()
