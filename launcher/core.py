"""
CRIMESIGHT Revival - launcher logic (no interface).

- Finds Steam, the active account and the game folder.
- Takes the keys from the player's own installation (nothing from Konami is distributed).
- Points the game at the chosen server and opens it through Steam.
- Starts the local server (play solo / be the host).
- Syncs the local profile with a friend's server or your own server.

Each player's progress lives on THEIR PC (the launcher's data folder). Other people's servers
only borrow it: it is uploaded on joining, the new matches are brought back on leaving, and the
two copies are merged by adding up matches (each one has a unique id, they are never duplicated).
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
    """Linux, packaged version (PyInstaller): the packager points LD_LIBRARY_PATH at its own libraries,
    and the programs we open (/bin/sh, steam, xdg-open, the interface's browser...) inherit them. With a readline or a libc
    different from the system's they break ("symbol lookup error: /bin/sh: undefined symbol: rl_trim_arg_from_keyseq").
    The launcher already loaded its own at startup, so for the children the environment is left as it was."""
    if IS_WINDOWS or not getattr(sys, "frozen", False):
        return
    orig = os.environ.get("LD_LIBRARY_PATH_ORIG")       # the one there was before opening the launcher
    if orig is not None:
        os.environ["LD_LIBRARY_PATH"] = orig
    else:
        os.environ.pop("LD_LIBRARY_PATH", None)


_clean_child_env()


# ------------------------------------------------------------------ folders and settings
def app_dir():
    base = os.environ.get("APPDATA") if IS_WINDOWS else os.path.expanduser("~/.local/share")
    d = os.path.join(base or os.path.expanduser("~"), "CrimeSightRevival")
    os.makedirs(d, exist_ok=True)
    return d


def setup_launcher_log():
    """Launcher warnings and errors in %APPDATA%\\CrimeSightRevival\\launcher.log (for diagnosis)."""
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


def load_config():
    path = os.path.join(app_dir(), "config.json")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    cfg.setdefault("servers", [])
    cfg.setdefault("port", DEFAULT_PORT)
    if cfg.get("roster_v") != 3 and os.path.isfile(path):
        _migrate_roster(cfg)
    return cfg


def _migrate_roster(cfg):
    """Once (roster_v 3): your new characters switched on in the launcher and ticked in the game's Character
    Selection, and no original character left unticked from earlier versions (ed139-ed150 defaults)."""
    ids = {c.get("id") for c in cfg.get("characters") or [] if isinstance(c, dict) and c.get("id")}
    for c in cfg.get("characters") or []:
        if isinstance(c, dict):
            c["active"] = True
    cfg["roster_disabled"] = [x for x in (cfg.get("roster_disabled") or [])
                              if not str(x).startswith("orig:") and x not in ids]
    cfg["roster_v"] = 3
    try:
        write_config(cfg)
    except OSError:
        pass


# Settings changed only straight in the file (load, change, save at once: characters, model and animation
# swaps, the Character Selection). The launcher's own copy of the settings, loaded when it opened, has old values
# for these: saving that copy used to put them back (e.g. a new character vanished when the game was launched).
FILE_KEYS = ("characters", "anim_swaps", "model_swaps", "roster_disabled")


def save_config(cfg):
    """Saves the launcher's copy of the settings. FILE_KEYS keep what's in the file (and the copy gets them too)."""
    disk = load_config()
    for k in FILE_KEYS:
        if k in disk:
            cfg[k] = disk[k]
        else:
            cfg.pop(k, None)
    write_config(cfg)


def write_config(cfg):
    """Writes the settings as they are: only for a copy just loaded from the file (see FILE_KEYS)."""
    path = os.path.join(app_dir(), "config.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def import_old_data():
    """If we come from the script version (server/data/db.json next to the launcher), copy it."""
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


LINUX_STEAM = ("~/.local/share/Steam", "~/.steam/steam", "~/.steam/root",          # Steam Deck / native
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
    """Steam folders that exist on Linux (native, Flatpak, Snap), without repeats."""
    out = []
    for cand in LINUX_STEAM:
        p = os.path.realpath(os.path.expanduser(cand))
        if os.path.isdir(p) and p not in out:
            out.append(p)
    return out


def _linux_registry(key):
    """On Linux, Steam keeps in ~/.steam/registry.vdf what on Windows goes to the registry."""
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
    """[(SteamID64, fields)] from config/loginusers.vdf, from every Steam folder there is."""
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
    """The account Steam used last: the most recently modified userdata/<id> folder."""
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
    """(SteamID64, user name) of the account logged into Steam.
    Windows: the registry. Linux: ~/.steam/registry.vdf; otherwise, the account marked as the most recent in
    loginusers.vdf; otherwise, the only account there is; otherwise, the userdata folder used last."""
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
        if msg != _ACC_LOGGED:                       # to the log (launcher.log) once per change
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
    """Launcher language = the game's. Order: the one the game used the last time it logged
    into a Revival server; the language Steam has the game installed in; Steam's
    language. If the game is not found: English."""
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


# ------------------------------------------------------------------ keys and patch
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
    """Removes the "read-only" attribute from the game files the launcher touches. With it set
    (it happens after copying or restoring the game folder from somewhere else), Windows doesn't let them be replaced
    and "Access denied" comes up even though nobody has them open. Returns how many were unlocked."""
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
                try:                         # half-done copy from an earlier attempt (it can take hundreds of MB)
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
            credits_patch.patch(game_dir)    # credits line on the title screen (decorative only)
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
    if live_mode(game_dir):                 # the original game has no BepInEx
        uninstall_bepinex(game_dir)
        m = True
    a = patch_client.restore(game_dir)
    b = credits_patch.restore(game_dir)
    return a or b or m


# ------------------------------------------------------------------ game
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
    """Names (lowercase) of the running processes, asking Windows directly with the same
    function the Task Manager uses, without tasklist. None if Windows doesn't answer."""
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
        if ctypes.get_last_error() != 18:                # ERROR_NO_MORE_FILES: reached the end
            return None
    finally:
        k32.CloseHandle(snap)
    # Check: the launcher itself has to be in the list; otherwise, the answer can't be trusted
    if os.path.basename(sys.executable).lower() not in names:
        return None
    return names


def game_running():
    """Whether CrimeSight.exe is open. Windows is asked directly; tasklist is only kept in case that
    fails. If tasklist also fails or is slow (it happens with a very busy PC, e.g. while loading the end of the
    match), nobody knows: the last thing seen is returned, instead of taking the game as closed and ending
    the session."""
    global _last_running
    if not IS_WINDOWS:
        return _linux_game_running()
    try:
        names = _win_process_names()
    except Exception:  # noqa: BLE001 - if it fails, it is checked with tasklist as before
        names = None
    if names is not None:
        _last_running = "crimesight.exe" in names
        return _last_running
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CrimeSight.exe", "/NH"], capture_output=True,
                           timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return _last_running
    out = (r.stdout or b"").decode("utf-8", errors="ignore")   # the text comes in the console's encoding
    if r.returncode != 0 or not out.strip():
        return _last_running
    _last_running = "crimesight.exe" in out.lower()
    return _last_running


def close_game(wait=10):
    """Closes the game (to update the launcher). First it is asked to close; otherwise, by force."""
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
    """PIDs of other open launchers (only Windows' compiled .exe; from Python, none)."""
    if not (IS_WINDOWS and getattr(sys, "frozen", False)):
        return []
    from version import ASSET
    mine = {os.getpid(), os.getppid()}           # a one-file .exe is two processes: this one and its parent
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
    """With Proton the game is a Wine process whose command line includes CrimeSight.exe."""
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
            continue                       # a terminal that only mentions the name doesn't count
        if b"crimesight.exe" in args:
            return True
    return False


def linux_launch_option_ok():
    """Linux / Steam Deck: BepInEx needs Proton to load its winhttp.dll, which is turned on with the
    launch option WINEDLLOVERRIDES="winhttp=n,b" %command% (the game's Properties in Steam).
    True if it is set, False if not, None if it can't be known."""
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
    """BepInEx has finished loading in this run of the game (its log, rewritten on every
    start, reaches "Chainloader startup complete")."""
    path = os.path.join(game_dir, "BepInEx", "LogOutput.log")
    try:
        if os.path.getmtime(path) < since:
            return False
        with open(path, encoding="utf-8", errors="ignore") as f:
            return "Chainloader startup complete" in f.read()
    except OSError:
        return False


def wait_game(log, start_timeout=180, stop_flag=lambda: False, game_dir=None):
    """Waits for the game to open and then for it to close.

    When CrimeSight.exe is opened directly (not through Steam), the game usually closes at once so that
    Steam opens it again. If that were taken as "the player closed the game", the session would end
    and the reopened game wouldn't find the server (error 100010). So, if it disappears right after
    opening (Steam closes it as soon as it starts), it waits for it to come back; and if it closes later, there is
    a margin of a few seconds."""
    first = bool(game_dir) and bepinex_state(game_dir)["installed"] and not bepinex_state(game_dir)["ready"]
    if not _wait_start(start_timeout, stop_flag):
        log(t("game_not_seen"))
        return False
    if first:
        # The first time, BepInEx gets ready (around a minute) before the game shows up
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
            # Steam is reopening it: it only happens once, right at startup
            restarted = True
            if not _wait_start(45, stop_flag):
                break
        elif not _wait_start(6, stop_flag):    # really closed (checked again for a few seconds)
            break
    if not stop_flag():
        logging.getLogger("crimesight").info("El juego se ha cerrado: termina la sesion")
    return True


# ------------------------------------------------------------------ local server
class LocalServer:
    def __init__(self, public=False, port=DEFAULT_PORT, password="", mods=None, player_mods="ignore", names=None,
                 stages=None):
        os.environ["CSR_DATA_DIR"] = data_dir()
        import server
        import match
        match.forced_roles = dev_forced_roles          # developer mode: picked killer/target
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


# ------------------------------------------------------------------ appearance mods
def mods_dir():
    """Your mod: the mods folder itself, with stamps/, avatars/ and mod.json (created if missing) and some
    instructions. Your models (models/), your cursor (cursor/) and your stages (stages/) also go inside."""
    d = os.path.join(app_dir(), "mods")
    for sub in ("stamps", "avatars"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    meta = os.path.join(d, "mod.json")
    if not os.path.exists(meta):
        with open(meta, "w", encoding="utf-8") as f:
            # empty name = the usual one ("Main folder")
            json.dump({"name": "", "author": ""}, f, ensure_ascii=False, indent=2)
    readme = os.path.join(d, "README.txt")
    text = t("mods_readme") + "\n"
    try:
        with open(readme, encoding="utf-8-sig") as f:
            same = f.read() == text
    except OSError:
        same = False
    if not same:
        try:
            with open(readme, "w", encoding="utf-8-sig") as f:   # on Windows, \n is already written as \r\n
                f.write(text)
        except OSError:
            pass
    return d


def _in_mods(name):
    """Folder inside the mods one (models, cursor, stages); created empty if it doesn't exist."""
    d = os.path.join(mods_dir(), name)
    os.makedirs(d, exist_ok=True)
    return d


def temp_mods_dir():
    """Mods downloaded from another player's room ("<id>+temp"); deleted at the end."""
    return os.path.join(app_dir(), "mods_temp")


_OWNER = []


def mod_owner():
    """Your Steam account: it is part of your mods' id (so they don't clash with someone else's)."""
    if not _OWNER:
        try:
            _OWNER.append(steam_account()[0] or "")
        except Exception:  # noqa: BLE001
            _OWNER.append("")
    return _OWNER[0]


def my_mods(cfg):
    """Your mod (the mods folder), in a list like a room's."""
    import modpack
    d = mods_dir()
    m = modpack.load_mod(d, mod_owner())
    m["name"] = t("mods_root")
    m["enabled"] = os.path.basename(d) not in set(cfg.get("mods_disabled", []))
    return [m]


def mod_folder(name):
    """Path of your mod by its folder name ("mods")."""
    base = mods_dir()
    if name == os.path.basename(base):
        return base
    raise ValueError(t("err_unexpected", err=name))


def mods_enabled(cfg=None):
    """The switch of your mods folder in the launcher ("Main folder" in Mods > General). When it is off, nothing in
    the folder is used or shared: no stickers or avatars, and no models, animations or new characters either (they
    live in its models/ subfolder; before, only the stickers and avatars followed the switch)."""
    cfg = cfg if cfg is not None else load_config()
    return "mods" not in set(cfg.get("mods_disabled", []))


def my_room_set(cfg):
    import modpack
    return modpack.room_set([m for m in my_mods(cfg) if m["enabled"]])


def install_mods(game_dir, rs, log=None):
    """Leaves exactly those mods in the game (empty = none). True if something had to change.
    With the BepInEx plugin (hot reload) the game files stay original and
    the mods go to the folder the plugin watches; without it, they go into the game files."""
    import modinject
    if live_mode(game_dir):
        changed = modinject.restore(game_dir, fix=False)
        return write_live(rs, game_dir) or changed
    clear_live(game_dir)
    return modinject.apply(game_dir, rs, log=log)


# ------------------------------------------------------------------ hot reload (BepInEx, on by default)
BEPINEX_URL = ("https://github.com/BepInEx/BepInEx/releases/download/v6.0.0-pre.2/"
               "BepInEx-Unity.IL2CPP-win-x64-6.0.0-pre.2.zip")
BEPINEX_SHA256 = "616ec7eb06cf11b2a0000e8fcef04d1b12bb58e84a2e0bdac9523234fc193ceb"
BEPINEX_SIZE = 34146254
BEPINEX_FILES = ("winhttp.dll", "doorstop_config.ini", ".doorstop_version", "changelog.txt", "BepInEx", "dotnet")
PLUGIN_NAME = "CrimeSightRevival.Mods.dll"




def cursor_dir():
    """Your own cursor (cursor.png and, if you want, the game's other cursors), in mods/cursor. Its instructions
    (README.txt) are in the launcher's language, like the other folders'."""
    d = _in_mods("cursor")
    readme = os.path.join(d, "README.txt")
    text = t("cursor_readme") + "\n"
    try:
        with open(readme, encoding="utf-8-sig") as f:
            same = f.read() == text
    except (OSError, UnicodeDecodeError):
        same = False
    if not same:
        try:
            with open(readme, "w", encoding="utf-8-sig") as f:
                f.write(text)
        except OSError:
            pass
    return d


CURSOR_SIZE = 32


def cursor_enabled():
    return load_config().get("cursor_enabled", True)


def cursor_state():
    """For the launcher: whether you have your own cursor, whether it is on, its thumbnail and its click point."""
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
    """Sets an image as the cursor: with transparency, square and 32x32 (the size Windows handles
    best). If the image has no transparency, its plain background is removed."""
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
    sq.alpha_composite(img, (0, 0))              # stuck to the top left: an arrow's tip
    sq = sq.resize((CURSOR_SIZE, CURSOR_SIZE), Image.LANCZOS)
    d = cursor_dir()
    sq.save(os.path.join(d, "cursor.png"))
    if not os.path.isfile(os.path.join(d, "hotspot.txt")):
        cursor_set_hotspot("tip")


def cursor_set_hotspot(mode):
    """The cursor's click point: "tip" (the top left corner, like an arrow) or "center"."""
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


def install_cursor(game_dir):
    """Copies your cursor to the folder the plugin watches (only what changes). True if there were changes.
    Off in the launcher = the plugin's folder stays empty (the game's cursor comes back)."""
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


# ---------------------------------------------------------------- 3D models (swap one character for another)
# The slots that can be changed and the models that can be used (the plugin's keys, CrimeSightRevivalModels.cs).
# The characters' names are the game's (the same in every language); victim and traitor are translated.
MODEL_SLOTS = [("PawnTypeData_A", "Agatha"), ("PawnTypeData_B", "Berkeley"), ("PawnTypeData_C", "Catherine"),
               ("PawnTypeData_D", "Dorothy"), ("PawnTypeData_E", "Ellery"), ("PawnTypeData_F", "Freeman"),
               ("ThreatTypeData_Survivor", None), ("ThreatTypeData_Traitor", None)]
# Sherlock and Moriarty are kept for the story mode: they only show up in developer mode.
MODEL_EXTRA = [("sherlock", "Sherlock"), ("moriarty", "Moriarty")]


def dev_mode():
    """Developer mode: "dev": true in config.json (or the environment variable CSR_DEV=1)."""
    return os.environ.get("CSR_DEV") == "1" or bool(load_config().get("dev"))


def dev_forced_roles():
    """Picked killer and target (developer mode): {"killer": ..., "target": ...} or None (random)."""
    if not dev_mode():
        return None
    cfg = load_config()
    f = {"killer": str(cfg.get("dev_killer") or "") or None, "target": str(cfg.get("dev_target") or "") or None}
    return f if any(f.values()) else None


def model_targets():
    """The models that can be used: the characters, your own models (.glb) and, in developer mode,
    Sherlock and Moriarty."""
    custom = [(CUSTOM_PREFIX + n, n) for n in custom_models()]
    return list(MODEL_SLOTS) + custom + (list(MODEL_EXTRA) if dev_mode() else [])


def model_swaps():
    """{slot: model} picked in the launcher (only those that change something and are available)."""
    sw = load_config().get("model_swaps") or {}
    valid = {k for k, _ in MODEL_SLOTS} | {k for k, _ in model_targets()}
    return {k: v for k, v in sw.items() if k in valid and v in valid and k != v}


# ---------------------------------------------------------------- own models (.glb)
# Each .glb in the models folder is a model that can be put on a character ("custom:<name>"). The plugin
# writes each character's skeleton (bones only) to csr_live/skeletons and here it is copied to models/skeletons
# to build the model on top of it in Blender.
CUSTOM_PREFIX = "custom:"
SKELETON_DIR = "skeletons"




def models_dir():
    """Your 3D models (mods/models): one .glb per model. The first time it is created with some instructions and the
    skeletons folder."""
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
    """{name: file} of your models: each .glb or .fbx in the models folder, and each subfolder with a model
    inside (that way an .fbx can come with its textures next to it; if there are several, the biggest)."""
    out = {}
    try:
        d = models_dir()
        for f in os.listdir(d):
            p = os.path.join(d, f)
            stem, ext = os.path.splitext(f)
            if os.path.isfile(p) and ext.lower() in MODEL_EXTS:
                if stem not in out or ext.lower() == ".fbx":        # same name as .glb and .fbx: the .fbx
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
    """Names of your own models, in order."""
    return sorted(custom_sources(), key=str.lower)


# warnings from each model's last trip to the game: {name: text} (it couldn't be converted, textures missing...)
model_issues = {}


def sync_skeletons(game_dir):
    """Copies the skeletons the plugin wrote to the models folder (skeletons). Returns how many there are."""
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
    """Copies the picked own models to the game (csr_live/models) and removes the ones no longer used."""
    want = {v[len(CUSTOM_PREFIX):] for v in swaps.values() if v.startswith(CUSTOM_PREFIX)}
    return _sync_files(os.path.join(live_dir(game_dir), "models"), want, custom_sources(), model_issues)


def _file_sig(path):
    st = os.stat(path)
    return "%s|%d|%d" % (os.path.basename(path), st.st_size, int(st.st_mtime))


def built_glb(name, src, issues):
    """The .glb of a model or animation of yours: the same file if it already is a .glb, or the converted .fbx (kept
    in models_cache and only converted again if it changes). None if it couldn't be done."""
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
    except Exception as e:                                           # noqa: BLE001 (an odd file doesn't bring anything down)
        logging.getLogger("crimesight").warning("No pude preparar el modelo %s: %s", name, e)
        key = getattr(e, "key", None)
        issues[name] = t("models_convert_error", err=t("models_" + key) if key else e)
        try:
            os.remove(b + ".part")
        except OSError:
            pass
        return None


SHARE_MAX_TEXTURE = 2048      # the plugin never uses more (TexDec scales bigger textures down to this)


def slim_glb_bytes(data, max_side=SHARE_MAX_TEXTURE):
    """The same .glb with its embedded textures scaled down to max_side (PNG, so the plugin still decodes them off
    the game thread). Returns the original bytes if nothing needs it or the file can't be read."""
    import io
    import struct
    try:
        from PIL import Image
        if data[:4] != b"glTF" or len(data) < 28:
            return data
        jlen, jtype = struct.unpack_from("<II", data, 12)
        if jtype != 0x4E4F534A:
            return data
        doc = json.loads(data[20:20 + jlen])
        p = 20 + jlen
        if p + 8 > len(data):
            return data
        blen, btype = struct.unpack_from("<II", data, p)
        if btype != 0x004E4942:
            return data
        binc = data[p + 8:p + 8 + blen]
        views = doc.get("bufferViews") or []
        new = {}
        for im in doc.get("images") or []:
            vi = im.get("bufferView")
            if not isinstance(vi, int) or vi >= len(views) or views[vi].get("buffer", 0) != 0:
                continue
            v = views[vi]
            raw = binc[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]]
            img = Image.open(io.BytesIO(raw))
            if max(img.size) <= max_side:
                continue
            k = max_side / max(img.size)
            img = img.convert("RGBA" if "A" in img.getbands() or img.mode == "P" else "RGB")
            img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
            out = io.BytesIO()
            img.save(out, "PNG", compress_level=9)
            if out.tell() < len(raw):
                new[vi] = out.getvalue()
                im["mimeType"] = "image/png"
        if not new:
            return data
        # the binary chunk again: every view in its order, each one aligned to 4 bytes
        buf = bytearray()
        order = sorted(range(len(views)), key=lambda i: views[i].get("byteOffset", 0))
        for i in order:
            v = views[i]
            if v.get("buffer", 0) != 0:
                continue
            chunk = new.get(i) or binc[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]]
            buf += b"\0" * (-len(buf) % 4)
            v["byteOffset"] = len(buf)
            v["byteLength"] = len(chunk)
            buf += chunk
        buf += b"\0" * (-len(buf) % 4)
        doc["buffers"][0]["byteLength"] = len(buf)
        js = json.dumps(doc, separators=(",", ":")).encode("utf-8")
        js += b" " * (-len(js) % 4)
        body = struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(buf), 0x004E4942) + bytes(buf)
        return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body
    except Exception as e:                                           # noqa: BLE001 (the full file still works)
        logging.getLogger("crimesight").warning("No pude reducir las texturas del modelo: %s", e)
        return data


