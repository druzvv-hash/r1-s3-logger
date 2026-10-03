import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,pad,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
f=b.FindFootprintByReference('C102');old={p.GetNumber():k.VECTOR2I(p.GetPosition()) for p in f.Pads()};f.SetPosition(vec(40.2,49.4))
for p in f.Pads():
    for t in ts:
        if isinstance(t,k.PCB_VIA):continue
        if t.GetStart()==old[p.GetNumber()]:t.SetStart(p.GetPosition())
        if t.GetEnd()==old[p.GetNumber()]:t.SetEnd(p.GetPosition())
for t in ts:
    if not isinstance(t,k.PCB_VIA):continue
    xy=point(t);new=None
    if xy in [(56.75,49.225),(57.65,49.225)]:new=(xy[0],48.1)
    if xy==(55.6,48.8):new=(55.65,49.2)
    if new:
        before=k.VECTOR2I(t.GetPosition());t.SetPosition(vec(*new))
        for s in ts:
            if isinstance(s,k.PCB_VIA):continue
            if s.GetStart()==before:s.SetStart(t.GetPosition())
            if s.GetEnd()==before:s.SetEnd(t.GetPosition())
k.SaveBoard(str(BOARD),b)
