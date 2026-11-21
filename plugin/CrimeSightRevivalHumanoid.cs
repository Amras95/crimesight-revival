// CRIMESIGHT Revival - adaptar un modelo humanoide cualquiera al esqueleto de los personajes del juego (sin Unity).
//
// Los modelos que circulan (Mixamo, VRChat/Unity, VRoid, Blender/Rigify, 3ds Max Biped, DAZ, MMD...) tienen su propio
// esqueleto. Aqui se reconoce cada hueso por su nombre (cadera, columna, brazos, piernas, dedos...), y el modelo se
// pasa al esqueleto del juego:
//   1. Se gira, escala y coloca entero para que quede de pie, mirando hacia delante y con la altura del personaje.
//   2. Cada brazo y pierna se gira hasta la postura del juego (T), aunque el modelo venga en A o con los codos
//      doblados. Es como "aplicar una postura" en Blender: cada vertice sigue a sus huesos con sus pesos.
//   3. Cada trozo se lleva a donde esta su hueso en el juego (por si tiene otras proporciones) y sus pesos pasan a
//      los huesos del juego. Lo que no se reconoce (pelo, falda, giros, ayudantes...) va con el hueso reconocido
//      mas cercano por encima (el pelo con la cabeza, la falda con la cadera).
// Sale un Glb.Model con los nombres del juego que CrimeSightRevivalModelsGlb.cs pone como uno hecho a medida.
using System;
using System.Collections.Generic;
using System.Linq;

namespace CrimeSightRevival.Mods
{
    static class Humanoid
    {
        /// <summary>Un hueso del personaje del juego: donde esta en reposo (respecto a su modelo) y su padre.</summary>
        public class GameBone { public string name, parent; public double[] pos; }

        static readonly string[] Fingers = { "thumb", "index", "middle", "ring", "little" };

        // ------------------------------------------------------------ los huesos del juego (c_hum_XX) por papel
        static readonly Dictionary<string, string> GameRoles = BuildGameRoles();

        static Dictionary<string, string> BuildGameRoles()
        {
            var d = new Dictionary<string, string>
            {
                ["root"] = "ROOT_c_hum", ["hips"] = "SKL_000_WAIST", ["spine"] = "SKL_001_SPINE", ["chest"] = "SKL_002_CHEST",
                ["neck"] = "SKL_003_NECK", ["head"] = "SKL_004_HEAD", ["eye.L"] = "SKL_506_Left_EYE", ["eye.R"] = "SKL_507_Right_EYE",
            };
            foreach (var (s, a, l) in new[] { ("L", 1, 3), ("R", 2, 4) })
            {
                string arm = a == 1 ? "L" : "R";
                d["shoulder." + s] = $"SKL_0{a}0_{arm}SHLD"; d["upperarm." + s] = $"SKL_0{a}1_{arm}UARM";
                d["lowerarm." + s] = $"SKL_0{a}2_{arm}FARM"; d["hand." + s] = $"SKL_0{a}3_{arm}HAND";
                d["upperleg." + s] = $"SKL_0{l}0_{arm}THIGH"; d["lowerleg." + s] = $"SKL_0{l}1_{arm}LEG";
                d["foot." + s] = $"SKL_0{l}2_{arm}FOOT"; d["toes." + s] = $"SKL_0{l}3_{arm}TOE";
                // dedos: SKL_101_LF10.. pulgar F10-12, indice F21-23, corazon F31-33, anular F41-43, menique F51-53 (F40, la palma)
                var first = new[] { 10, 21, 31, 41, 51 };
                var seq = new[] { 1, 4, 7, 11, 14 };
                for (int f = 0; f < 5; f++)
                    for (int k = 0; k < 3; k++)
                        d[$"{Fingers[f]}{k + 1}.{s}"] = $"SKL_{a}{seq[f] + k:00}_{arm}F{first[f] + k}";
            }
            return d;
        }

        /// <summary>El papel de quien hereda si el juego no tiene ese hueso (los dedos van a la mano, etc.).</summary>
        static string RoleParent(string role)
        {
            string side = role.EndsWith(".L") ? ".L" : role.EndsWith(".R") ? ".R" : "";
            string b = side.Length > 0 ? role.Substring(0, role.Length - 2) : role;
            switch (b)
            {
                case "root": return null;
                case "hips": return "root";
                case "spine": return "hips";
                case "chest": return "spine";
                case "neck": return "chest";
                case "head": return "neck";
                case "eye": return "head";
                case "shoulder": return "chest";
                case "upperarm": return "shoulder" + side;
                case "lowerarm": return "upperarm" + side;
                case "hand": return "lowerarm" + side;
                case "upperleg": return "hips";
                case "lowerleg": return "upperleg" + side;
                case "foot": return "lowerleg" + side;
                case "toes": return "foot" + side;
            }
            char n = b[b.Length - 1];
            if (n >= '2' && n <= '3') return b.Substring(0, b.Length - 1) + (char)(n - 1) + side;
            return "hand" + side;
        }

        // segmentos que se giran a la postura del juego: papel -> papel del hueso hijo que marca la direccion
        static readonly (string role, string[] child)[] Aim =
        {
            ("shoulder", new[] { "upperarm" }), ("upperarm", new[] { "lowerarm" }), ("lowerarm", new[] { "hand", "middle1", "index1" }),
            ("hand", new[] { "middle1", "index1", "ring1" }),
            ("upperleg", new[] { "lowerleg" }), ("lowerleg", new[] { "foot", "toes" }), ("foot", new[] { "toes" }),
        };

