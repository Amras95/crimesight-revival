// CRIMESIGHT Revival - aviso de mods de un invitado dentro del juego.
//
// Cuando alguien entra en tu sala con stickers o avatares propios, el lanzador te pregunta si los
// descargas. Pero el anfitrion suele estar mirando el juego, no el lanzador, asi que el lanzador deja
// tambien el aviso en csr_live/offer.json y aqui se ensena encima del juego con dos botones. La
// respuesta va a csr_live/offer_answer.json y el lanzador la recoge (sirve contestar en cualquiera
// de los dos sitios). Si el lanzador quita el aviso (contestado alli), la ventana se cierra sola.
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

        static readonly Color Back = new Color(0.07f, 0.08f, 0.16f, 0.97f);
        static readonly Color Btn = new Color(0.20f, 0.22f, 0.42f, 1f);
        static readonly Color BtnHover = new Color(0.36f, 0.38f, 0.70f, 1f);
        static readonly Color BtnNo = new Color(0.16f, 0.17f, 0.26f, 1f);
        static readonly Color BtnNoHover = new Color(0.28f, 0.29f, 0.42f, 1f);

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
            if (_yesImg != null) _yesImg.color = overYes ? BtnHover : Btn;
            if (_noImg != null) _noImg.color = overNo ? BtnNoHover : BtnNo;
            if (_alwaysImg != null) _alwaysImg.color = overAlways ? BtnNoHover : BtnNo;
            if (!Input.GetMouseButtonDown(0)) return;
            if (overYes) Answer(true);
            else if (overAlways) Answer(true, true);
            else if (overNo) Answer(false);
        }

        static void Hide()
        {
            if (_root != null) UnityEngine.Object.Destroy(_root);
            _root = null; _yesRect = _noRect = _alwaysRect = null; _yesImg = _noImg = _alwaysImg = null; _shownId = null;
        }

        static TMP_FontAsset GameFont()
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

        static RectTransform Box(string name, Transform parent, Vector2 anchorMin, Vector2 anchorMax, Vector2 pos, Vector2 size)
        {
            var go = new GameObject(name);
            var rt = go.AddComponent<RectTransform>();
            rt.SetParent(parent, false);
            rt.anchorMin = anchorMin; rt.anchorMax = anchorMax;
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.anchoredPosition = pos; rt.sizeDelta = size;
            return rt;
        }

        static TextMeshProUGUI Label(Transform parent, string text, TMP_FontAsset font, float size, Vector2 pos, Vector2 box)
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

        static Image Button(Transform parent, string text, TMP_FontAsset font, Vector2 pos, Color c, out RectTransform rt)
        {
            rt = Box("Button", parent, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), pos, new Vector2(236, 64));
            var img = rt.gameObject.AddComponent<Image>();
            img.color = c;
            Label(rt, text, font, 26, Vector2.zero, new Vector2(216, 56));
            return img;
        }

        static void Show(Msg m)
        {
            Hide();
            try
            {
                var font = GameFont();
                _root = new GameObject("CSR_ModOffer");
                UnityEngine.Object.DontDestroyOnLoad(_root);
                var canvas = _root.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvas.sortingOrder = 32000;
                var scaler = _root.AddComponent<CanvasScaler>();
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920, 1080);
                scaler.matchWidthOrHeight = 0.5f;
                _root.AddComponent<GraphicRaycaster>();     // tapa los clics al juego mientras esta abierto

                var dim = Box("Dim", _root.transform, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
                dim.gameObject.AddComponent<Image>().color = new Color(0f, 0f, 0f, 0.55f);

                var panel = Box("Panel", _root.transform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(820, 420));
                panel.gameObject.AddComponent<Image>().color = Back;
                Label(panel, m.title, font, 38, new Vector2(0, 150), new Vector2(760, 60));
                Label(panel, m.body, font, 26, new Vector2(0, 25), new Vector2(760, 180));
                if (string.IsNullOrEmpty(m.always))
                {
                    _yesImg = Button(panel, m.yes, font, new Vector2(-140, -150), Btn, out _yesRect);
                    _noImg = Button(panel, m.no, font, new Vector2(140, -150), BtnNo, out _noRect);
                }
                else
                {
                    _yesImg = Button(panel, m.yes, font, new Vector2(-256, -150), Btn, out _yesRect);
                    _alwaysImg = Button(panel, m.always, font, new Vector2(0, -150), BtnNo, out _alwaysRect);
                    _noImg = Button(panel, m.no, font, new Vector2(256, -150), BtnNo, out _noRect);
                }
                _shownId = m.id;
                Plugin.L.LogInfo("[Mods] aviso de mods en el juego: " + m.title);
            }
            catch (Exception e)
            {
                Plugin.L.LogWarning("[Mods] no pude ensenar el aviso de mods: " + e.Message);
                Hide();
                _answeredId = m.id;        // no se reintenta en bucle: queda el aviso del lanzador
            }
        }
    }
}
