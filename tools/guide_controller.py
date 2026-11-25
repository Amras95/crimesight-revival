"""CRIMESIGHT Revival - gamepad drawing for the "Gamepad" page of the Revival Guide.

It starts from the gamepad template (tools/guide_controller_template.png, 1024x768, free from itch.io) and removes
the letters of the triggers, the face buttons and the sticks: the plugin puts on top the icons of the gamepad
in use (Xbox, PlayStation or Switch) and, at the end of each line, what each button does (see CrimeSightRevivalGuide.cs,
PadButtons and PadLines). It also crops 48 px on each side (what is left over outside the gamepad): that way the drawing
comes out bigger on the page. Generates plugin/guide_controller.png (928x768), which is embedded in the DLL.
Usage: python tools/guide_controller.py
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage as nd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "guide_controller_template.png")
OUT = os.path.join(ROOT, "plugin", "guide_controller.png")
CROP = 48                                        # px removed on the left and right (up to the gamepad's edge)
BUTTON = np.array([177, 197, 199, 255])          # bluish grey of the template's buttons
# boxes with letters or arrows that are removed: LT RT, LB RB, face buttons (top, left, right, bottom), LS RS
BOXES = [(240, 70, 345, 140), (680, 70, 785, 140),
         (245, 170, 305, 212), (718, 170, 782, 212),
         (740, 265, 790, 315), (675, 320, 725, 370), (797, 322, 847, 372), (740, 380, 790, 430),
         (360, 425, 426, 491), (599, 425, 665, 491)]

def main():
    im = np.array(Image.open(SRC).convert("RGBA")).astype(np.int32)
    lum = im[..., :3].mean(axis=2)
    lab, _ = nd.label((lum < 50) & (im[..., 3] > 0))      # dark strokes (the letters stay loose from the outline)
    out = im.copy()
    for i, sl in enumerate(nd.find_objects(lab), start=1):
        if sl is None:
            continue
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        for bx0, by0, bx1, by1 in BOXES:
            if x0 >= bx0 and x1 <= bx1 and y0 >= by0 and y1 <= by1 and x1 - x0 < 60:
                m = nd.binary_dilation(lab == i, iterations=3) & ~((lab > 0) & (lab != i))   # with its soft edge
                out[m] = BUTTON
    img = Image.fromarray(out.astype(np.uint8))
    img = img.crop((CROP, 0, img.width - CROP, img.height))
    img.save(OUT, optimize=True)
    print(OUT, os.path.getsize(OUT), "bytes")

if __name__ == "__main__":
    main()
