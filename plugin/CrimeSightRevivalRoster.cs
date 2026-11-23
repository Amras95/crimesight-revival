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

        internal class Entry { public string id, name, image, model, role, animFrom; public Dictionary<string, string> talk = new(), talkImages = new(); }
        internal static readonly Color PortraitBg = new Color(0.16f, 0.17f, 0.22f, 1f);
        class State { public string id = ""; public readonly Entry[] pos = new Entry[6]; public Entry traitor; }

        static string File_ => Path.Combine(LiveMods.LiveDir, "roster.json");
        static string _sig = "";
        static State _cur;
        static float _next, _nextSprites, _nextTalk;

        // ------------------------------------------------------------ una sola frase en la presentacion
        // En la presentacion de la partida algunos personajes hablan dos veces (una por cada companero al que saludan:
        // pawnGameStart03, pawnGameStart06...). Un personaje nuevo tiene una sola frase para eso, asi que solo dice la
        // primera; las demas no entran en la cola de dialogos del juego.
        static readonly Dictionary<string, string> _introLine = new();   // "partida|posicion" -> su frase

        public static void Init(HarmonyLib.Harmony h)
        {
            try
            {
                var m = HarmonyLib.AccessTools.DeclaredMethod(typeof(CharaTalkDialogue), "OpenTalkDialogue");
                if (m != null) h.Patch(m, prefix: new HarmonyLib.HarmonyMethod(typeof(Roster).GetMethod(nameof(BeforeOpenTalk),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Personajes] presentacion: " + e.Message); }
        }

        static bool BeforeOpenTalk(object[] __args, ref bool __result)
        {
            try
            {
                if (_cur == null || __args == null || __args.Length == 0) return true;
                var d = (__args[0] as Il2CppSystem.Object)?.TryCast<HintTalkData>() ?? __args[0] as HintTalkData;
                if (d == null) return true;
                string name = d.name ?? "";
                var m = TalkKey.Match(name);
                if (!m.Success || BaseSituation(m.Groups[2].Value) != "pawnGameStart") return true;
                int i = m.Groups[1].Value[0] - '1';
                if (_cur.pos[i] == null) return true;
                string k = _cur.id + "|" + i;
                // Las frases se piden todas al empezar y el juego las pone en cola; al cerrarse una, saca la siguiente
                // llamando OTRA VEZ a esta misma funcion. Por eso la frase elegida tiene que poder abrirse siempre, y las
                // demas no se dejan entrar en la cola (asi la cola nunca llega a pedirlas).
                if (!_introLine.TryGetValue(k, out var chosen)) { _introLine[k] = name; return true; }
                if (chosen == name) return true;
                Plugin.L.LogInfo("[Personajes] presentacion: " + (_cur.pos[i].name ?? Pawns[i]) + " ya habla en " + chosen + ", se quita " + name);
                __result = true;
                return false;
            }
            catch { return true; }
        }

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
                if (Time.unscaledTime >= _nextTalk) { _nextTalk = Time.unscaledTime + 5f; ApplyTalkPics(); }
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
            RestoreTalkPics();
            _nextTalk = 0f;
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
            if (e.TryGetProperty("talk_images", out var ti) && ti.ValueKind == JsonValueKind.Object)
                foreach (var p in ti.EnumerateObject())
                    if (p.Value.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(p.Value.GetString())) en.talkImages[p.Name] = p.Value.GetString();
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
        // Pictures made here (portraits and name plates), and the game's own ones for each character. A copy of a
        // character's data made while it had a new character's pictures (the game makes some) carries them too:
        // taking "the original" from such a copy would keep the new character's picture, and it showed as a white
        // portrait (destroyed picture) and the new name at their feet in later matches. So originals always come
        // from the game's own pictures, and every copy is put back, not only the one that was changed.
        static readonly HashSet<IntPtr> _ours = new();
        static readonly Dictionary<string, Dictionary<string, Sprite>> _gameSprites = new();   // character -> field -> the game's
        static readonly Dictionary<string, Texture> _gamePanel = new();                         // character -> the game's name plate
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
                    if (_ours.Contains(o.Pointer)) { if (!_gamePanel.TryGetValue(Pawns[i], out o) || o == null) continue; }
                    else _gamePanel[Pawns[i]] = o;
                    int w = Math.Min(1024, Math.Max(64, o.width)), h = Math.Min(512, Math.Max(16, o.height));
                    var p = PanelFor(e.name, w, h);
                    if (p != null)
                    {
                        _ours.Add(p.Pointer);
                        sw.panelOrig = o;
                        d.namePanelTexture = p;
                        sw.panel = true;
                        RefreshNamePanels(d, p);
                    }
                }
            }
        }

        // ------------------------------------------------------------ retratos de los dialogos
        // Las frases de cada personaje (HintTalkData) llevan su retrato (talk_chara_pawn0N, _impatient, _killer,
        // talk_chara_2way_pawn0N). Con un personaje nuevo en ese sitio, sus dialogos llevan su imagen (o la silueta),
        // en la forma del retrato original, igual que los demas retratos.
        static readonly Dictionary<IntPtr, (HintTalkData d, Sprite orig)> _talkSwapped = new();
        static readonly Dictionary<string, Sprite> _talkMade = new();      // "sprite original|imagen" -> retrato
        static readonly List<UnityEngine.Object> _talkObjs = new();
        static int _talkSeen = -1;
        static readonly Regex TalkSprite = new(@"^talk_chara_(?:2way_)?pawn0([1-6])");

        static void ApplyTalkPics()
        {
            bool any = false;
            if (_cur != null) foreach (var e in _cur.pos) any |= e != null;
            if (!any) { RestoreTalkPics(); return; }
            var all = Resources.FindObjectsOfTypeAll(Il2CppType.Of<HintTalkData>());
            if (all.Length == _talkSeen) return;                              // nada nuevo cargado
            _talkSeen = all.Length;
            int n = 0;
            foreach (var o in all)
            {
                var d = o.TryCast<HintTalkData>();
                if (d == null || _talkSwapped.ContainsKey(d.Pointer)) continue;
                var sp = d.CharaImage;
                if (sp == null) continue;
                var m = TalkSprite.Match(sp.name);
                if (!m.Success) continue;
                var e = _cur.pos[m.Groups[1].Value[0] - '1'];
                if (e == null) continue;
                string path = TalkImageOf(e, d.name);
                string mk = sp.Pointer + "|" + path;
                if (!_talkMade.TryGetValue(mk, out var ns))
                {
                    var img = path != null ? LoadImage(Path.Combine(LiveMods.LiveDir, path)) : null;
                    try { ns = img != null ? FitContain(img, sp, _talkObjs) : Fitted(null, sp, 0, _talkObjs); }
                    catch (Exception ex) { Warn("talkfit", "[Personajes] dialogo: " + ex.Message); ns = null; }
                    _talkMade[mk] = ns;
                }
                if (ns == null) continue;
                _talkSwapped[d.Pointer] = (d, sp);
                d.CharaImage = ns;
                n++;
            }
            if (n > 0) Plugin.L.LogInfo($"[Personajes] {n} dialogo(s) con el retrato del personaje nuevo ({_talkMade.Count} imagen(es))");
        }

        /// <summary>La imagen de una frase (por su nombre, ctg_talk_pwPawn0N_situacion_...): la suya o la principal.</summary>
        static string TalkImageOf(Entry e, string dataName)
        {
            var m = dataName != null ? TalkKey.Match(dataName) : null;
            if (m != null && m.Success && e.talkImages.Count > 0)
            {
                string sit = BaseSituation(m.Groups[2].Value);
                if (e.talkImages.TryGetValue(sit, out var p)) return p;
                if (sit == "startAction")                                        // una sola frase para los tres estados
                    foreach (var k in new[] { "startAction_statusInjury", "startAction_statusHunger", "startAction_statusDying" })
                        if (e.talkImages.TryGetValue(k, out p)) return p;
            }
            return string.IsNullOrEmpty(e.image) ? null : e.image;
        }

        /// <summary>Retrato de dialogo: la imagen entera (sin lo transparente de alrededor), lo mas grande que quepa en
        /// el del juego, apoyada abajo y centrada; sin recortarla con la forma del original. Por abajo se desvanece como
        /// los del juego (que se funden con el recuadro del texto, que queda por delante).</summary>
        static Sprite FitContain(Texture2D img, Sprite orig, List<UnityEngine.Object> made)
        {
            var r = orig.rect;
            int w = Math.Max(4, Math.Min(2048, (int)r.width)), h = Math.Max(4, Math.Min(2048, (int)r.height));
            var src = Pixels(img);
            int sw = img.width, sh = img.height;
            int x0 = sw, y0 = sh, x1 = -1, y1 = -1;
            for (int y = 0; y < sh; y++)
                for (int x = 0; x < sw; x++)
                    if (src[y * sw + x].a > 16) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
            if (x1 < 0) { x0 = 0; y0 = 0; x1 = sw - 1; y1 = sh - 1; }
            float bw = x1 - x0 + 1, bh = y1 - y0 + 1;
            float k = Math.Min(w * 0.96f / bw, h * 0.98f / bh);
            float dw = bw * k, left = (w - dw) / 2f;
            // cuanto se ve el original en cada fila (lo mas opaco de la fila): asi se desvanece por abajo
            var fade = new float[h];
            try
            {
                var shape = SpriteToTex(orig);
                var mp = Pixels(shape);
                _pixels.Remove(shape.Pointer);
                int mw = shape.width, mh = shape.height;
                UnityEngine.Object.Destroy(shape);
                var rowMax = new float[mh];
                float top = 0;
                for (int y = 0; y < mh; y++)
                {
                    int m = 0;
                    for (int x = 0; x < mw; x++) { int a = mp[y * mw + x].a; if (a > m) m = a; }
                    rowMax[y] = m / 255f;
                    if (rowMax[y] > top) top = rowMax[y];
                }
                // de abajo arriba, la curva solo sube (los huecos de la figura no cuentan): la parte de abajo que se funde
                float run = 0;
                for (int y = 0; y < h; y++)
                {
                    int my = Math.Min(mh - 1, (int)((y + 0.5f) * mh / h));
                    run = Math.Max(run, top > 0 ? rowMax[my] / top : 1f);
                    fade[y] = run;
                }
            }
            catch { for (int y = 0; y < h; y++) fade[y] = 1f; }
            var dst = new Color32[w * h];
            for (int y = 0; y < h; y++)
            {
                float sy = y0 + (y + 0.5f) / k - 0.5f;
                if (sy > y1 + 0.5f) continue;
                float f = fade[y];
                for (int x = 0; x < w; x++)
                {
                    float sx = x0 + (x - left + 0.5f) / k - 0.5f;
                    if (sx < x0 - 0.5f || sx > x1 + 0.5f) continue;
                    var c = Bilinear(src, sw, sh, sx, sy);
                    if (f < 1f) c.a = (byte)(c.a * f);
                    dst[y * w + x] = c;
                }
            }
            var tex = Px.Make(w, h, dst, "csr_talk_" + orig.name);
            var pivot = new Vector2(orig.pivot.x / Math.Max(1f, r.width), orig.pivot.y / Math.Max(1f, r.height));
            var s = Sprite.Create(tex, new Rect(0, 0, w, h), pivot, orig.pixelsPerUnit, 0, SpriteMeshType.FullRect);
            s.name = orig.name;
            s.hideFlags = HideFlags.DontUnloadUnusedAsset;
            made.Add(s); made.Add(tex);
            return s;
        }

        static void RestoreTalkPics()
        {
            foreach (var v in _talkSwapped.Values) try { if (v.d != null) v.d.CharaImage = v.orig; } catch { }
            _talkSwapped.Clear();
            foreach (var o in _talkObjs) if (o != null) UnityEngine.Object.Destroy(o);
            _talkObjs.Clear();
            _talkMade.Clear();
            _talkSeen = -1;
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
                        if (_ours.Contains(o.Pointer)) { if (!GameSprite(sw.key, f, out o)) continue; }
                        else RememberGame(sw.key, f, o);
                        var s = Fitted(sw.img, o, tint, sw.made);
                        if (s == null) continue;
                        _ours.Add(s.Pointer);
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
            }
            PutBackCopies();
            foreach (var sw in _swapped.Values)
                foreach (var o in sw.made) if (o != null) UnityEngine.Object.Destroy(o);
            _swapped.Clear();
        }

        static void RememberGame(string key, string f, Sprite s)
        {
            if (!_gameSprites.TryGetValue(key, out var m)) _gameSprites[key] = m = new Dictionary<string, Sprite>();
            m[f] = s;
        }

        static bool GameSprite(string key, string f, out Sprite s)
        {
            s = null;
            return _gameSprites.TryGetValue(key, out var m) && m.TryGetValue(f, out s) && s != null;
        }

        /// <summary>Every copy of a character's data still showing a picture made here gets the game's own back.</summary>
        static void PutBackCopies()
        {
            if (_ours.Count == 0) return;
            int n = 0;
            try
            {
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<PawnTypeData>()))
                {
                    var d = o.TryCast<PawnTypeData>();
                    if (d == null || Array.IndexOf(Pawns, d.name) < 0) continue;
                    foreach (var ft in SpriteFields)
                    {
                        var s = GetSp(d, ft.name);
                        if ((object)s == null || !_ours.Contains(s.Pointer) || !GameSprite(d.name, ft.name, out var g)) continue;
                        SetSp(d, ft.name, g);
                        n++;
                    }
                    var t = d.namePanelTexture;
                    if ((object)t != null && _ours.Contains(t.Pointer) && _gamePanel.TryGetValue(d.name, out var gp) && gp != null)
                    {
                        d.namePanelTexture = gp;
                        RefreshNamePanels(d, gp);
                        n++;
                    }
                }
            }
            catch (Exception e) { Warn("copies", "[Personajes] " + e.Message); }
            if (n > 0) Plugin.L.LogInfo($"[Personajes] {n} picture(s) of a previous new character put back in copies of the game's data");
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
        // ------------------------------------------------------------ fondo de las fotos de resultados
        // Result_SSKiller_* / Result_SSTarget_* son la figura del personaje sobre un fondo: degradado gris con la arana
        // (asesino) o la diana (objetivo) a la derecha. Para un personaje nuevo se rehace ese fondo sin nadie a partir
        // de las seis fotos del juego (en cada una el personaje tapa una parte distinta):
        //   - el degradado sale de las primeras columnas (libres en todas);
        //   - el dibujo es lo que en al menos 2 fotos tiene su color y no el del fondo, en trozos grandes que se ven
        //     claros en casi todas; lo que tapan los personajes se completa con su simetria (la arana es simetrica de
        //     izquierda a derecha; la diana tambien de arriba abajo).
        // Se guarda en csr_live/cache/bg_<campo>.png (solo en este PC).
        static readonly Dictionary<string, Color32[]> _under = new();

        static Color32[] UnderFor(Sprite orig, int w, int h)
        {
            string n = orig.name ?? "";
            string field = n.StartsWith("Result_SSKiller_") ? "resultKillerSprite" : n.StartsWith("Result_SSTarget_") ? "resultTargetSprite" : null;
            if (field == null) return null;
            string key = field + "|" + w + "x" + h;
            if (_under.TryGetValue(key, out var have)) return have;
            Color32[] bg = null;
            string path = Path.Combine(LiveMods.LiveDir, "cache", "bg_" + field + ".png");
            try
            {
                var cached = LoadImage(path);
                if (cached != null && cached.width == w && cached.height == h) bg = Pixels(cached);
                if (bg == null)
                {
                    var all = new List<Color32[]>();
                    foreach (var kv in FindPawnData())
                    {
                        Sprite sp = _swapped.TryGetValue(kv.Value.Pointer, out var sw) && sw.orig.TryGetValue(field, out var o) ? o : GetSp(kv.Value, field);
                        if (sp == null || !(sp.name ?? "").StartsWith("Result_SS")) continue;
                        var t = SpriteToTex(sp);
                        if (t.width == w && t.height == h) all.Add(Pixels(t));
                        _pixels.Remove(t.Pointer);
                        UnityEngine.Object.Destroy(t);
                    }
                    if (all.Count >= 4)
                    {
                        bg = CleanBackground(all, w, h, field == "resultTargetSprite");
                        try
                        {
                            Directory.CreateDirectory(Path.GetDirectoryName(path));
                            var t = Px.Make(w, h, bg, "csr_bg");
                            File.WriteAllBytes(path, ImageConversion.EncodeToPNG(t));
                            UnityEngine.Object.Destroy(t);
                        }
                        catch { }
                        Plugin.L.LogInfo($"[Personajes] fondo de {field} rehecho ({all.Count} fotos del juego)");
                    }
                }
            }
            catch (Exception e) { Warn("under" + field, "[Personajes] fondo de " + field + ": " + e.Message); bg = null; }
            _under[key] = bg;
            return bg;
        }

        static Color32[] CleanBackground(List<Color32[]> all, int w, int h, bool vertical)
        {
            int k = all.Count, np = w * h;
            var med = new Color32[np]; var low = new int[np];
            var tr = new int[k]; var tg = new int[k]; var tb = new int[k]; var ts = new int[k];
            for (int i = 0; i < np; i++)
            {
                for (int j = 0; j < k; j++) { var c = all[j][i]; tr[j] = c.r; tg[j] = c.g; tb[j] = c.b; ts[j] = c.r + c.g + c.b; }
                Array.Sort(tr); Array.Sort(tg); Array.Sort(tb); Array.Sort(ts);
                med[i] = Px.C((byte)tr[k / 2], (byte)tg[k / 2], (byte)tb[k / 2], 255);
                low[i] = ts[1];                                                  // el segundo mas oscuro (suma)
            }
            // degradado: media de las 6 primeras columnas de cada fila
            var gr = new int[h * 3];
            for (int y = 0; y < h; y++)
            {
                int r = 0, g = 0, b = 0, c6 = Math.Min(6, w);
                for (int x = 0; x < c6; x++) { var c = med[y * w + x]; r += c.r; g += c.g; b += c.b; }
                gr[y * 3] = r / c6; gr[y * 3 + 1] = g / c6; gr[y * 3 + 2] = b / c6;
            }
            int xr = (int)(w * 0.5f);
            // color del dibujo: mediana de lo que se ve claro en casi todas
            var strict = new bool[np];
            var hr = new int[256]; var hg = new int[256]; var hb = new int[256]; int ns = 0;
            for (int y = 0; y < h; y++)
                for (int x = xr + 1; x < w; x++)
                {
                    int i = y * w + x;
                    if (low[i] > gr[y * 3] + gr[y * 3 + 1] + gr[y * 3 + 2] + 75) { strict[i] = true; hr[med[i].r]++; hg[med[i].g]++; hb[med[i].b]++; ns++; }
                }
            int Mid(int[] hist) { int acc = 0; for (int v = 0; v < 256; v++) { acc += hist[v]; if (acc * 2 >= ns) return v; } return 128; }
            int er = Mid(hr), eg = Mid(hg), eb = Mid(hb);
            var nEc = new byte[np]; var nGr = new byte[np];
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    int i = y * w + x, a = 0, b = 0;
                    for (int j = 0; j < k; j++)
                    {
                        var c = all[j][i];
                        if (Math.Abs(c.r - er) + Math.Abs(c.g - eg) + Math.Abs(c.b - eb) < 45) a++;
                        if (Math.Abs(c.r - gr[y * 3]) + Math.Abs(c.g - gr[y * 3 + 1]) + Math.Abs(c.b - gr[y * 3 + 2]) < 45) b++;
                    }
                    nEc[i] = (byte)a; nGr[i] = (byte)b;
                }
            // trozos del dibujo (vecinos de 4) que tienen al menos 300 pixeles claros en casi todas
            var keep = new bool[np]; var seen = new bool[np]; var q = new Queue<int>(); var comp = new List<int>();
            for (int s0 = 0; s0 < np; s0++)
            {
                int x0 = s0 % w;
                if (seen[s0] || x0 <= xr || !(nEc[s0] >= 2 && nEc[s0] >= nGr[s0])) continue;
                comp.Clear(); q.Enqueue(s0); seen[s0] = true; int sc = 0;
                while (q.Count > 0)
                {
                    int i = q.Dequeue(); comp.Add(i); if (strict[i]) sc++;
                    int x = i % w, y = i / w;
                    void Try(int xx, int yy)
                    {
                        if (xx <= xr || xx >= w || yy < 0 || yy >= h) return;
                        int jj = yy * w + xx;
                        if (seen[jj] || !(nEc[jj] >= 2 && nEc[jj] >= nGr[jj])) return;
                        seen[jj] = true; q.Enqueue(jj);
                    }
                    Try(x + 1, y); Try(x - 1, y); Try(x, y + 1); Try(x, y - 1);
                }
                if (sc >= 300) foreach (var i in comp) keep[i] = true;
            }
            var pts = new List<int>();
            for (int i = 0; i < np; i++) if (keep[i]) pts.Add(i);
            var fill = (bool[])keep.Clone();
            if (pts.Count > 0)
            {
                int Best(bool horiz)
                {
                    int bestA = 0; double bestS = -1;
                    int lo = horiz ? w : 0, hi = horiz ? 2 * w : 2 * h;
                    for (int a2 = lo; a2 < hi; a2 += 2)
                    {
                        int m = 0;
                        foreach (var i in pts)
                        {
                            int x = i % w, y = i / w, xx = horiz ? a2 - x : x, yy = horiz ? y : a2 - y;
                            if (xx >= 0 && xx < w && yy >= 0 && yy < h && keep[yy * w + xx]) m++;
                        }
                        if (m > bestS) { bestS = m; bestA = a2; }
                    }
                    return bestA;
                }
                int ax2 = Best(true), ay2 = vertical ? Best(false) : 0;
                foreach (var i in pts)
                {
                    int x = i % w, y = i / w;
                    void Mark(int xx, int yy)
                    {
                        if (xx < 0 || xx >= w || yy < 0 || yy >= h) return;
                        int jj = yy * w + xx;
                        if (nEc[jj] >= 1 && nGr[jj] <= 2) fill[jj] = true;
                    }
                    Mark(ax2 - x, y);
                    if (vertical) { Mark(x, ay2 - y); Mark(ax2 - x, ay2 - y); }
                }
            }
            var bg = new Color32[np];
            var ec = Px.C((byte)er, (byte)eg, (byte)eb, 255);
            for (int y = 0; y < h; y++)
            {
                var g = Px.C((byte)gr[y * 3], (byte)gr[y * 3 + 1], (byte)gr[y * 3 + 2], 255);
                for (int x = 0; x < w; x++) bg[y * w + x] = fill[y * w + x] ? ec : g;
            }
            return bg;
        }

        // la figura de una imagen: lo que no es transparente, y donde esta la cabeza (centro de lo de arriba)
        static readonly Dictionary<IntPtr, (int x0, int y0, int x1, int y1, float hx)> _figures = new();
        static (int x0, int y0, int x1, int y1, float hx) Figure(Texture2D img, Color32[] src)
        {
            if (_figures.TryGetValue(img.Pointer, out var have)) return have;
            int sw = img.width, sh = img.height, x0 = sw, y0 = sh, x1 = -1, y1 = -1;
            for (int y = 0; y < sh; y++)
                for (int x = 0; x < sw; x++)
                    if (src[y * sw + x].a > 16) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
            if (x1 < 0) { x0 = 0; y0 = 0; x1 = sw - 1; y1 = sh - 1; }
            int band = Math.Max(1, (int)((y1 - y0 + 1) * 0.12f));
            double sx = 0; long n = 0;
            for (int y = y1; y > y1 - band && y >= 0; y--)                  // filas de arriba (las texturas van de abajo arriba)
                for (int x = x0; x <= x1; x++)
                    if (src[y * sw + x].a > 128) { sx += x; n++; }
            var f = (x0, y0, x1, y1, n > 0 ? (float)(sx / n) : (x0 + x1) / 2f);
            _figures[img.Pointer] = f;
            return f;
        }

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
                // se encuadra la figura (sin lo transparente de alrededor) desde arriba, centrada en la cabeza: asi la
                // cara siempre se ve; en los retratos cuadrados o apaisados, de la cabeza a medio cuerpo
                src = Pixels(img); sw = img.width; sh = img.height;
                var fg0 = Figure(img, src);
                float A = (float)w / h, bw = fg0.x1 - fg0.x0 + 1, bh = fg0.y1 - fg0.y0 + 1;
                float winW = bw, winH = bw / A;
                if (winH > bh) { winH = bh; winW = winH * A; }
                if (A >= 0.6f && bh > bw * 1.15f && winH > bh * 0.62f) { winH = bh * 0.62f; winW = winH * A; }
                float top = fg0.y1 + 1 + winH * 0.12f;                        // aire por encima de la cabeza
                y0 = top - winH;
                x0 = fg0.hx - winW / 2f;
                scale = w / winW;
            }
            var sil = img == null ? Pixels(RosterUi.Silhouette()) : null;
            bool cutout = false;                                          // el retrato es la figura recortada de un personaje
            if (img == null)
            {
                int opaque = 0;
                for (int i = 0; i < mask.Length; i += 3) if (mask[i].a > 128) opaque++;
                cutout = opaque < mask.Length / 3 * 0.72f;
            }
            int sn = 128;
            float sSize = h * 0.86f, sLeft = (w - sSize) / 2f;
            var bg = Px.C(34, 36, 46, 255);
            var fg = Px.C(122, 128, 150, 255);
            var under = img != null ? UnderFor(orig, w, h) : null;           // resultados: el fondo de asesino / objetivo
            var dst = new Color32[w * h];
            for (int y = 0; y < h; y++)
            {
                float sy = y0 + (y + 0.5f) / scale - 0.5f;
                for (int x = 0; x < w; x++)
                {
                    byte m = mask[y * w + x].a;
                    if (m == 0) { dst[y * w + x] = Px.C(0, 0, 0, 0); continue; }
                    Color32 c;
                    if (src != null)
                    {
                        float sx = x0 + (x + 0.5f) / scale - 0.5f;
                        c = sx < -0.5f || sx > sw - 0.5f || sy < -0.5f || sy > sh - 0.5f ? Px.C(0, 0, 0, 0) : Bilinear(src, sw, sh, sx, sy);
                    }
                    else if (cutout) c = bg;                                  // la silueta de un personaje, en oscuro
                    else
                    {
                        float u = (x - sLeft) / sSize * sn, v = y / sSize * sn;
                        float a = u >= 0 && v >= 0 && u < sn && v < sn ? Bilinear(sil, sn, sn, u, v).a / 255f : 0f;
                        c = Px.C((byte)(bg.r + (fg.r - bg.r) * a), (byte)(bg.g + (fg.g - bg.g) * a), (byte)(bg.b + (fg.b - bg.b) * a), 255);
                    }
                    if (under != null)
                    {
                        var u = under[y * w + x];
                        float ia = c.a / 255f;
                        c = Px.C((byte)(c.r * ia + u.r * (1 - ia)), (byte)(c.g * ia + u.g * (1 - ia)), (byte)(c.b * ia + u.b * (1 - ia)), 255);
                    }
                    if (tint == 1) c = Px.C(c.r, (byte)(c.g * 0.55f), (byte)(c.b * 0.55f), c.a);
                    else if (tint == 2) { byte g = (byte)((c.r * 0.3f + c.g * 0.59f + c.b * 0.11f) * 0.6f); c = Px.C(g, g, g, c.a); }
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
            if (x < 0) x = 0; else if (x > w - 1) x = w - 1;
            if (y < 0) y = 0; else if (y > h - 1) y = h - 1;
            int x0 = (int)x, y0 = (int)y, x1 = x0 + 1 < w ? x0 + 1 : x0, y1 = y0 + 1 < h ? y0 + 1 : y0;
            float fx = x - x0, fy = y - y0;
            float w00 = (1 - fx) * (1 - fy), w10 = fx * (1 - fy), w01 = (1 - fx) * fy, w11 = fx * fy;
            Color32 a = px[y0 * w + x0], b = px[y0 * w + x1], c = px[y1 * w + x0], d = px[y1 * w + x1];
            return Px.C((byte)(a.r * w00 + b.r * w10 + c.r * w01 + d.r * w11 + 0.5f), (byte)(a.g * w00 + b.g * w10 + c.g * w01 + d.g * w11 + 0.5f),
                        (byte)(a.b * w00 + b.b * w10 + c.b * w01 + d.b * w11 + 0.5f), (byte)(a.a * w00 + b.a * w10 + c.a * w01 + d.a * w11 + 0.5f));
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
                        outp[y * w + x] = Px.C(v, v, v, a);
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
            // el fondo de las fotos de resultados, ya en la sala (asi no cuesta nada al empezar la partida)
            foreach (var f in new[] { "resultKillerSprite", "resultTargetSprite" })
            {
                if (File.Exists(Path.Combine(dir, "bg_" + f + ".png"))) continue;
                foreach (var kv in FindPawnData())
                {
                    var sp = GetSp(kv.Value, f);
                    if (sp == null || !(sp.name ?? "").StartsWith("Result_SS")) continue;
                    UnderFor(sp, (int)sp.textureRect.width, (int)sp.textureRect.height);
                    break;
                }
                break;                                                           // uno cada vez
            }
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
