"""Intentional faults on scratch copies only. Restore positive reports afterward."""
import json,subprocess,sys
import pcbnew as k
from route_reva import ROOT,BOARD,vec
results=[]
for tool,kind in [('check_polarity.py','reversed_D3'),('check_abs_max.py','EN_to_VSYS'),('check_current_paths.py','thin_3V3_trunk')]:
    b=k.LoadBoard(str(BOARD));ts=b.GetTracks()
    if kind=='reversed_D3':
        pads={p.GetNumber():p for p in b.FindFootprintByReference('D3').Pads()};a,c=pads['1'].GetNet(),pads['2'].GetNet();pads['1'].SetNet(c);pads['2'].SetNet(a)
    elif kind=='EN_to_VSYS':
        p=next(p for p in b.FindFootprintByReference('U2').Pads() if p.GetNumber()=='5');p.SetNet(b.FindNet('VSYS_MAIN'))
    else:
        found=0
        for t in ts:
            if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='+3V3_D':t.SetWidth(k.FromMM(.2));found+=1
        assert found>0,found
    scratch=ROOT/'tmp'/('negative_'+kind+'.kicad_pcb');k.SaveBoard(str(scratch),b)
    code="import sys,runpy;sys.path.insert(0,'tools');import route_reva;from pathlib import Path;route_reva.BOARD=Path("+repr(str(scratch))+");runpy.run_path('tools/"+tool+"',run_name='__main__')"
    r=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True)
    results.append(dict(fault=kind,detected=r.returncode!=0,exit_code=r.returncode))
    if 'Traceback' in r.stderr:raise RuntimeError(r.stderr)
for tool in ['check_polarity.py','check_abs_max.py','check_current_paths.py']:
    subprocess.run([sys.executable,str(ROOT/'tools'/tool)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
out=dict(pass_check=all(x['detected'] for x in results),tests=results)
(ROOT/'reports/review1_semantic_negative_controls.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
raise SystemExit(not out['pass_check'])
