// CRIMESIGHT Revival - end of match: names on the Results screen and "Rematch" after a Quick Match.
//
// Names: the server's "StartResultPhase" carries the player id and name of each role (detective, criminal, irene,
// watson). GameManager.ResultPhaseCallback looks each id up in the game's player list and, when the name it gets is
// "", takes the server's name instead. A role whose name was never filled in is null, not "", so it kept no name:
// in a 2v2 (one person and three AIs) the last role (Irene or Watson) showed an empty name. After the callback, any
// role still without a name gets the server's.
// A match won by deduction doesn't go through ResultPhaseCallback but through GameManager.OnAnswerReturn, which only
// fills three of the names (Watson, and in some line-ups Irene, stayed empty): the same is done after it, with the
// name lists of the answer phase (AnswerPhaseData).
// A match that ends by forfeit takes neither path (the game builds the result itself), so, as a last resort, right
// before the Results screen writes its texts (ResultHud.SetText / SetSideInfomations) any name still missing is
// taken from the room's member list (each member carries its role).
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
                var pre = new HarmonyMethod(typeof(ResultNames).GetMethod(nameof(BeforeHud),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic));
                foreach (var name in new[] { nameof(ResultHud.SetText), nameof(ResultHud.SetSideInfomations) })
                {
                    var hm = AccessTools.Method(typeof(ResultHud), name);
                    if (hm == null) Plugin.L.LogWarning("[Results] ResultHud." + name + " not found");
                    else h.Patch(hm, prefix: pre);
                }
                var a = AccessTools.Method(typeof(GameManager), nameof(GameManager.OnAnswerReturn));
                if (a == null) Plugin.L.LogWarning("[Results] GameManager.OnAnswerReturn not found");
                else h.Patch(a, postfix: new HarmonyMethod(typeof(ResultNames).GetMethod(nameof(AfterAnswer),
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

        static string First(Il2CppSystem.Collections.Generic.List<string> l)
        {
            try
            {
                if (l == null || l.Count == 0) return null;
                var s = l[0];
                if (string.IsNullOrEmpty(s)) return null;
                try { return UiBaseManager.GetDummyNameFromName(ref s) ?? s; } catch { return s; }
            }
            catch { return null; }
        }

        static string Dummy(string s)
        {
            if (string.IsNullOrEmpty(s)) return null;
            try { return UiBaseManager.GetDummyNameFromName(ref s) ?? s; } catch { return s; }
        }

        /// <summary>Right before the Results screen writes its texts: the names still missing, from the room list.</summary>
        static void BeforeHud()
        {
            try
            {
                var r = GameManager.instance?.resultInfo;
                var members = NetworkManager.Instance?.GetCurrentRoom()?.Members;
                if (r == null || members == null) return;
                string det = null, cri = null, ire = null, wat = null;
                int detI = -1, criI = -1, ireI = -1, watI = -1;
                var hs = NetworkManager.GetHostSystem();
                for (int i = 0; i < members.Count; i++)
                {
                    var x = members[i];
                    if (x == null) continue;
                    var n = Dummy(x.Name);
                    if (n == null) continue;
                    int idx = -1;
                    try { string pid = x.PlayerId; if (hs != null && !string.IsNullOrEmpty(pid)) idx = hs.SearchMemberIndex(ref pid); } catch { }
                    if (x.IsCriminal) { if (cri == null) { cri = n; criI = idx; } }
                    else if (x.IsIrene) { if (ire == null) { ire = n; ireI = idx; } }
                    else if (x.IsWatson) { if (wat == null) { wat = n; watI = idx; } }
                    else if (x.IsDetective) { if (det == null) { det = n; detI = idx; } }
                }
                // the name's colour is the player's (by their number, 0..3); an unknown number shows it in plain black
                bool Bad(int v) => v < 0 || v > 3;
                int k = 0;
                if (Bad(r.GetDetectivePlayerId()) && !Bad(detI)) { r.SetDetectivePlayerId(ref detI); k++; }
                if (Bad(r.GetCriminalPlayerId()) && !Bad(criI)) { r.SetCriminalPlayerId(ref criI); k++; }
                if (Bad(r.GetIreneCriminalPlayerId()) && !Bad(ireI)) { r.SetIrenePlayerId(ref ireI); k++; }
                if (Bad(r.GetWatsonPlayerId()) && !Bad(watI)) { r.SetWatsonPlayerId(ref watI); k++; }
                if (k > 0) Plugin.L.LogInfo($"[Results] {k} role colour(s) taken from the room list");
                int c = 0;
                if (string.IsNullOrEmpty(r.DetectivePlayerName) && det != null) { r.DetectivePlayerName = det; c++; }
                if (string.IsNullOrEmpty(r.CriminalPlayerName) && cri != null) { r.CriminalPlayerName = cri; c++; }
                if (string.IsNullOrEmpty(r.IrenePlayerName) && ire != null) { r.IrenePlayerName = ire; c++; }
                if (string.IsNullOrEmpty(r.WatsonPlayerName) && wat != null) { r.WatsonPlayerName = wat; c++; }
                if (c > 0) Plugin.L.LogInfo($"[Results] {c} role name(s) taken from the room list");
            }
            catch (Exception e) { Plugin.L.LogWarning("[Results] " + e.Message); }
        }

        static void AfterAnswer(AnswerPhaseData __0)
        {
            try
            {
                var r = GameManager.instance?.resultInfo;
                if (r == null || __0 == null) return;
                int n = 0;
                string s;
                if (string.IsNullOrEmpty(r.DetectivePlayerName) && (s = First(__0.SherlockNames)) != null) { r.DetectivePlayerName = s; n++; }
                if (string.IsNullOrEmpty(r.CriminalPlayerName) && (s = First(__0.MoriartyNames)) != null) { r.CriminalPlayerName = s; n++; }
                if (string.IsNullOrEmpty(r.IrenePlayerName) && (s = First(__0.IreneNames)) != null) { r.IrenePlayerName = s; n++; }
                if (string.IsNullOrEmpty(r.WatsonPlayerName) && (s = First(__0.WatsonNames)) != null) { r.WatsonPlayerName = s; n++; }
                if (n > 0) Plugin.L.LogInfo($"[Results] {n} role name(s) taken from the answer phase");
            }
            catch (Exception e) { Plugin.L.LogWarning("[Results] " + e.Message); }
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
