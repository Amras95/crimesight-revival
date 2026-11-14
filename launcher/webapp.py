"""
CRIMESIGHT Revival - lanzador con interfaz grafica (HTML con pywebview / WebView2).

Si el equipo no tiene WebView2 o pywebview falla, se abre la interfaz sencilla (app.py).
Este proyecto solo ofrece la herramienta; no gestiona ni aloja servidores.
"""
import json, logging, os, sys, threading, traceback, webbrowser

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

UI_DIR = os.path.join(getattr(sys, "_MEIPASS", HERE), "ui")
_window = None


def js(fn, *args):
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
        if gd and not art.ready(core.app_dir()):
            js("loading", t("loading_art"))
            try:
                art.extract(gd, core.app_dir())
            except Exception:  # noqa: BLE001
                logging.getLogger("crimesight").exception("No pude sacar las ilustraciones")
        state = self._state()
        if imported:
            state["notice"] = t("notice_imported")
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
              "lang": i18n.get_lang(), "i18n": i18n.table(), "version": VERSION, "kofi": KOFI}
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
            self._update_lang()          # el juego pudo cambiar de idioma durante la partida
            js("state", self._state(with_art=False))
            js("busy", False)

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
        import webview
        res = _window.create_file_dialog(webview.FOLDER_DIALOG)
        if not res:
            return None
        d = res[0] if isinstance(res, (list, tuple)) else res
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
    global _window
    try:
        import webview
    except ImportError:
        import app
        return app.main()
    logging.getLogger("crimesight").addHandler(_GuiLog())
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
