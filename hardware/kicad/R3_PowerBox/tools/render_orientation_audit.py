"""Render actual KiCad copper/fab/silk; never synthesize board geometry."""
from pathlib import Path
import subprocess,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
E.register_namespace('','http://www.w3.org/2000/svg')
cli=Path.home()/'AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe'
sharp=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
views=[('u4',(136,33,18,18),'F.Cu,F.Fab,F.SilkS'),('usb',(20,20,22,21),'F.Cu,F.Fab,F.SilkS'),('q1',(23,80,16,14),'F.Cu,F.Fab,F.SilkS'),('q2q3',(43,73,16,13),'F.Cu,F.Fab,F.SilkS'),('q4',(66,64,16,14),'F.Cu,F.Fab,F.SilkS'),('u8',(47,47,8,9),'F.Cu,F.Fab,F.SilkS'),('u9',(61,73,10,9),'F.Cu,F.Fab,F.SilkS'),('u1',(72,38,8,8),'F.Cu,F.Fab,F.SilkS'),('u2',(92,48,8,8),'F.Cu,F.Fab,F.SilkS'),('u5',(141,63,8,8),'F.Cu,F.Fab,F.SilkS'),('u7',(41,29,8,8),'F.Cu,F.Fab,F.SilkS'),('c1',(28,53,13,12),'F.Cu,F.Fab,F.SilkS'),('d1d3',(47,25,12,39),'F.Cu,F.Fab,F.SilkS'),('led',(55,25,31,16),'F.Cu,F.Fab,F.SilkS'),('bottom',(20,20,100,80),'B.Cu,B.Fab,B.SilkS')]
for name,box,layers in views:
    path=ROOT/f'reports/orientation_{name}.svg'
    subprocess.run([str(cli),'pcb','export','svg','--layers',layers,'--mode-single','--page-size-mode','1','--exclude-drawing-sheet','-o',str(path),str(ROOT/'R3_power.kicad_pcb')],check=True,stdout=subprocess.DEVNULL)
    r=E.parse(path).getroot();r.set('viewBox',' '.join(map(str,box)));r.set('width','1400');r.set('height',str(int(1400*box[3]/box[2])));E.ElementTree(r).write(path,encoding='utf-8',xml_declaration=True)
    subprocess.run(['node','-e','require(process.argv[1])(process.argv[2]).flatten({background:"white"}).png().toFile(process.argv[3]);',str(sharp),str(path),str(path.with_suffix('.png'))],check=True)
