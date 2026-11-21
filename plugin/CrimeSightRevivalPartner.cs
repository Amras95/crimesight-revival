// CRIMESIGHT Revival - icono de Watson en la lista de jugadores de Sherlock.
//
// En la lista de jugadores (abajo a la derecha) el juego pone tu propio icono, el de Irene a Moriarty y el de
// Moriarty a Irene (Hud.SetPlayersInfoRoleIrene/Moriarty), pero no tiene nada para ensenar Watson a Sherlock:
// solo Watson veia su propio icono. Aqui, cada vez que el juego rellena los iconos (Hud.SetPlayersInfoRoleAll),
// si eres Sherlock y hay un Watson, se le pone su icono igual que hace el juego con Irene. El juego de Sherlock no
// sabe quien es Watson, asi que se busca en la lista de la sala (cada miembro lleva su papel).
using System;
using HarmonyLib;

namespace CrimeSightRevival.Mods
{
    static class PartnerIcon
    {
        static bool _warned;

        public static void Init(Harmony h)
        {
            try
            {
                var post = new HarmonyMethod(typeof(PartnerIcon).GetMethod(nameof(AfterRoleAll),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic));
                // SetPlayersInfoRoleOwn: lo llama el juego al empezar la partida y en cada fase de ordenes;
                // SetPlayersInfoRoleAll: al repartir los papeles
                foreach (var name in new[] { nameof(Hud.SetPlayersInfoRoleAll), nameof(Hud.SetPlayersInfoRoleOwn) })
                {
                    var m = AccessTools.DeclaredMethod(typeof(Hud), name);
                    if (m == null) { Plugin.L.LogWarning("[Watson] Hud." + name + " no existe"); continue; }
                    h.Patch(m, postfix: post);
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Watson] " + e.Message); }
        }

        static void AfterRoleAll(Hud __instance)
        {
            try
            {
                var gm = GameManager.instance;
                var nm = NetworkManager.Instance;
                if (gm == null || nm == null || __instance == null) return;
                if (nm.IsCriminal || nm.IsIrene || nm.IsWatson) return;               // solo Sherlock
                int watson = gm.GetWatsonPlayerIndex();
                // El juego no sabe quien es Watson (solo lo sabe el propio Watson); se busca en la sala
                if (watson < 0) watson = WatsonIndex(nm);
                if (watson < 0) return;
                var list = __instance.playersInfo;
                if (list == null) return;
                bool on = true;
                list.SetRoleIconActive(ref watson, ref on);
                list.SetRoleIconWatson(ref watson);
            }
            catch (Exception e)
            {
                if (!_warned) { _warned = true; Plugin.L.LogWarning("[Watson] " + e.Message); }
            }
        }

        /// <summary>Numero de jugador de Watson segun la lista de la sala (el servidor manda el papel de cada uno).</summary>
        static int WatsonIndex(NetworkManager nm)
        {
            var members = nm.GetCurrentRoom()?.Members;
            var hs = NetworkManager.GetHostSystem();
            if (members == null || hs == null) return -1;
            for (int i = 0; i < members.Count; i++)
            {
                var x = members[i];
                if (x == null || !x.IsWatson) continue;
                string id = x.PlayerId;
                return string.IsNullOrEmpty(id) ? -1 : hs.SearchMemberIndex(ref id);
            }
            return -1;
        }
    }
}
