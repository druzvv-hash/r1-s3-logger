"""Opt-in production rate smoke recordings through the USB panel, without SAVE.

The output directory is private/ignored. The exact initial runtime configuration
is restored on exit while the same boot remains connected. Recordings are kept
on SD for independent validation; this tool does not infer integrity from counters.
"""
import argparse,json,subprocess,time,urllib.request
from pathlib import Path
import contracts
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hardware',required=True,action='store_true')
    p.add_argument('--rates',default='1,5,10,25,50,100,150,200,250,300')
    p.add_argument('--seconds',type=int,default=10)
    p.add_argument('--label',required=True)
    args=p.parse_args();rates=[int(v) for v in args.rates.split(',')]
    if not rates or any(not 1<=v<=300 for v in rates) or not 8<=args.seconds<=600:p.error('Rates 1..300, duration 8..600 seconds')
    if not args.label.replace('-','').replace('_','').isalnum():p.error('Simple output label required')
    out=ROOT/'data/production-rates'/args.label;out.mkdir(parents=True,exist_ok=False)
    url=json.loads((ROOT/'data/device-panel/session.json').read_text(encoding='utf8'))['url']
    def api(route,body=None):
        req=urllib.request.Request(url.replace('/?',route+'?'),data=body.encode() if body else None,headers={'X-R1-Panel':'1','Content-Type':'text/plain'})
        with urllib.request.urlopen(req,timeout=18) as r:return json.load(r)
    initial=api('/api/state');owned='';results=[]
    assert initial['ready'] and not initial['benchmark'] and initial['recording_state']=='READY' and not initial['file_transfer']
    (out/'baseline.json').write_text(json.dumps(initial),encoding='utf8')
    config=contracts.decode_payload(bytes.fromhex(initial['config_hex']))
    script="const fs=require('fs'),{configForRate}=require('./device_ui/rate_profile.js');const v=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(v.rates.map(hz=>configForRate(v.config,hz))));"
    node=r'C:\Program Files\nodejs\node.exe'
    profiles=json.loads(subprocess.check_output([node,'-e',script],cwd=ROOT,input=json.dumps(dict(config=config,rates=rates)).encode()))
    def state():
        s=api('/api/state');assert s['boot']==initial['boot'],'Unexpected reboot';return s
    def command(verb):
        s=state();r=api('/api/command',f"{s['boot']} {s['revision']} {verb}");assert r.get('ok'),r.get('message')
    def wait_phase(phase):
        for _ in range(24):
            time.sleep(.3);s=state()
            if s['recording_state']==phase:return s
            assert s['recording_state']!='ERROR',s.get('recording_error')
        raise RuntimeError('Timed out waiting for '+phase)
    try:
        for n,profile in enumerate(profiles):
            command('APPLY '+contracts.encode_payload(profile).hex());time.sleep(1)
            baseline=state();assert baseline['requested_hz']==profile['requested_rate_hz']
            command('START');s=wait_phase('RUNNING');owned=s['recording_path']
            snapshots=[s];began=time.monotonic()
            while time.monotonic()-began<args.seconds:
                time.sleep(.8);s=state();snapshots.append(s)
                assert s['recording_state']=='RUNNING' and s['recording_path']==owned,'Recording changed'
            command('STOP');s=wait_phase('READY');owned=''
            result={k:s.get(k) for k in ('firmware','boot','recording_path','recording_rows','recording_bytes','recording_seconds','recording_error','recording_overflows','recording_high_water','recording_write_us','recording_sync_us','generation','i2c_hz','requested_hz')}
            result.update(missed=s['missed_samples']-baseline['missed_samples'],invalid=s['invalid_samples']-baseline['invalid_samples'],oled_frames=s['oled_frames']-baseline['oled_frames'],snapshots=len(snapshots),fresh_snapshots=len(set(v['uptime_ms'] for v in snapshots)))
            (out/f'{n:02}-snapshots.json').write_text(json.dumps(snapshots),encoding='utf8')
            results.append(result);(out/'report.json').write_text(json.dumps(results,indent=2),encoding='utf8')
            print(json.dumps(result),flush=True)
            assert s['generation']==initial['generation'],'EEPROM generation changed'
    finally:
        s=api('/api/state')
        if s['boot']==initial['boot']:
            if owned and s['recording_path']==owned and s['recording_state']=='RUNNING':command('STOP');s=wait_phase('READY')
            if s['recording_state']=='READY':
                command('APPLY '+initial['config_hex']);time.sleep(1);s=state()
                assert s['config_hex']==initial['config_hex'] and s['generation']==initial['generation']
                (out/'restored.json').write_text(json.dumps(dict(restored=True,boot=s['boot'],generation=s['generation'],requested_hz=s['requested_hz'])))
    return 0
if __name__=='__main__':raise SystemExit(main())
