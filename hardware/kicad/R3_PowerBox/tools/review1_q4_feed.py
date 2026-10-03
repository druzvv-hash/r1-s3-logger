import review1_eco_guard
import pcbnew as k
from route_reva import BOARD,vec
b=k.LoadBoard(str(BOARD));ts=b.GetTracks();count=0
for t in ts:
    if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='VSYS_PROT' and t.GetStart()==vec(70.225,65) and t.GetEnd()==vec(69.35,66.5):
        assert t.GetWidth()==k.FromMM(.5),'Already changed'
        t.SetWidth(k.FromMM(.8));count+=1
assert count==1
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
k.SaveBoard(str(BOARD),b)
