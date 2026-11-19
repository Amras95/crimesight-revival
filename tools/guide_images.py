"""
Genera plugin/CrimeSightRevivalGuideImages.cs: las capturas que salen en algunas paginas de la Guia Revival
(ver GuideText.Image y CrimeSightRevivalGuide.cs). Van dentro del codigo, en base64, para no tener que
anadir recursos al .csproj.
  python tools/guide_images.py
Cada imagen se hace con uno o varios recortes de una captura del repo (uno debajo de otro), se reduce a
WIDTH de ancho y se guarda como JPG.
"""
import base64
import io
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIDTH, QUALITY, GAP = 1000, 82, 6
MODES = "assets/screenshots/launcher.jpg"            # lanzador sin sesion: tarjetas y barra de "Play"
SESSION = "assets/screenshots/launcher_session.jpg"  # lanzador con una sesion abierta
# nombre que usa el plugin -> (captura del repo, [recortes (izq, arriba, der, abajo)])
IMAGES = {
    "launcher_modes": (MODES, [(0, 136, 1260, 712)]),                          # las cuatro tarjetas y la barra de "Play"
    "launcher_bars": (SESSION, [(0, 40, 1259, 132), (0, 545, 1259, 767)]),    # arriba; sesion abierta y barra de abajo
}
OUT = os.path.join(ROOT, "plugin", "CrimeSightRevivalGuideImages.cs")


def build(path, boxes):
    src = Image.open(os.path.join(ROOT, path)).convert("RGB")
    parts = [src.crop(b) for b in boxes]
    w = max(p.width for p in parts)
    h = sum(p.height for p in parts) + GAP * (len(parts) - 1)
    im = Image.new("RGB", (w, h), (12, 12, 20))
    y = 0
    for p in parts:
        im.paste(p, (0, y))
        y += p.height + GAP
    return im


def encode(im):
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=QUALITY, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii"), im.size


def main():
    lines = [
        "// CRIMESIGHT Revival - capturas de la Guia Revival. ARCHIVO GENERADO por tools/guide_images.py: no lo edites a mano.",
        "using System.Collections.Generic;",
        "",
        "namespace CrimeSightRevival.Mods",
        "{",
        "    static class GuideImages",
        "    {",
        "        /// <summary>Nombre -> JPG en base64.</summary>",
        "        public static readonly Dictionary<string, string> Data = new()",
        "        {",
    ]
    for name, (path, boxes) in IMAGES.items():
        b64, size = encode(build(path, boxes))
        lines.append(f"            // {path} ({size[0]}x{size[1]})")
        lines.append(f'            ["{name}"] =')
        chunks = [b64[i:i + 160] for i in range(0, len(b64), 160)]
        for i, c in enumerate(chunks):
            end = "," if i == len(chunks) - 1 else " +"
            lines.append(f'                "{c}"{end}')
    lines += ["        };", "    }", "}", ""]
    with open(OUT, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines))
    print("->", OUT)


if __name__ == "__main__":
    main()
