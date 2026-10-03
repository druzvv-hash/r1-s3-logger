"""Two parallel 0.9mm layers in the M3/edge channel, 1mm elsewhere."""
import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
def endpoint(a,c):
    for t in ts:
        if isinstance(t,k.PCB_VIA):continue
        if t.GetStart()==vec(*a):t.SetStart(vec(*c))
        if t.GetEnd()==vec(*a):t.SetEnd(vec(*c))
for t in list(ts):
    if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='USB_VBUS_RAW' and t.GetLayer()==k.In2_Cu:b.Remove(t)
line(b,'USB_VBUS_RAW',[(28.2,35.4),(28,35.4),(28,30.8),(28.2,30.6),(29.2,29.6),(29.2,22.5)],1,k.In2_Cu)
line(b,'USB_VBUS_RAW',[(28.8,35.6),(28.2,35.4)],.7,k.In2_Cu)
line(b,'USB_VBUS_RAW',[(28.9,30.6),(28.2,30.6)],.7,k.In2_Cu)
line(b,'USB_VBUS_RAW',[(29.2,22.5),(28,23)],.3,k.In2_Cu)
for y in [22.5,23.4]:via(b,'USB_VBUS_RAW',29.2,y)
for layer in [k.B_Cu,k.In2_Cu]:
    line(b,'USB_VBUS_RAW',[(29.2,23.4),(29.2,20.98),(40.775,20.98),(40.775,24.275),(40.775,25.175)],.9,layer)
for t in ts:
    if not isinstance(t,k.PCB_VIA):continue
    changes={(45.8,35.3):(46.4,34.5),(47.2,33.35):(47.5,33.35),(47.2,34.2):(47.5,34.2),(48.7,31.2):(49,31.2)}
    old=point(t)
    if old in changes:t.SetPosition(vec(*changes[old]));endpoint(old,changes[old])
for t in list(ts):
    if isinstance(t,k.PCB_VIA):continue
    a=(k.ToMM(t.GetStart().x),k.ToMM(t.GetStart().y));c=(k.ToMM(t.GetEnd().x),k.ToMM(t.GetEnd().y))
    if t.GetNetname()=='USB_VBUS_PROT' and t.GetLayer()==k.F_Cu and a in [(45.675,33.35),(46.7,33.35)]:b.Remove(t)
    if t.GetNetname()=='USB_VBUS_PROT' and t.GetLayer()==k.B_Cu and a==(43.4,36.8):b.Remove(t)
line(b,'USB_VBUS_PROT',[(45.675,33.35),(46.85,33.35)],.5)
line(b,'USB_VBUS_PROT',[(46.85,33.35),(47.5,33.35)],1)
line(b,'USB_VBUS_PROT',[(43.4,36.8),(47.5,36.8),(47.5,34.2)],.2,k.B_Cu)
for ref,x,y in [('R21',94.5,49.2),('R22',91.5,49.2)]:
    f=b.FindFootprintByReference(ref);old={p.GetNumber():point(p) for p in f.Pads()};f.SetPosition(vec(x,y))
    for p in f.Pads():endpoint(old[p.GetNumber()],point(p))
k.SaveBoard(str(BOARD),b)
