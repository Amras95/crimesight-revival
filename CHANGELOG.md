# Cambios / Changelog

El primer bloque (desde el primer `## ` hasta el siguiente) es el que el lanzador enseña al ofrecer una
actualización. Antes de subir una versión con novedades, añade arriba un bloque nuevo con sus dos
apartados, `### Español` y `### English`. Si subes un arreglo sin tocar este archivo, el lanzador enseña el
mensaje del commit.

The first block (from the first `## ` to the next one) is what the launcher shows when it offers an update.

## 1.1 (actualización) · Irene, entrenamiento y salir de partidas / Irene, training and leaving matches

### Español
- **Irene ya puede dirigir a Moriarty IA de verdad** (en solitario: tú eres Irene y Moriarty es la IA). Antes no funcionaba: el servidor dejaba de hacer caso a tus avisos después de la primera orden de la partida y no reconocía el sticker de Irene. Cómo se hace:
  1. Pon el sticker de Irene **«¡Aquí tienes a tu asesino!»** sobre un personaje. Moriarty IA lo moverá este turno y te contesta «Entendido». Si el sticker no cae justo encima, cuenta el personaje más cercano.
  2. Justo después, pon el ping de Irene **«Moverse»** en el suelo, donde quieras que vaya. Si no pones ninguno, Moriarty lo mueve a su manera.
  3. Puedes hacerlo con **dos personajes por turno**: sticker y «Moverse» para el primero, y luego lo mismo para el segundo.
  4. **Para matar**: sticker sobre el asesino y «Moverse» en la casilla de la víctima. Si el asesino lleva arma y llega este turno, ataca. Asegúrate de que no hay testigos: Moriarty hace lo que le pides aunque los haya.
  5. Si no le das órdenes, Moriarty juega solo y ataca cuando puede hacerlo sin que le vean (antes, si le pedías dos personajes, ya no atacaba nunca).
  6. **«Yo controlaré a…»** sobre un personaje = Moriarty no lo toca este turno.
- Cuando dirige a tu compañero, solo contesta él (antes contestaba cualquier IA con un sticker al azar).
- Tu compañero IA en solitario con Irene o Watson se llama ahora «(Difícil)» en la partida, que es como juega. En la sala vuelve a su dificultad.
- Las IA ya vuelven a avisarte con un ping de qué personajes van a mover y a hacer caso de tus «Yo controlaré a…» durante toda la partida (dejaban de hacerlo tras la primera orden).
- Las IA contestan a tu sticker con el mismo («Hola» → «Hola»). Si es uno de pago o de un mod, con uno gratuito al azar.
- **Entrenamiento en solitario** (menú del juego): ya no se cierra el juego al empezarlo, y Moriarty mueve al asesino y mata, como en el original (antes no pasaba nada en toda la partida).
- **Salir de una partida**: si eres la única persona de la sala (contra IAs o en el entrenamiento), en los ajustes de la partida (la llave inglesa) está siempre el botón **«Rendirse»**, con cualquier papel y desde el primer turno. Te lleva a los resultados y de vuelta a la sala (cuenta como derrota). Con más personas en la sala sigue como en el juego original: solo Moriarty y desde el turno 4.
- **Avatares**: ya no quedan huecos en ningún marco. Si la imagen se corta por un lado (la ropa de un busto, el borde de una foto), se continúa hasta el borde del marco sin deformar la cara. Las fotos ya no se agujerean al quitar el «fondo». No hace falta volver a añadir los avatares.
- **Stickers de los invitados**: al unirte a una sala con tus propios stickers, el lanzador espera a que el anfitrión los acepte antes de abrir el juego. Además, los stickers sacados de una lámina con nombre largo recibían en la sala otros ids que en tu PC y no salían. Antes solo veías los del anfitrión.
- **Mando**:
  - La barra de ayuda enseña los iconos del mando (antes seguía enseñando las teclas), sin iconos repetidos ni colores raros.
  - Con Steam Input, los mandos de PlayStation y Switch salen con sus propios iconos: Revival le pregunta a Steam qué mando es de verdad.
  - Start (Options / +) pulsa «Finalizar turno» de verdad.
  - El stick derecho desplaza las listas en los menús, en los ajustes de la sala y en el Registro.

