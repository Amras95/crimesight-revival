// CRIMESIGHT Revival - cursor propio.
//
// El lanzador copia tus imagenes de la carpeta "cursor" (junto a la de mods) a csr_live/cursor:
//   cursor.png          el cursor normal (menus y partida)
//   <nombre>.png        opcional: sustituye un cursor concreto del juego (al moverte, correr, atacar...).
//                       Los nombres de los del juego salen en el registro de BepInEx la primera vez que se usan.
//   hotspot.txt         opcional: el punto que hace clic en cursor.png, "x,y" en pixeles (por defecto 0,0,
//                       la esquina de arriba a la izquierda, como una flecha)
// Solo lo ves tu. Sin imagenes, el juego usa sus cursores de siempre.
using System;
using System.Collections.Generic;
using System.IO;
using HarmonyLib;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class CustomCursor
    {
        static string Dir => Path.Combine(LiveMods.LiveDir, "cursor");
        static readonly Dictionary<string, Texture2D> _tex = new(StringComparer.OrdinalIgnoreCase);
        static Texture2D _main;
        static Vector2 _hot;
        static string _sig = "";
        static float _next;
        static bool _inside;
        static readonly HashSet<string> _logged = new();

        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.Method(typeof(Cursor), nameof(Cursor.SetCursor),
                    new[] { typeof(Texture2D), typeof(Vector2), typeof(CursorMode) });
                h.Patch(m, prefix: new HarmonyMethod(typeof(CustomCursor).GetMethod(nameof(BeforeSet),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Cursor] " + e.Message); }
        }

        // cada pocos segundos: si cambian las imagenes, se recargan y se pone el cursor
        public static void Frame()
        {
            if (Time.unscaledTime < _next) return;
            _next = Time.unscaledTime + 2f;
            string sig = Signature();
            if (sig == _sig) return;
            _sig = sig;
            Load();
            _inside = false;
            Cursor.SetCursor(null, Vector2.zero, CursorMode.Auto);   // el prefijo pone el nuestro (o el del juego)
        }

        static string Signature()
        {
            try
            {
                if (!Directory.Exists(Dir)) return "";
                var parts = new List<string>();
                foreach (var f in Directory.GetFiles(Dir))
                {
                    var fi = new FileInfo(f);
                    parts.Add(fi.Name + ":" + fi.Length + ":" + fi.LastWriteTimeUtc.Ticks);
                }
                parts.Sort(StringComparer.Ordinal);
                return string.Join("|", parts);
            }
            catch { return ""; }
        }

        static void Load()
        {
            foreach (var t in _tex.Values) if (t != null) UnityEngine.Object.Destroy(t);
            _tex.Clear(); _main = null; _hot = Vector2.zero;
            if (!Directory.Exists(Dir)) return;
            foreach (var f in Directory.GetFiles(Dir, "*.png"))
            {
                try
                {
                    var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
                    if (!ImageConversion.LoadImage(tex, File.ReadAllBytes(f), false)) { UnityEngine.Object.Destroy(tex); continue; }
                    tex.wrapMode = TextureWrapMode.Clamp;
                    tex.hideFlags = HideFlags.DontUnloadUnusedAsset;
                    _tex[Path.GetFileNameWithoutExtension(f)] = tex;
                }
                catch (Exception e) { Plugin.L.LogWarning("[Cursor] " + Path.GetFileName(f) + ": " + e.Message); }
            }
            _tex.TryGetValue("cursor", out _main);
            try
            {
                var hp = Path.Combine(Dir, "hotspot.txt");
                if (File.Exists(hp))
                {
                    var p = File.ReadAllText(hp).Split(new[] { ',', ';', ' ', 'x' }, StringSplitOptions.RemoveEmptyEntries);
                    if (p.Length >= 2) _hot = new Vector2(float.Parse(p[0]), float.Parse(p[1]));
                }
            }
            catch { }
            Plugin.L.LogInfo(_tex.Count == 0 ? "[Cursor] cursores del juego" :
                $"[Cursor] {_tex.Count} imagen(es) de cursor" + (_main != null ? $" (cursor.png {_main.width}x{_main.height})" : ""));
        }

        static void BeforeSet(ref Texture2D texture, ref Vector2 hotspot, ref CursorMode cursorMode)
        {
            try
            {
                if (texture == null)
                {
                    if (_main != null) { texture = _main; hotspot = _hot; }
                    return;
                }
                string name = texture.name ?? "";
                if (_logged.Add(name)) Plugin.L.LogInfo($"[Cursor] el juego usa el cursor \"{name}\" ({texture.width}x{texture.height})");
                if (name.Length > 0 && _tex.TryGetValue(name, out var mine) && mine != null && mine.Pointer != texture.Pointer)
                {
                    // mismo punto de clic, a la escala de la imagen nueva
                    hotspot = new Vector2(hotspot.x * mine.width / Math.Max(1, texture.width),
                                          hotspot.y * mine.height / Math.Max(1, texture.height));
                    texture = mine;
                }
            }
            catch { }
        }
    }
}
