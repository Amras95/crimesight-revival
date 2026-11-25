// CRIMESIGHT Revival - "Forfeit" to leave a match against the AI.
//
// The game already has a "Forfeit" button in the match settings, but it only shows it to Moriarty
// and from turn 4 on (and never in training rooms). Now it is shown to every role from the
// first turn, in every online match, during the command phase only (as the game's Forfeit window says). With a person
// on your team, the server asks them first (vote, see
// CrimeSightRevivalTeam.cs); otherwise your side forfeits right away.
using System;
using System.Collections.Generic;
using HarmonyLib;

namespace CrimeSightRevival.Mods
{
    static class Quit
    {
        public static void Init(Harmony h)
        {
            Patch(h, AccessTools.Method(typeof(GameManager), nameof(GameManager.IsEnableSurrender)), postfix: nameof(AfterEnable));
            Patch(h, AccessTools.Method(typeof(GameManager), nameof(GameManager.RunSurrender)), prefix: nameof(BeforeRun));
            Patch(h, AccessTools.Method(typeof(GameManager), "AbandonCallback"), prefix: nameof(BeforeAbandon));
            Patch(h, AccessTools.Method(typeof(ResultInfo), nameof(ResultInfo.SetResultType)), postfix: nameof(AfterResult));
            Patch(h, AccessTools.Method(typeof(ResultInfo), nameof(ResultInfo.SetStateType)), postfix: nameof(AfterState));
        }

        static void Patch(Harmony h, System.Reflection.MethodBase m, string prefix = null, string postfix = null, string finalizer = null)
        {
            try
            {
                if (m == null) { Plugin.L.LogWarning("[Salir] metodo no encontrado"); return; }
                HarmonyMethod Hm(string n) => n == null ? null : new HarmonyMethod(typeof(Quit).GetMethod(n,
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic));
                h.Patch(m, prefix: Hm(prefix), postfix: Hm(postfix), finalizer: Hm(finalizer));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Salir] " + m?.Name + ": " + e.Message); }
        }

        // The only person in the room (the server's AIs have ids "bot0001"...)
        static bool Alone()
        {
            try
            {
                var room = NetworkManager.Instance?.currentRoom;
                var members = room?.Members;
                if (members == null) return false;
                int people = 0;
                for (int i = 0; i < members.Count; i++)
                {
                    var id = members[i]?.PlayerId ?? "";
                    if (!Team.IsAi(id)) people++;               // players an AI took over don't count
                }
                return people <= 1;
            }
            catch { return false; }
        }

        static void AfterEnable(ref bool __result)
        {
            try
            {
                if (!__result && !ReplayManager.IsReplay() && GameManager.instance != null && GameManager.instance.IsInstructPhase())
                    __result = true;
            }
            catch { }
        }

        // When someone forfeits, the game decides the results screen assuming it was
        // Moriarty who forfeited: Moriarty's side loses and Sherlock's wins. The Revival server says which
        // side really wins (csr_winner) and the result is corrected here if needed.
        static string _winner;
        static ResultInfo.StateType? _state;

        static void AfterState(ResultInfo __instance)
        {
            try
            {
                if (_state == null || __instance == null) return;
                __instance.stateType = _state.Value;
                _state = null;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Salir] cartel: " + e.Message); }
        }
        static bool _iSurrendered;
        static float _winnerUntil;

        static void BeforeAbandon(Il2CppSystem.Collections.Generic.Dictionary<string, Il2CppSystem.Object> dict)
        {
            _winner = null;
            try
            {
                if (dict != null && dict.ContainsKey("csr_winner"))
                {
                    _winner = dict["csr_winner"]?.ToString();
                    _winnerUntil = UnityEngine.Time.unscaledTime + 30f;
                }
                Plugin.L.LogInfo("[Salir] fin por abandono, gana: " + (_winner ?? "(el servidor no lo dice)"));
                string role = dict != null && dict.ContainsKey("csr_quitter_role") ? dict["csr_quitter_role"]?.ToString() : null;
                string reason = dict != null && dict.ContainsKey("csr_reason") ? dict["csr_reason"]?.ToString() : "surrender";
                SetNotice(role, reason);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Salir] " + e.Message); }
        }

