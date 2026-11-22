// CRIMESIGHT Revival - Sherlock and Watson see each other's icon in the player list.
//
// In the player list (bottom right) the game shows your own icon, Irene's to Moriarty and Moriarty's to Irene
// (Hud.SetPlayersInfoRoleIrene/Moriarty), but had nothing to show Watson to Sherlock or Sherlock to Watson (Watson
// wasn't playable before). Here, each time the game fills in the icons (Hud.SetPlayersInfoRoleAll/Own), Sherlock
// gets Watson's icon and Watson gets Sherlock's, the same way the game does it for Irene. Neither game knows who the
// other one is, so they are found in the room's member list (each member carries its role).
//
// Ademas, el mapa de muebles para la Watson IA: cada turno el juego manda al servidor un resumen de la partida
// (GameManager.CreateServerReferenceData), pero los muebles solo salen en las casillas a las que llega cada personaje.
// Se anade al principio "searchMap": [[mueble, casilla, x, y, z], ...] con TODOS los muebles del escenario, para
// que la Watson IA pueda senalar con un ping de "Registrar" justo encima de cualquier sitio con comida que descubra.
using System;
using System.Text;
using HarmonyLib;
using Il2CppInterop.Runtime;

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
            SearchMap.Init(h);
            WatsonFoodPing.Init(h);
        }

        static void AfterRoleAll(Hud __instance)
        {
            try
            {
                var gm = GameManager.instance;
                var nm = NetworkManager.Instance;
                if (gm == null || nm == null || __instance == null) return;
                if (nm.IsCriminal || nm.IsIrene) return;                               // only Sherlock and Watson
                var list = __instance.playersInfo;
                if (list == null) return;
                bool on = true;
                if (nm.IsWatson)
                {
                    // Watson: Sherlock's icon
                    int sherlock = SherlockIndex(nm);
                    if (sherlock < 0) return;
                    list.SetRoleIconActive(ref sherlock, ref on);
                    list.SetRoleIconSherlock(ref sherlock);
                    return;
                }
                // Sherlock: Watson's icon (Sherlock's game doesn't know who Watson is: found in the room)
                int watson = gm.GetWatsonPlayerIndex();
                if (watson < 0) watson = WatsonIndex(nm);
                if (watson < 0) return;
                list.SetRoleIconActive(ref watson, ref on);
                list.SetRoleIconWatson(ref watson);
            }
            catch (Exception e)
            {
                if (!_warned) { _warned = true; Plugin.L.LogWarning("[Watson] " + e.Message); }
            }
        }

        /// <summary>Sherlock's player number from the room list: the member who is not Moriarty, Irene or Watson.</summary>
        static int SherlockIndex(NetworkManager nm)
        {
            var members = nm.GetCurrentRoom()?.Members;
            var hs = NetworkManager.GetHostSystem();
            if (members == null || hs == null) return -1;
            for (int i = 0; i < members.Count; i++)
            {
                var x = members[i];
                if (x == null || x.IsCriminal || x.IsIrene || x.IsWatson) continue;
                string id = x.PlayerId;
                return string.IsNullOrEmpty(id) ? -1 : hs.SearchMemberIndex(ref id);
            }
            return -1;
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

    static class WatsonFoodPing
    {
        const string LogSearch = "ctg_name_log_ping_search";               // "{player}: Searching."
        static readonly string[] Lines = { "ctg_talk_watson_newFoodDetected_mc01_p010_v10",   // primera comida
                                           "ctg_talk_watson_newFoodDetected_mc02_p010_v10" }; // las siguientes
        static string _room;          // sala de la partida en curso (para saber cual es la primera comida)
        static bool _said, _busy, _warned;

        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.DeclaredMethod(typeof(TextManager), nameof(TextManager.SetMacroText));
                if (m == null) { Plugin.L.LogWarning("[Watson] TextManager.SetMacroText no existe"); return; }
                h.Patch(m, postfix: new HarmonyMethod(typeof(WatsonFoodPing).GetMethod(nameof(AfterMacro),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Watson] " + e.Message); }
        }

        /// <summary>Nombre de la Watson IA de la sala (las IA tienen un id que empieza por "bot"), o null.</summary>
        static string AiWatsonName(out string room)
        {
            room = null;
            var r = NetworkManager.Instance?.currentRoom;
            var members = r?.Members;
            if (members == null) return null;
            room = r.Id;
            for (int i = 0; i < members.Count; i++)
            {
                var x = members[i];
                if (x != null && x.IsWatson && (x.PlayerId ?? "").StartsWith("bot")) return x.Name;
            }
            return null;
        }

        // El aviso de un ping se escribe metiendo el nombre de quien lo manda en "{player}: Searching."; si es la
        // Watson IA, lo que va detras del nombre pasa a ser su frase
        static void AfterMacro(TextManager __instance, ref string __0, ref string __1, ref string __2, ref string __result)
        {
            if (_busy || string.IsNullOrEmpty(__0) || string.IsNullOrEmpty(__2)) return;
            try
            {
                _busy = true;
                string id = LogSearch;
                if (__0 != __instance.GetLangText(ref id)) return;           // no es el aviso de "Registrar"
                string name = AiWatsonName(out string room);
                if (string.IsNullOrEmpty(name) || !__2.Contains(name)) return;
                string token = (__1 ?? "").StartsWith("{") ? __1 : "{" + __1 + "}";
                int at = __0.IndexOf(token, StringComparison.Ordinal);
                if (at < 0) return;
                if (room != _room) { _room = room; _said = false; }          // partida nueva: otra vez la primera
                string lineId = _said ? Lines[1] : Lines[0];
                string line = __instance.GetLangText(ref lineId);
                if (string.IsNullOrEmpty(line) || line == lineId) return;   // sin traduccion: se deja el original
                _said = true;
                // lo que separa el nombre del texto en este idioma (": ", "：", ...)
                string tail = __0.Substring(at + token.Length);
                int k = 0;
                while (k < tail.Length && !char.IsLetterOrDigit(tail[k])) k++;
                string template = __0.Substring(0, at + token.Length) + tail.Substring(0, k)
                                  + line.Replace("\\n", " ").Replace("\n", " ").Trim();
                __result = __instance.SetMacroText(ref template, ref __1, ref __2);
            }
            catch (Exception e)
            {
                if (!_warned) { _warned = true; Plugin.L.LogWarning("[Watson] " + e.Message); }
            }
            finally { _busy = false; }
        }
    }

    static class SearchMap
    {
        static bool _warned;

        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.DeclaredMethod(typeof(GameManager), nameof(GameManager.CreateServerReferenceData));
                if (m == null) { Plugin.L.LogWarning("[Mapa] GameManager.CreateServerReferenceData no existe"); return; }
                h.Patch(m, postfix: new HarmonyMethod(typeof(SearchMap).GetMethod(nameof(After),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Mapa] " + e.Message); }
        }

        static void After(NetworkManager.JsonStringBuilder __result)
        {
            try
            {
                var isb = __result?.stringBuilder;
                if (isb == null) return;
                var extra = new StringBuilder("\"searchMap\":[");
                bool first = true;
                foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<SearchObject>()))
                {
                    var so = o?.TryCast<SearchObject>();
                    if (so == null) continue;
                    if (!first) extra.Append(',');
                    first = false;
                    // [mueble, casilla, x, y, z]: posicion en el mundo x10 (como los pings), encima del mueble
                    var pos = so.transform.position;
                    var rend = so.GetComponentInChildren<UnityEngine.Renderer>();
                    if (rend != null) { var bb = rend.bounds; pos = new UnityEngine.Vector3(bb.center.x, bb.max.y, bb.center.z); }  // encima
                    extra.Append('[').Append(so.UniqId).Append(',').Append(so.GetGridId())
                         .Append(',').Append(UnityEngine.Mathf.RoundToInt(pos.x * 10))
                         .Append(',').Append(UnityEngine.Mathf.RoundToInt(pos.y * 10))
                         .Append(',').Append(UnityEngine.Mathf.RoundToInt(pos.z * 10)).Append(']');
                }
                if (first) return;                       // sin muebles (no es una partida)
                extra.Append("],");
                string s = isb.ToString();
                int start = s.IndexOf('{');              // el resumen es un objeto JSON: se mete justo al abrirlo
                if (start < 0) return;
                isb.Clear();
                isb.Append(s.Substring(0, start + 1) + extra + s.Substring(start + 1));
            }
            catch (Exception e)
            {
                if (!_warned) { _warned = true; Plugin.L.LogWarning("[Mapa] " + e.Message); }
            }
        }
    }
}
