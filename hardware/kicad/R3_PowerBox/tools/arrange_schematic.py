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

# Coordinates are KiCad millimetres on an A4 landscape sheet. Existing symbol
# rotations are preserved; only origins and attached graphics are translated.
LAYOUTS = {
    "R3_power_input_protection1.kicad_sch": {
        "J1": (45, 105), "F1": (72, 105), "Q1": (108, 105),
        "R1": (98, 150), "D2": (132, 150), "D1": (150, 125),
        "C1": (178, 128), "C2": (205, 128), "FB1": (170, 88),
        "C3": (205, 82), "C4": (232, 82),
        "TP1": (50, 58), "TP2": (245, 55),
    },
    "R3_power_battery_management1.kicad_sch": {
        "J8": (42, 92), "J9": (42, 150),
        "TP24": (42, 48), "TP25": (72, 48), "TP26": (102, 48),
        "TP29": (132, 48), "TP30": (162, 48),
        "U9": (148, 105), "Q2": (205, 78), "Q3": (260, 78),
        "R90": (185, 62), "R91": (185, 95), "R92": (100, 122),
        "C93": (148, 145), "R93": (120, 165),
        "R94": (80, 125), "R95": (190, 150), "C94": (145, 130),
        "R96": (215, 115), "R97": (250, 115),
        "TP27": (202, 48), "TP28": (232, 48),
        "#FLG0601": (220, 155), "#FLG0602": (242, 155),
        "#FLG0603": (264, 155),
    },
    "R3_power_charger_powerpath1.kicad_sch": {
        "J7": (35, 105), "F2": (65, 72), "D3": (65, 122),
        "R70": (55, 150), "R71": (82, 150), "R72": (38, 170),
        "C70": (65, 170), "C71": (90, 120),
        "U7": (112, 88), "R73": (132, 135), "C72": (105, 135),
        "C73": (145, 70), "U8": (190, 108), "L3": (190, 48),
        "C74": (160, 48), "C75": (220, 48), "C76": (150, 105),
        "C77": (242, 58), "C78": (258, 58), "C79": (274, 58),
        "C80": (258, 78), "C81": (230, 105), "C82": (245, 105),
        "C83": (260, 105), "C84": (230, 125), "C85": (245, 125),
        "C86": (260, 125), "C87": (235, 150), "C88": (258, 150),
        "C89": (220, 170), "R74": (245, 170), "R75": (175, 175),
        "R76": (145, 155), "R77": (165, 155), "R78": (185, 155),
        "R79": (205, 155), "R80": (110, 175), "R81": (130, 175),
        "R82": (150, 175), "F3": (275, 145),
        "#FLG0501": (225, 188), "#FLG0502": (250, 188),
        "#FLG0503": (275, 188),
        "TP20": (45, 42), "TP21": (115, 42), "TP22": (235, 42),
        "TP23": (275, 42),
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
        "#FLG0301": (48, 115), "#FLG0302": (48, 55), "#FLG0303": (255, 178),
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
        "J10": (205, 110),
    },
}

ROOT_SHEETS = {
    "R3_power_input_protection1.kicad_sch": (25, 35),
    "R3_power_battery_management1.kicad_sch": (110, 35),
    "R3_power_charger_powerpath1.kicad_sch": (195, 35),
    "R3_power_digital_buck1.kicad_sch": (25, 85),
    "R3_power_preiso_buck1.kicad_sch": (110, 85),
    "R3_power_isolation1.kicad_sch": (195, 85),
    "R3_power_isolated_ldos1.kicad_sch": (25, 135),
    "R3_power_ina_isolation1.kicad_sch": (110, 135),
    "R3_power_outputs1.kicad_sch": (195, 135),
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
        return data.decode("utf-8")
    except UnicodeDecodeError:
        # SKiDL on Windows may emit the title-block em dash using cp1252.
        return data.decode("cp1252")


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
            "(size 1.27 1.27)", "(size 1 1)"
        )
        symbol_replacements.append((start, end, moved_symbol))

    missing = set(target_positions) - seen
    if missing:
        raise RuntimeError(f"Missing symbols in {path.name}: {sorted(missing)}")
    text = replace_blocks(text, symbol_replacements)

    # Replace the auto-router's coincident pins and short wire fragments with an
    # explicit label on every connected pin. This keeps the drawing readable and
    # makes geometry independent of connectivity.
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
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 0.9 0.9)\n\t\t\t)\n'
            f'\t\t\t(justify {justify})\n\t\t)\n'
            f'\t\t(uuid "{item_uuid}")\n\t)\n'
        )
    insertion = blocks(text, "symbol")[0][0]
    text = text[:insertion] + "".join(generated) + text[insertion:]
    path.write_text(text, encoding="utf-8")


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
    path.write_text(replace_blocks(text, replacements), encoding="utf-8")


def main():
    connectivity = net_map()
    for filename, positions in LAYOUTS.items():
        arrange_child(ROOT / filename, positions, connectivity)
    arrange_root()
    print(f"Arranged {len(LAYOUTS)} child sheets and the root hierarchy.")


if __name__ == "__main__":
    main()
