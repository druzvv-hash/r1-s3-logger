"""Address the independent copper-graph findings, not sense-branch widths."""
import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,pad,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
for t in ts:
    if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='CHARGER_IN' and t.GetStart()==vec(48.1,50):t.SetWidth(k.FromMM(.8))
for xy,anchor,layers in [((46.65,31.15),(46.65,32),[k.F_Cu,k.In1_Cu]),((41.675,38.9),(42.525,38.9),[k.B_Cu,k.In1_Cu]),((35.9,51.725),(35.9,50.875),[k.F_Cu,k.B_Cu])]:
    via(b,'CHARGER_IN',*xy)
    for l in layers:line(b,'CHARGER_IN',[xy,anchor],.8,l)
for t in ts:
    if isinstance(t,k.PCB_VIA) and t.GetNetname()=='N$9' and point(t)==(54.5,49):
        before=k.VECTOR2I(t.GetPosition());t.SetPosition(vec(54.9,48.7))
        for s in ts:
            if isinstance(s,k.PCB_VIA):continue
            if s.GetStart()==before:s.SetStart(t.GetPosition())
            if s.GetEnd()==before:s.SetEnd(t.GetPosition())
for t in list(ts):
    if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='N$9' and t.GetLayer()==k.F_Cu:b.Remove(t)
line(b,'N$9',[point(pad(b,'U8',24)),(52.8625,48.5),(54.9,48.5),(54.9,48.7)],.2)
via(b,'PACK_POS',53.95,49.15)
for l in [k.F_Cu,k.In1_Cu]:line(b,'PACK_POS',[(53.95,49.15),(54,50)],.7,l)
k.SaveBoard(str(BOARD),b)
