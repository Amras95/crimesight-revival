"""
Sesiones de juego del lanzador (las usan la interfaz web y la sencilla).

ctx tiene que ofrecer:
  ctx.log(texto)            mensaje para el registro
  ctx.set_address(texto)    direccion para pasar a los amigos ("" para borrarla)
  ctx.cancelled()           True si el jugador pulso "Terminar sesion"
  ctx.confirm_mods(info)    pregunta si descargar los mods de la sala (True = descargar y unirse)
"""
import logging, threading, time

import core
import upnp
from i18n import t

log = logging.getLogger("crimesight")


def _mods(ctx, game_dir, rs):
    """Pone en el juego justo esos mods (los archivos solo se reescriben si cambia algo)."""
    def say(n_st, n_av):
        ctx.log(t("mods_installing", stickers=n_st, avatars=n_av))
    try:
        if core.install_mods(game_dir, rs, log=say) and not rs["hash"]:
            ctx.log(t("mods_removed"))
    except Exception as e:  # noqa: BLE001
        if rs["hash"]:
            raise ValueError(t("mods_failed", err=e))
        ctx.log(t("mods_failed", err=e))


def _play(ctx, game_dir, url, rs=None, watch=None, every=3):
    if core.game_running():
        # con el juego abierto no se pueden preparar sus archivos (y no se conectaria a esta sesion)
        raise ValueError(t("err_game_open"))
    core.unlock_game_files(game_dir)
    if rs is not None:
        _mods(ctx, game_dir, rs)
    try:
        core.update_plugin(game_dir)
    except (OSError, ValueError):
        pass
    try:
        core.install_cursor(game_dir)
    except OSError as e:
        log.warning("No pude copiar el cursor: %s", e)
    try:
        core.install_models(game_dir)
    except OSError as e:
        log.warning("No pude guardar los modelos: %s", e)
    ctx.log(t("pointing", url=url))
    core.point_game_to(game_dir, url)
    ctx.log(t("opening"))
    core.launch_game()
    stop = threading.Event()
    if watch:
        def loop():
            while not stop.wait(every):
                try:
                    watch()
                except Exception:  # noqa: BLE001
                    log.exception("Fallo vigilando los mods")
        threading.Thread(target=loop, daemon=True).start()
    try:
        core.wait_game(ctx.log, stop_flag=ctx.cancelled, game_dir=game_dir)
    finally:
        stop.set()


def _own_watcher(ctx, cfg, rs, srv=None):
    """Recarga en caliente de TUS mods mientras juegas solo (con el plugin de BepInEx): si cambias
    imagenes o activas/desactivas un mod, el juego lo recibe (y el servidor, para que las IA sepan
    a que sticker del juego equivale cada uno)."""
    gd = cfg["game_dir"]
    state = {"hash": rs["hash"]}

    def check():
        if not core.live_mode(gd):
            return
        new = core.my_room_set(cfg)
        if new["hash"] == state["hash"]:
            return
        state["hash"] = new["hash"]
        core.write_live(new, gd)
        if srv is not None:
            srv.room.set_base([m["folder"] for m in new["mods"]], {m["folder"]: m["name"] for m in new["mods"]})
        ctx.log(t("mods_live_updated"))
    return check


def _host_watcher(ctx, cfg, srv):
    """Anfitrion: tus cambios de mods llegan a la sala, y cuando un jugador trae mods te pregunta si
    los descargas (si aceptas, los ve todo el mundo). Necesita la recarga en caliente: sin ella, el
    juego de los que ya estan dentro no podria cambiar su lista de stickers."""
    gd = cfg["game_dir"]
    room = srv.room
    state = {"own": room.rs["hash"], "room": room.rs["hash"], "asked": set()}

    def check():
        live = core.live_mode(gd)
        if live:
            own = core.my_room_set(cfg)
            if own["hash"] != state["own"]:
                state["own"] = own["hash"]
                room.set_base([m["folder"] for m in own["mods"]], {m["folder"]: m["name"] for m in own["mods"]})
        for off in room.pending_list():
            if off["id"] in state["asked"]:
                continue
            state["asked"].add(off["id"])
            if not live:
                ctx.log(t("mods_offer_need_live", player=off["player"]))
                room.answer(off["id"], False)
                continue
            auto = bool(cfg.get("guest_mods_always"))   # "Aceptar siempre": sin preguntar
            ask = getattr(ctx, "confirm_offer", None)
            ok = auto or bool(ask and ask(off))
            room.answer(off["id"], ok)
            if ok:
                ctx.log(t("mods_offer_auto" if auto else "mods_offer_accepted", player=off["player"]))
        rs = room.rs
        if live and rs["hash"] != state["room"]:
            state["room"] = rs["hash"]
            core.write_live(rs, gd)
            ctx.log(t("mods_live_updated"))
    return check


