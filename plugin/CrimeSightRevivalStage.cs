// CRIMESIGHT Revival - laboratorio de escenarios (prueba de concepto del creador de escenarios).
//
// Anade a la lista de escenarios uno de pruebas ("Escenario de pruebas (CSR)", Stage_Yokn_CSRTest),
// que es una copia del 01 (Lauriston Gardens). Los escenarios del juego no se tocan nunca: los cambios
// solo se aplican cuando se juega el de pruebas. Necesita el plugin en todos los jugadores de la sala.
//
// Que hace en el de pruebas: carga el escenario 01 y, segun BepInEx\csr_live\layout_test.json, mueve
// sus piezas unas casillas (antes de que el juego calcule sus casillas), convierte las casillas de
// salida de los personajes y recalcula la navegacion (NavMesh) con las mallas NAV_* del propio juego.
// Sin ese archivo es una copia exacta del 01.
//
// layout_test.json: {"dx":0,"dz":2,"navmesh":"rebuild"}
//   navmesh: "rebuild" (la construye de cero), "offset" (mueve la original) o "keep" (no la toca)
// navsrc.json (lo genera el lanzador desde la copia del juego del usuario): las mallas NAV_* en
// version legible, porque las del juego no se pueden leer desde codigo.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text.Json;
using HarmonyLib;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.SceneManagement;
using System.Runtime.InteropServices;
using Il2CppInterop.Runtime;

namespace CrimeSightRevival.Mods
{
    public class LayoutTest
    {
        public int dx { get; set; }
        public int dz { get; set; }
        public string navmesh { get; set; } = "keep";
    }

    public class NavSrcMesh { public float[] v { get; set; } public int[] t { get; set; } }
    public class NavSrcFile { public Dictionary<string, NavSrcMesh> meshes { get; set; } }

    public static class StageLab
    {
        const float GRID = 6f;
        static LayoutTest _cfg;
        static int _movedHandle = int.MinValue;
        static readonly HashSet<int> _seenScenes = new();
        static bool _navPending;
        static Scene _scene;
        static Transform _root;
        static Vector3 _off;
        static int[] _spawnsBefore = Array.Empty<int>();
        static readonly Dictionary<string, Mesh> _readable = new();
        static readonly List<(Transform t, Vector3 local)> _watch = new();
        static float _watchUntil;
        static int _agentReports;

        static string TestFile => Path.Combine(LiveMods.LiveDir, "layout_test.json");
        static string NavFile => Path.Combine(LiveMods.LiveDir, "navsrc.json");
        static void Log(string s) => Plugin.L.LogInfo("[Escenario] " + s);
        static void Warn(string s) => Plugin.L.LogWarning("[Escenario] " + s);

        public const string TEST_STAGE = "Stage_Yokn_CSRTest";
        const string BASE_STAGE = "Stage_Yokn";
        static bool _armed;

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
            foreach (var t in new[] { typeof(Stage), typeof(Area), typeof(Room), typeof(Door), typeof(Shelf), typeof(WindowShelf) })
                Patch(t, "Awake", nameof(BeforeAwake));
            Log("escenario de pruebas disponible: " + TEST_STAGE);
        }

        // ---------------------------------------------------------------- escenario de pruebas
        static readonly string[] TestName =
        {   // ja, en, fr, it, de, es, pt, ru, ko, zh-CN, zh-TW (orden de TextManager)
            "テスト用ステージ (CSR)", "Test stage (CSR)", "Scénario de test (CSR)", "Scenario di prova (CSR)",
            "Testszenario (CSR)", "Escenario de pruebas (CSR)", "Cenário de testes (CSR)", "Тестовый сценарий (CSR)",
            "테스트 스테이지 (CSR)", "测试场景 (CSR)", "測試場景 (CSR)",
        };

        public static void EnsureTexts()
        {
            var tm = TextManager.Instance;
            if (tm == null || tm.LangText == null) return;
            int lang = (int)tm.GetLangType();
            string text = lang >= 0 && lang < TestName.Length ? TestName[lang] : TestName[1];
            string key = "ctg_name_stageName_" + TEST_STAGE;
            if (!tm.LangText.ContainsKey(key) || tm.LangText[key] != text) tm.LangText[key] = text;
        }

        // la lista de la ventana de ajustes de la sala: se anade el de pruebas antes de "Aleatorio"
        static void BeforeStageList(OutGameRoomPopupRoomSetting __instance)
        {
            try
            {
                EnsureTexts();
                var list = __instance.UseStageList;
                if (list == null) return;
                int random = -1;
                for (int i = 0; i < list.Count; i++)
                {
                    var n = list[i]?.StageName;
                    if (n == TEST_STAGE) return;
                    if (n == "Random") random = i;
                }
                var d = new OutGameRoomPopupRoomSetting.StageData { StageName = TEST_STAGE };
                if (random >= 0) list.Insert(random, d); else list.Add(d);
            }
            catch (Exception e) { Plugin.L.LogError(e); }
        }