        // The game's notice on forfeiting ("Moriarty has abandoned his devious plan.") is swapped for one
        // with who it really was. If it is Moriarty forfeiting, the game's is left.
        const string NoticeId = "ctg_name_info_game_end_surrender";
        static string _original;
        static readonly Dictionary<string, string> RoleNames = new()
        {
            ["detective"] = "Sherlock", ["criminal"] = "Moriarty", ["irene"] = "Irene", ["watson"] = "Watson",
        };
        // game language order: Japanese, English, French, Italian, German, Spanish, Portuguese, Russian,
        // Korean, Simplified Chinese, Traditional Chinese
        static readonly string[] Surrendered =
        {
            "{0}が降参しました。", "{0} has surrendered.", "{0} a abandonné.", "{0} si è arreso.",
            "{0} hat aufgegeben.", "{0} se ha rendido.", "{0} desistiu.", "{0} сдаётся.",
            "{0}이(가) 항복했습니다.", "{0} 认输了。", "{0} 認輸了。",
        };
        static readonly string[] Left =
        {
            "{0}がゲームから抜けました。", "{0} has left the match.", "{0} a quitté la partie.",
            "{0} ha lasciato la partita.", "{0} hat das Spiel verlassen.", "{0} ha abandonado la partida.",
            "{0} saiu da partida.", "{0} покинул матч.", "{0}이(가) 게임을 나갔습니다.", "{0} 离开了对局。",
            "{0} 離開了對局。",
        };

        static void SetNotice(string role, string reason)
        {
            var tm = TextManager.Instance;
            if (tm == null || tm.LangText == null) return;
            if (_original == null && tm.LangText.ContainsKey(NoticeId)) _original = tm.LangText[NoticeId];
            string text;
            if (role == null || !RoleNames.TryGetValue(role, out var who) || (role == "criminal" && reason != "left"))
                text = _original;
            else
            {
                int lang = Math.Max(0, Math.Min(Surrendered.Length - 1, (int)tm.GetLangType()));
                text = string.Format(reason == "left" ? Left[lang] : Surrendered[lang], who);
            }
            if (text != null) tm.LangText[NoticeId] = text;
        }

        // After the game saves the result, it is corrected by writing it directly
        static void AfterResult(ResultInfo __instance)
        {
            try
            {
                if (__instance == null || UnityEngine.Time.unscaledTime > _winnerUntil) return;
                var type = __instance.resultType;
                if (type != ResultInfo.ResultType.WIN && type != ResultInfo.ResultType.LOSE) return;
                bool moriartySide = type == ResultInfo.ResultType.LOSE;     // that is how the game decides it
                bool moriartyWins;
                if (_iSurrendered) moriartyWins = !moriartySide;           // you forfeited: the other side wins
                else if (_winner != null) moriartyWins = _winner == "moriarty";
                else return;
                bool won = moriartySide == moriartyWins;
                __instance.resultType = won ? ResultInfo.ResultType.WIN : ResultInfo.ResultType.LOSE;
                // and the banner of who wins ("Sherlock achieves victory" / Moriarty's), which the game sets
                // next assuming Sherlock won
                _state = moriartyWins ? ResultInfo.StateType.KILL_SUCCESS : ResultInfo.StateType.ARREST_SUCCESS;
                Plugin.L.LogInfo("[Salir] resultado: " + (won ? "victoria" : "derrota") + ", gana " + (moriartyWins ? "Moriarty" : "Sherlock"));
                _iSurrendered = false; _winner = null;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Salir] resultado: " + e.Message); }
        }

        // The game's "Forfeit": it only allows Moriarty, from turn 4 and outside training. Here the server
        // is told the same thing the game would tell it, for any role and turn. It ends the match, or first asks
        // a teammate who is a person (then the match only ends if they agree).
        static bool BeforeRun()
        {
            try
            {
                if (ReplayManager.IsReplay()) return true;
                var nm = NetworkManager.Instance;
                if (nm == null) return true;
                string msg = "{\"surrenderPlayerId\":\"" + (ApiServer.PlayerId ?? "") + "\"}";
                _iSurrendered = Alone();             // with other people the server says who wins (csr_winner)
                if (_iSurrendered) _winnerUntil = UnityEngine.Time.unscaledTime + 60f;
                nm.Abandon(msg,
                    Il2CppInterop.Runtime.DelegateSupport.ConvertDelegate<Il2CppSystem.Action>(new Action(() =>
                        Plugin.L.LogInfo("[Salir] te has rendido"))),
                    Il2CppInterop.Runtime.DelegateSupport.ConvertDelegate<Il2CppSystem.Action<string, NetworkManager.ErrorCode>>(
                        new Action<string, NetworkManager.ErrorCode>((m, c) => Plugin.L.LogWarning("[Salir] el servidor no acepto la rendicion: " + m))));
                Plugin.L.LogInfo("[Salir] rendirse para salir de la partida");
                return false;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Salir] " + e.Message); return true; }
        }
    }
}
