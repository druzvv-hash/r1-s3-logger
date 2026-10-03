"""Fit enlarged passive parts without moving functional block anchors."""
import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,pad,point,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
def move(ref,x,y):
    f=b.FindFootprintByReference(ref); old={p.GetNumber():k.VECTOR2I(p.GetPosition()) for p in f.Pads()}
    f.SetPosition(vec(x,y))
    for p in f.Pads():
        for t in ts:
            if isinstance(t,k.PCB_VIA):continue
            if t.GetStart()==old[p.GetNumber()]:t.SetStart(p.GetPosition())
            if t.GetEnd()==old[p.GetNumber()]:t.SetEnd(p.GetPosition())
move('C40',149.5,45.2);move('C41',140.5,45.2);move('C42',140,41)
move('C44',142,37);move('C24',108.8,55);move('FB4',128,80)
for t in ts:
    if t.GetNetname()=='+5V_PREISO':
        if isinstance(t,k.PCB_VIA) and t.GetPosition()==vec(110,49.3):t.SetPosition(vec(109,48.7))
        elif not isinstance(t,k.PCB_VIA):
            if t.GetStart()==vec(110,49.3):t.SetStart(vec(109,48.7))
            if t.GetEnd()==vec(110,49.3):t.SetEnd(vec(109,48.7))
for t in list(ts):
    if t.GetNetname()=='N$14':b.Remove(t)
line(b,'N$14',[point(pad(b,'U4',3)),(142.8,41.75)],.2)
for xy in [(142.8,41.75),(142.8,37.775)]:
    v=k.PCB_VIA(b);v.SetPosition(vec(*xy));v.SetWidth(k.FromMM(.5));v.SetDrill(k.FromMM(.2));v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet('N$14'));b.Add(v)
line(b,'N$14',[(142.8,41.75),(142.8,37.775)],.2,k.B_Cu)
line(b,'N$14',[(142.8,37.775),point(pad(b,'C44',1))],.2)
for ref,xy,net in [('R107',(139,80),'+5V_INA'),('R108',(139,84),'-5V_INA')]:
    f=b.FindFootprintByReference(ref);old=point(pad(b,ref,1))
    for t in list(ts):
        if not isinstance(t,k.PCB_VIA) and t.GetNetname()==net and (t.GetStart()==vec(*old) or t.GetEnd()==vec(*old)):b.Remove(t)
    f.SetPosition(vec(*xy));f.Flip(f.GetPosition(),True);f.SetOrientationDegrees(0)
    f.Reference().SetLayer(k.B_Fab);f.Value().SetVisible(False)
    p=point(pad(b,ref,1));via(b,net,*p)
    if ref=='R107':line(b,net,[(132.05,77),(p[0],77),p],.35)
    else:line(b,net,[point(pad(b,'C62',2)),(p[0],86),p],.35)
b.FindFootprintByReference('C63').Reference().SetLayer(k.F_Fab)
b.FindFootprintByReference('R40').Reference().SetLayer(k.B_Fab)
k.SaveBoard(str(BOARD),b)
