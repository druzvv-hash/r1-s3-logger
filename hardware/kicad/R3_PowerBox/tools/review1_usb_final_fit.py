import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,point,line
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
for t in ts:
    if not isinstance(t,k.PCB_VIA):continue
    old=point(t);changes={(47.5,33.35):(47.4,33.35),(47.5,34.2):(47.4,34.2),(29.2,22.5):(29.7,22.5),(29.2,23.4):(29.7,23.4)}
    if old not in changes:continue
    new=changes[old];t.SetPosition(vec(*new))
    for s in ts:
        if isinstance(s,k.PCB_VIA):continue
        if s.GetStart()==vec(*old):s.SetStart(vec(*new))
        if s.GetEnd()==vec(*old):s.SetEnd(vec(*new))
for t in list(ts):
    if isinstance(t,k.PCB_VIA):continue
    if t.GetNetname()=='USB_VBUS_PROT' and t.GetLayer()==k.B_Cu and t.GetStart() in [vec(43.4,36.8),vec(47.5,36.8)]:b.Remove(t)
line(b,'USB_VBUS_PROT',[(43.4,36.8),(45.2,35),(45.6,34.5),(45.6,33.8),(47.4,33.35)],.2,k.B_Cu)
k.SaveBoard(str(BOARD),b)
