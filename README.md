<p align="center"><img src="assets/logo.png" width="220" alt="CRIMESIGHT Revival"></p>

<h1 align="center">CRIMESIGHT Revival</h1>

<p align="center"><b>Español</b> · <a href="README.en.md">English</a></p>

<p align="center">
Vuelve a jugar a CRIMESIGHT (Konami, 2022) después del cierre de sus servidores oficiales.<br>
Play CRIMESIGHT (Konami, 2022) again after its official servers shut down.
</p>

<p align="center">
<a href="https://github.com/Amras95/crimesight-revival/releases/latest"><b>⬇ Descargar / Download</b></a> ·
<a href="https://ko-fi.com/amrasmithandir95">☕ Ko-fi</a>
</p>


<p align="center">
<img src="assets/screenshots/launcher.jpg" width="820" alt="Lanzador">
</p>

<p align="center">
<img src="assets/screenshots/title.jpg" width="32%" alt="Pantalla de título">
<img src="assets/screenshots/lobby.jpg" width="32%" alt="Sala con IA">
<img src="assets/screenshots/gameplay.jpg" width="32%" alt="Partida">
</p>

---

> [!NOTE]
> **Probado y funcionando:** partidas en solitario contra la IA y partidas entre dos personas (anfitrión y
> amigo), también a través de Radmin VPN.
>
> **Mods de stickers y avatares:** probados en solitario, con y sin recarga en caliente. La descarga de los
> mods del anfitrión al unirse a su sala está probada en local, aún no entre dos personas.
>
> **Creador de escenarios:** probado en solitario. Compartir escenarios con la sala aún no está probado
> entre dos personas.
>
> **Modelos 3D, personajes nuevos y Selección de personajes:** probados en solitario. Compartirlos con la
> sala aún no está probado entre dos personas.
>
> **Linux / Steam Deck:** versión nueva, aún en pruebas.
>
> **Aún sin probar con personas:** partidas con **Watson** o **Irene** (3 o 4 jugadores) y el servidor propio
> en un VPS. Deberían funcionar, pero si encontráis cualquier problema, contádmelo en
> [Issues](https://github.com/Amras95/crimesight-revival/issues) y lo arreglo.

- Proyecto de la comunidad, no oficial y sin ánimo de lucro. No está relacionado con Konami.
- **Necesitas tener CRIMESIGHT en tu biblioteca de Steam.** Aquí no se incluye ningún archivo, clave ni
  imagen del juego: todo se lee de tu propia instalación.
- **Este proyecto solo publica la herramienta.** No gestiona ni aloja servidores: cada jugador o grupo de
  amigos monta el suyo. Si alguien monta uno, que no cobre por entrar.
- Todo se puede deshacer con el botón «Dejar el juego original».

## Cómo jugar (paso a paso)

1. Ten **CRIMESIGHT instalado** desde Steam y **Steam abierto** con tu cuenta.
2. Descarga **`CrimeSightRevival.exe`** desde [la última versión](https://github.com/Amras95/crimesight-revival/releases/latest).
3. Ábrelo. La primera vez tarda unos segundos en preparar las claves y las ilustraciones a partir de tu
   copia del juego. Si Windows SmartScreen avisa ("Windows protegió su PC"), pulsa *Más información* →
   *Ejecutar de todas formas*: pasa con cualquier programa nuevo sin firma de pago.
4. Elige cómo jugar:

   | Opción | Para qué |
   |---|---|
   | **Jugar solo** | Partidas contra la IA en tu PC. |
   | **Ser anfitrión** | Tus amigos se conectan a tu PC. El lanzador intenta abrir el puerto del router y te da la dirección para pasársela. |
   | **Unirme a un amigo** | Escribes la dirección que te pase tu amigo anfitrión. |
   | **Servidor propio** | Entras en un servidor que haya montado alguien, con contraseña si la tiene. |

5. Pulsa el botón y el juego se abre solo. Al cerrar el juego, termina la sesión.

Cuando se publica una versión nueva, el lanzador **te avisa al abrirlo**, te enseña las novedades y tú
decides si actualizas en ese momento o más tarde (queda un aviso junto al número de versión). Para jugar
con otras personas, lo mejor es que todos tengáis la misma versión. El lanzador se muestra en el idioma en
que tienes el juego (los 11 idiomas del juego).

### En la sala

- Los huecos libres se llenan con **IA** (`IA_1 (Normal)`…). **Expulsa a una IA** para abrir una ventana
  en la que eliges su dificultad (Fácil, Normal, Difícil, Experto o Pesadilla), la aplicas a todas las IA a
  la vez o dejas el hueco libre para un amigo. Sin la recarga en caliente, cada expulsión la pasa a la
  siguiente dificultad.
- Cuando entra un amigo, ocupa el sitio de una IA.
- El botón **Selección de personajes** (junto a «Manual online») elige qué personajes pueden salir en la
  partida: mira [Personajes nuevos y Selección de personajes](#personajes-nuevos-y-selección-de-personajes).

### Si tu amigo no puede entrar

Cuando eres anfitrión, tu router tiene que dejar pasar el puerto **18080 (TCP)**. El lanzador lo intenta
solo (UPnP); si tu router no lo permite:

- Ábrelo a mano en la configuración del router (reenviar el puerto 18080 TCP a la IP de tu PC), **o**
- Usad una red privada gratuita como **Radmin VPN** (la más sencilla), **Tailscale** o **ZeroTier**, y pásale a tu amigo la
  IP que te dé esa red (por ejemplo `100.64.1.2:18080`).

### Tu progreso

Tus partidas, victorias y puntos se guardan **en tu PC** (`%APPDATA%\CrimeSightRevival`), no en la carpeta
del juego: aunque lo desinstales o reinstales, no pierdes nada. Cuando juegas en el servidor de un amigo,
tu progreso se junta con el suyo al entrar y vuelve a tu PC al salir: nunca se duplica ni se pierde nada.

Con el botón **«Tu progreso»** del lanzador puedes:

- **Exportarlo / importarlo** en un archivo `.csrsave` para llevarlo a otro PC. Importar solo suma las
  partidas que falten, así que nunca duplica nada.
- Activar la **copia automática** en una carpeta de OneDrive, Google Drive o Dropbox: se guarda una copia
  al terminar cada sesión y, en otro PC, tu progreso vuelve solo al elegir la misma carpeta.

Steam Cloud no se usa porque el espacio en la nube de cada juego lo controla su editora.

## Mods: tus propios stickers y avatares

Añade stickers y avatares tuyos. **Son huecos nuevos**: los del juego (también los de pago, que siguen
dependiendo de tenerlos en Steam) no se tocan nunca.

1. En el lanzador, pulsa **Mods → Abrir carpeta de mods** (`%APPDATA%\CrimeSightRevival\mods`). Viene
   preparada con sus carpetas y un `README.txt`.
2. Mete tus imágenes (PNG, JPG, WEBP…) en `stamps\` y/o `avatars\`. Las de varios packs pueden ir en
   las mismas carpetas.
3. Juega. El lanzador las mete en el juego antes de abrirlo.

```
mods\
  stamps\          01_saludo.png, ¡Buenas noches!.png…
  avatars\         yo.png
  mod.json         el nombre y el autor que se muestran para tus mods, y los mensajes de tus stickers
  models\          tus modelos 3D, esqueletos, animaciones e imágenes
  cursor\          tu cursor propio
  stages\          los escenarios que guardas en el Creador de escenarios
```

- **Cualquier imagen sirve.** Se ajustan solas al tamaño del juego (stickers de 128×128 con su borde blanco;
  avatares de 256×256 colocados como los originales). Una **lámina con muchos stickers** en cuadrícula se
  separa sola, y si la imagen no tiene transparencia se le quita el fondo. Los avatares que llegan hasta los
  bordes (un busto cortado, una foto) van en un círculo para que encajen en todos los marcos.
- **El mensaje del sticker** (lo que sale en el registro: «Amras: ¡Buenas noches!») es el nombre del archivo;
  un número delante (`01_`) solo sirve para ordenar. Para usar signos que Windows no deja en los nombres
  (`? : " *`), escríbelo en **Mods → Mensajes**. Se guarda en `mod.json`.
- **Equivale a…:** elige para cada sticker a qué sticker del juego equivale, para que las IA puedan
  contestarle. Si lo dejas vacío, no contestan.
- **Activa o desactiva tus mods** desde la ventana de Mods.
- **En la sala de otro jugador**, antes de entrar sale un aviso con sus mods: **Descargar y unirme** o
  **No unirme**. Se descargan como temporales (`<id>+temp`), tus mods quedan en pausa durante la partida y
  al salir se borran los temporales y vuelven los tuyos. Si la sala no tiene mods, se entra sin ninguno:
  todos los jugadores tienen que tener exactamente la misma lista. Si entras con mods tuyos, se le ofrecen
  al anfitrión, que puede aceptarlos (o elegir **Aceptar siempre**); entonces los ve toda la sala.
- Lo que tengas puesto en la rueda de stickers y el avatar elegido **se conservan** aunque añadas imágenes,
  cambies mensajes o se actualice el lanzador. Solo se quita un sticker si borras o renombras su imagen (el
  juego pone «Hola» en su hueco).

### Recarga en caliente (con BepInEx, activada por defecto)

Los cambios de mods aparecen **con el juego abierto**, sin reiniciarlo. BepInEx es también lo que hace
funcionar el cursor propio, los modelos 3D, los personajes nuevos, los escenarios personalizados, el mando y
los extras dentro del juego (Selección de personajes, Guía Revival, Créditos Revival):

- Al abrirse, el lanzador descarga [BepInEx](https://github.com/BepInEx/BepInEx) (un cargador de mods para
  juegos de Unity, 34 MB) **de su GitHub**: no viene incluido. Lo instala en la carpeta del juego junto
  al plugin del proyecto. El primer arranque tarda un minuto mientras BepInEx se prepara. Si la descarga
  falla, puedes jugar igualmente sin él y el lanzador lo vuelve a intentar la próxima vez.
- Mientras juegas, el lanzador vigila tu carpeta de mods: si añades una imagen, cambias un mensaje o
  activas/desactivas un mod, aparece en el juego en unos segundos. Si eres anfitrión, también le llega a tu
  sala; si estás en la sala de otro, recibes sus cambios.
- Los cambios nunca se aplican a mitad de partida (se esperan al menú), para que todos tengan la misma lista.
- **Mods → General → Quitar BepInEx** (o «Dejar el juego original») lo borra todo y el juego vuelve
  a estar como siempre. Si lo quitas, el lanzador no lo vuelve a instalar hasta que pulses **Activar**.

## Modelos 3D

Pon a los personajes tus propios modelos 3D y animaciones, desde **Mods → Modelos**. Necesitan la recarga
en caliente.

- Mete archivos `.fbx` o `.glb` (o una subcarpeta con un modelo y sus texturas) en `mods\models\` y elige a
  qué personaje sustituye cada uno. Los modelos humanoides (Mixamo, VRChat/Unity, VRoid, Blender, DAZ,
  MMD…) se ajustan solos al personaje, y en ellos se ven las animaciones del juego.
- **Tus propias animaciones:** sustituye el reposo, el andar o el correr de cualquier personaje por una
  animación `.fbx` o `.glb` (por ejemplo de Mixamo). Funciona con los modelos del juego y con los tuyos.
- Para un ajuste perfecto, el lanzador saca un esqueleto por personaje de tu copia del juego. El
  `README.txt` de la carpeta de modelos explica cómo usarlo en Blender.
- **Se comparten con la sala:** en tu sala todos ven tus modelos. Si entras en la sala de otro con los
  tuyos, se le ofrecen al anfitrión; si acepta, todos los ven en los personajes que el anfitrión no haya
  cambiado. Los modelos descargados son temporales y se borran al cerrarse la sala.

## Personajes nuevos y Selección de personajes

Un modelo también puede ser un **personaje nuevo** (**Mods → Modelos → Personajes nuevos**) en vez de
sustituir a uno:

- Entra en el sorteo de cada partida: en cada partida salen 6 de los personajes activados, y los
  originales y los nuevos tienen la misma probabilidad.
- Ponle un nombre, una imagen para los retratos, sus propias frases para cada situación, y las animaciones
  de cualquier personaje del juego (**Animaciones de**) o las tuyas. Sin nombre o sin frases, usa los del
  personaje cuyo sitio ocupa; sin imagen, se hace un retrato a partir de su modelo. Siempre juega como el
  personaje cuyo sitio ocupa.
- En la sala de espera del juego, el botón **Selección de personajes** enseña a todos los personajes con
  su retrato, su nombre y su modelo 3D girando, y el anfitrión marca quién puede salir (mínimo 6). Se
  guarda para la próxima vez; los demás jugadores pueden verlo, pero no cambiarlo.
- Los personajes nuevos se comparten con la sala igual que los modelos.
- Los personajes de tipo **Traidor** todavía no salen en las partidas.

## Cursor propio

**Mods → Cursor propio → Elegir imagen…** convierte cualquier imagen en el cursor del ratón del juego;
luego eliges su punto de clic (punta o centro). Solo lo ves tú, y necesita la recarga en caliente.

## Creador de escenarios

**Mods → Creador de escenarios** te deja recolocar las habitaciones de un escenario del juego y guardarlo
como uno nuevo. Los escenarios originales no se tocan. Para jugarlos hace falta la recarga en caliente.

- Mueve, gira, quita o repite habitaciones; cambia puertas por muebles o pasadizos; elige por qué ventanas
  entran los perros salvajes, dónde hay gas y dónde empiezan los personajes. El creador avisa de lo que
  impediría jugar el escenario, y «Prueba rápida» te deja verlo en el juego sin guardarlo.
- Cada escenario guardado aparece en la lista de escenarios del juego con su nombre. Puedes guardar los que
  quieras y tener hasta 20 activados a la vez; los desactivados conservan su diseño.
- **Exportar / Importar** los comparte como archivos `.csrstage`. Solo llevan la distribución de las
  habitaciones: nada del juego.
- En una sala, todos se bajan los escenarios del anfitrión al unirse. Con un escenario personalizado elegido,
  la partida no puede empezar hasta que todos lo tienen: el nombre de quien falta lo indica («cargando
  escenario…», o «sin el escenario» si no tiene la recarga en caliente).
- El creador lee las habitaciones de **tu** copia del juego; el proyecto no incluye ninguna.

## Qué funciona

- Inicio de sesión, perfil, tutorial, ajustes y nivel.
- Salas de 2 a 4 jugadores mezclando personas e IA (probado con 2 personas; con Watson/Irene humanos,
  **pendiente de probar**). IA para los cuatro papeles (Sherlock, Moriarty, Watson e Irene), con cinco
  dificultades, de Fácil a Pesadilla.
- Partidas completas: objetos, perros salvajes, escapes de gas, la orden Atacar, turno final, asesinato,
  detención y deducción final, con la cinemática correcta para cada bando.
- Victorias, empates, derrotas y puntos. Ganar da 200 contra la IA Fácil, 400 en Normal, 800 en Difícil,
  1000 en Experto, 1200 en Pesadilla y 1000 contra otras personas; empatar o perder, la mitad; abandonar, 0.
- Extras por acciones, cada uno una vez por partida:
  - **Bando de Sherlock:** acertar quién es el asesino (+100, con Sherlock o con Watson), gas lacrimógeno al
    asesino (+100), arreglar la caja de fusibles (+50), encontrar una caja de fusibles (+50, y +50 más si es
    antes que Moriarty), encontrar comida (+50) y descartar a alguien como asesino o como objetivo (+50
    cada uno).
  - **Bando de Moriarty:** dejar en estado crítico a alguien que no es el asesino (+100), matar con la orden
    Atacar (+50), provocar el apagón (+50), gasear a alguien (+50), imponerse a una orden de Sherlock (+50, y
    +50 más por volver a hacerlo sobre el mismo personaje), encontrar una caja de fusibles antes que
    Sherlock (+50), curar al asesino (+50), y que un perro salvaje o un escape de gas hiera a alguien que no
    es el asesino (+50 cada uno).
  - **Cualquier bando:** curar a alguien (+50), usar un pasadizo secreto (+50), arreglar un escape de gas
    (+50) y acabar con un perro salvaje o un traidor (+50).
- Recompensas por puntos y nivel como en el original. El evento Project Winter queda abierto con su
  avatar desbloqueado. El contenido Deluxe sigue dependiendo de tenerlo en Steam.
- Los logros de Steam se siguen consiguiendo (los gestiona el propio juego con Steam).
- Mods de stickers y avatares nuevos, compartidos con la sala, con recarga en caliente.
- Modelos 3D, animaciones propias, personajes nuevos y Selección de personajes, compartidos con la sala.
- Cursor propio.
- Creador de escenarios, con escenarios compartidos con la sala.
- Las IA a menudo contestan a tus stickers; con los tuyos propios, se guían por lo que elijas en
  **Equivale a…**.
- Sherlock y Watson ven el icono del otro en la lista de jugadores, y Watson IA señala cada sitio nuevo con
  comida que descubre.
- Dentro del juego: una **Guía Revival** (en el menú Jugar) que explica lo que añade Revival, y los
  **Créditos Revival** (en la ventana de Opciones).
- Controles con mando (Xbox, PlayStation, Switch, Steam Deck), con la recarga en caliente activada. Los
  botones están en la [wiki](https://github.com/Amras95/crimesight-revival/wiki/Mando).

## Plataformas

CRIMESIGHT solo salió para **Windows 10/11 (64 bits)**. En Mac no hay versión del juego.

### Linux / Steam Deck (en pruebas)

El juego funciona con **Proton**, y hay versión del lanzador para Linux: **`CrimeSightRevival-linux`** en
[la última versión](https://github.com/Amras95/crimesight-revival/releases/latest).

1. Descárgalo, dale permiso de ejecución (clic derecho → Propiedades → «Es ejecutable», o
   `chmod +x CrimeSightRevival-linux`) y ábrelo. En Steam Deck, desde el **modo escritorio**.
2. La interfaz se abre en tu **navegador** (es la misma que en Windows). Mientras la pestaña esté abierta,
   el lanzador sigue funcionando; si la cierras sin ninguna partida en marcha, se cierra solo.
3. Encuentra Steam y el juego solo (Steam normal, Flatpak o Snap) y abre el juego por Steam con Proton.

Los mods funcionan igual. Para la **recarga en caliente** (BepInEx), además hay que poner esto en las
**opciones de lanzamiento** de CRIMESIGHT en Steam (Propiedades → General); el lanzador te avisa si falta:

```
WINEDLLOVERRIDES="winhttp=n,b" %command%
```

## Montar un servidor (por ejemplo, en un VPS)

1. En tu PC, con el juego instalado: `python tools/extract_keys.py "<carpeta del juego>"`. Crea
   `server/keys.json` con las claves de **tu** copia. Súbelo al servidor junto con la carpeta `server/`.
2. En el servidor (Python 3.10+): `pip install aiohttp pycryptodome` y
   `python server.py --password UNA_CONTRASEÑA` (puerto 18080; ábrelo en el cortafuegos).
3. Los jugadores usan «Servidor propio» con `IP_O_DOMINIO:18080` y la contraseña.
4. Opcional: `--mods-dir CARPETA` ofrece a los jugadores los mods de esa carpeta (misma estructura que la
   carpeta de mods del lanzador; necesita `pip install pillow`).
5. Opcional: `--stages-dir CARPETA` ofrece a los jugadores los escenarios del creador que haya en esa
   carpeta (los `.json` de `%APPDATA%\CrimeSightRevival\mods\stages`).

La contraseña protege la sincronización de perfiles: el juego solo se identifica con su ID de Steam,
así que un servidor sin contraseña permitiría a cualquiera hacerse pasar por otro jugador.

## Para desarrolladores

- `4_lanzador.bat`: abre el lanzador con Python, sin compilar.
- `crear_exe.bat`: crea `dist\CrimeSightRevival.exe` (versión de desarrollo, no se actualiza sola).
- `CHANGELOG.md`: novedades de cada versión. Su primer bloque es lo que el lanzador enseña al ofrecer una
  actualización, si el archivo cambia en la subida; si no, enseña el mensaje del commit.
- `plugin/`: código del plugin opcional de BepInEx y su `.dll` ya compilado. Se compila contra los ensamblados
  que genera BepInEx 6 (IL2CPP) en `BepInEx\interop` al arrancar el juego por primera vez; no se incluye
  ningún archivo del juego.
- Cada vez que se sube algo a `main`, GitHub Actions compila el `.exe` en Windows y publica una release
  (`.github/workflows/release.yml`). Los lanzadores instalados la descargan, comprueban su huella
  SHA-256 y se sustituyen solos.
- Scripts sin lanzador: `1_preparar.bat` (dependencias, claves y redirección), `2_servidor.bat` y
  `3_restaurar_juego_original.bat`.

### Cómo funciona por dentro

Unity 2020.3 con IL2CPP. La dirección del servidor (`https://cott-game.cs.konami.net`) se cambia en
`global-metadata.dat`. El tráfico va cifrado con AES-256-CBC; las claves están en `resources.assets` del
propio juego. La API es `POST /cott/api/index.php` y las partidas van por WebSocket con WAMP v2: el
servidor marca las fases del turno, reparte objetos y decide peligros y asesinatos; la simulación visual
va en el cliente. Extras del servidor comunitario: `POST /revival/sync` (perfiles), `GET /revival/info` y
`GET /revival/mods` (paquete de mods de la sala).

**Mods (`server/modpack.py`, `server/modimage.py`, `launcher/modinject.py`):**

- Los stickers son `StampData` en `resources.assets`; los gratuitos están en el `StampSet` 0. El juego los
  identifica por `tipo | cara` y en red manda la **posición** en la lista (`setIndex`, `dataIndex`), así que
  todos los jugadores de la sala necesitan la misma lista en el mismo orden. Cada sticker nuevo recibe un tipo
  de 1000 a 4095 (el juego usa 0-38) calculado a partir de la carpeta del mod y el nombre del archivo, de modo
  que es estable y el orden (el juego ordena por tipo) sale igual en todos los PCs.
- Los avatares son `CursorAvatarData` en `sharedassets3.assets`, listados por los `CursorAvatarSet` de las
  escenas `level3` (menú) y `level4` (partida); en red viajan por su nombre (`Icon_CSR_<hash>`).
- **Sin BepInEx**, `modinject.py` reconstruye esos archivos con UnityPy partiendo siempre de los originales
  (`*.original`): clona un `StampData`/`CursorAvatarData` de plantilla, añade textura RGBA32 incrustada y
  sprite de 4 vértices, y los añade al final de las listas. Los mensajes se añaden al texto del juego
  (`ctg_name`, en los 11 idiomas). Si la rueda o el avatar guardados (PlayerPrefs) apuntan a un mod que ya no
  está, se cambian por uno del juego.
- **Con BepInEx**, los archivos del juego se quedan originales: el lanzador escribe el conjunto de la sala en
  `BepInEx\csr_live\live.json` (en la carpeta del juego) y el plugin (`plugin/CrimeSightRevivalMods.cs`) crea los
  objetos en memoria (`Texture2D` + `Sprite.Create` + `ScriptableObject.CreateInstance`), los mete en las
  listas del juego y añade los textos a `TextManager.LangText`. Comprueba cada segundo y lo reaplica tras cada
  cambio de escena.
- Por la red viaja un zip interno con las imágenes ya ajustadas y validadas (tamaño, nombres, formato): el
  jugador nunca comprime nada.

## Licencia

[GPL-3.0](LICENSE) con [términos adicionales](ADDITIONAL_TERMS.md) (sección 7): hay que mantener la
atribución al autor y las versiones modificadas deben indicar que lo son y no hacerse pasar por la
original.

## Créditos

CRIMESIGHT Revival por **Amras95** · [GitHub](https://github.com/Amras95) · [X](https://x.com/AmrasMithandir) ·
[Ko-fi](https://ko-fi.com/amrasmithandir95)

Contribuciones de **Ashen** · [GitHub](https://github.com/AshenAF92)

El icono del lanzador es un diseño propio del proyecto. CRIMESIGHT es una marca de Konami Digital
Entertainment; este proyecto no está afiliado ni avalado por Konami.

## Aviso

Proyecto de preservación para quienes compraron el juego. Si Konami pide retirarlo, se retirará.
