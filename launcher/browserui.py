"""
CRIMESIGHT Revival - la misma interfaz, pero en el navegador del sistema (Linux / Steam Deck).

En Windows la interfaz va dentro de una ventana propia (pywebview + WebView2). En Linux eso
obligaria a instalar WebKitGTK o Qt, asi que se sirve la misma pagina desde un servidor local
(solo 127.0.0.1, con un token secreto en la direccion) y se abre en el navegador:

  POST /<token>/api/<metodo>   llama a Api.<metodo>(*args) y devuelve el resultado en JSON
  GET  /<token>/events         espera (hasta 25 s) los avisos de Python para la pagina (ui.log...)

Si se cierra la pestana y no hay ninguna sesion en marcha, el lanzador se cierra solo.
"""
import json, logging, os, secrets, shutil, subprocess, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("crimesight")
IDLE_EXIT = 90          # segundos sin la pestana abierta (y sin sesion) antes de cerrarse

_events = []
_cond = threading.Condition()
_last_seen = [time.time()]


def push(fn, *args):
    """Equivalente a window.evaluate_js("ui.fn(...)") de pywebview."""
    with _cond:
        _events.append({"fn": fn, "args": list(args)})
        del _events[:-500]
        _cond.notify_all()


def _take(timeout=25):
    with _cond:
        if not _events:
            _cond.wait(timeout)
        out = list(_events)
        _events.clear()
        return out


# ------------------------------------------------------------------ dialogos de archivos
def dialog(kind, save_filename=None, file_types=None):
    """Selector de archivos nativo: zenity (GNOME/Steam Deck), kdialog (KDE) o tkinter."""
    if shutil.which("zenity"):
        cmd = ["zenity", "--file-selection"]
        if kind == "FOLDER_DIALOG":
            cmd.append("--directory")
        elif kind == "SAVE_DIALOG":
            cmd += ["--save", "--confirm-overwrite"]
            if save_filename:
                cmd.append("--filename=" + os.path.join(os.path.expanduser("~"), save_filename))
        return _run(cmd)
    if shutil.which("kdialog"):
        home = os.path.expanduser("~")
        if kind == "FOLDER_DIALOG":
            return _run(["kdialog", "--getexistingdirectory", home])
        if kind == "SAVE_DIALOG":
            return _run(["kdialog", "--getsavefilename", os.path.join(home, save_filename or "")])
        return _run(["kdialog", "--getopenfilename", home])
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if kind == "FOLDER_DIALOG":
            res = filedialog.askdirectory()
        elif kind == "SAVE_DIALOG":
            res = filedialog.asksaveasfilename(initialfile=save_filename or "")
        else:
            res = filedialog.askopenfilename()
        root.destroy()
        return res or None
    except Exception:  # noqa: BLE001
        log.warning("No hay selector de archivos (zenity, kdialog o tkinter)")
        return None


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = r.stdout.strip()
    return out or None


# ------------------------------------------------------------------ servidor
def serve(api, ui_dir, busy=lambda: False):
    token = secrets.token_urlsafe(24)
    prefix = f"/{token}"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _ok_origin(self):
            host = (self.headers.get("Host") or "").split(":")[0]
            return host in ("127.0.0.1", "localhost") and self.path.startswith(prefix + "/")

        def do_GET(self):
            if not self._ok_origin():
                return self._send(404, {"error": "not found"})
            _last_seen[0] = time.time()
            path = self.path[len(prefix):].split("?")[0]
            if path == "/events":
                return self._send(200, _take())
            if path in ("/", "/index.html"):
                with open(os.path.join(ui_dir, "index.html"), "rb") as f:
                    page = f.read().replace(b"<head>", b"<head><script>window.CSR_HTTP=true</script>", 1)
                return self._send(200, page, "text/html; charset=utf-8")
            rel = os.path.normpath(path.lstrip("/"))
            full = os.path.join(ui_dir, rel)
            if rel.startswith("..") or not os.path.isfile(full):
                return self._send(404, {"error": "not found"})
            ctype = {".png": "image/png", ".jpg": "image/jpeg", ".ico": "image/x-icon", ".css": "text/css",
                     ".js": "text/javascript", ".svg": "image/svg+xml", ".woff2": "font/woff2"}.get(
                         os.path.splitext(full)[1].lower(), "application/octet-stream")
            with open(full, "rb") as f:
                return self._send(200, f.read(), ctype)

        def do_POST(self):
            if not self._ok_origin():
                return self._send(404, {"error": "not found"})
            _last_seen[0] = time.time()
            path = self.path[len(prefix):]
            if not path.startswith("/api/"):
                return self._send(404, {"error": "not found"})
            name = path[len("/api/"):]
            fn = getattr(api, name, None)
            if name.startswith("_") or not callable(fn):
                return self._send(404, {"error": "no such method"})
            length = int(self.headers.get("Content-Length") or 0)
            try:
                args = json.loads(self.rfile.read(length) or b"[]")
                result = fn(*args)
            except Exception as e:  # noqa: BLE001
                log.exception("Fallo en %s", name)
                return self._send(500, {"error": str(e)})
            return self._send(200, {"result": result})

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{httpd.server_port}{prefix}/"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    log.warning("Interfaz en el navegador: %s", url.replace(token, "…"))
    print("CRIMESIGHT Revival:", url, flush=True)
    if not webbrowser.open(url):
        print("Abre esa direccion en tu navegador / Open that address in your browser.", flush=True)
    # vive mientras la pestana siga abierta (sondea /events) o haya una sesion en marcha
    try:
        while True:
            time.sleep(5)
            if time.time() - _last_seen[0] > IDLE_EXIT and not busy():
                break
    except KeyboardInterrupt:
        pass
    httpd.shutdown()
    sys.exit(0)