### English
- **Irene can now really direct an AI Moriarty** (solo: you're Irene and Moriarty is the AI). It didn't work before: the server stopped listening to your pings after the first order of the match and didn't recognise Irene's stamp. How it works:
  1. Put Irene's **"Here is your villain!"** stamp on a character. The AI Moriarty will move it this turn and answers "Understood". If the stamp doesn't land right on top, the nearest character counts.
  2. Right after, put Irene's **"Move"** ping on the floor where you want it to go. If you don't, Moriarty moves it its own way.
  3. You can do it with **two characters per turn**: stamp and "Move" for the first one, then the same for the second.
  4. **To kill**: stamp on the killer and "Move" on the victim's tile. If the killer is armed and can get there this turn, it attacks. Make sure there are no witnesses: Moriarty does what you ask even if there are.
  5. If you don't give orders, Moriarty plays on its own and attacks when it can do it unseen (before, once you asked for two characters it never attacked).
  6. **"I'll command…"** on a character = Moriarty leaves it alone this turn.
- When you direct your teammate, only it answers (before, any AI answered with a random stamp).
- Your AI teammate when playing solo as Irene or Watson is now called "(Hard)" in the match, which is how it plays. Back in the room it returns to its difficulty.
- The AIs ping which characters they're going to move again, and respect your "I'll command…" for the whole match (they stopped after the first order).
- The AIs answer your stamp with the same one ("Hello" → "Hello"). If it's a paid or modded one, with a random free one.
- **Solo training** (game menu): the game no longer closes when you start it, and Moriarty now moves the killer and kills, like in the original (nothing happened during the whole match before).
- **Leaving a match**: if you're the only person in the room (against AIs or in training), the match settings (the wrench) always have the **"Surrender"** button, with any role and from the first turn. It takes you to the results and back to the room (counts as a loss). With more people in the room it stays as in the original game: Moriarty only, from turn 4.
- **Avatars**: no more gaps in any frame. If the picture is cut on one side (a bust's clothes, the edge of a photo), it's continued to the edge of the frame without distorting the face. Photos no longer get holes when the "background" is removed. No need to add your avatars again.
- **Guests' stamps**: when you join a room with your own stamps, the launcher waits for the host to accept them before opening the game. Also, stamps cut from a sheet with a long file name got different ids in the room than on your PC and didn't show up. Before, you only saw the host's.
- **Controller**:
  - The help bar shows the controller icons (it kept showing the keys before), with no repeated icons or odd colours.
  - With Steam Input, PlayStation and Switch controllers get their own icons: Revival asks Steam which controller it really is.
  - Start (Options / +) really presses "Commit Command".
  - The right stick scrolls lists in menus, in the room settings and in the Log.

## 1.1 · Creador de escenarios / Scenario creator

### Español
- **Creador de escenarios** (Mods → Creador de escenarios): recoloca las habitaciones de un escenario del juego y guárdalo como uno nuevo. Aparece en la lista de escenarios del juego con su nombre; los originales no se tocan. Necesita la recarga en caliente.
- Exporta e importa escenarios como archivos `.csrstage`, y activa o desactiva los que quieras (hasta 20 a la vez).
- En una sala, todos reciben los escenarios del anfitrión. La partida no empieza hasta que todos tienen el escenario elegido.
- Las IA contestan a tus stickers con otro al azar.
- **Se puede jugar con mando** (Xbox, DualSense, DualShock, Switch, Steam Deck…): stick izquierdo para el cursor, A/B para hacer clic, stick derecho, gatillos y bumpers para la cámara, y Start para finalizar el turno. La barra de ayuda muestra los botones de tu mando (Xbox, PlayStation o Switch). Con vibración: al elegir un personaje y darle una orden, un latido cuando el asesino y otro personaje se quedan a solas (hasta que hablan, o hasta el golpe si hay ejecución) y cuando Sherlock hace su deducción. Necesita la recarga en caliente.
- Los avatares hechos con una foto ya no se recortan en un círculo: llenan el cuadro y toman la forma del marco que elijas en el juego. Los que ya tenías importados hay que volver a añadirlos.
- **Watson** ya descubre cada turno un mueble con comida, como en el juego original.
- Si avisas con un ping de que llevas un personaje («Yo controlaré a…»), la IA de tu bando lo deja y te contesta «Entendido». Irene ya puede jugar con un Moriarty IA sin que le pise las órdenes.
- Tus compañeros IA te avisan con un ping de qué personajes van a mover cada turno.
- **Irene** ve dónde está toda la comida desde el principio, como dice ella al empezar.
- **En solitario con Irene o Watson** (tú contra IAs), tu compañero IA juega en «Difícil» y puedes dirigirlo:
  - Irene: «¡Aquí tienes a tu asesino!» sobre un personaje y luego un ping en el suelo («Moverse») = Moriarty lleva a ese personaje allí (hasta dos por turno). Si es el asesino armado y lo mandas a la casilla de la víctima, ataca.
  - Watson: «Sospecho que es el asesino» sobre alguien = Sherlock aparta de él a quien esté en su habitación; «No creo que sea el asesino» = lo olvida.
- Arreglado: tras jugar un escenario personalizado, en el siguiente los personajes podían andar por el vacío.
- Arreglado: un fallo del propio juego que a veces dejaba al asesino andando sin parar y colgaba el turno.
- El lanzador ya no se actualiza solo: te enseña las novedades y tú decides cuándo.

### English
- **Scenario creator** (Mods → Scenario creator): rearrange the rooms of one of the game's scenarios and save it as a new one. It shows up in the game's scenario list with its name; the originals are never changed. Needs hot reload.
- Export and import scenarios as `.csrstage` files, and turn on or off the ones you want (up to 20 at once).
- In a room, everyone gets the host's scenarios. The match doesn't start until everyone has the selected one.
- The AI players answer your stickers with a random one.
- **You can play with a controller** (Xbox, DualSense, DualShock, Switch, Steam Deck…): left stick for the cursor, A/B to click, right stick, triggers and bumpers for the camera, and Start to commit your turn. The help bar shows your controller's buttons (Xbox, PlayStation or Switch). With rumble: when you select a character and give an order, a heartbeat when the killer and someone else are left alone (until they talk, or until the blow if it's an execution) and when Sherlock makes his deduction. Needs hot reload.
- Avatars made from a photo are no longer cut into a circle: they fill the frame and take the shape of the frame you pick in the game. Avatars you had already imported need to be added again.
- **Watson** now discovers a piece of furniture with food every turn, like in the original game.
- If you ping that you're taking a character ("I'll control…"), the AI on your side leaves it to you and answers "Understood". Irene can now play with an AI Moriarty without it overriding her orders.
- Your AI teammates ping which characters they're going to move each turn.
- **Irene** sees where all the food is from the start, as she says at the beginning.
- **Solo with Irene or Watson** (you against AIs): your AI teammate plays on "Hard" and you can direct it:
  - Irene: "Here's your killer!" on a character, then a ping on the floor ("Move") = Moriarty takes that character there (up to two per turn). If it's the armed killer and you send it to the victim's tile, it attacks.
  - Watson: "I suspect they're the killer" on someone = Sherlock moves everyone in their room away from them; "I don't think they're the killer" = forgets it.
- Fixed: after playing a custom scenario, characters could walk through the void in the next one.
- Fixed: a bug in the game itself that sometimes left the killer walking endlessly and froze the turn.
- The launcher no longer updates by itself: it shows you what's new and you decide when.

## 1.0

### Español
- Primera versión pública: partidas en solitario y con amigos, IA para los cuatro papeles, progreso local y mods de stickers y avatares.

### English
- First public version: solo and friends matches, AI for all four roles, local progress, and sticker and avatar mods.
