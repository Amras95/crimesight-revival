// CRIMESIGHT Revival - plugin OPCIONAL de BepInEx: stickers y avatares de mods en caliente.
//
// Sin este plugin, el lanzador mete los mods en los archivos del juego antes de abrirlo (hay que
// reiniciar para cambiarlos). Con BepInEx instalado, el lanzador deja el juego original y escribe
// el conjunto de mods de la sala en BepInEx\csr_live\live.json (en la carpeta del juego). Este plugin
// lo vigila y, fuera de las partidas, crea en memoria los stickers y avatares nuevos y los anade a
// las listas del juego (los del juego no se tocan). Si cambia mientras juegas, se aplica al volver
// al menu, para que todos los jugadores tengan siempre la misma lista.
//
// No toca la red ni el servidor: solo anade huecos de apariencia.
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
    [BepInPlugin("com.amras95.crimesightrevival.mods", "CRIMESIGHT Revival - Mods", "1.0.0")]
    public class Plugin : BasePlugin
    {
        internal static ManualLogSource L;

        public override void Load()
        {
            L = Log;
            ClassInjector.RegisterTypeInIl2Cpp<LiveMods>();
            AddComponent<LiveMods>();
            Harmony.CreateAndPatchAll(typeof(Hooks));
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

        [HarmonyPostfix, HarmonyPatch(typeof(CursorAvatarManager), nameof(CursorAvatarManager.RegistCursorAvatarSet))]
        static void AfterAvatarSet() => LiveMods.Instance?.Sync();

        [HarmonyPrefix, HarmonyPatch(typeof(CursorAvatarManager), nameof(CursorAvatarManager.GetMyCursorAvatarData))]
        static void BeforeMyAvatar() => LiveMods.Instance?.Sync();
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

        void Update()
        {
            if (Time.unscaledTime < _next) return;
            _next = Time.unscaledTime + 1f;
            try { Tick(); }
            catch (Exception e) { Plugin.L.LogError(e); }
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
            _stamps.Clear(); _avatars.Clear(); _texts.Clear(); _types.Clear(); _avatarIds.Clear();

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
        [HideFromIl2Cpp]
        static void RefreshMenus()
        {
            var found = UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<PingStampMenuBase>());
            if (found == null) return;
            foreach (var o in found)
            {
                var menu = o?.TryCast<PingStampMenuBase>();
                if (menu == null) continue;
                try
                {
                    for (int p = 0; p < 4; p++)
                    {
                        var preset = (StampManager.PresetType)p;
                        menu.RefreshMenuStampReferenceSaveData(ref preset);
                    }
                    menu.RefreshMenuStampReferenceCustom();
                }
                catch (Exception e) { Plugin.L.LogWarning("No pude refrescar la rueda: " + e.Message); }
            }
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
