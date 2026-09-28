"""Incremental checkpoint F cleanup. Never reloads an earlier PCB checkpoint.

Only the six individually audited, redundant DRC dangling objects are removed.
Conflicting footprint legends are retained on fabrication layers, not deleted.
Board-level service/polarity legends are never silently removed.
"""
from pathlib import Path
import json
import pcbnew as k

ROOT=Path(__file__).resolve().parent.parent
BOARD=ROOT/'R3_power.kicad_pcb'
REMOVE={
    '86be6c96-dfe8-4437-8333-0159c9d93902',
    '4d757a27-0b09-4043-8d1f-fe513eea768a',
    'b163afd4-6105-492c-8ec6-237bc9e24a63',
    '1b972f8d-cc1c-44b9-84a2-53a6984c74e3',
    '40c80985-40ee-40b8-8ecd-afcefce54af3',
    'f390aadd-fcbf-4172-a1b4-52a79f296208',
}

def main():
    b=k.LoadBoard(str(BOARD))
    report={'removed_this_invocation':[], 'legends_moved_this_invocation':[]}
    tracks=b.GetTracks()
    removed=[]
    for t in tracks:
        if t.m_Uuid.AsString() in REMOVE:
            report['removed_this_invocation'].append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname()))
            removed.append(t)
    for t in removed:
        b.Remove(t)
    drc=json.loads((ROOT/'reports/routing_checkpoint_E_drc.json').read_text(encoding='utf-8'))
    ids={i['uuid'] for v in drc['violations'] if v['type'].startswith('silk') or v['type']=='text_height' for i in v['items']}
    print('Removed dangling objects',len(report['removed_this_invocation']),flush=True)
    for f in b.GetFootprints():
        for g in [f.Reference(),f.Value(),*f.GraphicalItems()]:
            if g.m_Uuid.AsString() in ids and g.GetLayer() in (k.F_SilkS,k.B_SilkS):
                report['legends_moved_this_invocation'].append(dict(ref=f.GetReference(),uuid=g.m_Uuid.AsString()))
                g.SetLayer(k.F_Fab if g.GetLayer()==k.F_SilkS else k.B_Fab)
    print('Moved legends',len(report['legends_moved_this_invocation']),flush=True)
    labels={
        'PRIMARY / DGND':(92,96.8), 'POWER ON/OFF':(94,65),
        'H3 M3':(33,96.5), 'SERVICE IN 6-12V':(36,54.5),
        'J12 PRIMARY B2B':(113,48.5), 'USB-C':(24,25),
        'CHG':(59,39.2), 'RUN':(85.5,26.5),
        'J13 ISOLATED B2B':(158,37.5),
    }
    for g in b.GetDrawings():
        if isinstance(g,k.PCB_TEXT) and g.GetText() in labels:
            x,y=labels[g.GetText()]
            g.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y)))
            g.SetTextAngle(k.EDA_ANGLE(0,k.DEGREES_T))
            g.SetTextSize(k.VECTOR2I(k.FromMM(.85),k.FromMM(.85)))
            g.SetTextThickness(k.FromMM(.13))
    # Connector references originally lay wholly outside the board outline.
    for ref,(x,y) in {'J1':(29,57),'J2':(77,21.5),'J4':(97,21.5),
                      'J8':(31,76),'J9':(53,32)}.items():
        g=b.FindFootprintByReference(ref).Reference()
        g.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y)))
        g.SetLayer(k.F_SilkS)
        g.SetTextAngle(k.EDA_ANGLE(0,k.DEGREES_T))
        g.SetTextSize(k.VECTOR2I(k.FromMM(.85),k.FromMM(.85)))
    for ref in ('C23','R105','C1','TP2'):
        b.FindFootprintByReference(ref).Reference().SetLayer(k.F_Fab)
    report['audited_redundant_uuids']=sorted(REMOVE)
    b.FindFootprintByReference('L3').SetValue('SRP7028A-1R0M 1uH')
    filler=k.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    k.SaveBoard(str(BOARD),b)
    (ROOT/'reports/routing_F_cleanup.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
