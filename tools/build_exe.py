"""
Crea dist/CrimeSightRevival.exe (Windows) o dist/CrimeSightRevival (Linux / Steam Deck) con
PyInstaller (lo usan crear_exe.bat y GitHub Actions).

  python tools/build_exe.py            -> version "dev" (no se actualiza sola)
  python tools/build_exe.py 1.0.12     -> version publicada (se actualiza desde GitHub)

El .exe no contiene ningun archivo de Konami: claves e ilustraciones se leen del juego de cada uno.
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
          "upnp", "art", "modpack", "modimage", "modroom", "modinject", "netssl", "certifi", "browserui", "sessions", "app", "core", "i18n", "updater", "version"]
args = ["--noconfirm", "--clean", "--onefile", "--windowed", "--name", "CrimeSightRevival",
        "--paths", "server", "--paths", "tools", "--paths", "launcher",
        "--add-data", f"launcher{os.sep}ui{sep}ui", "--add-data", f"launcher{os.sep}icon.ico{sep}.",
        # plugin opcional de BepInEx (recarga en caliente de mods); BepInEx NO va incluido
        "--add-data", f"plugin{os.sep}CrimeSightRevival.Mods.dll{sep}plugin",
        "--collect-all", "UnityPy",
        # UnityPy carga su modulo de audio al sacar imagenes: sin la libreria de fmod no hay ilustraciones
        "--collect-all", "fmod_toolkit", "--collect-all", "archspec", "--collect-data", "certifi"]
if os.name == "nt":
    # ventana propia con WebView2; en Linux la interfaz se abre en el navegador (browserui.py)
    args += ["--icon", os.path.join("launcher", "icon.ico"), "--collect-all", "webview"]
else:
    args += ["--exclude-module", "webview"]
for h in hidden:
    args += ["--hidden-import", h]


def crypto_binaries():
    """Librerias nativas de pycryptodome. Se meten a mano: el hook de PyInstaller a veces no las
    recoge y entonces el servidor no puede descifrar nada (error 100010 al iniciar sesion)."""
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

# Lo que tiene que llevar el .exe si o si: cifrado (sin esto el servidor no entiende al juego)
# y la libreria de audio de UnityPy (sin ella no se sacan las ilustraciones del juego)
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
        open(vfile, "w", encoding="utf-8").write(src)   # no dejar la version escrita en el codigo
exe = os.path.join("dist", "CrimeSightRevival.exe" if os.name == "nt" else "CrimeSightRevival")
check_exe(exe)
print(f"\nListo: {exe} (version {version})")
