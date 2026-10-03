"""Fit charger bulk capacitors beside local bypasses, retain all other blocks."""
import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,pad,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
def move(ref,x,y,angle):
    f=b.FindFootprintByReference(ref);old={p.GetNumber():k.VECTOR2I(p.GetPosition()) for p in f.Pads()}
    f.SetPosition(vec(x,y));f.SetOrientationDegrees(angle);f.Reference().SetLayer(k.F_Fab)
    for p in f.Pads():
        for t in ts:
            if isinstance(t,k.PCB_VIA):continue
            if t.GetStart()==old[p.GetNumber()]:t.SetStart(p.GetPosition())
            if t.GetEnd()==old[p.GetNumber()]:t.SetEnd(p.GetPosition())
move('C77',46,46.9,180);move('C81',56,46.9,0);move('C87',57.2,50.7,90)
for t in ts:
    if isinstance(t,k.PCB_VIA) and t.GetPosition()==vec(56,49):
        old=k.VECTOR2I(t.GetPosition());t.SetPosition(vec(55.6,48.8))
        for s in ts:
            if isinstance(s,k.PCB_VIA):continue
            if s.GetStart()==old:s.SetStart(t.GetPosition())
            if s.GetEnd()==old:s.SetEnd(t.GetPosition())
line(b,'CHG_PMID',[point(pad(b,'C77',1)),(48.4,47.825),point(pad(b,'C80',1))],.8)
line(b,'VSYS_RAW',[point(pad(b,'C81',1)),(54,47.825),point(pad(b,'C86',1))],.8)
k.SaveBoard(str(BOARD),b)
