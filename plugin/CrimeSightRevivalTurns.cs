// CRIMESIGHT Revival - "Max turns" in the room settings.
//
// The game comes with the setting already made (slider from 6 to 15 turns, with its text in every language), but it
// hides it when opening the room settings window, and when pressing "Apply" it doesn't send it. Here it is
// shown again, it starts at the room's value and the choice is added to the settings sent (max_turn).
// The Revival server already stores it and hands it out to everyone. With custom stages the range opens
// to 1 to 99 turns (the original was 6 to 15).
//
// Time per turn: the game allowed 10 to 999 seconds in private rooms and 60 to 180 in public ones.
// Now it is always 60 to 999, for whoever wants to play calmly.
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

        // the game picks the seconds range depending on whether the room is private or public: both become 60-999
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
        static int _chosen;          // turns chosen in the window (0 = not touched)
        static OutGameRoomPopupRoomSetting _win;   // the settings window open

        // Typing the turns in the box: the game never wired that box (the setting was hidden),
        // so the number is passed to the slider, as if it had been moved (and "Apply" is enabled).
        static void TypedTurns(OutGameRoomPopupRoomSetting win, string text)
        {
            try
            {
                if (win == null || win.TurnSlider == null || win.TurnInputField == null) return;
                int now = Mathf.RoundToInt(win.TurnSlider.value);
                if (!int.TryParse((text ?? "").Trim(), out int v))
                {
                    win.TurnInputField.text = now.ToString();     // not a number: the slider's is left
                    return;
                }
                v = Mathf.Clamp(v, MIN, MAX);
                win.TurnInputField.text = v.ToString();
                if (v != now) win.TurnSlider.value = v;           // notifies the slider -> AfterSlider
                else AfterSlider(win, v);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Turnos] casilla: " + e.Message); }
        }

        // What the box says when pressing "Apply" (in case it is pressed without leaving it)
        static void ReadTypedTurns()
        {
            try
            {
                var win = _win;
                if (win == null || win.TurnInputField == null || !win.gameObject.activeInHierarchy) return;
                if (int.TryParse((win.TurnInputField.text ?? "").Trim(), out int v)) _chosen = Mathf.Clamp(v, MIN, MAX);
            }
            catch { }
        }

        // the game never got to enable "Apply" when moving this slider (the setting was hidden):
        // it is enabled here when the chosen turns aren't the ones the room already has
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
                ReadTypedTurns();
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
                // range from 1 to 99 (the "1 - 99 turn(s)" text comes from these values)
                try
                {
                    __instance.MIN_TURN = MIN; __instance.MAX_TURN = MAX;
                    if (__instance.TurnSlider != null) { __instance.TurnSlider.minValue = MIN; __instance.TurnSlider.maxValue = MAX; }
                    if (__instance.TurnInputField != null)
                    {
                        __instance.TurnInputField.characterLimit = 2;
                        // numbers only, like the time box: the game sets its own filter (Val) on it
                        // when opening the window; the turns box uses the same
                        if (__instance.SecondsInputField != null)
                            __instance.TurnInputField.onValidateInput = __instance.SecondsInputField.onValidateInput;
                    }
                    __instance.SetText();
                }
                catch (Exception e) { Plugin.L.LogWarning("[Turnos] rango: " + e.Message); }
                // the turns box also works for typing them
                try
                {
                    _win = __instance;
                    var win = __instance;
                    if (__instance.TurnInputField != null)
                        __instance.TurnInputField.onEndEdit.AddListener(
                            Il2CppInterop.Runtime.DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction<string>>(
                                new Action<string>(t => TypedTurns(win, t))));
                }
                catch (Exception e) { Plugin.L.LogWarning("[Turnos] casilla: " + e.Message); }
                // the slider starts at the turns the room has now
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
