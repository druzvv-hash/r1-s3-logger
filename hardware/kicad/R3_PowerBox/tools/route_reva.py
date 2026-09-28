"""Explicit, reviewed Rev.A routing recipes; NOT an autorouter.

Run with KiCad 10 Python. Each route is specified by pad and waypoints.
The pre-routing baseline stays in Git; this script refuses to erase routes.
"""
from pathlib import Path
import json
import subprocess
import pcbnew as k

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / 'R3_power.kicad_pcb'
BASELINE = '1ccbc857938f1d36dbe252c1533ed0361289e0a1'

# Routing-blocking corrections only. Connector, module, mounting and B2B
# anchors remain unchanged. Local bypass loops supersede generic packing.
PLACEMENT = {
    'R105': (85, 28, 0), 'TP15': (111, 59, 0),
    'FB2': (128, 46, 0), 'FB3': (128, 54, 0),
    'C32': (133, 46, 0), 'C33': (133, 49, 0),
    'C34': (133, 54, 0), 'C35': (133, 57, 0),
    'FB4': (128, 79, 0), 'FB5': (128, 86, 0),
    'C60': (133, 79, 0), 'C61': (133, 82, 0),
    'C62': (133, 86, 0), 'C63': (128, 89, 0),
    'L3': (51, 41, 0),
    'C80': (50.1, 47.05, 90), 'C86': (51.9, 47.05, 90),
    'C77': (44, 43.5, 90), 'C78': (41, 43.5, 90),
    'C79': (38, 43.5, 90),
    'C81': (58, 43.5, 90), 'C82': (61, 43.5, 90),
    'C83': (64, 43.5, 90), 'C84': (67, 43.5, 90),
    'C85': (70, 43.5, 90),
    'C100': (46.5, 49.4, 90), 'C101': (43.5, 49.4, 90),
    'C102': (40.5, 49.4, 90), 'C103': (37.5, 49.4, 90),
    'C76': (46.5, 53, 90),
    'C87': (56.5, 49.4, 90), 'C88': (59.5, 49.4, 90),
    'C74': (48, 53.8, 0), 'C75': (54, 53.8, 180),
    'C89': (62, 52.5, 0),
    'C73': (44, 37.5, 0), 'TP2': (43, 56, 0),
    'TP31': (38, 39, 0), 'TP32': (33, 46, 0), 'D1': (65, 61, 0),
    'R77': (56, 60, 0),
    # Vacate positions occupied by the compact charger cluster.
    'D4': (31, 42, 0), 'TP22': (69, 55, 0),
    'TP23': (72, 59, 0), 'TP34': (31, 50, 0),
    'C104': (31, 38, 0), 'C105': (35, 40, 90),
    'R78': (60, 56, 0), 'R79': (60, 58, 0),
    'R81': (66, 52, 0), 'C70': (67, 48, 0), 'R72': (67, 50, 0),
    'R104': (55, 36, 0), 'D5': (59, 37, 0),
    'D7': (63, 37, 0), 'R80': (67, 40, 0),
}

def vec(x, y):
    return k.VECTOR2I(k.FromMM(x), k.FromMM(y))

def pad(board, ref, num):
    return next(p for p in board.FindFootprintByReference(ref).Pads()
                if p.GetNumber() == str(num))

def point(p):
    return (k.ToMM(p.GetPosition().x), k.ToMM(p.GetPosition().y))

def line(board, net, points, width=.2, layer=k.F_Cu):
    for a, b in zip(points, points[1:]):
        if a == b:
            continue
        t = k.PCB_TRACK(board)
        t.SetStart(vec(*a)); t.SetEnd(vec(*b))
        t.SetWidth(k.FromMM(width)); t.SetLayer(layer)
        t.SetNetCode(board.FindNet(net).GetNetCode())
        board.Add(t)

def via(board, net, x, y):
    v = k.PCB_VIA(board)
    v.SetPosition(vec(x,y)); v.SetWidth(k.FromMM(.7))
    v.SetDrill(k.FromMM(.3))
    v.SetLayerPair(k.F_Cu, k.B_Cu)
    v.SetNetCode(board.FindNet(net).GetNetCode()); board.Add(v)

def join(board, a, b, waypoints=(), width=.2, layer=k.F_Cu):
    pa, pb = pad(board,*a), pad(board,*b)
    assert pa.GetNetCode() == pb.GetNetCode(), (a,b)
    line(board, str(pa.GetNetname()), [point(pa), *waypoints, point(pb)], width, layer)

