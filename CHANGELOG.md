# Cambios / Changelog

El primer bloque (desde el primer `## ` hasta el siguiente) es el que el lanzador enseña al ofrecer una
actualización. Antes de subir una versión con novedades, añade arriba un bloque nuevo con sus dos
apartados, `### Español` y `### English`. Si subes un arreglo sin tocar este archivo, el lanzador enseña el
mensaje del commit.

The first block (from the first `## ` to the next one) is what the launcher shows when it offers an update.

## 1.3 · Modelos 3D y animaciones propios / Your own 3D models and animations

### Español

- **Pon tus propios modelos 3D a los personajes** (Mods > Modelos, con la recarga en caliente de BepInEx). Mete un archivo `.fbx` o `.glb` en la carpeta de modelos (o una subcarpeta con el modelo y sus texturas) y elígelo en la lista del personaje. Solo lo ves tú.
  - **Vale casi cualquier humanoide**: Mixamo, Ready Player Me, VRoid/VRM, VRChat/Unity, Blender, Biped de 3ds Max, DAZ, Unreal o MMD. Sus huesos se reconocen por el nombre y el modelo se pone de pie, a la altura del personaje y en su postura, aunque venga en otra escala, con otros ejes o en postura A.
  - **Conserva sus proporciones**: lleva su propio esqueleto, que copia en cada fotograma las animaciones del personaje, así que no se deforma aunque tenga los brazos o las piernas más largos. Los hombros acompañan a los brazos para que no queden cuadrados.
  - **Texturas**: la de color de cada material, dentro del `.fbx` o junto a él (PNG, JPG, TGA, BMP, PSD…).
  - Lee FBX binarios y de texto, también los antiguos 6.1 que da Mixamo con «FBX for Unity».
  - Para que encaje perfecto, el juego deja en la carpeta `esqueletos` el esqueleto de cada personaje (solo los huesos) para hacer el modelo encima en Blender. El `README.txt` de la carpeta lo explica.
  - Los animales, los bustos y los modelos sin esqueleto no se pueden poner (a una malla sin esqueleto se le puede poner gratis en Mixamo). El pelo y las faldas van rígidos.
- **Animaciones propias**: en la misma pestaña, cambia el reposo, el andar o el correr de cada personaje por una animación tuya (`.fbx` o `.glb`, por ejemplo de Mixamo con «Without Skin» e «In Place») de la carpeta `animaciones`. Se adapta sola a su esqueleto y funciona con los modelos del juego y con los tuyos.

### English

- **Give the characters your own 3D models** (Mods > Models, with BepInEx hot reload). Put a `.fbx` or `.glb` file in the models folder (or a subfolder with the model and its textures) and pick it in the character's list. Only you see it.
  - **Almost any humanoid works**: Mixamo, Ready Player Me, VRoid/VRM, VRChat/Unity, Blender, 3ds Max Biped, DAZ, Unreal or MMD. Its bones are recognised by name and the model is stood up, scaled to the character and put in its pose, even with another scale, other axes or an A pose.
  - **It keeps its proportions**: it gets its own skeleton, which copies the character's animations every frame, so it doesn't get distorted even with longer arms or legs. The shoulders follow the arms so they don't look square.
  - **Textures**: each material's colour texture, inside the `.fbx` or next to it (PNG, JPG, TGA, BMP, PSD…).
  - Reads binary and text FBX, including the old 6.1 ones Mixamo gives with "FBX for Unity".
  - For a perfect fit, the game leaves each character's skeleton (bones only) in the `esqueletos` folder to build the model on in Blender. The folder's `README.txt` explains it.
  - Animals, busts and models without a skeleton can't be used (Mixamo rigs a mesh for free). Hair and skirts are rigid.
- **Your own animations**: in the same tab, replace each character's idle, walk or run with your own animation (`.fbx` or `.glb`, e.g. from Mixamo with "Without Skin" and "In Place") from the `animaciones` folder. It fits itself to the skeleton and works with the game's models and with yours.

## 1.2 · IA Experto y Pesadilla / Expert and Nightmare AI

### Español

