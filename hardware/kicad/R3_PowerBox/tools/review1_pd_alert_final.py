import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec,line
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
for t in list(ts):
    if t.GetNetname()!='PD_ALERT_N':continue
    if isinstance(t,k.PCB_VIA):
        if t.GetStart()==vec(37.6,30.8):b.Remove(t)
    elif t.GetLayer() in (k.B_Cu,k.In2_Cu) and 34<=k.ToMM(t.GetStart().x)<=42 and k.ToMM(t.GetStart().y)<32:b.Remove(t)
line(b,'PD_ALERT_N',[(35,29.95),(35.6,29.1),(37.8,29.1),(37.8,28.6),(41,28.6),(41,31.85),(42,31.85)],.2,k.F_Cu)
k.SaveBoard(str(BOARD),b)
