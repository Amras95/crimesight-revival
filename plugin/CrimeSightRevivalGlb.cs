// CRIMESIGHT Revival - reading and writing .glb models (binary glTF), with nothing from Unity.
//
// Read(): takes from a .glb what is needed to dress a game character: the meshes at rest (in the
// .glb's scene), their weights per bone, the bones (name, parents and where they are) and the textures. The move to
// the game's
// skeleton (which can be moved, at another scale or with other proportions) is done by CrimeSightRevivalModelsGlb.cs.
// Blender exports it as is
// ("glTF Binary"). What is passed to Unity's system (positions, normals, UV, triangles) is already converted:
// glTF is right-handed and Unity left-handed, so X changes sign, the triangles are flipped and the UVs' V is
// inverted.
// WriteSkeleton(): writes a character's skeleton (only the bones, with a minimal mesh so Blender
// imports it as an armature) so each person can build their model over it. It carries nothing of the game's model.
//
// The matrices are 4x4 column-major (like glTF): m[column * 4 + row].
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;

namespace CrimeSightRevival.Mods
{
    static class Glb
    {
        // ------------------------------------------------------------ what Read() returns
        public class Model
        {
            public readonly List<Part> parts = new();
            public readonly List<Joint> joints = new();        // every bone the meshes use
            public readonly List<Image> images = new();
            public readonly List<string> notes = new();        // notices for the log
            public readonly Dictionary<string, float[]> nodePos = new();   // position of each node in the scene (Unity)
            public bool proxy;          // adapted (Humanoid): goes with its own skeleton, with its measurements, which copies the game's rotations
            public readonly List<NodeInfo> nodes = new();      // every node (to animate): rest in glTF
            public readonly List<Anim> anims = new();
        }

        public class NodeInfo
        {
            public string name; public int parent = -1;
            public float[] t = { 0, 0, 0 }, r = { 0, 0, 0, 1 }, s = { 1, 1, 1 };   // local rest (glTF)
        }

        /// <summary>An animation: position (0), rotation (1) or scale (2) curves of the nodes.</summary>
        public class Anim
        {
            public string name; public float duration;
            public readonly List<Channel> channels = new();
        }

        public class Channel { public int node, path, interp; public float[] times, values; }   // interp: 0 linear, 1 step, 2 cubic

        public class Joint
        {
            public string name;                               // "<root>": the model itself (pieces without a bone)
            public readonly List<string> ancestors = new();   // names of its parents, from the closest to the farthest
            public float[] pos = { 0, 0, 0 };                 // where it is in the .glb's scene, at rest (Unity)
        }

        public class Part
        {
            public string name;
            public float[] pos, nrm, uv;                      // xyz, xyz, uv per vertex (Unity space)
            public int[] boneIdx;                             // 4 per vertex (indices of Model.joints)
            public float[] boneW;                             // 4 per vertex, they add up to 1
            public int[] tris;                                // already flipped for Unity
            public int image = -1;                            // colour texture (Model.images) or -1
            public float[] color = { 1, 1, 1, 1 };            // base colour (if there is no texture, or multiplied)
        }

        public class Image
        {
            public byte[] data; public string mime;
            // already decoded on another thread (TexDec): RGBA32 bottom to top with all its mipmaps, ready to upload
            public byte[] raw; public int rw, rh, rmips;
        }

        // ------------------------------------------------------------ matrices
        public static float[] Identity() => new float[] { 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1 };

        public static float[] Mul(float[] a, float[] b)
        {
            var r = new float[16];
            for (int c = 0; c < 4; c++)
                for (int rr = 0; rr < 4; rr++)
                {
                    float s = 0;
                    for (int k = 0; k < 4; k++) s += a[k * 4 + rr] * b[c * 4 + k];
                    r[c * 4 + rr] = s;
                }
            return r;
        }

        public static float[] Trs(float[] t, float[] q, float[] s)
        {
            float x = q[0], y = q[1], z = q[2], w = q[3];
            float xx = x * x, yy = y * y, zz = z * z, xy = x * y, xz = x * z, yz = y * z, wx = w * x, wy = w * y, wz = w * z;
            return new float[]
            {
                (1 - 2 * (yy + zz)) * s[0], (2 * (xy + wz)) * s[0], (2 * (xz - wy)) * s[0], 0,
                (2 * (xy - wz)) * s[1], (1 - 2 * (xx + zz)) * s[1], (2 * (yz + wx)) * s[1], 0,
                (2 * (xz + wy)) * s[2], (2 * (yz - wx)) * s[2], (1 - 2 * (xx + yy)) * s[2], 0,
                t[0], t[1], t[2], 1,
            };
        }

