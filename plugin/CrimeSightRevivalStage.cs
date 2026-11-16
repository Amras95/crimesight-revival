// CRIMESIGHT Revival - escenarios del creador de escenarios (plugin de BepInEx, opcional).
//
// Anade a la lista de escenarios del juego:
//   - un escenario por cada distribucion guardada en el creador (Stage_CSR_<id>, con el nombre que le
//     puso el jugador; BepInEx\csr_live\stages.json dice cuales hay y en que archivo esta cada una);
//   - "Escenario de pruebas (CSR)" (Stage_Yokn_CSRTest), para probar sin guardar (layout_test.json).
// Los escenarios del juego no se tocan nunca: los cambios solo se aplican al jugar uno de los
// nuestros. Necesita el plugin en todos los jugadores de la sala.
//
// Al jugar uno se carga un escenario del juego (el "base") y se recolocan sus piezas segun el
// archivo de la distribucion (lo escribe el lanzador desde el creador de escenarios):
//   - habitaciones: se mueven y giran (con todo lo que llevan dentro); las que sobran se esconden y
//     las que se repiten se duplican;
//   - puertas, muebles que tapan huecos, ventanas y puerta principal: igual, pieza a pieza;
//   - puntos de lobos, gas y pasadizos, y casillas de salida de los personajes;
//   - la navegacion (NavMesh) se reconstruye con las mallas NAV_* del propio juego.
// El lanzador decide donde va cada pieza (launcher/stagelayout.py); aqui solo se aplica.
// El titulo que sale al empezar la partida es el nombre de la distribucion.
// Sin archivo, el de pruebas es una copia exacta del escenario 01.
//
// navsrc.json (lo genera el lanzador desde la copia del juego del usuario): las mallas NAV_* en
// version legible, porque las del juego no se pueden leer desde codigo.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Text.Json.Serialization;
using HarmonyLib;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.SceneManagement;

namespace CrimeSightRevival.Mods
{
    // de donde sale una pieza del escenario base (nombre, posicion y giro originales) y donde va
    public class LPose
    {
        public string name { get; set; }
        public float sx { get; set; }
        public float sz { get; set; }
        public float syaw { get; set; }
        public float x { get; set; }
        public float z { get; set; }
        public float yaw { get; set; }
        public float w { get; set; }
        public float d { get; set; }
    }
    public class LByway { public float x { get; set; } public float z { get; set; } public float yaw { get; set; } public int[] shelves { get; set; } }
    public class LWolf { public float x { get; set; } public float z { get; set; } public float yaw { get; set; } public int window { get; set; } }
    public class LPoint { public float x { get; set; } public float z { get; set; } }
    public class StageLayout
    {
        public int format { get; set; }
        public string name { get; set; }
        [JsonPropertyName("base")] public string baseStage { get; set; }
        public string navmesh { get; set; } = "rebuild";
        public LPose[] rooms { get; set; }
        public LPose[] hide_rooms { get; set; }
        public LPose[] pieces { get; set; }
        public LPose[] hide { get; set; }
        public LByway[] byways { get; set; }
        public LWolf[] wolves { get; set; }
        public LPoint[] gas { get; set; }
        public int[] spawns { get; set; }
        public float[] bounds { get; set; }
    }

    // escenarios guardados en el creador: cada uno sale en la lista del juego como un escenario mas
    public class StageEntry { public string id { get; set; } public string name { get; set; } public string file { get; set; } }
    public class StageIndex { public StageEntry[] stages { get; set; } }

    public class NavSrcMesh { public float[] v { get; set; } public int[] t { get; set; } }
    public class NavSrcFile { public Dictionary<string, NavSrcMesh> meshes { get; set; } }

    public static class StageLab
    {
        public const string TEST_STAGE = "Stage_Yokn_CSRTest";
        const string CUSTOM_PREFIX = "Stage_CSR_";          // escenarios guardados: Stage_CSR_<id>
        const string TITLE_KEY = "csr_stage_title";         // texto del titulo que sale al empezar la partida
        static string _title = "";
        static StageEntry[] _index = Array.Empty<StageEntry>();
        static DateTime _indexSeen = DateTime.MinValue;
        static string IndexFile => Path.Combine(LiveMods.LiveDir, "stages.json");
        const string DEFAULT_BASE = "Stage_Yokn";
        static readonly string[] BASES = { "Stage_Yokn", "Stage_Yokn_v1030", "Stage_Yokn_v1040", "Stage_Yokn_v1050", "Stage_Yokn_v1060" };

        static bool _armed;                     // se va a jugar (o se esta jugando) el escenario de pruebas
        static StageLayout _cfg;                // distribucion a aplicar (null: copia exacta del base)
        static string _base = DEFAULT_BASE;
        static int _doneHandle = int.MinValue;  // escena ya recolocada
        static Scene _scene;
        static Transform _root;
        static bool _started, _ready, _pending;
        static int _frames, _skipped;
        static GameObject[] _placed = Array.Empty<GameObject>();     // pieza i de la distribucion -> objeto
        static readonly List<(int k, GameObject src, Vector3 pos, Quaternion rot)> _jobs = new();
        static readonly Dictionary<string, Mesh> _readable = new();

        static string TestFile => Path.Combine(LiveMods.LiveDir, "layout_test.json");
        static string NavFile => Path.Combine(LiveMods.LiveDir, "navsrc.json");
        static void Log(string s) => Plugin.L.LogInfo("[Escenario] " + s);
        static void Warn(string s) => Plugin.L.LogWarning("[Escenario] " + s);

