"""Apply the reviewed R3 PowerBox drawing layout to generated KiCad sheets.

The SKiDL generator owns electrical connectivity. This post-processor only
translates complete symbols and their attached labels/wire endpoints, then lays
out the root hierarchy. It is intentionally deterministic so regeneration does
not reintroduce overlapping components.
"""

from __future__ import annotations

import math
import json
import re
import uuid
from collections import defaultdict
from pathlib import Path

from simp_sexp import Sexp


ROOT = Path(__file__).resolve().parent.parent

# Coordinates are KiCad millimetres on each sheet's configured landscape paper.
# Existing symbol rotations are preserved; only origins and attached graphics
# are translated.
LAYOUTS = {
    "R3_power_input_protection1.kicad_sch": {
        "J1": (45, 105), "F1": (72, 105), "Q1": (108, 105),
        "R1": (98, 150), "D2": (132, 150), "D1": (150, 125),
        "C1": (178, 128), "C2": (205, 128), "FB1": (170, 88),
        "C3": (205, 82), "C4": (232, 82),
        "TP1": (50, 58), "TP2": (245, 55),
    },
    "R3_power_battery_management1.kicad_sch": {
        "J8": (45, 120), "J9": (45, 210),
        "TP24": (45, 35), "TP25": (95, 35), "TP26": (145, 35),
        "TP29": (195, 35), "TP30": (245, 35),
        "U9": (200, 140), "Q2": (285, 90), "Q3": (365, 90),
        "R90": (145, 75), "R91": (145, 105), "R92": (115, 155),
        "R98": (275, 135), "R99": (315, 165),
        "R100": (355, 135), "R101": (395, 165),
        "C95": (305, 50), "C96": (385, 50),
        "C97": (235, 185), "C98": (265, 185),
        "C93": (200, 210), "R93": (135, 240),
        "R94": (100, 190), "R95": (270, 215), "C94": (200, 185),
        "R96": (280, 155), "R97": (350, 155),
        "U11": (345, 235),
        "TP27": (295, 35), "TP28": (345, 35),
        "#FLG0601": (285, 245), "#FLG0602": (335, 215),
        "#FLG0603": (365, 215), "#FLG0604": (400, 215),
    },
    "R3_power_charger_powerpath1.kicad_sch": {
        "J7": (35, 145), "F2": (82, 62), "D3": (120, 62),
        "R72": (35, 245), "C70": (75, 245), "C71": (155, 62),
        "U10": (115, 150), "D4": (65, 205),
        "C104": (105, 230), "C105": (140, 230), "C106": (175, 230),
        "R83": (185, 155), "R84": (185, 190), "R85": (185, 120),
        "U7": (245, 135), "R73": (245, 215), "C72": (215, 215),
        "C73": (300, 75), "U8": (395, 155), "L3": (395, 55),
        "C100": (325, 105), "C101": (330, 75),
        "C102": (360, 75), "C103": (390, 90),
        "C74": (345, 55), "C75": (445, 55), "C76": (325, 155),
        "C77": (455, 90), "C78": (495, 90), "C79": (535, 90),
        "C80": (495, 130), "C81": (455, 170), "C82": (500, 170),
        "C83": (545, 170), "C84": (455, 215), "C85": (500, 215),
        "C86": (545, 215), "C87": (455, 260), "C88": (520, 260),
        "C89": (320, 260), "R74": (370, 260), "R75": (420, 260),
        "R76": (250, 305), "R77": (310, 305), "R78": (370, 305),
        "R79": (430, 305), "R80": (250, 350), "D7": (285, 350),
        "R81": (335, 350), "R82": (395, 350), "F3": (520, 320),
        "SW2": (545, 350), "R104": (455, 350), "D5": (500, 350),
        "#FLG0501": (380, 25), "#FLG0502": (450, 25),
        "#FLG0503": (520, 25), "#FLG0504": (205, 25),
        "TP20": (30, 25), "TP21": (75, 25), "TP22": (120, 25),
        "TP23": (165, 25), "TP31": (30, 285), "TP32": (70, 285),
        "TP33": (110, 285), "TP34": (150, 285), "TP35": (190, 285),
        "TP36": (30, 330), "TP37": (75, 330), "TP38": (120, 330),
        "TP39": (165, 330),
    },
    "R3_power_system_power_control1.kicad_sch": {
        "Q4": (135, 105), "R102": (105, 145), "C107": (145, 150),
        "R103": (185, 105), "SW1": (225, 105), "C108": (185, 150),
        "TP40": (245, 55),
    },
    "R3_power_digital_buck1.kicad_sch": {
        "#FLG0101": (62, 55), "#FLG0102": (62, 155),
        "TP3": (105, 52), "TP4": (130, 52),
        "L1": (92, 88), "R10": (92, 120),
        "C12": (65, 105), "C13": (65, 140),
        "U1": (145, 108),
        "C14": (195, 68), "C10": (210, 108), "C11": (210, 145),
    },
    "R3_power_preiso_buck1.kicad_sch": {
        "TP5": (145, 42), "TP6": (265, 42), "TP16": (265, 155),
        "C23": (125, 65), "C24": (155, 65),
        "FB6": (198, 72), "C26": (228, 62), "C27": (252, 62),
        "FB7": (198, 132), "C28": (228, 128), "C29": (252, 128),
        "C22": (68, 105), "L2": (95, 92), "R21": (145, 92),
        "C25": (170, 92), "U2": (105, 122), "R22": (152, 122),
        "C20": (55, 148), "C21": (82, 150),
    },
    "R3_power_isolation1.kicad_sch": {
        "#FLG0201": (48, 50), "U3": (82, 112),
        "C30": (125, 82), "C31": (125, 140),
        "FB2": (165, 82), "FB3": (165, 142),
        "C32": (202, 72), "C33": (230, 72),
        "C34": (202, 145), "C35": (230, 145),
        "TP7": (145, 48), "TP8": (200, 48), "TP9": (245, 48),
        "TP10": (260, 172),
    },
    "R3_power_isolated_ldos1.kicad_sch": {
        "#FLG0301": (48, 115), "#FLG0302": (48, 55),
        "U5": (140, 68), "C50": (90, 68), "C51": (195, 68),
        "TP12": (238, 48),
        "U4": (140, 142), "C40": (72, 125), "R40": (72, 163),
        "C41": (108, 178), "C43": (155, 178), "C44": (195, 158),
        "C42": (205, 120), "TP11": (245, 142),
    },
    "R3_power_ina_isolation1.kicad_sch": {
        "#FLG0401": (48, 50),
        "U6": (92, 110), "FB4": (155, 78), "FB5": (155, 145),
        "C60": (198, 68), "C61": (230, 68),
        "C62": (198, 150), "C63": (230, 150),
        "TP13": (245, 42), "TP14": (245, 178),
    },
    "R3_power_outputs1.kicad_sch": {
        "J2": (52, 72), "J4": (52, 145), "TP15": (105, 145),
        "J3": (145, 110), "J5": (245, 65), "J6": (245, 145),
        "J10": (205, 110), "J11": (320, 110),
        "J12": (105, 225), "J13": (245, 225),
        "R105": (285, 175), "D6": (330, 175),
    },
}

