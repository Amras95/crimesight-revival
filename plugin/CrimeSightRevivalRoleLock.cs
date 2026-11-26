// CRIMESIGHT Revival - roles locked during the countdown.
//
// When the host presses "Start Match" the server deals the roles and a short countdown starts. Changing role during
// it left two players with the same role. Now the role buttons of the waiting room are locked while the countdown
// runs: they look dimmed, don't react to the mouse and a click does nothing (cancelling the countdown unlocks them).
// The server also ignores role changes in that time (match.py, apply_var_ops).
using System;
using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class RoleLock
    {
        static float _until = -1f;      // end of the running countdown (Time.unscaledTime), -1 when there is none
        static readonly List<CanvasGroup> _dimmed = new List<CanvasGroup>();
        static readonly List<float> _alpha = new List<float>();

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
                var upd = AccessTools.Method(typeof(OutGameRoomWaitingMenuVer2), "Update");
                if (upd != null) h.Patch(upd, postfix: M(nameof(AfterUpdate)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Roles] " + e.Message); }
        }

        static void AfterStart(int __0)
        {
            _until = Time.unscaledTime + Mathf.Max(1, __0) + 2f;    // a margin for the match to start loading
            Dim(true);
            Plugin.L.LogInfo("[Roles] roles locked during the countdown");
        }

        static void Unlock()
        {
            _until = -1f;
            Dim(false);
        }

        /// <summary>The countdown ran out (the match is loading) or was cancelled: the buttons come back.</summary>
        static void AfterUpdate()
        {
            // (the countdown window stays active in the room when it's not counting: it can't tell whether a
            // countdown is running, only OnCountDownStart / OnCountDownCancel can)
            if (_dimmed.Count > 0 && !Counting) Unlock();
        }

        static void Dim(bool on)
        {
            try
            {
                if (!on)
                {
                    for (int i = 0; i < _dimmed.Count; i++)
                        if (_dimmed[i] != null) _dimmed[i].alpha = _alpha[i];
                    _dimmed.Clear();
                    _alpha.Clear();
                    return;
                }
                foreach (var b in UnityEngine.Object.FindObjectsOfType<RoomRoleSelectButton>())
                {
                    if (b == null) continue;
                    var cg = b.GetComponent<CanvasGroup>() ?? b.gameObject.AddComponent<CanvasGroup>();
                    if (_dimmed.Contains(cg)) continue;
                    _dimmed.Add(cg);
                    _alpha.Add(cg.alpha);
                    cg.alpha = cg.alpha * 0.45f;
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Roles] " + e.Message); }
        }

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