        public static void Init(Harmony h)
        {
            var me = typeof(StageLab);
            HarmonyMethod M(string n) => new HarmonyMethod(me.GetMethod(n, BindingFlags.Static | BindingFlags.NonPublic));
            void Patch(Type t, string method, string prefix)
            {
                try
                {
                    var m = AccessTools.DeclaredMethod(t, method);
                    if (m == null) { Log($"{t.Name}.{method}: no existe"); return; }
                    h.Patch(m, prefix: M(prefix));
                }
                catch (Exception e) { Warn($"{t.Name}.{method}: {e.Message}"); }
            }
            Patch(typeof(OutGameRoomPopupRoomSetting), "CreateStageList", nameof(BeforeStageList));
            Patch(typeof(MatchSettings), "LoadStageData", nameof(MapStage));
            Patch(typeof(OutGameManager), "StartInGame", nameof(MapStage));
            Patch(typeof(GameManager), "LoadStage", nameof(BeforeLoadStage));
            foreach (var t in new[] { typeof(Stage), typeof(Area), typeof(Room), typeof(Door), typeof(OutDoor), typeof(Shelf), typeof(WindowShelf) })
                Patch(t, "Awake", nameof(BeforeAwake));
            Patch(typeof(Stage), "Start", nameof(BeforeStageStart));
            Log("escenario de pruebas disponible: " + TEST_STAGE);
        }

        // ---------------------------------------------------------------- escenario de pruebas
        static readonly string[] TestName =
        {   // ja, en, fr, it, de, es, pt, ru, ko, zh-CN, zh-TW (orden de TextManager)
            "テスト用ステージ (CSR)", "Test stage (CSR)", "Scénario de test (CSR)", "Scenario di prova (CSR)",
            "Testszenario (CSR)", "Escenario de pruebas (CSR)", "Cenário de testes (CSR)", "Тестовый сценарий (CSR)",
            "테스트 스테이지 (CSR)", "测试场景 (CSR)", "測試場景 (CSR)",
        };

        static string TestLabel()
        {
            var tm = TextManager.Instance;
            int lang = tm != null ? (int)tm.GetLangType() : 1;
            return lang >= 0 && lang < TestName.Length ? TestName[lang] : TestName[1];
        }

        static StageEntry[] Index()
        {
            try
            {
                var t = File.Exists(IndexFile) ? File.GetLastWriteTimeUtc(IndexFile) : DateTime.MinValue;
                if (t == _indexSeen) return _index;
                _indexSeen = t;
                var list = new List<StageEntry>();
                if (t != DateTime.MinValue)
                    foreach (var e in JsonSerializer.Deserialize<StageIndex>(File.ReadAllText(IndexFile))?.stages ?? Array.Empty<StageEntry>())
                        if (e?.id != null && e.id.StartsWith(CUSTOM_PREFIX) && !string.IsNullOrEmpty(e.file)) list.Add(e);
                _index = list.ToArray();
                Log($"escenarios guardados: {_index.Length}");
            }
            catch (Exception e) { Warn("stages.json no valido: " + e.Message); _index = Array.Empty<StageEntry>(); }
            return _index;
        }

        public static void EnsureTexts()
        {
            var tm = TextManager.Instance;
            if (tm == null || tm.LangText == null) return;
            void Put(string key, string text)
            {
                if (!tm.LangText.ContainsKey(key) || tm.LangText[key] != text) tm.LangText[key] = text;
            }
            Put("ctg_name_stageName_" + TEST_STAGE, TestLabel());
            foreach (var e in Index()) Put("ctg_name_stageName_" + e.id, string.IsNullOrEmpty(e.name) ? e.id : e.name);
            if (!string.IsNullOrEmpty(_title)) Put(TITLE_KEY, _title);
        }

        // la lista de la ventana de ajustes de la sala: los escenarios guardados y el de pruebas, antes de "Aleatorio"
        static void BeforeStageList(OutGameRoomPopupRoomSetting __instance)
        {
            try
            {
                EnsureTexts();
                var list = __instance.UseStageList;
                if (list == null) return;
                for (int i = list.Count - 1; i >= 0; i--)
                {
                    var n = list[i]?.StageName;
                    if (n != null && (n == TEST_STAGE || n.StartsWith(CUSTOM_PREFIX))) list.RemoveAt(i);
                }
                int random = list.Count;
                for (int i = 0; i < list.Count; i++)
                    if (list[i]?.StageName == "Random") { random = i; break; }
                foreach (var e in Index())
                    list.Insert(random++, new OutGameRoomPopupRoomSetting.StageData { StageName = e.id });
                list.Insert(random, new OutGameRoomPopupRoomSetting.StageData { StageName = TEST_STAGE });
            }
            catch (Exception e) { Plugin.L.LogError(e); }
        }

        // el juego pide cargar uno de los nuestros: se carga su escenario base y se prepara la distribucion
        static bool Ours(string stageName, out string file, out string title)
        {
            file = null; title = null;
            if (stageName == TEST_STAGE) { file = TestFile; title = TestLabel(); return true; }
            if (stageName == null || !stageName.StartsWith(CUSTOM_PREFIX)) return false;
            title = stageName;
            foreach (var e in Index())
                if (e.id == stageName) { file = Path.Combine(LiveMods.LiveDir, Path.GetFileName(e.file)); title = string.IsNullOrEmpty(e.name) ? e.id : e.name; }
            return true;
        }

        static void MapStage(ref string stageName)
        {
            if (Ours(stageName, out var file, out var title))
            {
                Arm(file, title);
                stageName = _base;
            }
            else if (!string.IsNullOrEmpty(stageName) && stageName.StartsWith("Stage_"))
            {
                if (_armed) Log("escenario normal: sin cambios");
                _armed = false;
            }
        }

