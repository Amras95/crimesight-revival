// CRIMESIGHT Revival - aspecto de las ventanas del plugin (aviso de mods, dificultad de la IA).
//
// Para que parezcan del juego, se toma el aspecto de una ventana suya: la de "Expulsar" de la sala, que
// siempre esta cargada en la sala aunque no se vea. De ella se copian el fondo de la ventana, los botones
// (el principal y el secundario), la fuente y los colores de los textos. Si no se encuentra (por ejemplo
// en mitad de una partida), se usa un aspecto oscuro propio.
using System;
using Il2CppInterop.Runtime;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace CrimeSightRevival.Mods
{
    sealed class Skin
    {
        public Sprite Panel, BtnMain, BtnSub;
        public Color PanelColor = new Color(0.07f, 0.08f, 0.16f, 0.97f);
        public Color BtnMainColor = new Color(0.36f, 0.38f, 0.70f, 1f);
        public Color BtnSubColor = new Color(0.16f, 0.17f, 0.26f, 1f);
        public Color Title = new Color(0.93f, 0.94f, 1f, 1f), Body = new Color(0.85f, 0.87f, 0.95f, 1f);
        public Color BtnMainText = Color.white, BtnSubText = new Color(0.93f, 0.94f, 1f, 1f);
        public TMP_FontAsset Font;
        public Material FontMat;
        public bool FromGame;

        static Skin _cached;

        public static Skin Get()
        {
            if (_cached != null && _cached.FromGame && _cached.Panel != null && _cached.BtnMain != null) return _cached;
            _cached = FromKickPopup() ?? new Skin { Font = ModOffer.GameFont() };
            return _cached;
        }

        static Skin FromKickPopup()
        {
            try
            {
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<OutGameRoomPopupKickConfirm>()))
                {
                    var pop = o?.TryCast<OutGameRoomPopupKickConfirm>();
                    if (pop == null || !pop.gameObject.scene.IsValid()) continue;
                    var sk = new Skin { FromGame = true };
                    var ok = pop.ConfirmButton?.image;
                    var back = pop.BackButton?.image;
                    if (ok == null || ok.sprite == null) continue;
                    sk.BtnMain = ok.sprite; sk.BtnMainColor = ok.color;
                    sk.BtnSub = back?.sprite ?? ok.sprite; sk.BtnSubColor = back != null ? back.color : ok.color;
                    if (pop.ConfirmButtonTMP != null) sk.BtnMainText = pop.ConfirmButtonTMP.color;
                    if (pop.BackButtonTMP != null) sk.BtnSubText = pop.BackButtonTMP.color;
                    var title = pop.TitleTMP;
                    if (title != null)
                    {
                        sk.Font = title.font; sk.FontMat = title.fontSharedMaterial; sk.Title = title.color;
                    }
                    if (pop.MainTMP != null) sk.Body = pop.MainTMP.color;
                    // el fondo: la imagen mas grande de la ventana que no sea un boton
                    var root = pop.PosNull != null ? pop.PosNull.transform : pop.transform;
                    float best = 0;
                    foreach (var c in root.GetComponentsInChildren(Il2CppType.Of<Image>(), true))
                    {
                        var img = c.TryCast<Image>();
                        if (img == null || img.sprite == null || img.Pointer == ok.Pointer || (back != null && img.Pointer == back.Pointer))
                            continue;
                        var r = img.rectTransform.rect;
                        float area = Math.Abs(r.width * r.height);
                        if (area > best) { best = area; sk.Panel = img.sprite; sk.PanelColor = img.color; }
                    }
                    if (sk.Panel == null) continue;
                    if (sk.Font == null) sk.Font = ModOffer.GameFont();
                    Plugin.L.LogInfo("[Ventanas] aspecto del juego: fondo " + sk.Panel.name + ", boton " + sk.BtnMain.name);
                    return sk;
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Ventanas] no pude copiar el aspecto del juego: " + e.Message); }
            return null;
        }

        static void Fit(Image img, Sprite sp)
        {
            if (sp == null) return;
            img.sprite = sp;
            img.type = sp.border.sqrMagnitude > 0 ? Image.Type.Sliced : Image.Type.Simple;
            img.preserveAspect = false;
        }

        public Image MakePanel(Transform parent, Vector2 size)
        {
            var rt = ModOffer.Box("Panel", parent, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, size);
            var img = rt.gameObject.AddComponent<Image>();
            Fit(img, Panel);
            img.color = PanelColor;
            return img;
        }

        public TextMeshProUGUI MakeText(Transform parent, string text, float size, Vector2 pos, Vector2 box, bool title)
        {
            var t = ModOffer.Label(parent, text, Font, size, pos, box);
            if (FontMat != null) t.fontSharedMaterial = FontMat;
            t.color = title ? Title : Body;
            return t;
        }

        public Image MakeButton(Transform parent, string text, bool main, Vector2 pos, Vector2 size, float fontSize,
                                out RectTransform rt, out TextMeshProUGUI label)
        {
            rt = ModOffer.Box("Button", parent, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), pos, size);
            var img = rt.gameObject.AddComponent<Image>();
            Fit(img, main ? BtnMain : BtnSub);
            img.color = main ? BtnMainColor : BtnSubColor;
            label = ModOffer.Label(rt, text, Font, fontSize, Vector2.zero, size - new Vector2(16, 8));
            if (FontMat != null) label.fontSharedMaterial = FontMat;
            label.color = main ? BtnMainText : BtnSubText;
            return img;
        }

        /// <summary>Pone el boton en estilo principal o secundario (p. ej. la dificultad elegida).</summary>
        public void Style(Image img, TextMeshProUGUI label, bool main)
        {
            if (img == null) return;
            Fit(img, main ? BtnMain : BtnSub);
            img.color = main ? BtnMainColor : BtnSubColor;
            if (label != null) label.color = main ? BtnMainText : BtnSubText;
        }

        public static Color Hover(Color c) => new Color(Mathf.Lerp(c.r, 1f, 0.22f), Mathf.Lerp(c.g, 1f, 0.22f),
                                                        Mathf.Lerp(c.b, 1f, 0.22f), c.a);
    }
}

