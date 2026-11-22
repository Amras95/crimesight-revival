// CRIMESIGHT Revival - pixeles de una textura sin pasar uno a uno por Il2Cpp.
//
// GetPixels32/SetPixels32 devuelven/piden un array de Il2Cpp: leerlo o rellenarlo elemento a elemento desde el plugin
// cuesta mucho (en una imagen grande, segundos). Aqui se copia de golpe la memoria del array (cabecera de 4 punteros +
// datos) y se carga con LoadRawTextureData (RGBA32: los mismos bytes que Color32).
using System;
using System.Runtime.InteropServices;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class Px
    {
        /// <summary>Un Color32 sin llamar a su constructor (cada llamada a un metodo de Unity desde el plugin pasa por
        /// Il2Cpp y cuesta; en un bucle por pixel, segundos). Lo mismo con Mathf: en los bucles, matematicas de C#.</summary>
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

        /// <summary>Una textura RGBA32 nueva con estos pixeles (filas de abajo a arriba, como GetPixels32).</summary>
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
