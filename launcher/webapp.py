"""
CRIMESIGHT Revival - lanzador con interfaz grafica (HTML con pywebview / WebView2).

En Windows va en su propia ventana; en Linux / Steam Deck la misma interfaz se abre en el
navegador (browserui.py). Si nada de eso funciona, se abre la interfaz sencilla (app.py).
Este proyecto solo ofrece la herramienta; no gestiona ni aloja servidores.
"""
import json, logging, os, re, sys, threading, traceback, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core  # noqa: E402
import art  # noqa: E402
import i18n  # noqa: E402
import sessions  # noqa: E402
import updater  # noqa: E402
from i18n import t  # noqa: E402
from version import VERSION  # noqa: E402

KOFI = "https://ko-fi.com/amrasmithandir95"
SAVE_FILTER = "CRIMESIGHT Revival (*.csrsave)"
ALL_FILTER = "All files (*.*)"
# Tipos de dialogo de pywebview (iguales en 5.x y 6.x; los nombres antiguos estan obsoletos)
DIALOGS = {"OPEN_DIALOG": 10, "FOLDER_DIALOG": 20, "SAVE_DIALOG": 30}

UI_DIR = os.path.join(getattr(sys, "_MEIPASS", HERE), "ui")
_window = None
_browser = False          # Linux / Steam Deck: la interfaz va en el navegador


def js(fn, *args):
    if _browser:
        import browserui
        browserui.push(fn, *args)
        return
    if _window is not None:
        try:
            _window.evaluate_js(f"ui.{fn}({','.join(json.dumps(a, ensure_ascii=False) for a in args)})")
        except Exception:  # noqa: BLE001
            pass


