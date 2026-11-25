"""
Creates dist/CrimeSightRevival.exe (Windows) or dist/CrimeSightRevival (Linux / Steam Deck) with
PyInstaller (used by crear_exe.bat and GitHub Actions).

  python tools/build_exe.py            -> "dev" version (doesn't update itself)
  python tools/build_exe.py 1.1.12     -> published version (updates from GitHub)

The .exe contains no Konami file: keys and illustrations are read from each person's game.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
version = sys.argv[1] if len(sys.argv) > 1 else "dev"
vfile = os.path.join("launcher", "version.py")
src = open(vfile, encoding="utf-8").read()
lines = [f'VERSION = "{version}"' if ln.startswith("VERSION =") else ln for ln in src.splitlines()]
open(vfile, "w", encoding="utf-8").write("\n".join(lines) + "\n")

sep = ";" if os.name == "nt" else ":"
hidden = ["server", "match", "ai", "stats", "cscrypto", "extract_keys", "patch_client", "credits_patch",
          "upnp", "art", "modpack", "modimage", "modroom", "matchlog", "profiles", "modinject", "netssl", "certifi", "browserui", "sessions", "app", "core", "i18n", "updater", "version",
          "stagedata", "stagelayout", "stageroom", "fbx2glb", "modelpack", "modelroom"]
args = ["--noconfirm", "--clean", "--onefile", "--windowed", "--name", "CrimeSightRevival",
        "--paths", "server", "--paths", "tools", "--paths", "launcher",
        "--add-data", f"launcher{os.sep}ui{sep}ui", "--add-data", f"launcher{os.sep}icon.ico{sep}.",
        # optional BepInEx plugin (live mod reload); BepInEx is NOT included
        "--add-data", f"plugin{os.sep}CrimeSightRevival.Mods.dll{sep}plugin",
        "--collect-all", "UnityPy",
        # UnityPy loads its audio module when extracting images: without the fmod library there are no illustrations
        "--collect-all", "fmod_toolkit", "--collect-all", "archspec", "--collect-data", "certifi"]
if os.name == "nt":
    # own window with WebView2; on Linux the interface opens in the browser (browserui.py)
    args += ["--icon", os.path.join("launcher", "icon.ico"), "--collect-all", "webview"]
else:
    args += ["--exclude-module", "webview"]
for h in hidden:
    args += ["--hidden-import", h]


def crypto_binaries():
    """pycryptodome native libraries. Added by hand: the PyInstaller hook sometimes doesn't
    collect them and then the server can't decrypt anything (error 100010 when logging in)."""
    import glob
    import Crypto
    base = os.path.dirname(Crypto.__file__)
    ext = "*.pyd" if os.name == "nt" else "*.so"
    out = []
    for f in glob.glob(os.path.join(base, "**", "_" + ext), recursive=True):
        if "SelfTest" not in f:
            out.append((f, os.path.relpath(os.path.dirname(f), os.path.dirname(base))))
    if not out:
        sys.exit("No encuentro las librerias nativas de pycryptodome (pip install pycryptodome)")
    return out


for src_file, dest in crypto_binaries():
    args += ["--add-binary", f"{src_file}{sep}{dest}"]
args.append(os.path.join("launcher", "webapp.py"))

# What the .exe must carry no matter what: crypto (without it the server doesn't understand the game)
# and UnityPy's audio library (without it the game's illustrations can't be extracted)
REQUIRED = ["Crypto/Cipher/_raw_cbc.", "Crypto/Cipher/_raw_aes.", "Crypto/Util/_cpuid_c.", "fmod_toolkit/libfmod/"]


def check_exe(path):
    from PyInstaller.archive.readers import CArchiveReader
    names = {n.replace("\\", "/") for n in CArchiveReader(path).toc}
    missing = [r for r in REQUIRED if not any(n.startswith(r) for n in names)]
    if missing:
        sys.exit(f"ERROR: al ejecutable le faltan {missing}. No se publica.")
    print("Comprobado: el ejecutable lleva las librerias de cifrado y de las ilustraciones.")


import PyInstaller.__main__  # noqa: E402
try:
    PyInstaller.__main__.run(args)
finally:
    if version != "dev":
        open(vfile, "w", encoding="utf-8").write(src)   # don't leave the version written in the code
exe = os.path.join("dist", "CrimeSightRevival.exe" if os.name == "nt" else "CrimeSightRevival")
check_exe(exe)
print(f"\nListo: {exe} (version {version})")
