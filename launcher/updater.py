"""
Launcher update.

On opening, the .exe checks the official repository's releases on GitHub. If there is a newer one, the
launcher offers it with its release notes (the notes of each release you don't have yet) and the player
decides whether to update. On accepting: it downloads the .exe, checks its SHA-256 fingerprint (the one GitHub
publishes for each file), replaces itself and reopens. It only works in the
compiled version; from Python it does nothing. If something fails (no internet, GitHub down...), it carries on with the
current version.
"""
import hashlib, json, os, re, subprocess, sys, time, urllib.request

from version import ASSET, REPO, VERSION
import netssl
netssl.install()

API = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
MAX_NOTES = 12             # versions whose release notes are shown, at most
UA = {"User-Agent": "CrimeSightRevival-Launcher", "Accept": "application/vnd.github+json"}


def _parse(v):
    try:
        return tuple(int(x) for x in str(v).lstrip("vV").split("."))
    except ValueError:
        return None


def frozen():
    return getattr(sys, "frozen", False) and VERSION != "dev"


def cleanup_old():
    """Deletes the old copy left by a previous update."""
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
    """The release notes in a release's text, in the launcher's language if it has them.
    They go between <!-- changes --> and <!-- /changes --> (tools/release_notes.py writes them), with a
    "### Español" block and an "### English" one; in old releases, after the "Cambios / Changes:" heading."""
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
    """From the GitHub release list: {"version", "url", "sha256", "notes": [{"version", "date",
    "text"}]} if there is one newer than current (with the notes of all the missing ones, the
    newest first), or None."""
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
        return None                      # still being built for this system
    seen, out = set(), []
    for v, rel in newer:                 # oldest to newest: repeated lines only show once
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
    """Returns the available update (see pick) or None."""
    if not frozen():
        return None
    try:
        with urllib.request.urlopen(urllib.request.Request(API, headers=UA), timeout=6) as r:
            releases = json.load(r)
        return pick(releases, _parse(VERSION), lang)
    except Exception:  # noqa: BLE001
        return None


def apply(update, progress=lambda pct: None):
    """Downloads and installs the update and opens the new version. Raises OSError/ValueError if it fails."""
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
    os.replace(exe, old)        # Windows allows renaming the .exe in use (and Linux too)
    os.replace(new, exe)
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([exe], close_fds=True, creationflags=flags, env=fresh_env())
    os._exit(0)


def fresh_env():
    """Environment to open another PyInstaller .exe from this one. Without this, the new one inherits the
    _PYI_* variables and uses the old one's temp folder, which is deleted when it closes: it lacks its libraries
    (for example the crypto ones) and the server doesn't understand the game."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("_PYI_", "_MEIPASS"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env