        static void BeforeLoadStage(GameManager __instance)
        {
            try
            {
                if (Ours(__instance.currentStageName, out var file, out var title))
                {
                    Arm(file, title);
                    __instance.currentStageName = _base;
                }
            }
            catch (Exception e) { Plugin.L.LogError(e); }
        }

        static void Arm(string file, string title)
        {
            _armed = true; _cfg = null; _base = DEFAULT_BASE; _title = title ?? "";
            if (file != null && File.Exists(file))
            {
                try
                {
                    var c = JsonSerializer.Deserialize<StageLayout>(File.ReadAllText(file));
                    if (c != null && c.format == 2 && c.rooms != null && c.rooms.Length > 0 && Array.IndexOf(BASES, c.baseStage) >= 0)
                    {
                        _cfg = c; _base = c.baseStage;
                        if (!string.IsNullOrWhiteSpace(c.name)) _title = c.name;
                    }
                    else Warn(Path.GetFileName(file) + " no es una distribucion del creador de escenarios: se ignora");
                }
                catch (Exception e) { Warn(Path.GetFileName(file) + " no valido: " + e.Message); }
            }
            else if (file != TestFile) Warn("no encuentro la distribucion de ese escenario: se carga el 01 tal cual");
            Log(_cfg == null ? $"'{_title}': copia exacta de {_base}"
                : $"'{_title}' sobre {_base} ({_cfg.rooms.Length} habitaciones, {(_cfg.pieces ?? Array.Empty<LPose>()).Length} piezas)");
        }

        // ---------------------------------------------------------------- recolocar antes de Awake
        // Se engancha el Awake de las piezas del escenario: en el primero (antes de que el juego calcule
        // nada) se recoloca todo. Devuelve false para las piezas escondidas: no deben inicializarse.
        static bool BeforeAwake(Component __instance)
        {
            if (!_armed) return true;
            try
            {
                var go = __instance.gameObject;
                var sc = go.scene;
                if (sc.name != _base) return true;
                if (sc.handle != _doneHandle)
                {
                    _doneHandle = sc.handle;
                    _root = __instance.transform.root; _scene = sc;
                    _started = _ready = false; _pending = _cfg != null; _frames = 0; _skipped = 0;
                    _jobs.Clear(); _placed = Array.Empty<GameObject>();
                    try
                    {   // el titulo que sale al empezar ("Caso: ...") es el texto con esta clave
                        var st = _root.GetComponentInChildren<Stage>(true);
                        if (st != null && !string.IsNullOrEmpty(_title)) { EnsureTexts(); st.stageNamelangId = TITLE_KEY; }
                    }
                    catch (Exception e) { Warn("titulo: " + e.Message); }
                    if (_cfg != null) Apply(_root, _cfg);
                }
                if (_cfg != null && !go.activeInHierarchy) { _skipped++; return false; }
            }
            catch (Exception e) { Plugin.L.LogError(e); }
            return true;
        }

        class Src { public Transform t; public Vector3 pos; public Quaternion rot; public float yaw; }

        static void Apply(Transform root, StageLayout cfg)
        {
            var sw = Stopwatch.StartNew();
            // foto de la escena original: las piezas se buscan por su nombre, posicion y giro de origen
            var byName = new Dictionary<string, List<Src>>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                if (!byName.TryGetValue(t.name, out var l)) byName[t.name] = l = new List<Src>();
                l.Add(new Src { t = t, pos = t.position, rot = t.rotation, yaw = t.eulerAngles.y });
            }
            Src Find(LPose p)
            {
                if (p?.name == null || !byName.TryGetValue(p.name, out var l)) return null;
                Src best = null; float bd = 0.36f;
                foreach (var s in l)
                {
                    if (Mathf.Abs(Mathf.DeltaAngle(s.yaw, p.syaw)) > 3f) continue;
                    float dx = s.pos.x - p.sx, dz = s.pos.z - p.sz, d = dx * dx + dz * dz;
                    if (d < bd) { bd = d; best = s; }
                }
                return best;
            }
            static Quaternion Rot(Src s, LPose p) => Quaternion.Euler(0, p.yaw - p.syaw, 0) * s.rot;
            static Vector3 Pos(Src s, LPose p) => new Vector3(p.x, s.pos.y, p.z);

            int moved = 0, cloned = 0, hidden = 0, missing = 0;
            var used = new HashSet<int>();
            // habitaciones (las repetidas se duplican ya: su Awake no depende de nada mas)
            foreach (var r in cfg.rooms)
            {
                var s = Find(r);
                if (s == null) { missing++; Warn($"no encuentro la habitacion '{r.name}' en ({r.sx},{r.sz})"); continue; }
                if (used.Add(s.t.GetInstanceID())) { s.t.position = Pos(s, r); s.t.rotation = Rot(s, r); moved++; }
                else
                {
                    var c = UnityEngine.Object.Instantiate((UnityEngine.Object)s.t.gameObject, Pos(s, r), Rot(s, r), s.t.parent).Cast<GameObject>();
                    c.name = s.t.name + " (csr)";
                    cloned++;
                }
            }
            foreach (var r in cfg.hide_rooms ?? Array.Empty<LPose>())
            {
                var s = Find(r);
                if (s == null) { missing++; continue; }
                s.t.gameObject.SetActive(false); hidden++;
            }
            Physics.SyncTransforms();
            Log($"habitaciones: {moved} colocadas, {cloned} duplicadas, {hidden} escondidas" + (missing > 0 ? $", {missing} NO ENCONTRADAS" : ""));

