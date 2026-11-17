# Cambios / Changelog

El primer bloque (desde el primer `## ` hasta el siguiente) es el que el lanzador enseña al ofrecer una
actualización. Antes de subir una versión con novedades, añade arriba un bloque nuevo con sus dos
apartados, `### Español` y `### English`. Si subes un arreglo sin tocar este archivo, el lanzador enseña el
mensaje del commit.

The first block (from the first `## ` to the next one) is what the launcher shows when it offers an update.

## 1.1 · Creador de escenarios / Scenario creator

### Español
- **Creador de escenarios** (Mods → Creador de escenarios): recoloca las habitaciones de un escenario del juego y guárdalo como uno nuevo. Aparece en la lista de escenarios del juego con su nombre; los originales no se tocan. Necesita la recarga en caliente.
- Exporta e importa escenarios como archivos `.csrstage`, y activa o desactiva los que quieras (hasta 20 a la vez).
- En una sala, todos reciben los escenarios del anfitrión. La partida no empieza hasta que todos tienen el escenario elegido.
- Las IA contestan a tus stickers con otro al azar.
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
