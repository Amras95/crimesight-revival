// CRIMESIGHT Revival - "Omitir" en los dialogos de los personajes (Sherlock, Moriarty...).
//
// El juego solo ensena su boton "Cerrar" en algunos momentos del dialogo, asi que para saltarlo habia que esperar
// o pinchar en la caja de texto. Aqui el boton se ve siempre que hay un dialogo en pantalla, se llama "Omitir"
// y cierra el dialogo entero (lo mismo que hacia "Cerrar"). Con el mando, B hace lo mismo.
// Los consejos de los menus (y la Guia Revival, que los usa) no se tocan.
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
            }
            catch (Exception e) { Plugin.L.LogWarning("[Omitir] " + e.Message); }
        }

        /// <summary>El dialogo de un personaje que se puede omitir ahora mismo (no los consejos de los menus).</summary>
        internal static CharaTalkDialogue Current()
        {
            var d = CharaTalkDialogue.Instance;
            if (d == null || !d.gameObject.activeInHierarchy || d.isTips || d.isPreview) return null;
            int ph = (int)d.dialoguePhase;
            if (ph < 2 || ph > 5) return null;                         // abriendose ... esperando: si; cerrandose: no
            if (d.dialogueCanvas != null && !d.dialogueCanvas.enabled) return null;
            return d;
        }

        /// <summary>Omitir: cierra el dialogo como su boton "Cerrar".</summary>
        internal static bool Close()
        {
            try
            {
                var d = Current();
                if (d == null) return false;
                d.OnDialogueClose();
                return true;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Omitir] " + e.Message); return false; }
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
