// CRIMESIGHT Revival - animaciones propias en lugar de las del juego (reposo, andar y correr) para cada personaje.
//
// En models.json: "anims": { "PawnTypeData_A": { "idle": "<nombre>", "walk": "<nombre>", "run": "<nombre>" } }, con
// cada animacion en csr_live/anims/<nombre>.glb (el lanzador la copia, o la convierte si es .fbx). Sirve cualquier
// animacion humanoide (Mixamo, VRChat, Blender...): se adapta al esqueleto del juego con Humanoid.PrepareAnim.
// El juego sigue decidiendo que hace cada personaje (SimpleAnimation); cuando lo que suena es un reposo, un paso o
// una carrera, despues de sus animaciones (LateUpdate) se ponen los giros de la propia, con un fundido corto.
// Va sobre los huesos del juego, o sobre el esqueleto propio si el personaje lleva un modelo adaptado.
using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static partial class Models
    {
        public static readonly string[] AnimKinds = { "idle", "walk", "run" };
        static Dictionary<string, Dictionary<string, string>> _anims = new();

        class AnimFile { public string sig; public Glb.Model model; }
        static readonly Dictionary<string, AnimFile> _animFiles = new();
        static readonly Dictionary<string, Humanoid.AnimMap> _animMaps = new();     // "nombre|personaje|firma"
        static readonly HashSet<string> _animFailed = new();

        class Driver
        {
            public GameObject root; public string key; public SimpleAnimation sa;
            public Applied applied; public bool built;
            public readonly Dictionary<string, Transform> targets = new();
            public readonly Dictionary<string, Quaternion> restRot = new();       // reposo de cada hueso del juego (espacio del modelo)
            public Vector3 hipsRest; public float hipK = 1f;
            public Humanoid.AnimMap map, fading; public float start, w;
            public string lastClip;
        }
        static readonly Dictionary<int, Driver> _drivers = new();
        static readonly List<(string game, double[] q)> _rot = new();
        static int _clipLogs;

        static string AnimPath(string name) => Path.Combine(LiveMods.LiveDir, "anims", name + ".glb");

        static string FileSig(string path)
        {
            try { var fi = new FileInfo(path); return fi.Exists ? fi.Length + ":" + fi.LastWriteTimeUtc.Ticks : "-"; }
            catch { return "-"; }
        }

        static string AnimSigs(Dictionary<string, Dictionary<string, string>> anims)
        {
            var sb = new System.Text.StringBuilder();
            foreach (var kv in anims) foreach (var a in kv.Value.Values) sb.Append('|').Append(a).Append('=').Append(FileSig(AnimPath(a)));
            return sb.ToString();
        }

        static Glb.Model LoadAnim(string name)
        {
            string path = AnimPath(name), sig = FileSig(path);
            if (sig == "-") { Warn("noanim" + name, "[Animaciones] no esta " + path); return null; }
            if (_animFiles.TryGetValue(name, out var have) && have.sig == sig) return have.model;
            if (_animFailed.Contains(name + "|" + sig)) return null;
            try
            {
                var m = Glb.Read(File.ReadAllBytes(path));
                if (m.anims.Count == 0) { _animFailed.Add(name + "|" + sig); Warn("noanim2" + name, "[Animaciones] " + name + " no tiene ninguna animacion"); return null; }
                _animFiles[name] = new AnimFile { sig = sig, model = m };
                Plugin.L.LogInfo($"[Animaciones] {name}: {m.anims[0].name}, {m.anims[0].duration:0.##} s, {m.nodes.Count} huesos");
                return m;
            }
            catch (Exception e)
            {
                _animFailed.Add(name + "|" + sig);
                Plugin.L.LogWarning("[Animaciones] no pude leer " + name + ": " + e.Message);
                return null;
            }
        }

        static Humanoid.AnimMap MapFor(string name, Driver d)
        {
            var m = LoadAnim(name);
            if (m == null) return null;
            string k = name + "|" + d.key + "|" + _animFiles[name].sig;
            if (_animMaps.TryGetValue(k, out var have)) return have;
            Humanoid.AnimMap map = null;
            try
            {
                var rest = RestPose(d.key, d.root, out var parents);
                var live = new Dictionary<string, Transform>();
                foreach (var t in d.root.GetComponentsInChildren<Transform>(true)) if (!live.ContainsKey(t.name)) live[t.name] = t;
                var game = new Dictionary<string, Humanoid.GameBone>();
                foreach (var kv in rest)
                    if (live.ContainsKey(kv.Key))
                        game[kv.Key] = new Humanoid.GameBone { name = kv.Key, parent = parents.GetValueOrDefault(kv.Key), pos = new double[] { kv.Value.m03, kv.Value.m13, kv.Value.m23 } };
                map = Humanoid.PrepareAnim(m, m.anims[0], game, out var report);
                Plugin.L.LogInfo($"[Animaciones] {name} en {d.key}: {report}");
            }
            catch (Exception e) { Plugin.L.LogWarning($"[Animaciones] {name} en {d.key}: {e.Message}"); }
            _animMaps[k] = map;
            return map;
        }

        static void HandleAnim(GameObject owner, string key)
        {
            if (!_anims.ContainsKey(key)) return;
            var root = ModelRoot(owner);
            if (root == null) return;
            int id = root.GetInstanceID();
            if (_drivers.ContainsKey(id)) return;
            var sa = owner.GetComponentInChildren<SimpleAnimation>(true);
            if (sa == null) { Warn("nosa" + key, "[Animaciones] " + key + " no tiene SimpleAnimation"); return; }
            _drivers[id] = new Driver { root = root, key = key, sa = sa };
        }

        /// <summary>Lo que hace ahora el personaje: la animacion del juego con mas peso -> idle / walk / run (o null).</summary>
        static string Kind(Driver d)
        {
            string best = null; float bw = 0;
            var it = d.sa.GetStates().GetEnumerator();
            var en = it.Cast<Il2CppSystem.Collections.IEnumerator>();
            while (en.MoveNext())
            {
                var st = it.Current;
                if (st == null || !st.enabled || st.weight <= bw) continue;
                bw = st.weight;
                var clip = st.clip;
                best = clip != null ? clip.name : st.name;
            }
            if (best != d.lastClip) { d.lastClip = best; if (_clipLogs++ < 40) Plugin.L.LogInfo("[Animaciones] " + d.key + " hace " + best); }
            if (best == null) return null;
            best = best.ToLowerInvariant();
            if (best.Contains("_nml_i_idl")) return "idle";
            if (best.Contains("_nml_t_wlk")) return "walk";
            if (best.Contains("_nml_t_run")) return "run";
            return null;
        }

        static void BuildTargets(Driver d)
        {
            d.targets.Clear(); d.restRot.Clear();
            var rest = RestPose(d.key, d.root, out var parents);
            foreach (var kv in rest) d.restRot[kv.Key] = kv.Value.rotation;
            var live = new Dictionary<string, Transform>();
            foreach (var t in d.root.GetComponentsInChildren<Transform>(true)) if (!live.ContainsKey(t.name)) live[t.name] = t;
            d.hipK = 1f;
            Link hipLink = null;
            if (d.applied?.links != null)
                foreach (var l in d.applied.links)
                {
                    if (l.own == null || l.game == null) continue;
                    d.targets[l.game.name] = l.own;
                    if (l.mode == 1) hipLink = l;
                }
            foreach (var kv in live) if (!d.targets.ContainsKey(kv.Key)) d.targets[kv.Key] = kv.Value;
            if (hipLink != null) { d.hipsRest = hipLink.ownRest; d.hipK = hipLink.k; }
            else if (rest.TryGetValue("SKL_000_WAIST", out var hm) && rest.TryGetValue(parents.GetValueOrDefault("SKL_000_WAIST") ?? "", out var pm))
                d.hipsRest = Quaternion.Inverse(pm.rotation) * (new Vector3(hm.m03, hm.m13, hm.m23) - new Vector3(pm.m03, pm.m13, pm.m23));
            else if (live.TryGetValue("SKL_000_WAIST", out var ht)) d.hipsRest = ht.localPosition;
            d.built = true;
        }

        static void LateAnims()
        {
            if (_drivers.Count == 0) return;
            List<int> gone = null;
            foreach (var kv in _drivers)
            {
                var d = kv.Value;
                if (d.root == null || d.sa == null) { (gone ??= new List<int>()).Add(kv.Key); continue; }
                try { Drive(d, kv.Key); }
                catch (Exception e) { Warn("drive" + d.key, "[Animaciones] " + d.key + ": " + e.Message); }
            }
            if (gone != null) foreach (var id in gone) _drivers.Remove(id);
        }

        static void Drive(Driver d, int id)
        {
            var kind = Kind(d);
            Humanoid.AnimMap map = null;
            if (kind != null && _anims.TryGetValue(d.key, out var set) && set.TryGetValue(kind, out var name) && !string.IsNullOrEmpty(name))
                map = MapFor(name, d);
            if (map != d.map)
            {
                if (map != null) d.start = Time.time;
                if (d.map != null) d.fading = d.map;
                d.map = map;
            }
            d.w = Mathf.MoveTowards(d.w, map != null ? 1f : 0f, Time.deltaTime / 0.25f);
            var use = map ?? d.fading;
            if (d.w <= 0f || use == null || use.anim.duration <= 0f) { if (d.w <= 0f) d.fading = null; return; }

            _applied.TryGetValue(id, out var ap);
            if (!d.built || ap != d.applied) { d.applied = ap; BuildTargets(d); }

            float t = (Time.time - d.start) % use.anim.duration;
            Humanoid.SampleAnim(use, t, _rot, out var hipUp);
            var rootRot = d.root.transform.rotation;
            var toRoot = Quaternion.Inverse(rootRot);
            var q = new float[4];
            foreach (var (g, m) in _rot)
            {
                if (!d.targets.TryGetValue(g, out var tr) || tr == null || !d.restRot.TryGetValue(g, out var r0)) continue;
                // m es un giro por filas en el espacio del modelo: columnas (m0 m3 m6), (m1 m4 m7), (m2 m5 m8)
                Glb.Quat((float)m[0], (float)m[3], (float)m[6], (float)m[1], (float)m[4], (float)m[7], (float)m[2], (float)m[5], (float)m[8], q);
                var world = new Quaternion(q[0], q[1], q[2], q[3]) * r0;
                var parentWorld = tr.parent != null ? toRoot * tr.parent.rotation : Quaternion.identity;
                var local = Quaternion.Inverse(parentWorld) * world;
                tr.localRotation = d.w >= 1f ? local : Quaternion.Slerp(tr.localRotation, local, d.w);
            }
            if (d.targets.TryGetValue("SKL_000_WAIST", out var hips) && hips != null)
            {
                var target = d.hipsRest + new Vector3(0f, (float)hipUp * d.hipK, 0f);
                hips.localPosition = Vector3.Lerp(hips.localPosition, target, d.w);
            }
        }
    }
}
