"""Create a reproducible, unrouted preliminary R3 PowerBox placement.

Run with KiCad's bundled Python after exporting a KiCad XML netlist. The
script preserves the board outline, documentation graphics and isolation
keepout, replaces footprints from the schematic, assigns nets, and packs the
parts into the reviewed DIRTY -> PRIMARY -> ISOLATION -> CLEAN zones.
"""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parent.parent
BOARD_PATH = ROOT / "R3_power.kicad_pcb"
BASE_BOARD_PATH = ROOT / "tools" / "R3_power_floorplan_base.kicad_pcb"
SCHEMATIC_PATH = ROOT / "R3_power.kicad_sch"
NETLIST_PATH = ROOT / "tmp" / "R3_power_placement.xml"
KICAD_CLI = ROOT.parents[4] / "AppData"  # replaced below on Windows
KICAD_CLI = Path.home() / "AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"
GLOBAL_FP = Path.home() / "AppData/Local/Programs/KiCad/10.0/share/kicad/footprints"
LOCAL_FP = ROOT / "footprints"


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def export_netlist() -> None:
    NETLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(KICAD_CLI), "sch", "export", "netlist", "--format", "kicadxml",
         "-o", str(NETLIST_PATH), str(SCHEMATIC_PATH)],
        check=True,
    )


def footprint_from_id(footprint_id: str):
    library, name = footprint_id.split(":", 1)
    if library == "R3_Power":
        library_path = LOCAL_FP / "R3_Power.pretty"
    else:
        library_path = GLOBAL_FP / f"{library}.pretty"
    footprint = pcbnew.FootprintLoad(str(library_path), name)
    if footprint is None:
        raise RuntimeError(f"Cannot load footprint {footprint_id} from {library_path}")
    return footprint


def component_sheet(comp: ET.Element) -> str:
    for prop in comp.findall("property"):
        if prop.get("name") == "Sheetname":
            return prop.get("value", "")
    return ""


ANCHORS = {
    # Dirty-edge connectors and the two principal high-current paths.
    "J7": (23.0, 33.0, 90), "J1": (27.0, 55.0, 90),
    "J8": (29.0, 78.0, 90), "J9": (28.0, 92.0, 90),
    "U10": (33.0, 33.0, 0), "D4": (33.0, 43.0, 0),
    "TP31": (38.0, 39.0, 0), "TP32": (38.0, 44.0, 0),
    "U7": (45.0, 33.0, 0), "C73": (48.5, 37.0, 0),
    "U8": (51.0, 51.0, 0), "L3": (51.0, 59.0, 90),
    "C74": (47.0, 46.0, 0), "C75": (55.0, 46.0, 0),
    "C77": (58.0, 49.0, 0), "C78": (65.0, 49.0, 0),
    "C79": (58.0, 55.0, 0), "C80": (65.0, 55.0, 0),
    "C100": (46.0, 49.0, 0), "C101": (40.5, 50.0, 90),
    "C102": (40.5, 56.0, 90), "C103": (40.5, 62.0, 90),
    "U9": (39.0, 82.0, 0), "Q2": (48.0, 78.0, 0),
    "Q3": (53.0, 78.0, 180), "R93": (59.0, 87.0, 90),
    "R90": (34.0, 70.0, 0), "R91": (38.0, 70.0, 0),
    "C97": (34.0, 74.0, 0), "C98": (38.0, 74.0, 0),
    "R94": (42.5, 84.0, 0), "R95": (46.0, 84.0, 0),
    "C94": (44.0, 87.0, 0),
    # Primary switchers.
    "U1": (76.0, 42.0, 0), "L1": (84.0, 42.0, 0),
    "U2": (96.0, 52.0, 0), "L2": (104.0, 52.0, 90),
    "J2": (72.0, 24.0, 0), "J4": (98.0, 24.0, 0),
    "J5": (108.0, 90.0, 90), "J10": (68.0, 92.0, 0),
    # Isolation modules straddle the corridor; their local parts remain on
    # their respective sides. No unrelated footprint enters the keepout.
    # Pin 1/2/3 are on the primary (left) side; pin 5/6/7/8 are on the
    # secondary (right) side. The 3.0 mm all-layer barrier lies between the
    # edge of pad 3 and the edge of pad 5 for both SIP8 modules.
    "U3": (114.9, 40.0, 0), "U6": (114.9, 73.0, 0),
    # Clean-side regulators and connectors.
    "U4": (145.0, 42.0, 0),
    "C40": (140.5, 38.0, 0), "C41": (145.0, 37.0, 0),
    "C42": (149.5, 38.0, 0), "C43": (140.5, 46.0, 0),
    "C44": (149.5, 46.0, 0), "R40": (145.0, 48.0, 0),
    "U5": (145.0, 67.0, 0), "C50": (141.0, 67.0, 0),
    "C51": (149.0, 67.0, 0),
    # Dedicated isolated-side probe rows; they stay physically separated from
    # every primary/dirty test point and use only the GND_ISO reference group.
    "TP7": (137.5, 88.0, 0), "TP8": (143.0, 88.0, 0),
    "TP9": (148.5, 88.0, 0), "TP10": (154.0, 88.0, 0),
    "TP11": (137.5, 94.0, 0), "TP12": (143.0, 94.0, 0),
    "TP13": (148.5, 94.0, 0), "TP14": (154.0, 94.0, 0),
    "J3": (175.0, 88.0, 90), "J6": (175.0, 34.0, 90),
}