def shared_glb(path):
    """The file of one of your models that goes to the rooms: with its textures at most SHARE_MAX_TEXTURE (a 4096
    texture is 4 times the bytes and the game shows it at 2048 anyway). Kept in models_cache."""
    d = os.path.join(app_dir(), "models_cache")
    try:
        os.makedirs(d, exist_ok=True)
        b = os.path.join(d, hashlib.sha1(("share|" + os.path.abspath(path)).encode("utf-8")).hexdigest()[:10] + ".glb")
        sig = "%d|%s" % (SHARE_MAX_TEXTURE, _file_sig(path))
        try:
            with open(b + ".src", encoding="utf-8") as f:
                if f.read() == sig:
                    return b if os.path.isfile(b) else path     # no file: the original was already fine
        except OSError:
            pass
        with open(path, "rb") as f:
            data = f.read()
        slim = slim_glb_bytes(data)
        if slim is data:
            if os.path.isfile(b):
                os.remove(b)
            with open(b + ".src", "w", encoding="utf-8") as f:
                f.write(sig)
            return path
        with open(b + ".part", "wb") as f:
            f.write(slim)
        os.replace(b + ".part", b)
        with open(b + ".src", "w", encoding="utf-8") as f:
            f.write(sig)
        return b
    except OSError:
        return path