- **Nueva dificultad de la IA: Experto** (por encima de Difícil; se elige en la sala, con la ventana de abajo o expulsando a la IA). Juega con lo mismo que vería una persona, sin trampas, pero piensa más:
  - **Sherlock / Watson**: sospechan con más criterio (correr sin que lo mande Sherlock delata, porque quien va por su cuenta nunca corre; también las órdenes pisadas, acercarse a las posibles víctimas y llevar arma). Alejan primero al sospechoso claro de todas las víctimas, nunca lo acercan al grupo, y en los últimos turnos lo dan todo por proteger.
  - **Moriarty**: prevé lo que va a ordenar Sherlock y no le da a su asesino órdenes que chocarían y le delatarían. Si su asesino ya es el principal sospechoso, se esconde y hace correr a un inocente hacia otra posible víctima para que parezca el culpable. En los últimos turnos busca el asesinato con lo previsto, y en el último se la juega.
  - **Irene**: aparta testigos hacia los peligros y, si no hay nada mejor, hace parecer culpable a un inocente.
  - Ganar contra la IA Experta da 1000 puntos. En solitario con Irene o Watson, si los rivales son Expertos, tu compañero IA también lo es.
- **Nueva dificultad: Pesadilla** (después de Experto en el ciclo). Es la Experta, pero aprende de tus partidas anteriores en ese servidor, como haría un rival que ya ha jugado contra ti:
  - **Contra tu Moriarty**: aprende qué delata a tu asesino (si suele correr, registrar, acercarse a las víctimas…) comparándolo con cómo se mueven los inocentes, y en qué turnos sueles atacar; en esos turnos lo da todo por proteger.
  - **Contra tu Sherlock o Watson**: aprende si te tragas los señuelos (si acusas al inocente que corrió) y si vigilas al asesino con tus órdenes. Si te los tragas, Moriarty usa señuelos casi siempre; si no, casi nunca, y esconde antes a su asesino si le vigilas. Además busca el asesinato desde cuatro turnos antes del final.
  - Necesita al menos 3 partidas tuyas en ese papel; hasta entonces juega como Experta, algo más agresiva. Ganarle da 1200 puntos.
- **Elegir la dificultad de la IA con una ventana** (con el plugin de BepInEx): en la sala, al pulsar «Expulsar» sobre una IA sale una ventana con las cinco dificultades a la vista (al pasar el ratón explica qué hace cada una), la opción de aplicarla a todas las IA de la sala y la de dejar el hueco libre. Funciona con ratón, mando y Esc para cancelar. Sin el plugin, expulsar sigue cambiando la dificultad en ciclo como antes.
- **Stickers cruzados en la sala al unirse otro jugador con mods**: cuando llegaban sus stickers, tu rueda de la sala (que suele estar cerrada) se quedaba con las posiciones de antes y al usar «tu» sticker salía el de otro hasta empezar la partida. Ahora se recalculan también las ruedas cerradas y, por si acaso, cada rueda al abrirse.
- **Las ventanas del plugin** (aviso de mods de los invitados y dificultad de la IA) son una copia de las ventanas del propio juego (banda verde con el título, papel, recuadro y botones en chevrón, que se iluminan igual al pasar el ratón); solo cambian sus textos y botones. La opción elegida va en ámbar, como «Iniciar partida».
- **Registro de partidas**: el servidor guarda lo que pasa en cada partida (quién llevaba cada papel, las órdenes de cada turno, el asesinato y las acusaciones) en la carpeta de datos, en `match_logs`. Solo se queda en el PC de quien hace de servidor y es de donde aprende la dificultad Pesadilla.
- **El servidor ya no se cierra solo al acabar una partida**: el lanzador comprobaba si el juego seguía abierto y, si Windows tardaba en responder (pasa con el PC cargado), lo daba por cerrado y terminaba la sesión. Ahora vuelve a mirar antes de cerrar nada.

### English