class Api:
    """Metodos que la interfaz llama con window.pywebview.api.<metodo>()."""

    def __init__(self):
        self._cfg = core.load_config()
        self._steam = (None, "")
        self._busy = False
        self._cancel = False
        self._mods_answer = None
        self._mods_event = threading.Event()

    # ---------------------------------------------------------------- estado
    def init(self):
        imported = core.import_old_data()
        self._steam = core.steam_account()
        if not core.is_game_dir(self._cfg.get("game_dir")):
            self._cfg["game_dir"] = core.find_game()
            core.save_config(self._cfg)
        gd = self._cfg.get("game_dir")
        self._update_lang()
        self._self_update()
        try:
            core.mods_dir()               # la carpeta de mods ya preparada desde el principio
        except OSError:
            pass
        if gd and not art.ready(core.app_dir()):
            js("loading", t("loading_art"))
            try:
                art.extract(gd, core.app_dir())
            except Exception:  # noqa: BLE001
                logging.getLogger("crimesight").exception("No pude sacar las ilustraciones")
        notice = t("notice_imported") if imported else None
        try:
            added = core.backup_now(self._cfg, self._steam[0])
            if added:
                notice = t("backup_restored", n=added)
        except ValueError as e:
            notice = str(e)
        except Exception:  # noqa: BLE001
            logging.getLogger("crimesight").exception("Fallo la copia automatica al arrancar")
        state = self._state()
        if notice:
            state["notice"] = notice
        return state

    def _self_update(self):
        """Si hay una version nueva del lanzador en GitHub, se instala y se vuelve a abrir."""
        updater.cleanup_old()
        upd = updater.check()
        if not upd:
            return
        js("loading", t("updating", v=upd["version"]))
        try:
            updater.apply(upd, progress=lambda pct: js("loading", t("updating", v=upd["version"]) + f"  {pct}%"))
        except Exception as e:  # noqa: BLE001
            logging.getLogger("crimesight").warning("Actualizacion fallida: %s", e)
            js("loading", t("update_failed", err=e))

    def _update_lang(self):
        i18n.set_lang(core.game_language(self._cfg.get("game_dir"), self._steam[0]))

    def _state(self, with_art=True):
        sid, name = self._steam
        st = {"account": name or (sid and f"Steam {sid}") or "", "steam_id": sid,
              "record": core.local_record(sid) if sid else {},
              "game_dir": self._cfg.get("game_dir"), "servers": self._cfg.get("servers", []),
              "port": self._cfg.get("port", core.DEFAULT_PORT), "last_friend": self._cfg.get("last_friend", ""),
              "lang": i18n.get_lang(), "i18n": i18n.table(), "version": VERSION, "kofi": KOFI,
              "backup_dir": self._cfg.get("backup_dir", "")}
        if with_art:
            st["art"] = art.data_urls(core.app_dir())
        return st

    # ---------------------------------------------------------------- sesiones
    def start(self, mode, args):
        if self._busy:
            return {"error": t("err_busy")}
        gd = self._cfg.get("game_dir")
        if not gd:
            return {"error": t("err_no_game")}
        if not self._steam[0]:
            self._steam = core.steam_account()
            if not self._steam[0]:
                return {"error": t("err_no_steam")}
        args = args or {}
        if mode in ("join", "server") and not (args.get("address") or "").strip():
            return {"error": t("err_no_address")}
        self._busy, self._cancel = True, False
        js("busy", True, t("title_" + mode))
        threading.Thread(target=self._run, args=(mode, args), daemon=True).start()
        return {"ok": True}

    def _run(self, mode, args):
        try:
            core.ensure_keys(self._cfg["game_dir"])
            if mode == "solo":
                sessions.solo(self, self._cfg)
            elif mode == "host":
                sessions.host(self, self._cfg, args.get("port"))
            else:
                sessions.join(self, self._cfg, self._steam[0], args.get("address", ""), args.get("password", ""))
        except ValueError as e:
            self.log(f"✗ {e}", "err")
            js("error", str(e))
        except Exception as e:  # noqa: BLE001
            self.log("✗ " + t("err_unexpected", err="".join(traceback.format_exception_only(type(e), e)).strip()), "err")
            logging.getLogger("crimesight").exception("Error en la sesion")
        finally:
            self._busy = False
            self._auto_backup()
            self._update_lang()          # el juego pudo cambiar de idioma durante la partida
            js("state", self._state(with_art=False))
            js("busy", False)

    def _auto_backup(self):
        try:
            if core.backup_now(self._cfg, self._steam[0]) is not None:
                self.log(t("backup_saved"), "ok")
        except Exception as e:  # noqa: BLE001
            self.log(t("backup_failed", err=e), "err")

    def stop(self):
        self._cancel = True
        self.log(t("stopping"))

    # contexto de sessions.py
    def log(self, text, kind=None):
        js("log", text, kind)

    def set_address(self, addr):
        js("address", addr)

    def cancelled(self):
        return self._cancel

    # ---------------------------------------------------------------- utilidades
    def copy(self, text):
        core.copy_to_clipboard(text or "")

    def open_url(self, url):
        if url.startswith(("https://github.com/", "https://x.com/", KOFI)):
            webbrowser.open(url)

    def pick_game(self):
        d = self._dialog("FOLDER_DIALOG")
        if not d:
            return None
        if not core.is_game_dir(d):
            js("error", t("err_bad_folder"))
            return None
        self._cfg["game_dir"] = os.path.normpath(d)
        core.save_config(self._cfg)
        self._update_lang()
        if not art.ready(core.app_dir()):
            try:
                art.extract(self._cfg["game_dir"], core.app_dir())
            except Exception:  # noqa: BLE001
                pass
        return self._state()

    def restore(self):
        if self._busy:
            return t("err_finish_first")
        gd = self._cfg.get("game_dir")
        if not gd:
            return None
        return t("restored") if core.restore_game(gd) else t("already_original")

    # ---------------------------------------------------------------- progreso
    def _dialog(self, kind, **kw):
        if _browser:
            import browserui
            return browserui.dialog(kind, save_filename=kw.get("save_filename"))
        res = _window.create_file_dialog(DIALOGS[kind], **kw)
        if not res:
            return None
        return res[0] if isinstance(res, (list, tuple)) else res

    def _need_account(self):
        if not self._steam[0]:
            self._steam = core.steam_account()
        if self._busy:
            return t("err_finish_first")
        if not self._steam[0]:
            return t("err_no_steam")
        return None

    def export_progress(self):
        err = self._need_account()
        if err:
            return {"msg": err}
        name = re.sub(r"[^\w.-]+", "_", self._steam[1] or "") or str(self._steam[0])
        path = self._dialog("SAVE_DIALOG", save_filename=f"CrimeSightRevival_{name}{core.SAVE_EXT}",
                            file_types=(SAVE_FILTER,))
        if not path:
            return None
        if not path.lower().endswith(core.SAVE_EXT):
            path += core.SAVE_EXT
        try:
            core.export_save(self._steam[0], path)
        except (OSError, ValueError) as e:
            return {"msg": t("err_save_write", err=e)}
        return {"msg": t("exported", path=path)}

    def import_progress(self):
        err = self._need_account()
        if err:
            return {"msg": err}
        path = self._dialog("OPEN_DIALOG", file_types=(SAVE_FILTER, ALL_FILTER))
        if not path:
            return None
        try:
            added = core.import_save(self._steam[0], path)
        except ValueError as e:
            return {"msg": str(e)}
        self._auto_backup()
        msg = t("imported", n=added) if added else t("import_nothing")
        return {"msg": msg, "state": self._state(with_art=False)}

    def pick_backup(self):
        err = self._need_account()
        if err:
            return {"msg": err}
        folder = self._dialog("FOLDER_DIALOG")
        if not folder:
            return None
        self._cfg["backup_dir"] = os.path.normpath(folder)
        core.save_config(self._cfg)
        try:
            added = core.backup_now(self._cfg, self._steam[0])
        except (OSError, ValueError) as e:
            return {"msg": t("backup_failed", err=e), "state": self._state(with_art=False)}
        msg = t("backup_restored", n=added) if added else t("backup_set")
        return {"msg": msg, "state": self._state(with_art=False)}

    def clear_backup(self):
        self._cfg.pop("backup_dir", None)
        core.save_config(self._cfg)
        return {"msg": t("backup_removed"), "state": self._state(with_art=False)}

    # ---------------------------------------------------------------- mods de apariencia
    def mods_list(self):
        import base64
        out = []
        for m in core.my_mods(self._cfg):
            imgs = [it["png"] for it in (m["stickers"] + m["avatars"])[:5]]
            out.append({"folder": os.path.basename(m["folder"]), "name": m["name"], "author": m["author"],
                        "stickers": len(m["stickers"]), "avatars": len(m["avatars"]), "enabled": m["enabled"],
                        "errors": len(m["errors"]),
                        "thumbs": ["data:image/png;base64," + base64.b64encode(p).decode() for p in imgs]})
        return {"dir": core.mods_dir(), "mods": out}

    def mods_stickers(self, folder):
        """Stickers de un mod con su mensaje, para editarlos desde el lanzador."""
        import base64, modpack
        m = modpack.load_mod(core.mod_folder(folder))
        out = []
        for it in m["stickers"]:
            cur = it.get("text") or ""
            if isinstance(cur, dict):            # textos por idioma puestos a mano en mod.json
                cur = cur.get(i18n.get_lang()) or next(iter(cur.values()), "")
            out.append({"key": it["key"], "default": it.get("default") or "",
                        "text": "" if cur == it.get("default") else cur,
                        "thumb": "data:image/png;base64," + base64.b64encode(it["png"]).decode()})
        return {"name": m["name"], "stickers": out}

    def mods_set_text(self, folder, key, text):
        import modpack
        try:
            return {"ok": True, "text": modpack.set_text(core.mod_folder(folder), key, text)}
        except (OSError, ValueError) as e:
            return {"error": str(e)}

    def mods_toggle(self, folder, on):
        off = [f for f in self._cfg.get("mods_disabled", []) if f != folder]
        if not on:
            off.append(folder)
        self._cfg["mods_disabled"] = off
        core.save_config(self._cfg)
        return True

    def mods_open(self):
        core.open_folder(core.mods_dir())

    # recarga en caliente (BepInEx, opcional)
    def bep_state(self):
        st = core.bepinex_state(self._cfg.get("game_dir"))
        st["busy"] = self._busy
        if not core.IS_WINDOWS:          # Linux / Steam Deck: Proton necesita una opcion de lanzamiento
            st["linux"] = True
            st["launch_ok"] = core.linux_launch_option_ok()
            st["launch_option"] = core.LINUX_LAUNCH_OPTION
        return st

    def bep_install(self):
        gd = self._cfg.get("game_dir")
        if not gd:
            return {"error": t("err_no_game")}
        if self._busy or core.game_running():
            return {"error": t("bep_busy")}
        self._busy = True

        def work():
            try:
                core.install_bepinex(gd, progress=lambda pct: js("bepProgress", t("bep_installing", pct=pct)))
                js("bepDone", t("bep_installed"))
            except ValueError as e:
                js("bepDone", str(e), True)
            except Exception as e:  # noqa: BLE001
                logging.getLogger("crimesight").exception("No pude instalar BepInEx")
                js("bepDone", t("err_unexpected", err=e), True)
            finally:
                self._busy = False
        threading.Thread(target=work, daemon=True).start()
        return {"ok": True}

    def bep_uninstall(self):
        gd = self._cfg.get("game_dir")
        if self._busy or core.game_running():
            return {"error": t("bep_busy")}
        try:
            core.uninstall_bepinex(gd)
        except OSError as e:
            return {"error": t("err_unexpected", err=e)}
        return {"ok": True, "msg": t("bep_removed")}

    def mods_new(self):
        folder = core.new_mod()
        core.open_folder(folder)
        return os.path.basename(folder)

    def answer_mods(self, ok):
        self._mods_answer = bool(ok)
        self._mods_event.set()

    # contexto de sessions.py: unirse a una sala con mods / un jugador trae mods a tu sala
    def _ask(self, fn, info):
        self._mods_answer = None
        self._mods_event.clear()
        js(fn, info)
        while not self._mods_event.wait(0.3):
            if self._cancel:
                return False
        return bool(self._mods_answer)

    def confirm_mods(self, info):
        return self._ask("confirmMods", info)

    def confirm_offer(self, info):
        return self._ask("confirmOffer", info)

    def save_server(self, name, address, password):
        name = (name or address or "").strip()
        if not name or not (address or "").strip():
            js("error", t("err_need_address"))
            return None
        self._cfg["servers"] = [s for s in self._cfg["servers"] if s["name"] != name]
        self._cfg["servers"].append({"name": name, "address": address.strip(), "password": password or ""})
        core.save_config(self._cfg)
        return self._state(with_art=False)

    def delete_server(self, name):
        self._cfg["servers"] = [s for s in self._cfg["servers"] if s["name"] != name]
        core.save_config(self._cfg)
        return self._state(with_art=False)