def _sync_files(d, want, sources, issues):
    """Leaves in d one .glb per name in want (copied, or converted if it is an .fbx) and removes the rest."""
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


# ---------------------------------------------------------------- own animations
# Each .fbx/.glb in models/animations is an animation (the first one it has) that can replace a character's idle,
# walk or run. The plugin adapts it to its skeleton (CrimeSightRevivalAnims.cs).
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
    """{slot: {idle|walk|run: animation}} (only the ones that exist)."""
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
    write_config(cfg)


# ---------------------------------------------------------------- new characters (slots)
# A new character doesn't replace anyone: it joins each match's draw (Character Selection). It has its
# model and, if you want, its animations, its name, its image and its lines; whatever it lacks comes from the
# character
# whose place it takes (also its way of playing). If it comes out as the traitor, only the model and the animations
# count.
IMAGE_DIR = "images"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
TALK_KEYS = ("cannotGetAnything", "damagedByGasRoom", "dangerHasInvaded", "destroySwitchboard", "discoverBypass",
             "discoverNote", "discoverSwitchboard", "fullItem", "fullWeapon", "getFood", "getMedicine", "getWeapon",
             "killCheckKillerEachOther", "killCheckKillerOnlyOne", "killCheckTarget", "pawnGameStart", "raid",
             "raidFinalDay", "recoveredByOtherUsingMedicine", "repairSwitchboard", "startAction_statusDying",
             "startAction_statusHunger", "startAction_statusInjury", "stepIntoBlackoutRoom", "useBypass",
             "useFoodForOther", "useMedicineForMyself", "useMedicineForOther")