            // piezas de los huecos. Las repetidas se duplican mas tarde (Stage.Start), con todo ya inicializado.
            var pieces = cfg.pieces ?? Array.Empty<LPose>();
            _placed = new GameObject[pieces.Length];
            moved = hidden = missing = 0;
            for (int k = 0; k < pieces.Length; k++)
            {
                var p = pieces[k];
                var s = Find(p);
                if (s == null) { missing++; Warn($"no encuentro la pieza '{p.name}' en ({p.sx},{p.sz})"); continue; }
                if (used.Add(s.t.GetInstanceID())) { s.t.position = Pos(s, p); s.t.rotation = Rot(s, p); _placed[k] = s.t.gameObject; moved++; }
                else _jobs.Add((k, s.t.gameObject, Pos(s, p), Rot(s, p)));
            }
            foreach (var p in cfg.hide ?? Array.Empty<LPose>())
            {
                var s = Find(p);
                if (s == null) { missing++; continue; }
                s.t.gameObject.SetActive(false); hidden++;
            }
            Physics.SyncTransforms();
            Log($"piezas: {moved} colocadas, {_jobs.Count} por duplicar, {hidden} escondidas" + (missing > 0 ? $", {missing} NO ENCONTRADAS" : ""));

            try
            {
                var stage = root.GetComponentInChildren<Stage>(true);
                if (stage != null && cfg.spawns != null && cfg.spawns.Length > 0)
                {
                    stage.pawnSpawnGridIds = new Il2CppStructArray<int>(cfg.spawns);
                    Log("salidas: " + string.Join(", ", cfg.spawns));
                }
            }
            catch (Exception e) { Warn("salidas: " + e.Message); }
            try { FitExtras(root, cfg); } catch (Exception e) { Warn("camara/paneles: " + e.Message); }
            Log($"distribucion aplicada en {sw.ElapsedMilliseconds} ms");
        }

        // limites de la camara y paneles del suelo digital, al tamano de la nueva casa
        static void FitExtras(Transform root, StageLayout cfg)
        {
            if (cfg.bounds == null || cfg.bounds.Length != 4) return;
            float x0 = cfg.bounds[0], z0 = cfg.bounds[1], x1 = cfg.bounds[2], z1 = cfg.bounds[3];
            float cx = (x0 + x1) / 2, cz = (z0 + z1) / 2, w = x1 - x0, d = z1 - z0;
            var cam = root.Find("CameraRange");
            if (cam != null)
            {
                cam.position = new Vector3(cx, cam.position.y, cz + 1f);
                cam.localScale = new Vector3((w + 12f) / 10f, cam.localScale.y, (d + 14f) / 10f);
            }
            var panels = root.Find("Digital_Panel");
            if (panels == null || panels.childCount == 0) return;
            var list = new List<Transform>();
            for (int i = 0; i < panels.childCount; i++) list.Add(panels.GetChild(i));
            var tpl = list[0];
            float y = tpl.position.y, sy = tpl.localScale.y;
            for (int i = 0; i < cfg.rooms.Length; i++)
            {
                var r = cfg.rooms[i];
                if (r.w <= 0 || r.d <= 0) continue;
                Transform p = i < list.Count ? list[i]
                    : UnityEngine.Object.Instantiate((UnityEngine.Object)tpl.gameObject, panels, false).Cast<GameObject>().transform;
                p.position = new Vector3(r.x, y, r.z);
                p.rotation = Quaternion.identity;
                p.localScale = new Vector3((r.w + 1.4f) / 10f, sy, (r.d + 1.4f) / 10f);
            }
            for (int i = cfg.rooms.Length; i < list.Count; i++) list[i].gameObject.SetActive(false);
        }

        // ---------------------------------------------------------------- duplicados y puntos de interes
        // Stage.Start: todas las piezas del escenario ya estan inicializadas (y el juego aun no ha
        // hecho sus listas de habitaciones, puertas y muebles).
        static void BeforeStageStart(Stage __instance)
        {
            if (!_armed || _cfg == null || _started) return;
            try
            {
                if (__instance.gameObject.scene.handle != _doneHandle) return;
                _started = true;
                Physics.SyncTransforms();
                int n = 0;
                foreach (var j in _jobs)
                {
                    try
                    {
                        var c = UnityEngine.Object.Instantiate((UnityEngine.Object)j.src, j.pos, j.rot, j.src.transform.parent).Cast<GameObject>();
                        c.name = j.src.name + " (csr)";
                        _placed[j.k] = c; n++;
                    }
                    catch (Exception e) { Warn($"no pude duplicar '{j.src.name}': {e.Message}"); }
                }
                _jobs.Clear();
                Physics.SyncTransforms();
                if (n > 0) Log($"piezas duplicadas: {n}");
                if (_skipped > 0) Log($"piezas escondidas sin inicializar: {_skipped}");
                Locators(__instance, _cfg);
                try { FogMask(_root, _cfg); } catch (Exception e) { Warn("niebla: " + e.Message); }
            }
            catch (Exception e) { Plugin.L.LogError(e); }
            finally { _ready = true; }
        }

        // La niebla que rodea la casa (GB_Plane_Top / _Under) lleva una textura con el hueco de la casa
        // original. Se pinta una nueva con el hueco de la distribucion: R = disco suave general,
        // G = 0 dentro de la casa, B = 0 dentro y un halo ancho alrededor (como las del juego).
        static Texture2D _fogTex;
        static float Smooth(float a, float b, float x)
        {
            float t = Mathf.Clamp01((x - a) / (b - a));
            return t * t * (3f - 2f * t);
        }

