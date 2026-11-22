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
import hashlib, json, logging, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request

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


def _clean_child_env():
    """Linux, version empaquetada (PyInstaller): el empaquetador apunta LD_LIBRARY_PATH a sus propias librerias,
    y los programas que abrimos (/bin/sh, steam, xdg-open, el navegador de la interfaz...) las heredan. Con un readline o un libc
    distinto al del sistema revientan ("symbol lookup error: /bin/sh: undefined symbol: rl_trim_arg_from_keyseq").
    El lanzador ya cargo lo suyo al arrancar, asi que para los hijos se deja el entorno como estaba."""
    if IS_WINDOWS or not getattr(sys, "frozen", False):
        return
    orig = os.environ.get("LD_LIBRARY_PATH_ORIG")       # el que habia antes de abrir el lanzador
    if orig is not None:
        os.environ["LD_LIBRARY_PATH"] = orig
    else:
        os.environ.pop("LD_LIBRARY_PATH", None)


_clean_child_env()


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


def _linux_steam_roots():
    """Carpetas de Steam que existen en Linux (nativo, Flatpak, Snap), sin repetir."""
    out = []
    for cand in LINUX_STEAM:
        p = os.path.realpath(os.path.expanduser(cand))
        if os.path.isdir(p) and p not in out:
            out.append(p)
    return out


