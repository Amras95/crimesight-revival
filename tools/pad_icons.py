"""
Generates plugin/pad_icons.png: the gamepad button icons the plugin shows in the game's help bar
when you play with a gamepad (the game only has keyboard and mouse icons). Our own drawings.
  python tools/pad_icons.py
64x64 cells in a 512x512 sheet; the order of NAMES and COMBOS is the one the plugin uses
(CrimeSightRevivalPad.cs). dpad_up/down/left/right: the D-pad with that direction marked. The last cell (bottom right) stays empty: it is the "nothing" icon.
"""
import os
from PIL import Image, ImageDraw, ImageFont

CELL, COLS, SS = 64, 8, 4                 # SS: drawn 4 times bigger and scaled down (smooth edges)
NAMES = [
    "xbox_a", "xbox_b", "xbox_x", "xbox_y", "xbox_lb", "xbox_rb", "xbox_lt", "xbox_rt",
    "ps_a", "ps_b", "ps_x", "ps_y", "ps_lb", "ps_rb", "ps_lt", "ps_rt",
    "sw_a", "sw_b", "sw_x", "sw_y", "sw_lb", "sw_rb", "sw_lt", "sw_rt",
    "lstick", "rstick", "dpad", "xbox_start", "xbox_back", "ps_start", "ps_back", "sw_start",
    "sw_back", "dpad_up", "dpad_down", "dpad_left", "dpad_right",
]
# Double buttons (turn: LB+RB; zoom: LT+RT), in 128x64 cells from row 5, four per row
COMBOS = [("xbox", "lb", "rb"), ("xbox", "lt", "rt"), ("ps", "lb", "rb"), ("ps", "lt", "rt"),
          ("sw", "lb", "rb"), ("sw", "lt", "rt")]
WHITE, DARK = (240, 240, 236, 255), (34, 36, 44, 255)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(px):
    return ImageFont.truetype(FONT, px)


def text(d, s, size, fill, cx, cy):
    f = font(size)
    b = d.textbbox((0, 0), s, font=f)
    d.text((cx - (b[0] + b[2]) / 2, cy - (b[1] + b[3]) / 2), s, font=f, fill=fill)


def disc(d, S):
    d.ellipse((S * .06, S * .06, S * .94, S * .94), fill=WHITE, outline=DARK, width=int(S * .05))


def face(name, S):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    style, b = name.split("_")
    if b in ("a", "b", "x", "y"):
        disc(d, S)
        if style == "xbox":
            col = {"a": (40, 160, 70), "b": (205, 50, 50), "x": (40, 110, 210), "y": (220, 170, 20)}[b]
            text(d, b.upper(), int(S * .52), col + (255,), S / 2, S / 2)
        elif style == "sw":           # Steam maps the Switch ones by position: bottom B, right A, left Y, top X
            text(d, {"a": "B", "b": "A", "x": "Y", "y": "X"}[b], int(S * .52), DARK, S / 2, S / 2)
        else:                         # PlayStation: bottom cross, right circle, left square, top triangle
            w, c = int(S * .075), S / 2
            if b == "a":
                r = S * .2
                d.line((c - r, c - r, c + r, c + r), fill=(60, 120, 220, 255), width=w)
                d.line((c - r, c + r, c + r, c - r), fill=(60, 120, 220, 255), width=w)
            elif b == "b":
                r = S * .2
                d.ellipse((c - r, c - r, c + r, c + r), outline=(220, 60, 70, 255), width=w)
            elif b == "x":
                r = S * .18
                d.rectangle((c - r, c - r, c + r, c + r), outline=(210, 90, 170, 255), width=w)
            else:
                r = S * .22
                d.polygon([(c, c - r), (c + r * .95, c + r * .65), (c - r * .95, c + r * .65)],
                          outline=(40, 170, 130, 255), width=w)
    elif b in ("lb", "rb", "lt", "rt"):
        label = {"xbox": {"lb": "LB", "rb": "RB", "lt": "LT", "rt": "RT"},
                 "ps": {"lb": "L1", "rb": "R1", "lt": "L2", "rt": "R2"},
                 "sw": {"lb": "L", "rb": "R", "lt": "ZL", "rt": "ZR"}}[style][b]
        if b in ("lb", "rb"):
            box = (S * .04, S * .22, S * .96, S * .78)
            d.rounded_rectangle(box, radius=S * .16, fill=WHITE, outline=DARK, width=int(S * .05))
        else:
            box = (S * .14, S * .06, S * .86, S * .94)
            d.rounded_rectangle(box, radius=S * .2, fill=WHITE, outline=DARK, width=int(S * .05))
        text(d, label, int(S * (.36 if len(label) > 1 else .46)), DARK, S / 2, S / 2)
    elif b in ("start", "back"):
        d.rounded_rectangle((S * .1, S * .2, S * .9, S * .8), radius=S * .28, fill=WHITE, outline=DARK, width=int(S * .05))
        c, w = S / 2, int(S * .055)
        if style == "xbox" and b == "start":        # three stripes
            for k in (-1, 0, 1):
                d.line((c - S * .16, c + k * S * .1, c + S * .16, c + k * S * .1), fill=DARK, width=w)
        elif style == "xbox":                       # two windows
            d.rectangle((c - S * .17, c - S * .12, c + S * .05, c + S * .06), outline=DARK, width=w)
            d.rectangle((c - S * .05, c - S * .04, c + S * .17, c + S * .14), outline=DARK, width=w)
        elif style == "ps":
            text(d, "OPT" if b == "start" else "SHR", int(S * .22), DARK, c, c)
        else:
            text(d, "+" if b == "start" else "−", int(S * .5), DARK, c, c)
    return im


