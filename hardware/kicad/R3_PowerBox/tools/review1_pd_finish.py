import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,pad,line
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
changes={(39.4,29.8):(38.5,29.9),(40.5,30):(39.35,29.9)}
for t in list(ts):
    if isinstance(t,k.PCB_VIA):
        if point(t)==(32.75,33):b.Remove(t);continue
        old=point(t)
        if old in changes:
            new=changes[old];t.SetPosition(vec(*new))
            for s in ts:
                if isinstance(s,k.PCB_VIA):continue
                if s.GetStart()==vec(*old):s.SetStart(vec(*new))
                if s.GetEnd()==vec(*old):s.SetEnd(vec(*new))
        continue
    if t.GetNetname()=='DGND' and t.GetEnd()==vec(32.75,33):t.SetEnd(vec(33,33))
    if t.GetNetname()=='+3V3_D' and t.GetLayer()==k.In1_Cu:
        if t.GetStart()==vec(39.5,30.5):t.SetStart(vec(39.35,30.5))
        if t.GetEnd()==vec(39.5,30.5):t.SetEnd(vec(39.35,30.5))
line(b,'PD_VREG_2V7',[point(pad(b,'C105',1)),(36.2,37.4)],.2,k.B_Cu)
k.SaveBoard(str(BOARD),b)
