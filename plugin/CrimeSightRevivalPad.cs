// CRIMESIGHT Revival - gamepad controls.
//
// The game is only played with mouse and keyboard. Its input manager (KeySettingManager) already has
// gamepad functions, but empty. Here:
//   - The gamepad is read with XInput. Steam presents PlayStation and Switch pads and the Steam Deck
//     itself as an Xbox pad, so it works for all of them (also on Linux with Proton).
//   - The left stick really moves the cursor and A / B do left / right click: that way every
//     menu and button of the game works without touching them.
//   - The camera, the indicator menu, seeing suspects and the arrows are given to the game's input
//     manager as if they were its own keys (KeySettingManager.IsDown/IsUp/IsStatus/GetScroll).
//   - Start presses "End turn" (or "Skip action") and Back opens or closes the log.
//
//   Left stick: cursor                       A: click       B: right click
//   L3 / R3: cursor / camera speed (slow, medium, fast; 1, 2 or 3 vibration taps)
//   Right stick: move the camera             LB / RB: turn the camera   LT / RT: zoom out / in
//   X: indicators and stickers               Y: see suspects            D-pad: arrows
//   Start: End turn / Skip action            Back: Log
//   Create room, waiting room and their windows: B / Start / Back (and LB / RB, X / Y) press their button; D-pad
//   up: the settings cog (see CrimeSightRevivalPadUi.cs)
//
// Vibration: a tap when choosing a character and another when confirming an order for it; a heartbeat when two
// characters are left alone with a weapon (murder check scene) until the
// dialogue starts, or, if it is an execution, until the blow, which vibrates hard; and a normal vibration when
// Sherlock shows up to make his deduction. The moments are detected by the sounds the game plays.
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using HarmonyLib;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using TMPro;
using UnityEngine;
using UnityEngine.TextCore;

namespace CrimeSightRevival.Mods
{
    static partial class Pad
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
        struct XVibration { public ushort left, right; }      // left: low (thud); right: high (tap)
        delegate uint SetStateFn(uint user, ref XVibration v);
        static SetStateFn _set;
        [DllImport("xinput1_4.dll", EntryPoint = "XInputSetState")] static extern uint Set14(uint u, ref XVibration v);
        [DllImport("xinput1_3.dll", EntryPoint = "XInputSetState")] static extern uint Set13(uint u, ref XVibration v);
        [DllImport("xinput9_1_0.dll", EntryPoint = "XInputSetState")] static extern uint Set910(uint u, ref XVibration v);

        const ushort DUP = 0x0001, DDOWN = 0x0002, DLEFT = 0x0004, DRIGHT = 0x0008, START = 0x0010, BACK = 0x0020,
                     L3 = 0x0040, R3 = 0x0080, LB = 0x0100, RB = 0x0200, A = 0x1000, B = 0x2000, X = 0x4000, Y = 0x8000;

        // ------------------------------------------------------------ system mouse and keyboard
        [StructLayout(LayoutKind.Sequential)]
        struct MouseInput { public int dx, dy; public uint data, flags, time; public IntPtr extra; }
        [StructLayout(LayoutKind.Explicit, Size = 40)]
        struct Input { [FieldOffset(0)] public uint type; [FieldOffset(8)] public MouseInput mi; }
        [DllImport("user32.dll")] static extern uint SendInput(uint n, Input[] inputs, int size);

        const uint MOVE = 0x0001, LDOWN = 0x0002, LUP = 0x0004, RDOWN = 0x0008, RUP = 0x0010;

        static void Mouse(uint flags, int dx = 0, int dy = 0)
        {
            _lastInjected = Time.unscaledTime;
            var i = new Input[1];
            i[0].type = 0;
            i[0].mi = new MouseInput { dx = dx, dy = dy, flags = flags };
            SendInput(1, i, Marshal.SizeOf<Input>());
        }

        // ------------------------------------------------------------ state
        static ushort _now, _prev;
        static float _lx, _ly, _rx, _ry, _lt, _rt;
        static float _rawLx, _rawLy;           // left stick without dead zone (-1..1)
        static double _cx, _cy;                // cursor position with decimals
        static bool _cursorHeld;               // _cx/_cy follow the real cursor
        const float CursorDead = 0.16f;
        static int _rotDone;                   // pixels moved to turn (given back on release)
        static bool _rotating, _connected, _announced;
        static readonly Dictionary<string, ushort> Buttons = new()
        {
            ["PingStampMenu"] = X, ["ViewHint"] = Y, ["Cancel"] = B,          // Cancel (Esc): only in the match
            ["UpArrow"] = DUP, ["DownArrow"] = DDOWN, ["LeftArrow"] = DLEFT, ["RightArrow"] = DRIGHT,
        };

        static void Log(string s) => Plugin.L.LogInfo("[Mando] " + s);

        // speeds: 0 slow, 1 medium, 2 fast (saved in csr_live/pad.txt)
        static readonly float[] CursorSpeeds = { 0.5f, 0.9f, 1.4f };     // screens per second at full tilt
        static readonly float[] CameraSpeeds = { 0.35f, 0.65f, 1f };      // fraction of the game's speed
        static int _cursorSpeed = 1, _cameraSpeed = 1;
        static string _styleSetting = "auto";
        // camera with the right stick: it is moved here directly (not pressing "keys" now and then, which
        // stuttered), in the exact direction of the stick and with the speed according to the tilt
        static float _camVx, _camVy;           // current speed (smoothed), -1..1 per axis
        static int _camAllowedFrame = -10;     // last frame in which the game allowed the camera to move
        const float KeyStep = 0.25f;           // what the game moves per frame with the keys (KEY_MOVE_SPEED)

        static string SpeedFile => System.IO.Path.Combine(LiveMods.LiveDir, "pad.txt");

        static void LoadSpeeds()
        {
            try
            {
                var p = System.IO.File.ReadAllText(SpeedFile).Trim().Split(',');
                _cursorSpeed = Math.Clamp(int.Parse(p[0]), 0, 2);
                _cameraSpeed = Math.Clamp(int.Parse(p[1]), 0, 2);
                if (p.Length > 2 && (p[2] == "xbox" || p[2] == "ps" || p[2] == "sw")) _styleSetting = p[2];
            }
            catch { }
        }

