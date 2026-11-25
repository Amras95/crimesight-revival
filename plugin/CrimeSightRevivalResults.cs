// CRIMESIGHT Revival - end of match: names on the Results screen and "Rematch" after a Quick Match.
//
// Names: the server's "StartResultPhase" carries the player id and name of each role (detective, criminal, irene,
// watson). GameManager.ResultPhaseCallback looks each id up in the game's player list and, when the name it gets is
// "", takes the server's name instead. A role whose name was never filled in is null, not "", so it kept no name:
// in a 2v2 (one person and three AIs) the last role (Irene or Watson) showed an empty name. After the callback, any
// role still without a name gets the server's.
//
// Rematch: in the original game, the Rematch popup (OutGameRematchPopup.ClickConfirm) checks the current room: if it
// is a Quick Match room (MatchRoom.IsQuick), it leaves the room and goes back to the Quick Match menu to search again;
// otherwise it asks the server for a rematch in the same room. With the Revival server the Quick Match path ends with
// only the room background on screen. Here a Quick Match room gets the same rematch as any other room: everyone stays
// in the room and the next match is set up there, which is also what you want with few players online.
using System;
using HarmonyLib;

using Dict = Il2CppSystem.Collections.Generic.Dictionary<string, Il2CppSystem.Object>;

namespace CrimeSightRevival.Mods
{
    static class ResultNames
    {
        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.Method(typeof(GameManager), nameof(GameManager.ResultPhaseCallback));
                if (m == null) { Plugin.L.LogWarning("[Results] GameManager.ResultPhaseCallback not found"); return; }
                h.Patch(m, postfix: new HarmonyMethod(typeof(ResultNames).GetMethod(nameof(After),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Results] " + e.Message); }
        }

        static string Server(Dict d, string key)
        {
            try
            {
                if (d == null || !d.ContainsKey(key)) return null;
                var s = d[key]?.ToString();
                if (string.IsNullOrEmpty(s)) return null;
                try { return UiBaseManager.GetDummyNameFromName(ref s) ?? s; } catch { return s; }   // streamer mode names
            }
            catch { return null; }
        }

        static void After(Dict __0)
        {
            try
            {
                var r = GameManager.instance?.resultInfo;
                if (r == null) return;
                int n = 0;
                string s;
                if (string.IsNullOrEmpty(r.DetectivePlayerName) && (s = Server(__0, "detective_name")) != null) { r.DetectivePlayerName = s; n++; }
                if (string.IsNullOrEmpty(r.CriminalPlayerName) && (s = Server(__0, "criminal_name")) != null) { r.CriminalPlayerName = s; n++; }
                if (string.IsNullOrEmpty(r.IrenePlayerName) && (s = Server(__0, "irene_name")) != null) { r.IrenePlayerName = s; n++; }
                if (string.IsNullOrEmpty(r.WatsonPlayerName) && (s = Server(__0, "watson_name")) != null) { r.WatsonPlayerName = s; n++; }
                if (n > 0) Plugin.L.LogInfo($"[Results] {n} role name(s) taken from the server");
            }
            catch (Exception e) { Plugin.L.LogWarning("[Results] " + e.Message); }
        }
    }

    static class QuickRematch
    {
        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.Method(typeof(OutGameRematchPopup), "ClickConfirm");
                if (m == null) { Plugin.L.LogWarning("[Rematch] OutGameRematchPopup.ClickConfirm not found"); return; }
                h.Patch(m, prefix: new HarmonyMethod(typeof(QuickRematch).GetMethod(nameof(BeforeConfirm),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Rematch] " + e.Message); }
        }

        static bool BeforeConfirm(OutGameRematchPopup __instance)
        {
            try
            {
                var room = NetworkManager.Instance?.GetCurrentRoom();
                if (room == null || !room.IsQuick) return true;          // normal room: the game's own rematch
                Plugin.L.LogInfo("[Rematch] Quick Match room: rematch in the same room");
                __instance.Rematch();
                return false;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Rematch] " + e.Message); return true; }
        }
    }
}
