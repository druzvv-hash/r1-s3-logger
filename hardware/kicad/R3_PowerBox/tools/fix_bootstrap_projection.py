"""F local fix: remove SW2 bootstrap projection under I2C/TS fanout.
Only C75 and its bootstrap branch plus adjacent PROG via escape are touched.
"""
import pcbnew as k
from route_reva import ROOT,BOARD,line,via,vec,point
b=k.LoadBoard(str(BOARD))
if point(b.FindFootprintByReference('C75')) not in ((54.0,53.8),(54.8,51.8)):
    raise SystemExit('Unexpected capacitor position; review before modification')
tracks=b.GetTracks(); removed=[]
for t in tracks:
    if (t.GetNetname()=='CHG_SW2' and t.GetLayer()==k.B_Cu and not isinstance(t,k.PCB_VIA)) or t.GetNetname()=='N$8':
        removed.append(t)
for t in removed:b.Remove(t)
# Move the neighboring PROG via just enough to clear C75's solder land.
for t in b.GetTracks():
    if t.GetNetname()!='N$6':continue
    if t.GetStart()==vec(54.4,52.8):t.SetStart(vec(54.4,53.1))
    if t.GetEnd()==vec(54.4,52.8):t.SetEnd(vec(54.4,53.1))
b.FindFootprintByReference('C75').SetPosition(vec(54.8,51.8))
line(b,'CHG_SW2',[(51.7,51.5),(52.2,52),(53.2,52),(54.025,51.8)],.2,k.B_Cu)
line(b,'N$8',[(52.8625,51.4),(54.2,51.4),(55,52.2),(55.4,52.6),(55.4,53)],.2)
via(b,'N$8',55.4,53)
line(b,'N$8',[(55.4,53),(55.575,52.825),(55.575,51.8)],.2,k.B_Cu)
filler=k.ZONE_FILLER(b);filler.Fill(b.Zones())
k.SaveBoard(str(BOARD),b)
print('C75 bootstrap projection correction saved on current F board')