def prepare(board):
    if len(board.GetTracks()):
        raise RuntimeError('Refusing to overwrite routing. Restore an explicit checkpoint first.')
    for ref,(x,y,angle) in PLACEMENT.items():
        f=board.FindFootprintByReference(ref)
        f.SetPosition(vec(x,y)); f.SetOrientationDegrees(angle)
    # TI figure 8-21 places bootstrap capacitors on the bottom layer.
    for ref in ('C74','C75'):
        f=board.FindFootprintByReference(ref)
        f.Flip(f.GetPosition(),True)
    for z in board.Zones():
        if z.GetIsRuleArea():
            z.SetZoneName('ISOLATION_CORRIDOR')

def charger_start(board):
    # TI SLUSDV2C sec 8.4: local same-layer PMID/SYS bypasses first.
    join(board, ('U8',29), ('C80',1), width=.2)
    join(board, ('U8',25), ('C86',1), width=.2)
    join(board, ('C80',2), ('C86',2), width=.5)
    line(board,'DGND',[(51,49.3),(51,46.275)],.2)
    for y in (44.5,45.4):
        via(board,'DGND',51,y)
    line(board,'DGND',[(51,44.5),(51,46.275)],.4)
    # SW vias under U8; no top-layer SW spread around the bypass capacitors.
    for pin,net,x in [(28,'CHG_SW1',50.8),(26,'CHG_SW2',51.7)]:
        p=point(pad(board,'U8',pin))
        line(board,net,[p,(p[0],50),(x,50.6)],.2)
        line(board,net,[(x,50.6),(x,51.5)],.35)
        for y in (50.6,51.5):
            via(board,net,x,y)
    # Explicit inner-layer short links, with same-net paired through vias.
    for net,x,pin,outx in [('CHG_SW1',50.8,1,48.3),('CHG_SW2',51.7,2,53.7)]:
        line(board,net,[(x,51.5),(x,50.6),(outx,48),(outx,41)],.7,k.In2_Cu)
        for y in (40.5,41.4):
            via(board,net,outx,y)
        line(board,net,[(outx,40.5),(outx,41.4)],.7,k.In2_Cu)
        line(board,net,[(outx,40.5),point(pad(board,'L3',pin)),(outx,41.4)],.7)
    # Bootstrap loops use the underside and dedicated 0.30/0.70 vias.
    line(board,'N$7',[(49.1,50.6),(49.9,50.6),(49.9,51)],.2)
    via(board,'N$7',49.9,51)
    line(board,'N$7',[(49.9,51),(47.225,53.8)],.2,k.B_Cu)
    line(board,'CHG_SW1',[(50.8,51.5),(50.8,53.8),(48.775,53.8)],.2,k.B_Cu)
    line(board,'N$8',[(52.8625,51.4),(54,51.4)],.2)
    via(board,'N$8',54,51.4)
    line(board,'N$8',[(54,51.4),(54.775,53.8)],.2,k.B_Cu)
    line(board,'CHG_SW2',[(51.7,51.5),(51.7,53.8),(53.225,53.8)],.2,k.B_Cu)
    # PMID/SYS bulk banks: no switch current is allowed through these returns.
    for ref in ('C77','C78','C79'):
        p=point(pad(board,ref,1))
        line(board,'CHG_PMID',[p,(p[0],46.2)],.8)
    line(board,'CHG_PMID',[(38,46.2),(48.4,46.2),(48.4,47.825),(50.1,47.825)],.8)
    for ref in ('C81','C82','C83','C84','C85'):
        p=point(pad(board,ref,1))
        line(board,'VSYS_RAW',[p,(p[0],46.2)],.8)
    line(board,'VSYS_RAW',[(70,46.2),(54,46.2),(54,47.825),(51.9,47.825)],.8)
    # Local VBUS caps are separate from TPS2121 output bulk C73.
    join(board,('U8',2),('U8',3),width=.2)
    line(board,'CHARGER_IN',[(49.1,49.8),(48.5,49.8),(48.1,50.2),
                           (46.9,50.2),point(pad(board,'C100',1))],.2)
    for ref in ('C101','C102','C103'):
        p=point(pad(board,ref,1))
        line(board,'CHARGER_IN',[p,(p[0],51.7)],.8)
    line(board,'CHARGER_IN',[(37.5,51.7),(45,51.7),point(pad(board,'C100',1))],.8)
    # BAT bypasses directly adjacent to BAT pins; Kelvin BATP exits separately.
    join(board,('U8',22),('U8',23),width=.2)
    line(board,'PACK_POS',[(52.9,50.2),(54,50.2),(55,50.875),point(pad(board,'C87',1))],.2)
    for ref in ('C87','C88'):
        p=point(pad(board,ref,1))
        line(board,'PACK_POS',[p,(p[0],52),(56.5,52),point(pad(board,'C87',1))],.8)
    # REGN: short dedicated connection, not a shared gate-driver/LED loop.
    line(board,'CHG_REGN',[(49.1,51),(48,51),(47.6,51.4),(47.6,53.775),point(pad(board,'C76',1))],.2)
    # Ground via pairs are local stubs at capacitor pads. Full ground planes
    # are deliberately deferred until checkpoint E, as requested.
    for ref in ('C77','C78','C79','C81','C82','C83','C84','C85',
                'C100','C101','C102','C103','C76','C87','C88'):
        p=point(pad(board,ref,2))
        if ref in ('C77','C78','C79','C81','C82','C83','C84','C85'):
            sites=[(p[0]-.45,p[1]-.9),(p[0]+.45,p[1]-.9)]
        elif ref=='C100':
            sites=[(p[0]-.9,p[1]-.4),(p[0]-.9,p[1]+.4)]
        elif ref=='C76':
            sites=[(45.4,52.8),(45.4,53.65)]
        else:
            sites=[(p[0]-1.25,p[1]-.45),(p[0]-1.25,p[1]+.45)]
        # Drills sit outside the capacitor solder lands; no filled-via-in-pad
        # assembly process is assumed for these bypasses.
        for x,y in sites:
            via(board,'DGND',x,y)
            line(board,'DGND',[p,(x,y)],.3)