        // ------------------------------------------------------------ reconocer un hueso por su nombre
        static readonly HashSet<string> Skip = new()
        {
            "twist", "roll", "ik", "fk", "pole", "target", "nub", "end", "tip", "helper", "hlp", "ctrl", "control", "corrective",
            "adj", "share", "null", "socket", "prop", "weapon", "attach", "dummy", "ref", "effector", "goal", "offset", "aux",
            "jiggle", "bust", "breast", "boob", "oppai", "hair", "skirt", "cloth", "eyebrow", "eyelid", "eyelash", "brow", "lid",
            "teeth", "tongue", "jaw", "mouth", "lip", "cheek", "ear", "tail", "wing", "metacarpal", "palm", "carpal", "mch",
            "org", "wgt", "sec", "aim", "tops", "physics", "dyn", "cape", "coat", "ribbon", "sleeve", "hat", "glasses", "nouse", "item",
        };
        static readonly HashSet<string> Noise = new()
        {
            "mixamorig", "bip", "j", "def", "valvebiped", "cc", "base", "rig", "armature", "skeleton", "jnt", "joint", "bone",
            "bn", "b", "c", "sk", "skl", "deform", "pivot", "bind", "drv", "d",
        };

        /// <summary>(papel sin lado, lado "L"/"R"/"") o null. Los papeles: hips, spine, neck, head, eye, shoulder, upperarm,
        /// lowerarm, hand, upperleg, lowerleg, leg? (pierna sin saber si muslo o espinilla), foot, toes, y los dedos como
        /// "finger:thumb" (su falange se decide por el orden en la cadena).</summary>
        internal static (string role, string side)? Classify(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            string n = name;
            int cut = Math.Max(n.LastIndexOf(':'), n.LastIndexOf('|'));
            if (cut >= 0 && cut < n.Length - 1) n = n.Substring(cut + 1);
            foreach (char ch in n) if (ch >= 0x3040 && ch <= 0x9FFF) return ClassifyJp(n);

            // palabras: "LeftUpperArm" "upper_arm.L" "Bip01 L UpperArm" "J_Bip_L_UpperArm" "lShldrBend"...
            var words = new List<string>();
            var cur = new System.Text.StringBuilder();
            void Flush() { if (cur.Length > 0) { words.Add(cur.ToString().ToLowerInvariant()); cur.Clear(); } }
            for (int i = 0; i < n.Length; i++)
            {
                char c = n[i];
                if (!char.IsLetterOrDigit(c)) { Flush(); continue; }
                if (cur.Length > 0)
                {
                    char p = cur[cur.Length - 1];
                    bool split = (char.IsLower(p) && char.IsUpper(c)) || (char.IsDigit(p) != char.IsDigit(c))
                              || (char.IsUpper(p) && char.IsUpper(c) && i + 1 < n.Length && char.IsLower(n[i + 1]) && cur.Length > 1);
                    if (split) Flush();
                }
                cur.Append(c);
            }
            Flush();
            string side = "";
            var w = new List<string>();
            var digits = new List<string>();
            string fingerDigit = null; bool afterFinger = false;
            foreach (var t in words)
            {
                if (afterFinger && char.IsDigit(t[0])) fingerDigit ??= t;
                afterFinger = t == "finger";
                if (Skip.Contains(t)) return null;
                if (t == "l" || t == "left" || t == "lft") { side = "L"; continue; }
                if (t == "r" || t == "right" || t == "rt") { side = "R"; continue; }
                if (char.IsDigit(t[0])) { digits.Add(t); continue; }
                if (Noise.Contains(t)) continue;
                w.Add(t);
            }
            string j = string.Concat(w);
            if (j.Length == 0) return null;
            if (j.Contains("forehead")) return null;

            // dedos
            string finger = null;
            if (j.Contains("thumb")) finger = "thumb";
            else if (j.Contains("index") || j.Contains("pointer") || j.Contains("forefinger")) finger = "index";
            else if (j.Contains("middle")) finger = "middle";
            else if (j.Contains("ring")) finger = "ring";
            else if (j.Contains("pinky") || j.Contains("pinkie") || j.Contains("little") || j.Contains("small")) finger = "little";
            else if (j.Contains("finger") && fingerDigit != null) finger = "finger" + fingerDigit[0];   // Biped: Finger0..4 (se ajusta luego)
            if (finger != null) return side.Length > 0 ? ("finger:" + finger, side) : null;

            if (j.Contains("eye")) return side.Length > 0 ? ("eye", side) : null;
            if (j.Contains("head")) return side.Length == 0 ? ("head", "") : null;
            if (j.Contains("neck")) return side.Length == 0 ? ("neck", "") : null;
            string r = null;
            if (j.Contains("clavicle") || j.Contains("collar") || j.Contains("shoulder")) r = "shoulder";
            else if (j.Contains("forearm") || j.Contains("lowerarm") || j.Contains("lowarm") || j.Contains("elbow") || j == "farm") r = "lowerarm";
            else if (j.Contains("upperarm") || j.Contains("uparm") || j.Contains("shldr") || j == "arm" || j.EndsWith("arm")) r = "upperarm";
            else if (j.Contains("hand") || j.Contains("wrist")) r = "hand";
            else if (j.Contains("toe") || j == "ball") r = "toes";
            else if (j.Contains("foot") || j.Contains("ankle")) r = "foot";
            else if (j.Contains("calf") || j.Contains("shin") || j.Contains("knee") || j.Contains("lowerleg") || j.Contains("lowleg")) r = "lowerleg";
            else if (j.Contains("thigh") || j.Contains("upleg") || j.Contains("upperleg") || j.Contains("femur")) r = "upperleg";
            else if (j.Contains("leg")) r = "leg?";
            if (r != null) return side.Length > 0 ? (r, side) : null;
            if (j == "hips" || j == "hip" || j.Contains("pelvis") || j.Contains("lowerbody")) return side.Length == 0 ? ("hips", "") : null;
            return null;
        }

