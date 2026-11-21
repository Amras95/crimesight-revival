// CRIMESIGHT Revival - modelos 3D propios (.glb) en lugar de los personajes del juego, y el esqueleto de cada
// personaje para hacerlos.
//
// En models.json, un modelo propio va como "custom:<nombre>" y su archivo esta en csr_live/models/<nombre>.glb (lo
// copia el lanzador desde la carpeta de modelos del jugador). Se lee con Glb.Read y se pone en el personaje:
//   - Las mallas se enganchan a los huesos del personaje por el nombre (el esqueleto que se exporta abajo tiene
//     los nombres del juego). Un hueso que el juego no tiene se cambia por su padre mas cercano que si tenga.
//   - Las mallas se recolocan sobre el esqueleto del juego en reposo, hueso a hueso: da igual si en Blender se
//     movio la armadura, se exporto en centimetros o el modelo se hizo para otro personaje (se ajusta a sus
//     proporciones). Solo cuenta donde esta cada hueso, no hacia donde mira, porque Blender cambia los ejes de
//     los huesos al importarlos.
//   - Los materiales son copias del material del propio personaje (el sombreado del juego) con la textura de
//     color del .glb (o su color, si no tiene textura).
// El esqueleto (csr_live/skeletons/<personaje>.glb) se escribe solo, una vez, desde el modelo del juego que tiene el
// jugador: solo los huesos y una malla diminuta para que Blender lo abra como armadura. No lleva ni mallas ni
// texturas del juego.
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
        const string CustomPrefix = "custom:";

        class Custom
        {
            public string sig; public Glb.Model model; public Texture2D[] tex;
            public readonly Dictionary<string, Mesh[]> meshes = new();      // por personaje (sus proporciones)
            public readonly Dictionary<string, Glb.Model> fitted = new();   // adaptado a cada personaje (otro esqueleto) o null
        }

        static readonly Dictionary<string, Custom> _custom = new();
        static readonly HashSet<string> _customFailed = new();               // "id|firma" que no se pudieron leer

        static string CustomPath(string id) => Path.Combine(LiveMods.LiveDir, "models", id + ".glb");

        /// <summary>Firma del archivo de un modelo propio (tamano y fecha), para no reintentar uno que fallo.</summary>
        static string CustomSig(string target)
        {
            try { var fi = new FileInfo(CustomPath(target.Substring(CustomPrefix.Length))); return fi.Exists ? fi.Length + ":" + fi.LastWriteTimeUtc.Ticks : "-"; }
            catch { return "-"; }
        }

        static Custom LoadCustom(string id)
        {
            string path = CustomPath(id), sig;
            try { var fi = new FileInfo(path); if (!fi.Exists) { Warn("nofile" + id, "[Modelos] no esta " + path); return null; } sig = fi.Length + ":" + fi.LastWriteTimeUtc.Ticks; }
            catch (Exception e) { Warn("nofile" + id, "[Modelos] " + id + ": " + e.Message); return null; }
            if (_custom.TryGetValue(id, out var have) && have.sig == sig) return have;
            if (have != null)                                                   // el .glb cambio: fuera lo de antes
            {
                foreach (var ms in have.meshes.Values) foreach (var m in ms) if (m != null) UnityEngine.Object.Destroy(m);
                foreach (var t in have.tex) if (t != null) UnityEngine.Object.Destroy(t);
                _custom.Remove(id);
            }
            if (_customFailed.Contains(id + "|" + sig)) return null;
            try
            {
                var model = Glb.Read(File.ReadAllBytes(path));
                foreach (var n in model.notes) Plugin.L.LogWarning("[Modelos] " + id + ": " + n);
                if (model.parts.Count == 0) { _customFailed.Add(id + "|" + sig); return null; }
                var c = new Custom { sig = sig, model = model, tex = new Texture2D[model.images.Count] };
                for (int i = 0; i < model.images.Count; i++)
                {
                    var t = new Texture2D(2, 2, TextureFormat.RGBA32, true) { name = "csr_" + id + "_" + i, hideFlags = HideFlags.DontUnloadUnusedAsset };
                    if (ImageConversion.LoadImage(t, model.images[i].data, false)) { t.wrapMode = TextureWrapMode.Repeat; c.tex[i] = t; }
                    else Plugin.L.LogWarning($"[Modelos] {id}: no pude leer la textura {i} ({model.images[i].mime})");
                }
                int verts = 0; foreach (var p in model.parts) verts += p.pos.Length / 3;
                Plugin.L.LogInfo($"[Modelos] {id}.glb: {model.parts.Count} malla(s), {verts} vertices, {model.joints.Count} huesos, {model.images.Count} textura(s)");
                _custom[id] = c;
                return c;
            }
            catch (Exception e)
            {
                _customFailed.Add(id + "|" + sig);
                Plugin.L.LogWarning("[Modelos] no pude leer " + id + ".glb: " + e.Message);
                return null;
            }
        }

        /// <summary>Donde esta cada hueso del personaje en reposo, respecto a su modelo (del prefab del juego; si no
        /// se encuentra, la postura de ahora, que vale peor).</summary>
        static Dictionary<string, Matrix4x4> RestPose(string key, GameObject root, out Dictionary<string, string> parents)
        {
            var rest = new Dictionary<string, Matrix4x4>();
            parents = new Dictionary<string, string>();
            GameObject prefab = null;
            try { prefab = key.StartsWith("PawnTypeData_") || key.StartsWith("ThreatTypeData_") ? Template(key) : null; } catch { }
            var src = prefab != null ? (ModelRoot(prefab) ?? prefab) : root;      // el mismo nivel que el del personaje (c_hum_XX)
            if (prefab == null) Warn("rest" + key, "[Modelos] no encuentro el modelo original de " + key + ": se usa su postura de ahora");
            var toRoot = src.transform.worldToLocalMatrix;
            foreach (var t in src.GetComponentsInChildren<Transform>(true))
                if (!rest.ContainsKey(t.name))
                {
                    rest[t.name] = toRoot * t.localToWorldMatrix;
                    parents[t.name] = t == src.transform || t.parent == null ? null : t.parent.name;
                }
            return rest;
        }

        static Applied ApplyCustom(GameObject root, string target, string key)
        {
            string id = target.Substring(CustomPrefix.Length);
            var c = LoadCustom(id);
            if (c == null) return null;
            var model = c.model;

            var live = new Dictionary<string, Transform>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true)) if (!live.ContainsKey(t.name)) live[t.name] = t;
            var rest = RestPose(key, root, out var parents);

            // un modelo con otro esqueleto (Mixamo, VRChat, un FBX cualquiera...): se adapta al del juego
            int known = 0, named = 0;
            foreach (var jt in model.joints) if (jt.name != "<root>") { named++; if (live.ContainsKey(jt.name) && rest.ContainsKey(jt.name)) known++; }
            if (named > 0 && known < named * 0.5f)
            {
                if (!c.fitted.TryGetValue(key, out var fit))
                {
                    var game = new Dictionary<string, Humanoid.GameBone>();
                    foreach (var kv in rest)
                        if (live.ContainsKey(kv.Key))
                            game[kv.Key] = new Humanoid.GameBone { name = kv.Key, parent = parents.GetValueOrDefault(kv.Key), pos = new double[] { kv.Value.m03, kv.Value.m13, kv.Value.m23 } };
                    try { fit = Humanoid.Retarget(model, game, out var report); Plugin.L.LogInfo($"[Modelos] {id} en {key}: {report}"); }
                    catch (Exception e) { fit = null; Plugin.L.LogWarning($"[Modelos] {id} en {key}: no pude adaptarlo: {e}"); }
                    if (fit == null) Warn("fitc" + key + id, $"[Modelos] {id} no usa el esqueleto del juego ni lo reconozco como humanoide " +
                                          "(mira la linea de arriba); hazlo sobre uno de los esqueletos de la carpeta de modelos");
                    c.fitted[key] = fit;
                }
                if (fit == null) return null;
                model = fit;
            }

            // adaptado: su propio esqueleto, con sus medidas, que cada fotograma copia los giros del del juego (Late)
            Dictionary<string, (Transform t, Matrix4x4 bind)> proxy = null;
            List<Link> links = null;
            var proxyTops = new List<GameObject>();
            List<Shoulder> shoulders = null;
            if (model.proxy) proxy = BuildProxy(root, model, rest, live, proxyTops, out links, out shoulders);

            // huesos del .glb -> huesos del personaje (por nombre, o el padre mas cercano que exista)
            int nj = model.joints.Count;
            var bones = new Transform[nj];
            var bind = new Matrix4x4[nj];
            var pGame = new Vector3[nj];
            var pFile = new Vector3[nj];
            int exact = 0, real = 0;
            var pairs = new List<(Vector3 f, Vector3 g)>();
            for (int j = 0; j < nj; j++)
            {
                var jt = model.joints[j];
                string name = null;
                if (proxy != null && proxy.TryGetValue(jt.name, out var px))
                {
                    real++; exact++;
                    bones[j] = px.t; bind[j] = px.bind; pGame[j] = pFile[j] = V(jt.pos);
                    continue;
                }
                if (jt.name != "<root>")
                {
                    real++;
                    if (live.ContainsKey(jt.name) && rest.ContainsKey(jt.name)) { name = jt.name; exact++; }
                    else foreach (var an in jt.ancestors) if (live.ContainsKey(an) && rest.ContainsKey(an)) { name = an; break; }
                }
                if (name == null) { bones[j] = root.transform; bind[j] = Matrix4x4.identity; pGame[j] = Vector3.zero; pFile[j] = V(jt.pos); continue; }
                var r = rest[name];
                bones[j] = live[name];
                bind[j] = r.inverse;
                pGame[j] = new Vector3(r.m03, r.m13, r.m23);
                pFile[j] = name == jt.name ? V(jt.pos) : (model.nodePos.TryGetValue(name, out var np) ? V(np) : V(jt.pos));
                if (name == jt.name) pairs.Add((pFile[j], pGame[j]));
            }

            // escala: la del .glb respecto al juego (por si se exporto en centimetros)
            float s = 1f;
            if (pairs.Count >= 3)
            {
                Vector3 cf = Vector3.zero, cg = Vector3.zero;
                foreach (var (f, g) in pairs) { cf += f; cg += g; }
                cf /= pairs.Count; cg /= pairs.Count;
                double sf = 0, sg = 0;
                foreach (var (f, g) in pairs) { sf += (f - cf).sqrMagnitude; sg += (g - cg).sqrMagnitude; }
                if (sf > 1e-12) s = (float)Math.Sqrt(sg / sf);
            }
            var delta = new Vector3[nj];
            for (int j = 0; j < nj; j++) delta[j] = pGame[j] - s * pFile[j];

            // mallas para este personaje
            if (!c.meshes.TryGetValue(key, out var meshes))
            {
                meshes = new Mesh[model.parts.Count];
                for (int i = 0; i < model.parts.Count; i++) meshes[i] = BuildMesh(model.parts[i], s, delta, bind, id + "_" + key);
                c.meshes[key] = meshes;
            }

            var a = new Applied { root = root, target = target, links = links, shoulders = shoulders };
            a.created.AddRange(proxyTops);
            Material baseMat = null;
            int layer = root.layer;
            foreach (var smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (!Slot.IsMatch(smr.name.Replace("(Clone)", ""))) continue;          // sombras y demas: no se tocan
                a.saved.Add(new Saved { smr = smr, mesh = smr.sharedMesh, mats = ToArr(smr.sharedMaterials), bones = ToArr(smr.bones),
                                        rootBone = smr.rootBone, enabled = smr.enabled, offscreen = smr.updateWhenOffscreen });
                if (baseMat == null && smr.sharedMaterial != null) { baseMat = smr.sharedMaterial; layer = smr.gameObject.layer; }
            }
            var il2Bones = new Il2CppReferenceArray<Transform>(nj);
            for (int j = 0; j < nj; j++) il2Bones[j] = bones[j];
            Transform rootBone = null;
            for (int j = 0; j < nj && rootBone == null; j++) if (bones[j] != root.transform) rootBone = bones[j];

            for (int i = 0; i < model.parts.Count; i++)
            {
                if (meshes[i] == null) continue;
                var part = model.parts[i];
                var go = new GameObject("CSR_Modelo_" + part.name);
                go.transform.SetParent(root.transform, false);
                go.layer = layer;
                var smr = go.AddComponent<SkinnedMeshRenderer>();
                smr.sharedMesh = meshes[i];
                smr.bones = il2Bones;
                smr.rootBone = rootBone ?? root.transform;
                var tex = part.image >= 0 && part.image < c.tex.Length ? c.tex[part.image] : null;
                smr.sharedMaterials = new Il2CppReferenceArray<Material>(new[] { MaterialFor(baseMat, tex, part.color, id) });
                smr.updateWhenOffscreen = true;
                a.created.Add(go);
            }
            foreach (var sv in a.saved) sv.smr.enabled = false;
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
                if (r.name.StartsWith("mesh_") && r.enabled) { a.hidden.Add((r, r.enabled)); r.enabled = false; }

            Plugin.L.LogInfo($"[Modelos] {key} con {id}.glb ({exact} de {real} huesos, escala {s:0.###})");
            return a;
        }

        static Vector3 V(float[] p) => new Vector3(p[0], p[1], p[2]);

        /// <summary>Un hueso del esqueleto propio y el del juego del que copia: el giro siempre; la posicion, la raiz
        /// (tal cual) y la cadera (a la escala de sus piernas), para que ande, se agache y salte igual.</summary>
        internal class Link { public Transform own, game; public Vector3 ownRest, gameRest; public int mode; public float k; }

        /// <summary>Hombro del esqueleto propio: la clavicula acompana un poco el giro del brazo (como en una persona y en
        /// las animaciones de Mixamo). Si no, al bajar los brazos los hombros se quedan rectos, como en la T.</summary>
        internal class Shoulder { public Transform sh, ua; public Quaternion uaRest; public Vector3 dir; }
        const float ShoulderFollow = 0.3f;

        static Dictionary<string, (Transform, Matrix4x4)> BuildProxy(GameObject root, Glb.Model model, Dictionary<string, Matrix4x4> rest,
                                                                     Dictionary<string, Transform> live, List<GameObject> tops, out List<Link> links,
                                                                     out List<Shoulder> shoulders)
        {
            links = new List<Link>();
            shoulders = new List<Shoulder>();
            var outp = new Dictionary<string, (Transform, Matrix4x4)>();
            var world = new Dictionary<string, (Vector3 p, Quaternion r)>();          // reposo, respecto al modelo
            var order = new List<Glb.Joint>(model.joints);
            order.Sort((x, y) => x.ancestors.Count.CompareTo(y.ancestors.Count));
            float hipK = 1f;
            if (model.nodePos.TryGetValue("SKL_000_WAIST", out var hp) && rest.TryGetValue("SKL_000_WAIST", out var hr) && Math.Abs(hr.m13) > 1e-4f)
                hipK = hp[1] / hr.m13;
            foreach (var jt in order)
            {
                if (jt.name == "<root>" || outp.ContainsKey(jt.name)) continue;
                var go = new GameObject("CSR_" + jt.name);
                string par = jt.ancestors.Count > 0 && outp.ContainsKey(jt.ancestors[0]) ? jt.ancestors[0] : null;
                go.transform.SetParent(par != null ? outp[par].Item1 : root.transform, false);
                if (par == null) tops.Add(go);
                var P = V(jt.pos);
                var R = rest.TryGetValue(jt.name, out var rm) ? rm.rotation : Quaternion.identity;
                var (pp, pr) = par != null ? world[par] : (Vector3.zero, Quaternion.identity);
                var inv = Quaternion.Inverse(pr);
                go.transform.localPosition = inv * (P - pp);
                go.transform.localRotation = inv * R;
                world[jt.name] = (P, R);
                outp[jt.name] = (go.transform, Matrix4x4.TRS(P, R, Vector3.one).inverse);
                if (live.TryGetValue(jt.name, out var g))
                {
                    // donde esta el del juego en reposo, respecto a su padre (del prefab)
                    Vector3 gameRest = g.localPosition;
                    if (rm != default && jt.ancestors.Count > 0 && rest.TryGetValue(jt.ancestors[0], out var prm))
                        gameRest = Quaternion.Inverse(prm.rotation) * (new Vector3(rm.m03, rm.m13, rm.m23) - new Vector3(prm.m03, prm.m13, prm.m23));
                    else if (rm != default) gameRest = new Vector3(rm.m03, rm.m13, rm.m23);
                    links.Add(new Link { own = go.transform, game = g, ownRest = go.transform.localPosition, gameRest = gameRest,
                                         mode = par == null ? 2 : jt.name == "SKL_000_WAIST" ? 1 : 0, k = hipK });
                }
            }
            foreach (var (sh, ua, fa) in new[] { ("SKL_010_LSHLD", "SKL_011_LUARM", "SKL_012_LFARM"), ("SKL_020_RSHLD", "SKL_021_RUARM", "SKL_022_RFARM") })
                if (outp.TryGetValue(sh, out var s) && outp.TryGetValue(ua, out var u) && outp.TryGetValue(fa, out var f)
                    && f.Item1.parent == u.Item1 && u.Item1.parent == s.Item1 && f.Item1.localPosition.sqrMagnitude > 1e-6f)
                    shoulders.Add(new Shoulder { sh = s.Item1, ua = u.Item1, uaRest = u.Item1.localRotation, dir = f.Item1.localPosition });
            return outp;
        }

        /// <summary>Despues de las animaciones: los esqueletos propios copian la postura de los del juego.</summary>
        public static void Late()
        {
            LateLinks();
            LateAnims();
            LateShoulders();
        }

        static void LateShoulders()
        {
            foreach (var a in _applied.Values)
            {
                if (a.shoulders == null) continue;
                foreach (var s in a.shoulders)
                {
                    if (s.sh == null || s.ua == null) continue;
                    var uaWorld = s.ua.rotation;
                    var now = uaWorld * s.dir;                               // hacia donde apunta el brazo
                    var rest = s.sh.rotation * (s.uaRest * s.dir);           // hacia donde apuntaria en reposo
                    var swing = Quaternion.FromToRotation(rest, now);
                    s.sh.rotation = Quaternion.Slerp(Quaternion.identity, swing, ShoulderFollow) * s.sh.rotation;
                    s.ua.rotation = uaWorld;                                 // el brazo, igual que lo pone el juego
                }
            }
        }

        static void LateLinks()
        {
            foreach (var a in _applied.Values)
            {
                if (a.links == null) continue;
                foreach (var l in a.links)
                {
                    if (l.own == null || l.game == null) continue;
                    l.own.localRotation = l.game.localRotation;
                    if (l.mode == 2) l.own.localPosition = l.ownRest + (l.game.localPosition - l.gameRest);
                    else if (l.mode == 1) l.own.localPosition = l.ownRest + (l.game.localPosition - l.gameRest) * l.k;
                }
            }
        }

        static Mesh BuildMesh(Glb.Part p, float s, Vector3[] delta, Matrix4x4[] bind, string name)
        {
            int vc = p.pos.Length / 3;
            var verts = new Vector3[vc];
            var weights = new BoneWeight[vc];
            for (int v = 0; v < vc; v++)
            {
                var pos = new Vector3(p.pos[v * 3], p.pos[v * 3 + 1], p.pos[v * 3 + 2]) * s;
                int b0 = p.boneIdx[v * 4], b1 = p.boneIdx[v * 4 + 1], b2 = p.boneIdx[v * 4 + 2], b3 = p.boneIdx[v * 4 + 3];
                float w0 = p.boneW[v * 4], w1 = p.boneW[v * 4 + 1], w2 = p.boneW[v * 4 + 2], w3 = p.boneW[v * 4 + 3];
                pos += delta[b0] * w0 + delta[b1] * w1 + delta[b2] * w2 + delta[b3] * w3;       // a su sitio en el juego
                verts[v] = pos;
                weights[v] = new BoneWeight { boneIndex0 = b0, boneIndex1 = b1, boneIndex2 = b2, boneIndex3 = b3, weight0 = w0, weight1 = w1, weight2 = w2, weight3 = w3 };
            }
            var mesh = new Mesh { name = "csr_" + name + "_" + p.name, hideFlags = HideFlags.DontUnloadUnusedAsset };
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
            mesh.boneWeights = weights;
            mesh.bindposes = bind;
            if (p.nrm == null) mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }

        static readonly Dictionary<string, Material> _customMats = new();
        static Texture2D _flatNormal;

        /// <summary>Una copia del material del personaje (el sombreado del juego) con la textura o el color del .glb.</summary>
        static Material MaterialFor(Material baseMat, Texture2D tex, float[] color, string id)
        {
            string key = (baseMat != null ? baseMat.GetInstanceID().ToString() : "-") + "|" + (tex != null ? tex.GetInstanceID().ToString() : string.Join(",", color));
            if (_customMats.TryGetValue(key, out var have) && have != null) return have;
            Material m;
            if (baseMat != null) m = new Material(baseMat);
            else
            {
                var sh = Shader.Find("Universal Render Pipeline/Lit");
                m = sh != null ? new Material(sh) : new Material(Shader.Find("Sprites/Default"));
            }
            m.name = "csr_" + id;
            m.hideFlags = HideFlags.DontUnloadUnusedAsset;
            Texture t = tex != null ? tex : Solid(color);
            foreach (var prop in new[] { "_Tex2D_Color", "_BaseMap", "_MainTex" })
                if (m.HasProperty(prop)) m.SetTexture(prop, t);
            if (m.HasProperty("_Tex2D_Normal")) m.SetTexture("_Tex2D_Normal", FlatNormal());
            foreach (var prop in new[] { "_Tex2D_SpeRoughRim", "_Specluar_Color_Map" })
                if (m.HasProperty(prop)) m.SetTexture(prop, Texture2D.blackTexture);
            if (tex != null && (color[0] < 0.999f || color[1] < 0.999f || color[2] < 0.999f))
                foreach (var prop in new[] { "_BaseColor", "_Color" })
                    if (m.HasProperty(prop)) m.SetColor(prop, new Color(color[0], color[1], color[2], color[3]));
            _customMats[key] = m;
            return m;
        }

        static Texture2D Solid(float[] c)
        {
            var t = new Texture2D(2, 2, TextureFormat.RGBA32, false) { name = "csr_color", hideFlags = HideFlags.DontUnloadUnusedAsset };
            var px = new Color32[4];
            for (int i = 0; i < 4; i++) px[i] = new Color(c[0], c[1], c[2], c[3]);
            t.SetPixels32(px);
            t.Apply();
            return t;
        }

        static Texture2D FlatNormal()
        {
            if (_flatNormal != null) return _flatNormal;
            _flatNormal = new Texture2D(2, 2, TextureFormat.RGBA32, false, true) { name = "csr_normal", hideFlags = HideFlags.DontUnloadUnusedAsset };
            var px = new Color32[4];
            for (int i = 0; i < 4; i++) px[i] = new Color32(128, 128, 255, 255);
            _flatNormal.SetPixels32(px);
            _flatNormal.Apply();
            return _flatNormal;
        }

        // ------------------------------------------------------------ esqueletos para Blender
        const string SkeletonVersion = "1";
        static readonly (string key, string name)[] SkeletonOf =
        {
            ("PawnTypeData_A", "Agatha"), ("PawnTypeData_B", "Berkeley"), ("PawnTypeData_C", "Catherine"),
            ("PawnTypeData_D", "Dorothy"), ("PawnTypeData_E", "Ellery"), ("PawnTypeData_F", "Freeman"),
            ("ThreatTypeData_Survivor", "Victima"), ("ThreatTypeData_Traitor", "Traidor"),
        };
        static bool _skeletonsDone;
        static float _skeletonsNext;

        /// <summary>Escribe una vez el esqueleto de cada personaje en csr_live/skeletons (los que falten).</summary>
        static void ExportSkeletons()
        {
            if (_skeletonsDone || Time.unscaledTime < _skeletonsNext) return;
            _skeletonsNext = Time.unscaledTime + 10f;
            string dir = Path.Combine(LiveMods.LiveDir, "skeletons");
            string stamp = Path.Combine(dir, "version.txt");
            try
            {
                bool fresh = File.Exists(stamp) && File.ReadAllText(stamp).Trim() == SkeletonVersion;
                int missing = 0, written = 0;
                foreach (var (key, name) in SkeletonOf)
                {
                    string path = Path.Combine(dir, name + ".glb");
                    if (fresh && File.Exists(path)) continue;
                    GameObject prefab = null;
                    foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<PawnTypeData>()))
                    { var d = o.TryCast<PawnTypeData>(); if (d != null && d.name == key && d.modelPrefab != null) { prefab = d.modelPrefab; break; } }
                    if (prefab == null)
                        foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.Of<ThreatTypeData>()))
                        { var d = o.TryCast<ThreatTypeData>(); if (d != null && d.name == key && d.modelPrefab != null) { prefab = d.modelPrefab; break; } }
                    if (prefab == null) { missing++; continue; }
                    var model = ModelRoot(prefab) ?? prefab;
                    var bones = SkeletonBones(model);
                    if (bones.Count == 0) continue;
                    Directory.CreateDirectory(dir);
                    File.WriteAllBytes(path, Glb.WriteSkeleton(model.name.Replace("(Clone)", ""), bones));
                    written++;
                }
                if (missing == 0)
                {
                    Directory.CreateDirectory(dir);
                    File.WriteAllText(stamp, SkeletonVersion);
                    _skeletonsDone = true;
                }
                if (written > 0) Plugin.L.LogInfo($"[Modelos] esqueletos para Blender: {written} en {dir}" + (missing > 0 ? $" (faltan {missing}, cuando el juego los cargue)" : ""));
            }
            catch (Exception e) { Warn("skel", "[Modelos] esqueletos: " + e.Message); _skeletonsDone = true; }
        }

        /// <summary>Los huesos que usan las mallas del modelo (y sus padres), en orden de padres a hijos.</summary>
        static List<Glb.Bone> SkeletonBones(GameObject prefab)
        {
            var used = new HashSet<int>();
            var rootT = prefab.transform;
            foreach (var smr in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                foreach (var b in smr.bones)
                    for (var t = b; t != null && t != rootT; t = t.parent) used.Add(t.GetInstanceID());
            var list = new List<Glb.Bone>();
            var index = new Dictionary<int, int>();
            foreach (var t in prefab.GetComponentsInChildren<Transform>(true))
            {
                if (!used.Contains(t.GetInstanceID())) continue;
                int parent = t.parent != null && index.TryGetValue(t.parent.GetInstanceID(), out var pi) ? pi : -1;
                // si cuelga de algo que no es hueso (entre el modelo y el hueso), su postura se toma respecto al modelo
                var lp = t.localPosition; var lr = t.localRotation; var ls = t.localScale;
                if (parent < 0 && t.parent != rootT)
                {
                    var m = rootT.worldToLocalMatrix * t.localToWorldMatrix;
                    lp = new Vector3(m.m03, m.m13, m.m23);
                    lr = Quaternion.LookRotation(m.GetColumn(2), m.GetColumn(1));
                    ls = new Vector3(((Vector3)m.GetColumn(0)).magnitude, ((Vector3)m.GetColumn(1)).magnitude, ((Vector3)m.GetColumn(2)).magnitude);
                }
                index[t.GetInstanceID()] = list.Count;
                list.Add(new Glb.Bone { name = t.name, parent = parent, pos = new[] { lp.x, lp.y, lp.z }, rot = new[] { lr.x, lr.y, lr.z, lr.w }, scale = new[] { ls.x, ls.y, ls.z } });
            }
            return list;
        }
    }
}