        static void FogMask(Transform root, StageLayout cfg)
        {
            const int N = 256;
            const float KU = 3.273f, CU = 0.5008f, KV = 3.262f, CV = 0.4976f;     // uv de la malla GB_Normal
            var planes = new List<Transform>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                if (t.name == "GB_Plane_Top" || t.name == "GB_Plane_Under") planes.Add(t);
            if (planes.Count == 0) return;
            var plane = planes[0];
            // huella de la casa: habitaciones y porche de la puerta principal
            var rects = new List<Vector4>();
            foreach (var r in cfg.rooms)
                if (r.w > 0 && r.d > 0) rects.Add(new Vector4(r.x - r.w / 2, r.z - r.d / 2, r.x + r.w / 2, r.z + r.d / 2));
            foreach (var p in cfg.pieces ?? Array.Empty<LPose>())
            {
                if (p.name == null || !p.name.StartsWith("Out_door")) continue;
                var f = Quaternion.Euler(0, p.yaw, 0) * Vector3.forward;           // hacia dentro de la casa
                float cx = p.x - f.x * 1.2f, cz = p.z - f.z * 1.2f;
                bool alongX = Mathf.Abs(f.z) > 0.5f;
                float hx = alongX ? 3f : 1.3f, hz = alongX ? 1.3f : 3f;
                rects.Add(new Vector4(cx - hx, cz - hz, cx + hx, cz + hz));
            }
            var inside = new bool[N * N];
            for (int py = 1; py < N - 1; py++)
                for (int px = 1; px < N - 1; px++)
                {
                    float u = (px + 0.5f) / N, v = (py + 0.5f) / N;
                    var w = plane.TransformPoint(new Vector3((CU - u) / KU, 0, (CV - v) / KV));
                    foreach (var r in rects)
                        if (w.x >= r.x && w.x <= r.z && w.z >= r.y && w.z <= r.w) { inside[py * N + px] = true; break; }
                }
            float upp = (plane.TransformPoint(new Vector3(1f / (KU * N), 0, 0)) - plane.TransformPoint(Vector3.zero)).magnitude;
            // distancia (en pixeles) al borde de la casa, por dentro y por fuera
            float[] Dist(bool target)
            {
                var d = new float[N * N];
                for (int i = 0; i < d.Length; i++) d[i] = inside[i] == target ? 0f : 1e6f;
                for (int y = 0; y < N; y++)
                    for (int x = 0; x < N; x++)
                    {
                        int i = y * N + x; float m = d[i];
                        if (x > 0) m = Mathf.Min(m, d[i - 1] + 1f);
                        if (y > 0) m = Mathf.Min(m, d[i - N] + 1f);
                        if (x > 0 && y > 0) m = Mathf.Min(m, d[i - N - 1] + 1.4142f);
                        if (x < N - 1 && y > 0) m = Mathf.Min(m, d[i - N + 1] + 1.4142f);
                        d[i] = m;
                    }
                for (int y = N - 1; y >= 0; y--)
                    for (int x = N - 1; x >= 0; x--)
                    {
                        int i = y * N + x; float m = d[i];
                        if (x < N - 1) m = Mathf.Min(m, d[i + 1] + 1f);
                        if (y < N - 1) m = Mathf.Min(m, d[i + N] + 1f);
                        if (x < N - 1 && y < N - 1) m = Mathf.Min(m, d[i + N + 1] + 1.4142f);
                        if (x > 0 && y < N - 1) m = Mathf.Min(m, d[i + N - 1] + 1.4142f);
                        d[i] = m;
                    }
                return d;
            }
            var toHouse = Dist(true);      // 0 dentro; fuera, lo que falta para llegar a la casa
            var toOut = Dist(false);       // 0 fuera; dentro, lo que falta para salir
            var data = new byte[N * N * 4];
            for (int py = 0; py < N; py++)
                for (int px = 0; px < N; px++)
                {
                    int i = py * N + px;
                    float sd = (toHouse[i] - toOut[i]) * upp;                       // unidades; negativo dentro
                    float u = (px + 0.5f) / N - 0.5f, v = (py + 0.5f) / N - 0.5f;
                    data[i * 4] = (byte)(251f * (1f - Smooth(0.283f, 0.459f, Mathf.Sqrt(u * u + v * v))));
                    data[i * 4 + 1] = (byte)(255f * Smooth(-2.5f, 1.5f, sd));
                    data[i * 4 + 2] = (byte)(255f * Smooth(-3f, 9f, sd));
                    data[i * 4 + 3] = 255;
                }
            if (_fogTex != null) UnityEngine.Object.Destroy(_fogTex);
            _fogTex = new Texture2D(N, N, TextureFormat.RGBA32, false, true) { name = "csr_fog_mask" };
            _fogTex.wrapMode = TextureWrapMode.Clamp;
            _fogTex.filterMode = FilterMode.Bilinear;
            _fogTex.LoadRawTextureData(new Il2CppStructArray<byte>(data));
            _fogTex.Apply(false, false);
            int n = 0;
            foreach (var t in planes)
            {
                var r = t.GetComponent<Renderer>();
                if (r == null) continue;
                r.material.SetTexture("_Main_Texture", _fogTex);
                n++;
            }
            Log($"niebla: hueco de la casa repintado en {n} capas");
        }

        static GameObject Placed(int k) => k >= 0 && k < _placed.Length ? _placed[k] : null;

        static Transform Locator(Transform reuse, Transform like, string name, float x, float z, float yaw)
        {
            var t = reuse;
            if (t == null)
            {
                var go = new GameObject(name);
                t = go.transform;
                t.SetParent(like.parent, false);
            }
            t.position = new Vector3(x, like.position.y, z);
            t.rotation = Quaternion.Euler(0, yaw, 0);
            return t;
        }

