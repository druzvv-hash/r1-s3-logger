"""Guarded, local ADM7150 ECO. Never replay a routing-stage generator.

ADI top view requires 1..4 down the left, 5..8 up the right. Keep pin/net
identity; move each physical pad and its local bypass topology, NOT CPL angle.
Only U4/C40..44/R40 local copper is affected. External trunk anchors stay fixed.
"""
import hashlib,json
import pcbnew as k
from route_reva import ROOT,BOARD,vec,point
assert hashlib.sha256(BOARD.read_bytes()).hexdigest()=='f1cc618b274fae46e68432f66f089f505c7378a0eb8d68889083c54bba1eaa61','ECO already applied or source changed: review first'
b=k.LoadBoard(str(BOARD))
backup=ROOT/'tmp/orientation/pre_u4_0aeaea7.kicad_pcb'
assert not backup.exists(),'Preserved original exists; do not overwrite/replay'
backup.write_bytes(BOARD.read_bytes())
def reflect(p):return vec(k.ToMM(p.x),84-k.ToMM(p.y))
def local(p):return 137<k.ToMM(p.x)<151.5 and 34<k.ToMM(p.y)<50
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
changed=[];ts=b.GetTracks()
for t in ts:
    net=str(t.GetNetname());a=t.GetStart();end=t.GetEnd()
    selected=(local(a) and local(end) and t.GetLayer()!=k.In2_Cu and net in {'N$13','N$14','ADM7150_REF','EN_3V3_A_ISO','GND_ISO','+5V_ISO_A','+3V3_A_ISO'})
    if selected:
        changed.append(t.m_Uuid.AsString())
        if isinstance(t,k.PCB_VIA):t.SetPosition(reflect(a))
        else:t.SetStart(reflect(a));t.SetEnd(reflect(end))
    elif t.GetLayer()==k.In2_Cu:
        # Exactly two connections to retained distribution trunks.
        for getter,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
            p=getter()
            if (net=='+3V3_A_ISO' and p==vec(140.8,39.8)) or (net=='+5V_ISO_A' and p==vec(146.175,44.2)):
                setter(reflect(p));changed.append(t.m_Uuid.AsString())
for ref in ['C40','C41','C42','C43','C44','R40']:
    f=b.FindFootprintByReference(ref)
    oldref=k.VECTOR2I(f.Reference().GetPosition())
    f.SetPosition(reflect(f.GetPosition()));f.SetOrientationDegrees(-f.GetOrientationDegrees())
    f.Reference().SetPosition(reflect(oldref))
f=b.FindFootprintByReference('U4')
for p in f.Pads():
    if p.GetNumber() in [str(i) for i in range(1,9)]:p.SetPosition(reflect(p.GetPosition()))
# Add the SAME library fab/silk marks without globally updating footprints.
lib=k.FootprintLoad(str(ROOT/'footprints/R3_Power.pretty'),'LFCSP-8-1EP_3x3mm_P0.5mm_EP1.74x1.45mm')
for g in lib.GraphicalItems():
    if g.GetLayer()==k.F_Fab or (g.GetLayer()==k.F_SilkS and g.GetShape()==k.SHAPE_T_CIRCLE):
        copy=g.Duplicate();f.Add(copy);copy.Move(f.GetPosition())
k.SaveBoard(str(BOARD),b)
(ROOT/'reports/orientation_u4_eco.json').write_text(json.dumps({'original_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'local_track_uuids':changed,'moved_bypasses':['C40','C41','C42','C43','C44','R40'],'U4_origin_rotation_unchanged':True},indent=2)+'\n')
print('Local U4 physical-numbering ECO applied; requires DRC/refill/visual inspection.')
