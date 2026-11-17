// CRIMESIGHT Revival - controles con mando.
//
// El juego solo se maneja con raton y teclado. Su gestor de controles (KeySettingManager) ya tiene
// funciones para mando, pero vacias. Aqui:
//   - Se lee el mando con XInput. Steam presenta como mando de Xbox los de PlayStation, Switch y la propia
//     Steam Deck, asi que vale para todos (tambien en Linux con Proton).
//   - El stick izquierdo mueve el cursor de verdad y A / B hacen clic izquierdo / derecho: asi funcionan
//     todos los menus y botones del juego sin tocarlos.
//   - La camara, el menu de indicadores, ver sospechosos y las flechas se le dan al gestor de controles del
//     juego como si fueran sus propias teclas (KeySettingManager.IsDown/IsUp/IsStatus/GetScroll).
//   - Start pulsa "Finalizar turno" (u "Omitir accion") y Back abre o cierra el registro.
//
//   Stick izq.: cursor (L3 pulsado: lento)   A: clic        B: clic derecho
//   Stick der.: mover la camara              LB / RB: girar la camara   LT / RT: alejar / acercar
//   X: indicadores y stickers                Y: ver sospechosos         Cruceta: flechas
//   Start: Finalizar turno / Omitir accion   Back: Registro
//
// Vibracion: un toque al elegir un personaje y otro al confirmarle una orden; un latido cuando dos
// personajes se quedan a solas con un arma (escena de comprobacion del asesinato) hasta que empieza el
// dialogo, o, si es una ejecucion, hasta el golpe, que vibra fuerte; y una vibracion normal cuando
// Sherlock aparece para hacer su deduccion. Los momentos se detectan por los sonidos que lanza el juego.
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using HarmonyLib;
using Il2CppInterop.Runtime;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class Pad
    {
        // ------------------------------------------------------------ XInput
        [StructLayout(LayoutKind.Sequential)]
        struct XState { public uint packet; public ushort buttons; public byte lt, rt; public short lx, ly, rx, ry; }

        delegate uint GetStateFn(uint user, out XState state);
        static GetStateFn _get;
        static bool _noXInput;

        [DllImport("xinput1_4.dll", EntryPoint = "XInputGetState")] static extern uint Get14(uint u, out XState s);
        [DllImport("xinput1_3.dll", EntryPoint = "XInputGetState")] static extern uint Get13(uint u, out XState s);
        [DllImport("xinput9_1_0.dll", EntryPoint = "XInputGetState")] static extern uint Get910(uint u, out XState s);

        [StructLayout(LayoutKind.Sequential)]
        struct XVibration { public ushort left, right; }      // izquierdo: grave (golpe); derecho: agudo (toque)
        delegate uint SetStateFn(uint user, ref XVibration v);
        static SetStateFn _set;
        [DllImport("xinput1_4.dll", EntryPoint = "XInputSetState")] static extern uint Set14(uint u, ref XVibration v);
        [DllImport("xinput1_3.dll", EntryPoint = "XInputSetState")] static extern uint Set13(uint u, ref XVibration v);
        [DllImport("xinput9_1_0.dll", EntryPoint = "XInputSetState")] static extern uint Set910(uint u, ref XVibration v);

        const ushort DUP = 0x0001, DDOWN = 0x0002, DLEFT = 0x0004, DRIGHT = 0x0008, START = 0x0010, BACK = 0x0020,
                     L3 = 0x0040, R3 = 0x0080, LB = 0x0100, RB = 0x0200, A = 0x1000, B = 0x2000, X = 0x4000, Y = 0x8000;

        // ------------------------------------------------------------ raton y teclado del sistema
        [StructLayout(LayoutKind.Sequential)]
        struct MouseInput { public int dx, dy; public uint data, flags, time; public IntPtr extra; }
        [StructLayout(LayoutKind.Explicit, Size = 40)]
        struct Input { [FieldOffset(0)] public uint type; [FieldOffset(8)] public MouseInput mi; }
        [DllImport("user32.dll")] static extern uint SendInput(uint n, Input[] inputs, int size);

        const uint MOVE = 0x0001, LDOWN = 0x0002, LUP = 0x0004, RDOWN = 0x0008, RUP = 0x0010;

        static void Mouse(uint flags, int dx = 0, int dy = 0)
        {
            var i = new Input[1];
            i[0].type = 0;
            i[0].mi = new MouseInput { dx = dx, dy = dy, flags = flags };
            SendInput(1, i, Marshal.SizeOf<Input>());
        }

        // ------------------------------------------------------------ estado
        static ushort _now, _prev;
        static float _lx, _ly, _rx, _ry, _lt, _rt;
        static float _fx, _fy;                 // restos de pixel del cursor
        static int _rotDone;                   // pixeles movidos para girar (se devuelven al soltar)
        static bool _rotating, _connected, _announced;
        static readonly Dictionary<string, ushort> Buttons = new()
        {
            ["PingStampMenu"] = X, ["ViewHint"] = Y,
            ["UpArrow"] = DUP, ["DownArrow"] = DDOWN, ["LeftArrow"] = DLEFT, ["RightArrow"] = DRIGHT,
        };

        static void Log(string s) => Plugin.L.LogInfo("[Mando] " + s);

        public static void Init(Harmony h)
        {
            void Post(string method, string post)
            {
                try
                {
                    var m = AccessTools.DeclaredMethod(typeof(KeySettingManager), method);
                    if (m == null) { Log($"KeySettingManager.{method}: no existe"); return; }
                    h.Patch(m, postfix: new HarmonyMethod(typeof(Pad).GetMethod(post,
                        System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
                }
                catch (Exception e) { Plugin.L.LogWarning($"[Mando] {method}: {e.Message}"); }
            }
            Post("IsDown", nameof(AfterIsDown));
            Post("IsUp", nameof(AfterIsUp));
            Post("IsStatus", nameof(AfterIsStatus));
            Post("GetScroll", nameof(AfterGetScroll));
            PatchRumble(h);
        }

        static bool Read(out XState s)
        {
            s = default;
            if (_noXInput) return false;
            if (_get == null)
            {
                var gets = new GetStateFn[] { Get14, Get13, Get910 };
                var sets = new SetStateFn[] { Set14, Set13, Set910 };
                for (int i = 0; i < gets.Length && _get == null; i++)
                {
                    try { gets[i](0, out _); _get = gets[i]; _set = sets[i]; }
                    catch (DllNotFoundException) { }
                    catch (EntryPointNotFoundException) { }
                }
                if (_get == null) { _noXInput = true; Log("XInput no disponible: sin soporte de mando"); return false; }
            }
            // con el mando conectado se lee su ranura cada fotograma; sin mando se buscan las cuatro una vez
            // por segundo (preguntar por ranuras vacias es lento y daria tirones)
            if (_slot >= 0 && _get((uint)_slot, out s) == 0) return true;
            _slot = -1;
            if (Time.unscaledTime < _nextScan) return false;
            _nextScan = Time.unscaledTime + 1f;
            for (uint u = 0; u < 4; u++)
                if (_get(u, out s) == 0) { _slot = (int)u; return true; }
            return false;
        }
        static int _slot = -1;
        static float _nextScan;

        static float Stick(short v, float dead = 0.22f)
        {
            float f = Math.Max(-1f, v / 32767f);
            float a = Math.Abs(f);
            if (a < dead) return 0;
            return Math.Sign(f) * (a - dead) / (1 - dead);
        }

        static bool Held(ushort b) => (_now & b) != 0;
        static bool Pressed(ushort b) => (_now & b) != 0 && (_prev & b) == 0;
        static bool Released(ushort b) => (_now & b) == 0 && (_prev & b) != 0;

        // ------------------------------------------------------------ cada fotograma
        public static void Frame()
        {
            if (!Read(out var s))
            {
                if (_connected) { Release(); _connected = false; }
                return;
            }
            if (!_connected) { _connected = true; if (!_announced) { Log("mando conectado"); _announced = true; } }
            if (!Application.isFocused) { Release(); return; }

            _prev = _now;
            _now = s.buttons;
            _lx = Stick(s.lx); _ly = Stick(s.ly); _rx = Stick(s.rx); _ry = Stick(s.ry);
            _lt = s.lt > 30 ? (s.lt - 30) / 225f : 0; _rt = s.rt > 30 ? (s.rt - 30) / 225f : 0;
            float dt = Math.Min(Time.unscaledDeltaTime, 0.05f);

            // cursor: curva para poder apuntar fino y cruzar la pantalla rapido
            float speed = Screen.height * (Held(L3) ? 0.35f : 1.25f);
            _fx += Math.Sign(_lx) * _lx * _lx * speed * dt;
            _fy -= Math.Sign(_ly) * _ly * _ly * speed * dt;
            int mx = (int)_fx, my = (int)_fy;
            if (_rotating) { _fx = _fy = 0; }                      // mientras gira, el cursor es de la camara
            else if (mx != 0 || my != 0) { Mouse(MOVE, mx, my); _fx -= mx; _fy -= my; }

            if (Pressed(A)) Mouse(LDOWN);
            if (Released(A)) Mouse(LUP);
            if (Pressed(B)) Mouse(RDOWN);
            if (Released(B)) Mouse(RUP);

            // girar la camara: el juego gira mientras "CameraRotate" esta activo, segun lo que se mueva el cursor
            bool rot = Held(LB) ^ Held(RB);
            if (rot)
            {
                _rotating = true;
                int d = (int)Math.Round((Held(RB) ? 1 : -1) * Screen.height * 0.45f * dt);
                if (d != 0) { Mouse(MOVE, d, 0); _rotDone += d; }
            }
            else if (_rotating)
            {
                _rotating = false;
                if (_rotDone != 0) { Mouse(MOVE, -_rotDone, 0); _rotDone = 0; }   // el cursor vuelve a su sitio
            }

            if (Pressed(START)) TurnButton();
            if (Pressed(BACK)) ToggleLog();
            UpdateRumble();
        }

        static void Release()
        {
            StopRumble();
            if ((_now & A) != 0) Mouse(LUP);
            if ((_now & B) != 0) Mouse(RUP);
            if (_rotDone != 0) { Mouse(MOVE, -_rotDone, 0); _rotDone = 0; }
            _prev = _now = 0; _rotating = false;
            _lx = _ly = _rx = _ry = _lt = _rt = 0;
        }

        // ------------------------------------------------------------ botones del juego
        static T Find<T>() where T : UnityEngine.Object
        {
            var o = UnityEngine.Object.FindObjectOfType(Il2CppType.Of<T>());
            return o == null ? null : o.TryCast<T>();
        }

        static bool Click(UnityEngine.UI.Button b)
        {
            if (b == null || !b.gameObject.activeInHierarchy || !b.IsInteractable()) return false;
            b.onClick.Invoke();
            return true;
        }

        static void TurnButton()
        {
            try
            {
                var hud = Find<Hud>();
                if (hud == null) return;
                if (!Click(hud.instructCompleteButton)) Click(hud.skipActionPhaseButton);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Mando] Finalizar turno: " + e.Message); }
        }

        static void ToggleLog()
        {
            try
            {
                var log = Find<InGameLogManager>();
                if (log == null) return;
                if (log.IsOpenLogWindow()) log.CloseLogWindow(); else log.OpenLogWindow();
            }
            catch (Exception e) { Plugin.L.LogWarning("[Mando] Registro: " + e.Message); }
        }

        // ------------------------------------------------------------ vibracion
        struct Pulse { public float start, end, left, right; }
        static readonly List<Pulse> _pulses = new();
        static float _beatUntil, _nextBeat;     // latido: hasta cuando y cuando toca el siguiente
        static bool _execution;                 // el latido es de una ejecucion: sigue hasta el golpe
        static ushort _sentL, _sentR;

        static void Rumble(float delay, float dur, float left, float right)
        {
            if (!_connected) return;
            float t = Time.unscaledTime + delay;
            _pulses.Add(new Pulse { start = t, end = t + dur, left = left, right = right });
        }

        static void Heartbeat(bool execution, float maxSeconds)
        {
            if (!_connected) return;
            if (Time.unscaledTime >= _beatUntil) _nextBeat = Time.unscaledTime;
            _execution = execution || (_execution && Time.unscaledTime < _beatUntil);
            _beatUntil = Time.unscaledTime + maxSeconds;
        }

        static void StopHeartbeat() { _beatUntil = 0; _execution = false; }

        static void UpdateRumble()
        {
            float now = Time.unscaledTime;
            if (now < _beatUntil && now >= _nextBeat)
            {
                Rumble(0f, 0.09f, 0.55f, 0.10f);      // "pum"
                Rumble(0.19f, 0.07f, 0.35f, 0.05f);   // "pum"
                _nextBeat = now + 0.95f;
            }
            float l = 0, r = 0;
            for (int i = _pulses.Count - 1; i >= 0; i--)
            {
                var p = _pulses[i];
                if (now >= p.end) { _pulses.RemoveAt(i); continue; }
                if (now >= p.start) { l = Math.Max(l, p.left); r = Math.Max(r, p.right); }
            }
            Send((ushort)(l * 65535), (ushort)(r * 65535));
        }

        static void Send(ushort l, ushort r)
        {
            if (_set == null || _slot < 0 || (l == _sentL && r == _sentR)) return;
            var v = new XVibration { left = l, right = r };
            try { _set((uint)_slot, ref v); _sentL = l; _sentR = r; } catch { }
        }

        static void StopRumble() { _pulses.Clear(); StopHeartbeat(); Send(0, 0); }

        // Wwise identifica cada sonido por un numero: FNV-1 de 32 bits del nombre en minusculas
        static uint WwiseId(string name)
        {
            uint h = 2166136261;
            foreach (char c in name.ToLowerInvariant()) { h *= 16777619; h ^= (byte)c; }
            return h;
        }

        static readonly uint KillCheck = WwiseId("Play_sfx_sys_killcheck_start");
        static readonly uint KillJingle = WwiseId("Play_bgm_jingle_killcheck");
        static readonly uint Hit = WwiseId("Play_sfx_p_atk_hit");
        static readonly uint SherlockAppear = WwiseId("Play_sfx_p_sherlock_appear");
        static float _lastSound;
        static uint _lastId;

        static void OnSound(uint id)
        {
            float now = Time.unscaledTime;
            if (id == _lastId && now - _lastSound < 0.1f) return;    // el mismo sonido por dos caminos
            _lastId = id; _lastSound = now;
            if (id == KillCheck || id == KillJingle)
                Heartbeat(false, 12f);
            else if (id == Hit && _execution && now < _beatUntil)
            {
                StopHeartbeat();
                Rumble(0f, 0.5f, 1f, 0.8f);                           // el golpe
            }
            else if (id == SherlockAppear)
                Rumble(0f, 0.3f, 0.45f, 0.35f);
        }

        static void PatchRumble(Harmony h)
        {
            var me = typeof(Pad);
            HarmonyMethod M(string n) => new HarmonyMethod(me.GetMethod(n, System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic));
            void Patch(Type t, string method, string post)
            {
                try
                {
                    var m = AccessTools.DeclaredMethod(t, method);
                    if (m == null) { Log($"{t.Name}.{method}: no existe"); return; }
                    h.Patch(m, postfix: M(post));
                }
                catch (Exception e) { Plugin.L.LogWarning($"[Mando] {t.Name}.{method}: {e.Message}"); }
            }
            try
            {
                foreach (var m in typeof(AkSoundEngine).GetMethods(System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public))
                    if (m.Name == "PostEvent" && m.GetParameters().Length > 0)
                        h.Patch(m, postfix: M(nameof(AfterPostEvent)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Mando] sonidos: " + e.Message); }
            Patch(typeof(PawnController), "SelectPawn", nameof(AfterSelectPawn));
            Patch(typeof(PawnController), "SetPing", nameof(AfterOrder));
            Patch(typeof(GameManager), "PlayKillScene", nameof(AfterKillScene));
            Patch(typeof(GameManager), "PlayKillPrevendScene", nameof(AfterKillScene));
            Patch(typeof(CharaTalkDialogue), "OpenTalkDialogue", nameof(AfterDialogue));
        }

        static void AfterPostEvent(object[] __args)
        {
            try
            {
                if (!_connected || __args == null || __args.Length == 0) return;
                switch (__args[0])
                {
                    case uint id: OnSound(id); break;
                    case string name: OnSound(WwiseId(name)); break;
                }
            }
            catch { }
        }

        static void AfterSelectPawn(bool __result) { if (__result) Rumble(0f, 0.06f, 0f, 0.30f); }
        static void AfterOrder() { Rumble(0f, 0.10f, 0.20f, 0.45f); }
        static void AfterKillScene() { Heartbeat(true, 20f); }
        static void AfterDialogue(bool __result)
        {
            if (__result && !_execution && Time.unscaledTime < _beatUntil) StopHeartbeat();   // empieza a hablar
        }

        // ------------------------------------------------------------ gestor de controles del juego
        static bool Status(string id)
        {
            if (!_connected || id == null) return false;
            switch (id)
            {
                case "CameraMoveUp": return _ry > 0;
                case "CameraMoveDown": return _ry < 0;
                case "CameraMoveLeft": return _rx < 0;
                case "CameraMoveRight": return _rx > 0;
                case "CameraRotate": return _rotating;
            }
            return Buttons.TryGetValue(id, out var b) && Held(b);
        }

        static bool Down(string id) => _connected && id != null && Buttons.TryGetValue(id, out var b) && Pressed(b);
        static bool Up(string id) => _connected && id != null && Buttons.TryGetValue(id, out var b) && Released(b);

        static void AfterIsDown(ref bool __result, ref string id) { if (!__result && Down(id)) __result = true; }
        static void AfterIsUp(ref bool __result, ref string id) { if (!__result && Up(id)) __result = true; }
        static void AfterIsStatus(ref bool __result, ref string id) { if (!__result && Status(id)) __result = true; }

        static void AfterGetScroll(ref float __result)
        {
            if (!_connected || __result != 0) return;
            float z = _rt - _lt;
            if (z != 0) __result = z * 2.5f * Math.Min(Time.unscaledDeltaTime, 0.05f);
        }
    }
}
