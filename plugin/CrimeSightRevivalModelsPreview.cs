// CRIMESIGHT Revival - models to show outside the match (Character Selector, automatic portraits).
//
// A custom model (.glb) is assembled still, in the pose it was made in, without the game's skeleton: that way it
// can be seen even if the game hasn't loaded its characters yet (in the waiting room). An original character is
// copied from its prefab (only if the game already has it loaded) with its scripts off.
using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.InteropTypes.Arrays;

namespace CrimeSightRevival.Mods
{
    static partial class Models
    {
        /// <summary>A game character's material (so the model shows with its shading), or null.</summary>
        static Material HumanMaterial()
        {
            try
            {
                var tpl = Template("PawnTypeData_A");
                if (tpl == null) return null;
                foreach (var smr in tpl.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (smr.sharedMaterial != null && Slot.IsMatch(smr.name.Replace("(Clone)", ""))) return smr.sharedMaterial;
            }
            catch { }
            return null;
        }

        /// <summary>A custom model (csr_live/models/&lt;id&gt;.glb) assembled still on the given layer. made: created
        /// meshes
        /// (they must be destroyed with the object).</summary>
        internal static GameObject PreviewGlb(string id, int layer, List<UnityEngine.Object> made)
        {
            var c = LoadCustom(id);
            if (c == null) return null;
            var root = new GameObject("CSR_Vista_" + id);
            root.layer = layer;
            var baseMat = HumanMaterial();
            foreach (var p in c.model.parts)
            {
                int vc = p.pos.Length / 3;
                var verts = new Vector3[vc];
                for (int v = 0; v < vc; v++) verts[v] = new Vector3(p.pos[v * 3], p.pos[v * 3 + 1], p.pos[v * 3 + 2]);
                var mesh = new Mesh { name = "csr_vista_" + id + "_" + p.name };
                if (vc > 65535) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                mesh.vertices = verts;
                if (p.nrm != null)
                {
                    var n = new Vector3[vc];
                    for (int v = 0; v < vc; v++) n[v] = new Vector3(p.nrm[v * 3], p.nrm[v * 3 + 1], p.nrm[v * 3 + 2]);
                    mesh.normals = n;
                }
                if (p.uv != null)
                {
                    var uv = new Vector2[vc];
                    for (int v = 0; v < vc; v++) uv[v] = new Vector2(p.uv[v * 2], p.uv[v * 2 + 1]);
                    mesh.uv = uv;
                }
                mesh.SetTriangles(p.tris, 0);
                if (p.nrm == null) mesh.RecalculateNormals();
                mesh.RecalculateBounds();
                made.Add(mesh);
                var go = new GameObject("CSR_Vista_" + p.name);
                go.layer = layer;
                go.transform.SetParent(root.transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>();
                var tex = p.image >= 0 && p.image < c.tex.Length ? c.tex[p.image] : null;
                mr.sharedMaterials = new Il2CppReferenceArray<Material>(new[] { MaterialFor(baseMat, tex, p.color, id) });
            }
            return root;
        }

        /// <summary>A character to show outside the match, with the game's idle animation.</summary>
        static readonly HashSet<string> _pvLogged = new();

        // ---------------------------------------------------------------- heavy work on another thread
        // Reading a big .glb and adapting its skeleton to the game's (Humanoid.Retarget) is pure computation (no
        // Unity): it is
        // done on another thread so the window or the match start don't freeze. On the game thread
        // stays what can only be done there (textures and meshes).
        static readonly System.Collections.Concurrent.ConcurrentDictionary<string, (string sig, Glb.Model model)> _parsed = new();
        static readonly System.Collections.Concurrent.ConcurrentDictionary<string, bool> _parsing = new();
        static readonly System.Collections.Concurrent.ConcurrentDictionary<string, (Glb.Model fit, string report)> _fits = new();
        static readonly System.Collections.Concurrent.ConcurrentDictionary<string, bool> _fitting = new();

        static string FileSigOf(string path)
        {
            try { var fi = new FileInfo(path); return fi.Exists ? fi.Length + ":" + fi.LastWriteTimeUtc.Ticks : null; } catch { return null; }
        }

        /// <summary>Starts reading a custom model on another thread (if it isn't already read or being
        /// read).</summary>
        internal static void Prefetch(string id)
        {
            if (string.IsNullOrEmpty(id)) return;
            string path = CustomPath(id), sig = FileSigOf(path);
            if (sig == null) return;
            if (_custom.TryGetValue(id, out var have) && have.sig == sig) return;
            if (_parsed.TryGetValue(id, out var p) && p.sig == sig) return;
            if (!_parsing.TryAdd(id, true)) return;
            System.Threading.Tasks.Task.Run(() =>
            {
                try
                {
                    var model = Glb.Read(File.ReadAllBytes(path));
                    var jobs = new System.Threading.Tasks.Task[model.images.Count];            // the textures too, here (at the same time)
                    for (int k = 0; k < jobs.Length; k++) { var img = model.images[k]; jobs[k] = System.Threading.Tasks.Task.Run(() => TexDec.Prepare(img)); }
                    System.Threading.Tasks.Task.WaitAll(jobs);
                    _parsed[id] = (sig, model);
                }
                catch { }
                finally { _parsing.TryRemove(id, out _); }
            });
        }

        /// <summary>Gets ready (bit by bit, and the heavy part on another thread) a custom model assembled over key:
        /// true once it
        /// can be assembled without waiting. Call it every frame until it returns true.</summary>
        internal static bool Prefit(string id, string key)
        {
            string path = CustomPath(id), sig = FileSigOf(path);
            if (sig == null) return true;                                        // not there: let it fail when assembling it
            if (!(_custom.TryGetValue(id, out var c) && c.sig == sig))
            {
                if (_parsed.TryGetValue(id, out var p) && p.sig == sig) { LoadCustom(id); return false; }   // textures: here
                Prefetch(id);
                return false;
            }
            if (c.fitted.ContainsKey(key)) return true;
            string fk = id + "|" + key + "|" + sig;
            if (_fits.TryRemove(fk, out var done))
            {
                c.fitted[key] = done.fit;
                if (done.fit != null) Plugin.L.LogInfo($"[Modelos] {id} en {key}: {done.report}");
                else Warn("fitc" + key + id, $"[Modelos] {id} en {key}: {done.report}");
                return true;
            }
            if (_fitting.ContainsKey(fk)) return false;
            var tpl = Template(key);
            if (tpl == null) return true;
            var root = ModelRoot(tpl) ?? tpl;
            var live = new HashSet<string>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true)) live.Add(t.name);
            var rest = RestPose(key, root, out var parents);
            int known = 0, named = 0;
            foreach (var jt in c.model.joints) if (jt.name != "<root>") { named++; if (live.Contains(jt.name) && rest.ContainsKey(jt.name)) known++; }
            if (!(named > 0 && known < named * 0.5f)) return true;                 // uses the game's skeleton: nothing to adapt
            var game = new Dictionary<string, Humanoid.GameBone>();
            foreach (var kv in rest)
                if (live.Contains(kv.Key))
                    game[kv.Key] = new Humanoid.GameBone { name = kv.Key, parent = parents.GetValueOrDefault(kv.Key), pos = new double[] { kv.Value.m03, kv.Value.m13, kv.Value.m23 } };
            var model = c.model;
            _fitting[fk] = true;
            System.Threading.Tasks.Task.Run(() =>
            {
                try { var f = Humanoid.Retarget(model, game, out var report); _fits[fk] = (f, report); }
                catch (Exception e) { _fits[fk] = (null, "no pude adaptarlo: " + e.Message); }
                finally { _fitting.TryRemove(fk, out _); }
            });
            return false;
        }
        internal static GameObject ModelRootOf(GameObject owner) => ModelRoot(owner);

