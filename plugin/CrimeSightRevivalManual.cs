// CRIMESIGHT Revival - "Manual online" abre la wiki del proyecto.
//
// El boton del juego llevaba a la pagina de Konami del manual, que ahora solo dice que el juego ya no esta en
// servicio. Se cambia por la wiki de CRIMESIGHT Revival en GitHub (las demas direcciones no se tocan).
using System;
using HarmonyLib;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class Manual
    {
        public const string Wiki = "https://github.com/Amras95/crimesight-revival/wiki";

        public static void Init(Harmony h)
        {
            try
            {
                h.Patch(AccessTools.Method(typeof(OutGameManager), "GetURLOnlineManual"),
                    postfix: new HarmonyMethod(typeof(Manual), nameof(AfterManualUrl)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Manual] " + e.Message); }
            try
            {
                h.Patch(AccessTools.Method(typeof(Application), nameof(Application.OpenURL), new[] { typeof(string) }),
                    prefix: new HarmonyMethod(typeof(Manual), nameof(BeforeOpenUrl)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Manual] " + e.Message); }
        }

        static void AfterManualUrl(ref string __result) => __result = Wiki;

        // por si algun boton abre la pagina de Konami del juego sin pasar por GetURLOnlineManual
        static void BeforeOpenUrl(ref string url)
        {
            if (url != null && url.IndexOf("konami.com/games/crimesight", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                Plugin.L.LogInfo("[Manual] " + url + " -> wiki");
                url = Wiki;
            }
        }
    }
}