        static (string, string)? ClassifyJp(string n)
        {
            if (n.Contains("捩") || n.Contains("IK") || n.Contains("ＩＫ") || n.Contains("親") && n.Contains("全")) return null;
            string side = n.Contains("左") ? "L" : n.Contains("右") ? "R" : "";
            string r = null;
            if (n.Contains("つま先")) r = "toes";
            else if (n.Contains("先")) return null;
            else if (n.Contains("親指")) r = "finger:thumb";
            else if (n.Contains("人指") || n.Contains("人差")) r = "finger:index";
            else if (n.Contains("中指")) r = "finger:middle";
            else if (n.Contains("薬指")) r = "finger:ring";
            else if (n.Contains("小指")) r = "finger:little";
            else if (n.Contains("目")) r = "eye";
            else if (n.Contains("下半身")) return side.Length == 0 ? ("hips", "") : null;
            else if (n.Contains("上半身")) return null;                       // la columna sale de la cadena
            else if (n.Contains("手首")) r = "hand";
            else if (n.Contains("足首")) r = "foot";
            else if (n.Contains("首")) return side.Length == 0 ? ("neck", "") : null;
            else if (n.Contains("頭")) return side.Length == 0 ? ("head", "") : null;
            else if (n.Contains("肩")) r = "shoulder";
            else if (n.Contains("ひじ") || n.Contains("肘")) r = "lowerarm";
            else if (n.Contains("腕")) r = "upperarm";
            else if (n.Contains("ひざ") || n.Contains("膝")) r = "lowerleg";
            else if (n.Contains("足")) r = "upperleg";
            if (r == null) return null;
            if (r == "eye" && side.Length == 0) return null;
            return side.Length > 0 ? (r, side) : null;
        }

        /// <summary>Lo que se sabe de un esqueleto humanoide frente al del juego: papel de cada hueso, giro y escala
        /// para ponerlo de pie como el del juego, y el giro de cada hueso hasta la postura T del juego.</summary>
        internal class Fit
        {
            public Dictionary<string, string> parent, role, roleOf;
            public Dictionary<string, double[]> pos, p0, posed, delta;
            public double[] rot, hipS, hipG; public double scale; public bool arms, legs; public int aimed;
            public Dictionary<string, GameBone> game;
            public string GameFor(string r)
            {
                if (r.StartsWith("spine:")) r = "spine";
                for (var x = r; x != null; x = RoleParent(x))
                    if (GameRoles.TryGetValue(x, out var g) && game.ContainsKey(g)) return g;
                return null;
            }
            public bool Exact(string r) => GameRoles.TryGetValue(r, out var g) && game.ContainsKey(g);
            public double[] G(string r) => game[GameFor(r)].pos;
            public double[] T0(double[] v) => Add(Scale(Apply(rot, Sub(v, hipS)), scale), hipG);
        }