        // el juego pide cargar el de pruebas: se carga el 01 y se activa la prueba
        static void MapStage(ref string stageName)
        {
            if (stageName == TEST_STAGE)
            {
                if (!_armed) Arm();
                stageName = BASE_STAGE;
            }
            else if (!string.IsNullOrEmpty(stageName) && stageName.StartsWith("Stage_"))
            {
                if (_armed) Log("escenario normal: prueba desactivada");
                _armed = false;
            }
        }

        static void BeforeLoadStage(GameManager __instance)
        {
            try
            {
                if (__instance.currentStageName == TEST_STAGE)
                {
                    if (!_armed) Arm();
                    __instance.currentStageName = BASE_STAGE;
                }
            }
            catch (Exception e) { Plugin.L.LogError(e); }
        }

        static void Arm()
        {
            _armed = true;
            _cfg = new LayoutTest();
            if (File.Exists(TestFile))
                try { _cfg = JsonSerializer.Deserialize<LayoutTest>(File.ReadAllText(TestFile)) ?? new LayoutTest(); }
                catch (Exception e) { Warn("layout_test.json no valido: " + e.Message); }
            _off = new Vector3(_cfg.dx * GRID, 0, _cfg.dz * GRID);
            Log($"PRUEBA ACTIVA: dx={_cfg.dx} dz={_cfg.dz} navmesh={_cfg.navmesh}");
        }

        // ---------------------------------------------------------------- mover antes de Awake
        static void BeforeAwake(Component __instance)
        {
            try
            {
                if (!_armed) return;
                var sc = __instance.gameObject.scene;
                int handle = sc.handle;
                if (_seenScenes.Add(handle)) Log($"escena cargando: '{sc.name}' (primer Awake: {__instance.GetIl2CppType().Name} {__instance.gameObject.name})");
                if (!_armed || handle == _movedHandle) return;
                if (sc.name != BASE_STAGE) return;
                _movedHandle = handle;
                Move(__instance.transform.root, sc);
            }
            catch (Exception e) { Plugin.L.LogError(e); }
        }

        static void Move(Transform root, Scene sc)
        {
            _root = root; _scene = sc; _navPending = true;
            // La raiz tiene un Animator que el juego reproduce al empezar (y le devuelve su posicion),
            // asi que se mueven sus hijos, no la raiz.
            Log($"raiz '{root.name}' en {root.position}; se mueven sus {root.childCount} hijos {_off}");
            _watch.Clear();
            for (int i = 0; i < root.childCount; i++)
            {
                var c = root.GetChild(i);
                c.position += _off;
                _watch.Add((c, c.localPosition));
            }
            _watchUntil = Time.unscaledTime + 30f;
            _agentReports = 0;
            Physics.SyncTransforms();

            var stage = root.GetComponentInChildren<Stage>(true);
            if (stage == null) { Warn("no hay componente Stage"); return; }
            var ids = stage.pawnSpawnGridIds;
            if (ids == null) { Warn("pawnSpawnGridIds vacio"); return; }
            _spawnsBefore = new int[ids.Length];
            var txt = new List<string>();
            for (int i = 0; i < ids.Length; i++)
            {
                _spawnsBefore[i] = ids[i];
                int n = Shift(ids[i], _cfg.dx, _cfg.dz, out bool ok);
                txt.Add($"{ids[i]}->{n}{(ok ? "" : "(FUERA)")}");
                ids[i] = n;
            }
            Log("salidas: " + string.Join(", ", txt));
        }

        // GridManager: id = 10*x + (x<0 ? -z : z), casillas de 6 unidades, x -6..6, z 0..9
        static void IdToXZ(int id, out int x, out int z)
        {
            int a = Math.Abs(id);
            x = a / 10; z = a % 10;
            if (id < 0) x = -x;
        }
        static int XZToId(int x, int z) => (x < 0 ? -z : z) + 10 * x;
        static int Shift(int id, int dx, int dz, out bool ok)
        {
            IdToXZ(id, out int x, out int z);
            x += dx; z += dz;
            ok = x >= -6 && x <= 6 && z >= 0 && z <= 9;
            return XZToId(x, z);
        }

        // ---------------------------------------------------------------- despues de cargar
        public static void Frame()
        {
            if (_cfg == null) return;
            Watch();
            if (!_navPending) return;
            try
            {
                if (_root == null) { _navPending = false; return; }
                if (!_scene.isLoaded) return;
                _navPending = false;
                Report();
                if (_cfg.navmesh == "keep") Log("navmesh: sin tocar");
                else if (_cfg.navmesh == "offset") NavOffset();
                else if (!NavRebuild()) { Warn("reconstruccion fallida: se usa la original desplazada"); NavOffset(); }
                WarpAgents();
                Probe();
            }
            catch (Exception e) { Plugin.L.LogError(e); }
        }

