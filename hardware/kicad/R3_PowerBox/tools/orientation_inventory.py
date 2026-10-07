"""Read-only physical audit inventory. Run with KiCad Python."""
import json
from pathlib import Path
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1]
b=k.LoadBoard(str(ROOT/'R3_power.kicad_pcb'))
def xy(p): return [round(k.ToMM(p.x),6),round(k.ToMM(p.y),6)]
result=[]
for f in b.GetFootprints():
    fid=f.GetFPID()
    result.append(dict(ref=f.GetReference(),value=f.GetValue(),fp=str(fid.GetLibNickname())+':'+str(fid.GetLibItemName()),xy=xy(f.GetPosition()),rotation=f.GetOrientationDegrees(),side=k.LayerName(f.GetLayer()),dnp=f.IsDNP(),pads=[dict(num=p.GetNumber(),net=str(p.GetNetname()),xy=xy(p.GetPosition()),local=xy(p.GetFPRelativePosition()),size=xy(p.GetSize()),drill=xy(p.GetDrillSize())) for p in f.Pads()],reference=dict(xy=xy(f.Reference().GetPosition()),visible=f.Reference().IsVisible(),layer=k.LayerName(f.Reference().GetLayer()),mirrored=f.Reference().IsMirrored())))
(ROOT/'reports/orientation_inventory.json').write_text(json.dumps(result,indent=2)+'\n')
for r in sorted(result,key=lambda r:r['ref']):
    if r['ref'].startswith(('U','Q','D','J','SW')) or r['ref'] in ('C1','C40','C41','C42','C43','C44','R40'):
        print(r['ref'],r['value'],r['fp'],r['xy'],r['rotation'],r['side'])
        print(' '.join(f"{p['num']}:{p['local']}={p['net']}" for p in r['pads'] if p['num']))
