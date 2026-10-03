"""Bounded second charger refinement after the failed courtyard trial.
TI Fig8-21 inner-layer SW arrangement retained. Never replay.
"""
import pcbnew as k
from route_reva import BOARD,vec,pad,point,line,via
b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
assert point(b.FindFootprintByReference('L3'))==(51.,41.)
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
def move(ref,x,y):
    f=b.FindFootprintByReference(ref);prev={p.GetNumber():k.VECTOR2I(p.GetPosition()) for p in f.Pads()}
    f.SetPosition(vec(x,y))
    for p in f.Pads():
        for t in ts:
            if isinstance(t,k.PCB_VIA):continue
            if t.GetStart()==prev[p.GetNumber()]:t.SetStart(p.GetPosition())
            if t.GetEnd()==prev[p.GetNumber()]:t.SetEnd(p.GetPosition())
move('L3',51,42)
move('C77',45,44.5);move('C81',57,44.5)
for t in ts:
    if not isinstance(t,k.PCB_VIA):continue
    if str(t.GetNetname()) in ['CHG_SW1','CHG_SW2'] and k.ToMM(t.GetPosition().y)<43:
        prev=k.VECTOR2I(t.GetPosition());new=prev+vec(0,1);t.SetPosition(new)
        for s in ts:
            if isinstance(s,k.PCB_VIA):continue
            if s.GetStart()==prev:s.SetStart(new)
            if s.GetEnd()==prev:s.SetEnd(new)
for t in list(ts):
    if isinstance(t,k.PCB_VIA):continue
    net=str(t.GetNetname());a=(k.ToMM(t.GetStart().x),k.ToMM(t.GetStart().y));c=(k.ToMM(t.GetEnd().x),k.ToMM(t.GetEnd().y))
    if net in ['CHG_PMID','VSYS_RAW'] and t.GetLayer()==k.F_Cu and a in [(50.1,49.275),(51.9,49.3)] and c[1]==47.825:
        b.Remove(t);line(b,net,[a,(a[0],48.8)],.2);line(b,net,[(a[0],48.8),c],.45)
    if net in ['CHG_SW1','CHG_SW2'] and t.GetLayer()==k.F_Cu and abs(a[1]-50.6)<.001 and abs(c[1]-51.5)<.001:t.SetWidth(k.FromMM(.7))
k.SaveBoard(str(BOARD),b)
