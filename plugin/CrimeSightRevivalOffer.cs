// CRIMESIGHT Revival - a guest's mods notice inside the game.
//
// When someone enters your room with their own stickers or avatars, the launcher asks you whether
// to download them. But the host is usually looking at the game, not the launcher, so the launcher also leaves
// the notice in csr_live/offer.json and here it is shown over the game with two buttons. The
// answer goes to csr_live/offer_answer.json and the launcher picks it up (answering in either
// place works). If the launcher removes the notice (answered there), the window closes by itself.
using System;
using System.IO;
using System.Text.Json;
using Il2CppInterop.Runtime;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace CrimeSightRevival.Mods
{
    static class ModOffer
    {
        class Msg
        {
            public string id { get; set; }
            public string title { get; set; }
            public string body { get; set; }
            public string yes { get; set; }
            public string no { get; set; }
            public string always { get; set; }
        }

        static string File_ => Path.Combine(LiveMods.LiveDir, "offer.json");
        static string AnswerFile => Path.Combine(LiveMods.LiveDir, "offer_answer.json");

        static float _next;
        static string _shownId, _answeredId;
        static GameObject _root;
        static RectTransform _yesRect, _noRect, _alwaysRect;
        static Image _yesImg, _noImg, _alwaysImg;

        static Color _yesBase, _noBase, _alwaysBase;      // button colours (from our own look)
        static GameWindow _gw;                             // window cloned from the game (null: our own look)

        public static void Frame()
        {
            if (_root != null) Clicks();
            if (Time.unscaledTime < _next) return;
            _next = Time.unscaledTime + 0.5f;
            Msg m = null;
            try
            {
                if (File.Exists(File_)) m = JsonSerializer.Deserialize<Msg>(File.ReadAllText(File_));
            }
            catch { m = null; }
            if (m == null || string.IsNullOrEmpty(m.id))
            {
                if (_root != null) { Hide(); Plugin.L.LogInfo("[Mods] aviso de mods cerrado desde el lanzador"); }
                return;
            }
            if (m.id == _shownId || m.id == _answeredId) return;
            Show(m);
        }

        static void Answer(bool accept, bool always = false)
        {
            try
            {
                File.WriteAllText(AnswerFile, JsonSerializer.Serialize(new { id = _shownId, accept, always }));
                Plugin.L.LogInfo("[Mods] mods del invitado " + (always ? "aceptados (siempre)" : accept ? "aceptados" : "rechazados") + " desde el juego");
            }
            catch (Exception e) { Plugin.L.LogWarning("[Mods] no pude guardar la respuesta: " + e.Message); }
            _answeredId = _shownId;
            Hide();
        }

        static void Clicks()
        {
            Vector2 mouse = Input.mousePosition;
            bool overYes = _yesRect != null && RectTransformUtility.RectangleContainsScreenPoint(_yesRect, mouse, null);
            bool overNo = _noRect != null && RectTransformUtility.RectangleContainsScreenPoint(_noRect, mouse, null);
            bool overAlways = _alwaysRect != null && RectTransformUtility.RectangleContainsScreenPoint(_alwaysRect, mouse, null);
            if (_gw != null) _gw.KeepTexts();       // with the game's window, its buttons provide the glow
            else
            {
                if (_yesImg != null) _yesImg.color = overYes ? Skin.Hover(_yesBase) : _yesBase;
                if (_noImg != null) _noImg.color = overNo ? Skin.Hover(_noBase) : _noBase;
                if (_alwaysImg != null) _alwaysImg.color = overAlways ? Skin.Hover(_alwaysBase) : _alwaysBase;
            }
            if (!Input.GetMouseButtonDown(0)) return;
            if (overYes) Answer(true);
            else if (overAlways) Answer(true, true);
            else if (overNo) Answer(false);
        }

        static void Hide()
        {
            if (_root != null) UnityEngine.Object.Destroy(_root);
            _root = null; _yesRect = _noRect = _alwaysRect = null; _yesImg = _noImg = _alwaysImg = null; _shownId = null;
            _gw = null;
        }

        internal static TMP_FontAsset GameFont()
        {
            try
            {
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<TMP_Text>()))
                {
                    var t = o.TryCast<TMP_Text>();
                    if (t != null && t.font != null && t.gameObject.activeInHierarchy) return t.font;
                }
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<TMP_FontAsset>()))
                {
                    var f = o.TryCast<TMP_FontAsset>();
                    if (f != null) return f;
                }
            }
            catch { }
            return null;
        }

        internal static RectTransform Box(string name, Transform parent, Vector2 anchorMin, Vector2 anchorMax, Vector2 pos, Vector2 size)
        {
            var go = new GameObject(name);
            var rt = go.AddComponent<RectTransform>();
            rt.SetParent(parent, false);
            rt.anchorMin = anchorMin; rt.anchorMax = anchorMax;
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.anchoredPosition = pos; rt.sizeDelta = size;
            return rt;
        }

        internal static TextMeshProUGUI Label(Transform parent, string text, TMP_FontAsset font, float size, Vector2 pos, Vector2 box)
        {
            var rt = Box("Text", parent, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), pos, box);
            var t = rt.gameObject.AddComponent<TextMeshProUGUI>();
            if (font != null) t.font = font;
            t.text = text ?? "";
            t.fontSize = size;
            t.enableAutoSizing = true; t.fontSizeMin = 14; t.fontSizeMax = size;
            t.enableWordWrapping = true;
            t.alignment = TextAlignmentOptions.Center;
            t.color = new Color(0.93f, 0.94f, 1f, 1f);
            t.raycastTarget = false;
            return t;
        }


        static void Show(Msg m)
        {
            Hide();
            try
            {
                var sk = Skin.Get();
                _root = new GameObject("CSR_ModOffer");
                UnityEngine.Object.DontDestroyOnLoad(_root);
                var canvas = _root.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvas.sortingOrder = 32000;
                var scaler = _root.AddComponent<CanvasScaler>();
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920, 1080);
                scaler.matchWidthOrHeight = 0.5f;
                _root.AddComponent<GraphicRaycaster>();     // blocks clicks to the game while it is open

                var dim = Box("Dim", _root.transform, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
                dim.gameObject.AddComponent<Image>().color = new Color(0f, 0f, 0f, 0.55f);

                _gw = GameWindow.Create(_root.transform);
                if (_gw != null)
                {
                    _gw.SetText(_gw.Title, m.title);
                    _gw.SetText(_gw.Body, m.body);
                    bool three = !string.IsNullOrEmpty(m.always);
                    int n = three ? 3 : 2;
                    _yesImg = _gw.AddBottomButton(m.yes, false, 0, n, GameWindow.Amber, out _yesRect, out _);
                    if (three) _alwaysImg = _gw.AddBottomButton(m.always, false, 1, n, null, out _alwaysRect, out _);
                    _noImg = _gw.AddBottomButton(m.no, false, n - 1, n, null, out _noRect, out _);
                    _shownId = m.id;
                    Plugin.L.LogInfo("[Mods] aviso de mods en el juego: " + m.title);
                    return;
                }
                var panel = sk.MakePanel(_root.transform, new Vector2(860, 440)).transform;
                sk.MakeText(panel, m.title, 38, new Vector2(0, 160), new Vector2(780, 60), true);
                sk.MakeText(panel, m.body, 26, new Vector2(0, 30), new Vector2(780, 180), false);
                var bs = new Vector2(236, 64);
                if (string.IsNullOrEmpty(m.always))
                {
                    _yesImg = sk.MakeButton(panel, m.yes, true, new Vector2(-140, -155), bs, 26, out _yesRect, out _);
                    _noImg = sk.MakeButton(panel, m.no, false, new Vector2(140, -155), bs, 26, out _noRect, out _);
                }
                else
                {
                    _yesImg = sk.MakeButton(panel, m.yes, true, new Vector2(-256, -155), bs, 26, out _yesRect, out _);
                    _alwaysImg = sk.MakeButton(panel, m.always, false, new Vector2(0, -155), bs, 26, out _alwaysRect, out _);
                    _noImg = sk.MakeButton(panel, m.no, false, new Vector2(256, -155), bs, 26, out _noRect, out _);
                }
                _yesBase = _yesImg.color; _noBase = _noImg.color;
                if (_alwaysImg != null) _alwaysBase = _alwaysImg.color;
                _shownId = m.id;
                Plugin.L.LogInfo("[Mods] aviso de mods en el juego: " + m.title);
            }
            catch (Exception e)
            {
                Plugin.L.LogWarning("[Mods] no pude ensenar el aviso de mods: " + e.Message);
                Hide();
                _answeredId = m.id;        // not retried in a loop: the launcher's notice stays
            }
        }
    }
}
