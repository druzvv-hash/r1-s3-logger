"""Compare the prototype checkpoint against the immutable pre-routing board."""
import json
import subprocess
import re
import pcbnew as k
from route_reva import ROOT,BASELINE

scratch=ROOT/'tmp'/'invariant_baseline.kicad_pcb'
scratch.parent.mkdir(exist_ok=True)
scratch.write_bytes(subprocess.check_output(['git','show',BASELINE+
    ':hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
before=k.LoadBoard(str(scratch)); after=k.LoadBoard(str(ROOT/'R3_power.kicad_pcb'))
def pinmap(b):
    return sorted((f.GetReference(),p.GetNumber(),str(p.GetNetname()))
                  for f in b.GetFootprints() for p in f.Pads())
def xy(f):
    p=f.GetPosition()
    return [k.ToMM(p.x),k.ToMM(p.y),f.GetOrientationDegrees()]
def outline(b,layer):
    return sorted((int(d.GetShape()),tuple(d.GetStart()),tuple(d.GetEnd()))
                  for d in b.GetDrawings() if isinstance(d,k.PCB_SHAPE) and d.GetLayer()==layer)
fixed=[f'J{i}' for i in range(1,14)]+[f'H{i}' for i in range(1,7)]+['U3','U6','SW1','SW2','Q4']
locations={ref:xy(after.FindFootprintByReference(ref)) for ref in fixed}
checks={
    'all_pad_net_assignments_unchanged':pinmap(before)==pinmap(after),
    'fixed_mechanical_and_isolation_positions_unchanged':all(
        xy(before.FindFootprintByReference(ref))==locations[ref] for ref in fixed),
    'board_outline_unchanged':outline(before,k.Edge_Cuts)==outline(after,k.Edge_Cuts),
    'upper_board_envelope_unchanged':outline(before,k.Dwgs_User)==outline(after,k.Dwgs_User),
    'four_copper_layers':after.GetCopperLayerCount()==4,
    'ground_nets_distinct':after.FindNet('DGND').GetNetCode()!=after.FindNet('GND_ISO').GetNetCode(),
    'no_copper_zones_yet':not any(not z.GetIsRuleArea() for z in after.Zones()),
}
report={'baseline':BASELINE,'checks':checks,'fixed_locations_mm':locations,
        'tracks':sum(not isinstance(t,k.PCB_VIA) for t in after.GetTracks()),
        'vias':sum(isinstance(t,k.PCB_VIA) for t in after.GetTracks())}
caps=[p for f in after.GetFootprints() if f.GetReference().startswith('C') for p in f.Pads()]
via_holes_in_cap_lands=[]
for v in after.GetTracks():
    if not isinstance(v,k.PCB_VIA): continue
    pt=v.GetPosition(); radius=v.GetDrill()/2
    for p in caps:
        box=p.GetBoundingBox()
        dx=max(box.GetLeft()-pt.x,0,pt.x-box.GetRight())
        dy=max(box.GetTop()-pt.y,0,pt.y-box.GetBottom())
        if dx*dx+dy*dy < radius*radius:
            via_holes_in_cap_lands.append(p.GetParentFootprint().GetReference()+'.'+p.GetNumber())
checks['no_via_drills_in_capacitor_lands']=not via_holes_in_cap_lands
report['via_holes_in_cap_lands']=via_holes_in_cap_lands
drc=ROOT/'reports'/'routing_checkpoint_A0_drc.json'
if drc.exists():
    d=json.loads(drc.read_text(encoding='utf-8'))
    names=set(re.findall(r'\[([^\]]+)\]',' '.join(i['description']
        for finding in d['unconnected_items'] for i in finding['items'])))
    report['critical_local_nets_without_unconnected_findings']={
        n:n not in names for n in ('CHG_SW1','CHG_SW2','CHG_PMID','N$7','N$8')}
(ROOT/'reports'/'routing_invariants.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