        internal static Fit Build(Dictionary<string, string> parent, Dictionary<string, double[]> pos, Dictionary<string, double> weight,
                                  Dictionary<string, GameBone> game, out string report)
        {
            report = null;
            int Depth(string nm) { int d = 0; for (var p = parent.GetValueOrDefault(nm); p != null && d < 512; p = parent.GetValueOrDefault(p)) d++; return d; }
            bool IsAncestor(string a, string of) { for (var p = parent.GetValueOrDefault(of); p != null; p = parent.GetValueOrDefault(p)) if (p == a) return true; return false; }
            // --- papeles por nombre (si dos huesos dicen lo mismo, gana el que mas malla mueve)
            var cand = new Dictionary<string, List<string>>();
            bool zeroBased = false;
            foreach (var nm in parent.Keys)
            {
                var c = Classify(nm);
                if (c == null) continue;
                var (rl, side) = c.Value;
                if (rl == "finger:finger0") zeroBased = true;
                string key = side.Length > 0 ? rl + "." + side : rl;
                if (!cand.TryGetValue(key, out var l)) cand[key] = l = new List<string>();
                l.Add(nm);
            }
            var role = new Dictionary<string, string>();                     // papel -> hueso del modelo
            string Best(List<string> l) => l.OrderByDescending(x => weight.GetValueOrDefault(x)).ThenBy(Depth).First();
            foreach (var kv in cand)
            {
                if (kv.Key.StartsWith("finger:")) continue;
                role[kv.Key] = Best(kv.Value);
            }
            // cadenas con nombres genericos ("arm_joint_L_1/2/3", "Leg_L_01/02/03"): todos dicen "brazo" o "pierna";
            // si no hay antebrazo (o espinilla) con nombre, van por orden en la cadena
            foreach (var s in new[] { "L", "R" })
            {
                foreach (var (kind, seq) in new[] { ("upperarm", new[] { "shoulder", "upperarm", "lowerarm", "hand" }),
                                                    ("leg?", new[] { "upperleg", "lowerleg", "foot", "toes" }),
                                                    ("upperleg", new[] { "upperleg", "lowerleg", "foot", "toes" }) })
                {
                    if (!cand.TryGetValue(kind + "." + s, out var l) || l.Count < 2 || role.ContainsKey(seq[2] + "." + s)) continue;
                    var chain = l.OrderBy(Depth).ToList();
                    bool linked = true;
                    for (int k = 1; k < chain.Count; k++) if (!IsAncestor(chain[k - 1], chain[k])) linked = false;
                    if (!linked) continue;
                    var names = kind == "upperarm" && chain.Count < 4 ? seq.Skip(1).ToArray() : seq;
                    role.Remove(kind + "." + s);
                    for (int k = 0; k < chain.Count && k < names.Length; k++) role[names[k] + "." + s] = chain[k];
                }
            }
            foreach (var s in new[] { "L", "R" })                            // "leg": muslo si no hay otro muslo, si no espinilla
                if (role.TryGetValue("leg?." + s, out var leg))
                {
                    role.Remove("leg?." + s);
                    if (!role.ContainsKey("upperleg." + s)) role["upperleg." + s] = leg;
                    else if (!role.ContainsKey("lowerleg." + s)) role["lowerleg." + s] = leg;
                }
            // dedos: las falanges por orden en la cadena (las 3 primeras)
            foreach (var kv in cand)
            {
                if (!kv.Key.StartsWith("finger:")) continue;
                string f = kv.Key.Substring(7, kv.Key.Length - 9), s = kv.Key.Substring(kv.Key.Length - 1);
                if (f.StartsWith("finger"))
                {
                    int d = f[6] - '0' - (zeroBased ? 0 : 1);
                    if (d < 0 || d > 4) continue;
                    f = Fingers[d];
                }
                var chain = kv.Value.Where(x => Depth(x) >= 0).OrderBy(Depth).ToList();
                // si vienen de dos cadenas distintas (pulgar de la palma y otro hueso), la que tenga mas peso
                for (int k = 0; k < 3 && k < chain.Count; k++) role.TryAdd($"{f}{k + 1}.{s}", chain[k]);
            }
            if (!role.ContainsKey("hips") && role.TryGetValue("upperleg.L", out var ll) && role.TryGetValue("upperleg.R", out var lr))
            {
                var h = Lca(ll, lr, parent);
                if (h != null) role["hips"] = h;
            }
            // cuello y cabeza que no se llamen asi (Rigify): por encima de los hombros, lo mas alto
            if (!role.ContainsKey("neck") && !role.ContainsKey("head") && role.TryGetValue("upperarm.L", out var al) && role.TryGetValue("upperarm.R", out var ar))
            {
                var top = Lca(al, ar, parent);
                if (top != null && role.TryGetValue("hips", out var hh))
                {
                    var up = Sub(pos[top], pos[hh]);
                    string best = null; double bh = Dot(Sub(pos[top], pos[hh]), up);
                    foreach (var nm in parent.Keys)
                    {
                        if (!IsAncestor(top, nm) || IsAncestor(al, nm) || IsAncestor(ar, nm) || nm == al || nm == ar) continue;
                        if (role.Values.Contains(nm)) continue;
                        double hgt = Dot(Sub(pos[nm], pos[hh]), up);
                        if (hgt > bh + 1e-6) { bh = hgt; best = nm; }
                    }
                    if (best != null)
                    {
                        var path = new List<string>();
                        for (var p = best; p != null && p != top; p = parent.GetValueOrDefault(p)) path.Add(p);
                        path.Reverse();                                     // de abajo a arriba
                        if (path.Count >= 2) { role["neck"] = path[0]; role["head"] = path[path.Count - 1] == best && path.Count > 1 ? path[path.Count - 2] : best; }
                        else role["head"] = best;
                        if (role["head"] == role.GetValueOrDefault("neck")) role.Remove("neck");
                    }
                }
            }
            // la columna: lo que hay entre la cadera y el cuello (sin la cadera)
            role.Remove("spine"); role.Remove("chest");
            var neckOrHead = role.GetValueOrDefault("neck") ?? role.GetValueOrDefault("head");
            if (neckOrHead != null && role.TryGetValue("hips", out var hips))
            {
                var stop = Lca(neckOrHead, hips, parent);
                var spine = new List<string>();
                for (var p = parent.GetValueOrDefault(neckOrHead); p != null && p != stop && p != hips; p = parent.GetValueOrDefault(p)) spine.Add(p);
                spine.Reverse();
                spine.RemoveAll(x => role.ContainsValue(x));
                if (spine.Count > 0) role["spine"] = spine[0];
                if (spine.Count > 1) role["chest"] = spine[spine.Count - 1];
                for (int k = 1; k < spine.Count - 1; k++) role["spine:" + k] = spine[k];      // las del medio, con la columna
            }

            bool arms = role.ContainsKey("upperarm.L") && role.ContainsKey("upperarm.R");
            bool legs = role.ContainsKey("upperleg.L") && role.ContainsKey("upperleg.R");
            // un animal (zorro, perro...) tambien tiene "patas" y "cabeza": en un humanoide las piernas van hacia abajo,
            // al lado contrario de la cabeza
            if (legs && neckOrHead != null && role.TryGetValue("hips", out var hp0))
            {
                string fl = role.GetValueOrDefault("foot.L") ?? role.GetValueOrDefault("lowerleg.L") ?? role["upperleg.L"];
                string fr = role.GetValueOrDefault("foot.R") ?? role.GetValueOrDefault("lowerleg.R") ?? role["upperleg.R"];
                var down = Sub(Scale(Add(pos[fl], pos[fr]), 0.5), pos[hp0]);
                var upv = Sub(pos[neckOrHead], pos[hp0]);
                if (Len(down) > 1e-9 && Len(upv) > 1e-9 && Dot(Norm(down), Norm(upv)) > -0.6)
                {
                    report = "no parece un humanoide de pie (las piernas no van hacia abajo desde la cadera)";
                    return null;
                }
            }
            if (!role.ContainsKey("hips") || neckOrHead == null || !(arms || legs))
            {
                report = "no parece un humanoide: no encuentro " + string.Join(", ",
                    new[] { role.ContainsKey("hips") ? null : "la cadera", neckOrHead != null ? null : "el cuello o la cabeza",
                            arms || legs ? null : "los brazos o las piernas" }.Where(x => x != null));
                return null;
            }

            // --- hueso del juego de cada papel (o el de su papel padre si el juego no lo tiene)
            string GameFor(string r)
            {
                if (r.StartsWith("spine:")) r = "spine";
                for (var x = r; x != null; x = RoleParent(x))
                    if (GameRoles.TryGetValue(x, out var g) && game.ContainsKey(g)) return g;
                return null;
            }
            bool Exact(string r) => GameRoles.TryGetValue(r, out var g) && game.ContainsKey(g);
            var roleOf = new Dictionary<string, string>();                    // hueso del modelo -> papel
            foreach (var kv in role) roleOf[kv.Value] = kv.Key;
            double[] G(string r) => game[GameFor(r)].pos;

            // --- 1. girar, escalar y colocar entero
            string top2 = role.GetValueOrDefault("head") ?? role["neck"];
            string topR = role.ContainsKey("head") ? "head" : "neck";
            var upS = Sub(pos[top2], pos[role["hips"]]); var upG = Sub(G(topR), G("hips"));
            double[] rightS, rightG;
            if (arms) { rightS = Sub(pos[role["upperarm.R"]], pos[role["upperarm.L"]]); rightG = Sub(G("upperarm.R"), G("upperarm.L")); }
            else { rightS = Sub(pos[role["upperleg.R"]], pos[role["upperleg.L"]]); rightG = Sub(G("upperleg.R"), G("upperleg.L")); }
            // escala: la altura de los pies a la cabeza (la de la cadera a la cabeza falla con proporciones raras)
            double scale = Len(upG) / Math.Max(Len(upS), 1e-9);
            string footS = role.GetValueOrDefault("foot.L") ?? role.GetValueOrDefault("foot.R");
            if (footS != null)
            {
                string fr = role.ContainsKey("foot.L") ? "foot.L" : "foot.R";
                var u = Norm(upS);
                double hs = Dot(Sub(pos[top2], pos[footS]), u), hg = Dot(Sub(G(topR), G(fr)), Norm(upG));
                if (hs > 1e-6 && hg > 1e-6) scale = hg / hs;
            }
            var rot = Mul(Frame(upG, rightG), Transpose(Frame(upS, rightS)));
            var hipS = pos[role["hips"]]; var hipG = G("hips");
            double[] T0(double[] v) => Add(Scale(Apply(rot, Sub(v, hipS)), scale), hipG);
            var p0 = new Dictionary<string, double[]>();
            foreach (var kv in pos) p0[kv.Key] = T0(kv.Value);

            // --- 2. brazos y piernas a la postura del juego (de padres a hijos)
            var order = parent.Keys.OrderBy(Depth).ToList();
            var delta = new Dictionary<string, double[]>();                  // giro de cada hueso (en el espacio del modelo)
            var posed = new Dictionary<string, double[]>();
            int aimed = 0;
            foreach (var nm in order)
            {
                var pa = parent.GetValueOrDefault(nm);
                if (pa == null || !posed.ContainsKey(pa)) { delta[nm] = Identity(); posed[nm] = p0[nm]; }
                else { posed[nm] = Add(posed[pa], Apply(delta[pa], Sub(p0[nm], p0[pa]))); delta[nm] = delta[pa]; }
                if (!roleOf.TryGetValue(nm, out var r)) continue;
                string side = r.EndsWith(".L") ? ".L" : r.EndsWith(".R") ? ".R" : null;
                if (side == null) continue;
                string b = r.Substring(0, r.Length - 2);
                foreach (var (ar2, kids) in Aim)
                {
                    if (ar2 != b) continue;
                    foreach (var k in kids)
                    {
                        if (!role.TryGetValue(k + side, out var child) || !IsAncestor(nm, child) || !Exact(r) || !Exact(k + side)) continue;
                        var curDir = Apply(delta[nm], Sub(p0[child], p0[nm]));
                        var tgt = Sub(G(k + side), G(r));
                        if (Len(curDir) < 1e-9 || Len(tgt) < 1e-9) break;
                        delta[nm] = Mul(FromTo(curDir, tgt), delta[nm]);
                        aimed++;
                        break;
                    }
                }
            }

            return new Fit { parent = parent, role = role, roleOf = roleOf, pos = pos, p0 = p0, posed = posed, delta = delta, rot = rot,
                             hipS = hipS, hipG = hipG, scale = scale, arms = arms, legs = legs, aimed = aimed, game = game };
        }

