"""
Actualizacion automatica del lanzador.

Al abrirse, el .exe mira la ultima release del repositorio oficial en GitHub. Si es mas nueva,
descarga el .exe, comprueba su huella SHA-256 (la que publica GitHub para cada archivo), se
sustituye a si mismo y se vuelve a abrir. Solo funciona en la version compilada; desde Python no hace
nada. Si algo falla (sin internet, GitHub caido...), se sigue usando la version actual.
"""
import hashlib, json, os, subprocess, sys, time, urllib.request

from version import ASSET, REPO, VERSION
import netssl
netssl.install()

API = f"https://api.github.com/repos/{REPO}/releases/latest"
UA = {"User-Agent": "CrimeSightRevival-Launcher", "Accept": "application/vnd.github+json"}


def _parse(v):
    try:
        return tuple(int(x) for x in str(v).lstrip("vV").split("."))
    except ValueError:
        return None


def frozen():
    return getattr(sys, "frozen", False) and VERSION != "dev"


def cleanup_old():
    """Borra la copia vieja que deja una actualizacion anterior."""
    if not frozen():
        return
    old = sys.executable + ".old"
    for _ in range(10):
        try:
            if os.path.exists(old):
                os.remove(old)
            return
        except OSError:
            time.sleep(0.5)


def check():
    """Devuelve {"version", "url", "sha256"} si hay una version nueva, o None."""
    if not frozen():
        return None
    try:
        with urllib.request.urlopen(urllib.request.Request(API, headers=UA), timeout=6) as r:
            rel = json.load(r)
    except Exception:  # noqa: BLE001
        return None
    latest, current = _parse(rel.get("tag_name")), _parse(VERSION)
    if not latest or not current or latest <= current:
        return None
    for a in rel.get("assets", []):
        if a.get("name") == ASSET:
            digest = (a.get("digest") or "").split(":", 1)
            return {"version": rel["tag_name"].lstrip("vV"), "url": a["browser_download_url"],
                    "sha256": digest[1] if len(digest) == 2 and digest[0] == "sha256" else None}
    return None


def apply(update, progress=lambda pct: None):
    """Descarga e instala la actualizacion y abre la version nueva. Lanza OSError/ValueError si falla."""
    exe = sys.executable
    new, old = exe + ".new", exe + ".old"
    req = urllib.request.Request(update["url"], headers={"User-Agent": UA["User-Agent"]})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=30) as r, open(new, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            done += len(chunk)
            if total:
                progress(int(done * 100 / total))
    if update.get("sha256") and h.hexdigest() != update["sha256"].lower():
        os.remove(new)
        raise ValueError("SHA-256")
    if os.path.exists(old):
        os.remove(old)
    os.replace(exe, old)        # Windows deja renombrar el .exe en uso
    os.replace(new, exe)
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([exe], close_fds=True, creationflags=flags, env=fresh_env())
    os._exit(0)


def fresh_env():
    """Entorno para abrir otro .exe de PyInstaller desde este. Sin esto, el nuevo hereda las variables
    _PYI_* y usa la carpeta temporal del viejo, que se borra al cerrarse: le faltan sus librerias
    (por ejemplo las de cifrado) y el servidor no entiende al juego."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("_PYI_", "_MEIPASS"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env
