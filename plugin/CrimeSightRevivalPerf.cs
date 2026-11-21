// CRIMESIGHT Revival - medidor de tirones.
//
// Mide cuanto tarda cada parte del plugin en cada fotograma y apunta en el registro ("[Rendimiento] ...") las que
// tardan mas de 25 ms, y los fotogramas que tardan mas de 150 ms (con lo que tardo el plugin en ellos): asi se sabe
// si un tiron viene del plugin (y de que parte) o del propio juego.
using System.Collections.Generic;
using System.Diagnostics;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class Perf
    {
        static readonly Stopwatch _sw = Stopwatch.StartNew();
        static readonly Dictionary<string, float> _lastLog = new();
        static double _ours;                 // ms del plugin en el fotograma anterior
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

        /// <summary>Al principio de cada fotograma: si el anterior fue lento, lo apunta.</summary>
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