def _room_watcher(ctx, cfg, url, password, rs):
    """En la sala de otro: si el anfitrion cambia sus mods, se bajan y se aplican en caliente."""
    gd = cfg["game_dir"]
    state = {"hash": rs["hash"], "warned": False}

    def check():
        info = core.server_info(url).get("mods") or {}
        h = info.get("hash", "")
        if h == state["hash"]:
            return
        if not core.live_mode(gd):
            if not state["warned"]:
                ctx.log(t("mods_host_changed"))
                state["warned"] = True
            return
        state["hash"] = h
        if h:
            new = core.download_mods(url, password, h)
        else:
            import modpack
            new = modpack.room_set([])
        core.write_live(new, gd)
        ctx.log(t("mods_live_updated"))
    return check


def _stages(ctx, cfg, url, password, steam_id, srv=None, room=False):
    """Escenarios del creador de escenarios. Solo / anfitrion: los tuyos activos se dejan listos en el
    juego (y en la sala, para que se los bajen los demas). En la sala de otro: se bajan los suyos.
    Siempre se le dice al servidor cuales tiene listos tu juego: solo deja jugar un escenario
    personalizado si lo tienen todos. Devuelve la comprobacion que se repite durante la sesion."""
    gd = cfg["game_dir"]
    state = {"key": None, "warned": False, "fails": 0}

    def check():
        live = core.live_mode(gd)
        if room:
            key = (core.server_info(url).get("stages") or {}).get("hash", "")
            if key == state["key"]:
                return
            if key and not live and not state["warned"]:
                ctx.log(t("stage_room_need_bep"))
                state["warned"] = True
            stages = core.stage_room_fetch(url, password) if key and live else []
        else:
            stages = core.stage_own(cfg.get("stages_disabled", [])) if live else []
            key = tuple((s["id"], core.stage_hash(s["layout"])) for s in stages)
            if key == state["key"]:
                return
            if srv is not None:
                srv.stages.set(stages)
        have = core.stage_publish(gd, stages) if live else {}
        seen = key if room else (srv.stages.key() if srv is not None else "")
        if not core.stage_report(url, password, steam_id, have, seen) and state["fails"] < 5:
            state["fails"] += 1                 # el servidor no se ha enterado: se repite en la proxima pasada
            return
        if room and have:
            ctx.log(t("stage_room_synced", n=len(have)))
        state["key"], state["fails"] = key, 0
    return check


def _host_gone_watcher(ctx, url, steam_id):
    """En la sala de otro: si el anfitrion desaparece a mitad de partida (cierra el lanzador, se queda sin
    conexion...), su servidor ya no puede apuntar el resultado. Entonces cuenta como victoria para ti,
    siempre que tu si tengas internet (si el que se ha caido eres tu, no)."""
    state = {"match": None, "fails": 0}

    def check():
        try:
            state["match"] = core.match_state(url, steam_id) or None
            state["fails"] = 0
            return
        except ValueError:
            state["fails"] += 1
        if state["match"] and state["fails"] >= 4 and core.internet_ok():
            m, state["match"] = state["match"], None
            pts = core.record_host_left(steam_id, m)
            ctx.log(t("host_left_win", points=pts))
    return check


def _both(*checks):
    def run():
        for c in checks:
            try:
                c()
            except Exception:  # noqa: BLE001
                log.exception("Fallo vigilando la sala")
    return run


def _every(n, check):
    """La comprobacion solo se hace una de cada n veces."""
    count = [0]

    def run():
        count[0] += 1
        if count[0] % n == 0:
            check()
    return run


def _first(ctx, check):
    """Primera pasada de los escenarios, antes de abrir el juego (si falla, se juega sin ellos)."""
    try:
        check()
    except Exception as e:  # noqa: BLE001
        log.exception("No pude preparar los escenarios")
        ctx.log(t("stage_room_failed", err=e))


