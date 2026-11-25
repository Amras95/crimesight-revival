// CRIMESIGHT Revival - a new character moves like the game character chosen for it in the launcher.
//
// Each seat (A..F) plays as its original, and the game gives it its animations (that character's: van_..., drt_...).
// If a new character with "Animations from: Dorothy" appears in that seat, after the game's animations
// (LateUpdate, before the custom skeleton copies the bones) Dorothy's equivalent animation is put on its bones:
// same action (idle, walk, run...) at the same point. Rotations only; the hips, with their height scaled.
// While the game plays a one-off action (PlayClip: attack, pick up...) the game's is left, with a short fade, and
// while a scene (Timeline: attacking someone, the ending...) moves the character, the scene's, with nothing on top.
// Custom animations (idle/walk/run from the .glb) go after these and take precedence.
using System;
using System.Collections.Generic;
using UnityEngine;
using Il2CppInterop.Runtime;

namespace CrimeSightRevival.Mods
{
    static partial class Models
    {
        class Borrow
        {
            public GameObject root; public ControllerMixerPlayable cmp; public string key, from, fromCode;
            public readonly Dictionary<string, AnimationClip> clips = new();
            public Transform[] bones; public Transform hips;
            public Vector3 hipsRest, fromHipsRest; public float hipK = 1f;
            public float w; public AnimationClip last; public float lastT;
            public Quaternion[] keepR; public Vector3[] keepP; public bool scene;
        }
        static Dictionary<string, string> _borrowMap = new();
        static readonly Dictionary<int, Borrow> _borrows = new();

        internal static void SetBorrow(Dictionary<string, string> map)
        {
            _borrowMap = map ?? new Dictionary<string, string>();
            _borrows.Clear();
            if (_borrowMap.Count > 0)
            {
                var sb = new System.Text.StringBuilder();
                foreach (var kv in _borrowMap) sb.Append(sb.Length > 0 ? ", " : "").Append(kv.Key).Append(" como ").Append(kv.Value);
                Plugin.L.LogInfo("[Animaciones] se mueven como otro personaje: " + sb);
            }
        }

        // ---------------------------------------------------------------- game scenes (Timeline)
        // The scenes (attacking someone, the ending...) are Timelines that move the character with its
        // seat's animations, coordinated with the others and with the camera. While a scene moves a character,
        // nothing is
        // put on top (neither the borrowed animations nor the custom ones): the scene rules.
        static readonly List<Transform> _sceneBound = new();
        static float _sceneNext;
        static string _sceneNames = "";

