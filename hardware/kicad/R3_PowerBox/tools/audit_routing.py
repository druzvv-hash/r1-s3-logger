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
    net=str(t.GetNetname())
    if net in isolated and lo<124:issues.append(dict(kind='isolated_track_on_primary',net=net))
    if net not in isolated and hi>121:issues.append(dict(kind='primary_track_on_isolated',net=net))

def rectangle(x1,y1,x2,y2):
    poly=k.SHAPE_POLY_SET();poly.NewOutline()
    for x,y in ((x1,y1),(x2,y1),(x2,y2),(x1,y2)):poly.Append(k.FromMM(x),k.FromMM(y))
    return poly

obstacles={'barrier':rectangle(121,0,124,120)}
for f in b.GetFootprints():
    if f.GetReference() in ('H1','H2','H3','H4','H5','H6'):
        x,y=k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y)
        obstacles[f.GetReference()]=rectangle(x-4,y-4,x+4,y+4)
zones=[]
for z in b.Zones():
    if z.GetIsRuleArea():continue
    poly=z.GetFilledPolysList(z.GetLayer());net=str(z.GetNetname())
    zones.append(dict(name=z.GetZoneName(),net=net,layer=k.LayerName(z.GetLayer()),
        outlines=poly.OutlineCount(),area_mm2=round(poly.Area()/1e12,3)))
    if poly.OutlineCount():
        box=poly.BBox();lo,hi=k.ToMM(box.GetLeft()),k.ToMM(box.GetRight())
        if (net in isolated and lo<124) or (net not in isolated and hi>121):
            issues.append(dict(kind='filled_zone_wrong_domain',name=z.GetZoneName()))
    for name,obstacle in obstacles.items():
        intersection=k.SHAPE_POLY_SET(poly);intersection.BooleanIntersection(obstacle)
        if intersection.Area()>1:
            issues.append(dict(kind='filled_zone_in_keepout',name=z.GetZoneName(),keepout=name,
                area_mm2=intersection.Area()/1e12))
report={'board':path.name,'footprints':len(b.GetFootprints()),
        'track_via_objects':len(b.GetTracks()),'filled_zones':zones,'issues':issues,
        'scope':'Pads/tracks/vias by physical domain; actual filled polygons intersected with corridor and six conservative 8 mm mounting envelopes. Does not certify EMC or functional safety.'}
print(json.dumps(report,indent=2))
args.output.write_text(json.dumps(report,indent=2)+'\n')
sys.exit(bool(issues))