        // ------------------------------------------------------------ el paso al esqueleto del juego
        public static Glb.Model Retarget(Glb.Model src, Dictionary<string, GameBone> game, out string report)
        {
            report = null;
            // --- huesos del modelo: padres, profundidad, posicion, peso
            var parent = new Dictionary<string, string>();
            var pos = new Dictionary<string, double[]>();
            foreach (var jt in src.joints)
            {
                if (jt.name == "<root>") continue;
                var chain = new List<string> { jt.name };
                chain.AddRange(jt.ancestors);
                for (int i = 0; i < chain.Count; i++)
                    if (!parent.ContainsKey(chain[i])) parent[chain[i]] = i + 1 < chain.Count ? chain[i + 1] : null;
                pos[jt.name] = D(jt.pos);
            }
            foreach (var nm in parent.Keys.ToList())
                if (!pos.ContainsKey(nm)) pos[nm] = src.nodePos.TryGetValue(nm, out var np) ? D(np) : new double[3];
            var weight = new Dictionary<string, double>();
            foreach (var p in src.parts)
                for (int k = 0; k < p.boneW.Length; k++)
                {
                    var nm = src.joints[p.boneIdx[k]].name;
                    weight[nm] = weight.GetValueOrDefault(nm) + p.boneW[k];
                }

            var f = Build(parent, pos, weight, game, out report);
            if (f == null) return null;
            var role = f.role; var roleOf = f.roleOf; var rot = f.rot; double scale = f.scale;
            var p0 = f.p0; var delta = f.delta; var posed = f.posed; bool arms = f.arms, legs = f.legs; int aimed = f.aimed;
            string GameFor(string r) => f.GameFor(r);
            bool Exact(string r) => f.Exact(r);
            double[] G(string r) => f.G(r);
            double[] T0(double[] v) => f.T0(v);

            // --- 3. cada hueso del modelo -> hueso del juego, y como se mueven sus vertices
            string Up(string nm) { for (var x = nm; x != null; x = parent.GetValueOrDefault(x)) if (roleOf.ContainsKey(x)) return x; return null; }
            // huesos reconocidos que cuelgan directamente de cada reconocido, y el segmento de cada uno (hasta su hijo)
            var kids = new Dictionary<string, List<string>>();
            foreach (var b in roleOf.Keys) { var u = Up(parent.GetValueOrDefault(b)); if (u != null) { if (!kids.TryGetValue(u, out var l)) kids[u] = l = new List<string>(); l.Add(b); } }
            var mappedCache = new Dictionary<string, string>();
            string Mapped(string nm)
            {
                if (mappedCache.TryGetValue(nm, out var hit)) return hit;
                var a = Up(nm);
                // uno no reconocido (manga, ayudante) que esta sobre el segmento de un hijo reconocido de su padre
                // (p. ej. colgado del hombro pero a lo largo del brazo) va con ese hijo
                if (a != null && a != nm && kids.TryGetValue(a, out var ks) && pos.TryGetValue(nm, out var pu))
                    foreach (var b in ks)
                    {
                        if (!kids.TryGetValue(b, out var bk) || bk.Count == 0) continue;
                        var seg = Sub(pos[bk[0]], pos[b]); double l2 = Dot(seg, seg);
                        if (l2 < 1e-12) continue;
                        double tt = Dot(Sub(pu, pos[b]), seg) / l2;
                        if (tt < -0.05 || tt > 1.1) continue;
                        var off = Sub(Sub(pu, pos[b]), Scale(seg, tt));
                        if (Len(off) < 0.2 * Math.Sqrt(l2)) { a = b; break; }
                    }
                return mappedCache[nm] = a;
            }
            // el esqueleto propio del modelo: cada hueso del juego, donde lo tiene el modelo (o el del juego si no lo tiene),
            // y todo un poco arriba o abajo para que los tobillos queden a la altura de los del juego (los pies en el suelo)
            var rig = new Dictionary<string, double[]>();
            foreach (var kv in role)
                if (Exact(kv.Key) && !rig.ContainsKey(GameRoles[kv.Key])) rig[GameRoles[kv.Key]] = posed[kv.Value];
            double lift = 0; int feet = 0;
            foreach (var ft in new[] { "foot.L", "foot.R" })
                if (role.ContainsKey(ft) && Exact(ft)) { lift += G(ft)[1] - posed[role[ft]][1]; feet++; }
            if (feet > 0) lift /= feet;
            var lifted = new double[] { 0, lift, 0 };
            var outModel = new Glb.Model { proxy = true };
            outModel.images.AddRange(src.images);
            outModel.notes.AddRange(src.notes);
            var gIndex = new Dictionary<string, int>();
            int GameJoint(string g)
            {
                if (gIndex.TryGetValue(g, out var i)) return i;
                var at = rig.TryGetValue(g, out var rp) ? Add(rp, lifted) : game[g].pos;
                var jt = new Glb.Joint { name = g, pos = F(at) };
                for (var p = game[g].parent; p != null && game.ContainsKey(p); p = game[p].parent) jt.ancestors.Add(p);
                outModel.joints.Add(jt);
                outModel.nodePos[g] = F(at);
                return gIndex[g] = outModel.joints.Count - 1;
            }
            string rootGame = GameFor("root") ?? GameFor("hips");
            int nj = src.joints.Count;
            var jGame = new int[nj];
            var jDelta = new double[nj][];
            var jFrom = new double[nj][];
            var jTo = new double[nj][];
            for (int j = 0; j < nj; j++)
            {
                var nm = src.joints[j].name;
                var m = nm == "<root>" ? null : Mapped(nm);
                if (m == null) { jGame[j] = GameJoint(rootGame); jDelta[j] = Identity(); jFrom[j] = new double[3]; jTo[j] = lifted; continue; }
                var r = roleOf[m];
                jGame[j] = GameJoint(GameFor(r));
                jDelta[j] = delta[m];
                jFrom[j] = p0[m];
                jTo[j] = Add(posed[m], lifted);                                     // v -> delta(v - p0[m]) + posed[m]: sus medidas
            }

            foreach (var p in src.parts)
            {
                int vc = p.pos.Length / 3;
                var q = new Glb.Part { name = p.name, uv = p.uv, tris = p.tris, image = p.image, color = p.color,
                                       pos = new float[p.pos.Length], nrm = p.nrm != null ? new float[p.nrm.Length] : null,
                                       boneIdx = new int[vc * 4], boneW = new float[vc * 4] };
                var acc = new Dictionary<int, float>();
                for (int v = 0; v < vc; v++)
                {
                    var v0 = T0(new double[] { p.pos[v * 3], p.pos[v * 3 + 1], p.pos[v * 3 + 2] });
                    double[] n0 = p.nrm != null ? Apply(rot, new double[] { p.nrm[v * 3], p.nrm[v * 3 + 1], p.nrm[v * 3 + 2] }) : null;
                    var vs = new double[3]; var ns = new double[3];
                    acc.Clear();
                    for (int k = 0; k < 4; k++)
                    {
                        float wk = p.boneW[v * 4 + k];
                        if (wk <= 0) continue;
                        int j = p.boneIdx[v * 4 + k];
                        var t = Add(Apply(jDelta[j], Sub(v0, jFrom[j])), jTo[j]);
                        for (int c = 0; c < 3; c++) vs[c] += wk * t[c];
                        if (n0 != null) { var tn = Apply(jDelta[j], n0); for (int c = 0; c < 3; c++) ns[c] += wk * tn[c]; }
                        acc[jGame[j]] = acc.GetValueOrDefault(jGame[j]) + wk;
                    }
                    if (acc.Count == 0) { vs = Add(v0, lifted); ns = n0 ?? ns; acc[GameJoint(rootGame)] = 1; }
                    for (int c = 0; c < 3; c++) q.pos[v * 3 + c] = (float)vs[c];
                    if (q.nrm != null) { double l = Len(ns); for (int c = 0; c < 3; c++) q.nrm[v * 3 + c] = (float)(l > 1e-9 ? ns[c] / l : 0); }
                    var top4 = acc.OrderByDescending(x => x.Value).Take(4).ToList();
                    float sum = top4.Sum(x => x.Value);
                    for (int k = 0; k < 4; k++)
                    {
                        q.boneIdx[v * 4 + k] = k < top4.Count ? top4[k].Key : top4[0].Key;
                        q.boneW[v * 4 + k] = k < top4.Count && sum > 0 ? top4[k].Value / sum : 0;
                    }
                }
                outModel.parts.Add(q);
            }
            foreach (var jt in outModel.joints.ToList()) foreach (var an in jt.ancestors) GameJoint(an);   // la cadena entera hasta la raiz
            int known = roleOf.Count(kv => !kv.Value.StartsWith("spine:"));
            report = $"adaptado como humanoide: {known} huesos reconocidos ({(arms ? "brazos" : "sin brazos")}, {(legs ? "piernas" : "sin piernas")}, " +
                     $"{role.Keys.Count(k => k.Contains("1."))} dedos), {aimed} giros a la postura del juego, escala {scale:0.###}";
            return outModel;
        }

