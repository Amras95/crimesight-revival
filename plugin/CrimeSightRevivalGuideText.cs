// CRIMESIGHT Revival - textos de la Guia Revival (ver CrimeSightRevivalGuide.cs).
//
// Una pagina por tema (las flechas de pagina del juego van con el dialogo de un personaje, que la guia no usa).
// En los textos:
//   {A} {B} {X} {Y} {LB} {RB} {LT} {RT} {LBRB} {LTRT} {START} {BACK} {LS} {RS} {DPAD} {DUP} {DDOWN} {DLEFT} {DRIGHT}: icono del boton del
//   mando que se usa (Xbox, PlayStation o Switch); {ST_IRENE} {ST_SUS} {ST_NOSUS}: la imagen del sticker del juego
//   ("Aqui tienes a tu asesino", "Sospecho que es el asesino", "No creo que sea el asesino");
//   {H}...{/H}: resaltado en verde.
// One version per game language, in TextManager order: ja, en, fr, it, de, es, pt, ru, ko, zh-CN, zh-TW.
// {PAGE} parte un tema en varias paginas (se pasan con las flechas de la pantalla).
// Algunas paginas llevan una captura arriba, de lado a lado, y el texto debajo (ver Images y tools/guide_images.py).
namespace CrimeSightRevival.Mods
{
    static class GuideText
    {
        // Guide name in each language (same order as the arrays below)
        static readonly string[] Names = { "Revivalガイド", "Revival Guide", "Guide Revival", "Guida Revival", "Revival-Leitfaden", "Guía Revival", "Guia Revival", "Гид Revival", "Revival 가이드", "Revival 指南", "Revival 指南" };
        public static string Title(int lang) => Names[L(lang)];

        /// <summary>Game language (TextManager order) -> array index; anything unknown shows English.</summary>
        static int L(int lang) => lang >= 0 && lang <= 10 ? lang : 1;

        static readonly string[] TitlesEs =
        {
            "¿Qué es Revival?",
            "Lanzador",
            "Mando",
            "Dificultad de la IA",
            "Irene: dar órdenes a Moriarty",
            "Watson: guiar a Sherlock",
            "Rendirse y salir de una partida",
            "Ajustes de la sala",
            "Mods: stickers, avatares y cursor",
            "Escenarios propios",
        };
        static readonly string[] TitlesEn =
        {
            "What is Revival?",
            "Launcher",
            "Controller",
            "AI difficulty",
            "Irene: giving Moriarty orders",
            "Watson: guiding Sherlock",
            "Forfeiting and leaving a match",
            "Room settings",
            "Mods: stamps, avatars and cursor",
            "Custom scenarios",
        };

        static readonly string[] PagesEs =
        {
            "{H}CRIMESIGHT Revival{/H} devuelve el juego en línea con servidores de la comunidad y le añade funciones nuevas. Esta guía explica cómo se usan.\n\n" +
                "• Se juega desde el {H}lanzador{/H}: contra la IA, con amigos o en servidores de la comunidad.\n" +
                "• Hay soporte de mando, cinco dificultades de IA, stickers, avatares y escenarios propios, y más.\n\n" +
                "Revival no incluye archivos de Konami: necesitas tener CRIMESIGHT en Steam.",
            "Elige uno de los {H}cuatro modos{/H} y pulsa {H}«Jugar»{/H}: el lanzador abre el juego ya conectado.\n\n" +
                "• La sesión termina al cerrar el juego o al pulsar {H}«Terminar sesión»{/H}.\n" +
                "• Una {H}campana{/H} arriba avisa de una versión nueva: púlsala para actualizar.\n" +
                "• Tus partidas, victorias y puntos se guardan en tu PC.",
            "{PAGE}Cada botón que puedes usar muestra su icono al lado en la pantalla.\n\n" +
                "• {H}Menús{/H}: {START} acepta y {B} vuelve o cierra.\n\n" +
                "• {H}Sala{/H}:\n" +
                "<indent=3.3em>{Y} elige jugador.\n<size=40%>\n</size>" +
                "{DLEFT} lo expulsa (en una IA, cambia su dificultad).\n<size=40%>\n</size>" +
                "{DRIGHT} añade jugadores.\n<size=40%>\n</size>" +
                "{DDOWN} quita los huecos vacíos.</indent>\n\n" +
                "• {H}Ajustes y perfil{/H}: {LB} y {RB} cambian de pestaña; {Y} cambia el avatar.\n\n" +
                "• {H}Partida{/H}: {B} omite los diálogos.\n\n" +
                "• {H}Velocidad{/H}: pulsa {LS} (stick izquierdo) para cambiar la velocidad del cursor, o {RS} (stick derecho) para la de la cámara: lenta, media o rápida (el mando vibra 1, 2 o 3 veces).\n\n" +
                "Funciona con mandos de Xbox, PlayStation, Switch y Steam Deck a través de Steam Input. Los iconos de los botones coinciden con los de tu mando.",
            "En la sala, pulsa {H}«Expulsar»{/H} sobre una IA para elegir su dificultad, aplicarla a {H}todas las IA{/H} o {H}dejar el hueco libre{/H} para otro jugador.\n\n" +
                "• {H}Fácil{/H}: comete errores; ideal para aprender.\n" +
                "• {H}Normal{/H}: juega con cabeza, sin pasarse.\n" +
                "• {H}Difícil{/H}: como asesino, solo ataca si es seguro; como detective, nunca deja a un personaje solo.\n" +
                "• {H}Experto{/H}: piensa más, sin trampas; prevé tus órdenes y usa señuelos.\n" +
                "• {H}Pesadilla{/H}: como Experto, pero aprende de tus partidas anteriores en ese servidor (necesita al menos 3 partidas tuyas en ese papel).\n\n" +
                "Cuanto más difícil, más puntos al ganar: de 200 (Fácil) a 1200 (Pesadilla).",
            "Si llevas a Irene y Moriarty lo controla la IA, le das órdenes con tus stickers:\n\n" +
                "{ST_IRENE}  Pon el sticker {H}«¡Aquí tienes a tu asesino!»{/H} sobre un personaje y luego el indicador {H}«Moverse»{/H} en el suelo, donde quieras que vaya: Moriarty lo mueve este turno y te contesta «Entendido». Puedes hacerlo con {H}hasta dos personajes por turno{/H}.\n\n" +
                "• {H}Para matar{/H}: pon el sticker sobre el asesino y {H}«Moverse»{/H} en la casilla de la víctima. Si lleva arma y llega este turno, ataca. Antes, comprueba que no haya testigos.\n" +
                "• Pon {H}«Yo controlaré a…»{/H} sobre un personaje: Moriarty no lo toca este turno.\n" +
                "• Si no le das órdenes, Moriarty juega solo y ataca cuando puede hacerlo sin que lo vean.\n\n" +
                "Tu compañero IA juega en Difícil (o en Experto si los rivales son Experto o Pesadilla).",
            "Si llevas a Watson y Sherlock lo controla la IA, lo guías con tus stickers:\n\n" +
                "{ST_SUS}  Pon {H}«Sospecho que es el asesino»{/H} sobre un personaje (o el indicador {H}«Peligro»{/H}): Sherlock aparta de él a quien esté en su habitación, turno tras turno, y al final lo acusa a él. Te contesta «Entendido».\n\n" +
                "{ST_NOSUS}  Pon {H}«No creo que sea el asesino»{/H} sobre el mismo personaje: Sherlock deja de sospechar de él.\n\n" +
                "Tu compañero IA juega en Difícil (o en Experto si los rivales son Experto o Pesadilla).",
            "Para rendirte durante la fase de mando, abre el menú {H}«Ajustes del sistema»{/H} y elige {H}«Penalización»{/H}. Vale para cualquier papel, desde el primer turno, y cuenta como derrota.\n\n" +
                "• {H}Con otra persona en tu equipo{/H}: se le pregunta primero y tiene 20 segundos para contestar. Si dice que no o no contesta, la partida sigue.\n" +
                "• {H}Si sales de la partida{/H}: te llevas la derrota y, si quedan otras personas, una IA ocupa tu lugar hasta el final. Si no queda nadie más, cuenta como rendirse.\n\n" +
                "Si el anfitrión cierra el juego, la victoria de los invitados se guarda igualmente en su PC (si tienen internet).",
            "En la sala, {H}«Modificar ajustes del juego»{/H} cambia dos ajustes respecto al original:\n\n" +
                "• {H}Máximo de turnos{/H}: el original lo escondía; ahora se ve, de 1 a 99 (por defecto 10). Útil en mapas grandes y escenarios propios.\n" +
                "• {H}Límite de tiempo{/H}: de 60 a 999 segundos en cualquier sala (en las públicas antes llegaba solo a 180), para jugar con calma.\n\n" +
                "Los elige el anfitrión y se aplican a todos.",
            "En el lanzador, abre {H}Mods{/H} para convertir cualquier imagen en un sticker, un avatar o un cursor.\n\n" +
                "• {H}Stickers{/H}: una lámina con varios stickers se separa en stickers sueltos, sin fondo. Puedes añadir a cada uno un texto para el registro de la partida.\n" +
                "• {H}Avatares{/H}: la imagen llena el marco que elijas, sin huecos.\n" +
                "• {H}Cursor{/H}: elige si hace clic con la punta o con el centro. Solo lo ves tú.\n" +
                "• {H}En una sala{/H}: todos reciben los mods del anfitrión. Si un invitado trae los suyos, el anfitrión elige {H}«Descargar»{/H}, {H}«Aceptar siempre»{/H} o {H}«No, gracias»{/H}.\n\n" +
                "Los mods nunca modifican los stickers ni avatares originales del juego, tampoco los de pago.",
            "En el lanzador, abre {H}Mods → «Creador de escenarios»{/H} para recolocar las habitaciones de un escenario y guardarlo como uno nuevo.\n\n" +
                "• Mueve, gira, quita o repite habitaciones, y elige puertas, ventanas de los perros, gas y casillas de salida.\n" +
                "• Pulsa {H}«Prueba rápida»{/H} para probarlo en el {H}«Escenario de pruebas (CSR)»{/H} sin guardarlo.\n" +
                "• Los escenarios guardados salen en la lista de escenarios de la sala, y todos en la sala reciben los del anfitrión antes de empezar.\n\n" +
                "Todos los jugadores de la sala deben activar en el lanzador {H}Mods → «Recarga en caliente»{/H}.",
        };