        public static float[] Inverse(float[] m)
        {
            var inv = new double[16];
            double[] a = new double[16];
            for (int i = 0; i < 16; i++) a[i] = m[i];
            inv[0] = a[5] * a[10] * a[15] - a[5] * a[11] * a[14] - a[9] * a[6] * a[15] + a[9] * a[7] * a[14] + a[13] * a[6] * a[11] - a[13] * a[7] * a[10];
            inv[4] = -a[4] * a[10] * a[15] + a[4] * a[11] * a[14] + a[8] * a[6] * a[15] - a[8] * a[7] * a[14] - a[12] * a[6] * a[11] + a[12] * a[7] * a[10];
            inv[8] = a[4] * a[9] * a[15] - a[4] * a[11] * a[13] - a[8] * a[5] * a[15] + a[8] * a[7] * a[13] + a[12] * a[5] * a[11] - a[12] * a[7] * a[9];
            inv[12] = -a[4] * a[9] * a[14] + a[4] * a[10] * a[13] + a[8] * a[5] * a[14] - a[8] * a[6] * a[13] - a[12] * a[5] * a[10] + a[12] * a[6] * a[9];
            inv[1] = -a[1] * a[10] * a[15] + a[1] * a[11] * a[14] + a[9] * a[2] * a[15] - a[9] * a[3] * a[14] - a[13] * a[2] * a[11] + a[13] * a[3] * a[10];
            inv[5] = a[0] * a[10] * a[15] - a[0] * a[11] * a[14] - a[8] * a[2] * a[15] + a[8] * a[3] * a[14] + a[12] * a[2] * a[11] - a[12] * a[3] * a[10];
            inv[9] = -a[0] * a[9] * a[15] + a[0] * a[11] * a[13] + a[8] * a[1] * a[15] - a[8] * a[3] * a[13] - a[12] * a[1] * a[11] + a[12] * a[3] * a[9];
            inv[13] = a[0] * a[9] * a[14] - a[0] * a[10] * a[13] - a[8] * a[1] * a[14] + a[8] * a[2] * a[13] + a[12] * a[1] * a[10] - a[12] * a[2] * a[9];
            inv[2] = a[1] * a[6] * a[15] - a[1] * a[7] * a[14] - a[5] * a[2] * a[15] + a[5] * a[3] * a[14] + a[13] * a[2] * a[7] - a[13] * a[3] * a[6];
            inv[6] = -a[0] * a[6] * a[15] + a[0] * a[7] * a[14] + a[4] * a[2] * a[15] - a[4] * a[3] * a[14] - a[12] * a[2] * a[7] + a[12] * a[3] * a[6];
            inv[10] = a[0] * a[5] * a[15] - a[0] * a[7] * a[13] - a[4] * a[1] * a[15] + a[4] * a[3] * a[13] + a[12] * a[1] * a[7] - a[12] * a[3] * a[5];
            inv[14] = -a[0] * a[5] * a[14] + a[0] * a[6] * a[13] + a[4] * a[1] * a[14] - a[4] * a[2] * a[13] - a[12] * a[1] * a[6] + a[12] * a[2] * a[5];
            inv[3] = -a[1] * a[6] * a[11] + a[1] * a[7] * a[10] + a[5] * a[2] * a[11] - a[5] * a[3] * a[10] - a[9] * a[2] * a[7] + a[9] * a[3] * a[6];
            inv[7] = a[0] * a[6] * a[11] - a[0] * a[7] * a[10] - a[4] * a[2] * a[11] + a[4] * a[3] * a[10] + a[8] * a[2] * a[7] - a[8] * a[3] * a[6];
            inv[11] = -a[0] * a[5] * a[11] + a[0] * a[7] * a[9] + a[4] * a[1] * a[11] - a[4] * a[3] * a[9] - a[8] * a[1] * a[7] + a[8] * a[3] * a[5];
            inv[15] = a[0] * a[5] * a[10] - a[0] * a[6] * a[9] - a[4] * a[1] * a[10] + a[4] * a[2] * a[9] + a[8] * a[1] * a[6] - a[8] * a[2] * a[5];
            double det = a[0] * inv[0] + a[1] * inv[4] + a[2] * inv[8] + a[3] * inv[12];
            var r = new float[16];
            if (Math.Abs(det) < 1e-12) return Identity();
            for (int i = 0; i < 16; i++) r[i] = (float)(inv[i] / det);
            return r;
        }

        static void Point(float[] m, float x, float y, float z, out float ox, out float oy, out float oz)
        {
            ox = m[0] * x + m[4] * y + m[8] * z + m[12];
            oy = m[1] * x + m[5] * y + m[9] * z + m[13];
            oz = m[2] * x + m[6] * y + m[10] * z + m[14];
        }

        static void Dir(float[] m, float x, float y, float z, out float ox, out float oy, out float oz)
        {
            ox = m[0] * x + m[4] * y + m[8] * z;
            oy = m[1] * x + m[5] * y + m[9] * z;
            oz = m[2] * x + m[6] * y + m[10] * z;
        }

        // ------------------------------------------------------------ reading
        class Node
        {
            public string name; public int parent = -1; public int mesh = -1, skin = -1;
            public float[] local = Identity(), global;
            public readonly List<int> children = new();
        }

