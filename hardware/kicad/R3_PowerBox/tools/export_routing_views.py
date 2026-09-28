"""Native KiCad copper plots with explicit incomplete-checkpoint labels."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as E
import argparse,json
args=argparse.ArgumentParser()
args.add_argument('--checkpoint',default='A0')
args.add_argument('--drc',default='routing_checkpoint_A0_drc.json')
args=args.parse_args()
ROOT=Path(__file__).resolve().parent.parent
cli=Path.home()/'AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe'
sharp=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
ns='http://www.w3.org/2000/svg'
unrouted=len(json.loads((ROOT/'reports'/args.drc).read_text(encoding='utf-8'))['unconnected_items'])
E.register_namespace('',ns)
views={
    'top':('F.Cu,F.SilkS,Edge.Cuts',(18,0,164,107)),
    'bottom':('B.Cu,B.SilkS,Edge.Cuts',(18,0,164,107)),
    'all_layers':('F.Cu,In1.Cu,In2.Cu,B.Cu,F.SilkS,Edge.Cuts',(18,0,164,107)),
    'isolation':('F.Cu,In1.Cu,In2.Cu,B.Cu,F.SilkS,Edge.Cuts',(108,0,33,105)),
}
if args.checkpoint in ('E','F'):
    views['inner1']=('In1.Cu,F.Fab,Edge.Cuts',(18,0,164,107))
    views['inner2']=('In2.Cu,F.Fab,Edge.Cuts',(18,0,164,107))
for name,(layers,box) in views.items():
    out=ROOT/'reports'/f'R3_power_{args.checkpoint}_{name}.svg'
    subprocess.run([str(cli),'pcb','export','svg','--layers',layers,
        '--mode-single','--page-size-mode','1','--exclude-drawing-sheet',
        '--output',str(out),str(ROOT/'R3_power.kicad_pcb')],check=True)
    root=E.parse(out).getroot()
    x,y,w,h=box
    root.set('viewBox',' '.join(map(str,box)))
    root.set('width','3200' if name!='isolation' else '1200')
    root.set('height',str(round(int(root.get('width'))*h/w)))
    background=E.Element(f'{{{ns}}}rect',dict(x=str(x),y=str(y),width=str(w),height=str(h),fill='#101820'))
    root.insert(0,background)
    E.SubElement(root,f'{{{ns}}}rect',dict(x='121',y='20',width='3',height='80',
        fill='#c71b68',opacity='.30',stroke='#ff83ae',**{'stroke-width':'.18'}))
    title=E.SubElement(root,f'{{{ns}}}text',dict(x=str(x+1),y='4.5',fill='white',
        **{'font-size':'1.15','font-family':'Arial'}))
    title.text=f'{args.checkpoint} PROTOTYPE CHECKPOINT - {name.upper()} - NOT FOR FABRICATION'
    sub=E.SubElement(root,f'{{{ns}}}text',dict(x=str(x+1),y='7.5',fill='#cddbe0',
        **{'font-size':'.85','font-family':'Arial'}))
    stage='Filled domain planes.' if args.checkpoint in ('E','F') else 'No planes yet.'
    sub.text=f'{stage} {unrouted} unrouted connections. Corridor 121-124 mm: NO COPPER.'
    if name=='isolation':
        title.text=f'{args.checkpoint} / ISOLATION CHECK'
        sub.text=stage+' Corridor 121-124 mm: NO COPPER.'
    E.ElementTree(root).write(out,encoding='utf-8',xml_declaration=True)
    out.write_text('\n'.join(s.rstrip() for s in out.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    js="const sharp=require(process.argv[1]); sharp(process.argv[2]).png().toFile(process.argv[3]);"
    subprocess.run(['node','-e',js,str(sharp),str(out),str(out.with_suffix('.png'))],check=True)