        internal sealed class Preview
        {
            public GameObject holder;              // what moves / rotates / is destroyed
            public GameObject animGo;              // where the animation is applied (the Animator's)
            public AnimationClip idle;
            public Baked baked; public Transform[] bakedBones;
            public int appliedId;                  // custom model assembled over the game's (Late moves it)
        }

        // ---------------------------------------------------------------- recorded idle
        // The game characters' animations aren't loaded in the waiting room. In the match their
        // idle is recorded once (rotations and positions of each bone, by name, at 15 frames per second) in
        // csr_live/cache/idle_<character>.bin (only on this PC) and the view plays it back.
        internal sealed class Baked { public string[] bones; public float fps; public int frames; public float[] data; }
        static readonly Dictionary<string, Baked> _baked = new();
        internal static string IdlePath(string key) => Path.Combine(LiveMods.LiveDir, "cache", "idle_" + key + ".bin");

        static Baked LoadBaked(string key)
        {
            if (_baked.TryGetValue(key, out var have)) return have;
            Baked b = null;
            try
            {
                string path = IdlePath(key);
                if (File.Exists(path))
                {
                    using var r = new BinaryReader(File.OpenRead(path));
                    if (r.ReadInt32() == 0x43535231)                           // "CSR1"
                    {
                        b = new Baked();
                        int nb = r.ReadInt32();
                        b.bones = new string[nb];
                        for (int i = 0; i < nb; i++) b.bones[i] = r.ReadString();
                        b.fps = r.ReadSingle();
                        b.frames = r.ReadInt32();
                        b.data = new float[b.frames * nb * 7];
                        for (int i = 0; i < b.data.Length; i++) b.data[i] = r.ReadSingle();
                    }
                }
            }
            catch (Exception e) { Warn("bakedr" + key, "[Modelos] reposo grabado de " + key + ": " + e.Message); b = null; }
            if (b != null) _baked[key] = b;
            return b;
        }

