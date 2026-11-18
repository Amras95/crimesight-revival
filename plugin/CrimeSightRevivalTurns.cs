// CRIMESIGHT Revival - "Máximo de turnos" en los ajustes de la sala.
//
// El juego trae el ajuste ya hecho (barra de 6 a 15 turnos, con su texto en todos los idiomas), pero lo
// esconde al abrir la ventana de ajustes de la sala, y al pulsar "Aplicar" no lo manda. Aqui se vuelve a
// ensenar, empieza en el valor de la sala y lo elegido se anade a los ajustes que se envian (max_turn).
// El servidor de Revival ya lo guarda y lo reparte a todos. Con los escenarios propios el rango se abre
// de 1 a 99 turnos (el original era de 6 a 15).
//
// Tiempo por turno: el juego dejaba de 10 a 999 segundos en salas privadas y de 60 a 180 en publicas.
// Ahora siempre es de 60 a 999, para quien quiera jugar con calma.
using System;
using HarmonyLib;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class Turns
    {
        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.Method(typeof(OutGameRoomPopupRoomSetting), "Start");
                if (m == null) { Plugin.L.LogWarning("[Turnos] no encuentro la ventana de ajustes"); return; }
                h.Patch(m, postfix: Hm(nameof(AfterStart)));
                h.Patch(AccessTools.Method(typeof(OutGameRoomPopupRoomSetting), "OnTurnSliderValueChanged"), postfix: Hm(nameof(AfterSlider)));
                h.Patch(AccessTools.Method(typeof(RoomSettings), nameof(RoomSettings.GetParam)), postfix: Hm(nameof(AfterGetParam)));
                var init = AccessTools.Method(typeof(OutGameRoomPopupRoomSetting), "InitializeSettingValue");
                if (init != null) h.Patch(init, prefix: Hm(nameof(BeforeInit)), postfix: Hm(nameof(AfterInit)));
                else Plugin.L.LogWarning("[Turnos] no encuentro el ajuste de tiempo");
            }
            catch (Exception e) { Plugin.L.LogWarning("[Turnos] " + e.Message); }
        }

        static HarmonyMethod Hm(string n) => new HarmonyMethod(typeof(Turns).GetMethod(n,
            System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic));

        const int MIN = 1, MAX = 99;
        const int MIN_SEC = 60, MAX_SEC = 999;

        // el juego elige el rango de segundos segun la sala sea privada o publica: los dos pasan a 60-999
        static void BeforeInit(OutGameRoomPopupRoomSetting __instance)
        {
            try
            {
                __instance.MIN_SECONDS = MIN_SEC; __instance.MAX_SECONDS = MAX_SEC;
                __instance.MIN_SECOND_PUBLIC = MIN_SEC; __instance.MAX_SECOND_PUBLIC = MAX_SEC;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Turnos] tiempo: " + e.Message); }
        }

        static void AfterInit(OutGameRoomPopupRoomSetting __instance)
        {
            try
            {
                __instance.roomMinSeconds = MIN_SEC; __instance.roomMaxSeconds = MAX_SEC;
                var sl = __instance.SecondsSlider;
                if (sl != null)
                {
                    sl.minValue = MIN_SEC; sl.maxValue = MAX_SEC;
                    int v = Mathf.Clamp(Mathf.RoundToInt(sl.value), MIN_SEC, MAX_SEC);
                    sl.value = v;
                    if (__instance.SecondsInputField != null)
                    {
                        __instance.SecondsInputField.characterLimit = 3;
                        __instance.SecondsInputField.text = v.ToString();
                    }
                }
                __instance.SetText();   // "60 - 999 segundo(s)"
                if (!_timeLogged) { _timeLogged = true; Plugin.L.LogInfo("[Turnos] tiempo por turno: 60-999 s"); }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Turnos] tiempo: " + e.Message); }
        }
        static bool _timeLogged;
        static int _chosen;          // turnos elegidos en la ventana (0 = no se ha tocado)

        // el juego nunca llego a activar "Aplicar" al mover esta barra (el ajuste estaba escondido):
        // se activa aqui cuando los turnos elegidos no son los que ya tiene la sala
        static void AfterSlider(OutGameRoomPopupRoomSetting __instance, float value)
        {
            _chosen = Mathf.RoundToInt(value);
            try
            {
                int now = NetworkManager.Instance?.currentRoom?.MaxTurn ?? 0;
                if (__instance != null && _chosen != now) __instance.SetApplyButtonEnable(true);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Turnos] aplicar: " + e.Message); }
        }

        static void AfterGetParam(RoomSettings __instance, Il2CppSystem.Collections.Generic.Dictionary<string, Il2CppSystem.Object> __result)
        {
            try
            {
                if (_chosen <= 0 || __result == null) return;
                var boxed = new Il2CppSystem.Int32 { m_value = _chosen }.BoxIl2CppObject();
                if (__result.ContainsKey("max_turn")) __result["max_turn"] = boxed;
                else __result.Add("max_turn", boxed);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Turnos] " + e.Message); }
        }

        static void AfterStart(OutGameRoomPopupRoomSetting __instance)
        {
            try
            {
                // rango de 1 a 99 (el texto "1 - 99 turno(s)" sale de estos valores)
                try
                {
                    __instance.MIN_TURN = MIN; __instance.MAX_TURN = MAX;
                    if (__instance.TurnSlider != null) { __instance.TurnSlider.minValue = MIN; __instance.TurnSlider.maxValue = MAX; }
                    if (__instance.TurnInputField != null) __instance.TurnInputField.characterLimit = 2;
                    __instance.SetText();
                }
                catch (Exception e) { Plugin.L.LogWarning("[Turnos] rango: " + e.Message); }
                // la barra empieza en los turnos que tiene la sala ahora
                try
                {
                    int now = NetworkManager.Instance?.currentRoom?.MaxTurn ?? 0;
                    if (now > 0 && __instance.TurnSlider != null)
                    {
                        __instance.TurnSlider.value = now;
                        _chosen = now;
                    }
                }
                catch { }
                var hidden = __instance.DontUseSettingList;
                if (hidden == null) return;
                int shown = 0;
                foreach (var c in new Component[] { __instance.TurnSlider, __instance.TurnInputField, __instance.TurnTitleTMP })
                {
                    for (var t = c != null ? c.transform : null; t != null; t = t.parent)
                    {
                        if (t == __instance.transform) break;
                        bool found = false;
                        for (int i = 0; i < hidden.Count; i++)
                            if (hidden[i] != null && hidden[i].Pointer == t.gameObject.Pointer) { found = true; break; }
                        if (found)
                        {
                            if (!t.gameObject.activeSelf) { t.gameObject.SetActive(true); shown++; }
                            break;
                        }
                    }
                }
                Plugin.L.LogInfo(shown > 0 ? "[Turnos] ajuste de turnos visible" : "[Turnos] el ajuste de turnos no estaba escondido");
            }
            catch (Exception e) { Plugin.L.LogWarning("[Turnos] " + e.Message); }
        }
    }
}