# the face the character makes in each line, in the game (the same for all six): worried or attacked; the rest, normal
TALK_REACTION = {"damagedByGasRoom": "worried", "dangerHasInvaded": "worried", "startAction_statusDying": "worried",
                 "startAction_statusHunger": "worried", "startAction_statusInjury": "worried",
                 "raid": "attacked", "raidFinalDay": "attacked"}
REACTIONS = ("worried", "attacked")


def _talk_img(v):
    """Images of the lines: per reaction ("@worried", "@attacked") and per line (the ones in TALK_KEYS)."""
    out = {}
    for k, name in (v or {}).items():
        if name and (k in TALK_KEYS or (k.startswith("@") and k[1:] in REACTIONS)):
            out[k] = str(name)
    return out


def talk_image_for(c_imgs, sit, main):
    """The image of a line: its own, otherwise its reaction's, otherwise the main one."""
    return c_imgs.get(sit) or c_imgs.get("@" + TALK_REACTION.get(sit, "")) or main


def images_dir():
    d = os.path.join(models_dir(), IMAGE_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def custom_images():
    """{name: file} of the images for the new characters (images folder)."""
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
    """Which game character a new character takes its animations from (Agatha if not said)."""
    return v if v in CHAR_PAWNS else CHAR_PAWNS[0]


def _char_active(c, off=None):
    """A new character is shared with rooms only while it is switched on in the launcher (on by default)."""
    v = c.get("active")
    return bool(v) if isinstance(v, bool) else True


def characters():
    """Your new characters (config "characters"), with whatever is missing removed."""
    out = []
    cfg = load_config()
    off = set(cfg.get("roster_disabled") or [])
    for c in cfg.get("characters") or []:
        if not isinstance(c, dict) or not re.match(r"^[a-z0-9]{10}$", str(c.get("id", ""))):
            continue
        out.append({"id": c["id"], "name": str(c.get("name") or "")[:24], "role": "pawn",       # traitors: later on
                    "active": _char_active(c, off),
                    "anim_from": _anim_from(c.get("anim_from")),
                    "model": str(c.get("model") or ""), "image": str(c.get("image") or ""),
                    "talk_img": _talk_img(c.get("talk_img")),
                    "anims": {k: v for k, v in (c.get("anims") or {}).items() if k in ANIM_KINDS and v},
                    "talk": {k: str(v)[:240] for k, v in (c.get("talk") or {}).items() if k in TALK_KEYS and str(v).strip()}})
    return out


def save_character(c):
    """Creates or changes a new character. Returns its id."""
    import secrets
    cfg = load_config()
    lst = [x for x in (cfg.get("characters") or []) if isinstance(x, dict)]
    cid = str(c.get("id") or "")
    if not re.match(r"^[a-z0-9]{10}$", cid):
        cid = secrets.token_hex(5)
    entry = {"id": cid, "name": str(c.get("name") or "").strip()[:24], "role": "pawn", "anim_from": _anim_from(c.get("anim_from")),
             "model": str(c.get("model") or ""), "image": str(c.get("image") or ""), "talk_img": _talk_img(c.get("talk_img")),
             "anims": {k: v for k, v in (c.get("anims") or {}).items() if k in ANIM_KINDS and v},
             "talk": {k: str(v).strip()[:240] for k, v in (c.get("talk") or {}).items() if k in TALK_KEYS and str(v).strip()}}
    old = next((x for x in lst if x.get("id") == cid), None)
    # a new character of yours: switched on in the launcher (shared with the rooms) but unticked in the game's
    # Character Selection, like the ones other players bring (server ModelRoom._build): you tick it when you want it.
    entry["active"] = _char_active(old) if old else True
    if not old:
        off = [x for x in (cfg.get("roster_disabled") or []) if x != cid]
        cfg["roster_disabled"] = off + [cid]
    lst = [x for x in lst if x.get("id") != cid] + [entry]
    cfg["characters"] = lst
    write_config(cfg)
    return cid


def set_character_active(cid, on):
    """Switches a new character on (shared with rooms; ticking it in the game's Character Selection is separate)
    or off (not shared, so its files are never uploaded)."""
    cfg = load_config()
    for x in cfg.get("characters") or []:
        if isinstance(x, dict) and x.get("id") == cid:
            x["active"] = bool(on)
    write_config(cfg)


def delete_character(cid):
    cfg = load_config()
    cfg["characters"] = [x for x in (cfg.get("characters") or []) if isinstance(x, dict) and x.get("id") != cid]
    cfg["roster_disabled"] = [x for x in (cfg.get("roster_disabled") or []) if x != cid]
    write_config(cfg)


def _image_file(name, src):
    """The image as it is if it is PNG or JPG; otherwise, converted to PNG (in models_cache)."""
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
    write_config(cfg)
    return model_swaps()


def install_models(game_dir):
    """Writes to the plugin's folder which character is seen with which model. True if something changed."""
    if not game_dir or not live_mode(game_dir):
        return False
    d = live_dir(game_dir)
    os.makedirs(d, exist_ok=True)
    if room_models is not None:                         # in a room: the room's (yours put aside for a while)
        swaps, anims, msrc, asrc = _room_install_set(room_models, room_roster)
        copied = _sync_files(os.path.join(d, "models"), set(msrc), msrc, model_issues)
        copied = _sync_files(os.path.join(d, "anims"), set(asrc), asrc, anim_issues) or copied
        copied = _install_roster(d, room_models, room_roster) or copied
    else:
        on = mods_enabled()                             # your mods folder switched off: the game's own models
        swaps = model_swaps() if on else {}
        anims = anim_swaps() if on else {}
        copied = _install_custom_models(game_dir, swaps)    # before models.json: the plugin reads the file when it sees it
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


# ---------------------------------------------------------------- room models (like the stickers)
# The host shares their models and animations with their room, and the guests' ones they accept fill the
# free characters. Whoever joins downloads them (only the files they don't have, by their sha256) to models_room,
# which
# is deleted at the end; meanwhile the game sees the room's and yours come back on leaving.
room_models = None          # None: yours. Otherwise: {"hash", "swaps", "anims", "chars", "files": {sha: {"kind", "path"}}}
room_roster = None          # character draw of the ongoing match (from the server) or None
room_disabled = []          # characters turned off in the room's Character Selection
room_disabled_fn = None     # host: the room server's live list (includes guests' characters, unticked on arrival)
room_host = False           # True if this PC decides the Selection (host or solo)
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
    """Your models and animations in the room format: the files by their sha256 (with their path on this PC).
    Sherlock and Moriarty (developer mode) are not shared."""
    import modelpack
    ms = modelpack.empty()
    if not mods_enabled():                  # your mods folder is switched off: nothing to share
        return ms
    slots = {k for k, _ in MODEL_SLOTS}
    msrc, asrc = custom_sources(), anim_sources()

    def add(kind, name, src, issues):
        path = built_glb(name, src, issues)
        if not path:
            return None
        if kind == "model":
            path = shared_glb(path)
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
        if not c["active"]:                 # switched off in the launcher: not shared (nothing is uploaded)
            continue
        model = add("model", c["model"], msrc.get(c["model"]), model_issues) if c["model"] else None
        if not model:
            continue
        entry = {"name": c["name"], "role": c["role"], "anim_from": c["anim_from"], "model": model, "anims": {}, "talk": dict(c["talk"])}
        for kind, name in c["anims"].items():
            ref = add("anim", name, asrc.get(name), anim_issues)
            if ref:
                entry["anims"][kind] = ref

        def add_image(name):
            img = _image_file(name, isrc.get(name)) if name else None
            if not img or os.path.getsize(img) > modelpack.MAX_IMAGE_BYTES:
                return None
            sha = _sha256_file(img)
            ms["files"][sha] = {"kind": "image", "size": os.path.getsize(img), "name": name, "path": img}
            return modelpack.FILE_PREFIX + sha
        ref = add_image(c["image"])
        if ref:
            entry["image"] = ref
        timg = {k: r for k, r in ((k, add_image(n)) for k, n in c["talk_img"].items()) if r}
        if timg:
            entry["talk_img"] = timg
        ms["chars"][c["id"]] = entry
    ms["hash"] = modelpack.set_hash(ms)
    return ms


def _room_install_set(rm, roster=None):
    """What is written to the game for a room's model set: rm_<sha> names for its files. With the
    match's draw, each place with a new character gets its model and its animations (or the game's)."""
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
    for c in chars.values():                       # all its models in the game (to see them in the selector)
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
        anims.pop(slot, None)                      # no own animations: the game's
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
    """Outside a room there is no draw or Character Selection: the game goes back to its characters."""
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
    """For the plugin: roster.json (which name, lines and image each place has in this match) and
    roster_pool.json (every character, for the Character Selection). Copies the images."""
    import modelpack
    chars = (rm or {}).get("chars", {})
    files = (rm or {}).get("files", {})
    idir = os.path.join(d, "images")
    want = {}
    for c in chars.values():
        for v in [c.get("image")] + list((c.get("talk_img") or {}).values()):
            sha = (v or "")[len(modelpack.FILE_PREFIX):]
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

    def image_of(c, v=None):
        sha = ((c.get("image") if v is None else v) or "")[len(modelpack.FILE_PREFIX):]
        for name in want:
            if sha and name.startswith(sha[:16]):
                return "images/" + name
        return None

    def talk_images(c):
        """The image of each line that doesn't use the main one (per line or per the reaction it shows in the game)."""
        timg = c.get("talk_img") or {}
        out = {}
        for sit in TALK_KEYS:
            v = talk_image_for(timg, sit, None)
            path = image_of(c, v) if v else None
            if path:
                out[sit] = path
        return out

    def model_of(c):
        sha = (c.get("model") or "")[len(modelpack.FILE_PREFIX):]
        return ROOM_PREFIX + sha[:16] if sha else None

    def entry(cid):
        c = chars.get(cid) if cid else None
        if not c:
            return None
        return {"id": cid, "name": c.get("name") or None, "talk": dict(c.get("talk") or {}), "image": image_of(c),
                "talk_images": talk_images(c), "model": model_of(c), "anim_from": _anim_from(c.get("anim_from"))}
    out = {"id": (roster or {}).get("id", ""), "positions": {}, "traitor": None}
    if roster:
        out["positions"] = {k: entry(v) for k, v in (roster.get("positions") or {}).items()}
        out["traitor"] = entry(roster.get("traitor"))
    changed = _write_json_if_changed(os.path.join(d, "roster.json"), out)
    try:
        disabled = set(room_disabled_fn() if room_disabled_fn else (room_disabled or []))
    except Exception:                                                # noqa: BLE001
        disabled = set(room_disabled or [])
    items = [{"id": "orig:" + k, "key": k, "role": "pawn", "enabled": "orig:" + k not in disabled} for k in modelpack.PAWNS]
    for cid, c in sorted(chars.items(), key=lambda kv: (kv[1].get("name") or "").lower()):
        if c.get("role", "pawn") != "pawn":                     # the traitor isn't in the Selection (yet)
            continue
        items.append({"id": cid, "role": "pawn", "name": c.get("name") or "", "image": image_of(c),
                      "model": model_of(c), "anim_from": _anim_from(c.get("anim_from")), "enabled": cid not in disabled})
    pool = {"host": bool(room_host), "min": modelpack.MIN_PAWNS, "items": modelpack.fill_enabled(items)}
    return _write_json_if_changed(os.path.join(d, "roster_pool.json"), pool) or changed


def _http(url, password, data=None, method=None, headers=None, timeout=60):
    h = {"X-CSR-Password": password or ""}
    h.update(headers or {})
    return urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=h), timeout=timeout)