        static readonly string[] PagesEn =
        {
            "{H}CRIMESIGHT Revival{/H} brings online play back with community servers and adds new features. This guide explains how to use them.\n\n" +
                "• You play from the {H}launcher{/H}: against the AI, with friends or on community servers.\n" +
                "• There's controller support, five AI difficulties, your own stamps, avatars and scenarios, and more.\n\n" +
                "Revival includes no Konami files: you need to own CRIMESIGHT on Steam.",
            "Pick one of the {H}four modes{/H} and click {H}\"Play\"{/H}: the launcher opens the game already connected.\n\n" +
                "• The session ends when you close the game or click {H}\"End session\"{/H}.\n" +
                "• A {H}bell{/H} at the top means a new version is out: click it to update.\n" +
                "• Your matches, wins and points are saved on your PC.",
            "{PAGE}Every button you can use shows its icon next to it on screen.\n\n" +
                "• {H}Menus{/H}: {START} accepts and {B} goes back or closes.\n\n" +
                "• {H}Room{/H}:\n" +
                "<indent=4.1em>{Y} picks a player.\n<size=40%>\n</size>" +
                "{DLEFT} kicks them (on an AI, it changes the difficulty).\n<size=40%>\n</size>" +
                "{DRIGHT} adds players.\n<size=40%>\n</size>" +
                "{DDOWN} removes empty seats.</indent>\n\n" +
                "• {H}Settings and profile{/H}: {LB} and {RB} switch tabs; {Y} changes your avatar.\n\n" +
                "• {H}Match{/H}: {B} skips dialogue.\n\n" +
                "• {H}Speed{/H}: press {LS} (left stick) to change the cursor speed, or {RS} (right stick) for the camera: slow, medium or fast (the controller vibrates 1, 2 or 3 times).\n\n" +
                "It works with Xbox, PlayStation, Switch and Steam Deck controllers through Steam Input. The button icons match yours.",
            "In the room, click {H}\"Kick\"{/H} on an AI to pick its difficulty, apply it to {H}every AI{/H}, or {H}free the seat{/H} for another player.\n\n" +
                "• {H}Easy{/H}: makes mistakes; good for learning.\n" +
                "• {H}Normal{/H}: plays sensibly, without going overboard.\n" +
                "• {H}Hard{/H}: as the killer, only strikes when it's safe; as a detective, never leaves a character alone.\n" +
                "• {H}Expert{/H}: thinks harder, no cheating; predicts your orders and uses decoys.\n" +
                "• {H}Nightmare{/H}: like Expert, but learns from your previous matches on that server (it needs at least 3 of yours in that role).\n\n" +
                "The harder the AI, the more points you get for winning: from 200 (Easy) to 1200 (Nightmare).",
            "If you play Irene and Moriarty is controlled by the AI, you give him orders with your stamps:\n\n" +
                "{ST_IRENE}  Place the {H}\"Here is your villain!\"{/H} stamp on a character, then the {H}\"Move\"{/H} ping on the floor where you want them to go: Moriarty moves them this turn and answers \"Understood\". You can do this with {H}up to two characters per turn{/H}.\n\n" +
                "• {H}To kill{/H}: place the stamp on the killer and {H}\"Move\"{/H} on the victim's tile. If they're armed and can get there this turn, they strike. Check for witnesses first.\n" +
                "• Place {H}\"I'll command…\"{/H} on a character: Moriarty leaves them alone this turn.\n" +
                "• If you give no orders, Moriarty plays on his own and strikes when he can do so unseen.\n\n" +
                "Your AI partner plays on Hard (or Expert if your opponents are Expert or Nightmare).",
            "If you play Watson and Sherlock is controlled by the AI, you guide him with your stamps:\n\n" +
                "{ST_SUS}  Place {H}\"I suspect they are the villain\"{/H} on a character (or the {H}\"Danger\"{/H} ping): Sherlock moves everyone in their room away from them, turn after turn, and accuses them at the end. He answers \"Understood\".\n\n" +
                "{ST_NOSUS}  Place {H}\"I don't think they are the villain\"{/H} on the same character: Sherlock stops suspecting them.\n\n" +
                "Your AI partner plays on Hard (or Expert if your opponents are Expert or Nightmare).",
            "To forfeit during the command phase, open the {H}\"System Settings\"{/H} menu and choose {H}\"Forfeit\"{/H}. It works for any role, from the first turn, and counts as a loss.\n\n" +
                "• {H}With another person on your team{/H}: they're asked first and have 20 seconds to answer. If they say no or don't answer, the match goes on.\n" +
                "• {H}If you leave the match{/H}: you get the loss and, if other people are still playing, an AI takes your place until the end. If no one else is left, it counts as forfeiting.\n\n" +
                "If the host closes the game, the guests' win is still recorded on their PC (if they're online).",
            "In the room, {H}\"Edit Game Settings\"{/H} works differently from the original in two settings:\n\n" +
                "• {H}Max. Turns{/H}: the original hid it; now it's shown, from 1 to 99 (10 by default). Handy for big maps and custom scenarios.\n" +
                "• {H}Time Limit{/H}: from 60 to 999 seconds in any room (public rooms used to stop at 180), to play at your own pace.\n\n" +
                "The host sets them, and they apply to everyone.",
            "In the launcher, open {H}Mods{/H} to turn any image into a stamp, an avatar or a cursor.\n\n" +
                "• {H}Stamps{/H}: a sheet of several stamps is split into separate stamps, with the background removed. You can add a caption to each one for the match log.\n" +
                "• {H}Avatars{/H}: the image fills the frame you choose, with no gaps.\n" +
                "• {H}Cursor{/H}: choose whether it clicks at the tip or the centre. Only you see it.\n" +
                "• {H}In a room{/H}: everyone gets the host's mods. If a guest brings their own, the host chooses {H}\"Download\"{/H}, {H}\"Always accept\"{/H} or {H}\"No thanks\"{/H}.\n\n" +
                "Mods never change the game's original stamps or avatars, including paid ones.",
            "In the launcher, open {H}Mods → \"Scenario Creator\"{/H} to rearrange the rooms of a scenario and save it as a new one.\n\n" +
                "• Move, rotate, remove or repeat rooms, and choose doors, dog windows, gas and starting cells.\n" +
                "• Click {H}\"Quick test\"{/H} to try it in the {H}\"Test Stage (CSR)\"{/H} without saving it.\n" +
                "• Saved scenarios appear in the room's scenario list, and everyone in the room gets the host's scenarios before the match starts.\n\n" +
                "Every player in the room must turn on {H}Mods → \"Hot reload\"{/H} in the launcher.",
        };

        static readonly string[] Helps =
        {
            "Revivalで追加された機能の使い方：ランチャー、コントローラー、AI、スタンプなど。",
            "How everything Revival adds works: launcher, controller, AI, stamps and more.",
            "Comment marche tout ce qu'ajoute Revival : lanceur, manette, IA, stickers et plus.",
            "Come funziona tutto ciò che aggiunge Revival: launcher, controller, IA, sticker e altro.",
            "So funktioniert alles, was Revival hinzufügt: Launcher, Controller, KI, Sticker und mehr.",
            "Cómo funciona lo que añade Revival: lanzador, mando, IA, stickers y más.",
            "Como funciona tudo o que o Revival adiciona: inicializador, controle, IA, emojis e mais.",
            "Как работает все, что добавляет Revival: лаунчер, геймпад, ИИ, шаблоны и не только.",
            "Revival이 더한 기능의 사용법: 런처, 컨트롤러, AI, 스탬프 등.",
            "Revival新增功能的用法：启动器、手柄、AI、表情等。",
            "Revival新增功能的用法：啟動器、控制器、AI、貼圖等。",
        };
        public static string Help(int lang) => Helps[L(lang)];

        // Tema -> captura (nombre en GuideImages) que sale encima del texto
        static readonly System.Collections.Generic.Dictionary<int, string> Images = new()
        {
            [1] = "launcher",         // El lanzador
        };

        // Lo que hace cada boton, al final de su linea en el dibujo del mando (pagina "Mando"): primero los 8 de la
        // izquierda (LT, LB, Back, cruceta arriba / derecha / izquierda / abajo, stick izquierdo) y luego los 8 de la
        // derecha (RT, RB, Start, Y, X, B, A, stick derecho). Cortos para que se lean bien; lo de la sala y los menus va
        // en la segunda pagina.
        static readonly string[] PadEs =
        {
            "Alejar", "Girar · Pestaña", "Registro", "Ajustes",
            "Personaje siguiente", "Personaje anterior", "Quitar huecos", "Cursor",
            "Acercar", "Girar · Pestaña", "Fin turno · Aceptar", "Sospechosos",
            "Stickers", "Cancelar · Atrás", "Clic", "Cámara",
        };
        static readonly string[] PadEn =
        {
            "Zoom out", "Rotate · Tab", "Log", "Settings",
            "Next character", "Previous character", "Remove seats", "Cursor",
            "Zoom in", "Rotate · Tab", "End turn · Accept", "Suspects",
            "Stamps", "Cancel · Back", "Click", "Camera",
        };

        static readonly string[] TitlesJa =
        {
            "Revivalとは？",
            "ランチャー",
            "コントローラー",
            "AIの難易度",
            "Irene：Moriartyに指示する",
            "Watson：Sherlockを導く",
            "降参と対戦からの退出",
            "ルーム設定",
            "MOD：スタンプ・アバター・カーソル",
            "オリジナルステージ",
        };

        static readonly string[] PagesJa =
        {
            "{H}CRIMESIGHT Revival{/H}は、コミュニティサーバーでオンライン対戦を復活させ、新しい機能を追加します。このガイドではその使い方を説明します。\n\n" +
                "• {H}ランチャー{/H}から遊びます：AIと、友達と、またはコミュニティサーバーで。\n" +
                "• コントローラー対応、5段階のAI難易度、オリジナルのスタンプ・アバター・ステージなどがあります。\n\n" +
                "RevivalにKONAMIのファイルは含まれていません：SteamでCRIMESIGHTを持っている必要があります。",
            "{H}4つのモード{/H}から1つ選んで{H}「プレイ」{/H}を押すと、ランチャーが接続済みのゲームを開きます。\n\n" +
                "• ゲームを閉じるか{H}「セッションを終了」{/H}を押すと、セッションが終わります。\n" +
                "• 上の{H}ベル{/H}は新しいバージョンのお知らせです：押すと更新します。\n" +
                "• 対戦数、勝利数、ポイントはPCに保存されます。",
            "{PAGE}画面上の操作できる場所には、使うボタンのアイコンが表示されます。\n\n" +
                "• {H}メニュー{/H}：{START}で決定、{B}で戻る・閉じる。\n\n" +
                "• {H}ルーム{/H}：\n" +
                "<indent=5.5em>{Y}でプレイヤーを選択。\n<size=40%>\n</size>" +
                "{DLEFT}でキック（AIなら難易度を変更）。\n<size=40%>\n</size>" +
                "{DRIGHT}でプレイヤーを追加。\n<size=40%>\n</size>" +
                "{DDOWN}で空き枠を削除。</indent>\n\n" +
                "• {H}設定とプロフィール{/H}：{LB}と{RB}でタブを切り替え、{Y}でアバターを変更。\n\n" +
                "• {H}対戦{/H}：{B}で会話をスキップ。\n\n" +
                "• {H}速度{/H}：{LS}（左スティック）を押すとカーソル、{RS}（右スティック）を押すとカメラの速度が変わります：遅い・普通・速い（コントローラーが1・2・3回振動）。\n\n" +
                "Steam入力を通じて、Xbox、PlayStation、Switch、Steam Deckのコントローラーに対応しています。ボタンのアイコンはお使いのコントローラーに合わせて表示されます。",
            "ルームでAIの{H}「キック」{/H}を押すと、難易度を選んだり、{H}すべてのAI{/H}に適用したり、{H}枠を空けて{/H}他のプレイヤーを入れたりできます。\n\n" +
                "• {H}かんたん{/H}：ミスをします。慣れるのに最適です。\n" +
                "• {H}ふつう{/H}：無理をせず、よく考えて遊びます。\n" +
                "• {H}むずかしい{/H}：Moriarty側では安全なときだけ襲い、Sherlock側ではキャラを決して1人にしません。\n" +
                "• {H}エキスパート{/H}：ズルなしでより深く考え、あなたの指示を読んでおとりも使います。\n" +
                "• {H}ナイトメア{/H}：エキスパートと同じですが、そのサーバーでのあなたの過去の対戦から学びます（その役でのあなたの対戦が3回以上必要）。\n\n" +
                "難しいほど勝利時のポイントが増えます：200（かんたん）から1200（ナイトメア）まで。",
            "IreneでプレイしていてMoriartyをAIが操作している場合、スタンプで指示を出せます：\n\n" +
                "{ST_IRENE}  キャラに{H}「キラーは任せろ！」{/H}スタンプを置き、行かせたい床に{H}「移動」{/H}Pingを置きます：Moriartyはこのターンそのキャラを動かし、「了解」と答えます。{H}1ターンに2キャラまで{/H}指示できます。\n\n" +
                "• {H}殺害するには{/H}：キラーにスタンプを置き、ターゲットのマスに{H}「移動」{/H}を置きます。武器を持っていてこのターンにたどり着ければ襲います。先に目撃者がいないか確認しましょう。\n" +
                "• キャラに{H}「〜を制御します」{/H}を置くと、Moriartyはこのターンそのキャラを動かしません。\n" +
                "• 指示を出さなければ、Moriartyは自分で動き、見られずに襲えるときに襲います。\n\n" +
                "AIの味方はむずかしいでプレイします（相手がエキスパートかナイトメアならエキスパート）。",
            "WatsonでプレイしていてSherlockをAIが操作している場合、スタンプで導けます：\n\n" +
                "{ST_SUS}  キャラに{H}「キラーだと疑っています」{/H}（または{H}「危険」{/H}Ping）を置くと、Sherlockは毎ターン同じ部屋の人をそのキャラから離し、最後にそのキャラを指名します。「了解」と答えます。\n\n" +
                "{ST_NOSUS}  同じキャラに{H}「キラーではないと言っています」{/H}を置くと、Sherlockは疑うのをやめます。\n\n" +
                "AIの味方はむずかしいでプレイします（相手がエキスパートかナイトメアならエキスパート）。",
            "コマンドフェイズ中に降参するには、{H}「システム設定」{/H}メニューを開いて{H}「降参」{/H}を選びます。どの役でも1ターン目からでき、敗北になります。\n\n" +
                "• {H}チームに他の人がいる場合{/H}：先にその人に確認し、20秒以内に答えてもらいます。断るか答えがなければ、対戦は続きます。\n" +
                "• {H}対戦から退出した場合{/H}：あなたは敗北となり、他の人がまだプレイしていれば、最後までAIがあなたの代わりを務めます。誰も残っていなければ、降参と同じ扱いです。\n\n" +
                "ホストがゲームを閉じても、ゲストの勝利はそれぞれのPCに記録されます（インターネットに接続していれば）。",
            "ルームの{H}「ゲーム設定変更」{/H}では、2つの設定がオリジナルと異なります：\n\n" +
                "• {H}最大ターン数{/H}：オリジナルでは隠れていましたが、表示されるようになりました。1〜99（標準は10）。広いマップやオリジナルステージに便利です。\n" +
                "• {H}制限時間{/H}：どのルームでも60〜999秒（以前は公開ルームでは180秒まで）。じっくり遊べます。\n\n" +
                "ホストが決め、全員に適用されます。",
            "ランチャーで{H}MOD{/H}を開くと、どんな画像もスタンプ、アバター、カーソルにできます。\n\n" +
                "• {H}スタンプ{/H}：複数のスタンプが並んだ画像は、背景を消して1つずつに分けられます。それぞれに対戦ログ用のテキストを付けられます。\n" +
                "• {H}アバター{/H}：選んだ枠いっぱいに、すき間なく画像が入ります。\n" +
                "• {H}カーソル{/H}：先端と中央のどちらでクリックするか選べます。見えるのはあなただけです。\n" +
                "• {H}ルームでは{/H}：全員がホストのMODを受け取ります。ゲストが自分のMODを持っていれば、ホストは{H}「ダウンロード」{/H}、{H}「常に受け入れる」{/H}、{H}「いいえ」{/H}から選びます。\n\n" +
                "MODがゲーム本来のスタンプやアバター（有料のものも含む）を変えることはありません。",
            "ランチャーで{H}MOD →「ステージクリエイター」{/H}を開くと、ステージの部屋を並べ替えて新しいステージとして保存できます。\n\n" +
                "• 部屋の移動・回転・削除・複製ができ、ドア、野犬の窓、ガス、開始マスも選べます。\n" +
                "• {H}「クイックテスト」{/H}を押すと、保存せずに{H}「テスト用ステージ (CSR)」{/H}で試せます。\n" +
                "• 保存したステージはルームのステージ一覧に表示され、ルームの全員が開始前にホストのステージを受け取ります。\n\n" +
                "ルームの全員が、ランチャーで{H}MOD →「ホットリロード」{/H}をオンにする必要があります。",
        };

