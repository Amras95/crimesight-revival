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
            "Qué añade Revival",
            "El lanzador: modos de juego",
            "El lanzador: sesión y novedades",
            "Controles con mando",
            "Mando: velocidad y vibración",
            "Elegir la dificultad de la IA",
            "Las cinco dificultades",
            "Irene en solitario",
            "Irene: matar y más órdenes",
            "Watson en solitario",
            "Rendirse y salir de una partida",
            "Ajustes de la sala",
            "Stickers y avatares",
            "Mods en una sala",
            "Cursor propio",
            "Escenarios propios",
        };
        static readonly string[] TitlesEn =
        {
            "What Revival adds",
            "The launcher: ways to play",
            "The launcher: session and updates",
            "Controller",
            "Controller: speed and rumble",
            "Choosing the AI difficulty",
            "The five difficulties",
            "Irene on your own",
            "Irene: killing and more orders",
            "Watson on your own",
            "Surrendering and leaving a match",
            "Room settings",
            "Stamps and avatars",
            "Mods in a room",
            "Custom cursor",
            "Custom scenarios",
        };

        static readonly string[] PagesEs =
        {
            "{H}CRIMESIGHT Revival{/H} devuelve el juego en línea con servidores de la comunidad y le añade funciones nuevas. Esta guía explica cómo se usan.\n\n" +
                "• Se juega desde el {H}lanzador{/H}: eliges un modo y él abre el juego ya conectado.\n" +
                "• Partidas contra la IA, con amigos o en servidores de la comunidad.\n" +
                "• Mando, cinco dificultades de IA, stickers y avatares propios, escenarios propios y más.\n\n" +
                "Revival no incluye archivos de Konami: necesitas tener CRIMESIGHT en Steam.",
            "Elige uno de los {H}cuatro modos{/H} y pulsa {H}«Jugar»{/H}: el lanzador abre el juego ya conectado.\n\n" +
                "Tus partidas, victorias y puntos se guardan en tu PC.",
            "La sesión termina al cerrar el juego o con {H}«Terminar sesión»{/H}.\n" +
                "• ¿El juego ya estaba abierto? Ciérralo y vuelve a pulsar el modo.\n" +
                "• Una {H}campana{/H} arriba avisa de una versión nueva: ahí actualizas.\n" +
                "• {H}Mods{/H}: stickers, avatares, cursor y escenarios.",
            "<size=85%><pos=7.5%>Alejar<pos=22.25%>Girar<pos=70.25%>Girar<pos=82.75%>Acercar</size>\n" +
                "<size=130%><pos=8%>{LT}<pos=22%>{LB}<pos=70%>{RB}<pos=84%>{RT}</size>\n" +
                "<size=85%><pos=36%>Registro<pos=51.25%>Fin turno<pos=71.75%>Sospechosos</size>\n" +
                "<size=130%><pos=38%>{BACK}<pos=54%>{START}<pos=76%>{Y}</size>\n" +
                "<size=85%><pos=7.5%>Cursor<pos=66%>Stickers<pos=81%>Clic derecho</size>\n" +
                "<size=130%><pos=8%>{LS}<pos=68%>{X}<pos=84%>{B}</size>\n" +
                "<size=85%><pos=20.75%>Flechas<pos=59.5%>Cámara<pos=77%>Clic</size>\n" +
                "<size=130%><pos=22%>{DPAD}<pos=60%>{RS}<pos=76%>{A}</size>\n\n" +
                "La barra de ayuda de abajo enseña los botones del mando mientras lo usas.",
            "• Pulsa {LS} (el {H}stick izquierdo{/H}) para cambiar la velocidad del cursor y {RS} (el {H}derecho{/H}) para la de la cámara: lenta, media o rápida (el mando vibra 1, 2 o 3 veces).\n" +
                "• Vibra al elegir un personaje, al darle una orden y en los momentos de tensión.\n" +
                "• Funciona con mandos de Xbox, PlayStation, Switch y Steam Deck (con Steam Input), y los iconos se adaptan al tuyo.\n\n" +
                "Necesita la {H}recarga en caliente (BepInEx){/H}, que se activa en el lanzador, en Mods.",
            "En la sala, pulsa {H}«Expulsar»{/H} sobre una IA. Sale una ventana para:\n\n" +
                "• Elegir su dificultad: Fácil, Normal, Difícil, Experto o Pesadilla (al pasar el cursor explica cada una).\n" +
                "• Aplicarla a {H}todas las IA{/H} de la sala.\n" +
                "• {H}Dejar el hueco libre{/H} para que entre otra persona.\n\n" +
                "Sin BepInEx, cada expulsión pasa a la siguiente dificultad.",
            "• {H}Fácil{/H}: comete errores; ideal para aprender.\n" +
                "• {H}Normal{/H}: juega con cabeza, sin pasarse.\n" +
                "• {H}Difícil{/H}: solo ataca si es seguro y no deja a nadie solo.\n" +
                "• {H}Experto{/H}: piensa más, sin trampas; prevé tus órdenes y usa señuelos.\n" +
                "• {H}Pesadilla{/H}: como Experto, pero aprende de tus partidas anteriores en ese servidor (necesita al menos 3 tuyas en ese papel).\n\n" +
                "Cuanto más difícil, más puntos al ganar: de 200 (Fácil) a 1200 (Pesadilla).",
            "Si eres la única persona de la sala y llevas a Irene, das órdenes a Moriarty con tus stickers:\n\n" +
                "{ST_IRENE}  Pon el sticker {H}«¡Aquí tienes a tu asesino!»{/H} sobre un personaje: Moriarty lo moverá este turno y te contesta «Entendido».\n\n" +
                "Justo después, pon el indicador {H}«Moverse»{/H} en el suelo, donde quieras que vaya.\n\n" +
                "Puedes hacerlo con {H}dos personajes por turno{/H}.",
            "{ST_IRENE}  {H}Para matar{/H}: el sticker sobre el asesino y «Moverse» en la casilla de la víctima. Si lleva arma y llega este turno, ataca. Mira antes que no haya testigos.\n\n" +
                "• Si no le das órdenes, Moriarty juega solo y ataca cuando puede hacerlo sin que le vean.\n" +
                "• {H}«Yo controlaré a…»{/H} sobre un personaje: Moriarty no lo toca este turno.\n\n" +
                "Tu compañero IA juega en Difícil (o en Experto si los rivales son Experto o Pesadilla).",
            "Si eres la única persona de la sala y llevas a Watson, guías a Sherlock con tus stickers:\n\n" +
                "{ST_SUS}  {H}«Sospecho que es el asesino»{/H} sobre alguien (o el indicador {H}«Peligro»{/H}): Sherlock aparta de él a quien esté en su habitación, turno tras turno, y al final lo acusa a él. Te contesta «Entendido».\n\n" +
                "{ST_NOSUS}  {H}«No creo que sea el asesino»{/H} sobre el mismo personaje: lo olvida.\n\n" +
                "Tu compañero IA juega en Difícil (o en Experto si los rivales son Experto o Pesadilla).",
            "• Si eres la única persona de la sala (contra la IA o en el entrenamiento), en los ajustes de la partida ({H}la llave inglesa{/H}, arriba a la derecha) siempre tienes {H}«Rendirse»{/H}, con cualquier papel y desde el primer turno. Cuenta como derrota.\n" +
                "• Con más personas sigue como en el original: solo Moriarty y desde el turno 4.\n\n" +
                "• Si alguien se rinde o se va a mitad de partida, su bando pierde y gana el otro.\n" +
                "• Si el que desaparece es el anfitrión, los invitados se apuntan la victoria en su PC (si ellos tienen internet).",
            "En la sala, {H}«Modificar ajustes del juego»{/H} tiene dos ajustes más que el original:\n\n" +
                "• {H}Máximo de turnos{/H}: de 1 a 99 (por defecto 10). Útil en mapas grandes y escenarios propios.\n" +
                "• {H}Tiempo por turno{/H}: de 60 a 999 segundos en cualquier sala, para jugar con calma.\n\n" +
                "Los aplica el anfitrión y les llegan a todos.",
            "En el lanzador, {H}Mods{/H}: añade tus propios stickers y avatares a partir de cualquier imagen.\n\n" +
                "• Una lámina con varios stickers se separa sola y se les quita el fondo.\n" +
                "• Puedes poner un texto a cada sticker para el registro de la partida.\n" +
                "• Los avatares llenan el marco que elijas, sin huecos.\n" +
                "• Nunca tocan los stickers ni avatares originales, tampoco los de pago.",
            "En una sala, los mods se comparten:\n\n" +
                "• Quien se une se descarga los del anfitrión.\n" +
                "• Si traes los tuyos, al anfitrión le sale un aviso aquí en el juego: {H}«Descargar»{/H}, {H}«Aceptar siempre»{/H} o «No, gracias».\n" +
                "• «Aceptar siempre» también se puede poner en el lanzador, en Mods → «Mods de los invitados».\n\n" +
                "Con BepInEx, los cambios se ven sin reiniciar el juego.",
            "En el lanzador, {H}Mods → «Cursor propio»{/H}:\n\n" +
                "• {H}«Elegir imagen…»{/H}: cualquier imagen se convierte en el cursor del juego (se ajusta sola y se le quita el fondo si no tiene transparencia).\n" +
                "• Elige dónde hace clic: en la punta (flecha) o en el centro (mira).\n" +
                "• Actívalo o desactívalo cuando quieras.\n\n" +
                "Solo lo ves tú. Necesita BepInEx.",
            "En el lanzador, {H}Mods → Creador de escenarios{/H}: recoloca las habitaciones de un escenario y guárdalo como uno nuevo.\n\n" +
                "• Mueve, gira, quita o repite habitaciones; elige puertas, ventanas de los perros, gas y salidas.\n" +
                "• {H}Prueba rápida{/H}: lo ves en el «Escenario de pruebas (CSR)» sin guardarlo.\n" +
                "• Los guardados salen en la lista de escenarios de la sala.\n" +
                "• En una sala, todos reciben los escenarios del anfitrión antes de empezar.",
        };

        static readonly string[] PagesEn =
        {
            "{H}CRIMESIGHT Revival{/H} brings online play back with community servers and adds new features. This guide explains how to use them.\n\n" +
                "• You play from the {H}launcher{/H}: pick a mode and it opens the game already connected.\n" +
                "• Matches against the AI, with friends or on community servers.\n" +
                "• Controller support, five AI difficulties, your own stamps and avatars, custom scenarios and more.\n\n" +
                "Revival includes no Konami files: you need to own CRIMESIGHT on Steam.",
            "Pick one of the {H}four modes{/H} and press {H}\"Play\"{/H}: the launcher opens the game already connected.\n\n" +
                "Your matches, wins and points are saved on your PC.",
            "The session ends when you close the game, or with {H}\"End session\"{/H}.\n" +
                "• Game already open? Close it and press the mode again.\n" +
                "• A {H}bell{/H} at the top means a new version: update there.\n" +
                "• {H}Mods{/H}: stamps, avatars, cursor and scenarios.",
            "<size=85%><pos=6%>Zoom out<pos=21.5%>Rotate<pos=69.5%>Rotate<pos=82.75%>Zoom in</size>\n" +
                "<size=130%><pos=8%>{LT}<pos=22%>{LB}<pos=70%>{RB}<pos=84%>{RT}</size>\n" +
                "<size=85%><pos=39.75%>Log<pos=52%>End turn<pos=74%>Suspects</size>\n" +
                "<size=130%><pos=38%>{BACK}<pos=54%>{START}<pos=76%>{Y}</size>\n" +
                "<size=85%><pos=7.5%>Cursor<pos=62%>Pings/stamps<pos=81.5%>Right-click</size>\n" +
                "<size=130%><pos=8%>{LS}<pos=68%>{X}<pos=84%>{B}</size>\n" +
                "<size=85%><pos=21.5%>Arrows<pos=59.5%>Camera<pos=76.25%>Click</size>\n" +
                "<size=130%><pos=22%>{DPAD}<pos=60%>{RS}<pos=76%>{A}</size>\n\n" +
                "The help bar at the bottom shows the controller buttons while you use it.",
            "• Click {LS} (the {H}left stick{/H}) to change the cursor speed and {RS} (the {H}right{/H} one) for the camera speed: slow, medium or fast (it vibrates 1, 2 or 3 times).\n" +
                "• It vibrates when you pick a character, when you give an order and in tense moments.\n" +
                "• Works with Xbox, PlayStation, Switch and Steam Deck controllers (with Steam Input), and the icons match yours.\n\n" +
                "Needs {H}hot reload (BepInEx){/H}, turned on in the launcher, under Mods.",
            "In the room, click {H}\"Kick\"{/H} on an AI. A window opens to:\n\n" +
                "• Pick its difficulty: Easy, Normal, Hard, Expert or Nightmare (hover to see what each one does).\n" +
                "• Apply it to {H}every AI{/H} in the room.\n" +
                "• {H}Free the seat{/H} so another person can join.\n\n" +
                "Without BepInEx, each kick moves to the next difficulty.",
            "• {H}Easy{/H}: makes mistakes; good for learning.\n" +
                "• {H}Normal{/H}: plays sensibly, without going overboard.\n" +
                "• {H}Hard{/H}: only strikes when it's safe and never leaves anyone alone.\n" +
                "• {H}Expert{/H}: thinks harder, no cheating; predicts your orders and uses decoys.\n" +
                "• {H}Nightmare{/H}: like Expert, but learns from your previous matches on that server (it needs at least 3 of yours in that role).\n\n" +
                "The harder, the more points for winning: from 200 (Easy) to 1200 (Nightmare).",
            "If you're the only person in the room and you play Irene, you give Moriarty orders with your stamps:\n\n" +
                "{ST_IRENE}  Place the {H}\"Here is your villain!\"{/H} stamp on a character: Moriarty will move them this turn and answers \"Understood\".\n\n" +
                "Right after, place the {H}\"Move\"{/H} ping on the floor where you want them to go.\n\n" +
                "You can do this with {H}two characters per turn{/H}.",
            "{ST_IRENE}  {H}To kill{/H}: the stamp on the killer and \"Move\" on the victim's tile. If they're armed and can get there this turn, they strike. Check for witnesses first.\n\n" +
                "• If you give no orders, Moriarty plays on its own and strikes when it can do it unseen.\n" +
                "• {H}\"I'll command…\"{/H} on a character: Moriarty leaves it alone this turn.\n\n" +
                "Your AI partner plays on Hard (or Expert if your rivals are Expert or Nightmare).",
            "If you're the only person in the room and you play Watson, you guide Sherlock with your stamps:\n\n" +
                "{ST_SUS}  {H}\"I suspect they are the villain\"{/H} on someone (or the {H}\"Danger\"{/H} ping): Sherlock moves everyone in their room away from them, turn after turn, and accuses them at the end. He answers \"Understood\".\n\n" +
                "{ST_NOSUS}  {H}\"I don't think they are the villain\"{/H} on the same character: he forgets it.\n\n" +
                "Your AI partner plays on Hard (or Expert if your rivals are Expert or Nightmare).",
            "• If you're the only person in the room (against the AI or in training), the match settings ({H}the wrench{/H}, top right) always have {H}\"Surrender\"{/H}, with any role and from the first turn. It counts as a loss.\n" +
                "• With more people it works like the original: only Moriarty, from turn 4.\n\n" +
                "• If someone surrenders or leaves mid-match, their side loses and the other one wins.\n" +
                "• If the one who disappears is the host, the guests get the win recorded on their PC (if they have internet).",
            "In the room, the {H}game settings{/H} have two more options than the original:\n\n" +
                "• {H}Max. turns{/H}: from 1 to 99 (10 by default). Handy on big maps and custom scenarios.\n" +
                "• {H}Turn time{/H}: from 60 to 999 seconds in any room, to play at your own pace.\n\n" +
                "The host sets them and everyone gets them.",
            "In the launcher, {H}Mods{/H}: add your own stamps and avatars from any image.\n\n" +
                "• A sheet with several stamps is split up automatically and their background removed.\n" +
                "• You can give each stamp a text for the match log.\n" +
                "• Avatars fill the frame you pick, with no gaps.\n" +
                "• They never touch the original stamps or avatars, including paid ones.",
            "In a room, mods are shared:\n\n" +
                "• Whoever joins downloads the host's.\n" +
                "• If you bring yours, the host gets a prompt here in the game: {H}\"Download\"{/H}, {H}\"Always accept\"{/H} or \"No thanks\".\n" +
                "• \"Always accept\" can also be set in the launcher, under Mods → \"Guests' mods\".\n\n" +
                "With BepInEx, changes show up without restarting the game.",
            "In the launcher, {H}Mods → \"Custom cursor\"{/H}:\n\n" +
                "• {H}\"Choose image…\"{/H}: any image becomes the game's cursor (it's resized and its background removed if it has no transparency).\n" +
                "• Choose where it clicks: the tip (arrow) or the centre (crosshair).\n" +
                "• Turn it on or off whenever you like.\n\n" +
                "Only you see it. Needs BepInEx.",
            "In the launcher, {H}Mods → Scenario creator{/H}: rearrange the rooms of a scenario and save it as a new one.\n\n" +
                "• Move, rotate, remove or repeat rooms; choose doors, dog windows, gas and starting points.\n" +
                "• {H}Quick test{/H}: see it in the \"Test scenario (CSR)\" without saving it.\n" +
                "• Saved ones appear in the room's scenario list.\n" +
                "• In a room, everyone gets the host's scenarios before the match starts.",
        };

        public static string Help(int lang) => lang == 5
            ? "Cómo funciona lo que añade Revival: lanzador, mando, IA, stickers y más."
            : "How everything Revival adds works: launcher, controller, AI, stamps and more.";

        // Tema -> captura (nombre en GuideImages) que sale encima del texto
        static readonly System.Collections.Generic.Dictionary<int, string> Images = new()
        {
            [1] = "launcher_modes",   // El lanzador: modos de juego
            [2] = "launcher_bars",    // El lanzador: sesion y novedades
        };

        /// <summary>La captura de la pagina, o null si no tiene.</summary>
        public static string Image(int t) => Images.TryGetValue(t, out var n) ? n : null;

        public static int Count => TitlesEs.Length;
        public static string TopicTitle(int t, int lang) => lang == 5 ? TitlesEs[t] : TitlesEn[t];
        public static string Page(int t, int lang) => lang == 5 ? PagesEs[t] : PagesEn[t];
    }
}
