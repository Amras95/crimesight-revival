// CRIMESIGHT Revival - swap a character's 3D model for another game character's.
//
// The launcher writes in csr_live/models.json which character is seen with which model:
//   { "swaps": { "PawnTypeData_A": "sherlock", "PawnTypeData_C": "PawnTypeData_E" } }
// Keys (what is swapped): PawnTypeData_A..F (Agatha, Berkeley, Catherine, Dorothy, Ellery, Freeman),
//   ThreatTypeData_Survivor / ThreatTypeData_Traitor (victim and traitor).
// Values (the model put on): the same keys, or "sherlock" / "moriarty" (the models of the murder
//   scene, KillCutPrefab, which the game loads with Addressables), or "custom:<name>" (a custom model in
//   csr_live/models/<name>.glb: see CrimeSightRevivalModelsGlb.cs).
//
// How it is done: the character stays as it is (its skeleton, its animations, its AI); only the
// meshes and materials of its SkinnedMeshRenderers are swapped for the other model's, hooked to its bones by
// name (every human in the game uses the same skeleton: ROOT_c_hum/SKL_000_WAIST/...). The bones
// only the other model has (capes, coat tails, collars) are created in place and stay at rest.
// The meshes go on the same objects as the originals when they match (the body, _00); the ones the
// character doesn't have (Sherlock's and Moriarty's separate eyes, eyebrows and mouth) are created next to them. The
// character's own
// extra meshes are switched off. If the skeleton doesn't fit (e.g. an animal), it isn't touched.
// Only whoever has it set sees it. The 2D portraits (cards, results) don't change.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.AddressableAssets;
using Il2CppInterop.Runtime;

namespace CrimeSightRevival.Mods
{
    static partial class Models
    {
        class Config
        {
            public Dictionary<string, string> swaps { get; set; }
            public Dictionary<string, Dictionary<string, string>> anims { get; set; }
        }

        class Saved
        {
            public SkinnedMeshRenderer smr; public Mesh mesh; public Material[] mats; public Transform[] bones;
            public Transform rootBone; public bool enabled; public bool offscreen;
        }

        class Applied
        {
            public GameObject root; public string target;
            public List<Link> links;                                     // own skeleton (adapted model) or null
            public List<Shoulder> shoulders;                             // its shoulders, which follow the arms
            public float sceneLogAt = -1f; public int sceneLogs;             // log of positions in the scenes
            public readonly List<Saved> saved = new();
            public readonly List<(Renderer r, bool enabled)> hidden = new();
            public readonly List<GameObject> created = new();
        }

        static string File_ => Path.Combine(LiveMods.LiveDir, "models.json");
        static Dictionary<string, string> _swaps = new();
        static string _sig = "";
        static float _next;
        static readonly Dictionary<int, Applied> _applied = new();          // by the character object's id
        static readonly Dictionary<int, string> _customTried = new();       // custom models that couldn't be applied
        static readonly HashSet<string> _warned = new();
        static GameObject _killCut;                                          // Sherlock and Moriarty template
        static bool _killCutAsked;
        static UnityEngine.ResourceManagement.AsyncOperations.AsyncOperationHandle<GameObject> _killCutHandle;

        public static void Frame()
        {
            if (Time.unscaledTime < _next) return;
            _next = Time.unscaledTime + 1f;
            try
            {
                ReadConfig();
                ExportSkeletons();
                Scan();
            }
            catch (Exception e) { Warn("frame", "[Modelos] " + e.Message); }
        }