PAPER_SIZES = {
    "R3_power_battery_management1.kicad_sch": "A3",
    "R3_power_charger_powerpath1.kicad_sch": "A2",
    "R3_power_outputs1.kicad_sch": "A3",
}

ROOT_SHEETS = {
    "R3_power_input_protection1.kicad_sch": (25, 35),
    "R3_power_battery_management1.kicad_sch": (110, 35),
    "R3_power_charger_powerpath1.kicad_sch": (195, 35),
    "R3_power_system_power_control1.kicad_sch": (25, 85),
    "R3_power_digital_buck1.kicad_sch": (110, 85),
    "R3_power_preiso_buck1.kicad_sch": (195, 85),
    "R3_power_isolation1.kicad_sch": (25, 135),
    "R3_power_isolated_ldos1.kicad_sch": (110, 135),
    "R3_power_ina_isolation1.kicad_sch": (195, 135),
    "R3_power_outputs1.kicad_sch": (110, 185),
}

NUMBER = r"-?\d+(?:\.\d+)?"


def fmt(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def direct_child(node, name):
    for item in node[1:]:
        if isinstance(item, list) and item and item[0] == name:
            return item
    return None


def property_value(symbol, name):
    for item in symbol[1:]:
        if isinstance(item, list) and item and item[0] == "property" and item[1] == name:
            return item[2]
    raise KeyError(name)


def blocks(text: str, head: str):
    pattern = re.compile(rf"(?m)^(\t|  )\({re.escape(head)}(?:\s|$)")
    found = []
    for match in pattern.finditer(text):
        start = match.start() + len(match.group(1))
        depth = 0
        quoted = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
                continue
            if char == '"':
                quoted = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    found.append((start, index + 1, text[start:index + 1]))
                    break
    return found


def shift_at_fields(block: str, dx: float, dy: float) -> str:
    pattern = re.compile(rf"(\(at\s+)({NUMBER})(\s+)({NUMBER})")
    return pattern.sub(
        lambda m: f"{m.group(1)}{fmt(float(m.group(2)) + dx)}"
        f"{m.group(3)}{fmt(float(m.group(4)) + dy)}",
        block,
    )


def replace_blocks(text: str, replacements):
    for start, end, replacement in sorted(replacements, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


def read_schematic(path: Path) -> str:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        # SKiDL on Windows may emit the title-block em dash using cp1252.
        text = data.decode("cp1252")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def clean_output(text: str) -> str:
    """Normalize generator whitespace for stable, reviewable Git diffs."""
    text = re.sub(r"(?m)^ +\t", "\t", text)
    text = re.sub(r"(?m)^[ \t]+$", "", text)
    return text.rstrip() + "\n"


def net_map() -> dict[tuple[str, str], str]:
    raw = json.loads((ROOT / "tools" / "logical_nets.json").read_text(encoding="utf-8"))
    return {tuple(key.rsplit(".", 1)): value for key, value in raw.items()}


def pin_position(origin, rotation, mirror, local):
    px, py = float(local[0]), -float(local[1])
    angle = math.radians(-float(rotation))
    rx = px * math.cos(angle) - py * math.sin(angle)
    ry = px * math.sin(angle) + py * math.cos(angle)
    if mirror == "x":
        ry = -ry
    elif mirror == "y":
        rx = -rx
    return round(float(origin[0]) + rx, 3), round(float(origin[1]) + ry, 3)


def arrange_child(path: Path, target_positions, connectivity):
    text = read_schematic(path)
    if path.name in PAPER_SIZES:
        text = re.sub(
            r'\(paper\s+"[^"]+"\)',
            f'(paper "{PAPER_SIZES[path.name]}")',
            text,
            count=1,
        )
    parsed = Sexp(text)
    library_pins = {}
    for lib in parsed.search("/kicad_sch/lib_symbols/symbol"):
        pins = {}
        for pin in lib.search("/symbol/symbol/pin"):
            number = str(direct_child(pin, "number")[1])
            pins[number] = direct_child(pin, "at")[1:3]
        library_pins[lib[1]] = pins

    pin_moves = defaultdict(list)
    arranged_pins = []
    symbol_replacements = []
    seen = set()
    raw_symbols = {re.search(r'\(property "Reference" "([^"]+)"', raw).group(1): (start, end, raw)
                   for start, end, raw in blocks(text, "symbol")}

    for symbol in parsed.search("/kicad_sch/symbol"):
        ref = property_value(symbol, "Reference")
        if ref not in target_positions:
            continue
        seen.add(ref)
        at = direct_child(symbol, "at")
        old = (float(at[1]), float(at[2]))
        rotation = float(at[3]) if len(at) > 3 else 0.0
        mirror_node = direct_child(symbol, "mirror")
        mirror = mirror_node[1] if mirror_node else None
        new = target_positions[ref]
        delta = (new[0] - old[0], new[1] - old[1])
        lib_id = direct_child(symbol, "lib_id")[1]
        for number, local in library_pins[lib_id].items():
            old_pin = pin_position(old, rotation, mirror, local)
            net = connectivity.get((ref, number))
            pin_moves[old_pin].append((net, delta, ref, number))
            new_pin = pin_position(new, rotation, mirror, local)
            arranged_pins.append((ref, number, net, new_pin, new))
        start, end, raw = raw_symbols[ref]
        moved_symbol = shift_at_fields(raw, *delta).replace(
            "(size 1.27 1.27)", "(size 0.9 0.9)"
        )
        # SKiDL 2.3 does not serialize Part.dnp into the KiCad instance flag.
        # Preserve the approved Rev.A assembly options in PDF/BOM/parity checks.
        if ref in {"U11", "J5", "J6", "J12", "J13"}:
            moved_symbol = moved_symbol.replace("(dnp no)", "(dnp yes)")
        symbol_replacements.append((start, end, moved_symbol))

    missing = set(target_positions) - seen
    if missing:
        raise RuntimeError(f"Missing symbols in {path.name}: {sorted(missing)}")
    text = replace_blocks(text, symbol_replacements)

    # Replace the auto-router's coincident pins and short wire fragments with an
    # explicit label on every connected pin. Labels stay directly on the pin:
    # generated symbols can contain stacked/off-grid pins, and adding graphical
    # wire stubs to those pins can accidentally merge unrelated nets.
    remove = []
    for kind in ("global_label", "wire", "no_connect"):
        remove.extend((start, end, "") for start, end, _ in blocks(text, kind))
    text = replace_blocks(text, remove)

    generated = []
    for ref, number, net, point, origin in arranged_pins:
        token = f"{path.name}:{ref}:{number}:{net}"
        item_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, token))
        if net in (None, "__NOCONNECT"):
            generated.append(
                f'\t(no_connect\n\t\t(at {fmt(point[0])} {fmt(point[1])})\n'
                f'\t\t(uuid "{item_uuid}")\n\t)\n'
            )
            continue
        dx, dy = point[0] - origin[0], point[1] - origin[1]
        if abs(dx) >= abs(dy):
            angle = 180 if dx < 0 else 0
        else:
            angle = 270 if dy < 0 else 90
        justify = "left" if angle in (0, 90) else "right"
        generated.append(
            f'\t(global_label "{net}"\n'
            f'\t\t(shape bidirectional)\n'
            f'\t\t(at {fmt(point[0])} {fmt(point[1])} {angle})\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 0.8 0.8)\n\t\t\t)\n'
            f'\t\t\t(justify {justify})\n\t\t)\n'
            f'\t\t(uuid "{item_uuid}")\n\t)\n'
        )
    insertion = blocks(text, "symbol")[0][0]
    text = text[:insertion] + "".join(generated) + text[insertion:]
    path.write_text(clean_output(text), encoding="utf-8", newline="\n")


def arrange_root():
    path = ROOT / "R3_power.kicad_sch"
    text = read_schematic(path)
    replacements = []
    for start, end, raw in blocks(text, "sheet"):
        file_match = re.search(r'\(property "Sheetfile" "([^"]+)"', raw)
        if not file_match or file_match.group(1) not in ROOT_SHEETS:
            continue
        at_match = re.search(rf"\(at\s+({NUMBER})\s+({NUMBER})", raw)
        old = (float(at_match.group(1)), float(at_match.group(2)))
        new = ROOT_SHEETS[file_match.group(1)]
        moved = shift_at_fields(raw, new[0] - old[0], new[1] - old[1])
        moved = re.sub(r"\(size\s+[^\s)]+\s+[^\s)]+\)", "(size 50 25)", moved, count=1)
        replacements.append((start, end, moved))
    path.write_text(
        clean_output(replace_blocks(text, replacements)),
        encoding="utf-8",
        newline="\n",
    )


def main():
    connectivity = net_map()
    for filename, positions in LAYOUTS.items():
        arrange_child(ROOT / filename, positions, connectivity)
    arrange_root()
    print(f"Arranged {len(LAYOUTS)} child sheets and the root hierarchy.")


if __name__ == "__main__":
    main()