        /// <summary>Records a match character's idle: the animation is put on its bones frame by
        /// frame, each bone is noted down and everything is left as it was (in the same instant: the player sees
        /// nothing).</summary>
        internal static bool BakeIdle(string key, GameObject animGo, AnimationClip clip, GameObject modelRoot)
        {
            try
            {
                var ts = new List<Transform>();
                foreach (var t in modelRoot.GetComponentsInChildren<Transform>(true)) if (t != modelRoot.transform) ts.Add(t);
                var keepR = new Quaternion[ts.Count]; var keepP = new Vector3[ts.Count];
                for (int i = 0; i < ts.Count; i++) { keepR[i] = ts[i].localRotation; keepP[i] = ts[i].localPosition; }
                const float fps = 15f;
                int frames = Math.Max(1, Math.Min(240, (int)Math.Round(clip.length * fps)));
                var data = new float[frames * ts.Count * 7];
                for (int f = 0; f < frames; f++)
                {
                    clip.SampleAnimation(animGo, f / fps);
                    for (int i = 0; i < ts.Count; i++)
                    {
                        var q = ts[i].localRotation; var v = ts[i].localPosition;
                        int o = (f * ts.Count + i) * 7;
                        data[o] = q.x; data[o + 1] = q.y; data[o + 2] = q.z; data[o + 3] = q.w; data[o + 4] = v.x; data[o + 5] = v.y; data[o + 6] = v.z;
                    }
                }
                for (int i = 0; i < ts.Count; i++) { ts[i].localRotation = keepR[i]; ts[i].localPosition = keepP[i]; }
                Directory.CreateDirectory(Path.GetDirectoryName(IdlePath(key)));
                using (var w = new BinaryWriter(File.Create(IdlePath(key))))
                {
                    w.Write(0x43535231);
                    w.Write(ts.Count);
                    foreach (var t in ts) w.Write(t.name);
                    w.Write(fps);
                    w.Write(frames);
                    foreach (var x in data) w.Write(x);
                }
                _baked.Remove(key);
                Plugin.L.LogInfo($"[Modelos] reposo de {key} grabado para el Selector ({clip.name}, {frames} fotogramas, {ts.Count} huesos)");
                return true;
            }
            catch (Exception e) { Warn("bake" + key, "[Modelos] no pude grabar el reposo de " + key + ": " + e.Message); return false; }
        }