        // ------------------------------------------------------------ config
        static void ReadConfig()
        {
            string sig = "";
            try { var fi = new FileInfo(File_); if (fi.Exists) sig = fi.Length + ":" + fi.LastWriteTimeUtc.Ticks; } catch { }
            string json = sig;
            sig += CustomSigs(_swaps) + AnimSigs(_anims);  // a .glb changed with the game open is reloaded too
            if (sig == _sig) return;
            var swaps = new Dictionary<string, string>();
            var anims = new Dictionary<string, Dictionary<string, string>>();
            if (json != "")
                try
                {
                    var c = JsonSerializer.Deserialize<Config>(File.ReadAllText(File_));
                    if (c?.swaps != null)
                        foreach (var kv in c.swaps)
                            if (!string.IsNullOrEmpty(kv.Value) && kv.Value != kv.Key) swaps[kv.Key] = kv.Value;
                    if (c?.anims != null)
                        foreach (var kv in c.anims)
                        {
                            var set = new Dictionary<string, string>();
                            if (kv.Value != null) foreach (var a in kv.Value) if (!string.IsNullOrEmpty(a.Value)) set[a.Key] = a.Value;
                            if (set.Count > 0) anims[kv.Key] = set;
                        }
                }
                catch (Exception e) { Plugin.L.LogWarning("[Modelos] models.json: " + e.Message); }
            _swaps = swaps;
            _anims = anims;
            _animMaps.Clear();
            foreach (var d in _drivers.Values) { d.map = null; d.fading = null; }
            _sig = json + CustomSigs(swaps) + AnimSigs(anims);
            _customTried.Clear();
            RevertAll();                                   // with the new config everything is applied again
            Plugin.L.LogInfo("[Modelos] " + (swaps.Count == 0 ? "sin cambios de modelo"
                : swaps.Count + " cambio(s): " + string.Join(", ", Pairs(swaps))));
            foreach (var kv in anims) Plugin.L.LogInfo("[Animaciones] " + kv.Key + ": " + string.Join(", ", Pairs(kv.Value)));
        }

        static string CustomSigs(Dictionary<string, string> swaps)
        {
            var sb = new System.Text.StringBuilder();
            foreach (var v in swaps.Values) if (v.StartsWith(CustomPrefix)) sb.Append('|').Append(v).Append('=').Append(CustomSig(v));
            return sb.ToString();
        }

        static IEnumerable<string> Pairs(Dictionary<string, string> d) { foreach (var kv in d) yield return kv.Key + " -> " + kv.Value; }

