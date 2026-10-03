"""Review ECO invariants against cf7ea7c, plus explicit warning accounting."""
import json,subprocess,collections,re
import pcbnew as k
from route_reva import ROOT,BOARD
BASE='cf7ea7c2a540037fdbbc916575e068ce5bee85fc'
scratch=ROOT/'tmp/review1_authoritative.kicad_pcb'
scratch.write_bytes(subprocess.check_output(['git','show',BASE+':hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
a=k.LoadBoard(str(scratch));b=k.LoadBoard(str(BOARD));ats=a.GetTracks();bts=b.GetTracks()
def pt(p):return (round(k.ToMM(p.x),5),round(k.ToMM(p.y),5))
def anchor(board,ref):
    f=board.FindFootprintByReference(ref)
    return (pt(f.GetPosition()),f.GetOrientationDegrees(),f.GetLayer(),[(p.GetNumber(),pt(p.GetPosition()),p.GetDrillSize().x,p.GetDrillSize().y) for p in f.Pads()])
mechanics=['H1','H2','H3','H4','H5','H6','J1','J2','J3','J4','J7','J8','J9','J10','J11','J12','J13','U3','U6']
checks={r+'_geometry_unchanged':anchor(a,r)==anchor(b,r) for r in mechanics}
def boundaries(board):return sorted((z.GetZoneName(),z.Outline().Format(),z.GetLayer()) for z in board.Zones())
checks['zone_keepout_outlines_unchanged']=boundaries(a)==boundaries(b)
checks['board_outline_unchanged']=sorted(d.GetShapeStr()+str(pt(d.GetStart()))+str(pt(d.GetEnd())) for d in a.GetDrawings() if isinstance(d,k.PCB_SHAPE) and d.GetLayer()==k.Edge_Cuts)==sorted(d.GetShapeStr()+str(pt(d.GetStart()))+str(pt(d.GetEnd())) for d in b.GetDrawings() if isinstance(d,k.PCB_SHAPE) and d.GetLayer()==k.Edge_Cuts)
def records(ts):
    return sorted((t.GetNetname(),pt(t.GetStart()),pt(t.GetEnd()),t.GetLayer(),t.GetWidth(k.F_Cu) if isinstance(t,k.PCB_VIA) else t.GetWidth()) for t in ts if t.GetNetname() in ['BMS_SRP_FILT','BMS_SRN_FILT','BMS_VC1_FILT','BMS_VC2_FILT'] or (t.GetNetname() in ['DGND','BAT_NEG_RAW'] and 58<=k.ToMM(t.GetStart().x)<=62 and 65<=k.ToMM(t.GetStart().y)<=76))
checks['Kelvin_cell_sense_and_local_shunt_copper_unchanged']=records(ats)==records(bts)
for num,y in [('1',74.05),('2',67.95)]:
    p=next(p for p in b.FindFootprintByReference('R93').Pads() if p.GetNumber()==num)
    checks['R93_'+num+'_Kelvin_root_inside_pad']=p.HitTest(k.VECTOR2I(k.FromMM(61.4),k.FromMM(y)))
d=json.loads((ROOT/'reports/review1_work_drc.json').read_text(encoding='utf8'))
checks['DRC_no_errors']=not any(v['severity']=='error' for v in d['violations'])
checks['DRC_zero_unconnected']=not d['unconnected_items'];checks['DRC_exact_parity']=not d.get('schematic_parity')
old_d=json.loads(subprocess.check_output(['git','show',BASE+':hardware/kicad/R3_PowerBox/reports/routing_checkpoint_F_drc.json'],cwd=ROOT))
old_warn={i['uuid'] for v in old_d['violations'] if v['type']=='lib_footprint_mismatch' for i in v['items']}
warning_ledger=[dict(type=v['type'],severity=v['severity'],description=v['description'],items=v['items'],previously_present=all(i['uuid'] in old_warn for i in v['items'])) for v in d['violations']]
checks['all_DRC_warnings_individually_present_in_F']=all(v['type']=='lib_footprint_mismatch' and v['previously_present'] for v in warning_ledger)
erc=json.loads((ROOT/'reports/review1_erc.json').read_text(encoding='utf8'))
ev=[v for s in erc['sheets'] for v in s['violations']]
checks['ERC_no_errors']=not any(v['severity']=='error' for v in ev)
checks['ERC_only_known_generator_warning_types']=all(v['type'] in ['endpoint_off_grid','lib_symbol_mismatch'] for v in ev)
old_e=json.loads(subprocess.check_output(['git','show',BASE+':hardware/kicad/R3_PowerBox/reports/routing_checkpoint_F_erc.json'],cwd=ROOT))
old_keys={(v['type'],i['uuid']) for s in old_e['sheets'] for v in s['violations'] for i in v['items']}
added_refs={'R106','R107','R108','C109','#FLG0103'}
old_refs={(v['type'],re.sub(r'^(Symbol|Символ)\s+','',i['description']).split()[0]) for s in old_e['sheets'] for v in s['violations'] for i in v['items']}
for v in ev:
    v['previously_present']=all((v['type'],i['uuid']) in old_keys for i in v['items'])
    v['review1_added_symbol']=all(any(re.search(r'(?<![A-Za-z0-9])'+re.escape(ref)+r'(?![A-Za-z0-9])',i['description']) for ref in added_refs) for i in v['items'])
    v['same_existing_ref_artifact']=all((v['type'],re.sub(r'^(Symbol|Символ)\s+','',i['description']).split()[0]) in old_refs for i in v['items'])
    v['regenerated_C101_grid_artifact']=v['type'] in {'endpoint_off_grid','lib_symbol_mismatch'} and all(re.search(r'\bC101\b',i['description']) for i in v['items'])
    v['disposition']='Existing generator/library artifact' if v['previously_present'] else 'Existing reference, pin UUID changed after verified polarity/label regeneration' if v['same_existing_ref_artifact'] else 'Same generator artifact on explicitly added review symbol' if v['review1_added_symbol'] else 'Newly reported C101 generator artifact; passive C uses the same generated symbol; exact logical parity checked, not an electrical-error waiver' if v['regenerated_C101_grid_artifact'] else 'UNACCOUNTED'
checks['ERC_every_warning_accounted']=all(v['previously_present'] or v['review1_added_symbol'] or v['same_existing_ref_artifact'] or v['regenerated_C101_grid_artifact'] for v in ev)
report=dict(base=BASE,pass_check=all(checks.values()),checks=checks,DRC_warning_ledger=warning_ledger,
    ERC_warning_ledger=ev,ERC_counts=dict(collections.Counter(v['type'] for v in ev)),
    limitation='Warning types/references accounted individually; not a claim that the stock-library warnings have been suppressed. No physical thermal, EMC, capacitance or USB compliance test.')
(ROOT/'reports/review1_verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps(checks,indent=2));raise SystemExit(not report['pass_check'])
