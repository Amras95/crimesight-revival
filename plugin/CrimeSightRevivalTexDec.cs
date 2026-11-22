// CRIMESIGHT Revival - texturas de los modelos propios descodificadas fuera del hilo del juego.
//
// ImageConversion.LoadImage solo se puede usar en el hilo del juego, y un PNG de 4096x4096 tarda medio segundo:
// al empezar la partida se congelaba la imagen (con los personajes aun en T). Aqui el PNG se descodifica en otro
// hilo (calculo puro), se reduce a 2048 como mucho (de sobra para un personaje en pantalla) y se le calculan los
// mipmaps; en el hilo del juego solo queda copiar los bytes a la textura (LoadRawTextureData). Lo que no se sepa
// leer (JPEG, PNG entrelazado o de menos de 8 bits) devuelve null y se carga como antes.
using System;
using System.IO;
using System.IO.Compression;

namespace CrimeSightRevival.Mods
{
    static class TexDec
    {
        public const int Max = 2048;

        /// <summary>Rellena raw/rw/rh/rmips de la imagen si es un PNG que se sabe leer.</summary>
        public static void Prepare(Glb.Image img)
        {
            try
            {
                var px = Png(img.data, out int w, out int h);
                if (px == null) return;
                while (Math.Max(w, h) > Max && w > 1 && h > 1) px = Half(px, ref w, ref h);
                img.raw = Mips(px, w, h, out img.rmips);
                img.rw = w; img.rh = h;
            }
            catch { img.raw = null; }
        }

        public static int MipCount(int w, int h) { int n = 1, m = Math.Max(w, h); while (m > 1) { m >>= 1; n++; } return n; }

        /// <summary>RGBA de abajo a arriba (como las texturas de Unity), o null.</summary>
        static byte[] Png(byte[] d, out int w, out int h)
        {
            w = h = 0;
            if (d == null || d.Length < 33 || d[0] != 0x89 || d[1] != 'P' || d[2] != 'N' || d[3] != 'G') return null;
            int depth = 0, type = 0, inter = 0;
            byte[] pal = null, palA = null;
            var idat = new MemoryStream();
            int p = 8;
            while (p + 8 <= d.Length)
            {
                int len = (d[p] << 24) | (d[p + 1] << 16) | (d[p + 2] << 8) | d[p + 3];
                string tag = "" + (char)d[p + 4] + (char)d[p + 5] + (char)d[p + 6] + (char)d[p + 7];
                int s = p + 8;
                if (len < 0 || s + len > d.Length) return null;
                if (tag == "IHDR")
                {
                    w = (d[s] << 24) | (d[s + 1] << 16) | (d[s + 2] << 8) | d[s + 3];
                    h = (d[s + 4] << 24) | (d[s + 5] << 16) | (d[s + 6] << 8) | d[s + 7];
                    depth = d[s + 8]; type = d[s + 9]; inter = d[s + 12];
                }
                else if (tag == "PLTE") { pal = new byte[len]; Buffer.BlockCopy(d, s, pal, 0, len); }
                else if (tag == "tRNS") { palA = new byte[len]; Buffer.BlockCopy(d, s, palA, 0, len); }
                else if (tag == "IDAT") idat.Write(d, s, len);
                else if (tag == "IEND") break;
                p = s + len + 4;
            }
            if (w <= 0 || h <= 0 || w > 16384 || h > 16384 || inter != 0 || (depth != 8 && depth != 16)) return null;
            int ch = type switch { 0 => 1, 2 => 3, 3 => 1, 4 => 2, 6 => 4, _ => 0 };
            if (ch == 0 || (type == 3 && (pal == null || depth != 8))) return null;
            int bpp = ch * depth / 8, stride = w * bpp;
            var raw = new byte[(long)h * (stride + 1)];
            idat.Position = 0;
            using (var z = new ZLibStream(idat, CompressionMode.Decompress))
            {
                int got = 0;
                while (got < raw.Length) { int r = z.Read(raw, got, raw.Length - got); if (r <= 0) return null; got += r; }
            }
            // quitar los filtros fila a fila (en el mismo array)
            for (int y = 0; y < h; y++)
            {
                int row = y * (stride + 1), f = raw[row], cur = row + 1, prev = row - stride;   // prev: fila anterior (sus datos)
                bool first = y == 0;
                switch (f)
                {
                    case 0: break;
                    case 1: for (int x = bpp; x < stride; x++) raw[cur + x] += raw[cur + x - bpp]; break;
                    case 2: if (!first) for (int x = 0; x < stride; x++) raw[cur + x] += raw[prev + x]; break;
                    case 3:
                        for (int x = 0; x < stride; x++)
                        {
                            int a = x >= bpp ? raw[cur + x - bpp] : 0, b = first ? 0 : raw[prev + x];
                            raw[cur + x] += (byte)((a + b) >> 1);
                        }
                        break;
                    case 4:
                        for (int x = 0; x < stride; x++)
                        {
                            int a = x >= bpp ? raw[cur + x - bpp] : 0, b = first ? 0 : raw[prev + x], c = (x >= bpp && !first) ? raw[prev + x - bpp] : 0;
                            int pp = a + b - c, pa = Math.Abs(pp - a), pb = Math.Abs(pp - b), pc = Math.Abs(pp - c);
                            raw[cur + x] += (byte)(pa <= pb && pa <= pc ? a : pb <= pc ? b : c);
                        }
                        break;
                    default: return null;
                }
            }
            var o = new byte[(long)w * h * 4];
            int step = depth / 8;                                     // 16 bits: se queda el byte alto
            for (int y = 0; y < h; y++)
            {
                int src = y * (stride + 1) + 1, dst = (h - 1 - y) * w * 4;
                for (int x = 0; x < w; x++, dst += 4)
                {
                    int q = src + x * bpp;
                    switch (type)
                    {
                        case 0: { byte g = raw[q]; o[dst] = o[dst + 1] = o[dst + 2] = g; o[dst + 3] = 255; break; }
                        case 4: { byte g = raw[q]; o[dst] = o[dst + 1] = o[dst + 2] = g; o[dst + 3] = raw[q + step]; break; }
                        case 2: o[dst] = raw[q]; o[dst + 1] = raw[q + step]; o[dst + 2] = raw[q + 2 * step]; o[dst + 3] = 255; break;
                        case 6: o[dst] = raw[q]; o[dst + 1] = raw[q + step]; o[dst + 2] = raw[q + 2 * step]; o[dst + 3] = raw[q + 3 * step]; break;
                        case 3:
                            {
                                int i = raw[q];
                                if (i * 3 + 2 < pal.Length) { o[dst] = pal[i * 3]; o[dst + 1] = pal[i * 3 + 1]; o[dst + 2] = pal[i * 3 + 2]; }
                                o[dst + 3] = palA != null && i < palA.Length ? palA[i] : (byte)255;
                                break;
                            }
                    }
                }
            }
            return o;
        }