        public static Model Read(byte[] file)
        {
            var (json, bin) = Chunks(file);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            var model = new Model();
            var g = new Reader(root, bin, model);

            // nodes and their position in the scene
            var nodes = new List<Node>();
            if (root.TryGetProperty("nodes", out var jn))
                foreach (var n in jn.EnumerateArray())
                {
                    var node = new Node { name = Str(n, "name") ?? "nodo" + nodes.Count };
                    if (n.TryGetProperty("mesh", out var m)) node.mesh = m.GetInt32();
                    if (n.TryGetProperty("skin", out var s)) node.skin = s.GetInt32();
                    if (n.TryGetProperty("matrix", out var mx)) node.local = Floats(mx, 16);
                    else
                        node.local = Trs(n.TryGetProperty("translation", out var t) ? Floats(t, 3) : new float[] { 0, 0, 0 },
                                         n.TryGetProperty("rotation", out var r) ? Floats(r, 4) : new float[] { 0, 0, 0, 1 },
                                         n.TryGetProperty("scale", out var sc) ? Floats(sc, 3) : new float[] { 1, 1, 1 });
                    if (n.TryGetProperty("children", out var ch)) foreach (var c in ch.EnumerateArray()) node.children.Add(c.GetInt32());
                    nodes.Add(node);
                }
            for (int i = 0; i < nodes.Count; i++) foreach (var c in nodes[i].children) if (c >= 0 && c < nodes.Count) nodes[c].parent = i;
            for (int i = 0; i < nodes.Count; i++) Global(nodes, i);
            foreach (var n in nodes)
            {
                var ni = new NodeInfo { name = n.name, parent = n.parent };
                Decompose(n.local, ni.t, ni.r, ni.s);
                model.nodes.Add(ni);
            }
            foreach (var n in nodes) model.nodePos[n.name] = new[] { -n.global[12], n.global[13], n.global[14] };

            // bones: the nodes of every skin
            var skins = new List<(int[] joints, float[][] ibm)>();
            var jointOf = new Dictionary<int, int>();                 // node -> index in model.joints
            if (root.TryGetProperty("skins", out var js))
                foreach (var s in js.EnumerateArray())
                {
                    var j = new List<int>();
                    foreach (var x in s.GetProperty("joints").EnumerateArray()) j.Add(x.GetInt32());
                    float[][] ibm = new float[j.Count][];
                    if (s.TryGetProperty("inverseBindMatrices", out var ib))
                    {
                        var f = g.Accessor(ib.GetInt32(), out int comps);
                        for (int k = 0; k < j.Count; k++) { ibm[k] = new float[16]; Array.Copy(f, k * 16, ibm[k], 0, 16); }
                    }
                    else for (int k = 0; k < j.Count; k++) ibm[k] = Identity();
                    foreach (var nodeIdx in j) JointIndex(model, nodes, jointOf, nodeIdx);
                    skins.Add((j.ToArray(), ibm));
                }

            // meshes
            for (int ni = 0; ni < nodes.Count; ni++)
            {
                var node = nodes[ni];
                if (node.mesh < 0) continue;
                var mesh = root.GetProperty("meshes")[node.mesh];
                string meshName = Str(mesh, "name") ?? node.name;
                int pi = 0;
                foreach (var prim in mesh.GetProperty("primitives").EnumerateArray())
                {
                    int mode = prim.TryGetProperty("mode", out var md) ? md.GetInt32() : 4;
                    if (mode != 4) { model.notes.Add($"{meshName}: solo se leen triangulos (modo {mode})"); continue; }
                    var part = g.Primitive(prim, meshName + (pi > 0 ? "_" + pi : ""), out var joints0, out var weights0, out var joints1, out var weights1);
                    pi++;
                    if (part == null) continue;
                    int vc = part.pos.Length / 3;
                    float[] bind;                                     // from the mesh to the scene, at rest
                    int[] map;                                        // skin bone -> model bone
                    if (node.skin >= 0 && node.skin < skins.Count && joints0 != null)
                    {
                        var (sj, ibm) = skins[node.skin];
                        bind = Mul(nodes[sj[0]].global, ibm[0]);
                        map = new int[sj.Length];
                        for (int k = 0; k < sj.Length; k++) map[k] = jointOf[sj[k]];
                    }
                    else
                    {
                        // rigid piece (glasses, hat...): stuck to the nearest bone above, or to the model
                        bind = node.global;
                        int anc = node.parent; while (anc >= 0 && !jointOf.ContainsKey(anc)) anc = nodes[anc].parent;
                        int j = anc >= 0 ? jointOf[anc] : RootJoint(model);
                        joints0 = new int[vc * 4]; weights0 = new float[vc * 4];
                        for (int v = 0; v < vc; v++) { joints0[v * 4] = 0; weights0[v * 4] = 1; }
                        joints1 = null; weights1 = null;
                        map = new[] { j };
                    }
                    Bake(part, bind, joints0, weights0, joints1, weights1, map);
                    model.parts.Add(part);
                }
            }
            // animations
            if (root.TryGetProperty("animations", out var jan))
                foreach (var an in jan.EnumerateArray())
                {
                    var anim = new Anim { name = Str(an, "name") ?? "anim" + model.anims.Count };
                    var samplers = an.GetProperty("samplers");
                    foreach (var ch in an.GetProperty("channels").EnumerateArray())
                    {
                        var tg = ch.GetProperty("target");
                        if (!tg.TryGetProperty("node", out var tn)) continue;
                        string path = Str(tg, "path");
                        int pth = path == "translation" ? 0 : path == "rotation" ? 1 : path == "scale" ? 2 : -1;
                        if (pth < 0) continue;
                        var sm = samplers[ch.GetProperty("sampler").GetInt32()];
                        var times = g.Accessor(sm.GetProperty("input").GetInt32(), out _);
                        var vals = g.Accessor(sm.GetProperty("output").GetInt32(), out _);
                        string ip = Str(sm, "interpolation") ?? "LINEAR";
                        var c = new Channel { node = tn.GetInt32(), path = pth, times = times, interp = ip == "STEP" ? 1 : ip == "CUBICSPLINE" ? 2 : 0 };
                        int w = pth == 1 ? 4 : 3;
                        if (c.interp == 2)                      // cubic: [in, value, out] per key -> only the value
                        {
                            c.values = new float[times.Length * w];
                            for (int k = 0; k < times.Length && (k * 3 + 2) * w <= vals.Length; k++) Array.Copy(vals, (k * 3 + 1) * w, c.values, k * w, w);
                            c.interp = 0;
                        }
                        else c.values = vals;
                        if (times.Length > 0) anim.duration = Math.Max(anim.duration, times[times.Length - 1]);
                        anim.channels.Add(c);
                    }
                    if (anim.channels.Count > 0) model.anims.Add(anim);
                }
            if (model.parts.Count == 0 && model.anims.Count == 0) model.notes.Add("no hay mallas");
            return model;
        }

