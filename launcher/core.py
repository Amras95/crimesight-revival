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


def steam_path():
    p = _reg(r"Software\Valve\Steam", "SteamPath")
    if p and os.path.isdir(p):
        return os.path.normpath(p)
    for cand in (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam", os.path.expanduser("~/.steam/steam")):
        if os.path.isdir(cand):
            return cand
    return None


def _vdf_pairs(text):
    return re.findall(r'"([^"]+)"\s+"([^"]*)"', text)


def steam_account():
    """(SteamID64, nombre de usuario) de la cuenta con sesion iniciada en Steam."""
    active = _reg(r"Software\Valve\Steam\ActiveProcess", "ActiveUser")
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
    return i18n.from_steam(_reg(r"Software\Valve\Steam", "Language")) or "en"


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
    import patch_client, credits_patch
    a = patch_client.restore(game_dir)
    b = credits_patch.restore(game_dir)
    return a or b


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
    else:
        subprocess.Popen(["xdg-open", f"steam://rungameid/{APP_ID}"])


def game_running():
    if not IS_WINDOWS:
        return False
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CrimeSight.exe", "/NH"], capture_output=True,
                         text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    return "CrimeSight.exe" in out


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
    def __init__(self, public=False, port=DEFAULT_PORT, password=""):
        os.environ["CSR_DATA_DIR"] = data_dir()
        import server
        if not getattr(LocalServer, "_logging", False):
            server.setup_logging(data_dir())
            LocalServer._logging = True
        self.bg = server.BackgroundServer(host="0.0.0.0" if public else "127.0.0.1", port=port,
                                          password=password, data_dir=data_dir())
        self.port = port

    def start(self):
        self.bg.start()
        return self

    def stop(self):
        self.bg.stop()


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
