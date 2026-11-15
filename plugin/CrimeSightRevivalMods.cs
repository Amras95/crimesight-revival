// CRIMESIGHT Revival - plugin OPCIONAL de BepInEx: stickers y avatares de mods en caliente.
//
// Sin este plugin, el lanzador mete los mods en los archivos del juego antes de abrirlo (hay que
// reiniciar para cambiarlos). Con BepInEx instalado, el lanzador deja el juego original y escribe
// el conjunto de mods de la sala en %APPDATA%\CrimeSightRevival\mods_live\live.json. Este plugin
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
using Il2CppInterop.Runtime;
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
            L.LogInfo("Mods en caliente activos. Carpeta: " + LiveMods.LiveDir);
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
        public LiveMods(IntPtr ptr) : base(ptr) { }

        public static readonly string LiveDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "CrimeSightRevival", "mods_live");
        const int FIRST_TYPE = 1000;
        const int DEFAULT_STAMP = 28;          // "hola": sustituye a un sticker que ya no esta

        float _next;
        DateTime _seen = DateTime.MinValue;
        LiveState _pending;                     // lo que pide el lanzador
        string _appliedHash = "";
        bool _waitLogged;

        // objetos creados por nosotros (se destruyen al cambiar de conjunto)
        readonly List<StampData> _stamps = new();
        readonly List<CursorAvatarData> _avatars = new();
        readonly List<UnityEngine.Object> _assets = new();
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
        void Rebuild(LiveState st)
        {
            Unregister();
            foreach (var o in _assets) if (o != null) UnityEngine.Object.Destroy(o);
            _assets.Clear(); _stamps.Clear(); _avatars.Clear(); _texts.Clear(); _types.Clear(); _avatarIds.Clear();

            foreach (var s in st.stickers)
            {
                var fg = MakeSprite(s.png);
                if (fg == null) continue;
                var bg = MakeSprite(s.bg);
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
                _stamps.Add(d); _assets.Add(d);
                _types.Add(s.type);
                if (s.log != null) _texts[d.LogMsgId] = s.log;
                if (s.doc != null) _texts[d.DocMsgId] = s.doc;
            }
            foreach (var a in st.avatars)
            {
                var sp = MakeSprite(a.png);
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
                _avatars.Add(d); _assets.Add(d);
                _avatarIds.Add(a.id);
            }
            FixConfig();
            Plugin.L.LogInfo($"Mods aplicados: {_stamps.Count} stickers y {_avatars.Count} avatares.");
        }

        Sprite MakeSprite(string file)
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
            _assets.Add(tex); _assets.Add(sp);
            return sp;
        }

        // ------------------------------------------------------------ meterlos en las listas del juego
        static bool Ours(StampData d) =>
            d != null && (int)d.FaceType == 0 && (int)d.Type >= FIRST_TYPE;

        void Unregister()
        {
            var sm = StampManager.Instance;
            if (sm != null && sm.registStampSet != null)
                foreach (var set in sm.registStampSet)
                {
                    if (set == null || set.registStampData == null) continue;
                    var list = set.registStampData;
                    for (int i = list.Count - 1; i >= 0; i--)
                        if (Ours(list[i])) list.RemoveAt(i);
                }
            var cm = CursorAvatarManager.Instance;
            if (cm != null && cm.registCursorAvatarSet != null)
                foreach (var set in cm.registCursorAvatarSet)
                {
                    if (set == null || set.registCursorAvatarData == null) continue;
                    var list = set.registCursorAvatarData;
                    for (int i = list.Count - 1; i >= 0; i--)
                    {
                        var d = list[i];
                        if (d != null && d.nameMsgId != null && d.nameMsgId.StartsWith("Icon_CSR_")) list.RemoveAt(i);
                    }
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
                    if (changed) set.Sort();
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

        // si la rueda de stickers o el avatar elegido apuntan a un mod que ya no esta, se cambian
        // por uno del juego (en memoria; el lanzador corrige tambien lo guardado)
        void FixConfig()
        {
            var menus = new[] { ConfigSystem.stampTypeMenu, ConfigSystem.stampTypeMenuPreset2,
                                ConfigSystem.stampTypeMenuPreset3, ConfigSystem.stampTypeMenuPreset4 };
            foreach (var arr in menus)
            {
                if (arr == null) continue;
                for (int i = 0; i < arr.Length; i++)
                {
                    int v = arr[i];
                    if ((v >> 12) == 0 && (v & 4095) >= FIRST_TYPE && !_types.Contains(v)) arr[i] = DEFAULT_STAMP;
                }
            }
            var icon = ConfigSystem.cursorAvatarIconName;
            if (icon != null && icon.StartsWith("Icon_CSR_") && !_avatarIds.Contains(icon))
                CursorAvatarManager.SetMyCursorAvatarDefaultData();
        }
    }
}