        // ------------------------------------------------------------ poses of an animation
        /// <summary>Each node's matrix in the scene (glTF) at instant t of the animation (without an animation:
        /// rest).</summary>
        public static float[][] Pose(Model m, Anim a, float time)
        {
            int n = m.nodes.Count;
            var T = new float[n][]; var R = new float[n][]; var S = new float[n][];
            for (int i = 0; i < n; i++) { T[i] = (float[])m.nodes[i].t.Clone(); R[i] = (float[])m.nodes[i].r.Clone(); S[i] = (float[])m.nodes[i].s.Clone(); }
            if (a != null)
                foreach (var c in a.channels)
                {
                    if (c.node < 0 || c.node >= n || c.times.Length == 0) continue;
                    var dst = c.path == 0 ? T[c.node] : c.path == 1 ? R[c.node] : S[c.node];
                    Sample(c, time, dst);
                }
            var glob = new float[n][];
            float[] G(int i)
            {
                if (glob[i] != null) return glob[i];
                glob[i] = Identity();
                var l = Trs(T[i], R[i], S[i]);
                int p = m.nodes[i].parent;
                return glob[i] = p >= 0 && p < n ? Mul(G(p), l) : l;
            }
            for (int i = 0; i < n; i++) G(i);
            return glob;
        }

        static void Sample(Channel c, float t, float[] dst)
        {
            int w = c.path == 1 ? 4 : 3;
            var tm = c.times;
            if (t <= tm[0] || tm.Length == 1) { Array.Copy(c.values, 0, dst, 0, w); return; }
            if (t >= tm[tm.Length - 1]) { Array.Copy(c.values, (tm.Length - 1) * w, dst, 0, w); return; }
            int lo = 0, hi = tm.Length - 1;
            while (hi - lo > 1) { int mid = (lo + hi) / 2; if (tm[mid] <= t) lo = mid; else hi = mid; }
            float f = c.interp == 1 ? 0 : (t - tm[lo]) / Math.Max(tm[hi] - tm[lo], 1e-6f);
            if (c.path == 1)
            {
                float dot = 0;
                for (int k = 0; k < 4; k++) dot += c.values[lo * 4 + k] * c.values[hi * 4 + k];
                float sg = dot < 0 ? -1 : 1, len = 0;
                for (int k = 0; k < 4; k++) { dst[k] = c.values[lo * 4 + k] * (1 - f) + sg * c.values[hi * 4 + k] * f; len += dst[k] * dst[k]; }
                len = (float)Math.Sqrt(len); if (len > 1e-8f) for (int k = 0; k < 4; k++) dst[k] /= len;
            }
            else for (int k = 0; k < w; k++) dst[k] = c.values[lo * w + k] * (1 - f) + c.values[hi * w + k] * f;
        }

        /// <summary>Position, rotation (x y z w) and scale of a matrix.</summary>
        public static void Decompose(float[] m, float[] t, float[] q, float[] s)
        {
            t[0] = m[12]; t[1] = m[13]; t[2] = m[14];
            float sx = (float)Math.Sqrt(m[0] * m[0] + m[1] * m[1] + m[2] * m[2]);
            float sy = (float)Math.Sqrt(m[4] * m[4] + m[5] * m[5] + m[6] * m[6]);
            float sz = (float)Math.Sqrt(m[8] * m[8] + m[9] * m[9] + m[10] * m[10]);
            float det = m[0] * (m[5] * m[10] - m[9] * m[6]) - m[4] * (m[1] * m[10] - m[9] * m[2]) + m[8] * (m[1] * m[6] - m[5] * m[2]);
            if (det < 0) sx = -sx;
            s[0] = sx; s[1] = sy; s[2] = sz;
            if (Math.Abs(sx) < 1e-9f || sy < 1e-9f || sz < 1e-9f) { q[0] = q[1] = q[2] = 0; q[3] = 1; return; }
            Quat(m[0] / sx, m[1] / sx, m[2] / sx, m[4] / sy, m[5] / sy, m[6] / sy, m[8] / sz, m[9] / sz, m[10] / sz, q);
        }

