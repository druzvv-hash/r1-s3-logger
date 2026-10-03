"""One-shot final local clearance ECO; do not replay on a later board."""
import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,line
b=k.LoadBoard(str(BOARD)); ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea(): z.UnFill()
removed=0
for t in list(ts):
    if isinstance(t,k.PCB_VIA) or t.GetNetname()!='PD_ALERT_N' or t.GetLayer()!=k.B_Cu: continue
    if t.GetStart()==vec(38,31.8) and t.GetEnd()==vec(42,31.85):
        b.Remove(t); removed+=1
    elif t.GetEnd()==vec(38,31.8): t.SetEnd(vec(38.3,32.2))
assert removed==1, 'Unexpected board state; not saved'
line(b,'PD_ALERT_N',[(38.3,32.2),(41.5,32.2),(42,31.85)],.2,k.B_Cu)
k.SaveBoard(str(BOARD),b)
