// CRIMESIGHT Revival - "Rendirse" para salir de una partida contra la IA.
//
// El juego ya trae un boton "Rendirse" en los ajustes de la partida, pero solo lo ensena a Moriarty
// y a partir del turno 4 (y nunca en las salas de entrenamiento). Cuando eres la unica persona de la
// sala (contra IAs o en el entrenamiento), aqui se ensena siempre y vale para cualquier papel: asi
// se puede salir de una partida sin cerrar el juego. Con mas personas en la sala se deja como estaba.
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

        // La unica persona de la sala (las IAs del servidor tienen ids "bot0001"...)
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
                    if (!id.StartsWith("bot", StringComparison.Ordinal)) people++;
                }
                return people <= 1;
            }
            catch { return false; }
        }

        static void AfterEnable(ref bool __result)
        {
            try { if (!__result && Alone() && !ReplayManager.IsReplay()) __result = true; }
            catch { }
        }

        // Al rendirse alguien, el juego decide la pantalla de resultados dando por hecho que se ha rendido
        // Moriarty: el bando de Moriarty pierde y el de Sherlock gana. El servidor de Revival dice que
        // bando gana de verdad (csr_winner) y aqui se corrige el resultado si hace falta.
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

        // El aviso del juego al rendirse ("Moriarty ha abandonado su perverso plan.") se cambia por uno
        // con quien ha sido de verdad. Si es Moriarty rindiendose, se deja el del juego.
        const string NoticeId = "ctg_name_info_game_end_surrender";
        static string _original;
        static readonly Dictionary<string, string> RoleNames = new()
        {
            ["detective"] = "Sherlock", ["criminal"] = "Moriarty", ["irene"] = "Irene", ["watson"] = "Watson",
        };
        // orden de idiomas del juego: japones, ingles, frances, italiano, aleman, espanol, portugues, ruso,
        // coreano, chino simplificado, chino tradicional
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

        // Despues de que el juego guarde el resultado, se corrige escribiendolo directamente
        static void AfterResult(ResultInfo __instance)
        {
            try
            {
                if (__instance == null || UnityEngine.Time.unscaledTime > _winnerUntil) return;
                var type = __instance.resultType;
                if (type != ResultInfo.ResultType.WIN && type != ResultInfo.ResultType.LOSE) return;
                bool moriartySide = type == ResultInfo.ResultType.LOSE;     // asi lo decide el juego
                bool moriartyWins;
                if (_iSurrendered) moriartyWins = !moriartySide;           // te has rendido tu: gana el otro bando
                else if (_winner != null) moriartyWins = _winner == "moriarty";
                else return;
                bool won = moriartySide == moriartyWins;
                __instance.resultType = won ? ResultInfo.ResultType.WIN : ResultInfo.ResultType.LOSE;
                // y el cartel de quien gana ("Sherlock logra la victoria" / el de Moriarty), que el juego pone
                // a continuacion dando por hecho que ha ganado Sherlock
                _state = moriartyWins ? ResultInfo.StateType.KILL_SUCCESS : ResultInfo.StateType.ARREST_SUCCESS;
                Plugin.L.LogInfo("[Salir] resultado: " + (won ? "victoria" : "derrota") + ", gana " + (moriartyWins ? "Moriarty" : "Sherlock"));
                _iSurrendered = false; _winner = null;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Salir] resultado: " + e.Message); }
        }

        // "Rendirse" del juego: solo deja a Moriarty, desde el turno 4 y fuera del entrenamiento. Si estas
        // solo en la sala se hace aqui lo mismo que hace el juego (avisar al servidor de que te rindes),
        // sin esas condiciones; el servidor termina la partida y el juego ensena el final.
        static bool BeforeRun()
        {
            try
            {
                if (!Alone() || ReplayManager.IsReplay()) return true;
                var nm = NetworkManager.Instance;
                if (nm == null) return true;
                string msg = "{\"surrenderPlayerId\":\"" + (ApiServer.PlayerId ?? "") + "\"}";
                _iSurrendered = true;
                _winnerUntil = UnityEngine.Time.unscaledTime + 60f;
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
