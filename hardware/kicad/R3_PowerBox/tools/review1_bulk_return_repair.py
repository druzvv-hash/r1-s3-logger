"""Replace stretched old cap fanouts with explicit local power/ground routes."""
import pcbnew as k
from route_reva import BOARD,vec,point,pad,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
for ref,x,y in [('C77',46.6,46.9),('C101',42.7,49.4)]:
    f=b.FindFootprintByReference(ref);old={p.GetNumber():k.VECTOR2I(p.GetPosition()) for p in f.Pads()};f.SetPosition(vec(x,y))
    for p in f.Pads():
        for t in ts:
            if isinstance(t,k.PCB_VIA):continue
            if t.GetStart()==old[p.GetNumber()]:t.SetStart(p.GetPosition())
            if t.GetEnd()==old[p.GetNumber()]:t.SetEnd(p.GetPosition())
groundpads=[vec(*point(pad(b,r,2))) for r in ['C77','C81','C87']]
for t in list(ts):
    n=str(t.GetNetname())
    if isinstance(t,k.PCB_VIA):
        if n=='DGND' and abs(k.ToMM(t.GetPosition().x)-55.25)<.01 and 47<k.ToMM(t.GetPosition().y)<49:b.Remove(t)
        continue
    if n=='DGND' and (t.GetStart() in groundpads or t.GetEnd() in groundpads):b.Remove(t);continue
    if n in ['CHG_PMID','VSYS_RAW'] and t.GetLayer()==k.F_Cu and min(k.ToMM(t.GetStart().y),k.ToMM(t.GetEnd().y))<47 and max(k.ToMM(t.GetStart().y),k.ToMM(t.GetEnd().y))<48:
        b.Remove(t)
for r in ['C77','C81','C87']:
    x,y=point(pad(b,r,2))
    for dx in [-.45,.45]:
        via(b,'DGND',x+dx,y);line(b,'DGND',[(x,y),(x+dx,y)],.5)
line(b,'CHG_PMID',[(38,44.975),(38,45.4),(48.075,45.4),(48.075,46.9),(48.4,47.825),(50.1,47.825)],.8)
line(b,'CHG_PMID',[(41,44.975),(41,45.4)],.8)
line(b,'VSYS_RAW',[(54.525,46.9),(54.525,45.4),(70,45.4),(70,46.2)],.8)
line(b,'VSYS_RAW',[(54.525,46.9),(54,47.825),(51.9,47.825)],.8)
for x in [61,64,67]:line(b,'VSYS_RAW',[(x,44.975),(x,45.4)],.8)
for x in [68,69]:line(b,'VSYS_RAW',[(x,45.4),(x,46.2)],.8)
for r in ['C80','C100']:b.FindFootprintByReference(r).Reference().SetLayer(k.F_Fab)
k.SaveBoard(str(BOARD),b)
