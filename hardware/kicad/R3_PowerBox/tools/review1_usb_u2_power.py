"""USB trunk copper and local U2 bypass ECO; no other converter changes."""
import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,pad,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
for t in ts:
    if isinstance(t,k.PCB_VIA):continue
    if t.GetNetname() in ['USB_VBUS_RAW','USB_VBUS_PROT'] and k.ToMM(t.GetWidth())>=.5:
        # Short USB connector pin escapes remain 0.5mm, two parallel feeds.
        if t.GetNetname()=='USB_VBUS_RAW' and t.GetLayer()==k.F_Cu:continue
        t.SetWidth(k.FromMM(1))
for net,xy,anchor,layer in [
    ('USB_VBUS_RAW',(40.775,24.275),(40.775,25.175),k.In2_Cu),
    ('USB_VBUS_RAW',(28.9,30.6),(28.2,30.6),k.In2_Cu),
    ('USB_VBUS_RAW',(28.9,35.4),(28.2,35.4),k.In2_Cu),
    ('USB_VBUS_PROT',(47.2,32.5),(47.2,33.35),k.B_Cu),
    ('USB_VBUS_PROT',(47.525,27.85),(47.525,27),k.B_Cu)]:
    via(b,net,*xy);line(b,net,[xy,anchor],1,layer)
    line(b,net,[xy,anchor],1,k.B_Cu if net=='USB_VBUS_RAW' and xy[0]>40 else k.F_Cu)
# C20 on reverse directly below the local VIN/return, C21 remains top-side.
f=b.FindFootprintByReference('C20');f.SetPosition(vec(100,49.2));f.Flip(f.GetPosition(),True);f.SetOrientationDegrees(0);f.Reference().SetLayer(k.B_Fab)
f=b.FindFootprintByReference('C21');f.SetPosition(vec(97.5,49.3));f.SetOrientationDegrees(180);f.Reference().SetLayer(k.F_Fab)
for t in list(ts):
    if isinstance(t,k.PCB_VIA):continue
    x,y=k.ToMM(t.GetStart().x),k.ToMM(t.GetStart().y)
    if t.GetNetname()=='VSYS_MAIN' and t.GetLayer()==k.F_Cu and 95<x<100 and 44<y<52:b.Remove(t)
    if t.GetNetname()=='DGND' and t.GetLayer()==k.F_Cu and (t.GetStart()==vec(97.775,48.6) or t.GetStart()==vec(101.475,45.4)):b.Remove(t)
for t in ts:
    if isinstance(t,k.PCB_VIA) and point(t)==(96.225,49.5):
        old=k.VECTOR2I(t.GetPosition());t.SetPosition(vec(98.2,50.15))
        for s in ts:
            if isinstance(s,k.PCB_VIA):continue
            if s.GetStart()==old:s.SetStart(t.GetPosition())
            if s.GetEnd()==old:s.SetEnd(t.GetPosition())
line(b,'VSYS_MAIN',[point(pad(b,'U2',3)),(98.2,50.15),point(pad(b,'C21',1))],.5)
line(b,'VSYS_MAIN',[(98.2,50.15),point(pad(b,'C20',1))],1,k.B_Cu)
for ref,xy,layer in [('C20',(101.5,48.5),k.B_Cu),('C21',(96.5,48.5),k.F_Cu)]:
    via(b,'DGND',*xy);line(b,'DGND',[point(pad(b,ref,2)),xy],.5,layer)
k.SaveBoard(str(BOARD),b)
