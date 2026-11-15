"""
CRIMESIGHT Revival - prepara las imagenes de los mods "a lo loco".

La gente no siempre sube un sticker limpio por archivo: a veces es una lamina con muchos
stickers en cuadricula, con fondo de color, o un JPG sin transparencia. Aqui se:

  1. separa la lamina en piezas, cortando por las filas y columnas "vacias" (transparentes o de
     un solo color). Solo se corta si las piezas salen de tamano parecido, para no partir un
     sticker que tenga un adorno suelto (unas "zZZ", una estrella...);
  2. quita el fondo de cada pieza si no tiene transparencia y su borde es de uno o pocos colores
     (rellenando desde el borde, asi el negro de la ropa o los ojos, que esta dentro del
     contorno, no se toca). Una foto o un dibujo con fondo variado se deja tal cual;
  3. borra las motas sueltas que quedan pegadas a los bordes de cada casilla y recorta.

Solo usa Pillow (sin numpy) para no engordar el lanzador.
"""
from collections import deque

SEP_ALPHA = 16          # una fila/columna es separador si todo es casi transparente...
SEP_STD = 10            # ...o casi de un solo color (desviacion por canal)
MIN_PIECE = 40          # pixeles minimos de una pieza a lo largo de un eje
SIMILAR = 0.5           # las piezas tienen que medir al menos la mitad que la mayor
WORK_SIDE = 512         # cada pieza se procesa a este tamano como mucho
COLOR_TOL = 48          # parecido al color de fondo (diferencia maxima por canal)
MAIN_BORDER = 0.5       # el fondo solo se quita si un color ocupa al menos la mitad del borde...
CLEAN_BORDER = 0.8      # ...y los colores dominantes cubren el 80 %


def _has_alpha(img):
    return img.getchannel("A").getextrema()[0] < 200


def _separators(img, axis, alpha):
    """Lista de booleanos: True si la fila (axis=1) o columna (axis=0) es un separador."""
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
    """Recortes (cajas) de cada pieza de la lamina, en orden de lectura. Una sola caja si no es
    una lamina."""
    w, h = img.size
    alpha = _has_alpha(img)
    rows = _split(img, 1, alpha) or [(0, h)]
    out = []
    for y0, y1 in rows:
        band = img.crop((0, y0, w, y1))
        cols = _split(band, 0, alpha) or [(0, w)]
        out += [(x0, y0, x1, y1) for x0, x1 in cols]
    if len(out) > 1:   # un poco de margen (es fondo) para que el dibujo no toque el borde del recorte
        out = [(max(0, a - 4), max(0, b - 4), min(w, c + 4), min(h, d + 4)) for a, b, c, d in out]
    return out


# ------------------------------------------------------------------ fondo
def _border_palette(img):
    """Colores dominantes del borde, o None si el borde es variado (foto, ilustracion completa)."""
    w, h = img.size
    px = img.load()
    border = [px[x, y] for x in range(w) for y in (0, 1, h - 2, h - 1)]
    border += [px[x, y] for y in range(h) for x in (0, 1, w - 2, w - 1)]
    border = [c[:3] for c in border if c[3] > 16]      # lo ya transparente no cuenta
    if len(border) < 16:
        return None
    groups = []                                   # [color, cuenta]
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
    """Quita el fondo de una pieza sin transparencia. Dos intentos:
    1) sticker troquelado (con contorno blanco, lo mas habitual): se rellena desde el borde todo lo
       que NO es blanco, asi el contorno hace de muro y lo de dentro (ropa negra, ojos) se queda;
    2) fondo liso: se quita lo conectado con el borde que sea del color dominante del borde."""
    out = _diecut(img)
    if out is None:
        out = _peel(img)
    return out if out is not None else img


def _flood(img, passable):
    """Pixeles conectados con el borde por los que se puede pasar. Devuelve (mascara, cuantos)."""
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
    # tiene que haber quitado bastante y dejado un dibujo de tamano razonable (si no tenia
    # contorno blanco, el relleno se come casi todo y se descarta)
    if removed < 0.12 * w * h or left < 0.2 * w * h:
        return None
    # si lo que queda es casi todo blanco, lo que se ha quedado es el fondo: descartado
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
    """Quita trocitos sueltos pegados al borde de la casilla (restos de la cuadricula)."""
    w, h = img.size
    m = max(10, round(0.05 * max(w, h)))       # franja del borde de la casilla
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
    """Piezas listas (RGBA, recortadas) a partir de una imagen cualquiera."""
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
