import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,pad,point,line
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
f=b.FindFootprintByReference('C100');old={p.GetNumber():k.VECTOR2I(p.GetPosition()) for p in f.Pads()};f.SetPosition(vec(47.5,49.4))
for p in f.Pads():
    for t in ts:
        if isinstance(t,k.PCB_VIA):continue
        if t.GetStart()==old[p.GetNumber()]:t.SetStart(p.GetPosition())
        if t.GetEnd()==old[p.GetNumber()]:t.SetEnd(p.GetPosition())
for t in ts:
    if not isinstance(t,k.PCB_VIA):continue
    xy=point(t);new=None
    if xy==(55.65,49.2):new=(55.65,49.1)
    if xy==(47.6,49) and t.GetNetname()=='BQ_STAT_RAW':new=(48.3,48.75)
    if new:
        before=k.VECTOR2I(t.GetPosition());t.SetPosition(vec(*new))
        for s in ts:
            if isinstance(s,k.PCB_VIA):continue
            if s.GetStart()==before:s.SetStart(t.GetPosition())
            if s.GetEnd()==before:s.SetEnd(t.GetPosition())
# Replace stretched VBUS small-cap link, keeping VAC1/2 sensing independent.
for t in list(ts):
    if isinstance(t,k.PCB_VIA) or t.GetLayer()!=k.F_Cu or t.GetNetname()!='CHARGER_IN':continue
    a=(k.ToMM(t.GetStart().x),k.ToMM(t.GetStart().y));c=(k.ToMM(t.GetEnd().x),k.ToMM(t.GetEnd().y))
    if 45<=min(a[0],c[0]) and max(a[1],c[1])<=51.7 and min(a[1],c[1])>=49.7:b.Remove(t)
line(b,'CHARGER_IN',[(49.1,49.8),(49.1,50.2)],.2)
line(b,'CHARGER_IN',[(49.1,49.8),(48.5,49.8),(48.1,50)],.2)
line(b,'CHARGER_IN',[(48.1,50),point(pad(b,'C100',1))],.5)
line(b,'CHARGER_IN',[(45,51.7),(46.3,50.5),point(pad(b,'C100',1))],.8)
k.SaveBoard(str(BOARD),b)
