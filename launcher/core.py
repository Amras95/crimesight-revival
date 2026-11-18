"""
CRIMESIGHT Revival - logica del lanzador (sin interfaz).

- Encuentra Steam, la cuenta activa y la carpeta del juego.
- Saca las claves de la instalacion del propio jugador (no se reparte nada de Konami).
- Apunta el juego al servidor elegido y lo abre desde Steam.
- Arranca el servidor local (jugar solo / ser anfitrion).
- Sincroniza el perfil local con el servidor de un amigo o un servidor propio.

El progreso de cada jugador vive en SU PC (carpeta de datos del lanzador). Los servidores de
otros solo lo tienen prestado: al entrar se sube, al salir se traen las partidas nuevas, y las
dos copias se juntan sumando partidas (cada una tiene un id unico, nunca se duplican).
"""
import json, logging, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request

from i18n import t
import netssl
netssl.install()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = getattr(sys, "_MEIPASS", os.path.dirname(HERE))
for sub in ("server", "tools"):
    p = os.path.join(ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

APP_ID = 1491710
DEFAULT_PORT = 18080
IS_WINDOWS = os.name == "nt"


# ------------------------------------------------------------------ carpetas y configuracion
def app_dir():
    base = os.environ.get("APPDATA") if IS_WINDOWS else os.path.expanduser("~/.local/share")
    d = os.path.join(base or os.path.expanduser("~"), "CrimeSightRevival")
    os.makedirs(d, exist_ok=True)
    return d


def setup_launcher_log():
    """Avisos y errores del lanzador en %APPDATA%\\CrimeSightRevival\\launcher.log (para diagnosticar)."""
    from logging.handlers import RotatingFileHandler
    lg = logging.getLogger("crimesight")
    if any(getattr(h, "_csr_launcher", False) for h in lg.handlers):
        return
    h = RotatingFileHandler(os.path.join(app_dir(), "launcher.log"), maxBytes=512 * 1024, backupCount=1,
                            encoding="utf-8")
    h.setLevel(logging.WARNING)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    h._csr_launcher = True
    lg.addHandler(h)
    if lg.level == logging.NOTSET or lg.level > logging.INFO:
        lg.setLevel(logging.INFO)


def data_dir():
    d = os.path.join(app_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return d


def exe_dir():
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(HERE)


CONFIG_PATH = None


def load_config():
    path = os.path.join(app_dir(), "config.json")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    cfg.setdefault("servers", [])
    cfg.setdefault("port", DEFAULT_PORT)
    return cfg


def save_config(cfg):
    path = os.path.join(app_dir(), "config.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def import_old_data():
    """Si venimos de la version por scripts (server/data/db.json junto al lanzador), copiarla."""
    dst = os.path.join(data_dir(), "db.json")
    if os.path.isfile(dst):
        return None
    for cand in (os.path.join(exe_dir(), "server", "data", "db.json"),
                 os.path.join(os.path.dirname(HERE), "server", "data", "db.json")):
        if os.path.isfile(cand):
            shutil.copy2(cand, dst)
            return cand
    return None


# ------------------------------------------------------------------ Steam
def _reg(path, name):
    if not IS_WINDOWS:
        return None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


LINUX_STEAM = ("~/.local/share/Steam", "~/.steam/steam", "~/.steam/root",          # Steam Deck / nativo
               "~/.var/app/com.valvesoftware.Steam/.local/share/Steam",           # Flatpak
               "~/snap/steam/common/.local/share/Steam")                           # Snap


def steam_path():
    p = _reg(r"Software\Valve\Steam", "SteamPath")
    if p and os.path.isdir(p):
        return os.path.normpath(p)
    cands = (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam") if IS_WINDOWS else LINUX_STEAM
    for cand in cands:
        cand = os.path.realpath(os.path.expanduser(cand))
        if os.path.isdir(os.path.join(cand, "steamapps")) or os.path.isdir(os.path.join(cand, "config")):
            return cand
    return None


def _linux_registry(key):
    """En Linux, Steam guarda en ~/.steam/registry.vdf lo que en Windows va al registro."""
    for p in ("~/.steam/registry.vdf", "~/.var/app/com.valvesoftware.Steam/.steam/registry.vdf"):
        try:
            text = open(os.path.expanduser(p), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        m = re.search(r'"%s"\s+"([^"]*)"' % re.escape(key), text)
        if m:
            return m.group(1)
    return None


def _vdf_pairs(text):
    return re.findall(r'"([^"]+)"\s+"([^"]*)"', text)


def steam_account():
    """(SteamID64, nombre de usuario) de la cuenta con sesion iniciada en Steam."""
    active = _reg(r"Software\Valve\Steam\ActiveProcess", "ActiveUser")
    if not IS_WINDOWS:
        active = _linux_registry("ActiveUser")
        if active == "0":
            active = None
    if active:
        sid = str(76561197960265728 + int(active))
    else:
        sid = None
    name = _reg(r"Software\Valve\Steam", "AutoLoginUser") or ""
    sp = steam_path()
    if sp:
        try:
            text = open(os.path.join(sp, "config", "loginusers.vdf"), encoding="utf-8", errors="ignore").read()
            for block in re.finditer(r'"(\d{17})"\s*\{([^}]*)\}', text):
                fields = dict(_vdf_pairs(block.group(2)))
                if sid == block.group(1) or (not sid and fields.get("MostRecent") == "1"):
                    sid = block.group(1)
                    name = fields.get("PersonaName") or fields.get("AccountName") or name
                    break
        except OSError:
            pass
    return sid, name


def find_game():
    sp = steam_path()
    libs = []
    if sp:
        libs.append(sp)
        try:
            text = open(os.path.join(sp, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="ignore").read()
            libs += [v.replace("\\\\", "\\") for k, v in _vdf_pairs(text) if k == "path"]
        except OSError:
            pass
    for lib in libs:
        manifest = os.path.join(lib, "steamapps", f"appmanifest_{APP_ID}.acf")
        folder = "CrimeSight"
        if os.path.isfile(manifest):
            m = re.search(r'"installdir"\s+"([^"]+)"', open(manifest, encoding="utf-8", errors="ignore").read())
            folder = m.group(1) if m else folder
        game = os.path.join(lib, "steamapps", "common", folder)
        if is_game_dir(game):
            return os.path.normpath(game)
    return None


def game_language(game_dir, steam_id=None):
    """Idioma del lanzador = el del juego. Orden: el que uso el juego la ultima vez que inicio
    sesion en un servidor Revival; el idioma con el que Steam tiene instalado el juego; el idioma
    de Steam. Si no se encuentra el juego: ingles."""
    import i18n
    if not is_game_dir(game_dir):
        return "en"
    if steam_id:
        try:
            import server
            pid, _ = server.derived_ids(3, steam_id)
            lang = i18n.from_game_code((_store().db["users"].get(pid) or {}).get("lang"))
            if lang:
                return lang
        except Exception:  # noqa: BLE001
            pass
    lib = os.path.dirname(os.path.dirname(os.path.normpath(game_dir)))      # .../steamapps
    try:
        text = open(os.path.join(lib, f"appmanifest_{APP_ID}.acf"), encoding="utf-8", errors="ignore").read()
        m = re.search(r'"language"\s+"([^"]+)"', text)
        if m and i18n.from_steam(m.group(1)):
            return i18n.from_steam(m.group(1))
    except OSError:
        pass
    steam_lang = _reg(r"Software\Valve\Steam", "Language") if IS_WINDOWS else _linux_registry("language")
    return i18n.from_steam(steam_lang) or "en"


def is_game_dir(path):
    return bool(path) and os.path.isfile(os.path.join(path, "CrimeSight_Data", "il2cpp_data", "Metadata",
                                                      "global-metadata.dat"))


# ------------------------------------------------------------------ claves y parche
def ensure_keys(game_dir):
    import cscrypto
    path = os.path.join(app_dir(), "keys.json")
    if not os.path.isfile(path):
        import extract_keys
        keys = extract_keys.extract(game_dir)
        with open(path, "w") as f:
            json.dump(keys, f)
    with open(path) as f:
        cscrypto.set_keys(json.load(f))
    os.environ["CSR_KEYS"] = path
    return path


def point_game_to(game_dir, url):
    import patch_client, credits_patch
    if not credits_patch.is_patched(game_dir):
        credits_patch.patch(game_dir)        # linea de creditos en la pantalla de titulo
    return patch_client.patch(game_dir, url)


def restore_game(game_dir):
    import patch_client, credits_patch, modinject
    m = modinject.restore(game_dir)
    if live_mode(game_dir):                 # el juego original no lleva BepInEx
        uninstall_bepinex(game_dir)
        m = True
    a = patch_client.restore(game_dir)
    b = credits_patch.restore(game_dir)
    return a or b or m


def game_url(game_dir):
    import patch_client
    try:
        return patch_client.current_url(game_dir)
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ juego
def launch_game():
    if IS_WINDOWS:
        os.startfile(f"steam://rungameid/{APP_ID}")  # noqa: S606
    elif shutil.which("steam"):
        subprocess.Popen(["steam", f"steam://rungameid/{APP_ID}"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["xdg-open", f"steam://rungameid/{APP_ID}"])


def game_running():
    if not IS_WINDOWS:
        return _linux_game_running()
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CrimeSight.exe", "/NH"], capture_output=True,
                         text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    return "CrimeSight.exe" in out


def _linux_game_running():
    """Con Proton el juego es un proceso de Wine cuya linea de comandos incluye CrimeSight.exe."""
    me = str(os.getpid())
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit() and p != me]
    except OSError:
        return False
    for pid in pids:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().lower()
        except OSError:
            continue
        args = [a.replace(b"\\", b"/").rsplit(b"/", 1)[-1] for a in cmd.split(b"\0") if a]
        if not args or args[0] in (b"sh", b"bash", b"zsh", b"fish", b"dash"):
            continue                       # una terminal que solo menciona el nombre no cuenta
        if b"crimesight.exe" in args:
            return True
    return False


def linux_launch_option_ok():
    """Linux / Steam Deck: BepInEx necesita que Proton cargue su winhttp.dll, lo que se activa con la
    opcion de lanzamiento WINEDLLOVERRIDES="winhttp=n,b" %command% (Propiedades del juego en Steam).
    True si esta puesta, False si no, None si no se puede saber."""
    if IS_WINDOWS:
        return True
    sp, sid = steam_path(), steam_account()[0]
    if not sp or not sid:
        return None
    path = os.path.join(sp, "userdata", str(int(sid) - 76561197960265728), "config", "localconfig.vdf")
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return None
    for m in re.finditer(r'"%d"\s*\{' % APP_ID, text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        block = text[m.end():i]
        lo = re.search(r'"LaunchOptions"\s+"((?:[^"\\]|\\.)*)"', block)
        if lo is not None:
            return "winhttp=n" in lo.group(1).replace(" ", "").lower()
    return False


LINUX_LAUNCH_OPTION = 'WINEDLLOVERRIDES="winhttp=n,b" %command%'


def wait_game(log, start_timeout=180, stop_flag=lambda: False):
    """Espera a que el juego se abra y despues a que se cierre."""
    t0 = time.time()
    while not game_running():
        if stop_flag() or time.time() - t0 > start_timeout:
            log(t("game_not_seen"))
            return False
        time.sleep(2)
    log(t("game_open"))
    while game_running() and not stop_flag():
        time.sleep(3)
    return True


# ------------------------------------------------------------------ servidor local
class LocalServer:
    def __init__(self, public=False, port=DEFAULT_PORT, password="", mods=None, player_mods="ignore", names=None,
                 stages=None):
        os.environ["CSR_DATA_DIR"] = data_dir()
        import server
        if not getattr(LocalServer, "_logging", False):
            server.setup_logging(data_dir())
            LocalServer._logging = True
        self.bg = server.BackgroundServer(host="0.0.0.0" if public else "127.0.0.1", port=port,
                                          password=password, data_dir=data_dir(), mods=mods or [],
                                          owner=mod_owner(), player_mods=player_mods, mod_names=names,
                                          stages=stages or [])
        self.port = port

    def start(self):
        self.bg.start()
        return self

    @property
    def room(self):
        return self.bg.room

    @property
    def stages(self):
        return self.bg.stages

    def stop(self):
        self.bg.stop()


# ------------------------------------------------------------------ mods de apariencia
def mods_dir():
    """Tus mods: una carpeta por mod, con subcarpetas stickers/ y avatars/ llenas de imagenes.
    La primera vez se crea ya preparada: un mod de ejemplo vacio y unas instrucciones."""
    d = os.path.join(app_dir(), "mods")
    first = not os.path.isdir(d)
    os.makedirs(d, exist_ok=True)
    if first:
        new_mod(d)
    readme = os.path.join(d, "README.txt")
    text = t("mods_readme") + "\n" + t("mods_text_hint") + "\n"
    try:
        with open(readme, encoding="utf-8-sig") as f:
            same = f.read() == text
    except OSError:
        same = False
    if not same:
        try:
            with open(readme, "w", encoding="utf-8-sig") as f:   # en Windows, \n ya se escribe como \r\n
                f.write(text)
        except OSError:
            pass
    return d


def new_mod(base=None):
    """Crea una carpeta de mod lista para llenar (stickers/, avatars/ y mod.json). Devuelve la ruta."""
    base = base or mods_dir()
    name, n = t("mods_example"), 1
    while os.path.exists(os.path.join(base, name if n == 1 else f"{name} {n}")):
        n += 1
    folder = os.path.join(base, name if n == 1 else f"{name} {n}")
    for sub in ("stickers", "avatars"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    with open(os.path.join(folder, "mod.json"), "w", encoding="utf-8") as f:
        # nombre vacio = se usa el de la carpeta (asi basta con renombrarla)
        json.dump({"name": "", "author": ""}, f, ensure_ascii=False, indent=2)
    return folder


def temp_mods_dir():
    """Mods descargados de la sala de otro jugador ("<id>+temp"); se borran al terminar."""
    return os.path.join(app_dir(), "mods_temp")


_OWNER = []


def mod_owner():
    """Tu cuenta de Steam: forma parte del id de tus mods (para que no choquen con los de otro)."""
    if not _OWNER:
        try:
            _OWNER.append(steam_account()[0] or "")
        except Exception:  # noqa: BLE001
            _OWNER.append("")
    return _OWNER[0]


def my_mods(cfg):
    import modpack
    return modpack.load_all(mods_dir(), cfg.get("mods_disabled", []), root_name=t("mods_root"), owner=mod_owner())


def mod_folder(name):
    """Ruta de uno de tus mods por su nombre de carpeta ("mods" = la carpeta principal)."""
    base = mods_dir()
    if name == os.path.basename(base):
        return base
    path = os.path.normpath(os.path.join(base, name))
    if os.path.dirname(path) != os.path.normpath(base) or not os.path.isdir(path):
        raise ValueError(t("err_unexpected", err=name))
    return path


def my_room_set(cfg):
    import modpack
    return modpack.room_set([m for m in my_mods(cfg) if m["enabled"]])


def install_mods(game_dir, rs, log=None):
    """Deja en el juego exactamente esos mods (vacio = ninguno). True si hubo que cambiar algo.
    Con el plugin de BepInEx (recarga en caliente) los archivos del juego se quedan originales y
    los mods van a la carpeta que vigila el plugin; sin el, se meten en los archivos del juego."""
    import modinject
    if live_mode(game_dir):
        changed = modinject.restore(game_dir, fix=False)
        return write_live(rs, game_dir) or changed
    clear_live(game_dir)
    return modinject.apply(game_dir, rs, log=log)


# ------------------------------------------------------------------ recarga en caliente (BepInEx, opcional)
BEPINEX_URL = ("https://github.com/BepInEx/BepInEx/releases/download/v6.0.0-pre.2/"
               "BepInEx-Unity.IL2CPP-win-x64-6.0.0-pre.2.zip")
BEPINEX_SHA256 = "616ec7eb06cf11b2a0000e8fcef04d1b12bb58e84a2e0bdac9523234fc193ceb"
BEPINEX_SIZE = 34146254
BEPINEX_FILES = ("winhttp.dll", "doorstop_config.ini", ".doorstop_version", "changelog.txt", "BepInEx", "dotnet")
PLUGIN_NAME = "CrimeSightRevival.Mods.dll"


CURSOR_README = """CRIMESIGHT Revival - cursor propio / custom cursor

ES
Pon aqui tus imagenes PNG (con fondo transparente; mejor de 32x32 o 64x64 pixeles):
  cursor.png    el cursor normal, en los menus y en la partida.
  hotspot.txt   opcional: el punto que hace clic en cursor.png, "x,y" en pixeles desde la esquina de
                arriba a la izquierda (por defecto 0,0, como una flecha). Para una mira centrada de
                32x32, por ejemplo: 16,16
  otros .png    opcional: sustituyen un cursor concreto del juego (moverse, correr, atacar...) si se
                llaman igual que el. Los nombres salen en el registro de BepInEx (LogOutput.log),
                en las lineas "[Cursor] el juego usa el cursor ...".
Hace falta el plugin de BepInEx activado. Solo lo ves tu. Para volver al cursor del juego, vacia la carpeta.

EN
Put your PNG images here (transparent background; 32x32 or 64x64 pixels work best):
  cursor.png    the normal cursor, in menus and in matches.
  hotspot.txt   optional: the point of cursor.png that clicks, "x,y" in pixels from the top-left
                corner (0,0 by default, like an arrow). For a centred 32x32 crosshair, e.g.: 16,16
  other .png    optional: replace a specific game cursor (move, run, attack...) if they have the same
                name. The names show up in the BepInEx log (LogOutput.log), in the lines
                "[Cursor] el juego usa el cursor ...".
It needs the BepInEx plugin turned on. Only you see it. To go back to the game's cursor, empty the folder.
"""


def cursor_dir():
    """Tu cursor propio (cursor.png y, si quieres, los demas cursores del juego)."""
    d = os.path.join(app_dir(), "cursor")
    os.makedirs(d, exist_ok=True)
    readme = os.path.join(d, "README.txt")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as f:
            f.write(CURSOR_README)
    return d


CURSOR_SIZE = 32


def cursor_enabled():
    return load_config().get("cursor_enabled", True)


def cursor_state():
    """Para el lanzador: si tienes cursor propio, si esta activado, su miniatura y su punto de clic."""
    import base64
    d = cursor_dir()
    path = os.path.join(d, "cursor.png")
    st = {"exists": os.path.isfile(path), "enabled": cursor_enabled(), "thumb": "", "hotspot": "tip",
          "extra": sorted(f for f in os.listdir(d) if f.lower().endswith(".png") and f.lower() != "cursor.png")}
    if st["exists"]:
        with open(path, "rb") as f:
            st["thumb"] = "data:image/png;base64," + base64.b64encode(f.read()).decode()
        try:
            from PIL import Image
            w, h = Image.open(path).size
            st["size"] = f"{w}x{h}"
            x, y = [int(float(v)) for v in open(os.path.join(d, "hotspot.txt")).read().replace(";", ",").split(",")[:2]]
            st["hotspot"] = "center" if (x, y) == (w // 2, h // 2) else ("tip" if x <= 2 and y <= 2 else "custom")
        except (OSError, ValueError, ImportError):
            pass
    return st


def cursor_set_image(path):
    """Pone una imagen como cursor: con transparencia, cuadrada y de 32x32 (el tamano que mejor admite
    Windows). Si la imagen no tiene transparencia se le quita el fondo liso."""
    from PIL import Image
    import modimage
    try:
        img = Image.open(path)
        img.load()
    except (OSError, ValueError) as e:
        raise ValueError(t("cursor_bad_image", err=e))
    img = img.convert("RGBA")
    if not modimage._has_alpha(img):
        pieces = modimage.extract(img)
        if pieces:
            img = pieces[0]
    box = img.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
    if box:
        img = img.crop(box)
    side = max(img.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(img, (0, 0))              # pegado arriba a la izquierda: la punta de una flecha
    sq = sq.resize((CURSOR_SIZE, CURSOR_SIZE), Image.LANCZOS)
    d = cursor_dir()
    sq.save(os.path.join(d, "cursor.png"))
    if not os.path.isfile(os.path.join(d, "hotspot.txt")):
        cursor_set_hotspot("tip")


def cursor_set_hotspot(mode):
    """Punto de clic del cursor: "tip" (la esquina de arriba a la izquierda, como una flecha) o "center"."""
    xy = (CURSOR_SIZE // 2, CURSOR_SIZE // 2) if mode == "center" else (0, 0)
    try:
        from PIL import Image
        w, h = Image.open(os.path.join(cursor_dir(), "cursor.png")).size
        if mode == "center":
            xy = (w // 2, h // 2)
    except (OSError, ImportError):
        pass
    with open(os.path.join(cursor_dir(), "hotspot.txt"), "w") as f:
        f.write(f"{xy[0]},{xy[1]}\n")


def cursor_remove():
    d = cursor_dir()
    for f in os.listdir(d):
        if f.lower().endswith(".png") or f.lower() == "hotspot.txt":
            os.remove(os.path.join(d, f))


def install_cursor(game_dir):
    """Copia tu cursor a la carpeta que vigila el plugin (solo lo que cambia). True si hubo cambios.
    Desactivado en el lanzador = la carpeta del plugin se queda vacia (vuelve el cursor del juego)."""
    if not game_dir or not live_mode(game_dir):
        return False
    src, dst = cursor_dir(), os.path.join(live_dir(game_dir), "cursor")
    os.makedirs(dst, exist_ok=True)
    want = {f for f in os.listdir(src) if f.lower().endswith(".png") or f.lower() == "hotspot.txt"}
    if not cursor_enabled():
        want = set()
    changed = False
    for f in os.listdir(dst):
        if f not in want:
            os.remove(os.path.join(dst, f))
            changed = True
    for f in want:
        with open(os.path.join(src, f), "rb") as a:
            data = a.read()
        path = os.path.join(dst, f)
        try:
            with open(path, "rb") as b:
                if b.read() == data:
                    continue
        except OSError:
            pass
        with open(path, "wb") as b:
            b.write(data)
        changed = True
    return changed


def live_dir(game_dir):
    """Carpeta que vigila el plugin: dentro de BepInEx, en la carpeta del juego. Asi sirve igual en
    Windows y con Proton (donde el juego ve otra carpeta de usuario, la de Wine)."""
    return os.path.join(game_dir, "BepInEx", "csr_live")


def bepinex_state(game_dir):
    """installed: BepInEx en la carpeta del juego; plugin: nuestro plugin dentro; ready: ya arranco
    una vez (genero sus archivos, la primera vez tarda un minuto)."""
    if not game_dir:
        return {"installed": False, "plugin": False, "ready": False}
    bep = os.path.join(game_dir, "BepInEx")
    installed = os.path.isfile(os.path.join(game_dir, "winhttp.dll")) and os.path.isdir(os.path.join(bep, "core"))
    plugin = os.path.isfile(os.path.join(bep, "plugins", PLUGIN_NAME))
    ready = os.path.isfile(os.path.join(bep, "interop", "Assembly-CSharp.dll"))
    return {"installed": installed, "plugin": installed and plugin, "ready": ready}


def live_mode(game_dir):
    return bepinex_state(game_dir)["plugin"]


def _plugin_source():
    for base in (getattr(sys, "_MEIPASS", ""), os.path.dirname(HERE)):
        p = os.path.join(base, "plugin", PLUGIN_NAME)
        if base and os.path.isfile(p):
            return p
    raise ValueError(t("bep_no_plugin"))


def install_bepinex(game_dir, progress=None):
    """Descarga BepInEx (el cargador de mods oficial, desde su GitHub) y lo pone en la carpeta del
    juego junto a nuestro plugin. No se incluye con el lanzador: solo si el jugador lo activa."""
    import zipfile
    if not is_game_dir(game_dir):
        raise ValueError(t("err_no_game"))
    cache = os.path.join(app_dir(), "bepinex")
    os.makedirs(cache, exist_ok=True)
    zpath = os.path.join(cache, os.path.basename(BEPINEX_URL))
    if not _sha_ok(zpath):
        _download_bepinex(zpath, progress, cache)
    try:
        with zipfile.ZipFile(zpath) as z:
            for name in z.namelist():
                top = name.split("/")[0]
                if top not in BEPINEX_FILES or ".." in name.replace("\\", "/").split("/"):
                    continue
                z.extract(name, game_dir)
    except zipfile.BadZipFile:
        os.remove(zpath)
        raise ValueError(t("bep_download_failed", err="zip"))
    plugins = os.path.join(game_dir, "BepInEx", "plugins")
    os.makedirs(plugins, exist_ok=True)
    shutil.copy2(_plugin_source(), os.path.join(plugins, PLUGIN_NAME))
    _quiet_bepinex(game_dir)
    import modinject
    modinject.restore(game_dir, fix=False)   # con el plugin, los archivos del juego vuelven a ser los originales
    return True


def _sha_ok(path):
    """El zip es exactamente el oficial (misma huella SHA-256)."""
    if not os.path.isfile(path) or os.path.getsize(path) != BEPINEX_SIZE:
        return False
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == BEPINEX_SHA256


def _download_bepinex(zpath, progress, cache):
    tmp = zpath + ".part"
    err = None
    try:
        with urllib.request.urlopen(BEPINEX_URL, timeout=60) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(int(done * 100 / total))
    except (urllib.error.URLError, OSError) as e:
        err = getattr(e, "reason", e)
    if (err is not None or not _sha_ok(tmp)) and IS_WINDOWS:
        # plan B: el descargador de Windows (consigue solo los certificados que falten)
        if progress:
            progress(0)
        ps = ("$ProgressPreference='SilentlyContinue';"
              "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;"
              f"Invoke-WebRequest -UseBasicParsing -Uri '{BEPINEX_URL}' -OutFile '{tmp}'")
        try:
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           capture_output=True, timeout=600,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.TimeoutExpired) as e:
            err = err or e
    if not _sha_ok(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise ValueError(t("bep_download_failed", err=err or "SHA-256") + " " +
                         t("bep_manual", url=BEPINEX_URL, folder=cache))
    os.replace(tmp, zpath)


def _quiet_bepinex(game_dir):
    """Sin ventana de consola de BepInEx (el registro sigue en BepInEx/LogOutput.log)."""
    cfg = os.path.join(game_dir, "BepInEx", "config", "BepInEx.cfg")
    os.makedirs(os.path.dirname(cfg), exist_ok=True)
    try:
        with open(cfg, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        text = ""
    if "[Logging.Console]" in text:
        text = re.sub(r"(\[Logging\.Console\][^\[]*?Enabled\s*=\s*)\w+", r"\1false", text, flags=re.S)
    else:
        text += "\n[Logging.Console]\nEnabled = false\n"
    with open(cfg, "w", encoding="utf-8") as f:
        f.write(text)


def update_plugin(game_dir):
    """Si el lanzador trae una version nueva del plugin, la copia."""
    if not live_mode(game_dir):
        return False
    src, dst = _plugin_source(), os.path.join(game_dir, "BepInEx", "plugins", PLUGIN_NAME)
    with open(src, "rb") as a, open(dst, "rb") as b:
        if a.read() == b.read():
            return False
    shutil.copy2(src, dst)
    return True


def uninstall_bepinex(game_dir):
    """Quita BepInEx de la carpeta del juego (todo lo que trae su zip)."""
    for name in BEPINEX_FILES:
        p = os.path.join(game_dir, name)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p):
            os.remove(p)
    old = os.path.join(app_dir(), "mods_live")          # sitio antiguo (versiones anteriores)
    if os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)
    return True


def write_live(rs, game_dir):
    """Escribe el conjunto de mods para el plugin: imagenes ya ajustadas + live.json."""
    import modpack, io
    d = live_dir(game_dir)
    os.makedirs(d, exist_ok=True)
    state_path = os.path.join(d, "live.json")
    try:
        with open(state_path, encoding="utf-8") as f:
            if json.load(f).get("hash") == rs["hash"]:
                return False
    except (OSError, ValueError):
        pass
    order = list(modpack.LANGS)
    files, stickers, avatars = set(), [], []

    def put(name, data):
        # solo si cambia: el plugin reutiliza lo que no cambia (si no, se perderia el avatar elegido)
        path = os.path.join(d, name)
        try:
            with open(path, "rb") as f:
                if f.read() == data:
                    return
        except OSError:
            pass
        with open(path, "wb") as f:
            f.write(data)

    for s in rs["stickers"]:
        fg, bg = f"s_{s['type']}.png", f"s_{s['type']}_bg.png"
        put(fg, s["png"])
        buf = io.BytesIO()
        modpack.sticker_background(s["png"]).save(buf, "PNG")
        put(bg, buf.getvalue())
        entry = {"type": s["type"], "png": fg, "bg": bg}
        if s.get("text"):
            g = modpack.text_for_game(s["text"])
            texts = [g[modpack.LANGS[k]] for k in order]
            entry["doc"] = texts
            entry["log"] = ["{player}: " + x for x in texts]
        stickers.append(entry)
        files |= {fg, bg}
    for a in rs["avatars"]:
        fn = f"a_{a['data_id']}.png"
        put(fn, a["png"])
        avatars.append({"id": a["data_id"], "png": fn})
        files.add(fn)
    _write_json(state_path, {"hash": rs["hash"], "stickers": stickers, "avatars": avatars})
    for name in os.listdir(d):                  # imagenes de un conjunto anterior
        if name.endswith(".png") and name not in files:
            try:
                os.remove(os.path.join(d, name))
            except OSError:
                pass
    return True


def clear_live(game_dir):
    d = live_dir(game_dir)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def download_mods(url, password, expected_hash, timeout=60):
    """Descarga el paquete de mods de un servidor y lo guarda como mods temporales."""
    import modpack
    req = urllib.request.Request(url + "/revival/mods", headers={"X-CSR-Password": password or ""})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            got = r.headers.get("X-CSR-Mods", "")
            data = r.read(modpack.MAX_PACK_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise ValueError(t("need_password") if e.code == 403 else t("mods_download_failed", err=e.code))
    except urllib.error.URLError as e:
        raise ValueError(t("mods_download_failed", err=e.reason))
    if expected_hash and got != expected_hash:
        raise ValueError(t("mods_download_failed", err="hash"))
    modpack.clear_temp(temp_mods_dir())
    folders = modpack.unpack(data, temp_mods_dir())
    rs = modpack.room_set([modpack.load_mod(f) for f in folders])
    if expected_hash and rs["hash"] != expected_hash:
        raise ValueError(t("mods_download_failed", err="hash"))
    return rs


def offer_mods(url, password, rs, player, timeout=60):
    """Ofrece tus mods al anfitrion de la sala. Devuelve 'pending', 'accepted', 'known' o 'ignored'."""
    import modpack
    from urllib.parse import quote
    if not rs["hash"]:
        return "none"
    req = urllib.request.Request(url + "/revival/mods/offer", data=modpack.pack(rs), method="POST",
                                 headers={"X-CSR-Password": password or "", "X-CSR-Player": quote(player or "?"),
                                          "Content-Type": "application/zip"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("status", "ignored")
    except urllib.error.HTTPError as e:
        if e.code == 404:          # servidor de una version anterior
            return "ignored"
        raise ValueError(t("mods_download_failed", err=e.code))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ValueError(t("mods_download_failed", err=getattr(e, "reason", e)))


def clear_temp_mods():
    import modpack
    return modpack.clear_temp(temp_mods_dir())


def open_folder(path):
    if IS_WINDOWS:
        os.startfile(path)  # noqa: S606
    else:
        subprocess.Popen(["xdg-open", path])


# ------------------------------------------------------------------ perfiles
def _store():
    os.environ["CSR_DATA_DIR"] = data_dir()
    import server
    return server.Store(os.path.join(data_dir(), "db.json"))


def local_summary(steam_id):
    import server, stats
    if not steam_id:
        return "sin cuenta de Steam detectada"
    st = _store()
    pid, _ = server.derived_ids(3, steam_id)
    u = st.db["users"].get(pid)
    return stats.summary(u) if u else "sin partidas todavia"


def local_record(steam_id):
    """{w, d, l, p}: victorias, empates, derrotas y puntos del registro local."""
    import server, stats
    if not steam_id:
        return {"w": 0, "d": 0, "l": 0, "p": 0}
    pid, _ = server.derived_ids(3, steam_id)
    u = _store().db["users"].get(pid)
    if not u:
        return {"w": 0, "d": 0, "l": 0, "p": 0}
    rec = stats._record(u)
    c = rec["counts"]
    tot = lambda k: sum(int(c.get(str(ids[k]), 0)) for ids in stats.COUNT_IDS.values())
    return {"w": tot("win"), "d": tot("draw"), "l": tot("lose"), "p": int(sum(rec["points"].values()))}


def copy_to_clipboard(text):
    if IS_WINDOWS:
        subprocess.run("clip", input=text.encode("utf-16-le"), check=False,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def normalize_address(addr):
    addr = addr.strip().rstrip("/")
    if not addr:
        raise ValueError(t("err_empty_addr"))
    if not addr.startswith(("http://", "https://")):
        addr = "http://" + addr
    if not re.search(r"://[^/]+:\d+$", addr) and addr.startswith("http://"):
        addr += f":{DEFAULT_PORT}"
    return addr


def server_info(url, timeout=6):
    try:
        with urllib.request.urlopen(url + "/revival/info", timeout=timeout) as r:
            info = json.load(r)
        if info.get("server") != "crimesight-revival":
            raise ValueError(t("err_not_revival"))
        return info
    except urllib.error.URLError as e:
        raise ValueError(t("err_unreachable", url=url, reason=e.reason))


def match_state(url, steam_id, timeout=5):
    """Tu partida en curso en ese servidor ({"role", "match_id", ...} o None). ValueError si no contesta."""
    try:
        with urllib.request.urlopen(f"{url}/revival/match?platform_id={steam_id}", timeout=timeout) as r:
            return json.load(r).get("match")
    except urllib.error.HTTPError as e:
        if e.code == 404:              # anfitrion con una version sin esto
            return None
        raise ValueError(str(e))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ValueError(str(e))


def internet_ok(timeout=5):
    """True si hay internet (para no dar por ganada una partida si el que se ha quedado sin conexion eres tu)."""
    for u in ("https://api.github.com", "https://store.steampowered.com"):
        try:
            with urllib.request.urlopen(u, timeout=timeout):
                return True
        except urllib.error.HTTPError:
            return True
        except (urllib.error.URLError, OSError):
            continue
    return False


def record_host_left(steam_id, state):
    """El anfitrion ha desaparecido a mitad de partida: cuenta como victoria para ti. Devuelve los puntos.
    Lleva el mismo id de partida que en el servidor, asi que nunca se apunta dos veces."""
    import stats
    st = _store()
    user = _local_user(st, steam_id)
    pts = stats.record_match(user, int(state.get("role", 0)), "win", (), state.get("stage", ""),
                             match_id=state.get("match_id") or None, level=state.get("level") or "online")
    st.save()
    return pts


def _local_user(st, steam_id):
    """El perfil local de esa cuenta de Steam (lo crea si aun no ha jugado)."""
    import server
    pid, token = server.derived_ids(3, steam_id)
    user = st.db["users"].setdefault(pid, {"name": "", "progress": 0, "tutorial_step": 0, "config": {},
                                           "created": int(time.time())})
    st.db["accounts"].setdefault(f"3:{steam_id}", {"player_id": pid, "token": token, "platform": 3,
                                                  "platform_id": steam_id, "country": ""})
    return user


def sync_profile(url, steam_id, password=""):
    """Sube el perfil local, recibe el del servidor ya juntado y lo junta aqui. Devuelve el registro."""
    import stats
    st = _store()
    user = _local_user(st, steam_id)
    body = json.dumps({"platform": 3, "platform_id": steam_id, "password": password,
                       "profile": stats.export_profile(user)}).encode()
    req = urllib.request.Request(url + "/revival/sync", body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            remote = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise ValueError(t("err_password"))
        raise ValueError(t("err_sync_rejected", code=e.code))
    except urllib.error.URLError as e:
        raise ValueError(t("err_sync_failed", url=url, reason=e.reason))
    stats.merge_into(user, remote.get("profile") or {})
    st.save()
    return local_record(steam_id)


# ------------------------------------------------------------------ creador de escenarios
STAGE_BASES = ("Stage_Yokn", "Stage_Yokn_v1030", "Stage_Yokn_v1040", "Stage_Yokn_v1050", "Stage_Yokn_v1060")
_stage_cat = {}


def stages_dir():
    """Distribuciones guardadas por el jugador (un .json por escenario)."""
    d = os.path.join(app_dir(), "stages")
    os.makedirs(d, exist_ok=True)
    return d


def stage_cache_dir():
    return os.path.join(app_dir(), "stage_cache")


def stage_catalog(game_dir, progress=None):
    """Piezas de los escenarios, leidas de la copia del juego del jugador (con cache)."""
    import stagedata
    dev = os.environ.get("CSR_STAGE_CATALOG")          # pruebas sin el juego
    if dev:
        with open(dev, encoding="utf-8") as f:
            return json.load(f)
    if not is_game_dir(game_dir):
        raise ValueError(t("err_no_game"))
    key = os.path.abspath(game_dir)
    if key not in _stage_cat:
        try:
            _stage_cat[key] = stagedata.load(game_dir, stage_cache_dir(), progress)
        except stagedata.StageDataError as e:
            raise ValueError(str(e)) from e
    return _stage_cat[key]


def _stage_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")[:40]
    return slug or "escenario"


def stage_hash(layout):
    """Huella de una distribucion (la misma que calcula el servidor)."""
    import stageroom
    return stageroom.layout_hash(layout)


def stage_list(disabled=()):
    """Escenarios guardados. enabled: sale en la lista de escenarios del juego."""
    out, off = [], set(disabled or ())
    for fn in sorted(os.listdir(stages_dir())):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(stages_dir(), fn), encoding="utf-8") as f:
                lay = json.load(f)
            out.append({"id": fn[:-5], "name": lay.get("name") or fn[:-5], "base": lay.get("base"),
                        "rooms": len(lay.get("rooms") or []), "enabled": fn[:-5] not in off})
        except (OSError, ValueError, AttributeError):
            continue
    return out


def stage_load(sid):
    with open(os.path.join(stages_dir(), os.path.basename(str(sid)) + ".json"), encoding="utf-8") as f:
        return json.load(f)


def stage_save(layout, sid=None):
    """Guarda una distribucion. Sin sid, el archivo sale del nombre (y pisa al que se llame igual)."""
    sid = sid or _stage_slug(layout.get("name"))
    _write_json(os.path.join(stages_dir(), sid + ".json"), layout)
    return sid


def stage_delete(sid):
    p = os.path.join(stages_dir(), os.path.basename(str(sid)) + ".json")
    if os.path.isfile(p):
        os.remove(p)


def stage_own(disabled=()):
    """Tus escenarios activos, como los necesita la sala: [{"id": "Stage_CSR_<id>", "name", "layout"}]."""
    out = []
    for it in stage_list(disabled):
        if it["enabled"] and len(out) < MAX_GAME_STAGES:
            try:
                out.append({"id": STAGE_PREFIX + it["id"], "name": it["name"], "layout": stage_load(it["id"])})
            except (OSError, ValueError):
                continue
    return out


# ---- compartir: archivo .csrstage
STAGE_EXT = ".csrstage"
STAGE_FILE_FORMAT = "crimesight-revival-stage"


def stage_export(sid, path):
    _write_json(path, {"format": STAGE_FILE_FORMAT, "version": 1, "layout": stage_load(sid)})


def stage_import(path, cat):
    """Anade a tus escenarios el de un archivo .csrstage. Devuelve su id."""
    import stagelayout
    try:
        if os.path.getsize(path) > 512 * 1024:
            raise ValueError
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("format") != STAGE_FILE_FORMAT:
            raise ValueError
        lay = stagelayout.derive(cat, data["layout"])["layout"]
        if not lay["rooms"]:
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError):
        raise ValueError(t("stage_import_bad"))
    lay["name"] = lay["name"].strip() or os.path.splitext(os.path.basename(path))[0][:60]
    taken = {it["id"] for it in stage_list()}
    base_name, n = lay["name"], 1
    while _stage_slug(lay["name"]) in taken:
        n += 1
        lay["name"] = f"{base_name} ({n})"
    return stage_save(lay)


# ---- escenarios en la sala (como los mods: el anfitrion los ofrece y cada jugador se los baja)
def stage_room_fetch(url, password, timeout=20):
    req = urllib.request.Request(url + "/revival/stages", headers={"X-CSR-Password": password or ""})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, ValueError) as e:
        raise ValueError(t("err_unexpected", err=e))
    return [s for s in data.get("stages") or [] if isinstance(s, dict) and isinstance(s.get("layout"), dict)]


def stage_report(url, password, steam_id, have, seen="", timeout=10):
    """Le dice al servidor que escenarios tiene listos tu juego (sin eso no deja jugarlos) y con que
    lista de la sala se ha sincronizado (seen), para que sepa si aun te espera o ya no puedes tenerlos."""
    if not steam_id:
        return False
    body = json.dumps({"platform": 3, "platform_id": str(steam_id), "have": have, "seen": seen or ""}).encode()
    req = urllib.request.Request(url + "/revival/stages/have", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "X-CSR-Password": password or ""})
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except (urllib.error.URLError, ValueError):
        return False              # servidor de una version anterior


STAGE_TEST_FILE = "layout_test.json"


def stage_test(game_dir, cat, layout):
    """Deja la distribucion lista para jugarla en el "Escenario de pruebas (CSR)" (necesita el plugin)."""
    import stagedata, stagelayout
    if not live_mode(game_dir):
        raise ValueError(t("stage_need_bep"))
    compiled = stagelayout.compile_layout(cat, layout)
    d = live_dir(game_dir)
    os.makedirs(d, exist_ok=True)
    nav = stagedata.nav_path(stage_cache_dir())
    if os.path.isfile(nav):
        dst = os.path.join(d, "navsrc.json")
        if not os.path.isfile(dst) or os.path.getsize(dst) != os.path.getsize(nav):
            shutil.copyfile(nav, dst)
    _write_json(os.path.join(d, STAGE_TEST_FILE), compiled)
    return compiled


STAGE_INDEX_FILE = "stages.json"
STAGE_PREFIX = "Stage_CSR_"
MAX_GAME_STAGES = 20


_stage_lock = __import__("threading").Lock()


def stage_publish(game_dir, stages, cat=None):
    with _stage_lock:                  # lo llaman la ventana y la sesion en marcha
        return _stage_publish(game_dir, stages, cat)


def _stage_publish(game_dir, stages, cat=None):
    """Deja en la carpeta del plugin esos escenarios ([{"id", "name", "layout"}]): cada uno sale en la
    lista de escenarios del juego como uno nuevo. Los que tienen errores no se publican.
    Devuelve {id: huella} de los que han quedado listos."""
    import stagedata, stagelayout
    if not game_dir or not live_mode(game_dir):
        return {}
    d = live_dir(game_dir)
    os.makedirs(d, exist_ok=True)
    index, have, keep = [], {}, {STAGE_INDEX_FILE}
    for st in list(stages)[:MAX_GAME_STAGES]:
        sid = str(st.get("id") or "")
        slug = sid[len(STAGE_PREFIX):]
        if not sid.startswith(STAGE_PREFIX) or not re.fullmatch(r"[a-z0-9-]{1,48}", slug):
            continue
        try:
            cat = cat or stage_catalog(game_dir)
            compiled = stagelayout.compile_layout(cat, st["layout"])
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            continue                                   # con errores (o de otra version): no se publica
        compiled["name"] = str(st.get("name") or compiled["name"] or slug)[:60]
        fn = f"stage_{slug}.json"
        text = json.dumps(compiled, ensure_ascii=False)
        path = os.path.join(d, fn)
        try:
            with open(path, encoding="utf-8") as f:
                same = f.read() == text
        except OSError:
            same = False
        if not same:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        have[sid] = stage_hash(st["layout"])
        index.append({"id": sid, "name": compiled["name"], "file": fn, "hash": have[sid]})
        keep.add(fn)
    for fn in os.listdir(d):
        if fn.startswith("stage_") and fn.endswith(".json") and fn not in keep:
            try:
                os.remove(os.path.join(d, fn))
            except OSError:
                pass
    ipath = os.path.join(d, STAGE_INDEX_FILE)
    try:
        with open(ipath, encoding="utf-8") as f:
            old = json.load(f).get("stages")
    except (OSError, ValueError, AttributeError):
        old = None
    if old != index:
        _write_json(ipath, {"stages": index})
    if index:
        nav = stagedata.nav_path(stage_cache_dir())
        if not os.path.isfile(nav):
            stage_catalog(game_dir)
        dst = os.path.join(d, "navsrc.json")
        if os.path.isfile(nav) and (not os.path.isfile(dst) or os.path.getsize(dst) != os.path.getsize(nav)):
            shutil.copyfile(nav, dst)
    return have


def stage_test_active(game_dir):
    """Nombre de la distribucion que se jugara en el escenario de pruebas ("" si es la copia del 01)."""
    try:
        with open(os.path.join(live_dir(game_dir), STAGE_TEST_FILE), encoding="utf-8") as f:
            lay = json.load(f)
        return lay.get("name") or "?" if lay.get("format") == 2 else ""
    except (OSError, ValueError, TypeError):
        return ""


def stage_test_clear(game_dir):
    p = os.path.join(live_dir(game_dir), STAGE_TEST_FILE)
    if os.path.isfile(p):
        os.remove(p)


# ------------------------------------------------------------------ copias del progreso
SAVE_FORMAT = "crimesight-revival-save"
SAVE_EXT = ".csrsave"


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def export_save(steam_id, path):
    """Guarda todo el progreso de esa cuenta en un archivo que el jugador se puede llevar."""
    import stats
    if not steam_id:
        raise ValueError(t("err_no_steam"))
    st = _store()
    user = _local_user(st, steam_id)
    _write_json(path, {"format": SAVE_FORMAT, "version": 1, "steam_id": str(steam_id),
                       "exported": int(time.time()), "profile": stats.export_profile(user)})
    return path


def _read_save(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        raise ValueError(t("err_save_bad"))
    if not isinstance(data, dict) or data.get("format") != SAVE_FORMAT or not isinstance(data.get("profile"), dict):
        raise ValueError(t("err_save_bad"))
    return data


def import_save(steam_id, path):
    """Junta un archivo de progreso con el local. Solo suma: nunca duplica ni borra partidas.
    Devuelve cuantas partidas nuevas trajo."""
    import stats
    if not steam_id:
        raise ValueError(t("err_no_steam"))
    data = _read_save(path)
    if str(data.get("steam_id", steam_id)) != str(steam_id):
        raise ValueError(t("err_save_other"))
    st = _store()
    user = _local_user(st, steam_id)
    before = len(user.get("history") or [])
    stats.merge_into(user, data["profile"])
    st.save()
    return len(user.get("history") or []) - before


def backup_path(folder, steam_id):
    return os.path.join(folder, f"CrimeSightRevival_{steam_id}{SAVE_EXT}")


def backup_now(cfg, steam_id):
    """Copia automatica en la carpeta que eligio el jugador (OneDrive, Google Drive...).
    Primero recoge lo que haya dejado ahi otro PC y luego escribe la copia juntada.
    Devuelve las partidas nuevas que trajo, o None si no hay carpeta elegida."""
    folder = cfg.get("backup_dir")
    if not folder or not steam_id:
        return None
    if not os.path.isdir(folder):
        raise ValueError(t("err_backup_missing", path=folder))
    path = backup_path(folder, steam_id)
    added = 0
    if os.path.isfile(path):
        try:
            added = import_save(steam_id, path)
        except ValueError:
            logging.getLogger("crimesight").warning("Copia de seguridad ilegible, se sobrescribe: %s", path)
    export_save(steam_id, path)
    return added


def public_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as r:
            return r.read().decode().strip()
    except OSError:
        return None