        // ------------------------------------------------------------ animaciones de otro esqueleto
        /// <summary>Una animacion (de un .glb/.fbx humanoide) lista para mover el esqueleto del juego: para cada hueso del
        /// juego, que nodo la mueve y como pasar su giro (Q = pre * giro del nodo * post, en el espacio del modelo).</summary>
        public class AnimMap
        {
            public Glb.Model src; public Glb.Anim anim;
            public readonly List<(string game, int node, double[] pre, double[] post)> bones = new();
            public int hips = -1; public double[] hipRest, rot; public double scale;
            public string report;
        }

        /// <summary>El giro de una matriz de escena glTF, en Unity (filas), sin escala.</summary>
        static double[] RotU(float[] m)
        {
            var r = new double[9];
            for (int row = 0; row < 3; row++)
                for (int col = 0; col < 3; col++)
                    r[row * 3 + col] = m[col * 4 + row] * ((row == 0) != (col == 0) ? -1 : 1);
            for (int col = 0; col < 3; col++)
            {
                double l = Math.Sqrt(r[col] * r[col] + r[3 + col] * r[3 + col] + r[6 + col] * r[6 + col]);
                if (l > 1e-12) { r[col] /= l; r[3 + col] /= l; r[6 + col] /= l; }
            }
            return r;
        }

