"""
CRIMESIGHT Revival - prepares "messy" mod images.

People don't always upload one clean sticker per file: sometimes it is a sheet with many
stickers in a grid, with a coloured background, or a JPG without transparency. Here it:

  1. splits the sheet into pieces, cutting along the "empty" rows and columns (transparent or
     a single colour). It only cuts if the pieces come out a similar size, so as not to split a
     sticker that has a loose ornament (some "zZZ", a star...);
  2. removes each piece's background if it has no transparency and its border is one or a few colours
     (flood-filling from the border, so the black of clothes or eyes, which is inside the
     outline, isn't touched). A photo or a drawing with a varied background is left as is;
  3. erases the loose specks stuck to each cell's edges and crops.

It only uses Pillow (no numpy) to avoid bloating the launcher.
"""
from collections import deque

SEP_ALPHA = 16          # a row/column is a separator if everything is almost transparent...
SEP_STD = 10            # ...or almost a single colour (deviation per channel)
MIN_PIECE = 40          # minimum pixels of a piece along an axis
SIMILAR = 0.5           # pieces must measure at least half of the biggest
WORK_SIDE = 512         # each piece is processed at this size at most
COLOR_TOL = 48          # similar to the background colour (maximum difference per channel)
MAIN_BORDER = 0.5       # the background is only removed if one colour takes at least half the border...
CLEAN_BORDER = 0.8      # ...and the dominant colours cover 80 %


def _has_alpha(img):
    return img.getchannel("A").getextrema()[0] < 200


def _separators(img, axis, alpha):
    """List of booleans: True if the row (axis=1) or column (axis=0) is a separator."""
    from PIL import ImageStat
    w, h = img.size
    n = h if axis == 1 else w
    a = img.getchannel("A") if alpha else None
    rgb = img.convert("RGB")
    out = []
    for i in range(n):
        box = (0, i, w, i + 1) if axis == 1 else (i, 0, i + 1, h)
        if alpha and a.crop(box).getextrema()[1] < SEP_ALPHA:
            out.append(True)
            continue
        st = ImageStat.Stat(rgb.crop(box))
        out.append(max(st.stddev) < SEP_STD)
    return out


def _segments(seps):
    segs, start = [], None
    for i, s in enumerate(seps + [True]):
        if not s and start is None:
            start = i
        elif s and start is not None:
            if i - start >= MIN_PIECE:
                segs.append((start, i))
            start = None
    return segs


def _split(img, axis, alpha):
    segs = _segments(_separators(img, axis, alpha))
    if len(segs) < 2:
        return None
    sizes = [b - a for a, b in segs]
    if min(sizes) < SIMILAR * max(sizes):
        return None
    return segs


def cells(img):
    """Crops (boxes) of each piece of the sheet, in reading order. A single box if it isn't
    a sheet."""
    w, h = img.size
    alpha = _has_alpha(img)
    rows = _split(img, 1, alpha) or [(0, h)]
    out = []
    for y0, y1 in rows:
        band = img.crop((0, y0, w, y1))
        cols = _split(band, 0, alpha) or [(0, w)]
        out += [(x0, y0, x1, y1) for x0, x1 in cols]
    if len(out) > 1:   # a bit of margin (it's background) so the drawing doesn't touch the crop's edge
        out = [(max(0, a - 4), max(0, b - 4), min(w, c + 4), min(h, d + 4)) for a, b, c, d in out]
    return out


# ------------------------------------------------------------------ background
def _border_palette(img):
    """Dominant colours of the border, or None if the border is varied (photo, full illustration)."""
    w, h = img.size
    px = img.load()
    border = [px[x, y] for x in range(w) for y in (0, 1, h - 2, h - 1)]
    border += [px[x, y] for y in range(h) for x in (0, 1, w - 2, w - 1)]
    border = [c[:3] for c in border if c[3] > 16]      # what is already transparent doesn't count
    if len(border) < 16:
        return None
    groups = []                                   # [colour, count]
    for c in border:
        for g in groups:
            if max(abs(c[0] - g[0][0]), abs(c[1] - g[0][1]), abs(c[2] - g[0][2])) < COLOR_TOL:
                g[1] += 1
                break
        else:
            if len(groups) < 12:
                groups.append([c, 1])
    groups.sort(key=lambda g: -g[1])
    main = [g for g in groups[:4] if g[1] >= 0.04 * len(border)]
    if not main or main[0][1] < MAIN_BORDER * len(border) or sum(g[1] for g in main) < CLEAN_BORDER * len(border):
        return None
    return [g[0] for g in main]


