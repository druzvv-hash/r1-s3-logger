"""ST DS12499: power VSYS on battery so common I2C is not held low."""
from pathlib import Path
import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,pad,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
assert not b.FindFootprintByReference('C109')
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
p=pad(b,'U10',22)
for t in list(ts):
    if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='DGND' and (t.GetStart()==p.GetPosition() or t.GetEnd()==p.GetPosition()):b.Remove(t)
p.SetNet(b.FindNet('+3V3_D'))
for t in ts:
    if not isinstance(t,k.PCB_VIA):continue
    xy=point(t);changes={(31.25,29.95):(30.8,29.95),(32.25,29.95):(31.8,29.95),(33.25,29.95):(33.7,29.95)}
    if xy not in changes:continue
    new=changes[xy];t.SetPosition(vec(*new))
    for s in ts:
        if isinstance(s,k.PCB_VIA):continue
        if s.GetStart()==vec(*xy):s.SetStart(vec(*new))
        if s.GetEnd()==vec(*xy):s.SetEnd(vec(*new))
lib=Path.home()/'AppData/Local/Programs/KiCad/10.0/share/kicad/footprints/Capacitor_SMD.pretty'
f=k.FootprintLoad(str(lib),'C_0603_1608Metric');b.Add(f);f.SetReference('C109');f.SetValue('1uF/10V PD VSYS');f.SetPosition(vec(33,31));f.Flip(f.GetPosition(),True);f.SetOrientationDegrees(0);f.Reference().SetLayer(k.B_Fab);f.Value().SetVisible(False)
for p in f.Pads():p.SetNet(b.FindNet('+3V3_D' if p.GetNumber()=='1' else 'DGND'))
via(b,'+3V3_D',32.75,30);line(b,'+3V3_D',[point(pad(b,'U10',22)),(32.75,30)],.2)
line(b,'+3V3_D',[point(pad(b,'C109',1)),(32.75,30)],.35,k.B_Cu)
line(b,'+3V3_D',[(32.75,30),(32.75,30.8),(39.6,30.8),(39.6,37.4)],.2,k.In1_Cu)
via(b,'DGND',34,32.5);line(b,'DGND',[point(pad(b,'C109',2)),(34,32.5)],.35,k.B_Cu)
for ref,val in [('R76','28.7k 0.1% ILIM TOP / SAFE START'),('R77','10k 0.1% ILIM BOT')]:b.FindFootprintByReference(ref).SetValue(val)
k.SaveBoard(str(BOARD),b)