        // ------------------------------------------------------------ match characters
        static void Scan()
        {
            // the ones that no longer exist (end of the match)
            var gone = new List<int>();
            foreach (var kv in _applied) if (kv.Value.root == null) gone.Add(kv.Key);
            foreach (var id in gone) _applied.Remove(id);
            if (_borrowMap.Count > 0)
                foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<Pawn>()))
                {
                    var p = o.TryCast<Pawn>();
                    if (p?.pawnTypeData != null) HandleBorrow(p.gameObject, p.pawnTypeData.name);
                }
            if (_swaps.Count == 0 && _anims.Count == 0) return;
            if (_swaps.ContainsValue("sherlock") || _swaps.ContainsValue("moriarty")) AskKillCut();

            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<Pawn>()))
            {
                var p = o.TryCast<Pawn>();
                var data = p?.pawnTypeData;
                if (data == null) continue;
                Handle(p.gameObject, data.name);
                HandleAnim(p.gameObject, data.name);
            }
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<Threat>()))
            {
                var t = o.TryCast<Threat>();
                var data = t?.threatTypeData;
                if (data == null) continue;
                Handle(t.gameObject, data.name);
                HandleAnim(t.gameObject, data.name);
            }
        }

        static void Handle(GameObject owner, string key)
        {
            if (!_swaps.TryGetValue(key, out var target)) return;
            var root = ModelRoot(owner);
            if (root == null) return;
            int id = root.GetInstanceID();
            if (_applied.TryGetValue(id, out var a) && a.target == target) return;
            if (target.StartsWith(CustomPrefix))
            {
                if (_customTried.TryGetValue(id, out var tried) && tried == target + "|" + CustomSig(target)) return;   // already failed
                if (!Prefit(target.Substring(CustomPrefix.Length), key)) return;     // the heavy part, on another thread: assembled when ready
                if (a != null) { Revert(a); _applied.Remove(id); }
                var ac = ApplyCustom(root, target, key);
                if (ac != null) { _applied[id] = ac; _customTried.Remove(id); }
                else _customTried[id] = target + "|" + CustomSig(target);
                return;
            }
            var tpl = Template(target);
            if (tpl == null) return;                        // not there yet (Sherlock/Moriarty loading) or doesn't exist
            if (a != null) { Revert(a); _applied.Remove(id); }
            var applied = Apply(root, tpl, target, key);
            if (applied != null) _applied[id] = applied;
        }

        /// <summary>The model object inside the character (c_hum_XX); if it isn't found, the character
        /// itself.</summary>
        static GameObject ModelRoot(GameObject owner)
        {
            foreach (var t in owner.GetComponentsInChildren<Transform>(true))
                if (Regex.IsMatch(t.name, @"^c_(hum|anm)_\d\d(\(Clone\))?$")) return t.gameObject;
            return owner.GetComponentInChildren<SkinnedMeshRenderer>(true) != null ? owner : null;
        }

        // ------------------------------------------------------------ models that can be applied
        static GameObject Template(string target)
        {
            if (target == "sherlock" || target == "moriarty")
            {
                if (_killCut == null) return null;
                var t = _killCut.transform.Find(target == "sherlock" ? "Timeline/Ruler01/c_hum_10" : "Timeline/Ruler02/c_hum_11");
                if (t == null) Warn("tpl" + target, "[Modelos] no encuentro a " + target + " en KillCutPrefab");
                return t != null ? t.gameObject : null;
            }
            foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<PawnTypeData>()))
            {
                var d = o.TryCast<PawnTypeData>();
                if (d != null && d.name == target && d.modelPrefab != null) return d.modelPrefab;
            }
            foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<ThreatTypeData>()))
            {
                var d = o.TryCast<ThreatTypeData>();
                if (d != null && d.name == target && d.modelPrefab != null) return d.modelPrefab;
            }
            Warn("tpl" + target, "[Modelos] no encuentro el modelo " + target);
            return null;
        }

        /// <summary>The game's murder scene (it has Sherlock and Moriarty): requested once from
        /// Addressables.</summary>
        static void AskKillCut()
        {
            if (_killCut != null) return;
            try
            {
                if (!_killCutAsked)
                {
                    _killCutAsked = true;
                    var key = new Il2CppSystem.Object(IL2CPP.ManagedStringToIl2Cpp("KillCutPrefab"));
                    _killCutHandle = Addressables.LoadAssetAsync<GameObject>(key);
                    Plugin.L.LogInfo("[Modelos] cargando los modelos de Sherlock y Moriarty");
                    return;
                }
                if (!_killCutHandle.IsDone) return;
                _killCut = _killCutHandle.Result;
                Plugin.L.LogInfo(_killCut != null ? "[Modelos] Sherlock y Moriarty listos" : "[Modelos] no pude cargar KillCutPrefab");
            }
            catch (Exception e) { Warn("killcut", "[Modelos] KillCutPrefab: " + e.Message); }
        }

        // ------------------------------------------------------------ mesh swap
        // "mesh_c_hum_10_00" (Sherlock, Moriarty: body, eyes, eyebrows and mouth separately) or "c_hum_04_00" (the
        // board characters: everything in one mesh)
        static readonly Regex Slot = new(@"^(?:mesh_)?c_[a-z]+_\d+_(.+)$");

        static string SlotOf(string name)
        {
            var m = Slot.Match(name.Replace("(Clone)", ""));
            return m.Success ? m.Groups[1].Value : name;
        }

        static Applied Apply(GameObject root, GameObject tpl, string target, string key)
        {
            var bones = new Dictionary<string, Transform>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                if (!bones.ContainsKey(t.name)) bones[t.name] = t;
            var tplBones = new Dictionary<string, Transform>();
            foreach (var t in tpl.GetComponentsInChildren<Transform>(true))
                if (!tplBones.ContainsKey(t.name)) tplBones[t.name] = t;

            var tSmrs = tpl.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            if (tSmrs.Length == 0) { Warn("nosmr" + target, "[Modelos] " + target + " no tiene mallas"); return null; }

            // does the skeleton fit? (how many bones used by the other model exist here)
            int used = 0, found = 0;
            foreach (var s in tSmrs)
                foreach (var b in s.bones)
                    if (b != null) { used++; if (bones.ContainsKey(b.name)) found++; }
            if (used == 0 || found < used * 0.6f)
            {
                Warn("fit" + key + target, $"[Modelos] {target} no encaja en {key} ({found} de {used} huesos): no se cambia");
                return null;
            }

            var a = new Applied { root = root, target = target };
            var own = new Dictionary<string, SkinnedMeshRenderer>();
            foreach (var s in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (!Slot.IsMatch(s.name.Replace("(Clone)", ""))) continue;     // shadows and the like: not touched
                a.saved.Add(new Saved { smr = s, mesh = s.sharedMesh, mats = ToArr(s.sharedMaterials), bones = ToArr(s.bones),
                                        rootBone = s.rootBone, enabled = s.enabled, offscreen = s.updateWhenOffscreen });
                own[SlotOf(s.name)] = s;
            }
            var usedOwn = new HashSet<int>();
            Transform meshParent = a.saved.Count > 0 ? a.saved[0].smr.transform.parent : root.transform;

            foreach (var ts in tSmrs)
            {
                if (!own.TryGetValue(SlotOf(ts.name), out var dst) || usedOwn.Contains(dst.GetInstanceID()))
                {
                    var go = new GameObject(ts.name);                     // the other model has an extra mesh
                    go.transform.SetParent(meshParent, false);
                    go.transform.localPosition = ts.transform.localPosition;
                    go.transform.localRotation = ts.transform.localRotation;
                    go.transform.localScale = ts.transform.localScale;
                    go.layer = meshParent.gameObject.layer;
                    dst = go.AddComponent<SkinnedMeshRenderer>();
                    a.created.Add(go);
                }
                usedOwn.Add(dst.GetInstanceID());
                var tb = ts.bones;
                var nb = new Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppReferenceArray<Transform>(tb.Length);
                for (int i = 0; i < tb.Length; i++)
                    nb[i] = tb[i] == null ? null : Bone(tb[i], bones, tplBones, root.transform, a);
                dst.sharedMesh = ts.sharedMesh;
                dst.sharedMaterials = ts.sharedMaterials;
                dst.bones = nb;
                dst.rootBone = ts.rootBone != null ? Bone(ts.rootBone, bones, tplBones, root.transform, a) : dst.rootBone;
                dst.updateWhenOffscreen = true;                           // the original mesh's bounds are no longer valid
                dst.enabled = true;
            }
            // the character's own meshes the other model doesn't have, out
            foreach (var s in a.saved)
                if (!usedOwn.Contains(s.smr.GetInstanceID())) s.smr.enabled = false;
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
                if (r.name.StartsWith("mesh_") && r.enabled) { a.hidden.Add((r, r.enabled)); r.enabled = false; }

            Plugin.L.LogInfo($"[Modelos] {key} con el modelo de {target} ({found} de {used} huesos, {a.created.Count} piezas nuevas)");
            return a;
        }

        /// <summary>The bone with that name in the character; if it doesn't have it (cape, coat tail...), it is
        /// created hanging from the
        /// same parent as in the other model and in the same rest pose.</summary>
        static Transform Bone(Transform tb, Dictionary<string, Transform> bones, Dictionary<string, Transform> tplBones,
                              Transform root, Applied a)
        {
            if (bones.TryGetValue(tb.name, out var b)) return b;
            Transform parent = tb.parent != null && tplBones.ContainsKey(tb.parent.name)
                ? Bone(tb.parent, bones, tplBones, root, a) : root;
            var go = new GameObject(tb.name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = tb.localPosition;
            go.transform.localRotation = tb.localRotation;
            go.transform.localScale = tb.localScale;
            a.created.Add(go);
            bones[tb.name] = go.transform;
            return go.transform;
        }

        static void Revert(Applied a)
        {
            try
            {
                foreach (var s in a.saved)
                {
                    if (s.smr == null) continue;
                    s.smr.sharedMesh = s.mesh;
                    s.smr.sharedMaterials = s.mats;
                    s.smr.bones = s.bones;
                    s.smr.rootBone = s.rootBone;
                    s.smr.updateWhenOffscreen = s.offscreen;
                    s.smr.enabled = s.enabled;
                }
                foreach (var (r, en) in a.hidden) if (r != null) r.enabled = en;
                for (int i = a.created.Count - 1; i >= 0; i--) if (a.created[i] != null) UnityEngine.Object.Destroy(a.created[i]);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Modelos] deshacer: " + e.Message); }
        }

        static void RevertAll()
        {
            foreach (var a in _applied.Values) Revert(a);
            _applied.Clear();
        }

        static T[] ToArr<T>(IEnumerable<T> e) => new List<T>(e).ToArray();

        static void Warn(string key, string msg)
        {
            if (_warned.Add(key)) Plugin.L.LogWarning(msg);
        }
    }
}