        static readonly string[] PadJa =
        {
            "ズームアウト", "回転 · タブ", "ログ", "設定",
            "次のキャラ", "前のキャラ", "空き枠を削除", "カーソル",
            "ズームイン", "回転 · タブ", "ターン終了 · 決定", "容疑者",
            "スタンプ", "キャンセル · 戻る", "クリック", "カメラ",
        };

        static readonly string[] TitlesFr =
        {
            "Qu'est-ce que Revival ?",
            "Lanceur",
            "Manette",
            "Difficulté de l'IA",
            "Irene : donner des ordres à Moriarty",
            "Watson : guider Sherlock",
            "Abandonner et quitter une partie",
            "Paramètres du salon",
            "Mods : stickers, avatars et curseur",
            "Scénarios perso",
        };

        static readonly string[] PagesFr =
        {
            "{H}CRIMESIGHT Revival{/H} fait revivre le jeu en ligne grâce à des serveurs communautaires et ajoute de nouvelles fonctions. Ce guide explique comment les utiliser.\n\n" +
                "• On joue depuis le {H}lanceur{/H} : contre l'IA, avec des amis ou sur des serveurs communautaires.\n" +
                "• Prise en charge de la manette, cinq difficultés d'IA, vos propres stickers, avatars et scénarios, et plus encore.\n\n" +
                "Revival ne contient aucun fichier de Konami : vous devez posséder CRIMESIGHT sur Steam.",
            "Choisissez l'un des {H}quatre modes{/H} et cliquez sur {H}\"Jouer\"{/H} : le lanceur ouvre le jeu déjà connecté.\n\n" +
                "• La session se termine quand vous fermez le jeu ou cliquez sur {H}\"Terminer la session\"{/H}.\n" +
                "• Une {H}cloche{/H} en haut signale une nouvelle version : cliquez dessus pour mettre à jour.\n" +
                "• Vos parties, victoires et points sont enregistrés sur votre PC.",
            "{PAGE}Chaque bouton utilisable affiche son icône à côté, à l'écran.\n\n" +
                "• {H}Menus{/H} : {START} valide et {B} revient ou ferme.\n\n" +
                "• {H}Salon{/H} :\n" +
                "<indent=4.3em>{Y} choisit un joueur.\n<size=40%>\n</size>" +
                "{DLEFT} l'expulse (sur une IA, change sa difficulté).\n<size=40%>\n</size>" +
                "{DRIGHT} ajoute des joueurs.\n<size=40%>\n</size>" +
                "{DDOWN} retire les places vides.</indent>\n\n" +
                "• {H}Paramètres et profil{/H} : {LB} et {RB} changent d'onglet ; {Y} change l'avatar.\n\n" +
                "• {H}Partie{/H} : {B} passe les dialogues.\n\n" +
                "• {H}Vitesse{/H} : appuyez sur {LS} (stick gauche) pour la vitesse du curseur, ou sur {RS} (stick droit) pour celle de la caméra : lente, moyenne ou rapide (la manette vibre 1, 2 ou 3 fois).\n\n" +
                "Compatible avec les manettes Xbox, PlayStation, Switch et Steam Deck via Steam Input. Les icônes correspondent à votre manette.",
            "Dans le salon, cliquez sur {H}\"Expulser\"{/H} sur une IA pour choisir sa difficulté, l'appliquer à {H}toutes les IA{/H} ou {H}libérer la place{/H} pour un autre joueur.\n\n" +
                "• {H}Facile{/H} : fait des erreurs ; idéal pour apprendre.\n" +
                "• {H}Normal{/H} : joue avec bon sens, sans excès.\n" +
                "• {H}Difficile{/H} : côté Moriarty, n'attaque que sans risque ; côté Sherlock, ne laisse jamais un personnage seul.\n" +
                "• {H}Expert{/H} : réfléchit davantage, sans tricher ; anticipe vos ordres et utilise des leurres.\n" +
                "• {H}Cauchemar{/H} : comme Expert, mais apprend de vos parties précédentes sur ce serveur (il lui faut au moins 3 de vos parties dans ce rôle).\n\n" +
                "Plus l'IA est difficile, plus une victoire rapporte de points : de 200 (Facile) à 1200 (Cauchemar).",
            "Si vous jouez Irene et que Moriarty est contrôlé par l'IA, vous lui donnez des ordres avec vos stickers :\n\n" +
                "{ST_IRENE}  Placez le sticker {H}\"Je contrôle l'assassin !\"{/H} sur un personnage, puis le marquage {H}\"Déplacement\"{/H} au sol, là où il doit aller : Moriarty le déplace ce tour-ci et répond \"Compris\". {H}Deux personnages par tour au maximum{/H}.\n\n" +
                "• {H}Pour tuer{/H} : placez le sticker sur l'assassin et {H}\"Déplacement\"{/H} sur la case de la cible. S'il est armé et l'atteint ce tour-ci, il attaque. Vérifiez d'abord l'absence de témoins.\n" +
                "• Placez {H}\"Je vais contrôler…\"{/H} sur un personnage : Moriarty n'y touche pas ce tour-ci.\n" +
                "• Sans ordres, Moriarty joue seul et attaque sans être vu.\n\n" +
                "Votre partenaire IA joue en Difficile (ou en Expert si vos adversaires sont en Expert ou Cauchemar).",
            "Si vous jouez Watson et que Sherlock est contrôlé par l'IA, vous le guidez avec vos stickers :\n\n" +
                "{ST_SUS}  Placez {H}\"Je pense que c'est l'assassin.\"{/H} sur un personnage (ou le marquage {H}\"Danger\"{/H}) : tour après tour, Sherlock éloigne de lui tous ceux de sa pièce, puis l'accuse à la fin. Il répond \"Compris\".\n\n" +
                "{ST_NOSUS}  Placez {H}\"Je ne pense pas que ce soit l'assassin.\"{/H} sur le même personnage : Sherlock cesse de le soupçonner.\n\n" +
                "Votre partenaire IA joue en Difficile (ou en Expert si vos adversaires sont en Expert ou Cauchemar).",
            "Pour abandonner pendant la phase d'ordre, ouvrez le menu {H}\"Configuration\"{/H} et choisissez {H}\"Abandonner\"{/H}. C'est possible dans tous les rôles dès le premier tour, et cela compte comme une défaite.\n\n" +
                "• {H}Avec une autre personne dans votre équipe{/H} : on lui demande d'abord, et elle a 20 secondes pour répondre. Si elle refuse ou ne répond pas, la partie continue.\n" +
                "• {H}Si vous quittez la partie{/H} : la défaite vous est attribuée et, s'il reste d'autres personnes, une IA vous remplace jusqu'à la fin. S'il ne reste personne, cela compte comme un abandon.\n\n" +
                "Si l'hôte ferme le jeu, la victoire des invités est quand même enregistrée sur leur PC (s'ils sont en ligne).",
            "Dans le salon, {H}\"Modifier les paramètres de partie\"{/H} change deux paramètres par rapport à l'original :\n\n" +
                "• {H}Tours max{/H} : l'original le cachait ; il est maintenant affiché, de 1 à 99 (10 par défaut). Pratique pour les grandes cartes et les scénarios perso.\n" +
                "• {H}Limite de temps{/H} : de 60 à 999 secondes dans tous les salons (les salons publics s'arrêtaient à 180), pour jouer à votre rythme.\n\n" +
                "L'hôte les choisit, et ils s'appliquent à tous.",
            "Dans le lanceur, ouvrez {H}Mods{/H} pour transformer n'importe quelle image en sticker, en avatar ou en curseur.\n\n" +
                "• {H}Stickers{/H} : une planche de plusieurs stickers est découpée en stickers séparés, sans fond. Vous pouvez ajouter à chacun un texte pour le journal de la partie.\n" +
                "• {H}Avatars{/H} : l'image remplit le cadre choisi, sans vide.\n" +
                "• {H}Curseur{/H} : choisissez s'il clique avec la pointe ou le centre. Vous seul le voyez.\n" +
                "• {H}Dans un salon{/H} : tout le monde reçoit les mods de l'hôte. Si un invité apporte les siens, l'hôte choisit {H}\"Télécharger\"{/H}, {H}\"Toujours accepter\"{/H} ou {H}\"Non merci\"{/H}.\n\n" +
                "Les mods ne modifient jamais les stickers ni les avatars d'origine du jeu, payants compris.",
            "Dans le lanceur, ouvrez {H}Mods → \"Créateur de scénarios\"{/H} pour réorganiser les pièces d'un scénario et l'enregistrer comme nouveau scénario.\n\n" +
                "• Déplacez, tournez, retirez ou dupliquez des pièces, et choisissez les portes, les fenêtres des chiens, le gaz et les cases de départ.\n" +
                "• Cliquez sur {H}\"Test rapide\"{/H} pour l'essayer dans le {H}\"Scénario de test (CSR)\"{/H} sans l'enregistrer.\n" +
                "• Les scénarios enregistrés apparaissent dans la liste des scénarios du salon, et tout le monde reçoit ceux de l'hôte avant le début.\n\n" +
                "Tous les joueurs du salon doivent activer {H}Mods → \"Rechargement à chaud\"{/H} dans le lanceur.",
        };

        static readonly string[] PadFr =
        {
            "Zoom arrière", "Pivoter · Onglet", "Journal", "Paramètres",
            "Perso suivant", "Perso précédent", "Retirer places", "Curseur",
            "Zoom avant", "Pivoter · Onglet", "Fin du tour · Valider", "Suspects",
            "Stickers", "Annuler · Retour", "Clic", "Caméra",
        };