def _remove_background(img):
    """Removes the background of a piece without transparency. Two attempts:
    1) die-cut sticker (with a white outline, the most common): everything that is NOT white is filled from the border,
       so the outline acts as a wall and the inside (black clothes, eyes) stays;
    2) plain background: what is connected to the border and has the border's dominant colour is removed."""
    out = _diecut(img)
    if out is None:
        out = _peel(img)
    return out if out is not None else img


def _flood(img, passable):
    """Pixels connected to the border that can be passed through. Returns (mask, how many)."""
    w, h = img.size
    px = img.load()
    bg = bytearray(w * h)
    q = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))
    removed = 0
    while q:
        x, y = q.popleft()
        i = y * w + x
        if bg[i]:
            continue
        c = px[x, y]
        if c[3] > 16:
            if not passable(c):
                continue
            removed += 1
        bg[i] = 1
        if x > 0:
            q.append((x - 1, y))
        if x < w - 1:
            q.append((x + 1, y))
        if y > 0:
            q.append((x, y - 1))
        if y < h - 1:
            q.append((x, y + 1))
    return bg, removed


def _apply(img, bg):
    w, h = img.size
    out = img.copy()
    a = out.getchannel("A")
    ap = a.load()
    for i in range(w * h):
        if bg[i]:
            ap[i % w, i // w] = 0
    out.putalpha(a)
    return out


def _is_white(c):
    return min(c[0], c[1], c[2]) > 185 and max(c[0], c[1], c[2]) - min(c[0], c[1], c[2]) < 45


def _diecut(img):
    w, h = img.size
    bg, removed = _flood(img, lambda c: not _is_white(c))
    left = w * h - sum(bg)
    # it must have removed quite a lot and left a drawing of reasonable size (if it had no
    # white outline, the fill eats almost everything and it is discarded)
    if removed < 0.12 * w * h or left < 0.2 * w * h:
        return None
    # if what is left is almost all white, what stayed is the background: discarded
    px = img.load()
    white = sum(1 for i in range(0, w * h, 7) if not bg[i] and _is_white(px[i % w, i // w]))
    kept = sum(1 for i in range(0, w * h, 7) if not bg[i])
    if kept and white > 0.6 * kept:
        return None
    return _apply(img, bg)


def _peel(img):
    pal = _border_palette(img)
    if not pal:
        return None

    def is_bg(c):
        for p in pal:
            if abs(c[0] - p[0]) < COLOR_TOL and abs(c[1] - p[1]) < COLOR_TOL and abs(c[2] - p[2]) < COLOR_TOL:
                return True
        return False
    w, h = img.size
    bg, removed = _flood(img, is_bg)
    if removed < 0.05 * w * h:
        return None
    return _apply(img, bg)


def _drop_specks(img):
    """Removes loose bits stuck to the cell's edge (grid leftovers)."""
    w, h = img.size
    m = max(10, round(0.05 * max(w, h)))       # strip along the cell's edge
    a = img.getchannel("A")
    ap = a.load()
    seen = bytearray(w * h)
    comps = []
    for sy in range(h):
        for sx in range(w):
            if seen[sy * w + sx] or ap[sx, sy] <= 16:
                continue
            q = deque([(sx, sy)])
            seen[sy * w + sx] = 1
            pts, edge = [], False
            while q:
                x, y = q.popleft()
                pts.append((x, y))
                if x < m or y < m or x >= w - m or y >= h - m:
                    edge = True
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
                               (x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and ap[nx, ny] > 16:
                        seen[ny * w + nx] = 1
                        q.append((nx, ny))
            comps.append((pts, edge))
    if len(comps) <= 1:
        return img
    biggest = max(len(p) for p, _ in comps)
    for pts, edge in comps:
        keep = len(pts) >= 0.08 * biggest or (not edge and len(pts) >= 12)
        if not keep:
            for x, y in pts:
                ap[x, y] = 0
    out = img.copy()
    out.putalpha(a)
    return out


def extract(img):
    """Ready pieces (RGBA, cropped) from any image."""
    from PIL import Image
    img = img.convert("RGBA")
    boxes = cells(img)
    alpha = _has_alpha(img)
    pieces = []
    for box in boxes:
        p = img.crop(box)
        k = min(1.0, WORK_SIDE / max(p.size))
        if k < 1.0:
            p = p.resize((max(1, round(p.width * k)), max(1, round(p.height * k))), Image.LANCZOS)
        if not alpha:
            p = _remove_background(p)
        if len(boxes) > 1 or not alpha:
            p = _drop_specks(p)
        bbox = p.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
        if bbox:
            pieces.append(p.crop(bbox))
    return pieces or [img]
