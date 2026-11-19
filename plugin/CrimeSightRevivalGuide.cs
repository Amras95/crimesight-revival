// CRIMESIGHT Revival - "Guia Revival": como funciona lo que anade Revival, dentro del juego.
//
// El menu "Jugar" trae un tercer boton pequeno, "Consejos", que el juego deja apagado junto a "Tutorial".
// Aqui se enciende con el nombre "Guia Revival" y abre la pantalla de consejos del juego (la misma de
// Tutorial y Entrenamiento: lista a la izquierda, titulo, paginas con flechas). Mientras se abre desde
// ese boton, la lista solo tiene las entradas de la guia (registradas como consejos del juego) y el texto
// de cada pagina, con los iconos de los botones del mando que uses, va donde normalmente va la imagen.
// Los textos de la guia estan en GuideText.cs (espanol e ingles; los demas idiomas ven el ingles).
// Todas las paginas usan el mismo tamano de letra (BodySize). Las que tienen captura (GuideText.Image) la
// ensenan arriba, de lado a lado, y el texto debajo; las capturas estan en GuideImages.cs, generado por
// tools/guide_images.py.
using System;
using System.Collections.Generic;
using System.IO;
using HarmonyLib;
using Il2CppInterop.Runtime;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace CrimeSightRevival.Mods
{
    static class Guide
    {
        const int TipsPhase = 12;                 // OutGameManager.RootPhase.Tips
        const string TitleId = "ctg_outgame_tutorialTips_title";
        const string HeaderId = "ctg_outgame_tutorialTips_subtitle_tips";
        const string HelpId = "csr_guide_help";                 // texto de ayuda al pasar el raton por el boton
        static readonly string[] ButtonLabel = { "Revivalガイド", "Revival Guide", "Guide Revival", "Guida Revival",
            "Revival-Leitfaden", "Guía Revival", "Guia Revival", "Гид Revival", "Revival 가이드", "Revival 指南", "Revival 指南" };

        public static bool Active;
        static Il2CppSystem.Collections.Generic.List<TipsData> _list;
        static readonly Dictionary<IntPtr, int> _topicOf = new();        // TipsData -> tema
        static readonly Dictionary<string, string> _saved = new();         // textos del juego cambiados mientras se ve la guia
        static TextMeshProUGUI _page;                                      // texto de la pagina (sobre la imagen)
        static RawImage _pic;                                              // captura de la pagina (arriba, de lado a lado), si tiene
        static readonly Dictionary<string, Texture2D> _picTex = new();     // nombre -> textura (null si no se pudo cargar)
        static string _laidOut;                                            // tamano de pagina + texto con los que se coloco todo
        const float BodySize = 24f;                                        // tamano de letra de todas las paginas
        const float MinBodySize = 18f;                                     // solo si el texto no cabe ni quitando la captura
        const float Side = 34, Top = 26, Bottom = 26, Gap = 12;            // margenes de la pagina y entre captura y texto
        const float PicMaxShare = 0.6f;                                    // la captura, como mucho esta parte de la altura
        static OutGameTips _tips;                                          // la pantalla donde se ve
        static int _topic = -1;
        static string _shown;                                              // lo que tiene puesto _page
        static int _lang = 1;

        static string SeenFile => Path.Combine(LiveMods.LiveDir, "guide_seen.txt");

        public static void Init(Harmony h)
        {
            try
            {
                Patch(h, typeof(OutGameSelectGameMenu), "Start", post: nameof(AfterMenuStart));
                Patch(h, typeof(OutGameSelectGameMenu), "SetText", post: nameof(AfterMenuText));
                Patch(h, typeof(OutGameSelectGameMenu), "ClickTipsButton", pre: nameof(BeforeOpenGuide));
                Patch(h, typeof(OutGameSelectGameMenu), "ClickTutorialButton", pre: nameof(NotGuide));
                Patch(h, typeof(OutGameSelectGameMenu), "ClickAIMatchButton", pre: nameof(NotGuide));
                Patch(h, typeof(OutGameManager), "SetRootPhase", post: nameof(AfterRootPhase));
                Patch(h, typeof(TipsDataManager), "GetRegistTipsData", post: nameof(AfterGetTips));
                Patch(h, typeof(OutGameTips), "SetTipsDisplay", post: nameof(AfterTipsDisplay));
                Patch(h, typeof(OutGameTips), "CallTipsTalk", pre: nameof(BeforeTipsTalk));
                Patch(h, typeof(OutGameTips), "RefreshTutorialList", pre: nameof(OnlyGuide));   // con la guia, solo la guia
                Patch(h, typeof(OutGameTips), "RefreshSoloRoomList", pre: nameof(OnlyGuide));
                Patch(h, typeof(OutGameTips), "GetTipsDoneFromSaveData", pre: nameof(BeforeTipsDone));
                Patch(h, typeof(OutGameTips), "SetTutorialDisplay", pre: nameof(BeforeTutorialDisplay));    // sin "Empezar el tutorial"
                Patch(h, typeof(OutGameTips), "RefreshTipsList", post: nameof(AfterRefreshTips));
                Patch(h, typeof(OutGameTips), "Open", pre: nameof(BeforeTipsOpen));     // listas de la guia o del juego
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] " + e.Message); }
        }

        static void Patch(Harmony h, Type t, string method, string pre = null, string post = null)
        {
            var m = AccessTools.Method(t, method);
            if (m == null) { Plugin.L.LogWarning("[Guia] no encuentro " + t.Name + "." + method); return; }
            HarmonyMethod Hm(string n) => n == null ? null : new HarmonyMethod(typeof(Guide).GetMethod(n,
                System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic));
            h.Patch(m, prefix: Hm(pre), postfix: Hm(post));
        }

        static int Lang()
        {
            try { return Math.Max(0, Math.Min(10, (int)TextManager.Instance.GetLangType())); } catch { return 1; }
        }

        // ------------------------------------------------------------ el boton del menu "Jugar"
        // El juego tiene un boton "Consejos" en el mismo hueco que "Tutorial" (o uno u otro), y al encenderlo
        // desaparece el del tutorial. Por eso la guia es una copia del rombo del tutorial, un rombo mas alla
        // en la misma diagonal (Entrenamiento -> Tutorial -> Guia), que abre la pantalla de consejos.
        static OutGameSelectGameMenu _menu;
        static GameObject _src, _btn;
        static TextMeshProUGUI _label;
        static GameObject _badge;
        static Transform _srcButton, _aiButton, _srcBadge;
        static bool _fromTips;
        // piezas del original y de la copia, en el mismo orden: cada fotograma la copia imita al original
        // (asi tiene las mismas animaciones de entrada, salida y del aviso, sin animar nada por su cuenta)
        static Transform[] _ts, _td;
        static Transform _setposSrc, _setposCopy;           // donde sale el marco de resaltado del juego
        static Graphic[] _gs, _gd;
        static CanvasGroup[] _cs, _cd;
        static UnityEngine.Events.UnityAction _onClick;
        static bool _lateSeen, _lateFailed;

        static float _createAt;

        // La copia se hace en cuanto se ve el rombo original y, cada fotograma, imita lo que hace (animaciones).
        static void AfterMenuStart(OutGameSelectGameMenu __instance)
        {
            try
            {
                _menu = __instance;
                _createAt = 0;
                if (_btn != null) { try { UnityEngine.Object.Destroy(_btn); } catch { } _btn = null; }
                Dump(__instance);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] boton: " + e); }
        }

        static float _waitSince = -1;

        static void CreateButton()
        {
            var m = _menu;
            // Se copia el rombo de "Tutorial" (set_TutorialButton). Ojo: en el juego, el "grupo de consejos"
            // es el de "Entrenamiento individual"; solo se usa si el del tutorial no llega a verse.
            bool tips = false;
            if (m.TutorialButtonGroupObject == null || !m.TutorialButtonGroupObject.activeInHierarchy)
            {
                if (_waitSince < 0) _waitSince = Time.unscaledTime;
                if (Time.unscaledTime - _waitSince < 3f) return;     // aun no se ve: se espera un poco
                tips = m.TipsButtonGroupObject != null && m.TipsButtonGroupObject.activeInHierarchy;
                if (!tips) return;
            }
            _waitSince = -1;
            var button = tips ? m.TipsButton : m.TutorialButton;
            var group = tips ? m.TipsButtonGroupObject : m.TutorialButtonGroupObject;
            var tmp = tips ? m.TipsTMP : m.TutorialTMP;
            var badge = tips ? m.TipsBadge : m.TutorialBadge;
            if (button == null) { _menu = null; return; }
            _src = group != null ? group : button.gameObject;
            _createAt = float.MaxValue;
            var src = _src.transform;
            var copy = UnityEngine.Object.Instantiate(_src, src.parent, false);
            copy.name = "CSR_GuideButton";
            copy.transform.SetSiblingIndex(src.GetSiblingIndex() + 1);
            _btn = copy;

            var b = Find(copy.transform, src, button.transform)?.GetComponent<Button>() ?? copy.GetComponentInChildren<Button>(true);
            if (b != null)
            {
                try
                {
                    var sp = tips ? m.setposTipsButton : m.setposTutorialButton;
                    _setposSrc = sp != null ? sp.transform : null;
                    _setposCopy = null;
                    if (sp != null)
                    {
                        var inCopy = Find(copy.transform, src, sp.transform);
                        if (inCopy != null) { _setposCopy = inCopy; _setposSrc = null; }
                        else
                        {
                            var spc = UnityEngine.Object.Instantiate(sp, sp.transform.parent, false);
                            spc.name = "CSR_GuideSetpos";
                            _setposCopy = spc.transform;
                        }
                    }
                    SetGameText(HelpId, GuideText.Help(Lang()), keep: true);
                    if (_setposCopy != null) m.SetButtonEnterEvent(b, _setposCopy.gameObject, HelpId);
                }
                catch (Exception e) { Plugin.L.LogWarning("[Guia] resaltado: " + e.Message); }
                b.onClick = new Button.ButtonClickedEvent();
                _onClick ??= DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction>(new Action(OpenFromMenu));
                b.onClick.AddListener(_onClick);
                b.interactable = true;
            }
            _copyButton = b != null ? b.transform : null;
            var lt = tmp != null ? Find(copy.transform, src, tmp.transform) : null;
            _label = lt != null ? lt.GetComponent<TextMeshProUGUI>() : copy.GetComponentInChildren<TextMeshProUGUI>(true);
            var bt = badge != null ? Find(copy.transform, src, badge.transform) : null;
            _badge = bt != null ? bt.gameObject : null;
            if (_badge != null) _badge.SetActive(!File.Exists(SeenFile));

            _srcButton = button.transform;
            _aiButton = m.AIMatchButton != null ? m.AIMatchButton.transform : null;
            _srcBadge = badge != null ? badge.transform : null;
            _fromTips = tips;
            // Lo de dentro del boton se anima solo (pasar el raton, pulsar) con sus propias animaciones; para la
            // entrada y salida del menu imita al original, mientras nadie este encima de ninguno de los dos.
            var ts = new List<Transform>(); var td = new List<Transform>();
            var all = ToArr(_src.GetComponentsInChildren<Transform>(true)); var allc = ToArr(copy.GetComponentsInChildren<Transform>(true));
            if (all.Length == allc.Length)
                for (int i = 0; i < all.Length; i++)
                    if (all[i] != _srcButton && all[i].IsChildOf(_srcButton)) { ts.Add(all[i]); td.Add(allc[i]); }
            _ts = ts.ToArray(); _td = td.ToArray();
            var gs = new List<Graphic>(); var gd = new List<Graphic>();
            var ag = ToArr(_src.GetComponentsInChildren<Graphic>(true)); var agc = ToArr(copy.GetComponentsInChildren<Graphic>(true));
            if (ag.Length == agc.Length)
                for (int i = 0; i < ag.Length; i++)
                    if (ag[i].transform.IsChildOf(_srcButton)) { gs.Add(ag[i]); gd.Add(agc[i]); }
            _gs = gs.ToArray(); _gd = gd.ToArray();
            _cs = ToArr(_src.GetComponentsInChildren<CanvasGroup>(true)); _cd = ToArr(copy.GetComponentsInChildren<CanvasGroup>(true));
            if (_cs.Length != _cd.Length) _cs = _cd = new CanvasGroup[0];
            Place();
            Plugin.L.LogInfo($"[Guia] boton en {copy.transform.position} (copia de {(tips ? "consejos" : "tutorial")} en {src.position}), " +
                             $"clic {(b != null)}, texto {(_label != null ? _label.name : "-")}, aviso {(_badge != null)}");
        }

        static Transform _copyButton;
        static float _hotUntil;

        /// <summary>El raton (o el mando) esta sobre el rombo dado.</summary>
        static bool Hot(Transform t)
        {
            if (t == null) return false;
            try
            {
                var es = UnityEngine.EventSystems.EventSystem.current;
                if (es != null && es.currentSelectedGameObject != null && es.currentSelectedGameObject.transform.IsChildOf(t)) return true;
                var rt = t.TryCast<RectTransform>();
                if (rt == null) return false;
                var canvas = rt.GetComponentInParent<Canvas>();
                Camera cam = canvas != null && canvas.rootCanvas.renderMode != RenderMode.ScreenSpaceOverlay ? canvas.rootCanvas.worldCamera : null;
                Vector2 mp = Input.mousePosition;
                if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(rt, mp, cam, out var lp)) return false;
                var r = rt.rect;
                // rombo: |x|/(w/2) + |y|/(h/2) <= 1
                return Math.Abs(lp.x - r.center.x) / (r.width / 2f) + Math.Abs(lp.y - r.center.y) / (r.height / 2f) <= 1f;
            }
            catch { return false; }
        }

        static T[] ToArr<T>(IEnumerable<T> a) => new List<T>(a).ToArray();

        /// <summary>Para el registro: donde esta cada pieza del menu (si el boton no sale bien, se ve por que).</summary>
        static void Dump(OutGameSelectGameMenu m)
        {
            try
            {
                string P(Component c) => c == null ? "-" : P2(c.transform);
                string P2(Transform t) { var s = ""; for (var x = t; x != null; x = x.parent) s = "/" + x.name + s; return s + (t.gameObject.activeSelf ? "" : " (off)"); }
                Plugin.L.LogInfo("[Guia] grupo tutorial " + (m.TutorialButtonGroupObject != null ? P2(m.TutorialButtonGroupObject.transform) : "-")
                    + " | grupo consejos " + (m.TipsButtonGroupObject != null ? P2(m.TipsButtonGroupObject.transform) : "-"));
                Plugin.L.LogInfo("[Guia] tutorial " + P(m.TutorialButton) + " | texto " + P(m.TutorialTMP) + " | aviso " + (m.TutorialBadge != null ? P2(m.TutorialBadge.transform) : "-"));
                if (m.TutorialButtonGroupObject != null)
                    foreach (var t in m.TutorialButtonGroupObject.GetComponentsInChildren<Transform>(true))
                    {
                        var names = new List<string>();
                        foreach (var c in t.GetComponents<Component>()) names.Add(c.GetIl2CppType().Name);
                        Plugin.L.LogInfo("[Guia]   " + P2(t) + ": " + string.Join(", ", names));
                    }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] dump: " + e.Message); }
        }

        /// <summary>El mismo objeto dentro de la copia (por su ruta desde el original).</summary>
        static Transform Find(Transform copy, Transform root, Transform child)
        {
            if (child == root) return copy;
            if (!child.IsChildOf(root)) return null;
            var path = new List<string>();
            for (var t = child; t != null && t != root; t = t.parent) path.Insert(0, t.name);
            return copy.Find(string.Join("/", path));
        }

        // ClickTipsButton tambien lo usa el juego (su propio boton de consejos abre la misma pantalla): la guia solo
        // se enciende si el clic es en nuestro boton: si se acaba de pulsar o si el raton (o el mando) esta sobre el.
        static float _ourClickAt = -100f;
        const float OurClickWindow = 1f;

        static void OpenFromMenu()
        {
            _ourClickAt = Time.unscaledTime;
            try { if (_menu != null) _menu.ClickTipsButton(); }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] abrir: " + e.Message); }
        }

        /// <summary>Cada fotograma (Update y LateUpdate): el rombo sigue al del tutorial; y la guia, si esta abierta.</summary>
        public static void Frame(bool late)
        {
            if (late && !_lateSeen) { _lateSeen = true; Plugin.L.LogInfo("[Guia] LateUpdate activo"); }
            try { GuideFrame(); } catch (Exception e) { if (!_lateFailed) { _lateFailed = true; Plugin.L.LogWarning("[Guia] guia: " + e); } }
            Place();
        }

        static void Place()
        {
            if ((object)_menu == null) return;
            try
            {
                if (_menu == null) { _menu = null; return; }
                if (_btn == null)
                {
                    if (Time.unscaledTime >= _createAt) CreateButton();
                    return;
                }
                if (_src == null) { _menu = null; return; }
                // si el juego cambia "Tutorial" por "Consejos" (o al reves), se vuelve a copiar el que se vea
                var other = _fromTips ? _menu.TutorialButtonGroupObject : _menu.TipsButtonGroupObject;
                if (!_src.activeSelf && other != null && other.activeSelf)
                {
                    UnityEngine.Object.Destroy(_btn); _btn = null; _createAt = 0;
                    return;
                }
                bool show = _src.activeSelf;
                if (_btn.activeSelf != show) _btn.SetActive(show);
                if (!show) return;

                // dentro del boton: imita al original (entrada y salida del menu) salvo cuando alguno de los dos
                // tiene el raton encima; entonces cada uno hace su propia animacion
                if (Hot(_copyButton) || Hot(_srcButton)) _hotUntil = Time.unscaledTime + 0.6f;
                if (Time.unscaledTime >= _hotUntil)
                {
                    for (int i = 0; i < _ts.Length; i++)
                    {
                        var a = _ts[i]; var d = _td[i];
                        if (a == null || d == null) continue;
                        if (d.localPosition != a.localPosition) d.localPosition = a.localPosition;
                        if (d.localScale != a.localScale) d.localScale = a.localScale;
                        if (d.localRotation != a.localRotation) d.localRotation = a.localRotation;
                        if (d.gameObject.activeSelf != a.gameObject.activeSelf) d.gameObject.SetActive(a.gameObject.activeSelf);
                    }
                    for (int i = 0; i < _gs.Length; i++)
                        if (_gs[i] != null && _gd[i] != null && _gd[i].color != _gs[i].color) _gd[i].color = _gs[i].color;
                }
                for (int i = 0; i < _cs.Length; i++)
                {
                    if (_cs[i] == null || _cd[i] == null) continue;
                    bool inner = _cs[i].transform != _src.transform && _cs[i].transform.IsChildOf(_srcButton);
                    if (inner && Time.unscaledTime < _hotUntil) continue;
                    if (_cd[i].alpha != _cs[i].alpha) _cd[i].alpha = _cs[i].alpha;
                }
                var root = _btn.transform; var sr = _src.transform;
                var scale = sr.localScale * 0.9f;                                 // un 10 % mas pequeno
                if (root.localScale != scale) root.localScale = scale;
                if (root.localRotation != sr.localRotation) root.localRotation = sr.localRotation;

                // sitio
                Vector3 want;
                if (_aiButton != null && _srcButton != null)
                {
                    var ai = _aiButton.position; var tut = _srcButton.position;
                    // debajo de "Entrenamiento individual" y a la izquierda de "Tutorial"
                    var target = new Vector3(ai.x, tut.y + 0.5f * (tut.y - ai.y), tut.z);
                    want = sr.position + (target - tut);
                }
                else want = sr.position + new Vector3(0, -((RectTransform)sr).rect.height * sr.lossyScale.y * 1.1f, 0);
                if ((root.position - want).sqrMagnitude > 1e-4f) root.position = want;
                if (_setposCopy != null && _setposSrc != null) _setposCopy.position = _setposSrc.position + (want - sr.position);
                if (_label != null) { var txt = ButtonLabel[Lang()]; if (_label.text != txt) _label.text = txt; }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] boton (sitio): " + e.Message); _menu = null; }
        }

        static void AfterMenuText(OutGameSelectGameMenu __instance)
        {
            try { if (_label != null) _label.text = ButtonLabel[Lang()]; } catch { }
        }

        static void BeforeOpenGuide()
        {
            bool ours = Time.unscaledTime - _ourClickAt <= OurClickWindow || Hot(_copyButton);
            if (!ours)                                                   // la pantalla de consejos del juego, no la guia
            {
                Plugin.L.LogInfo("[Guia] consejos del juego (no la guia)");
                Close();
                return;
            }
            Active = true;
            _lang = Lang();
            SetGameText(TitleId, GuideText.Title(_lang));
            SetGameText(HeaderId, GuideText.Title(_lang));
            try { File.WriteAllText(SeenFile, DateTime.UtcNow.ToString("o")); } catch { }
            try { if (_badge != null) _badge.SetActive(false); } catch { }
            Pad.EnsureIcons();
            Plugin.L.LogInfo("[Guia] abierta");
        }

        static void NotGuide() => Close();

        static bool OnlyGuide() => !Active;

        // ------------------------------------------------------------ listas de la pantalla de consejos
        // El juego monta las listas de la izquierda (tutoriales, salas de entrenamiento, consejos) una sola vez, la
        // primera vez que se abre la pantalla, y luego las reutiliza. La guia y el boton de consejos del juego usan
        // la misma pantalla: si se abre la otra, se borran las entradas y se vuelven a montar (con la guia, los
        // parches de arriba hacen que solo salgan sus temas).
        const int BuiltNone = 0, BuiltGame = 1, BuiltGuide = 2;
        static int _builtFor = BuiltNone;
        static bool _rebuilding;

        static void AfterRefreshTips(bool isNew)
        {
            if (isNew && !_rebuilding) _builtFor = Active ? BuiltGuide : BuiltGame;
        }

        static void BeforeTipsOpen(OutGameTips __instance)
        {
            try
            {
                int want = Active ? BuiltGuide : BuiltGame;
                if (_builtFor == BuiltNone || _builtFor == want || _rebuilding) return;
                RebuildLists(__instance, want);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] listas: " + e); }
        }

        // Las cabeceras de seccion (Tutorial, Consejos...) las crea el juego la primera vez que monta cada seccion
        // y ya no se borran. Con la guia, las que no son suyas se esconden (vacias se verian igual); sin la guia,
        // se vuelven a ensenar y "Tutorial" va antes que "Consejos", como en el juego sin mods.
        static readonly List<GameObject> _hiddenHeaders = new();

        static void FixHeaders(OutGameTips t, int want)
        {
            try
            {
                if (want == BuiltGuide)
                {
                    foreach (var h in new[] { t.headerTutorial, t.headerSoloRoom, t.headerImitation, t.headerPJW })
                        if (h != null && h.activeSelf) { h.SetActive(false); _hiddenHeaders.Add(h); }
                }
                else
                {
                    foreach (var h in _hiddenHeaders) if (h != null) h.SetActive(true);
                    _hiddenHeaders.Clear();
                    var tut = t.headerTutorial; var tips = t.headerTips;
                    var items = t.headerTutorialTransform;          // solo si sus entradas van dentro (si no, se separarian)
                    if (tut != null && tips != null && tut.transform.parent == tips.transform.parent
                        && (items == null || items.IsChildOf(tut.transform))
                        && tut.transform.GetSiblingIndex() > tips.transform.GetSiblingIndex())
                        tut.transform.SetSiblingIndex(tips.transform.GetSiblingIndex());
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] cabeceras: " + e.Message); }
        }

        static void RebuildLists(OutGameTips t, int want)
        {
            _rebuilding = true;
            try
            {
                int old = 0;
                var list = t.instanceTipsListButton;
                if (list != null)
                {
                    foreach (var b in list)
                        if (b != null && b.parentObj != null) { UnityEngine.Object.Destroy(b.parentObj); old++; }   // no es un componente: su boton es parentObj
                    list.Clear();
                }
                // en el orden del juego sin mods (comprobado): "Tutorial" arriba y "Consejos" (Tips) debajo
                t.RefreshTutorialList(true);       // con la guia no hacen nada (OnlyGuide)
                t.RefreshSoloRoomList(true);
                t.RefreshTipsList(true);
                // los nombres de las secciones se ponen al montar la pantalla; la guia cambia el de "Consejos"
                // mientras esta abierta (y lo devuelve al cerrarse), asi que se vuelven a poner
                try { t.SetTipsHeaderText(); t.SetTutorialHeaderText(); t.SetSoloRoomHeaderText(); }
                catch (Exception e) { Plugin.L.LogWarning("[Guia] nombres de secciones: " + e.Message); }
                // lo seleccionado era de la lista de antes (sin esto, al volver al tutorial el juego falla al montar su lista)
                try { t.selectTipsIndex = 0; t.selectTipsIndexPre = 0; }
                catch (Exception e) { Plugin.L.LogWarning("[Guia] seleccion: " + e.Message); }
                FixHeaders(t, want);
                _builtFor = want;
                Plugin.L.LogInfo($"[Guia] listas rehechas para {(want == BuiltGuide ? "la guia" : "el juego")}: " +
                    $"{old} entradas quitadas, {(list != null ? list.Count : -1)} nuevas");
            }
            finally { _rebuilding = false; }
        }

        static void AfterRootPhase(object[] __args)
        {
            try
            {
                if (!Active || __args == null || __args.Length == 0) return;
                if (Convert.ToInt32(__args[0]) != TipsPhase) Close();
            }
            catch { }
        }

        static void Close()
        {
            if (!Active) return;
            Active = false;
            var tm = TextManager.Instance;
            if (tm != null && tm.LangText != null)
                foreach (var kv in _saved) tm.LangText[kv.Key] = kv.Value;
            _saved.Clear();
            if (_page != null) _page.gameObject.SetActive(false);
            if (_pic != null) _pic.gameObject.SetActive(false);
        }

        static void SetGameText(string id, string text, bool keep = false)
        {
            var tm = TextManager.Instance;
            if (tm == null || tm.LangText == null) return;
            if (!keep && !_saved.ContainsKey(id) && tm.LangText.ContainsKey(id)) _saved[id] = tm.LangText[id];
            tm.LangText[id] = text;
        }

        // ------------------------------------------------------------ las entradas, como consejos del juego
        static Il2CppSystem.Collections.Generic.List<TipsData> Entries()
        {
            if (_list != null) return _list;
            _list = new Il2CppSystem.Collections.Generic.List<TipsData>();
            var tex = new Texture2D(4, 4, TextureFormat.RGBA32, false) { hideFlags = HideFlags.DontUnloadUnusedAsset };
            var clear = new Color32[16];
            tex.SetPixels32(clear);
            tex.Apply();
            for (int t = 0; t < GuideText.Count; t++)
            {
                var d = ScriptableObject.CreateInstance(Il2CppType.Of<TipsData>()).Cast<TipsData>();
                d.hideFlags = HideFlags.DontUnloadUnusedAsset;
                d.name = "CSR_Guide_" + (t + 1).ToString("00");
                d.serialNo = 90000 + t;
                d.tipsTitleMsgId = "csr_guide_" + (t + 1).ToString("00");
                d.isPJWTips = false;
                d.tipsDataList = new Il2CppSystem.Collections.Generic.List<TipsDataParam>();
                var sp = Sprite.Create(tex, new Rect(0, 0, 4, 4), new Vector2(0.5f, 0.5f));
                sp.hideFlags = HideFlags.DontUnloadUnusedAsset;
                d.tipsDataList.Add(new TipsDataParam { TriggerName = d.name, SpriteName = sp });   // GetName() = su nombre
                d.SetDone(true);
                _topicOf[d.Pointer] = t;
                _list.Add(d);
            }
            return _list;
        }

        static readonly HashSet<string> _regexSeen = new();

        static void AfterGetTips(string searchDataNameRegex, ref Il2CppSystem.Collections.Generic.List<TipsData> __result)
        {
            if (!Active) return;
            try
            {
                var tm = TextManager.Instance;
                if (tm != null && tm.LangText != null)
                    for (int t = 0; t < GuideText.Count; t++) tm.LangText["csr_guide_" + (t + 1).ToString("00")] = GuideText.TopicTitle(t, _lang);
                var all = Entries();
                // El juego pide la lista entera con un patron y cada tema con su nombre: si el patron
                // nombra temas concretos, solo esos; si no, todos.
                var only = new Il2CppSystem.Collections.Generic.List<TipsData>();
                foreach (var d in all)
                {
                    bool ok;
                    try { ok = System.Text.RegularExpressions.Regex.IsMatch(d.name, searchDataNameRegex ?? ""); } catch { ok = false; }
                    if (ok) only.Add(d);
                }
                __result = only.Count > 0 && only.Count < all.Count ? only : all;
                if (_regexSeen.Add(searchDataNameRegex ?? "")) Plugin.L.LogInfo($"[Guia] patron '{searchDataNameRegex}' -> {__result.Count}");
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] lista: " + e.Message); }
        }

        static bool Ours(TipsData d, out int topic)
        {
            topic = -1;
            return d != null && _topicOf.TryGetValue(d.Pointer, out topic);
        }

        static TipsData Arg(object[] a) => a != null && a.Length > 0 ? a[0] as TipsData : null;

        static bool BeforeTipsTalk(object[] __args) => !Ours(Arg(__args), out _);   // sin dialogo de personaje

        static bool BeforeTipsDone(object[] __args, ref bool __result)
        {
            if (!Ours(Arg(__args), out _)) return true;
            __result = true;
            return false;
        }

        // ------------------------------------------------------------ el texto de cada pagina
        static void AfterTipsDisplay(OutGameTips __instance, object[] __args)
        {
            try
            {
                var img = __instance.tipsImage;
                if (img == null) return;
                if (!Ours(Arg(__args), out int topic) || !Active)
                {
                    if (_page != null) _page.gameObject.SetActive(false);
                    if (_pic != null) _pic.gameObject.SetActive(false);
                    return;
                }
                if (_page == null || _page.transform.parent != img.transform)
                {
                    var go = new GameObject("CSR_GuidePage");
                    var rt = go.AddComponent<RectTransform>();
                    rt.SetParent(img.transform, false);
                    rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
                    rt.offsetMin = new Vector2(34, 26); rt.offsetMax = new Vector2(-34, -26);
                    _page = go.AddComponent<TextMeshProUGUI>();
                    var src = __instance.tutorialDocText ?? __instance.tipsTitleText;
                    if (src != null) { _page.font = src.font; _page.fontSharedMaterial = src.fontSharedMaterial; }
                    _page.color = new Color(0.10f, 0.12f, 0.11f, 1f);
                    _page.alignment = TextAlignmentOptions.TopLeft;
                    _page.enableWordWrapping = true;
                    _page.richText = true;
                    _page.enableAutoSizing = false;
                    _page.fontSize = BodySize;
                    _page.lineSpacing = 12;
                    _page.raycastTarget = false;
                }
                HideTutorialStart(__instance, true);
                _page.gameObject.SetActive(true);
                _tips = __instance;
                _topic = topic;
                _shown = null;
                SetPicture(img.transform, topic);
                RefreshPage();
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] pagina: " + e.Message); }
        }

        /// <summary>La captura del tema (si tiene) va arriba, y el texto debajo; ver Layout.</summary>
        static void SetPicture(Transform parent, int topic)
        {
            var name = GuideText.Image(topic);
            var tex = name == null ? null : PictureTexture(name);
            _laidOut = null;
            if (tex == null)
            {
                if (_pic != null) _pic.gameObject.SetActive(false);
                return;
            }
            if (_pic == null || _pic.transform.parent != parent)
            {
                var go = new GameObject("CSR_GuidePic");
                var rt = go.AddComponent<RectTransform>();
                rt.SetParent(parent, false);
                rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0.5f, 1f);
                _pic = go.AddComponent<RawImage>();
                _pic.raycastTarget = false;
            }
            _pic.texture = tex;
            _pic.gameObject.SetActive(true);
        }

        /// <summary>Coloca la pagina: la captura arriba, de lado a lado; el texto debajo, siempre a BodySize (las
        /// paginas con captura llevan poco texto para que quepa). Se repite si cambia el tamano de la pagina (al
        /// abrirse aun puede no tenerlo) o el texto.</summary>
        static void Layout()
        {
            if (_page == null || _shown == null) return;
            var size = _page.transform.parent.GetComponent<RectTransform>().rect.size;
            if (size.x <= 0 || size.y <= 0) return;
            bool pic = _pic != null && _pic.gameObject.activeSelf && _pic.texture != null;
            string key = size.x + "x" + size.y + (pic ? "p" : "") + _shown.Length;
            if (key == _laidOut) return;
            _laidOut = key;

            float w = size.x - 2 * Side, h = size.y - Top - Bottom;
            _page.enableAutoSizing = false;
            _page.fontSize = BodySize;
            float textH = _page.GetPreferredValues(_shown, w, 0).y;

            float picH = 0;
            if (pic)
            {
                float aspect = _pic.texture.width / (float)Math.Max(1, _pic.texture.height);
                picH = Math.Min(w / aspect, h * PicMaxShare);           // de lado a lado (el texto va en lo que sobra)
                _pic.rectTransform.anchoredPosition = new Vector2(0, -Top);
                _pic.rectTransform.sizeDelta = new Vector2(Math.Min(w, picH * aspect), picH);
            }
            var prt = _page.rectTransform;
            prt.anchorMin = Vector2.zero; prt.anchorMax = Vector2.one;
            prt.offsetMin = new Vector2(Side, Bottom);
            prt.offsetMax = new Vector2(-Side, -(Top + (pic ? picH + Gap : 0)));

            float room = h - (pic ? picH + Gap : 0);
            if (textH > room)                                            // no cabe: se encoge solo esta pagina
            {
                _page.enableAutoSizing = true;
                _page.fontSizeMax = BodySize; _page.fontSizeMin = MinBodySize;
                Plugin.L.LogInfo($"[Guia] la pagina {_topic + 1} no cabe a {BodySize} ({textH:0} de {room:0} px): se reduce la letra");
            }
        }

        /// <summary>La captura (de GuideImages) como textura; se carga una vez.</summary>
        static Texture2D PictureTexture(string name)
        {
            if (_picTex.TryGetValue(name, out var t)) return t;
            Texture2D tex = null;
            try
            {
                if (GuideImages.Data.TryGetValue(name, out var b64))
                {
                    tex = new Texture2D(2, 2, TextureFormat.RGBA32, false) { name = "csr_guide_" + name, hideFlags = HideFlags.DontUnloadUnusedAsset };
                    if (!ImageConversion.LoadImage(tex, Convert.FromBase64String(b64), false)) tex = null;
                }
                if (tex == null) Plugin.L.LogWarning("[Guia] no pude cargar la captura " + name);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] captura " + name + ": " + e.Message); tex = null; }
            _picTex[name] = tex;
            return tex;
        }

        /// <summary>Pone el texto del tema (otra vez si ya hay iconos o stickers que antes no estaban).</summary>
        static void RefreshPage()
        {
            if (_page == null || _topic < 0) return;
            if (Pad.KeyIcons != null && _page.spriteAsset != Pad.KeyIcons) { _page.spriteAsset = Pad.KeyIcons; _shown = null; }
            var text = Icons(GuideText.Page(_topic, _lang));
            if (text == _shown) { Layout(); return; }
            _page.text = text;
            _shown = text;
            Layout();
        }

        /// <summary>Cada fotograma con la guia abierta: iconos, stickers, texto y sin flechas de pagina.</summary>
        static void GuideFrame()
        {
            if (!Active || _tips == null) return;
            if (Pad.KeyIcons == null) Pad.EnsureIcons();
            Stickers.Ensure();
            RefreshPage();
            foreach (var b in new[] { _tips.prevButton, _tips.nextButton })
                if (b != null && b.gameObject.activeSelf) b.gameObject.SetActive(false);
        }

        static readonly List<GameObject> _hidden = new();

        /// <summary>El boton "Empezar el tutorial" no pinta nada en la guia; se devuelve antes de ver un tutorial.</summary>
        static void HideTutorialStart(OutGameTips t, bool hide)
        {
            if (hide)
            {
                foreach (var go in new[] { t.tutorialNull, t.tutorialButton != null ? t.tutorialButton.gameObject : null })
                    if (go != null && go.activeSelf) { go.SetActive(false); _hidden.Add(go); }
                return;
            }
            foreach (var go in _hidden) try { if (go != null) go.SetActive(true); } catch { }
            _hidden.Clear();
        }

        static bool BeforeTutorialDisplay(OutGameTips __instance)
        {
            if (Active) return false;
            if (_hidden.Count > 0) HideTutorialStart(__instance, false);
            return true;
        }

        /// <summary>{A}, {LS}, {START}... -> iconos del mando que se usa (o el de Xbox si no hay ninguno).</summary>
        static string Icons(string text)
        {
            string st = Pad.PadStyle ?? "xbox";
            string S(string n) => $"<sprite name=\"csr_{n}\">";
            return text
                .Replace("{A}", S(st + "_a")).Replace("{B}", S(st + "_b")).Replace("{X}", S(st + "_x")).Replace("{Y}", S(st + "_y"))
                .Replace("{LBRB}", S(st + "_lbrb")).Replace("{LTRT}", S(st + "_ltrt"))
                .Replace("{LB}", S(st + "_lb")).Replace("{RB}", S(st + "_rb")).Replace("{LT}", S(st + "_lt")).Replace("{RT}", S(st + "_rt"))
                .Replace("{START}", S(st + "_start")).Replace("{BACK}", S(st + "_back"))
                .Replace("{LS}", S("lstick")).Replace("{RS}", S("rstick")).Replace("{DPAD}", S("dpad"))
                .Replace("{ST_IRENE}", Stickers.Tag(38)).Replace("{ST_SUS}", Stickers.Tag(25)).Replace("{ST_NOSUS}", Stickers.Tag(24))
                .Replace("{H}", "<color=#1f6e57>").Replace("{/H}", "</color>");
        }
    }

    /// <summary>Las imagenes de los stickers del juego, para ponerlas dentro del texto de la guia.</summary>
    static class Stickers
    {
        static readonly Dictionary<int, string> _names = new();   // tipo de sticker -> nombre del icono
        static readonly HashSet<int> _wanted = new() { 38, 25, 24 };   // Irene "asesino", sospecho, no creo
        static float _nextTry;

        /// <summary>El icono del sticker para TextMeshPro, o nada si aun no esta.</summary>
        public static string Tag(int type) => _names.TryGetValue(type, out var n) ? $"<sprite name=\"{n}\">" : "";

        public static void Ensure()
        {
            if (_names.Count >= _wanted.Count || Time.unscaledTime < _nextTry) return;
            _nextTry = Time.unscaledTime + 2f;
            var root = Pad.KeyIcons;
            if (root == null) return;
            try
            {
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<StampData>()))
                {
                    var d = o == null ? null : o.TryCast<StampData>();
                    if (d == null) continue;
                    int type;
                    try { type = (int)d.GetStampType(); } catch { continue; }
                    if (!_wanted.Contains(type) || _names.ContainsKey(type)) continue;
                    var sp = d.spriteImageThumbnail ?? d.spriteImage;
                    if (sp == null || sp.texture == null) continue;
                    var name = "csr_stamp_" + type;
                    var asset = Build(root, sp, name);
                    if (asset == null) continue;
                    if (root.fallbackSpriteAssets == null) root.fallbackSpriteAssets = new Il2CppSystem.Collections.Generic.List<TMP_SpriteAsset>();
                    root.fallbackSpriteAssets.Add(asset);
                    _names[type] = name;
                    Plugin.L.LogInfo($"[Guia] sticker {type} listo ({sp.name})");
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Guia] stickers: " + e.Message); _nextTry = float.MaxValue; }
        }

        /// <summary>Un sprite del juego como icono de TextMeshPro (sin copiar la imagen: se usa su textura tal cual).</summary>
        static TMP_SpriteAsset Build(TMP_SpriteAsset root, Sprite sp, string name)
        {
            int refIdx = root.GetSpriteIndexFromName("keyboard_ctrl");
            if (refIdx < 0 || root.spriteCharacterTable.Count == 0) refIdx = 0;
            var refChar = root.spriteCharacterTable[refIdx];
            var refGlyph = root.spriteGlyphTable[(int)Math.Min(refChar.glyphIndex, (uint)(root.spriteGlyphTable.Count - 1))];
            var rm = refGlyph.metrics;

            var a = UnityEngine.Object.Instantiate(root);
            a.name = name;
            a.hideFlags = HideFlags.DontUnloadUnusedAsset;
            var tex = sp.texture;
            a.spriteSheet = tex;
            var mat = new Material(root.material) { name = name + "_mat", hideFlags = HideFlags.DontUnloadUnusedAsset };
            mat.mainTexture = tex;
            a.material = mat;
            a.hashCode = TMP_TextUtilities.GetSimpleHashCode(a.name);
            a.materialHashCode = TMP_TextUtilities.GetSimpleHashCode(mat.name);

            var r = sp.textureRect;
            float h = rm.height * 2.2f;                                  // un poco mas grande que una linea
            float w = h * (r.width / Math.Max(1f, r.height));
            var metrics = new UnityEngine.TextCore.GlyphMetrics(w, h, 0, rm.horizontalBearingY + (h - rm.height) * 0.6f, w + rm.height * 0.2f);
            var g = new TMP_SpriteGlyph(0, metrics,
                new UnityEngine.TextCore.GlyphRect((int)r.x, (int)r.y, (int)r.width, (int)r.height), refGlyph.scale, 0);
            a.spriteGlyphTable.Clear();
            a.spriteCharacterTable.Clear();
            a.spriteGlyphTable.Add(g);
            a.spriteCharacterTable.Add(new TMP_SpriteCharacter(0xFFFE, g) { name = name });
            a.fallbackSpriteAssets = new Il2CppSystem.Collections.Generic.List<TMP_SpriteAsset>();
            a.UpdateLookupTables();
            return a;
        }
    }
}
