"""
Ilustraciones del lanzador, sacadas de la instalacion del propio jugador.

El lanzador no lleva ninguna imagen de Konami: la primera vez que se abre las lee de los archivos
del juego que ya tiene el jugador y las guarda en su carpeta de datos (%APPDATA%\\CrimeSightRevival\\art).
"""
import base64, json, os

ART_VERSION = 2
# nombre en el juego -> (archivo, tamano maximo)
WANTED = {
    "Result_ImgDirectingAi_Sherlock": ("sherlock.webp", 760),
    "Result_ImgDirectingAi_Moriarty": ("moriarty.webp", 760),
    "Result_ImgDirectingAi_Watson": ("watson.webp", 760),
    "Result_ImgDirectingAi_Irene": ("irene.webp", 760),
    "cottage_bgmovie_london": ("city.jpg", 1920),
}
SOURCES = ("sharedassets3.assets", "resources.assets")


def art_dir(base):
    d = os.path.join(base, "art")
    os.makedirs(d, exist_ok=True)
    return d


def ready(base):
    d = art_dir(base)
    try:
        with open(os.path.join(d, "version.json")) as f:
            if json.load(f).get("v") != ART_VERSION:
                return False
    except (OSError, ValueError):
        return False
    return all(os.path.isfile(os.path.join(d, fn)) for fn, _ in WANTED.values())


def extract(game_dir, base, log=lambda m: None):
    """Lee las ilustraciones del juego. Devuelve True si las tiene todas."""
    if ready(base):
        return True
    import UnityPy
    d = art_dir(base)
    pending = dict(WANTED)
    for src in SOURCES:
        path = os.path.join(game_dir, "CrimeSight_Data", src)
        if not pending or not os.path.isfile(path):
            continue
        env = UnityPy.load(path)
        for obj in env.objects:
            if obj.type.name != "Texture2D":
                continue
            try:
                tex = obj.read()
            except Exception:  # noqa: BLE001
                continue
            if tex.m_Name not in pending:
                continue
            fn, size = pending.pop(tex.m_Name)
            im = tex.image
            im.thumbnail((size, size))
            out = os.path.join(d, fn)
            if fn.endswith(".jpg"):
                im.convert("RGB").save(out, quality=88)
            else:
                im.convert("RGBA").save(out, "WEBP", quality=86, method=5)
            if not pending:
                break
    with open(os.path.join(d, "version.json"), "w") as f:
        json.dump({"v": ART_VERSION, "missing": sorted(pending)}, f)
    if pending:
        log("No he encontrado algunas ilustraciones del juego; el lanzador funciona igual.")
    return not pending


def data_urls(base):
    """Las ilustraciones como data: URLs para la interfaz web."""
    d = art_dir(base)
    out = {}
    for fn, _ in WANTED.values():
        p = os.path.join(d, fn)
        if os.path.isfile(p):
            mime = "image/jpeg" if fn.endswith(".jpg") else "image/webp"
            with open(p, "rb") as f:
                out[fn.split(".")[0]] = f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    return out
