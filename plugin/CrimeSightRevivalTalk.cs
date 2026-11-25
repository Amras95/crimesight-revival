// CRIMESIGHT Revival - "Skip" in the characters' dialogues (Sherlock, Moriarty...).
//
// The game only shows its "Close" button at some moments of the dialogue, so to skip it you had to wait
// or click the text box. Here the button shows whenever there is a dialogue on screen, it is called "Skip"
// and it closes the whole dialogue (the same "Close" did). With a gamepad, B does the same.
// The menu tips (and the Revival Guide, which uses them) aren't touched.
using System;
using HarmonyLib;
using TMPro;
using UnityEngine;

namespace CrimeSightRevival.Mods
{
    static class TalkSkip
    {
        static readonly string[] Skip = { "スキップ", "Skip", "Passer", "Salta", "Überspringen", "Omitir", "Pular",
            "Пропустить", "건너뛰기", "跳过", "跳過" };
        static bool _warned;

        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.DeclaredMethod(typeof(CharaTalkDialogue), "LateUpdate");
                if (m == null) { Plugin.L.LogWarning("[Omitir] CharaTalkDialogue.LateUpdate no existe"); return; }
                h.Patch(m, postfix: new HarmonyMethod(typeof(TalkSkip).GetMethod(nameof(AfterLateUpdate),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
                var c = AccessTools.DeclaredMethod(typeof(CharaTalkDialogue), "OnDialogueClose");
                if (c != null)
                    h.Patch(c, postfix: new HarmonyMethod(typeof(TalkSkip).GetMethod(nameof(AfterClose),
                        System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Omitir] " + e.Message); }
        }

        /// <summary>The character dialogue that can be skipped right now (not the menu tips).</summary>
        internal static CharaTalkDialogue Current()
        {
            var d = CharaTalkDialogue.Instance;
            if (d == null || !d.gameObject.activeInHierarchy || d.isTips || d.isPreview) return null;
            int ph = (int)d.dialoguePhase;
            if (ph < 2 || ph > 5) return null;                         // opening ... waiting: yes; closing: no
            if (d.dialogueCanvas != null && !d.dialogueCanvas.enabled) return null;
            return d;
        }

        /// <summary>Skip: closes the dialogue like its "Close" button.</summary>
        internal static bool Close()
        {
            try
            {
                var d = Current();
                if (d == null) return false;
                _byUser = true;
                d.OnDialogueClose();
                _byUser = false;
                return true;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Omitir] " + e.Message); return false; }
        }

        // ---------------------------------------------------------------- what is left of the scene, at once
        // When skipping a scene's dialogue (the end-of-match ones), the scene went on without text: a few
        // seconds of black screen or flicker. If you are the one skipping and a scene is running (PlayableDirector),
        // the game runs 8 times faster until the scene ends or another dialogue shows (6 s at most), so nothing
        // the scene does is skipped (its notices to the game arrive the same, only sooner).
        static bool _byUser;
        static float _rushUntil, _rushStart, _noScene;
        static bool _rushing;
        const float Rush = 8f;

        static void AfterClose()
        {
            try
            {
                bool user = _byUser || Input.GetMouseButtonUp(0) || Input.GetMouseButton(0) || Input.GetKeyDown(KeyCode.Escape);
                if (!user) return;
                var playing = PlayingScenes();
                if (playing.Length == 0) return;
                if (!_rushing && Time.timeScale > 0.5f && Time.timeScale < 1.5f)
                {
                    _rushing = true;
                    Time.timeScale = Rush;
                    _rushStart = Time.unscaledTime;
                    Plugin.L.LogInfo("[Omitir] resto de la escena al momento: " + playing);
                }
                _rushUntil = Time.unscaledTime + 6f;
                _noScene = 0f;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Omitir] escena: " + e.Message); }
        }

        static string PlayingScenes()
        {
            var sb = new System.Text.StringBuilder();
            foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppInterop.Runtime.Il2CppType.Of<UnityEngine.Playables.PlayableDirector>()))
            {
                var pd = o.TryCast<UnityEngine.Playables.PlayableDirector>();
                if (pd == null || pd.state != UnityEngine.Playables.PlayState.Playing) continue;
                sb.Append(sb.Length > 0 ? ", " : "").Append(pd.name).Append(' ').Append(pd.time.ToString("0.0")).Append('/').Append(pd.duration.ToString("0.0"));
            }
            return sb.ToString();
        }

        /// <summary>Every frame: back to normal speed as soon as another dialogue shows, the scene ends or 6 s
        /// pass.</summary>
        public static void Frame()
        {
            if (!_rushing) return;
            try
            {
                bool stop = Time.unscaledTime > _rushUntil || Current() != null || Math.Abs(Time.timeScale - Rush) > 0.01f;
                if (!stop)
                {
                    if (PlayingScenes().Length == 0) { if ((_noScene += Time.unscaledDeltaTime) > 0.25f) stop = true; }
                    else _noScene = 0f;
                }
                if (!stop) return;
                if (Math.Abs(Time.timeScale - Rush) < 0.01f) Time.timeScale = 1f;
                _rushing = false;
                Plugin.L.LogInfo($"[Omitir] escena terminada en {Time.unscaledTime - _rushStart:0.0} s");
            }
            catch { Time.timeScale = 1f; _rushing = false; }
        }

        static void AfterLateUpdate(CharaTalkDialogue __instance)
        {
            try
            {
                var d = __instance;
                if (d == null || d != Current()) return;
                var cb = d.closeButton;
                if (cb == null) return;
                if (!cb.activeSelf) cb.SetActive(true);
                TextMeshProUGUI label = null;
                foreach (var t in cb.GetComponentsInChildren<TextMeshProUGUI>(true))
                    if (t != null && (label == null || t.fontSize > label.fontSize)) label = t;
                if (label == null) return;
                int lang;
                try { lang = Math.Max(0, Math.Min(10, (int)TextManager.Instance.GetLangType())); } catch { lang = 1; }
                string want = Pad.Tag("b") + Skip[lang];
                if (label.text != want)
                {
                    if (Pad.Active && Pad.KeyIcons != null && label.spriteAsset != Pad.KeyIcons) label.spriteAsset = Pad.KeyIcons;
                    label.text = want;
                }
            }
            catch (Exception e)
            {
                if (!_warned) { _warned = true; Plugin.L.LogWarning("[Omitir] " + e.Message); }
            }
        }
    }
}