        static void Locators(Stage stage, StageLayout cfg)
        {
            var t0 = stage.threatLocateDatas;
            if (cfg.wolves != null && t0 != null && t0.Length > 0)
            {
                var arr = new Il2CppReferenceArray<ThreatLocateData>(cfg.wolves.Length);
                int bad = 0;
                for (int i = 0; i < cfg.wolves.Length; i++)
                {
                    var w = cfg.wolves[i];
                    var d = new ThreatLocateData();
                    d.locator = Locator(i < t0.Length ? t0[i].locator : null, t0[0].locator, "CSR_WolfLocator", w.x, w.z, w.yaw);
                    var win = Placed(w.window);
                    d.entryWindowShelf = win != null ? win.GetComponent<WindowShelf>() : null;
                    if (d.entryWindowShelf == null) bad++;
                    d.threatTypeData = t0[0].threatTypeData;
                    arr[i] = d;
                }
                stage.threatLocateDatas = arr;
                Log($"lobos: {arr.Length} entradas" + (bad > 0 ? $" ({bad} SIN VENTANA)" : ""));
            }
            var g0 = stage.gaspipeLocateDatas;
            if (cfg.gas != null && g0 != null && g0.Length > 0)
            {
                var arr = new Il2CppReferenceArray<GaspipeLocateData>(cfg.gas.Length);
                for (int i = 0; i < cfg.gas.Length; i++)
                {
                    var d = new GaspipeLocateData();
                    d.locator = Locator(i < g0.Length ? g0[i].locator : null, g0[0].locator, "CSR_GaspipeLocator", cfg.gas[i].x, cfg.gas[i].z, 0);
                    d.gimmickTypeData = g0[0].gimmickTypeData;
                    arr[i] = d;
                }
                stage.gaspipeLocateDatas = arr;
                Log($"gas: {arr.Length} puntos");
            }
            var b0 = stage.bywayLocateDatas;
            if (cfg.byways != null && b0 != null && b0.Length > 0)
            {
                var arr = new Il2CppReferenceArray<BywayLocateData>(cfg.byways.Length);
                int bad = 0;
                for (int i = 0; i < cfg.byways.Length; i++)
                {
                    var b = cfg.byways[i];
                    var d = new BywayLocateData();
                    d.locator = Locator(i < b0.Length ? b0[i].locator : null, b0[0].locator, "CSR_BywayLocator", b.x, b.z, b.yaw);
                    var shelves = new List<Shelf>();
                    foreach (var k in b.shelves ?? Array.Empty<int>())
                    {
                        var go = Placed(k);
                        var sh = go != null ? go.GetComponent<Shelf>() : null;
                        if (sh != null) shelves.Add(sh);
                    }
                    if (shelves.Count < 2) bad++;
                    d.shelfs = new Il2CppReferenceArray<Shelf>(shelves.ToArray());
                    d.bywayTypeData = b0[0].bywayTypeData;
                    arr[i] = d;
                }
                stage.bywayLocateDatas = arr;
                Log($"pasadizos: {arr.Length}" + (bad > 0 ? $" ({bad} SIN SUS DOS MUEBLES)" : ""));
            }
        }

        // ---------------------------------------------------------------- navegacion, con todo cargado
        public static void Frame()
        {
            if (!_pending || !_armed || _cfg == null) return;
            try
            {
                if (_root == null) { _pending = false; return; }
                if (!_scene.isLoaded) return;
                if (!_ready && ++_frames < 600) return;          // espera a Stage.Start (duplicados)
                _pending = false;
                if (!_ready) Warn("Stage.Start no ha llegado: sigo sin las piezas duplicadas");
                Report();
                if (_cfg.navmesh == "keep") Log("navmesh: sin tocar");
                else if (!NavRebuild()) Warn("no pude reconstruir la navegacion: los personajes pueden no moverse bien");
                Probe();
            }
            catch (Exception e) { Plugin.L.LogError(e); }
        }

        static int PosId(Vector3 p) => GridManager.PositionToId(ref p);

        static void Report()
        {
            int rooms = 0, doors = 0, shelves = 0;
            foreach (var r in _root.GetComponentsInChildren<Room>(false))
            {
                rooms++;
                var p = r.transform.position;
                Log($"  {r.gameObject.name} en ({p.x:0.#},{p.z:0.#}) giro {r.transform.eulerAngles.y:0} casilla {PosId(p)}");
            }
            foreach (var d in _root.GetComponentsInChildren<Door>(false)) doors++;
            foreach (var s in _root.GetComponentsInChildren<Shelf>(false)) shelves++;
            Log($"en escena: {rooms} habitaciones (con las interiores), {doors} puertas, {shelves} muebles y ventanas");
        }

