"""Copper-contact widest paths, not minimum width across unrelated sense stubs.

Uses actual KiCad pad/track/via shapes and same-layer contact. Filled zones are
deliberately excluded: these power routes must work without relying on islands.
This is a geometric regression check, not IPC-2152/thermal qualification.
"""
import heapq,json,math,sys
import pcbnew as k
from route_reva import BOARD,ROOT
b=k.LoadBoard(str(BOARD));ts=b.GetTracks();fs=b.GetFootprints()
LAYERS=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu]
def xy(p):return (round(k.ToMM(p.x),5),round(k.ToMM(p.y),5))
def isvia(x):return isinstance(x,k.PCB_VIA)
def ispad(x):return isinstance(x,k.PAD)
def ident(x):
    if ispad(x):return x.GetParentFootprint().GetReference()+'.'+x.GetNumber()
    return ('via' if isvia(x) else k.LayerName(x.GetLayer()))+':'+str(xy(x.GetStart()))+('' if isvia(x) else '->'+str(xy(x.GetEnd())))
def layers(x):return [l for l in LAYERS if x.GetLayerSet().Contains(l)]
def pad(ref,num):return next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber()==str(num))
def key(x):return x.m_Uuid.AsString()
def shapes(x):return {l:x.GetEffectiveShape(l) for l in layers(x)}
configs=[
    ('USB_VBUS_RAW',('J7','A4'),('F2','1'),2.25,1.,2),
    ('USB_VBUS_PROT',('F2','2'),('U7','7'),2.25,1.,2),
    ('+3V3_D',('L1','2'),('J2','1'),3.,1.,2),
    ('CHG_SW1',('U8','28'),('L3','1'),3.3,.7,2),
    ('CHG_SW2',('U8','26'),('L3','2'),3.3,.7,2),
    ('CHG_PMID',('U8','29'),('C77','1'),2.25,.8,2),
    ('VSYS_RAW',('U8','25'),('F3','1'),3.3,.8,2),
    ('CHARGER_IN',('U7','1'),('U8','2'),2.25,.8,2),
    ('PACK_POS',('C87','1'),('U8','22'),3.3,.8,2),
    ('VSYS_MAIN',('C20','1'),('U2','3'),2.,.5,1),
    ('BAT_POS_RAW',('J8','1'),('Q3','2'),5.,.8,2),
    ('BAT_NEG_RAW',('J8','3'),('R93','1'),5.,.8,2),
    ('PACK_POS',('Q2','2'),('C87','1'),5.,.8,2),
    ('BMS_FET_COMMON',('Q3','3'),('Q2','3'),5.,.8,2),
    ('VSYS_PROT',('F3','2'),('Q4','2'),3.3,.8,2),
]
results=[]
for net,src,dst,amps,minimum,nvias in configs:
    items=[t for t in ts if t.GetNetname()==net]+[p for f in fs for p in f.Pads() if p.GetNetname()==net]
    ids={key(x):i for i,x in enumerate(items)};S=ids[key(pad(*src))];T=ids[key(pad(*dst))]
    sh=[shapes(x) for x in items];adj=[set() for x in items]
    for i in range(len(items)):
        for j in range(i):
            common=set(sh[i])&set(sh[j])
            if any(sh[i][l].Collide(sh[j][l],1) for l in common):adj[i].add(j);adj[j].add(i)
    escape=[];equiv=[]
    def capacity(i):
        x=items[i]
        if ispad(x) or isvia(x):return 100.
        width=k.ToMM(x.GetWidth());a,c=xy(x.GetStart()),xy(x.GetEnd());length=k.ToMM(x.GetLength())
        # Documented package escapes only, not arbitrary small signal branches.
        near_u8=all(48.0<=p[0]<=54.1 and 47.7<=p[1]<=51.6 for p in [a,c])
        near_mux=all(44<=p[0]<=47.5 and 32<=p[1]<=34 for p in [a,c])
        near_j7=all(27<=p[0]<=29.5 and 30<=p[1]<=36 for p in [a,c])
        if width<minimum and length<=1.6 and x.GetLayer()==k.F_Cu and (near_u8 or near_mux or near_j7):
            escape.append(ident(x));return minimum
        # The 1mm edge/M3 window cannot fit a 1mm track with useful margin.
        # Two matching 0.9mm conductors on B/In2, joined by paired vias.
        if net=='USB_VBUS_RAW' and width>=.89 and max(a[1],c[1])<25.3:
            twins=[y for y in items if not ispad(y) and not isvia(y) and y.GetLayer()!=x.GetLayer()
                   and k.ToMM(y.GetWidth())>=.89 and {xy(y.GetStart()),xy(y.GetEnd())}=={a,c}]
            if twins:equiv.append(ident(x));return width+k.ToMM(twins[0].GetWidth())
        return width
    caps=[capacity(i) for i in range(len(items))]
    score=[-1.]*len(items);score[S]=100.;prev={};q=[(-100.,S)]
    while q:
        cost,u=heapq.heappop(q)
        if -cost<score[u]:continue
        for v in adj[u]:
            s=min(score[u],caps[v])
            if s>score[v]:score[v]=s;prev[v]=u;heapq.heappush(q,(-s,v))
    path=[];u=T
    if score[T]>=0:
        while True:
            path.append(u)
            if u==S:break
            u=prev[u]
        path.reverse()
    clusters=[]
    for u in path:
        if not isvia(items[u]):continue
        x=items[u];near=[v for v,y in enumerate(items) if isvia(y) and math.dist(xy(x.GetPosition()),xy(y.GetPosition()))<=1.6]
        # Parallel means connected without crossing layers on BOTH sides.
        def layer_reachable(a,l):
            seen={a};todo=[a]
            while todo:
                z=todo.pop()
                for v in adj[z]-seen:
                    if l in sh[z] and l in sh[v] and sh[z][l].Collide(sh[v][l],1):seen.add(v);todo.append(v)
            return seen
        actual_layers=set()
        ix=path.index(u)
        for neighbor in path[max(0,ix-1):ix+2]:
            if neighbor!=u and not isvia(items[neighbor]):actual_layers.update(set(sh[neighbor])&set(sh[u]))
        paired=set(near)
        for l in actual_layers:paired &= layer_reachable(u,l)
        count=len(paired) if len(actual_layers)>=2 else 0
        clusters.append(dict(at=xy(x.GetPosition()),layers=[k.LayerName(l) for l in actual_layers],parallel_count=count))
    # Only real layer transitions, not unused same-layer vias, require a pair.
    active=[c for c in clusters if len(c['layers'])>=2]
    passed=score[T]>=minimum-1e-6 and all(c['parallel_count']>=nvias for c in active)
    results.append(dict(net=net,source=src,target=dst,current_A=amps,required_width_mm=minimum,
        widest_effective_width_mm=score[T],pass_check=passed,path=[ident(items[u]) for u in path],
        short_package_escapes=[ident(items[u]) for u in path if ident(items[u]) in escape],
        verified_parallel_edge_segments=[ident(items[u]) for u in path if ident(items[u]) in equiv],via_transitions=active))
report=dict(pass_check=all(r['pass_check'] for r in results),results=results,
    limitations='Geometric copper graph. Package escapes explicit, not thermal signoff. No DC current sharing simulation, no filled-zone shortcut, no impedance/EMC claim.')
(ROOT/'reports/review1_current_paths.json').write_text(json.dumps(report,indent=2)+'\n')
for r in results:print(r['net'],r['pass_check'],r['widest_effective_width_mm'],r['via_transitions'])
sys.exit(not report['pass_check'])
