import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
for t in list(ts):
    if isinstance(t,k.PCB_VIA) or t.GetNetname()!='PD_ALERT_N' or t.GetLayer()!=k.B_Cu:continue
    if t.GetStart() in [vec(37.8,29.95),vec(38.3,32.2),vec(41.5,32.2)]:b.Remove(t)
line(b,'PD_ALERT_N',[(37.8,29.95),(37.6,30.8)],.2,k.B_Cu)
via(b,'PD_ALERT_N',37.6,30.8)
line(b,'PD_ALERT_N',[(37.6,30.8),(40.5,30.8),(42,31.85)],.2,k.In2_Cu)
k.SaveBoard(str(BOARD),b)
