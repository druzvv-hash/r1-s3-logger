import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from pathlib import Path
from route_reva import BOARD,vec,point,pad,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
oldf=b.FindFootprintByReference('C109');oldpads=[p.GetPosition() for p in oldf.Pads()]
for t in list(ts):
    if isinstance(t,k.PCB_VIA):
        if point(t)==(34,32.5):b.Remove(t)
        continue
    n=t.GetNetname();a=point(t) if False else (k.ToMM(t.GetStart().x),k.ToMM(t.GetStart().y))
    if n in ['DGND','+3V3_D'] and (t.GetStart() in oldpads or t.GetEnd() in oldpads):b.Remove(t);continue
    if n=='+3V3_D' and t.GetLayer()==k.In1_Cu and a in [(32.75,30),(32.75,30.8),(39.6,30.8)]:b.Remove(t)
    if n=='PD_VREG_2V7' and t.GetLayer()==k.B_Cu:b.Remove(t)
b.Remove(oldf)
lib=Path.home()/'AppData/Local/Programs/KiCad/10.0/share/kicad/footprints/Capacitor_SMD.pretty'
f=k.FootprintLoad(str(lib),'C_0402_1005Metric');b.Add(f);f.SetReference('C109');f.SetValue('1uF/10V PD VSYS');f.SetPosition(vec(32.75,31.2));f.Flip(f.GetPosition(),True);f.SetOrientationDegrees(270);f.Reference().SetLayer(k.B_Fab);f.Value().SetVisible(False)
for p in f.Pads():p.SetNet(b.FindNet('+3V3_D' if p.GetNumber()=='1' else 'DGND'))
def endpoint(a,c):
    for t in ts:
        if isinstance(t,k.PCB_VIA):continue
        if t.GetStart()==vec(*a):t.SetStart(vec(*c))
        if t.GetEnd()==vec(*a):t.SetEnd(vec(*c))
c=b.FindFootprintByReference('C104');old={p.GetNumber():point(p) for p in c.Pads()};c.SetPosition(vec(34.9,32))
for p in c.Pads():endpoint(old[p.GetNumber()],point(p))
for t in ts:
    if isinstance(t,k.PCB_VIA) and point(t)==(38.725,30):t.SetPosition(vec(39.4,29.8));endpoint((38.725,30),(39.4,29.8))
line(b,'PD_VREG_2V7',[(31.8,29.95),(31.6,31.5),(31.6,33.7),(35.05,34),point(pad(b,'C105',1))],.2,k.B_Cu)
line(b,'+3V3_D',[(32.75,30),point(pad(b,'C109',1))],.2,k.B_Cu)
via(b,'DGND',32.75,33);line(b,'DGND',[point(pad(b,'C109',2)),(32.75,33)],.2,k.B_Cu)
via(b,'+3V3_D',40.5,30)
line(b,'+3V3_D',[(32.75,30),(32.75,30.5),(39.5,30.5),(40.5,30)],.13,k.In1_Cu)
line(b,'+3V3_D',[(40.5,30),(40.5,29.3)],.2,k.In2_Cu)
k.SaveBoard(str(BOARD),b)