        static double[] PosU(float[] m) => new double[] { -m[12], m[13], m[14] };

        public static AnimMap PrepareAnim(Glb.Model src, Glb.Anim anim, Dictionary<string, GameBone> game, out string report)
        {
            var rest = Glb.Pose(src, null, 0);
            var parent = new Dictionary<string, string>();
            var pos = new Dictionary<string, double[]>();
            var index = new Dictionary<string, int>();
            for (int i = 0; i < src.nodes.Count; i++)
            {
                var n = src.nodes[i];
                if (index.ContainsKey(n.name)) continue;
                index[n.name] = i;
                parent[n.name] = n.parent >= 0 ? src.nodes[n.parent].name : null;
                pos[n.name] = PosU(rest[i]);
            }
            var weight = new Dictionary<string, double>();
            foreach (var p in src.parts)
                for (int k = 0; k < p.boneW.Length; k++)
                {
                    var nm = src.joints[p.boneIdx[k]].name;
                    weight[nm] = weight.GetValueOrDefault(nm) + p.boneW[k];
                }
            var f = Build(parent, pos, weight, game, out report);
            if (f == null) return null;
            var m = new AnimMap { src = src, anim = anim, rot = f.rot, scale = f.scale };
            var rotT = Transpose(f.rot);
            foreach (var kv in f.role)
            {
                if (kv.Key.StartsWith("spine:") || !f.Exact(kv.Key) || !index.TryGetValue(kv.Value, out var ni)) continue;
                var w0 = RotU(rest[ni]);
                // Q(t) = R * W(t) * W0^-1 * R^-1 * aim^-1 : el giro desde su reposo, en el reposo en T del juego
                var post = Mul(Mul(Transpose(w0), rotT), Transpose(f.delta[kv.Value]));
                m.bones.Add((GameRoles[kv.Key], ni, f.rot, post));
                if (kv.Key == "hips") { m.hips = ni; m.hipRest = pos[kv.Value]; }
            }
            // de padres a hijos (asi el plugin pone cada giro sobre el de su padre ya puesto)
            int Depth(string g) { int d = 0; for (var p = game[g].parent; p != null && game.ContainsKey(p); p = game[p].parent) d++; return d; }
            m.bones.Sort((x, y) => Depth(x.game).CompareTo(Depth(y.game)));
            m.report = report = $"animacion adaptada: {m.bones.Count} huesos del juego movidos";
            return m;
        }

