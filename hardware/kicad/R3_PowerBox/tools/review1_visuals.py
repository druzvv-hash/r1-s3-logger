"""Contact sheets and native-layer closeups for review, not PCB modifications."""
from pathlib import Path
import subprocess,xml.etree.ElementTree as E
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent.parent
E.register_namespace('','http://www.w3.org/2000/svg')
for first,last in [(1,4),(5,8),(9,11)]:
    out=Image.new('RGB',(2000,1500),'white');d=ImageDraw.Draw(out)
    for i,n in enumerate(range(first,last+1)):
        im=Image.open(ROOT/f'tmp/pdfs/review1-{n:02}.png');im.thumbnail((990,710))
        x=(i%2)*1000;y=(i//2)*750;out.paste(im,(x,y+25));d.text((x+10,y+5),f'PDF PAGE {n}',fill='black')
    out.save(ROOT/f'tmp/pdfs/contact-{first}.png')
cli=Path.home()/'AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe'
sharp=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
for name,box,layers in [('charger',(39,38,22,19),'F.Cu,In2.Cu,F.Fab,Edge.Cuts'),('usb',(20,20,30,21),'F.Cu,B.Cu,F.Fab,B.Fab,Edge.Cuts'),('u2',(90,45,22,16),'F.Cu,B.Cu,F.Fab,B.Fab'),('ldo',(137,34,18,16),'F.Cu,B.Cu,F.Fab,B.Fab')]:
    path=ROOT/f'reports/R3_power_review1_{name}.svg'
    subprocess.run([str(cli),'pcb','export','svg','--layers',layers,'--mode-single','--page-size-mode','1','--exclude-drawing-sheet','-o',str(path),str(ROOT/'R3_power.kicad_pcb')],check=True,stdout=subprocess.DEVNULL)
    r=E.parse(path).getroot();r.set('viewBox',' '.join(map(str,box)));r.set('width','1800');r.set('height',str(int(1800*box[3]/box[2])));E.ElementTree(r).write(path,encoding='utf-8',xml_declaration=True)
    path.write_text('\n'.join(s.rstrip() for s in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    subprocess.run(['node','-e','require(process.argv[1])(process.argv[2]).flatten({background:"white"}).png().toFile(process.argv[3]);',str(sharp),str(path),str(path.with_suffix('.png'))],check=True)