        static bool NavRebuild()
        {
            var sw = Stopwatch.StartNew();
            if (!File.Exists(NavFile)) { Warn("falta navsrc.json"); return false; }
            NavSrcFile src;
            try { src = JsonSerializer.Deserialize<NavSrcFile>(File.ReadAllText(NavFile)); }
            catch (Exception e) { Warn("navsrc.json no valido: " + e.Message); return false; }

            var sources = new List<RawNav.Source>();
            bool any = false; Bounds all = default;
            int floors = 0, blocks = 0, missing = 0;
            foreach (var mf in _root.GetComponentsInChildren<MeshFilter>(true))
            {
                var go = mf.gameObject;
                if (!go.name.StartsWith("NAV_")) continue;
                // los objetos NAV_ estan siempre apagados: cuenta si lo esta la pieza a la que pertenecen
                var owner = mf.transform.parent;
                if (owner == null || !owner.gameObject.activeInHierarchy) continue;
                var orig = mf.sharedMesh;
                if (orig == null) continue;
                var mesh = Readable(orig, src);
                if (mesh == null) { missing++; Warn("sin datos: " + orig.name); continue; }
                // Todo como en la NavMesh original: caminable. Los muebles no generan suelo util (su
                // parte de arriba queda aislada), y los huecos de las paredes los tapan los obstaculos.
                var m = mf.transform.localToWorldMatrix;
                sources.Add(new RawNav.Source { transform = m, shape = 0, area = 0, instanceID = mesh.GetInstanceID() });
                if (go.name.StartsWith("NAV_FLOOR")) floors++; else blocks++;
                var wb = WorldBounds(mesh.bounds, m);
                if (!any) { all = wb; any = true; } else all.Encapsulate(wb);
            }
            // El juego aparca a los personajes en (0,0,0) y (2,0,0) antes de colocarlos (y a los que no
            // juegan, todo el rato). Si ahi no hay casa, Unity se queja sin parar: se deja una isla de
            // suelo invisible (no conecta con la casa si no la toca).
            var park = new Bounds(new Vector3(1f, -0.1f, 0f), new Vector3(8f, 0.2f, 6f));
            sources.Add(new RawNav.Source { transform = Matrix4x4.TRS(park.center, Quaternion.identity, Vector3.one), size = park.size, shape = 2, area = 0 });
            if (!any || floors == 0) { Warn("no hay suelos para la navegacion"); return false; }
            all.Encapsulate(park);
            all.Expand(2f);
            Log($"fuentes: {floors} suelos, {blocks} bloqueos, {missing} sin datos; limites {all.center}/{all.size}");
            var settings = RawNav.Settings.Default();
            IntPtr data = RawNav.Build(settings, sources, all, out bool ok);
            if (!ok || data == IntPtr.Zero) return false;
            RawNav.RemoveAll();
            int h = RawNav.Add(data, Vector3.zero);
            Log($"navmesh: reconstruida en {sw.ElapsedMilliseconds} ms (instancia {h})");
            return h != 0;
        }

        // Las mallas del juego no son legibles: se crea una copia con los datos de navsrc.json.
        static Mesh Readable(Mesh orig, NavSrcFile src)
        {
            if (_readable.TryGetValue(orig.name, out var cached) && cached != null) return cached;
            if (src.meshes == null || !src.meshes.TryGetValue(orig.name, out var d) || d.v == null || d.t == null) return null;
            var verts = new Vector3[d.v.Length / 3];
            for (int i = 0; i < verts.Length; i++) verts[i] = new Vector3(d.v[i * 3], d.v[i * 3 + 1], d.v[i * 3 + 2]);
            // comprobar que coincide con la original (por si los datos vienen con X invertida)
            var ob = orig.bounds;
            var nb = BoundsOf(verts);
            if (Mathf.Abs(nb.center.x + ob.center.x) < Mathf.Abs(nb.center.x - ob.center.x) - 0.01f)
            {
                for (int i = 0; i < verts.Length; i++) verts[i].x = -verts[i].x;
                nb = BoundsOf(verts);
                Log($"{orig.name}: X invertida corregida");
            }
            if ((nb.center - ob.center).magnitude > 0.05f || (nb.size - ob.size).magnitude > 0.05f)
                Warn($"{orig.name}: limites distintos orig={ob.center}/{ob.size} copia={nb.center}/{nb.size}");
            // suelos mirando hacia arriba (la pendiente se calcula con la normal)
            var tris = (int[])d.t.Clone();
            for (int i = 0; i + 2 < tris.Length; i += 3)
            {
                var n = Vector3.Cross(verts[tris[i + 1]] - verts[tris[i]], verts[tris[i + 2]] - verts[tris[i]]);
                if (n.y < -1e-4f) { (tris[i + 1], tris[i + 2]) = (tris[i + 2], tris[i + 1]); }
            }
            var m = new Mesh { name = orig.name + "_csr" };
            if (verts.Length > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            m.vertices = verts;
            m.triangles = tris;
            m.RecalculateBounds();
            UnityEngine.Object.DontDestroyOnLoad(m);
            _readable[orig.name] = m;
            return m;
        }

        static Bounds BoundsOf(Vector3[] v)
        {
            if (v.Length == 0) return default;
            var b = new Bounds(v[0], Vector3.zero);
            foreach (var p in v) b.Encapsulate(p);
            return b;
        }

        static Bounds WorldBounds(Bounds b, Matrix4x4 m)
        {
            var c = b.center; var e = b.extents;
            var wb = new Bounds(m.MultiplyPoint3x4(c), Vector3.zero);
            for (int i = 0; i < 8; i++)
            {
                var p = c + new Vector3((i & 1) == 0 ? -e.x : e.x, (i & 2) == 0 ? -e.y : e.y, (i & 4) == 0 ? -e.z : e.z);
                wb.Encapsulate(m.MultiplyPoint3x4(p));
            }
            return wb;
        }

        // Comprueba que hay suelo navegable en las salidas y en cada habitacion, y que los personajes lo pisan.
        static void Probe()
        {
            var stage = _root.GetComponentInChildren<Stage>(true);
            if (stage != null && stage.pawnSpawnGridIds != null)
            {
                var ids = stage.pawnSpawnGridIds;
                for (int i = 0; i < ids.Length; i++)
                {
                    int id = ids[i];
                    var p = GridManager.IdToPosition(ref id);
                    bool hit = NavMesh.SamplePosition(p, out var h, 2f, -1);
                    if (!hit || h.distance > 0.5f) Warn($"salida {i}: casilla {ids[i]} pos {p} -> {(hit ? $"suelo a {h.distance:0.00}" : "SIN NAVMESH")}");
                }
            }
            int bad = 0;
            foreach (var r in _root.GetComponentsInChildren<Room>(false))
            {
                if (!NavMesh.SamplePosition(r.transform.position, out _, 3f, -1)) { bad++; Warn($"{r.gameObject.name}: SIN NAVMESH"); }
            }
            int off = 0;
            foreach (var a in UnityEngine.Object.FindObjectsOfType<NavMeshAgent>())
                if (a.enabled && !a.Warp(a.transform.position)) off++;
            Log($"navegacion comprobada: {bad} habitaciones sin suelo, {off} personajes fuera");
        }
    }

