// CRIMESIGHT Revival - un personaje nuevo se mueve como el personaje del juego que se le elige en el lanzador.
//
// Cada sitio (A..F) juega como su original, y el juego le pone sus animaciones (las de ese personaje: van_..., drt_...).
// Si en ese sitio sale un personaje nuevo con "Animaciones de: Dorothy", despues de las animaciones del juego
// (LateUpdate, antes de que el esqueleto propio copie los huesos) se pone en sus huesos la animacion equivalente de
// Dorothy: misma accion (reposo, andar, correr...) en el mismo punto. Solo giros; la cadera, con su altura escalada.
// Mientras el juego hace una accion suelta (PlayClip: atacar, coger...) se deja la del juego, con un fundido corto.
// Las animaciones propias (reposo/andar/correr del .glb) van despues y mandan sobre estas.
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
            public Quaternion[] keepR; public Vector3[] keepP;
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

        /// <summary>La animacion del juego que pesa mas ahora (null si hay una accion suelta encima).</summary>
        internal static AnimationClip CurrentClip(ControllerMixerPlayable cmp, out float normTime)
        {
            normTime = 0f;
            if (cmp == null) return null;
            try { if (cmp.playOnce) return null; } catch { }
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

        /// <summary>Las animaciones de un personaje del juego (las de su prefab), por nombre, y su prefijo (van, drt...).</summary>
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
            _borrows[id] = b;                                       // aunque no valga: asi no se repite cada segundo
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
                    var p = b.hipsRest + (t.localPosition - b.fromHipsRest) * b.hipK;   // misma accion, a su altura
                    t.localPosition = Vector3.Lerp(b.keepP[i], p, b.w);
                }
                else t.localPosition = b.keepP[i];                                     // solo giros
            }
        }
    }
}
