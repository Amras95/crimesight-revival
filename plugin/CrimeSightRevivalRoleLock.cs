// CRIMESIGHT Revival - roles locked during the countdown.
//
// When the host presses "Start Match" the server deals the roles and a short countdown starts. Changing role during
// it left two players with the same role. Now the role buttons of the waiting room are locked while the countdown
// runs: they look the same as always, but they don't react to the mouse and a click does nothing (cancelling the
// countdown unlocks them). The server also ignores role changes in that time (match.py, apply_var_ops).
using System;
using HarmonyLib;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class RoleLock
    {
        static float _until = -1f;      // end of the running countdown (Time.unscaledTime), -1 when there is none

        public static bool Counting => _until > 0f && Time.unscaledTime < _until;

        public static void Init(Harmony h)
        {
            try
            {
                var flags = System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic;
                HarmonyMethod M(string n) => new HarmonyMethod(typeof(RoleLock).GetMethod(n, flags));
                var cd = typeof(OutGameRoomPopupCountdown);
                var start = AccessTools.Method(cd, nameof(OutGameRoomPopupCountdown.OnCountDownStart));
                var cancel = AccessTools.Method(cd, nameof(OutGameRoomPopupCountdown.OnCountDownCancel));
                if (start != null) h.Patch(start, postfix: M(nameof(AfterStart)));
                if (cancel != null) h.Patch(cancel, postfix: M(nameof(Unlock)));
                // the button itself (sound, selected look) and the action it runs
                var rb = typeof(RoomRoleSelectButton);
                foreach (var n in new[] { nameof(RoomRoleSelectButton.OnClick), nameof(RoomRoleSelectButton.OnPointerEnter) })
                {
                    var m = AccessTools.Method(rb, n);
                    if (m == null) Plugin.L.LogWarning("[Roles] RoomRoleSelectButton." + n + " not found");
                    else h.Patch(m, prefix: M(n == nameof(RoomRoleSelectButton.OnClick) ? nameof(BeforeClick) : nameof(BeforeHover)));
                }
                var inner = AccessTools.Inner(typeof(OutGameRoomWaitingMenuVer2), "__c__DisplayClass94_0");
                System.Reflection.MethodInfo click = null;
                if (inner != null)
                    foreach (var m in inner.GetMethods())
                        if (m.Name.Contains("InitializeRoleButtonAction")) { click = m; break; }
                if (click == null) Plugin.L.LogWarning("[Roles] role button action not found");
                else h.Patch(click, prefix: M(nameof(BeforeAction)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Roles] " + e.Message); }
        }

        static void AfterStart(int __0)
        {
            _until = Time.unscaledTime + Mathf.Max(1, __0) + 2f;    // a margin for the match to start loading
            Plugin.L.LogInfo("[Roles] roles locked during the countdown");
        }

        // The countdown was cancelled (when it runs out, Counting turns false by itself)
        static void Unlock() => _until = -1f;

        static bool BeforeClick()
        {
            if (!Counting) return true;
            try { AudioManager.PlayOutGameCancelReturn(); } catch { }
            Plugin.L.LogInfo("[Roles] role change blocked during the countdown");
            return false;
        }

        static bool BeforeHover() => !Counting;

        static bool BeforeAction() => !Counting;
    }
}
