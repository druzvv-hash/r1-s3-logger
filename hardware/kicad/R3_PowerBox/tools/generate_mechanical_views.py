"""Generate reproducible annotated pre-routing mechanical reference images."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
W, H = 2400, 1300
BOARD = (180, 150, 2220, 1170)
X0, Y0, X1, Y1 = BOARD


def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def xy(x_mm, y_mm):
    return (
        X0 + (x_mm - 20.0) / 160.0 * (X1 - X0),
        Y0 + (y_mm - 20.0) / 80.0 * (Y1 - Y0),
    )


def dashed(draw, box, color, width=5, dash=18):
    x0, y0, x1, y1 = box
    for a, b in ((x0, x1), (y0, y1)):
        pass
    for x in range(int(x0), int(x1), dash * 2):
        draw.line((x, y0, min(x + dash, x1), y0), fill=color, width=width)
        draw.line((x, y1, min(x + dash, x1), y1), fill=color, width=width)
    for y in range(int(y0), int(y1), dash * 2):
        draw.line((x0, y, x0, min(y + dash, y1)), fill=color, width=width)
        draw.line((x1, y, x1, min(y + dash, y1)), fill=color, width=width)


def base(title, subtitle):
    image = Image.new("RGB", (W, H), "#101820")
    draw = ImageDraw.Draw(image)
    draw.text((80, 35), title, fill="white", font=font(46, True))
    draw.text((82, 92), subtitle, fill="#b9c8d4", font=font(25))
    draw.rectangle(BOARD, fill="#173d2c", outline="#d5e4dc", width=5)
    return image, draw


HOLES = {
    "H1": (35.0, 25.5), "H2": (174.5, 25.5),
    "H3": (25.5, 94.5), "H4": (174.5, 94.5),
    "H5": (115.0, 25.5), "H6": (135.0, 94.5),
}

CONNECTORS = {
    "J7 USB-C": (24.8, 33.0), "J1 SERVICE": (27.0, 55.0),
    "J8 BATTERY": (29.0, 78.0), "J9 NTC": (52.0, 24.0),
    "J2 DIGITAL": (72.0, 24.0), "J4 CONTROL": (96.5, 24.0),
    "J10 TELEMETRY": (55.0, 92.0), "J11 USER": (91.0, 92.0),
    "J3 ISO OUT": (175.0, 81.0),
}


def draw_holes(draw):
    for ref, (x, y) in HOLES.items():
        px, py = xy(x, y)
        r_keep = (4.0 / 160.0) * (X1 - X0)
        r_hole = (1.6 / 160.0) * (X1 - X0)
        draw.ellipse((px-r_keep, py-r_keep, px+r_keep, py+r_keep),
                     outline="#ffd166", width=5)
        draw.ellipse((px-r_hole, py-r_hole, px+r_hole, py+r_hole),
                     fill="#101820", outline="white", width=3)
        tx = px - 155 if x > 165 else px + 20
        ty = py + 34 if y < 50 else py - 74
        draw.text((tx, ty), f"{ref}  ({x:.1f}, {y:.1f})",
                  fill="#ffe39b", font=font(20, True))


def zones_image():
    image, draw = base(
        "R3 PowerBox — zones and isolation",
        "160 x 80 mm · final mechanical pre-routing baseline · 0 tracks / 0 vias",
    )
    zones = [
        (20, 65, "DIRTY", "#6c3f2b"),
        (65, 108, "PRIMARY", "#314d79"),
        (108, 124, "ISOLATION", "#735b24"),
        (124, 180, "CLEAN", "#27604a"),
    ]
    for xa, xb, label, color in zones:
        x_a, _ = xy(xa, 20)
        x_b, _ = xy(xb, 100)
        draw.rectangle((x_a, Y0, x_b, Y1), fill=color)
        draw.text((x_a+20, Y0+20), label, fill="white", font=font(31, True))
    bx0, _ = xy(121, 20)
    bx1, _ = xy(124, 100)
    draw.rectangle((bx0, Y0, bx1, Y1), fill="#ffcc00", outline="white", width=3)
    draw.text((bx0-170, Y0+400), "3.0 mm ALL-LAYER\nNO COPPER / VIA / PAD",
              fill="#111111", font=font(23, True), align="center")
    draw_holes(draw)
    for label, pos in CONNECTORS.items():
        px, py = xy(*pos)
        draw.rectangle((px-10, py-10, px+10, py+10), fill="#78e0ff")
        draw.text((px+14, py-12), label, fill="white", font=font(18, True))
    image.save(REPORTS / "R3_power_zone_isolation_annotated.png")
    image.save(REPORTS / "R3_power_zone_isolation_annotated.pdf", "PDF", resolution=180)


def mechanical_top():
    image, draw = base(
        "R3 PowerBox — future R3 stack reference",
        "Coordinates use KiCad board space; upper-board envelope is reference-only",
    )
    ux0, uy0 = xy(22, 22)
    ux1, uy1 = xy(178, 98)
    dashed(draw, (ux0, uy0, ux1, uy1), "#57d4ff", 5, 20)
    draw.text((ux0+35, uy0+30), "FUTURE R3 UPPER-BOARD ENVELOPE",
              fill="#72ddff", font=font(28, True))
    bx0, _ = xy(121, 20)
    bx1, _ = xy(124, 100)
    draw.rectangle((bx0, Y0, bx1, Y1), fill="#f5b700")
    draw_holes(draw)
    for label, (x, y) in CONNECTORS.items():
        px, py = xy(x, y)
        draw.rectangle((px-14, py-14, px+14, py+14), fill="#ff8c69")
        draw.text((px+18, py-10), label, fill="white", font=font(18))
    for label, x, y, color in (
        ("J12 PRIMARY B2B\n2x8 · origin (106, 28)", 106, 28, "#7db7ff"),
        ("J13 ISOLATED B2B\n2x5 · origin (154, 24)", 154, 24, "#9df0bf"),
    ):
        px, py = xy(x, y)
        draw.rounded_rectangle((px-28, py-28, px+28, py+190), radius=10,
                               outline=color, width=6)
        draw.text((px-95, py+200), label, fill=color, font=font(19, True), align="center")
    draw.text((210, 1190),
              "Recommended stack: 15 mm. Keep side-entry cable/latch corridors open at all board edges.",
              fill="#ffd166", font=font(25, True))
    image.save(REPORTS / "R3_power_mechanical_stack_top.png")


def side_profile():
    image = Image.new("RGB", (2400, 1100), "#101820")
    draw = ImageDraw.Draw(image)
    draw.text((90, 45), "R3 PowerBox — stack side profile", fill="white", font=font(46, True))
    draw.text((92, 105), "15 mm recommended; 12 mm is conditional", fill="#b9c8d4", font=font(27))
    x0, x1 = 250, 2150
    base_y = 820
    upper_y = 400
    draw.rectangle((x0, base_y, x1, base_y+34), fill="#2f865f", outline="white", width=3)
    draw.rectangle((x0, upper_y, x1, upper_y+34), fill="#3772a8", outline="white", width=3)
    for x in (360, 2030):
        draw.rectangle((x-16, upper_y+34, x+16, base_y), fill="#b9c8d4")
        draw.text((x-65, 610), "M3\nSTANDOFF", fill="#111", font=font(18, True), align="center")
    # 15 mm nominal gap: 420 px. 11.1 mm converter: 311 px.
    converter_h = int((11.1 / 15.0) * (base_y - (upper_y + 34)))
    draw.rectangle((970, base_y-converter_h, 1260, base_y), fill="#d8902f", outline="white", width=3)
    draw.text((1000, base_y-converter_h+40), "U3/U6\n11.1 mm", fill="#111", font=font(27, True), align="center")
    draw.line((2250, upper_y+34, 2250, base_y), fill="#ffd166", width=6)
    draw.polygon(((2250, upper_y+34), (2235, upper_y+60), (2265, upper_y+60)), fill="#ffd166")
    draw.polygon(((2250, base_y), (2235, base_y-26), (2265, base_y-26)), fill="#ffd166")
    draw.text((2180, 585), "15 mm\nnominal", fill="#ffd166", font=font(27, True), align="center")
    draw.text((285, 900), "POWERBOX PCB", fill="#78e6b3", font=font(30, True))
    draw.text((285, 320), "FUTURE R3 PCB", fill="#7db7ff", font=font(30, True))
    draw.text((570, 955),
              "15 mm: about 3.9 mm nominal clearance above 11.1 mm RECOM modules.\n"
              "12 mm: only about 0.9 mm nominal; use upper-board cutout/keepout and validate tolerances.",
              fill="white", font=font(25), align="left")
    image.save(REPORTS / "R3_power_mechanical_stack_side.png")


if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    zones_image()
    mechanical_top()
    side_profile()
