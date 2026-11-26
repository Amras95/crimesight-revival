// CRIMESIGHT Revival - the detective team (Sherlocks and Watsons) can see each other's icons in the player list
// (room setting).
//
// In the player list (bottom right) the original game shows your own icon, Irene's to Moriarty and Moriarty's to
// Irene (Hud.SetPlayersInfoRoleIrene/Moriarty), but never the detectives' to each other. That stays the default. The
// host can turn on "Reveal Partner (Detective Team)" in the room's Match Settings: then, each time the game fills in
// the icons (Hud.SetPlayersInfoRoleAll/Own), every Sherlock and Watson sees the Sherlock or Watson icon of every
// member of the detective team. Moriarty's side sees nothing new. The games don't know the others' roles, so they
// are taken from the room's member list (each member carries its role).
//
// The setting travels with the room settings as "partner_icons" (RoomSettings.GetParam). The Revival server keeps it
// and tells every game in the room with "CsrPartnerIcons" (Team.cs), when someone enters, when the settings change
// and when a match starts. The row in the window is a copy of the "Increase Action Speed" row (Off / On), with
// Sherlock's diamond icon.
//
// The furniture map for the AI Watson: every turn the game sends the server a summary of the match
// (GameManager.CreateServerReferenceData), but furniture only shows on the squares each character can reach.
// "searchMap": [[furniture, square, x, y, z], ...] with ALL the stage's furniture is added at the start, so
// the AI Watson can point with a "Search" ping right above any spot with food it discovers.
using System;
using System.Text;
using HarmonyLib;
using Il2CppInterop.Runtime;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace CrimeSightRevival.Mods
{
    static class PartnerIcon
    {
        /// <summary>The room's setting, as the server last told it ("CsrPartnerIcons"). Off until it says otherwise.</summary>
        internal static bool RoomValue;
        static bool _warned;

        public static void Init(Harmony h)
        {
            try
            {
                var post = new HarmonyMethod(typeof(PartnerIcon).GetMethod(nameof(AfterRoleAll),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic));
                // SetPlayersInfoRoleOwn: the game calls it when the match starts and in each orders phase;
                // SetPlayersInfoRoleAll: when dealing the roles
                foreach (var name in new[] { nameof(Hud.SetPlayersInfoRoleAll), nameof(Hud.SetPlayersInfoRoleOwn) })
                {
                    var m = AccessTools.DeclaredMethod(typeof(Hud), name);
                    if (m == null) { Plugin.L.LogWarning("[Watson] Hud." + name + " no existe"); continue; }
                    h.Patch(m, postfix: post);
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Watson] " + e.Message); }
            PartnerSetting.Init(h);
            SearchMap.Init(h);
            WatsonFoodPing.Init(h);
        }

        /// <summary>The server's "CsrPartnerIcons": the room's setting ("Show": 1 or 0).</summary>
        internal static void FromServer(string show)
        {
            show = (show ?? "").Trim();
            bool v = show == "1" || string.Equals(show, "true", StringComparison.OrdinalIgnoreCase);
            RoomValue = v;
            PartnerSetting.RoomChanged();
        }

        static void AfterRoleAll(Hud __instance)
        {
            try
            {
                if (!RoomValue) return;                                                // off: as in the original game
                var nm = NetworkManager.Instance;
                if (nm == null || __instance == null) return;
                if (nm.IsCriminal || nm.IsIrene) return;          // only the detective team sees it, never Moriarty's side
                var list = __instance.playersInfo;
                var members = nm.GetCurrentRoom()?.Members;
                var hs = NetworkManager.GetHostSystem();
                if (list == null || members == null || hs == null) return;
                bool on = true;
                // every Sherlock and every Watson of the room, with their icon (the game only knows its own role)
                for (int i = 0; i < members.Count; i++)
                {
                    var x = members[i];
                    if (x == null || x.IsCriminal || x.IsIrene) continue;
                    string id = x.PlayerId;
                    if (string.IsNullOrEmpty(id)) continue;
                    int idx = hs.SearchMemberIndex(ref id);
                    if (idx < 0) continue;
                    list.SetRoleIconActive(ref idx, ref on);
                    if (x.IsWatson) list.SetRoleIconWatson(ref idx);
                    else list.SetRoleIconSherlock(ref idx);
                }
            }
            catch (Exception e)
            {
                if (!_warned) { _warned = true; Plugin.L.LogWarning("[Watson] " + e.Message); }
            }
        }

    }

    /// <summary>The "Reveal Partner (Detective Team)" row (Off / On) in the room's Match Settings window.</summary>
    static class PartnerSetting
    {
        // Game languages (TextManager.GetLangType): ja, en, fr, it, de, es, pt, ru, ko, zh-cn, zh-tw
        static readonly string[] Title =
        {
            "パートナーを表示（探偵チーム）", "Reveal Partner (Detective Team)", "Révéler le partenaire (équipe des détectives)",
            "Mostra il partner (squadra dei detective)", "Partner anzeigen (Detektiv-Team)", "Revelar compañero (equipo detective)",
            "Revelar parceiro (equipe de detetives)", "Показать напарника (команда детективов)", "파트너 공개 (탐정 팀)",
            "显示搭档（侦探阵营）", "顯示搭檔（偵探陣營）",
        };
        // Sherlock's diamond icon from the game's own sprites
        const string IconSprite = "iconRhombus_Sherlock";

        static bool _chosen;                      // what the window shows (and sends with "Apply")
        static OutGameRoomPopupRoomSetting _win;
        static GameObject _row;                   // our copy of the row (or of its title when the row has no parent of its own)
        static TextMeshProUGUI[] _title;          // the title and its copy behind it (the game draws two)
        static Image _icon;
        static bool _iconSet;
        static int _iconTries;
        static Toggle _off, _on;
        static bool _setting, _warned;

        public static void Init(Harmony h)
        {
            try
            {
                var t = typeof(OutGameRoomPopupRoomSetting);
                h.Patch(AccessTools.Method(t, "Start"), postfix: Hm(nameof(AfterStart)));
                var upd = AccessTools.Method(t, "Update");
                if (upd != null) h.Patch(upd, postfix: Hm(nameof(AfterUpdate)));
                var def = AccessTools.Method(t, "ClickDefault");
                if (def != null) h.Patch(def, postfix: Hm(nameof(AfterDefault)));
                h.Patch(AccessTools.Method(typeof(RoomSettings), nameof(RoomSettings.GetParam)), postfix: Hm(nameof(AfterGetParam)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Watson] ajuste: " + e.Message); }
        }

        static HarmonyMethod Hm(string n) => new HarmonyMethod(typeof(PartnerSetting).GetMethod(n,
            System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic));

        static int Lang()
        {
            try { return Math.Max(0, Math.Min(10, (int)TextManager.Instance.GetLangType())); } catch { return 1; }
        }

        static bool Alive() => _win != null && _row != null && _off != null && _on != null;

        /// <summary>The server sent the room's value: an open window that wasn't touched shows it.</summary>
        internal static void RoomChanged()
        {
            try
            {
                if (!Alive() || !_win.gameObject.activeInHierarchy) { _chosen = PartnerIcon.RoomValue; return; }
                _chosen = PartnerIcon.RoomValue;
                Show();
            }
            catch { }
        }

        static void AfterStart(OutGameRoomPopupRoomSetting __instance)
        {
            try
            {
                _win = __instance;
                _chosen = PartnerIcon.RoomValue;
                Build(__instance);
                Show();
            }
            catch (Exception e) { Plugin.L.LogWarning("[Watson] ajuste: " + e.Message); }
        }

        static Transform Tr(Component c) => c != null ? c.transform : null;
        static Transform Tr(GameObject g) => g != null ? g.transform : null;

        /// <summary>Lowest object that holds a and b (null if none below the window).</summary>
        static Transform Common(Transform a, Transform b, Transform stop)
        {
            for (var x = a; x != null && x != stop; x = x.parent)
                for (var y = b; y != null; y = y.parent)
                    if (y == x) return x;
            return null;
        }

        static bool Holds(Transform parent, Transform t)
        {
            for (var x = t; x != null; x = x.parent) if (x == parent) return true;
            return false;
        }

        static void Build(OutGameRoomPopupRoomSetting w)
        {
            if (Alive() && _row.transform.parent != null) return;
            var title = Tr(w.QuickModeTitleTMP);
            var offT = Tr(w.QuickModeOffToggle);
            var onT = Tr(w.QuickModeOnToggle);
            var above = Tr(w.GaspipeCountTitleTMP);
            if (title == null || offT == null || onT == null) { Plugin.L.LogWarning("[Watson] ajuste: no encuentro la fila de velocidad"); return; }

            // the row: the object that holds the title and both buttons, if it holds nothing else of the window
            var row = Common(title, Common(offT, onT, w.transform) ?? offT, w.transform);
            if (row == null || row == w.transform || (above != null && Holds(row, above)))
            {
                Plugin.L.LogWarning("[Watson] ajuste: la fila de velocidad no tiene objeto propio");
                return;
            }
            var copy = UnityEngine.Object.Instantiate(row.gameObject, row.parent, false);
            copy.name = row.name + "_CsrPartnerIcons";
            copy.transform.SetSiblingIndex(row.GetSiblingIndex() + 1);

            // place it one row lower, unless the parent lays out its children itself
            if (row.parent != null && row.parent.GetComponent<LayoutGroup>() == null)
            {
                float step = 0f;
                if (above != null)
                {
                    var a = row.parent.InverseTransformPoint(above.position);
                    var b = row.parent.InverseTransformPoint(title.position);
                    step = b.y - a.y;                       // distance between two rows (negative going down)
                }
                if (Math.Abs(step) < 1f) step = -60f;
                var rt = copy.GetComponent<RectTransform>();
                if (rt != null) rt.anchoredPosition += new Vector2(0f, step);
                else copy.transform.localPosition += new Vector3(0f, step, 0f);
            }

            _row = copy;
            var titles = new System.Collections.Generic.List<TextMeshProUGUI>();
            foreach (var c in copy.GetComponentsInChildren<TextMeshProUGUI>(true))
                if (c != null && c.gameObject.name == title.name) titles.Add(c);
            _title = titles.ToArray();
            _icon = Find<Image>(copy.transform, "Icon");
            _iconSet = false;
            _iconTries = 0;
            SetIcon();
            _off = FindToggle(copy.transform, offT.name);
            _on = FindToggle(copy.transform, onT.name);
            if (_off == null || _on == null)
            {
                Plugin.L.LogWarning("[Watson] ajuste: los botones de la fila no son Toggle");
                UnityEngine.Object.Destroy(copy);
                _row = null;
                return;
            }
            foreach (var tg in new[] { _off, _on })
            {
                tg.group = null;                                 // not tied to the speed buttons
                // Keep the copied persistent calls that play a sound (the click sound lives there) and switch off the
                // rest (calls to the speed setting). Runtime listeners are not copied by Instantiate.
                var ev = tg.onValueChanged;
                int n = ev.GetPersistentEventCount();
                for (int i = 0; i < n; i++)
                {
                    string m = ev.GetPersistentMethodName(i) ?? "";
                    if (!m.StartsWith("Play", StringComparison.Ordinal)) ev.SetPersistentListenerState(i, UnityEngine.Events.UnityEventCallState.Off);
                }
            }
            foreach (var tg in new[] { _off, _on }) HoverSound(tg);
            _off.onValueChanged.AddListener(DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction<bool>>(
                new Action<bool>(v => { if (v && !_setting) Choose(false, true); })));
            _on.onValueChanged.AddListener(DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction<bool>>(
                new Action<bool>(v => { if (v && !_setting) Choose(true, true); })));
        }

        /// <summary>The game's buttons get their hover sound from code (PointerUI actions set at runtime), which the
        /// copy doesn't have: the same sound is set here.</summary>
        static void HoverSound(Toggle tg)
        {
            try
            {
                var pu = tg.GetComponent<PointerUI>() ?? tg.gameObject.AddComponent<PointerUI>();
                pu.PointerEnterAction = DelegateSupport.ConvertDelegate<Il2CppSystem.Action<UnityEngine.EventSystems.PointerEventData>>(
                    new Action<UnityEngine.EventSystems.PointerEventData>(_ =>
                    {
                        if (tg != null && tg.interactable)
                            try { AudioManager.PlayOutGameMouseOverButton(); } catch { }
                    }));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Watson] ajuste: sonido: " + e.Message); }
        }

        /// <summary>Sherlock's diamond icon instead of the copied speed icon.</summary>
        static void SetIcon()
        {
            if (_iconSet || _icon == null) return;
            try
            {
                Sprite best = null;
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<Sprite>()))
                {
                    var sp = o?.TryCast<Sprite>();
                    if (sp == null || sp.name != IconSprite) continue;
                    best = sp;
                    break;
                }
                if (best == null)                              // not loaded yet: tried again a few times while the window is open
                {
                    if (++_iconTries >= 10) { _iconSet = true; Plugin.L.LogWarning("[Watson] ajuste: no encuentro " + IconSprite); }
                    return;
                }
                _icon.sprite = best;
                _icon.preserveAspect = true;
                _iconSet = true;
            }
            catch (Exception e) { _iconSet = true; Plugin.L.LogWarning("[Watson] ajuste: icono: " + e.Message); }
        }

        static T Find<T>(Transform root, string name) where T : Component
        {
            foreach (var c in root.GetComponentsInChildren<T>(true))
                if (c != null && c.gameObject.name == name) return c;
            return null;
        }

        static Toggle FindToggle(Transform root, string name)
        {
            foreach (var t in root.GetComponentsInChildren<Toggle>(true))
                if (t != null && t.gameObject.name == name) return t;
            return null;
        }

        /// <summary>A change in the window. Like the game's own buttons, any change turns "Apply" on (comparing with the
        /// room's value failed when the server's answer to the last "Apply" had not arrived yet).</summary>
        static void Choose(bool v, bool click = false)
        {
            bool changed = v != _chosen;
            _chosen = v;
            Show();
            try { if (_win != null) _win.SetApplyButtonEnable(true); } catch { }
            // the copied buttons don't sound (their "Play" calls aren't the sound): the game's toggle sound
            if (click && changed)
                try { AudioManager.PlayToggleCheck(v); } catch { }
        }

        /// <summary>Both buttons show _chosen.</summary>
        static void Show()
        {
            if (!Alive()) return;
            _setting = true;
            try { _off.isOn = !_chosen; _on.isOn = _chosen; }
            finally { _setting = false; }
        }

        static void AfterUpdate(OutGameRoomPopupRoomSetting __instance)
        {
            try
            {
                if (!Alive() || __instance != _win) return;
                if (_title != null)
                {
                    string want = Title[Lang()];
                    foreach (var t in _title)                                 // the copied title would say "speed" again
                        if (t != null && t.text != want) t.text = want;
                }
                if (!_iconSet && Time.frameCount % 30 == 0) SetIcon();
                // only the host can change it: the same as the speed buttons
                var src = __instance.QuickModeOnToggle != null ? __instance.QuickModeOnToggle.GetComponent<Selectable>() : null;
                if (src != null)
                {
                    if (_on.interactable != src.interactable) _on.interactable = src.interactable;
                    if (_off.interactable != src.interactable) _off.interactable = src.interactable;
                }
                // a click the buttons' own event missed: the clicked one turned on while the other one still is
                if (_off.isOn && _on.isOn) Choose(!_chosen, true);
                else if (_off.isOn == _chosen || _on.isOn != _chosen) Show();
            }
            catch (Exception e)
            {
                if (!_warned) { _warned = true; Plugin.L.LogWarning("[Watson] ajuste: " + e.Message); }
            }
        }

        static void AfterDefault(OutGameRoomPopupRoomSetting __instance)
        {
            try { if (__instance == _win) Choose(false); } catch { }
        }

        static void AfterGetParam(Il2CppSystem.Collections.Generic.Dictionary<string, Il2CppSystem.Object> __result)
        {
            try
            {
                if (__result == null) return;
                var boxed = new Il2CppSystem.Boolean { m_value = _chosen }.BoxIl2CppObject();
                if (__result.ContainsKey("partner_icons")) __result["partner_icons"] = boxed;
                else __result.Add("partner_icons", boxed);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Watson] ajuste: " + e.Message); }
        }
    }

    static class WatsonFoodPing
    {
        const string LogSearch = "ctg_name_log_ping_search";               // "{player}: Searching."
        static readonly string[] Lines = { "ctg_talk_watson_newFoodDetected_mc01_p010_v10",   // first food
                                           "ctg_talk_watson_newFoodDetected_mc02_p010_v10" }; // the following ones
        static string _room;          // room of the current match (to know which is the first food)
        static bool _said, _busy, _warned;

        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.DeclaredMethod(typeof(TextManager), nameof(TextManager.SetMacroText));
                if (m == null) { Plugin.L.LogWarning("[Watson] TextManager.SetMacroText no existe"); return; }
                h.Patch(m, postfix: new HarmonyMethod(typeof(WatsonFoodPing).GetMethod(nameof(AfterMacro),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Watson] " + e.Message); }
        }

        /// <summary>Name of the room's AI Watson (AIs have an id starting with "bot", or a player an AI took over),
        /// or null.</summary>
        static string AiWatsonName(out string room)
        {
            room = null;
            var r = NetworkManager.Instance?.currentRoom;
            var members = r?.Members;
            if (members == null) return null;
            room = r.Id;
            for (int i = 0; i < members.Count; i++)
            {
                var x = members[i];
                if (x != null && x.IsWatson && Team.IsAi(x.PlayerId)) return x.Name;
            }
            return null;
        }

        // A ping's notice is written by putting the sender's name into "{player}: Searching."; if it is the
        // AI Watson, what follows the name becomes its line
        static void AfterMacro(TextManager __instance, ref string __0, ref string __1, ref string __2, ref string __result)
        {
            if (_busy || string.IsNullOrEmpty(__0) || string.IsNullOrEmpty(__2)) return;
            try
            {
                _busy = true;
                string id = LogSearch;
                if (__0 != __instance.GetLangText(ref id)) return;           // it isn't the "Search" notice
                string name = AiWatsonName(out string room);
                if (string.IsNullOrEmpty(name) || !__2.Contains(name)) return;
                string token = (__1 ?? "").StartsWith("{") ? __1 : "{" + __1 + "}";
                int at = __0.IndexOf(token, StringComparison.Ordinal);
                if (at < 0) return;
                if (room != _room) { _room = room; _said = false; }          // new match: the first one again
                string lineId = _said ? Lines[1] : Lines[0];
                string line = __instance.GetLangText(ref lineId);
                if (string.IsNullOrEmpty(line) || line == lineId) return;   // no translation: the original is left
                _said = true;
                // what separates the name from the text in this language (": ", "：", ...)
                string tail = __0.Substring(at + token.Length);
                int k = 0;
                while (k < tail.Length && !char.IsLetterOrDigit(tail[k])) k++;
                string template = __0.Substring(0, at + token.Length) + tail.Substring(0, k)
                                  + line.Replace("\\n", " ").Replace("\n", " ").Trim();
                __result = __instance.SetMacroText(ref template, ref __1, ref __2);
            }
            catch (Exception e)
            {
                if (!_warned) { _warned = true; Plugin.L.LogWarning("[Watson] " + e.Message); }
            }
            finally { _busy = false; }
        }
    }

    static class SearchMap
    {
        static bool _warned;

        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.DeclaredMethod(typeof(GameManager), nameof(GameManager.CreateServerReferenceData));
                if (m == null) { Plugin.L.LogWarning("[Mapa] GameManager.CreateServerReferenceData no existe"); return; }
                h.Patch(m, postfix: new HarmonyMethod(typeof(SearchMap).GetMethod(nameof(After),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Mapa] " + e.Message); }
        }

        static void After(NetworkManager.JsonStringBuilder __result)
        {
            try
            {
                var isb = __result?.stringBuilder;
                if (isb == null) return;
                var extra = new StringBuilder("\"searchMap\":[");
                bool first = true;
                foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<SearchObject>()))
                {
                    var so = o?.TryCast<SearchObject>();
                    if (so == null) continue;
                    if (!first) extra.Append(',');
                    first = false;
                    // [furniture, square, x, y, z]: world position x10 (like the pings), above the furniture
                    var pos = so.transform.position;
                    var rend = so.GetComponentInChildren<UnityEngine.Renderer>();
                    if (rend != null) { var bb = rend.bounds; pos = new UnityEngine.Vector3(bb.center.x, bb.max.y, bb.center.z); }  // above
                    extra.Append('[').Append(so.UniqId).Append(',').Append(so.GetGridId())
                         .Append(',').Append(UnityEngine.Mathf.RoundToInt(pos.x * 10))
                         .Append(',').Append(UnityEngine.Mathf.RoundToInt(pos.y * 10))
                         .Append(',').Append(UnityEngine.Mathf.RoundToInt(pos.z * 10)).Append(']');
                }
                if (first) return;                       // no furniture (it isn't a match)
                extra.Append("],");
                // The type of each item of the match (Item.Type: 0 miss, 1 food, 2 weapon... 9 memo), in the order of the
                // match list the server deals out: the server needs it to know which items are notes (memos).
                try
                {
                    var list = ItemManager.Instance?.GetMatchItemList()?.TryCast<Il2CppSystem.Collections.Generic.List<Item>>();
                    if (list != null && list.Count > 0)
                    {
                        extra.Append("\"itemTypes\":[");
                        for (int i = 0; i < list.Count; i++)
                        {
                            if (i > 0) extra.Append(',');
                            var it = list[i];
                            extra.Append(it != null ? (int)it.itemType : -1);
                        }
                        extra.Append("],");
                    }
                }
                catch { }
                string s = isb.ToString();
                int start = s.IndexOf('{');              // the summary is a JSON object: inserted right as it opens
                if (start < 0) return;
                isb.Clear();
                isb.Append(s.Substring(0, start + 1) + extra + s.Substring(start + 1));
            }
            catch (Exception e)
            {
                if (!_warned) { _warned = true; Plugin.L.LogWarning("[Mapa] " + e.Message); }
            }
        }
    }
}
