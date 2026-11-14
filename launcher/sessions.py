"""
Sesiones de juego del lanzador (las usan la interfaz web y la sencilla).

ctx tiene que ofrecer:
  ctx.log(texto)            mensaje para el registro
  ctx.set_address(texto)    direccion para pasar a los amigos ("" para borrarla)
  ctx.cancelled()           True si el jugador pulso "Terminar sesion"
"""
import core
import upnp
from i18n import t


def _play(ctx, game_dir, url):
    ctx.log(t("pointing", url=url))
    core.point_game_to(game_dir, url)
    ctx.log(t("opening"))
    core.launch_game()
    core.wait_game(ctx.log, stop_flag=ctx.cancelled)


def solo(ctx, cfg):
    gd = cfg["game_dir"]
    port = int(cfg.get("port", core.DEFAULT_PORT))
    srv = core.LocalServer(public=False, port=port).start()
    ctx.log(t("srv_local_on"))
    try:
        _play(ctx, gd, f"http://127.0.0.1:{port}")
    finally:
        srv.stop()
        ctx.log(t("srv_stopped"))


def host(ctx, cfg, port):
    gd = cfg["game_dir"]
    try:
        port = int(port)
    except (TypeError, ValueError):
        raise ValueError(t("port") + ": 18080")
    cfg["port"] = port
    core.save_config(cfg)
    srv = core.LocalServer(public=True, port=port).start()
    mapping = upnp.PortMapping(port)
    try:
        ctx.log(t("host_upnp"))
        if mapping.open():
            ctx.log(t("port_opened", port=port))
        else:
            ctx.log(t("port_failed", port=port))
        ip = mapping.external_ip or core.public_ip()
        lan = upnp.local_ip()
        addr = f"{ip}:{port}" if ip else f"{lan}:{port}"
        ctx.set_address(addr)
        ctx.log(t("give_address", addr=addr, lan=f"{lan}:{port}"))
        _play(ctx, gd, f"http://127.0.0.1:{port}")
    finally:
        mapping.close()
        srv.stop()
        ctx.set_address("")
        ctx.log(t("host_closed"))


def join(ctx, cfg, steam_id, address, password=""):
    gd = cfg["game_dir"]
    url = core.normalize_address(address)
    if not password:
        cfg["last_friend"] = address.strip()
        core.save_config(cfg)
    ctx.log(t("checking", url=url))
    info = core.server_info(url)
    if info.get("password") and not password:
        raise ValueError(t("need_password"))
    ctx.log(t("syncing"))
    ctx.log(t("record", **core.sync_profile(url, steam_id, password)))
    try:
        _play(ctx, gd, url)
    finally:
        try:
            ctx.log(t("fetching"))
            ctx.log(t("record", **core.sync_profile(url, steam_id, password)))
        except ValueError as e:
            ctx.log(t("sync_later", err=e))
