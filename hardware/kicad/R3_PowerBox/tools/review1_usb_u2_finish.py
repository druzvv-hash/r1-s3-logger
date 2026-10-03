import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,line
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
def endpoint(a,c):
    for t in ts:
        if isinstance(t,k.PCB_VIA):continue
        if t.GetStart()==vec(*a):t.SetStart(vec(*c))
        if t.GetEnd()==vec(*a):t.SetEnd(vec(*c))
for t in list(ts):
    if isinstance(t,k.PCB_VIA):
        if point(t)==(98.6,48.6):b.Remove(t);continue
        changes={(46.9,34.5):(45.8,35.3),(101.5,48.3):(102.8,49.7)}
        if point(t) in changes:
            old=point(t);t.SetPosition(vec(*changes[old]));endpoint(old,changes[old])
        continue
    n=t.GetNetname();a=(k.ToMM(t.GetStart().x),k.ToMM(t.GetStart().y));c=(k.ToMM(t.GetEnd().x),k.ToMM(t.GetEnd().y))
    if n=='USB_VBUS_RAW' and t.GetLayer()==k.In2_Cu and min(a[1],c[1])<21.2:b.Remove(t)
    if n=='USB_VBUS_PROT' and t.GetLayer()==k.F_Cu and (a==(45.675,33.35) or a==(46.25,33.65)):b.Remove(t)
    if n=='USB_VBUS_PROT' and t.GetLayer()==k.B_Cu:
        for meth,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
            p=meth()
            if abs(k.ToMM(p.x)-47.525)<.001 and abs(k.ToMM(p.y)-32.8)<.001:setter(vec(47.8,32.8))
line(b,'USB_VBUS_RAW',[(29.2,22.5),(29.2,29.6)],1,k.In2_Cu)
line(b,'USB_VBUS_RAW',[(28.9,30.6),(30.5,31),(36,31),(36.7,30.6),(37.5,31),(40.775,31),(40.775,25.175)],1,k.In2_Cu)
line(b,'USB_VBUS_PROT',[(45.675,33.35),(46.7,33.35)],.5)
line(b,'USB_VBUS_PROT',[(46.7,33.35),(47.2,33.35)],1)
f=b.FindFootprintByReference('R22');old={p.GetNumber():point(p) for p in f.Pads()};f.SetPosition(vec(91.1,49.2))
for p in f.Pads():endpoint(old[p.GetNumber()],point(p))
k.SaveBoard(str(BOARD),b)