        /// <summary>Quaternion of a rotation matrix given by columns (c0 = column 0...).</summary>
        public static void Quat(float c0x, float c0y, float c0z, float c1x, float c1y, float c1z, float c2x, float c2y, float c2z, float[] q)
        {
            float tr = c0x + c1y + c2z;
            if (tr > 0) { float s = (float)Math.Sqrt(tr + 1) * 2; q[3] = 0.25f * s; q[0] = (c1z - c2y) / s; q[1] = (c2x - c0z) / s; q[2] = (c0y - c1x) / s; }
            else if (c0x > c1y && c0x > c2z) { float s = (float)Math.Sqrt(1 + c0x - c1y - c2z) * 2; q[3] = (c1z - c2y) / s; q[0] = 0.25f * s; q[1] = (c1x + c0y) / s; q[2] = (c2x + c0z) / s; }
            else if (c1y > c2z) { float s = (float)Math.Sqrt(1 + c1y - c0x - c2z) * 2; q[3] = (c2x - c0z) / s; q[0] = (c1x + c0y) / s; q[1] = 0.25f * s; q[2] = (c2y + c1z) / s; }
            else { float s = (float)Math.Sqrt(1 + c2z - c0x - c1y) * 2; q[3] = (c0y - c1x) / s; q[0] = (c2x + c0z) / s; q[1] = (c2y + c1z) / s; q[2] = 0.25f * s; }
        }

        static int RootJoint(Model m)
        {
            int i = m.joints.FindIndex(j => j.name == "<root>");
            if (i >= 0) return i;
            m.joints.Add(new Joint { name = "<root>" });
            return m.joints.Count - 1;
        }

        static int JointIndex(Model model, List<Node> nodes, Dictionary<int, int> jointOf, int nodeIdx)
        {
            if (jointOf.TryGetValue(nodeIdx, out var j)) return j;
            var gm = nodes[nodeIdx].global;
            var joint = new Joint { name = nodes[nodeIdx].name, pos = new[] { -gm[12], gm[13], gm[14] } };
            for (int p = nodes[nodeIdx].parent; p >= 0; p = nodes[p].parent) joint.ancestors.Add(nodes[p].name);
            model.joints.Add(joint);
            jointOf[nodeIdx] = model.joints.Count - 1;
            return model.joints.Count - 1;
        }

        static float[] Global(List<Node> nodes, int i)
        {
            var n = nodes[i];
            if (n.global != null) return n.global;
            n.global = Identity();                                        // in case there is a cycle
            n.global = n.parent >= 0 ? Mul(Global(nodes, n.parent), n.local) : n.local;
            return n.global;
        }

        /// <summary>Moves the piece to the scene (rest position), to Unity space, and leaves 4 bones per
        /// vertex.</summary>
        static void Bake(Part p, float[] bind, int[] j0, float[] w0, int[] j1, float[] w1, int[] map)
        {
            int vc = p.pos.Length / 3;
            var nrmM = Transpose(Inverse(bind));
            for (int v = 0; v < vc; v++)
            {
                Point(bind, p.pos[v * 3], p.pos[v * 3 + 1], p.pos[v * 3 + 2], out var x, out var y, out var z);
                p.pos[v * 3] = -x; p.pos[v * 3 + 1] = y; p.pos[v * 3 + 2] = z;
                if (p.nrm != null)
                {
                    Dir(nrmM, p.nrm[v * 3], p.nrm[v * 3 + 1], p.nrm[v * 3 + 2], out x, out y, out z);
                    float l = (float)Math.Sqrt(x * x + y * y + z * z); if (l > 1e-8f) { x /= l; y /= l; z /= l; }
                    p.nrm[v * 3] = -x; p.nrm[v * 3 + 1] = y; p.nrm[v * 3 + 2] = z;
                }
                if (p.uv != null) p.uv[v * 2 + 1] = 1f - p.uv[v * 2 + 1];
            }
            // weights: the 4 biggest of the two sets, normalised
            p.boneIdx = new int[vc * 4]; p.boneW = new float[vc * 4];
            var cand = new List<(int j, float w)>(8);
            for (int v = 0; v < vc; v++)
            {
                cand.Clear();
                for (int k = 0; k < 4; k++)
                {
                    if (j0 != null && w0[v * 4 + k] > 0) cand.Add((Map(map, j0[v * 4 + k]), w0[v * 4 + k]));
                    if (j1 != null && w1[v * 4 + k] > 0) cand.Add((Map(map, j1[v * 4 + k]), w1[v * 4 + k]));
                }
                cand.Sort((a, b) => b.w.CompareTo(a.w));
                float sum = 0; for (int k = 0; k < cand.Count && k < 4; k++) sum += cand[k].w;
                for (int k = 0; k < 4; k++)
                {
                    if (k < cand.Count && sum > 0) { p.boneIdx[v * 4 + k] = cand[k].j; p.boneW[v * 4 + k] = cand[k].w / sum; }
                    else { p.boneIdx[v * 4 + k] = k < cand.Count ? cand[k].j : (cand.Count > 0 ? cand[0].j : map[0]); p.boneW[v * 4 + k] = sum > 0 ? 0 : (k == 0 ? 1 : 0); }
                }
            }
            // triangles flipped (because of the handedness change)
            for (int t = 0; t + 2 < p.tris.Length; t += 3) { int a = p.tris[t + 1]; p.tris[t + 1] = p.tris[t + 2]; p.tris[t + 2] = a; }
        }

