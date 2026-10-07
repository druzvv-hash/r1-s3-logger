"""Fail-closed Bottom inventory and physical-pin anchors; no factory export."""
import hashlib,json
from pathlib import Path
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'R3_power.kicad_pcb';b=k.LoadBoard(str(path));errors=[]
def mm(p):return [round(k.ToMM(p.x),6),round(k.ToMM(p.y),6)]
def require(ok,label):
    if not ok:errors.append(label)
rows=[]
for f in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
    if f.GetLayer()!=k.B_Cu:continue
    ref=f.GetReference();name=str(f.GetFPID().GetLibItemName())
    if ref=='D4':kind='ORIENTED_TVS_ARRAY'
    elif ref=='F2' and name=='Fuse_2920_7451Metric':kind='NONPOLAR_PPTC'
    elif ref.startswith('C') and name.startswith('C_'):kind='NONPOLAR_CERAMIC'
    elif ref.startswith('R') and name.startswith('R_'):kind='NONPOLAR_RESISTOR'
    elif ref.startswith('FB') and name.startswith('L_'):kind='NONPOLAR_BEAD'
    elif ref.startswith('TP'):kind='PCB_TEST_PAD'
    else:kind='UNREVIEWED';errors.append(ref+': unclassified Bottom footprint')
    rows.append(dict(ref=ref,value=f.GetValue(),package=name,kind=kind,dnp=f.IsDNP(),xy_mm=mm(f.GetPosition()),native_rotation=f.GetOrientationDegrees(),pads=[dict(number=p.GetNumber(),net=str(p.GetNetname()),xy_mm=mm(p.GetPosition())) for p in f.Pads()]))
    for v in [f.Reference(),f.Value()]:
        if v.IsVisible() and v.GetLayer()==k.B_SilkS:require(v.IsMirrored(),ref+': Bottom silk not mirrored')
require(len(rows)==54,'Unexpected Bottom footprint count')
require(sum(not r['dnp'] and r['kind']!='PCB_TEST_PAD' for r in rows)==50,'Unexpected populated Bottom count')
for ref in ['R107','R108']:require(b.FindFootprintByReference(ref).IsDNP(),ref+': DNP required')
# These anchors refer to PHYSICAL package pins, not generic logical G/S/D pad1.
anchors={'Q1':('2',[26.35,83.095],'SERVICE_IN_REV'),
         'Q4':('2',[69.35,68.095],'VSYS_PROT'),
         'U10':('1',[31.0375,31.75],'USB_CC1'),
         'C1':('1',[31.3,59.0],'SERVICE_IN_REV'),
         'D4':('1',[30.0875,32.35],'USB_CC1')}
for ref,(number,xy,net) in anchors.items():
    pads=[p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber()==number and mm(p.GetPosition())==xy]
    require(len(pads)==1 and str(pads[0].GetNetname())==net,ref+': physical pin1/positive anchor')
result=dict(pass_cad=not errors,errors=errors,board_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),physical_anchors=anchors,bottom_inventory=rows,
scope='PCB-side inventory and physical anchors only. D4 manufacturer polarity diagram and supplier part-specific zero-angle acceptance are separate gates. C1 exact manufacturer/package not established by a generic footprint.')
(ROOT/'reports/orientation_bottom_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key!='bottom_inventory'},indent=2));raise SystemExit(bool(errors))
