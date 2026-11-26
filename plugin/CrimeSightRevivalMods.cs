// CRIMESIGHT Revival - OPTIONAL BepInEx plugin: mod stickers and avatars, live.
//
// Without this plugin, the launcher puts the mods into the game's files before opening it (a
// restart is needed to change them). With BepInEx installed, the launcher leaves the game original and writes
// the room's mod set in BepInEx\csr_live\live.json (in the game folder). This plugin
// watches it and, outside matches, creates the new stickers and avatars in memory and adds them to
// the game's lists (the game's own aren't touched). If it changes while you play, it is applied when going back
// to the menu, so every player always has the same list.
//
// It doesn't touch the server: it only adds appearance slots (and makes a mod stamp received from another
// player show the right stamp, see StampPlace).
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.Attributes;
using Il2CppInterop.Runtime.Injection;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    [BepInPlugin("com.amras95.crimesightrevival.mods", "CRIMESIGHT Revival - Mods", "1.3.0")]
    public class Plugin : BasePlugin
    {
        internal static ManualLogSource L;

        public override void Load()
        {
            L = Log;
            ClassInjector.RegisterTypeInIl2Cpp<LiveMods>();
            AddComponent<LiveMods>();
            var h = Harmony.CreateAndPatchAll(typeof(Hooks));
            StageLab.Init(h);
            Pad.Init(h);
            Quit.Init(h);
            Turns.Init(h);
            CustomCursor.Init(h);
            AiPicker.Init(h);
            Guide.Init(h);
            RevivalCredits.Init(h);
            Manual.Init(h);
            TalkSkip.Init(h);
            Roster.Init(h);
            PartnerIcon.Init(h);
            Team.Init(h);
            QuickRematch.Init(h);
            RoleLock.Init(h);
            ResultNames.Init(h);
            L.LogInfo("Mods en caliente activos. Carpeta: " + LiveMods.LiveDir);
        }
    }

    // ---------------------------------------------------------------- hooks
    // The game builds the sticker wheel and looks up the chosen avatar right when each scene loads. If
    // our stickers/avatars aren't there at that moment, it puts others in their place (and they look
    // "removed"). That is why, besides checking every second, they are inserted right when the game registers
    // its lists or is about to read them.
    [HarmonyPatch]
    static class Hooks
    {
        [HarmonyPostfix, HarmonyPatch(typeof(StampManager), nameof(StampManager.RegistStampSet))]
        static void AfterStampSet() => LiveMods.Instance?.Sync();

        [HarmonyPrefix, HarmonyPatch(typeof(PingStampMenuBase), nameof(PingStampMenuBase.RefreshMenuStampReferenceSaveData))]
        static void BeforeStampMenu() => LiveMods.Instance?.Sync();

        // When a wheel is created (on loading each scene) the game puts the first sticker of the list in the slots
        // whose saved sticker isn't there: it is rebuilt just like when the list changes, with the default one.
        [HarmonyPostfix, HarmonyPatch(typeof(PingStampMenuBase), "Start")]
        static void AfterMenuStart(PingStampMenuBase __instance) => LiveMods.RefreshMenu(__instance);

        [HarmonyPostfix, HarmonyPatch(typeof(PingStampMenuBase), nameof(PingStampMenuBase.SetActive))]
        static void AfterMenuActive(PingStampMenuBase __instance, bool isActive)
        {
            if (isActive) LiveMods.MenuOpened(__instance);
        }

        [HarmonyPostfix, HarmonyPatch(typeof(CursorAvatarManager), nameof(CursorAvatarManager.RegistCursorAvatarSet))]
        static void AfterAvatarSet() => LiveMods.Instance?.Sync();

        [HarmonyPrefix, HarmonyPatch(typeof(CursorAvatarManager), nameof(CursorAvatarManager.GetMyCursorAvatarData))]
        static void BeforeMyAvatar() => LiveMods.Instance?.Sync();

        // A mod sticker without a message writes nothing in the match log: neither "Player: ..."
        // when sending it, nor the line for answering a ping with it.
        [HarmonyPrefix, HarmonyPatch(typeof(StampManager), nameof(StampManager.CallStampInGameLog))]
        static bool BeforeStampLog(ref StampParam param) => !LiveMods.Silent(param?.logMsgId);

        [HarmonyPrefix, HarmonyPatch(typeof(StampManager), nameof(StampManager.StampFromPingButtonInGameLog))]
        static bool BeforePingStampLog(ref StampParam stampParam) => !LiveMods.Silent(stampParam?.responseMsgId);

        // Stamps received from other players, in the room and in the match (see StampPlace)
        [HarmonyPrefix, HarmonyPatch(typeof(StampManager), nameof(StampManager.CreateRoomStamp))]
        static void BeforeRoomStamp(ref StampParam __0)
        {
            try { StampPlace.Fix(__0); } catch (Exception e) { StampPlace.Warn(e); }
        }

        [HarmonyPrefix, HarmonyPatch(typeof(StampManager), "CallStamp")]
        static void BeforeCallStamp(ref StampParam __0)
        {
            try { StampPlace.Fix(__0); } catch (Exception e) { StampPlace.Warn(e); }
        }
    }

    // ---------------------------------------------------------------- stamps from other players
    // A stamp message says which stamp it is twice: its type, and its place in the sender's stamp list
    // (setId/dataIndex). The game shows the one at that place in ITS OWN list. Mod stamps all go into set 0 (see
    // Ensure), sorted by type, so if two games' lists differ (different mods loaded at that moment), the place
    // points at another stamp, e.g. one of yours instead of theirs. Just before the game shows a received mod
    // stamp, its place is worked out again from its type in this game's set 0. If this game doesn't have that
    // stamp at all (the sender's mods were declined or aren't loaded yet), the game's first default stamp is
    // shown instead. (The network message itself can't be fixed: stamps don't come through there.)
    static class StampPlace
    {
        static readonly HashSet<int> _logged = new();
        static bool _warned;

        public static void Fix(StampParam p)
        {
            if (p == null) return;
            int type = (int)p.type, place = p.dataIndex;
            if (type < LiveMods.FIRST_TYPE) return;
            var set = ModSet();
            if (set == null) return;
            var list = set.registStampData;
            if (p.setId == set.SetId && place >= 0 && place < list.Count && list[place] != null && (int)list[place].Type == type)
                return;     // same place here
            for (int i = 0; i < list.Count; i++)
            {
                if (list[i] == null || (int)list[i].Type != type) continue;
                Plugin.L.LogInfo($"[Stamps] stamp {type} from another player: place {place} -> {i}");
                p.setId = set.SetId;
                p.dataIndex = i;
                return;
            }
            for (int i = 0; i < list.Count; i++)
            {
                var d = list[i];
                if (d == null || (int)d.Type >= LiveMods.FIRST_TYPE) continue;
                if (_logged.Add(type))
                    Plugin.L.LogInfo($"[Stamps] stamp {type} from another player isn't in this game: shown as default stamp {(int)d.Type}");
                p.type = d.Type;
                p.facetype = d.FaceType;
                p.typeInt = d.GetTypeInt();
                p.setId = set.SetId;
                p.dataIndex = i;
                return;
            }
        }

        static StampSet ModSet()
        {
            var sets = StampManager.Instance?.registStampSet;
            if (sets == null) return null;
            foreach (var set in sets)
                if (set != null && set.SetId == 0 && set.registStampData != null) return set;
            return null;
        }

        public static void Warn(Exception e)
        {
            if (_warned) return;
            _warned = true;
            Plugin.L.LogWarning("[Stamps] " + e.Message);
        }
    }

    // ---------------------------------------------------------------- live.json format
    public class LiveSticker
    {
        public int type { get; set; }
        public string png { get; set; }
        public string bg { get; set; }
        public string[] log { get; set; }      // 11 languages, in the order of ConfigSystem.LangType
        public string[] doc { get; set; }
    }

    public class LiveAvatar
    {
        public string id { get; set; }
        public string png { get; set; }
    }

    public class LiveState
    {
        public string hash { get; set; } = "";
        public List<LiveSticker> stickers { get; set; } = new();
        public List<LiveAvatar> avatars { get; set; } = new();
    }

    // ---------------------------------------------------------------- component that applies it
    public class LiveMods : MonoBehaviour
    {
        public LiveMods(IntPtr ptr) : base(ptr) { Instance = this; }

        public static LiveMods Instance;
        int _syncFrame = -1;

        // called from the hooks (at most once per frame)
        public void Sync()
        {
            if (Time.frameCount == _syncFrame) return;
            _syncFrame = Time.frameCount;
            try { Tick(); }
            catch (Exception e) { Plugin.L.LogError(e); }
        }

        // Inside BepInEx, in the game folder: that way the launcher and the plugin see it the same on
        // Windows and with Proton (Linux / Steam Deck), where the user folder is Wine's.
        public static readonly string LiveDir = Path.Combine(BepInEx.Paths.BepInExRootPath, "csr_live");
        internal const int FIRST_TYPE = 1000;

        float _next;
        DateTime _seen = DateTime.MinValue;
        LiveState _pending;                     // what the launcher asks for
        string _appliedHash = "";
        bool _waitLogged;

        // objects we created (destroyed when the set changes)
        readonly List<StampData> _stamps = new();
        readonly List<CursorAvatarData> _avatars = new();
        readonly Dictionary<string, string[]> _texts = new();
        readonly HashSet<int> _types = new();
        readonly HashSet<string> _avatarIds = new();
        static readonly HashSet<string> _silent = new();   // texts of the stickers without a message

        [HideFromIl2Cpp]
        internal static bool Silent(string msgId) => msgId != null && _silent.Contains(msgId);

        void Update()
        {
            Perf.Frame();
            StageLab.Frame();
            { long t0 = Perf.T(); try { Pad.Frame(); } catch (Exception e) { Plugin.L.LogWarning("[Mando] " + e.Message); } Perf.Done("Pad.Frame", t0); }
            { long t0 = Perf.T(); try { CustomCursor.Frame(); } catch (Exception e) { Plugin.L.LogWarning("[Cursor] " + e.Message); } Perf.Done("CustomCursor.Frame", t0); }
            { long t0 = Perf.T(); try { ModOffer.Frame(); } catch (Exception e) { Plugin.L.LogWarning("[Mods] " + e.Message); } Perf.Done("ModOffer.Frame", t0); }
            { long t0 = Perf.T(); try { AiPicker.Frame(); } catch (Exception e) { Plugin.L.LogWarning("[IA] " + e.Message); } Perf.Done("AiPicker.Frame", t0); }
            { long t0 = Perf.T(); try { Guide.Frame(false); } catch (Exception e) { Plugin.L.LogWarning("[Guia] " + e.Message); } Perf.Done("Guide.Frame(false)", t0); }
            { long t0 = Perf.T(); try { RevivalCredits.Frame(); } catch (Exception e) { Plugin.L.LogWarning("[Creditos] " + e.Message); } Perf.Done("RevivalCredits.Frame", t0); }
            { long t0 = Perf.T(); try { Models.Frame(); } catch (Exception e) { Plugin.L.LogWarning("[Modelos] " + e.Message); } Perf.Done("Models.Frame", t0); }
            { long t0 = Perf.T(); try { Roster.Frame(); } catch (Exception e) { Plugin.L.LogWarning("[Personajes] " + e.Message); } Perf.Done("Roster.Frame", t0); }
            try { TalkSkip.Frame(); } catch { }
            try { Team.Frame(); } catch (Exception e) { Plugin.L.LogWarning("[Team] " + e.Message); }
            { long t0 = Perf.T(); try { RosterUi.Frame(); } catch (Exception e) { Plugin.L.LogWarning("[Selector] " + e.Message); } Perf.Done("RosterUi.Frame", t0); }
            if (Time.unscaledTime < _next) return;
            _next = Time.unscaledTime + 1f;
            { long t0 = Perf.T(); try { Tick(); } catch (Exception e) { Plugin.L.LogError(e); } Perf.Done("Tick", t0); }
        }

        void LateUpdate()
        {
            { long t0 = Perf.T(); try { Guide.Frame(true); } catch { } Perf.Done("Guide.Frame(true)", t0); }
            { long t0 = Perf.T(); try { RevivalCredits.Late(); } catch { } Perf.Done("RevivalCredits.Late", t0); }
            { long t0 = Perf.T(); try { Models.Late(); } catch { } Perf.Done("Models.Late", t0); }
        }

        void Tick()
        {
            ReadLive();
            if (_pending != null && _pending.hash != _appliedHash)
            {
                if (InGame())
                {
                    if (!_waitLogged) Plugin.L.LogInfo("Mods nuevos: se aplicaran al terminar la partida.");
                    _waitLogged = true;
                }
                else
                {
                    Rebuild(_pending);
                    _appliedHash = _pending.hash;
                    _waitLogged = false;
                }
            }
            Ensure();
            try { StageLab.EnsureTexts(); } catch (Exception e) { Plugin.L.LogWarning("[Escenario] textos: " + e.Message); }
        }

        static bool InGame()
        {
            return SceneSequenceManager.Instance != null && SceneSequenceManager.IsInGame();
        }

        void ReadLive()
        {
            string path = Path.Combine(LiveDir, "live.json");
            DateTime t = File.Exists(path) ? File.GetLastWriteTimeUtc(path) : DateTime.MinValue;
            if (t == _seen) return;
            _seen = t;
            if (t == DateTime.MinValue) { _pending = new LiveState(); return; }
            try
            {
                _pending = JsonSerializer.Deserialize<LiveState>(File.ReadAllText(path)) ?? new LiveState();
            }
            catch (Exception e)
            {
                Plugin.L.LogWarning("live.json ilegible (lo vuelvo a leer en un momento): " + e.Message);
                _seen = DateTime.MinValue;
            }
        }

        // ------------------------------------------------------------ create / destroy
        // objects already created, by key (type/id + fingerprint of their images). When the set changes
        // (e.g. another player's mods come in) the ones that don't change are REUSED: if they were destroyed
        // and recreated, the game would lose the reference to the chosen avatar and go back to the default one.
        class Entry { public UnityEngine.Object Main; public readonly List<UnityEngine.Object> Assets = new(); }
        readonly Dictionary<string, Entry> _cache = new();

        [HideFromIl2Cpp]
        static string Sig(string file)
        {
            if (string.IsNullOrEmpty(file)) return "-";
            var fi = new FileInfo(Path.Combine(LiveDir, Path.GetFileName(file)));
            return fi.Exists ? fi.Length + ":" + fi.LastWriteTimeUtc.Ticks : "x";
        }

        [HideFromIl2Cpp]
        void Rebuild(LiveState st)
        {
            var next = new Dictionary<string, Entry>();
            _stamps.Clear(); _avatars.Clear(); _texts.Clear(); _types.Clear(); _avatarIds.Clear(); _silent.Clear();

            foreach (var s in st.stickers)
            {
                string key = $"s{s.type}|{Sig(s.png)}|{Sig(s.bg)}";
                if (!_cache.TryGetValue(key, out var e))
                {
                    e = new Entry();
                    var fg = MakeSprite(s.png, e.Assets);
                    if (fg == null) continue;
                    var bg = MakeSprite(s.bg, e.Assets);
                    var d = ScriptableObject.CreateInstance(Il2CppType.Of<StampData>()).Cast<StampData>();
                    d.hideFlags = HideFlags.DontUnloadUnusedAsset;
                    d.FaceType = (Stamp.FaceType)0;
                    d.Type = (Stamp.Type)s.type;
                    d.spriteImage = fg;
                    d.spriteImageBg = bg;
                    d.spriteImageThumbnail = null;
                    d.LogMsgId = "ctg_name_log_stamp_csr_" + s.type;
                    d.DocMsgId = "ctg_name_stamp_csr_" + s.type;
                    d.LockMsgId = "";
                    d.DLCId = "";
                    d.CreateTypeInt();
                    e.Main = d; e.Assets.Add(d);
                }
                next[key] = e;
                var sd = e.Main.Cast<StampData>();
                _stamps.Add(sd);
                _types.Add(s.type);
                if (s.log != null) _texts[sd.LogMsgId] = s.log;
                if (s.doc != null) _texts[sd.DocMsgId] = s.doc;
                if (s.log == null)
                {
                    // without a message: empty text (so the id doesn't show) and nothing is written to the log
                    _texts[sd.LogMsgId] = _texts[sd.DocMsgId] = new[] { "" };
                    _silent.Add(sd.LogMsgId); _silent.Add(sd.DocMsgId);
                }
            }
            foreach (var a in st.avatars)
            {
                string key = $"a{a.id}|{Sig(a.png)}";
                if (!_cache.TryGetValue(key, out var e))
                {
                    e = new Entry();
                    var sp = MakeSprite(a.png, e.Assets);
                    if (sp == null) continue;
                    var d = ScriptableObject.CreateInstance(Il2CppType.Of<CursorAvatarData>()).Cast<CursorAvatarData>();
                    d.hideFlags = HideFlags.DontUnloadUnusedAsset;
                    d.parts = CursorAvatarManager.Parts.ICON;
                    d.partsImage = sp;
                    d.nameMsgId = a.id;
                    d.docMsgId = "";
                    d.pairId = "";
                    d.LockMsgId = "";
                    d.DLCId = "";
                    e.Main = d; e.Assets.Add(d);
                }
                next[key] = e;
                _avatars.Add(e.Main.Cast<CursorAvatarData>());
                _avatarIds.Add(a.id);
            }
            Ensure();                                  // takes out of the lists what no longer belongs (before destroying it)
            foreach (var kv in _cache)
                if (!next.ContainsKey(kv.Key))
                    foreach (var o in kv.Value.Assets) if (o != null) UnityEngine.Object.Destroy(o);
            _cache.Clear();
            foreach (var kv in next) _cache[kv.Key] = kv.Value;
            RefreshMenus();
            Plugin.L.LogInfo($"Mods aplicados: {_stamps.Count} stickers y {_avatars.Count} avatares.");
        }

        [HideFromIl2Cpp]
        static Sprite MakeSprite(string file, List<UnityEngine.Object> assets)
        {
            if (string.IsNullOrEmpty(file)) return null;
            string path = Path.Combine(LiveDir, Path.GetFileName(file));
            if (!File.Exists(path)) return null;
            var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            if (!ImageConversion.LoadImage(tex, File.ReadAllBytes(path), false))
            {
                UnityEngine.Object.Destroy(tex);
                return null;
            }
            tex.wrapMode = TextureWrapMode.Clamp;
            tex.hideFlags = HideFlags.DontUnloadUnusedAsset;
            var sp = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f), 100f);
            sp.hideFlags = HideFlags.DontUnloadUnusedAsset;
            assets.Add(tex); assets.Add(sp);
            return sp;
        }

        // ------------------------------------------------------------ putting them in the game's lists
        [HideFromIl2Cpp]
        static bool Ours(StampData d) =>
            d != null && (int)d.FaceType == 0 && (int)d.Type >= FIRST_TYPE;


        // The sticker wheel stores "position in the list" (not the sticker). When the list changes
        // (another player's mods come in, interleaved when sorting by type), the positions of
        // yours change: the wheel has to be recalculated from your settings, or others would show.
        // ALL the wheels are recalculated, also the closed ones (in the room it usually is closed when
        // another player's mods arrive): before, only the visible ones were looked for and the closed one kept the
        // old positions (you used "your" sticker and someone else's showed) until the match started. And just
        // in case, when a wheel opens it is recalculated if the stickers changed since the last time.
        static int _stampGen;
        static readonly Dictionary<IntPtr, int> _menuGen = new();

        [HideFromIl2Cpp]
        static void RefreshMenus()
        {
            _stampGen++;
            UnityEngine.Object[] found;
            try { found = Resources.FindObjectsOfTypeAll(Il2CppType.Of<PingStampMenuBase>()); }
            catch { found = null; }
            if (found == null) return;
            foreach (var o in found)
            {
                var menu = o?.TryCast<PingStampMenuBase>();
                if (menu == null || !menu.gameObject.scene.IsValid()) continue;     // not the prefabs
                RefreshMenu(menu);
            }
        }

        [HideFromIl2Cpp]
        internal static void RefreshMenu(PingStampMenuBase menu)
        {
            try
            {
                // Like PingStampMenuBase.Start: first the default wheels and, only if the player has
                // customised theirs (ConfigSystem.isUseStampCustomize), the saved one on top. Without saved
                // settings, loading "the saved one" left every slot with the same sticker.
                var defaults = new List<StampReference>[4];
                for (int p = 0; p < 4; p++)
                {
                    int first = 0;
                    var preset = (StampManager.PresetType)p;
                    menu.RefreshMenuStampReferenceDefault(ref first, ref preset);
                    defaults[p] = new List<StampReference>();
                    var refs = PresetRefs(menu, p);
                    if (refs != null)
                        for (int i = 0; i < refs.Count; i++) defaults[p].Add(refs[i]);
                }
                if (ConfigSystem.isUseStampCustomize)
                    for (int p = 0; p < 4; p++)
                    {
                        var preset = (StampManager.PresetType)p;
                        menu.RefreshMenuStampReferenceSaveData(ref preset);
                        // A saved sticker that isn't there now (a disabled mod, or from someone who isn't in
                        // the room) is swapped by the game for the first in the list. That slot gets its default
                        // sticker; when the mod comes back, the next time the wheel is rebuilt its own comes back.
                        var refs = PresetRefs(menu, p);
                        if (refs == null) continue;
                        for (int i = 0; i < refs.Count && i < defaults[p].Count; i++)
                        {
                            int slot = i;
                            var pr = (StampManager.PresetType)p;
                            int saved = ConfigSystem.GetStampTypeMenu(ref slot, ref pr);
                            var r = refs[i];
                            if (r != null && (int)r.StampType != saved) refs[i] = defaults[p][i];
                        }
                    }
                menu.RefreshMenuStampReferenceCustom();
                _menuGen[menu.Pointer] = _stampGen;
            }
            catch (Exception e) { Plugin.L.LogWarning("No pude refrescar la rueda: " + e.Message); }
        }

        // The lists of each wheel page (like in RefreshMenuStampReferenceDefault)
        [HideFromIl2Cpp]
        static Il2CppSystem.Collections.Generic.List<StampReference> PresetRefs(PingStampMenuBase menu, int p) => p switch
        {
            1 => menu.MenuStampReferenceCustomPreset2,
            2 => menu.MenuStampReferenceCustomPreset3,
            3 => menu.MenuStampReferenceCustomPreset4,
            _ => menu.MenuStampReferenceCustom,
        };

        [HideFromIl2Cpp]
        internal static void MenuOpened(PingStampMenuBase menu)
        {
            if (menu == null || _stampGen == 0) return;
            if (!_menuGen.TryGetValue(menu.Pointer, out var g) || g != _stampGen) RefreshMenu(menu);
        }

        // every second: the game's lists have exactly our stickers/avatars (when the scene changes
        // the game creates its own again, so it is always checked)
        void Ensure()
        {
            var sm = StampManager.Instance;
            if (sm != null && sm.registStampSet != null)
                foreach (var set in sm.registStampSet)
                {
                    if (set == null || set.SetId != 0 || set.registStampData == null) continue;
                    var list = set.registStampData;
                    bool changed = false;
                    var present = new HashSet<IntPtr>();
                    for (int i = list.Count - 1; i >= 0; i--)
                    {
                        var d = list[i];
                        if (!Ours(d)) continue;
                        if (_stamps.Exists(x => x.Pointer == d.Pointer)) present.Add(d.Pointer);
                        else { list.RemoveAt(i); changed = true; }
                    }
                    foreach (var d in _stamps)
                        if (!present.Contains(d.Pointer)) { list.Add(d); changed = true; }
                    if (changed) { set.Sort(); RefreshMenus(); }
                }

            var cm = CursorAvatarManager.Instance;
            if (cm != null && cm.registCursorAvatarSet != null)
                foreach (var set in cm.registCursorAvatarSet)
                {
                    if (set == null || set.registCursorAvatarData == null) continue;
                    var list = set.registCursorAvatarData;
                    bool icons = false;
                    var present = new HashSet<IntPtr>();
                    for (int i = list.Count - 1; i >= 0; i--)
                    {
                        var d = list[i];
                        if (d == null) continue;
                        if (d.nameMsgId != null && d.nameMsgId.StartsWith("Icon_CSR_"))
                        {
                            if (_avatars.Exists(x => x.Pointer == d.Pointer)) present.Add(d.Pointer);
                            else list.RemoveAt(i);
                        }
                        else if (d.parts == CursorAvatarManager.Parts.ICON) icons = true;
                    }
                    if (!icons) continue;              // the frames/backgrounds list isn't touched
                    foreach (var d in _avatars)
                        if (!present.Contains(d.Pointer)) list.Add(d);
                }

            var tm = TextManager.Instance;
            if (tm != null && tm.LangText != null && _texts.Count > 0)
            {
                int lang = (int)tm.GetLangType();
                foreach (var kv in _texts)
                {
                    var arr = kv.Value;
                    string text = arr.Length > lang && !string.IsNullOrEmpty(arr[lang]) ? arr[lang] : arr[0];
                    if (!tm.LangText.ContainsKey(kv.Key) || tm.LangText[kv.Key] != text)
                        tm.LangText[kv.Key] = text;
                }
            }
        }
    }
}
