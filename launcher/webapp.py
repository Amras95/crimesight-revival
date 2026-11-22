"""
CRIMESIGHT Revival - lanzador con interfaz grafica (HTML con pywebview / WebView2).

En Windows va en su propia ventana; en Linux / Steam Deck la misma interfaz se abre en el
navegador (browserui.py). Si nada de eso funciona, se abre la interfaz sencilla (app.py).
Este proyecto solo ofrece la herramienta; no gestiona ni aloja servidores.
"""
import json, logging, os, re, sys, threading, time, traceback, webbrowser

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
STAGE_FILTER = "CRIMESIGHT Revival (*.csrstage)"
ALL_FILTER = "All files (*.*)"
IMAGE_FILTER = "Images (*.png;*.jpg;*.jpeg;*.gif;*.webp;*.bmp)"
EXE_FILTER = "Executable (*.exe)"
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
        self._update = None
        self._bep_lock = threading.Lock()
        self._bep_thread = None

    # ---------------------------------------------------------------- estado
    def init(self):
        imported = core.import_old_data()
        self._steam = core.steam_account()
        if not core.is_game_dir(self._cfg.get("game_dir")):
            self._cfg["game_dir"] = core.find_game()
            core.save_config(self._cfg)
        gd = self._cfg.get("game_dir")
        self._update_lang()
        self._check_update()
        self._watch_updates()
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
        if self._update:
            state["update"] = self._update_info()
        if _browser:        # los avisos de "cargando" llegan por otro camino y pueden adelantar a esta respuesta
            js("loading", None)
        self._bep_auto()
        return state

    def _check_update(self):
        """Mira si hay una version nueva del lanzador. No se instala sola: se ofrece con sus novedades."""
        updater.cleanup_old()
        try:
            self._update = updater.check(i18n.get_lang())
        except Exception:  # noqa: BLE001
            self._update = None

    def _update_info(self):
        u = self._update
        return {"version": u["version"], "current": VERSION, "notes": u["notes"],
                "skipped": self._cfg.get("update_skipped") == u["version"]}

    def _watch_updates(self, every=30 * 60):
        """Con el lanzador abierto se vuelve a mirar cada media hora: si sale una version nueva, aparece
        la campana (sin abrir ninguna ventana, que puede haber una partida en marcha)."""
        if getattr(self, "_watching", False) or not updater.frozen():
            return
        self._watching = True

        def loop():
            while True:
                time.sleep(every)
                try:
                    new = updater.check(i18n.get_lang())
                except Exception:  # noqa: BLE001
                    new = None
                if new and (not self._update or new["version"] != self._update["version"]):
                    self._update = new
                    js("update", self._update_info())
        threading.Thread(target=loop, daemon=True).start()

    def update_apply(self, force=False):
        """El jugador acepta la actualizacion: se descarga, se instala y el lanzador se vuelve a abrir.
        Si hay una sesion, el juego u otro lanzador abiertos, primero se pregunta; al confirmar se cierra
        todo (la sesion termina como al pulsar "Terminar sesion") y se actualiza."""
        upd = self._update
        if not upd:
            return {"error": t("update_failed", err="-")}
        need_close = self._busy or core.game_running() or bool(core.other_launchers())
        if need_close and not force:
            return {"confirm": t("update_confirm_close")}

        def run():
            if need_close:
                js("loading", t("update_closing"))
                core.close_game()
                if self._busy:
                    self.stop()
                    t0 = time.time()
                    while self._busy and time.time() - t0 < 40:
                        time.sleep(0.5)
                core.close_other_launchers()
            js("loading", t("updating", v=upd["version"]))
            try:
                updater.apply(upd, progress=lambda pct: js("loading", t("updating", v=upd["version"]) + f"  {pct}%"))
            except Exception as e:  # noqa: BLE001
                logging.getLogger("crimesight").warning("Actualizacion fallida: %s", e)
                js("loading", None)
                js("error", t("update_failed", err=e))
        threading.Thread(target=run, daemon=True).start()
        return {"ok": True}

    def update_later(self):
        """«Ahora no»: esa version no se vuelve a ofrecer sola (queda el aviso junto al numero de version)."""
        if self._update:
            self._cfg["update_skipped"] = self._update["version"]
            core.save_config(self._cfg)
        return {"ok": True}

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
        self._mode = mode
        try:
            core.ensure_keys(self._cfg["game_dir"])
            self._bep_ready()
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
            self._mode = None
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
        exe = self._dialog("OPEN_DIALOG", file_types=(EXE_FILTER, ALL_FILTER))
        if not exe:
            return None
        d = os.path.dirname(exe)
        if not core.is_game_dir(d):
            js("error", t("err_bad_folder"))
            return None
        self._cfg["game_dir"] = os.path.normpath(d)
        self._cfg["game_exe"] = os.path.normpath(exe)
        core.save_config(self._cfg)
        self._update_lang()
        if not art.ready(core.app_dir()):
            try:
                art.extract(self._cfg["game_dir"], core.app_dir())
            except Exception:  # noqa: BLE001
                pass
        self._bep_auto()
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
            def thumbs(items, n):
                return ["data:image/png;base64," + base64.b64encode(it["png"]).decode() for it in items[:n]]
            out.append({"folder": os.path.basename(m["folder"]), "name": m["name"], "author": m["author"],
                        "stickers": len(m["stickers"]), "avatars": len(m["avatars"]), "enabled": m["enabled"],
                        "errors": len(m["errors"]),
                        "thumbs": thumbs(m["stickers"] + m["avatars"], 5),
                        "sticker_thumbs": thumbs(m["stickers"], 12),     # pestañas de la ventana de mods
                        "avatar_thumbs": thumbs(m["avatars"], 12)})
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
            out.append({"key": it["key"], "text": cur, "means": it.get("means") or "",
                        "thumb": "data:image/png;base64," + base64.b64encode(it["png"]).decode()})
        return {"name": m["name"], "stickers": out}

    def mods_set_text(self, folder, key, text):
        import modpack
        try:
            return {"ok": True, "text": modpack.set_text(core.mod_folder(folder), key, text)}
        except (OSError, ValueError) as e:
            return {"error": str(e)}

    def mods_set_means(self, folder, key, value):
        """A que sticker del juego equivale un sticker (para que las IA le contesten)."""
        import modpack
        try:
            return {"ok": True, "means": modpack.set_means(core.mod_folder(folder), key, value) or ""}
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

    def _cursor_apply(self):
        try:                                   # si el juego ya esta abierto, se aplica en caliente
            core.install_cursor(self._cfg.get("game_dir") or "")
        except (OSError, KeyError, TypeError):
            pass
        return core.cursor_state()

    def cursor_open(self):
        core.open_folder(core.cursor_dir())
        return self._cursor_apply()

    def cursor_state(self):
        return self._cursor_apply()

    def cursor_pick(self):
        path = self._dialog("OPEN_DIALOG", file_types=(IMAGE_FILTER, ALL_FILTER))
        if not path:
            return None
        if isinstance(path, (list, tuple)):
            path = path[0] if path else ""
        try:
            core.cursor_set_image(path)
        except ValueError as e:
            return {"error": str(e)}
        self._cfg["cursor_enabled"] = True
        core.save_config(self._cfg)
        return self._cursor_apply()

    def cursor_hotspot(self, mode):
        core.cursor_set_hotspot(mode)
        return self._cursor_apply()

    def cursor_toggle(self, on):
        self._cfg["cursor_enabled"] = bool(on)
        core.save_config(self._cfg)
        return self._cursor_apply()

    def cursor_remove(self):
        core.cursor_remove()
        return self._cursor_apply()

    # recarga en caliente (BepInEx): activada por defecto. El lanzador la instala sola al arrancar, salvo
    # que el jugador la haya quitado (bep_removed en la configuracion, hasta que la vuelva a activar).
    def _bep_wanted(self):
        gd = self._cfg.get("game_dir")
        return core.is_game_dir(gd) and not self._cfg.get("bep_removed") and not core.live_mode(gd)

    def _bep_auto(self):
        """Al abrir el lanzador (o al elegir la carpeta del juego) instala BepInEx si falta, sin esperar.
        Con el juego abierto no: se intenta al empezar a jugar."""
        if not self._bep_wanted() or core.game_running():
            return
        if self._bep_thread is not None and self._bep_thread.is_alive():
            return
        self._bep_thread = threading.Thread(target=self._bep_install, args=(self._cfg["game_dir"],), daemon=True)
        self._bep_thread.start()

    def _bep_install(self, gd):
        """Instala BepInEx y lo cuenta en el registro. Si falla, se juega sin el y se reintenta otra vez."""
        with self._bep_lock:
            if core.live_mode(gd):
                return
            self.log(t("bep_installing_log"))
            js("bepProgress", t("bep_installing_log"), None)      # aviso con barra en la ventana principal
            try:
                core.install_bepinex(gd, progress=lambda pct: js("bepProgress", t("bep_installing", pct=pct), pct))
                self.log(t("bep_ready_log"), "ok")
                js("bepDone", t("bep_installed"))
            except ValueError as e:
                self.log(t("bep_failed_log", err=e), "err")
                js("bepDone", str(e), True)
            except Exception as e:  # noqa: BLE001
                logging.getLogger("crimesight").exception("No pude instalar BepInEx")
                self.log(t("bep_failed_log", err=t("err_unexpected", err=e)), "err")
                js("bepDone", t("err_unexpected", err=e), True)

    def _bep_ready(self):
        """Antes de abrir el juego: espera a la instalacion en marcha o la vuelve a intentar."""
        th = self._bep_thread
        if th is not None and th.is_alive():
            self.log(t("bep_wait"))
            th.join()
        elif self._bep_wanted() and not core.game_running():
            self._bep_install(self._cfg["game_dir"])
        gd = self._cfg.get("game_dir")
        if not core.IS_WINDOWS and core.live_mode(gd) and core.linux_launch_option_ok() is not True:
            self.log(t("bep_linux_note", opt=core.LINUX_LAUNCH_OPTION), "err")

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
        if self._bep_thread is not None and self._bep_thread.is_alive():
            return {"ok": True}                  # ya se esta instalando: el aviso llega al terminar
        if self._busy or core.game_running():
            return {"error": t("bep_busy")}
        self._cfg.pop("bep_removed", None)   # vuelve a instalarse sola
        core.save_config(self._cfg)
        self._bep_thread = threading.Thread(target=self._bep_install, args=(gd,), daemon=True)
        self._bep_thread.start()
        return {"ok": True}

    def bep_uninstall(self):
        gd = self._cfg.get("game_dir")
        if self._busy or core.game_running():
            return {"error": t("bep_busy")}
        if self._bep_thread is not None and self._bep_thread.is_alive():
            return {"error": t("bep_wait")}
        try:
            core.uninstall_bepinex(gd)
        except OSError as e:
            return {"error": t("err_unexpected", err=e)}
        self._cfg["bep_removed"] = True      # no se vuelve a instalar sola hasta que la activen
        core.save_config(self._cfg)
        return {"ok": True, "msg": t("bep_removed")}

    # ---------------------------------------------------------------- modelos 3D
    def models_state(self):
        gd = self._cfg.get("game_dir") or ""
        try:                                   # un .glb que se ha vuelto a exportar llega al juego al refrescar
            core.install_models(gd)
        except OSError:
            pass
        names = {"ThreatTypeData_Survivor": t("models_survivor"), "ThreatTypeData_Traitor": t("models_traitor")}
        slots = [{"id": k, "name": n or names.get(k, k)} for k, n in core.MODEL_SLOTS]
        custom = [{"id": core.CUSTOM_PREFIX + n, "name": t("models_custom_tag", name=n), "custom": True}
                  for n in core.custom_models()]
        targets = slots + custom + [{"id": k, "name": n} for k, n in core.MODEL_EXTRA if core.dev_mode()]
        issues = {core.CUSTOM_PREFIX + k: v for k, v in core.model_issues.items() if v}
        return {"slots": slots, "targets": targets, "swaps": core.model_swaps(), "issues": issues,
                "live": bool(gd) and core.live_mode(gd), "skeletons": core.sync_skeletons(gd),
                "anims": core.custom_anims(), "anim_swaps": core.anim_swaps(), "anim_kinds": list(core.ANIM_KINDS),
                "anim_issues": {k: v for k, v in core.anim_issues.items() if v}}

    # ---- personajes nuevos (slots del Selector de personajes)
    def chars_state(self):
        return {"chars": core.characters(), "models": core.custom_models(), "anims": core.custom_anims(),
                "images": list(core.custom_images()), "talk_keys": list(core.TALK_KEYS), "kinds": list(core.ANIM_KINDS)}

    def chars_save(self, c):
        if not isinstance(c, dict) or not c.get("model"):
            return {"error": t("chars_need_model")}
        core.save_character(c)
        return self.chars_state()

    def chars_delete(self, cid):
        core.delete_character(str(cid or ""))
        return self.chars_state()

    def chars_images_open(self):
        core.open_folder(core.images_dir())

    def models_anim_set(self, slot, kind, name):
        core.set_anim_swap(slot, kind, name)
        try:
            core.install_models(self._cfg.get("game_dir") or "")
        except OSError as e:
            return {"error": t("err_unexpected", err=e)}
        self._cfg["anim_swaps"] = core.load_config().get("anim_swaps") or {}
        return self.models_state()

    def models_anims_open(self):
        core.open_folder(core.anims_dir())

    def models_open(self):
        core.sync_skeletons(self._cfg.get("game_dir") or "")
        core.open_folder(core.models_dir())

    def models_set(self, slot, target):
        core.set_model_swap(slot, target)
        try:
            core.install_models(self._cfg.get("game_dir") or "")
        except OSError as e:
            return {"error": t("err_unexpected", err=e)}
        self._cfg["model_swaps"] = core.load_config().get("model_swaps") or {}   # que no lo pise otro guardado
        return self.models_state()

    # ---------------------------------------------------------------- creador de escenarios
    STAGE_LABELS = {"Stage_Yokn": "01 · Lauriston Gardens", "Stage_Yokn_v1030": "02 · Briony Lodge",
                    "Stage_Yokn_v1040": "03 · Josiah Amberley", "Stage_Yokn_v1050": "04 · The Abbey Grange",
                    "Stage_Yokn_v1060": "05 · Lysander Stark"}

    def _stage_cat(self):
        return core.stage_catalog(self._cfg.get("game_dir"))

    def stage_open(self):
        """Datos para abrir el editor. La primera vez hay que leer el juego (tarda): se hace aparte."""
        gd = self._cfg.get("game_dir")
        if not getattr(self, "_stage_ready", False):
            if not getattr(self, "_stage_loading", False):
                self._stage_loading = True

                def work():
                    try:
                        core.stage_catalog(gd, progress=lambda pct: js("stageProgress", t("stage_reading", pct=pct)))
                        self._stage_ready = True
                        js("stageReady", "")
                    except ValueError as e:
                        js("stageReady", str(e))
                    except Exception as e:  # noqa: BLE001
                        logging.getLogger("crimesight").exception("No pude leer los escenarios")
                        js("stageReady", t("err_unexpected", err=e))
                    finally:
                        self._stage_loading = False
                threading.Thread(target=work, daemon=True).start()
            return {"loading": True}
        import stagedata
        cat = self._stage_cat()
        self._stage_publish()
        types = {k: {x: v[x] for x in ("w", "d", "floor", "block", "outline")} for k, v in cat["types"].items()}
        stages = [{"scene": sc, "label": self.STAGE_LABELS.get(sc, sc),
                   "rooms": [{"type": r["type"], "entrance": r["entrance"]} for r in cat["stages"][sc]["rooms"]]}
                  for sc in core.STAGE_BASES if sc in cat["stages"]]
        return {"types": types, "stages": stages, "layouts": self._stage_layouts(), "bep": core.live_mode(gd),
                "active": core.stage_test_active(gd) if gd else "",
                "grid": [stagedata.MIN_X, stagedata.MAX_X, stagedata.MIN_Z, stagedata.MAX_Z]}

    def _stage_view(self, layout):
        import stagelayout
        d = stagelayout.derive(self._stage_cat(), layout)
        probs = []
        for p in d["problems"]:
            kw = {k: v for k, v in p.items() if k not in ("level", "code")}
            for k in ("room", "other"):
                if k in kw:
                    kw[k] = kw[k] + 1
            probs.append({"level": p["level"], "text": t("stage_p_" + p["code"], **kw),
                          "rooms": [p[k] for k in ("room", "other") if k in p]})
        keys = ("src", "type", "x", "z", "yaw", "i", "j", "w", "d", "rot", "entrance")
        return {"layout": d["layout"], "rooms": [{k: r[k] for k in keys} for r in d["rooms"]], "edges": d["edges"],
                "ok": d["ok"], "problems": probs, "stats": t("stage_stats", **d["stats"])}

    def stage_default(self, scene):
        import stagelayout
        try:
            return self._stage_view(stagelayout.default_layout(self._stage_cat(), scene))
        except (ValueError, KeyError, TypeError) as e:
            return {"error": str(e)}

    def stage_derive(self, layout):
        try:
            return self._stage_view(layout)
        except (ValueError, KeyError, TypeError, IndexError) as e:
            return {"error": str(e)}

    def stage_load(self, sid):
        try:
            return self._stage_view(core.stage_load(sid))
        except (OSError, ValueError, KeyError, TypeError, IndexError) as e:
            return {"error": t("err_unexpected", err=e)}

    def stage_save(self, layout):
        try:
            view = self._stage_view(layout)
            if not view["layout"]["name"].strip():
                return {"error": t("stage_need_name")}
            sid = core.stage_save(view["layout"])
            msg = "stage_saved_errors" if not view["ok"] else None
            if sum(1 for it in self._stage_layouts() if it["enabled"]) > core.MAX_GAME_STAGES:
                self._stage_enable(sid, False)
                msg = msg or "stage_saved_off"
            live = self._stage_publish()
        except (OSError, ValueError, KeyError, TypeError, IndexError) as e:
            return {"error": t("err_unexpected", err=e)}
        msg = msg or ("stage_saved_live" if live else "stage_saved")
        return {"ok": True, "id": sid, "layouts": self._stage_layouts(), "msg": t(msg, n=core.MAX_GAME_STAGES)}

    def _stage_publish(self):
        """Tus escenarios activos -> lista de escenarios del juego (solo con el plugin). True si hay plugin.
        En la sala de otro jugador no se toca: ahi mandan los escenarios de la sala."""
        gd = self._cfg.get("game_dir")
        if not gd or not core.live_mode(gd):
            return False
        if getattr(self, "_mode", None) in ("join", "server"):
            return True
        try:
            core.stage_publish(gd, core.stage_own(self._cfg.get("stages_disabled", [])), self._stage_cat())
        except OSError:
            logging.getLogger("crimesight").exception("No pude publicar los escenarios")
        return True

    def _stage_layouts(self):
        return core.stage_list(self._cfg.get("stages_disabled", []))

    def _stage_enable(self, sid, on):
        off = [x for x in self._cfg.get("stages_disabled", []) if x != sid]
        if not on:
            off.append(sid)
        self._cfg["stages_disabled"] = off
        core.save_config(self._cfg)

    def stage_toggle(self, sid, on):
        if on and sum(1 for it in self._stage_layouts() if it["enabled"]) >= core.MAX_GAME_STAGES:
            return {"error": t("stage_too_many", n=core.MAX_GAME_STAGES)}
        self._stage_enable(sid, bool(on))
        self._stage_publish()
        return {"ok": True, "layouts": self._stage_layouts()}

    def stage_export(self, sid):
        try:
            name = core.stage_load(sid).get("name") or sid
        except (OSError, ValueError):
            return {"error": t("stage_import_bad")}
        path = self._dialog("SAVE_DIALOG", save_filename=re.sub(r"[^\w.-]+", "_", name) + core.STAGE_EXT,
                            file_types=(STAGE_FILTER,))
        if not path:
            return None
        if not path.lower().endswith(core.STAGE_EXT):
            path += core.STAGE_EXT
        try:
            core.stage_export(sid, path)
        except (OSError, ValueError) as e:
            return {"error": t("err_save_write", err=e)}
        return {"ok": True, "msg": t("stage_exported", path=path)}

    def stage_import(self):
        path = self._dialog("OPEN_DIALOG", file_types=(STAGE_FILTER, ALL_FILTER))
        if not path:
            return None
        try:
            sid = core.stage_import(path, self._stage_cat())
        except ValueError as e:
            return {"error": str(e)}
        msg = "stage_imported"
        if sum(1 for it in self._stage_layouts() if it["enabled"]) > core.MAX_GAME_STAGES:
            self._stage_enable(sid, False)
            msg = "stage_saved_off"
        self._stage_publish()
        return {"ok": True, "id": sid, "layouts": self._stage_layouts(), "msg": t(msg, n=core.MAX_GAME_STAGES)}

    def stage_delete(self, sid):
        try:
            core.stage_delete(sid)
            self._stage_enable(sid, True)          # fuera de la lista de desactivados
            self._stage_publish()
        except OSError as e:
            return {"error": t("err_unexpected", err=e)}
        return {"ok": True, "layouts": self._stage_layouts()}

    def stage_test(self, layout):
        gd = self._cfg.get("game_dir")
        try:
            view = self._stage_view(layout)
            if not view["ok"]:
                return {"error": t("stage_fix_first")}
            core.stage_test(gd, self._stage_cat(), view["layout"])
        except ValueError as e:
            return {"error": str(e)}
        except (OSError, KeyError, TypeError, IndexError) as e:
            return {"error": t("err_unexpected", err=e)}
        return {"ok": True, "msg": t("stage_test_ok"), "active": core.stage_test_active(gd)}

    def stage_test_off(self):
        try:
            core.stage_test_clear(self._cfg.get("game_dir") or "")
        except OSError as e:
            return {"error": t("err_unexpected", err=e)}
        return {"ok": True, "msg": t("stage_test_off"), "active": ""}

    def answer_mods(self, ok):
        if ok == "always":                      # "Aceptar siempre" en el aviso
            self._set_guest_always(True)
            ok = True
        self._mods_answer = bool(ok)
        self._mods_event.set()

    def _set_guest_always(self, on):
        self._cfg["guest_mods_always"] = bool(on)
        core.save_config(self._cfg)

    def guest_mods(self, mode=None):
        """Anfitrion: que hacer cuando un invitado trae mods ("ask" o "always")."""
        if mode in ("ask", "always"):
            self._set_guest_always(mode == "always")
        return {"mode": "always" if self._cfg.get("guest_mods_always") else "ask"}

    # contexto de sessions.py: unirse a una sala con mods / un jugador trae mods a tu sala
    def _ask(self, fn, info, poll=None):
        self._mods_answer = None
        self._mods_event.clear()
        js(fn, info)
        while not self._mods_event.wait(0.3):
            if self._cancel:
                return False
            got = poll() if poll else None
            if got is not None:                 # contestado desde el juego
                js("closeOffer")
                return got
        return bool(self._mods_answer)

    def confirm_mods(self, info):
        return self._ask("confirmMods", info)

    def confirm_offer(self, info):
        """Un invitado trae mods: se pregunta en el lanzador y tambien dentro del juego (con el plugin)."""
        gd = self._cfg.get("game_dir") or ""
        oid = str(info.get("id", ""))
        shown = False
        try:
            if info.get("text"):                # modelos 3D: el texto y el resumen ya vienen hechos
                body = info["text"] + "\n\n" + "\n".join(m.get("text", "") for m in info.get("mods", []))
            else:
                body = t("mods_offer_text", player=info.get("player", "?")) + "\n\n" + \
                    t("mods_count", stickers=info.get("stickers", 0), avatars=info.get("avatars", 0))
            shown = bool(gd) and core.offer_prompt(gd, oid, t("mods_offer_title", player=info.get("player", "?")),
                                                   body, t("mods_offer_yes"), t("mods_offer_no"),
                                                   t("mods_offer_always"))
        except (OSError, ValueError, KeyError):
            logging.getLogger("crimesight").warning("No pude llevar el aviso de mods al juego", exc_info=True)
        try:
            got = self._ask("confirmOffer", info, poll=(lambda: core.offer_answer(gd, oid)) if shown else None)
            if got == "always":                 # "Aceptar siempre" desde el juego
                self._set_guest_always(True)
                return True
            return bool(got)
        finally:
            if shown:
                core.offer_clear(gd)

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