        /// <summary>The idle animation among several (an Animator's); seen notes their names.</summary>
        internal static AnimationClip IdleClip(Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppReferenceArray<AnimationClip> clips, List<string> seen)
        {
            AnimationClip best = null; int bestScore = 0;
            if (clips == null) return null;
            for (int i = 0; i < clips.Length; i++)
            {
                var c = clips[i];
                if (c == null) continue;
                string n = c.name.ToLowerInvariant();
                if (seen.Count < 30) seen.Add(c.name);
                int sc = n.Contains("_nml_i_idl_lp") ? 5 : n.Contains("_nml_i_idl") ? 4 : n.Contains("_i_idl") ? 3 : n.Contains("idl") ? 2 : n.Contains("idle") ? 1 : 0;
                if (sc > bestScore) { bestScore = sc; best = c; }
            }
            return best;
        }

        /// <summary>A match character's idle animation (from its SimpleAnimation).</summary>
        internal static AnimationClip IdleClip(SimpleAnimation sa)
        {
            AnimationClip best = null; int bestScore = -1;
            void Look(AnimationClip c)
            {
                if (c == null) return;
                string n = c.name.ToLowerInvariant();
                int sc = n.Contains("_nml_i_idl_lp") ? 4 : n.Contains("_nml_i_idl") ? 3 : n.Contains("_i_idl") ? 2 : n.Contains("idl") ? 1 : -1;
                if (sc > bestScore) { bestScore = sc; best = c; }
            }
            try { var st = sa.m_States; if (st != null) for (int i = 0; i < st.Length; i++) Look(st[i]?.clip); } catch { }
            if (bestScore < 3)
                try
                {
                    var it = sa.GetStates().GetEnumerator();
                    var en = it.Cast<Il2CppSystem.Collections.IEnumerator>();
                    while (en.MoveNext()) Look(it.Current?.clip);
                }
                catch { }
            return bestScore >= 1 ? best : null;
        }

