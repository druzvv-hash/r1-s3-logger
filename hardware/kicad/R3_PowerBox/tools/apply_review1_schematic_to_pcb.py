"""One-shot, narrowly scoped review1 ECO on the current routed PCB.

Never load an earlier checkpoint. Source connectivity is exported KiCad XML.
Run once after generation; subsequent routing is authoritative.
"""
import json
import xml.etree.ElementTree as ET
import pcbnew as k
from route_reva import ROOT, BOARD, vec, pad, point, line
from generate_preliminary_placement import footprint_from_id

b = k.LoadBoard(str(BOARD))
if b.FindFootprintByReference('R106'):
    raise RuntimeError('Review1 ECO already applied; refusing to replay')
assert pad(b, 'D1', 1).GetNetname() == 'DGND'
assert pad(b, 'U2', 5).GetNetname() == 'VSYS_MAIN'
root = ET.parse(ROOT / 'tmp/review1_netlist.xml').getroot()
components = {c.get('ref'): c for c in root.findall('./components/comp')}
expected = {}
for net in root.findall('./nets/net'):
    name = net.get('name')
    if not b.FindNet(name):
        b.Add(k.NETINFO_ITEM(b, name))
    for node in net.findall('node'):
        expected[(node.get('ref'), node.get('pin'))] = name

# Rotate physical packages, not just labels: the corrected cathode now lands
# on the old high-rail copper. Existing net geometry stays unchanged.
for ref in ('D1', 'D2', 'D3'):
    f = b.FindFootprintByReference(ref)
    f.SetOrientationDegrees(f.GetOrientationDegrees() + 180)
    for p in f.Pads():
        p.SetNet(b.FindNet(expected[(ref, p.GetNumber())]))

old = b.FindFootprintByReference('F2')
f = footprint_from_id(components['F2'].findtext('footprint'))
f.SetReference('F2'); f.SetPath(old.GetPath())
f.SetPosition(vec(44.5, 24)); f.SetOrientationDegrees(0)
b.Remove(old); b.Add(f)
f = footprint_from_id(components['R106'].findtext('footprint'))
f.SetReference('R106'); f.SetPosition(vec(37.5, 29.5)); b.Add(f)

allowed = {('U10','18'), ('U2','5')}
changes = []
for f in b.GetFootprints():
    ref = f.GetReference()
    if ref not in components:
        continue
    c = components[ref]
    f.SetValue(c.findtext('value'))
    fid = k.LIB_ID(); fid.Parse(k.UTF8(c.findtext('footprint'))); f.SetFPID(fid)
    f.Value().SetVisible(False)
    for p in f.Pads():
        key = (ref, p.GetNumber())
        if key not in expected:
            continue
        wanted = expected[key]
        if p.GetNetname() != wanted:
            if ref not in ('F2','R106') and key not in allowed:
                raise RuntimeError(('Unexpected electrical delta', key, p.GetNetname(), wanted))
            changes.append([ref, p.GetNumber(), str(p.GetNetname()), wanted])
            p.SetNet(b.FindNet(wanted))

tracks = b.GetTracks()  # retain SWIG container until all removals are complete
for t in list(tracks):
    if isinstance(t, k.PCB_VIA):
        continue
    a, z = (k.ToMM(t.GetStart().x), k.ToMM(t.GetStart().y)), (k.ToMM(t.GetEnd().x), k.ToMM(t.GetEnd().y))
    if t.GetNetname() == 'VSYS_MAIN' and t.GetLayer() == k.F_Cu and (a == (94.8625,52.0) or z == (94.8625,52.0)):
        b.Remove(t)
    if t.GetNetname() == 'USB_VBUS_PROT' and (a == (34.9625,31.75) or z == (34.9625,31.75)):
        b.Remove(t)

for pin, oldpoint in ((1,(40.775,24)),(2,(45.225,24))):
    line(b, str(pad(b,'F2',pin).GetNetname()), [point(pad(b,'F2',pin)),oldpoint],1.0)

# The discharge resistor is a low-current sensing branch, NOT the load path.
line(b,'PD_VBUS_SENSE_DISCH',[point(pad(b,'R106',2)),(39,29.5),(39,31.75),point(pad(b,'U10',18))],.2)
line(b,'USB_VBUS_PROT',[point(pad(b,'R106',1)),(36.725,27),(45.225,27),(45.225,24)],.2)
warning = k.PCB_TEXT(b); warning.SetText('FIRST POWER: 5V ONLY / PROGRAM PD NVM')
warning.SetPosition(vec(76,97.5)); warning.SetTextSize(vec(.8,.8))
warning.SetTextThickness(k.FromMM(.12)); warning.SetLayer(k.F_SilkS); b.Add(warning)
k.SaveBoard(str(BOARD), b)
(ROOT/'reports/review1_eco_delta.json').write_text(json.dumps(changes,indent=2)+'\n')
print('Review1 ECO saved. DRC/rerouting mandatory; no completion implied.')