namespace CrimeSightRevival.Mods
{
    /// <summary>
    /// Una ventana de verdad del juego: se clona la de "Expulsar" de la sala (banda verde con el titulo,
    /// papel, recuadro con borde y botones en chevron) y se le cambian textos y botones. Los botones nuevos
    /// son copias de los del juego, asi que tambien se iluminan igual al pasar el raton. Si la ventana del
    /// juego no esta (p. ej. en mitad de una partida), Create devuelve null y se usa el aspecto propio.
    /// </summary>
    sealed class GameWindow
    {
        public RectTransform Root, BodyBox, ButtonRow;
        public TextMeshProUGUI Title, Body;
        public Vector2 BtnSize;
        public float BtnY, RowCenterX;
        GameObject _light, _red;
        readonly System.Collections.Generic.List<(TextMeshProUGUI t, string s)> _texts = new();

        public static readonly Color Amber = new Color(1f, 0.70f, 0.12f, 1f);   // como "Iniciar partida"

        static Vector2 CenterIn(RectTransform parent, RectTransform t)
        {
            var world = t.TransformPoint(t.rect.center);
            Vector2 local = parent.InverseTransformPoint(world);
            return local - parent.rect.center;
        }

        static string Rel(Transform root, Transform t)
        {
            var parts = new System.Collections.Generic.List<string>();
            for (var x = t; x != null && x != root; x = x.parent) parts.Insert(0, x.name);
            return string.Join("/", parts);
        }

        /// <summary>
        /// En el juego la ventana se coloca respecto a los contenedores que tiene encima y con la escala de
        /// su lienzo. Aqui se copian: la misma escala (CanvasScaler) y una cadena de contenedores vacios con
        /// los mismos anclajes, tamanos y posiciones. Dentro de eso, la copia queda donde la original.
        /// </summary>
        static Transform Mirror(Transform src, Transform ourCanvas)
        {
            var chain = new System.Collections.Generic.List<RectTransform>();
            CanvasScaler gameScaler = null;
            for (var t = src.parent; t != null; t = t.parent)
            {
                var sc = t.GetComponent<CanvasScaler>();
                if (sc != null) { gameScaler = sc; break; }
                var rt = t.GetComponent<RectTransform>();
                if (rt != null) chain.Insert(0, rt);
            }
            var ours = ourCanvas.GetComponent<CanvasScaler>();
            if (gameScaler != null && ours != null)
            {
                ours.uiScaleMode = gameScaler.uiScaleMode;
                ours.referenceResolution = gameScaler.referenceResolution;
                ours.screenMatchMode = gameScaler.screenMatchMode;
                ours.matchWidthOrHeight = gameScaler.matchWidthOrHeight;
                ours.scaleFactor = gameScaler.scaleFactor;
            }
            Transform at = ourCanvas;
            foreach (var rt in chain)
            {
                var go = new GameObject("CSR_" + rt.name);
                var copy = go.AddComponent<RectTransform>();
                copy.SetParent(at, false);
                copy.anchorMin = rt.anchorMin; copy.anchorMax = rt.anchorMax; copy.pivot = rt.pivot;
                copy.sizeDelta = rt.sizeDelta; copy.anchoredPosition = rt.anchoredPosition;
                copy.localScale = rt.localScale; copy.localRotation = rt.localRotation;
                at = copy;
            }
            Plugin.L.LogInfo($"[Ventanas] {chain.Count} contenedores copiados; escala del juego " +
                             (gameScaler != null ? $"{gameScaler.referenceResolution.x:0}x{gameScaler.referenceResolution.y:0}" : "no encontrada"));
            return at;
        }

