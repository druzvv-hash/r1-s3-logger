"""Render existing KiCad vector plots, not a synthetic PCB image."""
from pathlib import Path
import xml.etree.ElementTree as E
import subprocess
E.register_namespace('','http://www.w3.org/2000/svg')
p=Path('tmp/review1_charger.svg');r=E.parse(p).getroot()
r.set('viewBox','36 37 26 20');r.set('width','1560');r.set('height','1200')
E.ElementTree(r).write('tmp/review1_charger_crop.svg')
sharp=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
subprocess.run(['node','-e','require(process.argv[1])(process.argv[2]).flatten({background:"white"}).png().toFile(process.argv[3]);',str(sharp),'tmp/review1_charger_crop.svg','tmp/review1_charger_crop.png'],check=True)