        static readonly string[] TitlesIt =
        {
            "Cos'è Revival?",
            "Launcher",
            "Controller",
            "Difficoltà dell'IA",
            "Irene: dare ordini a Moriarty",
            "Watson: guidare Sherlock",
            "Forfait e uscita da una partita",
            "Impostazioni della stanza",
            "Mod: sticker, avatar e cursore",
            "Scenari personalizzati",
        };

        static readonly string[] PagesIt =
        {
            "{H}CRIMESIGHT Revival{/H} riporta il gioco online con server della community e aggiunge nuove funzioni. Questa guida spiega come usarle.\n\n" +
                "• Si gioca dal {H}launcher{/H}: contro l'IA, con gli amici o sui server della community.\n" +
                "• Supporto per controller, cinque difficoltà dell'IA, sticker, avatar e scenari tuoi, e altro ancora.\n\n" +
                "Revival non include file di Konami: devi possedere CRIMESIGHT su Steam.",
            "Scegli una delle {H}quattro modalità{/H} e premi {H}\"Gioca\"{/H}: il launcher apre il gioco già connesso.\n\n" +
                "• La sessione finisce quando chiudi il gioco o premi {H}\"Termina sessione\"{/H}.\n" +
                "• Una {H}campanella{/H} in alto segnala una nuova versione: premila per aggiornare.\n" +
                "• Partite, vittorie e punti vengono salvati sul tuo PC.",
            "{PAGE}Ogni tasto che puoi usare mostra la sua icona accanto, sullo schermo.\n\n" +
                "• {H}Menu{/H}: {START} conferma e {B} torna indietro o chiude.\n\n" +
                "• {H}Stanza{/H}:\n" +
                "<indent=4.6em>{Y} sceglie un giocatore.\n<size=40%>\n</size>" +
                "{DLEFT} lo espelle (su un'IA, ne cambia la difficoltà).\n<size=40%>\n</size>" +
                "{DRIGHT} aggiunge giocatori.\n<size=40%>\n</size>" +
                "{DDOWN} toglie i posti vuoti.</indent>\n\n" +
                "• {H}Impostazioni e profilo{/H}: {LB} e {RB} cambiano scheda; {Y} cambia l'avatar.\n\n" +
                "• {H}Partita{/H}: {B} salta i dialoghi.\n\n" +
                "• {H}Velocità{/H}: premi {LS} (levetta sinistra) per la velocità del cursore, o {RS} (levetta destra) per quella della telecamera: lenta, media o veloce (il controller vibra 1, 2 o 3 volte).\n\n" +
                "Funziona con i controller Xbox, PlayStation, Switch e Steam Deck tramite Steam Input. Le icone dei tasti corrispondono al tuo controller.",
            "Nella stanza, premi {H}\"Espelli\"{/H} su un'IA per sceglierne la difficoltà, applicarla a {H}tutte le IA{/H} o {H}liberare il posto{/H} per un altro giocatore.\n\n" +
                "• {H}Facile{/H}: commette errori; ideale per imparare.\n" +
                "• {H}Normale{/H}: gioca con criterio, senza esagerare.\n" +
                "• {H}Difficile{/H}: con Moriarty attacca solo se è sicuro; con Sherlock non lascia mai solo un personaggio.\n" +
                "• {H}Esperto{/H}: ragiona di più, senza barare; prevede i tuoi ordini e usa esche.\n" +
                "• {H}Incubo{/H}: come Esperto, ma impara dalle tue partite precedenti su quel server (servono almeno 3 tue partite in quel ruolo).\n\n" +
                "Più è difficile, più punti ottieni vincendo: da 200 (Facile) a 1200 (Incubo).",
            "Se giochi con Irene e Moriarty è controllato dall'IA, gli dai ordini con i tuoi sticker:\n\n" +
                "{ST_IRENE}  Metti lo sticker {H}\"Ecco l'aggressore!\"{/H} su un personaggio, poi il segnale {H}\"Sposta\"{/H} sul pavimento, dove vuoi che vada: Moriarty lo muove in questo turno e risponde \"Capito\". {H}Al massimo due personaggi per turno{/H}.\n\n" +
                "• {H}Per uccidere{/H}: metti lo sticker sull'aggressore e {H}\"Sposta\"{/H} sulla casella del bersaglio. Se è armato e ci arriva in questo turno, attacca. Prima controlla che non ci siano testimoni.\n" +
                "• Metti {H}\"Io impartirò comandi a…\"{/H} su un personaggio: Moriarty non lo tocca in questo turno.\n" +
                "• Senza ordini, Moriarty gioca da solo e attacca senza farsi vedere.\n\n" +
                "Il tuo compagno IA gioca a Difficile (o a Esperto se gli avversari sono a Esperto o Incubo).",
            "Se giochi con Watson e Sherlock è controllato dall'IA, lo guidi con i tuoi sticker:\n\n" +
                "{ST_SUS}  Metti {H}\"Sospetto che sia l'aggressore.\"{/H} su un personaggio (o il segnale {H}\"Pericolo\"{/H}): turno dopo turno, Sherlock allontana da lui chi si trova nella sua stessa stanza e alla fine lo accusa. Risponde \"Capito\".\n\n" +
                "{ST_NOSUS}  Metti {H}\"Non penso che sia l'aggressore.\"{/H} sullo stesso personaggio: Sherlock smette di sospettare di lui.\n\n" +
                "Il tuo compagno IA gioca a Difficile (o a Esperto se gli avversari sono a Esperto o Incubo).",
            "Per dichiarare forfait durante la fase di comando, apri il menu {H}\"Impostazioni sistema\"{/H} e scegli {H}\"Forfait\"{/H}. Vale per qualsiasi ruolo, dal primo turno, e conta come sconfitta.\n\n" +
                "• {H}Con un'altra persona nella tua squadra{/H}: prima viene chiesto a lei, che ha 20 secondi per rispondere. Se dice di no o non risponde, la partita continua.\n" +
                "• {H}Se esci dalla partita{/H}: la sconfitta va a te e, se restano altre persone, un'IA prende il tuo posto fino alla fine. Se non resta nessun altro, conta come forfait.\n\n" +
                "Se l'host chiude il gioco, la vittoria degli ospiti viene comunque registrata sul loro PC (se sono online).",
            "Nella stanza, {H}\"Modifica impostazioni gioco\"{/H} cambia due impostazioni rispetto all'originale:\n\n" +
                "• {H}Numero max turni{/H}: l'originale lo nascondeva; ora è visibile, da 1 a 99 (10 di base). Utile per mappe grandi e scenari personalizzati.\n" +
                "• {H}Limite di tempo{/H}: da 60 a 999 secondi in qualsiasi stanza (nelle stanze pubbliche prima si arrivava solo a 180), per giocare con calma.\n\n" +
                "Le sceglie l'host e valgono per tutti.",
            "Nel launcher, apri {H}Mod{/H} per trasformare qualsiasi immagine in uno sticker, un avatar o un cursore.\n\n" +
                "• {H}Sticker{/H}: un foglio con più sticker viene diviso in sticker singoli, senza sfondo. A ognuno puoi aggiungere un testo per il registro della partita.\n" +
                "• {H}Avatar{/H}: l'immagine riempie la cornice che scegli, senza spazi vuoti.\n" +
                "• {H}Cursore{/H}: scegli se clicca con la punta o con il centro. Lo vedi solo tu.\n" +
                "• {H}In una stanza{/H}: tutti ricevono le mod dell'host. Se un ospite porta le sue, l'host sceglie {H}\"Scarica\"{/H}, {H}\"Accetta sempre\"{/H} o {H}\"No, grazie\"{/H}.\n\n" +
                "Le mod non cambiano mai gli sticker e gli avatar originali del gioco, nemmeno quelli a pagamento.",
            "Nel launcher, apri {H}Mod → \"Creatore di scenari\"{/H} per risistemare le stanze di uno scenario e salvarlo come nuovo.\n\n" +
                "• Sposta, ruota, togli o ripeti le stanze, e scegli porte, finestre dei cani, gas e caselle di partenza.\n" +
                "• Premi {H}\"Prova rapida\"{/H} per provarlo nello {H}\"Scenario di prova (CSR)\"{/H} senza salvarlo.\n" +
                "• Gli scenari salvati compaiono nell'elenco degli scenari della stanza, e tutti nella stanza ricevono quelli dell'host prima di iniziare.\n\n" +
                "Tutti i giocatori nella stanza devono attivare {H}Mod → \"Ricarica a caldo\"{/H} nel launcher.",
        };

        static readonly string[] PadIt =
        {
            "Riduci zoom", "Ruota · Scheda", "Registro", "Impostazioni",
            "Personaggio succ.", "Personaggio prec.", "Togli posti", "Cursore",
            "Aumenta zoom", "Ruota · Scheda", "Fine turno · Conferma", "Sospettati",
            "Sticker", "Annulla · Indietro", "Clic", "Telecamera",
        };

        static readonly string[] TitlesDe =
        {
            "Was ist Revival?",
            "Launcher",
            "Controller",
            "KI-Schwierigkeit",
            "Irene: Moriarty Befehle geben",
            "Watson: Sherlock lenken",
            "Aufgeben und Spiel verlassen",
            "Raumeinstellungen",
            "Mods: Sticker, Avatare und Cursor",
            "Eigene Szenarien",
        };