        static int Map(int[] map, int j) => j >= 0 && j < map.Length ? map[j] : map[0];

        static float[] Transpose(float[] m)
        {
            var r = new float[16];
            for (int c = 0; c < 4; c++) for (int rr = 0; rr < 4; rr++) r[c * 4 + rr] = m[rr * 4 + c];
            return r;
        }

        class Reader
        {
            readonly JsonElement root; readonly byte[] bin; readonly Model model;
            readonly Dictionary<int, int> imageOfTexture = new();
            public Reader(JsonElement root, byte[] bin, Model model) { this.root = root; this.bin = bin; this.model = model; }

            public Part Primitive(JsonElement prim, string name, out int[] j0, out float[] w0, out int[] j1, out float[] w1)
            {
                j0 = j1 = null; w0 = w1 = null;
                var at = prim.GetProperty("attributes");
                if (!at.TryGetProperty("POSITION", out var pa)) return null;
                var part = new Part { name = name };
                part.pos = Accessor(pa.GetInt32(), out _);
                int vc = part.pos.Length / 3;
                if (at.TryGetProperty("NORMAL", out var na)) part.nrm = Accessor(na.GetInt32(), out _);
                if (at.TryGetProperty("TEXCOORD_0", out var ta)) part.uv = Accessor(ta.GetInt32(), out _);
                if (at.TryGetProperty("JOINTS_0", out var ja)) j0 = Ints(ja.GetInt32());
                if (at.TryGetProperty("WEIGHTS_0", out var wa)) w0 = Accessor(wa.GetInt32(), out _);
                if (at.TryGetProperty("JOINTS_1", out var ja1)) j1 = Ints(ja1.GetInt32());
                if (at.TryGetProperty("WEIGHTS_1", out var wa1)) w1 = Accessor(wa1.GetInt32(), out _);
                if (j0 != null && w0 == null) { j0 = null; }
                if (j1 != null && w1 == null) { j1 = null; }
                if (prim.TryGetProperty("indices", out var ia)) part.tris = Ints(ia.GetInt32());
                else { part.tris = new int[vc]; for (int i = 0; i < vc; i++) part.tris[i] = i; }
                if (prim.TryGetProperty("material", out var mi)) Material(part, mi.GetInt32());
                return part;
            }

            void Material(Part part, int index)
            {
                if (!root.TryGetProperty("materials", out var mats) || index < 0 || index >= mats.GetArrayLength()) return;
                var m = mats[index];
                if (!m.TryGetProperty("pbrMetallicRoughness", out var pbr)) return;
                if (pbr.TryGetProperty("baseColorFactor", out var f)) part.color = Floats(f, 4);
                if (pbr.TryGetProperty("baseColorTexture", out var bt) && bt.TryGetProperty("index", out var ti))
                    part.image = Texture(ti.GetInt32());
            }

            int Texture(int tex)
            {
                if (imageOfTexture.TryGetValue(tex, out var have)) return have;
                int result = -1;
                try
                {
                    var t = root.GetProperty("textures")[tex];
                    if (t.TryGetProperty("source", out var src))
                    {
                        var img = root.GetProperty("images")[src.GetInt32()];
                        byte[] data = null;
                        string mime = Str(img, "mimeType") ?? "";
                        if (img.TryGetProperty("bufferView", out var bv)) data = View(bv.GetInt32());
                        else if (Str(img, "uri") is string uri && uri.StartsWith("data:"))
                        {
                            int comma = uri.IndexOf(',');
                            mime = uri.Substring(5, Math.Max(0, uri.IndexOf(';') - 5));
                            data = Convert.FromBase64String(uri.Substring(comma + 1));
                        }
                        else model.notes.Add("una textura esta fuera del .glb: exporta como glTF Binary con las texturas dentro");
                        if (data != null) { model.images.Add(new Image { data = data, mime = mime }); result = model.images.Count - 1; }
                    }
                }
                catch (Exception e) { model.notes.Add("textura: " + e.Message); }
                imageOfTexture[tex] = result;
                return result;
            }

            byte[] View(int view)
            {
                var v = root.GetProperty("bufferViews")[view];
                int off = v.TryGetProperty("byteOffset", out var o) ? o.GetInt32() : 0;
                int len = v.GetProperty("byteLength").GetInt32();
                var r = new byte[len];
                Buffer.BlockCopy(bin, off, r, 0, len);
                return r;
            }

            public int[] Ints(int acc)
            {
                var f = Accessor(acc, out _);
                var r = new int[f.Length];
                for (int i = 0; i < f.Length; i++) r[i] = (int)Math.Round(f[i]);
                return r;
            }