        /// <summary>
        /// La ventana original entra con una animacion (empieza desplazada y se desliza); la copia puede
        /// quedar en el punto de partida. Se mide donde esta su marco (la imagen mas grande) y se lleva al
        /// centro de la pantalla.
        /// </summary>
        static void Center(GameObject go, Transform canvas)
        {
            try
            {
                Canvas.ForceUpdateCanvases();
                RectTransform frame = null;
                float best = 0;
                foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<Image>(), false))
                {
                    var img = c.TryCast<Image>();
                    if (img == null) continue;
                    var r = img.rectTransform.rect;
                    float area = Math.Abs(r.width * r.height);
                    if (area > best) { best = area; frame = img.rectTransform; }
                }
                var crt = canvas.GetComponent<RectTransform>();
                if (frame == null || crt == null) return;
                var a = new Vector3[4]; var b = new Vector3[4];
                frame.GetWorldCorners(a); crt.GetWorldCorners(b);
                Vector3 mid = (a[0] + a[2]) / 2f, screen = (b[0] + b[2]) / 2f;
                var delta = screen - mid;
                delta.z = 0;
                go.transform.position += delta;
                Plugin.L.LogInfo($"[Ventanas] ventana centrada (movida {delta.x:0},{delta.y:0}; marco {frame.rect.width:0}x{frame.rect.height:0})");
            }
            catch (Exception e) { Plugin.L.LogWarning("[Ventanas] no pude centrar la ventana: " + e.Message); }
        }

        public static GameWindow Create(Transform parent)
        {
            try
            {
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<OutGameRoomPopupKickConfirm>()))
                {
                    var pop = o?.TryCast<OutGameRoomPopupKickConfirm>();
                    if (pop == null || !pop.gameObject.scene.IsValid() || pop.TitleTMP == null || pop.MainTMP == null
                        || pop.ConfirmButton == null || pop.BackButton == null) continue;
                    var src = pop.PosNull != null ? pop.PosNull : pop.gameObject;
                    string pTitle = Rel(src.transform, pop.TitleTMP.transform), pMain = Rel(src.transform, pop.MainTMP.transform);
                    string pOk = Rel(src.transform, pop.ConfirmButton.transform), pBack = Rel(src.transform, pop.BackButton.transform);
                    var holder = Mirror(src.transform, parent);
                    var go = UnityEngine.Object.Instantiate(src, holder, false);
                    go.name = "CSR_GameWindow";
                    go.SetActive(true);
                    go.transform.localScale = Vector3.one;          // por si la animacion de salida la dejo encogida
                    var w = new GameWindow { Root = go.GetComponent<RectTransform>() };
                    foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<OutGameRoomPopupKickConfirm>(), true))
                        UnityEngine.Object.Destroy(c);
                    // la copia queda quieta: sin las animaciones de entrada/salida de la ventana original
                    foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<Behaviour>(), true))
                    {
                        var bh = c.TryCast<Behaviour>();
                        string tn = bh != null ? bh.GetIl2CppType().Name : "";
                        if (tn == "SimpleAnimation" || tn == "Animator" || tn == "Animation") bh.enabled = false;
                    }
                    foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<CanvasGroup>(), true))
                    {
                        var cg = c.TryCast<CanvasGroup>();
                        cg.alpha = 1f; cg.interactable = true; cg.blocksRaycasts = true;
                    }
                    w.Title = go.transform.Find(pTitle)?.GetComponent<TextMeshProUGUI>();
                    w.Body = go.transform.Find(pMain)?.GetComponent<TextMeshProUGUI>();
                    w._red = go.transform.Find(pOk)?.gameObject;
                    w._light = go.transform.Find(pBack)?.gameObject;
                    if (w.Title == null || w.Body == null || w._red == null || w._light == null)
                    {
                        UnityEngine.Object.Destroy(go);
                        continue;
                    }
                    var lrt = w._light.GetComponent<RectTransform>();
                    var rrt = w._red.GetComponent<RectTransform>();
                    w.BtnSize = lrt.rect.size;
                    w.ButtonRow = lrt.parent.GetComponent<RectTransform>();
                    // Donde estan de verdad los botones del juego, medido desde el centro de su fila (que es
                    // como se colocan los nuevos): su anchoredPosition va respecto a sus propios anclajes
                    Canvas.ForceUpdateCanvases();
                    Vector2 cl = CenterIn(w.ButtonRow, lrt), cr = CenterIn(w.ButtonRow, rrt);
                    w.BtnY = (cl.y + cr.y) / 2f;
                    w.RowCenterX = (cl.x + cr.x) / 2f;
                    w.BodyBox = w.Body.rectTransform.parent.GetComponent<RectTransform>();
                    w._light.SetActive(false); w._red.SetActive(false);
                    Center(go, parent);
                    Plugin.L.LogInfo($"[Ventanas] ventana del juego clonada: boton {w.BtnSize.x:0}x{w.BtnSize.y:0}, " +
                                     $"recuadro {w.BodyBox.rect.width:0}x{w.BodyBox.rect.height:0}");
                    return w;
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Ventanas] no pude clonar la ventana del juego: " + e.Message); }
            return null;
        }

        /// <summary>The window's parts (title, framed box, buttons) together, in the window's space.</summary>
        public Rect Bounds()
        {
            Canvas.ForceUpdateCanvases();
            Rect r = RectIn(Root, Title.rectTransform), box = RectIn(Root, BodyBox), btn = RectIn(Root, _light.GetComponent<RectTransform>());
            return Rect.MinMaxRect(Math.Min(r.xMin, Math.Min(box.xMin, btn.xMin)), Math.Min(r.yMin, Math.Min(box.yMin, btn.yMin)),
                                   Math.Max(r.xMax, Math.Max(box.xMax, btn.xMax)), Math.Max(r.yMax, Math.Max(box.yMax, btn.yMax)));
        }

        /// <summary>The whole screen, in the window's space.</summary>
        public Rect ScreenRect()
        {
            var canvas = Root.GetComponentInParent<Canvas>()?.rootCanvas;
            var crt = canvas != null ? canvas.GetComponent<RectTransform>() : null;
            return crt != null ? RectIn(Root, crt) : new Rect(-960, -540, 1920, 1080);
        }

        /// <summary>
        /// Resizes the window so its framed box gets the given size (in the window's space), keeping the borders, the
        /// title band and the buttons the same size: what sits near an edge moves with that edge, what is in the
        /// middle stretches. Then the button row is measured again.
        /// </summary>
        public void Resize(Vector2 boxSize)
        {
            try
            {
                foreach (var c in Root.GetComponentsInChildren(Il2CppType.Of<Behaviour>(), true))
                {
                    var bh = c.TryCast<Behaviour>();
                    string tn = bh != null ? bh.GetIl2CppType().Name : "";
                    if (tn.EndsWith("LayoutGroup") || tn == "ContentSizeFitter" || tn == "AspectRatioFitter") bh.enabled = false;
                }
                Rect F = Bounds(), B = RectIn(Root, BodyBox);
                float dw = Math.Max(boxSize.x - B.width, -0.4f * F.width), dh = Math.Max(boxSize.y - B.height, -0.4f * F.height);
                Plugin.L.LogInfo($"[Windows] window {F.width:0}x{F.height:0}, box {B.width:0}x{B.height:0} -> box {B.width + dw:0}x{B.height + dh:0}");
                if (Math.Abs(dw) < 1f && Math.Abs(dh) < 1f) return;
                float mx = F.width * 0.25f, my = F.height * 0.25f;
                float Map(float v, float lo, float hi, float m, float d)
                {
                    if (v <= lo + m) return v - d / 2f;
                    if (v >= hi - m) return v + d / 2f;
                    float t = (v - (lo + m)) / (hi - lo - 2f * m);
                    return (lo + m - d / 2f) + t * (hi - lo - 2f * m + d);
                }
                // where everything should end up (measured before anything moves), then placed parents first
                var all = Root.GetComponentsInChildren<RectTransform>(true);
                var want = new System.Collections.Generic.List<(RectTransform rt, Rect r)>();
                foreach (var rt in all)
                {
                    if (rt == null || rt.Pointer == Root.Pointer) continue;
                    var r = RectIn(Root, rt);
                    float x0 = Map(r.xMin, F.xMin, F.xMax, mx, dw), x1 = Map(r.xMax, F.xMin, F.xMax, mx, dw);
                    float y0 = Map(r.yMin, F.yMin, F.yMax, my, dh), y1 = Map(r.yMax, F.yMin, F.yMax, my, dh);
                    want.Add((rt, Rect.MinMaxRect(x0, y0, x1, y1)));
                }
                foreach (var (rt, r) in want)
                {
                    var p = rt.parent != null ? rt.parent.GetComponent<RectTransform>() : null;
                    if (p == null) continue;
                    Vector3 a = p.InverseTransformPoint(Root.TransformPoint(new Vector3(r.xMin, r.yMin, 0f)));
                    Vector3 b = p.InverseTransformPoint(Root.TransformPoint(new Vector3(r.xMax, r.yMax, 0f)));
                    float w = Math.Abs(b.x - a.x), h = Math.Abs(b.y - a.y);
                    float sx = Math.Abs(rt.localScale.x) > 0.0001f ? Math.Abs(rt.localScale.x) : 1f;
                    float sy = Math.Abs(rt.localScale.y) > 0.0001f ? Math.Abs(rt.localScale.y) : 1f;
                    var pivotAt = new Vector2(Math.Min(a.x, b.x) + rt.pivot.x * w, Math.Min(a.y, b.y) + rt.pivot.y * h);
                    rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
                    rt.sizeDelta = new Vector2(w / sx, h / sy);
                    rt.anchoredPosition = pivotAt - p.rect.center;
                }
                Canvas.ForceUpdateCanvases();
                var lrt = _light.GetComponent<RectTransform>();
                var rrt = _red.GetComponent<RectTransform>();
                BtnSize = lrt.rect.size;
                Vector2 cl = CenterIn(ButtonRow, lrt), cr = CenterIn(ButtonRow, rrt);
                BtnY = (cl.y + cr.y) / 2f;
                RowCenterX = (cl.x + cr.x) / 2f;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Windows] could not resize the game window: " + e.Message); }
        }

        /// <summary>A rect's corners in another rect's space.</summary>
        internal static Rect RectIn(RectTransform space, RectTransform t)
        {
            // (GetWorldCorners can't be used: under Il2Cpp the array it fills is a copy, so it comes back empty)
            var r = t.rect;
            Vector3 a = space.InverseTransformPoint(t.TransformPoint(new Vector3(r.xMin, r.yMin, 0f)));
            Vector3 b = space.InverseTransformPoint(t.TransformPoint(new Vector3(r.xMax, r.yMax, 0f)));
            return Rect.MinMaxRect(Math.Min(a.x, b.x), Math.Min(a.y, b.y), Math.Max(a.x, b.x), Math.Max(a.y, b.y));
        }

        public void SetText(TextMeshProUGUI t, string s)
        {
            if (t == null) return;
            t.text = s;
            _texts.RemoveAll(x => x.t == t);
            _texts.Add((t, s));
        }

        /// <summary>Por si algun componente del juego vuelve a poner su texto: se repone cada fotograma.</summary>
        public void KeepTexts()
        {
            foreach (var (t, s) in _texts)
                if (t != null && t.text != s) t.text = s;
        }

        /// <summary>Un boton del juego (claro o rojo), opcionalmente tenido (ambar = el principal).</summary>
        public Image AddButton(string text, bool red, Transform parent, Vector2 pos, Vector2 size, Color? tint,
                               out RectTransform rt, out TextMeshProUGUI label)
        {
            var go = UnityEngine.Object.Instantiate(red ? _red : _light, parent, false);
            go.SetActive(true);
            rt = go.GetComponent<RectTransform>();
            rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0.5f, 0.5f);
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            var b = go.GetComponent<Button>();
            if (b != null) b.onClick = new Button.ButtonClickedEvent();   // sin acciones del juego
            var img = b != null && b.image != null ? b.image : go.GetComponent<Image>();
            if (img != null && tint.HasValue) img.color = tint.Value;
            label = go.GetComponentInChildren<TextMeshProUGUI>(true);
            if (label != null)
            {
                label.enableAutoSizing = true;
                label.fontSizeMax = label.fontSize;
                label.fontSizeMin = Math.Min(14f, label.fontSize);
                label.enableWordWrapping = false;
                SetText(label, text);
            }
            return img;
        }

        /// <summary>Fila de botones de abajo, centrada donde estaban los del juego.</summary>
        public Image AddBottomButton(string text, bool red, int index, int count, Color? tint,
                                     out RectTransform rt, out TextMeshProUGUI label)
        {
            float w = BtnSize.x * (count >= 3 ? 0.9f : 1f), gap = 14f;
            float x = RowCenterX + (index - (count - 1) / 2f) * (w + gap);
            return AddButton(text, red, ButtonRow, new Vector2(x, BtnY), new Vector2(w, BtnSize.y), tint, out rt, out label);
        }
    }
}