def solo(ctx, cfg):
    gd = cfg["game_dir"]
    port = int(cfg.get("port", core.DEFAULT_PORT))
    rs = core.my_room_set(cfg)
    # el servidor tambien tiene tus mods: las IA miran a que sticker del juego equivale cada uno
    srv = core.LocalServer(public=False, port=port, mods=[m["folder"] for m in rs["mods"]],
                           names={m["folder"]: m["name"] for m in rs["mods"]}).start()
    ctx.log(t("srv_local_on"))
    _models_room_start(cfg, srv)                        # tus modelos y personajes nuevos, como en tu sala
    try:
        url = f"http://127.0.0.1:{port}"
        steam_id = core.steam_account()[0]
        stages = _stages(ctx, cfg, url, "", steam_id, srv=srv)
        _first(ctx, stages)
        _play(ctx, gd, url, rs, watch=_both(_own_watcher(ctx, cfg, rs, srv), _host_models_watcher(ctx, cfg, srv),
                                            _roster_watcher(ctx, cfg, url, steam_id, srv), stages))
    finally:
        _models_room_end(gd)
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
    rs = core.my_room_set(cfg)
    srv = core.LocalServer(public=True, port=port, mods=[m["folder"] for m in rs["mods"]], player_mods="ask",
                           names={m["folder"]: m["name"] for m in rs["mods"]}).start()
    _models_room_start(cfg, srv)                           # tus modelos y personajes son los de la sala
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
        url = f"http://127.0.0.1:{port}"
        stages = _stages(ctx, cfg, url, "", core.steam_account()[0], srv=srv)
        _first(ctx, stages)
        steam_id = core.steam_account()[0]
        _play(ctx, gd, url, rs, watch=_both(_host_watcher(ctx, cfg, srv), _host_models_watcher(ctx, cfg, srv),
                                            _roster_watcher(ctx, cfg, url, steam_id, srv), stages))
    finally:
        mapping.close()
        _models_room_end(gd)                           # los de los invitados eran solo para esta sala
        if srv.room.accepted:                      # los mods de los jugadores eran solo para esta sala
            try:
                _mods(ctx, gd, core.my_room_set(cfg))
            except ValueError as e:
                ctx.log(f"✗ {e}")
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
    rs = _room_mods(ctx, cfg, url, password, info.get("mods"), info.get("models"))
    rm = _room_models(ctx, url, password, info.get("models"))
    rs = _offer_own(ctx, cfg, url, password, rs)
    rm, offer = _offer_own_models(ctx, url, password, rm)
    core.room_models = rm                              # el juego ve los modelos de la sala (los tuyos, apartados)
    ctx.log(t("syncing"))
    ctx.log(t("record", **core.sync_profile(url, steam_id, password)))
    stages = _stages(ctx, cfg, url, password, steam_id, room=True)
    _first(ctx, stages)
    roster = _roster_watcher(ctx, cfg, url, steam_id, None, password)
    try:
        # los escenarios se miran cada 3 s (la sala no deja empezar hasta tenerlos); los mods y modelos, cada 9
        _play(ctx, gd, url, rs, watch=_both(_every(3, _room_watcher(ctx, cfg, url, password, rs)),
                                            _every(3, _room_models_watcher(ctx, cfg, url, password, rm, offer)),
                                            roster, stages, _host_gone_watcher(ctx, url, steam_id)), every=3)
    finally:
        roster.stop()
        _models_room_end(gd)                           # vuelven tus modelos
        core.clear_temp_models()
        try:                                           # vuelven tus escenarios a la lista del juego
            core.stage_publish(gd, core.stage_own(cfg.get("stages_disabled", [])))
        except Exception:  # noqa: BLE001
            log.exception("No pude restaurar tus escenarios")
        if core.clear_temp_mods():
            ctx.log(t("mods_temp_cleared"))
        try:
            _mods(ctx, gd, core.my_room_set(cfg))  # vuelven tus mods (o el juego sin mods)
        except ValueError as e:
            ctx.log(f"✗ {e}")
        try:
            ctx.log(t("fetching"))
            ctx.log(t("record", **core.sync_profile(url, steam_id, password)))
        except ValueError as e:
            ctx.log(t("sync_later", err=e))


