"""One-shot cleanup after first ECO; current PCB only."""
import pcbnew as k
from route_reva import ROOT,BOARD,vec,pad,point,line,via
b=k.LoadBoard(str(BOARD))
f=b.FindFootprintByReference('F2'); f.SetPosition(vec(43.8,24)); f.Reference().SetLayer(k.F_Fab)
f=b.FindFootprintByReference('R106');f.SetPosition(vec(36.7,31.75));f.SetOrientationDegrees(180)
f.Reference().SetVisible(False)
ts=b.GetTracks()
for t in list(ts):
    net=str(t.GetNetname())
    a=(round(k.ToMM(t.GetStart().x),4),round(k.ToMM(t.GetStart().y),4))
    z=(round(k.ToMM(t.GetEnd().x),4),round(k.ToMM(t.GetEnd().y),4))
    if net=='PD_VBUS_SENSE_DISCH': b.Remove(t);continue
    if net=='USB_VBUS_PROT' and ((t.GetLayer()==k.F_Cu and (a in [(36.675,29.5),(36.725,27),(45.225,27),(47.8875,24),(36.45,31.75)])) or a==(36.7,31.5) or z==(36.7,31.5)):
        b.Remove(t);continue
    if net=='VSYS_MAIN' and (a==(93.7,52) or z==(93.7,52)):
        b.Remove(t);continue
    if isinstance(t,k.PCB_VIA):continue
    if net=='PD_ALERT_N' and t.GetLayer()==k.F_Cu and (a==(42,31.85) or a==(42,22)):
        t.SetLayer(k.In1_Cu)
    if net=='BQ_STAT_RAW' and t.GetLayer()==k.F_Cu and (a==(40.7,40.2) or a==(43.5,27)):
        t.SetLayer(k.In1_Cu)
line(b,'USB_VBUS_RAW',[point(pad(b,'F2',1)),(40.775,24)],1)
line(b,'USB_VBUS_PROT',[point(pad(b,'F2',2)),(47.525,24)],1)
line(b,'PD_VBUS_SENSE_DISCH',[point(pad(b,'U10',18)),point(pad(b,'R106',2))],.2)
line(b,'USB_VBUS_PROT',[point(pad(b,'R106',1)),(38.2,31.75)],.25)
via(b,'USB_VBUS_PROT',38.2,31.75)
line(b,'USB_VBUS_PROT',[(38.2,31.75),(38,32.35)],.25,k.B_Cu)
for net,xy in [('PD_ALERT_N',(42,31.85)),('PD_ALERT_N',(63,22)),('BQ_STAT_RAW',(40.7,40.2))]:via(b,net,*xy)
for d in b.GetDrawings():
    if isinstance(d,k.PCB_TEXT) and d.GetText().startswith('FIRST POWER:'):
        d.SetPosition(vec(61,97.5));d.SetTextSize(vec(.65,.65))
b.FindFootprintByReference('FB1').Reference().SetLayer(k.F_Fab)
k.SaveBoard(str(BOARD),b)
