// CRIMESIGHT Revival - plugin OPCIONAL de BepInEx: stickers y avatares de mods en caliente.
//
// Sin este plugin, el lanzador mete los mods en los archivos del juego antes de abrirlo (hay que
// reiniciar para cambiarlos). Con BepInEx instalado, el lanzador deja el juego original y escribe
// el conjunto de mods de la sala en BepInEx\csr_live\live.json (en la carpeta del juego). Este plugin
// lo vigila y, fuera de las partidas, crea en memoria los stickers y avatares nuevos y los anade a
// las listas del juego (los del juego no se tocan). Si cambia mientras juegas, se aplica al volver
// al menu, para que todos los jugadores tengan siempre la misma lista.
//
// No toca el servidor: solo anade huecos de apariencia (and makes a mod stamp received from another
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
            L.LogInfo("Mods en caliente activos. Carpeta: " + LiveMods.LiveDir);
        }
    }

    // ---------------------------------------------------------------- enganches
    // El juego monta la rueda de stickers y busca el avatar elegido justo al cargar cada escena. Si
    // nuestros stickers/avatares no estan en ese momento, pone otros en su lugar (y parece que se han
    // "quitado"). Por eso, ademas de comprobarlo cada segundo, se meten justo cuando el juego registra
    // sus listas o va a leerlas.
    [HarmonyPatch]
    static class Hooks
    {
        [HarmonyPostfix, HarmonyPatch(typeof(StampManager), nameof(StampManager.RegistStampSet))]
        static void AfterStampSet() => LiveMods.Instance?.Sync();

        [HarmonyPrefix, HarmonyPatch(typeof(PingStampMenuBase), nameof(PingStampMenuBase.RefreshMenuStampReferenceSaveData))]
        static void BeforeStampMenu() => LiveMods.Instance?.Sync();

        // Al crearse una rueda (al cargar cada escena) el juego pone el primer sticker de la lista en los huecos
        // cuyo sticker guardado no esta: se rehace igual que al cambiar la lista, con el de por defecto.
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

        // Un sticker de mod sin mensaje no escribe nada en el registro de la partida: ni "Jugador: ..."
        // al mandarlo, ni la linea de responder a un ping con el.
        [HarmonyPrefix, HarmonyPatch(typeof(StampManager), nameof(StampManager.CallStampInGameLog))]
        static bool BeforeStampLog(ref StampParam param) => !LiveMods.Silent(param?.logMsgId);

        [HarmonyPrefix, HarmonyPatch(typeof(StampManager), nameof(StampManager.StampFromPingButtonInGameLog))]
        static bool BeforePingStampLog(ref StampParam stampParam) => !LiveMods.Silent(stampParam?.responseMsgId);

        // Stamps received from other players (see StampPlace)
        [HarmonyPrefix, HarmonyPatch(typeof(NetworkManager), "WampEventCallback")]
        static void BeforeWampEvent(Il2CppSystem.Collections.Generic.Dictionary<string, Il2CppSystem.Object> __1)
        {
            try { StampPlace.Fix(__1); } catch (Exception e) { StampPlace.Warn(e); }
        }
    }

    // ---------------------------------------------------------------- stamps from other players
    // A stamp message says which stamp it is twice: its type, and its place in the sender's stamp list
    // (setIndex/dataIndex). The game shows the one at that place in ITS OWN list. Mod stamps are added to those
    // lists, and for a few seconds after someone joins a room the lists can differ (a game that hasn't loaded
    // the room's mods yet): the place then points at another stamp, e.g. one of yours instead of theirs. Here,
    // for mod stamps, the place is worked out again from the type, in this game's own list.
    static class StampPlace
    {
        const int FirstModType = 1000;
        static bool _warned;

        public static void Fix(Il2CppSystem.Collections.Generic.Dictionary<string, Il2CppSystem.Object> d)
        {
            if (d == null || !d.ContainsKey("tag") || !d.ContainsKey("type") || !d.ContainsKey("dataIndex")) return;
            if (d["tag"]?.ToString() != "stamp") return;
            if (!int.TryParse(d["type"]?.ToString(), out int type) || type < FirstModType) return;
            int.TryParse(d["dataIndex"]?.ToString(), out int place);
            int setId = 0;
            if (d.ContainsKey("setIndex")) int.TryParse(d["setIndex"]?.ToString(), out setId);
            var sm = StampManager.Instance;
            var sets = sm?.registStampSet;
            if (sets == null) return;
            foreach (var set in sets)
            {
                if (set == null || set.SetId != setId || set.registStampData == null) continue;
                var list = set.registStampData;
                if (place >= 0 && place < list.Count && list[place] != null && (int)list[place].Type == type) return;   // same place here
                for (int i = 0; i < list.Count; i++)
                {
                    if (list[i] == null || (int)list[i].Type != type) continue;
                    d["dataIndex"] = Box(d["dataIndex"], i);
                    Plugin.L.LogInfo($"[Stamps] stamp {type} from another player: place {place} -> {i}");
                    return;
                }
                return;     // this game doesn't have that stamp (yet): left as it is
            }
        }

        // the new number with the same kind of value the game's message had
        static Il2CppSystem.Object Box(Il2CppSystem.Object like, int v)
        {
            string tn = like?.GetIl2CppType()?.FullName;
            if (tn == "System.Int64") return new Il2CppSystem.Int64 { m_value = v }.BoxIl2CppObject();
            if (tn == "System.Double") return new Il2CppSystem.Double { m_value = v }.BoxIl2CppObject();
            if (tn == "System.Single") return new Il2CppSystem.Single { m_value = v }.BoxIl2CppObject();
            return new Il2CppSystem.Int32 { m_value = v }.BoxIl2CppObject();
        }

        public static void Warn(Exception e)
        {
            if (_warned) return;
            _warned = true;
            Plugin.L.LogWarning("[Stamps] " + e.Message);
        }
    }

    // ---------------------------------------------------------------- formato de live.json
    public class LiveSticker
    {
        public int type { get; set; }
        public string png { get; set; }
        public string bg { get; set; }
        public string[] log { get; set; }      // 11 idiomas, en el orden de ConfigSystem.LangType
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

    // ---------------------------------------------------------------- componente que lo aplica
    public class LiveMods : MonoBehaviour
    {
        public LiveMods(IntPtr ptr) : base(ptr) { Instance = this; }

        public static LiveMods Instance;
        int _syncFrame = -1;

        // llamado desde los enganches (como mucho una vez por fotograma)
        public void Sync()
        {
            if (Time.frameCount == _syncFrame) return;
            _syncFrame = Time.frameCount;
            try { Tick(); }
            catch (Exception e) { Plugin.L.LogError(e); }
        }

        // Dentro de BepInEx, en la carpeta del juego: asi el lanzador y el plugin la ven igual en
        // Windows y con Proton (Linux / Steam Deck), donde la carpeta de usuario es la de Wine.
        public static readonly string LiveDir = Path.Combine(BepInEx.Paths.BepInExRootPath, "csr_live");
        const int FIRST_TYPE = 1000;

        float _next;
        DateTime _seen = DateTime.MinValue;
        LiveState _pending;                     // lo que pide el lanzador
        string _appliedHash = "";
        bool _waitLogged;

        // objetos creados por nosotros (se destruyen al cambiar de conjunto)
        readonly List<StampData> _stamps = new();
        readonly List<CursorAvatarData> _avatars = new();
        readonly Dictionary<string, string[]> _texts = new();
        readonly HashSet<int> _types = new();
        readonly HashSet<string> _avatarIds = new();
        static readonly HashSet<string> _silent = new();   // textos de los stickers sin mensaje

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

        // ------------------------------------------------------------ crear / destruir
        // objetos ya creados, por clave (tipo/id + huella de sus imagenes). Al cambiar el conjunto
        // (p. ej. entran los mods de otro jugador) los que no cambian se REUTILIZAN: si se destruyeran
        // y recrearan, el juego perderia la referencia al avatar elegido y volveria al de por defecto.
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
                    // sin mensaje: texto vacio (para que no salga el id) y no se escribe en el registro
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
            Ensure();                                  // saca de las listas lo que ya no va (antes de destruirlo)
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

        // ------------------------------------------------------------ meterlos en las listas del juego
        [HideFromIl2Cpp]
        static bool Ours(StampData d) =>
            d != null && (int)d.FaceType == 0 && (int)d.Type >= FIRST_TYPE;


        // La rueda de stickers guarda "posicion en la lista" (no el sticker). Al cambiar la lista
        // (entran los mods de otro jugador, que se intercalan al ordenar por tipo), las posiciones de
        // los tuyos cambian: hay que volver a calcular la rueda desde tus ajustes, o saldrian otros.
        // Se recalculan TODAS las ruedas, tambien las que estan cerradas (en la sala suele estarlo cuando
        // llegan los mods de otro): antes solo se buscaban las visibles y la cerrada se quedaba con las
        // posiciones viejas (usabas "tu" sticker y salia el de otro) hasta que empezaba la partida. Y por si
        // acaso, al abrir una rueda se recalcula si los stickers han cambiado desde la ultima vez.
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
                if (menu == null || !menu.gameObject.scene.IsValid()) continue;     // los prefabs no
                RefreshMenu(menu);
            }
        }

        [HideFromIl2Cpp]
        internal static void RefreshMenu(PingStampMenuBase menu)
        {
            try
            {
                // Igual que PingStampMenuBase.Start: primero las ruedas por defecto y, solo si el jugador ha
                // personalizado la suya (ConfigSystem.isUseStampCustomize), encima la guardada. Sin ajustes
                // guardados, cargar "la guardada" dejaba todos los huecos con el mismo sticker.
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
                        // Un sticker guardado que ahora no esta (un mod desactivado, o de alguien que no esta en
                        // la sala) el juego lo cambia por el primero de la lista. Ese hueco lleva su sticker por
                        // defecto; cuando vuelva el mod, la siguiente vez que se rehaga la rueda vuelve el suyo.
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

        // Las listas de cada pagina de la rueda (como en RefreshMenuStampReferenceDefault)
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

        // cada segundo: las listas del juego tienen justo nuestros stickers/avatares (al cambiar de
        // escena el juego vuelve a crear las suyas, asi que se comprueba siempre)
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
                    if (!icons) continue;              // la lista de marcos/fondos no se toca
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
