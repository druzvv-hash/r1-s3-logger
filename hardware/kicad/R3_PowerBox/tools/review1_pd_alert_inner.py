import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
starts=[(35,29.95),(35.6,29.1),(37.8,29.1),(37.8,28.6),(41,28.6),(41,31.85)]
for t in list(ts):
    if isinstance(t,k.PCB_VIA):continue
    if t.GetNetname()=='PD_ALERT_N' and any(t.GetStart()==vec(*p) for p in starts):b.Remove(t)
    if t.GetNetname()=='PD_VBUS_SENSE_DISCH' and t.GetLayer()==k.B_Cu:b.Remove(t)
line(b,'PD_VBUS_SENSE_DISCH',[(36.7,31.5),(36.7,32.775),(37.5,32.775)],.2,k.B_Cu)
line(b,'PD_ALERT_N',[(35,29.95),(37.8,29.95),(37.8,31.5)],.2,k.B_Cu)
via(b,'PD_ALERT_N',37.8,31.5)
line(b,'PD_ALERT_N',[(37.8,31.5),(37.8,33.1),(42,33.1),(42,31.85)],.2,k.In1_Cu)
k.SaveBoard(str(BOARD),b)