        static readonly string[] PagesDe =
        {
            "{H}CRIMESIGHT Revival{/H} bringt das Online-Spiel mit Community-Servern zurück und fügt neue Funktionen hinzu. Diese Anleitung erklärt, wie sie funktionieren.\n\n" +
                "• Gespielt wird über den {H}Launcher{/H}: gegen die KI, mit Freunden oder auf Community-Servern.\n" +
                "• Controller-Unterstützung, fünf KI-Schwierigkeitsgrade, eigene Sticker, Avatare und Szenarien und mehr.\n\n" +
                "Revival enthält keine Dateien von Konami: Du brauchst CRIMESIGHT auf Steam.",
            "Wähle einen der {H}vier Modi{/H} und klicke auf {H}„Spielen“{/H}: Der Launcher öffnet das Spiel bereits verbunden.\n\n" +
                "• Die Sitzung endet, wenn du das Spiel schließt oder auf {H}„Sitzung beenden“{/H} klickst.\n" +
                "• Eine {H}Glocke{/H} oben zeigt eine neue Version an: Klicke darauf, um zu aktualisieren.\n" +
                "• Deine Spiele, Siege und Punkte werden auf deinem PC gespeichert.",
            "{PAGE}Jede Taste, die du benutzen kannst, zeigt daneben auf dem Bildschirm ihr Symbol.\n\n" +
                "• {H}Menüs{/H}: {START} bestätigt, {B} geht zurück oder schließt.\n\n" +
                "• {H}Raum{/H}:\n" +
                "<indent=4.0em>{Y} wählt einen Spieler.\n<size=40%>\n</size>" +
                "{DLEFT} wirft ihn raus (bei einer KI: ändert die Schwierigkeit).\n<size=40%>\n</size>" +
                "{DRIGHT} fügt Spieler hinzu.\n<size=40%>\n</size>" +
                "{DDOWN} entfernt leere Plätze.</indent>\n\n" +
                "• {H}Einstellungen und Profil{/H}: {LB} und {RB} wechseln den Reiter; {Y} ändert den Avatar.\n\n" +
                "• {H}Spiel{/H}: {B} überspringt Dialoge.\n\n" +
                "• {H}Tempo{/H}: Drücke {LS} (linker Stick) für das Cursortempo oder {RS} (rechter Stick) für das Kameratempo: langsam, mittel oder schnell (der Controller vibriert 1-, 2- oder 3-mal).\n\n" +
                "Funktioniert mit Xbox-, PlayStation-, Switch- und Steam-Deck-Controllern über Steam Input. Die Tastensymbole passen zu deinem Controller.",
            "Klicke im Raum bei einer KI auf {H}„Rauswerfen“{/H}, um ihre Schwierigkeit zu wählen, sie auf {H}alle KIs{/H} anzuwenden oder {H}den Platz freizugeben{/H}.\n\n" +
                "• {H}Leicht{/H}: macht Fehler; ideal zum Lernen.\n" +
                "• {H}Normal{/H}: spielt mit Verstand, ohne zu übertreiben.\n" +
                "• {H}Schwer{/H}: auf Moriartys Seite greift sie nur an, wenn es sicher ist; auf Sherlocks Seite lässt sie nie eine Figur allein.\n" +
                "• {H}Experte{/H}: denkt mehr nach, ohne zu schummeln; sieht deine Befehle voraus und nutzt Köder.\n" +
                "• {H}Albtraum{/H}: wie Experte, lernt aber aus deinen bisherigen Spielen auf diesem Server (braucht mindestens 3 deiner Spiele in dieser Rolle).\n\n" +
                "Je schwerer die KI, desto mehr Punkte gibt ein Sieg: von 200 (Leicht) bis 1200 (Albtraum).",
            "Wenn du Irene spielst und Moriarty von der KI gesteuert wird, gibst du ihm mit deinen Stickern Befehle:\n\n" +
                "{ST_IRENE}  Setze den Sticker {H}„Das ist der Schurke!“{/H} auf eine Figur und dann den Ping {H}„Bewegen“{/H} auf den Boden, wohin sie gehen soll: Moriarty bewegt sie in dieser Runde und antwortet „Verstanden“. {H}Bis zu zwei Figuren pro Runde{/H}.\n\n" +
                "• {H}Zum Töten{/H}: Setze den Sticker auf den Schurken und {H}„Bewegen“{/H} auf das Feld des Ziels. Ist er bewaffnet und kommt in dieser Runde hin, greift er an. Prüfe vorher, ob es Zeugen gibt.\n" +
                "• Setze {H}„Ich kontrolliere …“{/H} auf eine Figur: Moriarty rührt sie in dieser Runde nicht an.\n" +
                "• Ohne Befehle spielt Moriarty allein und greift unbemerkt an.\n\n" +
                "Dein KI-Partner spielt auf Schwer (oder Experte, wenn deine Gegner auf Experte oder Albtraum sind).",
            "Wenn du Watson spielst und Sherlock von der KI gesteuert wird, lenkst du ihn mit deinen Stickern:\n\n" +
                "{ST_SUS}  Setze {H}„Ich glaube, dass diese Figur der Schurke ist.“{/H} auf eine Figur (oder den Ping {H}„Gefahr“{/H}): Sherlock bringt Runde für Runde alle in ihrem Zimmer von ihr weg und beschuldigt sie am Ende. Er antwortet „Verstanden“.\n\n" +
                "{ST_NOSUS}  Setze {H}„Ich glaube nicht, dass diese Figur der Schurke ist.“{/H} auf dieselbe Figur: Sherlock verdächtigt sie nicht mehr.\n\n" +
                "Dein KI-Partner spielt auf Schwer (oder Experte, wenn deine Gegner auf Experte oder Albtraum sind).",
            "Um in der Befehlsphase aufzugeben, öffne das Menü {H}„Systemeinstellungen“{/H} und wähle {H}„Aufgeben“{/H}. Das geht mit jeder Rolle ab der ersten Runde und zählt als Niederlage.\n\n" +
                "• {H}Mit einer anderen Person im Team{/H}: Sie wird zuerst gefragt und hat 20 Sekunden für die Antwort. Sagt sie Nein oder antwortet nicht, geht das Spiel weiter.\n" +
                "• {H}Wenn du das Spiel verlässt{/H}: Du bekommst die Niederlage, und wenn noch andere Personen spielen, übernimmt eine KI bis zum Ende deinen Platz. Ist sonst niemand mehr da, zählt es als Aufgeben.\n\n" +
                "Schließt der Host das Spiel, wird der Sieg der Gäste trotzdem auf ihrem PC gespeichert (wenn sie online sind).",
            "Im Raum sind bei {H}„Spieleinstellungen bearbeiten“{/H} zwei Einstellungen anders als im Original:\n\n" +
                "• {H}Max. Runden{/H}: Das Original hat sie versteckt; jetzt wird sie angezeigt, 1 bis 99 (Standard: 10). Praktisch für große Karten und eigene Szenarien.\n" +
                "• {H}Zeitlimit{/H}: 60 bis 999 Sekunden in jedem Raum (öffentliche Räume gingen früher nur bis 180), um in Ruhe zu spielen.\n\n" +
                "Der Host legt sie fest, und sie gelten für alle.",
            "Öffne im Launcher {H}Mods{/H}, um jedes Bild in einen Sticker, einen Avatar oder einen Cursor zu verwandeln.\n\n" +
                "• {H}Sticker{/H}: Ein Bogen mit mehreren Stickern wird in einzelne Sticker ohne Hintergrund zerlegt. Zu jedem kannst du einen Text für das Spielprotokoll hinzufügen.\n" +
                "• {H}Avatare{/H}: Das Bild füllt den gewählten Rahmen ohne Lücken.\n" +
                "• {H}Cursor{/H}: Wähle, ob er mit der Spitze oder der Mitte klickt. Nur du siehst ihn.\n" +
                "• {H}In einem Raum{/H}: Alle bekommen die Mods des Hosts. Bringt ein Gast eigene mit, wählt der Host {H}„Herunterladen“{/H}, {H}„Immer annehmen“{/H} oder {H}„Nein, danke“{/H}.\n\n" +
                "Mods ändern nie die Original-Sticker oder -Avatare des Spiels, auch nicht die kostenpflichtigen.",
            "Öffne im Launcher {H}Mods → „Szenario-Editor“{/H}, um die Zimmer eines Szenarios neu anzuordnen und es als neues zu speichern.\n\n" +
                "• Verschiebe, drehe, entferne oder wiederhole Zimmer und wähle Türen, Hundefenster, Gas und Startfelder.\n" +
                "• Klicke auf {H}„Schnelltest“{/H}, um es ohne Speichern im {H}„Testszenario (CSR)“{/H} auszuprobieren.\n" +
                "• Gespeicherte Szenarien erscheinen in der Szenarioliste des Raums, und alle im Raum bekommen vor dem Start die Szenarien des Hosts.\n\n" +
                "Alle Spieler im Raum müssen im Launcher {H}Mods → „Hot Reload“{/H} einschalten.",
        };

        static readonly string[] PadDe =
        {
            "Rauszoomen", "Drehen · Reiter", "Protokoll", "Einstellungen",
            "Nächste Figur", "Vorherige Figur", "Plätze entfernen", "Cursor",
            "Reinzoomen", "Drehen · Reiter", "Rundenende · OK", "Verdächtige",
            "Sticker", "Abbrechen · Zurück", "Klick", "Kamera",
        };

        static readonly string[] TitlesPt =
        {
            "O que é o Revival?",
            "Inicializador",
            "Controle",
            "Dificuldade da IA",
            "Irene: dar ordens a Moriarty",
            "Watson: guiar Sherlock",
            "Desistir e sair de uma partida",
            "Configurações da sala",
            "Mods: emojis, avatares e cursor",
            "Cenários próprios",
        };

        static readonly string[] PagesPt =
        {
            "O {H}CRIMESIGHT Revival{/H} traz de volta o jogo on-line com servidores da comunidade e adiciona novos recursos. Este guia explica como usá-los.\n\n" +
                "• Você joga pelo {H}inicializador{/H}: contra a IA, com amigos ou em servidores da comunidade.\n" +
                "• Há suporte a controle, cinco dificuldades de IA, seus próprios emojis, avatares e cenários, e mais.\n\n" +
                "O Revival não inclui arquivos da Konami: você precisa ter CRIMESIGHT na Steam.",
            "Escolha um dos {H}quatro modos{/H} e clique em {H}\"Jogar\"{/H}: o inicializador abre o jogo já conectado.\n\n" +
                "• A sessão termina quando você fecha o jogo ou clica em {H}\"Encerrar sessão\"{/H}.\n" +
                "• Um {H}sino{/H} no topo avisa que há uma nova versão: clique nele para atualizar.\n" +
                "• Suas partidas, vitórias e pontos ficam salvos no seu PC.",
            "{PAGE}Cada botão que você pode usar mostra seu ícone ao lado, na tela.\n\n" +
                "• {H}Menus{/H}: {START} confirma e {B} volta ou fecha.\n\n" +
                "• {H}Sala{/H}:\n" +
                "<indent=3.3em>{Y} escolhe um jogador.\n<size=40%>\n</size>" +
                "{DLEFT} o expulsa (em uma IA, muda a dificuldade).\n<size=40%>\n</size>" +
                "{DRIGHT} adiciona jogadores.\n<size=40%>\n</size>" +
                "{DDOWN} remove as vagas vazias.</indent>\n\n" +
                "• {H}Configurações e perfil{/H}: {LB} e {RB} trocam de aba; {Y} muda o avatar.\n\n" +
                "• {H}Partida{/H}: {B} pula os diálogos.\n\n" +
                "• {H}Velocidade{/H}: aperte {LS} (analógico esquerdo) para mudar a velocidade do cursor, ou {RS} (analógico direito) para a da câmera: lenta, média ou rápida (o controle vibra 1, 2 ou 3 vezes).\n\n" +
                "Funciona com controles de Xbox, PlayStation, Switch e Steam Deck pelo Steam Input. Os ícones dos botões correspondem aos do seu controle.",
            "Na sala, clique em {H}\"Expulsar\"{/H} em uma IA para escolher a dificuldade, aplicá-la a {H}todas as IAs{/H} ou {H}liberar a vaga{/H} para outro jogador.\n\n" +
                "• {H}Fácil{/H}: comete erros; ideal para aprender.\n" +
                "• {H}Normal{/H}: joga com bom senso, sem exageros.\n" +
                "• {H}Difícil{/H}: do lado de Moriarty, só ataca quando é seguro; do lado de Sherlock, nunca deixa um personagem sozinho.\n" +
                "• {H}Especialista{/H}: pensa mais, sem trapacear; prevê suas ordens e usa iscas.\n" +
                "• {H}Pesadelo{/H}: como Especialista, mas aprende com suas partidas anteriores naquele servidor (precisa de pelo menos 3 partidas suas naquele papel).\n\n" +
                "Quanto mais difícil, mais pontos por vitória: de 200 (Fácil) a 1200 (Pesadelo).",
            "Se você joga com Irene e Moriarty é controlado pela IA, você dá ordens a ele com seus emojis:\n\n" +
                "{ST_IRENE}  Coloque o emoji {H}\"Aqui está o assassino!\"{/H} em um personagem e depois a marca {H}\"Mover\"{/H} no chão, onde quer que ele vá: Moriarty o move nesta rodada e responde \"Entendido\". {H}Até dois personagens por rodada{/H}.\n\n" +
                "• {H}Para matar{/H}: coloque o emoji no assassino e {H}\"Mover\"{/H} no espaço do alvo. Se ele estiver armado e chegar lá nesta rodada, ataca. Antes, verifique se não há testemunhas.\n" +
                "• Coloque {H}\"Vou controlar…\"{/H} em um personagem: Moriarty não mexe nele nesta rodada.\n" +
                "• Sem ordens, Moriarty joga sozinho e ataca sem ser visto.\n\n" +
                "Seu parceiro IA joga no Difícil (ou no Especialista se os adversários estiverem no Especialista ou Pesadelo).",
            "Se você joga com Watson e Sherlock é controlado pela IA, você o guia com seus emojis:\n\n" +
                "{ST_SUS}  Coloque {H}\"Suspeito que seja o assassino.\"{/H} em um personagem (ou a marca {H}\"Perigo\"{/H}): rodada após rodada, Sherlock afasta dele quem estiver no mesmo cômodo e, no final, o acusa. Ele responde \"Entendido\".\n\n" +
                "{ST_NOSUS}  Coloque {H}\"Não acho que seja o assassino.\"{/H} no mesmo personagem: Sherlock deixa de suspeitar dele.\n\n" +
                "Seu parceiro IA joga no Difícil (ou no Especialista se os adversários estiverem no Especialista ou Pesadelo).",
            "Para desistir durante a fase de comando, abra o menu {H}\"Configurações do sistema\"{/H} e escolha {H}\"Desistir\"{/H}. Vale para qualquer papel, desde a primeira rodada, e conta como derrota.\n\n" +
                "• {H}Com outra pessoa na sua equipe{/H}: ela é consultada primeiro e tem 20 segundos para responder. Se disser não ou não responder, a partida continua.\n" +
                "• {H}Se você sair da partida{/H}: a derrota fica com você e, se ainda houver outras pessoas, uma IA assume seu lugar até o final. Se não sobrar mais ninguém, conta como desistência.\n\n" +
                "Se o anfitrião fechar o jogo, a vitória dos convidados é registrada mesmo assim no PC deles (se estiverem on-line).",
            "Na sala, {H}\"Editar configurações do jogo\"{/H} muda duas opções em relação ao original:\n\n" +
                "• {H}Máximo de rodadas{/H}: o original a escondia; agora ela aparece, de 1 a 99 (10 por padrão). Útil em mapas grandes e cenários próprios.\n" +
                "• {H}Limite de tempo{/H}: de 60 a 999 segundos em qualquer sala (nas salas públicas ia só até 180), para jogar com calma.\n\n" +
                "O anfitrião define as duas, e elas valem para todos.",
            "No inicializador, abra {H}Mods{/H} para transformar qualquer imagem em emoji, avatar ou cursor.\n\n" +
                "• {H}Emojis{/H}: uma folha com vários emojis é separada em emojis avulsos, sem fundo. Você pode adicionar a cada um deles um texto para o registro da partida.\n" +
                "• {H}Avatares{/H}: a imagem preenche a moldura escolhida, sem espaços vazios.\n" +
                "• {H}Cursor{/H}: escolha se ele clica com a ponta ou com o centro. Só você o vê.\n" +
                "• {H}Em uma sala{/H}: todos recebem os mods do anfitrião. Se um convidado trouxer os seus, o anfitrião escolhe {H}\"Baixar\"{/H}, {H}\"Aceitar sempre\"{/H} ou {H}\"Não, obrigado\"{/H}.\n\n" +
                "Os mods nunca alteram os emojis nem os avatares originais do jogo, nem mesmo os pagos.",
            "No inicializador, abra {H}Mods → \"Criador de cenários\"{/H} para reorganizar os cômodos de um cenário e salvá-lo como um novo.\n\n" +
                "• Mova, gire, remova ou repita cômodos, e escolha portas, janelas dos cães, gás e casas de partida.\n" +
                "• Clique em {H}\"Teste rápido\"{/H} para testá-lo no {H}\"Cenário de testes (CSR)\"{/H} sem salvar.\n" +
                "• Os cenários salvos aparecem na lista de cenários da sala, e todos na sala recebem os do anfitrião antes de começar.\n\n" +
                "Todos os jogadores da sala devem ativar {H}Mods → \"Recarga instantânea\"{/H} no inicializador.",
        };

