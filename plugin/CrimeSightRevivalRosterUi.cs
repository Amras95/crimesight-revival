// CRIMESIGHT Revival - "Selector de personajes" en la sala de espera.
//
// Un boton (silueta de una persona y debajo "Selector de personajes") abre una ventana con todos los personajes
// que pueden salir en la sala: los originales y los nuevos que trae cada jugador. Cada uno tiene su imagen, su
// nombre debajo y una casilla a la izquierda para dejarlo salir o no; al pasar el raton por encima se ve su modelo
// 3D a la derecha, girando. En cada partida salen 6 al azar entre los marcados (con la misma probabilidad), asi
// que tiene que haber al menos 6 personajes y 1 traidor.
// Lo decide el anfitrion: su eleccion va a csr_live/roster_select.json, el lanzador se la pasa al servidor y vale
// para su sala (y la proxima vez). Los demas ven la ventana sin poder cambiarla.
// La lista la escribe el lanzador en csr_live/roster_pool.json; sin ese archivo (sin lanzador nuevo) no hay boton.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using Il2CppInterop.Runtime;

namespace CrimeSightRevival.Mods
{
    static class RosterUi
    {
        // idiomas del juego: ja, en, fr, it, de, es, pt, ru, ko, zh-cn, zh-tw
        static readonly string[] TBtn = { "キャラクター選択", "Character selector", "Sélecteur de personnages", "Selettore di personaggi",
            "Figurenauswahl", "Selector de personajes", "Seletor de personagens", "Выбор персонажей", "캐릭터 선택", "角色选择", "角色選擇" };
        static readonly string[] THost = {
            "出場できるキャラにチェック。毎試合、チェックした中からランダムに6人が出ます（最低6人）。",
            "Tick who can appear. Each match picks 6 at random among the ticked ones (at least 6).",
            "Cochez qui peut apparaître. Chaque partie en tire 6 au hasard parmi eux (au moins 6).",
            "Spunta chi può comparire. Ogni partita ne sorteggia 6 tra quelli spuntati (almeno 6).",
            "Hake an, wer erscheinen darf. Jede Partie lost 6 davon aus (mindestens 6).",
            "Marca quién puede salir. Cada partida salen 6 al azar entre los marcados (mínimo 6).",
            "Marque quem pode aparecer. Cada partida sorteia 6 entre os marcados (mínimo 6).",
            "Отметьте, кто может появиться. В каждом матче случайно выбираются 6 из отмеченных (минимум 6).",
            "나올 수 있는 캐릭터를 체크하세요. 매 판 체크한 캐릭터 중 6명이 무작위로 나옵니다(최소 6명).",
            "勾选可以出场的角色。每局从勾选的角色中随机选出 6 人（至少 6 人）。",
            "勾選可以出場的角色。每局從勾選的角色中隨機選出 6 人（至少 6 人）。" };
        static readonly string[] TGuest = { "このルームではホストが決めます。", "In this room the host decides.", "Dans ce salon, c'est l'hôte qui décide.",
            "In questa stanza decide l'host.", "In diesem Raum entscheidet der Host.", "En esta sala lo decide el anfitrión.",
            "Nesta sala quem decide é o anfitrião.", "В этой комнате решает хозяин.", "이 방에서는 방장이 정합니다.", "此房间由房主决定。", "此房間由房主決定。" };
        static readonly string[] TNeedPawns = { "キャラは最低{0}人必要です。", "There must be at least {0} characters.", "Il faut au moins {0} personnages.",
            "Servono almeno {0} personaggi.", "Es müssen mindestens {0} Figuren sein.", "Tiene que haber al menos {0} personajes.",
            "É preciso ter pelo menos {0} personagens.", "Нужно не меньше {0} персонажей.", "캐릭터는 최소 {0}명 필요합니다.", "至少需要 {0} 名角色。", "至少需要 {0} 名角色。" };
        static readonly string[] TNeedTraitor = { "裏切り者は最低1人必要です。", "There must be at least 1 traitor.", "Il faut au moins 1 traître.",
            "Serve almeno 1 traditore.", "Es muss mindestens 1 Verräter sein.", "Tiene que haber al menos 1 traidor.",
            "É preciso ter pelo menos 1 traidor.", "Нужен хотя бы 1 предатель.", "배신자는 최소 1명 필요합니다.", "至少需要 1 名叛徒。", "至少需要 1 名叛徒。" };
        static readonly string[] TSave = { "保存", "Save", "Enregistrer", "Salva", "Speichern", "Guardar", "Salvar", "Сохранить", "저장", "保存", "儲存" };
        static readonly string[] TCancel = { "キャンセル", "Cancel", "Annuler", "Annulla", "Abbrechen", "Cancelar", "Cancelar", "Отмена", "취소", "取消", "取消" };
        static readonly string[] TClose = { "閉じる", "Close", "Fermer", "Chiudi", "Schließen", "Cerrar", "Fechar", "Закрыть", "닫기", "关闭", "關閉" };
        static readonly string[] TTraitor = { "裏切り者", "Traitor", "Traître", "Traditore", "Verräter", "Traidor", "Traidor", "Предатель", "배신자", "叛徒", "叛徒" };
        static readonly string[] TOrigTraitor = { "裏切り者（オリジナル）", "Traitor (original)", "Traître (original)", "Traditore (originale)",
            "Verräter (Original)", "Traidor (original)", "Traidor (original)", "Предатель (оригинал)", "배신자(원래)", "叛徒（原版）", "叛徒（原版）" };
        static readonly string[] TNew = { "新キャラ", "New", "Nouveau", "Nuovo", "Neu", "Nuevo", "Novo", "Новый", "새 캐릭터", "新角色", "新角色" };
        static readonly string[] TNoModel = { "3Dモデルは試合を1回すると表示されます", "The 3D model shows up after your first match",
            "Le modèle 3D apparaît après votre première partie", "Il modello 3D compare dopo la prima partita", "Das 3D-Modell erscheint nach deiner ersten Partie",
            "El modelo 3D se ve después de tu primera partida", "O modelo 3D aparece depois da sua primeira partida", "3D-модель появится после первого матча",
            "3D 모델은 첫 판 이후에 보입니다", "3D 模型在第一局之后显示", "3D 模型在第一局之後顯示" };
        static readonly string[] TLoading = { "読み込み中…", "Loading…", "Chargement…", "Caricamento…", "Wird geladen…", "Cargando…",
            "Carregando…", "Загрузка…", "불러오는 중…", "加载中…", "載入中…" };
        static readonly string[] TSaved = { "保存しました。次の試合から有効です。", "Saved: it applies from the next match.", "Enregistré : valable dès la prochaine partie.",
            "Salvato: vale dalla prossima partita.", "Gespeichert: gilt ab der nächsten Partie.", "Guardado: vale desde la próxima partida.",
            "Salvo: vale a partir da próxima partida.", "Сохранено: действует со следующего матча.", "저장했습니다. 다음 판부터 적용됩니다.", "已保存，从下一局起生效。", "已儲存，從下一局起生效。" };