def _room_mods(ctx, cfg, url, password, info, models=None):
    """Mods de la sala a la que te unes. En la sala de otro solo valen los suyos (todos los
    jugadores tienen que tener exactamente los mismos), asi que los tuyos se apartan un rato.
    Si la sala tambien tiene modelos 3D, se pregunta una sola vez por todo."""
    import modpack
    need = bool(info and info.get("hash"))
    mine = core.my_room_set(cfg)
    if need and info["hash"] == mine["hash"]:          # la sala usa justo tus mods: no hay nada que bajar
        need = False
    if need or (models and models.get("hash")):
        ask = getattr(ctx, "confirm_mods", None)
        shown = dict(info) if need else {"hash": "", "stickers": 0, "avatars": 0, "mods": []}
        shown["mods"] = list(shown.get("mods") or [])
        if models and models.get("hash"):
            shown["mods"].append({"name": t("models_room_entry"), "author": "", "stickers": 0, "avatars": 0,
                                  "text": t("models_room_count", models=models.get("models", 0),
                                            anims=models.get("anims", 0), mb=_mb(models.get("bytes", 0)))})
        if not ask or not ask(shown):
            raise ValueError(t("mods_declined"))
    if not need:
        return mine if info and info.get("hash") else modpack.room_set([])
    ctx.log(t("mods_downloading", stickers=info.get("stickers", 0), avatars=info.get("avatars", 0)))
    return core.download_mods(url, password, info["hash"])


def _mb(n):
    return "%.1f" % (max(int(n or 0), 0) / 1e6)


def _room_models(ctx, url, password, info):
    """Modelos 3D y animaciones de la sala a la que te unes (se bajan solo los archivos que no tengas)."""
    if not info or not info.get("hash"):
        return {"hash": "", "swaps": {}, "anims": {}, "files": {}}
    return core.download_models(url, password, info["hash"],
                                progress=lambda n: ctx.log(t("models_downloading", mb=_mb(n))))


def _offer_own_models(ctx, url, password, room, wait=60):
    """Ofrece tus modelos al anfitrion. Primero solo la lista: si acepta, se suben los archivos que le falten y
    se espera a que entren en la sala. Devuelve (modelos de la sala, oferta aun sin contestar o None)."""
    own = core.my_model_set()
    if not own["hash"]:
        return room, None
    try:
        status, oid, need = core.offer_models(url, password, own, core.steam_account()[1])
    except ValueError as e:
        ctx.log(f"✗ {e}")
        return room, None
    if status not in ("pending", "accepted"):
        return room, None
    if status == "pending":
        ctx.log(t("models_offer_sent"))
        ctx.log(t("mods_offer_waiting"))
    deadline = time.time() + wait
    while time.time() < deadline:
        if status == "accepted":
            new = _upload_and_wait(ctx, url, password, room, oid, own, need)
            return new, None
        time.sleep(2)
        status, need = core.offer_models_state(url, password, oid)
        if status == "rejected":
            return room, None
    ctx.log(t("models_offer_timeout"))
    return room, (oid, own)


def _upload_and_wait(ctx, url, password, room, oid, own, need, wait=30):
    """Oferta aceptada: sube lo que pide el anfitrion y baja la sala cuando ya los incluye."""
    if need:
        ctx.log(t("models_uploading", mb=_mb(sum(own["files"][s]["size"] for s in need if s in own["files"]))))
        try:
            core.upload_models(url, password, oid, own, need)
        except ValueError as e:
            ctx.log(f"✗ {e}")
            return room
    deadline = time.time() + wait
    while time.time() < deadline:
        h = (core.server_info(url).get("models") or {}).get("hash", "")
        if h and h != room.get("hash"):
            try:
                new = core.download_models(url, password, h, progress=lambda n: ctx.log(t("models_downloading", mb=_mb(n))))
            except ValueError as e:
                ctx.log(f"✗ {e}")
                return room
            ctx.log(t("models_offer_ok"))
            return new
        time.sleep(2)
    return room


