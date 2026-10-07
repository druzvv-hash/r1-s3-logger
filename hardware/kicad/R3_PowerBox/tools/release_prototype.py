"""Read frozen Git source, plot fresh KiCad fabrication, stage assembly data.
Run with KiCad Python: release_prototype.py prepare|finish SOURCE_SHA
No source PCB writes and no old BOM/CPL reuse.
"""
import csv,json,hashlib,subprocess,sys,zipfile
from pathlib import Path
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[2]
mode,sha=sys.argv[1:];assert len(sha)==40
CLI=Path(sys.executable).with_name('kicad-cli.exe')
OUT=ROOT/'manufacturing'/('RevA_PROTOTYPE_'+sha[:7]);OUT.mkdir(exist_ok=True)
def git(*a):return subprocess.check_output(['git',*a],cwd=REPO)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert git('rev-parse',sha).decode().strip()==sha
inputs=['R3_power.kicad_pcb','R3_power.kicad_sch','R3_power.kicad_pro','bom/prototype_assembly_policy.json','bom/C1_sourcing.json','tools/logical_nets.json']
for name in inputs:
    committed=git('show',sha+':hardware/kicad/R3_PowerBox/'+name)
    assert committed.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),name+' differs from source commit'
board=ROOT/'R3_power.kicad_pcb';before=digest(board)
policy=json.loads((ROOT/'bom/prototype_assembly_policy.json').read_text())
def run(*a):subprocess.run([str(CLI),*map(str,a)],check=True,cwd=ROOT)
def load(name):return json.loads((ROOT/'reports'/name).read_text(encoding='utf-8'))
gates={}
d=load('release_prototype_drc.json');e=load('release_prototype_erc.json')
ev=[v for s in e['sheets'] for v in s['violations']]
gates.update(DRC_errors=sum(v['severity']=='error' for v in d['violations']),DRC_warnings=len(d['violations']),unconnected=len(d['unconnected_items']),parity=len(d.get('schematic_parity',[])),ERC_errors=sum(v['severity']=='error' for v in ev),ERC_warnings=len(ev))
assert gates['DRC_errors']==gates['unconnected']==gates['parity']==gates['ERC_errors']==0
for name,key in [('release_review1_verification.json','pass_check'),('review1_current_paths.json','pass_check'),('review1_abs_max.json','pass_check'),('review1_polarity.json','pass_check'),('orientation_physical_audit.json','pass'),('orientation_export_audit.json','pass_cad'),('orientation_bottom_audit.json','pass_cad')]:
    report=load(name);assert report[key],name;gates[name]='PASS'
    if 'board_sha256' in report:assert report['board_sha256']==before,name+' stale'