        // Avisa si algo del juego vuelve a colocar las piezas movidas (y las deja donde las pusimos).
        static void Watch()
        {
            if (_watch.Count == 0 || Time.unscaledTime > _watchUntil) return;
            for (int i = 0; i < _watch.Count; i++)
            {
                var (t, local) = _watch[i];
                if (t == null) continue;
                if ((t.localPosition - local).sqrMagnitude > 0.0001f)
                {
                    Warn($"'{t.name}' se ha movido solo de {local} a {t.localPosition} (seg {Time.unscaledTime:0.0}); se recoloca");
                    t.localPosition = local;
                    Physics.SyncTransforms();
                }
            }
            if (_root != null && Time.frameCount % 300 == 0 && _agentReports < 4)
            {
                _agentReports++;
                var off = new List<string>();
                foreach (var a in UnityEngine.Object.FindObjectsOfType<NavMeshAgent>(true))
                    if (!a.isOnNavMesh && off.Count < 12)
                        off.Add($"{a.gameObject.name}{(a.enabled ? "" : "(apagado)")} en {a.transform.position}");
                Log(off.Count == 0 ? "todos los agentes estan en la navmesh" : "agentes fuera de la navmesh: " + string.Join("; ", off));
            }
        }

        static void Report()
        {
            var rooms = _root.GetComponentsInChildren<Room>(true);
            var doors = _root.GetComponentsInChildren<Door>(true);
            var shelves = _root.GetComponentsInChildren<Shelf>(true);
            Log($"cargado: {rooms.Length} habitaciones, {doors.Length} puertas, {shelves.Length} muebles/ventanas");
            foreach (var r in rooms)
            {
                var p = r.transform.position;
                Log($"  {r.gameObject.name} en ({p.x:0.#},{p.z:0.#}) casilla {PosId(p)}");
            }
        }

        static int PosId(Vector3 p) => GridManager.PositionToId(ref p);

        static NavMeshData Baked()
        {
            NavMeshData best = null;
            foreach (var d in Resources.FindObjectsOfTypeAll<NavMeshData>())
            {
                Log($"NavMeshData '{d.name}' ({d.GetInstanceID()})");
                if (best == null || d.GetInstanceID() > 0) best = d;   // la del escenario es un asset (id > 0)
            }
            return best;
        }

        static void NavOffset()
        {
            var baked = Baked();
            if (baked == null) { Warn("no se encontro la NavMesh original"); return; }
            RawNav.RemoveAll();
            int h = RawNav.Add(baked.Pointer, _off);
            Log($"navmesh: original desplazada (instancia {h})");
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
                var orig = mf.sharedMesh;
                if (orig == null) continue;
                var mesh = Readable(orig, src);
                if (mesh == null) { missing++; Warn("sin datos: " + orig.name); continue; }
                bool floor = go.name.StartsWith("NAV_FLOOR");
                var m = mf.transform.localToWorldMatrix;
                sources.Add(new RawNav.Source { transform = m, shape = 0, area = floor ? 0 : 1, instanceID = mesh.GetInstanceID() });
                if (floor) floors++; else blocks++;
                var wb = WorldBounds(mesh.bounds, m);
                if (!any) { all = wb; any = true; } else all.Encapsulate(wb);
            }
            Log($"fuentes: {floors} suelos, {blocks} bloqueos, {missing} sin datos; limites {all.center}/{all.size}");
            if (!any || floors == 0) return false;
            all.Expand(2f);
            var settings = RawNav.Settings.Default();
            IntPtr data = RawNav.Build(settings, sources, all, out bool ok);
            Log($"construccion: ok={ok} en {sw.ElapsedMilliseconds} ms");
            if (!ok || data == IntPtr.Zero) return false;
            RawNav.RemoveAll();
            int h = RawNav.Add(data, Vector3.zero);
            Log($"navmesh: reconstruida (instancia {h})");
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

        static void WarpAgents()
        {
            int n = 0, off = 0;
            foreach (var a in UnityEngine.Object.FindObjectsOfType<NavMeshAgent>())
            {
                if (!a.enabled) continue;
                if (a.Warp(a.transform.position)) n++; else off++;
            }
            Log($"agentes recolocados: {n} (fuera de la navmesh: {off})");
        }

        // Comprueba que hay suelo navegable en las salidas y en el centro de cada habitacion.
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
                    Log($"salida {i}: casilla {ids[i]} pos {p} -> {(hit ? $"navegable a {h.distance:0.00}" : "SIN NAVMESH")}");
                }
            }
            foreach (var r in _root.GetComponentsInChildren<Room>(true))
            {
                var p = r.transform.position;
                bool hit = NavMesh.SamplePosition(p, out var h, 3f, -1);
                Log($"  {r.gameObject.name}: {(hit ? $"navegable a {h.distance:0.00}" : "SIN NAVMESH")}");
            }
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