def _linux_registry(key):
    """En Linux, Steam guarda en ~/.steam/registry.vdf lo que en Windows va al registro."""
    paths = ["~/.steam/registry.vdf", "~/.var/app/com.valvesoftware.Steam/.steam/registry.vdf",
             "~/snap/steam/common/.steam/registry.vdf"]
    paths += [os.path.join(r, "..", "registry.vdf") for r in _linux_steam_roots()]
    for p in paths:
        try:
            text = open(os.path.expanduser(p), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        m = re.search(r'"%s"\s+"([^"]*)"' % re.escape(key), text)
        if m and m.group(1) not in ("", "0"):
            return m.group(1)
    return None


def _vdf_pairs(text):
    return re.findall(r'"([^"]+)"\s+"([^"]*)"', text)


def _login_users():
    """[(SteamID64, campos)] de config/loginusers.vdf, de todas las carpetas de Steam que haya."""
    roots = [steam_path()] + ([] if IS_WINDOWS else _linux_steam_roots())
    seen, out = set(), []
    for sp in roots:
        if not sp:
            continue
        try:
            text = open(os.path.join(sp, "config", "loginusers.vdf"), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for block in re.finditer(r'"(\d{17})"\s*\{([^}]*)\}', text):
            if block.group(1) not in seen:
                seen.add(block.group(1))
                out.append((block.group(1), dict(_vdf_pairs(block.group(2)))))
    return out


def _newest_userdata():
    """La cuenta que uso Steam por ultima vez: la carpeta userdata/<id> modificada mas recientemente."""
    best = None
    roots = [steam_path()] + ([] if IS_WINDOWS else _linux_steam_roots())
    for sp in roots:
        ud = os.path.join(sp or "", "userdata")
        try:
            for d in os.listdir(ud):
                if d.isdigit() and d != "0":
                    t_ = os.path.getmtime(os.path.join(ud, d))
                    if not best or t_ > best[0]:
                        best = (t_, d)
        except OSError:
            continue
    return best[1] if best else None


_ACC_LOGGED = None


def steam_account():
    """(SteamID64, nombre de usuario) de la cuenta con sesion iniciada en Steam.
    Windows: el registro. Linux: ~/.steam/registry.vdf; si no, la cuenta marcada como la mas reciente en
    loginusers.vdf; si no, la unica cuenta que haya; si no, la carpeta userdata usada por ultima vez."""
    active = _reg(r"Software\Valve\Steam\ActiveProcess", "ActiveUser") if IS_WINDOWS else _linux_registry("ActiveUser")
    sid = None
    try:
        if active and int(active) > 0:
            sid = str(76561197960265728 + int(active))
    except ValueError:
        sid = None
    name = _reg(r"Software\Valve\Steam", "AutoLoginUser") or ""
    users = _login_users()
    how = "registro" if sid else ""
    if not sid:
        recent = [u for u in users if u[1].get("MostRecent") == "1"]
        if recent:
            sid, how = recent[0][0], "loginusers (MostRecent)"
        elif len(users) == 1:
            sid, how = users[0][0], "loginusers (unica cuenta)"
    if not sid and not IS_WINDOWS:
        acc = _newest_userdata()
        if acc:
            sid, how = str(76561197960265728 + int(acc)), "userdata"
    for uid, fields in users:
        if uid == sid:
            name = fields.get("PersonaName") or fields.get("AccountName") or name
            break
    if not IS_WINDOWS:
        global _ACC_LOGGED
        msg = "Cuenta de Steam: %s (%s). Carpetas de Steam: %s; cuentas en loginusers: %d" % (
            sid or "ninguna", how or "no encontrada", ", ".join(_linux_steam_roots()) or "ninguna", len(users))
        if msg != _ACC_LOGGED:                       # al registro (launcher.log) una vez por cambio
            _ACC_LOGGED = msg
            logging.getLogger("crimesight").warning(msg)
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


def unlock_game_files(game_dir):
    """Quita el atributo de "solo lectura" a los archivos del juego que toca el lanzador. Con el puesto
    (pasa tras copiar o restaurar la carpeta del juego desde otro sitio), Windows no deja sustituirlos
    y sale "Acceso denegado" aunque nadie los tenga abiertos. Devuelve cuantos se han desbloqueado."""
    if not IS_WINDOWS or not game_dir:
        return 0
    import stat
    n = 0
    for sub in ("CrimeSight_Data", os.path.join("CrimeSight_Data", "il2cpp_data", "Metadata"),
                os.path.join("BepInEx", "plugins")):
        d = os.path.join(game_dir, sub)
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for name in names:
            p = os.path.join(d, name)
            if name.endswith(".tmp") and os.path.isfile(p[:-4]):
                try:                         # copia a medias de un intento anterior (puede ocupar cientos de MB)
                    os.remove(p)
                except OSError:
                    pass
                continue
            try:
                st = os.stat(p)
                if os.path.isfile(p) and not st.st_mode & stat.S_IWRITE:
                    os.chmod(p, st.st_mode | stat.S_IWRITE)
                    n += 1
            except OSError:
                pass
    if n:
        logging.getLogger("crimesight").warning("Quitado 'solo lectura' a %d archivos del juego", n)
    return n


def point_game_to(game_dir, url):
    import patch_client, credits_patch
    if not credits_patch.is_patched(game_dir):
        try:
            credits_patch.patch(game_dir)    # linea de creditos en la pantalla de titulo (solo decorativa)
        except OSError as e:
            logging.getLogger("crimesight").warning("No pude poner la linea de creditos (%s); se intentara la proxima vez", e)
    try:
        return patch_client.patch(game_dir, url)
    except PermissionError as e:
        logging.getLogger("crimesight").warning("No puedo modificar el juego: %s", e)
        raise ValueError(t("err_game_locked", path=getattr(e, "filename", "") or game_dir))


def restore_game(game_dir):
    import patch_client, credits_patch, modinject
    unlock_game_files(game_dir)
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
def game_exe_path():
    """CrimeSight.exe: the one chosen in the launcher, or the one inside the game folder."""
    cfg = load_config()
    exe = cfg.get("game_exe")
    if exe and os.path.isfile(exe):
        return exe
    gd = cfg.get("game_dir")
    if gd:
        guess = os.path.join(gd, "CrimeSight.exe")
        if os.path.isfile(guess):
            return guess
    return None


def launch_game():
    if IS_WINDOWS:
        exe = game_exe_path()
        if not exe:
            raise ValueError("No encuentro CrimeSight.exe. Elígelo con «Cambiar ejecutable…».")
        try:
            subprocess.Popen([exe], cwd=os.path.dirname(exe))
        except OSError as e:
            raise ValueError(f"No se pudo iniciar el juego: {e}")
    elif shutil.which("steam"):
        subprocess.Popen(["steam", f"steam://rungameid/{APP_ID}"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["xdg-open", f"steam://rungameid/{APP_ID}"])


_last_running = False


def _win_process_names():
    """Nombres (en minusculas) de los procesos abiertos, preguntando directamente a Windows con la misma
    funcion que usa el Administrador de tareas, sin tasklist. None si Windows no contesta."""
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.Process32FirstW.argtypes = k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32FirstW.restype = k32.Process32NextW.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)          # TH32CS_SNAPPROCESS
    if not snap or snap == ctypes.c_void_p(-1).value:    # INVALID_HANDLE_VALUE
        return None
    names = set()
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            names.add(entry.szExeFile.lower())
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:                # ERROR_NO_MORE_FILES: ha llegado al final
            return None
    finally:
        k32.CloseHandle(snap)
    # Comprobacion: el propio lanzador tiene que salir en la lista; si no, la respuesta no es de fiar
    if os.path.basename(sys.executable).lower() not in names:
        return None
    return names


def game_running():
    """Si CrimeSight.exe esta abierto. Se pregunta directamente a Windows; tasklist queda solo por si eso
    falla. Si tasklist tambien falla o tarda (pasa con el PC muy cargado, p. ej. al cargar el final de la
    partida), no se sabe: se devuelve lo ultimo que se vio, en vez de dar el juego por cerrado y terminar
    la sesion."""
    global _last_running
    if not IS_WINDOWS:
        return _linux_game_running()
    try:
        names = _win_process_names()
    except Exception:  # noqa: BLE001 - si falla, se mira con tasklist como antes
        names = None
    if names is not None:
        _last_running = "crimesight.exe" in names
        return _last_running
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CrimeSight.exe", "/NH"], capture_output=True,
                           timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return _last_running
    out = (r.stdout or b"").decode("utf-8", errors="ignore")   # el texto viene en la codificacion de la consola
    if r.returncode != 0 or not out.strip():
        return _last_running
    _last_running = "crimesight.exe" in out.lower()
    return _last_running


def close_game(wait=10):
    """Cierra el juego (para actualizar el lanzador). Primero se le pide que se cierre; si no, a la fuerza."""
    if not game_running():
        return
    if IS_WINDOWS:
        quiet = {"capture_output": True, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        subprocess.run(["taskkill", "/IM", "CrimeSight.exe"], **quiet)
        t0 = time.time()
        while game_running() and time.time() - t0 < wait:
            time.sleep(1)
        if game_running():
            subprocess.run(["taskkill", "/F", "/IM", "CrimeSight.exe"], **quiet)
    else:
        subprocess.run(["pkill", "-f", "CrimeSight.exe"], capture_output=True)
    t0 = time.time()
    while game_running() and time.time() - t0 < 5:
        time.sleep(0.5)


def other_launchers():
    """PIDs de otros lanzadores abiertos (solo el .exe compilado de Windows; desde Python, ninguno)."""
    if not (IS_WINDOWS and getattr(sys, "frozen", False)):
        return []
    from version import ASSET
    mine = {os.getpid(), os.getppid()}           # el .exe de un archivo son dos procesos: este y su padre
    names = {os.path.basename(sys.executable).lower(), ASSET.lower()}
    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    pids = []
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[0].strip('"').lower() in names:
            try:
                pid = int(parts[1])
            except ValueError:
                continue
            if pid not in mine:
                pids.append(pid)
    return pids


def close_other_launchers():
    for pid in other_launchers():
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


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


def _wait_start(timeout, stop_flag):
    t0 = time.time()
    while not game_running():
        if stop_flag() or time.time() - t0 > timeout:
            return False
        time.sleep(1)
    return True


def bepinex_loaded(game_dir, since):
    """BepInEx ya ha terminado de cargar en esta apertura del juego (su registro, reescrito en cada
    arranque, llega a "Chainloader startup complete")."""
    path = os.path.join(game_dir, "BepInEx", "LogOutput.log")
    try:
        if os.path.getmtime(path) < since:
            return False
        with open(path, encoding="utf-8", errors="ignore") as f:
            return "Chainloader startup complete" in f.read()
    except OSError:
        return False


def wait_game(log, start_timeout=180, stop_flag=lambda: False, game_dir=None):
    """Espera a que el juego se abra y despues a que se cierre.

    Al abrir CrimeSight.exe directamente (no desde Steam), el juego suele cerrarse al momento para que
    Steam lo vuelva a abrir. Si eso se tomara por "el jugador ha cerrado el juego", la sesion terminaria
    y el juego reabierto no encontraria el servidor (error 100010). Por eso, si desaparece nada mas
    abrirse (Steam lo cierra en cuanto arranca), se espera a que vuelva; y si se cierra mas tarde, se da
    un margen de unos segundos."""
    first = bool(game_dir) and bepinex_state(game_dir)["installed"] and not bepinex_state(game_dir)["ready"]
    if not _wait_start(start_timeout, stop_flag):
        log(t("game_not_seen"))
        return False
    if first:
        # La primera vez, BepInEx se prepara (alrededor de un minuto) antes de que salga el juego
        log(t("bep_setup"))
        since = time.time() - 5
        while not stop_flag() and not bepinex_loaded(game_dir, since) and time.time() - since < 300:
            if not game_running() and not _wait_start(45, stop_flag):
                break
            time.sleep(1)
    if game_running():
        log(t("game_open"))
    opened, restarted = time.time(), False
    while not stop_flag():
        if game_running():
            time.sleep(1)
            continue
        if not restarted and time.time() - opened < 20:
            # Steam lo esta reabriendo: solo pasa una vez, nada mas arrancar
            restarted = True
            if not _wait_start(45, stop_flag):
                break
        elif not _wait_start(6, stop_flag):    # cerrado de verdad (se vuelve a mirar unos segundos)
            break
    if not stop_flag():
        logging.getLogger("crimesight").info("El juego se ha cerrado: termina la sesion")
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

    @property
    def models(self):
        return self.bg.models

    def stop(self):
        self.bg.stop()


# ------------------------------------------------------------------ mods de apariencia
def mods_dir():
    """Tu mod: la propia carpeta de mods, con stickers/, avatars/ y mod.json (se crean si faltan) y unas
    instrucciones. Dentro van tambien tus modelos (models/), tu cursor (cursor/) y tus escenarios (stages/)."""
    d = os.path.join(app_dir(), "mods")
    for sub in ("stickers", "avatars"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    meta = os.path.join(d, "mod.json")
    if not os.path.exists(meta):
        with open(meta, "w", encoding="utf-8") as f:
            # nombre vacio = el de siempre ("Carpeta principal")
            json.dump({"name": "", "author": ""}, f, ensure_ascii=False, indent=2)
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


def _in_mods(name):
    """Carpeta dentro de la de mods (models, cursor, stages); se crea vacia si no existe."""
    d = os.path.join(mods_dir(), name)
    os.makedirs(d, exist_ok=True)
    return d


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
    """Tu mod (la carpeta de mods), en una lista como los de una sala."""
    import modpack
    d = mods_dir()
    m = modpack.load_mod(d, mod_owner())
    m["name"] = t("mods_root")
    m["enabled"] = os.path.basename(d) not in set(cfg.get("mods_disabled", []))
    return [m]


def mod_folder(name):
    """Ruta de tu mod por su nombre de carpeta ("mods")."""
    base = mods_dir()
    if name == os.path.basename(base):
        return base
    raise ValueError(t("err_unexpected", err=name))


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


# ------------------------------------------------------------------ recarga en caliente (BepInEx, activada por defecto)
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
    """Tu cursor propio (cursor.png y, si quieres, los demas cursores del juego), en mods/cursor."""
    d = _in_mods("cursor")
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


# ---------------------------------------------------------------- modelos 3D (cambiar un personaje por otro)
# Los huecos que se pueden cambiar y los modelos que se pueden poner (claves del plugin, CrimeSightRevivalModels.cs).
# Los nombres de los personajes son los del juego (iguales en todos los idiomas); victima y traidor se traducen.
MODEL_SLOTS = [("PawnTypeData_A", "Agatha"), ("PawnTypeData_B", "Berkeley"), ("PawnTypeData_C", "Catherine"),
               ("PawnTypeData_D", "Dorothy"), ("PawnTypeData_E", "Ellery"), ("PawnTypeData_F", "Freeman"),
               ("ThreatTypeData_Survivor", None), ("ThreatTypeData_Traitor", None)]
# Sherlock y Moriarty se guardan para el modo historia: solo salen en modo desarrollador.
MODEL_EXTRA = [("sherlock", "Sherlock"), ("moriarty", "Moriarty")]


def dev_mode():
    """Modo desarrollador: "dev": true en config.json (o la variable de entorno CSR_DEV=1)."""
    return os.environ.get("CSR_DEV") == "1" or bool(load_config().get("dev"))


def model_targets():
    """Los modelos que se pueden poner: los personajes, tus modelos propios (.glb) y, en modo desarrollador,
    Sherlock y Moriarty."""
    custom = [(CUSTOM_PREFIX + n, n) for n in custom_models()]
    return list(MODEL_SLOTS) + custom + (list(MODEL_EXTRA) if dev_mode() else [])


def model_swaps():
    """{hueco: modelo} elegidos en el lanzador (solo los que cambian algo y estan disponibles)."""
    sw = load_config().get("model_swaps") or {}
    valid = {k for k, _ in MODEL_SLOTS} | {k for k, _ in model_targets()}
    return {k: v for k, v in sw.items() if k in valid and v in valid and k != v}


# ---------------------------------------------------------------- modelos propios (.glb)
# Cada .glb de la carpeta de modelos es un modelo que se puede poner a un personaje ("custom:<nombre>"). El plugin
# escribe en csr_live/skeletons el esqueleto de cada personaje (solo huesos) y aqui se copia a models/skeletons
# para hacer el modelo encima en Blender.
CUSTOM_PREFIX = "custom:"
SKELETON_DIR = "skeletons"




def models_dir():
    """Tus modelos 3D (mods/models): un .glb por modelo. La primera vez se crea con unas instrucciones y la carpeta
    de esqueletos."""
    d = _in_mods("models")
    os.makedirs(os.path.join(d, SKELETON_DIR), exist_ok=True)
    readme = os.path.join(d, "README.txt")
    text = t("models_readme") + "\n"
    try:
        with open(readme, encoding="utf-8-sig") as f:
            same = f.read() == text
    except OSError:
        same = False
    if not same:
        try:
            with open(readme, "w", encoding="utf-8-sig") as f:
                f.write(text)
        except OSError:
            pass
    return d


MODEL_EXTS = (".glb", ".fbx")


def custom_sources():
    """{nombre: archivo} de tus modelos: cada .glb o .fbx de la carpeta de modelos, y cada subcarpeta con un modelo
    dentro (asi un .fbx puede ir con sus texturas al lado; si hay varios, el mas grande)."""
    out = {}
    try:
        d = models_dir()
        for f in os.listdir(d):
            p = os.path.join(d, f)
            stem, ext = os.path.splitext(f)
            if os.path.isfile(p) and ext.lower() in MODEL_EXTS:
                if stem not in out or ext.lower() == ".fbx":        # mismo nombre en .glb y .fbx: el .fbx
                    out[stem] = p
            elif os.path.isdir(p) and f.lower() not in (SKELETON_DIR, ANIM_DIR, IMAGE_DIR):
                best = None
                for dp, _dn, fs in os.walk(p):
                    if dp.count(os.sep) - p.count(os.sep) > 3:
                        continue
                    for x in fs:
                        if os.path.splitext(x)[1].lower() in MODEL_EXTS:
                            q = os.path.join(dp, x)
                            if best is None or os.path.getsize(q) > os.path.getsize(best):
                                best = q
                if best:
                    out.setdefault(f, best)
    except OSError:
        pass
    return out


def custom_models():
    """Nombres de tus modelos propios, en orden."""
    return sorted(custom_sources(), key=str.lower)


# avisos del ultimo paso de cada modelo al juego: {nombre: texto} (no se pudo convertir, faltan texturas...)
model_issues = {}


def sync_skeletons(game_dir):
    """Copia los esqueletos que escribio el plugin a la carpeta de modelos (skeletons). Devuelve cuantos hay."""
    if not game_dir:
        return 0
    src = os.path.join(live_dir(game_dir), "skeletons")
    dst = os.path.join(models_dir(), SKELETON_DIR)
    n = 0
    try:
        for f in os.listdir(src):
            if not f.lower().endswith(".glb"):
                continue
            a, b = os.path.join(src, f), os.path.join(dst, f)
            n += 1
            try:
                if os.path.isfile(b) and os.path.getsize(a) == os.path.getsize(b) and os.path.getmtime(b) >= os.path.getmtime(a):
                    continue
                shutil.copy2(a, b)
            except OSError as e:
                logging.getLogger("crimesight").warning("No pude copiar el esqueleto %s: %s", f, e)
    except OSError:
        pass
    return n


def _install_custom_models(game_dir, swaps):
    """Copia al juego (csr_live/models) los modelos propios elegidos y quita los que ya no se usan."""
    want = {v[len(CUSTOM_PREFIX):] for v in swaps.values() if v.startswith(CUSTOM_PREFIX)}
    return _sync_files(os.path.join(live_dir(game_dir), "models"), want, custom_sources(), model_issues)


def _file_sig(path):
    st = os.stat(path)
    return "%s|%d|%d" % (os.path.basename(path), st.st_size, int(st.st_mtime))


def built_glb(name, src, issues):
    """El .glb de un modelo o animacion tuyo: el mismo archivo si ya es .glb, o el .fbx convertido (se guarda
    en models_cache y solo se vuelve a convertir si cambia). None si no se pudo."""
    if not src or not os.path.isfile(src):
        return None
    if src.lower().endswith(".glb"):
        issues[name] = None
        return src
    d = os.path.join(app_dir(), "models_cache")
    os.makedirs(d, exist_ok=True)
    b = os.path.join(d, hashlib.sha1(os.path.abspath(src).encode("utf-8")).hexdigest()[:10] + ".glb")
    sig = _file_sig(src)
    try:
        with open(b + ".src", encoding="utf-8") as f:
            if f.read() == sig and os.path.isfile(b):
                return b
    except OSError:
        pass
    try:
        import fbx2glb
        notes = []
        data = fbx2glb.convert(src, notes)
        with open(b + ".part", "wb") as f:
            f.write(data)
        os.replace(b + ".part", b)
        with open(b + ".src", "w", encoding="utf-8") as f:
            f.write(sig)
        issues[name] = "; ".join(t("models_" + k, **kw) for k, kw in notes) or None
        return b
    except Exception as e:                                           # noqa: BLE001 (un archivo raro no tumba nada)
        logging.getLogger("crimesight").warning("No pude preparar el modelo %s: %s", name, e)
        key = getattr(e, "key", None)
        issues[name] = t("models_convert_error", err=t("models_" + key) if key else e)
        try:
            os.remove(b + ".part")
        except OSError:
            pass
        return None


def _sync_files(d, want, sources, issues):
    """Deja en d un .glb por cada nombre de want (copiado, o convertido si es .fbx) y quita los demas."""
    if not want and not os.path.isdir(d):
        return False
    os.makedirs(d, exist_ok=True)
    changed = False
    for name in want:
        a, b = built_glb(name, sources.get(name), issues), os.path.join(d, name + ".glb")
        if not a:
            continue
        sig = _file_sig(a)
        try:
            with open(b + ".src", encoding="utf-8") as f:
                same = f.read() == sig and os.path.isfile(b)
        except OSError:
            same = False
        if same:
            continue
        try:
            shutil.copy2(a, b + ".part")
            os.replace(b + ".part", b)
            with open(b + ".src", "w", encoding="utf-8") as f:
                f.write(sig)
            changed = True
        except OSError as e:
            logging.getLogger("crimesight").warning("No pude copiar el modelo %s: %s", name, e)
            try:
                os.remove(b + ".part")
            except OSError:
                pass
    for f in os.listdir(d):
        stem = f[:-8] if f.lower().endswith(".glb.src") else os.path.splitext(f)[0]
        if (f.lower().endswith(".glb") or f.lower().endswith(".glb.src")) and stem not in want:
            try:
                os.remove(os.path.join(d, f))
                changed = True
            except OSError:
                pass
    return changed


# ---------------------------------------------------------------- animaciones propias
# Cada .fbx/.glb de models/animations es una animacion (la primera que tenga) que puede sustituir el reposo, el
# andar o el correr de un personaje. El plugin la adapta a su esqueleto (CrimeSightRevivalAnims.cs).
ANIM_DIR = "animations"
ANIM_KINDS = ("idle", "walk", "run")
anim_issues = {}


def anims_dir():
    d = os.path.join(models_dir(), ANIM_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def anim_sources():
    out = {}
    try:
        d = anims_dir()
        for f in os.listdir(d):
            stem, ext = os.path.splitext(f)
            if os.path.isfile(os.path.join(d, f)) and ext.lower() in MODEL_EXTS and (stem not in out or ext.lower() == ".fbx"):
                out[stem] = os.path.join(d, f)
    except OSError:
        pass
    return out


def custom_anims():
    return sorted(anim_sources(), key=str.lower)


def anim_swaps():
    """{hueco: {idle|walk|run: animacion}} (solo las que existen)."""
    have = set(custom_anims())
    slots = {k for k, _ in MODEL_SLOTS}
    out = {}
    for slot, kinds in (load_config().get("anim_swaps") or {}).items():
        if slot not in slots or not isinstance(kinds, dict):
            continue
        k = {kind: name for kind, name in kinds.items() if kind in ANIM_KINDS and name in have}
        if k:
            out[slot] = k
    return out


def set_anim_swap(slot, kind, name):
    cfg = load_config()
    sw = {k: dict(v) for k, v in (cfg.get("anim_swaps") or {}).items() if isinstance(v, dict)}
    cur = sw.setdefault(slot, {})
    if name:
        cur[kind] = name
    else:
        cur.pop(kind, None)
    if not cur:
        sw.pop(slot, None)
    cfg["anim_swaps"] = sw
    save_config(cfg)


# ---------------------------------------------------------------- personajes nuevos (slots)
# Un personaje nuevo no sustituye a nadie: entra en el sorteo de cada partida (Selector de personajes). Lleva su
# modelo y, si quieres, sus animaciones, su nombre, su imagen y sus frases; lo que no tenga lo pone el personaje
# cuyo sitio ocupa (tambien su forma de jugar). Si sale de traidor, solo cuentan el modelo y las animaciones.
IMAGE_DIR = "images"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
TALK_KEYS = ("cannotGetAnything", "damagedByGasRoom", "dangerHasInvaded", "destroySwitchboard", "discoverBypass",
             "discoverNote", "discoverSwitchboard", "fullItem", "fullWeapon", "getFood", "getMedicine", "getWeapon",
             "killCheckKillerEachOther", "killCheckKillerOnlyOne", "killCheckTarget", "pawnGameStart", "raid",
             "raidFinalDay", "recoveredByOtherUsingMedicine", "repairSwitchboard", "startAction_statusDying",
             "startAction_statusHunger", "startAction_statusInjury", "stepIntoBlackoutRoom", "useBypass",
             "useFoodForOther", "useMedicineForMyself", "useMedicineForOther")


def images_dir():
    d = os.path.join(models_dir(), IMAGE_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def custom_images():
    """{nombre: archivo} de las imagenes para los personajes nuevos (carpeta images)."""
    out = {}
    try:
        d = images_dir()
        for f in sorted(os.listdir(d), key=str.lower):
            stem, ext = os.path.splitext(f)
            if ext.lower() in IMAGE_EXTS and os.path.isfile(os.path.join(d, f)):
                out.setdefault(stem, os.path.join(d, f))
    except OSError:
        pass
    return out


CHAR_PAWNS = ("PawnTypeData_A", "PawnTypeData_B", "PawnTypeData_C", "PawnTypeData_D", "PawnTypeData_E", "PawnTypeData_F")


def _anim_from(v):
    """De que personaje del juego saca las animaciones un personaje nuevo (Agatha si no se dice)."""
    return v if v in CHAR_PAWNS else CHAR_PAWNS[0]


def characters():
    """Tus personajes nuevos (config "characters"), con lo que falte quitado."""
    out = []
    for c in load_config().get("characters") or []:
        if not isinstance(c, dict) or not re.match(r"^[a-z0-9]{10}$", str(c.get("id", ""))):
            continue
        out.append({"id": c["id"], "name": str(c.get("name") or "")[:24], "role": "pawn",       # traidores: mas adelante
                    "anim_from": _anim_from(c.get("anim_from")),
                    "model": str(c.get("model") or ""), "image": str(c.get("image") or ""),
                    "anims": {k: v for k, v in (c.get("anims") or {}).items() if k in ANIM_KINDS and v},
                    "talk": {k: str(v)[:240] for k, v in (c.get("talk") or {}).items() if k in TALK_KEYS and str(v).strip()}})
    return out


def save_character(c):
    """Crea o cambia un personaje nuevo. Devuelve su id."""
    import secrets
    cfg = load_config()
    lst = [x for x in (cfg.get("characters") or []) if isinstance(x, dict)]
    cid = str(c.get("id") or "")
    if not re.match(r"^[a-z0-9]{10}$", cid):
        cid = secrets.token_hex(5)
    entry = {"id": cid, "name": str(c.get("name") or "").strip()[:24], "role": "pawn", "anim_from": _anim_from(c.get("anim_from")),
             "model": str(c.get("model") or ""), "image": str(c.get("image") or ""),
             "anims": {k: v for k, v in (c.get("anims") or {}).items() if k in ANIM_KINDS and v},
             "talk": {k: str(v).strip()[:240] for k, v in (c.get("talk") or {}).items() if k in TALK_KEYS and str(v).strip()}}
    lst = [x for x in lst if x.get("id") != cid] + [entry]
    cfg["characters"] = lst
    save_config(cfg)
    return cid


def delete_character(cid):
    cfg = load_config()
    cfg["characters"] = [x for x in (cfg.get("characters") or []) if isinstance(x, dict) and x.get("id") != cid]
    cfg["roster_disabled"] = [x for x in (cfg.get("roster_disabled") or []) if x != cid]
    save_config(cfg)


def _image_file(name, src):
    """La imagen tal cual si es PNG o JPG; si no, pasada a PNG (en models_cache)."""
    if not src or not os.path.isfile(src):
        return None
    if src.lower().endswith((".png", ".jpg", ".jpeg")):
        return src
    d = os.path.join(app_dir(), "models_cache")
    os.makedirs(d, exist_ok=True)
    b = os.path.join(d, hashlib.sha1(os.path.abspath(src).encode("utf-8")).hexdigest()[:10] + ".png")
    if not (os.path.isfile(b) and os.path.getmtime(b) >= os.path.getmtime(src)):
        try:
            from PIL import Image
            Image.open(src).convert("RGBA").save(b, "PNG")
        except Exception as e:  # noqa: BLE001
            logging.getLogger("crimesight").warning("No pude leer la imagen %s: %s", name, e)
            return None
    return b


def set_model_swap(slot, target):
    cfg = load_config()
    sw = dict(cfg.get("model_swaps") or {})
    if not target or target == slot:
        sw.pop(slot, None)
    else:
        sw[slot] = target
    cfg["model_swaps"] = sw
    save_config(cfg)
    return model_swaps()


def install_models(game_dir):
    """Escribe en la carpeta del plugin que personaje se ve con que modelo. True si cambio algo."""
    if not game_dir or not live_mode(game_dir):
        return False
    d = live_dir(game_dir)
    os.makedirs(d, exist_ok=True)
    if room_models is not None:                         # en una sala: los de la sala (tuyos apartados un rato)
        swaps, anims, msrc, asrc = _room_install_set(room_models, room_roster)
        copied = _sync_files(os.path.join(d, "models"), set(msrc), msrc, model_issues)
        copied = _sync_files(os.path.join(d, "anims"), set(asrc), asrc, anim_issues) or copied
        copied = _install_roster(d, room_models, room_roster) or copied
    else:
        swaps = model_swaps()
        anims = anim_swaps()
        copied = _install_custom_models(game_dir, swaps)    # antes que models.json: el plugin lee el archivo al verlo
        want = {n for kinds in anims.values() for n in kinds.values()}
        copied = _sync_files(os.path.join(d, "anims"), want, anim_sources(), anim_issues) or copied
        copied = _clear_roster(d) or copied
    path = os.path.join(d, "models.json")
    data = json.dumps({"swaps": swaps, "anims": anims}, ensure_ascii=False, indent=1)
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == data:
                return copied
    except OSError:
        pass
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
    os.replace(tmp, path)
    return True


# ---------------------------------------------------------------- modelos de la sala (como los stickers)
# El anfitrion comparte sus modelos y animaciones con su sala, y los de los invitados que acepte rellenan los
# personajes libres. Quien se une los descarga (solo los archivos que no tiene, por su sha256) a models_room, que
# se borra al terminar; mientras tanto el juego ve los de la sala y los tuyos vuelven al salir.
room_models = None          # None: los tuyos. Si no: {"hash", "swaps", "anims", "chars", "files": {sha: {"kind", "path"}}}
room_roster = None          # reparto de la partida en curso (del servidor) o None
room_disabled = []          # personajes desactivados en el Selector de personajes de la sala
room_host = False           # True si este PC decide el Selector (anfitrion o en solitario)
ROOM_PREFIX = "rm_"
_sha_cache = {}


def temp_models_dir():
    return os.path.join(app_dir(), "models_room")


def clear_temp_models():
    d = temp_models_dir()
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
        return True
    return False


def _sha256_file(path):
    key = (os.path.abspath(path), _file_sig(path))
    if key not in _sha_cache:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _sha_cache[key] = h.hexdigest()
    return _sha_cache[key]


def my_model_set():
    """Tus modelos y animaciones en el formato de sala: los archivos por su sha256 (con su ruta en este PC).
    Sherlock y Moriarty (modo desarrollador) no se comparten."""
    import modelpack
    ms = modelpack.empty()
    slots = {k for k, _ in MODEL_SLOTS}
    msrc, asrc = custom_sources(), anim_sources()

    def add(kind, name, src, issues):
        path = built_glb(name, src, issues)
        if not path:
            return None
        sha = _sha256_file(path)
        ms["files"][sha] = {"kind": kind, "size": os.path.getsize(path), "name": name, "path": path}
        return modelpack.FILE_PREFIX + sha
    for slot, v in model_swaps().items():
        if v in slots:
            ms["swaps"][slot] = v
        elif v.startswith(CUSTOM_PREFIX):
            ref = add("model", v[len(CUSTOM_PREFIX):], msrc.get(v[len(CUSTOM_PREFIX):]), model_issues)
            if ref:
                ms["swaps"][slot] = ref
    for slot, kinds in anim_swaps().items():
        for kind, name in kinds.items():
            ref = add("anim", name, asrc.get(name), anim_issues)
            if ref:
                ms["anims"].setdefault(slot, {})[kind] = ref
    isrc = custom_images()
    for c in characters():
        model = add("model", c["model"], msrc.get(c["model"]), model_issues) if c["model"] else None
        if not model:
            continue
        entry = {"name": c["name"], "role": c["role"], "anim_from": c["anim_from"], "model": model, "anims": {}, "talk": dict(c["talk"])}
        for kind, name in c["anims"].items():
            ref = add("anim", name, asrc.get(name), anim_issues)
            if ref:
                entry["anims"][kind] = ref
        img = _image_file(c["image"], isrc.get(c["image"])) if c["image"] else None
        if img and os.path.getsize(img) <= modelpack.MAX_IMAGE_BYTES:
            sha = _sha256_file(img)
            ms["files"][sha] = {"kind": "image", "size": os.path.getsize(img), "name": c["image"], "path": img}
            entry["image"] = modelpack.FILE_PREFIX + sha
        ms["chars"][c["id"]] = entry
    ms["hash"] = modelpack.set_hash(ms)
    return ms


def _room_install_set(rm, roster=None):
    """Lo que se escribe en el juego para un juego de modelos de sala: nombres rm_<sha> para sus archivos. Con el
    reparto de la partida, cada sitio con un personaje nuevo lleva su modelo y sus animaciones (o las del juego)."""
    import modelpack
    msrc, asrc = {}, {}

    def ref(v, kind):
        if not v.startswith(modelpack.FILE_PREFIX):
            return v
        sha = v[len(modelpack.FILE_PREFIX):]
        f = rm["files"].get(sha)
        if not f:
            return None
        name = ROOM_PREFIX + sha[:16]
        (msrc if kind == "model" else asrc)[name] = f["path"]
        return (CUSTOM_PREFIX + name) if kind == "model" else name
    swaps = {}
    for slot, v in rm.get("swaps", {}).items():
        r = ref(v, "model")
        if r:
            swaps[slot] = r
    anims = {}
    for slot, kinds in rm.get("anims", {}).items():
        for kind, v in kinds.items():
            r = ref(v, "anim")
            if r:
                anims.setdefault(slot, {})[kind] = r
    chars = rm.get("chars", {})
    for c in chars.values():                       # todos sus modelos en el juego (para verlos en el selector)
        ref(c.get("model", ""), "model")
    taken = dict((roster or {}).get("positions") or {})
    if roster and roster.get("traitor"):
        taken[modelpack.TRAITOR] = roster["traitor"]
    for slot, cid in taken.items():
        c = chars.get(cid) if cid else None
        if not c:
            continue
        r = ref(c.get("model", ""), "model")
        if not r:
            continue
        swaps[slot] = r
        anims.pop(slot, None)                      # sin animaciones propias: las del juego
        for kind, v in (c.get("anims") or {}).items():
            ra = ref(v, "anim")
            if ra:
                anims.setdefault(slot, {})[kind] = ra
    return swaps, anims, msrc, asrc


def _write_json_if_changed(path, obj):
    data = json.dumps(obj, ensure_ascii=False, indent=1)
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == data:
                return False
    except OSError:
        pass
    with open(path + ".part", "w", encoding="utf-8") as f:
        f.write(data)
    os.replace(path + ".part", path)
    return True


def _clear_roster(d):
    """Fuera de una sala no hay reparto ni Selector de personajes: el juego vuelve a sus personajes."""
    gone = False
    for name in ("roster.json", "roster_pool.json"):
        try:
            os.remove(os.path.join(d, name))
            gone = True
        except OSError:
            pass
    shutil.rmtree(os.path.join(d, "images"), ignore_errors=True)
    return gone


def _install_roster(d, rm, roster):
    """Para el plugin: roster.json (que nombre, frases e imagen lleva cada sitio en esta partida) y
    roster_pool.json (todos los personajes, para el Selector de personajes). Copia las imagenes."""
    import modelpack
    chars = (rm or {}).get("chars", {})
    files = (rm or {}).get("files", {})
    idir = os.path.join(d, "images")
    want = {}
    for c in chars.values():
        sha = (c.get("image") or "")[len(modelpack.FILE_PREFIX):]
        if sha and sha in files:
            src = files[sha]["path"]
            want[sha[:16] + (".jpg" if src.lower().endswith((".jpg", ".jpeg")) else ".png")] = src
    if want or os.path.isdir(idir):
        os.makedirs(idir, exist_ok=True)
        for name, src in want.items():
            dst = os.path.join(idir, name)
            if not (os.path.isfile(dst) and os.path.getsize(dst) == os.path.getsize(src)):
                shutil.copy2(src, dst + ".part")
                os.replace(dst + ".part", dst)
        for f in os.listdir(idir):
            if f not in want:
                try:
                    os.remove(os.path.join(idir, f))
                except OSError:
                    pass

    def image_of(c):
        sha = (c.get("image") or "")[len(modelpack.FILE_PREFIX):]
        for name in want:
            if sha and name.startswith(sha[:16]):
                return "images/" + name
        return None

    def model_of(c):
        sha = (c.get("model") or "")[len(modelpack.FILE_PREFIX):]
        return ROOM_PREFIX + sha[:16] if sha else None

    def entry(cid):
        c = chars.get(cid) if cid else None
        if not c:
            return None
        return {"id": cid, "name": c.get("name") or None, "talk": dict(c.get("talk") or {}), "image": image_of(c),
                "model": model_of(c), "anim_from": _anim_from(c.get("anim_from"))}
    out = {"id": (roster or {}).get("id", ""), "positions": {}, "traitor": None}
    if roster:
        out["positions"] = {k: entry(v) for k, v in (roster.get("positions") or {}).items()}
        out["traitor"] = entry(roster.get("traitor"))
    changed = _write_json_if_changed(os.path.join(d, "roster.json"), out)
    disabled = set(room_disabled or [])
    items = [{"id": "orig:" + k, "key": k, "role": "pawn", "enabled": "orig:" + k not in disabled} for k in modelpack.PAWNS]
    for cid, c in sorted(chars.items(), key=lambda kv: (kv[1].get("name") or "").lower()):
        if c.get("role", "pawn") != "pawn":                     # el traidor no entra en el Selector (aun)
            continue
        items.append({"id": cid, "role": "pawn", "name": c.get("name") or "", "image": image_of(c),
                      "model": model_of(c), "anim_from": _anim_from(c.get("anim_from")), "enabled": cid not in disabled})
    pool = {"host": bool(room_host), "min": modelpack.MIN_PAWNS, "items": items}
    return _write_json_if_changed(os.path.join(d, "roster_pool.json"), pool) or changed


def _http(url, password, data=None, method=None, headers=None, timeout=60):
    h = {"X-CSR-Password": password or ""}
    h.update(headers or {})
    return urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=h), timeout=timeout)


def download_models(url, password, expected_hash, progress=None):
    """Baja los modelos de la sala (solo los archivos que no tengas ya) y devuelve el juego de modelos local."""
    import modelpack
    try:
        with _http(url + "/revival/models", password, timeout=20) as r:
            man = json.loads(r.read(4 * 1024 * 1024))
    except urllib.error.HTTPError as e:
        raise ValueError(t("need_password") if e.code == 403 else t("models_download_failed", err=e.code))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ValueError(t("models_download_failed", err=getattr(e, "reason", e)))
    try:
        ms = modelpack.clean(man)
    except modelpack.ModelError as e:
        raise ValueError(t("models_download_failed", err=e))
    if expected_hash and ms["hash"] != expected_hash:
        raise ValueError(t("models_download_failed", err="hash"))
    d = temp_models_dir()
    os.makedirs(d, exist_ok=True)
    missing = [s for s in ms["files"] if not (os.path.isfile(os.path.join(d, s + ".glb")) and
                                               _sha256_file(os.path.join(d, s + ".glb")) == s)]
    if missing and progress:
        progress(sum(ms["files"][s]["size"] for s in missing))
    for sha in missing:
        f, path = ms["files"][sha], os.path.join(d, sha + ".glb")
        try:
            with _http(url + "/revival/models/file/" + sha, password, timeout=120) as r:
                data = r.read(f["size"] + 1)
        except urllib.error.HTTPError as e:
            raise ValueError(t("models_download_failed", err=e.code))
        except (urllib.error.URLError, OSError) as e:
            raise ValueError(t("models_download_failed", err=getattr(e, "reason", e)))
        if len(data) != f["size"] or modelpack.sha256(data) != sha:
            raise ValueError(t("models_download_failed", err="sha256"))
        try:
            modelpack.check_file(data, f["kind"])
        except modelpack.ModelError as e:
            raise ValueError(t("models_download_failed", err=e))
        with open(path + ".part", "wb") as out:
            out.write(data)
        os.replace(path + ".part", path)
    return {"hash": ms["hash"], "swaps": ms["swaps"], "anims": ms["anims"], "chars": ms.get("chars", {}),
            "files": {s: {"kind": f["kind"], "path": os.path.join(d, s + ".glb"), "name": f["name"]}
                      for s, f in ms["files"].items()}}


def roster_state(url, steam_id):
    """Reparto de personajes de tu partida en ese servidor y los personajes desactivados de la sala."""
    try:
        with urllib.request.urlopen(url + "/revival/roster?platform_id=" + str(steam_id or ""), timeout=6) as r:
            a = json.loads(r.read(1 << 20))
        return a.get("roster"), list(a.get("disabled") or [])
    except (urllib.error.URLError, OSError, ValueError):
        return "error", []


def roster_answer(game_dir):
    """Lo que ha marcado el anfitrion en el Selector de personajes del juego: (n, desactivados) o None."""
    try:
        with open(os.path.join(live_dir(game_dir), "roster_select.json"), encoding="utf-8") as f:
            a = json.load(f)
        return int(a.get("n", 0)), [str(x) for x in (a.get("disabled") or [])]
    except (OSError, ValueError, TypeError):
        return None


def offer_models(url, password, ms, player):
    """Ofrece tus modelos al anfitrion (solo la lista). Devuelve (estado, id, archivos que pide)."""
    import modelpack
    from urllib.parse import quote
    if not ms.get("hash"):
        return "none", "", []
    body = json.dumps(modelpack.manifest(ms)).encode("utf-8")
    try:
        with _http(url + "/revival/models/offer", password, data=body, method="POST", timeout=30,
                   headers={"Content-Type": "application/json", "X-CSR-Player": quote(player or "?")}) as r:
            a = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:                  # servidor de una version anterior
            return "ignored", "", []
        raise ValueError(t("models_download_failed", err=e.code))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ValueError(t("models_download_failed", err=getattr(e, "reason", e)))
    return a.get("status", "ignored"), a.get("id", ""), list(a.get("need") or [])


def offer_models_state(url, password, oid):
    try:
        with _http(url + "/revival/models/offer/" + oid, password, timeout=15) as r:
            a = json.loads(r.read())
        return a.get("status", "rejected"), list(a.get("need") or [])
    except (urllib.error.URLError, OSError, ValueError):
        return "unknown", []


def upload_models(url, password, oid, ms, need):
    """Sube al anfitrion los archivos que ha pedido de tu oferta aceptada."""
    for sha in need:
        f = ms["files"].get(sha)
        if not f:
            continue
        with open(f["path"], "rb") as fh:
            data = fh.read()
        try:
            with _http(url + "/revival/models/upload/%s/%s" % (oid, sha), password, data=data, method="PUT",
                       timeout=600, headers={"Content-Type": "model/gltf-binary"}):
                pass
        except urllib.error.HTTPError as e:
            if e.code != 409:              # 409: ya lo tenia
                raise ValueError(t("models_upload_failed", err=e.code))
        except (urllib.error.URLError, OSError) as e:
            raise ValueError(t("models_upload_failed", err=getattr(e, "reason", e)))


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
    juego junto a nuestro plugin. No va dentro del lanzador: este lo instala solo al arrancar (salvo
    que el jugador lo haya quitado)."""
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


def offer_prompt(game_dir, oid, title, body, yes, no, always=""):
    """Aviso de mods de un invitado dentro del juego: el plugin lo ensena con dos botones y escribe
    la respuesta en offer_answer.json (el anfitrion suele estar en el juego, no en el lanzador)."""
    d = live_dir(game_dir)
    if not os.path.isdir(d):
        return False
    try:
        os.remove(os.path.join(d, "offer_answer.json"))
    except OSError:
        pass
    _write_json(os.path.join(d, "offer.json"), {"id": oid, "title": title, "body": body, "yes": yes, "no": no,
                                                "always": always})
    return True


def offer_answer(game_dir, oid):
    """True/False ("always" si eligio aceptar siempre) si se ha contestado desde el juego; None si aun no."""
    try:
        with open(os.path.join(live_dir(game_dir), "offer_answer.json"), encoding="utf-8") as f:
            a = json.load(f)
    except (OSError, ValueError):
        return None
    if a.get("id") != oid:
        return None
    return "always" if a.get("always") else bool(a.get("accept"))


def offer_clear(game_dir):
    for name in ("offer.json", "offer_answer.json"):
        try:
            os.remove(os.path.join(live_dir(game_dir), name))
        except OSError:
            pass


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
    """Distribuciones guardadas por el jugador (un .json por escenario), en mods/stages."""
    return _in_mods("stages")


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
