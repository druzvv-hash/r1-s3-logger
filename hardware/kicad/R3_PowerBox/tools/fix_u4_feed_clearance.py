"""Local input-trunk dogleg after U4 physical pin ECO, not a global reroute."""
import pcbnew as k
from route_reva import BOARD,line
b=k.LoadBoard(str(BOARD)); ts=b.GetTracks()
target=[t for t in ts if t.m_Uuid.AsString()=='f2bf781d-c29b-4f09-82a1-19163a21ddee']
assert len(target)==1,'Already applied or wrong checkpoint'
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
b.Remove(target[0])
line(b,'+5V_ISO_A',[(140,50.2),(147,50.2),(147,40.625),(146.175,39.8)],.6,k.In2_Cu)
k.SaveBoard(str(BOARD),b)
