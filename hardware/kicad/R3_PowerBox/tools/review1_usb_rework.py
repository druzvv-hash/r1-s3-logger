"""Correct DRC-proven conflicts from the larger F2 and R106 local ECO."""
import pcbnew as k
from route_reva import BOARD,vec,pad,point,line,via
b=k.LoadBoard(str(BOARD))
b.FindFootprintByReference('F2').SetPosition(vec(63.5,30.5))
f=b.FindFootprintByReference('R106');f.SetPosition(vec(37.4,31.0));f.SetOrientationDegrees(90)
ts=b.GetTracks();seen=set()
for t in list(ts):
    net=str(t.GetNetname());a=tuple(round(k.ToMM(v),4) for v in [t.GetStart().x,t.GetStart().y]);z=tuple(round(k.ToMM(v),4) for v in [t.GetEnd().x,t.GetEnd().y])
    if isinstance(t,k.PCB_VIA):
        if a in [(38.2,31.75),(63,22)]:b.Remove(t);continue
        if (net,a) in seen:b.Remove(t);continue
        seen.add((net,a));continue
    if net=='PD_ALERT_N' and t.GetLayer()==k.In1_Cu and (a==(42,31.85) or a==(42,22)):t.SetLayer(k.F_Cu)
    if net=='BQ_STAT_RAW' and t.GetLayer()==k.In1_Cu and (a==(40.7,40.2) or a==(43.5,27)):t.SetLayer(k.F_Cu)
    if net=='PD_VBUS_SENSE_DISCH':b.Remove(t);continue
    if net=='USB_VBUS_PROT' and (t.GetLayer()==k.F_Cu and a in [(37.525,31.75),(45.225,24),(47.1875,24)] or a in [(38.2,31.75),(37.4,31.75)]):b.Remove(t);continue
    if net=='USB_VBUS_RAW' and t.GetLayer()==k.F_Cu and a in [(40.4125,24),(41.1125,24)]:b.Remove(t);continue
    if net=='VSYS_MAIN' and a==(94.5,51.2) and t.GetLayer()==k.In2_Cu:b.Remove(t);continue

line(b,'PD_VBUS_SENSE_DISCH',[point(pad(b,'U10',18)),(36.45,31.75),point(pad(b,'R106',2))],.2)
line(b,'USB_VBUS_PROT',[point(pad(b,'R106',1)),(37.4,29.0)],.25)
via(b,'USB_VBUS_PROT',37.4,29.0)
line(b,'USB_VBUS_PROT',[(37.4,29),(37.4,27.5),(40,27.5),(40.825,28)],.25,k.B_Cu)
line(b,'USB_VBUS_RAW',[point(pad(b,'F2',1)),(60.1125,29.1)],1)
via(b,'USB_VBUS_RAW',60.1125,29.1)
line(b,'USB_VBUS_RAW',[(40.775,25.175),(40.775,21),(60.1125,21),(60.1125,29.1)],1,k.In2_Cu)
line(b,'USB_VBUS_PROT',[point(pad(b,'F2',2)),(66.8875,28.3)],1)
via(b,'USB_VBUS_PROT',66.8875,28.3)
line(b,'USB_VBUS_PROT',[(66.8875,28.3),(66.8875,26),(47.525,26),(47.525,27)],1,k.B_Cu)
for d in b.GetDrawings():
    if isinstance(d,k.PCB_TEXT) and d.GetText().startswith('FIRST POWER:'):
        d.SetTextSize(vec(.8,.8));d.SetPosition(vec(61,98.5))
k.SaveBoard(str(BOARD),b)