def download_models(url, password, expected_hash, progress=None):
    """Downloads the room's models (only the files you don't have yet) and returns the local model set."""
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
    if missing:
        # your own files (the ones you just offered to the room) are copied from this PC, not downloaded again
        try:
            own = {s: f["path"] for s, f in my_model_set()["files"].items() if s in missing}
        except Exception:                                            # noqa: BLE001 (then they are downloaded)
            own = {}
        for sha, src in own.items():
            try:
                shutil.copyfile(src, os.path.join(d, sha + ".glb.part"))
                if _sha256_file(os.path.join(d, sha + ".glb.part")) == sha:
                    os.replace(os.path.join(d, sha + ".glb.part"), os.path.join(d, sha + ".glb"))
                    missing.remove(sha)
            except OSError:
                pass
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
    """Character draw of your match on that server and the room's turned-off characters.
    Also the room's id and whether you created it: (roster, disabled, room id, owner)."""
    try:
        with urllib.request.urlopen(url + "/revival/roster?platform_id=" + str(steam_id or ""), timeout=6) as r:
            a = json.loads(r.read(1 << 20))
        return a.get("roster"), list(a.get("disabled") or []), a.get("room"), a.get("owner") is True
    except (urllib.error.URLError, OSError, ValueError):
        return "error", [], None, False


