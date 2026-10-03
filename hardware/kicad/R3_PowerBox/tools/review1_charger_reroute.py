"""Explicit local charger ECO, following TI Rev.C Figure8-21 inner-SW fanout.

This is NOT a generic router and never loads an old PCB. The changed hot-loop
region is checked by DRC after applying these named pads/waypoints.
"""
import pcbnew as k
from route_reva import BOARD,vec,pad,point,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
assert point(b.FindFootprintByReference('L3'))==(51.0,41.0),'Do not replay'
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
def move(ref,x,y,angle=None):
    f=b.FindFootprintByReference(ref);old={p.GetNumber():k.VECTOR2I(p.GetPosition()) for p in f.Pads()}
    f.SetPosition(vec(x,y))
    if angle is not None:f.SetOrientationDegrees(angle)
    for p in f.Pads():
        for t in ts:
            if isinstance(t,k.PCB_VIA):continue
            if t.GetStart()==old[p.GetNumber()]:t.SetStart(p.GetPosition())
            if t.GetEnd()==old[p.GetNumber()]:t.SetEnd(p.GetPosition())
move('L3',51,43.2)
move('C77',45.5,45.5);move('C81',56.5,45.5)
move('C100',47.8,49.34);move('C101',45.2,50,180)
move('C87',56.5,50,0)
for t in list(ts):
    net=str(t.GetNetname())
    if net in ['CHG_SW1','CHG_SW2','N$7','N$8']:b.Remove(t);continue
    if isinstance(t,k.PCB_VIA):continue
    a=point(pad(b,'U8',2));x=k.ToMM(t.GetStart().x);y=k.ToMM(t.GetStart().y)
    if net=='CHARGER_IN' and t.GetLayer()==k.F_Cu and 46<=x<=49.1 and 49.7<=y<=50.3:
        b.Remove(t);continue
    if net=='PACK_POS' and t.GetLayer()==k.F_Cu and 52.8<=x<=54 and 49.7<=y<=50.3:
        b.Remove(t);continue
    if net in ['CHG_PMID','VSYS_RAW'] and t.GetLayer()==k.F_Cu and x in [50.1,51.9] and 49<=y<=49.4:
        b.Remove(t)

# Keep short package-width escapes only; widen as soon as adjacent pads clear.
for pin,net,x in [(28,'CHG_SW1',50.55),(26,'CHG_SW2',51.45)]:
    line(b,net,[point(pad(b,'U8',pin)),(x,49.85)],.2)
    line(b,net,[(x,49.85),(x,50.3),(x,51.1),(x,51.9)],.7)
    for y in [50.3,51.1,51.9]:via(b,net,x,y)
    line(b,net,[(x,50.3),(x,51.1),(x,51.9)],.7,k.In2_Cu)
for net,x,outer,pin in [('CHG_SW1',50.55,48.05,1),('CHG_SW2',51.45,53.95,2)]:
    line(b,net,[(x,50.3),(outer,47.8),(outer,46.0)],1.0,k.In2_Cu)
    for vx in [outer-.8,outer,outer+.8]:
        via(b,net,vx,46.0)
        line(b,net,[(outer,46),(vx,46)],1.0,k.In2_Cu)
        line(b,net,[point(pad(b,'L3',pin)),(vx,46)],1.0)

# Bootstrap side paths are low-current; they do not carry inductor power.
# 0.30/0.70 via geometry retained everywhere, including bootstrap.
line(b,'N$7',[point(pad(b,'U8',4)),(49.9,50.6),(49.9,51)],.2)
via(b,'N$7',49.9,51)
line(b,'N$7',[(49.9,51),point(pad(b,'C74',1))],.2,k.B_Cu)
line(b,'CHG_SW1',[(50.55,51.9),(50.55,53.8),point(pad(b,'C74',2))],.2,k.B_Cu)
line(b,'N$8',[point(pad(b,'U8',19)),(54,51.4)],.2)
via(b,'N$8',54,51.4)
line(b,'N$8',[(54,51.4),point(pad(b,'C75',1))],.2,k.B_Cu)
line(b,'CHG_SW2',[(51.45,51.1),(53.2,51.1),(53.2,51.8),point(pad(b,'C75',2))],.2,k.B_Cu)

for pin,net,x in [(29,'CHG_PMID',50.1),(25,'VSYS_RAW',51.9)]:
    line(b,net,[point(pad(b,'U8',pin)),(x,48.6)],.2)
    line(b,net,[(x,48.6),(x,47.825)],.6)
for pin in [2,3]:line(b,'CHARGER_IN',[point(pad(b,'U8',pin)),(48.65,49.8 if pin==2 else 50.2),(48.35,50)],.2)
line(b,'CHARGER_IN',[(48.35,50),point(pad(b,'C100',1)),point(pad(b,'C101',1))],.6)
for pin in [22,23]:line(b,'PACK_POS',[point(pad(b,'U8',pin)),(53.35,50.2 if pin==22 else 49.8),(53.65,50)],.2)
line(b,'PACK_POS',[(53.65,50),point(pad(b,'C87',1))],1.0)
line(b,'PACK_POS',[(53.65,50),(54,50)],1.0)
for x,y in [(47.1,48.0),(47.1,48.8),(44.0,49.3),(44.0,50.1),(55.5,48.3),(56.3,48.3)]:via(b,'DGND',x,y)
k.SaveBoard(str(BOARD),b)