        static readonly string[] PadPt =
        {
            "Afastar", "Girar · Aba", "Registro", "Configurações",
            "Próximo personagem", "Personagem anterior", "Remover vagas", "Cursor",
            "Aproximar", "Girar · Aba", "Fim da rodada · OK", "Suspeitos",
            "Emojis", "Cancelar · Voltar", "Clique", "Câmera",
        };

        static readonly string[] TitlesRu =
        {
            "Что такое Revival?",
            "Лаунчер",
            "Геймпад",
            "Сложность ИИ",
            "Irene: приказы для Moriarty",
            "Watson: подсказки для Sherlock",
            "Сдаться и выйти из партии",
            "Настройки комнаты",
            "Моды: шаблоны, аватары, курсор",
            "Свои сценарии",
        };

        static readonly string[] PagesRu =
        {
            "{H}CRIMESIGHT Revival{/H} возвращает онлайн-игру на серверах сообщества и добавляет новые функции. Это руководство объясняет, как ими пользоваться.\n\n" +
                "• Играют через {H}лаунчер{/H}: против ИИ, с друзьями или на серверах сообщества.\n" +
                "• Поддержка геймпада, пять уровней сложности ИИ, свои шаблоны, аватары и сценарии и многое другое.\n\n" +
                "Revival не содержит файлов Konami: вам нужна своя копия CRIMESIGHT в Steam.",
            "Выберите один из {H}четырех режимов{/H} и нажмите {H}«Играть»{/H}: лаунчер откроет игру, уже подключенную к серверу.\n\n" +
                "• Сеанс заканчивается, когда вы закрываете игру или нажимаете {H}«Завершить сеанс»{/H}.\n" +
                "• {H}Колокольчик{/H} вверху сообщает о новой версии: нажмите его, чтобы обновиться.\n" +
                "• Ваши партии, победы и очки хранятся на вашем ПК.",
            "{PAGE}Рядом с каждой кнопкой, которую можно нажать, на экране видна ее иконка.\n\n" +
                "• {H}Меню{/H}: {START} подтверждает, {B} возвращает назад или закрывает.\n\n" +
                "• {H}Комната{/H}:\n" +
                "<indent=5.6em>{Y} выбирает игрока.\n<size=40%>\n</size>" +
                "{DLEFT} выгоняет его (у ИИ — меняет сложность).\n<size=40%>\n</size>" +
                "{DRIGHT} добавляет игроков.\n<size=40%>\n</size>" +
                "{DDOWN} убирает пустые места.</indent>\n\n" +
                "• {H}Настройки и профиль{/H}: {LB} и {RB} переключают вкладки; {Y} меняет аватар.\n\n" +
                "• {H}Партия{/H}: {B} пропускает диалоги.\n\n" +
                "• {H}Скорость{/H}: нажмите {LS} (левый стик), чтобы сменить скорость курсора, или {RS} (правый стик) — скорость камеры: медленно, средне или быстро (геймпад вибрирует 1, 2 или 3 раза).\n\n" +
                "Работает с геймпадами Xbox, PlayStation, Switch и Steam Deck через Steam Input. Иконки кнопок совпадают с вашим геймпадом.",
            "В комнате нажмите {H}«Выгнать»{/H} у ИИ, чтобы выбрать его сложность, применить ее ко {H}всем ИИ{/H} или {H}освободить место{/H} для другого игрока.\n\n" +
                "• {H}Легко{/H}: ошибается; подходит для обучения.\n" +
                "• {H}Нормально{/H}: играет разумно, без крайностей.\n" +
                "• {H}Сложно{/H}: за Moriarty нападает, только когда это безопасно; за Sherlock никогда не оставляет фигуранта одного.\n" +
                "• {H}Эксперт{/H}: думает дольше, без жульничества; предугадывает ваши приказы и использует приманки.\n" +
                "• {H}Кошмар{/H}: как Эксперт, но учится на ваших прошлых партиях на этом сервере (нужно минимум 3 ваши партии в этой роли).\n\n" +
                "Чем сложнее ИИ, тем больше очков за победу: от 200 (Легко) до 1200 (Кошмар).",
            "Если вы играете за Irene, а Moriarty управляет ИИ, вы отдаете ему приказы шаблонами:\n\n" +
                "{ST_IRENE}  Поставьте шаблон {H}«вот он, злодей!»{/H} на фигуранта, а затем сигнал {H}«Перемещение»{/H} на пол, куда он должен пойти: Moriarty передвинет его в этот ход и ответит «Ясно». Так можно сделать {H}не более чем с двумя фигурантами за ход{/H}.\n\n" +
                "• {H}Чтобы убить{/H}: поставьте шаблон на убийцу и {H}«Перемещение»{/H} на клетку жертвы. Если он вооружен и дойдет туда в этот ход, он нападет. Сначала проверьте, нет ли свидетелей.\n" +
                "• Поставьте {H}«Я отдам приказ…»{/H} на фигуранта: Moriarty не тронет его в этот ход.\n" +
                "• Без приказов Moriarty играет сам и нападает, когда его никто не видит.\n\n" +
                "Ваш напарник-ИИ играет на уровне Сложно (или Эксперт, если соперники на уровне Эксперт или Кошмар).",
            "Если вы играете за Watson, а Sherlock управляет ИИ, вы направляете его шаблонами:\n\n" +
                "{ST_SUS}  Поставьте {H}«Я подозреваю, что этот фигурант — убийца.»{/H} на фигуранта (или сигнал {H}«Опасность»{/H}): ход за ходом Sherlock уводит от него всех, кто с ним в одной комнате, а в конце обвиняет его. Он отвечает «Ясно».\n\n" +
                "{ST_NOSUS}  Поставьте {H}«Я не думаю, что этот фигурант — убийца.»{/H} на того же фигуранта: Sherlock перестанет его подозревать.\n\n" +
                "Ваш напарник-ИИ играет на уровне Сложно (или Эксперт, если соперники на уровне Эксперт или Кошмар).",
            "Чтобы сдаться в фазе команд, откройте меню {H}«Системные настройки»{/H} и выберите {H}«Сдаться»{/H}. Это можно сделать в любой роли с первого хода, и это считается поражением.\n\n" +
                "• {H}Если в вашей команде есть другой человек{/H}: сначала спрашивают его, и у него 20 секунд на ответ. Если он откажется или не ответит, партия продолжится.\n" +
                "• {H}Если вы выйдете из партии{/H}: вам засчитают поражение, и если остались другие люди, ваше место до конца займет ИИ. Если больше никого нет, это то же самое, что сдаться.\n\n" +
                "Если хост закроет игру, победа гостей все равно сохранится на их ПК (если они в сети).",
            "В комнате в окне {H}«Изменить настройки игры»{/H} две настройки работают иначе, чем в оригинале:\n\n" +
                "• {H}Макс. ходов{/H}: в оригинале эта настройка была скрыта; теперь она видна, от 1 до 99 (по умолчанию 10). Удобно для больших карт и своих сценариев.\n" +
                "• {H}Лимит времени{/H}: от 60 до 999 секунд в любой комнате (в публичных раньше было максимум 180), чтобы играть без спешки.\n\n" +
                "Их выбирает хост, и они действуют для всех.",
            "В лаунчере откройте {H}Моды{/H}, чтобы превратить любое изображение в шаблон, аватар или курсор.\n\n" +
                "• {H}Шаблоны{/H}: лист с несколькими шаблонами делится на отдельные шаблоны без фона. К каждому можно добавить текст для журнала партии.\n" +
                "• {H}Аватары{/H}: изображение заполняет выбранную рамку без пустых мест.\n" +
                "• {H}Курсор{/H}: выберите, чем он нажимает — кончиком или центром. Его видите только вы.\n" +
                "• {H}В комнате{/H}: все получают моды хоста. Если гость приносит свои, хост выбирает {H}«Скачать»{/H}, {H}«Всегда принимать»{/H} или {H}«Нет, спасибо»{/H}.\n\n" +
                "Моды никогда не меняют оригинальные шаблоны и аватары игры, в том числе платные.",
            "В лаунчере откройте {H}Моды → «Редактор сценариев»{/H}, чтобы переставить комнаты сценария и сохранить его как новый.\n\n" +
                "• Перемещайте, поворачивайте, убирайте или повторяйте комнаты, выбирайте двери, окна для собак, газ и стартовые клетки.\n" +
                "• Нажмите {H}«Быстрый тест»{/H}, чтобы без сохранения опробовать его: он появится как {H}«Тестовый сценарий (CSR)»{/H}.\n" +
                "• Сохраненные сценарии появляются в списке сценариев комнаты, и перед началом все в комнате получают сценарии хоста.\n\n" +
                "Все игроки в комнате должны включить в лаунчере {H}Моды → «Горячая перезагрузка»{/H}.",
        };

        static readonly string[] PadRu =
        {
            "Отдалить", "Поворот · Вкладка", "Журнал", "Настройки",
            "След. фигурант", "Пред. фигурант", "Убрать места", "Курсор",
            "Приблизить", "Поворот · Вкладка", "Конец хода · ОК", "Подозреваемые",
            "Шаблоны", "Отмена · Назад", "Клик", "Камера",
        };

        static readonly string[] TitlesKo =
        {
            "Revival이란?",
            "런처",
            "컨트롤러",
            "AI 난이도",
            "Irene: Moriarty에게 지시하기",
            "Watson: Sherlock 이끌기",
            "기권과 대전 나가기",
            "방 설정",
            "모드: 스탬프, 아바타, 커서",
            "나만의 스테이지",
        };