def stick(letter, S):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((S * .04, S * .04, S * .96, S * .96), fill=DARK)
    d.ellipse((S * .16, S * .16, S * .84, S * .84), fill=WHITE)
    text(d, letter, int(S * .42), DARK, S / 2, S / 2)
    return im


def dpad(S):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    t, c = S * .17, S / 2
    for box in ((c - t, S * .06, c + t, S * .94), (S * .06, c - t, S * .94, c + t)):
        d.rounded_rectangle(box, radius=S * .06, fill=WHITE, outline=DARK, width=int(S * .05))
    d.rectangle((c - t + S * .03, c - t + S * .03, c + t - S * .03, c + t - S * .03), fill=WHITE)
    return im


def dpad_dir(S, way):
    """The D-pad with one direction marked (a dark arrow on that arm)."""
    im = dpad(S)
    d = ImageDraw.Draw(im)
    c, a, h = S / 2, S * .11, S * .30          # centre, arrow half-width, distance of its tip
    pts = {"up": [(c, c - h - a), (c - a, c - h + a * .6), (c + a, c - h + a * .6)],
           "down": [(c, c + h + a), (c - a, c + h - a * .6), (c + a, c + h - a * .6)],
           "left": [(c - h - a, c), (c - h + a * .6, c - a), (c - h + a * .6, c + a)],
           "right": [(c + h + a, c), (c + h - a * .6, c - a), (c + h - a * .6, c + a)]}[way]
    d.polygon(pts, fill=DARK)
    return im


def main():
    S = CELL * SS
    sheet = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    for i, n in enumerate(NAMES):
        if n == "lstick":
            im = stick("L", S)
        elif n == "rstick":
            im = stick("R", S)
        elif n == "dpad":
            im = dpad(S)
        elif n.startswith("dpad_"):
            im = dpad_dir(S, n[5:])
        else:
            im = face(n, S)
        im = im.resize((CELL, CELL), Image.LANCZOS)
        sheet.alpha_composite(im, ((i % COLS) * CELL, (i // COLS) * CELL))
    for k, (st, a, b) in enumerate(COMBOS):
        x, y = (k % 4) * 2 * CELL, (5 + k // 4) * CELL
        for j, btn in enumerate((a, b)):
            im = face(st + "_" + btn, S).resize((CELL, CELL), Image.LANCZOS)
            sheet.alpha_composite(im, (x + j * CELL, y))
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugin", "pad_icons.png")
    sheet.save(out)
    print(out, len(NAMES), "iconos")


if __name__ == "__main__":
    main()