        /// <summary>La mitad de tamano (media de cada 2x2).</summary>
        static byte[] Half(byte[] s, ref int w, ref int h)
        {
            int nw = Math.Max(1, w >> 1), nh = Math.Max(1, h >> 1);
            var o = new byte[(long)nw * nh * 4];
            for (int y = 0; y < nh; y++)
            {
                int y0 = Math.Min(h - 1, y * 2), y1 = Math.Min(h - 1, y * 2 + 1);
                for (int x = 0; x < nw; x++)
                {
                    int x0 = Math.Min(w - 1, x * 2), x1 = Math.Min(w - 1, x * 2 + 1);
                    int a = (y0 * w + x0) * 4, b = (y0 * w + x1) * 4, c = (y1 * w + x0) * 4, e = (y1 * w + x1) * 4, d = (y * nw + x) * 4;
                    for (int k = 0; k < 4; k++) o[d + k] = (byte)((s[a + k] + s[b + k] + s[c + k] + s[e + k] + 2) >> 2);
                }
            }
            w = nw; h = nh;
            return o;
        }

        /// <summary>El nivel 0 seguido de todos sus mipmaps (como los espera LoadRawTextureData).</summary>
        static byte[] Mips(byte[] px, int w, int h, out int count)
        {
            count = MipCount(w, h);
            long total = 0;
            for (int l = 0; l < count; l++) total += (long)Math.Max(1, w >> l) * Math.Max(1, h >> l) * 4;
            var o = new byte[total];
            Buffer.BlockCopy(px, 0, o, 0, px.Length);
            long at = px.Length;
            int cw = w, chh = h;
            var cur = px;
            for (int l = 1; l < count; l++)
            {
                cur = Half(cur, ref cw, ref chh);
                Buffer.BlockCopy(cur, 0, o, (int)at, cur.Length);
                at += cur.Length;
            }
            return o;
        }
    }
}