class _GuiLog(logging.Handler):
    """Lleva al lanzador, traducidas, las lineas del servidor que interesan al jugador."""

    def emit(self, record):
        msg = record.getMessage()
        text = i18n.server_event(msg)
        if text:
            js("log", "· " + text, "ok" if " GANA," in msg else None)


def main():
    global _window, _browser
    logging.getLogger("crimesight").addHandler(_GuiLog())
    try:
        core.setup_launcher_log()
    except OSError:
        pass
    logging.getLogger("crimesight").warning("Lanzador %s iniciado", VERSION)
    if not core.IS_WINDOWS or os.environ.get("CSR_BROWSER"):
        import browserui
        _browser = True
        api = Api()
        return browserui.serve(api, UI_DIR, busy=lambda: api._busy)
    try:
        import webview
    except ImportError:
        import app
        return app.main()
    api = Api()
    _window = webview.create_window("CRIMESIGHT Revival", os.path.join(UI_DIR, "index.html"), js_api=api,
                                    width=1280, height=780, min_size=(1100, 700), background_color="#07081a")
    try:
        webview.start(gui="edgechromium" if core.IS_WINDOWS else None, debug=False)
    except Exception:  # noqa: BLE001  (sin WebView2: interfaz sencilla)
        _window = None
        import app
        app.main()


if __name__ == "__main__":
    main()