REGIONS = {
    "input_protection1": (25.0, 55.0, 63.0, 98.0),
    "battery_management1": (25.0, 65.0, 63.0, 98.0),
    "charger_powerpath1": (25.0, 22.0, 63.0, 64.0),
    "digital_buck1": (66.0, 30.0, 88.0, 65.0),
    "preiso_buck1": (89.0, 30.0, 110.0, 82.0),
    "isolation1": (108.0, 22.0, 134.0, 58.0),
    "ina_isolation1": (108.0, 61.0, 134.0, 98.0),
    "isolated_ldos1": (136.0, 22.0, 158.0, 98.0),
    "outputs1": (159.0, 22.0, 178.0, 98.0),
}


def bbox_mm(footprint):
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_CrtYd)
    box = footprint.GetLayerBoundingBox(layers)
    if box.GetWidth() == 0 or box.GetHeight() == 0:
        box = footprint.GetBoundingBox()
    return tuple(pcbnew.ToMM(v) for v in (box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom()))


def overlaps(a, b, margin=0.35):
    return not (
        a[2] + margin <= b[0] or b[2] + margin <= a[0]
        or a[3] + margin <= b[1] or b[3] + margin <= a[1]
    )


def place_at(footprint, x, y, rotation=0):
    footprint.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    footprint.SetOrientationDegrees(rotation)


def add_text(board, text, x, y, layer, size=1.0, angle=0, thickness=0.18):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    item.SetLayer(layer)
    item.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    item.SetTextThickness(mm(thickness))
    item.SetTextAngleDegrees(angle)
    board.Add(item)