def _room_models_watcher(ctx, cfg, url, password, rm, offer=None):
    """En la sala de otro: si cambian los modelos de la sala, se bajan los nuevos y se aplican en caliente. Si el
    anfitrion acepta tu oferta tarde (con el juego ya abierto), se suben entonces."""
    gd = cfg["game_dir"]
    state = {"hash": rm.get("hash", ""), "warned": False, "offer": offer, "busy": False}

    def upload_late(oid, own, need):
        try:
            core.upload_models(url, password, oid, own, need)
        except ValueError as e:
            ctx.log(f"✗ {e}")
        finally:
            state["busy"] = False

    def check():
        if state["offer"] and not state["busy"]:
            oid, own = state["offer"]
            st, need = core.offer_models_state(url, password, oid)
            if st == "accepted":
                state["offer"] = None
                if need:
                    state["busy"] = True
                    ctx.log(t("models_uploading", mb=_mb(sum(own["files"][s]["size"] for s in need if s in own["files"]))))
                    threading.Thread(target=upload_late, args=(oid, own, need), daemon=True).start()
            elif st == "rejected":
                state["offer"] = None
        h = (core.server_info(url).get("models") or {}).get("hash", "")
        if h == state["hash"]:
            return
        if not core.live_mode(gd):
            if not state["warned"]:
                ctx.log(t("mods_host_changed"))
                state["warned"] = True
            return
        new = core.download_models(url, password, h, progress=lambda n: ctx.log(t("models_downloading", mb=_mb(n)))) \
            if h else {"hash": "", "swaps": {}, "anims": {}, "files": {}}
        state["hash"] = h
        core.room_models = new
        core.install_models(gd)
        ctx.log(t("models_live_updated"))
    return check


def _models_room_start(cfg, srv):
    """Anfitrion o en solitario: tus modelos y personajes nuevos son los de la sala, y tu decides el Selector."""
    srv.models.set_base(core.my_model_set())
    core.room_disabled = srv.models.set_disabled(core.load_config().get("roster_disabled") or [])
    core.room_host = True
    core.room_roster = None
    core.room_models = srv.models.local()


def _models_room_end(gd):
    core.room_models = None
    core.room_roster = None
    core.room_disabled = []
    core.room_host = False
    try:
        core.install_models(gd)
    except OSError as e:
        log.warning("No pude volver a tus modelos: %s", e)


def _roster_watcher(ctx, cfg, url, steam_id, srv, password=""):
    """Reparto de personajes de cada partida (lo sortea el servidor al empezar la cuenta atras): se lo pasa al juego.
    El anfitrion, ademas, recoge lo que marca en el Selector de personajes del juego (srv: su servidor).
    On someone else's server, whoever created the room decides its Character Selection: their launcher sends it
    (check.stop() ends the quick check of the Selector)."""
    gd = cfg["game_dir"]
    state = {"id": None, "disabled": None, "answer": None, "owner": False, "room": None, "pushed": None,
             "seen": (core.roster_answer(gd) or (None,))[0]}
    lock = threading.Lock()
    stop = threading.Event()

    def pick_up():
        """What the host ticked in the Character Selection, for the server."""
        with lock:
            a = core.roster_answer(gd)
            if not a or a[0] == state["answer"]:
                return
            state["answer"] = a[0]
            core.room_disabled = srv.models.set_disabled(a[1])
            c2 = core.load_config()
            c2["roster_disabled"] = list(core.room_disabled)
            core.write_config(c2)
            cfg["roster_disabled"] = c2["roster_disabled"]
        core.install_models(gd)
        ctx.log(t("roster_saved"))

    if srv is not None:
        # The server also picks it up right before drawing a match's characters: checking every few seconds alone,
        # a match started just after closing the Selector still used the old choice (e.g. a character you had just
        # turned off was still in it).
        srv.models.before_draw = pick_up

    def send(ids, save):
        """Room creator on someone else's server: the room's Character Selection goes to the server."""
        done = core.roster_select(url, password, steam_id, ids)
        if done is None:
            return
        with lock:
            core.room_disabled = done
            state["disabled"] = done
            if save:                                    # your choice is kept for the next room you create
                c2 = core.load_config()
                c2["roster_disabled"] = list(done)
                core.write_config(c2)
                cfg["roster_disabled"] = c2["roster_disabled"]
        if core.room_models is not None and core.live_mode(gd):
            core.install_models(gd)
        if save:
            ctx.log(t("roster_saved"))

    def quick():
        """Checks the Selector 4 times a second, so a match started right after saving uses the new choice."""
        while not stop.wait(0.25):
            try:
                a = core.roster_answer(gd)
                if not a or a[0] == state["seen"]:
                    continue
                state["seen"] = a[0]
                if state["owner"]:
                    send(a[1], True)
            except Exception:  # noqa: BLE001
                log.exception("Fallo enviando el Selector de personajes")

    if srv is None:
        threading.Thread(target=quick, daemon=True).start()

    def check():
        if srv is not None:
            pick_up()
        roster, disabled, room, owner = core.roster_state(url, steam_id)
        if roster == "error":
            return
        if srv is None:
            if owner and room is not None and room != state["pushed"]:
                # a room you just created starts with your last Character Selection
                state["pushed"] = room
                send(cfg.get("roster_disabled") or [], False)
                return
            if owner != state["owner"] or room != state["room"]:
                state["owner"], state["room"] = owner, room
                core.room_host = owner                  # the Selector can be changed only by the room's creator
                state["disabled"] = None                # rewrite the Selector's list below
        rid = (roster or {}).get("id")
        if rid != state["id"] or disabled != state["disabled"]:
            state["id"], state["disabled"] = rid, disabled
            core.room_roster = roster
            if srv is None:
                core.room_disabled = disabled
            if core.room_models is not None and core.live_mode(gd):
                core.install_models(gd)
    check.stop = stop.set
    return check