    // Llamadas internas de Unity para construir la NavMesh. Los tipos de C# que las envuelven (lista de
    // fuentes, NavMeshDataInstance...) no existen en el juego porque Unity los elimino al compilar, asi
    // que se llama directamente al motor con las mismas estructuras en memoria.
    public static class RawNav
    {
        [StructLayout(LayoutKind.Sequential)]
        public struct Source            // NavMeshBuildSource (92 bytes)
        {
            public Matrix4x4 transform;
            public Vector3 size;
            public int shape;           // 0 malla, 2 caja
            public int area;            // 0 caminable, 1 no caminable
            public int instanceID;
            public int componentID;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct Settings          // NavMeshBuildSettings
        {
            public int agentTypeID; public float agentRadius, agentHeight, agentSlope, agentClimb;
            public float ledgeDropHeight, maxJumpAcrossDistance, minRegionArea;
            public int overrideVoxelSize; public float voxelSize;
            public int overrideTileSize, tileSize, accuratePlacement; public uint maxJobWorkers;
            public int preserveTilesOutsideBounds; public int debugFlags;
            // los mismos valores que la NavMesh original del juego
            public static Settings Default() => new Settings
            {
                agentTypeID = 0, agentRadius = 0.25f, agentHeight = 2f, agentSlope = 45f, agentClimb = 0.75f,
                minRegionArea = 2f, voxelSize = 0.25f / 3f, tileSize = 256,
            };
        }

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate byte UpdateListD(IntPtr data, ref Settings s, IntPtr sources, ref Bounds b);
        [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void CreateD(IntPtr mono, int agentTypeID);
        [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int AddTD(IntPtr data, ref Vector3 pos, ref Quaternion rot);
        [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void RemoveAllD();

        static UpdateListD _update; static CreateD _create; static AddTD _add; static RemoveAllD _removeAll;
        static readonly List<object> _keep = new();     // que el recolector no libere nada nuestro

        static void Resolve()
        {
            if (_update != null) return;
            _update = IL2CPP.ResolveICall<UpdateListD>("UnityEngine.AI.NavMeshBuilder::UpdateNavMeshDataListInternal_Injected");
            _create = IL2CPP.ResolveICall<CreateD>("UnityEngine.AI.NavMeshData::Internal_Create");
            _add = IL2CPP.ResolveICall<AddTD>("UnityEngine.AI.NavMesh::AddNavMeshDataTransformedInternal_Injected");
            _removeAll = IL2CPP.ResolveICall<RemoveAllD>("UnityEngine.AI.NavMesh::RemoveAllNavMeshData");
        }

        public static void RemoveAll() { Resolve(); _removeAll(); }

        public static int Add(IntPtr data, Vector3 pos)
        {
            Resolve();
            var rot = Quaternion.identity;
            return _add(data, ref pos, ref rot);
        }

        public static IntPtr Build(Settings settings, List<Source> sources, Bounds bounds, out bool ok)
        {
            Resolve();
            // NavMeshData nueva
            var cls = Il2CppClassPointerStore<NavMeshData>.NativeClassPtr;
            IntPtr data = IL2CPP.il2cpp_object_new(cls);
            _create(data, settings.agentTypeID);
            var wrapper = new NavMeshData(data);
            _keep.Add(wrapper);

            // List<NavMeshBuildSource>: una lista cualquiera con _items apuntando a un array con las fuentes
            int stride = Marshal.SizeOf<Source>();
            if (stride != 92) Plugin.L.LogWarning($"[Escenario] NavMeshBuildSource mide {stride} bytes (esperado 92)");
            var arr = new Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppStructArray<byte>(stride * sources.Count);
            IntPtr start = arr.Pointer + 4 * IntPtr.Size;        // cabecera de un array de IL2CPP
            for (int i = 0; i < sources.Count; i++) Marshal.StructureToPtr(sources[i], start + i * stride, false);
            var list = new Il2CppSystem.Collections.Generic.List<Il2CppSystem.Object>();
            IntPtr lcls = IL2CPP.il2cpp_object_get_class(list.Pointer);
            int itemsOff = (int)IL2CPP.il2cpp_field_get_offset(IL2CPP.il2cpp_class_get_field_from_name(lcls, "_items"));
            int sizeOff = (int)IL2CPP.il2cpp_field_get_offset(IL2CPP.il2cpp_class_get_field_from_name(lcls, "_size"));
            Marshal.WriteIntPtr(list.Pointer + itemsOff, arr.Pointer);
            Marshal.WriteInt32(list.Pointer + sizeOff, sources.Count);
            _keep.Add(arr); _keep.Add(list);

            ok = _update(data, ref settings, list.Pointer, ref bounds) != 0;
            return data;
        }
    }
}