        static readonly string[] PagesKo =
        {
            "{H}CRIMESIGHT Revival{/H}은 커뮤니티 서버로 온라인 대전을 되살리고 새로운 기능을 더합니다. 이 가이드에서 사용법을 설명합니다.\n\n" +
                "• {H}런처{/H}에서 플레이합니다: AI와, 친구와, 또는 커뮤니티 서버에서.\n" +
                "• 컨트롤러 지원, 5단계 AI 난이도, 나만의 스탬프·아바타·스테이지 등이 있습니다.\n\n" +
                "Revival에는 Konami 파일이 포함되어 있지 않습니다: Steam에서 CRIMESIGHT를 보유해야 합니다.",
            "{H}네 가지 모드{/H} 중 하나를 고르고 {H}'플레이'{/H}를 누르면, 런처가 이미 연결된 상태로 게임을 엽니다.\n\n" +
                "• 게임을 닫거나 {H}'세션 종료'{/H}를 누르면 세션이 끝납니다.\n" +
                "• 위쪽의 {H}종{/H}은 새 버전을 알려 줍니다: 누르면 업데이트합니다.\n" +
                "• 대전 수, 승리, 포인트는 PC에 저장됩니다.",
            "{PAGE}화면에서 조작할 수 있는 곳에는 사용할 버튼의 아이콘이 표시됩니다.\n\n" +
                "• {H}메뉴{/H}: {START}로 결정, {B}로 뒤로 가기·닫기.\n\n" +
                "• {H}방{/H}:\n" +
                "<indent=2.4em>{Y}로 플레이어 선택.\n<size=40%>\n</size>" +
                "{DLEFT}로 추방(AI는 난이도 변경).\n<size=40%>\n</size>" +
                "{DRIGHT}로 플레이어 추가.\n<size=40%>\n</size>" +
                "{DDOWN}로 빈자리 제거.</indent>\n\n" +
                "• {H}설정과 프로필{/H}: {LB}와 {RB}로 탭 전환, {Y}로 아바타 변경.\n\n" +
                "• {H}대전{/H}: {B}로 대화 건너뛰기.\n\n" +
                "• {H}속도{/H}: {LS}(왼쪽 스틱)를 누르면 커서 속도, {RS}(오른쪽 스틱)를 누르면 카메라 속도가 바뀝니다: 느림, 보통, 빠름(컨트롤러가 1, 2, 3번 진동).\n\n" +
                "Steam 입력을 통해 Xbox, PlayStation, Switch, Steam Deck 컨트롤러를 지원합니다. 버튼 아이콘은 사용하는 컨트롤러에 맞게 표시됩니다.",
            "방에서 AI의 {H}'추방'{/H}을 누르면 난이도를 고르거나, {H}모든 AI{/H}에 적용하거나, {H}자리를 비워{/H} 다른 플레이어를 받을 수 있습니다.\n\n" +
                "• {H}쉬움{/H}: 실수를 합니다. 배우기에 좋습니다.\n" +
                "• {H}보통{/H}: 무리하지 않고 생각하며 플레이합니다.\n" +
                "• {H}어려움{/H}: Moriarty 쪽에서는 안전할 때만 공격하고, Sherlock 쪽에서는 캐릭터를 절대 혼자 두지 않습니다.\n" +
                "• {H}전문가{/H}: 속임수 없이 더 깊이 생각하며, 당신의 지시를 예측하고 미끼를 씁니다.\n" +
                "• {H}악몽{/H}: 전문가와 같지만, 그 서버에서 당신이 했던 대전에서 배웁니다(그 역할로 최소 3번 대전해야 함).\n\n" +
                "어려울수록 승리 시 포인트가 많습니다: 200(쉬움)부터 1200(악몽)까지.",
            "Irene으로 플레이하고 Moriarty를 AI가 조종할 때, 스탬프로 지시를 내릴 수 있습니다:\n\n" +
                "{ST_IRENE}  캐릭터에 {H}'킬러는 내가 맡겠어!'{/H} 스탬프를 놓고, 보내고 싶은 바닥에 {H}'이동'{/H} Ping을 놓으세요: Moriarty가 이번 턴에 그 캐릭터를 움직이고 '알겠습니다'라고 답합니다. {H}한 턴에 캐릭터 2명까지{/H} 가능합니다.\n\n" +
                "• {H}살해하려면{/H}: 킬러에게 스탬프를, 타깃이 있는 칸에 {H}'이동'{/H}을 놓으세요. 무기를 들고 있고 이번 턴에 도착할 수 있으면 공격합니다. 먼저 목격자가 없는지 확인하세요.\n" +
                "• 캐릭터에 {H}'~(을)를 제어합니다'{/H}를 놓으면, Moriarty는 이번 턴에 그 캐릭터를 건드리지 않습니다.\n" +
                "• 지시가 없으면 Moriarty는 혼자 플레이하며, 들키지 않을 때 공격합니다.\n\n" +
                "AI 파트너는 어려움으로 플레이합니다(상대가 전문가나 악몽이면 전문가).",
            "Watson으로 플레이하고 Sherlock을 AI가 조종할 때, 스탬프로 이끌 수 있습니다:\n\n" +
                "{ST_SUS}  캐릭터에 {H}'킬러로 의심하고 있습니다.'{/H}(또는 {H}'위험'{/H} Ping)를 놓으면, Sherlock이 매 턴 같은 방에 있는 사람들을 그 캐릭터에게서 떼어 놓고, 마지막에 그 캐릭터를 지목합니다. '알겠습니다'라고 답합니다.\n\n" +
                "{ST_NOSUS}  같은 캐릭터에 {H}'킬러가 아니라고 생각합니다.'{/H}를 놓으면 Sherlock이 의심을 멈춥니다.\n\n" +
                "AI 파트너는 어려움으로 플레이합니다(상대가 전문가나 악몽이면 전문가).",
            "지시 단계 중에 기권하려면 {H}'시스템 설정'{/H} 메뉴를 열고 {H}'기권'{/H}을 고르세요. 어떤 역할이든 첫 턴부터 할 수 있으며, 패배로 처리됩니다.\n\n" +
                "• {H}팀에 다른 사람이 있으면{/H}: 먼저 그 사람에게 묻고, 그 사람은 20초 안에 답해야 합니다. 거절하거나 답이 없으면 대전은 계속됩니다.\n" +
                "• {H}대전에서 나가면{/H}: 당신은 패배로 처리되고, 다른 사람이 남아 있으면 끝날 때까지 AI가 당신 자리를 맡습니다. 아무도 남지 않으면 기권으로 처리됩니다.\n\n" +
                "호스트가 게임을 닫아도 게스트의 승리는 각자의 PC에 기록됩니다(인터넷에 연결되어 있으면).",
            "방의 {H}'게임 설정 변경'{/H}에서는 설정 2개가 원작과 다릅니다:\n\n" +
                "• {H}최대 턴 수{/H}: 원작에서는 숨겨져 있었지만 이제 표시됩니다. 1~99(기본 10). 큰 맵과 나만의 스테이지에 유용합니다.\n" +
                "• {H}제한 시간{/H}: 어떤 방에서든 60~999초(예전에는 공개 방에서 180초까지). 여유롭게 플레이할 수 있습니다.\n\n" +
                "호스트가 정하며 모두에게 적용됩니다.",
            "런처에서 {H}모드{/H}를 열면 어떤 이미지든 스탬프, 아바타, 커서로 만들 수 있습니다.\n\n" +
                "• {H}스탬프{/H}: 여러 스탬프가 담긴 이미지는 배경 없이 하나씩 나뉩니다. 각각에 대전 기록용 텍스트를 붙일 수 있습니다.\n" +
                "• {H}아바타{/H}: 이미지가 고른 틀을 빈틈없이 채웁니다.\n" +
                "• {H}커서{/H}: 끝으로 클릭할지 가운데로 클릭할지 고릅니다. 나에게만 보입니다.\n" +
                "• {H}방에서는{/H}: 모두가 호스트의 모드를 받습니다. 게스트가 자기 모드를 가져오면 호스트가 {H}'내려받기'{/H}, {H}'항상 수락'{/H}, {H}'괜찮습니다'{/H} 중에서 고릅니다.\n\n" +
                "모드는 게임의 원래 스탬프나 아바타(유료 포함)를 절대 바꾸지 않습니다.",
            "런처에서 {H}모드 → '스테이지 제작기'{/H}를 열면 스테이지의 방 배치를 바꿔 새 스테이지로 저장할 수 있습니다.\n\n" +
                "• 방을 옮기고, 돌리고, 지우고, 반복할 수 있으며, 문, 들개 창문, 가스, 시작 칸도 고를 수 있습니다.\n" +
                "• {H}'빠른 테스트'{/H}를 누르면 저장하지 않고 {H}'테스트 스테이지 (CSR)'{/H}에서 시험해 볼 수 있습니다.\n" +
                "• 저장한 스테이지는 방의 스테이지 목록에 나오며, 시작 전에 방의 모두가 호스트의 스테이지를 받습니다.\n\n" +
                "방의 모든 플레이어가 런처에서 {H}모드 → '실시간 반영'{/H}을 켜야 합니다.",
        };

        static readonly string[] PadKo =
        {
            "축소", "회전 · 탭", "대화 내역", "설정",
            "다음 캐릭터", "이전 캐릭터", "빈자리 제거", "커서",
            "확대", "회전 · 탭", "턴 종료 · 결정", "용의자",
            "스탬프", "취소 · 뒤로", "클릭", "카메라",
        };

        static readonly string[] TitlesZhCn =
        {
            "什么是Revival？",
            "启动器",
            "手柄",
            "AI难度",
            "Irene：向Moriarty下令",
            "Watson：引导Sherlock",
            "认输与退出对局",
            "房间设置",
            "模组：表情、头像与光标",
            "自制场景",
        };

        static readonly string[] PagesZhCn =
        {
            "{H}CRIMESIGHT Revival{/H}通过社区服务器恢复在线对战，并加入新功能。本指南介绍它们的用法。\n\n" +
                "• 通过{H}启动器{/H}游玩：与AI对战、与好友一起，或在社区服务器上。\n" +
                "• 支持手柄、五种AI难度、自制表情、头像和场景等。\n\n" +
                "Revival不含任何Konami文件：你需要在Steam上拥有CRIMESIGHT。",
            "从{H}四种模式{/H}中选择一种，点击{H}“开始游戏”{/H}：启动器会打开已连接好的游戏。\n\n" +
                "• 关闭游戏或点击{H}“结束会话”{/H}即结束会话。\n" +
                "• 顶部出现{H}铃铛{/H}表示有新版本：点击即可更新。\n" +
                "• 你的对局数、胜场和积分保存在你的电脑上。",
            "{PAGE}屏幕上可操作的地方会显示对应按钮的图标。\n\n" +
                "• {H}菜单{/H}：{START}确认，{B}返回或关闭。\n\n" +
                "• {H}房间{/H}：\n" +
                "<indent=4.4em>{Y}选择玩家。\n<size=40%>\n</size>" +
                "{DLEFT}踢出（对AI则更改难度）。\n<size=40%>\n</size>" +
                "{DRIGHT}添加玩家。\n<size=40%>\n</size>" +
                "{DDOWN}移除空位。</indent>\n\n" +
                "• {H}设置与个人资料{/H}：{LB}和{RB}切换标签页；{Y}更换头像。\n\n" +
                "• {H}对局{/H}：{B}跳过对话。\n\n" +
                "• {H}速度{/H}：按下{LS}（左摇杆）更改光标速度，按下{RS}（右摇杆）更改视角速度：慢、中、快（手柄振动1、2或3次）。\n\n" +
                "通过Steam输入支持Xbox、PlayStation、Switch和Steam Deck手柄。按钮图标与你的手柄一致。",
            "在房间中对AI点击{H}“踢出房间”{/H}，可以选择其难度、应用到{H}所有 AI{/H}，或{H}空出位置{/H}给其他玩家。\n\n" +
                "• {H}简单{/H}：会犯错，适合学习。\n" +
                "• {H}普通{/H}：认真思考，但不过分。\n" +
                "• {H}困难{/H}：在Moriarty一方时只在安全时出手；在Sherlock一方时绝不让任何角色落单。\n" +
                "• {H}专家{/H}：想得更多，绝不作弊；会预判你的指令并使用诱饵。\n" +
                "• {H}噩梦{/H}：与专家相同，但会从你在该服务器上的过往对局中学习（需要你以该身份至少玩过3局）。\n\n" +
                "难度越高，获胜积分越多：从200（简单）到1200（噩梦）。",
            "如果你扮演Irene，而Moriarty由AI控制，你可以用表情向他下令：\n\n" +
                "{ST_IRENE}  把{H}“我来控制杀手！”{/H}表情放在一个角色上，再把{H}“移动”{/H}Ping放在希望其前往的地面上：Moriarty会在本回合移动该角色，并回答“明白”。{H}每回合最多两个角色{/H}。\n\n" +
                "• {H}刺杀{/H}：把表情放在杀手身上，并把{H}“移动”{/H}放在刺杀目标所在的格子上。若杀手持有武器且本回合能到达，就会出手。请先确认没有目击者。\n" +
                "• 把{H}“我要控制……”{/H}放在角色上：Moriarty本回合不会动该角色。\n" +
                "• 若你不下令，Moriarty会自行行动，在不被看到时出手。\n\n" +
                "你的AI搭档以困难难度游玩（若对手为专家或噩梦，则为专家）。",
            "如果你扮演Watson，而Sherlock由AI控制，你可以用表情引导他：\n\n" +
                "{ST_SUS}  把{H}“怀疑是杀手。”{/H}（或{H}“危险”{/H}Ping）放在一个角色上：Sherlock会每回合把同一房间里的人从该角色身边带走，最后指认该角色。他会回答“明白”。\n\n" +
                "{ST_NOSUS}  把{H}“声称不是杀手。”{/H}放在同一角色上：Sherlock就不再怀疑该角色。\n\n" +
                "你的AI搭档以困难难度游玩（若对手为专家或噩梦，则为专家）。",
            "要在指令阶段认输，请打开{H}“系统设置”{/H}菜单并选择{H}“认输”{/H}。任何身份从第一回合起都可以认输，计为失败。\n\n" +
                "• {H}队伍中有其他真人玩家时{/H}：会先询问对方，对方有20秒回答。若对方拒绝或未回答，对局继续。\n" +
                "• {H}如果你退出对局{/H}：你会被记为失败；若仍有其他真人玩家，AI会接替你的位置直到结束。若没有其他人，则视为认输。\n\n" +
                "如果房主关闭游戏，客人的胜利仍会记录在他们的电脑上（需联网）。",
            "在房间中，{H}“变更游戏设置”{/H}有两个设置与原版不同：\n\n" +
                "• {H}最大回合数{/H}：原版中被隐藏，现在会显示，可设为1到99（默认10）。适合大地图和自制场景。\n" +
                "• {H}限制时间{/H}：任何房间都可设为60到999秒（原本公开房间最多只能设到180秒），慢慢玩。\n\n" +
                "由房主设定，对所有人生效。",
            "在启动器中打开{H}模组{/H}，可以把任何图片变成表情、头像或光标。\n\n" +
                "• {H}表情{/H}：包含多个表情的图片会被拆分成单独的表情并去除背景。可为每个表情添加用于对局记录的文字。\n" +
                "• {H}头像{/H}：图片会填满你选择的边框，不留空隙。\n" +
                "• {H}光标{/H}：选择用尖端还是中心点击。只有你能看到。\n" +
                "• {H}在房间中{/H}：所有人都会收到房主的模组。若客人带了自己的模组，房主可选择{H}“下载”{/H}、{H}“总是接受”{/H}或{H}“不用了”{/H}。\n\n" +
                "模组绝不会更改游戏原有的表情和头像，包括付费的。",
            "在启动器中打开{H}模组 → “场景编辑器”{/H}，可以重新排列场景中的房间，并另存为新场景。\n\n" +
                "• 可移动、旋转、删除或重复房间，并选择门、野狗窗、燃气和起始格。\n" +
                "• 点击{H}“快速测试”{/H}，无需保存即可在{H}“测试场景 (CSR)”{/H}中试玩。\n" +
                "• 保存的场景会出现在房间的场景列表中，开始前房间里所有人都会收到房主的场景。\n\n" +
                "房间里所有玩家都必须在启动器中开启{H}模组 → “热重载”{/H}。",
        };

