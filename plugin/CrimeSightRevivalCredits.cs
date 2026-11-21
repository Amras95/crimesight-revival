// CRIMESIGHT Revival - boton "Creditos Revival" en la ventana de Opciones.
//
// Debajo de "Creditos del personal" se anade una copia de ese boton que abre una ventana con los creditos de
// Revival. La ventana es una copia de la propia ventana de Opciones (mismo marco, titulo y boton de volver),
// con los botones escondidos y el texto de los creditos en su sitio. Los nombres son enlaces: al pulsarlos
// se abren en el navegador. Mientras esta abierta, la ventana de Opciones de debajo queda en pausa.
using System;
using System.Collections.Generic;
using HarmonyLib;
using Il2CppInterop.Runtime;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace CrimeSightRevival.Mods
{
    static class RevivalCredits
    {
        // ConfigSystem.LangType: ja, en, fr, it, de, es, pt, ru, ko, zh-CN, zh-TW
        static readonly string[] ButtonLabel = { "Revivalクレジット", "Revival Credits", "Crédits Revival", "Crediti Revival",
            "Revival-Credits", "Créditos de Revival", "Créditos do Revival", "Авторы Revival", "Revival 크레딧", "Revival 制作人员", "Revival 製作人員" };
        static readonly string[] RevivalBy = { "Revival 制作:", "Revival by", "Revival par", "Revival di", "Revival von",
            "Revival por", "Revival por", "Revival от", "Revival 제작:", "Revival 作者", "Revival 作者" };
        static readonly string[] ContributionsBy = { "協力:", "Contributions by", "Contributions de", "Contributi di", "Beiträge von",
            "Contribuciones de", "Contribuições de", "При участии", "기여:", "贡献者", "貢獻者" };
        static readonly string[] JoinLabel = { "コミュニティサーバーに参加", "Join our community server",
            "Rejoindre notre serveur communautaire", "Unisciti al nostro server della community", "Tritt unserem Community-Server bei",
            "Únete a nuestro servidor de la comunidad", "Entre no nosso servidor da comunidade", "Присоединяйтесь к нашему серверу сообщества",
            "커뮤니티 서버 참여하기", "加入我们的社区服务器", "加入我們的社群伺服器" };
        const string Discord = "https://discord.gg/uqndsJnR3r";

        // enlaces de los nombres (id del <link> -> direccion)
        static readonly Dictionary<string, string> Links = new()
        {
            ["amras_github"] = "https://github.com/Amras95",
            ["amras_x"] = "https://x.com/AmrasMithandir",
            ["amras_kofi"] = "https://ko-fi.com/amrasmithandir95",
            ["ashen_github"] = "https://github.com/AshenAF92",
        };
        const string LinkColor = "#9fb3ff";

        static string Body(int lang) =>
            $"<size=125%>CRIMESIGHT Revival</size>\n\n" +
            $"{RevivalBy[lang]}\n" +
            $"<size=115%>{Link("amras_github", "Amras95")}</size>\n" +
            $"<size=85%>{Link("amras_x", "X: @AmrasMithandir")}   ·   {Link("amras_kofi", "Ko-fi")}</size>\n\n" +
            $"{ContributionsBy[lang]}\n" +
            $"<size=115%>{Link("ashen_github", "Ashen")}</size>";

        static string Link(string id, string text) => $"<link=\"{id}\"><color={LinkColor}><u>{text}</u></color></link>";

        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.Method(typeof(OutGameOptionMainPopup), "Start");
                if (m == null) { Plugin.L.LogWarning("[Creditos] no encuentro la ventana de Opciones"); return; }
                h.Patch(m, postfix: new HarmonyMethod(typeof(RevivalCredits).GetMethod(nameof(AfterStart),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Creditos] " + e.Message); }
        }

        static int Lang()
        {
            try { return Math.Max(0, Math.Min(10, (int)TextManager.Instance.GetLangType())); } catch { return 1; }
        }

        // ------------------------------------------------------------ el boton
        static OutGameOptionMainPopup _popup;
        static GameObject _button;
        static UnityEngine.Events.UnityAction _onOpen, _onClose;

        static void AfterStart(OutGameOptionMainPopup __instance)
        {
            try
            {
                _popup = __instance;
                var credit = __instance.CreditButton;
                var quit = __instance.QuitButton;
                if (credit == null) return;
                var list = Common(credit.transform, quit != null ? quit.transform : credit.transform.parent);
                var item = ItemOf(credit.transform, list);
                var copy = UnityEngine.Object.Instantiate(item.gameObject, list, false);
                copy.name = "CSR_RevivalCreditsButton";
                copy.transform.SetSiblingIndex(item.GetSiblingIndex() + 1);
                _button = copy;
                if (list.GetComponent<LayoutGroup>() == null) MakeRoom(list, item, copy.transform, quit);
                else Grow(list, item);

                var b = Same(copy.transform, item, credit.transform)?.GetComponent<Button>() ?? copy.GetComponentInChildren<Button>(true);
                if (b != null)
                {
                    b.onClick = new Button.ButtonClickedEvent();
                    _onOpen ??= DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction>(new Action(Open));
                    b.onClick.AddListener(_onOpen);
                    try { UiBaseManager.SetBackButtonColor(b); UIScriptingHelper.SetMouseOverSoundEvent(b); } catch { }
                }
                var tmp = __instance.CreditButtonTMP;
                var lt = tmp != null ? Same(copy.transform, item, tmp.transform)?.GetComponent<TextMeshProUGUI>() : null;
                (lt ?? copy.GetComponentInChildren<TextMeshProUGUI>(true)).text = ButtonLabel[Lang()];
            }
            catch (Exception e) { Plugin.L.LogWarning("[Creditos] boton: " + e); }
        }

        /// <summary>Si los botones no estan en una lista automatica, el nuevo va un hueco por debajo de
        /// "Creditos del personal" y los que estaban debajo bajan ese mismo hueco.</summary>
        static void MakeRoom(Transform list, Transform item, Transform copy, Button quit)
        {
            var it = item.TryCast<RectTransform>();
            var below = quit != null ? ItemOf(quit.transform, list)?.TryCast<RectTransform>() : null;
            if (it == null || below == null || below == item) return;
            var step = below.anchoredPosition - it.anchoredPosition;          // el hueco entre dos botones
            var cr = copy.TryCast<RectTransform>();
            if (cr != null) cr.anchoredPosition = it.anchoredPosition + step;
            for (int i = 0; i < list.childCount; i++)
            {
                var c = list.GetChild(i).TryCast<RectTransform>();
                if (c == null || c.Pointer == copy.Pointer || c.Pointer == item.Pointer) continue;
                if (Vector2.Dot(c.anchoredPosition - it.anchoredPosition, step) > 0.01f) c.anchoredPosition += step;
            }
        }

        /// <summary>Hace sitio a un boton mas: crecen la lista (TextArea), el marco (PopupBg) y la ventana
        /// (set_popup); las dos que tienen Mask recortan lo que se sale. Todo esta centrado, asi que crece
        /// igual por arriba y por abajo y nada se descoloca.</summary>
        static void Grow(Transform list, Transform item)
        {
            var it = item.TryCast<RectTransform>();
            var vlg = list.GetComponent<VerticalLayoutGroup>();
            var popup = list.parent;
            if (it == null || popup == null) return;
            _step = it.sizeDelta.y + (vlg != null ? vlg.spacing : 0f);
            _grown.Clear();
            Add(list);
            Add(popup.Find("PopupBg"));
            Add(popup);
        }

        // la animacion de abrir Opciones les vuelve a poner su alto: despues de ella se les suma otra vez
        static readonly List<(RectTransform r, float set)> _grown = new();
        static float _step;

        static void Add(Transform t)
        {
            var r = t != null ? t.TryCast<RectTransform>() : null;
            if (r == null) return;
            if (Fits(t)) t.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.Unconstrained;
            r.sizeDelta += new Vector2(0f, _step);
            _grown.Add((r, r.sizeDelta.y));
        }

        /// <summary>Lo alto que hemos dejado una pieza de Opciones (o su alto, si no es de las que crecen).</summary>
        static float Height(RectTransform r)
        {
            foreach (var g in _grown) if (g.r != null && g.r.Pointer == r.Pointer) return g.set;
            return r.sizeDelta.y;
        }

        /// <summary>Cada fotograma, despues de las animaciones: si algo le ha cambiado el alto a una de las
        /// piezas que crecieron, se le vuelve a sumar el boton nuevo.</summary>
        public static void Late()
        {
            for (int i = 0; i < _grown.Count; i++)
            {
                var (r, set) = _grown[i];
                if (r == null || !r.gameObject.activeInHierarchy) continue;
                var s = r.sizeDelta;
                if (Mathf.Abs(s.y - set) < 0.01f) continue;
                _grown[i] = (r, s.y + _step);
                r.sizeDelta = new Vector2(s.x, s.y + _step);
            }
        }

        static bool Fits(Transform t)
        {
            var f = t.GetComponent<ContentSizeFitter>();
            return f != null && f.enabled && f.verticalFit != ContentSizeFitter.FitMode.Unconstrained;
        }

        // ------------------------------------------------------------ la ventana
        static GameObject _window;
        static TextMeshProUGUI _body, _join;
        static UnityEngine.Events.UnityAction _onJoin;
        internal static Button CloseButton;
        internal static Button JoinButton;
        internal static bool IsOpen => _window != null && _window.activeInHierarchy;

        static void Open()
        {
            try
            {
                var p = _popup;
                if (p == null || IsOpen) return;
                try { AudioManager.PlayOutGameNormalClick(); } catch { }
                if (_window == null) Build(p);
                if (_window == null) return;
                _body.text = Body(Lang());
                if (_join != null) _join.text = JoinLabel[Lang()];
                _window.SetActive(true);
                _window.transform.SetAsLastSibling();
                foreach (var cg in _window.GetComponentsInChildren<CanvasGroup>(true))
                {
                    cg.alpha = 1f; cg.interactable = true; cg.blocksRaycasts = true;
                }
                try { p.SetPause(); } catch { }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Creditos] abrir: " + e); }
        }

        static void Close()
        {
            try
            {
                if (_window == null) return;
                try { AudioManager.PlayOutGameCancelReturn(); } catch { }
                _window.SetActive(false);
                try { _popup?.ResetPause(); } catch { }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Creditos] cerrar: " + e); }
        }

        /// <summary>Copia la ventana de Opciones sin su codigo: se copia dentro de un objeto apagado para
        /// que el del juego no llegue a arrancar en la copia, y se le quita antes de encenderla.</summary>
        static void Build(OutGameOptionMainPopup p)
        {
            var src = p.gameObject.transform;
            var holder = new GameObject("CSR_CreditsHolder");
            holder.SetActive(false);
            var win = UnityEngine.Object.Instantiate(p.gameObject, holder.transform, false);
            win.name = "CSR_RevivalCredits";
            var code = win.GetComponent<OutGameOptionMainPopup>();
            if (code != null) UnityEngine.Object.DestroyImmediate(code);
            // sin registrarse en el juego como ventana suya (la esconderia o se haria pasar por Opciones) y sin
            // sus animaciones de entrada y salida (la dejaban invisible la primera vez): se queda como se copio
            var reg = win.GetComponent<OutGameManagerPopupRegist>();
            if (reg != null) UnityEngine.Object.DestroyImmediate(reg);
            var prio = win.GetComponent<UiPriority>();
            if (prio != null) UnityEngine.Object.DestroyImmediate(prio);
            foreach (var an in win.GetComponentsInChildren<Animator>(true)) an.enabled = false;
            foreach (var sa in win.GetComponentsInChildren<SimpleAnimation>(true)) sa.enabled = false;
            foreach (var (gr, _) in _grown)                                       // tan alta como Opciones
            {
                var w = gr != null ? Same(win.transform, src, gr)?.TryCast<RectTransform>() : null;
                if (w != null) w.sizeDelta = new Vector2(w.sizeDelta.x, Height(gr));
            }
            var canvas = win.GetComponent<Canvas>();
            var ocanvas = p.GetComponent<Canvas>();
            if (canvas != null && ocanvas != null) canvas.sortingOrder = ocanvas.sortingOrder + 1;     // encima de Opciones

            var title = Same(win.transform, src, p.TitleTMP != null ? p.TitleTMP.transform : null)?.GetComponent<TextMeshProUGUI>();
            if (title != null) title.text = ButtonLabel[Lang()];
            var back = Same(win.transform, src, p.BackButton != null ? p.BackButton.transform : null)?.GetComponent<Button>();
            CloseButton = back;
            if (back != null)
            {
                back.onClick = new Button.ButtonClickedEvent();
                _onClose ??= DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction>(new Action(Close));
                back.onClick.AddListener(_onClose);
                try { UiBaseManager.SetBackButtonColor(back); UIScriptingHelper.SetMouseOverSoundEvent(back); } catch { }
            }

            // los botones de Opciones (y el nuestro) se esconden; el texto ocupa su sitio
            var credit = p.CreditButton.transform;
            var list = Common(credit, p.QuitButton != null ? p.QuitButton.transform : credit.parent);
            var wlist = Same(win.transform, src, list);
            var backItem = back != null && wlist != null && back.transform.IsChildOf(wlist) ? ItemOf(back.transform, wlist) : null;
            Vector3 min = new(float.MaxValue, float.MaxValue), max = new(float.MinValue, float.MinValue);
            var corners = new Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppStructArray<Vector3>(4);
            if (wlist != null)
                for (int i = 0; i < wlist.childCount; i++)
                {
                    var c = wlist.GetChild(i);
                    if ((backItem != null && c.Pointer == backItem.Pointer) || c.GetComponentInChildren<Button>(true) == null) continue;
                    var rt = c.TryCast<RectTransform>();
                    if (rt != null)
                    {
                        rt.GetWorldCorners(corners);
                        for (int k = 0; k < 4; k++) { min = Vector3.Min(min, corners[k]); max = Vector3.Max(max, corners[k]); }
                    }
                    c.gameObject.SetActive(false);
                }

            // el boton del servidor de Discord: la copia del nuestro, donde estaba Salir
            var quitItem = p.QuitButton != null && wlist != null ? Same(win.transform, src, ItemOf(p.QuitButton.transform, list)) : null;
            var joinItem = _button != null && quitItem != null ? Same(win.transform, src, _button.transform) : null;
            if (joinItem != null)
            {
                joinItem.name = "CSR_JoinDiscordButton";
                var le = joinItem.GetComponent<LayoutElement>();
                if (le == null) le = joinItem.gameObject.AddComponent<LayoutElement>();
                le.ignoreLayout = true;                                           // fuera de la lista: va donde estaba Salir
                var jr = joinItem.TryCast<RectTransform>(); var qr = quitItem.TryCast<RectTransform>();
                if (jr != null && qr != null) jr.anchoredPosition = qr.anchoredPosition;
                var jb = joinItem.GetComponentInChildren<Button>(true);
                JoinButton = jb;
                if (jb != null)
                {
                    jb.onClick = new Button.ButtonClickedEvent();
                    _onJoin ??= DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction>(new Action(JoinDiscord));
                    jb.onClick.AddListener(_onJoin);
                }
                _join = joinItem.GetComponentInChildren<TextMeshProUGUI>(true);
                if (_join != null)
                {
                    _join.enableAutoSizing = true;                                // los idiomas con el texto mas largo
                    _join.fontSizeMax = _join.fontSize; _join.fontSizeMin = _join.fontSize * 0.6f;
                    _join.enableWordWrapping = false;
                }
                joinItem.gameObject.SetActive(true);
            }

            var go = new GameObject("CSR_CreditsBody");
            var parent = wlist ?? win.transform;
            go.transform.SetParent(parent, false);
            var r = go.AddComponent<RectTransform>();
            go.AddComponent<LayoutElement>().ignoreLayout = true;
            r.anchorMin = r.anchorMax = r.pivot = new Vector2(0.5f, 0.5f);
            if (min.x < max.x)
            {
                var a = parent.InverseTransformPoint(min); var bb = parent.InverseTransformPoint(max);
                if (joinItem != null && joinItem.parent.Pointer == parent.Pointer)              // el texto, por encima del boton
                    a.y = joinItem.localPosition.y + (_step > 0f ? _step : 83f) * 0.5f;
                r.localPosition = (a + bb) / 2f;
                r.sizeDelta = new Vector2(Mathf.Abs(bb.x - a.x), Mathf.Abs(bb.y - a.y));
            }
            else r.sizeDelta = new Vector2(600, 400);
            _body = go.AddComponent<TextMeshProUGUI>();
            var font = title != null ? title : p.CreditButtonTMP;
            if (font != null) { _body.font = font.font; _body.fontSharedMaterial = font.fontSharedMaterial; }
            _body.fontSize = p.CreditButtonTMP != null ? p.CreditButtonTMP.fontSize : 28f;
            _body.color = p.CreditButtonTMP != null ? p.CreditButtonTMP.color : Color.white;
            _body.alignment = TextAlignmentOptions.Center;
            _body.enableWordWrapping = true;
            _body.richText = true;
            _body.raycastTarget = false;

            win.SetActive(false);
            win.transform.SetParent(src.parent, false);
            UnityEngine.Object.Destroy(holder);
            _window = win;
        }

        static void JoinDiscord()
        {
            try { AudioManager.PlayOutGameNormalClick(); } catch { }
            Application.OpenURL(Discord);
        }

        /// <summary>Cada fotograma: los enlaces del texto, y si Opciones se cierra por su cuenta, la nuestra tambien.</summary>
        public static void Frame()
        {
            if (!IsOpen) return;
            if (_popup == null || !_popup.gameObject.activeInHierarchy) { _window.SetActive(false); return; }
            if (Input.GetKeyDown(KeyCode.Escape)) { Close(); return; }
            if (_body == null || !Input.GetMouseButtonDown(0)) return;
            var canvas = _body.canvas;
            var cam = canvas == null || canvas.renderMode == RenderMode.ScreenSpaceOverlay ? null : canvas.worldCamera;
            int i = TMP_TextUtilities.FindIntersectingLink(_body, Input.mousePosition, cam);
            if (i < 0) return;
            var id = _body.textInfo.linkInfo[i].GetLinkID();
            if (Links.TryGetValue(id, out var url))
            {
                try { AudioManager.PlayOutGameNormalClick(); } catch { }
                Application.OpenURL(url);
            }
        }

        // ------------------------------------------------------------ utilidades
        /// <summary>El objeto que contiene a los dos (la lista de botones).</summary>
        static Transform Common(Transform a, Transform b)
        {
            for (var t = a.parent; t != null; t = t.parent)
                if (b == t || b.IsChildOf(t)) return t;
            return a.parent;
        }

        /// <summary>El hijo directo de la lista que contiene a t (el boton con su marco).</summary>
        static Transform ItemOf(Transform t, Transform list)
        {
            while (t != null && t.parent != list) t = t.parent;
            return t;
        }

        /// <summary>En una copia de root, el objeto que corresponde a child.</summary>
        static Transform Same(Transform copy, Transform root, Transform child)
        {
            if (child == null) return null;
            if (child == root) return copy;
            if (!child.IsChildOf(root)) return null;
            var path = new List<string>();
            for (var t = child; t != null && t != root; t = t.parent) path.Insert(0, t.name);
            return copy.Find(string.Join("/", path));
        }
    }
}