            /// <summary>An accessor as floats (normalised ones, already between 0 and 1).</summary>
            public float[] Accessor(int index, out int comps)
            {
                var a = root.GetProperty("accessors")[index];
                int count = a.GetProperty("count").GetInt32();
                string type = a.GetProperty("type").GetString();
                comps = type switch { "SCALAR" => 1, "VEC2" => 2, "VEC3" => 3, "VEC4" => 4, "MAT2" => 4, "MAT3" => 9, "MAT4" => 16, _ => 1 };
                int ct = a.GetProperty("componentType").GetInt32();
                bool norm = a.TryGetProperty("normalized", out var nn) && nn.GetBoolean();
                var r = new float[count * comps];
                if (!a.TryGetProperty("bufferView", out var bvp)) return r;   // all zeros (sparse isn't read)
                var v = root.GetProperty("bufferViews")[bvp.GetInt32()];
                int size = ct switch { 5120 => 1, 5121 => 1, 5122 => 2, 5123 => 2, 5125 => 4, 5126 => 4, _ => 4 };
                int baseOff = (v.TryGetProperty("byteOffset", out var vo) ? vo.GetInt32() : 0) + (a.TryGetProperty("byteOffset", out var ao) ? ao.GetInt32() : 0);
                int stride = v.TryGetProperty("byteStride", out var st) ? st.GetInt32() : size * comps;
                for (int i = 0; i < count; i++)
                    for (int c = 0; c < comps; c++)
                    {
                        int p = baseOff + i * stride + c * size;
                        float val = ct switch
                        {
                            5126 => BitConverter.ToSingle(bin, p),
                            5121 => norm ? bin[p] / 255f : bin[p],
                            5120 => norm ? Math.Max((sbyte)bin[p] / 127f, -1f) : (sbyte)bin[p],
                            5123 => norm ? BitConverter.ToUInt16(bin, p) / 65535f : BitConverter.ToUInt16(bin, p),
                            5122 => norm ? Math.Max(BitConverter.ToInt16(bin, p) / 32767f, -1f) : BitConverter.ToInt16(bin, p),
                            5125 => BitConverter.ToUInt32(bin, p),
                            _ => 0,
                        };
                        r[i * comps + c] = val;
                    }
                return r;
            }
        }

        static (string json, byte[] bin) Chunks(byte[] f)
        {
            if (f.Length < 20 || BitConverter.ToUInt32(f, 0) != 0x46546C67) throw new InvalidDataException("no es un .glb (glTF binario)");
            string json = null; byte[] bin = Array.Empty<byte>();
            int p = 12;
            while (p + 8 <= f.Length)
            {
                int len = BitConverter.ToInt32(f, p); uint type = BitConverter.ToUInt32(f, p + 4);
                if (type == 0x4E4F534A) json = Encoding.UTF8.GetString(f, p + 8, len);
                else if (type == 0x004E4942) { bin = new byte[len]; Buffer.BlockCopy(f, p + 8, bin, 0, len); }
                p += 8 + len;
            }
            if (json == null) throw new InvalidDataException("el .glb no tiene JSON");
            return (json, bin);
        }

