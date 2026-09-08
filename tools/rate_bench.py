"""Opt-in timed bench recordings via the local USB panel; never saves EEPROM.

Requires esp32-s3-benchmark. Native records from experimental rates are diagnostic
artifacts, not released configuration presets. The firmware independently stops
each timed run and restores its initial volatile configuration.
"""
import argparse
import json
from pathlib import Path
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hardware',action='store_true',required=True)
    parser.add_argument('--cases',required=True,help='Semicolon-separated Hz:CT:AVG:I2C_Hz:seconds')
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    if not args.label.replace('-','').replace('_','').isalnum():parser.error('Simple output label required')
    cases=[tuple(map(int,item.split(':'))) for item in args.cases.split(';')]
    if any(len(c)!=5 or not 5<=c[4]<=600 for c in cases):parser.error('Each case needs five values; duration 5..600 s')
    out=ROOT/'data/rate-tests'/args.label;out.mkdir(parents=True,exist_ok=False)
    url=json.loads((ROOT/'data/device-panel/session.json').read_text())['url']
    def api(route,body=None):
        request=urllib.request.Request(url.replace('/?',route+'?'),data=body.encode() if body is not None else None,headers={'X-R1-Panel':'1','Content-Type':'text/plain'})
        with urllib.request.urlopen(request,timeout=18) as response:return json.load(response)
    def state():
        for attempt in range(4):
            try:return api('/api/state')
            except Exception:
                if attempt==3:raise
                time.sleep(1)
    initial=state()
    assert initial.get('benchmark') and initial['recording_state']=='READY' and not initial['file_transfer'],'Idle benchmark firmware required'
    (out/'baseline.json').write_text(json.dumps(initial),encoding='utf8')
    results=[]
    for number,case in enumerate(cases):
        baseline=state();assert baseline['boot']==initial['boot'] and baseline['config_hex']==initial['config_hex'] and baseline['recording_state']=='READY'
        reply=api('/api/command',f"{baseline['boot']} {baseline['revision']} BENCH "+' '.join(map(str,case)))
        result={'case':case,'accepted':reply.get('ok'),'message':reply.get('message')};snapshots=[]
        if reply.get('ok'):
            began=time.monotonic();last_uptime=baseline['uptime_ms'];last_fresh=began;max_age=0;finished=False
            while time.monotonic()-began<case[4]+35:
                time.sleep(1)
                s=state();snapshots.append(s)
                if s['boot']!=initial['boot']:
                    result.update(error='Unexpected reboot',reset_reason=s.get('reset_reason'));break
                now=time.monotonic()
                if s['uptime_ms']!=last_uptime:last_uptime=s['uptime_ms'];last_fresh=now
                max_age=max(max_age,now-last_fresh)
                if not s.get('benchmark_active') and s['revision']>reply['revision'] and s['recording_state'] not in ('RUNNING','STARTING','STOPPING'):
                    finished=True;break
            result.update(finished=finished,max_state_stale_s=round(max_age,3))
            if snapshots:
                final=snapshots[-1]
                result.update({k:final.get(k) for k in ('boot','firmware','recording_state','recording_path','recording_rows','recording_bytes','recording_seconds','recording_error','recording_high_water','recording_overflows','recording_write_us','recording_sync_us','reset_reason')})
                result.update(missed=final['missed_samples']-baseline['missed_samples'],invalid=final['invalid_samples']-baseline['invalid_samples'],restored=final['config_hex']==initial['config_hex'] and final['generation']==initial['generation'],oled_frames=final['oled_frames']-baseline['oled_frames'])
            (out/f'{number:02}-snapshots.json').write_text(json.dumps(snapshots),encoding='utf8')
        results.append(result);(out/'report.json').write_text(json.dumps(results,indent=2),encoding='utf8');print(json.dumps(result),flush=True)
        if reply.get('ok') and (not result.get('finished') or not result.get('restored') or result.get('recording_state')!='READY'):raise RuntimeError('Bench did not finish/restore; inspect device before another run')
    return 0

if __name__=='__main__':raise SystemExit(main())
