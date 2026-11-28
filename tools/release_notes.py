"""
Text of the release GitHub Actions publishes. The launcher shows its notes before updating.

  python tools/release_notes.py <sha256 of the .exe> <previous commit> <output file>

The notes come from the first block of CHANGELOG.md (from its first "## " to the next) if that file
changes in the push. If it doesn't, from the commit message (COMMIT_MESSAGE environment variable): that way a
quick fix doesn't repeat the previous version's notes.
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


def split_block(text):
    """(title, body) of the first "## " block of a changelog."""
    out, title = [], None
    for ln in (text or "").replace("\r\n", "\n").split("\n"):
        if ln.startswith("## "):
            if title is not None:
                break
            title = ln[3:].strip()
            continue
        if title is not None:
            out.append(ln)
    return title, "\n".join(out).strip()


def top_block(path):
    """The first block of the changelog, without its title."""
    try:
        with open(path, encoding="utf-8") as f:
            return split_block(f.read())[1]
    except OSError:
        return ""


def old_changelog(before):
    """CHANGELOG.md as it was in the previous commit ("" if unknown)."""
    if not before or not before.strip("0"):
        return ""
    try:
        r = subprocess.run(["git", "show", f"{before}:CHANGELOG.md"], cwd=ROOT, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


def only_new(block, old_block):
    """From the block, only the lines that weren't there (with their "### language" in front). If lines keep being added
    to the same block over several pushes, each update shows only its own and not everything again."""
    old = {ln.strip() for ln in old_block.split("\n") if ln.strip()}
    out, header = [], None
    for ln in block.split("\n"):
        if ln.startswith("### "):
            header = ln
            continue
        if ln.strip() and ln.strip() not in old:
            if header is not None and header not in out:
                out.append(header)
            out.append(ln)
    return "\n".join(out).strip()


def changelog_changed(before):
    """True / False if it is known whether CHANGELOG.md changes in this push; None if it can't be known."""
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
    if block and changed:
        title, _ = split_block(open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read())
        old_title, old_block = split_block(old_changelog(before))
        changes = only_new(block, old_block) if old_title == title else block
        changes = changes or message or block
    elif block and not message:
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
    except Exception as e:  # noqa: BLE001  (a release without notes is better than not publishing)
        text = HEAD.format(sha=sha, changes=(os.environ.get("COMMIT_MESSAGE") or "-").strip())
        print("No pude preparar las notas:", e)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"Notas escritas en {out}")
