"""
CRIMESIGHT Revival - lanzador.

Cuatro formas de jugar:
  - Jugar solo: servidor en este PC, partidas contra la IA.
  - Ser anfitrion: servidor en este PC abierto a tus amigos (intenta abrir el puerto solo).
  - Unirme a un amigo: te conectas al PC de un amigo que hace de anfitrion.
  - Servidor propio: te conectas a un servidor montado por alguien (por ejemplo, en un VPS).

Este proyecto solo ofrece la herramienta; no gestiona ni aloja servidores.
"""
import os, queue, sys, threading, traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402
import sessions  # noqa: E402
from i18n import t  # noqa: E402

TITLE = "CRIMESIGHT Revival"


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = core.load_config()
        self.q = queue.Queue()
        self.busy = False
        self.cancel = False
        self.steam_id, self.steam_name = core.steam_account()
        imported = core.import_old_data()

        root.title(TITLE)
        ico = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "icon.ico")
        if core.IS_WINDOWS and os.path.isfile(ico):
            try:
                root.iconbitmap(ico)
            except tk.TclError:
                pass
        root.geometry("620x560")
        root.minsize(560, 480)
        pad = {"padx": 10, "pady": 4}

        top = ttk.Frame(root)
        top.pack(fill="x", **pad)
        ttk.Label(top, text=TITLE, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        self.lbl_account = ttk.Label(top, text="")
        self.lbl_account.pack(anchor="w")
        row = ttk.Frame(top)
        row.pack(fill="x")
        self.lbl_game = ttk.Label(row, text="")
        self.lbl_game.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Cambiar carpeta…", command=self.pick_game).pack(side="right")

        nb = ttk.Notebook(root)
        nb.pack(fill="x", **pad)
        self.tab_solo(nb)
        self.tab_host(nb)
        self.tab_friend(nb)
        self.tab_server(nb)

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", **pad)
        self.btn_stop = ttk.Button(bottom, text="Terminar sesión", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left")
        ttk.Button(bottom, text="Dejar el juego original", command=self.restore).pack(side="right")
        ttk.Button(bottom, text=t("import_btn") + "…", command=self.import_progress).pack(side="right", padx=4)
        ttk.Button(bottom, text=t("export_btn") + "…", command=self.export_progress).pack(side="right")

        self.log_box = tk.Text(root, height=12, wrap="word", state="disabled")
        self.log_box.pack(fill="both", expand=True, **pad)

        if not self.cfg.get("game_dir") or not core.is_game_dir(self.cfg.get("game_dir")):
            self.cfg["game_dir"] = core.find_game()
            core.save_config(self.cfg)
        self.auto_backup()
        self.refresh_header()
        if imported:
            self.log(f"He traído tus partidas de la versión anterior ({imported}).")
        self.log("Este proyecto solo ofrece la herramienta para revivir el juego a quien ya lo tiene. "
                 "No incluye archivos de Konami ni gestiona servidores.")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(200, self.pump)

    # ---------------------------------------------------------------- pestañas
    def tab_solo(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="Jugar solo")
        ttk.Label(f, text="Servidor en este PC. Crea una sala y rellena los huecos con IA.\n"
                          "Expulsa a una IA para cambiar su dificultad.", justify="left").pack(anchor="w")
        ttk.Button(f, text="Jugar", command=lambda: self.run(self.do_solo)).pack(anchor="w", pady=8)

    def tab_host(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="Ser anfitrión")
        ttk.Label(f, text="Tus amigos se conectan a tu PC. Intentaré abrir el puerto del router solo;\n"
                          "si no se puede, ábrelo a mano o usad Tailscale / ZeroTier / Radmin VPN.",
                  justify="left").pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=4)
        ttk.Label(row, text="Puerto:").pack(side="left")
        self.port_var = tk.StringVar(value=str(self.cfg.get("port", core.DEFAULT_PORT)))
        ttk.Entry(row, textvariable=self.port_var, width=7).pack(side="left", padx=4)
        ttk.Button(f, text="Abrir partida para amigos", command=lambda: self.run(self.do_host)).pack(anchor="w", pady=4)
        self.addr_var = tk.StringVar(value="")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.addr_var, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Copiar", command=self.copy_addr).pack(side="right", padx=4)

    def tab_friend(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="Unirme a un amigo")
        ttk.Label(f, text="Escribe la dirección que te ha pasado tu amigo (por ejemplo 83.45.120.7:18080).\n"
                          "Tu progreso se junta con el suyo al entrar y vuelve a tu PC al salir.",
                  justify="left").pack(anchor="w")
        self.friend_var = tk.StringVar(value=self.cfg.get("last_friend", ""))
        ttk.Entry(f, textvariable=self.friend_var).pack(fill="x", pady=6)
        ttk.Button(f, text="Unirme", command=lambda: self.run(self.do_join, self.friend_var.get(), "")).pack(anchor="w")

    def tab_server(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="Servidor propio")
        ttk.Label(f, text="Conéctate a un servidor que haya montado alguien (por ejemplo en un VPS).",
                  justify="left").pack(anchor="w")
        grid = ttk.Frame(f)
        grid.pack(fill="x", pady=4)
        ttk.Label(grid, text="Guardados:").grid(row=0, column=0, sticky="w")
        self.srv_combo = ttk.Combobox(grid, values=[s["name"] for s in self.cfg["servers"]], state="readonly")
        self.srv_combo.grid(row=0, column=1, sticky="ew", padx=4)
        self.srv_combo.bind("<<ComboboxSelected>>", self.pick_server)
        ttk.Label(grid, text="Nombre:").grid(row=1, column=0, sticky="w")
        self.srv_name = tk.StringVar()
        ttk.Entry(grid, textvariable=self.srv_name).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Label(grid, text="Dirección:").grid(row=2, column=0, sticky="w")
        self.srv_addr = tk.StringVar()
        ttk.Entry(grid, textvariable=self.srv_addr).grid(row=2, column=1, sticky="ew", padx=4)
        ttk.Label(grid, text="Contraseña:").grid(row=3, column=0, sticky="w")
        self.srv_pw = tk.StringVar()
        ttk.Entry(grid, textvariable=self.srv_pw, show="•").grid(row=3, column=1, sticky="ew", padx=4)
        grid.columnconfigure(1, weight=1)
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=4)
        ttk.Button(row, text="Conectar", command=lambda: self.run(self.do_join, self.srv_addr.get(),
                                                                   self.srv_pw.get())).pack(side="left")
        ttk.Button(row, text="Guardar", command=self.save_server).pack(side="left", padx=4)
        ttk.Button(row, text="Borrar", command=self.delete_server).pack(side="left")

    # ---------------------------------------------------------------- utilidades de interfaz
    def log(self, text):
        self.q.put(("log", text))

    def pump(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self.log_box.configure(state="normal")
                    self.log_box.insert("end", val + "\n")
                    self.log_box.see("end")
                    self.log_box.configure(state="disabled")
                elif kind == "addr":
                    self.addr_var.set(val)
                elif kind == "idle":
                    self.busy = False
                    self.btn_stop.configure(state="disabled")
                    self.refresh_header()
                elif kind == "error":
                    messagebox.showerror(TITLE, val)
        except queue.Empty:
            pass
        self.root.after(200, self.pump)

    def refresh_header(self):
        acc = f"Cuenta de Steam: {self.steam_name or '?'}" if self.steam_id else \
            "No detecto tu cuenta de Steam: abre Steam e inicia sesión."
        if self.steam_id:
            acc += f"   ·   Tu registro: {core.local_summary(self.steam_id)}"
        self.lbl_account.configure(text=acc)
        gd = self.cfg.get("game_dir")
        self.lbl_game.configure(text=f"Juego: {gd}" if gd else "No encuentro CrimeSight: elige su carpeta.")

    def pick_game(self):
        d = filedialog.askdirectory(title="Carpeta de CrimeSight (la que tiene CrimeSight.exe)")
        if d:
            if not core.is_game_dir(d):
                messagebox.showerror(TITLE, "Esa carpeta no parece la del juego.")
                return
            self.cfg["game_dir"] = os.path.normpath(d)
            core.save_config(self.cfg)
            self.refresh_header()

    def copy_addr(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.addr_var.get())

    def pick_server(self, _=None):
        name = self.srv_combo.get()
        for s in self.cfg["servers"]:
            if s["name"] == name:
                self.srv_name.set(s["name"])
                self.srv_addr.set(s["address"])
                self.srv_pw.set(s.get("password", ""))

    def save_server(self):
        name = self.srv_name.get().strip() or self.srv_addr.get().strip()
        if not name or not self.srv_addr.get().strip():
            return
        self.cfg["servers"] = [s for s in self.cfg["servers"] if s["name"] != name]
        self.cfg["servers"].append({"name": name, "address": self.srv_addr.get().strip(),
                                    "password": self.srv_pw.get()})
        core.save_config(self.cfg)
        self.srv_combo.configure(values=[s["name"] for s in self.cfg["servers"]])
        self.srv_combo.set(name)

    def delete_server(self):
        name = self.srv_combo.get()
        self.cfg["servers"] = [s for s in self.cfg["servers"] if s["name"] != name]
        core.save_config(self.cfg)
        self.srv_combo.configure(values=[s["name"] for s in self.cfg["servers"]])
        self.srv_combo.set("")

    def restore(self):
        gd = self.cfg.get("game_dir")
        if self.busy or not gd:
            return
        if core.restore_game(gd):
            self.log("Juego devuelto a su estado original (apunta otra vez a los servidores de Konami).")
        else:
            self.log("El juego ya estaba en su estado original.")

    # ---------------------------------------------------------------- progreso
    def auto_backup(self):
        try:
            added = core.backup_now(self.cfg, self.steam_id)
            if added:
                self.log(t("backup_restored", n=added))
        except Exception as e:  # noqa: BLE001
            self.log(t("backup_failed", err=e))

    def export_progress(self):
        if self.busy or not self.steam_id:
            return
        path = filedialog.asksaveasfilename(title=t("export_btn"), defaultextension=core.SAVE_EXT,
                                            initialfile=f"CrimeSightRevival_{self.steam_id}{core.SAVE_EXT}",
                                            filetypes=[("CRIMESIGHT Revival", "*" + core.SAVE_EXT)])
        if not path:
            return
        try:
            core.export_save(self.steam_id, path)
            self.log(t("exported", path=path))
        except (OSError, ValueError) as e:
            messagebox.showerror(TITLE, t("err_save_write", err=e))

    def import_progress(self):
        if self.busy or not self.steam_id:
            return
        path = filedialog.askopenfilename(title=t("import_btn"),
                                          filetypes=[("CRIMESIGHT Revival", "*" + core.SAVE_EXT), ("*", "*.*")])
        if not path:
            return
        try:
            added = core.import_save(self.steam_id, path)
        except ValueError as e:
            messagebox.showerror(TITLE, str(e))
            return
        self.auto_backup()
        self.log(t("imported", n=added) if added else t("import_nothing"))
        self.refresh_header()

    def stop(self):
        self.cancel = True
        self.log("Terminando la sesión…")

    def on_close(self):
        if self.busy and not messagebox.askyesno(TITLE, "Hay una sesión en marcha. ¿Cerrar de todas formas?"):
            return
        self.cancel = True
        self.root.after(300, self.root.destroy)

    # ---------------------------------------------------------------- acciones
    def run(self, fn, *args):
        if self.busy:
            return
        gd = self.cfg.get("game_dir")
        if not gd:
            messagebox.showerror(TITLE, "Primero elige la carpeta del juego.")
            return
        if not self.steam_id:
            self.steam_id, self.steam_name = core.steam_account()
            if not self.steam_id:
                messagebox.showerror(TITLE, "Abre Steam e inicia sesión con la cuenta que tiene CRIMESIGHT.")
                return
        self.busy, self.cancel = True, False
        self.btn_stop.configure(state="normal")

        def work():
            try:
                core.ensure_keys(gd)
                fn(gd, *args)
            except ValueError as e:
                self.log(f"✗ {e}")
                self.q.put(("error", str(e)))
            except Exception as e:  # noqa: BLE001
                self.log("✗ Error inesperado:\n" + traceback.format_exc())
                self.q.put(("error", f"Error inesperado: {e}"))
            finally:
                self.auto_backup()
                self.q.put(("idle", None))
        threading.Thread(target=work, daemon=True).start()

    # contexto para sessions.py
    def set_address(self, addr):
        self.q.put(("addr", addr))

    def cancelled(self):
        return self.cancel

    def do_solo(self, gd):
        sessions.solo(self, self.cfg)

    def do_host(self, gd):
        sessions.host(self, self.cfg, self.port_var.get())

    def do_join(self, gd, address, password):
        sessions.join(self, self.cfg, self.steam_id, address, password)


class GuiLogHandler(__import__("logging").Handler):
    """Lleva al lanzador las lineas importantes del servidor (partidas, resultados, sincronizacion)."""
    KEYS = ("empieza la partida", "GANA", "PIERDE", "EMPATA", "ABANDONA", "Perfil sincronizado",
            "la victima ha muerto", "turno final", "aparece")

    def __init__(self, app):
        super().__init__()
        self.app = app

    def emit(self, record):
        msg = record.getMessage()
        if any(k in msg for k in self.KEYS):
            self.app.log("· " + msg)


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista" if core.IS_WINDOWS else "clam")
    except tk.TclError:
        pass
    app = App(root)
    import logging
    logging.getLogger("crimesight").addHandler(GuiLogHandler(app))
    try:
        core.setup_launcher_log()
    except OSError:
        pass
    root.mainloop()


if __name__ == "__main__":
    main()