        class Item { public string id, key, role, name, image, model, animFrom; public bool enabled, orig; }

        static string PoolFile => Path.Combine(LiveMods.LiveDir, "roster_pool.json");
        static string SelectFile => Path.Combine(LiveMods.LiveDir, "roster_select.json");
        static int _lang = 1;

        // ------------------------------------------------------------ boton en la sala de espera
        // Es una copia del boton "Manual online" de la cabecera de la sala (mismo aspecto y mismo lienzo), justo a
        // su izquierda, con la silueta de una persona y el texto debajo. Si no se encuentra, va en una esquina.
        static GameObject _btnRoot;
        static RectTransform _btnRect;
        static RectTransform _manual;
        static bool _ownCanvas;
        static Image _btnImg;
        static Color _btnBase;
        static float _nextLook;
        static OutGameRoomWaitingMenuVer2 _menu;
        static bool _menuOpen;
        static bool _btnFaded;      // la sala se ve detras de una ventana: el boton se queda, como el del manual, sin pulsar
        static readonly Vector2 BtnSize = new Vector2(176, 118);

        public static void Frame()
        {
            if (_root != null) { WindowFrame(); return; }
            if (Time.unscaledTime >= _nextLook)
            {
                _nextLook = Time.unscaledTime + 0.15f;                // como los iconos del mando (Pad.UiScan)
                _menuOpen = MenuVisible();
                // La sala se ve aunque tenga una ventana encima (ajustes, confirmaciones, dificultad de la IA...): el
                // boton se queda igual que el del manual de al lado (el juego oscurece los dos), sin poder pulsarse.
                // Con una ventana encima solo si se ve el del manual: fuera de la sala el juego la deja cargada.
                bool want = File.Exists(PoolFile) && (_menuOpen || (RoomShown() && ManualSeen(_manual != null ? _manual : FindManual())));
                if (want && (_btnRoot == null || (!_ownCanvas && _manual == null) || (_ownCanvas && FindManual() != null))) MakeButton();
                if (_btnRoot != null) _btnRoot.SetActive(want);
                if (want && !_ownCanvas && _btnRoot != null && _manual != null) Place(_btnRect, _manual);
                if (want && _btnRoot != null) FadeButton(Covered());
            }
            if (_btnRoot == null || !_btnRoot.activeSelf || !_ownCanvas) return;
            // en nuestro lienzo (sin el del juego): raton a mano
            bool over = !_btnFaded && RectTransformUtility.RectangleContainsScreenPoint(_btnRect, Input.mousePosition, null);
            if (_btnImg != null) _btnImg.color = over ? Skin.Hover(_btnBase) : _btnBase;
            if (over && Input.GetMouseButtonDown(0) && !Covered()) Open();
        }