assert not load('release_domain_audit.json')['issues']
if mode=='prepare':
    fab=OUT/'fabrication';fab.mkdir(exist_ok=True)
    run('pcb','export','gerbers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts','--subtract-soldermask','-o',str(fab)+'/',board)
    run('pcb','export','drill','--format','excellon','--drill-origin','absolute','--excellon-separate-th','--generate-map','--map-format','svg','--generate-report','--report-path',fab/'drill_report.txt','-o',str(fab)+'/',board)
    run('pcb','export','pos','--format','csv','--units','mm','--side','both','-o',OUT/'native_positions_reference.csv',board)
    b=k.LoadBoard(str(board));pos={r['Ref']:r for r in csv.DictReader((OUT/'native_positions_reference.csv').open())}
    rows=[]
    for f in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
        ref=f.GetReference();reason='DNP' if f.IsDNP() else 'PCB_FEATURE' if ref.startswith(('H','TP')) else 'MANUAL_POPULATE' if ref in policy['manual'] else 'FACTORY_CANDIDATE'
        if ref in policy['mandatory_dnp']:assert f.IsDNP()
        row=dict(ref=ref,value=f.GetValue(),footprint=str(f.GetFPID().GetLibItemName()),side='Bottom' if f.GetLayer()==k.B_Cu else 'Top',x=round(k.ToMM(f.GetPosition().x),6),y=round(-k.ToMM(f.GetPosition().y),6),rotation=round(f.GetOrientationDegrees()%360,6),mpn=policy['exact_mpn'].get(ref,'UNRESOLVED'),lcsc=policy['lcsc'].get(ref,'UNRESOLVED'),disposition=reason)
        if reason=='FACTORY_CANDIDATE':
            p=pos[ref];assert p['Package']==row['footprint'] and p['Val']==row['value'] and p['Side'].lower()==row['side'].lower()
            assert abs(float(p['PosX'])-row['x'])<1e-5 and abs(float(p['PosY'])-row['y'])<1e-5 and abs(float(p['Rot'])%360-row['rotation'])<1e-5
        rows.append(row)
    A=[r for r in rows if r['disposition']=='FACTORY_CANDIDATE' and r['side']=='Top'];B=[r for r in rows if r['disposition']=='FACTORY_CANDIDATE']
    assert len(A)==91 and len(B)==141
    tables={}
    for label,selected in [('A_TOP',A),('B_BOTH',B)]:
        tables[label+'_BOM']=[['Comment','Designator','Footprint','LCSC Part #','MPN','Qty','Side','Sourcing status']]+[[r['value'],r['ref'],r['footprint'],r['lcsc'],r['mpn'],1,r['side'],'UNRESOLVED' if 'UNRESOLVED' in (r['mpn'],r['lcsc']) else 'EXACT_ID_ONLY'] for r in selected]
        tables[label+'_CPL']=[['Designator','Mid X','Mid Y','Layer','Rotation','Footprint','MPN','LCSC Part #']]+[[r['ref'],r['x'],r['y'],r['side'],r['rotation'],r['footprint'],r['mpn'],r['lcsc']] for r in selected]
    tables['MANUAL_DNP_BOM']=[['Designator','Value','Footprint','MPN','LCSC Part #','Disposition','Side']]+[[r['ref'],r['value'],r['footprint'],r['mpn'],r['lcsc'],r['disposition'],r['side']] for r in rows if r['disposition']!='FACTORY_CANDIDATE']
    data=dict(source_commit=sha,branch='fix/r3-powerbox-reva-review1',date='2026-10-07',pcb_sha256=before,inventory=rows,tables=tables,gates=gates,counts=dict(A=91,B=141,Bottom=50),axis='absolute board origin; mm; Y up; no extra Bottom mirror; native KiCad angles normalized 0..360; verify library orientation before order')
    (OUT/'assembly_source.json').write_text(json.dumps(data,indent=2)+'\n')
    name='R3_PowerBox_RevA_PROTOTYPE_'+sha[:7]+'_Gerbers.zip'
    with zipfile.ZipFile(OUT/name,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(fab.iterdir()):
            if p.suffix.lower() not in {'.svg','.txt'}:z.write(p,p.name)
    print(json.dumps({'output':str(OUT),'A':len(A),'B':len(B),'gates':gates}))
elif mode=='finish':
    a=json.loads((OUT/'assembly_source.json').read_text());assert a['source_commit']==sha and a['pcb_sha256']==before
    audit=json.loads((OUT/'assembly_file_validation.json').read_text());assert audit['pass']
    hashes={p.relative_to(OUT).as_posix():digest(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['SHA256SUMS.txt','MANUFACTURING_RELEASE_REVA_PROTOTYPE.md']}
    (OUT/'SHA256SUMS.txt').write_text(''.join(h+'  '+n+'\n' for n,h in hashes.items()))
    manual=[r['ref'] for r in a['inventory'] if r['disposition']=='MANUAL_POPULATE'];dnp=[r['ref'] for r in a['inventory'] if r['disposition']=='DNP']
    text=f'''# R3 PowerBox Rev.A PROTOTYPE manufacturing release

Date: 2026-10-07. Branch: fix/r3-powerbox-reva-review1.
Final manufacturing source commit: `{sha}`.
PCB SHA256: `{before}`.
All manufacturing files were generated from the same final source commit.
Release/report commit is subsequent and does not modify the source PCB.

## Validation

{json.dumps(gates,indent=2)}

Warnings: 42 library-copy footprint mismatches; 423 ERC generator/library
warnings (212 lib_symbol_mismatch, 211 endpoint_off_grid). Individually accounted
in reports/release_review1_verification.json, no suppressed electrical errors.
Current paths, Kelvin preservation, mounting/isolation and negative controls PASS.
Orientation PASS means CAD physical mapping/native CPL parity. JLC component
library visual acceptance remains manual, not a claim of factory qualification.
D4: machine verified / visual JLC confirmation pending.

## Assembly

A TOP ONLY: 91 intended factory positions. B BOTH SIDES: 141 (91 Top + 50 Bottom).
Five PCB / two PCBA / three bare is the intended ordering configuration, not an order.
Manual common: {', '.join(manual)}.
DNP: {', '.join(dnp)}. PCB test points/mounting holes excluded as PCB features.
A additionally requires all 50 Bottom parts manually; B includes them as candidates.
C1 — MANUAL_POPULATE, NOT DNP — Panasonic EEE-FK1E470P / LCSC C178545.
No automatic substitutions. Missing MPN/LCSC is UNRESOLVED, not a generic purchase
approval. All factory LCSC identifiers remain unresolved in this source state;
resolve exact matches before authorizing placement. Q1/Q4 use the owner-selected
AO4407A assembly override; logical pad1 is Gate, physical package pin1 is Source.

## Required JLC review before order

J7 USB-C: verify and manually align component body to PCB pads/edge in JLC
Component Placements before order. Do not change PCB geometry solely to compensate
JLC library centroid. Visually align contact row, mechanical tabs and PCB edge;
small manual X/Y correction is expected/allowed by owner.
Check every polarized component and both sides against physical pins/polarity,
not model text. Verify layer order F.Cu/In1.Cu/In2.Cu/B.Cu, 160x80mm, 1.6mm,
1oz copper target, manufacturing stackup and 2 assembled + 3 bare quantities.
Drill maps/reference native position CSV are not factory CPL uploads.
Resolve UNRESOLVED sourcing without substitutions and preserve manual/DNP list.

## Prototype limits

Powered, thermal, effective MLCC capacitance, PPTC derating and EMI validation
remain ahead. First STUSB4500 NVM programming power: 5V-only/non-PD. INA light-load
behavior remains a bench check. This is NOT production-qualified hardware.
No JLC visit/order/payment occurred during release.

## File hashes (SHA256)

| File | SHA256 |
|---|---|
'''+''.join(f'| {n} | `{h}` |\n' for n,h in hashes.items())
    (OUT/'MANUFACTURING_RELEASE_REVA_PROTOTYPE.md').write_text(text,encoding='utf-8')
    print(str(OUT/'MANUFACTURING_RELEASE_REVA_PROTOTYPE.md'))
else:raise ValueError(mode)
assert digest(board)==before,'Exporter changed source PCB'