        static void RefreshScenes()
        {
            if (Time.unscaledTime < _sceneNext) return;
            _sceneNext = Time.unscaledTime + 0.2f;
            _sceneBound.Clear();
            var names = new System.Text.StringBuilder();
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<UnityEngine.Playables.PlayableDirector>()))
            {
                var pd = o.TryCast<UnityEngine.Playables.PlayableDirector>();
                if (pd == null || pd.state != UnityEngine.Playables.PlayState.Playing) continue;
                var ta = pd.playableAsset != null ? pd.playableAsset.TryCast<UnityEngine.Timeline.TimelineAsset>() : null;
                if (ta == null) continue;
                int n = ta.outputTrackCount, bound = 0;
                for (int i = 0; i < n; i++)
                {
                    var tr = ta.GetOutputTrack(i);
                    if (tr == null || tr.TryCast<UnityEngine.Timeline.AnimationTrack>() == null) continue;
                    var bo = pd.GetGenericBinding(tr);
                    if (bo == null) continue;
                    Transform t = null;
                    var an = bo.TryCast<Animator>();
                    if (an != null) t = an.transform;
                    else { var go = bo.TryCast<GameObject>(); if (go != null) t = go.transform; }
                    if (t != null) { _sceneBound.Add(t); bound++; }
                }
                if (bound > 0) names.Append(names.Length > 0 ? ", " : "").Append(pd.name);
            }
            _sceneNames = names.ToString();
        }

        /// <summary>true if a game scene (Timeline) is moving this character now.</summary>
        internal static bool InScene(Component c)
        {
            if (c == null) return false;
            try
            {
                RefreshScenes();
                if (_sceneBound.Count == 0) return false;
                var t = c.transform;
                foreach (var bt in _sceneBound)
                    if (bt != null && (t == bt || t.IsChildOf(bt) || bt.IsChildOf(t))) return true;
            }
            catch { }
            return false;
        }

        /// <summary>The game animation weighing the most now (null if there is a one-off action on top or a
        /// scene).</summary>
        internal static AnimationClip CurrentClip(ControllerMixerPlayable cmp, out float normTime)
        {
            normTime = 0f;
            if (cmp == null) return null;
            try { if (cmp.playOnce) return null; } catch { }
            if (InScene(cmp)) return null;
            var acp = cmp.GetAnimator();
            var infos = acp.GetCurrentAnimatorClipInfo(0);
            if (infos == null) return null;
            AnimationClip best = null; float bw = 0f;
            for (int i = 0; i < infos.Length; i++)
            {
                var ci = infos[i];
                if (ci.weight > bw && ci.clip != null) { bw = ci.weight; best = ci.clip; }
            }
            if (best != null) normTime = acp.GetCurrentAnimatorStateInfo(0).normalizedTime;
            return best;
        }

        /// <summary>A game character's animations (its prefab's), by name, and its prefix (van, drt...).</summary>
        static Dictionary<string, AnimationClip> GameClips(string key, out string code)
        {
            code = null;
            var outp = new Dictionary<string, AnimationClip>();
            var tpl = Template(key);
            var cmp = tpl != null ? tpl.GetComponentInChildren<ControllerMixerPlayable>(true) : null;
            var ctrl = cmp != null ? cmp.controller : null;
            if (ctrl == null) return outp;
            int u = ctrl.name.IndexOf('_');
            code = u > 0 ? ctrl.name.Substring(0, u) : null;
            foreach (var c in ctrl.animationClips) if (c != null && !outp.ContainsKey(c.name)) outp[c.name] = c;
            return outp;
        }

        static void HandleBorrow(GameObject owner, string key)
        {
            if (!_borrowMap.TryGetValue(key, out var from) || from == key) return;
            var root = ModelRoot(owner);
            if (root == null) return;
            int id = root.GetInstanceID();
            if (_borrows.ContainsKey(id)) return;
            var cmp = owner.GetComponentInChildren<ControllerMixerPlayable>(true);
            var b = new Borrow { root = root, cmp = cmp, key = key, from = from };
            if (cmp != null)
            {
                var clips = GameClips(from, out b.fromCode);
                foreach (var kv in clips) b.clips[kv.Key] = kv.Value;
            }
            _borrows[id] = b;                                       // even if it isn't valid: so it isn't repeated every second
            if (cmp == null || b.fromCode == null || b.clips.Count == 0)
            {
                Warn("borrow" + key, $"[Animaciones] {key}: no encuentro las animaciones de {from}");
                b.cmp = null;
                return;
            }
            var bones = new List<Transform>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true)) if (t != root.transform) bones.Add(t);
            b.bones = bones.ToArray();
            b.keepR = new Quaternion[b.bones.Length]; b.keepP = new Vector3[b.bones.Length];
            foreach (var t in b.bones) if (t.name == "SKL_000_WAIST") b.hips = t;
            b.hipsRest = RestHips(key);
            b.fromHipsRest = RestHips(from);
            if (b.fromHipsRest.y > 0.01f && b.hipsRest.y > 0.01f) b.hipK = b.hipsRest.y / b.fromHipsRest.y;
            Plugin.L.LogInfo($"[Animaciones] {key} se mueve como {from} ({b.clips.Count} animaciones de {b.fromCode})");
        }

        static Vector3 RestHips(string key)
        {
            var tpl = Template(key);
            if (tpl == null) return Vector3.zero;
            foreach (var t in tpl.GetComponentsInChildren<Transform>(true)) if (t.name == "SKL_000_WAIST") return t.localPosition;
            return Vector3.zero;
        }

        static void LateBorrow()
        {
            if (_borrows.Count == 0) return;
            List<int> gone = null;
            foreach (var kv in _borrows)
            {
                var b = kv.Value;
                if (b.root == null) { (gone ??= new List<int>()).Add(kv.Key); continue; }
                if (b.cmp == null) continue;
                try { DriveBorrow(b); }
                catch (Exception e) { Warn("borrowd" + b.key, "[Animaciones] " + b.key + ": " + e.Message); b.cmp = null; }
            }
            if (gone != null) foreach (var id in gone) _borrows.Remove(id);
        }

        static void DriveBorrow(Borrow b)
        {
            if (InScene(b.cmp))                                                   // the scene rules, right away
            {
                if (!b.scene) { b.scene = true; Plugin.L.LogInfo($"[Animaciones] {b.key}: escena del juego ({_sceneNames}), con sus animaciones"); }
                b.w = 0f;
                return;
            }
            b.scene = false;
            var cur = CurrentClip(b.cmp, out float nt);
            AnimationClip use = null;
            if (cur != null)
            {
                int u = cur.name.IndexOf('_');
                if (u > 0) b.clips.TryGetValue(b.fromCode + cur.name.Substring(u), out use);
            }
            b.w = Mathf.MoveTowards(b.w, use != null ? 1f : 0f, Time.deltaTime / 0.2f);
            if (use != null)
            {
                b.last = use;
                float len = Math.Max(0.001f, use.length);
                b.lastT = use.isLooping ? (nt - (float)Math.Floor(nt)) * len : Math.Min(1f, nt) * len;
            }
            if (b.w <= 0f || b.last == null) return;
            var rt = b.root.transform;
            Vector3 rootP = rt.localPosition; Quaternion rootR = rt.localRotation; Vector3 rootS = rt.localScale;
            for (int i = 0; i < b.bones.Length; i++) { b.keepR[i] = b.bones[i].localRotation; b.keepP[i] = b.bones[i].localPosition; }
            b.last.SampleAnimation(b.root, b.lastT);
            rt.localPosition = rootP; rt.localRotation = rootR; rt.localScale = rootS;
            for (int i = 0; i < b.bones.Length; i++)
            {
                var t = b.bones[i];
                if (t == null) continue;
                var q = t.localRotation;
                t.localRotation = b.w >= 1f ? q : Quaternion.Slerp(b.keepR[i], q, b.w);
                if (t == b.hips && b.hipsRest != Vector3.zero)
                {
                    var p = b.hipsRest + (t.localPosition - b.fromHipsRest) * b.hipK;   // same action, at its height
                    t.localPosition = Vector3.Lerp(b.keepP[i], p, b.w);
                }
                else t.localPosition = b.keepP[i];                                     // rotations only
            }
        }
    }
}
