// CRIMESIGHT Revival - textos de la Guia Revival (ver CrimeSightRevivalGuide.cs).
//
// Una pagina por tema (las flechas de pagina del juego van con el dialogo de un personaje, que la guia no usa).
// En los textos:
//   {A} {B} {X} {Y} {LB} {RB} {LT} {RT} {LBRB} {LTRT} {START} {BACK} {LS} {RS} {DPAD}: icono del boton del
//   mando que se usa (Xbox, PlayStation o Switch); {ST_IRENE} {ST_SUS} {ST_NOSUS}: la imagen del sticker del juego
//   ("Aqui tienes a tu asesino", "Sospecho que es el asesino", "No creo que sea el asesino");
//   {H}...{/H}: resaltado en verde.
// Espanol para el juego en espanol; ingles para los demas idiomas.
// Algunas paginas llevan una captura arriba, de lado a lado, y el texto debajo (ver Images y tools/guide_images.py).
namespace CrimeSightRevival.Mods
{
    static class GuideText
    {
        public static string Title(int lang) => lang == 5 ? "Guía Revival" : "Revival Guide";

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
            "<size=85%><pos=7.5%>Alejar<pos=22.25%>Girar<pos=70.25%>Girar<pos=82.75%>Acercar</size>\n" +
                "<size=130%><pos=8%>{LT}<pos=22%>{LB}<pos=70%>{RB}<pos=84%>{RT}</size>\n" +
                "<size=85%><pos=36%>Registro<pos=51.25%>Fin turno<pos=71.75%>Sospechosos</size>\n" +
                "<size=130%><pos=38%>{BACK}<pos=54%>{START}<pos=76%>{Y}</size>\n" +
                "<size=85%><pos=7.5%>Cursor<pos=66%>Stickers<pos=81%>Clic derecho</size>\n" +
                "<size=130%><pos=8%>{LS}<pos=68%>{X}<pos=84%>{B}</size>\n" +
                "<size=85%><pos=20.75%>Flechas<pos=59.5%>Cámara<pos=77%>Clic</size>\n" +
                "<size=130%><pos=22%>{DPAD}<pos=60%>{RS}<pos=76%>{A}</size>\n\n\n" +
                "• Pulsa {LS} para cambiar la velocidad del cursor, o {RS} para la de la cámara: lenta, media o rápida (el mando vibra 1, 2 o 3 veces).\n" +
                "• Funciona con mandos de Xbox, PlayStation, Switch y Steam Deck a través de Steam Input. Los iconos de los botones se adaptan al tuyo.",
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
            "Para rendirte durante la fase de mando, abre el menú {H}«Ajustes del sistema»{/H} y elige {H}«Penalización»{/H}. Cuenta como derrota.\n\n" +
                "• {H}Contra la IA o en el entrenamiento{/H}: con cualquier papel, desde el primer turno.\n" +
                "• {H}Con otros jugadores{/H}: solo Moriarty, desde el turno 4 (como en el juego original).\n\n" +
                "Salir de una partida cuenta como rendirse: tu bando pierde y gana el otro. Si se va el anfitrión, la victoria de los invitados se guarda igualmente en su PC (si tienen internet).",
            "En la sala, {H}«Modificar ajustes del juego»{/H} tiene dos ajustes más que el original:\n\n" +
                "• {H}Máximo de turnos{/H}: de 1 a 99 (por defecto 10). Útil en mapas grandes y escenarios propios.\n" +
                "• {H}Tiempo por turno{/H}: de 60 a 999 segundos en cualquier sala, para jugar con calma.\n\n" +
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
            "<size=85%><pos=6%>Zoom out<pos=21.5%>Rotate<pos=69.5%>Rotate<pos=82.75%>Zoom in</size>\n" +
                "<size=130%><pos=8%>{LT}<pos=22%>{LB}<pos=70%>{RB}<pos=84%>{RT}</size>\n" +
                "<size=85%><pos=39.75%>Log<pos=52%>End turn<pos=74%>Suspects</size>\n" +
                "<size=130%><pos=38%>{BACK}<pos=54%>{START}<pos=76%>{Y}</size>\n" +
                "<size=85%><pos=7.5%>Cursor<pos=66.75%>Stamps<pos=81.5%>Right-click</size>\n" +
                "<size=130%><pos=8%>{LS}<pos=68%>{X}<pos=84%>{B}</size>\n" +
                "<size=85%><pos=21.5%>Arrows<pos=59.5%>Camera<pos=76.25%>Click</size>\n" +
                "<size=130%><pos=22%>{DPAD}<pos=60%>{RS}<pos=76%>{A}</size>\n\n\n" +
                "• Press {LS} to change the cursor speed, or {RS} to change the camera speed: slow, medium or fast (the controller vibrates 1, 2 or 3 times).\n" +
                "• It works with Xbox, PlayStation, Switch and Steam Deck controllers through Steam Input. The button icons match yours.",
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
            "To forfeit during the command phase, open the {H}\"System Settings\"{/H} menu and choose {H}\"Forfeit\"{/H}. It counts as a loss.\n\n" +
                "• {H}Against the AI or in training{/H}: any role, from the first turn.\n" +
                "• {H}With other players{/H}: only Moriarty, from turn 4 (as in the original game).\n\n" +
                "Leaving a match counts as forfeiting: your side loses and the other side wins. If the host leaves, the guests' win is still recorded on their PC (if they're online).",
            "In the room, {H}\"Edit Game Settings\"{/H} has two more options than the original:\n\n" +
                "• {H}Max. turns{/H}: from 1 to 99 (10 by default). Handy for big maps and custom scenarios.\n" +
                "• {H}Turn time{/H}: from 60 to 999 seconds in any room, to play at your own pace.\n\n" +
                "The host sets them, and they apply to everyone.",
            "In the launcher, open {H}Mods{/H} to turn any image into a stamp, an avatar or a cursor.\n\n" +
                "• {H}Stamps{/H}: a sheet of several stamps is split into separate stamps, with the background removed. You can add a caption to each one for the match log.\n" +
                "• {H}Avatars{/H}: the image fills the frame you choose, with no gaps.\n" +
                "• {H}Cursor{/H}: choose whether it clicks at the tip or the centre. Only you see it.\n" +
                "• {H}In a room{/H}: everyone gets the host's mods. If a guest brings their own, the host chooses {H}\"Download\"{/H}, {H}\"Always accept\"{/H} or {H}\"No thanks\"{/H}.\n\n" +
                "Mods never change the game's original stamps or avatars, including paid ones.",
            "In the launcher, open {H}Mods → \"Scenario creator\"{/H} to rearrange the rooms of a scenario and save it as a new one.\n\n" +
                "• Move, rotate, remove or repeat rooms, and choose doors, dog windows, gas and starting cells.\n" +
                "• Click {H}\"Quick test\"{/H} to try it in the {H}\"Test scenario (CSR)\"{/H} without saving it.\n" +
                "• Saved scenarios appear in the room's scenario list, and everyone in the room gets the host's scenarios before the match starts.\n\n" +
                "Every player in the room must turn on {H}Mods → \"Hot reload\"{/H} in the launcher.",
        };

        public static string Help(int lang) => lang == 5
            ? "Cómo funciona lo que añade Revival: lanzador, mando, IA, stickers y más."
            : "How everything Revival adds works: launcher, controller, AI, stamps and more.";

        // Tema -> captura (nombre en GuideImages) que sale encima del texto
        static readonly System.Collections.Generic.Dictionary<int, string> Images = new()
        {
            [1] = "launcher",         // El lanzador
        };

        /// <summary>La captura de la pagina, o null si no tiene.</summary>
        public static string Image(int t) => Images.TryGetValue(t, out var n) ? n : null;

        public static int Count => TitlesEs.Length;
        public static string TopicTitle(int t, int lang) => lang == 5 ? TitlesEs[t] : TitlesEn[t];
        public static string Page(int t, int lang) => lang == 5 ? PagesEs[t] : PagesEn[t];
    }
}
