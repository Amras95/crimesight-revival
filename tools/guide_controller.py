"""CRIMESIGHT Revival - dibujo del mando de la pagina "Mando" de la Guia Revival.

Parte de la plantilla de mando (tools/guide_controller_template.png, 1024x768, gratuita de itch.io) y le quita
las letras de los gatillos, los botones frontales y los sticks: el plugin pone encima los iconos del mando que se
usa (Xbox, PlayStation o Switch) y, al final de cada linea, lo que hace cada boton (ver CrimeSightRevivalGuide.cs,
PadButtons y PadLines). Tambien recorta 48 px por cada lado (lo que sobra fuera del mando): asi el dibujo
sale mas grande en la pagina. Genera plugin/guide_controller.png (928x768), que va incrustado en la DLL.
Uso: python tools/guide_controller.py
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage as nd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "guide_controller_template.png")
OUT = os.path.join(ROOT, "plugin", "guide_controller.png")
CROP = 48                                        # px que se quitan a izquierda y derecha (hasta el borde del mando)
BUTTON = np.array([177, 197, 199, 255])          # gris azulado de los botones de la plantilla
# cajas con letras o flechas que se quitan: LT RT, LB RB, botones frontales (arriba, izquierda, derecha, abajo), LS RS
BOXES = [(240, 70, 345, 140), (680, 70, 785, 140),
         (245, 170, 305, 212), (718, 170, 782, 212),
         (740, 265, 790, 315), (675, 320, 725, 370), (797, 322, 847, 372), (740, 380, 790, 430),
         (360, 425, 426, 491), (599, 425, 665, 491)]

def main():
    im = np.array(Image.open(SRC).convert("RGBA")).astype(np.int32)
    lum = im[..., :3].mean(axis=2)
    lab, _ = nd.label((lum < 50) & (im[..., 3] > 0))      # trazos oscuros (las letras quedan sueltas del contorno)
    out = im.copy()
    for i, sl in enumerate(nd.find_objects(lab), start=1):
        if sl is None:
            continue
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        for bx0, by0, bx1, by1 in BOXES:
            if x0 >= bx0 and x1 <= bx1 and y0 >= by0 and y1 <= by1 and x1 - x0 < 60:
                m = nd.binary_dilation(lab == i, iterations=3) & ~((lab > 0) & (lab != i))   # con su borde suave
                out[m] = BUTTON
    img = Image.fromarray(out.astype(np.uint8))
    img = img.crop((CROP, 0, img.width - CROP, img.height))
    img.save(OUT, optimize=True)
    print(OUT, os.path.getsize(OUT), "bytes")

if __name__ == "__main__":
    main()
