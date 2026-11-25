// CRIMESIGHT Revival - "Online manual" opens the project's wiki.
//
// The game's button led to Konami's manual page, which now only says the game is no longer in
// service. It is swapped for the CRIMESIGHT Revival wiki on GitHub (the other addresses aren't touched).
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

        // in case some button opens Konami's game page without going through GetURLOnlineManual
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
