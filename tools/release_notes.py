"""
Texto de la release que publica GitHub Actions. El lanzador ensena sus novedades antes de actualizarse.

  python tools/release_notes.py <sha256 del .exe> <commit anterior> <archivo de salida>

Las novedades salen del primer bloque de CHANGELOG.md (de su primer "## " al siguiente) si ese archivo
cambia en la subida. Si no cambia, del mensaje del commit (variable de entorno COMMIT_MESSAGE): asi un
arreglo rapido no repite las novedades de la version anterior.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD = """Descarga **CrimeSightRevival.exe** y ábrelo. Necesitas tener CRIMESIGHT en tu biblioteca de Steam.
Download **CrimeSightRevival.exe** and run it. You need to own CRIMESIGHT on Steam.

Si ya lo tienes, el lanzador te la ofrecerá al abrirlo. · If you already have it, the launcher will offer it on launch.

SHA-256: `{sha}`

## Cambios / Changes

<!-- changes -->
{changes}
<!-- /changes -->
"""


def top_block(path):
    """El primer bloque del registro de cambios, sin su titulo."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().replace("\r\n", "\n").split("\n")
    except OSError:
        return ""
    out, inside = [], False
    for ln in lines:
        if ln.startswith("## "):
            if inside:
                break
            inside = True
            continue
        if inside:
            out.append(ln)
    return "\n".join(out).strip()


def changelog_changed(before):
    """True / False si se sabe si CHANGELOG.md cambia en esta subida; None si no se puede saber."""
    if not before or not before.strip("0"):
        return None
    try:
        r = subprocess.run(["git", "diff", "--name-only", before, "HEAD", "--", "CHANGELOG.md"],
                           cwd=ROOT, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return bool(r.stdout.strip())


def build(sha, before, message):
    block = top_block(os.path.join(ROOT, "CHANGELOG.md"))
    message = (message or "").strip()
    changed = changelog_changed(before)
    if block and (changed or not message):
        changes = block
    else:
        changes = message or block or "-"
    return HEAD.format(sha=sha, changes=changes)


if __name__ == "__main__":
    sha = sys.argv[1] if len(sys.argv) > 1 else ""
    before = sys.argv[2] if len(sys.argv) > 2 else ""
    out = sys.argv[3] if len(sys.argv) > 3 else "notas.md"
    try:
        text = build(sha, before, os.environ.get("COMMIT_MESSAGE"))
    except Exception as e:  # noqa: BLE001  (una release sin notas es mejor que no publicar)
        text = HEAD.format(sha=sha, changes=(os.environ.get("COMMIT_MESSAGE") or "-").strip())
        print("No pude preparar las notas:", e)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"Notas escritas en {out}")
