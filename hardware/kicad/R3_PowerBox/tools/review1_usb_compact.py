"""Use the free underside for the enlarged fuse; preserve signal placement."""
import pcbnew as k
from route_reva import BOARD,vec,pad,point,line,via
b=k.LoadBoard(str(BOARD))
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
f=b.FindFootprintByReference('F2');f.SetPosition(vec(43.8,23.5))
if f.GetLayer()!=k.B_Cu:f.Flip(f.GetPosition(),True)
f.SetOrientationDegrees(0)
f=b.FindFootprintByReference('R106');f.SetPosition(vec(38,34.5))
if f.GetLayer()!=k.B_Cu:f.Flip(f.GetPosition(),True)
f.SetOrientationDegrees(90)
if point(pad(b,'R106',1))[1]<point(pad(b,'R106',2))[1]:f.SetOrientationDegrees(270)
f=b.FindFootprintByReference('TP38');old=point(pad(b,'TP38',1));f.SetPosition(vec(62,33))
ts=b.GetTracks()
for t in list(ts):
    net=str(t.GetNetname());a=tuple(round(k.ToMM(v),4) for v in [t.GetStart().x,t.GetStart().y]);z=tuple(round(k.ToMM(v),4) for v in [t.GetEnd().x,t.GetEnd().y])
    if net=='PM_I2C_SDA' and not isinstance(t,k.PCB_VIA):
        if t.GetStart()==vec(*old):t.SetStart(vec(62,33))
        if t.GetEnd()==vec(*old):t.SetEnd(vec(62,33))
    if net=='PD_VBUS_SENSE_DISCH':b.Remove(t);continue
    if net=='USB_VBUS_RAW' and (a[0]>41 or z[0]>41):b.Remove(t);continue
    if net=='USB_VBUS_PROT' and (a[0]>58 or z[0]>58 or a in [(39.4,31.75),(39.4,34.5),(39.4,36.8),(38.225,31.75),(47.525,30.5)]):b.Remove(t);continue
    if isinstance(t,k.PCB_VIA):
        if net=='NTC_CHG' and a in [(59,27),(60,34.5)]:b.Remove(t)
        continue
    if net=='USB_VBUS_PROT' and a==(38,32.35):b.Remove(t);continue
    if net=='NTC_CHG' and t.GetLayer()==k.B_Cu and a in [(59,27),(60,29),(60,30.5)]:t.SetLayer(k.F_Cu)
line(b,'USB_VBUS_RAW',[(40.775,25.175),point(pad(b,'F2',1))],1,k.B_Cu)
line(b,'USB_VBUS_PROT',[point(pad(b,'F2',2)),(47.525,26)],1,k.B_Cu)
line(b,'PD_VBUS_SENSE_DISCH',[point(pad(b,'U10',18)),(36.45,31.75),(36.7,31.5)],.2)
via(b,'PD_VBUS_SENSE_DISCH',36.7,31.5)
line(b,'PD_VBUS_SENSE_DISCH',[(36.7,31.5),(37.4,31.75),(38,32.35),point(pad(b,'R106',2))],.2,k.B_Cu)
line(b,'USB_VBUS_PROT',[point(pad(b,'R106',1)),(38,36.8),(43.4,36.8)],.2,k.B_Cu)
k.SaveBoard(str(BOARD),b)