def _host_models_watcher(ctx, cfg, srv):
    """Anfitrion: tus cambios de modelos llegan a la sala, y cuando un jugador trae modelos te pregunta si los
    aceptas (como con los stickers). El juego del anfitrion ve los de la sala (los tuyos + los aceptados)."""
    gd = cfg["game_dir"]
    room = srv.models
    state = {"own": room.base.get("hash", ""), "room": room.ms["hash"], "asked": set()}

    def check():
        live = core.live_mode(gd)
        own = core.my_model_set()
        if own["hash"] != state["own"]:
            state["own"] = own["hash"]
            room.set_base(own)
        for off in room.pending_list():
            if off["id"] in state["asked"]:
                continue
            state["asked"].add(off["id"])
            if not live:
                ctx.log(t("mods_offer_need_live", player=off["player"]))
                room.answer(off["id"], False)
                continue
            auto = bool(cfg.get("guest_mods_always"))
            ask = getattr(ctx, "confirm_offer", None)
            entry = {"name": t("models_room_entry"), "author": "", "stickers": 0, "avatars": 0,
                     "text": t("models_room_count", models=off["models"], anims=off["anims"], mb=_mb(off["bytes"]))}
            info = dict(off, mods=[entry], text=t("models_offer_text", player=off["player"], mb=_mb(off["bytes"])))
            ok = auto or bool(ask and ask(info))
            room.answer(off["id"], ok)
            if ok:
                ctx.log(t("mods_offer_auto" if auto else "mods_offer_accepted", player=off["player"]))
        if room.ms["hash"] != state["room"]:
            state["room"] = room.ms["hash"]
            core.room_models = room.local()
            if live:
                core.install_models(gd)
                ctx.log(t("models_live_updated"))
    return check


def _offer_own(ctx, cfg, url, password, room, wait=60):
    """Ofrece tus mods al anfitrion: si los acepta, los veis todos en la sala. Devuelve los mods con
    los que se entra en la sala.

    Se espera a que el anfitrion conteste ANTES de abrir el juego: si el juego arrancara con los mods
    de la sala sin los tuyos, al no encontrar tus stickers los quitaria de tu rueda (y lo guarda), y
    cuando llegaran despues ya no estarian puestos: solo verias los del anfitrion."""
    own = core.my_room_set(cfg)
    have = {m["uid"] for m in room.get("mods", [])}
    if not own["hash"] or all(m["uid"] in have for m in own["mods"]):
        return room
    try:
        status = core.offer_mods(url, password, own, core.steam_account()[1])
    except ValueError as e:
        ctx.log(f"✗ {e}")
        return room
    if status not in ("pending", "accepted"):
        return room
    if status == "pending":
        ctx.log(t("mods_offer_sent"))
        ctx.log(t("mods_offer_waiting"))
    mine = {m["uid"] for m in own["mods"]}
    deadline = time.time() + (wait if status == "pending" else 10)
    while time.time() < deadline:
        h = (core.server_info(url).get("mods") or {}).get("hash", "")
        if h and h != room.get("hash"):
            try:
                new = core.download_mods(url, password, h)
            except ValueError as e:
                ctx.log(f"✗ {e}")
                return room
            if mine <= {m["uid"] for m in new.get("mods", [])}:
                ctx.log(t("mods_offer_ok"))
                return new
            room = new                    # el anfitrion cambio otra cosa: se sigue esperando
        time.sleep(2)
    ctx.log(t("mods_offer_timeout"))
    return room