        /// <summary>Los giros de la animacion en el instante t: hueso del juego -> giro en el espacio del modelo (filas),
        /// que se aplica sobre su giro de reposo; y cuanto sube o baja la cadera (en metros del juego).</summary>
        public static void SampleAnim(AnimMap m, float t, List<(string game, double[] q)> outRot, out double hipUp)
        {
            var gl = Glb.Pose(m.src, m.anim, t);
            outRot.Clear();
            foreach (var (g, node, pre, post) in m.bones) outRot.Add((g, Mul(Mul(pre, RotU(gl[node])), post)));
            hipUp = 0;
            if (m.hips >= 0) hipUp = Apply(m.rot, Sub(PosU(gl[m.hips]), m.hipRest))[1] * m.scale;
        }

        static string Lca(string a, string b, Dictionary<string, string> parent)
        {
            var seen = new HashSet<string>();
            for (var x = a; x != null; x = parent.GetValueOrDefault(x)) seen.Add(x);
            for (var x = b; x != null; x = parent.GetValueOrDefault(x)) if (seen.Contains(x)) return x;
            return null;
        }

        // ------------------------------------------------------------ cuentas (matrices 3x3 por filas)
        static double[] D(float[] f) => new double[] { f[0], f[1], f[2] };
        static float[] F(double[] d) => new[] { (float)d[0], (float)d[1], (float)d[2] };
        static double[] Add(double[] a, double[] b) => new[] { a[0] + b[0], a[1] + b[1], a[2] + b[2] };
        static double[] Sub(double[] a, double[] b) => new[] { a[0] - b[0], a[1] - b[1], a[2] - b[2] };
        static double[] Scale(double[] a, double s) => new[] { a[0] * s, a[1] * s, a[2] * s };
        static double Dot(double[] a, double[] b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
        static double Len(double[] a) => Math.Sqrt(Dot(a, a));
        static double[] Norm(double[] a) { double l = Len(a); return l > 1e-12 ? Scale(a, 1 / l) : new double[] { 0, 1, 0 }; }
        static double[] Cross(double[] a, double[] b) => new[] { a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0] };
        static double[] Identity() => new double[] { 1, 0, 0, 0, 1, 0, 0, 0, 1 };
        static double[] Apply(double[] m, double[] v) => new[]
        {
            m[0] * v[0] + m[1] * v[1] + m[2] * v[2], m[3] * v[0] + m[4] * v[1] + m[5] * v[2], m[6] * v[0] + m[7] * v[1] + m[8] * v[2],
        };
        static double[] Mul(double[] a, double[] b)
        {
            var r = new double[9];
            for (int i = 0; i < 3; i++) for (int j = 0; j < 3; j++) r[i * 3 + j] = a[i * 3] * b[j] + a[i * 3 + 1] * b[3 + j] + a[i * 3 + 2] * b[6 + j];
            return r;
        }
        static double[] Transpose(double[] m) => new[] { m[0], m[3], m[6], m[1], m[4], m[7], m[2], m[5], m[8] };

        /// <summary>Base ortonormal (derecha, arriba, delante) en columnas, a partir de "arriba" y "derecha".</summary>
        static double[] Frame(double[] up, double[] right)
        {
            var u = Norm(up);
            var r = Norm(Sub(right, Scale(u, Dot(right, u))));
            var f = Cross(r, u);
            return new[] { r[0], u[0], f[0], r[1], u[1], f[1], r[2], u[2], f[2] };
        }

        /// <summary>El giro mas corto que lleva la direccion a hasta la b.</summary>
        static double[] FromTo(double[] a, double[] b)
        {
            a = Norm(a); b = Norm(b);
            var v = Cross(a, b);
            double c = Dot(a, b);
            if (c < -0.999999)
            {
                var ax = Norm(Math.Abs(a[0]) < 0.9 ? Cross(a, new double[] { 1, 0, 0 }) : Cross(a, new double[] { 0, 1, 0 }));
                return new[] { 2 * ax[0] * ax[0] - 1, 2 * ax[0] * ax[1], 2 * ax[0] * ax[2], 2 * ax[1] * ax[0], 2 * ax[1] * ax[1] - 1, 2 * ax[1] * ax[2],
                               2 * ax[2] * ax[0], 2 * ax[2] * ax[1], 2 * ax[2] * ax[2] - 1 };
            }
            double k = 1 / (1 + c);
            return new[]
            {
                v[0] * v[0] * k + c, v[0] * v[1] * k - v[2], v[0] * v[2] * k + v[1],
                v[1] * v[0] * k + v[2], v[1] * v[1] * k + c, v[1] * v[2] * k - v[0],
                v[2] * v[0] * k - v[1], v[2] * v[1] * k + v[0], v[2] * v[2] * k + c,
            };
        }
    }
}
