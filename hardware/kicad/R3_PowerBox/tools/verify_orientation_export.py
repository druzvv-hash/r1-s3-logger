"""Native position parity and bounded ECO audit; NOT JLC library acceptance."""
import csv,json,hashlib,subprocess
from pathlib import Path
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'R3_power.kicad_pcb'
board=k.LoadBoard(str(path))
baseline=ROOT/'tmp/orientation/pre_u4_0aeaea7.kicad_pcb'
if not baseline.exists():
    baseline.parent.mkdir(parents=True,exist_ok=True)
    baseline.write_bytes(subprocess.check_output(['git','show','0aeaea77a38e7b103af06dd491d3ec8ec9fd85f6:hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
assert hashlib.sha256(baseline.read_bytes()).hexdigest()=='f1cc618b274fae46e68432f66f089f505c7378a0eb8d68889083c54bba1eaa61','Unexpected baseline bytes'
old=k.LoadBoard(str(baseline))
errors=[]
def check(ok,label):
    if not ok: errors.append(label)
def point(p):return [round(k.ToMM(p.x),6),round(k.ToMM(p.y),6)]
def angle(a,b):return abs((a-b+180)%360-180)<0.00001
rows=list(csv.DictReader((ROOT/'reports/orientation_positions_NATIVE_NOT_FOR_ASSEMBLY.csv').open()))
seen=set()
for r in rows:
    ref=r['Ref'];f=board.FindFootprintByReference(ref)
    check(ref not in seen,ref+': duplicate position');seen.add(ref)
    check(f is not None,ref+': absent footprint')
    if f is None:continue
    x,y=point(f.GetPosition())
    check(abs(float(r['PosX'])-x)<1e-5 and abs(float(r['PosY'])+y)<1e-5,ref+': XY')
    check(angle(float(r['Rot']),f.GetOrientationDegrees()),ref+': rotation')
    check(r['Side']==('bottom' if f.GetLayer()==k.B_Cu else 'top'),ref+': side')
    check(r['Val']==f.GetValue() and r['Package']==str(f.GetFPID().GetLibItemName()),ref+': value/package')
expected={f.GetReference() for f in board.GetFootprints() if not f.IsExcludedFromPosFiles()}
check(seen==expected,'Position RefDes coverage')
allowed={'C40','C41','C42','C43','C44','R40'}
changes=[]
for f in board.GetFootprints():
    ref=f.GetReference();g=old.FindFootprintByReference(ref)
    check(g is not None,ref+': added footprint')
    if g is None:continue
    moved=point(f.GetPosition())!=point(g.GetPosition()) or not angle(f.GetOrientationDegrees(),g.GetOrientationDegrees())
    if moved:
        changes.append(dict(ref=ref,old_xy=point(g.GetPosition()),new_xy=point(f.GetPosition()),old_rotation=g.GetOrientationDegrees(),new_rotation=f.GetOrientationDegrees()))
        check(ref in allowed,ref+': unexpected placement change')
    def pads(fp):return sorted((p.GetNumber(),str(p.GetNetname())) for p in fp.Pads())
    check(pads(f)==pads(g),ref+': changed pad/net identity')
check(len(board.GetFootprints())==len(old.GetFootprints()),'Footprint count')
for ref in ['R107','R108']:check(board.FindFootprintByReference(ref).IsDNP(),ref+': must remain DNP')
def track(t):
    width=t.GetWidth(t.GetLayer()) if isinstance(t,k.PCB_VIA) else t.GetWidth()
    return (point(t.GetStart()),point(t.GetEnd()),width,t.GetLayer(),str(t.GetNetname()))
prior={str(t.m_Uuid.AsString()):t for t in old.GetTracks()}
new={str(t.m_Uuid.AsString()):t for t in board.GetTracks()}
changed=[]
for uid in set(prior)|set(new):
    a=prior.get(uid);b=new.get(uid)
    if a is not None and b is not None and track(a)==track(b):continue
    changed.append(uid)
    for t in [a,b]:
        if t is None:continue
        for x,y in [point(t.GetStart()),point(t.GetEnd())]:
            fixed_output_anchor=uid=='2266dfdf-712f-40ff-b1f3-a8a050152880' and [x,y]==[140.8,30.0]
            check(fixed_output_anchor or (135<=x<=153 and 32<=y<=52),'Copper ECO outside U4 region: '+uid)
check(board.GetCopperLayerCount()==4,'Four layers')
def edges(b):return sorted((point(d.GetStart()),point(d.GetEnd()),int(d.GetShape())) for d in b.GetDrawings() if d.GetLayer()==k.Edge_Cuts)
check(edges(old)==edges(board),'Board outline changed')
result=dict(pass_cad=not errors,errors=errors,native_position_rows=len(rows),placement_changes=changes,changed_track_via_records=len(changed),board_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),supplier_release='BLOCKED: accepted LCSC/MPN list, C1 exact part and J7 supplier-library centroid/orientation unavailable. Native angle parity is not JLC assembly acceptance.')
(ROOT/'reports/orientation_export_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
