import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,line,pad
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
def endpoint(before,after):
    for s in ts:
        if isinstance(s,k.PCB_VIA):continue
        if s.GetStart()==vec(*before):s.SetStart(vec(*after))
        if s.GetEnd()==vec(*before):s.SetEnd(vec(*after))
for t in ts:
    if not isinstance(t,k.PCB_VIA):continue
    xy=point(t);changes={(28.9,35.4):(28.8,35.6),(47.525,27.85):(47.525,26.15),(47.2,32.5):(47.2,34.2),(98.2,50.15):(98.2,50.35),(101.5,48.5):(101.5,48.3)}
    if xy in changes:t.SetPosition(vec(*changes[xy]));endpoint(xy,changes[xy])
for t in ts:
    if isinstance(t,k.PCB_VIA):continue
    n=t.GetNetname()
    if n=='USB_VBUS_RAW':
        for meth,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
            p=meth()
            if abs(k.ToMM(p.y)-20.95)<.001:setter(vec(k.ToMM(p.x),21.1))
        if t.GetLayer()==k.F_Cu and k.ToMM(t.GetWidth())==1:t.SetWidth(k.FromMM(.7))
    if n=='USB_VBUS_PROT' and t.GetLayer()==k.B_Cu:
        for meth,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
            p=meth()
            if abs(k.ToMM(p.x)-47.525)<.001 and k.ToMM(p.y) in [29.,32.8]:setter(vec(47.8,k.ToMM(p.y)))
for t in list(ts):
    if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='USB_VBUS_PROT' and t.GetLayer()==k.F_Cu and t.GetEnd()==vec(45.675,33.35):b.Remove(t)
line(b,'USB_VBUS_PROT',[(45.675,33.35),(46.25,33.65)],.5)
line(b,'USB_VBUS_PROT',[(46.25,33.65),(47.2,34.2)],1)
for ref,x,y in [('C21',97.2,49.3),('R21',94.1,49.2)]:
    f=b.FindFootprintByReference(ref);old={p.GetNumber():point(p) for p in f.Pads()};f.SetPosition(vec(x,y))
    for p in f.Pads():endpoint(old[p.GetNumber()],point(p))
k.SaveBoard(str(BOARD),b)