        static readonly string[] PadZhCn =
        {
            "缩小", "旋转 · 标签页", "记录", "设置",
            "下一个角色", "上一个角色", "移除空位", "光标",
            "放大", "旋转 · 标签页", "结束回合 · 确认", "嫌疑人",
            "表情", "取消 · 返回", "点击", "视角",
        };

        static readonly string[] TitlesZhTw =
        {
            "什麼是Revival？",
            "啟動器",
            "控制器",
            "AI難度",
            "Irene：對Moriarty下指示",
            "Watson：引導Sherlock",
            "投降與退出對戰",
            "房間設定",
            "模組：貼圖、頭像與游標",
            "自製場景",
        };

        static readonly string[] PagesZhTw =
        {
            "{H}CRIMESIGHT Revival{/H}透過社群伺服器讓線上對戰復活，並加入新功能。本指南說明這些功能的用法。\n\n" +
                "• 從{H}啟動器{/H}遊玩：與AI對戰、和好友一起，或在社群伺服器上。\n" +
                "• 支援控制器、五種AI難度、自製貼圖、頭像與場景等。\n\n" +
                "Revival不含任何Konami檔案：你需要在Steam上擁有CRIMESIGHT。",
            "從{H}四種模式{/H}中選一種，點擊{H}「開始遊戲」{/H}：啟動器會開啟已連線的遊戲。\n\n" +
                "• 關閉遊戲或點擊{H}「結束工作階段」{/H}即結束工作階段。\n" +
                "• 上方出現{H}鈴鐺{/H}表示有新版本：點擊即可更新。\n" +
                "• 你的對戰數、勝場與點數都儲存在你的電腦上。",
            "{PAGE}畫面上可操作的地方會顯示對應按鈕的圖示。\n\n" +
                "• {H}選單{/H}：{START}確認，{B}返回或關閉。\n\n" +
                "• {H}房間{/H}：\n" +
                "<indent=4.4em>{Y}選擇玩家。\n<size=40%>\n</size>" +
                "{DLEFT}踢出（對AI則變更難度）。\n<size=40%>\n</size>" +
                "{DRIGHT}新增玩家。\n<size=40%>\n</size>" +
                "{DDOWN}移除空位。</indent>\n\n" +
                "• {H}設定與個人檔案{/H}：{LB}和{RB}切換分頁；{Y}更換頭像。\n\n" +
                "• {H}對戰{/H}：{B}略過對話。\n\n" +
                "• {H}速度{/H}：按下{LS}（左搖桿）變更游標速度，按下{RS}（右搖桿）變更鏡頭速度：慢、中、快（控制器震動1、2或3次）。\n\n" +
                "透過Steam輸入支援Xbox、PlayStation、Switch與Steam Deck控制器。按鈕圖示會配合你的控制器。",
            "在房間中對AI點擊{H}「踢出」{/H}，可選擇其難度、套用到{H}所有 AI{/H}，或{H}空出位置{/H}給其他玩家。\n\n" +
                "• {H}簡單{/H}：會犯錯，適合學習。\n" +
                "• {H}普通{/H}：用心思考，但不過頭。\n" +
                "• {H}困難{/H}：在Moriarty這方時只在安全時出手；在Sherlock這方時絕不讓角色落單。\n" +
                "• {H}專家{/H}：想得更多，絕不作弊；會預判你的指示並使用誘餌。\n" +
                "• {H}噩夢{/H}：與專家相同，但會從你在該伺服器的過往對戰中學習（需要你以該角色對戰至少3次）。\n\n" +
                "難度越高，獲勝點數越多：從200（簡單）到1200（噩夢）。",
            "如果你扮演Irene，而Moriarty由AI操控，你可以用貼圖對他下指示：\n\n" +
                "{ST_IRENE}  把{H}「兇手交給我！」{/H}貼圖放在角色上，再把{H}「移動」{/H}Ping放在希望其前往的地面上：Moriarty會在本回合移動該角色，並回答「了解」。{H}每回合最多兩個角色{/H}。\n\n" +
                "• {H}殺害{/H}：把貼圖放在兇手身上，並把{H}「移動」{/H}放在目標所在的格子。若兇手持有武器且本回合能抵達，就會出手。請先確認沒有目擊者。\n" +
                "• 把{H}「我要指揮……」{/H}放在角色上：Moriarty本回合不會動該角色。\n" +
                "• 若你不下指示，Moriarty會自行行動，在不被看見時出手。\n\n" +
                "你的AI夥伴以困難難度遊玩（若對手為專家或噩夢，則為專家）。",
            "如果你扮演Watson，而Sherlock由AI操控，你可以用貼圖引導他：\n\n" +
                "{ST_SUS}  把{H}「懷疑是兇手。」{/H}（或{H}「危險」{/H}Ping）放在角色上：Sherlock會每回合把同一房間的人從該角色身邊帶開，最後指認該角色。他會回答「了解」。\n\n" +
                "{ST_NOSUS}  把{H}「澄清不是兇手。」{/H}放在同一角色上：Sherlock便不再懷疑該角色。\n\n" +
                "你的AI夥伴以困難難度遊玩（若對手為專家或噩夢，則為專家）。",
            "要在指令階段投降，請開啟{H}「系統設定」{/H}選單並選擇{H}「投降」{/H}。任何角色從第一回合起都能投降，並記為敗北。\n\n" +
                "• {H}隊伍中有其他真人玩家時{/H}：會先詢問對方，對方有20秒可以回答。若對方拒絕或未回答，對戰繼續。\n" +
                "• {H}如果你退出對戰{/H}：你會記為敗北；若還有其他真人玩家，AI會接替你的位置直到結束。若沒有其他人，則視為投降。\n\n" +
                "如果房主關閉遊戲，客人的勝利仍會記錄在他們的電腦上（需連上網路）。",
            "在房間中，{H}「變更遊戲設定」{/H}有兩個設定與原版不同：\n\n" +
                "• {H}最多回合數{/H}：原版中被隱藏，現在會顯示，可設為1到99（預設10）。適合大地圖與自製場景。\n" +
                "• {H}限制時間{/H}：任何房間都能設為60到999秒（原本公開房間最多只能設到180秒），慢慢遊玩。\n\n" +
                "由房主設定，套用到所有人。",
            "在啟動器中開啟{H}模組{/H}，就能把任何圖片做成貼圖、頭像或游標。\n\n" +
                "• {H}貼圖{/H}：含有多張貼圖的圖片會被拆成單張貼圖並去除背景。可為每張貼圖加上用於對戰記錄的文字。\n" +
                "• {H}頭像{/H}：圖片會填滿你選擇的框，不留空隙。\n" +
                "• {H}游標{/H}：選擇用尖端還是中心點擊。只有你看得到。\n" +
                "• {H}在房間中{/H}：所有人都會收到房主的模組。若客人帶了自己的模組，房主可選擇{H}「下載」{/H}、{H}「總是接受」{/H}或{H}「不用了」{/H}。\n\n" +
                "模組絕不會更改遊戲原本的貼圖和頭像，包括付費的。",
            "在啟動器中開啟{H}模組 →「場景編輯器」{/H}，即可重新排列場景的房間並另存為新場景。\n\n" +
                "• 可移動、旋轉、移除或重複房間，並選擇門、野狗窗、瓦斯與起始格。\n" +
                "• 點擊{H}「快速測試」{/H}，不必儲存就能在{H}「測試場景 (CSR)」{/H}中試玩。\n" +
                "• 儲存的場景會出現在房間的場景列表中，開始前房間內所有人都會收到房主的場景。\n\n" +
                "房間內所有玩家都必須在啟動器中開啟{H}模組 →「熱重載」{/H}。",
        };

        static readonly string[] PadZhTw =
        {
            "縮小", "旋轉 · 分頁", "履歷", "設定",
            "下一個角色", "上一個角色", "移除空位", "游標",
            "放大", "旋轉 · 分頁", "結束回合 · 確認", "嫌疑人",
            "貼圖", "取消 · 返回", "點擊", "鏡頭",
        };

        static readonly string[][] TitlesAll = { TitlesJa, TitlesEn, TitlesFr, TitlesIt, TitlesDe, TitlesEs, TitlesPt, TitlesRu, TitlesKo, TitlesZhCn, TitlesZhTw };
        static readonly string[][] PagesAll = { PagesJa, PagesEn, PagesFr, PagesIt, PagesDe, PagesEs, PagesPt, PagesRu, PagesKo, PagesZhCn, PagesZhTw };
        static readonly string[][] PadAll = { PadJa, PadEn, PadFr, PadIt, PadDe, PadEs, PadPt, PadRu, PadKo, PadZhCn, PadZhTw };

        public static string[] PadLabels(int lang) => PadAll[L(lang)];

        /// <summary>La captura de la pagina, o null si no tiene.</summary>
        public static string Image(int t) => Images.TryGetValue(t, out var n) ? n : null;

        public static int Count => TitlesEs.Length;
        public static string TopicTitle(int t, int lang) => TitlesAll[L(lang)][t];
        public static string Page(int t, int lang) => PagesAll[L(lang)][t];
    }
}
