"""Explicit current-state repair; invalidate old zone fills before new vias."""
import pcbnew as k
from route_reva import BOARD,vec,pad,point,line,via
b=k.LoadBoard(str(BOARD))
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
f=b.FindFootprintByReference('R106');f.SetPosition(vec(37.4,31.75));f.SetOrientationDegrees(180)
f=b.FindFootprintByReference('TP38');old=point(pad(b,'TP38',1));f.SetPosition(vec(62,35.5))
for t in b.GetTracks():
    if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='PM_I2C_SDA':
        if t.GetStart()==vec(*old):t.SetStart(vec(62,35.5))
        if t.GetEnd()==vec(*old):t.SetEnd(vec(62,35.5))
ts=b.GetTracks()
for t in list(ts):
    net=str(t.GetNetname());a=tuple(round(k.ToMM(v),4) for v in [t.GetStart().x,t.GetStart().y]);z=tuple(round(k.ToMM(v),4) for v in [t.GetEnd().x,t.GetEnd().y])
    if isinstance(t,k.PCB_VIA):
        if a in [(37.4,29),(60.1125,29.1),(66.8875,28.3)]:b.Remove(t)
        continue
    if net=='PD_VBUS_SENSE_DISCH':b.Remove(t);continue
    if net=='USB_VBUS_PROT' and (a in [(37.4,31.825),(37.4,29),(37.4,27.5),(40,27.5),(66.8875,30.5),(66.8875,28.3),(66.8875,26),(47.525,24)]):b.Remove(t);continue
    if net=='USB_VBUS_RAW' and a in [(60.1125,30.5),(60.1125,21),(40.775,21),(40.775,25.175)] and (t.GetLayer()==k.F_Cu or t.GetLayer()==k.In2_Cu and z[0]==60.1125):b.Remove(t);continue
    if net=='NTC_CHG' and t.GetLayer()==k.F_Cu and a in [(59,27),(60,29),(60,30.5)]:t.SetLayer(k.B_Cu)
line(b,'PD_VBUS_SENSE_DISCH',[point(pad(b,'U10',18)),point(pad(b,'R106',2))],.2)
line(b,'USB_VBUS_PROT',[point(pad(b,'R106',1)),(39.4,31.75),(39.4,34.5)],.25)
via(b,'USB_VBUS_PROT',39.4,34.5)
line(b,'USB_VBUS_PROT',[(39.4,34.5),(39.4,36.8),(43.4,36.8)],.25,k.B_Cu)
via(b,'USB_VBUS_RAW',60.1125,21.1)
via(b,'USB_VBUS_RAW',60.1125,27.8)
line(b,'USB_VBUS_RAW',[(40.775,25.175),(40.775,21.1),(60.1125,21.1)],1,k.In2_Cu)
line(b,'USB_VBUS_RAW',[(60.1125,21.1),(60.1125,27.8)],1,k.B_Cu)
line(b,'USB_VBUS_RAW',[(60.1125,27.8),point(pad(b,'F2',1))],1)
line(b,'USB_VBUS_PROT',[point(pad(b,'F2',2)),(65.5,30.5)],1)
via(b,'USB_VBUS_PROT',65.5,30.5);via(b,'USB_VBUS_PROT',47.525,30.5)
line(b,'USB_VBUS_PROT',[(65.5,30.5),(47.525,30.5)],1,k.In2_Cu)
line(b,'USB_VBUS_PROT',[(47.525,30.5),(47.525,29)],1,k.B_Cu)
for xy in [(59,27),(60,34.5)]:via(b,'NTC_CHG',*xy)
b.FindFootprintByReference('F2').GetField('Datasheet').SetText('https://www.littelfuse.com/~/media/electronics/datasheets/resettable_ptcs/littelfuse_ptc_2920l_datasheet.pdf.pdf')
k.SaveBoard(str(BOARD),b)