SERVERS_URL = "https://raw.githubusercontent.com/{repo}/main/servers.json"
MAX_PUBLIC_SERVERS = 20


def fetch_public_servers(timeout=8):
    """The community servers listed in servers.json on GitHub (edited there, no new launcher needed).
    Returns the list, or None if it couldn't be read (the launcher keeps the last one it got)."""
    from version import REPO
    req = urllib.request.Request(SERVERS_URL.format(repo=REPO), headers={"User-Agent": "CrimeSightRevival-Launcher"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read(64 * 1024))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    servers = data.get("servers") if isinstance(data, dict) else None
    if not isinstance(servers, list):
        return None
    out = []
    for s in servers:
        if not isinstance(s, dict):
            continue
        name, address = str(s.get("name") or "").strip()[:60], str(s.get("address") or "").strip()[:200]
        if name and address:
            out.append({"name": name, "address": address, "password": str(s.get("password") or "")[:100]})
    return out[:MAX_PUBLIC_SERVERS]


def server_list(cfg):
    """Servers shown under "Custom server": the community ones first (marked "official"), then your own.
    A community server you saved yourself (same name or address) only shows once, as yours."""
    own = [s for s in (cfg.get("servers") or []) if isinstance(s, dict)]
    names = {s.get("name") for s in own}
    addrs = {str(s.get("address") or "").strip().lower() for s in own}
    public = [dict(s, official=True) for s in (cfg.get("public_servers") or [])
              if isinstance(s, dict) and s.get("name") not in names and str(s.get("address") or "").strip().lower() not in addrs]
    return public + own


def roster_select(url, password, steam_id, disabled):
    """Sends your Character Selection for the room you created on that server. Returns the room's list,
    or None if the server didn't take it (older server, or you're not the room's creator)."""
    body = json.dumps({"platform_id": str(steam_id or ""), "disabled": list(disabled or [])}).encode("utf-8")
    try:
        with _http(url + "/revival/roster/select", password, data=body, method="POST", timeout=6,
                   headers={"Content-Type": "application/json"}) as r:
            return list(json.loads(r.read(1 << 20)).get("disabled") or [])
    except (urllib.error.URLError, OSError, ValueError):
        return None


def roster_answer(game_dir):
    """What the host ticked in the game's Character Selection: (n, disabled) or None."""
    try:
        with open(os.path.join(live_dir(game_dir), "roster_select.json"), encoding="utf-8") as f:
            a = json.load(f)
        return int(a.get("n", 0)), [str(x) for x in (a.get("disabled") or [])]
    except (OSError, ValueError, TypeError):
        return None


def offer_models(url, password, ms, player):
    """Offers your models to the host (only the list). Returns (state, id, files it asks for)."""
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
        if e.code == 404:                  # server from an older version
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
    """Uploads to the host the files it asked for from your accepted offer."""
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
            if e.code != 409:              # 409: it already had it
                raise ValueError(t("models_upload_failed", err=e.code))
        except (urllib.error.URLError, OSError) as e:
            raise ValueError(t("models_upload_failed", err=getattr(e, "reason", e)))


def live_dir(game_dir):
    """Folder the plugin watches: inside BepInEx, in the game folder. That way it works the same on
    Windows and with Proton (where the game sees another user folder, Wine's)."""
    return os.path.join(game_dir, "BepInEx", "csr_live")


def bepinex_state(game_dir):
    """installed: BepInEx in the game folder; plugin: our plugin inside; ready: it has started
    once (it generated its files; the first time it takes a minute)."""
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
    """Downloads BepInEx (the official mod loader, from its GitHub) and puts it in the game
    folder next to our plugin. It doesn't ship inside the launcher: the launcher installs it on its own at startup (unless
    the player removed it)."""
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
    modinject.restore(game_dir, fix=False)   # with the plugin, the game files go back to being the original ones
    return True


def _sha_ok(path):
    """The zip is exactly the official one (same SHA-256 fingerprint)."""
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
        # plan B: Windows' downloader (it gets the missing certificates on its own)
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
    """No BepInEx console window (the log is still in BepInEx/LogOutput.log)."""
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
    """If the launcher brings a new version of the plugin, it copies it."""
    if not live_mode(game_dir):
        return False
    src, dst = _plugin_source(), os.path.join(game_dir, "BepInEx", "plugins", PLUGIN_NAME)
    with open(src, "rb") as a, open(dst, "rb") as b:
        if a.read() == b.read():
            return False
    shutil.copy2(src, dst)
    return True


def uninstall_bepinex(game_dir):
    """Removes BepInEx from the game folder (everything its zip brings)."""
    for name in BEPINEX_FILES:
        p = os.path.join(game_dir, name)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p):
            os.remove(p)
    old = os.path.join(app_dir(), "mods_live")          # old place (earlier versions)
    if os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)
    return True


