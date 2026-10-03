"""Reuse the geometric SW/quiet test functions, never execute old F mutations."""
import ast,math,json
import pcbnew as k
from route_reva import ROOT,BOARD
tree=ast.parse((ROOT/'tools/verify_final_routing.py').read_text())
ns={'math':math,'k':k}
for n in tree.body:
    if isinstance(n,ast.FunctionDef) and n.name in {'pt','point_segment','cross','distance'}:
        exec(compile(ast.Module(body=[n],type_ignores=[]),'geometry','exec'),ns)
b=k.LoadBoard(str(BOARD));ts=b.GetTracks();tracks=[t for t in ts if not isinstance(t,k.PCB_VIA)]
sw={'CHG_SW1','CHG_SW2','SW_3V3','SW_5V'}
quiet={'PM_I2C_SCL','PM_I2C_SDA','USB_CC1','USB_CC2','BMS_SRP_FILT','BMS_SRN_FILT','BMS_VC1_FILT','BMS_VC2_FILT','NTC_BMS','NTC_CHG'}
pt=ns['pt'];hits=[]
for t in tracks:
    if t.GetNetname() not in sw:continue
    for q in tracks:
        if q.GetNetname() in quiet and ns['distance'](pt(t.GetStart()),pt(t.GetEnd()),pt(q.GetStart()),pt(q.GetEnd()))<k.ToMM(t.GetWidth()+q.GetWidth())/2:
            hits.append(dict(switch=t.GetNetname(),quiet=q.GetNetname(),start=pt(t.GetStart()),quiet_start=pt(q.GetStart())))
out=dict(pass_check=not hits,projection_overlaps=hits,scope='Track projections on all layers; not field simulation or plane-return impedance.')
(ROOT/'reports/review1_projection.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
raise SystemExit(bool(hits))
