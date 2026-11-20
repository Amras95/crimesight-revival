// CRIMESIGHT Revival - elegir la dificultad de una IA de la sala con una ventana.
//
// En el juego original, "Expulsar" a una IA era la unica forma de tocarla, asi que el servidor de Revival
// lo usaba para ir cambiando su dificultad (Normal -> Dificil -> Experto -> Pesadilla -> Facil -> hueco
// libre): habia que expulsar varias veces. Con el plugin, al pulsar Expulsar sobre una IA sale esta
// ventana con todas las dificultades a la vista (con una frase de que hace cada una), la opcion de
// aplicarla a todas las IA de la sala y la de dejar el hueco libre.
//
// Se manda por el mismo camino que la expulsion (NetworkManager.Kick) con la eleccion pegada al id:
// "bot0001#expert" o "bot0001#expert#all". Asi el servidor sabe que viene del anfitrion sin nada mas.
// Sin el plugin todo sigue como antes (el ciclo de expulsar).
using System;
using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace CrimeSightRevival.Mods
{
    static class AiPicker
    {
        // idiomas del juego (TextManager.GetLangType): ja, en, fr, it, de, es, pt, ru, ko, zh-cn, zh-tw
        static readonly string[] Keys = { "easy", "normal", "hard", "expert", "nightmare" };
        static readonly string[][] Names =
        {
            new[] { "かんたん", "Easy", "Facile", "Facile", "Leicht", "Fácil", "Fácil", "Легко", "쉬움", "简单", "簡單" },
            new[] { "ふつう", "Normal", "Normal", "Normale", "Normal", "Normal", "Normal", "Нормально", "보통", "普通", "普通" },
            new[] { "むずかしい", "Hard", "Difficile", "Difficile", "Schwer", "Difícil", "Difícil", "Сложно", "어려움", "困难", "困難" },
            new[] { "エキスパート", "Expert", "Expert", "Esperto", "Experte", "Experto", "Especialista", "Эксперт", "전문가", "专家", "專家" },
            new[] { "ナイトメア", "Nightmare", "Cauchemar", "Incubo", "Albtraum", "Pesadilla", "Pesadelo", "Кошмар", "악몽", "噩梦", "噩夢" },
        };
        static readonly string[][] Desc =
        {
            new[] { "ミスをする。練習向け。", "Makes mistakes: good for learning.", "Fait des erreurs : idéal pour apprendre.",
                    "Commette errori: ideale per imparare.", "Macht Fehler: gut zum Lernen.", "Comete errores: ideal para aprender.",
                    "Comete erros: ideal para aprender.", "Ошибается: подходит для обучения.", "실수를 합니다. 연습용.",
                    "会犯错，适合练习。", "會犯錯，適合練習。" },
            new[] { "そこそこ考えてプレイ。", "Plays sensibly, without going overboard.", "Joue avec bon sens, sans excès.",
                    "Gioca con criterio, senza esagerare.", "Spielt vernünftig, ohne zu übertreiben.", "Juega con cabeza, sin pasarse.",
                    "Joga com cabeça, sem exagerar.", "Играет разумно, без перегибов.", "적당히 생각하며 플레이.",
                    "正常思考，不会太难。", "正常思考，不會太難。" },
            new[] { "確実な時だけ襲撃し、誰も一人にしない。", "Only strikes when it's sure and never leaves anyone alone.",
                    "N'attaque qu'à coup sûr et ne laisse personne seul.", "Attacca solo quando è sicuro e non lascia nessuno da solo.",
                    "Greift nur an, wenn es sicher ist, und lässt niemanden allein.", "Solo ataca si es seguro y no deja a nadie solo.",
                    "Só ataca quando é certo e não deixa ninguém sozinho.", "Нападает только наверняка и никого не оставляет одного.",
                    "확실할 때만 공격하고 아무도 혼자 두지 않음.", "只在有把握时出手，不让任何人落单。", "只在有把握時出手，不讓任何人落單。" },
            new[] { "ズルなしで深く考える。指示を読み、おとりを使う。", "Thinks harder, no cheating: predicts your orders and uses decoys.",
                    "Réfléchit plus, sans tricher : prévoit vos ordres et utilise des leurres.",
                    "Pensa di più, senza barare: prevede i tuoi ordini e usa esche.",
                    "Denkt weiter, ohne zu schummeln: sieht deine Befehle voraus und nutzt Lockvögel.",
                    "Piensa más, sin trampas: prevé tus órdenes y usa señuelos.", "Pensa mais, sem trapaça: prevê suas ordens e usa iscas.",
                    "Думает глубже, без жульничества: предугадывает приказы и использует приманки.",
                    "속임수 없이 더 깊이 생각: 지시를 예측하고 미끼를 씀.", "想得更深、不作弊：预判你的指令并使用诱饵。",
                    "想得更深、不作弊：預判你的指令並使用誘餌。" },
            new[] { "エキスパート＋あなたの過去の対戦から学習。", "Like Expert, but learns from your previous matches.",
                    "Comme Expert, mais apprend de vos parties précédentes.", "Come Esperto, ma impara dalle tue partite precedenti.",
                    "Wie Experte, lernt aber aus deinen bisherigen Partien.", "Como Experto, pero aprende de tus partidas anteriores.",
                    "Como Especialista, mas aprende com suas partidas anteriores.", "Как Эксперт, но учится на ваших прошлых матчах.",
                    "전문가와 같지만 이전 대전에서 학습함.", "与专家相同，但会从你以前的对局中学习。", "與專家相同，但會從你以前的對局中學習。" },
        };
        static readonly string[] Title = { "{0}の難易度", "Difficulty for {0}", "Difficulté de {0}", "Difficoltà di {0}",
            "Schwierigkeit von {0}", "Dificultad de {0}", "Dificuldade de {0}", "Сложность: {0}", "{0} 난이도", "{0} 的难度", "{0} 的難度" };
        static readonly string[] OnlyThis = { "このAIだけ", "This AI only", "Cette IA seulement", "Solo questa IA", "Nur diese KI",
            "Solo esta IA", "Só esta IA", "Только этот ИИ", "이 AI만", "仅此 AI", "僅此 AI" };
        static readonly string[] AllAis = { "すべてのAI", "All AIs", "Toutes les IA", "Tutte le IA", "Alle KIs",
            "Todas las IA", "Todas as IAs", "Все ИИ", "모든 AI", "所有 AI", "所有 AI" };
        static readonly string[] Free = { "枠を空ける", "Free the seat", "Libérer la place", "Libera il posto", "Platz freigeben",
            "Dejar el hueco libre", "Liberar a vaga", "Освободить место", "자리 비우기", "空出位置", "空出位置" };
        static readonly string[] Cancel = { "キャンセル", "Cancel", "Annuler", "Annulla", "Abbrechen", "Cancelar", "Cancelar",
            "Отмена", "취소", "取消", "取消" };

        static readonly Color Blood = new Color(0.62f, 0.10f, 0.16f, 1f);    // Pesadilla, sobre el boton del juego
        static Skin _sk;
        static GameWindow _gw;                 // la ventana clonada del juego (null: aspecto propio)
        static readonly Color[] _diffBase = new Color[5];
        static Color _allBase, _freeBase, _cancelBase;

        static GameObject _root;
        static string _botId;
        static int _current = -1, _lang = 1;
        static bool _all;
        static readonly RectTransform[] _diffRects = new RectTransform[5];
        static readonly Image[] _diffImgs = new Image[5];
        static RectTransform _allRect, _freeRect, _cancelRect;
        static Image _allImg, _freeImg, _cancelImg;
        static TextMeshProUGUI _desc, _allLabel, _freeLabel, _cancelLabel;
        static int _hover = -2;

        public static void Init(Harmony h)
        {
            try
            {
                var m = AccessTools.Method(typeof(OutGameRoomPopupKickConfirm), "Open");
                if (m == null) { Plugin.L.LogWarning("[IA] no encuentro la ventana de expulsar"); return; }
                h.Patch(m, prefix: new HarmonyMethod(typeof(AiPicker).GetMethod(nameof(BeforeOpen),
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)));
            }
            catch (Exception e) { Plugin.L.LogWarning("[IA] " + e.Message); }
        }

        // Expulsar sobre una IA del servidor de Revival (ids "bot0001"...): nuestra ventana en vez de la del juego
        static bool BeforeOpen(OutGameRoomPopupKickConfirm __instance)
        {
            try
            {
                string id = __instance?.KickingPlayerID;
                if (string.IsNullOrEmpty(id) || !id.StartsWith("bot", StringComparison.Ordinal)) return true;
                string name = "";
                try { name = __instance.GetPlayerName() ?? ""; } catch { }
                Show(id, name);
                return _root == null;          // si no se pudo ensenar, la del juego (el ciclo de siempre)
            }
            catch (Exception e) { Plugin.L.LogWarning("[IA] " + e.Message); return true; }
        }

        static int FromName(string name)
        {
            int a = name.LastIndexOf('('), b = name.LastIndexOf(')');
            if (a < 0 || b <= a) return -1;
            string label = name.Substring(a + 1, b - a - 1).Trim();
            for (int k = 0; k < Names.Length; k++)
                foreach (var n in Names[k])
                    if (string.Equals(n, label, StringComparison.OrdinalIgnoreCase)) return k;
            return -1;
        }

        static string BotLabel(string name)
        {
            int a = name.LastIndexOf('(');
            return (a > 0 ? name.Substring(0, a) : name).Trim();
        }

        static void Show(string botId, string name)
        {
            Close();
            try
            {
                try { _lang = Math.Max(0, Math.Min(10, (int)TextManager.Instance.GetLangType())); } catch { _lang = 1; }
                _botId = botId; _current = FromName(name); _all = false; _hover = -2;
                _sk = Skin.Get();
                _gw = null;
                _root = new GameObject("CSR_AiPicker");
                UnityEngine.Object.DontDestroyOnLoad(_root);
                var canvas = _root.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvas.sortingOrder = 32000;
                var scaler = _root.AddComponent<CanvasScaler>();
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920, 1080);
                scaler.matchWidthOrHeight = 0.5f;
                _root.AddComponent<GraphicRaycaster>();
                var dim = ModOffer.Box("Dim", _root.transform, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
                dim.gameObject.AddComponent<Image>().color = new Color(0f, 0f, 0f, 0.55f);
                string who = BotLabel(name);
                if (ShowNative(string.Format(Title[_lang], string.IsNullOrEmpty(who) ? "IA" : who)))
                {
                    UpdateDesc(_current >= 0 ? _current : 1);
                    Plugin.L.LogInfo("[IA] elegir dificultad de " + botId + " (ahora " + (_current >= 0 ? Keys[_current] : "?") + ")");
                    return;
                }
                var panel = _sk.MakePanel(_root.transform, new Vector2(1120, 490)).transform;

                _sk.MakeText(panel, string.Format(Title[_lang], string.IsNullOrEmpty(who) ? "IA" : who), 38,
                             new Vector2(0, 182), new Vector2(1020, 60), true);
                for (int k = 0; k < 5; k++)
                {
                    _diffImgs[k] = _sk.MakeButton(panel, Names[k][_lang], k == _current, new Vector2(-416 + k * 208, 75),
                                                  new Vector2(196, 74), 26, out _diffRects[k], out _);
                    if (k == 4 && k != _current)
                        _diffImgs[k].color = Color.Lerp(_diffImgs[k].color, Blood, 0.55f);
                    _diffBase[k] = _diffImgs[k].color;
                }
                _desc = _sk.MakeText(panel, "", 26, new Vector2(0, -28), new Vector2(1020, 70), false);
                var bs = new Vector2(300, 64);
                _allImg = _sk.MakeButton(panel, OnlyThis[_lang], false, new Vector2(-330, -165), bs, 26, out _allRect, out _allLabel);
                _freeImg = _sk.MakeButton(panel, Free[_lang], false, new Vector2(0, -165), bs, 26, out _freeRect, out _freeLabel);
                _cancelImg = _sk.MakeButton(panel, Cancel[_lang], false, new Vector2(330, -165), bs, 26, out _cancelRect, out _cancelLabel);
                _allBase = _allImg.color; _freeBase = _freeImg.color; _cancelBase = _cancelImg.color;
                UpdateDesc(_current >= 0 ? _current : 1);
                Plugin.L.LogInfo("[IA] elegir dificultad de " + botId + " (ahora " + (_current >= 0 ? Keys[_current] : "?") + ")");
            }
            catch (Exception e)
            {
                Plugin.L.LogWarning("[IA] no pude ensenar la ventana: " + e.Message);
                Close();
            }
        }


        static void UpdateDesc(int k)
        {
            if (_desc == null || k < 0 || k >= 5) return;
            string t = Names[k][_lang] + ": " + Desc[k][_lang];
            if (_gw != null) _gw.SetText(_desc, t); else _desc.text = t;
        }

        // Con la ventana del juego: dificultades dentro del recuadro, la explicacion debajo y abajo las opciones
        static bool ShowNative(string title)
        {
            var gw = GameWindow.Create(_root.transform);
            if (gw == null) return false;
            _gw = gw;
            gw.SetText(gw.Title, title);
            var box = gw.BodyBox;
            float bw = box.rect.width, bh = box.rect.height;
            float dw = Math.Min(gw.BtnSize.x * 0.62f, bw * 0.96f / 5f - 10f), dh = gw.BtnSize.y * 0.85f;
            for (int k = 0; k < 5; k++)
            {
                bool cur = k == _current;
                _diffImgs[k] = gw.AddButton(Names[k][_lang], k == 4 && !cur, box, new Vector2((k - 2) * (dw + 10f), bh * 0.17f),
                                            new Vector2(dw, dh), cur ? GameWindow.Amber : (Color?)null, out _diffRects[k], out _);
                _diffBase[k] = _diffImgs[k] != null ? _diffImgs[k].color : Color.white;
            }
            var d = gw.Body.rectTransform;
            d.anchorMin = d.anchorMax = d.pivot = new Vector2(0.5f, 0.5f);
            d.sizeDelta = new Vector2(bw * 0.94f, bh * 0.42f);
            d.anchoredPosition = new Vector2(0, -bh * 0.2f);
            gw.Body.enableAutoSizing = true;
            gw.Body.fontSizeMax = gw.Body.fontSize;
            gw.Body.fontSizeMin = Math.Min(14f, gw.Body.fontSize);
            _desc = gw.Body;
            _allImg = gw.AddBottomButton(OnlyThis[_lang], false, 0, 3, null, out _allRect, out _allLabel);
            _freeImg = gw.AddBottomButton(Free[_lang], false, 1, 3, null, out _freeRect, out _freeLabel);
            _cancelImg = gw.AddBottomButton(Cancel[_lang], false, 2, 3, null, out _cancelRect, out _cancelLabel);
            _allBase = _allImg != null ? _allImg.color : Color.white;
            _freeBase = _freeImg != null ? _freeImg.color : Color.white;
            _cancelBase = _cancelImg != null ? _cancelImg.color : Color.white;
            return true;
        }

        static bool Over(RectTransform r, Vector2 m) => r != null && RectTransformUtility.RectangleContainsScreenPoint(r, m, null);

        static bool _tagged, _taggedPad;

        public static void Frame()
        {
            if (_root == null) { _tagged = false; return; }
            if (!_tagged || _taggedPad != Pad.Active) { _tagged = true; _taggedPad = Pad.Active; try { PadTags(); } catch { } }
            Vector2 mouse = Input.mousePosition;
            int over = -1;
            for (int k = 0; k < 5; k++)
            {
                bool o = Over(_diffRects[k], mouse);
                if (o) over = k;
                if (_diffImgs[k] != null && _gw == null) _diffImgs[k].color = o ? Skin.Hover(_diffBase[k]) : _diffBase[k];
            }
            if (over != _hover) { _hover = over; UpdateDesc(over >= 0 ? over : (_current >= 0 ? _current : 1)); }
            bool oAll = Over(_allRect, mouse), oFree = Over(_freeRect, mouse), oCancel = Over(_cancelRect, mouse);
            if (_gw != null) _gw.KeepTexts();
            else
            {
                if (_allImg != null) _allImg.color = oAll ? Skin.Hover(_allBase) : _allBase;
                if (_freeImg != null) _freeImg.color = oFree ? Skin.Hover(_freeBase) : _freeBase;
                if (_cancelImg != null) _cancelImg.color = oCancel ? Skin.Hover(_cancelBase) : _cancelBase;
            }
            if (Input.GetKeyDown(KeyCode.Escape)) { Close(); return; }
            if (!Input.GetMouseButtonDown(0)) return;
            if (over >= 0) Send(Keys[over] + (_all ? "#all" : ""));
            else if (oAll) ToggleAll();
            else if (oFree) Send("free");
            else if (oCancel) Close();
        }

        static void ToggleAll()
        {
            _all = !_all;
            string lbl = Pad.Tag("y") + (_all ? AllAis[_lang] : OnlyThis[_lang]);
            if (_gw != null)
            {
                _gw.SetText(_allLabel, lbl);
                if (_allImg != null) _allImg.color = _all ? GameWindow.Amber : Color.white;   // marcado en ambar
            }
            else
            {
                if (_allLabel != null) _allLabel.text = lbl;
                _sk?.Style(_allImg, _allLabel, _all);      // "Todas las IA" se ve marcado
                if (_allImg != null) _allBase = _allImg.color;
            }
        }

        // ---- mando (CrimeSightRevivalPadUi.cs): B cerrar, Y "Solo esta IA / Todas", X "Dejar el hueco libre"
        internal static bool IsOpen => _root != null;
        internal static void PadCancel() { if (_root != null) Close(); }
        internal static void PadAll() { if (_root != null) ToggleAll(); }
        internal static void PadFree() { if (_root != null) Send("free"); }

        /// <summary>Con mando, el icono de su boton delante del texto de los tres botones de abajo.</summary>
        static void PadTags()
        {
            void Put(TextMeshProUGUI t, string btn, string text)
            {
                if (t == null) return;
                if (Pad.KeyIcons != null) t.spriteAsset = Pad.KeyIcons;
                if (_gw != null) _gw.SetText(t, Pad.Tag(btn) + text); else t.text = Pad.Tag(btn) + text;
            }
            Put(_allLabel, "y", _all ? AllAis[_lang] : OnlyThis[_lang]);
            Put(_freeLabel, "x", Free[_lang]);
            Put(_cancelLabel, "b", Cancel[_lang]);
        }

        static void Send(string choice)
        {
            string id = _botId;
            Close();
            try
            {
                var nm = NetworkManager.Instance;
                if (nm == null || string.IsNullOrEmpty(id)) return;
                nm.Kick(id + "#" + choice,
                    Il2CppInterop.Runtime.DelegateSupport.ConvertDelegate<Il2CppSystem.Action>(new Action(() =>
                        Plugin.L.LogInfo("[IA] " + id + " -> " + choice))),
                    Il2CppInterop.Runtime.DelegateSupport.ConvertDelegate<Il2CppSystem.Action<string, NetworkManager.ErrorCode>>(
                        new Action<string, NetworkManager.ErrorCode>((m, c) => Plugin.L.LogWarning("[IA] el servidor no acepto el cambio: " + m))));
            }
            catch (Exception e) { Plugin.L.LogWarning("[IA] " + e.Message); }
        }

        static void Close()
        {
            if (_root != null)
            {
                UnityEngine.Object.Destroy(_root);
                // La sala se queda "con una ventana abierta" desde que pide abrir la de expulsar: los botones
                // del juego (Confirmar y Volver) la liberan asi; si no, la sala no responde hasta abrir Opciones
                try { OutGameManager.ResetAddPhaseRoot(); }
                catch (Exception e) { Plugin.L.LogWarning("[IA] no pude liberar la sala: " + e.Message); }
            }
            _root = null; _allRect = _freeRect = _cancelRect = null; _allImg = _freeImg = _cancelImg = null;
            _desc = _allLabel = _freeLabel = _cancelLabel = null;
            _gw = null;
            for (int k = 0; k < 5; k++) { _diffRects[k] = null; _diffImgs[k] = null; }
        }
    }
}
