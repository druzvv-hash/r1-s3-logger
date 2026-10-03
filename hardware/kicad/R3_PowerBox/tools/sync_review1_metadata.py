"""Exact bidirectional source/PCB pin-net parity, then metadata only."""
import json,xml.etree.ElementTree as E
import pcbnew as k
from route_reva import ROOT,BOARD
b=k.LoadBoard(str(BOARD));r=E.parse(ROOT/'tmp/review1_netlist.xml').getroot()
want={f"{p.get('ref')}.{p.get('pin')}":n.get('name') for n in r.findall('./nets/net') for p in n.findall('node')}
actual={f'{f.GetReference()}.{p.GetNumber()}':str(p.GetNetname()) for f in b.GetFootprints() for p in f.Pads() if p.GetNumber() and f.GetReference() not in {'H1','H2','H3','H4','H5','H6'}}
issues=[(p,n,actual.get(p)) for p,n in want.items() if actual.get(p)!=n]
extra=[(p,n) for p,n in actual.items() if p not in want and n and not n.startswith('unconnected-')]
if issues or extra:raise RuntimeError(str((issues,extra)))
for c in r.findall('./components/comp'):
    f=b.FindFootprintByReference(c.get('ref'));ident=c.findtext('footprint');fid=k.LIB_ID();fid.Parse(k.UTF8(ident))
    if f.GetFPID().GetLibItemName()!=fid.GetLibItemName():raise RuntimeError('Wrong geometry family '+c.get('ref'))
    f.SetFPID(fid);f.SetValue(c.findtext('value'))
    # Match stable schematic UUID path, including newly added C109.
    sheet=c.find('sheetpath').get('tstamps');stamp=c.findtext('tstamps').split()[0]
    path=k.KIID_PATH()
    for uid in (sheet+stamp).split('/'):
        if uid:path.push_back(k.KIID(uid))
    f.SetPath(path)
    f.SetDNP(c.find("property[@name='dnp']") is not None)
    for name in ['Datasheet','Description']:
        node=c.find("./fields/field[@name='"+name+"']");f.GetField(name).SetText((node.text or '') if node is not None else '')
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
k.SaveBoard(str(BOARD),b)
report=dict(pass_check=True,schematic_nodes=len(want),pcb_numbered_pads=len(actual),issues=issues,extra_connected_pads=extra,scope='Exact named net/pin parity both directions; board-only mounting excluded; explicit NC handled by ERC/DRC.')
(ROOT/'reports/review1_net_parity.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