def write_live(rs, game_dir):
    """Writes the mod set for the plugin: images already fitted + live.json."""
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
        # only if it changes: the plugin reuses what doesn't change (otherwise the chosen avatar would be lost)
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
    for name in os.listdir(d):                  # images from an earlier set
        if name.endswith(".png") and name not in files:
            try:
                os.remove(os.path.join(d, name))
            except OSError:
                pass
    return True


def offer_prompt(game_dir, oid, title, body, yes, no, always=""):
    """Notice inside the game about a guest's mods: the plugin shows it with two buttons and writes
    the answer in offer_answer.json (the host is usually in the game, not in the launcher)."""
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
    """True/False ("always" if they chose to always accept) if it was answered from the game; None if not yet."""
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
    """Downloads a server's mod pack and saves it as temporary mods."""
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
    """Offers your mods to the room's host. Returns 'pending', 'accepted', 'known' or 'ignored'."""
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
        if e.code == 404:          # server from an older version
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


# ------------------------------------------------------------------ profiles
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
    """{w, d, l, p}: wins, draws, losses and points from the local record."""
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
    """Your ongoing match on that server ({"role", "match_id", ...} or None). ValueError if it doesn't answer."""
    try:
        with urllib.request.urlopen(f"{url}/revival/match?platform_id={steam_id}", timeout=timeout) as r:
            return json.load(r).get("match")
    except urllib.error.HTTPError as e:
        if e.code == 404:              # host with a version without this
            return None
        raise ValueError(str(e))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ValueError(str(e))


