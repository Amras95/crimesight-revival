// CRIMESIGHT Revival - "Character Selector" in the waiting room.
//
// A button (a person's silhouette with "Character Selector" below) opens a window with every character
// that can appear in the room: the original ones and the new ones each player brings. Each one has its image, its
// name below and a box on the left to let it appear or not; hovering over it shows its 3D model
// on the right, spinning. In each match 6 are drawn at random among the ticked ones (with the same probability), so
// there must be at least 6 characters and 1 traitor.
// The host decides: their choice goes to csr_live/roster_select.json, the launcher passes it to the server and it
// applies
// to their room (and next time). The others see the window without being able to change it.
// The launcher writes the list in csr_live/roster_pool.json; without that file (without a new launcher) there is no
// button.
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
        // game languages: ja, en, fr, it, de, es, pt, ru, ko, zh-cn, zh-tw
        static readonly string[] TBtn = { "キャラクター選択", "Character Selection", "Sélection des personnages", "Selezione dei personaggi",
            "Figurenauswahl", "Selección de personajes", "Seleção de personagens", "Выбор персонажей", "캐릭터 선택", "角色选择", "角色選擇" };
        static readonly string[] THost = {
            "毎試合、チェックしたキャラから6人がランダムに選ばれます。6人以上チェックしてください。",
            "Each match picks 6 of the ticked characters at random. Keep at least 6 ticked.",
            "Chaque partie tire au hasard 6 des personnages cochés. Gardez-en au moins 6 cochés.",
            "Ogni partita sceglie a caso 6 dei personaggi spuntati. Tienine spuntati almeno 6.",
            "Jede Partie wählt zufällig 6 der angehakten Figuren. Lass mindestens 6 angehakt.",
            "Cada partida elige al azar 6 de los personajes marcados. Deja al menos 6 marcados.",
            "Cada partida escolhe ao acaso 6 dos personagens marcados. Deixe pelo menos 6 marcados.",
            "В каждом матче случайно выбираются 6 из отмеченных персонажей. Оставьте отмеченными не меньше 6.",
            "매 판 체크한 캐릭터 중 6명이 무작위로 나옵니다. 6명 이상 체크해 두세요.",
            "每局从勾选的角色中随机选出 6 人。请至少勾选 6 人。",
            "每局從勾選的角色中隨機選出 6 人。請至少勾選 6 人。" };
        static readonly string[] TGuest = { "出場キャラを変更できるのはホストだけです。", "Only the host can change which characters can appear.",
            "Seul l'hôte peut choisir les personnages qui peuvent apparaître.", "Solo l'host può scegliere quali personaggi possono comparire.",
            "Nur der Host kann festlegen, welche Figuren erscheinen können.", "Solo el anfitrión puede elegir qué personajes pueden salir.",
            "Só o anfitrião pode escolher quais personagens podem aparecer.", "Выбирать персонажей может только хозяин комнаты.",
            "출전할 캐릭터는 방장만 바꿀 수 있습니다.", "只有房主可以更改能出场的角色。", "只有房主可以變更能出場的角色。" };
        static readonly string[] TNeedPawns = { "キャラは{0}人以上チェックしてください。", "Keep at least {0} characters ticked.",
            "Gardez au moins {0} personnages cochés.", "Tieni spuntati almeno {0} personaggi.", "Lass mindestens {0} Figuren angehakt.",
            "Deja al menos {0} personajes marcados.", "Deixe pelo menos {0} personagens marcados.", "Оставьте отмеченными не меньше {0} персонажей.",
            "캐릭터를 {0}명 이상 체크해 두세요.", "请至少勾选 {0} 名角色。", "請至少勾選 {0} 名角色。" };
        static readonly string[] TNeedTraitor = { "裏切り者は最低1人必要です。", "There must be at least 1 traitor.", "Il faut au moins 1 traître.",
            "Serve almeno 1 traditore.", "Es muss mindestens 1 Verräter sein.", "Tiene que haber al menos 1 traidor.",
            "É preciso ter pelo menos 1 traidor.", "Нужен хотя бы 1 предатель.", "배신자는 최소 1명 필요합니다.", "至少需要 1 名叛徒。", "至少需要 1 名叛徒。" };
        static readonly string[] TCount = { "選択中 {0} / {1}", "{0} of {1} ticked", "{0} sur {1} cochés", "{0} su {1} spuntati",
            "{0} von {1} angehakt", "{0} de {1} marcados", "{0} de {1} marcados", "Отмечено: {0} из {1}", "{0} / {1} 선택됨", "已勾选 {0} / {1}", "已勾選 {0} / {1}" };
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

        // ------------------------------------------------------------ button in the waiting room
        // It is a copy of the "Online manual" button in the room's header (same look and same canvas), right
        // to its left, with a person's silhouette and the text below. If it isn't found, it goes in a corner.
        static GameObject _btnRoot;
        static RectTransform _btnRect;
        static RectTransform _manual;
        static bool _ownCanvas;
        static Image _btnImg;
        static Color _btnBase;
        static float _nextLook;
        static OutGameRoomWaitingMenuVer2 _menu;
        static bool _menuOpen;
        static bool _btnOver;
        static bool _btnFaded;      // the room is seen behind a window: the button stays, like the manual's, unpressable
        static readonly Vector2 BtnSize = new Vector2(176, 118);

        public static void Frame()
        {
            if (_root != null)
            {
                if (!_host) WatchHost();
                if (_root != null) WindowFrame();
                return;
            }
            if (Time.unscaledTime >= _nextLook)
            {
                _nextLook = Time.unscaledTime + 0.15f;                // like the gamepad icons (Pad.UiScan)
                _menuOpen = MenuVisible();
                // The room shows even with a window on top (settings, confirmations, AI difficulty...): the
                // button stays like the manual one next to it (the game darkens both), unpressable.
                // With a window on top only if the manual one shows: outside the room the game leaves it loaded.
                bool want = File.Exists(PoolFile) && (_menuOpen || (RoomShown() && ManualSeen(_manual != null ? _manual : FindManual())));
                if (want && (_btnRoot == null || (!_ownCanvas && _manual == null) || (_ownCanvas && FindManual() != null))) MakeButton();
                if (_btnRoot != null) _btnRoot.SetActive(want);
                if (want && !_ownCanvas && _btnRoot != null && _manual != null) Place(_btnRect, _manual);
                if (want && _btnRoot != null) FadeButton(Covered());
            }
            if (_btnRoot == null || !_btnRoot.activeSelf || !_ownCanvas) return;
            // on our canvas (without the game's): mouse by hand
            bool over = !_btnFaded && RectTransformUtility.RectangleContainsScreenPoint(_btnRect, Input.mousePosition, null);
            if (over && !_btnOver) Sfx(AudioManager.PlayOutGameMouseOverButton);
            _btnOver = over;
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

        /// <summary>The waiting room is visible (even if there is a window on top).</summary>
        static bool RoomShown()
        {
            try { return _menu != null && _menu.gameObject.activeInHierarchy; }
            catch { _menu = null; return false; }
        }

        /// <summary>The manual button is visible (active and without a CanvasGroup hiding it).</summary>
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

        /// <summary>There is a window over the room (or it isn't the active screen): the button can't be
        /// pressed.</summary>
        static bool Covered()
        {
            if (!_menuOpen) return true;
            try { return _menu.IsOverlaySomeUI(); } catch { return true; }
        }

        /// <summary>With the room covered the button takes no clicks and looks exactly like the manual one next to
        /// it: they are
        /// in the same place, so whatever the game darkens darkens both, and on top of that what the manual one has
        /// is copied (its transparency and whether it is disabled).</summary>
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

        /// <summary>The room's "Online manual" button (by its text, in the game's language).</summary>
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
                // first only in the room's canvas (searching the whole game is slow)
                if (_menu != null)
                    foreach (var t in _menu.transform.root.GetComponentsInChildren<TextMeshProUGUI>(false))
                    {
                        if (t == null || t.text == null || t.text.Trim() != label) continue;
                        var b = t.GetComponentInParent<Button>();
                        if (b != null && !InSettings(b.transform)) return b.GetComponent<RectTransform>();
                    }
                if (Time.unscaledTime < _nextWideSearch) return null;
                _nextWideSearch = Time.unscaledTime + 10f;
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<TextMeshProUGUI>()))
                {
                    var t = o.TryCast<TextMeshProUGUI>();
                    if (t == null || !t.gameObject.activeInHierarchy || t.text == null || t.text.Trim() != label) continue;
                    var b = t.GetComponentInParent<Button>();
                    if (b != null && !InSettings(b.transform)) return b.GetComponent<RectTransform>();
                }
            }
            catch { }
            return null;
        }

        /// <summary>The Settings window has its own "Online Manual" button (same text): that one isn't the room's.</summary>
        static bool InSettings(Transform t)
        {
            try
            {
                for (; t != null; t = t.parent)
                    if (t.GetComponent<OutGameOptionMainPopup>() != null) return true;
            }
            catch { }
            return false;
        }

        /// <summary>"Character Selector" -> "Character" on top and "Selector" below (the first word alone).</summary>
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
                // the copy is made inside a disabled object: that way the game scripts it carries never start
                var holder = new GameObject("CSR_Copia");
                holder.SetActive(false);
                holder.transform.SetParent(manual.parent, false);
                var go = UnityEngine.Object.Instantiate(manual.gameObject, holder.transform, false);
                go.name = "CSR_SelectorPersonajes";
                // remove the game's texts and scripts (the one that sets "Online manual" and its action); the image
                // and the button stay
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
                    try { UIScriptingHelper.SetMouseOverSoundEvent(btn); } catch { }   // the copy loses the game's hover sound
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

        /// <summary>To the left of the manual, centred on its height (in the same container, measured in its
        /// space).</summary>
        static void Place(RectTransform rt, RectTransform manual)
        {
            var parent = manual.parent;
            var mr = manual.rect;
            Vector3 lo = parent.InverseTransformPoint(manual.TransformPoint(new Vector3(mr.xMin, mr.yMin, 0f)));
            Vector3 hi = parent.InverseTransformPoint(manual.TransformPoint(new Vector3(mr.xMax, mr.yMax, 0f)));
            var right = new Vector2(Math.Min(lo.x, hi.x) - 14f, (lo.y + hi.y) / 2f);    // container point
            var pr = parent.GetComponent<RectTransform>();
            Vector2 pc = pr != null ? pr.rect.center : Vector2.zero;
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.pivot = new Vector2(1f, 0.5f);
            rt.sizeDelta = BtnSize;
            rt.localScale = Vector3.one;
            rt.anchoredPosition = right - pc;
        }

        /// <summary>Without the manual button: one of our own at the top right (where it usually is).</summary>
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

        // ------------------------------------------------------------ window
        const int Cols = 4, Rows = 2, PerPage = Cols * Rows;
        static GameObject _root;
        static Skin _sk;
        static readonly List<Item> _items = new();
        static bool _host;
        static int _min = 6, _page, _hover = -1, _shown = -2;
        static TextMeshProUGUI _status, _pageLabel, _previewName, _previewNote, _count;
        static GameWindow _gw;              // the game's window, copied (null: the plugin's own dark window)
        static Color _ink = Color.white;    // text color on the window
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
                        if (string.IsNullOrEmpty(it.id) || it.role != "pawn") continue;        // the traitor: further on
                        it.orig = it.id.StartsWith("orig:", StringComparison.Ordinal);
                        _items.Add(it);
                    }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Selector] roster_pool.json: " + e.Message); return false; }
            // The launcher rewrites the pool a moment after a save: opening the window again before that showed the
            // previous choice (and saving it again undid the change). A save newer than the pool wins.
            try
            {
                if (_host && File.Exists(SelectFile) && File.GetLastWriteTimeUtc(SelectFile) > File.GetLastWriteTimeUtc(PoolFile))
                {
                    using var sel = JsonDocument.Parse(File.ReadAllText(SelectFile, Encoding.UTF8));
                    var off = new HashSet<string>();
                    if (sel.RootElement.TryGetProperty("disabled", out var d) && d.ValueKind == JsonValueKind.Array)
                        foreach (var x in d.EnumerateArray()) if (x.ValueKind == JsonValueKind.String) off.Add(x.GetString());
                    foreach (var it in _items) it.enabled = !off.Contains(it.id);
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Selector] roster_select.json: " + e.Message); }
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

        /// <summary>Card image: the character's, the saved original portrait or the silhouette.</summary>
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
                if (later) { _picsChanged = true; return t; }           // the colour one, in another frame
            }
            else if (!string.IsNullOrEmpty(it.image)) t = Roster.LoadImage(Path.Combine(LiveMods.LiveDir, it.image));
            if (t != null) _pics[it.id] = t;
            return t;                                   // a new character without an image: the silhouette, until one is given
        }

        /// <summary>The unticked card: in black and white (the game's black and white face if there is no colour one
        /// yet).</summary>
        static Texture2D OffPic(Item it, Texture2D on)
        {
            if (on == null) return null;
            if (it.orig && it.key != Roster.Traitor) return Roster.LoadImage(Roster.MonoPath(it.key)) ?? Gray(on);   // the game's
            return Gray(on);
        }

        // where the colour drawing (the dialogues', half as big) falls inside the game's black and white
        // face: scale and offset in pixels (measured by comparing the two drawings, which are the same)
        static readonly Dictionary<string, (float s, float x, float y)> ColorFit = new()
        {
            ["PawnTypeData_A"] = (2.005f, -85, -3), ["PawnTypeData_B"] = (1.86f, -217, -2), ["PawnTypeData_C"] = (2.005f, -70, -3),
            ["PawnTypeData_D"] = (2.0f, -80, -5), ["PawnTypeData_E"] = (2.0f, -79, -18), ["PawnTypeData_F"] = (2.005f, -14, -2),
        };
        static readonly Dictionary<string, Texture2D> _colorCards = new();

        /// <summary>The game's face, in colour: the colour drawing placed exactly over the black and white one
        /// (same size and framing), with its shape.</summary>
        static int _cardFrame;
        static Texture2D ColorCard(string key, out bool later)
        {
            later = false;
            if (_colorCards.TryGetValue(key, out var have) && have != null) return have;
            if (_cardFrame == Time.frameCount) { later = File.Exists(Roster.ColorPath(key)); return null; }   // one per frame
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
                    float cyTop = ((H - 1 - y) - fit.y) / fit.s;                  // rows counted from the top
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

        // photos taken from the model (the original traitor; new characters without an image): kept while the game
        // runs
        static readonly Dictionary<string, Texture2D> _autoPics = new();
        static readonly HashSet<string> _asked = new();
        static bool _picsChanged;

        /// <summary>The original traitor's face, taken from its model (only the first time: then it is
        /// saved).</summary>
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

        // the same image in black and white (unticked cards)
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
                    px[i] = Px.C(v, v, v, c.a);
                }
                g = new Texture2D(t.width, t.height, TextureFormat.RGBA32, false) { hideFlags = HideFlags.DontUnloadUnusedAsset, wrapMode = TextureWrapMode.Clamp };
                Px.Set(g, px);
            }
            catch { g = t; }
            _grays[t.Pointer] = g;
            return g;
        }

        // Opened read-only just before the launcher knew you created the room: as soon as its list says you can
        // change it, the window opens again, editable (no need to close it and open it again).
        static DateTime _poolTime;
        static float _nextPoolLook;
        static bool _reopening;

        static DateTime PoolStamp()
        {
            try { return File.GetLastWriteTimeUtc(PoolFile); } catch { return default; }
        }

        static void WatchHost()
        {
            if (Time.unscaledTime < _nextPoolLook) return;
            _nextPoolLook = Time.unscaledTime + 0.25f;
            var t = PoolStamp();
            if (t == _poolTime) return;
            _poolTime = t;
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(PoolFile, Encoding.UTF8));
                if (!doc.RootElement.TryGetProperty("host", out var h) || h.ValueKind != JsonValueKind.True) return;
            }
            catch { return; }
            _reopening = true;
            try { Open(); } finally { _reopening = false; }
            Plugin.L.LogInfo("[Selector] you created this room: now editable");
        }

        static void Open()
        {
            Close();
            var stamp = PoolStamp();             // before reading: a change made meanwhile is still seen
            if (!ReadPool()) return;
            _poolTime = stamp;
            _nextPoolLook = Time.unscaledTime + 0.25f;
            try
            {
                try { _lang = Math.Max(0, Math.Min(10, (int)TextManager.Instance.GetLangType())); } catch { _lang = 1; }
                _sk = Skin.Get();
                _page = 0; _hover = -1; _shown = -2; _dirty = false; _hot = -1;
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
                dim.gameObject.AddComponent<Image>().color = new Color(0f, 0f, 0f, 0.75f);
                _gw = null;
                if (!BuildNative()) BuildOwn();
                SetStatus(null);
                Fill();
                if (!_reopening) Sfx(AudioManager.PlayOutGameWindowOpen);
                Plugin.L.LogInfo($"[Selector] abierto ({_items.Count} personajes, {(_host ? "anfitrion" : "solo ver")})");
            }
            catch (Exception e)
            {
                Plugin.L.LogWarning("[Selector] no pude ensenar la ventana: " + e);
                Close();
            }
        }

        // The cards (left) and the 3D view (right) are laid out in their own units and scaled to fit the window.
        const float ContentW = 1462f, ContentH = 740f;

        /// <summary>The game's own window (green title band, paper, framed box, game buttons), made bigger.</summary>
        static bool BuildNative()
        {
            var gw = GameWindow.Create(_root.transform);
            if (gw == null) return false;
            _gw = gw;
            gw.SetText(gw.Title, TBtn[_lang]);
            var box = gw.BodyBox;
            _ink = gw.Body.color;
            const float pad = 16f;
            float fs = gw.Body.fontSize, headH = fs * 1.8f;
            // The window is sized around what goes in it: the cards and the view take 60% of the screen's width
            // (less if the window would get too tall), plus the header line and margins.
            Rect scr = gw.ScreenRect(), win = gw.Bounds(), boxNow = GameWindow.RectIn(gw.Root, box);
            float k = box.rect.width > 0f ? boxNow.width / box.rect.width : 1f;            // box units -> window units
            float chrome = win.height - boxNow.height, extraH = (headH + 2.5f * pad) * k;
            float wantW = scr.width * 0.6f, wantH = wantW * ContentH / ContentW;
            float maxH = scr.height * 0.9f - chrome - extraH;
            if (wantH > maxH) { wantH = maxH; wantW = wantH * ContentW / ContentH; }
            gw.Resize(new Vector2(wantW + 2f * pad * k, wantH + extraH));
            float bw = box.rect.width, bh = box.rect.height;
            float top = bh / 2f - pad - headH - pad * 0.5f, bottom = -bh / 2f + pad;
            float s = Math.Max(0.1f, Math.Min((bw - 2f * pad) / ContentW, (top - bottom) / ContentH));
            float cw = ContentW * s, countW = cw * 0.24f, headY = bh / 2f - pad - headH / 2f;
            // header: what to do on the left, how many are ticked on the right (lined up with the cards and the view)
            var d = gw.Body.rectTransform;
            d.anchorMin = d.anchorMax = d.pivot = new Vector2(0.5f, 0.5f);
            d.sizeDelta = new Vector2(cw - countW, headH);
            d.anchoredPosition = new Vector2(-countW / 2f, headY);
            gw.Body.alignment = TextAlignmentOptions.MidlineLeft;
            gw.Body.enableWordWrapping = true;
            gw.Body.enableAutoSizing = true;
            gw.Body.fontSizeMax = fs;
            gw.Body.fontSizeMin = Math.Min(14f, fs);
            _status = gw.Body;
            _count = ModOffer.Label(box, "", gw.Body.font, fs, new Vector2(cw / 2f - countW / 2f, headY), new Vector2(countW, headH));
            if (gw.Body.fontSharedMaterial != null) _count.fontSharedMaterial = gw.Body.fontSharedMaterial;
            _count.color = _ink;
            _count.alignment = TextAlignmentOptions.MidlineRight;
            _count.enableWordWrapping = false;
            _count.fontSizeMin = Math.Min(14f, fs);
            var content = ModOffer.Box("Content", box, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
                                       new Vector2(0f, (top + bottom) / 2f), new Vector2(ContentW, ContentH));
            content.localScale = new Vector3(s, s, 1f);
            BuildContent(content);
            if (_host)
            {
                _saveImg = gw.AddBottomButton(TSave[_lang], false, 0, 2, GameWindow.Amber, out _saveRect, out _);
                _cancelImg = gw.AddBottomButton(TCancel[_lang], false, 1, 2, null, out _cancelRect, out _);
            }
            else _cancelImg = gw.AddBottomButton(TClose[_lang], false, 0, 1, null, out _cancelRect, out _);
            return true;
        }

        /// <summary>Without the game's window (e.g. it isn't loaded): the plugin's own dark window.</summary>
        static void BuildOwn()
        {
            _ink = _sk.Body;
            var panel = _sk.MakePanel(_root.transform, new Vector2(1600, 920)).transform;
            // solid back: the room doesn't show through the window
            var back = ModOffer.Box("Back", panel, Vector2.zero, Vector2.one, Vector2.zero, new Vector2(-28, -28));
            back.gameObject.AddComponent<Image>().color = new Color(0.045f, 0.05f, 0.075f, 0.96f);
            back.SetAsFirstSibling();
            _sk.MakeText(panel, TBtn[_lang], 40, new Vector2(0, 410), new Vector2(1500, 60), true);
            // header lined up with the cards and the view below (content at 0.9 scale: x from -658 to 658)
            _status = _sk.MakeText(panel, "", 22, new Vector2(-139, 358), new Vector2(1038, 50), false);
            _status.alignment = TextAlignmentOptions.MidlineLeft;
            _status.enableWordWrapping = true;
            _count = _sk.MakeText(panel, "", 24, new Vector2(519, 358), new Vector2(278, 50), false);
            _count.alignment = TextAlignmentOptions.MidlineRight;
            _count.enableWordWrapping = false;
            var content = ModOffer.Box("Content", panel, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, -10), new Vector2(ContentW, ContentH));
            content.localScale = new Vector3(0.9f, 0.9f, 1f);
            BuildContent(content);
            var bs = new Vector2(250, 64);
            if (_host)
            {
                _saveImg = _sk.MakeButton(panel, TSave[_lang], true, new Vector2(-135, -395), bs, 26, out _saveRect, out _);
                _cancelImg = _sk.MakeButton(panel, TCancel[_lang], false, new Vector2(135, -395), bs, 26, out _cancelRect, out _);
            }
            else _cancelImg = _sk.MakeButton(panel, TClose[_lang], false, new Vector2(0, -395), bs, 26, out _cancelRect, out _);
            _cancelBase = _cancelImg.color;
            if (_saveImg != null) _saveBase = _saveImg.color;
        }

        /// <summary>Text on the window itself (the game's paper or the dark panel), in the window's ink.</summary>
        static TextMeshProUGUI InkText(Transform parent, string text, float size, Vector2 pos, Vector2 box)
        {
            var t = _sk.MakeText(parent, text, size, pos, box, true);
            if (_gw != null && _gw.Body != null)
            {
                t.font = _gw.Body.font;
                if (_gw.Body.fontSharedMaterial != null) t.fontSharedMaterial = _gw.Body.fontSharedMaterial;
                t.color = _ink;
            }
            return t;
        }

        /// <summary>Cards in a 4x2 grid with the page arrows under them, and the 3D view on the right.</summary>
        static void BuildContent(RectTransform content)
        {
            var cardSize = new Vector2(232, 318);
            for (int k = 0; k < PerPage; k++)
            {
                int col = k % Cols, row = k / Cols;
                var pos = new Vector2(-615 + col * 250, 211 - row * 336);
                var cd = new Card();
                cd.bg = _sk.MakeButton(content, "", false, pos, cardSize, 18, out cd.rect, out var lbl);
                UnityEngine.Object.Destroy(lbl.gameObject);
                cd.baseColor = cd.bg.color;
                var picR = ModOffer.Box("Image", cd.rect, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 28), new Vector2(200, 220));
                cd.pic = picR.gameObject.AddComponent<RawImage>();
                cd.pic.raycastTarget = false;
                cd.name = _sk.MakeText(cd.rect, "", 22, new Vector2(0, -114), new Vector2(216, 40), true);
                cd.name.enableAutoSizing = true; cd.name.fontSizeMin = 12; cd.name.fontSizeMax = 22;
                cd.name.raycastTarget = false;
                cd.name.color = new Color(0.07f, 0.07f, 0.09f, 1f);        // black: the window background is light
                cd.tag = _sk.MakeText(cd.rect, "", 16, new Vector2(0, -142), new Vector2(216, 24), false);
                cd.tag.raycastTarget = false;
                var boxR = ModOffer.Box("Box", cd.rect, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(26, -26), new Vector2(40, 40));
                cd.box = boxR.gameObject.AddComponent<Image>();
                cd.box.color = new Color(0.05f, 0.06f, 0.1f, 0.85f);
                cd.box.raycastTarget = false;
                var frame = ModOffer.Box("Frame", boxR, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero).gameObject.AddComponent<RawImage>();
                frame.texture = BoxTex(); frame.raycastTarget = false;
                var tickR = ModOffer.Box("Tick", boxR, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
                cd.tick = tickR.gameObject.AddComponent<RawImage>();
                cd.tick.texture = TickTex();
                cd.tick.color = GameWindow.Amber;
                cd.tick.raycastTarget = false;
                _cards[k] = cd;
            }

            // page arrows under the grid
            var sb = new Vector2(110, 60);
            if (_gw != null)
            {
                _prevImg = _gw.AddButton("<", false, content, new Vector2(-405, -335), sb, null, out _prevRect, out _);
                _nextImg = _gw.AddButton(">", false, content, new Vector2(-75, -335), sb, null, out _nextRect, out _);
            }
            else
            {
                _prevImg = _sk.MakeButton(content, "<", false, new Vector2(-405, -335), sb, 30, out _prevRect, out _);
                _nextImg = _sk.MakeButton(content, ">", false, new Vector2(-75, -335), sb, 30, out _nextRect, out _);
            }
            _pageLabel = InkText(content, "", 26, new Vector2(-240, -335), new Vector2(200, 50));
            _prevBase = _prevImg != null ? _prevImg.color : Color.white;
            _nextBase = _nextImg != null ? _nextImg.color : Color.white;

            // 3D view on the right, the name under it
            var pv = ModOffer.Box("View", content, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(511, 70), new Vector2(440, 600));
            pv.gameObject.AddComponent<Image>().color = new Color(0.03f, 0.035f, 0.06f, 0.95f);
            _previewPic = ModOffer.Box("Portrait", pv, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 40), new Vector2(360, 400)).gameObject.AddComponent<RawImage>();
            _previewPic.raycastTarget = false;
            _preview = ModOffer.Box("Model", pv, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero).gameObject.AddComponent<RawImage>();
            _preview.raycastTarget = false;
            _rig = Rig.Make("CSR_SelectorVista", new Vector3(5000, -6000, 0));
            _rig.Size(440, 600, new Color(0.03f, 0.035f, 0.06f, 1f));
            _preview.texture = _rig.rt;
            _previewName = InkText(content, "", 32, new Vector2(511, -268), new Vector2(440, 50));
            _previewNote = _sk.MakeText(pv, "", 18, new Vector2(0, -250), new Vector2(400, 60), false);
            _previewNote.enableWordWrapping = true;
        }

        static void SetText(TextMeshProUGUI t, string s) { if (_gw != null) _gw.SetText(t, s); else t.text = s; }

        static int Pages => Math.Max(1, (_items.Count + PerPage - 1) / PerPage);

        static void SetStatus(string warn)
        {
            if (_status == null) return;
            string t = warn ?? (_host ? THost[_lang] : TGuest[_lang]);
            if (_gw != null) _gw.SetText(_status, t); else _status.text = t;
            bool darkInk = _ink.r * 0.3f + _ink.g * 0.59f + _ink.b * 0.11f < 0.5f;     // light paper: a darker red reads better
            _status.color = warn == null ? _ink : darkInk ? new Color(0.75f, 0.12f, 0.1f, 1f) : new Color(1f, 0.45f, 0.4f, 1f);
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
                cd.name.color = new Color(0.07f, 0.07f, 0.09f, 1f);
                cd.tag.text = it.role == "traitor" ? (it.orig ? "" : TTraitor[_lang]) : (it.orig ? "" : TNew[_lang]);
                cd.tag.color = it.role == "traitor" ? new Color(0.75f, 0.15f, 0.12f, 1f) : new Color(0.1f, 0.35f, 0.72f, 1f);
                cd.tick.gameObject.SetActive(it.enabled);
                cd.bg.color = it.enabled ? cd.baseColor : Color.Lerp(cd.baseColor, Color.black, 0.45f);
            }
            if (_pageLabel != null) SetText(_pageLabel, (_page + 1) + " / " + Pages);
            if (_count != null)
            {
                int on = 0;
                foreach (var x in _items) if (x.enabled) on++;
                SetText(_count, string.Format(TCount[_lang], on, _items.Count));
            }
            bool many = Pages > 1;
            _prevRect.gameObject.SetActive(many); _nextRect.gameObject.SetActive(many); _pageLabel.gameObject.SetActive(many);
        }

        /// <summary>The whole image inside its box, without distorting it (cropping what is left over).</summary>
        // the base of the card's hexagon (measured on screen: the button drawing leaves a margin above and below)
        const float HexBottom = -82f, PicWidth = 200f, PicMaxHeight = 250f;

        /// <summary>The whole image, uncropped, with its base on the hexagon's base (the head can stick out at
        /// the top, like in the game's cards).</summary>
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
            else if (_waiting >= 0 && _waiting == _shown) ShowPreview(_shown);      // model being prepared
            // the new characters' models are prepared in the background as soon as the window opens
            for (int k = 0; k < _items.Count; k++)
            {
                var pit = _items[k];
                if (!pit.orig && !string.IsNullOrEmpty(pit.model) && !_prepared.Contains(pit.id))
                {
                    if (Models.Prefit(pit.model, BaseOf(pit))) _prepared.Add(pit.id);
                    break;                                          // one per frame
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
            _gw?.KeepTexts();
            // the game's hover sound when the mouse reaches a card or a button
            int hot = over >= 0 ? over : Over(_prevRect, mouse) ? -2 : Over(_nextRect, mouse) ? -3 : Over(_saveRect, mouse) ? -4 : Over(_cancelRect, mouse) ? -5 : -1;
            if (hot != _hot) { _hot = hot; if (hot != -1) Sfx(AudioManager.PlayOutGameMouseOverButton); }
            if (Input.GetKeyDown(KeyCode.Escape)) { Sfx(AudioManager.PlayOutGameCancel); Close(); return; }
            // mouse wheel: next / previous page (stops at the first and last page)
            float wheel = Input.mouseScrollDelta.y;
            if (Pages > 1 && Math.Abs(wheel) > 0.01f)
            {
                int to = Math.Max(0, Math.Min(Pages - 1, _page + (wheel < 0f ? 1 : -1)));
                if (to != _page) { _page = to; Fill(); Sfx(AudioManager.PlayOutGameNormalClick); }
            }
            if (!Input.GetMouseButtonDown(0)) return;
            if (over >= 0) Toggle(over);
            else if (Over(_prevRect, mouse)) { _page = (_page + Pages - 1) % Pages; Fill(); Sfx(AudioManager.PlayOutGameNormalClick); }
            else if (Over(_nextRect, mouse)) { _page = (_page + 1) % Pages; Fill(); Sfx(AudioManager.PlayOutGameNormalClick); }
            else if (Over(_saveRect, mouse)) Save();
            else if (Over(_cancelRect, mouse)) { Sfx(AudioManager.PlayOutGameCancel); Close(); }
        }

        static int _hot = -1;

        /// <summary>One of the game's sounds (never breaks the window if the sound system isn't there).</summary>
        static void Sfx(Action play) { try { play(); } catch { } }

        static void Hover(Image img, Color c, RectTransform r, Vector2 m) { if (img != null && _gw == null) img.color = Over(r, m) ? Skin.Hover(c) : c; }

        static void Toggle(int i)
        {
            if (!_host) { SetStatus(TGuest[_lang]); Sfx(AudioManager.PlaySystemNG); return; }
            var it = _items[i];
            if (it.enabled)
            {
                int pawns = 0, traitors = 0;
                foreach (var x in _items) if (x.enabled) { if (x.role == "traitor") traitors++; else pawns++; }
                if (it.role == "traitor" && traitors <= 1) { SetStatus(TNeedTraitor[_lang]); Sfx(AudioManager.PlaySystemNG); return; }
                if (it.role != "traitor" && pawns <= _min) { SetStatus(string.Format(TNeedPawns[_lang], _min)); Sfx(AudioManager.PlaySystemNG); return; }
            }
            it.enabled = !it.enabled;
            bool on = it.enabled;
            Sfx(() => AudioManager.PlayToggleCheck(on));
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

        /// <summary>A character's 3D model for the view (kept while the window is open).</summary>
        static GameObject ModelOf(Item it)
        {
            if (_models.TryGetValue(it.id, out var have) && have != null) return have;
            if (_noModel.Contains(it.id)) return null;
            GameObject go = null;
            try
            {
                // at idle, with the game's animation; a custom model, assembled like in the match
                Models.Preview pv = null;
                if (it.orig) pv = Models.PreviewChar(it.key, null, Rig.Layer);
                else if (!string.IsNullOrEmpty(it.model)) pv = Models.PreviewChar(BaseOf(it), it.model, Rig.Layer);
                if (pv != null) { go = pv.holder; _pvs[it.id] = pv; }
                else if (!it.orig && !string.IsNullOrEmpty(it.model)) go = Models.PreviewGlb(it.model, Rig.Layer, _made);   // still
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
            Sfx(AudioManager.PlayOutGameDecideClick);
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
            _status = _pageLabel = _previewName = _previewNote = _count = null;
            _gw = null;
            _prevRect = _nextRect = _saveRect = _cancelRect = null;
            _prevImg = _nextImg = _saveImg = _cancelImg = null;
            _preview = _previewPic = null;
            for (int k = 0; k < PerPage; k++) _cards[k] = null;
            _pics.Clear();
        }

        // short notice at the top centre
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

        // ------------------------------------------------------------ drawings (silhouette, box, tick)
        static Texture2D _silhouette, _box, _tick;

        static Texture2D Draw(int n, Func<float, float, float> cover)
        {
            var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { hideFlags = HideFlags.DontUnloadUnusedAsset, wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[n * n];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float a = cover(x + 0.5f, y + 0.5f); a = a < 0 ? 0 : a > 1 ? 1 : a;
                    px[y * n + x] = Px.C(255, 255, 255, (byte)(a * 255));
                }
            t.SetPixels32(px);
            t.Apply();
            return t;
        }

        /// <summary>A person's silhouette (head and shoulders), white on transparent.</summary>
        internal static Texture2D Silhouette()
        {
            if (_silhouette != null) return _silhouette;
            const int n = 128;
            _silhouette = Draw(n, (x, y) =>
            {
                float head = 24f - (float)Math.Sqrt((x - 64) * (x - 64) + (y - 86) * (y - 86));
                // shoulders: wide half ellipse at the bottom
                float dx = (x - 64) / 48f, dy = (y - 8) / 50f;
                float body = (1f - (float)Math.Sqrt(dx * dx + dy * dy)) * 40f;
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
            _tick = Draw(n, (x, y) => 4.2f - Math.Min(Seg(x, y, 11, 25, 20, 14), Seg(x, y, 20, 14, 38, 35)));
            return _tick;
        }

        static float Seg(float px, float py, float ax, float ay, float bx, float by)
        {
            float abx = bx - ax, aby = by - ay;
            float t = ((px - ax) * abx + (py - ay) * aby) / (abx * abx + aby * aby);
            t = t < 0 ? 0 : t > 1 ? 1 : t;
            float dx = px - (ax + abx * t), dy = py - (ay + aby * t);
            return (float)Math.Sqrt(dx * dx + dy * dy);
        }
    }
}
