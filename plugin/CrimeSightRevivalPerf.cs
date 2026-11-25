// CRIMESIGHT Revival - stutter meter.
//
// Measures how long each part of the plugin takes every frame and logs ("[Rendimiento] ...") the ones that
// take more than 25 ms, and the frames that take more than 150 ms (with how long the plugin took in them): that way
// you know
// whether a stutter comes from the plugin (and which part) or from the game itself.
using System.Collections.Generic;
using System.Diagnostics;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class Perf
    {
        static readonly Stopwatch _sw = Stopwatch.StartNew();
        static readonly Dictionary<string, float> _lastLog = new();
        static double _ours;                 // plugin ms in the previous frame
        static string _worst = ""; static double _worstMs;
        static int _logs;

        public static long T() => _sw.ElapsedTicks;

        public static void Done(string name, long t0)
        {
            double ms = (_sw.ElapsedTicks - t0) * 1000.0 / Stopwatch.Frequency;
            _ours += ms;
            if (ms > _worstMs) { _worstMs = ms; _worst = name; }
            if (ms < 25 || _logs > 200) return;
            if (_lastLog.TryGetValue(name, out var t) && Time.unscaledTime - t < 5f) return;
            _lastLog[name] = Time.unscaledTime;
            _logs++;
            Plugin.L.LogWarning($"[Rendimiento] {name} tardo {ms:0} ms");
        }

        /// <summary>At the start of each frame: if the previous one was slow, it logs it.</summary>
        public static void Frame()
        {
            float dt = Time.unscaledDeltaTime;
            if (dt > 0.15f && _logs <= 200 && Time.frameCount > 300)
            {
                _logs++;
                Plugin.L.LogWarning($"[Rendimiento] fotograma de {dt * 1000:0} ms (plugin: {_ours:0} ms, lo que mas: {_worst} {_worstMs:0} ms)");
            }
            _ours = 0; _worstMs = 0; _worst = "";
        }
    }
}