        static string Str(JsonElement e, string k) => e.TryGetProperty(k, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;

        static float[] Floats(JsonElement a, int n)
        {
            var r = new float[n]; int i = 0;
            foreach (var x in a.EnumerateArray()) { if (i < n) r[i++] = (float)x.GetDouble(); }
            return r;
        }

        // ------------------------------------------------------------ writing the skeleton
        public class Bone
        {
            public string name; public int parent = -1;        // index in the list (-1: hangs from the model)
            public float[] pos, rot, scale;                    // local, in Unity (rot: x y z w)
        }

        /// <summary>The skeleton as .glb: a root node (the model), the bones with their rest pose and a minimal
        /// mesh stuck to the first bone (Blender needs a skinned mesh to create the armature).</summary>
        public static byte[] WriteSkeleton(string rootName, List<Bone> bones)
        {
            // positions in glTF (X changes sign; the rotation, Y and Z)
            var local = new float[bones.Count][];
            var nodesJson = new StringBuilder();
            var rootChildren = new List<int>();
            var children = new List<int>[bones.Count];
            for (int i = 0; i < bones.Count; i++) children[i] = new List<int>();
            for (int i = 0; i < bones.Count; i++) { if (bones[i].parent >= 0) children[bones[i].parent].Add(i + 1); else rootChildren.Add(i + 1); }

            var global = new float[bones.Count][];
            for (int i = 0; i < bones.Count; i++)
            {
                var b = bones[i];
                var t = new[] { -b.pos[0], b.pos[1], b.pos[2] };
                var q = new[] { b.rot[0], -b.rot[1], -b.rot[2], b.rot[3] };
                local[i] = Trs(t, q, b.scale);
                global[i] = b.parent >= 0 ? Mul(global[b.parent], local[i]) : local[i];
            }

            var bin = new MemoryStream();
            void Align() { while (bin.Length % 4 != 0) bin.WriteByte(0); }
            // minimal mesh: a tiny triangle on the first bone
            float[] tri = new float[9];
            Point(global[0], 0, 0, 0, out tri[0], out tri[1], out tri[2]);
            tri[3] = tri[0] + 0.001f; tri[4] = tri[1]; tri[5] = tri[2];
            tri[6] = tri[0]; tri[7] = tri[1] + 0.001f; tri[8] = tri[2];
            int posOff = (int)bin.Length; foreach (var v in tri) bin.Write(BitConverter.GetBytes(v), 0, 4);
            int jOff = (int)bin.Length; for (int k = 0; k < 3; k++) { bin.Write(new byte[] { 0, 0, 0, 0 }, 0, 4); }
            int wOff = (int)bin.Length; for (int k = 0; k < 3; k++) foreach (var w in new float[] { 1, 0, 0, 0 }) bin.Write(BitConverter.GetBytes(w), 0, 4);
            Align();
            int ibmOff = (int)bin.Length;
            foreach (var m in global) foreach (var v in Inverse(m)) bin.Write(BitConverter.GetBytes(v), 0, 4);
            int binLen = (int)bin.Length;

            var sb = new StringBuilder();
            string F(float v) => v.ToString("R", System.Globalization.CultureInfo.InvariantCulture);
            string Arr(float[] a) { var p = new string[a.Length]; for (int i = 0; i < a.Length; i++) p[i] = F(a[i]); return "[" + string.Join(",", p) + "]"; }
            string J(string s) => JsonSerializer.Serialize(s);
            sb.Append("{\"asset\":{\"version\":\"2.0\",\"generator\":\"CRIMESIGHT Revival\"},\"scene\":0,");
            sb.Append("\"scenes\":[{\"nodes\":[0," + (bones.Count + 1) + "]}],\"nodes\":[");
            sb.Append("{\"name\":" + J(rootName) + ",\"children\":[" + string.Join(",", rootChildren) + "]}");
            for (int i = 0; i < bones.Count; i++)
            {
                var b = bones[i];
                sb.Append(",{\"name\":" + J(b.name));
                sb.Append(",\"translation\":" + Arr(new[] { -b.pos[0], b.pos[1], b.pos[2] }));
                sb.Append(",\"rotation\":" + Arr(new[] { b.rot[0], -b.rot[1], -b.rot[2], b.rot[3] }));
                if (Math.Abs(b.scale[0] - 1) > 1e-5 || Math.Abs(b.scale[1] - 1) > 1e-5 || Math.Abs(b.scale[2] - 1) > 1e-5) sb.Append(",\"scale\":" + Arr(b.scale));
                if (children[i].Count > 0) sb.Append(",\"children\":[" + string.Join(",", children[i]) + "]");
                sb.Append("}");
            }
            sb.Append(",{\"name\":\"CSR_borra_esta_malla\",\"mesh\":0,\"skin\":0}]");
            var joints = new int[bones.Count]; for (int i = 0; i < bones.Count; i++) joints[i] = i + 1;
            sb.Append(",\"skins\":[{\"name\":" + J(rootName) + ",\"joints\":[" + string.Join(",", joints) + "],\"inverseBindMatrices\":3,\"skeleton\":1}]");
            float minX = Math.Min(tri[0], Math.Min(tri[3], tri[6])), minY = Math.Min(tri[1], Math.Min(tri[4], tri[7])), minZ = Math.Min(tri[2], Math.Min(tri[5], tri[8]));
            float maxX = Math.Max(tri[0], Math.Max(tri[3], tri[6])), maxY = Math.Max(tri[1], Math.Max(tri[4], tri[7])), maxZ = Math.Max(tri[2], Math.Max(tri[5], tri[8]));
            sb.Append(",\"meshes\":[{\"name\":\"CSR_borra_esta_malla\",\"primitives\":[{\"attributes\":{\"POSITION\":0,\"JOINTS_0\":1,\"WEIGHTS_0\":2}}]}]");
            sb.Append(",\"accessors\":[");
            sb.Append("{\"bufferView\":0,\"componentType\":5126,\"count\":3,\"type\":\"VEC3\",\"min\":" + Arr(new[] { minX, minY, minZ }) + ",\"max\":" + Arr(new[] { maxX, maxY, maxZ }) + "}");
            sb.Append(",{\"bufferView\":1,\"componentType\":5121,\"count\":3,\"type\":\"VEC4\"}");
            sb.Append(",{\"bufferView\":2,\"componentType\":5126,\"count\":3,\"type\":\"VEC4\"}");
            sb.Append(",{\"bufferView\":3,\"componentType\":5126,\"count\":" + bones.Count + ",\"type\":\"MAT4\"}]");
            sb.Append(",\"bufferViews\":[");
            sb.Append("{\"buffer\":0,\"byteOffset\":" + posOff + ",\"byteLength\":36}");
            sb.Append(",{\"buffer\":0,\"byteOffset\":" + jOff + ",\"byteLength\":12}");
            sb.Append(",{\"buffer\":0,\"byteOffset\":" + wOff + ",\"byteLength\":48}");
            sb.Append(",{\"buffer\":0,\"byteOffset\":" + ibmOff + ",\"byteLength\":" + (bones.Count * 64) + "}]");
            sb.Append(",\"buffers\":[{\"byteLength\":" + binLen + "}]}");

            var json = Encoding.UTF8.GetBytes(sb.ToString());
            int jsonPad = (4 - json.Length % 4) % 4;
            var outS = new MemoryStream();
            void U32(uint v) => outS.Write(BitConverter.GetBytes(v), 0, 4);
            uint total = (uint)(12 + 8 + json.Length + jsonPad + 8 + binLen);
            U32(0x46546C67); U32(2); U32(total);
            U32((uint)(json.Length + jsonPad)); U32(0x4E4F534A); outS.Write(json, 0, json.Length); for (int i = 0; i < jsonPad; i++) outS.WriteByte(0x20);
            U32((uint)binLen); U32(0x004E4942); outS.Write(bin.GetBuffer(), 0, binLen);
            return outS.ToArray();
        }
    }
}
