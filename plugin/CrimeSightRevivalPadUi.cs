// CRIMESIGHT Revival - mando en las pantallas fuera de la partida (crear sala, sala de espera y sus ventanas).
//
// Cada pantalla tiene sus botones del mando, y el boton del juego que pulsan lleva delante de su texto el icono
// del boton del mando (se quita en cuanto deja de valer):
//
//   Crear sala:              Start  Crear sala           B  Atras
//   Sala de espera:          Start  Iniciar partida      B  Abandonar sala     Back  Modificar ajustes del juego
//                            Cruceta izquierda  Expulsar al jugador elegido (en una IA abre su dificultad)
//                            Y                  Elegir a quien (pasa al siguiente, de arriba abajo)
//                            Cruceta derecha    Anadir jugadores (+)
//                            Cruceta abajo      Quitar todos los huecos vacios (-)
//   Inicio:                  Start  Jugar                Back  Perfil
//   Perfil:                  Back   Resultado            Y     Cambiar avatar      B  Atras
//   Ajustes del sistema:     Start  Aplicar              Back  Restablecer         B  Cerrar
//                            LB / RB  pestana anterior / siguiente
//   Avisos (el anfitrion ha cambiado, errores): B o Start  Cerrar
//   Confirmaciones de la partida:              Start  Confirmar   B  Cancelar
//   Ajustes del juego:       Start  Aplicar              B  Cerrar             Back  Restablecer valores
//   ...su confirmacion:      Start  Confirmar            B  Cancelar
//   Abandonar la sala:       Start  Confirmar            B  Volver
//   Dificultad de una IA:    Y  Solo esta IA / Todas     X  Dejar el hueco libre   B  Cancelar
//   Resultado:               Start  Cerrar resultados    B  Siguiente / Atras
//   Revancha:                Start  Revancha             B  Abandonar
//   Donde se vea la rueda de ajustes (o la llave de la partida):  cruceta arriba
//   Dialogo de un personaje (Sherlock...): B  Omitir (CrimeSightRevivalTalk.cs)
//
// En la partida B es "Cancelar" (Esc; si esta abierta la ventana de stickers, la cierra), Start "Finalizar turno",
// Back el registro y LB/RB giran la camara. Fuera de la partida B es el clic derecho donde no haga otra cosa.
// Los botones se pulsan de verdad (el cursor va encima, clic y vuelve), como con el raton.
// Los iconos solo se ven mientras se usa el mando (se quitan en cuanto se toca el raton o el teclado).
using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace CrimeSightRevival.Mods
{
    static partial class Pad
    {
        static Button _uiB, _uiStart, _uiBack, _uiGear, _uiLB, _uiRB, _uiDown, _uiY;
        static Button _uiTabPrev, _uiTabNext;                    // pestanas de los ajustes (LB / RB)
        static bool _uiTabs;
        static readonly Dictionary<int, TMP_Text> _labelFor = new();          // texto de un boton que no lo lleva dentro
        static readonly List<(TMP_Text tmp, string btn)> _tagText = new();    // textos de la interfaz sin boton que se pueda pulsar
        static readonly List<(TMP_Text tmp, string btn)> _tag3d = new();      // textos 3D de la escena (rombos del inicio)
        static readonly HashSet<int> _hintAbove = new();                        // botones sin texto con el icono encima
        static readonly List<(Button b, string btn)> _tagOnly = new();        // botones que solo llevan icono (lo pulsa otra cosa)
        static bool _uiError, _uiRoom, _slow;
        static Home _home;                                       // pantalla de inicio (Jugar / Perfil)
        static GameObject _pawnPanel;                            // retratos A-F de la partida (la cruceta va de uno a otro)                           // aviso del juego abierto / sala de espera
        static int _kickFocus, _kickCount;
        static float _minusUntil, _minusNext;
        static RectTransform _uiTalkClose;                       // "Cerrar" del dialogo de un personaje
        static bool _gearInGame;                                 // la rueda es la llave de la partida
        static PingStampMenuBase _stampMenu;                     // ventana de stickers abierta al pulsar B
        static int _stampCloseAt = -1;
        static string _uiWhere = "";
        static bool _uiPicker;                                   // la ventana de dificultad de una IA (AiPicker)
        static float _uiNext;

        // La sala de espera detras de una ventana (ajustes, confirmaciones...): sus iconos se quedan, mas claros y sin
        // hacer nada, para que no desaparezcan de golpe al abrirla. El mando sigue yendo solo a la ventana de encima.
        static bool _bgRoom;
        static Button _bgB, _bgStart, _bgBack, _bgKick, _bgPlus, _bgMinus;
        const float Faded = 0.35f;
        static readonly HashSet<string> _overRoom = new()
        {
            "aviso", "dificultad de la IA", "expulsar (confirmar)", "aviso de plazas", "confirmacion",
            "ajustes del sistema", "ajustes del sistema (confirmar)", "opciones", "abandonar sala",
            "ajustes del juego", "ajustes (confirmar)", "cuenta atras", "sala (ventana encima)",
        };
        static bool _bConsumed, _gearHeld, _xTaken, _yTaken, _arrowHeld;
        static bool _uiWarned;

        internal static bool Connected => _connected;
        /// <summary>Se esta usando el mando (lo ultimo que se ha tocado): solo entonces se ven sus iconos.</summary>
        internal static bool Active => _connected && _padMode;

        /// <summary>El icono de un boton del mando para meterlo en un texto ("b", "start", "back", "dpad_up"...).</summary>
        internal static string Tag(string btn)
        {
            if (!Active) return "";
            string n = btn.StartsWith("dpad") || btn.EndsWith("stick") ? btn : _style + "_" + btn;
            return $"<sprite name=\"csr_{n}\"> ";
        }

        /// <summary>El mismo icono, mas claro: el de un boton de la sala que queda detras de una ventana.</summary>
        static string FadedTag(string btn)
        {
            if (!Active) return "";
            string n = btn.StartsWith("dpad") || btn.EndsWith("stick") ? btn : _style + "_" + btn;
            return $"<sprite name=\"csr_{n}\" color=#FFFFFF{(int)(Faded * 255):X2}> ";
        }

        /// <summary>Se ve, aunque no se pueda pulsar (activo y sin un CanvasGroup que lo oculte).</summary>
        static bool Visible(Button b)
        {
            if (b == null || !b.gameObject.activeInHierarchy) return false;
            for (var t = b.transform; t != null; t = t.parent)
            {
                var cg = t.GetComponent<CanvasGroup>();
                if (cg != null && cg.alpha < 0.05f) return false;
                if (cg != null && cg.ignoreParentGroups) break;
            }
            return true;
        }

        /// <summary>La sala de espera que se ve detras de la ventana de encima (si la hay): sus botones con icono.</summary>
        static void RoomBehind(string where)
        {
            if (_uiRoom || _inGame || !_overRoom.Contains(where)) return;
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameRoomWaitingMenuVer2>()))
            {
                var room = o?.TryCast<OutGameRoomWaitingMenuVer2>();
                if (room == null || !room.gameObject.activeInHierarchy) continue;
                Button back = Btn(room.HostBackTButton);
                if (!Visible(back)) back = Btn(room.GuestBackTButton);
                var start = Btn(room.HostStartTButton);
                if (!Visible(back) && !Visible(start)) continue;
                if (Visible(back)) _bgB = back;
                if (Visible(start)) _bgStart = start;
                if (Visible(room.ChangeRoomSettingButton)) _bgBack = room.ChangeRoomSettingButton;
                _bgKick = KickButton(room, true);
                _bgPlus = PlusButton(true);
                _bgMinus = MinusButton(true);
                _bgRoom = true;
                return;
            }
        }

        /// <summary>Un icono suelto, normal o mas claro.</summary>
        static void Fade(GameObject go, bool faded)
        {
            if (go == null) return;
            var cg = go.GetComponent<CanvasGroup>();
            if (cg == null) { if (!faded) return; cg = go.AddComponent<CanvasGroup>(); cg.blocksRaycasts = false; cg.interactable = false; }
            float a = faded ? Faded : 1f;
            if (cg.alpha != a) cg.alpha = a;
        }

        // ------------------------------------------------------------ que hace cada boton aqui
        static void UiScan()
        {
            if (Time.unscaledTime < _uiNext) return;
            _uiNext = Time.unscaledTime + 0.15f;
            _uiB = _uiStart = _uiBack = _uiGear = _uiLB = _uiRB = _uiDown = _uiY = null;
            _uiTabPrev = _uiTabNext = null;
            _uiTabs = false;
            _uiError = _uiRoom = _slow = false;
            _home = null;
            _pawnPanel = null;
            _labelFor.Clear();
            _tagText.Clear();
            _tag3d.Clear();
            _hintAbove.Clear();
            _tagOnly.Clear();
            _uiTalkClose = null;
            _uiPicker = false;
            _bgRoom = false;
            _bgB = _bgStart = _bgBack = _bgKick = _bgPlus = _bgMinus = null;
            string where = "";
            try { where = Contexts(); } catch (Exception e) { Warn("sala: " + e.Message); }
            try { RoomBehind(where); } catch (Exception e) { Warn("sala detras: " + e.Message); }
            try { if (!_uiPicker && _uiB == null) _uiTalkClose = TalkClose(); } catch { }
            if (where != _uiWhere) { _uiWhere = where; if (where != "") Log("pantalla: " + where); }
            try { _uiGear = Gear(); } catch { }
            Labels();
        }

        static void Warn(string m) { if (!_uiWarned) { _uiWarned = true; Plugin.L.LogWarning("[Mando] " + m); } }

        static string Contexts()
        {
            // de la ventana de mas arriba a la de mas abajo: la primera que se vea manda
            try { if (ErrorMessageManager.IsDisplayErrorMessage()) { _uiError = true; return "aviso"; } } catch { }
            if (AiPicker.IsOpen) { _uiPicker = true; return "dificultad de la IA"; }
            var kick = Find<OutGameRoomPopupKickConfirm>();
            if (kick != null && Shown(kick.BackButton)) { _uiB = kick.BackButton; _uiStart = kick.ConfirmButton; return "expulsar (confirmar)"; }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameRoomPopupNoticeChangeCapacity>()))
            {
                var n = o?.TryCast<OutGameRoomPopupNoticeChangeCapacity>();
                if (n != null && Shown(n.BackButton)) { _uiB = _uiStart = n.BackButton; return "aviso de plazas"; }
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameErrorEnterRoom>()))
            {
                var n = o?.TryCast<OutGameErrorEnterRoom>();
                if (n != null && Shown(n.BackButton)) { _uiB = _uiStart = n.BackButton; return "no se pudo entrar"; }
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<ConfirmUI>()))
            {
                var c = o?.TryCast<ConfirmUI>();
                if (c == null || !c.gameObject.activeInHierarchy) continue;
                bool on; try { on = c.IsActivated(); } catch { on = false; }
                if (!on || (!Shown(c.confirmButton) && !Shown(c.denyButton))) continue;
                if (Shown(c.confirmButton)) _uiStart = c.confirmButton;
                if (Shown(c.denyButton)) _uiB = c.denyButton;
                return "confirmacion";
            }
            // ajustes del sistema (la rueda, y la llave en la partida)
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<SystemSettingController>()))
            {
                var c = o?.TryCast<SystemSettingController>();
                if (c == null || !c.gameObject.activeInHierarchy) continue;
                if (Shown(c.DestroyCancelButton)) { _uiB = c.DestroyCancelButton; _uiStart = c.DestroyConfirmButton; return "ajustes del sistema (confirmar)"; }
                var back = Btn(c.BackTButton);
                if (!Shown(back)) continue;
                _uiB = back; _uiStart = Btn(c.ApplyTButton); _uiBack = Btn(c.DefaultTButton);
                if (!Shown(_uiStart)) _uiStart = SettingsAction();             // pestanas sin "Aplicar": Penalizacion, Salir...
                Tabs(c.tabParentObject != null ? c.tabParentObject.transform : c.transform);
                return "ajustes del sistema";
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<SystemSetting>()))
            {
                var c = o?.TryCast<SystemSetting>();
                if (c == null || !c.gameObject.activeInHierarchy) continue;
                if (Shown(c.DestroyCancelButton)) { _uiB = c.DestroyCancelButton; _uiStart = c.DestroyConfirmButton; return "ajustes del sistema (confirmar)"; }
                var back = Btn(c.BackTButton);
                if (!Shown(back)) continue;
                _uiB = back; _uiStart = Btn(c.ApplyTButton); _uiBack = Btn(c.DefaultTButton);
                if (!Shown(_uiStart)) _uiStart = SettingsAction();             // pestanas sin "Aplicar": Penalizacion, Salir...
                Tabs(c.transform);
                return "ajustes del sistema";
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameOptionMainPopup>()))
            {
                var c = o?.TryCast<OutGameOptionMainPopup>();
                if (c != null && c.gameObject.activeInHierarchy && Shown(c.BackButton)) { _uiB = c.BackButton; return "opciones"; }
            }
            var leave = Find<OutGameRoomPopupLeaveRoom>();
            if (leave != null && Shown(leave.BackButton)) { _uiB = leave.BackButton; _uiStart = leave.ConfirmButton; return "abandonar sala"; }
            var set = Find<OutGameRoomPopupRoomSetting>();
            if (set != null)
            {
                if (Shown(set.DestroyCancelButton)) { _uiB = set.DestroyCancelButton; _uiStart = set.DestroyConfirmButton; return "ajustes (confirmar)"; }
                if (Shown(set.BackButton)) { _uiB = set.BackButton; _uiStart = set.ApplyButton; _uiBack = set.DefaultButton; return "ajustes del juego"; }
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameRoomPopupCountdown>()))
            {
                var c = o?.TryCast<OutGameRoomPopupCountdown>();
                if (c != null && c.gameObject.activeInHierarchy && Shown(c.BackButton)) { _uiB = c.BackButton; return "cuenta atras"; }
            }
            var rematch = Find<OutGameRematchPopup>();
            if (rematch != null && (Shown(rematch.ConfirmButton) || Shown(rematch.BackButton)))
            {
                if (Shown(rematch.ConfirmButton)) _uiStart = rematch.ConfirmButton;
                if (Shown(rematch.BackButton)) _uiB = rematch.BackButton;
                return "revancha";
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameResult>()))
            {
                var res = o?.TryCast<OutGameResult>();
                if (res == null || !res.gameObject.activeInHierarchy) continue;
                var close = Btn(res.NextTButton); var page = Btn(res.ScrollTButton);
                if (!Shown(close) && !Shown(page)) continue;
                if (Shown(close)) _uiStart = close;
                if (Shown(page)) _uiB = page;
                return "resultado";
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameTips>()))
            {
                var tp = o?.TryCast<OutGameTips>();
                if (tp == null || !tp.gameObject.activeInHierarchy) continue;
                Button close = null;
                try { close = tp.CloseButtonObj != null ? tp.CloseButtonObj.GetComponentInChildren<Button>() : null; } catch { }
                bool prev = Shown(tp.prevButton), next = Shown(tp.nextButton);
                if (!Shown(close) && !prev && !next) continue;
                if (Shown(close)) _uiB = close;
                if (prev) { _uiTabPrev = tp.prevButton; _tagOnly.Add((tp.prevButton, "lb")); _hintAbove.Add(tp.prevButton.GetInstanceID()); }
                if (next) { _uiTabNext = tp.nextButton; _tagOnly.Add((tp.nextButton, "rb")); _hintAbove.Add(tp.nextButton.GetInstanceID()); }
                _uiTabs = true;
                return "consejos / guia";
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameProfile>()))
            {
                var pr = o?.TryCast<OutGameProfile>();
                if (pr == null || !pr.gameObject.activeInHierarchy) continue;
                if (!Shown(pr.ResultButton) && !Shown(pr.CursorAvatarButton)) continue;
                if (Shown(pr.ResultButton)) _uiBack = pr.ResultButton;
                if (Shown(pr.CursorAvatarButton)) _uiY = pr.CursorAvatarButton;
                try { var cb = pr.CloseButtonObj != null ? pr.CloseButtonObj.GetComponentInChildren<Button>() : null; if (Shown(cb)) _uiB = cb; } catch { }
                return "perfil";
            }
            // crear sala antes que la sala de espera: la sala puede estar cargada (y "activa") detras
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameCreateRoomMenu>()))
            {
                var create = o?.TryCast<OutGameCreateRoomMenu>();
                if (create == null || !create.gameObject.activeInHierarchy) continue;
                var ok = Btn(create.decideTButton); var no = Btn(create.cancelTButton);
                if (!Shown(ok) && !Shown(no)) continue;
                if (Shown(ok)) _uiStart = ok;
                if (Shown(no)) _uiB = no;
                return "crear sala";
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameRoomWaitingMenuVer2>()))
            {
                var room = o?.TryCast<OutGameRoomWaitingMenuVer2>();
                if (room == null || !room.gameObject.activeInHierarchy) continue;
                Button back = Btn(room.HostBackTButton);
                if (!Shown(back)) back = Btn(room.GuestBackTButton);
                var start = Btn(room.HostStartTButton);
                if (!Shown(back) && !Shown(start)) continue;              // cargada pero no es la que se ve
                bool cover;
                try { cover = room.IsOverlaySomeUI(); } catch { cover = false; }
                if (cover) return "sala (ventana encima)";             // lista de amigos, stickers...: como siempre
                if (Shown(back)) _uiB = back;
                if (Shown(start)) _uiStart = start;
                if (Shown(room.ChangeRoomSettingButton)) _uiBack = room.ChangeRoomSettingButton;
                _uiLB = KickButton(room);
                _uiRB = PlusButton();
                _uiDown = MinusButton();
                _uiRoom = true;
                return "sala de espera";
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<Home>()))
            {
                var h = o?.TryCast<Home>();
                if (h == null || !h.gameObject.activeInHierarchy) continue;
                Button play = null, prof = null;
                try { play = h.uiPlayButton?.stateButton; } catch { }
                try { prof = h.uiProfileButton?.stateButton; } catch { }
                bool glass = false;
                try { glass = (h.playButton != null && h.playButton.gameObject.activeInHierarchy) || (h.profileButton != null && h.profileButton.gameObject.activeInHierarchy); } catch { }
                if (!Shown(play) && !Shown(prof) && !glass) continue;
                _home = h;
                if (Shown(play)) { _uiStart = play; try { _labelFor[play.GetInstanceID()] = h.uiPlayButton.titleText; } catch { } }
                if (Shown(prof)) { _uiBack = prof; try { _labelFor[prof.GetInstanceID()] = h.uiProfileButton.titleText; } catch { } }
                // el nombre que se ve: el de la interfaz (aunque su boton no se pueda pulsar) o, si no, el del rombo 3D
                void HomeTag(HomeUiButton ui, HomeGlassButton g, string btn)
                {
                    try
                    {
                        var tt = ui != null ? ui.titleText : null;
                        if (tt != null && tt.gameObject.activeInHierarchy && tt.color.a > 0.05f && !string.IsNullOrEmpty(tt.text)) { _tagText.Add((tt, btn)); return; }
                        var gt = g != null ? g.displayText : null;
                        if (gt != null && gt.gameObject.activeInHierarchy) _tag3d.Add((gt, btn));
                    }
                    catch { }
                }
                if (!Shown(play)) HomeTag(h.uiPlayButton, h.playButton, "start");
                if (!Shown(prof)) HomeTag(h.uiProfileButton, h.profileButton, "back");
                _slow = true;                                                // los rombos del inicio piden el cursor encima un rato
                string hk = $"{Shown(play)}{Shown(prof)}{_tagText.Count}{_tag3d.Count}";
                if (hk != _homeLogKey)
                {
                    _homeLogKey = hk;
                    string D(HomeGlassButton g) { try { return g == null ? "no hay" : $"{g.gameObject.name} activo={g.gameObject.activeInHierarchy} texto={(g.displayText != null ? g.displayText.name : "no")}"; } catch (Exception e) { return e.Message; } }
                    string U(HomeUiButton u) { try { return u == null || u.titleText == null ? "no" : $"'{u.titleText.text}' activo={u.titleText.gameObject.activeInHierarchy} alfa={u.titleText.color.a:0.00}"; } catch (Exception e) { return e.Message; } }
                    Log($"inicio: Jugar 3D {D(h.playButton)} | Perfil 3D {D(h.profileButton)} | botones de la interfaz {Shown(play)}/{Shown(prof)} | textos {U(h.uiPlayButton)} / {U(h.uiProfileButton)} | iconos: {_tagText.Count} texto, {_tag3d.Count} 3D");
                }
                return "inicio";
            }
            var hud = GetHud();
            if (hud != null && hud.gameObject.activeInHierarchy)
            {
                // la partida: Start "Finalizar turno", Back el registro (este lo abre Pad.ToggleLog; aqui solo el icono)
                if (Shown(hud.instructCompleteButton)) _uiStart = hud.instructCompleteButton;
                else if (Shown(hud.skipActionPhaseButton)) _uiStart = hud.skipActionPhaseButton;
                try { var lw = InGameLogManager.Instance?.logWindow; if (lw != null && Shown(lw.rootButton)) _tagOnly.Add((lw.rootButton, "back")); } catch { }
                try { _pawnPanel = hud.pawnsPanelSum; } catch { }
                return "partida";
            }
            return "";
        }

        /// <summary>El "Cerrar" del dialogo de un personaje, si se esta viendo.</summary>
        static RectTransform TalkClose()
        {
            var d = CharaTalkDialogue.Instance;
            if (d == null || !d.gameObject.activeInHierarchy) return null;
            var go = d.closeButton;
            if (go == null || !go.activeInHierarchy) return null;
            if (d.dialogueCanvas != null && !d.dialogueCanvas.enabled) return null;
            var b = go.GetComponentInChildren<Button>();
            if (b != null) return Shown(b) ? b.GetComponent<RectTransform>() : null;
            return go.GetComponent<RectTransform>();
        }

        static Button Btn(TextButton t)
        {
            Button b = null;
            try { b = t?.GetButton(); } catch { }
            if (b == null) try { b = t?.button; } catch { }
            return b;
        }

        /// <summary>El boton de expulsar del jugador elegido con Y (de arriba abajo; al principio, el primero).</summary>
        static Button KickButton(OutGameRoomWaitingMenuVer2 room, bool behind = false)
        {
            var list = room.playerKickButtonList;
            _kickCount = 0;
            if (list == null) return null;
            var shown = new List<Button>();
            for (int i = 0; i < list.Count; i++) if (behind ? Visible(list[i]) : Shown(list[i])) shown.Add(list[i]);
            if (shown.Count == 0) return null;
            shown.Sort((a, b) => ScreenPos(b).y.CompareTo(ScreenPos(a).y));       // de arriba abajo
            _kickCount = shown.Count;
            if (_kickFocus >= shown.Count) _kickFocus = shown.Count - 1;
            if (_kickFocus < 0) _kickFocus = 0;
            return shown[_kickFocus];
        }

        /// <summary>El "-" de un hueco vacio (el de mas abajo).</summary>
        static Button MinusButton(bool behind = false)
        {
            Button best = null;
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<RoomPlayerList>()))
            {
                var r = o?.TryCast<RoomPlayerList>();
                var b = r?.PlayerMinusButton;
                if (behind ? !Visible(b) : !Shown(b)) continue;
                if (best == null || ScreenPos(b).y < ScreenPos(best).y) best = b;
            }
            return best;
        }

        /// <summary>El "+" para anadir jugadores (el primero, de arriba abajo).</summary>
        static Button PlusButton(bool behind = false)
        {
            Button best = null;
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<RoomPlayerList>()))
            {
                var r = o?.TryCast<RoomPlayerList>();
                var b = r?.PlayerPlusButton;
                if (behind ? !Visible(b) : !Shown(b)) continue;
                if (best == null || ScreenPos(b).y > ScreenPos(best).y) best = b;
            }
            return best;
        }

        static Vector2 ScreenPos(Button b)
        {
            var rt = b.GetComponent<RectTransform>();
            Camera cam = null;
            var canvas = b.GetComponentInParent<Canvas>();
            if (canvas != null) { canvas = canvas.rootCanvas; if (canvas.renderMode != RenderMode.ScreenSpaceOverlay) cam = canvas.worldCamera; }
            return RectTransformUtility.WorldToScreenPoint(cam, rt.TransformPoint(rt.rect.center));
        }

        /// <summary>La rueda de ajustes que se vea: la de los menus y la sala, o la de la partida.</summary>
        static Button Gear()
        {
            _gearInGame = false;
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OutGameRoomToolButtons>()))
            {
                var tb = o?.TryCast<OutGameRoomToolButtons>();
                if (tb != null && Shown(tb.OptionButton)) return tb.OptionButton;
            }
            var hud = GetHud();
            if (hud == null || !hud.gameObject.activeInHierarchy) return null;
            _gearInGame = true;
            if (Shown(hud.OptionButton)) return hud.OptionButton;
            if (Shown(hud.SystemSettingButton)) return hud.SystemSettingButton;
            return null;
        }

        /// <summary>Se ve y se puede pulsar (activo, interactuable y sin un CanvasGroup que lo oculte).</summary>
        static bool Shown(Button b)
        {
            if (b == null || !b.gameObject.activeInHierarchy || !b.IsInteractable()) return false;
            for (var t = b.transform; t != null; t = t.parent)
            {
                var cg = t.GetComponent<CanvasGroup>();
                if (cg != null && (cg.alpha < 0.05f || (!cg.interactable && !cg.ignoreParentGroups))) return false;
                if (cg != null && cg.ignoreParentGroups) break;
            }
            return true;
        }

        // ------------------------------------------------------------ botones del mando
        static bool Press(Button b)
        {
            if (_clickStage != 0 || b == null || !Shown(b) || !ClickAt(b)) return false;
            if (_slow) _clickHover = 14;
            return true;
        }
        static bool PressRect(RectTransform rt) => _clickStage == 0 && rt != null && ClickAt(rt);

        static PingStampMenuBase OpenStampMenu()
        {
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<PingStampMenuBase>()))
            {
                var m = o?.TryCast<PingStampMenuBase>();
                try { if (m != null && m.IsActive()) return m; } catch { }
            }
            return null;
        }

        /// <summary>B en la partida es Cancelar (Esc); si la ventana de stickers sigue abierta un momento despues, se cierra.</summary>
        static void StampClose()
        {
            if (Pressed(B) && _inGame && !_bConsumed)
            {
                try { _stampMenu = OpenStampMenu(); } catch { _stampMenu = null; }
                if (_stampMenu != null) _stampCloseAt = Time.frameCount + 4;
            }
            if (_stampMenu == null || Time.frameCount < _stampCloseAt) return;
            try { if (_stampMenu.IsActive()) _stampMenu.SetActive(false); }
            catch (Exception e) { Warn("stickers: " + e.Message); }
            _stampMenu = null;
        }

        /// <summary>Las pestanas de los ajustes, de izquierda a derecha: la anterior y la siguiente a la que esta
        /// elegida. La elegida es la que se ve distinta de las demas (su imagen o su color).</summary>
        static void Tabs(Transform root)
        {
            _uiTabs = true;                                              // LB/RB son de las pestanas (no giran la camara)
            // SystemSettingTab: la elegida lleva su imagen "on" (TabOnSprite). SystemSettingTabView: la elegida es
            // la unica con otro color (imagen o texto).
            var tabs = new List<(Button b, string sig, bool on)>();
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<SystemSettingTab>()))
            {
                var t = o?.TryCast<SystemSettingTab>();
                if (t == null || t.TabButton == null || !t.TabButton.gameObject.activeInHierarchy || !t.transform.IsChildOf(root)) continue;
                bool on = false;
                try { on = t.TabImage != null && t.TabImage.sprite != null && t.TabOnSprite != null && t.TabImage.sprite.Pointer == t.TabOnSprite.Pointer; } catch { }
                tabs.Add((t.TabButton, "", on));
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<SystemSettingTabView>()))
            {
                var t = o?.TryCast<SystemSettingTabView>();
                if (t == null || t.TabButton == null || !t.TabButton.gameObject.activeInHierarchy || !t.transform.IsChildOf(root)) continue;
                string sig = "";
                try { sig = (t.TabImage != null ? t.TabImage.color.ToString() + (t.TabImage.sprite != null ? t.TabImage.sprite.name : "") : "") + "/" + (t.TabText != null ? t.TabText.color.ToString() : ""); } catch { }
                tabs.Add((t.TabButton, sig, false));
            }
            if (tabs.Count < 2) { TabLog($"pestanas: solo {tabs.Count}"); return; }
            tabs.Sort((a, b) => ScreenPos(a.b).x.CompareTo(ScreenPos(b.b).x));
            int cur = tabs.FindIndex(t => t.on);
            if (cur < 0)
                for (int i = 0; i < tabs.Count; i++)
                {
                    int same = 0;
                    foreach (var g in tabs) if (g.sig == tabs[i].sig) same++;
                    if (same == 1 && tabs[i].sig != "") { cur = i; break; }      // la unica distinta
                }
            if (cur < 0) { TabLog($"pestanas: {tabs.Count}, no se cual esta elegida"); return; }
            TabLog($"pestanas: {tabs.Count}, elegida la {cur + 1}");
            for (int i = cur - 1; i >= 0; i--) if (tabs[i].b.IsInteractable()) { _uiTabPrev = tabs[i].b; break; }
            for (int i = cur + 1; i < tabs.Count; i++) if (tabs[i].b.IsInteractable()) { _uiTabNext = tabs[i].b; break; }
            if (_uiTabPrev != null) _tagOnly.Add((_uiTabPrev, "lb"));
            if (_uiTabNext != null) _tagOnly.Add((_uiTabNext, "rb"));
        }

        static string _tabLogged;
        static void TabLog(string m) { if (_tabLogged != m) { _tabLogged = m; Log(m); } }

        /// <summary>El boton de la pestana de ajustes que se este viendo y no tenga "Aplicar" (Penalizacion, Salir).</summary>
        static Button SettingsAction()
        {
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<SystemSettingSurrenderItem>()))
            { var i = o?.TryCast<SystemSettingSurrenderItem>(); if (i != null && Shown(i.SurrenderButton)) return i.SurrenderButton; }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<SystemSettingQuitSoloMatchItem>()))
            { var i = o?.TryCast<SystemSettingQuitSoloMatchItem>(); if (i != null && Shown(i.QuitButton)) return i.QuitButton; }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<SystemSettingQuitItem>()))
            { var i = o?.TryCast<SystemSettingQuitItem>(); if (i != null && Shown(i.QuitButton)) return i.QuitButton; }
            return null;
        }

        static bool HomeMenu(string name)
        {
            try
            {
                if (_home == null) return false;
                string n = name;
                _home.CallMenu(ref n);
                _uiNext = 0;
                return true;
            }
            catch (Exception e) { Warn("inicio: " + e.Message); return false; }
        }

        static void CyclePawn(int dir)
        {
            var gm = GameManager.instance;
            var pc = gm != null ? gm.pawnController : null;
            if (pc == null) return;
            int n = gm.GetPawnCount();
            if (n <= 0) return;
            var cur = pc.GetSelectPawn();
            int ci = -1;
            for (int i = 0; i < n && cur != null; i++)
            {
                int k = i;
                var p = gm.GetPawn(ref k);
                if (p != null && p.Pointer == cur.Pointer) { ci = i; break; }
            }
            int start = ci >= 0 ? ci : (dir > 0 ? -1 : n);
            for (int step = 1; step <= n; step++)
            {
                int i = ((start + dir * step) % n + n) % n;
                var p = gm.GetPawn(ref i);
                if (p == null || !p.gameObject.activeInHierarchy) continue;
                pc.SelectPawnWithFocus(ref p);
                var now = pc.GetSelectPawn();
                if (now != null && now.Pointer == p.Pointer) return;
            }
        }

        static bool _gearMissLogged;
        static void GearMiss()
        {
            if (_gearMissLogged) return;
            _gearMissLogged = true;
            try
            {
                var hud = GetHud();
                string D(Button b) => b == null ? "null" : $"{b.gameObject.name} activo={b.gameObject.activeInHierarchy} interactuable={b.IsInteractable()} visible={Shown(b)}";
                Log("cruceta arriba: no encuentro la llave. OptionButton: " + D(hud?.OptionButton) + " | SystemSettingButton: " + D(hud?.SystemSettingButton));
            }
            catch (Exception e) { Log("cruceta arriba: " + e.Message); }
        }

        /// <summary>Cada fotograma desde Frame, antes de los clics. Lo que pulsa aqui no hace lo de siempre.</summary>
        static void UiButtons(out bool startDone, out bool backDone)
        {
            UiScan();
            startDone = backDone = false;
            if (_uiPicker)
            {
                if (Pressed(B)) { AiPicker.PadCancel(); _bConsumed = true; }
                if (Pressed(Y)) { AiPicker.PadAll(); _yTaken = true; }
                if (Pressed(X)) { AiPicker.PadFree(); _xTaken = true; }
                if (Pressed(START)) startDone = true;               // nada que hacer aqui
                if (Pressed(BACK)) backDone = true;
            }
            else if (_uiError)
            {
                // aviso del juego (el anfitrion ha cambiado, errores): B o Start lo cierran
                bool b = Pressed(B), st = Pressed(START);
                if (b || st)
                {
                    try { ErrorMessageManager.Instance.ClickCloseButton(); } catch (Exception e) { Warn("aviso: " + e.Message); }
                    if (b) _bConsumed = true;
                    if (st) startDone = true;
                    _uiNext = 0;
                }
                if (Pressed(BACK)) backDone = true;
            }
            else
            {
                if (Pressed(B) && (Press(_uiB) || TalkSkip.Close() || PressRect(_uiTalkClose))) _bConsumed = true;
                if (_home != null)
                {
                    // inicio: se llama al menu directamente (los rombos solo aceptan el clic con el cursor un rato encima)
                    if (Pressed(START)) startDone = HomeMenu("Home_221B00_mgame_chess");
                    if (Pressed(BACK)) backDone = HomeMenu("Home_221B00_m_info_paper");
                }
                else
                {
                    if (Pressed(START)) startDone = Press(_uiStart);
                    if (Pressed(BACK)) backDone = Press(_uiBack);
                }
                if (Pressed(LB) && Press(_uiTabPrev)) _uiNext = 0;
                if (Pressed(RB) && Press(_uiTabNext)) _uiNext = 0;
                if (Pressed(DLEFT) && Press(_uiLB)) _arrowHeld = true;
                if (Pressed(DRIGHT) && Press(_uiRB)) _arrowHeld = true;
                // en la partida, sin nada encima: la cruceta va de un personaje a otro (derecha A -> F, izquierda F -> A)
                if (_inGame && !_uiRoom && _uiLB == null && _uiRB == null && (Pressed(DLEFT) || Pressed(DRIGHT)))
                {
                    _arrowHeld = true;
                    try { CyclePawn(Pressed(DRIGHT) ? 1 : -1); } catch (Exception e) { Warn("elegir personaje: " + e.Message); }
                }
                if (Pressed(Y) && Press(_uiY)) _yTaken = true;
                else if (_uiRoom && Pressed(Y) && _kickCount > 0)
                {
                    _kickFocus = (_kickFocus + 1) % _kickCount;
                    _yTaken = true;
                    _uiNext = 0;                                             // que el icono cambie de fila ya
                }
                if (_uiRoom && Pressed(DDOWN) && _uiDown != null)
                {
                    _arrowHeld = true;
                    _minusUntil = Time.unscaledTime + 4f;                    // quita los huecos vacios uno tras otro
                    _minusNext = 0;
                }
                if (Time.unscaledTime < _minusUntil)
                {
                    if (!_uiRoom || _uiDown == null) { if (_uiRoom) _minusUntil = 0; }
                    else if (Time.unscaledTime >= _minusNext && Press(_uiDown)) { _minusNext = Time.unscaledTime + 0.45f; _uiNext = 0; }
                }
            }
            if (Pressed(DUP))
            {
                if (Press(_uiGear)) _gearHeld = true;
                else if (_inGame) GearMiss();
            }
            StampClose();
            try { OverlayFrame(); } catch { }
            if (!Held(DUP)) _gearHeld = false;
            if (!Held(DLEFT) && !Held(DRIGHT) && !Held(DDOWN)) _arrowHeld = false;
            if (!Held(X)) _xTaken = false;
            if (!Held(Y)) _yTaken = false;
        }

        /// <summary>Para el gestor de controles del juego: lo que ya ha usado el mando aqui no cuenta como su tecla.</summary>
        static bool Taken(string id) =>
            (_gearHeld && id == "UpArrow") || (_xTaken && id == "PingStampMenu") || (_yTaken && id == "ViewHint") ||
            (id == "Cancel" && (!_inGame || _bConsumed)) ||
            (_arrowHeld && (id == "LeftArrow" || id == "RightArrow" || id == "DownArrow"));

        // ------------------------------------------------------------ iconos en los botones
        // Botones con texto: el icono va delante del texto (asi no tapa nada y se ve con el tamano de la letra).
        // La rueda (sin texto): un icono pequeno a su izquierda.
        static readonly Dictionary<int, (TMP_Text tmp, string tag)> _tagged = new();   // por texto
        static GameObject _gearHint;

        static void Labels()
        {
            var want = new Dictionary<int, (TMP_Text tmp, string btn)>();
            var noText = new Dictionary<int, (Button b, string btn)>();
            var faded = new HashSet<int>();
            if (Active)
            {
                void Add(Button b, string btn)
                {
                    if (b == null || !Shown(b)) return;
                    TMP_Text t = _labelFor.TryGetValue(b.GetInstanceID(), out var lf) && lf != null ? lf : Label(b);
                    if (t != null) want[t.GetInstanceID()] = (t, btn);
                    else noText[b.GetInstanceID()] = (b, btn);                   // sin texto: icono pequeno al lado
                }
                Add(_uiB, "b"); Add(_uiStart, "start"); Add(_uiBack, "back");
                foreach (var (b, btn) in _tagOnly) Add(b, btn);
                foreach (var (t, btn) in _tagText) if (t != null) want[t.GetInstanceID()] = (t, btn);
                // la sala detras de la ventana: sus iconos, mas claros (solo se ven; no hacen nada)
                if (_bgRoom)
                {
                    void AddBg(Button b, string btn)
                    {
                        if (b == null || !Visible(b)) return;
                        var t = Label(b);
                        if (t == null || want.ContainsKey(t.GetInstanceID())) return;
                        want[t.GetInstanceID()] = (t, btn);
                        faded.Add(t.GetInstanceID());
                    }
                    AddBg(_bgB, "b"); AddBg(_bgStart, "start"); AddBg(_bgBack, "back");
                }

            }
            var drop = new List<int>();
            foreach (var kv in _tagged)
                if (!want.ContainsKey(kv.Key)) { Untag(kv.Value.tmp, kv.Value.tag); drop.Add(kv.Key); }
            foreach (var id in drop) _tagged.Remove(id);
            foreach (var kv in want)
            {
                try
                {
                    var tmp = kv.Value.tmp;
                    string tag = faded.Contains(kv.Key) ? FadedTag(kv.Value.btn) : Tag(kv.Value.btn);
                    if (_tagged.TryGetValue(kv.Key, out var old) && old.tag != tag) Untag(old.tmp, old.tag);
                    if (KeyIcons != null && tmp.spriteAsset != KeyIcons) tmp.spriteAsset = KeyIcons;
                    var text = tmp.text ?? "";
                    if (!text.StartsWith(tag)) tmp.text = tag + text;       // el juego puede reescribir el texto: se vuelve a poner
                    _tagged[kv.Key] = (tmp, tag);
                }
                catch (Exception e) { Warn("iconos: " + e.Message); }
            }
            GearHint();
            try { ButtonHints(noText); } catch (Exception e) { Warn("iconos sueltos: " + e.Message); }
            try { PortraitHints(); } catch (Exception e) { Warn("iconos de los retratos: " + e.Message); }
            try { OverlaySync(); } catch (Exception e) { Warn("iconos 3D: " + e.Message); }
            try
            {
                TextMeshProUGUI et = null;
                if (_uiError && Active) et = ErrorMessageManager.Instance?.buttonText;
                if (_errTmp != null && et != _errTmp) { Untag(_errTmp, _errTag); _errTmp = null; }
                if (et != null)
                {
                    string tag = Tag("b");
                    if (_errTmp == et && _errTag != tag) Untag(et, _errTag);
                    if (KeyIcons != null && et.spriteAsset != KeyIcons) et.spriteAsset = KeyIcons;
                    if (!(et.text ?? "").StartsWith(tag)) et.text = tag + et.text;
                    _errTmp = et; _errTag = tag;
                }
            }
            catch (Exception e) { Warn("icono del aviso: " + e.Message); }
            try
            {
                bool room = Active && !_uiPicker;
                bool bg = Active && _bgRoom;                                 // la sala detras: mas claros
                SideHint(ref _kickHint, room && _uiLB != null ? _uiLB : bg ? _bgKick : null, _kickCount > 1 ? new[] { "y", "dpad_left" } : new[] { "dpad_left" }, bg && !(room && _uiLB != null));
                SideHint(ref _plusHint, room && _uiRB != null ? _uiRB : bg ? _bgPlus : null, new[] { "dpad_right" }, bg && !(room && _uiRB != null));
                SideHint(ref _downHint, room && _uiDown != null ? _uiDown : bg ? _bgMinus : null, new[] { "dpad_down" }, bg && !(room && _uiDown != null));
                SideHint(ref _yHint, room ? _uiY : null, new[] { "y" });
            }
            catch (Exception e) { Warn("iconos de expulsar/anadir: " + e.Message); }
        }

        static GameObject _kickHint, _plusHint, _downHint, _yHint;
        static readonly Dictionary<int, (GameObject go, string btn)> _btnHints = new();

        // Debajo de los retratos A-F: la cruceta derecha bajo el personaje al que se pasaria con ella y la izquierda bajo
        // el de la izquierda (sin nadie elegido: derecha bajo el primero, izquierda bajo el ultimo).
        static GameObject _portraitL, _portraitR;
        static bool _portraitLogged;

        static void PortraitHints()
        {
            bool show = Active && _pawnPanel != null && _pawnPanel.activeInHierarchy;
            List<RectTransform> cards = null;
            int next = -1, prev = -1;
            if (show)
            {
                cards = Portraits();
                next = NextPawn(1); prev = NextPawn(-1);
                show = cards.Count > 0 && next >= 0 && next < cards.Count && prev >= 0 && prev < cards.Count;
                if (!_portraitLogged && cards.Count > 0)
                {
                    _portraitLogged = true;
                    Log($"retratos: {cards.Count} en {_pawnPanel.name} ({string.Join(", ", cards.ConvertAll(c => c.gameObject.name))})");
                }
            }
            if (show)
            {
                if (_portraitL == null) _portraitL = PortraitIcon("dpad_left");
                if (_portraitR == null) _portraitR = PortraitIcon("dpad_right");
                Place(_portraitL, cards[prev]);
                Place(_portraitR, cards[next]);
            }
            if (_portraitL != null && _portraitL.activeSelf != show) _portraitL.SetActive(show);
            if (_portraitR != null && _portraitR.activeSelf != show) _portraitR.SetActive(show);
        }

        static void Place(GameObject icon, RectTransform card)
        {
            if (icon == null || card == null) return;
            if (icon.transform.parent != card) icon.transform.SetParent(card, false);
            var rt = icon.GetComponent<RectTransform>();
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0f);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.anchoredPosition = new Vector2(0f, -4f);
        }

        /// <summary>Los retratos de la fila, de izquierda a derecha (uno por personaje).</summary>
        static List<RectTransform> Portraits()
        {
            var list = new List<RectTransform>();
            var root = _pawnPanel.transform;
            for (int i = 0; i < root.childCount; i++)
            {
                var c = root.GetChild(i);
                if (c == null || !c.gameObject.activeInHierarchy) continue;
                var rt = c.GetComponent<RectTransform>();
                if (rt != null && rt.rect.width > 0) list.Add(rt);
            }
            // si la fila tiene una sola pieza que lo agrupa todo, se mira dentro
            if (list.Count == 1 && list[0].childCount > 1) { var only = list[0]; list.Clear(); for (int i = 0; i < only.childCount; i++) { var c = only.GetChild(i); var rt = c != null ? c.GetComponent<RectTransform>() : null; if (rt != null && c.gameObject.activeInHierarchy && rt.rect.width > 0) list.Add(rt); } }
            list.Sort((a, b) => a.position.x.CompareTo(b.position.x));
            return list;
        }

        /// <summary>El personaje al que se pasaria con la cruceta (1 derecha, -1 izquierda), o -1.</summary>
        static int NextPawn(int dir)
        {
            try
            {
                var gm = GameManager.instance;
                var pc = gm != null ? gm.pawnController : null;
                if (pc == null) return -1;
                int n = gm.GetPawnCount();
                if (n <= 0) return -1;
                var cur = pc.GetSelectPawn();
                int ci = -1;
                for (int i = 0; i < n && cur != null; i++)
                {
                    int k = i;
                    var p = gm.GetPawn(ref k);
                    if (p != null && p.Pointer == cur.Pointer) { ci = i; break; }
                }
                int start = ci >= 0 ? ci : (dir > 0 ? -1 : n);
                for (int step = 1; step <= n; step++)
                {
                    int i = ((start + dir * step) % n + n) % n;
                    var p = gm.GetPawn(ref i);
                    if (p != null && p.gameObject.activeInHierarchy) return i;
                }
            }
            catch { }
            return -1;
        }

        static GameObject PortraitIcon(string btn)
        {
            EnsureIcons();
            var go = new GameObject("CSR_PadHint:" + btn);
            go.layer = _pawnPanel.layer;
            var rt = go.AddComponent<RectTransform>();
            rt.SetParent(_pawnPanel.transform, false);
            const float size = 26f;
            rt.sizeDelta = new Vector2(size, size);
            var tmp = go.AddComponent<TextMeshProUGUI>();
            var any = Find<TextMeshProUGUI>();
            if (any != null) tmp.font = any.font;
            if (KeyIcons != null) tmp.spriteAsset = KeyIcons;
            tmp.text = $"<sprite name=\"csr_{btn}\">";
            tmp.fontSize = size;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.enableWordWrapping = false;
            tmp.raycastTarget = false;
            return go;
        }

        /// <summary>Botones sin texto (flechas de pagina, pestanas con dibujo...): su icono va a un lado.</summary>
        static void ButtonHints(Dictionary<int, (Button b, string btn)> want)
        {
            var drop = new List<int>();
            foreach (var kv in _btnHints)
                if (!want.TryGetValue(kv.Key, out var w) || w.btn != kv.Value.btn || kv.Value.go == null)
                {
                    try { if (kv.Value.go != null) UnityEngine.Object.Destroy(kv.Value.go); } catch { }
                    drop.Add(kv.Key);
                }
            foreach (var id in drop) _btnHints.Remove(id);
            foreach (var kv in want)
                if (!_btnHints.ContainsKey(kv.Key))
                {
                    var go = MakeIcon(kv.Value.b, new[] { kv.Value.btn }, _hintAbove.Contains(kv.Key));
                    if (go != null) _btnHints[kv.Key] = (go, kv.Value.btn);
                }
        }

        // Textos 3D de la escena (los rombos "Jugar" y "Perfil" del inicio): su icono va en un lienzo propio, por
        // encima de todo, a la izquierda del texto; se recoloca cada fotograma porque la camara se mueve.
        static GameObject _overlay;
        static readonly List<(TMP_Text t, string btn, TextMeshProUGUI icon)> _ovl = new();

        static void OverlaySync()
        {
            var want = Active ? _tag3d : new List<(TMP_Text tmp, string btn)>();
            bool same = want.Count == _ovl.Count;
            for (int i = 0; same && i < want.Count; i++)
                same = _ovl[i].t == want[i].tmp && _ovl[i].btn == want[i].btn && _ovl[i].icon != null && _ovl[i].icon.text == "<sprite name=\"csr_" + SpriteName(want[i].btn) + "\">";
            if (same) return;
            foreach (var o in _ovl) if (o.icon != null) UnityEngine.Object.Destroy(o.icon.gameObject);
            _ovl.Clear();
            if (want.Count == 0) return;
            EnsureIcons();
            if (_overlay == null)
            {
                _overlay = new GameObject("CSR_PadOverlay");
                UnityEngine.Object.DontDestroyOnLoad(_overlay);
                var cv = _overlay.AddComponent<Canvas>();
                cv.renderMode = RenderMode.ScreenSpaceOverlay;
                cv.sortingOrder = 32000;
            }
            var any = Find<TextMeshProUGUI>();
            foreach (var (t, btn) in want)
            {
                var go = new GameObject("CSR_PadOverlayIcon");
                var rt = go.AddComponent<RectTransform>();
                rt.SetParent(_overlay.transform, false);
                rt.anchorMin = rt.anchorMax = Vector2.zero;
                rt.pivot = new Vector2(1f, 0.5f);
                var tmp = go.AddComponent<TextMeshProUGUI>();
                if (any != null) tmp.font = any.font;
                if (KeyIcons != null) tmp.spriteAsset = KeyIcons;
                tmp.text = "<sprite name=\"csr_" + SpriteName(btn) + "\">";
                tmp.alignment = TextAlignmentOptions.Right;
                tmp.enableWordWrapping = false;
                tmp.raycastTarget = false;
                _ovl.Add((t, btn, tmp));
            }
            Log($"inicio: {_ovl.Count} iconos sobre los rombos 3D");
            OverlayFrame();
        }

        /// <summary>Cada fotograma: cada icono a la izquierda de su texto 3D, del alto de la letra.</summary>
        static void OverlayFrame()
        {
            if (_ovl.Count == 0) return;
            foreach (var (t, btn, icon) in _ovl)
            {
                if (icon == null) continue;
                bool ok = false;
                if (t != null && t.gameObject.activeInHierarchy && Active)
                {
                    var cam = CameraFor(t.gameObject);
                    var rend = t.GetComponent<Renderer>();
                    if (cam != null && rend != null)
                    {
                        // las 8 esquinas de lo que ocupa el texto, en la pantalla
                        var bb = rend.bounds;
                        float minX = float.MaxValue, minY = float.MaxValue, maxY = float.MinValue;
                        bool front = true;
                        for (int i = 0; i < 8; i++)
                        {
                            var c = new Vector3((i & 1) == 0 ? bb.min.x : bb.max.x, (i & 2) == 0 ? bb.min.y : bb.max.y, (i & 4) == 0 ? bb.min.z : bb.max.z);
                            var sp = cam.WorldToScreenPoint(c);
                            if (sp.z <= 0) front = false;
                            minX = Math.Min(minX, sp.x); minY = Math.Min(minY, sp.y); maxY = Math.Max(maxY, sp.y);
                        }
                        ok = front && bb.size.sqrMagnitude > 0;
                        if (ok)
                        {
                            float size = Math.Clamp((maxY - minY) * 1.1f, 18f, 56f);
                            icon.fontSize = size;
                            var rt = icon.rectTransform;
                            rt.sizeDelta = new Vector2(size * 1.2f, size * 1.2f);
                            rt.anchoredPosition = new Vector2(minX - size * 0.15f, (minY + maxY) / 2f);
                        }
                        if (!_ovlLogged) { _ovlLogged = true; Log($"inicio: icono 3D con la camara {cam.name} en ({minX:0},{(minY + maxY) / 2f:0})"); }
                    }
                    else if (!_ovlLogged) { _ovlLogged = true; Log($"inicio: sin camara ({cam != null}) o sin dibujo ({rend != null}) para {t.name}"); }
                }
                if (icon.gameObject.activeSelf != ok) icon.gameObject.SetActive(ok);
            }
        }

        static bool _ovlLogged;
        static string _homeLogKey;

        /// <summary>La camara que dibuja un objeto de la escena: la principal si lo ve, si no la de mas encima que lo vea.</summary>
        static Camera CameraFor(GameObject go)
        {
            int bit = 1 << go.layer;
            var main = Camera.main;
            if (main != null && main.isActiveAndEnabled && (main.cullingMask & bit) != 0) return main;
            Camera best = null;
            foreach (var c in Camera.allCameras)
                if (c != null && c.isActiveAndEnabled && (c.cullingMask & bit) != 0 && (best == null || c.depth > best.depth)) best = c;
            return best ?? main;
        }

        static string SpriteName(string btn) => btn.StartsWith("dpad") || btn.EndsWith("stick") ? btn : _style + "_" + btn;
        static TextMeshProUGUI _errTmp;
        static string _errTag;

        /// <summary>Un icono pequeno a la izquierda de un boton sin texto (se mueve al boton que toque en cada momento).</summary>
        static void SideHint(ref GameObject hint, Button b, string[] icons, bool faded = false)
        {
            if (b == null || (faded ? !Visible(b) : !Shown(b))) { if (hint != null && hint.activeSelf) hint.SetActive(false); return; }
            string key = string.Join(",", icons);
            if (hint == null || hint.transform.parent != b.transform || hint.name != "CSR_PadHint:" + key)
            {
                if (hint != null) UnityEngine.Object.Destroy(hint);
                hint = MakeIcon(b, icons, false);
                if (hint != null) hint.name = "CSR_PadHint:" + key;
            }
            if (hint != null && !hint.activeSelf) hint.SetActive(true);
            Fade(hint, faded);
        }

        static TextMeshProUGUI Label(Button b)
        {
            TextMeshProUGUI best = null;
            foreach (var t in b.GetComponentsInChildren<TextMeshProUGUI>(true))
                if (t != null && !t.gameObject.name.StartsWith("CSR_PadHint") && (best == null || t.fontSize > best.fontSize)) best = t;
            return best;
        }

        static void Untag(TMP_Text tmp, string tag)
        {
            try { if (tmp != null && tmp.text != null && tmp.text.StartsWith(tag)) tmp.text = tmp.text.Substring(tag.Length); } catch { }
        }

        static void GearHint()
        {
            bool show = Active && _uiGear != null;
            try
            {
                if (show && (_gearHint == null || _gearHint.transform.parent != _uiGear.transform || _gearHintGame != _gearInGame))
                {
                    if (_gearHint != null) UnityEngine.Object.Destroy(_gearHint);
                    _gearHint = MakeIcon(_uiGear, new[] { "dpad_up" }, false, _gearInGame ? 0.62f : 1f);   // en la caja de la partida, mas pequeno
                    _gearHintGame = _gearInGame;
                }
                if (_gearHint != null && _gearHint.activeSelf != show) _gearHint.SetActive(show);
            }
            catch (Exception e) { Warn("icono de la rueda: " + e.Message); }
            try { ManualGap(show && !_gearInGame ? _uiGear : null); } catch (Exception e) { Warn("manual online: " + e.Message); }
            try { BoxGap(show && _gearInGame ? _uiGear : null); } catch (Exception e) { Warn("caja de la llave: " + e.Message); }
        }

        static bool _gearHintGame;

        // La llave de la partida esta al final de una caja (jugadores, reloj): mientras se ve el icono de la cruceta,
        // el resto de la caja se corre a la izquierda para dejarle hueco y el fondo se alarga por la izquierda.
        // Se miden las piezas antes de tocar nada y se colocan de fuera hacia dentro, asi da igual como esten
        // ancladas (si al mover el fondo se mueve algo de dentro, se corrige). Al volver al raton, todo a su sitio.
        static readonly Dictionary<int, (RectTransform rt, Vector2 min0, Vector2 max0, Vector2 min1, Vector2 max1)> _box = new();
        static bool _boxLogged, _boxOkLogged;
        static float _boxRetry;

        static void BoxGap(Button gear)
        {
            if (_box.Count > 0)
            {
                bool intact = true;
                foreach (var kv in _box)
                {
                    var v = kv.Value;
                    if (v.rt == null || v.rt.offsetMin != v.min1 || v.rt.offsetMax != v.max1) { intact = false; break; }
                }
                if (gear != null && _gearHint != null && intact) return;     // ya esta hecho
                if (intact)
                    foreach (var kv in _box) { kv.Value.rt.offsetMin = kv.Value.min0; kv.Value.rt.offsetMax = kv.Value.max0; }
                _box.Clear();                                                // si el juego lo ha recolocado, se rehace
            }
            if (gear == null || _gearHint == null || Time.unscaledTime < _boxRetry) return;
            _boxRetry = Time.unscaledTime + 1f;                              // buscar es caro: como mucho una vez por segundo

            var grt = gear.GetComponent<RectTransform>();
            var hrt = _gearHint.GetComponent<RectTransform>();
            if (grt == null || hrt == null) return;
            Rect W = ScreenRect(grt), H = ScreenRect(hrt);
            if (W.width <= 0 || H.width <= 0)
            {
                if (!_boxLogged) { _boxLogged = true; Log($"llave: no puedo medirla ({W} / {H})"); }
                return;
            }
            float d = H.width + W.width * 0.12f;
            var wrenchT = gear.transform;

            // piezas: lo que este en la franja de la llave, a su izquierda y cerca (no la llave ni lo que lleva dentro).
            // Se busca en todo lo que cuelga de la interfaz de la partida (puede haber varios lienzos) y se mide en
            // pixeles de pantalla, que es lo comun a todos.
            // todos los lienzos que se ven (la caja puede estar en otro distinto del de la llave)
            var roots = new List<Transform>();
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<Canvas>()))
            {
                var c = o?.TryCast<Canvas>();
                if (c != null && c.isRootCanvas && c.enabled && c.gameObject.activeInHierarchy) roots.Add(c.transform);
            }
            var close = new List<(float dist, string what)>();
            var near = new List<(RectTransform rt, Rect R, bool span)>();
            var seen = new HashSet<int>();
            Transform row = null;                                            // retratos A-F: se mueven juntos (no pieza a pieza)
            try { var hd = GetHud(); if (hd != null && hd.pawnsPanelSum != null && hd.pawnsPanelSum.activeInHierarchy) row = hd.pawnsPanelSum.transform; } catch { }
            float boxLeft = W.xMin - W.width * 5f;                          // sin fondo: hasta 5 llaves a la izquierda
            float widest = 0;
            foreach (var root in roots)
                foreach (var rt in root.GetComponentsInChildren<RectTransform>(false))
                {
                    if (rt == null || rt.IsChildOf(wrenchT) || wrenchT.IsChildOf(rt) || !seen.Add(rt.GetInstanceID())) continue;
                    if (row != null && (rt.IsChildOf(row) || row.IsChildOf(rt))) continue;
                    var R = ScreenRect(rt);
                    if (R.width > 0 && R.width < W.width * 12f)
                    {
                        float dist = Vector2.Distance(R.center, W.center);
                        if (dist < W.width * 6f) close.Add((dist, $"{rt.gameObject.name}@{R.center.x - W.center.x:0},{R.center.y - W.center.y:0} {R.width:0}x{R.height:0}"));
                    }
                    if (R.width < W.width * 0.05f || R.width > W.width * 9f || R.height > W.height * 2.5f) continue;
                    if (R.center.y < W.yMin || R.center.y > W.yMax) continue;
                    if (R.xMin < W.xMin - W.width * 9f || R.xMin >= W.xMin) continue;
                    bool span = R.xMax > W.xMin + W.width * 0.2f;
                    near.Add((rt, R, span));
                    if (span && R.width > widest) { widest = R.width; boxLeft = R.xMin; }   // el fondo de la caja
                }
            var targets = new List<(RectTransform rt, float x0, float x1, int depth)>();
            var names = new List<string>();
            foreach (var n in near)
            {
                if (n.R.xMin < boxLeft - W.width * 0.3f) continue;               // fuera de la caja (retratos A-F...)
                targets.Add((n.rt, n.R.xMin - d, n.span ? n.R.xMax : n.R.xMax - d, Depth(n.rt)));
                if (names.Count < 16) names.Add(n.rt.gameObject.name + (n.span ? "*" : ""));
            }
            if (targets.Count == 0)
            {
                if (!_boxLogged)
                {
                    _boxLogged = true;
                    close.Sort((a, b) => a.dist.CompareTo(b.dist));
                    var sb = new List<string>();
                    for (int i = 0; i < close.Count && i < 25; i++) sb.Add(close[i].what);
                    Log($"llave: no encuentro la caja (llave {W}, {roots.Count} lienzos, {near.Count} piezas). Cerca: " + string.Join(" | ", sb));
                }
                _boxRetry = Time.unscaledTime + 3f;
                return;
            }
            {
                targets.Add((grt, W.xMin, W.xMax, Depth(grt)));          // la llave se queda donde esta
            }
            if (row != null)
            {
                // la fila de retratos se aparta lo mismo, para que la caja (que se alarga) no la pise
                var rrt = row.GetComponent<RectTransform>();
                if (rrt != null)
                {
                    var RR = ScreenRect(rrt);
                    targets.Add((rrt, RR.xMin - d, RR.xMax - d, Depth(rrt)));
                    names.Add(row.name + " (retratos)");
                }
            }
            targets.Sort((a, b) => a.depth.CompareTo(b.depth));
            foreach (var t in targets)
            {
                var R = ScreenRect(t.rt);
                float dl = t.x0 - R.xMin, dr = t.x1 - R.xMax;
                if (Math.Abs(dl) < W.width * 0.005f && Math.Abs(dr) < W.width * 0.005f) continue;
                if (R.width <= 0) continue;
                float k = t.rt.rect.width * t.rt.localScale.x / R.width;        // pixeles de pantalla -> unidades del padre
                var min0 = t.rt.offsetMin; var max0 = t.rt.offsetMax;
                int id = t.rt.GetInstanceID();
                if (_box.TryGetValue(id, out var prev)) { min0 = prev.min0; max0 = prev.max0; }
                t.rt.offsetMin = t.rt.offsetMin + new Vector2(dl * k, 0f);
                t.rt.offsetMax = t.rt.offsetMax + new Vector2(dr * k, 0f);
                _box[id] = (t.rt, min0, max0, t.rt.offsetMin, t.rt.offsetMax);
            }
            if (!_boxOkLogged) { _boxOkLogged = true; Log("llave: aparto " + string.Join(", ", names)); }
        }

        /// <summary>El rectangulo de una pieza en pixeles de pantalla (cada lienzo con su camara).</summary>
        static Rect ScreenRect(RectTransform rt)
        {
            var c = Corners(rt);
            Camera cam = null;
            var canvas = rt.GetComponentInParent<Canvas>();
            if (canvas != null)
            {
                canvas = canvas.rootCanvas;
                if (canvas.renderMode != RenderMode.ScreenSpaceOverlay) cam = canvas.worldCamera != null ? canvas.worldCamera : Camera.main;
            }
            Vector2 a = RectTransformUtility.WorldToScreenPoint(cam, c[0]), b = RectTransformUtility.WorldToScreenPoint(cam, c[2]);
            return Rect.MinMaxRect(Math.Min(a.x, b.x), Math.Min(a.y, b.y), Math.Max(a.x, b.x), Math.Max(a.y, b.y));
        }

        /// <summary>Las 4 esquinas en el mundo (como GetWorldCorners, que aqui no devuelve nada: el plugin le pasa
        /// una copia del array y el juego escribe en la copia).</summary>
        static Vector3[] Corners(RectTransform rt)
        {
            var r = rt.rect;
            return new[]
            {
                rt.TransformPoint(new Vector3(r.xMin, r.yMin, 0f)), rt.TransformPoint(new Vector3(r.xMin, r.yMax, 0f)),
                rt.TransformPoint(new Vector3(r.xMax, r.yMax, 0f)), rt.TransformPoint(new Vector3(r.xMax, r.yMin, 0f)),
            };
        }

        static int Depth(Transform t) { int n = 0; for (; t != null; t = t.parent) n++; return n; }

        // "Manual online" esta pegado a la rueda: mientras se ve el icono de la cruceta, se aparta a la izquierda.
        // Se mueve su pivote (no su posicion, que el juego recoloca y hacia que se fuera yendo poco a poco a la
        // izquierda): el boton se dibuja desplazado y el juego puede seguir poniendo la posicion que quiera.
        static readonly Dictionary<int, (RectTransform rt, Vector2 pivot0)> _moved = new();

        static void ManualGap(Button gear)
        {
            var keep = new HashSet<int>();
            if (gear != null && _gearHint != null)
            {
                var grt = gear.GetComponent<RectTransform>();
                var hrt = _gearHint.GetComponent<RectTransform>();
                Vector3[] gc = Corners(grt), hc = Corners(hrt);
                float gw = gc[2].x - gc[0].x, gh = gc[2].y - gc[0].y;
                float dx = (hc[2].x - hc[0].x) + gw * 0.25f;               // el ancho del icono y un poco de aire
                float gy = (gc[0].y + gc[2].y) * 0.5f;
                foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<OnlineManualButton>()))
                {
                    var m = o?.TryCast<OnlineManualButton>();
                    if (m == null || !m.gameObject.activeInHierarchy) continue;
                    var mrt = m.GetComponent<RectTransform>();
                    if (mrt == null || mrt.rect.width <= 0) continue;
                    int id = m.GetInstanceID();
                    Vector2 pivot0 = _moved.TryGetValue(id, out var prev) ? prev.pivot0 : mrt.pivot;
                    // donde estaria sin apartar (se mide quitando lo que ya se movio)
                    var mc = Corners(mrt);
                    float shiftNow = (mrt.pivot.x - pivot0.x) * mrt.rect.width * mrt.lossyScale.x;
                    float right = mc[2].x + shiftNow, my = (mc[0].y + mc[2].y) * 0.5f;
                    bool beside = Math.Abs(my - gy) < gh && right <= gc[0].x + gw * 0.5f && right > gc[0].x - gw * 3f;
                    if (!beside) continue;
                    keep.Add(id);
                    float sx = mrt.lossyScale.x;
                    if (Math.Abs(sx) < 1e-6f) continue;
                    var want = new Vector2(pivot0.x + dx / sx / mrt.rect.width, pivot0.y);
                    if ((mrt.pivot - want).sqrMagnitude > 1e-8f) mrt.pivot = want;
                    _moved[id] = (mrt, pivot0);
                }
            }
            var gone = new List<int>();
            foreach (var kv in _moved)
            {
                if (keep.Contains(kv.Key)) continue;
                gone.Add(kv.Key);
                try { if (kv.Value.rt != null) kv.Value.rt.pivot = kv.Value.pivot0; } catch { }
            }
            foreach (var id in gone) _moved.Remove(id);
        }

        /// <summary>Un icono suelto junto a un boton sin texto: a su izquierda, o encima (en la partida, donde a la
        /// izquierda esta el reloj).</summary>
        static GameObject MakeIcon(Button b, string[] btns, bool above, float scale = 1f)
        {
            EnsureIcons();
            var brt = b.GetComponent<RectTransform>();
            if (brt == null) return null;
            var go = new GameObject("CSR_PadHint");
            go.layer = b.gameObject.layer;
            var rt = go.AddComponent<RectTransform>();
            rt.SetParent(brt, false);
            float size = Math.Clamp(brt.rect.height * 0.5f, 22f, 34f) * scale;
            if (above)
            {
                rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 1f);
                rt.pivot = new Vector2(0.5f, 0f);
                rt.anchoredPosition = new Vector2(0f, 2f);
            }
            else
            {
                rt.anchorMin = rt.anchorMax = new Vector2(0f, 0.5f);
                rt.pivot = new Vector2(1f, 0.5f);
                rt.anchoredPosition = new Vector2(-4f, 0f);
            }
            rt.sizeDelta = new Vector2(size * btns.Length + 4f * (btns.Length - 1), size);
            var tmp = go.AddComponent<TextMeshProUGUI>();
            var any = Find<TextMeshProUGUI>();
            if (any != null) tmp.font = any.font;
            if (KeyIcons != null) tmp.spriteAsset = KeyIcons;
            var sb = new System.Text.StringBuilder();
            foreach (var btn in btns)
            {
                string n = btn.StartsWith("dpad") || btn.EndsWith("stick") ? btn : _style + "_" + btn;
                sb.Append($"<sprite name=\"csr_{n}\">");
            }
            tmp.text = sb.ToString();
            tmp.fontSize = size;
            tmp.alignment = above ? TextAlignmentOptions.Center : TextAlignmentOptions.Right;
            tmp.enableWordWrapping = false;
            tmp.raycastTarget = false;
            return go;
        }

        static void HideHints()
        {
            foreach (var kv in _tagged) Untag(kv.Value.tmp, kv.Value.tag);
            _tagged.Clear();
            try { if (_gearHint != null) _gearHint.SetActive(false); } catch { }
            try { ManualGap(null); } catch { }
            try { BoxGap(null); } catch { }
            try { if (_kickHint != null) _kickHint.SetActive(false); if (_plusHint != null) _plusHint.SetActive(false); if (_downHint != null) _downHint.SetActive(false); if (_yHint != null) _yHint.SetActive(false); } catch { }
            _uiTalkClose = null;
            _tagText.Clear();
            _tag3d.Clear();
            try { OverlaySync(); } catch { }
            try { ButtonHints(new Dictionary<int, (Button b, string btn)>()); } catch { }
            try { if (_portraitL != null) _portraitL.SetActive(false); if (_portraitR != null) _portraitR.SetActive(false); } catch { }
            _uiB = _uiStart = _uiBack = _uiGear = _uiLB = _uiRB = null;
            _uiPicker = false;
        }
    }
}
