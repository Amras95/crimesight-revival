// CRIMESIGHT Revival - team surrender vote and AI takeover notice.
//
// Surrender vote: when a player presses Surrender (Forfeit) and a person is on their team, the Revival server
// asks that teammate first. The teammate gets a copy of the game's in-match Yes/No window; the team only
// forfeits if they agree. If they say no, or don't answer in time, the match goes on and the one who asked is told.
// The server sends "CsrSurrenderVote" (to the teammate), "CsrSurrenderWait" (to the one who asked) and
// "CsrSurrenderVoteEnd" (to both, when the match goes on). Answers go back through the game's own Abandon call
// with {"csr_vote": "yes"/"no"}.
//
// AI takeover: when a player leaves mid-match and other people are still playing, the server gives their role to an
// AI and sends "CsrReplaced". Here the other players get a short notice at the top of the screen (and a line in the
// in-game log), and the name in the player list gets the same "(AI)" mark the server now uses for that player.
//
// The server also sends "CsrPartnerIcons" here (the room's "Reveal Partner (Detective Team)" setting, see CrimeSightRevivalPartner.cs).
using System;
using System.Collections.Generic;
using HarmonyLib;
using Il2CppInterop.Runtime;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

using Dict = Il2CppSystem.Collections.Generic.Dictionary<string, Il2CppSystem.Object>;

