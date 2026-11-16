"""
Actualizacion del lanzador.

Al abrirse, el .exe mira las releases del repositorio oficial en GitHub. Si hay una mas nueva, el
lanzador la ofrece con sus novedades (las notas de cada release que aun no tienes) y el jugador
decide si actualiza o no. Al aceptar: descarga el .exe, comprueba su huella SHA-256 (la que publica
GitHub para cada archivo), se sustituye a si mismo y se vuelve a abrir. Solo funciona en la version
compilada; desde Python no hace nada. Si algo falla (sin internet, GitHub caido...), se sigue con la
version actual.
"""
import hashlib, json, os, re, subprocess, sys, time, urllib.request

from version import ASSET, REPO, VERSION
import netssl
netssl.install()

API = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
MAX_NOTES = 12             # versiones de las que se ensenan las novedades, como mucho
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


def notes(body, lang="en"):
    """Las novedades que cuenta el texto de una release, en el idioma del lanzador si las trae.
    Van entre <!-- changes --> y <!-- /changes --> (las escribe tools/release_notes.py), con un bloque
    "### Español" y otro "### English"; en las releases antiguas, tras "Cambios / Changes:"."""
    body = (body or "").replace("\r\n", "\n")
    m = re.search(r"<!--\s*changes\s*-->(.*?)<!--\s*/changes\s*-->", body, re.S)
    if m:
        text = m.group(1)
    elif "Cambios / Changes:" in body:
        text = body.split("Cambios / Changes:", 1)[1]
    else:
        return ""
    parts = re.split(r"^###[ \t]*(.+?)[ \t]*$", text, flags=re.M)
    if len(parts) > 2:
        secs = {parts[i].strip().lower(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
        text = secs.get("español" if lang == "es" else "english") or secs.get("english") or next(iter(secs.values()))
    lines = [ln.rstrip() for ln in text.split("\n") if not ln.startswith("#")]
    return "\n".join(lines).strip()[:2000]


def pick(releases, current, lang="en"):
    """De la lista de releases de GitHub: {"version", "url", "sha256", "notes": [{"version", "date",
    "text"}]} si hay alguna mas nueva que current (con las novedades de todas las que faltan, la mas
    nueva primero), o None."""
    newer = []
    for rel in releases if isinstance(releases, list) else []:
        v = _parse(rel.get("tag_name"))
        if v and v > current and not rel.get("draft") and not rel.get("prerelease"):
            newer.append((v, rel))
    if not newer:
        return None
    newer.sort(key=lambda x: x[0])
    latest = newer[-1][1]
    asset = next((a for a in latest.get("assets", []) if a.get("name") == ASSET), None)
    if asset is None:
        return None                      # aun se esta compilando para este sistema
    seen, out = set(), []
    for v, rel in newer:                 # de la mas antigua a la mas nueva: lo repetido solo sale una vez
        text = notes(rel.get("body"), lang)
        if text and text not in seen:
            seen.add(text)
            out.append({"version": ".".join(map(str, v)), "date": str(rel.get("published_at") or "")[:10],
                        "text": text})
    digest = (asset.get("digest") or "").split(":", 1)
    return {"version": latest["tag_name"].lstrip("vV"), "url": asset["browser_download_url"],
            "sha256": digest[1] if len(digest) == 2 and digest[0] == "sha256" else None,
            "notes": out[::-1][:MAX_NOTES]}


def check(lang="en"):
    """Devuelve la actualizacion disponible (ver pick) o None."""
    if not frozen():
        return None
    try:
        with urllib.request.urlopen(urllib.request.Request(API, headers=UA), timeout=6) as r:
            releases = json.load(r)
        return pick(releases, _parse(VERSION), lang)
    except Exception:  # noqa: BLE001
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
    if os.name != "nt":
        os.chmod(new, 0o755)
    os.replace(exe, old)        # Windows deja renombrar el .exe en uso (y Linux tambien)
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