        /// <summary>The game character (baseKey: PawnTypeData_X / ThreatTypeData_Traitor) and, if model isn't null, a
        /// custom model assembled on top just like in the match (its bones follow the game's). Its scripts stay
        /// off; the idle animation is set with PreviewTick. null if the game doesn't have the model yet or the
        /// custom model can't be assembled.</summary>
        internal static Preview PreviewChar(string baseKey, string model, int layer)
        {
            GameObject tpl;
            try { tpl = Template(baseKey); } catch { tpl = null; }
            if (tpl == null) return null;
            var holder = new GameObject("CSR_Vista_" + baseKey + (model != null ? "_" + model : ""));
            holder.SetActive(false);                                   // that way the copy doesn't start its scripts
            try
            {
                var go = UnityEngine.Object.Instantiate(tpl, holder.transform, false);
                var pv = new Preview { holder = holder };
                // the idle animation: its controller's (ControllerMixerPlayable.controller, in the prefab itself)
                var cmp = go.GetComponentInChildren<ControllerMixerPlayable>(true);
                var ctrl = cmp != null ? cmp.controller : null;
                if (ctrl != null)
                {
                    var seen = new List<string>();
                    pv.idle = IdleClip(ctrl.animationClips, seen);
                    if (pv.idle != null) pv.animGo = cmp.gameObject;
                }
                var sa = pv.idle == null ? go.GetComponentInChildren<SimpleAnimation>(true) : null;
                if (sa != null)
                {
                    pv.animGo = sa.gameObject;
                    AnimationClip first = null;
                    try
                    {
                        var states = sa.m_States;
                        if (states != null)
                            for (int i = 0; i < states.Length; i++)
                            {
                                var es = states[i];
                                var c = es?.clip;
                                if (c == null) continue;
                                first ??= c;
                                if (pv.idle == null && c.name.ToLowerInvariant().Contains("_nml_i_idl")) pv.idle = c;
                            }
                    }
                    catch (Exception e) { Warn("pvidle" + baseKey, "[Modelos] vista: animaciones de " + baseKey + ": " + e.Message); }
                    pv.idle ??= sa.m_Clip ?? first;
                }
                pv.baked = LoadBaked(baseKey);                             // recorded in a match: takes precedence over the rest
                if (pv.baked == null && pv.idle == null)
                    foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<Animator>(), true))
                    {
                        var an = c.TryCast<Animator>();
                        var rac = an?.runtimeAnimatorController;
                        if (rac == null) continue;
                        foreach (var clip in rac.animationClips)
                            if (clip != null && clip.name.ToLowerInvariant().Contains("_i_idl")) { pv.idle = clip; pv.animGo = an.gameObject; break; }
                        if (pv.idle != null) break;
                    }
                if (pv.baked != null)
                {
                    var byName = new Dictionary<string, Transform>();
                    var mroot = ModelRoot(go) ?? go;
                    foreach (var t in mroot.GetComponentsInChildren<Transform>(true)) if (!byName.ContainsKey(t.name)) byName[t.name] = t;
                    pv.bakedBones = new Transform[pv.baked.bones.Length];
                    for (int i = 0; i < pv.bakedBones.Length; i++) byName.TryGetValue(pv.baked.bones[i], out pv.bakedBones[i]);
                }
                foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<MonoBehaviour>(), true))
                {
                    var mb = c.TryCast<MonoBehaviour>();
                    if (mb != null) mb.enabled = false;
                }
                foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<Animator>(), true))
                {
                    var an = c.TryCast<Animator>();
                    if (an != null) an.enabled = false;
                }
                if (model == null)
                {
                    // the traitor comes with everything hidden (the game shows it later): its meshes are shown
                    bool Shown(Renderer r)
                    {
                        if (!r.enabled) return false;
                        for (var t = r.transform; t != null && t != holder.transform; t = t.parent) if (!t.gameObject.activeSelf) return false;
                        return true;
                    }
                    int vis = 0;
                    foreach (var r in go.GetComponentsInChildren<Renderer>(true)) if (Shown(r)) vis++;
                    if (vis == 0)
                    {
                        var names = new List<string>();
                        foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                        {
                            if (r.TryCast<SkinnedMeshRenderer>() == null && r.TryCast<MeshRenderer>() == null) continue;
                            r.enabled = true;
                            for (var t = r.transform; t != null && t != holder.transform; t = t.parent) t.gameObject.SetActive(true);
                            var mat = r.sharedMaterial;
                            names.Add(r.name + " [" + (mat != null && mat.shader != null ? mat.shader.name : "sin material") + "]");
                        }
                        if (_pvLogged.Add("hidden" + baseKey)) Plugin.L.LogInfo($"[Modelos] vista de {baseKey}: estaba oculto, ensenadas: {string.Join(", ", names)}");
                    }
                }
                if (model != null)
                {
                    var root = ModelRoot(go) ?? go;
                    var ac = ApplyCustom(root, CustomPrefix + model, baseKey);
                    if (ac == null) { UnityEngine.Object.Destroy(holder); return null; }
                    pv.appliedId = root.GetInstanceID();
                    _applied[pv.appliedId] = ac;                           // Late: its bones copy the game's
                }
                foreach (var t in holder.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = layer;
                foreach (var smr in holder.GetComponentsInChildren<SkinnedMeshRenderer>(true)) smr.updateWhenOffscreen = true;
                holder.SetActive(true);
                PreviewTick(pv, 0f);
                if (_pvLogged.Add(baseKey + "|" + model))
                {
                    int all = 0, on = 0;
                    foreach (var r in holder.GetComponentsInChildren<Renderer>(true)) { all++; if (r.enabled && r.gameObject.activeInHierarchy) on++; }
                    Plugin.L.LogInfo($"[Modelos] vista de {model ?? baseKey}: {on}/{all} mallas a la vista, reposo {(pv.baked != null ? "grabado" : pv.idle != null ? pv.idle.name : "ninguno (se graba en la primera partida)")}");
                }
                return pv;
            }
            catch (Exception e)
            {
                Warn("pv" + baseKey + model, "[Modelos] vista de " + (model ?? baseKey) + ": " + e.Message);
                UnityEngine.Object.Destroy(holder);
                return null;
            }
        }

        internal static void PreviewTick(Preview pv, float t)
        {
            if (pv?.baked != null && pv.bakedBones != null)
            {
                var b = pv.baked;
                float ft = t * b.fps;
                int f0 = (int)Math.Floor(ft) % b.frames, f1 = (f0 + 1) % b.frames;
                float a = ft - (float)Math.Floor(ft);
                int nb = b.bones.Length;
                for (int i = 0; i < nb; i++)
                {
                    var tr = pv.bakedBones[i];
                    if (tr == null) continue;
                    int o0 = (f0 * nb + i) * 7, o1 = (f1 * nb + i) * 7;
                    var d = b.data;
                    tr.localRotation = Quaternion.Slerp(new Quaternion(d[o0], d[o0 + 1], d[o0 + 2], d[o0 + 3]), new Quaternion(d[o1], d[o1 + 1], d[o1 + 2], d[o1 + 3]), a);
                    tr.localPosition = Vector3.Lerp(new Vector3(d[o0 + 4], d[o0 + 5], d[o0 + 6]), new Vector3(d[o1 + 4], d[o1 + 5], d[o1 + 6]), a);
                }
                return;
            }
            if (pv?.idle == null || pv.animGo == null) return;
            try
            {
                float len = pv.idle.length;
                pv.idle.SampleAnimation(pv.animGo, len > 0f ? t % len : 0f);
            }
            catch (Exception e) { Warn("pvtick", "[Modelos] vista: " + e.Message); pv.idle = null; }
        }

        internal static void PreviewDestroy(Preview pv)
        {
            if (pv == null) return;
            if (pv.appliedId != 0) _applied.Remove(pv.appliedId);
            if (pv.holder != null) UnityEngine.Object.Destroy(pv.holder);
            pv.holder = null;
        }

        /// <summary>Copy of a character's original model (PawnTypeData_X / ThreatTypeData_Traitor) on the given
        /// layer,
        /// or null if the game hasn't loaded it yet. Its scripts stay off.</summary>
        internal static GameObject PreviewOriginal(string key, int layer)
        {
            GameObject tpl;
            try { tpl = Template(key); } catch { tpl = null; }
            if (tpl == null) return null;
            var holder = new GameObject("CSR_VistaOriginal_" + key);
            holder.SetActive(false);                                   // that way the copy doesn't start its scripts
            var go = UnityEngine.Object.Instantiate(tpl, holder.transform, false);
            foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<MonoBehaviour>(), true))
            {
                var mb = c.TryCast<MonoBehaviour>();
                if (mb != null) mb.enabled = false;
            }
            foreach (var c in go.GetComponentsInChildren(Il2CppType.Of<Animator>(), true))
            {
                var an = c.TryCast<Animator>();
                if (an != null) an.enabled = false;
            }
            foreach (var t in holder.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = layer;
            foreach (var smr in holder.GetComponentsInChildren<SkinnedMeshRenderer>(true)) smr.updateWhenOffscreen = true;
            holder.SetActive(true);
            return holder;
        }
    }
}
