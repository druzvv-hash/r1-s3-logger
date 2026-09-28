"""Independent pad/track domain audit, not a replacement for KiCad DRC."""
import json
import sys
import argparse
from pathlib import Path
import pcbnew as k
ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser()
parser.add_argument('board',nargs='?',type=Path,default=ROOT/'R3_power.kicad_pcb')
parser.add_argument('--output',type=Path,default=ROOT/'reports'/'routing_domain_audit.json')
args=parser.parse_args()
path=args.board
b=k.LoadBoard(str(path))
isolated={'+5V_ISO_RAW','+5V_ISO_A','+5V_ISO_D','+3V3_A_ISO',
          '+3V3_D_ISO','+5V_INA_RAW','-5V_INA_RAW','+5V_INA','-5V_INA',
          'GND_ISO','ADM7150_REF','EN_3V3_A_ISO','N$13','N$14'}
issues=[]
for f in b.GetFootprints():
    for p in f.Pads():
        if not any(p.GetLayerSet().Contains(layer) for layer in
                   (k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)): continue
        net=str(p.GetNetname())
        if not net: continue
        box=p.GetBoundingBox()
        lo,hi=k.ToMM(box.GetLeft()),k.ToMM(box.GetRight())
        item=f'{f.GetReference()}.{p.GetNumber()}'
        if lo<124 and hi>121: issues.append(dict(kind='barrier_pad',item=item,net=net,x=[lo,hi]))
        if net.startswith('unconnected-'): continue
        if net in isolated and lo<124: issues.append(dict(kind='isolated_pad_on_primary',item=item,net=net))
        if net not in isolated and hi>121: issues.append(dict(kind='primary_pad_on_isolated',item=item,net=net))
for t in b.GetTracks():
    box=t.GetBoundingBox(); lo,hi=k.ToMM(box.GetLeft()),k.ToMM(box.GetRight())
    if lo<124 and hi>121: issues.append(dict(kind='barrier_track_via',net=str(t.GetNetname())))
report={'board':path.name,'footprints':len(b.GetFootprints()),
        'track_via_objects':len(b.GetTracks()),'issues':issues,
        'scope':'Copper pad bounding boxes and tracks/vias; zones require separate filled-copper audit and DRC.'}
print(json.dumps(report,indent=2))
args.output.write_text(json.dumps(report,indent=2)+'\n')
sys.exit(bool(issues))
