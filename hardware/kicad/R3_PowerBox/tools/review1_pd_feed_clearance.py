import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,pad,line
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
f=b.FindFootprintByReference('C106');old={p.GetNumber():k.VECTOR2I(p.GetPosition()) for p in f.Pads()};f.SetPosition(vec(40,31))
for p in f.Pads():
    for t in ts:
        if isinstance(t,k.PCB_VIA):continue
        if t.GetStart()==old[p.GetNumber()]:t.SetStart(p.GetPosition())
        if t.GetEnd()==old[p.GetNumber()]:t.SetEnd(p.GetPosition())
for t in list(ts):
    if isinstance(t,k.PCB_VIA):continue
    if t.GetNetname()=='PD_VDD' and t.GetLayer()==k.B_Cu and t.GetStart() in [vec(39.6,28.425),vec(39.6,30.125)]:b.Remove(t)
    if t.GetNetname()=='PD_ALERT_N' and t.GetLayer()==k.B_Cu:
        if t.GetStart()==vec(38,29.95):t.SetStart(vec(37.8,29.95))
        if t.GetEnd()==vec(38,29.95):t.SetEnd(vec(37.8,29.95))
line(b,'PD_VDD',[(39.6,28.425),(40.1,28.8),(40.1,30.55),point(pad(b,'C106',1)),(38.5,29.9)],.2,k.B_Cu)
k.SaveBoard(str(BOARD),b)