- **New AI difficulty: Expert** (above Hard; you pick it in the room, with the window below or by kicking the AI). It plays with the same information a person would have, no cheating, but thinks harder:
  - **Sherlock / Watson**: sharper suspicion (running without Sherlock's order gives it away, since characters acting on their own never run; so do overridden orders, getting close to possible victims and carrying a weapon). They move the clear suspect away from every victim first, never bring them back to the group, and go all-in on protection in the last turns.
  - **Moriarty**: predicts Sherlock's orders and doesn't give its killer orders that would clash and give it away. If its killer is already the main suspect, it lies low and makes an innocent run towards another possible victim to frame them. In the last turns it hunts for the kill using that prediction, and on the final one it goes for it.
  - **Irene**: lures witnesses towards hazards and, if there's nothing better, frames an innocent.
  - Beating the Expert AI gives 1000 points. Playing solo as Irene or Watson against Expert rivals, your AI partner is Expert too.
- **New difficulty: Nightmare** (after Expert in the cycle). It's the Expert AI, but it learns from your previous matches on that server, like an opponent who has already played against you:
  - **Against your Moriarty**: it learns what gives your killer away (whether it tends to run, search, get close to victims…) by comparing it with how innocents move, and on which turns you usually strike; on those turns it goes all-in on protection.
  - **Against your Sherlock or Watson**: it learns whether you fall for decoys (whether you accuse the innocent who ran) and whether you watch the killer with your orders. If you fall for them, Moriarty uses decoys almost always; if not, hardly ever, and it hides its killer earlier if you watch it. It also hunts for the kill from four turns before the end.
  - It needs at least 3 of your matches in that role; until then it plays like Expert, a bit more aggressive. Beating it gives 1200 points.
- **Pick the AI difficulty from a window** (with the BepInEx plugin): in the room, clicking "Kick" on an AI opens a window with all five difficulties in view (hover to see what each one does), the option to apply it to every AI in the room and to free the seat. Works with mouse, controller and Esc to cancel. Without the plugin, kicking still cycles the difficulty like before.
- **Mixed-up stamps in the room when another player joins with mods**: when their stamps arrived, your room stamp wheel (usually closed) kept the old positions, so using "your" stamp showed someone else's until the match started. Now closed wheels are recalculated too and, just in case, each wheel when it opens.
- **The plugin's windows** (guests' mods prompt and AI difficulty) are copies of the game's own windows (green title band, paper, frame and chevron buttons that light up the same way on hover); only their texts and buttons change. The chosen option is amber, like "Start match".
- **Match records**: the server saves what happens in each match (who played each role, every turn's orders, the murder and the accusations) in its data folder, under `match_logs`. It stays on the host's PC and it's what the Nightmare difficulty learns from.
- **The server no longer closes on its own after a match**: the launcher checked whether the game was still open and, if Windows was slow to answer (it happens with a busy PC), assumed it was closed and ended the session. Now it checks again before closing anything.

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
- **Salir a mitad de partida cuenta como derrota**: si alguien cierra el juego, se desconecta o se rinde, pierde su bando y gana el otro; a los demás el juego les enseña el final. Si el que desaparece es el anfitrión (cierra el lanzador o se queda sin conexión), los invitados se apuntan la victoria en su PC, siempre que ellos sí tengan internet.
- **Máximo de turnos**: en los ajustes de la sala vuelve a estar el ajuste escondido del juego original, ahora de 1 a 99 turnos (por defecto 10). Útil con escenarios propios y en mapas grandes, donde hace falta más tiempo para explorar.
- **Tiempo por turno**: ahora va de **60 a 999 segundos** en cualquier sala (antes, en las públicas, el máximo era 180), por si quieres jugar con calma.
- **Cursor propio**: en el lanzador, Mods → «Cursor propio»: eliges una imagen y será el cursor del juego (se ajusta sola a 32×32 y se le quita el fondo si no tiene transparencia). Puedes elegir dónde hace clic (punta o centro), activarlo o desactivarlo, y ver cuál tienes puesto. Solo lo ves tú y necesita el plugin de BepInEx.
- **Mando: cursor más suave**: el stick izquierdo ya no mueve el cursor «a cuadros». La dirección es exactamente la del dedo (se pueden hacer círculos y diagonales finas), con una zona muerta redonda, y la aceleración del ratón de Windows ya no lo tuerce.
- **Mando: cámara más suave**: el stick derecho mueve la cámara sin tirones, en la dirección exacta del stick y más rápido cuanto más lo inclinas, igual que el cursor. Arranca y frena con suavidad, y la velocidad (R3) se sigue pudiendo cambiar.
- **Mods de los invitados en el juego**: cuando alguien entra en tu sala con sus stickers o avatares, el aviso para descargarlos sale también dentro del juego (antes solo en el lanzador y pasaba desapercibido). Puedes contestar en cualquiera de los dos.
- **«Aceptar siempre» los mods de los invitados**: en el aviso o en Mods → «Mods de los invitados». Así se añaden sin preguntar cada vez.
- **Aviso de actualización con el lanzador abierto**: cada media hora mira si hay versión nueva y, si la hay, aparece una campana arriba. Al pulsarla ves las novedades y puedes actualizar al momento; si el juego, una sesión u otro lanzador están abiertos, te avisa y los cierra antes de actualizar.
- **El servidor ya no se cierra al empezar si el juego estaba abierto**: ahora te dice que cierres el juego (el lanzador lo abre ya conectado). La línea de créditos de la pantalla de título tampoco puede tumbar la sesión si Windows no deja tocar el archivo.
- **«Acceso denegado» al empezar una sesión**: si los archivos del juego estaban marcados como de solo lectura (pasa al copiar o restaurar la carpeta del juego), el lanzador les quita esa marca antes de tocarlos. Si Windows sigue sin dejar, te explica qué revisar en vez de cerrar el servidor sin más.
- **Votación final**: el juego ya no se cierra cuando le llega dos veces la respuesta de un jugador (pasaba con Sherlock IA y Watson o Irene humanos).
- **Avisos de actualización**: ahora enseñan solo lo nuevo de cada versión, no todo el registro de cambios.
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
- **Leaving mid-match counts as a loss**: if someone closes the game, disconnects or surrenders, their side loses and the other one wins; the game shows the ending to everyone else. If the one who disappears is the host (closes the launcher or loses connection), the guests get the win recorded on their PC, as long as they still have internet.
- **Max. Turns**: the room settings have the original game's hidden option back, now from 1 to 99 turns (10 by default). Handy with custom scenarios and on big maps, where you need more time to explore.
- **Turn time**: now goes from **60 to 999 seconds** in any room (public rooms used to stop at 180), for anyone who wants to take it slow.
- **Custom cursor**: in the launcher, Mods → "Custom cursor": choose an image and it becomes the game's cursor (it's fitted to 32×32 and its background removed if it has no transparency). You can choose where it clicks (tip or centre), turn it on or off, and see which one you have. Only you see it and it needs the BepInEx plugin.
- **Controller: smoother cursor**: the left stick no longer moves the cursor in a "grid". The direction is exactly your thumb's (circles and fine diagonals work), with a round dead zone, and Windows mouse acceleration no longer bends it.
- **Controller: smoother camera**: the right stick moves the camera without stutter, in the stick's exact direction and faster the more you tilt it, just like the cursor. It eases in and out, and you can still change its speed (R3).
- **Guests' mods in the game**: when someone joins your room with their own stickers or avatars, the prompt to download them also shows up inside the game (before it was only in the launcher and went unnoticed). You can answer in either.
- **"Always accept" guests' mods**: from the prompt or in Mods → "Guests' mods", so they're added without asking every time.
- **Update notice with the launcher open**: it checks for a new version every half hour and, if there is one, a bell appears at the top. Click it to see what's new and update right away; if the game, a session or another launcher is open, it warns you and closes them first.
- **The server no longer closes on start if the game was already open**: it now tells you to close the game (the launcher opens it already connected). The credits line on the title screen can't bring the session down either if Windows won't let it touch the file.
- **"Access denied" when starting a session**: if the game's files were marked read-only (it happens when copying or restoring the game folder), the launcher clears that before touching them. If Windows still refuses, it tells you what to check instead of just closing the server.
- **Final vote**: the game no longer closes when it gets the same player's answer twice (it happened with an AI Sherlock and a human Watson or Irene).
- **Update notices**: they now show only what's new in each version, not the whole changelog.
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
