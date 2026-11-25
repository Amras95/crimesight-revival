// CRIMESIGHT Revival - a texture's pixels without going one by one through Il2Cpp.
//
// GetPixels32/SetPixels32 return/take an Il2Cpp array: reading or filling it element by element from the plugin
// is very slow (on a big image, seconds). Here the array's memory is copied in one go (header of 4 pointers +
// data) and loaded with LoadRawTextureData (RGBA32: the same bytes as Color32).
using System;
using System.Runtime.InteropServices;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class Px
    {
        /// <summary>A Color32 without calling its constructor (each call to a Unity method from the plugin goes
        /// through
        /// Il2Cpp and is costly; in a per-pixel loop, seconds). Same with Mathf: in the loops, C# maths.</summary>
        public static Color32 C(byte r, byte g, byte b, byte a) => new Color32 { r = r, g = g, b = b, a = a };

        public static unsafe Color32[] Get(Texture2D t)
        {
            var arr = t.GetPixels32();
            int n = arr.Length;
            var outp = new Color32[n];
            if (n == 0) return outp;
            var src = (byte*)IntPtr.Add(arr.Pointer, 4 * IntPtr.Size).ToPointer();
            fixed (Color32* dst = outp) Buffer.MemoryCopy(src, dst, (long)n * 4, (long)n * 4);
            return outp;
        }

        /// <summary>A new RGBA32 texture with these pixels (rows bottom to top, like GetPixels32).</summary>
        public static Texture2D Make(int w, int h, Color32[] px, string name)
        {
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false) { name = name, hideFlags = HideFlags.DontUnloadUnusedAsset, wrapMode = TextureWrapMode.Clamp };
            Set(t, px);
            return t;
        }

        public static void Set(Texture2D t, Color32[] px)
        {
            var h = GCHandle.Alloc(px, GCHandleType.Pinned);
            try { t.LoadRawTextureData(h.AddrOfPinnedObject(), px.Length * 4); }
            finally { h.Free(); }
            t.Apply(false, false);
        }
    }
}