def main() -> None:
    export_netlist()
    tree = ET.parse(NETLIST_PATH)
    root = tree.getroot()
    board = pcbnew.LoadBoard(str(BASE_BOARD_PATH))
    board.SetCopperLayerCount(4)
    barrier_layers = pcbnew.LSET()
    for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        barrier_layers.AddLayer(layer)
    for zone in board.Zones():
        if zone.GetIsRuleArea():
            zone.SetLayerSet(barrier_layers)
    # This placement generator is intentionally never a router. The tracked
    # floorplan board starts with no tracks, and this script does not add any.

    components = {}
    sheets = {}
    for comp in root.findall("./components/comp"):
        ref = comp.get("ref", "")
        footprint_id = (comp.findtext("footprint") or "").strip()
        if not ref or not footprint_id:
            continue
        fp = footprint_from_id(footprint_id)
        fp.SetReference(ref)
        fp.SetValue(comp.findtext("value") or "")
        if ref == "U11" or "DNP" in fp.GetValue():
            fp.SetDNP(True)
        board.Add(fp)
        components[ref] = fp
        sheets[ref] = component_sheet(comp)

    net_objects = {}
    for net_xml in root.findall("./nets/net"):
        name = net_xml.get("name", "")
        if not name:
            continue
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        net_objects[name] = net
        for node in net_xml.findall("node"):
            fp = components.get(node.get("ref", ""))
            pin = node.get("pin", "")
            if fp is None:
                continue
            for pad in fp.Pads():
                if pad.GetNumber() == pin:
                    pad.SetNet(net)

    placed_boxes = []
    placed_labels = []
    for ref, (x, y, rot) in ANCHORS.items():
        fp = components.get(ref)
        if fp is None:
            continue
        place_at(fp, x, y, rot)
        box = bbox_mm(fp)
        hits = [placed_labels[i] for i, other in enumerate(placed_boxes) if overlaps(box, other)]
        if hits:
            raise RuntimeError(f"Anchor courtyard overlap at {ref} with {hits}")
        placed_boxes.append(box)
        placed_labels.append(ref)

    # Place the remaining footprints largest-first onto a 1 mm search grid.
    remaining = [fp for ref, fp in components.items() if ref not in ANCHORS]
    remaining.sort(key=lambda fp: -(fp.GetBoundingBox().GetWidth() * fp.GetBoundingBox().GetHeight()))
    for fp in remaining:
        ref = fp.GetReference()
        x0, y0, x1, y1 = REGIONS.get(sheets.get(ref, ""), (67.0, 22.0, 110.0, 98.0))
        placed = False
        y = y0
        while y <= y1 and not placed:
            x = x0
            while x <= x1:
                place_at(fp, x, y, 0)
                box = bbox_mm(fp)
                inside = box[0] >= x0 and box[1] >= y0 and box[2] <= x1 and box[3] <= y1
                if inside and not any(overlaps(box, other) for other in placed_boxes):
                    placed_boxes.append(box)
                    placed_labels.append(ref)
                    placed = True
                    break
                x += 1.0
            y += 1.0
        if not placed:
            raise RuntimeError(f"No collision-free preliminary position for {ref} in {sheets.get(ref)}")

    # Service and isolation labels are generated with the placement so they
    # cannot silently drift away from their connector/test-point groups.
    for text_value, x, y, angle in (
        ("USB-C", 22.0, 27.0, 90), ("SERVICE IN 6-12V", 22.0, 54.0, 90),
        ("BAT+  CELL MID  BAT-", 22.0, 80.0, 90),
        ("PRIMARY / DGND", 88.0, 97.0, 0),
        ("ISOLATED / GND_ISO", 154.0, 97.0, 0),
        ("3V3 A ISO", 163.0, 60.0, 90), ("3V3 D ISO", 163.0, 70.0, 90),
        ("+5 INA", 163.0, 80.0, 90), ("-5 INA", 163.0, 90.0, 90),
        ("ISOLATION BOUNDARY - NO COPPER / VIA / PAD", 122.5, 60.0, 90),
    ):
        add_text(board, text_value, x, y, pcbnew.F_SilkS, 0.9, angle)

    for text_value, x, y in (
        ("THERMAL COPPER + VIAS: BQ25798", 52.0, 69.0),
        ("THERMAL COPPER + VIAS: Q2/Q3", 50.5, 82.5),
        ("THERMAL COPPER: SHUNT", 58.0, 94.0),
        ("THERMAL COPPER + VIAS: TPS2121", 44.0, 28.0),
        ("THERMAL COPPER + VIAS: TPS62132", 78.0, 48.0),
        ("THERMAL COPPER + VIAS: TPS54302", 98.0, 59.0),
        ("THERMAL COPPER IF LOSS REQUIRES: ADM7150", 148.0, 52.0),
    ):
        add_text(board, text_value, x, y, pcbnew.Cmts_User, 0.8, 0, 0.14)

    board.BuildListOfNets()
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(f"Placed {len(components)} footprints; tracks added=0")


if __name__ == "__main__":
    main()