def battery_start(board):
    # FET source fanouts: keep gate pads out of the force-current copper.
    for ref,net,x,ys in [('Q2','PACK_POS',45.4,(76.6,77.5,78.4)),
                         ('Q3','BAT_POS_RAW',55.55,(77.75,78.6,79.45))]:
        src=[p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber()=='2']
        pts=sorted([point(p) for p in src],key=lambda p:p[1])
        line(board,net,pts,.35)
        line(board,net,[pts[1],(x,pts[1][1])],1.2)
        line(board,net,[(x,ys[0]),(x,ys[-1])],1.2)
        for y in ys: via(board,net,x,y)
    join(board,('Q2',3),('Q3',3),width=2)
    for y in (77.3,78.2,79.1):
        via(board,'BMS_FET_COMMON',50.5,y)
    # Battery connector to CHG FET, bottom-side force path.
    line(board,'BAT_POS_RAW',[point(pad(board,'J8',1)),(29,88.5),
                             (54,88.5),(54,81.5)],2.5,k.B_Cu)
    line(board,'BAT_POS_RAW',[(54,81.5),(55.55,79.95),(55.55,77.75)],1.2,k.B_Cu)
    # PACK exits the opposite FET source; avoid service-input plated holes.
    line(board,'PACK_POS',[(45.4,78.4),(45.4,73.5)],1.2,k.B_Cu)
    line(board,'PACK_POS',[(45.4,73.5),(42.5,70.6),(42.5,63.5),
                          (45.4,60.6),(45.4,60),(55,60),(57.5,57.5),
                          (57.5,53)],2.5,k.B_Cu)
    for x,y in [(57.5,52.1),(57.5,53),(58.4,53)]:
        via(board,'PACK_POS',x,y)
    line(board,'PACK_POS',[(56.5,52),(57.5,52),(57.5,53),(58.4,53)],1.2)
    line(board,'PACK_POS',[(57.5,52.1),(57.5,53),(58.4,53)],1.2,k.B_Cu)

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--from-baseline',action='store_true',
                        help='Rebuild this recipe from the immutable Git baseline')
    args=parser.parse_args()
    source=BOARD
    if args.from_baseline:
        source=ROOT/'tmp'/'routing_baseline.kicad_pcb'
        source.parent.mkdir(exist_ok=True)
        source.write_bytes(subprocess.check_output(['git','show',
            BASELINE+':hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
    b=k.LoadBoard(str(source)); prepare(b)
    if not args.prepare_only:
        charger_start(b)
        battery_start(b)
    k.SaveBoard(str(BOARD),b)
    print(f'Saved {len(b.GetTracks())} track/via objects; routing incomplete.')

if __name__=='__main__': main()
