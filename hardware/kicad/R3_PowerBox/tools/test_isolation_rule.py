"""Negative control: only scratch boards receive deliberately forbidden copper."""
import json
import shutil
import subprocess
from pathlib import Path
import pcbnew as k
from route_reva import ROOT, line, via, vec

scratch=ROOT/'tmp'/'isolation_negative_control'
scratch.mkdir(parents=True,exist_ok=True)
b=k.LoadBoard(str(ROOT/'R3_power.kicad_pcb'))
line(b,'DGND',[(120.5,60),(124.5,60)],.2)
via(b,'DGND',122.5,63)
f=b.FindFootprintByReference('TP15')
f.SetPosition(vec(122.5,67))
k.SaveBoard(str(scratch/'R3_power.kicad_pcb'),b)
for ext in ('kicad_pro','kicad_dru'):
    shutil.copyfile(ROOT/f'R3_power.{ext}',scratch/f'R3_power.{ext}')
cli=Path.home()/'AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe'
out=scratch/'drc.json'
subprocess.run([str(cli),'pcb','drc','--format','json','-o',str(out),
                str(scratch/'R3_power.kicad_pcb')],check=True)
d=json.loads(out.read_text(encoding='utf-8'))
hits=[v for v in d['violations'] if v['type']=='items_not_allowed']
report={'test':'deliberate track + via + TP15 pad in isolation corridor',
        'expected_minimum_items_not_allowed':3,'actual':len(hits),
        'pass':len(hits)>=3,'violations':hits}
(ROOT/'reports'/'routing_isolation_negative_control.json').write_text(
    json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('Isolation negative control:',len(hits),'forbidden-item findings')
raise SystemExit(0 if report['pass'] else 1)
