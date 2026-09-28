"""Sync library identifiers/fields only; never reload or replace footprints."""
import json
import xml.etree.ElementTree as ET
import pcbnew as k
from route_reva import ROOT,BOARD
b=k.LoadBoard(str(BOARD)); root=ET.parse(ROOT/'tmp/F_netlist.xml').getroot()
issues=[]
for net in root.findall('./nets/net'):
    name=net.get('name')
    for node in net.findall('node'):
        f=b.FindFootprintByReference(node.get('ref'))
        pads=[p for p in f.Pads() if p.GetNumber()==node.get('pin')]
        if not pads or any(p.GetNetname()!=name for p in pads):
            issues.append((node.get('ref'),node.get('pin'),name))
if issues:raise RuntimeError('Schematic/PCB net mismatch: '+str(issues))
for comp in root.findall('./components/comp'):
    f=b.FindFootprintByReference(comp.get('ref'))
    ident=comp.findtext('footprint')
    if str(f.GetFPID().GetLibItemName())!=ident.split(':',1)[1]:
        raise RuntimeError('Footprint geometry family mismatch: '+comp.get('ref'))
    fid=k.LIB_ID();fid.Parse(k.UTF8(ident));f.SetFPID(fid)
    for name in ('Datasheet','Description'):
        node=comp.find("./fields/field[@name='"+name+"']")
        f.GetField(name).SetText(node.text or '' if node is not None else '')
    f.SetExcludedFromBOM(comp.find("property[@name='exclude_from_bom']") is not None)
for f in b.GetFootprints():
    if f.GetReference() in {'H1','H2','H3','H4','H5','H6'}:f.SetBoardOnly(True)
k.SaveBoard(str(BOARD),b)
(ROOT/'reports/routing_schematic_net_parity.json').write_text(json.dumps({
    'all_exported_schematic_nodes_match_PCB_pads':True,'issues':issues,
    'electrical_components':len(root.findall('./components/comp')),
    'scope':'Exact reference/pin/net comparison. Fields/library nicknames synchronized without replacing footprint geometry.'},indent=2)+'\n')
print('Schematic net parity PASS; metadata synchronized without geometry changes')