        static void SaveSpeeds()
        {
            try { System.IO.File.WriteAllText(SpeedFile, _cursorSpeed + "," + _cameraSpeed + "," + _styleSetting); } catch { }
        }

        static void SpeedTaps(int level)
        {
            for (int i = 0; i <= level; i++) Rumble(i * 0.18f, 0.08f, 0.25f, 0.5f);
        }

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
            LoadSpeeds();
            try
            {
                var m = AccessTools.DeclaredMethod(typeof(KeySettingManager), "GetSpriteMacro");
                if (m != null) h.Patch(m, postfix: new HarmonyMethod(typeof(Pad).GetMethod(nameof(AfterSpriteMacro),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Mando] iconos: " + e.Message); }
            // GetSpriteMacro is private and the game's compiler inlines it into its callers, so
            // the already built text is touched up too: the keyboard/mouse icons are swapped for the gamepad's.
            // (SetKeyMacroColor isn't touched: its colour reaches the plugin wrong and texts came out in odd colours;
            // Aliases changes those)
            foreach (var (name, post) in new[] { ("SetKeyMacroText", nameof(AfterMacroText)) })
            {
                try
                {
                    var m = AccessTools.DeclaredMethod(typeof(KeySettingManager), name);
                    if (m != null) h.Patch(m, postfix: new HarmonyMethod(typeof(Pad).GetMethod(post,
                        System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
                    else Log("KeySettingManager." + name + ": no existe");
                }
                catch (Exception e) { Plugin.L.LogWarning("[Mando] " + name + ": " + e.Message); }
            }
        }

        static readonly System.Text.RegularExpressions.Regex SpriteTag =
            new System.Text.RegularExpressions.Regex("<sprite name=\"?([A-Za-z0-9_]+)\"?[^>]*>");

        // Game icon -> gamepad icon (null = stays as it is)
        static string PadSprite(string name)
        {
            switch (name)
            {
                case "mouse_left_click": case "keyboard_enter": case "keyboard_space": return Btn("a");
                case "keyboard_esc": return Btn("b");
                case "keyboard_ctrl": return Btn("x");
                case "mouse_right_click": case "mouse_middle_click": return "";
                case "keyboard_tab": return Btn("y");
                case "mouse_blank": return "";                       // the game's gap when there is no mouse button
                case "mouse_DragLeft": return Sprite("rstick");
                case "mouse_DragRight": return Btn("lbrb");
                case "mouse_wheel": return Btn("ltrt");
                case "keyboard_up": case "keyboard_down": case "keyboard_left": case "keyboard_right": return Sprite("dpad");
            }
            return null;
        }

        // Already built text -> how it was built (to redo it when switching between gamepad and mouse)
        struct Macro { public string raw; public bool colored; public Color color; }
        static readonly Dictionary<string, Macro> _macros = new();

        static void Remember(string result, Macro m)
        {
            if (string.IsNullOrEmpty(result) || m.raw == null) return;
            if (_macros.Count > 3000) _macros.Clear();
            _macros[result] = m;
        }

        static void AfterMacroText(ref string ParseText, ref string __result)
        {
            var raw = ParseText;
            Swap(ref __result);
            Remember(__result, new Macro { raw = raw });
        }

        static void Swap(ref string __result)
        {
            if (!_iconsReady || !_padMode || string.IsNullOrEmpty(__result) || __result.IndexOf("<sprite", StringComparison.Ordinal) < 0) return;
            try
            {
                var s = SpriteTag.Replace(__result, m => m.Groups[1].Value.StartsWith("csr_") ? m.Value : (PadSprite(m.Groups[1].Value) ?? m.Value));
                // the same button twice in a row (mouse + key, or the four arrows) is left as one
                string prev;
                do
                {
                    prev = s;
                    s = System.Text.RegularExpressions.Regex.Replace(s,
                        "((?:<sprite name=\"csr_[a-z0-9_]+\">)+)(?:\\s|/|,|\u30fb)*\\1", "$1");
                } while (s != prev);
                __result = s;
            }
            catch (Exception e) { if (!_macroWarned) { _macroWarned = true; Plugin.L.LogWarning("[Mando] texto de teclas: " + e.Message); } }
        }
        static bool _macroWarned;

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
            // with the gamepad connected its slot is read every frame; without a gamepad the four are searched once
            // a second (asking about empty slots is slow and would stutter)
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

        [StructLayout(LayoutKind.Sequential)] struct Rect32 { public int left, top, right, bottom; }
        [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr h, out Rect32 r);

        static void MoveCursor(float dt)
        {
            float x = _rawLx, y = _rawLy;
            float mag = (float)Math.Sqrt(x * x + y * y);
            if (mag < CursorDead) { _cursorHeld = false; return; }
            float m = Math.Min(1f, (mag - CursorDead) / (1f - CursorDead));
            float curve = 0.25f * m + 0.75f * m * m;               // fine at the start, fast at full tilt
            float speed = Screen.height * CursorSpeeds[_cursorSpeed] * curve * dt;
            float dx = x / mag * speed, dy = -y / mag * speed;
            if (!GetCursorPos(out var now)) return;
            // if the real cursor isn't where we left it (the mouse moved it), it starts from there
            if (!_cursorHeld || Math.Abs(now.x - Math.Round(_cx)) > 1 || Math.Abs(now.y - Math.Round(_cy)) > 1)
            {
                _cx = now.x; _cy = now.y; _cursorHeld = true;
            }
            _cx += dx; _cy += dy;
            // without leaving the game window
            var w = GetActiveWindow();
            if (w != IntPtr.Zero && GetClientRect(w, out var rc))
            {
                var tl = new Point { x = rc.left, y = rc.top };
                var br = new Point { x = rc.right - 1, y = rc.bottom - 1 };
                ClientToScreen(w, ref tl); ClientToScreen(w, ref br);
                _cx = Math.Max(tl.x, Math.Min(br.x, _cx));
                _cy = Math.Max(tl.y, Math.Min(br.y, _cy));
            }
            int nx = (int)Math.Round(_cx), ny = (int)Math.Round(_cy);
            if (nx != now.x || ny != now.y)
            {
                _lastInjected = Time.unscaledTime;
                SetCursorPos(nx, ny);
            }
        }

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

        // ------------------------------------------------------------ every frame
        public static void Frame()
        {
            if (!Read(out var s))
            {
                if (_connected) { Release(); _connected = false; HideHints(); }
                return;
            }
            if (!_connected)
            {
                _connected = true;
                if (!_announced) { _style = DetectStyle(); Log("mando conectado (" + _style + ")"); _announced = true; }
            }
            if (!Application.isFocused) { Release(); return; }
            Icons();
            ClickStep();
            SteamStyle();

            _prev = _now;
            _now = s.buttons;
            _lx = Stick(s.lx); _ly = Stick(s.ly); _rx = Stick(s.rx); _ry = Stick(s.ry);
            _rawLx = Math.Max(-1f, s.lx / 32767f); _rawLy = Math.Max(-1f, s.ly / 32767f);
            _lt = s.lt > 30 ? (s.lt - 30) / 225f : 0; _rt = s.rt > 30 ? (s.rt - 30) / 225f : 0;
            float dt = Math.Min(Time.unscaledDeltaTime, 0.05f);

            if (Pressed(L3)) { _cursorSpeed = (_cursorSpeed + 1) % 3; SaveSpeeds(); SpeedTaps(_cursorSpeed); Log("velocidad del cursor: " + _cursorSpeed); }
            if (Pressed(R3)) { _cameraSpeed = (_cameraSpeed + 1) % 3; SaveSpeeds(); SpeedTaps(_cameraSpeed); Log("velocidad de la camara: " + _cameraSpeed); }

            // camera: the game moves it at a fixed speed while the "key" is held; it is held only in some
            // of the frames, depending on how far the stick is tilted and the chosen speed
            float k = CameraSpeeds[_cameraSpeed];
            if (ScrollMode())
            {
                // outside the match (or with the log open) the right stick is the mouse wheel
                _camVx = _camVy = 0;
                _wheel += _ry * Math.Abs(_ry) * 900f * (0.5f + 0.5f * k) * dt;
                int w = (int)_wheel;
                if (w != 0) { Wheel(w); _wheel -= w; }
            }
            else
            {
                _wheel = 0;
                try { CameraStick(s.rx, s.ry, k, dt); }
                catch (Exception e) { if (!_camWarned) { _camWarned = true; Plugin.L.LogWarning("[Mando] camara: " + e.Message); } }
            }

            // cursor: the stick as a vector (round dead zone and curve over the distance, not per axis),
            // so the direction is the finger's and circles can be made. It moves to an exact position
            // (not "x pixels"), so Windows' mouse acceleration doesn't bend it towards the axes.
            if (_rotating) { _cursorHeld = false; }                // while turning, the cursor belongs to the camera
            else MoveCursor(dt);

            // waiting room and its windows: B / Start / Back press their button (CrimeSightRevivalPadUi.cs)
            UiButtons(out bool startDone, out bool backDone);

            if (Pressed(A)) Mouse(LDOWN);
            if (Released(A)) Mouse(LUP);
            // B: in the match it is "Cancel" (Esc) and not the right click, which opens the sticker window
            if (Pressed(B) && !_bConsumed) { if (_inGame) _bCancel = true; else Mouse(RDOWN); }
            if (Released(B)) { if (!_bConsumed && !_bCancel) Mouse(RUP); _bConsumed = false; _bCancel = false; }

            // turn the camera: the game turns while "CameraRotate" is active, according to how much the cursor moves
            bool rot = !ScrollMode() && !_uiTabs && (Held(LB) ^ Held(RB));      // outside the match LB/RB do nothing
            if (rot)
            {
                _rotating = true;
                int d = (int)Math.Round((Held(RB) ? 1 : -1) * Screen.height * 0.45f * dt);
                if (d != 0) { Mouse(MOVE, d, 0); _rotDone += d; }
            }
            else if (_rotating)
            {
                _rotating = false;
                if (_rotDone != 0) { Mouse(MOVE, -_rotDone, 0); _rotDone = 0; }   // the cursor goes back to its place
            }

            if (Pressed(START) && !startDone && _inGame) TurnButton();
            if (Pressed(BACK) && !backDone && _inGame) ToggleLog();
            UpdateRumble();
            UpdateMode(s);
        }

        static float _wheel, _modeNext;
        static bool _scrollMode, _inGame, _bCancel;

        static void Wheel(int delta)
        {
            _lastInjected = Time.unscaledTime;
            var i = new Input[1];
            i[0].type = 0;
            i[0].mi = new MouseInput { data = unchecked((uint)delta), flags = 0x0800 };
            SendInput(1, i, Marshal.SizeOf<Input>());
        }

        static bool ScrollMode()
        {
            if (Time.unscaledTime < _modeNext) return _scrollMode;
            _modeNext = Time.unscaledTime + 0.25f;
            bool inGame = false, log = false;
            try
            {
                var hud = GetHud();
                inGame = hud != null && hud.gameObject.activeInHierarchy;
                if (inGame) { var l = Find<InGameLogManager>(); log = l != null && l.IsOpenLogWindow(); }
            }
            catch { }
            _scrollMode = !inGame || log;
            _inGame = inGame;
            return _scrollMode;
        }

        static bool _camWarned;

        // Like the game does with the arrows (the character tracking is released and the point it looks at
        // moves), but with an analog vector: round dead zone, soft curve and gradual start/stop.
        // It is measured by time, so it runs the same at 30 as at 144 fps.
        static void CameraStick(short sx, short sy, float k, float dt)
        {
            float x = Math.Max(-1f, sx / 32767f), y = Math.Max(-1f, sy / 32767f);
            float m = (float)Math.Sqrt(x * x + y * y);
            float tx = 0, ty = 0;
            const float dead = 0.16f;
            if (m > dead)
            {
                float n = Math.Min(1f, (m - dead) / (1f - dead));
                float c = (0.3f * n + 0.7f * n * n) * k / m;
                tx = x * c; ty = y * c;
            }
            float a = Math.Min(1f, dt * 14f);
            _camVx += (tx - _camVx) * a;
            _camVy += (ty - _camVy) * a;
            if (tx == 0 && Math.Abs(_camVx) < 0.004f) _camVx = 0;
            if (ty == 0 && Math.Abs(_camVy) < 0.004f) _camVy = 0;
            if ((_camVx == 0 && _camVy == 0) || _rotating) return;
            if (Time.frameCount - _camAllowedFrame > 2) return;     // menus, scenes, log open...
            var cm = CameraManager.Instance;
            if (cm == null) return;
            var cam = cm.GetCurrentCamera();
            if (cam == null || !cm.ResetFocusObject()) return;
            var t = cam.transform;
            Vector3 off = (t.up * _camVy + t.right * _camVx) * (KeyStep * 60f * dt);
            Vector3 pos = Vector3.zero;
            if (cm.GetTargetPosition(ref off, ref pos)) cam.SetTarget(ref pos);
        }

        static bool Tick(ref float acc, float amount)
        {
            if (amount <= 0) { acc = 0; return false; }
            acc += amount;
            if (acc < 1f) return false;
            acc -= 1f;
            return true;
        }

        static void Release()
        {
            StopRumble();
            if ((_now & A) != 0) Mouse(LUP);
            if ((_now & B) != 0 && !_bConsumed && !_bCancel) Mouse(RUP);
            _bConsumed = _bCancel = _gearHeld = _xTaken = _yTaken = false;
            if (_rotDone != 0) { Mouse(MOVE, -_rotDone, 0); _rotDone = 0; }
            _prev = _now = 0; _rotating = false;
            _lx = _ly = _rx = _ry = _lt = _rt = 0;
        }

        // ------------------------------------------------------------ game buttons
        static T Find<T>() where T : UnityEngine.Object
        {
            // FindObjectOfType isn't in the game (the compiler removed it): the version that returns all of them is
            // used
            var all = UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<T>());
            if (all == null) return null;
            foreach (var o in all) { var t = o == null ? null : o.TryCast<T>(); if (t != null) return t; }
            return null;
        }

        static Hud GetHud()
        {
            try { var gm = GameManager.instance; if (gm != null && gm.hud != null) return gm.hud; } catch { }
            try { return Find<Hud>(); } catch { return null; }
        }

        static bool Click(UnityEngine.UI.Button b)
        {
            if (b == null || !b.gameObject.activeInHierarchy || !b.IsInteractable()) return false;
            b.onClick.Invoke();
            return true;
        }

        // The button is really pressed: the cursor goes over it, clicks and goes back to where it was. That way the
        // game does
        // exactly the same as with the mouse (sound, confirmations...).
        [StructLayout(LayoutKind.Sequential)] struct Point { public int x, y; }
        [DllImport("user32.dll")] static extern bool GetCursorPos(out Point p);
        [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
        [DllImport("user32.dll")] static extern IntPtr GetActiveWindow();
        [DllImport("user32.dll")] static extern bool ClientToScreen(IntPtr h, ref Point p);
        static int _clickStage, _clickHover = 2;          // frames with the cursor over it before pressing
        static Point _clickBack;

        static bool ClickAt(UnityEngine.UI.Button b)
        {
            if (b == null || !b.gameObject.activeInHierarchy || !b.IsInteractable()) return false;
            return ClickAt(b.GetComponent<RectTransform>());
        }

        static bool ClickAt(RectTransform rt)
        {
            if (rt == null || !rt.gameObject.activeInHierarchy) return false;
            Camera cam = null;
            var canvas = rt.GetComponentInParent<Canvas>();
            if (canvas != null) { canvas = canvas.rootCanvas; if (canvas.renderMode != RenderMode.ScreenSpaceOverlay) cam = canvas.worldCamera; }
            var sp = RectTransformUtility.WorldToScreenPoint(cam, rt.TransformPoint(rt.rect.center));
            var p = new Point { x = (int)sp.x, y = Screen.height - (int)sp.y };
            ClientToScreen(GetActiveWindow(), ref p);
            GetCursorPos(out _clickBack);
            _lastInjected = Time.unscaledTime;
            SetCursorPos(p.x, p.y);
            _clickStage = 1;
            return true;
        }

        // one step per frame: over -> press -> release -> go back
        static void ClickStep()
        {
            if (_clickStage == 0) return;
            _lastInjected = Time.unscaledTime;
            int st = _clickStage++;
            if (st <= _clickHover) return;                   // so the game sees the cursor over the button
            switch (st - _clickHover)
            {
                case 1: Mouse(LDOWN); break;
                case 2: break;
                case 3: Mouse(LUP); break;
                default: SetCursorPos(_clickBack.x, _clickBack.y); _clickStage = 0; _clickHover = 2; break;
            }
        }

        static void TurnButton()
        {
            if (_clickStage != 0) return;
            try
            {
                var hud = GetHud();
                if (hud == null) { Log("Start: no encuentro la interfaz de la partida"); return; }
                if (!ClickAt(hud.instructCompleteButton) && !ClickAt(hud.skipActionPhaseButton))
                    if (!Click(hud.instructCompleteButton) && !Click(hud.skipActionPhaseButton)) Log("Start: no hay boton de turno activo");
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

        // ------------------------------------------------------------ gamepad icons in the help bar
        // The game draws the keys with a TextMeshPro "sprite asset" (keyboard_ctrl, mouse_wheel...). One of ours with
        // gamepad icons is added as a fallback (plugin/pad_icons.png, see tools/pad_icons.py) and,
        // while you play with a gamepad, each action is drawn with its button.
        static readonly string[] IconNames = {
            "xbox_a", "xbox_b", "xbox_x", "xbox_y", "xbox_lb", "xbox_rb", "xbox_lt", "xbox_rt",
            "ps_a", "ps_b", "ps_x", "ps_y", "ps_lb", "ps_rb", "ps_lt", "ps_rt",
            "sw_a", "sw_b", "sw_x", "sw_y", "sw_lb", "sw_rb", "sw_lt", "sw_rt",
            "lstick", "rstick", "dpad", "xbox_start", "xbox_back", "ps_start", "ps_back", "sw_start",
            "sw_back", "dpad_up", "dpad_down", "dpad_left", "dpad_right" };
        static readonly string[] Combos = { "xbox_lbrb", "xbox_ltrt", "ps_lbrb", "ps_ltrt", "sw_lbrb", "sw_ltrt" };
        static readonly Dictionary<string, TMP_SpriteGlyph> _glyphs = new();
        static TMP_SpriteAsset _src, _mine;
        static int _baseChars;
        static readonly Dictionary<int, string> _srcNames = new();   // original name of each game icon
        static string _aliasState = "";

        // Game icon -> ours (name in _glyphs). That way any game text changes, however it was built.
        static string AliasFor(string name)
        {
            switch (name)
            {
                case "mouse_left_click": case "keyboard_enter": case "keyboard_space": return _style + "_a";
                case "keyboard_esc": return _style + "_b";
                case "keyboard_ctrl": return _style + "_x";
                case "keyboard_tab": return _style + "_y";
                // in the bar each action shows as "mouse button + key"; with a gamepad the mouse one is extra
                case "mouse_blank": case "mouse_right_click": case "mouse_middle_click": return "blank";
                case "mouse_DragLeft": return "rstick";
                case "mouse_DragRight": return _style + "_lbrb";
                case "mouse_wheel": return _style + "_ltrt";
                case "keyboard_up": case "keyboard_down": case "keyboard_left": case "keyboard_right": return "dpad";
            }
            return null;
        }

        // With a gamepad, the game's icons are "hidden" (renamed) and ours take their name; TextMeshPro
        // doesn't find them in its own and looks for them in ours. With the mouse everything is left as it was.
        static void Aliases()
        {
            if (_src == null || _mine == null) return;
            string want = _padMode ? _style : "";
            if (want == _aliasState) return;
            try
            {
                var table = _src.spriteCharacterTable;
                for (int i = 0; i < table.Count; i++)
                {
                    var c = table[i];
                    if (!_srcNames.TryGetValue(i, out var orig)) { orig = c.name; _srcNames[i] = orig; }
                    string target = _padMode && AliasFor(orig) != null ? "csrhide_" + orig : orig;
                    if (c.name != target) c.name = target;
                }
                _src.UpdateLookupTables();

                var mt = _mine.spriteCharacterTable;
                if (mt.Count > _baseChars) mt.RemoveRange(_baseChars, mt.Count - _baseChars);
                if (_padMode)
                    foreach (var orig in _srcNames.Values)
                    {
                        var a = AliasFor(orig);
                        if (a != null && _glyphs.TryGetValue(a, out var g)) mt.Add(new TMP_SpriteCharacter(0xFFFE, g) { name = orig });
                    }
                _mine.UpdateLookupTables();
                _aliasState = want;

                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<TMP_Text>()))
                {
                    var t = o == null ? null : o.TryCast<TMP_Text>();
                    if (t != null && t.text != null && t.text.IndexOf("<sprite", StringComparison.Ordinal) >= 0) t.SetAllDirty();
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Mando] iconos (cambio): " + e.Message); _aliasState = want; }
        }

        const int CELL = 64, SHEET = 512;
        static bool _iconsReady, _iconsFailed, _padMode;
        static float _iconsNextTry, _lastPadInput = -10f, _lastInjected = -10f;
        static string _style = "xbox";         // xbox, ps or sw (Switch)

        static void Icons()
        {
            if (_iconsReady || _iconsFailed || Time.unscaledTime < _iconsNextTry) return;
            _iconsNextTry = Time.unscaledTime + 2f;
            try
            {
                TMP_SpriteAsset src = null;
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<TMP_SpriteAsset>()))
                {
                    var a = o.TryCast<TMP_SpriteAsset>();
                    if (a != null && a.GetSpriteIndexFromName("keyboard_ctrl") >= 0) { src = a; break; }
                }
                if (src == null) return;                         // not loaded yet: it is tried again

                byte[] png;
                using (var st = typeof(Pad).Assembly.GetManifestResourceStream("CrimeSightRevival.PadIcons.png"))
                using (var ms = new System.IO.MemoryStream()) { st.CopyTo(ms); png = ms.ToArray(); }
                var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false) { name = "csr_pad_icons" };
                if (!ImageConversion.LoadImage(tex, png, false)) { _iconsFailed = true; Log("no pude cargar los iconos"); return; }
                tex.hideFlags = HideFlags.DontUnloadUnusedAsset;

                var mine = UnityEngine.Object.Instantiate(src);
                mine.name = "csr_pad_icons";
                mine.hideFlags = HideFlags.DontUnloadUnusedAsset;
                mine.spriteSheet = tex;
                var mat = new Material(src.material) { name = "csr_pad_icons_mat", hideFlags = HideFlags.DontUnloadUnusedAsset };
                mat.mainTexture = tex;
                mine.material = mat;
                mine.hashCode = TMP_TextUtilities.GetSimpleHashCode(mine.name);
                mine.materialHashCode = TMP_TextUtilities.GetSimpleHashCode(mat.name);

                // on-screen size: a game key's, as a square
                var refGlyph = src.spriteGlyphTable[src.spriteCharacterTable[src.GetSpriteIndexFromName("keyboard_ctrl")].glyphIndex < src.spriteGlyphTable.Count
                    ? (int)src.spriteCharacterTable[src.GetSpriteIndexFromName("keyboard_ctrl")].glyphIndex : 0];
                var rm = refGlyph.metrics;
                float h = rm.height;
                var metrics = new GlyphMetrics(h, h, 0, rm.horizontalBearingY, h + Math.Max(0, rm.horizontalAdvance - rm.width));

                mine.spriteGlyphTable.Clear();
                mine.spriteCharacterTable.Clear();
                for (int i = 0; i < IconNames.Length; i++)
                {
                    int col = i % (SHEET / CELL), row = i / (SHEET / CELL);
                    var g = new TMP_SpriteGlyph((uint)i, metrics, new GlyphRect(col * CELL, SHEET - (row + 1) * CELL, CELL, CELL), refGlyph.scale, 0);
                    mine.spriteGlyphTable.Add(g);
                    var c = new TMP_SpriteCharacter(0xFFFE, g) { name = "csr_" + IconNames[i] };
                    mine.spriteCharacterTable.Add(c);
                    _glyphs[IconNames[i]] = g;
                }
                // double buttons, twice as wide
                var wide = new GlyphMetrics(2 * h, h, 0, rm.horizontalBearingY, 2 * h + Math.Max(0, rm.horizontalAdvance - rm.width));
                for (int k2 = 0; k2 < Combos.Length; k2++)
                {
                    var g = new TMP_SpriteGlyph((uint)(IconNames.Length + k2), wide,
                        new GlyphRect((k2 % 4) * 2 * CELL, SHEET - (6 + k2 / 4) * CELL, 2 * CELL, CELL), refGlyph.scale, 0);
                    mine.spriteGlyphTable.Add(g);
                    mine.spriteCharacterTable.Add(new TMP_SpriteCharacter(0xFFFE, g) { name = "csr_" + Combos[k2] });
                    _glyphs[Combos[k2]] = g;
                }
                // "nothing": the empty cell at the bottom right, without width
                var blank = new TMP_SpriteGlyph((uint)(IconNames.Length + Combos.Length), new GlyphMetrics(1, 1, 0, 0, 0),
                    new GlyphRect(SHEET - CELL + 8, 8, 4, 4), refGlyph.scale, 0);
                mine.spriteGlyphTable.Add(blank);
                mine.spriteCharacterTable.Add(new TMP_SpriteCharacter(0xFFFE, blank) { name = "csr_blank" });
                _glyphs["blank"] = blank;
                _baseChars = mine.spriteCharacterTable.Count;
                _src = src; _mine = mine;
                mine.fallbackSpriteAssets = new Il2CppSystem.Collections.Generic.List<TMP_SpriteAsset>();
                mine.UpdateLookupTables();
                if (src.fallbackSpriteAssets == null) src.fallbackSpriteAssets = new Il2CppSystem.Collections.Generic.List<TMP_SpriteAsset>();
                src.fallbackSpriteAssets.Add(mine);
                _iconsReady = true;
                Log("iconos de mando listos");
                Aliases();
                if (_padMode) RefreshHelp();
            }
            catch (Exception e) { _iconsFailed = true; Plugin.L.LogWarning("[Mando] iconos: " + e); }
        }

        static string Sprite(string name) => $"<sprite name=\"csr_{name}\">";
        // for the Revival Guide: the game's icons (with ours as fallback) and the gamepad type
        internal static TMP_SpriteAsset KeyIcons => _src;
        internal static void EnsureIcons() { try { Icons(); } catch { } }   // also without a gamepad connected
        internal static string PadStyle => _style;
        static string Btn(string b) => Sprite(_style + "_" + b);

        static string PadMacro(string id)
        {
            switch (id)
            {
                case "Decide": case "DecideClick": case "LeftClick": return Btn("a");
                case "Cancel": case "CancelClick": case "RightClick": return Btn("b");
                case "PingStampMenu": return Btn("x");
                case "ViewHint": return Btn("y");
                case "MouseMove": return Sprite("lstick");
                case "MouseDragLeft": case "CameraTranslate": return Sprite("rstick");
                case "MouseDragRight": case "CameraRotate": return Btn("lbrb");
                case "Wheel": return Btn("ltrt");
                case "UpArrow": case "DownArrow": case "LeftArrow": case "RightArrow": return Sprite("dpad");
            }
            return null;                                         // F1-F6 and the rest: the keyboard ones stay
        }

        static void AfterSpriteMacro(ref string __result, ref string checkKey)
        {
            if (!_iconsReady || !_padMode || checkKey == null) return;
            var s = PadMacro(checkKey);
            if (s != null) __result = s;
        }

        // Gamepad or mouse: the last one touched is used (not counting what the gamepad itself moves)
        static void UpdateMode(XState s)
        {
            float now = Time.unscaledTime;
            bool pad = s.buttons != 0 || _lx != 0 || _ly != 0 || _rawLx * _rawLx + _rawLy * _rawLy > CursorDead * CursorDead || _rx != 0 || _ry != 0 || _lt != 0 || _rt != 0;
            if (pad) _lastPadInput = now;
            if (pad && !_padMode) SetMode(true);
            else if (_padMode && now - _lastPadInput > 0.4f && now - _lastInjected > 0.4f)
            {
                bool mouse = false;
                try { mouse = UnityEngine.Input.GetAxisRaw("Mouse X") != 0 || UnityEngine.Input.GetAxisRaw("Mouse Y") != 0; } catch { }
                if (mouse || UnityEngine.Input.anyKeyDown) SetMode(false);
            }
            if (_padMode && _iconsReady && now >= _nextFix) FixTexts();
        }

        static bool _helpWarned;

        static void SetMode(bool pad)
        {
            _padMode = pad;
            Aliases();
            if (_iconsReady) RefreshHelp();
        }

        static void RefreshHelp()
        {
            try
            {
                var hud = GetHud();
                if (hud != null)
                {
                    try { hud.SetKeyHelpLangText(); }
                    catch (Exception e) { if (!_helpWarned) { _helpWarned = true; Plugin.L.LogWarning("[Mando] barra de ayuda (textos): " + e); } }
                    try { hud.RefreshKeyHelp(); } catch { }
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Mando] barra de ayuda: " + e.Message); }
            FixTexts();
        }

        // Texts already on screen (bottom bar, notices over the map): their icons are changed.
        // What was changed by hand is remembered to give it back when returning to the mouse.
        static readonly Dictionary<string, string> _unswap = new();
        static float _nextFix;

        static void FixTexts()
        {
            _nextFix = Time.unscaledTime + 1f;
            try
            {
                foreach (var t in UnityEngine.Object.FindObjectsOfType<TMP_Text>())
                {
                    try
                    {
                        var cur = t == null ? null : t.text;
                        if (string.IsNullOrEmpty(cur) || cur.IndexOf("<sprite", StringComparison.Ordinal) < 0) continue;
                        string next = null;
                        if (_macros.TryGetValue(cur, out var m) && !m.colored)
                        {
                            var raw = m.raw;
                            next = KeySettingManager.SetKeyMacroText(ref raw);
                        }
                        if (next != null && next != cur) t.text = next;
                    }
                    catch { }
                }
            }
            catch (Exception e) { if (!_fixWarned) { _fixWarned = true; Plugin.L.LogWarning("[Mando] textos: " + e.Message); } }
        }
        static bool _fixWarned;

        // Gamepad type, for its icons. With Steam Input the game sees an Xbox pad, but the physical pad
        // is still in the device list: the vendor is checked (Sony 054C, Nintendo 057E). It can be fixed
        // in csr_live/pad.txt (third value: auto, xbox, ps or sw).
        [StructLayout(LayoutKind.Sequential)] struct RawDevice { public IntPtr handle; public uint type; }
        [DllImport("user32.dll")] static extern uint GetRawInputDeviceList([Out] RawDevice[] list, ref uint count, uint size);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern uint GetRawInputDeviceInfoW(IntPtr dev, uint cmd, System.Text.StringBuilder data, ref uint size);

        // With Steam Input the game only sees an Xbox pad. Steam knows which is the real one: it is asked.
        const string SteamDll = "steam_api64";
        [DllImport(SteamDll)] static extern IntPtr SteamAPI_SteamInput_v002();
        [DllImport(SteamDll)] [return: MarshalAs(UnmanagedType.I1)] static extern bool SteamAPI_ISteamInput_Init(IntPtr self, [MarshalAs(UnmanagedType.I1)] bool explicitRunFrame);
        [DllImport(SteamDll)] static extern void SteamAPI_ISteamInput_RunFrame(IntPtr self, [MarshalAs(UnmanagedType.I1)] bool reserved);
        [DllImport(SteamDll)] static extern ulong SteamAPI_ISteamInput_GetControllerForGamepadIndex(IntPtr self, int index);
        [DllImport(SteamDll)] static extern int SteamAPI_ISteamInput_GetConnectedControllers(IntPtr self, [Out] ulong[] handles);
        [DllImport(SteamDll)] static extern int SteamAPI_ISteamInput_GetInputTypeForHandle(IntPtr self, ulong handle);
        static IntPtr _steamInput;
        static bool _steamFailed, _steamFound;
        static float _steamNext, _steamUntil = -1;

        static string SteamTypeStyle(int t) => t switch
        {
            5 or 12 or 13 => "ps",                 // PS4, PS3, PS5
            8 or 9 or 10 => "sw",                  // Joy-Con, Pro Controller
            _ => t == 0 ? null : "xbox",
        };

        static void SteamStyle()
        {
            if (_steamFailed || _steamFound || _styleSetting != "auto") return;
            float now = Time.unscaledTime;
            if (_steamUntil < 0) _steamUntil = now + 20f;            // it is tried for 20 s
            if (now < _steamNext) return;
            if (now > _steamUntil) { _steamFailed = true; Log("Steam no dice que mando es"); return; }
            _steamNext = now + 1f;
            try
            {
                if (_steamInput == IntPtr.Zero)
                {
                    _steamInput = SteamAPI_SteamInput_v002();
                    if (_steamInput == IntPtr.Zero) { _steamFailed = true; return; }
                    SteamAPI_ISteamInput_Init(_steamInput, false);
                }
                SteamAPI_ISteamInput_RunFrame(_steamInput, false);
                int type = 0;
                ulong h = _slot >= 0 ? SteamAPI_ISteamInput_GetControllerForGamepadIndex(_steamInput, _slot) : 0;
                if (h != 0) type = SteamAPI_ISteamInput_GetInputTypeForHandle(_steamInput, h);
                if (type == 0)
                {
                    var hs = new ulong[16];
                    int n = SteamAPI_ISteamInput_GetConnectedControllers(_steamInput, hs);
                    if (n > 0) type = SteamAPI_ISteamInput_GetInputTypeForHandle(_steamInput, hs[0]);
                }
                var st = SteamTypeStyle(type);
                if (st == null) return;
                _steamFound = true;
                Log("Steam dice que el mando es de tipo " + type + " (" + st + ")");
                if (st != _style) { _style = st; Aliases(); if (_iconsReady && _padMode) RefreshHelp(); }
            }
            catch (Exception e) { _steamFailed = true; Log("Steam Input no disponible: " + e.Message); }
        }

        static bool _hidLogged;
        static string DetectStyle()
        {
            if (_styleSetting != "auto") return _styleSetting;
            try
            {
                uint n = 0, sz = (uint)Marshal.SizeOf<RawDevice>();
                GetRawInputDeviceList(null, ref n, sz);
                if (n == 0 || n > 512) return "xbox";
                var list = new RawDevice[n];
                if (GetRawInputDeviceList(list, ref n, sz) == uint.MaxValue) return "xbox";
                bool sony = false, nintendo = false;
                foreach (var d in list)
                {
                    if (d.type != 2) continue;                       // HID
                    uint len = 512;
                    var sb = new System.Text.StringBuilder(512);
                    if (GetRawInputDeviceInfoW(d.handle, 0x20000007, sb, ref len) == uint.MaxValue) continue;
                    var name = sb.ToString().ToUpperInvariant();
                    if (name.Contains("VID_054C") || name.Contains("054C_PID")) sony = true;          // USB and Bluetooth (VID&0002054C_PID)
                    if (name.Contains("VID_057E") || name.Contains("057E_PID")) nintendo = true;
                    if (!_hidLogged && (name.Contains("VID") )) Log("dispositivo HID: " + name);
                }
                _hidLogged = true;
                return sony ? "ps" : nintendo ? "sw" : "xbox";
            }
            catch { return "xbox"; }
        }

        // ------------------------------------------------------------ vibration
        struct Pulse { public float start, end, left, right; }
        static readonly List<Pulse> _pulses = new();
        static float _beatUntil, _nextBeat;     // heartbeat: until when and when the next one is due
        static bool _execution;                 // the heartbeat belongs to an execution: it goes on until the blow
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

        // ------------------------------------------------------------ vibration in time with the scenes
        // The scenes are game Timelines; their time is checked every frame and it vibrates at the right moment
        // (the times come from the Timelines themselves; see tools or the CLAUDE.md):
        //   p0220_Demo_Timeline   Sherlock detects: one pulse with each wave of the sphere (3.5, 4.333, 4.833) and
        //   one
        //                         stronger at the end (5.5)
        //   p0100_Demo_Timeline   murder (KillCutPrefab): the screen breaks at 13.783 (Glitch_Spider_Effect_Plane)
        //   p0155_p_Demo_Timeline murder stopped by Sherlock: the screen breaks at 14.233 (SS_04_Movie_Texture_Set)
        //                         and the owl's flash at 16.667
        // The blow comes 2 frames later, cuts the heartbeat and is very strong.
        const float Frame2 = 2f / 30f;
        struct Cue { public string timeline; public float t; public int kind; }    // 0 pulse, 1 strong pulse, 2 blow
        static readonly Cue[] Cues =
        {
            new Cue { timeline = "p0220_Demo_Timeline", t = 3.5f, kind = 0 },
            new Cue { timeline = "p0220_Demo_Timeline", t = 4.333f, kind = 0 },
            new Cue { timeline = "p0220_Demo_Timeline", t = 4.833f, kind = 0 },
            new Cue { timeline = "p0220_Demo_Timeline", t = 5.5f, kind = 1 },
            new Cue { timeline = "p0100_Demo_Timeline", t = 13.783f + Frame2, kind = 2 },
            new Cue { timeline = "p0155_p_Demo_Timeline", t = 14.233f + Frame2, kind = 2 },
            new Cue { timeline = "p0155_p_Demo_Timeline", t = 16.667f, kind = 1 },
        };
        static readonly List<(UnityEngine.Playables.PlayableDirector d, string name, double last)> _directors = new();
        static float _directorScan;

        static void UpdateScenes()
        {
            float now = Time.unscaledTime;
            if (now >= _directorScan)
            {
                _directorScan = now + 0.25f;
                var found = new List<(UnityEngine.Playables.PlayableDirector, string, double)>();
                foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<UnityEngine.Playables.PlayableDirector>()))
                {
                    var d = o?.TryCast<UnityEngine.Playables.PlayableDirector>();
                    if (d == null || !d.isActiveAndEnabled) continue;
                    string name = null;
                    try { name = d.playableAsset != null ? d.playableAsset.name : null; } catch { }
                    if (name == null || Array.FindIndex(Cues, c => c.timeline == name) < 0) continue;
                    double last = -1;
                    foreach (var k in _directors) if (k.d != null && k.d.Pointer == d.Pointer) { last = k.last; break; }
                    if (last < 0) Log($"escena {name}");
                    found.Add((d, name, last < 0 ? d.time : last));
                }
                _directors.Clear();
                _directors.AddRange(found);
            }
            for (int i = 0; i < _directors.Count; i++)
            {
                var (d, name, last) = _directors[i];
                double t;
                try { if (d == null || !d.isActiveAndEnabled) continue; t = d.time; } catch { continue; }
                if (t < last - 0.5) last = -1;                         // starts over
                foreach (var c in Cues)
                    if (c.timeline == name && last < c.t && t >= c.t) SceneCue(c.kind);
                _directors[i] = (d, name, t);
            }
        }

        static void SceneCue(int kind)
        {
            switch (kind)
            {
                case 0: Rumble(0f, 0.12f, 0.55f, 0.35f); Rumble(0.12f, 0.15f, 0.2f, 0.1f); break;   // pulse
                case 1: Rumble(0f, 0.18f, 0.8f, 0.6f); Rumble(0.18f, 0.2f, 0.3f, 0.15f); break;    // strong pulse
                case 2:                                                                             // blow
                    StopHeartbeat();
                    _pulses.Clear();
                    _hitAt = Time.unscaledTime;
                    Rumble(0f, 0.55f, 1f, 1f);
                    Rumble(0.55f, 0.35f, 0.45f, 0.25f);
                    break;
            }
        }

        static float _hitAt = -10f;

        static void UpdateRumble()
        {
            try { UpdateScenes(); } catch { }
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

        // Wwise identifies each sound by a number: 32-bit FNV-1 of the lowercase name
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
            if (id == _lastId && now - _lastSound < 0.1f) return;    // the same sound through two paths
            _lastId = id; _lastSound = now;
            if (id == KillCheck || id == KillJingle)
                Heartbeat(false, 12f);
            else if (id == Hit && _execution && now < _beatUntil && now - _hitAt > 2f)
            {
                StopHeartbeat();
                Rumble(0f, 0.5f, 1f, 0.8f);                           // the blow
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
            if (__result && !_execution && Time.unscaledTime < _beatUntil) StopHeartbeat();   // starts talking
        }

        // ------------------------------------------------------------ the game's input manager
        static bool Status(string id)
        {
            if (!_connected || id == null) return false;
            switch (id)
            {
                case "CameraRotate": return _rotating;
            }
            return !Taken(id) && Buttons.TryGetValue(id, out var b) && Held(b);
        }

        static bool Down(string id) => _connected && id != null && !Taken(id) && Buttons.TryGetValue(id, out var b) && Pressed(b);
        static bool Up(string id) => _connected && id != null && !Taken(id) && Buttons.TryGetValue(id, out var b) && Released(b);

        static void AfterIsDown(ref bool __result, ref string id) { if (!__result && Down(id)) __result = true; }
        static void AfterIsUp(ref bool __result, ref string id) { if (!__result && Up(id)) __result = true; }
        static void AfterIsStatus(ref bool __result, ref string id)
        {
            if (id == "CameraMoveRight") _camAllowedFrame = Time.frameCount;   // the game is checking whether to move the camera
            if (!__result && Status(id)) __result = true;
        }

        static void AfterGetScroll(ref float __result)
        {
            if (!_connected || __result != 0) return;
            float z = _rt - _lt;
            if (z != 0) __result = z * 2.5f * Math.Min(Time.unscaledDeltaTime, 0.05f);
        }
    }
}