namespace CrimeSightRevival.Mods
{
    static class Team
    {
        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.Method(typeof(NetworkManager), "EventControl");
                if (m == null) { Plugin.L.LogWarning("[Team] NetworkManager.EventControl not found"); return; }
                h.Patch(m, prefix: new HarmonyMethod(typeof(Team).GetMethod(nameof(BeforeControl),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[Team] " + e.Message); }
        }

        // ---------------------------------------------------------------- messages from the server
        static readonly string[] Commands = { "CsrSurrenderVote", "CsrSurrenderWait", "CsrSurrenderVoteEnd", "CsrReplaced",
                                                     "CsrPartnerIcons" };
        static readonly Queue<(string cmd, Dictionary<string, string> data)> _queue = new();

        // The command can come as the first argument, as a key of the dictionary or inside its "Control" entry
        static bool BeforeControl(string __0, Dict __1)
        {
            try
            {
                foreach (var cmd in Commands)
                {
                    if (!Find(__0, __1, cmd, out var data)) continue;
                    _queue.Enqueue((cmd, Flat(data)));
                    return false;
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("[Team] " + e.Message); }
            return true;
        }

        static bool Find(string first, Dict dict, string cmd, out Dict data)
        {
            data = null;
            if (first == cmd) { data = dict; return true; }
            if (dict == null) return false;
            if (dict.ContainsKey(cmd)) { data = AsDict(dict[cmd]); return true; }
            if (dict.ContainsKey("Control"))
            {
                var control = AsDict(dict["Control"]);
                if (control != null && control.ContainsKey(cmd)) { data = AsDict(control[cmd]); return true; }
            }
            return false;
        }

        static Dict AsDict(Il2CppSystem.Object o)
        {
            try { return o?.TryCast<Dict>(); } catch { return null; }
        }

        static Dictionary<string, string> Flat(Dict d)
        {
            var res = new Dictionary<string, string>();
            if (d == null) return res;
            foreach (var kv in d) res[kv.Key] = kv.Value?.ToString() ?? "";
            return res;
        }

        static string Get(Dictionary<string, string> d, string key) => d.TryGetValue(key, out var v) ? v : "";

        /// <summary>True for the server's AIs (ids "bot0001"...) and for players an AI took over this match.</summary>
        public static bool IsAi(string playerId) =>
            playerId != null && (playerId.StartsWith("bot", StringComparison.Ordinal) || _renamed.ContainsKey(playerId));

        // ---------------------------------------------------------------- every frame (Update)
        static readonly Dictionary<string, string> _renamed = new();   // player id -> name with "(AI)"
        static float _nextName;

        public static void Frame()
        {
            while (_queue.Count > 0)
            {
                var (cmd, data) = _queue.Dequeue();
                Plugin.L.LogInfo("[Team] " + cmd);
                switch (cmd)
                {
                    case "CsrSurrenderVote": OpenVote(Get(data, "PlayerName")); break;
                    case "CsrSurrenderWait": Notify(Text(Waiting)); break;
                    case "CsrSurrenderVoteEnd": EndVote(Get(data, "Result"), Get(data, "PlayerName")); break;
                    case "CsrPartnerIcons": PartnerIcon.FromServer(Get(data, "Show")); break;
                    case "CsrReplaced":
                        _renamed[Get(data, "PlayerId")] = Get(data, "NewName");
                        Notify(string.Format(Text(Replaced), Get(data, "PlayerName")));
                        _nextName = 0f;
                        break;
                }
            }
            if (_vote != null) VoteClicks();
            if (_toast != null)
            {
                float left = _toastUntil - Time.unscaledTime;
                if (left <= 0f || GameManager.instance == null) HideToast();
                else _toastGroup.alpha = Mathf.Clamp01(left / 0.6f);          // fades out in the last 0.6 s
            }
            if (GameManager.instance == null)          // out of the match: forget the players taken over by an AI
            {
                _renamed.Clear();
                CloseVote();
                return;
            }
            if (_renamed.Count > 0 && UnityEngine.Time.unscaledTime >= _nextName)
            {
                _nextName = UnityEngine.Time.unscaledTime + 0.5f;
                ApplyNames();
            }
        }

        // ---------------------------------------------------------------- vote window
        // The game's in-match Yes/No window (Hud.confirmUI) answers "yes" by itself when it's opened from here
        // (CreateConfirmUI), so it isn't opened: it is copied, with our texts, and the copy's buttons answer.
        // If that fails, a plain dark window of our own is used. (The out-of-match windows' look isn't loaded in
        // a match: copying it gave a see-through window with dark text.)
        static GameObject _vote;
        static RectTransform _yesRect, _noRect;
        static Image _yesImg, _noImg;
        static Color _yesBase, _noBase;
        static bool _ownWindow;                 // our own window (clicks checked in VoteClicks)

        static void OpenVote(string asker)
        {
            CloseVote();
            string title = GameText("ctg_system_systemSetting_surrender_title");
            string body = string.Format(Text(VoteBody), asker);
            string yes = GameText("ctg_name_button_text_yes"), no = GameText("ctg_name_button_text_no");
            if (CopyGameConfirm(title, body, yes, no))
            {
                Sfx(AudioManager.PlayOutGameWindowOpen);
                return;
            }
            try
            {
                _ownWindow = true;
                _vote = new GameObject("CSR_SurrenderVote");
                var canvas = _vote.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvas.sortingOrder = 32000;
                var scaler = _vote.AddComponent<CanvasScaler>();
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920, 1080);
                scaler.matchWidthOrHeight = 0.5f;
                _vote.AddComponent<GraphicRaycaster>();          // the game behind can't be clicked while it's open
                var dim = ModOffer.Box("Dim", _vote.transform, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
                dim.gameObject.AddComponent<Image>().color = new Color(0f, 0f, 0f, 0.55f);
                var sk = new Skin { Font = ModOffer.GameFont() };     // plain dark look (fresh: not the room's)
                var panel = sk.MakePanel(_vote.transform, new Vector2(860, 440)).transform;
                sk.MakeText(panel, title, 38, new Vector2(0, 160), new Vector2(780, 60), true);
                sk.MakeText(panel, body, 26, new Vector2(0, 30), new Vector2(780, 180), false);
                var bs = new Vector2(236, 64);
                _yesImg = sk.MakeButton(panel, yes, true, new Vector2(-140, -155), bs, 26, out _yesRect, out _);
                _noImg = sk.MakeButton(panel, no, false, new Vector2(140, -155), bs, 26, out _noRect, out _);
                _yesBase = _yesImg.color; _noBase = _noImg.color;
                Sfx(AudioManager.PlayOutGameWindowOpen);
            }
            catch (Exception e)
            {
                Plugin.L.LogWarning("[Team] no vote window (" + e.Message + "); answering no");
                CloseVote();
                Answer(false);
            }
        }

        /// <summary>Copy of the game's in-match Yes/No window with our texts; its buttons answer the vote.</summary>
        static bool CopyGameConfirm(string title, string body, string yes, string no)
        {
            try
            {
                var ui = GameManager.instance?.hud?.confirmUI;
                var okBtn = ui?.ConfirmButton;
                var noBtn = ui?.DenyButton;
                if (ui == null || okBtn == null || noBtn == null) return false;
                var src = ui.gameObject;
                string pOk = Rel(src.transform, okBtn.transform), pNo = Rel(src.transform, noBtn.transform);
                // the texts are put on the (hidden) original just for the copy, then put back
                var t1 = ui.titleText; var t2 = ui.mainText; var t3 = ui.confirmText; var t4 = ui.denyText;
                string o1 = t1?.text, o2 = t2?.text, o3 = t3?.text, o4 = t4?.text;
                GameObject copy;
                try
                {
                    if (t1 != null) t1.text = title;
                    if (t2 != null) t2.text = body;
                    if (t3 != null) t3.text = yes;
                    if (t4 != null) t4.text = no;
                    copy = UnityEngine.Object.Instantiate(src, src.transform.parent, false);
                }
                finally
                {
                    if (t1 != null) t1.text = o1;
                    if (t2 != null) t2.text = o2;
                    if (t3 != null) t3.text = o3;
                    if (t4 != null) t4.text = o4;
                }
                copy.name = "CSR_SurrenderVote";
                foreach (var c in copy.GetComponentsInChildren(Il2CppType.Of<ConfirmUI>(), true))
                    UnityEngine.Object.DestroyImmediate(c);          // before it can run (its Start)
                foreach (var c in copy.GetComponentsInChildren(Il2CppType.Of<Behaviour>(), true))
                {
                    var bh = c.TryCast<Behaviour>();
                    string tn = bh != null ? bh.GetIl2CppType().Name : "";
                    if (tn == "SimpleAnimation" || tn == "Animator" || tn == "Animation") bh.enabled = false;
                }
                foreach (var c in copy.GetComponentsInChildren(Il2CppType.Of<CanvasGroup>(), true))
                {
                    var cg = c.TryCast<CanvasGroup>();
                    cg.alpha = 1f; cg.interactable = true; cg.blocksRaycasts = true;
                }
                var yesB = copy.transform.Find(pOk)?.GetComponent<Button>();
                var noB = copy.transform.Find(pNo)?.GetComponent<Button>();
                if (yesB == null || noB == null) { UnityEngine.Object.Destroy(copy); return false; }
                yesB.onClick = new Button.ButtonClickedEvent();
                noB.onClick = new Button.ButtonClickedEvent();
                yesB.onClick.AddListener(Ui(() => Click(true)));
                noB.onClick.AddListener(Ui(() => Click(false)));
                yesB.interactable = noB.interactable = true;
                copy.transform.localScale = Vector3.one;
                copy.SetActive(true);
                copy.transform.SetAsLastSibling();
                _vote = copy;
                _ownWindow = false;
                Plugin.L.LogInfo("[Team] vote window: copy of the game's");
                return true;
            }
            catch (Exception e)
            {
                Plugin.L.LogWarning("[Team] couldn't copy the game's window: " + e.Message);
                return false;
            }
        }

        static string Rel(Transform root, Transform t)
        {
            var parts = new List<string>();
            for (var x = t; x != null && x != root; x = x.parent) parts.Insert(0, x.name);
            return string.Join("/", parts);
        }

        static void Click(bool yes)
        {
            if (_vote == null) return;
            Sfx(yes ? AudioManager.PlayOutGameDecideClick : AudioManager.PlayOutGameCancel);
            CloseVote();
            Answer(yes);
        }

        static void VoteClicks()
        {
            if (!_ownWindow) return;                          // the game window's buttons answer by themselves
            Vector2 mouse = Input.mousePosition;
            bool overYes = _yesRect != null && RectTransformUtility.RectangleContainsScreenPoint(_yesRect, mouse, null);
            bool overNo = _noRect != null && RectTransformUtility.RectangleContainsScreenPoint(_noRect, mouse, null);
            if (_yesImg != null) _yesImg.color = overYes ? Skin.Hover(_yesBase) : _yesBase;
            if (_noImg != null) _noImg.color = overNo ? Skin.Hover(_noBase) : _noBase;
            if (!Input.GetMouseButtonDown(0)) return;
            if (overYes) Click(true);
            else if (overNo) Click(false);
        }

        static void CloseVote()
        {
            if (_vote != null) UnityEngine.Object.Destroy(_vote);
            _vote = null; _ownWindow = false;
            _yesRect = _noRect = null; _yesImg = _noImg = null;
        }

        static void EndVote(string result, string who)
        {
            CloseVote();
            if (result == "no") Notify(string.Format(Text(Declined), who));
            else if (result == "timeout") Notify(string.Format(Text(NoAnswer), who));
        }

        static void Answer(bool yes)
        {
            var nm = NetworkManager.Instance;
            if (nm == null) return;
            Plugin.L.LogInfo("[Team] vote: " + (yes ? "yes" : "no"));
            nm.Abandon("{\"csr_vote\":\"" + (yes ? "yes" : "no") + "\"}",
                DelegateSupport.ConvertDelegate<Il2CppSystem.Action>(new Action(() => { })),
                DelegateSupport.ConvertDelegate<Il2CppSystem.Action<string, NetworkManager.ErrorCode>>(
                    new Action<string, NetworkManager.ErrorCode>((m, c) => Plugin.L.LogWarning("[Team] vote not sent: " + m))));
        }

        static void Sfx(Action play) { try { play(); } catch { } }

        static UnityEngine.Events.UnityAction Ui(Action a) => DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction>(a);

        // ---------------------------------------------------------------- "(AI)" in the player list
        static void ApplyNames()
        {
            var nm = NetworkManager.Instance;
            var hs = NetworkManager.GetHostSystem();
            var members = nm?.GetCurrentRoom()?.Members;
            foreach (var kv in _renamed)
            {
                string id = kv.Key, name = kv.Value;
                if (string.IsNullOrEmpty(name)) continue;
                if (members != null)
                    for (int i = 0; i < members.Count; i++)
                        if (members[i] != null && members[i].PlayerId == id && members[i].Name != name) members[i].Name = name;
                if (hs == null) continue;
                try
                {
                    var info = hs.SearchMember(ref id);
                    if (info.name != name) info.name = name;
                }
                catch { }
                int index = hs.SearchMemberIndex(ref id);
                if (index < 0) continue;
                foreach (var o in UnityEngine.Object.FindObjectsOfType(Il2CppType.Of<PlayersInfoOne>()))
                {
                    var one = o.TryCast<PlayersInfoOne>();
                    if (one == null || one.GetPlayerId() != index || one.GetNameText() == name) continue;
                    string n = name;
                    one.SetNameText(ref n);
                }
            }
        }

        // ---------------------------------------------------------------- notice at the top of the screen
        static GameObject _toast;
        static CanvasGroup _toastGroup;
        static float _toastUntil;

        /// <summary>Shows the text at the top of the screen for a few seconds and also adds it to the in-game log.</summary>
        static void Notify(string text)
        {
            Log(text);
            HideToast();
            try
            {
                _toast = new GameObject("CSR_TeamNotice");
                var canvas = _toast.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvas.sortingOrder = 31000;
                var scaler = _toast.AddComponent<CanvasScaler>();
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920, 1080);
                scaler.matchWidthOrHeight = 0.5f;
                _toastGroup = _toast.AddComponent<CanvasGroup>();
                _toastGroup.blocksRaycasts = false;                          // never gets in the way of clicks
                _toastGroup.interactable = false;
                var panel = ModOffer.Box("Panel", _toast.transform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f),
                    new Vector2(0f, -130f), new Vector2(980f, 100f));
                var bg = panel.gameObject.AddComponent<Image>();
                bg.color = new Color(0.04f, 0.05f, 0.09f, 0.88f);
                bg.raycastTarget = false;
                ModOffer.Label(panel, text, ModOffer.GameFont(), 30f, Vector2.zero, new Vector2(940f, 88f));
                _toastUntil = Time.unscaledTime + 6f;
            }
            catch (Exception e) { Plugin.L.LogWarning("[Team] notice: " + e.Message); HideToast(); }
        }

        static void HideToast()
        {
            if (_toast != null) UnityEngine.Object.Destroy(_toast);
            _toast = null;
            _toastGroup = null;
        }

        // ---------------------------------------------------------------- texts
        static void Log(string text)
        {
            try
            {
                var log = new InGameLog(ref text);
                InGameLogManager.Regist(ref log);
            }
            catch (Exception e) { Plugin.L.LogWarning("[Team] log: " + e.Message); }
        }

        static string GameText(string id)
        {
            try { return TextManager.Instance.GetLangText(ref id); } catch { return id; }
        }

        static string Text(string[] t)
        {
            int lang = 1;
            try { lang = Math.Max(0, Math.Min(t.Length - 1, (int)TextManager.Instance.GetLangType())); } catch { }
            return t[lang];
        }

        // Game language order: Japanese, English, French, Italian, German, Spanish, Portuguese, Russian, Korean,
        // Simplified Chinese, Traditional Chinese. Same words as the game's Forfeit window in each language.
        static readonly string[] VoteBody =
        {
            "{0}が降参を提案しています。同意しますか？\n同意するとチームの敗北になります。",
            "{0} wants to forfeit this match. Do you agree?\nIf you agree, your team loses the match.",
            "{0} veut abandonner la partie. Êtes-vous d'accord ?\nSi vous acceptez, votre équipe perd la partie.",
            "{0} vuole dichiarare forfait. Sei d'accordo?\nSe accetti, la tua squadra perde la partita.",
            "{0} möchte das Spiel aufgeben. Bist du einverstanden?\nWenn du zustimmst, verliert dein Team das Spiel.",
            "{0} quiere abandonar la partida. ¿Estás de acuerdo?\nSi aceptas, tu equipo pierde la partida.",
            "{0} quer desistir do jogo. Você concorda?\nSe concordar, sua equipe perde a partida.",
            "{0} предлагает сдаться. Вы согласны?\nЕсли вы согласитесь, ваша команда проиграет матч.",
            "{0}이(가) 기권을 제안했습니다. 동의하시겠습니까?\n동의하면 팀이 대전에서 패배합니다.",
            "{0}想要认输。你同意吗？\n同意后你的队伍将输掉本局游戏。",
            "{0}想要投降。你同意嗎？\n同意後你的隊伍將輸掉本場對戰。",
        };
        static readonly string[] Waiting =
        {
            "降参するにはチームメイトの同意が必要です。返事を待っています…",
            "Your teammate must agree to forfeit. Waiting for their answer…",
            "Votre coéquipier doit accepter l'abandon. En attente de sa réponse…",
            "Il tuo compagno deve accettare il forfait. In attesa della sua risposta…",
            "Dein Teamkamerad muss dem Aufgeben zustimmen. Warte auf die Antwort …",
            "Tu compañero tiene que aceptar abandonar. Esperando su respuesta…",
            "Seu colega precisa concordar em desistir. Aguardando a resposta…",
            "Ваш союзник должен согласиться сдаться. Ждём ответа…",
            "기권하려면 팀원의 동의가 필요합니다. 응답을 기다리는 중…",
            "认输需要队友同意。正在等待对方回复…",
            "投降需要隊友同意。正在等待對方回覆…",
        };
        static readonly string[] Declined =
        {
            "{0}は降参に同意しませんでした。対戦を続けます。",
            "{0} doesn't want to forfeit. The match goes on.",
            "{0} ne veut pas abandonner. La partie continue.",
            "{0} non vuole dichiarare forfait. La partita continua.",
            "{0} möchte nicht aufgeben. Das Spiel geht weiter.",
            "{0} no quiere abandonar. La partida continúa.",
            "{0} não quer desistir. O jogo continua.",
            "{0} не хочет сдаваться. Матч продолжается.",
            "{0}이(가) 기권에 동의하지 않았습니다. 대전이 계속됩니다.",
            "{0}不同意认输。游戏继续。",
            "{0}不同意投降。對戰繼續。",
        };
        static readonly string[] NoAnswer =
        {
            "{0}から返事がありませんでした。対戦を続けます。",
            "{0} didn't answer. The match goes on.",
            "{0} n'a pas répondu. La partie continue.",
            "{0} non ha risposto. La partita continua.",
            "{0} hat nicht geantwortet. Das Spiel geht weiter.",
            "{0} no ha respondido. La partida continúa.",
            "{0} não respondeu. O jogo continua.",
            "{0} не ответил. Матч продолжается.",
            "{0}이(가) 응답하지 않았습니다. 대전이 계속됩니다.",
            "{0}没有回复。游戏继续。",
            "{0}沒有回覆。對戰繼續。",
        };
        static readonly string[] Replaced =
        {
            "{0}がゲームから抜けました。AIが代わりにプレイします。",
            "{0} has left the match. An AI takes over.",
            "{0} a quitté la partie. Une IA prend le relais.",
            "{0} ha lasciato la partita. Un'IA prende il suo posto.",
            "{0} hat das Spiel verlassen. Eine KI übernimmt.",
            "{0} ha abandonado la partida. Una IA ocupa su lugar.",
            "{0} saiu da partida. Uma IA assume o lugar.",
            "{0} покинул матч. Его место занимает ИИ.",
            "{0}이(가) 게임을 나갔습니다. AI가 대신 플레이합니다.",
            "{0} 离开了对局。由AI接替。",
            "{0} 離開了對局。由AI接替。",
        };
    }
}
