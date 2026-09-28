"""Independent conservative 8 mm mounting square / routed copper check."""
import pcbnew as k
from route_reva import ROOT, point
b=k.LoadBoard(str(ROOT/'R3_power.kicad_pcb'))
def intersects(a,c,x0,y0,x1,y1):
    lo,hi=0.,1.
    for aa,dd,mn,mx in [(a[0],c[0]-a[0],x0,x1),(a[1],c[1]-a[1],y0,y1)]:
        if abs(dd)<1e-10:
            if aa<mn or aa>mx:return False
        else:
            p,q=sorted(((mn-aa)/dd,(mx-aa)/dd));lo=max(lo,p);hi=min(hi,q)
            if lo>hi:return False
    return True
errors=[]
for f in b.GetFootprints():
    if not f.GetReference().startswith('H'):continue
    x,y=point(f)
    for t in b.GetTracks():
        r=k.ToMM(t.GetWidth(k.F_Cu) if isinstance(t,k.PCB_VIA) else t.GetWidth())/2
        a=(k.ToMM(t.GetStart().x),k.ToMM(t.GetStart().y))
        c=(k.ToMM(t.GetEnd().x),k.ToMM(t.GetEnd().y))
        if intersects(a,c,x-4-r,y-4-r,x+4+r,y+4+r):
            errors.append((f.GetReference(),str(t.GetNetname()),a,c,k.LayerName(t.GetLayer())))
print('Mounting copper findings:',len(errors))
for e in errors:print(e)
raise SystemExit(bool(errors))