        static bool MenuVisible()
        {
            try
            {
                if (_menu == null || _menu.gameObject == null)
                {
                    _menu = null;
                    foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<OutGameRoomWaitingMenuVer2>()))
                    {
                        var m = o.TryCast<OutGameRoomWaitingMenuVer2>();
                        if (m != null && m.gameObject.scene.IsValid()) { _menu = m; break; }
                    }
                }
                return _menu != null && _menu.gameObject.activeInHierarchy && _menu.IsActive() && !AiPicker.IsOpen;
            }
            catch { _menu = null; return false; }
        }

        /// <summary>La sala de espera se ve (aunque haya una ventana encima).</summary>
        static bool RoomShown()
        {
            try { return _menu != null && _menu.gameObject.activeInHierarchy; }
            catch { _menu = null; return false; }
        }

        /// <summary>El boton del manual se ve (activo y sin un CanvasGroup que lo oculte).</summary>
        static bool ManualSeen(RectTransform m)
        {
            try
            {
                if (m == null || !m.gameObject.activeInHierarchy) return false;
                for (var t = m.transform; t != null; t = t.parent)
                {
                    var cg = t.GetComponent<CanvasGroup>();
                    if (cg != null && cg.alpha < 0.05f) return false;
                    if (cg != null && cg.ignoreParentGroups) break;
                }
                return true;
            }
            catch { return false; }
        }

        /// <summary>Hay una ventana encima de la sala (o no es la pantalla activa): el boton no se puede pulsar.</summary>
        static bool Covered()
        {
            if (!_menuOpen) return true;
            try { return _menu.IsOverlaySomeUI(); } catch { return true; }
        }

        /// <summary>Con la sala tapada el boton no recibe clics y se ve exactamente como el del manual de al lado: estan
        /// en el mismo sitio, asi que lo que el juego oscurece los oscurece a los dos, y ademas se copia lo que lleva el
        /// del manual (su transparencia y si esta desactivado).</summary>
        static void FadeButton(bool faded)
        {
            _btnFaded = faded;
            float a = 1f;
            if (_manual != null)
            {
                try
                {
                    var mcg = _manual.GetComponent<CanvasGroup>();
                    if (mcg != null) a = mcg.alpha;
                    var mb = _manual.GetComponent<Button>();
                    var ours = _btnRoot.GetComponent<Button>();
                    if (mb != null && ours != null && ours.interactable != mb.interactable) ours.interactable = mb.interactable;
                }
                catch { }
            }
            var cg = _btnRoot.GetComponent<CanvasGroup>();
            if (cg == null) { if (!faded && a >= 1f) return; cg = _btnRoot.AddComponent<CanvasGroup>(); }
            if (cg.alpha != a) cg.alpha = a;
            if (cg.blocksRaycasts == faded) cg.blocksRaycasts = !faded;
        }

        /// <summary>El boton "Manual online" de la sala (por su texto, en el idioma del juego).</summary>
        static float _nextWideSearch;
        static RectTransform FindManual()
        {
            try
            {
                string label = null;
                var lt = TextManager.Instance?.LangText;
                if (lt != null && lt.ContainsKey("ctg_outgame_inTheRoom_button_onlineManual")) label = lt["ctg_outgame_inTheRoom_button_onlineManual"];
                if (string.IsNullOrEmpty(label)) return null;
                label = label.Trim();
                // primero solo en el lienzo de la sala (buscar en todo el juego tarda)
                if (_menu != null)
                    foreach (var t in _menu.transform.root.GetComponentsInChildren<TextMeshProUGUI>(false))
                    {
                        if (t == null || t.text == null || t.text.Trim() != label) continue;
                        var b = t.GetComponentInParent<Button>();
                        if (b != null) return b.GetComponent<RectTransform>();
                    }
                if (Time.unscaledTime < _nextWideSearch) return null;
                _nextWideSearch = Time.unscaledTime + 10f;
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<TextMeshProUGUI>()))
                {
                    var t = o.TryCast<TextMeshProUGUI>();
                    if (t == null || !t.gameObject.activeInHierarchy || t.text == null || t.text.Trim() != label) continue;
                    var b = t.GetComponentInParent<Button>();
                    if (b != null) return b.GetComponent<RectTransform>();
                }
            }
            catch { }
            return null;
        }

        /// <summary>"Selector de personajes" -> "Selector" arriba y "de personajes" debajo (la primera palabra sola).</summary>
        static string BtnText()
        {
            string t = TBtn[_lang];
            int sp = t.IndexOf(' ');
            return sp > 0 ? t.Substring(0, sp) + "\n" + t.Substring(sp + 1) : t;
        }

        static void MakeButton()
        {
            if (_btnRoot != null) UnityEngine.Object.Destroy(_btnRoot);
            _btnRoot = null; _btnImg = null; _manual = null;
            try { _lang = Math.Max(0, Math.Min(10, (int)TextManager.Instance.GetLangType())); } catch { _lang = 1; }
            var manual = FindManual();
            if (manual != null && CloneManual(manual)) return;
            OwnButton();
        }

        static bool CloneManual(RectTransform manual)
        {
            try
            {
                var srcLabel = manual.GetComponentInChildren<TextMeshProUGUI>(true);
                TMP_FontAsset font = srcLabel != null ? srcLabel.font : Skin.Get().Font;
                Material fontMat = srcLabel != null ? srcLabel.fontSharedMaterial : null;
                Color ink = srcLabel != null ? srcLabel.color : Color.black;
                // la copia se hace dentro de un objeto apagado: asi los scripts del juego que lleva no llegan a arrancar
                var holder = new GameObject("CSR_Copia");
                holder.SetActive(false);
                holder.transform.SetParent(manual.parent, false);
                var go = UnityEngine.Object.Instantiate(manual.gameObject, holder.transform, false);
                go.name = "CSR_SelectorPersonajes";
                // fuera textos y scripts del juego (el que pone "Manual online" y su accion); se quedan la imagen y el boton
                foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<TextMeshProUGUI>(), true))
                {
                    try
                    {
                        var t = c.TryCast<TextMeshProUGUI>();
                        if (t == null) continue;
                        if (t.gameObject.Pointer == go.Pointer) UnityEngine.Object.DestroyImmediate(t);
                        else UnityEngine.Object.DestroyImmediate(t.gameObject);
                    }
                    catch { }
                }
                foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<MonoBehaviour>(), true))
                {
                    var mb = c.TryCast<MonoBehaviour>();
                    if (mb == null) continue;
                    string tn = mb.GetIl2CppType().Name;
                    if (tn != "Image" && tn != "Button" && tn != "RawImage" && tn != "Mask" && tn != "RectMask2D") UnityEngine.Object.DestroyImmediate(mb);
                }
                var rt = go.GetComponent<RectTransform>();
                Place(rt, manual);
                Vector2 ms = manual.rect.size;
                var btn = go.GetComponent<Button>();
                if (btn != null)
                {
                    btn.onClick = new Button.ButtonClickedEvent();
                    btn.onClick.AddListener(Il2CppInterop.Runtime.DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction>(new Action(() =>
                    {
                        try { if (_root == null && !Covered()) Open(); } catch (Exception e) { Plugin.L.LogWarning("[Selector] " + e.Message); }
                    })));
                }
                var icon = ModOffer.Box("Icono", rt, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 28), new Vector2(40, 40));
                var ri = icon.gameObject.AddComponent<RawImage>();
                ri.texture = Silhouette(); ri.color = ink; ri.raycastTarget = false;
                var lbl = ModOffer.Label(rt, BtnText(), font, 17, new Vector2(0, -22), new Vector2(BtnSize.x - 56, 56));
                if (fontMat != null) lbl.fontSharedMaterial = fontMat;
                lbl.color = ink;
                lbl.enableAutoSizing = true; lbl.fontSizeMin = 10; lbl.fontSizeMax = 17;
                lbl.enableWordWrapping = false;
                lbl.lineSpacing = -8f;
                lbl.raycastTarget = false;
                go.transform.SetParent(manual.parent, false);
                rt.SetSiblingIndex(manual.GetSiblingIndex());
                UnityEngine.Object.Destroy(holder);
                go.SetActive(true);
                _btnRoot = go; _btnRect = rt; _manual = manual; _ownCanvas = false;
                Plugin.L.LogInfo($"[Selector] boton a la izquierda de \"Manual online\" (manual {ms.x:0}x{ms.y:0}, boton en {rt.anchoredPosition.x:0},{rt.anchoredPosition.y:0})");
                return true;
            }
            catch (Exception e)
            {
                Plugin.L.LogWarning("[Selector] no pude copiar el boton del manual: " + e.Message);
                if (_btnRoot != null) UnityEngine.Object.Destroy(_btnRoot);
                _btnRoot = null;
                return false;
            }
        }

        /// <summary>A la izquierda del manual, centrado en su altura (en el mismo contenedor, medido en su espacio).</summary>
        static void Place(RectTransform rt, RectTransform manual)
        {
            var parent = manual.parent;
            var mr = manual.rect;
            Vector3 lo = parent.InverseTransformPoint(manual.TransformPoint(new Vector3(mr.xMin, mr.yMin, 0f)));
            Vector3 hi = parent.InverseTransformPoint(manual.TransformPoint(new Vector3(mr.xMax, mr.yMax, 0f)));
            var right = new Vector2(Math.Min(lo.x, hi.x) - 14f, (lo.y + hi.y) / 2f);    // punto del contenedor
            var pr = parent.GetComponent<RectTransform>();
            Vector2 pc = pr != null ? pr.rect.center : Vector2.zero;
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.pivot = new Vector2(1f, 0.5f);
            rt.sizeDelta = BtnSize;
            rt.localScale = Vector3.one;
            rt.anchoredPosition = right - pc;
        }

        /// <summary>Sin el boton del manual: uno propio arriba a la derecha (donde suele estar).</summary>
        static void OwnButton()
        {
            var sk = Skin.Get();
            _btnRoot = new GameObject("CSR_SelectorBoton");
            UnityEngine.Object.DontDestroyOnLoad(_btnRoot);
            var canvas = _btnRoot.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 90;
            var scaler = _btnRoot.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 0.5f;
            _btnRoot.AddComponent<GraphicRaycaster>();
            _btnImg = sk.MakeButton(_btnRoot.transform, "", false, Vector2.zero, BtnSize, 18, out _btnRect, out var empty);
            UnityEngine.Object.Destroy(empty.gameObject);
            _btnRect.anchorMin = _btnRect.anchorMax = new Vector2(1f, 1f);
            _btnRect.anchoredPosition = new Vector2(-720, -78);
            _btnBase = _btnImg.color;
            var icon = ModOffer.Box("Icono", _btnRect, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 28), new Vector2(40, 40));
            var ri = icon.gameObject.AddComponent<RawImage>();
            ri.texture = Silhouette(); ri.color = sk.BtnSubText; ri.raycastTarget = false;
            var lbl = sk.MakeText(_btnRect, BtnText(), 17, new Vector2(0, -22), new Vector2(BtnSize.x - 40, 56), false);
            lbl.color = sk.BtnSubText;
            lbl.enableAutoSizing = true; lbl.fontSizeMin = 10; lbl.fontSizeMax = 17;
            lbl.enableWordWrapping = false;
            lbl.lineSpacing = -8f;
            lbl.raycastTarget = false;
            _ownCanvas = true;
            Plugin.L.LogInfo("[Selector] no encuentro \"Manual online\": boton propio arriba a la derecha");
        }

        // ------------------------------------------------------------ ventana
        const int Cols = 4, Rows = 2, PerPage = Cols * Rows;
        static GameObject _root;
        static Skin _sk;
        static readonly List<Item> _items = new();
        static bool _host;
        static int _min = 6, _page, _hover = -1, _shown = -2;
        static TextMeshProUGUI _status, _pageLabel, _previewName, _previewNote;
        static RectTransform _prevRect, _nextRect, _saveRect, _cancelRect;
        static Image _prevImg, _nextImg, _saveImg, _cancelImg;
        static Color _prevBase, _nextBase, _saveBase, _cancelBase;
        static RawImage _preview, _previewPic;
        static Rig _rig;
        static readonly Dictionary<string, GameObject> _models = new();
        static readonly Dictionary<string, Models.Preview> _pvs = new();
        static string BaseOf(Item it) => Array.IndexOf(Roster.Pawns, it.animFrom) >= 0 ? it.animFrom : "PawnTypeData_A";
        static readonly List<UnityEngine.Object> _made = new();
        static readonly HashSet<string> _noModel = new();
        static float _angle;
        static int _waiting = -1;
        static readonly HashSet<string> _prepared = new();
        static bool _dirty;

        class Card { public RectTransform rect; public Image bg, box; public RawImage pic, tick; public TextMeshProUGUI name, tag; public Color baseColor; }
        static readonly Card[] _cards = new Card[PerPage];

        static bool ReadPool()
        {
            _items.Clear();
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(PoolFile, Encoding.UTF8));
                var r = doc.RootElement;
                _host = r.TryGetProperty("host", out var h) && h.ValueKind == JsonValueKind.True;
                _min = r.TryGetProperty("min", out var m) && m.ValueKind == JsonValueKind.Number ? m.GetInt32() : 6;
                if (r.TryGetProperty("items", out var arr) && arr.ValueKind == JsonValueKind.Array)
                    foreach (var e in arr.EnumerateArray())
                    {
                        string S(string k) => e.TryGetProperty(k, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
                        var it = new Item { id = S("id"), key = S("key"), role = S("role") ?? "pawn", name = S("name"), image = S("image"), model = S("model"),
                                            animFrom = S("anim_from"), enabled = !e.TryGetProperty("enabled", out var en) || en.ValueKind != JsonValueKind.False };
                        if (string.IsNullOrEmpty(it.id) || it.role != "pawn") continue;        // el traidor: mas adelante
                        it.orig = it.id.StartsWith("orig:", StringComparison.Ordinal);
                        _items.Add(it);
                    }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Selector] roster_pool.json: " + e.Message); return false; }
            return _items.Count > 0;
        }

        static string NameOf(Item it)
        {
            if (it.orig)
            {
                int i = Array.IndexOf(Roster.Pawns, it.key);
                return i >= 0 ? Roster.OrigName(i) : TOrigTraitor[_lang];
            }
            if (!string.IsNullOrWhiteSpace(it.name)) return it.name;
            return it.role == "traitor" ? TTraitor[_lang] : TNew[_lang];
        }

        static readonly Dictionary<string, Texture2D> _pics = new();

        /// <summary>Imagen de la ficha: la del personaje, el retrato original guardado o la silueta.</summary>
        static Texture2D PicOf(Item it)
        {
            if (_pics.TryGetValue(it.id, out var have) && have != null) return have;
            Texture2D t = null;
            if (it.orig && it.key == Roster.Traitor)
            {
                t = Roster.LoadImage(Roster.FacePath(it.key));
                if (t == null) _autoPics.TryGetValue("orig:" + it.key, out t);
                if (t == null) AskPic(it);
            }
            else if (it.orig)
            {
                t = ColorCard(it.key, out bool later) ?? Roster.LoadImage(Roster.MonoPath(it.key));
                if (later) { _picsChanged = true; return t; }           // la de color, en otro fotograma
            }
            else if (!string.IsNullOrEmpty(it.image)) t = Roster.LoadImage(Path.Combine(LiveMods.LiveDir, it.image));
            if (t != null) _pics[it.id] = t;
            return t;                                   // un personaje nuevo sin imagen: la silueta, hasta que le pongan una
        }

        /// <summary>La ficha sin marcar: en blanco y negro (la cara del juego en blanco y negro si aun no hay la de color).</summary>
        static Texture2D OffPic(Item it, Texture2D on)
        {
            if (on == null) return null;
            if (it.orig && it.key != Roster.Traitor) return Roster.LoadImage(Roster.MonoPath(it.key)) ?? Gray(on);   // la del juego
            return Gray(on);
        }

        // donde cae el dibujo en color (el de los dialogos, la mitad de grande) dentro de la cara en blanco y negro del
        // juego: escala y desplazamiento en pixeles (medido comparando los dos dibujos, que son el mismo)
        static readonly Dictionary<string, (float s, float x, float y)> ColorFit = new()
        {
            ["PawnTypeData_A"] = (2.005f, -85, -3), ["PawnTypeData_B"] = (1.86f, -217, -2), ["PawnTypeData_C"] = (2.005f, -70, -3),
            ["PawnTypeData_D"] = (2.0f, -80, -5), ["PawnTypeData_E"] = (2.0f, -79, -18), ["PawnTypeData_F"] = (2.005f, -14, -2),
        };
        static readonly Dictionary<string, Texture2D> _colorCards = new();

        /// <summary>La cara del juego, en color: el dibujo en color puesto exactamente encima de la de blanco y negro
        /// (mismo tamano y encuadre), con la forma de esta.</summary>
        static int _cardFrame;
        static Texture2D ColorCard(string key, out bool later)
        {
            later = false;
            if (_colorCards.TryGetValue(key, out var have) && have != null) return have;
            if (_cardFrame == Time.frameCount) { later = File.Exists(Roster.ColorPath(key)); return null; }   // una por fotograma
            _cardFrame = Time.frameCount;
            var mono = Roster.LoadImage(Roster.MonoPath(key));
            var col = Roster.LoadImage(Roster.ColorPath(key));
            if (mono == null || col == null || !ColorFit.TryGetValue(key, out var fit)) return null;
            try
            {
                var mp = Roster.Pixels(mono); var cp = Roster.Pixels(col);
                int W = mono.width, H = mono.height, cw = col.width, ch = col.height;
                var px = new Color32[W * H];
                for (int y = 0; y < H; y++)
                {
                    float cyTop = ((H - 1 - y) - fit.y) / fit.s;                  // filas contadas desde arriba
                    float cy = ch - 1 - cyTop;
                    for (int x = 0; x < W; x++)
                    {
                        var m = mp[y * W + x];
                        if (m.a == 0) continue;
                        float cx = (x - fit.x) / fit.s;
                        if (cx < -1 || cy < -1 || cx > cw || cy > ch) continue;
                        var c = Roster.Bilinear(cp, cw, ch, cx, cy);
                        c.a = (byte)(c.a * m.a / 255);
                        px[y * W + x] = c;
                    }
                }
                var t = new Texture2D(W, H, TextureFormat.RGBA32, false) { hideFlags = HideFlags.DontUnloadUnusedAsset, wrapMode = TextureWrapMode.Clamp };
                Px.Set(t, px);
                _colorCards[key] = t;
                return t;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Selector] cara en color de " + key + ": " + e.Message); return null; }
        }

        // fotos sacadas del modelo (el traidor original; personajes nuevos sin imagen): se guardan mientras dure el juego
        static readonly Dictionary<string, Texture2D> _autoPics = new();
        static readonly HashSet<string> _asked = new();
        static bool _picsChanged;

        /// <summary>La cara del traidor original, sacada de su modelo (solo la primera vez: luego se guarda).</summary>
        static void AskPic(Item it)
        {
            if (!it.orig || it.key != Roster.Traitor || !_asked.Add(it.key)) return;
            bool ok = Roster.SnapTraitorFace(tex =>
            {
                _autoPics["orig:" + it.key] = tex;
                _pics[it.id] = tex;
                _picsChanged = true;
            });
            if (!ok) _asked.Remove(it.key);
        }

        // la misma imagen en blanco y negro (fichas sin marcar)
        static readonly Dictionary<IntPtr, Texture2D> _grays = new();
        static Texture2D Gray(Texture2D t)
        {
            if (t == null) return null;
            if (_grays.TryGetValue(t.Pointer, out var g) && g != null) return g;
            try
            {
                var src = Px.Get(t);
                var px = new Color32[src.Length];
                for (int i = 0; i < px.Length; i++)
                {
                    var c = src[i];
                    byte v = (byte)Math.Min(255, (int)(c.r * 0.3f + c.g * 0.59f + c.b * 0.11f));
                    px[i] = new Color32(v, v, v, c.a);
                }
                g = new Texture2D(t.width, t.height, TextureFormat.RGBA32, false) { hideFlags = HideFlags.DontUnloadUnusedAsset, wrapMode = TextureWrapMode.Clamp };
                Px.Set(g, px);
            }
            catch { g = t; }
            _grays[t.Pointer] = g;
            return g;
        }

        static void Open()
        {
            Close();
            if (!ReadPool()) return;
            try
            {
                try { _lang = Math.Max(0, Math.Min(10, (int)TextManager.Instance.GetLangType())); } catch { _lang = 1; }
                _sk = Skin.Get();
                _page = 0; _hover = -1; _shown = -2; _dirty = false;
                _root = new GameObject("CSR_Selector");
                UnityEngine.Object.DontDestroyOnLoad(_root);
                var canvas = _root.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvas.sortingOrder = 32000;
                var scaler = _root.AddComponent<CanvasScaler>();
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920, 1080);
                scaler.matchWidthOrHeight = 0.5f;
                _root.AddComponent<GraphicRaycaster>();
                var dim = ModOffer.Box("Dim", _root.transform, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
                dim.gameObject.AddComponent<Image>().color = new Color(0f, 0f, 0f, 0.82f);
                var panel = _sk.MakePanel(_root.transform, new Vector2(1600, 920)).transform;
                // fondo solido: que no se vea la sala a traves de la ventana
                var back = ModOffer.Box("Fondo", panel, Vector2.zero, Vector2.one, Vector2.zero, new Vector2(-28, -28));
                back.gameObject.AddComponent<Image>().color = new Color(0.045f, 0.05f, 0.075f, 0.96f);
                back.SetAsFirstSibling();
                _sk.MakeText(panel, TBtn[_lang], 40, new Vector2(0, 410), new Vector2(1500, 60), true);
                _status = _sk.MakeText(panel, "", 22, new Vector2(-230, 355), new Vector2(1060, 56), false);
                _status.enableWordWrapping = true;

                var cardSize = new Vector2(232, 318);
                for (int k = 0; k < PerPage; k++)
                {
                    int col = k % Cols, row = k / Cols;
                    var pos = new Vector2(-690 + col * 250, 160 - row * 336);
                    var cd = new Card();
                    cd.bg = _sk.MakeButton(panel, "", false, pos, cardSize, 18, out cd.rect, out var lbl);
                    UnityEngine.Object.Destroy(lbl.gameObject);
                    cd.baseColor = cd.bg.color;
                    var picR = ModOffer.Box("Imagen", cd.rect, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 28), new Vector2(200, 220));
                    cd.pic = picR.gameObject.AddComponent<RawImage>();
                    cd.pic.raycastTarget = false;
                    cd.name = _sk.MakeText(cd.rect, "", 22, new Vector2(0, -114), new Vector2(216, 40), true);
                    cd.name.enableAutoSizing = true; cd.name.fontSizeMin = 12; cd.name.fontSizeMax = 22;
                    cd.name.raycastTarget = false;
                    cd.tag = _sk.MakeText(cd.rect, "", 16, new Vector2(0, -142), new Vector2(216, 24), false);
                    cd.tag.raycastTarget = false;
                    var boxR = ModOffer.Box("Casilla", cd.rect, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(26, -26), new Vector2(40, 40));
                    cd.box = boxR.gameObject.AddComponent<Image>();
                    cd.box.color = new Color(0.05f, 0.06f, 0.1f, 0.85f);
                    cd.box.raycastTarget = false;
                    var frame = ModOffer.Box("Borde", boxR, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero).gameObject.AddComponent<RawImage>();
                    frame.texture = BoxTex(); frame.raycastTarget = false;
                    var tickR = ModOffer.Box("Marca", boxR, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
                    cd.tick = tickR.gameObject.AddComponent<RawImage>();
                    cd.tick.texture = TickTex();
                    cd.tick.color = GameWindow.Amber;
                    cd.tick.raycastTarget = false;
                    _cards[k] = cd;
                }

                // vista 3D a la derecha
                var pv = ModOffer.Box("Vista", panel, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(530, 20), new Vector2(440, 600));
                pv.gameObject.AddComponent<Image>().color = new Color(0.03f, 0.035f, 0.06f, 0.9f);
                _previewPic = ModOffer.Box("Retrato", pv, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 40), new Vector2(360, 400)).gameObject.AddComponent<RawImage>();
                _previewPic.raycastTarget = false;
                _preview = ModOffer.Box("Modelo", pv, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero).gameObject.AddComponent<RawImage>();
                _preview.raycastTarget = false;
                _rig = Rig.Make("CSR_SelectorVista", new Vector3(5000, -6000, 0));
                _rig.Size(440, 600, new Color(0.03f, 0.035f, 0.06f, 1f));
                _preview.texture = _rig.rt;
                _previewName = _sk.MakeText(panel, "", 30, new Vector2(530, -315), new Vector2(440, 44), true);
                _previewNote = _sk.MakeText(pv, "", 18, new Vector2(0, -250), new Vector2(400, 60), false);
                _previewNote.enableWordWrapping = true;

                // paginas y botones
                var sb = new Vector2(80, 60);
                _prevImg = _sk.MakeButton(panel, "<", false, new Vector2(-480, -372), sb, 30, out _prevRect, out _);
                _pageLabel = _sk.MakeText(panel, "", 24, new Vector2(-315, -372), new Vector2(200, 50), false);
                _nextImg = _sk.MakeButton(panel, ">", false, new Vector2(-150, -372), sb, 30, out _nextRect, out _);
                var bs = new Vector2(250, 64);
                if (_host)
                {
                    _saveImg = _sk.MakeButton(panel, TSave[_lang], true, new Vector2(400, -390), bs, 26, out _saveRect, out _);
                    _cancelImg = _sk.MakeButton(panel, TCancel[_lang], false, new Vector2(665, -390), bs, 26, out _cancelRect, out _);
                }
                else _cancelImg = _sk.MakeButton(panel, TClose[_lang], false, new Vector2(665, -390), bs, 26, out _cancelRect, out _);
                _prevBase = _prevImg.color; _nextBase = _nextImg.color; _cancelBase = _cancelImg.color;
                if (_saveImg != null) _saveBase = _saveImg.color;
                SetStatus(null);
                Fill();
                Plugin.L.LogInfo($"[Selector] abierto ({_items.Count} personajes, {(_host ? "anfitrion" : "solo ver")})");
            }
            catch (Exception e)
            {
                Plugin.L.LogWarning("[Selector] no pude ensenar la ventana: " + e);
                Close();
            }
        }

        static int Pages => Math.Max(1, (_items.Count + PerPage - 1) / PerPage);

        static void SetStatus(string warn)
        {
            if (_status == null) return;
            _status.text = warn ?? (_host ? THost[_lang] : TGuest[_lang]);
            _status.color = warn != null ? new Color(1f, 0.45f, 0.4f, 1f) : _sk.Body;
        }

        static void Fill()
        {
            for (int k = 0; k < PerPage; k++)
            {
                int i = _page * PerPage + k;
                var cd = _cards[k];
                bool has = i < _items.Count;
                cd.rect.gameObject.SetActive(has);
                if (!has) continue;
                var it = _items[i];
                var tex = PicOf(it);
                cd.pic.texture = tex == null ? Silhouette() : it.enabled ? tex : OffPic(it, tex);
                cd.pic.color = tex != null ? Color.white : it.enabled ? new Color(0.55f, 0.58f, 0.7f, 1f) : new Color(0.5f, 0.5f, 0.5f, 1f);
                BasePic(cd.pic, tex != null ? (Texture)tex : Silhouette());
                cd.name.text = NameOf(it);
                cd.tag.text = it.role == "traitor" ? (it.orig ? "" : TTraitor[_lang]) : (it.orig ? "" : TNew[_lang]);
                cd.tag.color = it.role == "traitor" ? new Color(1f, 0.42f, 0.38f, 1f) : new Color(0.6f, 0.85f, 1f, 1f);
                cd.tick.gameObject.SetActive(it.enabled);
                cd.bg.color = it.enabled ? cd.baseColor : Color.Lerp(cd.baseColor, Color.black, 0.45f);
            }
            if (_pageLabel != null) _pageLabel.text = (_page + 1) + " / " + Pages;
            bool many = Pages > 1;
            _prevRect.gameObject.SetActive(many); _nextRect.gameObject.SetActive(many); _pageLabel.gameObject.SetActive(many);
        }

        /// <summary>La imagen entera dentro de su recuadro, sin deformarla (recortando lo que sobre).</summary>
        // la base del hexagono de la ficha (medido en pantalla: el dibujo del boton deja margen arriba y abajo)
        const float HexBottom = -82f, PicWidth = 200f, PicMaxHeight = 250f;

        /// <summary>La imagen entera, sin recortar, con su base sobre la base del hexagono (la cabeza puede salir por
        /// arriba, como en las fichas del juego).</summary>
        static void BasePic(RawImage ri, Texture tex)
        {
            var rt = ri.rectTransform;
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.pivot = new Vector2(0.5f, 0f);
            rt.anchoredPosition = new Vector2(0f, HexBottom);
            float w = PicWidth, h = PicWidth;
            if (tex != null && tex.width > 0 && tex.height > 0)
            {
                h = w * tex.height / tex.width;
                if (h > PicMaxHeight) { w *= PicMaxHeight / h; h = PicMaxHeight; }
            }
            rt.sizeDelta = new Vector2(w, h);
            ri.uvRect = new Rect(0, 0, 1, 1);
        }

        static void FitPic(RawImage ri, Texture tex, Vector2 box)
        {
            if (tex == null || tex.width <= 0 || tex.height <= 0) { ri.uvRect = new Rect(0, 0, 1, 1); return; }
            float a = tex.width / (float)tex.height, b = box.x / box.y;
            if (a > b) { float w = b / a; ri.uvRect = new Rect((1 - w) / 2f, 0, w, 1); }
            else { float h = a / b; ri.uvRect = new Rect(0, 1 - h - (1 - h) * 0.25f, 1, h); }
        }

        static bool Over(RectTransform r, Vector2 m) => r != null && r.gameObject.activeInHierarchy && RectTransformUtility.RectangleContainsScreenPoint(r, m, null);

        static void WindowFrame()
        {
            Vector2 mouse = Input.mousePosition;
            int over = -1;
            for (int k = 0; k < PerPage; k++)
            {
                var cd = _cards[k];
                if (cd == null || !cd.rect.gameObject.activeSelf) continue;
                int i = _page * PerPage + k;
                bool o = Over(cd.rect, mouse);
                if (o) over = i;
                var c = _items[i].enabled ? cd.baseColor : Color.Lerp(cd.baseColor, Color.black, 0.45f);
                cd.bg.color = o ? Skin.Hover(c) : c;
            }
            if (over >= 0) _hover = over;
            if (_hover != _shown) ShowPreview(_hover);
            else if (_waiting >= 0 && _waiting == _shown) ShowPreview(_shown);      // modelo preparandose
            // los modelos de los personajes nuevos se preparan en segundo plano nada mas abrir la ventana
            for (int k = 0; k < _items.Count; k++)
            {
                var pit = _items[k];
                if (!pit.orig && !string.IsNullOrEmpty(pit.model) && !_prepared.Contains(pit.id))
                {
                    if (Models.Prefit(pit.model, BaseOf(pit))) _prepared.Add(pit.id);
                    break;                                          // uno por fotograma
                }
            }
            if (_rig?.content != null)
            {
                _angle += Time.unscaledDeltaTime * 30f;
                _rig.content.transform.localRotation = Quaternion.Euler(0, _angle, 0);
                if (_shown >= 0 && _shown < _items.Count && _pvs.TryGetValue(_items[_shown].id, out var pv)) Models.PreviewTick(pv, Time.unscaledTime);
            }
            if (_picsChanged) { _picsChanged = false; Fill(); if (_shown >= 0 && _rig?.content == null) ShowPreview(_shown); }
            Hover(_prevImg, _prevBase, _prevRect, mouse); Hover(_nextImg, _nextBase, _nextRect, mouse);
            Hover(_saveImg, _saveBase, _saveRect, mouse); Hover(_cancelImg, _cancelBase, _cancelRect, mouse);
            if (Input.GetKeyDown(KeyCode.Escape)) { Close(); return; }
            if (!Input.GetMouseButtonDown(0)) return;
            if (over >= 0) Toggle(over);
            else if (Over(_prevRect, mouse)) { _page = (_page + Pages - 1) % Pages; Fill(); }
            else if (Over(_nextRect, mouse)) { _page = (_page + 1) % Pages; Fill(); }
            else if (Over(_saveRect, mouse)) Save();
            else if (Over(_cancelRect, mouse)) Close();
        }

        static void Hover(Image img, Color c, RectTransform r, Vector2 m) { if (img != null) img.color = Over(r, m) ? Skin.Hover(c) : c; }

        static void Toggle(int i)
        {
            if (!_host) { SetStatus(TGuest[_lang]); return; }
            var it = _items[i];
            if (it.enabled)
            {
                int pawns = 0, traitors = 0;
                foreach (var x in _items) if (x.enabled) { if (x.role == "traitor") traitors++; else pawns++; }
                if (it.role == "traitor" && traitors <= 1) { SetStatus(TNeedTraitor[_lang]); return; }
                if (it.role != "traitor" && pawns <= _min) { SetStatus(string.Format(TNeedPawns[_lang], _min)); return; }
            }
            it.enabled = !it.enabled;
            _dirty = true;
            SetStatus(null);
            Fill();
        }

        static void ShowPreview(int i)
        {
            _shown = i;
            if (_rig == null) return;
            if (_rig.content != null) { _rig.content.SetActive(false); _rig.content = null; }
            _rig.cam.enabled = false;
            _preview.gameObject.SetActive(false);
            _previewPic.gameObject.SetActive(false);
            _previewNote.text = "";
            if (i < 0 || i >= _items.Count) { _previewName.text = ""; return; }
            var it = _items[i];
            _previewName.text = NameOf(it);
            bool ready = it.orig || string.IsNullOrEmpty(it.model) || Models.Prefit(it.model, BaseOf(it));
            _waiting = ready ? -1 : i;
            var go = ready ? ModelOf(it) : null;
            if (go != null)
            {
                go.SetActive(true);
                _rig.content = go;
                go.transform.SetParent(_rig.root.transform, false);
                go.transform.localPosition = Vector3.zero;
                go.transform.localRotation = Quaternion.Euler(0, _angle, 0);
                foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = Rig.Layer;
                var rot = go.transform.localRotation;
                go.transform.localRotation = Quaternion.identity;
                _rig.Aim();
                go.transform.localRotation = rot;
                _rig.cam.enabled = true;
                _preview.gameObject.SetActive(true);
                return;
            }
            var tex = PicOf(it);
            _previewPic.texture = tex != null ? (Texture)tex : Silhouette();
            _previewPic.color = tex != null ? Color.white : new Color(0.55f, 0.58f, 0.7f, 1f);
            FitPic(_previewPic, tex, new Vector2(360, 400));
            _previewPic.gameObject.SetActive(true);
            if (it.orig) _previewNote.text = TNoModel[_lang];
            else if (!ready) _previewNote.text = TLoading[_lang];
        }

        /// <summary>El modelo 3D de un personaje para la vista (se guarda mientras la ventana esta abierta).</summary>
        static GameObject ModelOf(Item it)
        {
            if (_models.TryGetValue(it.id, out var have) && have != null) return have;
            if (_noModel.Contains(it.id)) return null;
            GameObject go = null;
            try
            {
                // en reposo, con la animacion del juego; un modelo propio, montado como en la partida
                Models.Preview pv = null;
                if (it.orig) pv = Models.PreviewChar(it.key, null, Rig.Layer);
                else if (!string.IsNullOrEmpty(it.model)) pv = Models.PreviewChar(BaseOf(it), it.model, Rig.Layer);
                if (pv != null) { go = pv.holder; _pvs[it.id] = pv; }
                else if (!it.orig && !string.IsNullOrEmpty(it.model)) go = Models.PreviewGlb(it.model, Rig.Layer, _made);   // quieto
            }
            catch (Exception e) { Plugin.L.LogWarning("[Selector] vista de " + it.id + ": " + e.Message); }
            if (go == null) { _noModel.Add(it.id); return null; }
            go.SetActive(false);
            go.transform.SetParent(_rig.root.transform, false);
            _models[it.id] = go;
            return go;
        }

        static void Save()
        {
            if (!_host) return;
            var off = new List<string>();
            foreach (var it in _items) if (!it.enabled) off.Add(it.id);
            try
            {
                var sb = new StringBuilder("{\"n\": ").Append(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()).Append(", \"disabled\": [");
                for (int i = 0; i < off.Count; i++) sb.Append(i > 0 ? ", " : "").Append(JsonSerializer.Serialize(off[i]));
                sb.Append("]}");
                File.WriteAllText(SelectFile + ".part", sb.ToString(), new UTF8Encoding(false));
                File.Copy(SelectFile + ".part", SelectFile, true);
                File.Delete(SelectFile + ".part");
                Plugin.L.LogInfo("[Selector] guardado: " + (off.Count == 0 ? "todos" : off.Count + " sin marcar"));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Selector] no pude guardar: " + e.Message); SetStatus(e.Message); return; }
            Close();
            Toast(TSaved[_lang]);
        }

        static void Close()
        {
            foreach (var pv in _pvs.Values) Models.PreviewDestroy(pv);
            _pvs.Clear();
            foreach (var go in _models.Values) if (go != null) UnityEngine.Object.Destroy(go);
            _models.Clear();
            foreach (var o in _made) if (o != null) UnityEngine.Object.Destroy(o);
            _made.Clear();
            _noModel.Clear();
            if (_rig != null) { _rig.content = null; _rig.Destroy(); _rig = null; }
            if (_root != null) UnityEngine.Object.Destroy(_root);
            _root = null;
            _status = _pageLabel = _previewName = _previewNote = null;
            _prevRect = _nextRect = _saveRect = _cancelRect = null;
            _prevImg = _nextImg = _saveImg = _cancelImg = null;
            _preview = _previewPic = null;
            for (int k = 0; k < PerPage; k++) _cards[k] = null;
            _pics.Clear();
        }

        // aviso corto arriba en el centro
        static GameObject _toast;
        static void Toast(string text)
        {
            try
            {
                if (_toast != null) UnityEngine.Object.Destroy(_toast);
                _toast = new GameObject("CSR_SelectorAviso");
                UnityEngine.Object.DontDestroyOnLoad(_toast);
                var canvas = _toast.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvas.sortingOrder = 31000;
                var scaler = _toast.AddComponent<CanvasScaler>();
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920, 1080);
                scaler.matchWidthOrHeight = 0.5f;
                var sk = Skin.Get();
                var box = ModOffer.Box("Fondo", _toast.transform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -170), new Vector2(760, 60));
                box.gameObject.AddComponent<Image>().color = new Color(0.05f, 0.06f, 0.1f, 0.88f);
                var t = sk.MakeText(box, text, 24, Vector2.zero, new Vector2(740, 52), false);
                t.color = Color.white;
                UnityEngine.Object.Destroy(_toast, 4f);
            }
            catch { }
        }

        // ------------------------------------------------------------ dibujos (silueta, casilla, marca)
        static Texture2D _silhouette, _box, _tick;

        static Texture2D Draw(int n, Func<float, float, float> cover)
        {
            var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { hideFlags = HideFlags.DontUnloadUnusedAsset, wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[n * n];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float a = Mathf.Clamp01(cover(x + 0.5f, y + 0.5f));
                    px[y * n + x] = new Color32(255, 255, 255, (byte)(a * 255));
                }
            t.SetPixels32(px);
            t.Apply();
            return t;
        }

        /// <summary>Silueta de una persona (cabeza y hombros), blanca sobre transparente.</summary>
        internal static Texture2D Silhouette()
        {
            if (_silhouette != null) return _silhouette;
            const int n = 128;
            _silhouette = Draw(n, (x, y) =>
            {
                float head = 24f - Vector2.Distance(new Vector2(x, y), new Vector2(64, 86));
                // hombros: media elipse ancha abajo
                float dx = (x - 64) / 48f, dy = (y - 8) / 50f;
                float body = (1f - Mathf.Sqrt(dx * dx + dy * dy)) * 40f;
                if (y > 58) body = Math.Min(body, 58 - y + 1);
                return Math.Max(head, body) + 0.5f;
            });
            return _silhouette;
        }

        static Texture2D BoxTex()
        {
            if (_box != null) return _box;
            const int n = 48;
            _box = Draw(n, (x, y) =>
            {
                float d = Math.Min(Math.Min(x, n - x), Math.Min(y, n - y));
                return d < 4f ? 1f : (d < 5f ? 5f - d : 0f);
            });
            return _box;
        }

        static Texture2D TickTex()
        {
            if (_tick != null) return _tick;
            const int n = 48;
            var a = new Vector2(11, 25); var b = new Vector2(20, 14); var c = new Vector2(38, 35);
            _tick = Draw(n, (x, y) =>
            {
                var p = new Vector2(x, y);
                float d = Math.Min(Seg(p, a, b), Seg(p, b, c));
                return 4.2f - d;
            });
            return _tick;
        }

        static float Seg(Vector2 p, Vector2 a, Vector2 b)
        {
            var ab = b - a;
            float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
            return Vector2.Distance(p, a + ab * t);
        }
    }
}
