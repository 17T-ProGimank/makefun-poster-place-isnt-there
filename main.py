#!/usr/bin/env python3
"""VELMORA - a travel poster for a place that isn't there.

Draws a 1024x1024 vintage-style travel poster for Velmora, a city that
rises with the tide: a striped lighthouse (the Tide Spire) on a rocky
islet, stilt houses floating on a glowing lagoon, twin moons over a dusk
sea. Pure Python 3 standard library only (no network, no fonts, no PIL):
the rasterizer, the PNG encoder and the display lettering are all in
this file. Output is fully deterministic - same bytes on every run.

Writes /output/entry.png (falls back to ./entry.png when /output is
not writable, e.g. a local run).
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
INDIGO = (27, 20, 64)      # top of the dusk sky
VIOLET = (107, 58, 122)    # middle sky
CORAL = (240, 138, 92)     # sunset band at the horizon
PEACH = (247, 178, 103)    # warm glow near the sun-set
CREAM = (253, 243, 216)    # moonlight / title type
GOLD = (255, 201, 120)     # lit windows, moon reflection
TEAL = (20, 66, 78)        # sea at the horizon
DEEPSEA = (8, 32, 46)      # sea at the bottom
ROCK = (22, 18, 40)        # islet and headland silhouettes
RIDGE = (58, 38, 84)       # distant ridge
RIDGE2 = (44, 30, 68)      # nearer ridge
TOWER_CREAM = (250, 235, 205)
TOWER_CORAL = (226, 110, 74)
LAMP = (255, 214, 130)

# ---------------------------------------------------------------- canvas
# rows of RGB bytes; every primitive paints into this.
canvas = [bytearray(W * 3) for _ in range(H)]


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def set_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        row = canvas[y]
        i = x * 3
        row[i], row[i + 1], row[i + 2] = c


def blend_px(x, y, c, a):
    """Paint colour c over the pixel with alpha a (0..1)."""
    if 0 <= x < W and 0 <= y < H and a > 0:
        row = canvas[y]
        i = x * 3
        row[i] = int(round(row[i] + (c[0] - row[i]) * a))
        row[i + 1] = int(round(row[i + 1] + (c[1] - row[i + 1]) * a))
        row[i + 2] = int(round(row[i + 2] + (c[2] - row[i + 2]) * a))


def hline(y, x0, x1, c):
    if y < 0 or y >= H:
        return
    x0 = max(0, int(x0))
    x1 = min(W - 1, int(x1))
    if x1 < x0:
        return
    row = canvas[y]
    r, g, b = c
    for x in range(x0, x1 + 1):
        i = x * 3
        row[i], row[i + 1], row[i + 2] = r, g, b


def hline_alpha(y, x0, x1, c, a):
    if y < 0 or y >= H or a <= 0:
        return
    x0 = max(0, int(x0))
    x1 = min(W - 1, int(x1))
    for x in range(x0, x1 + 1):
        blend_px(x, y, c, a)


def fill_rect(x0, y0, x1, y1, c):
    for y in range(max(0, y0), min(H, y1 + 1)):
        hline(y, x0, x1, c)


def fill_circle(cx, cy, r, c):
    r = int(r)
    for dy in range(-r, r + 1):
        y = cy + dy
        if 0 <= y < H:
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            hline(y, cx - dx, cx + dx, c)


def fill_circle_alpha(cx, cy, r, c, a):
    r = int(r)
    for dy in range(-r, r + 1):
        y = cy + dy
        if 0 <= y < H:
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            hline_alpha(y, cx - dx, cx + dx, c, a)


def fill_poly(points, c):
    """Scanline polygon fill (points: list of (x, y))."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    y0, y1 = max(0, int(min(ys))), min(H - 1, int(max(ys)))
    n = len(points)
    for y in range(y0, y1 + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            x0, yy0 = points[i]
            x1, yy1 = points[(i + 1) % n]
            if (yy0 <= yc < yy1) or (yy1 <= yc < yy0):
                t = (yc - yy0) / (yy1 - yy0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            hline(y, xs[k], xs[k + 1], c)


def fill_poly_alpha(points, c, a):
    if len(points) < 3 or a <= 0:
        return
    ys = [p[1] for p in points]
    y0, y1 = max(0, int(min(ys))), min(H - 1, int(max(ys)))
    n = len(points)
    for y in range(y0, y1 + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            x0, yy0 = points[i]
            x1, yy1 = points[(i + 1) % n]
            if (yy0 <= yc < yy1) or (yy1 <= yc < yy0):
                t = (yc - yy0) / (yy1 - yy0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            hline_alpha(y, xs[k], xs[k + 1], c, a)


def disc(cx, cy, r, c):
    """Filled disc used as the brush for thick strokes."""
    fill_circle(int(round(cx)), int(round(cy)), int(math.ceil(r)), c)


def thick_line(x0, y0, x1, y1, w, c):
    """Line with round caps, drawn by stamping discs along it."""
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    steps = max(1, int(length * 2))
    r = w / 2.0
    for s in range(steps + 1):
        t = s / steps
        disc(x0 + dx * t, y0 + dy * t, r, c)


# ------------------------------------------------- deterministic pseudo-random
_seed = [123456789]


def rnd():
    _seed[0] = (_seed[0] * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed[0] / 0x7FFFFFFF


# ------------------------------------------------------------- stroke font
# Single-stroke capitals on a 5 x 7 grid (x: 0..4, y: 0..6, y grows down).
FONT = {
    "A": [((0, 6), (2, 0)), ((2, 0), (4, 6)), ((1, 4), (3, 4))],
    "B": [((0, 0), (0, 6)), ((0, 0), (3, 0)), ((3, 0), (4, 1)), ((4, 1), (4, 2)),
          ((4, 2), (3, 3)), ((3, 3), (0, 3)), ((3, 3), (4, 4)), ((4, 4), (4, 5)),
          ((4, 5), (3, 6)), ((3, 6), (0, 6))],
    "C": [((4, 1), (3, 0)), ((3, 0), (1, 0)), ((1, 0), (0, 1)), ((0, 1), (0, 5)),
          ((0, 5), (1, 6)), ((1, 6), (3, 6)), ((3, 6), (4, 5))],
    "D": [((0, 0), (0, 6)), ((0, 0), (3, 0)), ((3, 0), (4, 1)), ((4, 1), (4, 5)),
          ((4, 5), (3, 6)), ((3, 6), (0, 6))],
    "E": [((0, 0), (0, 6)), ((0, 0), (4, 0)), ((0, 3), (3, 3)), ((0, 6), (4, 6))],
    "F": [((0, 0), (0, 6)), ((0, 0), (4, 0)), ((0, 3), (3, 3))],
    "G": [((4, 1), (3, 0)), ((3, 0), (1, 0)), ((1, 0), (0, 1)), ((0, 1), (0, 5)),
          ((0, 5), (1, 6)), ((1, 6), (3, 6)), ((3, 6), (4, 5)), ((4, 5), (4, 3)),
          ((4, 3), (2, 3))],
    "H": [((0, 0), (0, 6)), ((4, 0), (4, 6)), ((0, 3), (4, 3))],
    "I": [((2, 0), (2, 6)), ((0, 0), (4, 0)), ((0, 6), (4, 6))],
    "J": [((4, 0), (4, 5)), ((4, 5), (3, 6)), ((3, 6), (1, 6)), ((1, 6), (0, 5))],
    "K": [((0, 0), (0, 6)), ((4, 0), (0, 3)), ((0, 3), (4, 6))],
    "L": [((0, 0), (0, 6)), ((0, 6), (4, 6))],
    "M": [((0, 6), (0, 0)), ((0, 0), (2, 3)), ((2, 3), (4, 0)), ((4, 0), (4, 6))],
    "N": [((0, 6), (0, 0)), ((0, 0), (4, 6)), ((4, 6), (4, 0))],
    "O": [((1, 0), (3, 0)), ((3, 0), (4, 1)), ((4, 1), (4, 5)), ((4, 5), (3, 6)),
          ((3, 6), (1, 6)), ((1, 6), (0, 5)), ((0, 5), (0, 1)), ((0, 1), (1, 0))],
    "P": [((0, 0), (0, 6)), ((0, 0), (3, 0)), ((3, 0), (4, 1)), ((4, 1), (4, 2)),
          ((4, 2), (3, 3)), ((3, 3), (0, 3))],
    "Q": [((1, 0), (3, 0)), ((3, 0), (4, 1)), ((4, 1), (4, 5)), ((4, 5), (3, 6)),
          ((3, 6), (1, 6)), ((1, 6), (0, 5)), ((0, 5), (0, 1)), ((0, 1), (1, 0)),
          ((3, 4), (4, 6))],
    "R": [((0, 0), (0, 6)), ((0, 0), (3, 0)), ((3, 0), (4, 1)), ((4, 1), (4, 2)),
          ((4, 2), (3, 3)), ((3, 3), (0, 3)), ((2, 3), (4, 6))],
    "S": [((4, 1), (3, 0)), ((3, 0), (1, 0)), ((1, 0), (0, 1)), ((0, 1), (0, 2)),
          ((0, 2), (1, 3)), ((1, 3), (3, 3)), ((3, 3), (4, 4)), ((4, 4), (4, 5)),
          ((4, 5), (3, 6)), ((3, 6), (1, 6)), ((1, 6), (0, 5))],
    "T": [((0, 0), (4, 0)), ((2, 0), (2, 6))],
    "U": [((0, 0), (0, 5)), ((0, 5), (1, 6)), ((1, 6), (3, 6)), ((3, 6), (4, 5)),
          ((4, 5), (4, 0))],
    "V": [((0, 0), (2, 6)), ((2, 6), (4, 0))],
    "W": [((0, 0), (1, 6)), ((1, 6), (2, 3)), ((2, 3), (3, 6)), ((3, 6), (4, 0))],
    "X": [((0, 0), (4, 6)), ((4, 0), (0, 6))],
    "Y": [((0, 0), (2, 3)), ((2, 3), (4, 0)), ((2, 3), (2, 6))],
    "Z": [((0, 0), (4, 0)), ((4, 0), (0, 6)), ((0, 6), (4, 6))],
    " ": [],
    ".": [((2, 6), (2, 6))],
    "-": [((0, 3), (4, 3))],
    "'": [((2, 0), (2, 2))],
    ":": [((2, 1), (2, 1)), ((2, 5), (2, 5))],
    ",": [((2, 5), (1, 7))],
}


def text_width(text, scale, advance=6.4):
    return (len(text) - 1) * advance * scale + 5 * scale


def draw_text(text, cx, y_top, scale, weight, c, advance=6.4, shadow=None):
    """Centred text. weight is the stroke thickness in pixels."""
    total = text_width(text, scale, advance)
    x = cx - total / 2.0
    for ch in text:
        for (p0, p1) in FONT.get(ch.upper(), []):
            x0 = x + p0[0] * scale
            y0 = y_top + p0[1] * scale
            x1 = x + p1[0] * scale
            y1 = y_top + p1[1] * scale
            if shadow is not None:
                thick_line(x0 + shadow[0], y0 + shadow[1],
                           x1 + shadow[0], y1 + shadow[1], weight, shadow[2])
            thick_line(x0, y0, x1, y1, weight, c)
        x += advance * scale


# ------------------------------------------------------------------ scene
def draw():
    # ---- sky: vertical gradient, indigo -> violet -> coral at horizon
    horizon = 640
    for y in range(0, horizon):
        if y < 300:
            c = lerp(INDIGO, VIOLET, y / 300.0)
        else:
            c = lerp(VIOLET, CORAL, (y - 300) / 340.0)
        hline(y, 0, W - 1, c)
    # warm peach wash hugging the horizon
    for y in range(540, horizon):
        a = 0.45 * (y - 540) / 100.0
        row = canvas[y]
        for x in range(W):
            i = x * 3
            row[i] = int(round(row[i] + (PEACH[0] - row[i]) * a))
            row[i + 1] = int(round(row[i + 1] + (PEACH[1] - row[i + 1]) * a))
            row[i + 2] = int(round(row[i + 2] + (PEACH[2] - row[i + 2]) * a))

    # ---- stars (fixed seed, so deterministic)
    for _ in range(150):
        sx, sy = int(rnd() * W), int(rnd() * 520)
        if math.hypot(sx - 150, sy - 300) < 92 or math.hypot(sx - 880, sy - 250) < 42:
            continue
        b = 0.35 + 0.65 * rnd()
        col = (int(253 * b), int(243 * b), int(216 * b))
        r = 2 if rnd() < 0.12 else 1
        fill_circle(sx, sy, r, col)

    # ---- twin moons, kept clear of the title band (y < 210) so the
    # place name stays legible: the big moon hangs low over the sea on
    # the left, the small one high on the right.
    fill_circle_alpha(150, 300, 90, CREAM, 0.10)
    fill_circle_alpha(150, 300, 76, CREAM, 0.12)
    fill_circle(150, 300, 62, CREAM)
    fill_circle(128, 283, 11, (238, 226, 196))
    fill_circle(166, 320, 7, (238, 226, 196))
    fill_circle(152, 273, 5, (240, 230, 200))
    fill_circle(880, 250, 26, (250, 238, 210))
    fill_circle_alpha(880, 250, 35, CREAM, 0.12)

    # ---- birds
    for bx, by, s in [(330, 290, 14), (385, 320, 11), (640, 280, 13), (950, 340, 10)]:
        thick_line(bx - s, by, bx, by - s * 0.45, 3, ROCK)
        thick_line(bx, by - s * 0.45, bx + s, by, 3, ROCK)

    # ---- distant ridges (layered silhouettes)
    fill_poly([(0, 640), (0, 585), (90, 560), (190, 600), (300, 545), (430, 600),
               (540, 560), (660, 605), (790, 555), (900, 600), (1024, 570),
               (1024, 640)], RIDGE)
    fill_poly([(0, 640), (0, 610), (120, 585), (260, 620), (380, 590), (520, 625),
               (660, 592), (820, 622), (950, 595), (1024, 615), (1024, 640)], RIDGE2)

    # ---- sea: gradient teal -> deep navy, with horizon glow
    for y in range(horizon, H):
        c = lerp(TEAL, DEEPSEA, (y - horizon) / (H - horizon))
        hline(y, 0, W - 1, c)
    hline(horizon, 0, W - 1, PEACH)

    # ---- moon reflection: widening gold dashes under the big moon
    # (left side, clear of the stilt village on the right)
    for k, y in enumerate(range(652, 1000, 9)):
        half = 24 + k * 3.0
        wob = 8 * math.sin(k * 0.9)
        a = max(0.05, 0.5 - k * 0.022)
        hline_alpha(y, 150 - half + wob, 150 + half + wob, GOLD, a)
        hline_alpha(y + 1, 150 - half * 0.7, 150 + half * 0.7, GOLD, a * 0.6)

    # ---- sea shimmer: thin lighter strokes
    for _ in range(90):
        y = 660 + int(rnd() * 330)
        x = int(rnd() * W)
        ln = 14 + int(rnd() * 60)
        a = 0.10 + 0.25 * rnd()
        hline_alpha(y, x, x + ln, (120, 190, 200), a)

    # ---- lighthouse beams (behind the tower glow, in front of the sea)
    fill_poly_alpha([(512, 470), (1024, 350), (1024, 590)], GOLD, 0.10)
    fill_poly_alpha([(512, 470), (0, 400), (0, 545)], GOLD, 0.08)

    # ---- rocky islet
    fill_poly([(398, 830), (428, 748), (468, 728), (548, 728), (592, 752),
               (622, 830), (398, 830)], ROCK)
    fill_poly([(428, 748), (468, 728), (500, 736), (470, 770), (436, 772)], (34, 28, 58))

    # ---- the Tide Spire: striped lighthouse
    # tower tapers from base (478..546, y=730) to top (494..530, y=468)
    def tower_x(y, side):
        # side 0 = left edge, 1 = right edge; linear taper
        t = (730 - y) / (730 - 468.0)
        left = 478 + (494 - 478) * t
        right = 546 + (530 - 546) * t
        return left if side == 0 else right

    bands = [(730, 668, TOWER_CREAM), (668, 612, TOWER_CORAL),
             (612, 556, TOWER_CREAM), (556, 500, TOWER_CORAL),
             (500, 468, TOWER_CREAM)]
    for yb, yt, col in bands:
        fill_poly([(tower_x(yb, 0), yb), (tower_x(yb, 1), yb),
                   (tower_x(yt, 1), yt), (tower_x(yt, 0), yt)], col)
    # gallery + lamp room + dome: a warm glowing lamp, not a dark block
    fill_rect(488, 452, 536, 468, ROCK)
    fill_rect(496, 422, 528, 452, LAMP)
    fill_rect(500, 428, 524, 448, (255, 232, 160))
    fill_circle(512, 422, 14, ROCK)
    fill_circle(512, 416, 6, LAMP)
    # lamp glow
    fill_circle_alpha(512, 438, 60, GOLD, 0.16)
    fill_circle_alpha(512, 438, 34, GOLD, 0.25)
    # tower windows (warm, lit)
    for wy in (690, 640, 584, 528):
        wx0 = int(tower_x(wy, 0)) + 8
        wx1 = int(tower_x(wy, 1)) - 8
        fill_rect((wx0 + wx1) // 2 - 4, wy - 8, (wx0 + wx1) // 2 + 4, wy + 8, LAMP)

    # ---- floating stilt village (right of the islet)
    houses = [
        # (x, y_base, w, h, roof) roof: 'tri' or 'dome'
        (668, 806, 62, 44, "tri"),
        (742, 822, 54, 38, "dome"),
        (812, 800, 66, 48, "tri"),
        (892, 818, 56, 40, "dome"),
        (958, 806, 48, 36, "tri"),
    ]
    for hx, hy, hw, hh, roof in houses:
        # stilts down into the water
        for sx in (hx + 6, hx + hw - 8):
            hline(sx, hy, hy, ROCK)  # anchor pixel, lines below drawn next
            for yy in range(hy, hy + 34):
                set_px(sx, yy, ROCK)
                set_px(sx + 1, yy, ROCK)
        # body
        fill_rect(hx, hy - hh, hx + hw, hy, (38, 30, 66))
        if roof == "tri":
            fill_poly([(hx - 6, hy - hh), (hx + hw // 2, hy - hh - 26),
                       (hx + hw + 6, hy - hh)], TOWER_CORAL)
        else:
            fill_circle(hx + hw // 2, hy - hh, hw // 2, TOWER_CORAL)
            fill_rect(hx, hy - hh, hx + hw, hy - hh + 4, TOWER_CORAL)
        # lit windows
        for wx in range(hx + 10, hx + hw - 8, 18):
            fill_rect(wx, hy - hh + 12, wx + 8, hy - hh + 24, GOLD)
        # reflection dashes in the water
        for k in range(3):
            ry = hy + 38 + k * 12
            hline_alpha(ry, hx + 8, hx + hw - 8, GOLD, 0.28 - k * 0.08)

    # ---- foreground headland, bottom-left, with two pines
    fill_poly([(0, 1024), (0, 906), (120, 928), (250, 962), (300, 1024)], ROCK)
    for tx, ty, s in [(90, 928, 1.0), (150, 940, 0.75)]:
        for k, (pw, ph) in enumerate([(46, 34), (36, 30), (26, 26)]):
            yy = ty - k * 22 * s
            fill_poly([(tx - pw * s / 2, yy), (tx, yy - ph * s),
                       (tx + pw * s / 2, yy)], (16, 14, 32))
        fill_rect(int(tx - 2 * s), int(ty - 4 * s), int(tx + 2 * s), int(ty + 6 * s),
                  (16, 14, 32))
    # foreground rocks, bottom-right
    fill_poly([(1024, 1024), (1024, 968), (940, 992), (880, 1024)], ROCK)

    # ---- thin gold frame
    for t in range(6):
        hline(t, 0, W - 1, GOLD)
        hline(H - 1 - t, 0, W - 1, GOLD)
        for y in range(H):
            set_px(t, y, GOLD)
            set_px(W - 1 - t, y, GOLD)

    # ---- typography: the invented place's name, set with intent
    draw_text("VELMORA", 512, 64, 19, 13, CREAM,
              shadow=(4, 5, (20, 14, 44)))
    draw_text("WHERE THE TIDE LIFTS THE CITY", 512, 206, 5.2, 4, GOLD,
              advance=6.6)
    draw_text("BEYOND THE LAST CHARTED SEA", 512, 946, 4.4, 3.5, CREAM,
              advance=6.6)


# ------------------------------------------------------------------- PNG
def png_bytes():
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += canvas[y]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def main():
    draw()
    data = png_bytes()
    out = "/output/entry.png"
    try:
        os.makedirs("/output", exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
    except OSError:
        out = "entry.png"
        with open(out, "wb") as f:
            f.write(data)
    print(f"wrote {out} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