def internet_ok(timeout=5):
    """True if there is internet (so as not to count a match as won if the one who lost the connection is you)."""
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
    """The host disappeared mid-match: it counts as a win for you. Returns the points.
    It has the same match id as on the server, so it is never written twice."""
    import stats
    st = _store()
    user = _local_user(st, steam_id)
    pts = stats.record_match(user, int(state.get("role", 0)), "win", (), state.get("stage", ""),
                             match_id=state.get("match_id") or None, level=state.get("level") or "online")
    st.save()
    return pts


def _local_user(st, steam_id):
    """The local profile of that Steam account (created if it hasn't played yet)."""
    import server
    pid, token = server.derived_ids(3, steam_id)
    user = st.db["users"].setdefault(pid, {"name": "", "progress": 0, "tutorial_step": 0, "config": {},
                                           "created": int(time.time())})
    st.db["accounts"].setdefault(f"3:{steam_id}", {"player_id": pid, "token": token, "platform": 3,
                                                  "platform_id": steam_id, "country": ""})
    return user


def sync_profile(url, steam_id, password=""):
    """Uploads the local profile, gets the server's already merged and merges it here. Returns the record."""
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


# ------------------------------------------------------------------ stage creator
STAGE_BASES = ("Stage_Yokn", "Stage_Yokn_v1030", "Stage_Yokn_v1040", "Stage_Yokn_v1050", "Stage_Yokn_v1060")
_stage_cat = {}


def stages_dir():
    """Layouts saved by the player (one .json per stage), in mods/stages."""
    return _in_mods("stages")


def stage_cache_dir():
    return os.path.join(app_dir(), "stage_cache")


def stage_catalog(game_dir, progress=None):
    """The stages' pieces, read from the player's copy of the game (cached)."""
    import stagedata
    dev = os.environ.get("CSR_STAGE_CATALOG")          # tests without the game
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
    """Fingerprint of a layout (the same the server works out)."""
    import stageroom
    return stageroom.layout_hash(layout)


def stage_list(disabled=()):
    """Saved stages. enabled: it shows in the game's stage list."""
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
    """Saves a layout. Without sid, the file name comes from the name (and overwrites the one with the same name)."""
    sid = sid or _stage_slug(layout.get("name"))
    _write_json(os.path.join(stages_dir(), sid + ".json"), layout)
    return sid


def stage_delete(sid):
    p = os.path.join(stages_dir(), os.path.basename(str(sid)) + ".json")
    if os.path.isfile(p):
        os.remove(p)


def stage_own(disabled=()):
    """Your active stages, as the room needs them: [{"id": "Stage_CSR_<id>", "name", "layout"}]."""
    out = []
    for it in stage_list(disabled):
        if it["enabled"] and len(out) < MAX_GAME_STAGES:
            try:
                out.append({"id": STAGE_PREFIX + it["id"], "name": it["name"], "layout": stage_load(it["id"])})
            except (OSError, ValueError):
                continue
    return out


# ---- sharing: .csrstage file
STAGE_EXT = ".csrstage"
STAGE_FILE_FORMAT = "crimesight-revival-stage"


def stage_export(sid, path):
    _write_json(path, {"format": STAGE_FILE_FORMAT, "version": 1, "layout": stage_load(sid)})


def stage_import(path, cat):
    """Adds the one in a .csrstage file to your stages. Returns its id."""
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


# ---- stages in the room (like the mods: the host offers them and each player downloads them)
def stage_room_fetch(url, password, timeout=20):
    req = urllib.request.Request(url + "/revival/stages", headers={"X-CSR-Password": password or ""})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, ValueError) as e:
        raise ValueError(t("err_unexpected", err=e))
    return [s for s in data.get("stages") or [] if isinstance(s, dict) and isinstance(s.get("layout"), dict)]


def stage_report(url, password, steam_id, have, seen="", timeout=10):
    """Tells the server which stages your game has ready (without that it doesn't let them be played) and which
    room list it synced with (seen), so it knows whether it still waits for you or you can't have them."""
    if not steam_id:
        return False
    body = json.dumps({"platform": 3, "platform_id": str(steam_id), "have": have, "seen": seen or ""}).encode()
    req = urllib.request.Request(url + "/revival/stages/have", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "X-CSR-Password": password or ""})
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except (urllib.error.URLError, ValueError):
        return False              # server from an older version


STAGE_TEST_FILE = "layout_test.json"


def stage_test(game_dir, cat, layout):
    """Leaves the layout ready to play in the "Test stage (CSR)" (needs the plugin)."""
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
    with _stage_lock:                  # called by the window and by the running session
        return _stage_publish(game_dir, stages, cat)


def _stage_publish(game_dir, stages, cat=None):
    """Leaves those stages in the plugin's folder ([{"id", "name", "layout"}]): each one shows in the
    game's stage list as a new one. The ones with errors are not published.
    Returns {id: fingerprint} of the ones left ready."""
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
            continue                                   # with errors (or from another version): not published
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
    """Name of the layout that will be played in the test stage ("" if it is the copy of 01)."""
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


# ------------------------------------------------------------------ progress backups
SAVE_FORMAT = "crimesight-revival-save"
SAVE_EXT = ".csrsave"


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def export_save(steam_id, path):
    """Saves all of that account's progress in a file the player can take along."""
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
    """Merges a progress file with the local one. It only adds: it never duplicates or deletes matches.
    Returns how many new matches it brought."""
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
    """Automatic backup in the folder the player chose (OneDrive, Google Drive...).
    First it picks up whatever another PC left there and then it writes the merged copy.
    Returns the new matches it brought, or None if no folder was chosen."""
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
