"""
Crea dist/CrimeSightRevival.exe con PyInstaller (lo usan crear_exe.bat y GitHub Actions).

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
          "upnp", "art", "sessions", "app", "core", "i18n", "updater", "version"]
args = ["--noconfirm", "--clean", "--onefile", "--windowed", "--name", "CrimeSightRevival",
        "--paths", "server", "--paths", "tools", "--paths", "launcher",
        "--add-data", f"launcher{os.sep}ui{sep}ui", "--add-data", f"launcher{os.sep}icon.ico{sep}.",
        "--icon", os.path.join("launcher", "icon.ico"),
        "--collect-all", "UnityPy", "--collect-all", "webview"]
for h in hidden:
    args += ["--hidden-import", h]
args.append(os.path.join("launcher", "webapp.py"))

import PyInstaller.__main__  # noqa: E402
try:
    PyInstaller.__main__.run(args)
finally:
    if version != "dev":
        open(vfile, "w", encoding="utf-8").write(src)   # no dejar la version escrita en el codigo
print(f"\nListo: dist{os.sep}CrimeSightRevival.exe (version {version})")
