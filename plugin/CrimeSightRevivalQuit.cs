// CRIMESIGHT Revival - "Rendirse" para salir de una partida contra la IA.
//
// El juego ya trae un boton "Rendirse" en los ajustes de la partida, pero solo lo ensena a Moriarty
// y a partir del turno 4 (y nunca en las salas de entrenamiento). Cuando eres la unica persona de la
// sala (contra IAs o en el entrenamiento), aqui se ensena siempre y vale para cualquier papel: asi
// se puede salir de una partida sin cerrar el juego. Con mas personas en la sala se deja como estaba.
using System;
using HarmonyLib;

namespace CrimeSightRevival.Mods
{
    static class Quit
    {
        static bool _forcing;

        public static void Init(Harmony h)
        {
            Patch(h, AccessTools.Method(typeof(GameManager), nameof(GameManager.IsEnableSurrender)), postfix: nameof(AfterEnable));
            Patch(h, AccessTools.Method(typeof(GameManager), nameof(GameManager.RunSurrender)), prefix: nameof(BeforeRun), finalizer: nameof(AfterRun));
            Patch(h, AccessTools.Method(typeof(GameManager), nameof(GameManager.IsCurrentPlayerCriminal)), postfix: nameof(AfterCriminal));
            Patch(h, AccessTools.Method(typeof(GameManager), nameof(GameManager.IsSoloRoom)), postfix: nameof(AfterSoloRoom));
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

        static void BeforeRun()
        {
            _forcing = Alone();
            if (_forcing) Plugin.L.LogInfo("[Salir] rendirse para salir de la partida");
        }

        static Exception AfterRun(Exception __exception) { _forcing = false; return __exception; }

        // Durante "Rendirse": el juego solo lo deja a Moriarty y fuera de las salas de entrenamiento
        static void AfterCriminal(ref bool __result) { if (_forcing) __result = true; }
        static void AfterSoloRoom(ref bool __result) { if (_forcing) __result = false; }
    }
}
