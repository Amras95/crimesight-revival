// CRIMESIGHT Revival - personajes nuevos en la partida (el reparto del Selector de personajes).
//
// Al empezar la cuenta atras, el servidor sortea que personajes salen (originales y nuevos) y el lanzador escribe
// csr_live/roster.json con lo que lleva cada sitio (A..F) en esta partida:
//   { "id": "...", "positions": { "PawnTypeData_C": { "id", "name", "talk": {situacion: frase}, "image", "model" }, ... },
//     "traitor": {...} | null }
// Un sitio a null es el personaje original. El modelo 3D y las animaciones ya van en models.json (Models); aqui:
//   - Nombre: el del original se cambia por el nuevo en todos los textos del juego (registro, dialogos, fichas).
//   - Frases: las situaciones que el personaje nuevo tiene escritas sustituyen a las del original; las variantes
//     de una situacion (con otro personaje, el primer dia...) usan la misma frase. Las demas se quedan.
//   - Imagen: los retratos del personaje (fichas, iconos, resultados...) se hacen con la imagen del personaje, del
//     mismo tamano que los originales (tenida de rojo / gris en los de herido / en coma). Sin imagen, se saca una
//     del modelo 3D. La placa con el nombre sobre el tablero se rehace con el nombre nuevo.
// Al cambiar el reparto (o al salir de la sala) todo vuelve a lo original. El juego no se entera: solo cambian
// sus textos y sus imagenes, la forma de jugar de cada sitio es la del original.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Il2CppInterop.Runtime;
using TMPro;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class Roster
    {
        internal static readonly string[] Pawns = { "PawnTypeData_A", "PawnTypeData_B", "PawnTypeData_C", "PawnTypeData_D", "PawnTypeData_E", "PawnTypeData_F" };
        internal const string Traitor = "ThreatTypeData_Traitor";
        static readonly string[] DefaultNames = { "Agatha", "Berkeley", "Catherine", "Dorothy", "Ellery", "Freeman" };

        internal class Entry { public string id, name, image, model, role, animFrom; public Dictionary<string, string> talk = new(); }
        internal static readonly Color PortraitBg = new Color(0.16f, 0.17f, 0.22f, 1f);
        class State { public string id = ""; public readonly Entry[] pos = new Entry[6]; public Entry traitor; }

        static string File_ => Path.Combine(LiveMods.LiveDir, "roster.json");
        static string _sig = "";
        static State _cur;
        static float _next, _nextSprites;

        public static void Frame()
        {
            try { Snaps(); } catch (Exception e) { Warn("snap", "[Personajes] " + e.Message); }
            try { SpriteJobs(); } catch (Exception e) { Warn("jobs", "[Personajes] " + e.Message); }
            if (Time.unscaledTime < _next) return;
            _next = Time.unscaledTime + 1f;
            try
            {
                Read();
                ApplyText();
                if (Time.unscaledTime >= _nextSprites) { _nextSprites = Time.unscaledTime + 3f; ApplySprites(); ApplyBorrow(); }
                CacheOriginals();
            }
            catch (Exception e) { Warn("frame", "[Personajes] " + e.Message); }
        }

        static readonly HashSet<string> _warned = new();
        static void Warn(string k, string m) { if (_warned.Add(k)) Plugin.L.LogWarning(m); }

        // ------------------------------------------------------------ roster.json
        static void Read()
        {
            string sig = "";
            try { var fi = new FileInfo(File_); if (fi.Exists) sig = fi.Length + ":" + fi.LastWriteTimeUtc.Ticks; } catch { }
            if (sig == _sig) return;
            _sig = sig;
            State st = null;
            if (sig != "")
                try
                {
                    using var doc = JsonDocument.Parse(File.ReadAllText(File_, Encoding.UTF8));
                    var r = doc.RootElement;
                    st = new State { id = Str(r, "id") ?? "" };
                    if (r.TryGetProperty("positions", out var pos) && pos.ValueKind == JsonValueKind.Object)
                        for (int i = 0; i < 6; i++)
                            if (pos.TryGetProperty(Pawns[i], out var e)) st.pos[i] = ParseEntry(e);
                    if (r.TryGetProperty("traitor", out var tr)) st.traitor = ParseEntry(tr);
                    bool any = st.traitor != null;
                    foreach (var e in st.pos) any |= e != null;
                    if (!any) st = null;
                }
                catch (Exception e) { Plugin.L.LogWarning("[Personajes] roster.json: " + e.Message); st = null; }
            RestoreSprites();
            _cur = st;
            if (st == null) { Plugin.L.LogInfo("[Personajes] partida con los personajes originales"); return; }
            var sb = new StringBuilder();
            for (int i = 0; i < 6; i++)
                if (st.pos[i] != null) sb.Append(sb.Length > 0 ? ", " : "").Append(DefaultNames[i]).Append(" -> ").Append(st.pos[i].name ?? st.pos[i].id);
            if (st.traitor != null) sb.Append(sb.Length > 0 ? ", " : "").Append("traidor -> ").Append(st.traitor.id);
            Plugin.L.LogInfo("[Personajes] reparto " + st.id + ": " + sb);
            foreach (var e in st.pos) if (e?.model != null) Models.Prefetch(e.model);      // se lee en otro hilo mientras carga la partida
        }

        static string Str(JsonElement e, string k) =>
            e.ValueKind == JsonValueKind.Object && e.TryGetProperty(k, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;

        static Entry ParseEntry(JsonElement e)
        {
            if (e.ValueKind != JsonValueKind.Object) return null;
            var en = new Entry { id = Str(e, "id") ?? "?", name = Str(e, "name"), image = Str(e, "image"), model = Str(e, "model"), animFrom = Str(e, "anim_from") };
            if (string.IsNullOrWhiteSpace(en.name)) en.name = null;
            if (e.TryGetProperty("talk", out var t) && t.ValueKind == JsonValueKind.Object)
                foreach (var p in t.EnumerateObject())
                    if (p.Value.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(p.Value.GetString())) en.talk[p.Name] = p.Value.GetString();
            return en;
        }

        // ------------------------------------------------------------ animaciones de otro personaje
        static string _borrowSig = "";
        /// <summary>Cada personaje nuevo se mueve como el personaje del juego que se le eligio en el lanzador, no como
        /// el del sitio que ocupa (Models hace el cambio en cada fotograma).</summary>
        static void ApplyBorrow()
        {
            var map = new Dictionary<string, string>();
            if (_cur != null)
                for (int i = 0; i < 6; i++)
                {
                    var e = _cur.pos[i];
                    if (e?.animFrom != null && Array.IndexOf(Pawns, e.animFrom) >= 0 && e.animFrom != Pawns[i]) map[Pawns[i]] = e.animFrom;
                }
            var sb = new StringBuilder();
            foreach (var kv in map) sb.Append(kv.Key).Append('>').Append(kv.Value).Append(';');
            if (sb.ToString() == _borrowSig) return;
            _borrowSig = sb.ToString();
            Models.SetBorrow(map);
        }

        // ------------------------------------------------------------ textos (nombres y frases)
        const string Mark = "csr_roster_mark";
        static readonly Dictionary<string, string> _savedText = new();     // clave -> texto original
        static IntPtr _textDict;
        static string _textSig = "";
        static readonly Regex TalkKey = new(@"^ctg_talk_pwPawn0([1-6])_(.+)_p\d+_v\d+$");

        /// <summary>El nombre original del personaje de un sitio (aunque ahora lleve el de otro).</summary>
        internal static string OrigName(int i)
        {
            string k = "ctg_name_pawn0" + (i + 1);
            if (_savedText.TryGetValue(k, out var s)) return s;
            try
            {
                var lt = TextManager.Instance?.LangText;
                if (lt != null && lt.ContainsKey(k)) return lt[k];
            }
            catch { }
            return DefaultNames[i];
        }

        static string TextSig(State st)
        {
            if (st == null) return "";
            var sb = new StringBuilder();
            for (int i = 0; i < 6; i++)
            {
                var e = st.pos[i];
                if (e == null || (e.name == null && e.talk.Count == 0)) continue;
                sb.Append(i).Append('=').Append(e.name).Append('|');
                foreach (var kv in e.talk) sb.Append(kv.Key).Append(':').Append(kv.Value.GetHashCode()).Append(',');
                sb.Append(';');
            }
            return sb.ToString();
        }

        /// <summary>La situacion base de una frase: "pawnGameStart04_gt01" -> "pawnGameStart", "x_toPawn03" -> "x".</summary>
        static string BaseSituation(string s)
        {
            s = Regex.Replace(s, @"_gt\d+$", "");
            s = Regex.Replace(s, @"_?(aloneWithPawn|toPawn|withPawn)\d+$", "");
            s = Regex.Replace(s, @"(?<=[A-Za-z])\d+$", "");
            return s;
        }

        static void ApplyText()
        {
            var tm = TextManager.Instance;
            var lt = tm != null ? tm.LangText : null;
            if (lt == null) return;
            bool fresh = lt.Pointer != _textDict || !lt.ContainsKey(Mark);    // otro idioma: el juego recargo los textos
            string want = TextSig(_cur);
            if (!fresh && want == _textSig) return;
            if (fresh) { _savedText.Clear(); _textDict = lt.Pointer; }
            else
            {
                foreach (var kv in _savedText) lt[kv.Key] = kv.Value;
                _savedText.Clear();
            }
            _textSig = want;
            lt[Mark] = "1";
            if (want == "") return;

            var names = new Dictionary<string, string>();                    // nombre original -> nuevo
            var newName = new string[6];
            for (int i = 0; i < 6; i++)
            {
                var e = _cur.pos[i];
                if (e?.name == null) continue;
                string k = "ctg_name_pawn0" + (i + 1);
                string orig = lt.ContainsKey(k) ? lt[k] : DefaultNames[i];
                newName[i] = e.name;
                if (!string.IsNullOrEmpty(orig)) names[orig] = e.name;
                if (orig != DefaultNames[i]) names[DefaultNames[i]] = e.name;
            }
            Regex rx = null;
            if (names.Count > 0)
            {
                var alts = new List<string>(names.Keys);
                alts.Sort((a, b) => b.Length.CompareTo(a.Length));
                var parts = new List<string>();
                foreach (var n in alts)
                {
                    bool ascii = Regex.IsMatch(n, @"^[A-Za-z .'-]+$");
                    parts.Add(ascii ? @"(?<![A-Za-z])" + Regex.Escape(n) + @"(?![A-Za-z])" : Regex.Escape(n));
                }
                rx = new Regex(string.Join("|", parts));
            }

            var changes = new List<(string k, string v, string nv)>();
            int talks = 0;
            foreach (var kv in lt)
            {
                string k = kv.Key, v = kv.Value;
                if (k == null || v == null || k == Mark) continue;
                string nv = null;
                var m = k.StartsWith("ctg_talk_pwPawn0", StringComparison.Ordinal) ? TalkKey.Match(k) : null;
                if (m != null && m.Success)
                {
                    int i = m.Groups[1].Value[0] - '1';
                    var e = _cur.pos[i];
                    if (e != null && e.talk.Count > 0 && e.talk.TryGetValue(BaseSituation(m.Groups[2].Value), out var line)) { nv = line; talks++; }
                }
                if (nv == null)
                {
                    var mn = Regex.Match(k, @"^ctg_name_(?:characterIntroduction_)?pawn0([1-6])(?:_name)?$");
                    if (mn.Success && newName[mn.Groups[1].Value[0] - '1'] != null) nv = newName[mn.Groups[1].Value[0] - '1'];
                    else if (rx != null && rx.IsMatch(v)) nv = rx.Replace(v, mm => names.TryGetValue(mm.Value, out var r) ? r : mm.Value);
                }
                if (nv != null && nv != v) changes.Add((k, v, nv));
            }
            foreach (var (k, v, nv) in changes)
            {
                if (!_savedText.ContainsKey(k)) _savedText[k] = v;
                lt[k] = nv;
            }
            Plugin.L.LogInfo($"[Personajes] textos: {changes.Count} cambiado(s) ({talks} frase(s) propias)");
        }

        // ------------------------------------------------------------ imagenes de los personajes
        // retratos de PawnTypeData: (nombre, tinte) 0 normal, 1 herido (rojo), 2 en coma (gris)
        static readonly (string name, int tint)[] SpriteFields =
        {
            ("charaInfoSprite", 0), ("charaInfoDamageSprite", 1), ("charaInfoComaSprite", 2), ("charaTelopSprite", 0),
            ("actoinPawnSprite", 0), ("actionPawnDamageSprite", 1), ("actionPawnComaSprite", 2),
            ("charaFinalReasoningSprite", 0), ("charaFinalReasoningKillerSprite", 0), ("charaFinalReasoningSelectedSprite", 0),
            ("resultKillerSprite", 0), ("resultTargetSprite", 0), ("outSideCharaIconNormal", 0), ("outSideCharaIconBad1", 1),
            ("outSideCharaIconBad2", 2), ("charaIntroLookIcon", 0), ("charaIntroFaceIcon", 0),
        };

        static Sprite GetSp(PawnTypeData d, string f) => f switch
        {
            "charaInfoSprite" => d.charaInfoSprite, "charaInfoDamageSprite" => d.charaInfoDamageSprite,
            "charaInfoComaSprite" => d.charaInfoComaSprite, "charaTelopSprite" => d.charaTelopSprite,
            "actoinPawnSprite" => d.actoinPawnSprite, "actionPawnDamageSprite" => d.actionPawnDamageSprite,
            "actionPawnComaSprite" => d.actionPawnComaSprite, "charaFinalReasoningSprite" => d.charaFinalReasoningSprite,
            "charaFinalReasoningKillerSprite" => d.charaFinalReasoningKillerSprite,
            "charaFinalReasoningSelectedSprite" => d.charaFinalReasoningSelectedSprite, "resultKillerSprite" => d.resultKillerSprite,
            "resultTargetSprite" => d.resultTargetSprite, "outSideCharaIconNormal" => d.outSideCharaIconNormal,
            "outSideCharaIconBad1" => d.outSideCharaIconBad1, "outSideCharaIconBad2" => d.outSideCharaIconBad2,
            "charaIntroLookIcon" => d.charaIntroLookIcon, "charaIntroFaceIcon" => d.charaIntroFaceIcon, _ => null,
        };

        static void SetSp(PawnTypeData d, string f, Sprite s)
        {
            switch (f)
            {
                case "charaInfoSprite": d.charaInfoSprite = s; break;
                case "charaInfoDamageSprite": d.charaInfoDamageSprite = s; break;
                case "charaInfoComaSprite": d.charaInfoComaSprite = s; break;
                case "charaTelopSprite": d.charaTelopSprite = s; break;
                case "actoinPawnSprite": d.actoinPawnSprite = s; break;
                case "actionPawnDamageSprite": d.actionPawnDamageSprite = s; break;
                case "actionPawnComaSprite": d.actionPawnComaSprite = s; break;
                case "charaFinalReasoningSprite": d.charaFinalReasoningSprite = s; break;
                case "charaFinalReasoningKillerSprite": d.charaFinalReasoningKillerSprite = s; break;
                case "charaFinalReasoningSelectedSprite": d.charaFinalReasoningSelectedSprite = s; break;
                case "resultKillerSprite": d.resultKillerSprite = s; break;
                case "resultTargetSprite": d.resultTargetSprite = s; break;
                case "outSideCharaIconNormal": d.outSideCharaIconNormal = s; break;
                case "outSideCharaIconBad1": d.outSideCharaIconBad1 = s; break;
                case "outSideCharaIconBad2": d.outSideCharaIconBad2 = s; break;
                case "charaIntroLookIcon": d.charaIntroLookIcon = s; break;
                case "charaIntroFaceIcon": d.charaIntroFaceIcon = s; break;
            }
        }

        class Swapped
        {
            public PawnTypeData d; public string key;
            public Queue<(string f, int tint)> todo; public Texture2D img; public string who; public int done;
            public readonly Dictionary<string, Sprite> orig = new();
            public bool sprites, panel; public Texture panelOrig;
            public readonly List<UnityEngine.Object> made = new();
        }
        static readonly Dictionary<IntPtr, Swapped> _swapped = new();
        static readonly Dictionary<string, Texture2D> _images = new();      // imagen (ruta / "auto:modelo") -> textura legible
        static readonly HashSet<string> _imageAsked = new();
        static readonly Dictionary<string, Texture2D> _panels = new();      // "nombre|w|h" -> placa
        static readonly HashSet<string> _panelAsked = new();

        static Dictionary<string, PawnTypeData> FindPawnData()
        {
            var r = new Dictionary<string, PawnTypeData>();
            foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<PawnTypeData>()))
            {
                var d = o.TryCast<PawnTypeData>();
                if (d != null && Array.IndexOf(Pawns, d.name) >= 0) r[d.name] = d;   // si hay varias, la ultima
            }
            return r;
        }

        static void ApplySprites()
        {
            if (_cur == null) return;
            bool pending = false;
            for (int i = 0; i < 6; i++) if (_cur.pos[i] != null) pending = true;
            if (!pending) return;
            var data = FindPawnData();
            for (int i = 0; i < 6; i++)
            {
                var e = _cur.pos[i];
                if (e == null || !data.TryGetValue(Pawns[i], out var d)) continue;
                if (!_swapped.TryGetValue(d.Pointer, out var sw)) _swapped[d.Pointer] = sw = new Swapped { d = d, key = Pawns[i] };
                if (!sw.sprites && sw.todo == null)
                {
                    // su imagen, metida en la forma de cada retrato original; sin imagen, una silueta en esa forma.
                    // Se hacen unos pocos por fotograma (SpriteJobs) para no dar tirones al empezar la partida.
                    sw.img = !string.IsNullOrEmpty(e.image) ? LoadImage(Path.Combine(LiveMods.LiveDir, e.image)) : null;
                    sw.who = e.name ?? e.id;
                    sw.todo = new Queue<(string, int)>();
                    foreach (var ft in SpriteFields) if (GetSp(d, ft.name) != null) sw.todo.Enqueue(ft);
                }
                if (!sw.panel && e.name != null && d.namePanelTexture != null)
                {
                    var o = d.namePanelTexture;
                    int w = Math.Min(1024, Math.Max(64, o.width)), h = Math.Min(512, Math.Max(16, o.height));
                    var p = PanelFor(e.name, w, h);
                    if (p != null)
                    {
                        sw.panelOrig = o;
                        d.namePanelTexture = p;
                        sw.panel = true;
                        RefreshNamePanels(d, p);
                    }
                }
            }
        }

        /// <summary>Las placas con el nombre que ya estan en el tablero se repintan con la nueva.</summary>
        static void RefreshNamePanels(PawnTypeData d, Texture tex)
        {
            try
            {
                foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<Pawn>()))
                {
                    var p = o.TryCast<Pawn>();
                    if (p == null || p.pawnTypeData == null || p.pawnTypeData.Pointer != d.Pointer) continue;
                    foreach (var c in p.GetComponentsInChildren(Il2CppType.Of<NamePanel>(), true))
                    {
                        var np = c.TryCast<NamePanel>();
                        if (np != null) { var tt = tex; np.SetTexture(ref tt); }
                    }
                }
            }
            catch (Exception e) { Warn("panel", "[Personajes] placa del nombre: " + e.Message); }
        }

        /// <summary>Cada fotograma, retratos pendientes hasta ~8 ms.</summary>
        static void SpriteJobs()
        {
            if (_swapped.Count == 0) return;
            var sw0 = System.Diagnostics.Stopwatch.StartNew();
            foreach (var sw in _swapped.Values)
            {
                if (sw.todo == null || sw.sprites) continue;
                while (sw.todo.Count > 0 && sw0.ElapsedMilliseconds < 8)
                {
                    var (f, tint) = sw.todo.Dequeue();
                    try
                    {
                        var o = GetSp(sw.d, f);
                        if (o == null) continue;
                        var s = Fitted(sw.img, o, tint, sw.made);
                        if (s == null) continue;
                        sw.orig[f] = o;
                        SetSp(sw.d, f, s);
                        sw.done++;
                    }
                    catch (Exception e) { Warn("fit" + f, "[Personajes] " + f + ": " + e.Message); }
                }
                if (sw.todo.Count == 0)
                {
                    sw.sprites = true;
                    Plugin.L.LogInfo($"[Personajes] {sw.key}: {sw.done} retrato(s) {(sw.img != null ? "con la imagen" : "con la silueta")} de {sw.who}");
                }
                if (sw0.ElapsedMilliseconds >= 8) return;
            }
        }

        static void RestoreSprites()
        {
            foreach (var sw in _swapped.Values)
            {
                try
                {
                    if (sw.d != null)
                    {
                        foreach (var kv in sw.orig) SetSp(sw.d, kv.Key, kv.Value);
                        if (sw.panel && sw.panelOrig != null) { sw.d.namePanelTexture = sw.panelOrig; RefreshNamePanels(sw.d, sw.panelOrig); }
                    }
                }
                catch { }
                foreach (var o in sw.made) if (o != null) UnityEngine.Object.Destroy(o);
            }
            _swapped.Clear();
        }

        internal static Texture2D LoadImage(string path)
        {
            if (_images.TryGetValue(path, out var have) && have != null) return have;
            try
            {
                if (!File.Exists(path)) return null;
                var t = new Texture2D(2, 2, TextureFormat.RGBA32, false) { name = "csr_roster_img", hideFlags = HideFlags.DontUnloadUnusedAsset };
                if (!ImageConversion.LoadImage(t, File.ReadAllBytes(path), false)) { UnityEngine.Object.Destroy(t); return null; }
                if (Math.Max(t.width, t.height) > 1024)                    // mas no hace falta (el retrato mas grande es de 920)
                {
                    float k = 1024f / Math.Max(t.width, t.height);
                    int w = Math.Max(1, (int)(t.width * k)), h = Math.Max(1, (int)(t.height * k));
                    var src = Px.Get(t);
                    var dst = new Color32[w * h];
                    for (int y = 0; y < h; y++)
                        for (int x = 0; x < w; x++)
                            dst[y * w + x] = Bilinear(src, t.width, t.height, (x + 0.5f) / k - 0.5f, (y + 0.5f) / k - 0.5f);
                    UnityEngine.Object.Destroy(t);
                    t = Px.Make(w, h, dst, "csr_roster_img");
                }
                _images[path] = t;
                return t;
            }
            catch (Exception ex) { Warn("img" + path, "[Personajes] " + path + ": " + ex.Message); return null; }
        }

        /// <summary>Un sprite del mismo tamano y forma que el original, con la imagen recortada para llenarlo (centrada
        /// a lo ancho, tirando hacia arriba, donde suele estar la cara) y tenida si es de herido o en coma.</summary>
        static Sprite Fitted(Texture2D img, Sprite orig, int tint, List<UnityEngine.Object> made)
        {
            // la forma del original (su transparencia): el retrato nuevo no se sale de ella
            Texture2D shape;
            try { shape = SpriteToTex(orig); } catch { return null; }
            var mask = Pixels(shape);
            _pixels.Remove(shape.Pointer);
            int w = shape.width, h = shape.height;
            UnityEngine.Object.Destroy(shape);
            if (w < 4 || h < 4 || w > 2048 || h > 2048) return null;
            Color32[] src = null; int sw = 0, sh = 0; float scale = 1, x0 = 0, y0 = 0;
            if (img != null)
            {
                src = Pixels(img); sw = img.width; sh = img.height;
                scale = Math.Max((float)w / sw, (float)h / sh);               // cubrir
                float cw = w / scale, ch = h / scale;
                x0 = (sw - cw) / 2f; y0 = (sh - ch) * 0.75f;                   // quitar mas de abajo que de arriba
            }
            var sil = img == null ? Pixels(RosterUi.Silhouette()) : null;
            int sn = 128;
            float sSize = h * 0.86f, sLeft = (w - sSize) / 2f;
            var bg = new Color32(34, 36, 46, 255);
            var fg = new Color32(122, 128, 150, 255);
            var dst = new Color32[w * h];
            for (int y = 0; y < h; y++)
            {
                float sy = y0 + (y + 0.5f) / scale - 0.5f;
                for (int x = 0; x < w; x++)
                {
                    byte m = mask[y * w + x].a;
                    if (m == 0) { dst[y * w + x] = new Color32(0, 0, 0, 0); continue; }
                    Color32 c;
                    if (src != null) c = Bilinear(src, sw, sh, x0 + (x + 0.5f) / scale - 0.5f, sy);
                    else
                    {
                        float u = (x - sLeft) / sSize * sn, v = y / sSize * sn;
                        float a = u >= 0 && v >= 0 && u < sn && v < sn ? Bilinear(sil, sn, sn, u, v).a / 255f : 0f;
                        c = new Color32((byte)(bg.r + (fg.r - bg.r) * a), (byte)(bg.g + (fg.g - bg.g) * a), (byte)(bg.b + (fg.b - bg.b) * a), 255);
                    }
                    if (tint == 1) c = new Color32(c.r, (byte)(c.g * 0.55f), (byte)(c.b * 0.55f), c.a);
                    else if (tint == 2) { byte g = (byte)((c.r * 0.3f + c.g * 0.59f + c.b * 0.11f) * 0.6f); c = new Color32(g, g, g, c.a); }
                    c.a = (byte)(c.a * m / 255);
                    dst[y * w + x] = c;
                }
            }
            var tex = new Texture2D(w, h, TextureFormat.RGBA32, false) { name = "csr_roster_" + orig.name, hideFlags = HideFlags.DontUnloadUnusedAsset, wrapMode = TextureWrapMode.Clamp };
            Px.Set(tex, dst);
            var r = orig.rect;
            var pivot = new Vector2(orig.pivot.x / Math.Max(1f, r.width), orig.pivot.y / Math.Max(1f, r.height));
            var s = Sprite.Create(tex, new Rect(0, 0, w, h), pivot, orig.pixelsPerUnit * (w / Math.Max(1f, r.width)), 0, SpriteMeshType.FullRect);
            s.name = orig.name;
            s.hideFlags = HideFlags.DontUnloadUnusedAsset;
            made.Add(s); made.Add(tex);
            return s;
        }

        static readonly Dictionary<IntPtr, Color32[]> _pixels = new();
        internal static Color32[] Pixels(Texture2D t)
        {
            if (_pixels.TryGetValue(t.Pointer, out var p) && p.Length == t.width * t.height) return p;
            p = Px.Get(t);
            _pixels[t.Pointer] = p;
            return p;
        }

        internal static Color32 Bilinear(Color32[] px, int w, int h, float x, float y)
        {
            x = Mathf.Clamp(x, 0, w - 1); y = Mathf.Clamp(y, 0, h - 1);
            int x0 = (int)x, y0 = (int)y, x1 = Math.Min(w - 1, x0 + 1), y1 = Math.Min(h - 1, y0 + 1);
            float fx = x - x0, fy = y - y0;
            Color32 a = px[y0 * w + x0], b = px[y0 * w + x1], c = px[y1 * w + x0], d = px[y1 * w + x1];
            byte L(byte p, byte q, byte r, byte s) => (byte)Mathf.Clamp(Mathf.Lerp(Mathf.Lerp(p, q, fx), Mathf.Lerp(r, s, fx), fy) + 0.5f, 0, 255);
            return new Color32(L(a.r, b.r, c.r, d.r), L(a.g, b.g, c.g, d.g), L(a.b, b.b, c.b, d.b), L(a.a, b.a, c.a, d.a));
        }

        // ------------------------------------------------------------ placa con el nombre
        static Texture2D PanelFor(string name, int w, int h)
        {
            string key = name + "|" + w + "|" + h;
            if (_panels.TryGetValue(key, out var have)) return have;
            if (!_panelAsked.Add(key)) return null;
            var go = new GameObject("CSR_Placa");
            go.layer = Rig.Layer;
            var t = go.AddComponent<TextMeshPro>();
            var font = ModOffer.GameFont();
            if (font != null) t.font = font;
            t.text = name;
            t.alignment = TextAlignmentOptions.Center;
            t.enableWordWrapping = false;
            t.enableAutoSizing = true;
            t.fontSizeMin = 1; t.fontSizeMax = 40;
            t.color = Color.white;
            t.rectTransform.sizeDelta = new Vector2(w / (float)h * 2f, 2f);   // mismo aspecto que la placa
            t.margin = new Vector4(0.12f, 0.2f, 0.12f, 0.2f);
            t.ForceMeshUpdate();
            Snap(go, null, w, h, -1f, Color.black, tex =>
            {
                // texto blanco sobre negro -> blanco con transparencia, con un borde oscuro para que se lea
                var px = Pixels(tex);
                var outp = new Color32[px.Length];
                for (int y = 0; y < h; y++)
                    for (int x = 0; x < w; x++)
                    {
                        int m = px[y * w + x].r, o = 0;
                        for (int dy = -2; dy <= 2 && o < 255; dy++)
                            for (int dx = -2; dx <= 2; dx++)
                            {
                                int xx = x + dx, yy = y + dy;
                                if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
                                o = Math.Max(o, px[yy * w + xx].r);
                            }
                        byte a = (byte)Math.Max(m, (int)(o * 0.85f));
                        byte v = (byte)m;
                        outp[y * w + x] = new Color32(v, v, v, a);
                    }
                Px.Set(tex, outp);
                _pixels.Remove(tex.Pointer);
                _panels[key] = tex;
            });
            return null;
        }

        // ------------------------------------------------------------ retratos originales para el Selector
        // Solo en este PC (csr_live/cache), para ensenarlos en la sala de espera, donde el juego aun no los tiene:
        //   mono_<X>.png  la cara de la presentacion del personaje (en el juego es en blanco y negro)
        //   color_<X>.png el mismo dibujo en color (el de sus dialogos), cuando el juego lo tiene cargado
        //   face_ThreatTypeData_Traitor.png  la cara del traidor, sacada de su modelo 3D
        //   idle_<X>.bin  su animacion de reposo (Models.BakeIdle), grabada en la partida
        static float _nextCache;
        static bool _traitorAsked;
        internal static string MonoPath(string key) => Path.Combine(LiveMods.LiveDir, "cache", "mono_" + key + ".png");
        internal static string ColorPath(string key) => Path.Combine(LiveMods.LiveDir, "cache", "color_" + key + ".png");
        internal static string FacePath(string key) => Path.Combine(LiveMods.LiveDir, "cache", "face2_" + key + ".png");

        static void CacheOriginals()
        {
            if (Time.unscaledTime < _nextCache) return;
            _nextCache = Time.unscaledTime + 10f;
            string dir = Path.Combine(LiveMods.LiveDir, "cache");
            Directory.CreateDirectory(dir);
            try
            {
                foreach (var old in Directory.GetFiles(dir, "orig*.png")) File.Delete(old);                  // las de antes
                foreach (var old in Directory.GetFiles(dir, "face_*.png")) File.Delete(old);
            }
            catch { }

            bool needMono = false, needColor = false;
            foreach (var k in Pawns) { if (!File.Exists(MonoPath(k))) needMono = true; if (!File.Exists(ColorPath(k))) needColor = true; }
            if (needMono)
                foreach (var kv in FindPawnData())
                {
                    if (File.Exists(MonoPath(kv.Key))) continue;
                    _swapped.TryGetValue(kv.Value.Pointer, out var sw);
                    var sp = sw != null && sw.orig.TryGetValue("charaIntroFaceIcon", out var o) ? o : kv.Value.charaIntroFaceIcon;
                    if (sp != null) SaveSprite(sp, MonoPath(kv.Key));
                }
            if (needColor)
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<Sprite>()))
                {
                    var sp = o.TryCast<Sprite>();
                    if (sp == null) continue;
                    var m = Regex.Match(sp.name, @"^talk_chara_pawn0([1-6])$");
                    if (!m.Success) continue;
                    string key = Pawns[m.Groups[1].Value[0] - '1'];
                    if (!File.Exists(ColorPath(key)) && SaveSprite(sp, ColorPath(key))) Plugin.L.LogInfo("[Personajes] retrato en color de " + key + " para el Selector");
                }
            if (!File.Exists(FacePath(Traitor)) && !_traitorAsked) _traitorAsked = SnapTraitorFace(null);
        }

        static bool SaveSprite(Sprite sp, string path)
        {
            try
            {
                var t = SpriteToTex(sp);
                File.WriteAllBytes(path, ImageConversion.EncodeToPNG(t));
                UnityEngine.Object.Destroy(t);
                return true;
            }
            catch (Exception e) { Warn("save" + path, "[Personajes] " + Path.GetFileName(path) + ": " + e.Message); return false; }
        }

        /// <summary>La cara del traidor, sacada de su modelo 3D (se guarda para la siguiente vez).</summary>
        internal static bool SnapTraitorFace(Action<Texture2D> then)
        {
            return SnapChar(Traitor, null, 400, 440, 0.2f, PortraitBg, tex =>
            {
                try { File.WriteAllBytes(FacePath(Traitor), ImageConversion.EncodeToPNG(tex)); Plugin.L.LogInfo("[Personajes] cara del traidor para el Selector"); }
                catch (Exception e) { Warn("cachet", "[Personajes] cara del traidor: " + e.Message); }
                then?.Invoke(tex);
            });
        }

        /// <summary>En la partida: graba el reposo de los personajes que aun no lo tienen (para la vista del Selector).</summary>
        static void BakeIdles()
        {
            bool missing = !File.Exists(Models.IdlePath(Traitor));
            foreach (var k in Pawns) if (!File.Exists(Models.IdlePath(k))) missing = true;
            if (!missing) return;
            try
            {
                foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<Pawn>()))
                {
                    var p = o.TryCast<Pawn>();
                    if (p?.pawnTypeData != null) BakeOne(p.pawnTypeData.name, p.gameObject);
                }
                foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<Threat>()))
                {
                    var t = o.TryCast<Threat>();
                    if (t?.threatTypeData != null) BakeOne(t.threatTypeData.name, t.gameObject);
                }
            }
            catch (Exception e) { Warn("bakes", "[Personajes] reposo: " + e.Message); }
        }

        static readonly HashSet<string> _bakeTried = new();
        static void BakeOne(string key, GameObject owner)
        {
            if (key != Traitor && Array.IndexOf(Pawns, key) < 0) return;
            if (File.Exists(Models.IdlePath(key)) || !_bakeTried.Add(key)) return;
            var sa = owner.GetComponentInChildren<SimpleAnimation>(true);
            var clip = sa != null ? Models.IdleClip(sa) : null;
            GameObject animGo = sa != null ? sa.gameObject : null;
            if (clip == null)
            {
                // sin SimpleAnimation (el traidor): las animaciones de su Animator
                var seen = new List<string>();
                foreach (var c in owner.GetComponentsInChildren(Il2CppType.Of<Animator>(), true))
                {
                    var an = c.TryCast<Animator>();
                    var rac = an?.runtimeAnimatorController;
                    if (rac == null) continue;
                    var best = Models.IdleClip(rac.animationClips, seen);
                    if (best != null) { clip = best; animGo = an.gameObject; break; }
                }
                if (clip == null)
                {
                    Warn("noidle" + key, "[Personajes] " + key + ": no encuentro su animacion de reposo (tiene: " + string.Join(", ", seen) + ")");
                    return;
                }
            }
            var root = Models.ModelRootOf(owner) ?? owner;
            Models.BakeIdle(key, animGo, clip, root);
        }

        /// <summary>Cuanto color tiene una imagen (saturacion media de lo que no es transparente, 0..1).</summary>
        static float Saturation(Texture2D t)
        {
            var px = Pixels(t);
            _pixels.Remove(t.Pointer);
            double sum = 0; int n = 0;
            for (int i = 0; i < px.Length; i += 7)
            {
                var c = px[i];
                if (c.a < 128) continue;
                int mx = Math.Max(c.r, Math.Max(c.g, c.b)), mn = Math.Min(c.r, Math.Min(c.g, c.b));
                if (mx > 0) sum += (mx - mn) / (double)mx;
                n++;
            }
            return n > 0 ? (float)(sum / n) : 0f;
        }

        internal static Texture2D SpriteToTex(Sprite sp)
        {
            var src = sp.texture;
            var r = sp.textureRect;
            int w = Math.Max(1, (int)r.width), h = Math.Max(1, (int)r.height);
            var rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32);
            Graphics.Blit(src, rt, new Vector2(r.width / src.width, r.height / src.height), new Vector2(r.x / src.width, r.y / src.height));
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false);
            t.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            t.Apply();
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);
            return t;
        }

        // ------------------------------------------------------------ fotos de modelos y textos (camara aparte)
        class Job
        {
            public GameObject content; public List<UnityEngine.Object> made; public int w, h, frames;
            public float frac; public Color bg; public Action<Texture2D> done; public Action cleanup;
        }
        static readonly Queue<Job> _jobs = new();
        static Job _job;
        static Rig _snapRig;

        /// <summary>Saca una foto de content (que pasa a ser nuestro y se destruye despues). frac: parte de arriba del modelo
        /// que entra (1 = entero); -1 = camara ortografica que encuadra un texto.</summary>
        internal static void Snap(GameObject content, List<UnityEngine.Object> made, int w, int h, float frac, Color bg, Action<Texture2D> done, Action cleanup = null)
        {
            content.SetActive(false);
            _jobs.Enqueue(new Job { content = content, made = made, w = w, h = h, frac = frac, bg = bg, done = done, cleanup = cleanup });
        }

        /// <summary>Foto de un personaje en reposo (el del juego, o con un modelo propio encima). false si no se puede.</summary>
        internal static bool SnapChar(string baseKey, string model, int w, int h, float frac, Color bg, Action<Texture2D> done)
        {
            var pv = Models.PreviewChar(baseKey, model, Rig.Layer);
            if (pv != null)
            {
                Snap(pv.holder, null, w, h, frac, bg, done, () => Models.PreviewDestroy(pv));
                return true;
            }
            if (model == null) return false;
            var made = new List<UnityEngine.Object>();
            var go = Models.PreviewGlb(model, Rig.Layer, made);                // sin el juego: quieto, tal cual
            if (go == null) return false;
            Snap(go, made, w, h, frac, bg, done);
            return true;
        }

        static void Snaps()
        {
            if (_job != null)
            {
                if (++_job.frames < 3) return;                              // ya se ha pintado (al final del fotograma anterior)
                Texture2D tex = null;
                try
                {
                    var prev = RenderTexture.active;
                    RenderTexture.active = _snapRig.rt;
                    tex = new Texture2D(_job.w, _job.h, TextureFormat.RGBA32, false) { hideFlags = HideFlags.DontUnloadUnusedAsset, wrapMode = TextureWrapMode.Clamp };
                    tex.ReadPixels(new Rect(0, 0, _job.w, _job.h), 0, 0);
                    tex.Apply();
                    RenderTexture.active = prev;
                }
                catch (Exception e) { Warn("snapread", "[Personajes] foto: " + e.Message); }
                try { _job.cleanup?.Invoke(); } catch { }
                _snapRig.Clear();
                if (_job.made != null) foreach (var o in _job.made) if (o != null) UnityEngine.Object.Destroy(o);
                var j = _job; _job = null;
                _snapRig.cam.enabled = false;
                if (tex != null) try { j.done(tex); } catch (Exception e) { Warn("snapdone", "[Personajes] " + e.Message); }
                return;
            }
            if (_jobs.Count == 0) return;
            _job = _jobs.Dequeue();
            if (_job.content == null) { _job = null; return; }
            if (_snapRig == null || _snapRig.root == null) _snapRig = Rig.Make("CSR_Fotos", new Vector3(0, -6000, 0));
            _snapRig.Size(_job.w, _job.h, _job.bg);
            _job.content.SetActive(true);
            _snapRig.Show(_job.content, _job.frac);
            _snapRig.cam.enabled = true;
        }
    }

    /// <summary>Una camara con su luz, lejos de la escena, que pinta un objeto en una textura (capa propia).</summary>
    sealed class Rig
    {
        public const int Layer = 31;
        public GameObject root, content;
        public Camera cam;
        public RenderTexture rt;
        float _frac = 1f;

        public static Rig Make(string name, Vector3 at)
        {
            var r = new Rig { root = new GameObject(name) };
            UnityEngine.Object.DontDestroyOnLoad(r.root);
            r.root.transform.position = at;
            var cgo = new GameObject("Camara");
            cgo.transform.SetParent(r.root.transform, false);
            r.cam = cgo.AddComponent<Camera>();
            r.cam.enabled = false;
            r.cam.cullingMask = 1 << Layer;
            r.cam.clearFlags = CameraClearFlags.SolidColor;
            r.cam.fieldOfView = 28f;
            r.cam.allowHDR = false;
            r.cam.allowMSAA = false;
            r.cam.depth = -50;
            var lgo = new GameObject("Luz");
            lgo.transform.SetParent(r.root.transform, false);
            lgo.transform.rotation = Quaternion.LookRotation(new Vector3(0.35f, -0.55f, -1f));
            var l = lgo.AddComponent<Light>();
            l.type = LightType.Directional;
            l.intensity = 1.15f;
            l.cullingMask = 1 << Layer;
            var lgo2 = new GameObject("Relleno");
            lgo2.transform.SetParent(r.root.transform, false);
            lgo2.transform.rotation = Quaternion.LookRotation(new Vector3(-0.6f, 0.1f, -1f));
            var l2 = lgo2.AddComponent<Light>();
            l2.type = LightType.Directional;
            l2.intensity = 0.45f;
            l2.cullingMask = 1 << Layer;
            return r;
        }

        public void Size(int w, int h, Color bg)
        {
            if (rt == null || rt.width != w || rt.height != h)
            {
                if (rt != null) { cam.targetTexture = null; rt.Release(); UnityEngine.Object.Destroy(rt); }
                rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32) { name = "csr_rig" };
                rt.Create();
            }
            cam.targetTexture = rt;
            cam.backgroundColor = bg;
        }

        public void Show(GameObject c, float frac)
        {
            Clear();
            content = c;
            _frac = frac;
            c.transform.SetParent(root.transform, false);
            c.transform.localPosition = Vector3.zero;
            c.transform.localRotation = Quaternion.identity;
            foreach (var t in c.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = Layer;
            Aim();
        }

        /// <summary>Encuadra el contenido (la parte de arriba que pide frac) mirandolo de frente.</summary>
        public void Aim()
        {
            if (content == null) return;
            var b = Measure(content);
            float aspect = rt != null ? rt.width / (float)rt.height : 1f;
            if (_frac < 0)
            {
                var rect = content.GetComponent<RectTransform>();             // un texto: se encuadra su recuadro entero
                if (rect != null)
                {
                    // (GetWorldCorners no funciona desde el plugin: devuelve ceros)
                    var rr = rect.rect;
                    Vector3 lo = rect.TransformPoint(new Vector3(rr.xMin, rr.yMin, 0f)), hi = rect.TransformPoint(new Vector3(rr.xMax, rr.yMax, 0f));
                    b = new Bounds((lo + hi) / 2f, new Vector3(Math.Abs(hi.x - lo.x), Math.Abs(hi.y - lo.y), 0.01f));
                }
                cam.orthographic = true;
                cam.orthographicSize = Math.Max(b.extents.y, b.extents.x / aspect);
                cam.transform.position = b.center + new Vector3(0, 0, -5f);
                cam.transform.rotation = Quaternion.identity;
                cam.nearClipPlane = 0.01f; cam.farClipPlane = 20f;
                return;
            }
            cam.orthographic = false;
            float top = b.max.y, bottom = b.max.y - b.size.y * Mathf.Clamp01(_frac);
            var center = new Vector3(b.center.x, (top + bottom) / 2f, b.center.z);
            float half = Math.Max((top - bottom) / 2f, b.extents.x / aspect) * 1.08f;
            float dist = half / Mathf.Tan(cam.fieldOfView * 0.5f * Mathf.Deg2Rad) + b.extents.z;
            cam.transform.position = center + new Vector3(0, 0, dist);
            cam.transform.rotation = Quaternion.LookRotation(Vector3.back);
            cam.nearClipPlane = Math.Max(0.01f, dist * 0.05f);
            cam.farClipPlane = dist * 3f + b.size.magnitude * 2f;
        }

        /// <summary>Lo que ocupa: los huesos de las mallas con esqueleto (sus "bounds" no valen hasta que se pintan una
        /// vez) y las cajas de las demas. Solo lo que esta a la vista.</summary>
        public static Bounds Measure(GameObject content)
        {
            var b = new Bounds();
            bool any = false, skinned = false;
            void Add(Vector3 p) { if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p); }
            foreach (var r in content.GetComponentsInChildren<Renderer>(false))
            {
                if (!r.enabled) continue;
                var smr = r.TryCast<SkinnedMeshRenderer>();
                if (smr != null)
                {
                    var bones = smr.bones;
                    if (bones != null && bones.Length > 0)
                    {
                        for (int i = 0; i < bones.Length; i++) if (bones[i] != null) Add(bones[i].position);
                        skinned = true;
                        continue;
                    }
                }
                var rb = r.bounds;
                Add(rb.min); Add(rb.max);
            }
            if (!any) return new Bounds(content.transform.position, Vector3.one);
            if (skinned)
            {
                float h = Math.Max(0.1f, b.size.y);
                b.SetMinMax(b.min - new Vector3(0.08f * h, 0.02f * h, 0.08f * h), b.max + new Vector3(0.08f * h, 0.1f * h, 0.08f * h));
            }
            return b;
        }

        public void Clear()
        {
            if (content != null) UnityEngine.Object.Destroy(content);
            content = null;
        }

        public void Destroy()
        {
            Clear();
            if (cam != null) cam.targetTexture = null;
            if (rt != null) { rt.Release(); UnityEngine.Object.Destroy(rt); }
            if (root != null) UnityEngine.Object.Destroy(root);
            rt = null; root = null;
        }
    }
}
