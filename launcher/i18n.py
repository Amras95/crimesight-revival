"""
Launcher texts in the game's 11 languages.

The language is taken from the game: the one it had set the last time it connected to a
Revival server and, otherwise, the language it is installed with on Steam. Without a localised game: English.
"""
import re

LANGS = ("en", "es", "ja", "fr", "it", "de", "pt", "ru", "zh-CN", "zh-TW", "ko")
# Codes the game sends when logging in (ConfigSystem.LangType)
GAME_CODES = {"JP": "ja", "JA": "ja", "EN": "en", "FR": "fr", "IT": "it", "DE": "de", "ES": "es",
              "PT": "pt", "RU": "ru", "KO": "ko", "KR": "ko", "CN": "zh-CN", "TW": "zh-TW"}
# Steam languages (appmanifest / client settings)
STEAM_CODES = {"english": "en", "spanish": "es", "latam": "es", "japanese": "ja", "french": "fr",
               "italian": "it", "german": "de", "brazilian": "pt", "portuguese": "pt", "russian": "ru",
               "koreana": "ko", "korean": "ko", "schinese": "zh-CN", "tchinese": "zh-TW"}

S = {}


def _add(lang, **kw):
    S[lang] = kw


_add("en",
     progress_btn='Your progress', progress_title='Your progress', progress_desc="Your matches, wins and points are saved on this PC. You can move them to another PC or keep a backup so you never lose them.", export_btn='Export to a file', import_btn='Import a file', backup_label='Automatic backup', backup_off='Off', backup_pick='Choose folder', backup_remove='Turn off', backup_hint="Tip: pick your OneDrive, Google Drive or Dropbox folder. A copy is saved after every session, and on another PC your progress is restored automatically when you pick the same folder.", close='Close', exported='Progress saved to {path}', imported='Done: {n} new matches added to your progress.', import_nothing="That file had no matches you didn't already have.", err_save_bad="That file isn't a CRIMESIGHT Revival progress file.", err_save_other='That file belongs to another Steam account.', err_save_write="Couldn't save the file ({err}).", backup_set='Automatic backup turned on.', backup_removed='Automatic backup turned off.', backup_restored="Progress restored from your backup: {n} new matches.", backup_saved='Progress backed up.', backup_failed="Couldn't make the backup ({err}).", err_backup_missing='Backup folder not found: {path}',
     updating='Updating the launcher to version {v}…', update_failed="Couldn't update ({err}). Using the current version for now.", kofi='Support me on Ko-fi',
     loading="Preparing the launcher…",
     tagline="Community server for people who already own the game · no Konami files included",
     steam_account="Steam account", no_steam="Open Steam and sign in",
     wins="Wins", draws="Draws", losses="Losses", points="Points",
     solo_title="Play solo", solo_desc="Play against the AI on your PC. Kick an AI from the room to change its difficulty.",
     host_title="Host a game", host_desc="Open your game to your friends. I'll give you the address they need to join.",
     join_title="Join a friend", join_desc="Connect to a friend's game. Your progress carries over.",
     server_title="Custom server", server_desc="Join a server someone has set up, using its password if it has one.",
     solo_hint="A server starts on your PC and the game opens. Create a room and the empty seats are filled with AIs. Kick an AI to change its difficulty.",
     play_btn="PLAY", port="Port",
     host_hint="I'll try to open your router's port automatically. If your friend can't connect, open it manually or use Tailscale, ZeroTier or Radmin VPN.",
     host_btn="OPEN GAME", friend_addr="Your friend's address", friend_ph="e.g. 83.45.120.7:18080", join_btn="JOIN",
     saved="Saved", name="Name", address="Address", server_ph="server.example.com:18080", password="Password",
     save="Save", delete="Delete", connect_btn="CONNECT",
     session_running="Session running", copy="Copy", stop_session="End session",
     game_path="Game: {path}", no_game="CRIMESIGHT not found: choose CrimeSight.exe",
     change_folder="Change game executable", restore_game="Restore original game", revival_by="Revival by", contributions_by="Contributions by",
     copied="Address copied", server_saved="Server saved",
     title_solo="Solo game", title_host="Game open to friends", title_join="Connected to your friend",
     title_server="Connected to the server",
     err_busy="A session is already running.", err_no_game="Choose the game executable first.",
     err_no_steam="Open Steam and sign in with the account that owns CRIMESIGHT.", err_no_address="Enter the address.",
     stopping="Ending the session…", err_unexpected="Unexpected error: {err}",
     err_bad_folder="That file doesn't look like CRIMESIGHT's executable (CrimeSight.exe).",
     err_finish_first="End the session first.", restored="Game restored to its original state.",
     already_original="The game was already in its original state.", err_need_address="The address is required.",
     loading_art="Preparing the artwork from your copy of the game (first time only)…",
     notice_imported="Your matches from the previous version have been imported.",
     srv_local_on="Local server running.", pointing="Connecting the game to {url}",
     opening="Opening CRIMESIGHT…", srv_stopped="Server stopped. See you next time!",
     host_upnp="Server started. Trying to open the port on your router (UPnP)…", port_opened="Port {port} is open on your router.",
     port_failed="Your router didn't let me open port {port} automatically. Open it manually (forward TCP to this PC), or use a private network (Tailscale, ZeroTier or Radmin VPN) and share that network's IP.",
     give_address="Give your friend this address: {addr}   (on the same home network: {lan})",
     host_closed="Your game is no longer open to friends, and the server has stopped.", checking="Checking {url}…",
     need_password="That server needs a password: use “Custom server”.", syncing="Syncing your progress with the server…",
     record="Your record: {w}W {d}D {l}L · {p} points", fetching="Downloading your new matches…",
     sync_later="Couldn't download them right now ({err}). They'll be added next time you connect.",
     game_not_seen="The game didn't seem to open. You can also start it yourself from Steam.",
     game_open="The game is running. Close it to end the session.",
     err_empty_addr="Enter an address.", err_not_revival="Something is answering at that address, but it isn't a CRIMESIGHT Revival server.",
     err_unreachable="Can't reach {url} ({reason}). Is the server running and the port open?",
     err_password="Wrong password for that server.", err_sync_rejected="The server rejected the sync ({code}).",
     err_sync_failed="Couldn't sync with {url} ({reason}).",
     ev_start="Match started", ev_win="{name} wins (+{pts} points)", ev_lose="{name} loses (+{pts} points)",
     ev_draw="{name} draws (+{pts} points)", ev_quit="{name} left the match", ev_kill="The victim has been killed",
     ev_arrest="Final turn over: the villain has been arrested", ev_threat="A threat appears",
     ev_gas="A gas leak appears", ev_synced="Profile synced")

_add("es",
     progress_btn='Tu progreso', progress_title='Tu progreso', progress_desc='Tus partidas, victorias y puntos se guardan en este PC. Puedes llevártelos a otro PC o guardar una copia para no perderlos nunca.', export_btn='Exportar a un archivo', import_btn='Importar un archivo', backup_label='Copia automática', backup_off='Desactivada', backup_pick='Elegir carpeta', backup_remove='Desactivar', backup_hint='Consejo: elige tu carpeta de OneDrive, Google Drive o Dropbox. Se guarda una copia al terminar cada sesión, y en otro PC tu progreso vuelve solo al elegir la misma carpeta.', close='Cerrar', exported='Progreso guardado en {path}', imported='Hecho: {n} partidas nuevas añadidas a tu progreso.', import_nothing='Ese archivo no tenía partidas que no tuvieras ya.', err_save_bad='Ese archivo no es un progreso de CRIMESIGHT Revival.', err_save_other='Ese archivo es de otra cuenta de Steam.', err_save_write='No se pudo guardar el archivo ({err}).', backup_set='Copia automática activada.', backup_removed='Copia automática desactivada.', backup_restored='Progreso recuperado de tu copia: {n} partidas nuevas.', backup_saved='Copia del progreso guardada.', backup_failed='No se pudo hacer la copia ({err}).', err_backup_missing='No encuentro la carpeta de copia: {path}',
     updating='Actualizando el lanzador a la versión {v}…', update_failed='No se pudo actualizar ({err}); sigo con la versión actual.', kofi='Apóyame en Ko-fi',
     loading="Preparando el lanzador…",
     tagline="Servidor comunitario para quien ya tiene el juego · sin archivos de Konami",
     steam_account="Cuenta de Steam", no_steam="Abre Steam e inicia sesión",
     wins="Victorias", draws="Empates", losses="Derrotas", points="Puntos",
     solo_title="Jugar solo", solo_desc="Partidas contra la IA en tu PC. Expulsa a una IA de la sala para cambiar su dificultad.",
     host_title="Ser anfitrión", host_desc="Abre tu partida a tus amigos. Te doy la dirección para que se unan.",
     join_title="Unirme a un amigo", join_desc="Conéctate a la partida de un amigo. Tu progreso viene contigo.",
     server_title="Servidor propio", server_desc="Entra en un servidor montado por alguien, con contraseña si la tiene.",
     solo_hint="Se arranca un servidor en tu PC y se abre el juego. Crea una sala: los huecos libres los ocupan IAs. Expulsa a una IA para cambiar su dificultad.",
     play_btn="JUGAR", port="Puerto",
     host_hint="Intentaré abrir el puerto del router yo solo. Si tu amigo no puede entrar, ábrelo a mano o usad Tailscale, ZeroTier o Radmin VPN.",
     host_btn="ABRIR PARTIDA", friend_addr="Dirección de tu amigo", friend_ph="por ejemplo 83.45.120.7:18080", join_btn="UNIRME",
     saved="Guardados", name="Nombre", address="Dirección", server_ph="servidor.ejemplo.com:18080", password="Contraseña",
     save="Guardar", delete="Borrar", connect_btn="CONECTAR",
     session_running="Sesión en marcha", copy="Copiar", stop_session="Terminar sesión",
     game_path="Juego: {path}", no_game="No encuentro CRIMESIGHT: elige CrimeSight.exe",
     change_folder="Cambiar ejecutable del juego", restore_game="Dejar el juego original", revival_by="Revival por", contributions_by="Contribuciones de",
     copied="Dirección copiada", server_saved="Servidor guardado",
     title_solo="Partida en solitario", title_host="Partida abierta para amigos", title_join="Conectado a tu amigo",
     title_server="Conectado al servidor",
     err_busy="Ya hay una sesión en marcha.", err_no_game="Primero elige el ejecutable del juego.",
     err_no_steam="Abre Steam e inicia sesión con la cuenta que tiene CRIMESIGHT.", err_no_address="Escribe la dirección.",
     stopping="Terminando la sesión…", err_unexpected="Error inesperado: {err}",
     err_bad_folder="Ese archivo no parece el ejecutable de CRIMESIGHT (CrimeSight.exe).",
     err_finish_first="Termina antes la sesión.", restored="Juego devuelto a su estado original.",
     already_original="El juego ya estaba en su estado original.", err_need_address="Pon al menos la dirección.",
     loading_art="Preparando las ilustraciones desde tu copia del juego (solo la primera vez)…",
     notice_imported="He traído tus partidas de la versión anterior.",
     srv_local_on="Servidor local en marcha.", pointing="Apuntando el juego a {url}",
     opening="Abriendo CRIMESIGHT…", srv_stopped="Servidor parado. ¡Hasta la próxima!",
     host_upnp="Servidor abierto. Intentando abrir el puerto en el router (UPnP)…", port_opened="Puerto {port} abierto en el router.",
     port_failed="El router no ha dejado abrir el puerto {port} automáticamente. Ábrelo a mano (reenviar TCP a este PC) o usad una red privada (Tailscale, ZeroTier o Radmin VPN) y pasa la IP de esa red.",
     give_address="Pásale a tu amigo esta dirección: {addr}   (en tu misma casa: {lan})",
     host_closed="Partida cerrada para amigos y servidor parado.", checking="Comprobando {url}…",
     need_password="Ese servidor pide contraseña: usa «Servidor propio».", syncing="Sincronizando tu progreso con el servidor…",
     record="Tu registro: {w}V {d}E {l}D · {p} puntos", fetching="Trayendo tus partidas nuevas…",
     sync_later="No pude traer las partidas ahora ({err}). Se juntarán la próxima vez que te conectes.",
     game_not_seen="No he visto abrirse el juego; si lo abres tú desde Steam también vale.",
     game_open="El juego está abierto. Ciérralo para terminar la sesión.",
     err_empty_addr="Escribe una dirección.", err_not_revival="Ahí responde algo, pero no es un servidor de CRIMESIGHT Revival.",
     err_unreachable="No llego a {url} ({reason}). ¿Está el servidor encendido y el puerto abierto?",
     err_password="Contraseña incorrecta para ese servidor.", err_sync_rejected="El servidor rechazó la sincronización ({code}).",
     err_sync_failed="No pude sincronizar con {url} ({reason}).",
     ev_start="Empieza la partida", ev_win="{name} gana (+{pts} puntos)", ev_lose="{name} pierde (+{pts} puntos)",
     ev_draw="{name} empata (+{pts} puntos)", ev_quit="{name} abandona la partida", ev_kill="La víctima ha muerto",
     ev_arrest="Fin del turno final: el asesino ha sido detenido", ev_threat="Aparece una amenaza",
     ev_gas="Aparece un escape de gas", ev_synced="Perfil sincronizado")

_add("fr",
     progress_btn='Ta progression', progress_title='Ta progression', progress_desc='Tes parties, victoires et points sont enregistrés sur ce PC. Tu peux les emporter sur un autre PC ou garder une copie pour ne jamais les perdre.', export_btn='Exporter dans un fichier', import_btn='Importer un fichier', backup_label='Sauvegarde automatique', backup_off='Désactivée', backup_pick='Choisir un dossier', backup_remove='Désactiver', backup_hint='Astuce : choisis ton dossier OneDrive, Google Drive ou Dropbox. Une copie est faite après chaque session, et sur un autre PC ta progression revient toute seule en choisissant le même dossier.', close='Fermer', exported='Progression enregistrée dans {path}', imported='Terminé : {n} nouvelles parties ajoutées à ta progression.', import_nothing="Ce fichier ne contenait aucune partie que tu n'avais pas déjà.", err_save_bad="Ce fichier n'est pas une progression CRIMESIGHT Revival.", err_save_other='Ce fichier appartient à un autre compte Steam.', err_save_write="Impossible d'enregistrer le fichier ({err}).", backup_set='Sauvegarde automatique activée.', backup_removed='Sauvegarde automatique désactivée.', backup_restored='Progression récupérée depuis ta sauvegarde : {n} nouvelles parties.', backup_saved='Progression sauvegardée.', backup_failed='Impossible de faire la sauvegarde ({err}).', err_backup_missing='Dossier de sauvegarde introuvable : {path}',
     updating='Mise à jour du lanceur vers la version {v}…', update_failed='Mise à jour impossible ({err}) ; la version actuelle est conservée.', kofi='Soutenez-moi sur Ko-fi',
     loading="Préparation du lanceur…",
     tagline="Serveur communautaire pour ceux qui possèdent déjà le jeu · aucun fichier de Konami",
     steam_account="Compte Steam", no_steam="Ouvrez Steam et connectez-vous",
     wins="Victoires", draws="Égalités", losses="Défaites", points="Points",
     solo_title="Jouer en solo", solo_desc="Des parties contre l'IA sur votre PC. Expulsez une IA du salon pour changer sa difficulté.",
     host_title="Héberger", host_desc="Ouvrez votre partie à vos amis. Je vous donne l'adresse pour qu'ils vous rejoignent.",
     join_title="Rejoindre un ami", join_desc="Connectez-vous à la partie d'un ami. Votre progression vous suit.",
     server_title="Serveur privé", server_desc="Rejoignez un serveur installé par quelqu'un, avec mot de passe s'il en a un.",
     solo_hint="Un serveur démarre sur votre PC et le jeu s'ouvre. Créez un salon : les places libres sont occupées par des IA. Expulsez une IA pour changer sa difficulté.",
     play_btn="JOUER", port="Port",
     host_hint="J'essaierai d'ouvrir le port de votre routeur automatiquement. Si votre ami ne peut pas entrer, ouvrez-le à la main ou utilisez Tailscale, ZeroTier ou Radmin VPN.",
     host_btn="OUVRIR LA PARTIE", friend_addr="Adresse de votre ami", friend_ph="ex. 83.45.120.7:18080", join_btn="REJOINDRE",
     saved="Enregistrés", name="Nom", address="Adresse", server_ph="serveur.exemple.com:18080", password="Mot de passe",
     save="Enregistrer", delete="Supprimer", connect_btn="SE CONNECTER",
     session_running="Session en cours", copy="Copier", stop_session="Terminer la session",
     game_path="Jeu : {path}", no_game="CRIMESIGHT introuvable : choisissez CrimeSight.exe",
     change_folder="Changer l'exécutable du jeu", restore_game="Restaurer le jeu d'origine", revival_by="Revival par", contributions_by="Contributions de",
     copied="Adresse copiée", server_saved="Serveur enregistré",
     title_solo="Partie en solo", title_host="Partie ouverte aux amis", title_join="Connecté à votre ami",
     title_server="Connecté au serveur",
     err_busy="Une session est déjà en cours.", err_no_game="Choisissez d'abord l'exécutable du jeu.",
     err_no_steam="Ouvrez Steam et connectez-vous avec le compte qui possède CRIMESIGHT.", err_no_address="Saisissez l'adresse.",
     stopping="Fin de la session…", err_unexpected="Erreur inattendue : {err}",
     err_bad_folder="Ce fichier ne semble pas être l'exécutable de CRIMESIGHT (CrimeSight.exe).",
     err_finish_first="Terminez d'abord la session.", restored="Jeu restauré à son état d'origine.",
     already_original="Le jeu était déjà dans son état d'origine.", err_need_address="Saisissez au moins l'adresse.",
     loading_art="Préparation des illustrations à partir de votre copie du jeu (première fois seulement)…",
     notice_imported="Vos parties de la version précédente ont été importées.",
     srv_local_on="Serveur local démarré.", pointing="Redirection du jeu vers {url}",
     opening="Ouverture de CRIMESIGHT…", srv_stopped="Serveur arrêté. À la prochaine !",
     host_upnp="Serveur ouvert. Tentative d'ouverture du port du routeur (UPnP)…", port_opened="Port {port} ouvert sur le routeur.",
     port_failed="Le routeur n'a pas permis d'ouvrir le port {port} automatiquement. Ouvrez-le à la main (redirection TCP vers ce PC) ou utilisez un réseau privé (Tailscale, ZeroTier ou Radmin VPN) et partagez l'IP de ce réseau.",
     give_address="Donnez cette adresse à votre ami : {addr}   (même réseau domestique : {lan})",
     host_closed="Partie fermée aux amis et serveur arrêté.", checking="Vérification de {url}…",
     need_password="Ce serveur demande un mot de passe : utilisez « Serveur privé ».", syncing="Synchronisation de votre progression avec le serveur…",
     record="Votre bilan : {w}V {d}N {l}D · {p} points", fetching="Récupération de vos nouvelles parties…",
     sync_later="Impossible de les récupérer maintenant ({err}). Elles seront fusionnées à votre prochaine connexion.",
     game_not_seen="Je n'ai pas vu le jeu s'ouvrir ; le lancer vous-même depuis Steam fonctionne aussi.",
     game_open="Le jeu est lancé. Fermez-le pour terminer la session.",
     err_empty_addr="Saisissez une adresse.", err_not_revival="Quelque chose répond, mais ce n'est pas un serveur CRIMESIGHT Revival.",
     err_unreachable="Impossible de joindre {url} ({reason}). Le serveur est-il allumé et le port ouvert ?",
     err_password="Mot de passe incorrect pour ce serveur.", err_sync_rejected="Le serveur a refusé la synchronisation ({code}).",
     err_sync_failed="Impossible de synchroniser avec {url} ({reason}).",
     ev_start="La partie commence", ev_win="{name} gagne (+{pts} points)", ev_lose="{name} perd (+{pts} points)",
     ev_draw="{name} fait égalité (+{pts} points)", ev_quit="{name} a quitté la partie", ev_kill="La victime a été tuée",
     ev_arrest="Fin du dernier tour : le criminel a été arrêté", ev_threat="Une menace apparaît",
     ev_gas="Une fuite de gaz apparaît", ev_synced="Profil synchronisé")

_add("it",
     progress_btn='I tuoi progressi', progress_title='I tuoi progressi', progress_desc='Le tue partite, vittorie e punti sono salvati su questo PC. Puoi portarli su un altro PC o tenerne una copia per non perderli mai.', export_btn='Esporta in un file', import_btn='Importa un file', backup_label='Backup automatico', backup_off='Disattivato', backup_pick='Scegli cartella', backup_remove='Disattiva', backup_hint='Consiglio: scegli la tua cartella di OneDrive, Google Drive o Dropbox. Viene salvata una copia alla fine di ogni sessione e, su un altro PC, i progressi tornano da soli scegliendo la stessa cartella.', close='Chiudi', exported='Progressi salvati in {path}', imported='Fatto: {n} nuove partite aggiunte ai tuoi progressi.', import_nothing='Quel file non conteneva partite che non avessi già.', err_save_bad='Quel file non è un salvataggio di CRIMESIGHT Revival.', err_save_other='Quel file appartiene a un altro account Steam.', err_save_write='Impossibile salvare il file ({err}).', backup_set='Backup automatico attivato.', backup_removed='Backup automatico disattivato.', backup_restored='Progressi recuperati dal backup: {n} nuove partite.', backup_saved='Backup dei progressi salvato.', backup_failed='Impossibile fare il backup ({err}).', err_backup_missing='Cartella di backup non trovata: {path}',
     updating='Aggiornamento del launcher alla versione {v}…', update_failed='Impossibile aggiornare ({err}); continuo con la versione attuale.', kofi='Sostienimi su Ko-fi',
     loading="Preparazione del launcher…",
     tagline="Server della community per chi possiede già il gioco · nessun file di Konami",
     steam_account="Account Steam", no_steam="Apri Steam ed effettua l'accesso",
     wins="Vittorie", draws="Pareggi", losses="Sconfitte", points="Punti",
     solo_title="Gioca da solo", solo_desc="Partite contro l'IA sul tuo PC. Espelli un'IA dalla stanza per cambiarne la difficoltà.",
     host_title="Ospita", host_desc="Apri la tua partita agli amici. Ti do l'indirizzo per farli entrare.",
     join_title="Unisciti a un amico", join_desc="Collegati alla partita di un amico. I tuoi progressi vengono con te.",
     server_title="Server privato", server_desc="Entra in un server allestito da qualcuno, con password se ne ha una.",
     solo_hint="Si avvia un server sul tuo PC e si apre il gioco. Crea una stanza: i posti liberi vengono occupati dalle IA. Espelli un'IA per cambiarne la difficoltà.",
     play_btn="GIOCA", port="Porta",
     host_hint="Proverò ad aprire la porta del router da solo. Se il tuo amico non riesce a entrare, aprila a mano o usate Tailscale, ZeroTier o Radmin VPN.",
     host_btn="APRI PARTITA", friend_addr="Indirizzo del tuo amico", friend_ph="es. 83.45.120.7:18080", join_btn="UNISCITI",
     saved="Salvati", name="Nome", address="Indirizzo", server_ph="server.esempio.com:18080", password="Password",
     save="Salva", delete="Elimina", connect_btn="CONNETTI",
     session_running="Sessione in corso", copy="Copia", stop_session="Termina sessione",
     game_path="Gioco: {path}", no_game="CRIMESIGHT non trovato: scegli CrimeSight.exe",
     change_folder="Cambia eseguibile del gioco", restore_game="Ripristina il gioco originale", revival_by="Revival di", contributions_by="Contributi di",
     copied="Indirizzo copiato", server_saved="Server salvato",
     title_solo="Partita in solitario", title_host="Partita aperta agli amici", title_join="Connesso al tuo amico",
     title_server="Connesso al server",
     err_busy="C'è già una sessione in corso.", err_no_game="Prima scegli l'eseguibile del gioco.",
     err_no_steam="Apri Steam e accedi con l'account che possiede CRIMESIGHT.", err_no_address="Scrivi l'indirizzo.",
     stopping="Chiusura della sessione…", err_unexpected="Errore imprevisto: {err}",
     err_bad_folder="Quel file non sembra l'eseguibile di CRIMESIGHT (CrimeSight.exe).",
     err_finish_first="Prima termina la sessione.", restored="Gioco riportato allo stato originale.",
     already_original="Il gioco era già nello stato originale.", err_need_address="Inserisci almeno l'indirizzo.",
     loading_art="Preparazione delle illustrazioni dalla tua copia del gioco (solo la prima volta)…",
     notice_imported="Ho importato le tue partite dalla versione precedente.",
     srv_local_on="Server locale avviato.", pointing="Indirizzo il gioco verso {url}",
     opening="Apertura di CRIMESIGHT…", srv_stopped="Server fermato. Alla prossima!",
     host_upnp="Server aperto. Provo ad aprire la porta del router (UPnP)…", port_opened="Porta {port} aperta sul router.",
     port_failed="Il router non ha permesso di aprire la porta {port} automaticamente. Aprila a mano (inoltro TCP a questo PC) o usate una rete privata (Tailscale, ZeroTier o Radmin VPN) e condividi l'IP di quella rete.",
     give_address="Dai al tuo amico questo indirizzo: {addr}   (stessa rete di casa: {lan})",
     host_closed="Partita chiusa agli amici e server fermato.", checking="Verifica di {url}…",
     need_password="Quel server richiede una password: usa «Server privato».", syncing="Sincronizzazione dei tuoi progressi con il server…",
     record="Il tuo record: {w}V {d}P {l}S · {p} punti", fetching="Recupero delle tue nuove partite…",
     sync_later="Non è stato possibile recuperarle ora ({err}). Verranno unite al prossimo collegamento.",
     game_not_seen="Non ho visto aprirsi il gioco; puoi anche avviarlo tu da Steam.",
     game_open="Il gioco è in esecuzione. Chiudilo per terminare la sessione.",
     err_empty_addr="Scrivi un indirizzo.", err_not_revival="Lì risponde qualcosa, ma non è un server CRIMESIGHT Revival.",
     err_unreachable="Impossibile raggiungere {url} ({reason}). Il server è acceso e la porta aperta?",
     err_password="Password errata per quel server.", err_sync_rejected="Il server ha rifiutato la sincronizzazione ({code}).",
     err_sync_failed="Impossibile sincronizzarsi con {url} ({reason}).",
     ev_start="La partita inizia", ev_win="{name} vince (+{pts} punti)", ev_lose="{name} perde (+{pts} punti)",
     ev_draw="{name} pareggia (+{pts} punti)", ev_quit="{name} ha abbandonato la partita", ev_kill="La vittima è stata uccisa",
     ev_arrest="Fine dell'ultimo turno: il colpevole è stato arrestato", ev_threat="Appare una minaccia",
     ev_gas="Appare una fuga di gas", ev_synced="Profilo sincronizzato")

_add("de",
     progress_btn='Dein Fortschritt', progress_title='Dein Fortschritt', progress_desc='Deine Partien, Siege und Punkte werden auf diesem PC gespeichert. Du kannst sie auf einen anderen PC mitnehmen oder eine Kopie behalten, damit nichts verloren geht.', export_btn='In Datei exportieren', import_btn='Datei importieren', backup_label='Automatische Sicherung', backup_off='Aus', backup_pick='Ordner wählen', backup_remove='Ausschalten', backup_hint='Tipp: Wähle deinen OneDrive-, Google-Drive- oder Dropbox-Ordner. Nach jeder Sitzung wird eine Kopie gespeichert, und auf einem anderen PC kommt dein Fortschritt von selbst zurück, wenn du denselben Ordner wählst.', close='Schließen', exported='Fortschritt gespeichert unter {path}', imported='Fertig: {n} neue Partien zu deinem Fortschritt hinzugefügt.', import_nothing='Diese Datei enthielt keine Partien, die du nicht schon hattest.', err_save_bad='Diese Datei ist kein CRIMESIGHT-Revival-Fortschritt.', err_save_other='Diese Datei gehört zu einem anderen Steam-Konto.', err_save_write='Datei konnte nicht gespeichert werden ({err}).', backup_set='Automatische Sicherung eingeschaltet.', backup_removed='Automatische Sicherung ausgeschaltet.', backup_restored='Fortschritt aus deiner Sicherung wiederhergestellt: {n} neue Partien.', backup_saved='Fortschritt gesichert.', backup_failed='Sicherung fehlgeschlagen ({err}).', err_backup_missing='Sicherungsordner nicht gefunden: {path}',
     updating='Launcher wird auf Version {v} aktualisiert…', update_failed='Aktualisierung fehlgeschlagen ({err}); die aktuelle Version wird weiter verwendet.', kofi='Unterstütze mich auf Ko-fi',
     loading="Launcher wird vorbereitet…",
     tagline="Community-Server für alle, die das Spiel bereits besitzen · ohne Dateien von Konami",
     steam_account="Steam-Konto", no_steam="Öffne Steam und melde dich an",
     wins="Siege", draws="Unentschieden", losses="Niederlagen", points="Punkte",
     solo_title="Allein spielen", solo_desc="Partien gegen die KI auf deinem PC. Wirf eine KI aus dem Raum, um ihren Schwierigkeitsgrad zu ändern.",
     host_title="Hosten", host_desc="Öffne dein Spiel für Freunde. Ich gebe dir die Adresse, damit sie beitreten können.",
     join_title="Freund beitreten", join_desc="Verbinde dich mit dem Spiel eines Freundes. Dein Fortschritt kommt mit.",
     server_title="Eigener Server", server_desc="Tritt einem Server bei, den jemand eingerichtet hat – mit Passwort, falls nötig.",
     solo_hint="Auf deinem PC startet ein Server und das Spiel öffnet sich. Erstelle einen Raum: Freie Plätze werden mit KIs besetzt. Wirf eine KI hinaus, um ihren Schwierigkeitsgrad zu ändern.",
     play_btn="SPIELEN", port="Port",
     host_hint="Ich versuche, den Port deines Routers automatisch zu öffnen. Kommt dein Freund nicht rein, öffne ihn manuell oder nutzt Tailscale, ZeroTier oder Radmin VPN.",
     host_btn="SPIEL ÖFFNEN", friend_addr="Adresse deines Freundes", friend_ph="z. B. 83.45.120.7:18080", join_btn="BEITRETEN",
     saved="Gespeichert", name="Name", address="Adresse", server_ph="server.beispiel.de:18080", password="Passwort",
     save="Speichern", delete="Löschen", connect_btn="VERBINDEN",
     session_running="Sitzung läuft", copy="Kopieren", stop_session="Sitzung beenden",
     game_path="Spiel: {path}", no_game="CRIMESIGHT nicht gefunden: wähle CrimeSight.exe aus",
     change_folder="Spiel-EXE ändern", restore_game="Originalspiel wiederherstellen", revival_by="Revival von", contributions_by="Beiträge von",
     copied="Adresse kopiert", server_saved="Server gespeichert",
     title_solo="Einzelspiel", title_host="Spiel für Freunde geöffnet", title_join="Mit deinem Freund verbunden",
     title_server="Mit dem Server verbunden",
     err_busy="Es läuft bereits eine Sitzung.", err_no_game="Wähle zuerst die EXE-Datei des Spiels.",
     err_no_steam="Öffne Steam und melde dich mit dem Konto an, das CRIMESIGHT besitzt.", err_no_address="Gib die Adresse ein.",
     stopping="Sitzung wird beendet…", err_unexpected="Unerwarteter Fehler: {err}",
     err_bad_folder="Diese Datei scheint nicht die EXE von CRIMESIGHT zu sein (CrimeSight.exe).",
     err_finish_first="Beende zuerst die Sitzung.", restored="Spiel in den Originalzustand zurückversetzt.",
     already_original="Das Spiel war bereits im Originalzustand.", err_need_address="Gib mindestens die Adresse ein.",
     loading_art="Bilder werden aus deiner Spielkopie vorbereitet (nur beim ersten Mal)…",
     notice_imported="Deine Partien aus der vorherigen Version wurden übernommen.",
     srv_local_on="Lokaler Server läuft.", pointing="Spiel wird auf {url} umgeleitet",
     opening="CRIMESIGHT wird gestartet…", srv_stopped="Server gestoppt. Bis zum nächsten Mal!",
     host_upnp="Server offen. Versuche, den Router-Port zu öffnen (UPnP)…", port_opened="Port {port} am Router geöffnet.",
     port_failed="Der Router hat das automatische Öffnen von Port {port} nicht erlaubt. Öffne ihn manuell (TCP an diesen PC weiterleiten) oder nutzt ein privates Netz (Tailscale, ZeroTier oder Radmin VPN) und gib die IP dieses Netzes weiter.",
     give_address="Gib deinem Freund diese Adresse: {addr}   (im selben Heimnetz: {lan})",
     host_closed="Spiel für Freunde geschlossen und Server gestoppt.", checking="Prüfe {url}…",
     need_password="Dieser Server verlangt ein Passwort: nutze „Eigener Server“.", syncing="Dein Fortschritt wird mit dem Server synchronisiert…",
     record="Deine Bilanz: {w}S {d}U {l}N · {p} Punkte", fetching="Deine neuen Partien werden übernommen…",
     sync_later="Konnte sie gerade nicht übernehmen ({err}). Sie werden bei der nächsten Verbindung zusammengeführt.",
     game_not_seen="Ich habe das Spiel nicht starten sehen; du kannst es auch selbst über Steam starten.",
     game_open="Das Spiel läuft. Schließe es, um die Sitzung zu beenden.",
     err_empty_addr="Gib eine Adresse ein.", err_not_revival="Dort antwortet etwas, aber es ist kein CRIMESIGHT-Revival-Server.",
     err_unreachable="{url} ist nicht erreichbar ({reason}). Läuft der Server und ist der Port offen?",
     err_password="Falsches Passwort für diesen Server.", err_sync_rejected="Der Server hat die Synchronisierung abgelehnt ({code}).",
     err_sync_failed="Synchronisierung mit {url} fehlgeschlagen ({reason}).",
     ev_start="Die Partie beginnt", ev_win="{name} gewinnt (+{pts} Punkte)", ev_lose="{name} verliert (+{pts} Punkte)",
     ev_draw="{name} spielt unentschieden (+{pts} Punkte)", ev_quit="{name} hat die Partie verlassen", ev_kill="Das Opfer wurde getötet",
     ev_arrest="Letzter Zug vorbei: Der Täter wurde verhaftet", ev_threat="Eine Bedrohung taucht auf",
     ev_gas="Ein Gasleck tritt auf", ev_synced="Profil synchronisiert")

_add("pt",
     progress_btn='Seu progresso', progress_title='Seu progresso', progress_desc='Suas partidas, vitórias e pontos ficam salvos neste PC. Você pode levá-los para outro PC ou guardar uma cópia para nunca perdê-los.', export_btn='Exportar para um arquivo', import_btn='Importar um arquivo', backup_label='Cópia automática', backup_off='Desativada', backup_pick='Escolher pasta', backup_remove='Desativar', backup_hint='Dica: escolha sua pasta do OneDrive, Google Drive ou Dropbox. Uma cópia é salva ao fim de cada sessão e, em outro PC, seu progresso volta sozinho ao escolher a mesma pasta.', close='Fechar', exported='Progresso salvo em {path}', imported='Pronto: {n} partidas novas adicionadas ao seu progresso.', import_nothing='Esse arquivo não tinha partidas que você já não tivesse.', err_save_bad='Esse arquivo não é um progresso do CRIMESIGHT Revival.', err_save_other='Esse arquivo é de outra conta Steam.', err_save_write='Não foi possível salvar o arquivo ({err}).', backup_set='Cópia automática ativada.', backup_removed='Cópia automática desativada.', backup_restored='Progresso recuperado da sua cópia: {n} partidas novas.', backup_saved='Cópia do progresso salva.', backup_failed='Não foi possível fazer a cópia ({err}).', err_backup_missing='Pasta de cópia não encontrada: {path}',
     updating='Atualizando o inicializador para a versão {v}…', update_failed='Não foi possível atualizar ({err}); continuo com a versão atual.', kofi='Me apoie no Ko-fi',
     loading="Preparando o inicializador…",
     tagline="Servidor da comunidade para quem já tem o jogo · sem arquivos da Konami",
     steam_account="Conta Steam", no_steam="Abra a Steam e faça login",
     wins="Vitórias", draws="Empates", losses="Derrotas", points="Pontos",
     solo_title="Jogar sozinho", solo_desc="Partidas contra a IA no seu PC. Expulse uma IA da sala para mudar a dificuldade dela.",
     host_title="Ser anfitrião", host_desc="Abra sua partida para os amigos. Eu te passo o endereço para eles entrarem.",
     join_title="Entrar com um amigo", join_desc="Conecte-se à partida de um amigo. Seu progresso vai junto.",
     server_title="Servidor próprio", server_desc="Entre em um servidor montado por alguém, com senha se tiver.",
     solo_hint="Um servidor é iniciado no seu PC e o jogo abre. Crie uma sala: as vagas livres são ocupadas por IAs. Expulse uma IA para mudar a dificuldade dela.",
     play_btn="JOGAR", port="Porta",
     host_hint="Vou tentar abrir a porta do roteador sozinho. Se seu amigo não conseguir entrar, abra-a manualmente ou usem Tailscale, ZeroTier ou Radmin VPN.",
     host_btn="ABRIR PARTIDA", friend_addr="Endereço do seu amigo", friend_ph="por exemplo 83.45.120.7:18080", join_btn="ENTRAR",
     saved="Salvos", name="Nome", address="Endereço", server_ph="servidor.exemplo.com:18080", password="Senha",
     save="Salvar", delete="Excluir", connect_btn="CONECTAR",
     session_running="Sessão em andamento", copy="Copiar", stop_session="Encerrar sessão",
     game_path="Jogo: {path}", no_game="CRIMESIGHT não encontrado: escolha o CrimeSight.exe",
     change_folder="Mudar executável do jogo", restore_game="Restaurar o jogo original", revival_by="Revival por", contributions_by="Contribuições de",
     copied="Endereço copiado", server_saved="Servidor salvo",
     title_solo="Partida solo", title_host="Partida aberta para amigos", title_join="Conectado ao seu amigo",
     title_server="Conectado ao servidor",
     err_busy="Já há uma sessão em andamento.", err_no_game="Primeiro escolha o executável do jogo.",
     err_no_steam="Abra a Steam e entre com a conta que tem CRIMESIGHT.", err_no_address="Digite o endereço.",
     stopping="Encerrando a sessão…", err_unexpected="Erro inesperado: {err}",
     err_bad_folder="Esse arquivo não parece ser o executável do CRIMESIGHT (CrimeSight.exe).",
     err_finish_first="Encerre a sessão primeiro.", restored="Jogo restaurado ao estado original.",
     already_original="O jogo já estava no estado original.", err_need_address="Informe pelo menos o endereço.",
     loading_art="Preparando as ilustrações a partir da sua cópia do jogo (só na primeira vez)…",
     notice_imported="Trouxe suas partidas da versão anterior.",
     srv_local_on="Servidor local em execução.", pointing="Apontando o jogo para {url}",
     opening="Abrindo CRIMESIGHT…", srv_stopped="Servidor parado. Até a próxima!",
     host_upnp="Servidor aberto. Tentando abrir a porta no roteador (UPnP)…", port_opened="Porta {port} aberta no roteador.",
     port_failed="O roteador não deixou abrir a porta {port} automaticamente. Abra-a manualmente (redirecionar TCP para este PC) ou usem uma rede privada (Tailscale, ZeroTier ou Radmin VPN) e passe o IP dessa rede.",
     give_address="Passe este endereço ao seu amigo: {addr}   (na mesma rede de casa: {lan})",
     host_closed="Partida fechada para amigos e servidor parado.", checking="Verificando {url}…",
     need_password="Esse servidor pede senha: use «Servidor próprio».", syncing="Sincronizando seu progresso com o servidor…",
     record="Seu histórico: {w}V {d}E {l}D · {p} pontos", fetching="Trazendo suas partidas novas…",
     sync_later="Não consegui trazê-las agora ({err}). Elas serão juntadas na próxima vez que você se conectar.",
     game_not_seen="Não vi o jogo abrir; abrir você mesmo pela Steam também funciona.",
     game_open="O jogo está aberto. Feche-o para encerrar a sessão.",
     err_empty_addr="Digite um endereço.", err_not_revival="Algo responde ali, mas não é um servidor do CRIMESIGHT Revival.",
     err_unreachable="Não consigo acessar {url} ({reason}). O servidor está ligado e a porta aberta?",
     err_password="Senha incorreta para esse servidor.", err_sync_rejected="O servidor recusou a sincronização ({code}).",
     err_sync_failed="Não foi possível sincronizar com {url} ({reason}).",
     ev_start="A partida começa", ev_win="{name} vence (+{pts} pontos)", ev_lose="{name} perde (+{pts} pontos)",
     ev_draw="{name} empata (+{pts} pontos)", ev_quit="{name} abandonou a partida", ev_kill="A vítima foi morta",
     ev_arrest="Fim do último turno: o criminoso foi preso", ev_threat="Surge uma ameaça",
     ev_gas="Surge um vazamento de gás", ev_synced="Perfil sincronizado")

_add("ru",
     progress_btn='Ваш прогресс', progress_title='Ваш прогресс', progress_desc='Ваши матчи, победы и очки хранятся на этом ПК. Их можно перенести на другой ПК или сохранить копию, чтобы ничего не потерять.', export_btn='Экспорт в файл', import_btn='Импорт файла', backup_label='Автоматическая копия', backup_off='Выключена', backup_pick='Выбрать папку', backup_remove='Выключить', backup_hint='Совет: выберите папку OneDrive, Google Drive или Dropbox. Копия сохраняется после каждой сессии, а на другом ПК прогресс вернётся сам, если выбрать ту же папку.', close='Закрыть', exported='Прогресс сохранён в {path}', imported='Готово: добавлено новых матчей: {n}.', import_nothing='В этом файле нет матчей, которых у вас ещё нет.', err_save_bad='Это не файл прогресса CRIMESIGHT Revival.', err_save_other='Этот файл принадлежит другому аккаунту Steam.', err_save_write='Не удалось сохранить файл ({err}).', backup_set='Автоматическая копия включена.', backup_removed='Автоматическая копия выключена.', backup_restored='Прогресс восстановлен из копии: новых матчей: {n}.', backup_saved='Копия прогресса сохранена.', backup_failed='Не удалось сделать копию ({err}).', err_backup_missing='Папка для копии не найдена: {path}',
     updating='Обновление лаунчера до версии {v}…', update_failed='Не удалось обновить ({err}); используется текущая версия.', kofi='Поддержать меня на Ko-fi',
     loading="Подготовка лаунчера…",
     tagline="Сервер сообщества для тех, у кого уже есть игра · без файлов Konami",
     steam_account="Аккаунт Steam", no_steam="Откройте Steam и войдите",
     wins="Победы", draws="Ничьи", losses="Поражения", points="Очки",
     solo_title="Играть одному", solo_desc="Матчи против ИИ на вашем ПК. Выгоните ИИ из комнаты, чтобы сменить его сложность.",
     host_title="Стать хостом", host_desc="Откройте игру для друзей. Я дам адрес, по которому они подключатся.",
     join_title="К другу", join_desc="Подключитесь к игре друга. Ваш прогресс останется с вами.",
     server_title="Свой сервер", server_desc="Зайдите на сервер, который кто-то поднял, — с паролем, если он есть.",
     solo_hint="На вашем ПК запускается сервер и открывается игра. Создайте комнату: свободные места займут ИИ. Выгоните ИИ, чтобы сменить его сложность.",
     play_btn="ИГРАТЬ", port="Порт",
     host_hint="Я попробую открыть порт на роутере сам. Если друг не может подключиться, откройте его вручную или используйте Tailscale, ZeroTier или Radmin VPN.",
     host_btn="ОТКРЫТЬ ИГРУ", friend_addr="Адрес друга", friend_ph="например 83.45.120.7:18080", join_btn="ПОДКЛЮЧИТЬСЯ",
     saved="Сохранённые", name="Название", address="Адрес", server_ph="server.example.com:18080", password="Пароль",
     save="Сохранить", delete="Удалить", connect_btn="ПОДКЛЮЧИТЬСЯ",
     session_running="Сеанс идёт", copy="Копировать", stop_session="Завершить сеанс",
     game_path="Игра: {path}", no_game="CRIMESIGHT не найдена: выберите CrimeSight.exe",
     change_folder="Сменить exe-файл игры", restore_game="Вернуть исходную игру", revival_by="Revival от", contributions_by="При участии",
     copied="Адрес скопирован", server_saved="Сервер сохранён",
     title_solo="Одиночная игра", title_host="Игра открыта для друзей", title_join="Подключено к другу",
     title_server="Подключено к серверу",
     err_busy="Сеанс уже запущен.", err_no_game="Сначала выберите exe-файл игры.",
     err_no_steam="Откройте Steam и войдите в аккаунт, где есть CRIMESIGHT.", err_no_address="Введите адрес.",
     stopping="Завершение сеанса…", err_unexpected="Непредвиденная ошибка: {err}",
     err_bad_folder="Этот файл не похож на исполняемый файл CRIMESIGHT (CrimeSight.exe).",
     err_finish_first="Сначала завершите сеанс.", restored="Игра возвращена в исходное состояние.",
     already_original="Игра уже была в исходном состоянии.", err_need_address="Укажите хотя бы адрес.",
     loading_art="Подготовка иллюстраций из вашей копии игры (только в первый раз)…",
     notice_imported="Ваши матчи из прошлой версии перенесены.",
     srv_local_on="Локальный сервер запущен.", pointing="Игра направляется на {url}",
     opening="Запуск CRIMESIGHT…", srv_stopped="Сервер остановлен. До встречи!",
     host_upnp="Сервер открыт. Пробую открыть порт на роутере (UPnP)…", port_opened="Порт {port} открыт на роутере.",
     port_failed="Роутер не дал открыть порт {port} автоматически. Откройте его вручную (проброс TCP на этот ПК) или используйте частную сеть (Tailscale, ZeroTier или Radmin VPN) и передайте IP этой сети.",
     give_address="Передайте другу этот адрес: {addr}   (в той же домашней сети: {lan})",
     host_closed="Игра закрыта для друзей, сервер остановлен.", checking="Проверка {url}…",
     need_password="Этот сервер требует пароль: используйте «Свой сервер».", syncing="Синхронизация прогресса с сервером…",
     record="Ваша статистика: {w} побед, {d} ничьих, {l} поражений · {p} очков", fetching="Забираю ваши новые матчи…",
     sync_later="Сейчас забрать не удалось ({err}). Они объединятся при следующем подключении.",
     game_not_seen="Я не увидел запуска игры; можно запустить её самому из Steam.",
     game_open="Игра запущена. Закройте её, чтобы завершить сеанс.",
     err_empty_addr="Введите адрес.", err_not_revival="Там что-то отвечает, но это не сервер CRIMESIGHT Revival.",
     err_unreachable="Не удаётся подключиться к {url} ({reason}). Сервер включён и порт открыт?",
     err_password="Неверный пароль для этого сервера.", err_sync_rejected="Сервер отклонил синхронизацию ({code}).",
     err_sync_failed="Не удалось синхронизироваться с {url} ({reason}).",
     ev_start="Матч начался", ev_win="{name} побеждает (+{pts} очков)", ev_lose="{name} проигрывает (+{pts} очков)",
     ev_draw="{name}: ничья (+{pts} очков)", ev_quit="{name} покинул матч", ev_kill="Жертва убита",
     ev_arrest="Последний ход окончен: злодей арестован", ev_threat="Появляется угроза",
     ev_gas="Появляется утечка газа", ev_synced="Профиль синхронизирован")

_add("ja",
     progress_btn='進行状況', progress_title='進行状況', progress_desc='試合・勝利・ポイントはこのPCに保存されています。別のPCに移したり、失わないようにコピーを残したりできます。', export_btn='ファイルに書き出す', import_btn='ファイルを読み込む', backup_label='自動バックアップ', backup_off='オフ', backup_pick='フォルダを選ぶ', backup_remove='オフにする', backup_hint='ヒント：OneDrive、Google ドライブ、Dropbox のフォルダを選んでください。セッション終了ごとにコピーが保存され、別のPCでも同じフォルダを選べば進行状況が自動で戻ります。', close='閉じる', exported='進行状況を保存しました：{path}', imported='完了：新しい試合を {n} 件追加しました。', import_nothing='このファイルには新しい試合がありませんでした。', err_save_bad='CRIMESIGHT Revival の進行状況ファイルではありません。', err_save_other='このファイルは別の Steam アカウントのものです。', err_save_write='ファイルを保存できませんでした（{err}）。', backup_set='自動バックアップをオンにしました。', backup_removed='自動バックアップをオフにしました。', backup_restored='バックアップから進行状況を復元しました：新しい試合 {n} 件。', backup_saved='進行状況をバックアップしました。', backup_failed='バックアップできませんでした（{err}）。', err_backup_missing='バックアップ先のフォルダが見つかりません：{path}',
     updating='ランチャーをバージョン {v} に更新しています…', update_failed='更新できませんでした（{err}）。現在のバージョンを使います。', kofi='Ko-fiで応援する',
     loading="ランチャーを準備しています…",
     tagline="ゲームを持っている人のためのコミュニティサーバー · KONAMIのファイルは含みません",
     steam_account="Steamアカウント", no_steam="Steamを起動してログインしてください",
     wins="勝利", draws="引き分け", losses="敗北", points="ポイント",
     solo_title="ひとりで遊ぶ", solo_desc="PCでAIと対戦します。ルームからAIをキックすると難易度を変えられます。",
     host_title="ホストになる", host_desc="友達にゲームを公開します。参加用のアドレスをお知らせします。",
     join_title="友達に参加", join_desc="友達のゲームに接続します。進行状況も一緒に引き継がれます。",
     server_title="独自サーバー", server_desc="誰かが立てたサーバーに接続します。パスワードがあれば入力してください。",
     solo_hint="PCでサーバーが起動し、ゲームが開きます。ルームを作成すると空き枠はAIが埋めます。AIをキックすると難易度を変えられます。",
     play_btn="プレイ", port="ポート",
     host_hint="ルーターのポートを自動で開けてみます。友達が入れない場合は手動で開けるか、Tailscale・ZeroTier・Radmin VPNを使ってください。",
     host_btn="ゲームを公開", friend_addr="友達のアドレス", friend_ph="例: 83.45.120.7:18080", join_btn="参加",
     saved="保存済み", name="名前", address="アドレス", server_ph="server.example.com:18080", password="パスワード",
     save="保存", delete="削除", connect_btn="接続",
     session_running="セッション中", copy="コピー", stop_session="セッションを終了",
     game_path="ゲーム: {path}", no_game="CRIMESIGHTが見つかりません: CrimeSight.exeを選んでください",
     change_folder="ゲームの実行ファイルを変更", restore_game="ゲームを元に戻す", revival_by="Revival 制作:", contributions_by="協力:",
     copied="アドレスをコピーしました", server_saved="サーバーを保存しました",
     title_solo="ソロプレイ", title_host="友達に公開中", title_join="友達に接続中", title_server="サーバーに接続中",
     err_busy="すでにセッションが実行中です。", err_no_game="先にゲームの実行ファイルを選んでください。",
     err_no_steam="Steamを起動し、CRIMESIGHTを持っているアカウントでログインしてください。", err_no_address="アドレスを入力してください。",
     stopping="セッションを終了しています…", err_unexpected="予期しないエラー: {err}",
     err_bad_folder="そのファイルはCRIMESIGHTの実行ファイル（CrimeSight.exe）ではないようです。",
     err_finish_first="先にセッションを終了してください。", restored="ゲームを元の状態に戻しました。",
     already_original="ゲームはすでに元の状態です。", err_need_address="少なくともアドレスを入力してください。",
     loading_art="お持ちのゲームからイラストを準備しています（初回のみ）…",
     notice_imported="以前のバージョンの対戦記録を取り込みました。",
     srv_local_on="ローカルサーバーを起動しました。", pointing="ゲームの接続先を {url} に設定しています",
     opening="CRIMESIGHTを起動しています…", srv_stopped="サーバーを停止しました。またね！",
     host_upnp="サーバーを公開しました。ルーターのポートを開けています（UPnP）…", port_opened="ルーターのポート {port} を開けました。",
     port_failed="ルーターがポート {port} の自動開放を許可しませんでした。手動で開ける（このPCへTCPを転送）か、プライベートネットワーク（Tailscale・ZeroTier・Radmin VPN）を使い、そのIPを伝えてください。",
     give_address="友達にこのアドレスを伝えてください: {addr}   （同じ家のネットワーク: {lan}）",
     host_closed="友達への公開を終了し、サーバーを停止しました。", checking="{url} を確認しています…",
     need_password="そのサーバーにはパスワードが必要です:「独自サーバー」を使ってください。", syncing="進行状況をサーバーと同期しています…",
     record="あなたの戦績: {w}勝 {d}分 {l}敗 · {p}ポイント", fetching="新しい対戦記録を取り込んでいます…",
     sync_later="今は取り込めませんでした（{err}）。次回接続時にまとめて反映されます。",
     game_not_seen="ゲームの起動を確認できませんでした。Steamから自分で起動しても大丈夫です。",
     game_open="ゲームを実行中です。閉じるとセッションが終了します。",
     err_empty_addr="アドレスを入力してください。", err_not_revival="応答はありますが、CRIMESIGHT Revivalのサーバーではありません。",
     err_unreachable="{url} に接続できません（{reason}）。サーバーが起動し、ポートが開いているか確認してください。",
     err_password="そのサーバーのパスワードが違います。", err_sync_rejected="サーバーが同期を拒否しました（{code}）。",
     err_sync_failed="{url} と同期できませんでした（{reason}）。",
     ev_start="対戦開始", ev_win="{name} の勝利（+{pts}ポイント）", ev_lose="{name} の敗北（+{pts}ポイント）",
     ev_draw="{name} は引き分け（+{pts}ポイント）", ev_quit="{name} が対戦から離脱しました", ev_kill="ターゲットが殺害されました",
     ev_arrest="最終ターン終了: 犯人を逮捕しました", ev_threat="脅威が現れました",
     ev_gas="ガス漏れが発生しました", ev_synced="プロフィールを同期しました")

_add("ko",
     progress_btn='내 진행 상황', progress_title='내 진행 상황', progress_desc='경기, 승리, 포인트는 이 PC에 저장됩니다. 다른 PC로 옮기거나 잃어버리지 않도록 사본을 보관할 수 있습니다.', export_btn='파일로 내보내기', import_btn='파일 가져오기', backup_label='자동 백업', backup_off='꺼짐', backup_pick='폴더 선택', backup_remove='끄기', backup_hint='팁: OneDrive, Google Drive 또는 Dropbox 폴더를 선택하세요. 세션이 끝날 때마다 사본이 저장되고, 다른 PC에서 같은 폴더를 선택하면 진행 상황이 자동으로 돌아옵니다.', close='닫기', exported='진행 상황을 저장했습니다: {path}', imported='완료: 새 경기 {n}개를 추가했습니다.', import_nothing='이 파일에는 새로운 경기가 없습니다.', err_save_bad='CRIMESIGHT Revival 진행 상황 파일이 아닙니다.', err_save_other='이 파일은 다른 Steam 계정의 것입니다.', err_save_write='파일을 저장할 수 없습니다 ({err}).', backup_set='자동 백업을 켰습니다.', backup_removed='자동 백업을 껐습니다.', backup_restored='백업에서 진행 상황을 복구했습니다: 새 경기 {n}개.', backup_saved='진행 상황을 백업했습니다.', backup_failed='백업할 수 없습니다 ({err}).', err_backup_missing='백업 폴더를 찾을 수 없습니다: {path}',
     updating='런처를 {v} 버전으로 업데이트하는 중…', update_failed='업데이트하지 못했습니다({err}). 현재 버전을 계속 사용합니다.', kofi='Ko-fi에서 후원하기',
     loading="런처를 준비하는 중…",
     tagline="게임을 이미 가진 사람을 위한 커뮤니티 서버 · Konami 파일 미포함",
     steam_account="Steam 계정", no_steam="Steam을 열고 로그인하세요",
     wins="승리", draws="무승부", losses="패배", points="포인트",
     solo_title="혼자 플레이", solo_desc="PC에서 AI와 대전합니다. 방에서 AI를 강퇴하면 난이도가 바뀝니다.",
     host_title="호스트하기", host_desc="친구에게 게임을 엽니다. 참가할 주소를 알려 드립니다.",
     join_title="친구에게 참가", join_desc="친구의 게임에 접속합니다. 진행 상황도 함께 따라갑니다.",
     server_title="개인 서버", server_desc="누군가 운영하는 서버에 접속합니다. 비밀번호가 있으면 입력하세요.",
     solo_hint="PC에서 서버가 시작되고 게임이 열립니다. 방을 만들면 빈자리는 AI가 채웁니다. AI를 강퇴하면 난이도가 바뀝니다.",
     play_btn="플레이", port="포트",
     host_hint="공유기 포트를 자동으로 열어 보겠습니다. 친구가 들어오지 못하면 직접 열거나 Tailscale, ZeroTier, Radmin VPN을 사용하세요.",
     host_btn="게임 열기", friend_addr="친구의 주소", friend_ph="예: 83.45.120.7:18080", join_btn="참가",
     saved="저장됨", name="이름", address="주소", server_ph="server.example.com:18080", password="비밀번호",
     save="저장", delete="삭제", connect_btn="접속",
     session_running="세션 진행 중", copy="복사", stop_session="세션 종료",
     game_path="게임: {path}", no_game="CRIMESIGHT를 찾을 수 없습니다: CrimeSight.exe를 선택하세요",
     change_folder="게임 실행 파일 변경", restore_game="원래 게임으로 되돌리기", revival_by="Revival 제작:", contributions_by="기여:",
     copied="주소를 복사했습니다", server_saved="서버를 저장했습니다",
     title_solo="솔로 플레이", title_host="친구에게 공개 중", title_join="친구에게 접속됨", title_server="서버에 접속됨",
     err_busy="이미 세션이 진행 중입니다.", err_no_game="먼저 게임 실행 파일을 선택하세요.",
     err_no_steam="Steam을 열고 CRIMESIGHT를 가진 계정으로 로그인하세요.", err_no_address="주소를 입력하세요.",
     stopping="세션을 종료하는 중…", err_unexpected="예상치 못한 오류: {err}",
     err_bad_folder="그 파일은 CRIMESIGHT 실행 파일(CrimeSight.exe)이 아닌 것 같습니다.",
     err_finish_first="먼저 세션을 종료하세요.", restored="게임을 원래 상태로 되돌렸습니다.",
     already_original="게임이 이미 원래 상태입니다.", err_need_address="최소한 주소는 입력하세요.",
     loading_art="보유한 게임에서 일러스트를 준비하는 중(처음 한 번만)…",
     notice_imported="이전 버전의 대전 기록을 가져왔습니다.",
     srv_local_on="로컬 서버가 실행 중입니다.", pointing="게임 접속 주소를 {url}(으)로 설정하는 중",
     opening="CRIMESIGHT를 실행하는 중…", srv_stopped="서버를 멈췄습니다. 다음에 또 만나요!",
     host_upnp="서버를 열었습니다. 공유기 포트를 여는 중(UPnP)…", port_opened="공유기의 {port} 포트를 열었습니다.",
     port_failed="공유기가 {port} 포트를 자동으로 열지 못하게 했습니다. 직접 열거나(이 PC로 TCP 포워딩) 개인 네트워크(Tailscale, ZeroTier, Radmin VPN)를 사용해 그 IP를 알려 주세요.",
     give_address="친구에게 이 주소를 알려 주세요: {addr}   (같은 집 네트워크: {lan})",
     host_closed="친구 공개를 닫고 서버를 멈췄습니다.", checking="{url} 확인 중…",
     need_password="그 서버는 비밀번호가 필요합니다: '개인 서버'를 사용하세요.", syncing="진행 상황을 서버와 동기화하는 중…",
     record="내 전적: {w}승 {d}무 {l}패 · {p}포인트", fetching="새 대전 기록을 가져오는 중…",
     sync_later="지금은 가져오지 못했습니다({err}). 다음 접속 때 합쳐집니다.",
     game_not_seen="게임이 실행되는 것을 확인하지 못했습니다. Steam에서 직접 실행해도 됩니다.",
     game_open="게임이 실행 중입니다. 게임을 닫으면 세션이 종료됩니다.",
     err_empty_addr="주소를 입력하세요.", err_not_revival="응답은 있지만 CRIMESIGHT Revival 서버가 아닙니다.",
     err_unreachable="{url}에 연결할 수 없습니다({reason}). 서버가 켜져 있고 포트가 열려 있나요?",
     err_password="그 서버의 비밀번호가 틀렸습니다.", err_sync_rejected="서버가 동기화를 거부했습니다({code}).",
     err_sync_failed="{url}와(과) 동기화하지 못했습니다({reason}).",
     ev_start="대전 시작", ev_win="{name} 승리(+{pts}포인트)", ev_lose="{name} 패배(+{pts}포인트)",
     ev_draw="{name} 무승부(+{pts}포인트)", ev_quit="{name}이(가) 대전을 떠났습니다", ev_kill="타깃이 살해되었습니다",
     ev_arrest="마지막 턴 종료: 범인이 체포되었습니다", ev_threat="위협이 나타났습니다",
     ev_gas="가스 누출이 발생했습니다", ev_synced="프로필을 동기화했습니다")

_add("zh-CN",
     progress_btn='我的进度', progress_title='我的进度', progress_desc='你的对局、胜场和积分保存在这台电脑上。你可以把它们带到另一台电脑，或保留一份副本以免丢失。', export_btn='导出到文件', import_btn='导入文件', backup_label='自动备份', backup_off='已关闭', backup_pick='选择文件夹', backup_remove='关闭', backup_hint='提示：选择你的 OneDrive、Google 云端硬盘或 Dropbox 文件夹。每次会话结束都会保存一份副本，在另一台电脑上选择同一个文件夹，进度会自动恢复。', close='关闭', exported='进度已保存到 {path}', imported='完成：已添加 {n} 场新对局。', import_nothing='该文件中没有你尚未拥有的对局。', err_save_bad='该文件不是 CRIMESIGHT Revival 进度文件。', err_save_other='该文件属于另一个 Steam 账号。', err_save_write='无法保存文件（{err}）。', backup_set='已开启自动备份。', backup_removed='已关闭自动备份。', backup_restored='已从备份恢复进度：{n} 场新对局。', backup_saved='进度已备份。', backup_failed='无法备份（{err}）。', err_backup_missing='找不到备份文件夹：{path}',
     updating='正在将启动器更新到 {v} 版…', update_failed='无法更新（{err}），继续使用当前版本。', kofi='在 Ko-fi 上支持我',
     loading="正在准备启动器…",
     tagline="面向已拥有游戏玩家的社区服务器 · 不含任何 Konami 文件",
     steam_account="Steam 账号", no_steam="请打开 Steam 并登录",
     wins="胜利", draws="平局", losses="失败", points="积分",
     solo_title="单人游玩", solo_desc="在你的电脑上与 AI 对战。将 AI 踢出房间即可更改其难度。",
     host_title="创建主机", host_desc="向好友开放你的对局。我会给你一个地址供他们加入。",
     join_title="加入好友", join_desc="连接到好友的对局。你的进度会一起带过去。",
     server_title="自建服务器", server_desc="加入他人搭建的服务器，如有密码请填写。",
     solo_hint="将在你的电脑上启动服务器并打开游戏。创建房间后，空位会由 AI 补上。踢出 AI 即可更改其难度。",
     play_btn="开始游戏", port="端口",
     host_hint="我会尝试自动打开路由器端口。如果好友无法进入，请手动打开，或使用 Tailscale、ZeroTier 或 Radmin VPN。",
     host_btn="开放对局", friend_addr="好友的地址", friend_ph="例如 83.45.120.7:18080", join_btn="加入",
     saved="已保存", name="名称", address="地址", server_ph="server.example.com:18080", password="密码",
     save="保存", delete="删除", connect_btn="连接",
     session_running="会话进行中", copy="复制", stop_session="结束会话",
     game_path="游戏：{path}", no_game="未找到 CRIMESIGHT：请选择 CrimeSight.exe",
     change_folder="更改游戏可执行文件", restore_game="恢复原版游戏", revival_by="Revival 作者", contributions_by="贡献者",
     copied="地址已复制", server_saved="服务器已保存",
     title_solo="单人对局", title_host="已向好友开放", title_join="已连接到好友", title_server="已连接到服务器",
     err_busy="已有会话在进行中。", err_no_game="请先选择游戏的可执行文件。",
     err_no_steam="请打开 Steam 并使用拥有 CRIMESIGHT 的账号登录。", err_no_address="请输入地址。",
     stopping="正在结束会话…", err_unexpected="意外错误：{err}",
     err_bad_folder="该文件似乎不是 CRIMESIGHT 的可执行文件（CrimeSight.exe）。",
     err_finish_first="请先结束会话。", restored="游戏已恢复为原始状态。",
     already_original="游戏已经是原始状态。", err_need_address="请至少填写地址。",
     loading_art="正在从你的游戏副本中准备插图（仅首次）…",
     notice_imported="已导入你在旧版本中的对局记录。",
     srv_local_on="本地服务器已启动。", pointing="正在将游戏指向 {url}",
     opening="正在启动 CRIMESIGHT…", srv_stopped="服务器已停止。下次见！",
     host_upnp="服务器已开放。正在尝试打开路由器端口（UPnP）…", port_opened="已在路由器上打开端口 {port}。",
     port_failed="路由器不允许自动打开端口 {port}。请手动打开（将 TCP 转发到此电脑），或使用私有网络（Tailscale、ZeroTier 或 Radmin VPN）并告知该网络的 IP。",
     give_address="请把这个地址发给好友：{addr}   （同一家庭网络：{lan}）",
     host_closed="已停止向好友开放，服务器已停止。", checking="正在检查 {url}…",
     need_password="该服务器需要密码：请使用“自建服务器”。", syncing="正在与服务器同步你的进度…",
     record="你的战绩：{w}胜 {d}平 {l}负 · {p} 积分", fetching="正在取回你的新对局…",
     sync_later="暂时无法取回（{err}）。下次连接时会自动合并。",
     game_not_seen="没有检测到游戏启动；你也可以自己从 Steam 启动。",
     game_open="游戏正在运行。关闭游戏即可结束会话。",
     err_empty_addr="请输入地址。", err_not_revival="该地址有响应，但不是 CRIMESIGHT Revival 服务器。",
     err_unreachable="无法连接到 {url}（{reason}）。服务器是否已开启、端口是否已打开？",
     err_password="该服务器的密码错误。", err_sync_rejected="服务器拒绝了同步（{code}）。",
     err_sync_failed="无法与 {url} 同步（{reason}）。",
     ev_start="对局开始", ev_win="{name} 获胜（+{pts} 积分）", ev_lose="{name} 失败（+{pts} 积分）",
     ev_draw="{name} 平局（+{pts} 积分）", ev_quit="{name} 离开了对局", ev_kill="目标已被杀害",
     ev_arrest="最终回合结束：犯人已被逮捕", ev_threat="出现了威胁",
     ev_gas="发生了燃气泄漏", ev_synced="资料已同步")

_add("zh-TW",
     progress_btn='我的進度', progress_title='我的進度', progress_desc='你的對局、勝場和積分儲存在這台電腦上。你可以把它們帶到另一台電腦，或保留一份副本以免遺失。', export_btn='匯出到檔案', import_btn='匯入檔案', backup_label='自動備份', backup_off='已關閉', backup_pick='選擇資料夾', backup_remove='關閉', backup_hint='提示：選擇你的 OneDrive、Google 雲端硬碟或 Dropbox 資料夾。每次工作階段結束都會儲存一份副本，在另一台電腦上選擇同一個資料夾，進度會自動恢復。', close='關閉', exported='進度已儲存到 {path}', imported='完成：已新增 {n} 場新對局。', import_nothing='該檔案中沒有你尚未擁有的對局。', err_save_bad='該檔案不是 CRIMESIGHT Revival 進度檔案。', err_save_other='該檔案屬於另一個 Steam 帳號。', err_save_write='無法儲存檔案（{err}）。', backup_set='已開啟自動備份。', backup_removed='已關閉自動備份。', backup_restored='已從備份恢復進度：{n} 場新對局。', backup_saved='進度已備份。', backup_failed='無法備份（{err}）。', err_backup_missing='找不到備份資料夾：{path}',
     updating='正在將啟動器更新至 {v} 版…', update_failed='無法更新（{err}），繼續使用目前版本。', kofi='在 Ko-fi 上支持我',
     loading="正在準備啟動器…",
     tagline="為已擁有遊戲的玩家架設的社群伺服器 · 不含任何 Konami 檔案",
     steam_account="Steam 帳號", no_steam="請開啟 Steam 並登入",
     wins="勝利", draws="平手", losses="落敗", points="點數",
     solo_title="單人遊玩", solo_desc="在你的電腦上與 AI 對戰。將 AI 踢出房間即可更改其難度。",
     host_title="擔任主機", host_desc="向好友開放你的對局。我會提供地址讓他們加入。",
     join_title="加入好友", join_desc="連線到好友的對局。你的進度會一起帶過去。",
     server_title="自架伺服器", server_desc="加入他人架設的伺服器，如有密碼請輸入。",
     solo_hint="將在你的電腦上啟動伺服器並開啟遊戲。建立房間後，空位會由 AI 補上。踢出 AI 即可更改其難度。",
     play_btn="開始遊戲", port="連接埠",
     host_hint="我會嘗試自動開啟路由器的連接埠。如果好友無法進入，請手動開啟，或使用 Tailscale、ZeroTier 或 Radmin VPN。",
     host_btn="開放對局", friend_addr="好友的地址", friend_ph="例如 83.45.120.7:18080", join_btn="加入",
     saved="已儲存", name="名稱", address="地址", server_ph="server.example.com:18080", password="密碼",
     save="儲存", delete="刪除", connect_btn="連線",
     session_running="工作階段進行中", copy="複製", stop_session="結束工作階段",
     game_path="遊戲：{path}", no_game="找不到 CRIMESIGHT：請選擇 CrimeSight.exe",
     change_folder="變更遊戲執行檔", restore_game="還原原版遊戲", revival_by="Revival 作者", contributions_by="貢獻者",
     copied="已複製地址", server_saved="已儲存伺服器",
     title_solo="單人對局", title_host="已向好友開放", title_join="已連線到好友", title_server="已連線到伺服器",
     err_busy="已有工作階段在進行中。", err_no_game="請先選擇遊戲的執行檔。",
     err_no_steam="請開啟 Steam 並以擁有 CRIMESIGHT 的帳號登入。", err_no_address="請輸入地址。",
     stopping="正在結束工作階段…", err_unexpected="意外錯誤：{err}",
     err_bad_folder="該檔案似乎不是 CRIMESIGHT 的執行檔（CrimeSight.exe）。",
     err_finish_first="請先結束工作階段。", restored="遊戲已還原為原始狀態。",
     already_original="遊戲已經是原始狀態。", err_need_address="請至少輸入地址。",
     loading_art="正在從你的遊戲副本準備插圖（僅限第一次）…",
     notice_imported="已匯入你在舊版本的對局紀錄。",
     srv_local_on="本機伺服器已啟動。", pointing="正在將遊戲指向 {url}",
     opening="正在啟動 CRIMESIGHT…", srv_stopped="伺服器已停止。下次見！",
     host_upnp="伺服器已開放。正在嘗試開啟路由器連接埠（UPnP）…", port_opened="已在路由器上開啟連接埠 {port}。",
     port_failed="路由器不允許自動開啟連接埠 {port}。請手動開啟（將 TCP 轉送到這台電腦），或使用私人網路（Tailscale、ZeroTier 或 Radmin VPN）並告知該網路的 IP。",
     give_address="請把這個地址告訴好友：{addr}   （同一家用網路：{lan}）",
     host_closed="已停止向好友開放，伺服器已停止。", checking="正在檢查 {url}…",
     need_password="該伺服器需要密碼：請使用「自架伺服器」。", syncing="正在與伺服器同步你的進度…",
     record="你的戰績：{w}勝 {d}平 {l}敗 · {p} 點", fetching="正在取回你的新對局…",
     sync_later="目前無法取回（{err}）。下次連線時會自動合併。",
     game_not_seen="沒有偵測到遊戲啟動；你也可以自己從 Steam 啟動。",
     game_open="遊戲正在執行。關閉遊戲即可結束工作階段。",
     err_empty_addr="請輸入地址。", err_not_revival="該地址有回應，但不是 CRIMESIGHT Revival 伺服器。",
     err_unreachable="無法連線到 {url}（{reason}）。伺服器是否已開啟、連接埠是否已開放？",
     err_password="該伺服器的密碼錯誤。", err_sync_rejected="伺服器拒絕了同步（{code}）。",
     err_sync_failed="無法與 {url} 同步（{reason}）。",
     ev_start="對局開始", ev_win="{name} 獲勝（+{pts} 點）", ev_lose="{name} 落敗（+{pts} 點）",
     ev_draw="{name} 平手（+{pts} 點）", ev_quit="{name} 離開了對局", ev_kill="目標已遭殺害",
     ev_arrest="最終回合結束：犯人已被逮捕", ev_threat="出現了威脅",
     ev_gas="發生了瓦斯外洩", ev_synced="個人資料已同步")

# --- appearance mods (new stickers and avatars) ------------------------------------------
_MODS = {
    "en": dict(
        mods_btn="Mods", mods_title="Mods",
        mods_desc="Add your own stamps and avatars. They're added as new ones: the game's originals are never changed.",
        mods_how_stickers="Put your stamp images (PNG, JPG…) in the “stamps” folder inside the mods folder. They're added to the game's stamps. Any size works: they're adjusted automatically.", mods_how_avatars="Put your avatar images (PNG, JPG…) in the “avatars” folder inside the mods folder. They're added to the game's avatars, to use as your profile picture. Any size works: they're adjusted automatically.",
        cursor_none="No custom cursor", cursor_on="Custom cursor on", cursor_off="Custom cursor off", cursor_desc_on="{size} · applied when you open the game from the launcher (or within a few seconds if it's already open). {extra} extra cursor(s).", cursor_desc_none="Choose an image (a transparent PNG works best) to use as the game's cursor. Only you can see it. Requires BepInEx.", cursor_hot_tip="Click point: tip (arrow)", cursor_hot_center="Click point: centre (crosshair)", cursor_hot_custom="Click point: custom", cursor_pick="Choose image…", cursor_folder="Folder", cursor_enable="Turn on", cursor_disable="Turn off", cursor_bad_image="That image can't be read ({err}).", mods_cursor="Custom cursor", mods_open="Open mods folder", mods_reload="Reload", mods_empty="Your mods folder is empty.",
        mods_count="{stickers} stamps · {avatars} avatars", mods_on="On", mods_off="Off", mods_by="by {author}",
        mods_bad_images="{n} images couldn't be read",
        mods_restart="Changes apply the next time you open the game from the launcher.",
        mods_installing="Installing mods: {stickers} stamps and {avatars} avatars…",
        mods_removed="Mods removed from the game.", mods_failed="Couldn't install the mods ({err}).",
        mods_download_failed="Couldn't download the room's mods ({err}).",
        mods_declined="You declined the room's mods, so you didn't join.",
        mods_downloading="Downloading the room's mods: {stickers} stamps and {avatars} avatars…",
        mods_temp_cleared="The room's temporary mods have been deleted.",
        mods_confirm_title="This room uses mods",
        mods_confirm_text="The host uses custom stamps and avatars. To join you need to download them: they're temporary and get deleted when you leave. Your own mods are paused meanwhile.",
        mods_confirm_yes="Download and join", mods_confirm_no="Don't join"),
    "es": dict(
        mods_btn="Mods", mods_title="Mods",
        mods_desc="Añade tus propios stickers y avatares. Son huecos nuevos: los del juego no se tocan nunca.",
        mods_how_stickers="Pon las imágenes de tus stickers (PNG, JPG…) en la carpeta “stamps” de la carpeta de mods. Se añaden a los stickers del juego. Sirve cualquier tamaño: se ajustan solas.", mods_how_avatars="Pon las imágenes de tus avatares (PNG, JPG…) en la carpeta “avatars” de la carpeta de mods. Se añaden a los avatares del juego, para usarlos como imagen de perfil. Sirve cualquier tamaño: se ajustan solas.",
        cursor_none="Sin cursor propio", cursor_on="Cursor propio activado", cursor_off="Cursor propio desactivado", cursor_desc_on="{size} · se aplica al abrir el juego desde el lanzador (o en unos segundos si ya está abierto). {extra} cursor(es) extra.", cursor_desc_none="Elige una imagen (mejor un PNG con transparencia) y será el cursor del juego. Solo lo ves tú. Necesita BepInEx.", cursor_hot_tip="Clic: punta (flecha)", cursor_hot_center="Clic: centro (mira)", cursor_hot_custom="Clic: personalizado", cursor_pick="Elegir imagen…", cursor_folder="Carpeta", cursor_enable="Activar", cursor_disable="Desactivar", cursor_bad_image="No se puede leer esa imagen ({err}).", mods_cursor="Cursor propio", mods_open="Abrir carpeta de mods", mods_reload="Recargar", mods_empty="Tu carpeta de mods está vacía.",
        mods_count="{stickers} stickers · {avatars} avatares", mods_on="Activado", mods_off="Desactivado",
        mods_by="de {author}", mods_bad_images="{n} imágenes no se han podido leer",
        mods_restart="Los cambios se aplican la próxima vez que abras el juego desde el lanzador.",
        mods_installing="Instalando mods: {stickers} stickers y {avatars} avatares…",
        mods_removed="Mods quitados del juego.", mods_failed="No se pudieron instalar los mods ({err}).",
        mods_download_failed="No se pudieron descargar los mods de la sala ({err}).",
        mods_declined="No has aceptado los mods de la sala, así que no te has unido.",
        mods_downloading="Descargando los mods de la sala: {stickers} stickers y {avatars} avatares…",
        mods_temp_cleared="Mods temporales de la sala borrados.",
        mods_confirm_title="Esta sala usa mods",
        mods_confirm_text="El anfitrión usa stickers y avatares personalizados. Para unirte tienes que descargarlos: son temporales y se borran al salir. Mientras tanto, tus mods quedan en pausa.",
        mods_confirm_yes="Descargar y unirme", mods_confirm_no="No unirme"),
    "fr": dict(
        mods_btn="Mods", mods_title="Mods",
        mods_desc="Ajoutez vos propres stickers et avatars. Ce sont de nouveaux emplacements : ceux du jeu ne sont jamais modifiés.",
        mods_how_stickers="Mettez les images de vos stickers (PNG, JPG…) dans le dossier « stamps » du dossier des mods. Elles s'ajoutent aux stickers du jeu. Toutes les tailles conviennent : elles sont ajustées automatiquement.", mods_how_avatars="Mettez les images de vos avatars (PNG, JPG…) dans le dossier « avatars » du dossier des mods. Elles s'ajoutent aux avatars du jeu, comme image de profil. Toutes les tailles conviennent : elles sont ajustées automatiquement.",
        cursor_none="Pas de curseur perso", cursor_on="Curseur perso activé", cursor_off="Curseur perso désactivé", cursor_desc_on="{size} · appliqué en ouvrant le jeu depuis le lanceur (ou en quelques secondes s'il est déjà ouvert). {extra} curseur(s) en plus.", cursor_desc_none="Choisissez une image (de préférence un PNG transparent) et ce sera le curseur du jeu. Vous seul le voyez. Nécessite BepInEx.", cursor_hot_tip="Clic : pointe (flèche)", cursor_hot_center="Clic : centre (viseur)", cursor_hot_custom="Clic : personnalisé", cursor_pick="Choisir une image…", cursor_folder="Dossier", cursor_enable="Activer", cursor_disable="Désactiver", cursor_bad_image="Impossible de lire cette image ({err}).", mods_cursor="Curseur perso", mods_open="Ouvrir le dossier des mods", mods_reload="Actualiser", mods_empty="Votre dossier des mods est vide.",
        mods_count="{stickers} stickers · {avatars} avatars", mods_on="Activé", mods_off="Désactivé",
        mods_by="par {author}", mods_bad_images="{n} images n'ont pas pu être lues",
        mods_restart="Les changements s'appliquent la prochaine fois que vous ouvrez le jeu depuis le lanceur.",
        mods_installing="Installation des mods : {stickers} stickers et {avatars} avatars…",
        mods_removed="Mods retirés du jeu.", mods_failed="Impossible d'installer les mods ({err}).",
        mods_download_failed="Impossible de télécharger les mods du salon ({err}).",
        mods_declined="Vous n'avez pas accepté les mods du salon, vous ne l'avez donc pas rejoint.",
        mods_downloading="Téléchargement des mods du salon : {stickers} stickers et {avatars} avatars…",
        mods_temp_cleared="Les mods temporaires du salon ont été supprimés.",
        mods_confirm_title="Ce salon utilise des mods",
        mods_confirm_text="L'hôte utilise des stickers et des avatars personnalisés. Pour rejoindre, vous devez les télécharger : ils sont temporaires et supprimés quand vous partez. Vos propres mods sont mis en pause en attendant.",
        mods_confirm_yes="Télécharger et rejoindre", mods_confirm_no="Ne pas rejoindre"),
    "it": dict(
        mods_btn="Mod", mods_title="Mod",
        mods_desc="Aggiungi i tuoi sticker e avatar. Sono spazi nuovi: quelli del gioco non vengono mai modificati.",
        mods_how_stickers="Metti le immagini dei tuoi sticker (PNG, JPG…) nella cartella “stamps” della cartella dei mod. Si aggiungono agli sticker del gioco. Va bene qualsiasi dimensione: vengono adattate da sole.", mods_how_avatars="Metti le immagini dei tuoi avatar (PNG, JPG…) nella cartella “avatars” della cartella dei mod. Si aggiungono agli avatar del gioco, da usare come immagine del profilo. Va bene qualsiasi dimensione: vengono adattate da sole.",
        cursor_none="Nessun cursore personalizzato", cursor_on="Cursore personalizzato attivo", cursor_off="Cursore personalizzato disattivato", cursor_desc_on="{size} · si applica aprendo il gioco dal launcher (o in pochi secondi se è già aperto). {extra} cursore/i extra.", cursor_desc_none="Scegli un'immagine (meglio un PNG trasparente) e diventerà il cursore del gioco. Lo vedi solo tu. Serve BepInEx.", cursor_hot_tip="Clic: punta (freccia)", cursor_hot_center="Clic: centro (mirino)", cursor_hot_custom="Clic: personalizzato", cursor_pick="Scegli immagine…", cursor_folder="Cartella", cursor_enable="Attiva", cursor_disable="Disattiva", cursor_bad_image="Impossibile leggere l'immagine ({err}).", mods_cursor="Cursore personalizzato", mods_open="Apri la cartella dei mod", mods_reload="Ricarica", mods_empty="La tua cartella dei mod è vuota.",
        mods_count="{stickers} sticker · {avatars} avatar", mods_on="Attivo", mods_off="Disattivato",
        mods_by="di {author}", mods_bad_images="{n} immagini non sono leggibili",
        mods_restart="Le modifiche si applicano la prossima volta che apri il gioco dal launcher.",
        mods_installing="Installazione dei mod: {stickers} sticker e {avatars} avatar…",
        mods_removed="Mod rimossi dal gioco.", mods_failed="Impossibile installare i mod ({err}).",
        mods_download_failed="Impossibile scaricare i mod della stanza ({err}).",
        mods_declined="Non hai accettato i mod della stanza, quindi non sei entrato.",
        mods_downloading="Download dei mod della stanza: {stickers} sticker e {avatars} avatar…",
        mods_temp_cleared="Mod temporanei della stanza eliminati.",
        mods_confirm_title="Questa stanza usa dei mod",
        mods_confirm_text="L'host usa sticker e avatar personalizzati. Per entrare devi scaricarli: sono temporanei e vengono eliminati quando esci. Nel frattempo i tuoi mod restano in pausa.",
        mods_confirm_yes="Scarica ed entra", mods_confirm_no="Non entrare"),
    "de": dict(
        mods_btn="Mods", mods_title="Mods",
        mods_desc="Füge eigene Sticker und Avatare hinzu. Es sind neue Plätze: Die des Spiels werden nie verändert.",
        mods_how_stickers="Lege deine Sticker-Bilder (PNG, JPG…) in den Ordner „stamps“ im Mod-Ordner. Sie kommen zu den Stickern des Spiels dazu. Jede Größe funktioniert: Sie werden automatisch angepasst.", mods_how_avatars="Lege deine Avatar-Bilder (PNG, JPG…) in den Ordner „avatars“ im Mod-Ordner. Sie kommen zu den Avataren des Spiels dazu, als Profilbild. Jede Größe funktioniert: Sie werden automatisch angepasst.",
        cursor_none="Kein eigener Cursor", cursor_on="Eigener Cursor an", cursor_off="Eigener Cursor aus", cursor_desc_on="{size} · wird beim Start des Spiels über den Launcher angewendet (oder in Sekunden, wenn es schon läuft). {extra} weitere Cursor.", cursor_desc_none="Wähle ein Bild (am besten ein transparentes PNG) und es wird zum Cursor des Spiels. Nur du siehst ihn. Braucht BepInEx.", cursor_hot_tip="Klick: Spitze (Pfeil)", cursor_hot_center="Klick: Mitte (Fadenkreuz)", cursor_hot_custom="Klick: eigener", cursor_pick="Bild wählen…", cursor_folder="Ordner", cursor_enable="Einschalten", cursor_disable="Ausschalten", cursor_bad_image="Das Bild kann nicht gelesen werden ({err}).", mods_cursor="Eigener Cursor", mods_open="Mod-Ordner öffnen", mods_reload="Neu laden", mods_empty="Dein Mod-Ordner ist leer.",
        mods_count="{stickers} Sticker · {avatars} Avatare", mods_on="An", mods_off="Aus",
        mods_by="von {author}", mods_bad_images="{n} Bilder konnten nicht gelesen werden",
        mods_restart="Änderungen gelten ab dem nächsten Spielstart über den Launcher.",
        mods_installing="Mods werden installiert: {stickers} Sticker und {avatars} Avatare…",
        mods_removed="Mods aus dem Spiel entfernt.", mods_failed="Die Mods konnten nicht installiert werden ({err}).",
        mods_download_failed="Die Mods des Raums konnten nicht heruntergeladen werden ({err}).",
        mods_declined="Du hast die Mods des Raums nicht angenommen, daher bist du nicht beigetreten.",
        mods_downloading="Mods des Raums werden heruntergeladen: {stickers} Sticker und {avatars} Avatare…",
        mods_temp_cleared="Temporäre Mods des Raums gelöscht.",
        mods_confirm_title="Dieser Raum nutzt Mods",
        mods_confirm_text="Der Host nutzt eigene Sticker und Avatare. Zum Beitreten musst du sie herunterladen: Sie sind temporär und werden beim Verlassen gelöscht. Deine eigenen Mods pausieren solange.",
        mods_confirm_yes="Herunterladen und beitreten", mods_confirm_no="Nicht beitreten"),
    "pt": dict(
        mods_btn="Mods", mods_title="Mods",
        mods_desc="Adicione seus próprios emojis e avatares. São espaços novos: os do jogo nunca são alterados.",
        mods_how_stickers="Coloque as imagens dos seus emojis (PNG, JPG…) na pasta “stamps” da pasta de mods. Elas se somam aos emojis do jogo. Qualquer tamanho serve: elas são ajustadas sozinhas.", mods_how_avatars="Coloque as imagens dos seus avatares (PNG, JPG…) na pasta “avatars” da pasta de mods. Elas se somam aos avatares do jogo, para usar como foto de perfil. Qualquer tamanho serve: elas são ajustadas sozinhas.",
        cursor_none="Sem cursor próprio", cursor_on="Cursor próprio ativado", cursor_off="Cursor próprio desativado", cursor_desc_on="{size} · aplicado ao abrir o jogo pelo lançador (ou em segundos se já estiver aberto). {extra} cursor(es) extra.", cursor_desc_none="Escolha uma imagem (de preferência um PNG transparente) e ela será o cursor do jogo. Só você vê. Precisa do BepInEx.", cursor_hot_tip="Clique: ponta (seta)", cursor_hot_center="Clique: centro (mira)", cursor_hot_custom="Clique: personalizado", cursor_pick="Escolher imagem…", cursor_folder="Pasta", cursor_enable="Ativar", cursor_disable="Desativar", cursor_bad_image="Não foi possível ler a imagem ({err}).", mods_cursor="Cursor próprio", mods_open="Abrir pasta de mods", mods_reload="Recarregar", mods_empty="Sua pasta de mods está vazia.",
        mods_count="{stickers} emojis · {avatars} avatares", mods_on="Ativado", mods_off="Desativado",
        mods_by="de {author}", mods_bad_images="{n} imagens não puderam ser lidas",
        mods_restart="As mudanças valem a partir da próxima vez que abrir o jogo pelo launcher.",
        mods_installing="Instalando mods: {stickers} emojis e {avatars} avatares…",
        mods_removed="Mods removidos do jogo.", mods_failed="Não foi possível instalar os mods ({err}).",
        mods_download_failed="Não foi possível baixar os mods da sala ({err}).",
        mods_declined="Você não aceitou os mods da sala, então não entrou.",
        mods_downloading="Baixando os mods da sala: {stickers} emojis e {avatars} avatares…",
        mods_temp_cleared="Mods temporários da sala apagados.",
        mods_confirm_title="Esta sala usa mods",
        mods_confirm_text="O anfitrião usa emojis e avatares personalizados. Para entrar, você precisa baixá-los: são temporários e apagados quando você sai. Enquanto isso, seus mods ficam pausados.",
        mods_confirm_yes="Baixar e entrar", mods_confirm_no="Não entrar"),
    "ru": dict(
        mods_btn="Моды", mods_title="Моды",
        mods_desc="Добавляйте свои шаблоны и аватары. Это новые слоты: игровые никогда не меняются.",
        mods_how_stickers="Положите картинки шаблонов (PNG, JPG…) в папку «stamps» в папке модов. Они добавятся к шаблонам игры. Подойдёт любой размер: картинки подгоняются сами.", mods_how_avatars="Положите картинки аватаров (PNG, JPG…) в папку «avatars» в папке модов. Они добавятся к аватарам игры, для фото профиля. Подойдёт любой размер: картинки подгоняются сами.",
        cursor_none="Свой курсор не задан", cursor_on="Свой курсор включён", cursor_off="Свой курсор выключен", cursor_desc_on="{size} · применяется при запуске игры из лаунчера (или через пару секунд, если она уже открыта). Доп. курсоров: {extra}.", cursor_desc_none="Выберите картинку (лучше PNG с прозрачностью), и она станет курсором игры. Видите только вы. Нужен BepInEx.", cursor_hot_tip="Клик: кончик (стрелка)", cursor_hot_center="Клик: центр (прицел)", cursor_hot_custom="Клик: свой", cursor_pick="Выбрать картинку…", cursor_folder="Папка", cursor_enable="Включить", cursor_disable="Выключить", cursor_bad_image="Не удаётся прочитать картинку ({err}).", mods_cursor="Свой курсор", mods_open="Открыть папку модов", mods_reload="Обновить", mods_empty="Папка модов пуста.",
        mods_count="Шаблоны: {stickers} · аватары: {avatars}", mods_on="Вкл.", mods_off="Выкл.",
        mods_by="автор: {author}", mods_bad_images="Не удалось прочитать изображений: {n}",
        mods_restart="Изменения вступят в силу при следующем запуске игры из лаунчера.",
        mods_installing="Установка модов: шаблоны — {stickers}, аватары — {avatars}…",
        mods_removed="Моды удалены из игры.", mods_failed="Не удалось установить моды ({err}).",
        mods_download_failed="Не удалось скачать моды комнаты ({err}).",
        mods_declined="Вы не приняли моды комнаты, поэтому не присоединились.",
        mods_downloading="Скачивание модов комнаты: шаблоны — {stickers}, аватары — {avatars}…",
        mods_temp_cleared="Временные моды комнаты удалены.",
        mods_confirm_title="В этой комнате есть моды",
        mods_confirm_text="Хост использует свои шаблоны и аватары. Чтобы присоединиться, их нужно скачать: они временные и удаляются, когда вы выходите. Ваши моды пока будут приостановлены.",
        mods_confirm_yes="Скачать и войти", mods_confirm_no="Не входить"),
    "ja": dict(
        mods_btn="MOD", mods_title="MOD",
        mods_desc="自分だけのスタンプやアバターを追加できます。新しい枠として追加されるので、ゲーム本来のものは一切変更されません。",
        mods_how_stickers="スタンプの画像（PNG、JPGなど）をMODフォルダの中の「stamps」フォルダに入れてください。ゲームのスタンプに追加されます。サイズは自動で調整されます。", mods_how_avatars="アバターの画像（PNG、JPGなど）をMODフォルダの中の「avatars」フォルダに入れてください。ゲームのアバターに追加され、プロフィール画像に使えます。サイズは自動で調整されます。",
        cursor_none="カスタムカーソルなし", cursor_on="カスタムカーソル：オン", cursor_off="カスタムカーソル：オフ", cursor_desc_on="{size} · ランチャーからゲームを開くと適用されます（起動中なら数秒で反映）。追加カーソル：{extra}", cursor_desc_none="画像（透過PNGがおすすめ）を選ぶとゲームのカーソルになります。自分にだけ表示されます。BepInExが必要です。", cursor_hot_tip="クリック位置：先端（矢印）", cursor_hot_center="クリック位置：中央（照準）", cursor_hot_custom="クリック位置：カスタム", cursor_pick="画像を選ぶ…", cursor_folder="フォルダ", cursor_enable="オンにする", cursor_disable="オフにする", cursor_bad_image="画像を読み込めません（{err}）。", mods_cursor="カーソル変更", mods_open="MODフォルダを開く", mods_reload="再読み込み", mods_empty="MODフォルダは空です。",
        mods_count="スタンプ {stickers} · アバター {avatars}", mods_on="オン", mods_off="オフ",
        mods_by="作者：{author}", mods_bad_images="{n} 枚の画像を読み込めませんでした",
        mods_restart="変更は次にランチャーからゲームを起動したときに反映されます。",
        mods_installing="MODをインストール中：スタンプ {stickers}、アバター {avatars}…",
        mods_removed="ゲームからMODを外しました。", mods_failed="MODをインストールできませんでした（{err}）。",
        mods_download_failed="ルームのMODをダウンロードできませんでした（{err}）。",
        mods_declined="ルームのMODを承認しなかったため、参加していません。",
        mods_downloading="ルームのMODをダウンロード中：スタンプ {stickers}、アバター {avatars}…",
        mods_temp_cleared="ルームの一時MODを削除しました。",
        mods_confirm_title="このルームはMODを使用しています",
        mods_confirm_text="ホストはオリジナルのスタンプとアバターを使用しています。参加するにはダウンロードが必要です。これらは一時的なもので、退出すると削除されます。その間、あなたのMODは一時停止されます。",
        mods_confirm_yes="ダウンロードして参加", mods_confirm_no="参加しない"),
    "ko": dict(
        mods_btn="모드", mods_title="모드",
        mods_desc="나만의 스탬프와 아바타를 추가하세요. 새 슬롯으로 추가되므로 게임 원래의 것은 절대 바뀌지 않습니다.",
        mods_how_stickers="스탬프 이미지(PNG, JPG 등)를 모드 폴더 안의 “stamps” 폴더에 넣으세요. 게임의 스탬프에 추가됩니다. 크기는 자동으로 맞춰집니다.", mods_how_avatars="아바타 이미지(PNG, JPG 등)를 모드 폴더 안의 “avatars” 폴더에 넣으세요. 게임의 아바타에 추가되어 프로필 이미지로 쓸 수 있습니다. 크기는 자동으로 맞춰집니다.",
        cursor_none="사용자 커서 없음", cursor_on="사용자 커서 켜짐", cursor_off="사용자 커서 꺼짐", cursor_desc_on="{size} · 런처에서 게임을 열면 적용됩니다(이미 열려 있으면 몇 초 안에). 추가 커서 {extra}개.", cursor_desc_none="이미지(투명 PNG 권장)를 고르면 게임 커서가 됩니다. 나만 보입니다. BepInEx가 필요합니다.", cursor_hot_tip="클릭: 끝(화살표)", cursor_hot_center="클릭: 가운데(조준)", cursor_hot_custom="클릭: 사용자 지정", cursor_pick="이미지 선택…", cursor_folder="폴더", cursor_enable="켜기", cursor_disable="끄기", cursor_bad_image="이미지를 읽을 수 없습니다 ({err}).", mods_cursor="커서 변경", mods_open="모드 폴더 열기", mods_reload="새로고침", mods_empty="모드 폴더가 비어 있습니다.",
        mods_count="스탬프 {stickers} · 아바타 {avatars}", mods_on="켜짐", mods_off="꺼짐",
        mods_by="제작: {author}", mods_bad_images="이미지 {n}개를 읽지 못했습니다",
        mods_restart="변경 사항은 다음에 런처로 게임을 열 때 적용됩니다.",
        mods_installing="모드 설치 중: 스탬프 {stickers}개, 아바타 {avatars}개…",
        mods_removed="게임에서 모드를 제거했습니다.", mods_failed="모드를 설치하지 못했습니다 ({err}).",
        mods_download_failed="방의 모드를 내려받지 못했습니다 ({err}).",
        mods_declined="방의 모드를 수락하지 않아 참가하지 않았습니다.",
        mods_downloading="방의 모드를 내려받는 중: 스탬프 {stickers}개, 아바타 {avatars}개…",
        mods_temp_cleared="방의 임시 모드를 삭제했습니다.",
        mods_confirm_title="이 방은 모드를 사용합니다",
        mods_confirm_text="호스트가 커스텀 스탬프와 아바타를 사용합니다. 참가하려면 내려받아야 하며, 임시 파일이라 나가면 삭제됩니다. 그동안 내 모드는 일시 중지됩니다.",
        mods_confirm_yes="내려받고 참가", mods_confirm_no="참가 안 함"),
    "zh-CN": dict(
        mods_btn="模组", mods_title="模组",
        mods_desc="添加你自己的表情和头像。它们是新增的栏位，游戏原有的内容永远不会被改动。",
        mods_how_stickers="把表情图片（PNG、JPG 等）放进模组文件夹里的“stamps”文件夹。它们会加入游戏的表情中。任何尺寸都可以，会自动调整。", mods_how_avatars="把头像图片（PNG、JPG 等）放进模组文件夹里的“avatars”文件夹。它们会加入游戏的头像中，可用作个人资料图片。任何尺寸都可以，会自动调整。",
        cursor_none="未设置自定义光标", cursor_on="自定义光标：开", cursor_off="自定义光标：关", cursor_desc_on="{size} · 从启动器打开游戏时生效（若游戏已打开，几秒内生效）。额外光标：{extra} 个。", cursor_desc_none="选择一张图片（最好是透明 PNG），它就会成为游戏光标。只有你能看到。需要 BepInEx。", cursor_hot_tip="点击点：尖端（箭头）", cursor_hot_center="点击点：中心（准星）", cursor_hot_custom="点击点：自定义", cursor_pick="选择图片…", cursor_folder="文件夹", cursor_enable="开启", cursor_disable="关闭", cursor_bad_image="无法读取该图片（{err}）。", mods_cursor="自定义光标", mods_open="打开模组文件夹", mods_reload="重新加载", mods_empty="你的模组文件夹是空的。",
        mods_count="表情 {stickers} · 头像 {avatars}", mods_on="已启用", mods_off="已停用",
        mods_by="作者：{author}", mods_bad_images="有 {n} 张图片无法读取",
        mods_restart="更改会在下次从启动器打开游戏时生效。",
        mods_installing="正在安装模组：表情 {stickers} 个，头像 {avatars} 个…",
        mods_removed="已从游戏中移除模组。", mods_failed="无法安装模组（{err}）。",
        mods_download_failed="无法下载房间的模组（{err}）。",
        mods_declined="你没有接受房间的模组，因此没有加入。",
        mods_downloading="正在下载房间的模组：表情 {stickers} 个，头像 {avatars} 个…",
        mods_temp_cleared="已删除该房间的临时模组。",
        mods_confirm_title="这个房间使用了模组",
        mods_confirm_text="房主使用了自定义表情和头像。要加入就需要下载它们：这些是临时文件，离开后会被删除。在此期间你自己的模组会暂停。",
        mods_confirm_yes="下载并加入", mods_confirm_no="不加入"),
    "zh-TW": dict(
        mods_btn="模組", mods_title="模組",
        mods_desc="加入你自己的貼圖和頭像。它們是新增的欄位，遊戲原有的內容永遠不會被更動。",
        mods_how_stickers="把貼圖圖片（PNG、JPG 等）放進模組資料夾裡的「stamps」資料夾。它們會加入遊戲的貼圖中。任何尺寸都可以，會自動調整。", mods_how_avatars="把頭像圖片（PNG、JPG 等）放進模組資料夾裡的「avatars」資料夾。它們會加入遊戲的頭像中，可用作個人資料圖片。任何尺寸都可以，會自動調整。",
        cursor_none="未設定自訂游標", cursor_on="自訂游標：開", cursor_off="自訂游標：關", cursor_desc_on="{size} · 從啟動器開啟遊戲時生效（若遊戲已開啟，幾秒內生效）。額外游標：{extra} 個。", cursor_desc_none="選擇一張圖片（最好是透明 PNG），它就會成為遊戲游標。只有你看得到。需要 BepInEx。", cursor_hot_tip="點擊點：尖端（箭頭）", cursor_hot_center="點擊點：中心（準星）", cursor_hot_custom="點擊點：自訂", cursor_pick="選擇圖片…", cursor_folder="資料夾", cursor_enable="開啟", cursor_disable="關閉", cursor_bad_image="無法讀取該圖片（{err}）。", mods_cursor="自訂游標", mods_open="開啟模組資料夾", mods_reload="重新載入", mods_empty="你的模組資料夾是空的。",
        mods_count="貼圖 {stickers} · 頭像 {avatars}", mods_on="已啟用", mods_off="已停用",
        mods_by="作者：{author}", mods_bad_images="有 {n} 張圖片無法讀取",
        mods_restart="變更會在下次從啟動器開啟遊戲時生效。",
        mods_installing="正在安裝模組：貼圖 {stickers} 個，頭像 {avatars} 個…",
        mods_removed="已從遊戲中移除模組。", mods_failed="無法安裝模組（{err}）。",
        mods_download_failed="無法下載房間的模組（{err}）。",
        mods_declined="你沒有接受房間的模組，因此沒有加入。",
        mods_downloading="正在下載房間的模組：貼圖 {stickers} 個，頭像 {avatars} 個…",
        mods_temp_cleared="已刪除該房間的暫時模組。",
        mods_confirm_title="這個房間使用了模組",
        mods_confirm_text="房主使用了自訂貼圖和頭像。要加入就需要下載它們：這些是暫時檔案，離開後會被刪除。在此期間你自己的模組會暫停。",
        mods_confirm_yes="下載並加入", mods_confirm_no="不加入"),
}
for _l, _d in _MODS.items():
    S[_l].update(_d)
_ROOT = {"en": "Mods", "es": "Mods", "fr": "Mods", "it": "Mod",
         "de": "Mods", "pt": "Mods", "ru": "Моды", "ja": "MOD",
         "ko": "모드", "zh-CN": "模组", "zh-TW": "模組"}
for _l, _v in _ROOT.items():
    S[_l]["mods_root"] = _v

_TEXT_HINT = {
    "en": "Stamps don't show a message in the match unless you give them one with the “Messages” button. A number at the start of the file name (01_) only sets the order.",
    "es": "Los stickers no muestran ningún mensaje en la partida salvo que les pongas uno con el botón “Mensajes”. Un número al principio del nombre del archivo (01_) solo sirve para ordenar.",
    "fr": "Les stickers n'affichent aucun message en partie, sauf si vous leur en donnez un avec le bouton « Messages ». Un numéro au début du nom du fichier (01_) sert seulement à l'ordre.",
    "it": "Gli sticker non mostrano nessun messaggio in partita, a meno che tu non gliene dia uno con il pulsante “Messaggi”. Un numero all'inizio del nome del file (01_) serve solo per l'ordine.",
    "de": "Sticker zeigen im Spiel keine Nachricht, außer du gibst ihnen eine über die Schaltfläche „Nachrichten“. Eine Zahl am Anfang des Dateinamens (01_) legt nur die Reihenfolge fest.",
    "pt": "Os emojis não mostram nenhuma mensagem na partida, a menos que você dê uma a eles com o botão “Mensagens”. Um número no início do nome do arquivo (01_) só serve para ordenar.",
    "ru": "Шаблоны не показывают сообщение в матче, если вы не зададите его кнопкой «Сообщения». Число в начале имени файла (01_) нужно только для порядка.",
    "ja": "「メッセージ」ボタンで設定しない限り、スタンプは試合中にメッセージを表示しません。ファイル名の先頭の番号（01_）は並び順にだけ使われます。",
    "ko": "“메시지” 버튼으로 정하지 않으면 스탬프는 게임 중에 메시지를 표시하지 않습니다. 파일 이름 앞의 숫자(01_)는 순서에만 쓰입니다.",
    "zh-CN": "除非用“消息”按钮设置，表情在对局中不会显示消息。文件名开头的数字（01_）只用于排序。",
    "zh-TW": "除非用「訊息」按鈕設定，貼圖在對局中不會顯示訊息。檔名開頭的數字（01_）只用於排序。",
}
for _l, _v in _TEXT_HINT.items():
    S[_l]["mods_text_hint"] = _v

# --- hot reload with BepInEx (on by default: the launcher installs it by itself)
# -----------------------------------------------
_BEP = {
    "en": dict(bep_title="Hot reload", bep_desc="BepInEx is a mod loader that shows mod changes without restarting the game and enables the custom cursor, 3D models and custom scenarios. The launcher downloads it for you (34 MB); you can remove it at any time.",
               bep_status_off="Off", bep_status_on="On", bep_status_first="On · the game will take about a minute to start next time (first time only)",
               bep_enable="Turn on", bep_disable="Remove BepInEx", bep_installing="Downloading BepInEx… {pct}%", bep_installed="Hot reload turned on.",
               bep_removed="BepInEx removed: the game is back to normal.", bep_download_failed="Couldn't download BepInEx ({err}).",
               bep_no_plugin="This launcher doesn't include the mods plugin.", bep_busy="Close the game first.",
               mods_live_restart="Hot reload is on: changes appear in the game automatically (if you're in a match, once you're back in the menu).",
               mods_live_updated="Mods updated in the game.", mods_host_changed="The host changed their mods: restart the game to see them (or turn on hot reload)."),
    "es": dict(bep_title="Recarga en caliente", bep_desc="BepInEx es un cargador de mods que muestra los cambios sin reiniciar el juego y activa el cursor propio, los modelos 3D y los escenarios personalizados. El lanzador lo descarga por ti (34 MB); puedes quitarlo cuando quieras.",
               bep_status_off="Desactivada", bep_status_on="Activada", bep_status_first="Activada · el próximo arranque del juego tarda un minuto (solo la primera vez)",
               bep_enable="Activar", bep_disable="Quitar BepInEx", bep_installing="Descargando BepInEx… {pct}%", bep_installed="Recarga en caliente activada.",
               bep_removed="BepInEx quitado: el juego vuelve a estar como siempre.", bep_download_failed="No se pudo descargar BepInEx ({err}).",
               bep_no_plugin="Este lanzador no trae el plugin de mods.", bep_busy="Cierra antes el juego.",
               mods_live_restart="Recarga en caliente activada: los cambios aparecen solos en el juego (si estás en una partida, al volver al menú).",
               mods_live_updated="Mods actualizados en el juego.", mods_host_changed="El anfitrión ha cambiado sus mods: vuelve a abrir el juego para verlos (o activa la recarga en caliente)."),
    "fr": dict(bep_title="Rechargement à chaud", bep_desc="BepInEx est un chargeur de mods qui affiche les changements sans redémarrer le jeu et active le curseur perso, les modèles 3D et les scénarios personnalisés. Le lanceur le télécharge pour vous (34 Mo) ; vous pouvez le retirer à tout moment.",
               bep_status_off="Désactivé", bep_status_on="Activé", bep_status_first="Activé · le prochain lancement du jeu prend environ une minute (la première fois seulement)",
               bep_enable="Activer", bep_disable="Retirer BepInEx", bep_installing="Téléchargement de BepInEx… {pct}%", bep_installed="Rechargement à chaud activé.",
               bep_removed="BepInEx retiré : le jeu est revenu à la normale.", bep_download_failed="Impossible de télécharger BepInEx ({err}).",
               bep_no_plugin="Ce lanceur n'inclut pas le plugin des mods.", bep_busy="Fermez d'abord le jeu.",
               mods_live_restart="Rechargement à chaud activé : les changements apparaissent seuls en jeu (en partie, au retour au menu).",
               mods_live_updated="Mods mis à jour en jeu.", mods_host_changed="L'hôte a changé ses mods : relancez le jeu pour les voir (ou activez le rechargement à chaud)."),
    "it": dict(bep_title="Ricarica a caldo", bep_desc="BepInEx è un caricatore di mod che mostra le modifiche senza riavviare il gioco e attiva il cursore personalizzato, i modelli 3D e gli scenari personalizzati. Il launcher lo scarica per te (34 MB); puoi rimuoverlo quando vuoi.",
               bep_status_off="Disattivata", bep_status_on="Attiva", bep_status_first="Attiva · il prossimo avvio del gioco richiede circa un minuto (solo la prima volta)",
               bep_enable="Attiva", bep_disable="Rimuovi BepInEx", bep_installing="Download di BepInEx… {pct}%", bep_installed="Ricarica a caldo attivata.",
               bep_removed="BepInEx rimosso: il gioco è tornato come prima.", bep_download_failed="Impossibile scaricare BepInEx ({err}).",
               bep_no_plugin="Questo launcher non include il plugin dei mod.", bep_busy="Chiudi prima il gioco.",
               mods_live_restart="Ricarica a caldo attiva: le modifiche compaiono da sole nel gioco (se sei in partita, al ritorno al menu).",
               mods_live_updated="Mod aggiornati nel gioco.", mods_host_changed="L'host ha cambiato i suoi mod: riapri il gioco per vederli (o attiva la ricarica a caldo)."),
    "de": dict(bep_title="Hot Reload", bep_desc="BepInEx ist ein Mod-Loader, der Änderungen ohne Neustart des Spiels anzeigt und den eigenen Cursor, 3D-Modelle und eigene Szenarien ermöglicht. Der Launcher lädt es für dich herunter (34 MB); du kannst es jederzeit entfernen.",
               bep_status_off="Aus", bep_status_on="An", bep_status_first="An · der nächste Spielstart dauert etwa eine Minute (nur beim ersten Mal)",
               bep_enable="Aktivieren", bep_disable="BepInEx entfernen", bep_installing="BepInEx wird heruntergeladen… {pct}%", bep_installed="Hot Reload aktiviert.",
               bep_removed="BepInEx entfernt: Das Spiel ist wieder wie vorher.", bep_download_failed="BepInEx konnte nicht heruntergeladen werden ({err}).",
               bep_no_plugin="Dieser Launcher enthält das Mod-Plugin nicht.", bep_busy="Schließe zuerst das Spiel.",
               mods_live_restart="Hot Reload ist an: Änderungen erscheinen von selbst im Spiel (im Match erst zurück im Menü).",
               mods_live_updated="Mods im Spiel aktualisiert.", mods_host_changed="Der Host hat seine Mods geändert: Starte das Spiel neu, um sie zu sehen (oder aktiviere Hot Reload)."),
    "pt": dict(bep_title="Recarga instantânea", bep_desc="BepInEx é um carregador de mods que mostra as mudanças sem reiniciar o jogo e ativa o cursor próprio, os modelos 3D e os cenários personalizados. O lançador o baixa para você (34 MB); você pode removê-lo quando quiser.",
               bep_status_off="Desativada", bep_status_on="Ativada", bep_status_first="Ativada · a próxima abertura do jogo leva cerca de um minuto (só na primeira vez)",
               bep_enable="Ativar", bep_disable="Remover BepInEx", bep_installing="Baixando o BepInEx… {pct}%", bep_installed="Recarga instantânea ativada.",
               bep_removed="BepInEx removido: o jogo voltou ao normal.", bep_download_failed="Não foi possível baixar o BepInEx ({err}).",
               bep_no_plugin="Este launcher não inclui o plugin de mods.", bep_busy="Feche o jogo primeiro.",
               mods_live_restart="Recarga instantânea ativada: as mudanças aparecem sozinhas no jogo (numa partida, ao voltar ao menu).",
               mods_live_updated="Mods atualizados no jogo.", mods_host_changed="O anfitrião mudou os mods: reabra o jogo para vê-los (ou ative a recarga instantânea)."),
    "ru": dict(bep_title="Горячая перезагрузка", bep_desc="BepInEx — загрузчик модов: изменения появляются без перезапуска игры, а также работают свой курсор, 3D-модели и свои сценарии. Лаунчер скачает его сам (34 МБ); удалить его можно в любой момент.",
               bep_status_off="Выкл.", bep_status_on="Вкл.", bep_status_first="Вкл. · следующий запуск игры займёт около минуты (только в первый раз)",
               bep_enable="Включить", bep_disable="Удалить BepInEx", bep_installing="Скачивание BepInEx… {pct}%", bep_installed="Горячая перезагрузка включена.",
               bep_removed="BepInEx удалён: игра снова как обычно.", bep_download_failed="Не удалось скачать BepInEx ({err}).",
               bep_no_plugin="В этом лаунчере нет плагина модов.", bep_busy="Сначала закройте игру.",
               mods_live_restart="Горячая перезагрузка включена: изменения появляются в игре сами (во время матча — после возврата в меню).",
               mods_live_updated="Моды в игре обновлены.", mods_host_changed="Хост изменил моды: перезапустите игру, чтобы их увидеть (или включите горячую перезагрузку)."),
    "ja": dict(bep_title="ホットリロード", bep_desc="BepInExはMODローダーです。ゲームを再起動せずにMODの変更が反映され、カスタムカーソル・3Dモデル・カスタムステージが使えます。ランチャーが自動でダウンロードします（34 MB）。いつでも削除できます。",
               bep_status_off="オフ", bep_status_on="オン", bep_status_first="オン · 次回のゲーム起動は1分ほどかかります（初回のみ）",
               bep_enable="オンにする", bep_disable="BepInExを削除", bep_installing="BepInExをダウンロード中… {pct}%", bep_installed="ホットリロードをオンにしました。",
               bep_removed="BepInExを削除しました。ゲームは元どおりです。", bep_download_failed="BepInExをダウンロードできませんでした（{err}）。",
               bep_no_plugin="このランチャーにはMODプラグインが含まれていません。", bep_busy="先にゲームを閉じてください。",
               mods_live_restart="ホットリロードがオンです：変更は自動でゲームに反映されます（試合中はメニューに戻ったとき）。",
               mods_live_updated="ゲーム内のMODを更新しました。", mods_host_changed="ホストがMODを変更しました。見るにはゲームを再起動してください（またはホットリロードをオンに）。"),
    "ko": dict(bep_title="실시간 반영", bep_desc="BepInEx는 모드 로더로, 게임을 다시 시작하지 않아도 변경 사항이 반영되고 사용자 커서·3D 모델·커스텀 스테이지를 쓸 수 있습니다. 런처가 대신 내려받으며(34 MB), 언제든지 제거할 수 있습니다.",
               bep_status_off="꺼짐", bep_status_on="켜짐", bep_status_first="켜짐 · 다음 게임 실행은 1분 정도 걸립니다(처음 한 번만)",
               bep_enable="켜기", bep_disable="BepInEx 제거", bep_installing="BepInEx 내려받는 중… {pct}%", bep_installed="실시간 반영을 켰습니다.",
               bep_removed="BepInEx를 제거했습니다. 게임이 원래대로 돌아왔습니다.", bep_download_failed="BepInEx를 내려받지 못했습니다 ({err}).",
               bep_no_plugin="이 런처에는 모드 플러그인이 없습니다.", bep_busy="먼저 게임을 닫으세요.",
               mods_live_restart="실시간 반영이 켜져 있습니다: 변경 사항이 게임에 자동으로 나타납니다(게임 중이면 메뉴로 돌아갈 때).",
               mods_live_updated="게임의 모드를 업데이트했습니다.", mods_host_changed="호스트가 모드를 바꿨습니다: 보려면 게임을 다시 여세요(또는 실시간 반영을 켜세요)."),
    "zh-CN": dict(bep_title="热重载", bep_desc="BepInEx 是模组加载器：无需重启游戏即可看到模组更改，并支持自定义光标、3D 模型和自定义场景。启动器会自动下载（34 MB），可随时移除。",
               bep_status_off="未开启", bep_status_on="已开启", bep_status_first="已开启 · 下次启动游戏大约需要一分钟（仅第一次）",
               bep_enable="开启", bep_disable="移除 BepInEx", bep_installing="正在下载 BepInEx… {pct}%", bep_installed="已开启热重载。",
               bep_removed="已移除 BepInEx：游戏恢复原样。", bep_download_failed="无法下载 BepInEx（{err}）。",
               bep_no_plugin="此启动器未包含模组插件。", bep_busy="请先关闭游戏。",
               mods_live_restart="已开启热重载：修改会自动出现在游戏中（对局中则在回到菜单时）。",
               mods_live_updated="游戏中的模组已更新。", mods_host_changed="房主更改了模组：重新打开游戏即可看到（或开启热重载）。"),
    "zh-TW": dict(bep_title="熱重載", bep_desc="BepInEx 是模組載入器：無需重啟遊戲即可看到模組變更，並支援自訂游標、3D 模型和自訂場景。啟動器會自動下載（34 MB），可隨時移除。",
               bep_status_off="未開啟", bep_status_on="已開啟", bep_status_first="已開啟 · 下次啟動遊戲大約需要一分鐘（僅第一次）",
               bep_enable="開啟", bep_disable="移除 BepInEx", bep_installing="正在下載 BepInEx… {pct}%", bep_installed="已開啟熱重載。",
               bep_removed="已移除 BepInEx：遊戲恢復原樣。", bep_download_failed="無法下載 BepInEx（{err}）。",
               bep_no_plugin="此啟動器未包含模組外掛。", bep_busy="請先關閉遊戲。",
               mods_live_restart="已開啟熱重載：修改會自動出現在遊戲中（對局中則在回到選單時）。",
               mods_live_updated="遊戲中的模組已更新。", mods_host_changed="房主變更了模組：重新開啟遊戲即可看到（或開啟熱重載）。"),
}
for _l, _d in _BEP.items():
    S[_l].update(_d)

# Automatic BepInEx install when opening the launcher (log)
_BEP_AUTO = {
    "en": dict(bep_installing_log="Installing BepInEx, the mod loader (34 MB download, first time only)…",
               bep_ready_log="BepInEx installed. The game will take about a minute to start next time (first time only).",
               bep_failed_log="{err} You can still play without it; the launcher will try again next time.",
               bep_wait="Waiting for BepInEx to finish installing…",
               bep_setup="Setting up BepInEx…"),
    "es": dict(bep_installing_log="Instalando BepInEx, el cargador de mods (descarga de 34 MB, solo la primera vez)…",
               bep_ready_log="BepInEx instalado. El próximo arranque del juego tarda un minuto (solo la primera vez).",
               bep_failed_log="{err} Puedes jugar igualmente sin él; el lanzador lo volverá a intentar la próxima vez.",
               bep_wait="Esperando a que termine de instalarse BepInEx…",
               bep_setup="Preparando BepInEx…"),
    "fr": dict(bep_installing_log="Installation de BepInEx, le chargeur de mods (téléchargement de 34 Mo, la première fois seulement)…",
               bep_ready_log="BepInEx installé. Le prochain lancement du jeu prend environ une minute (la première fois seulement).",
               bep_failed_log="{err} Vous pouvez quand même jouer sans lui ; le lanceur réessaiera la prochaine fois.",
               bep_wait="En attente de la fin de l'installation de BepInEx…",
               bep_setup="Configuration de BepInEx…"),
    "it": dict(bep_installing_log="Installazione di BepInEx, il caricatore di mod (download di 34 MB, solo la prima volta)…",
               bep_ready_log="BepInEx installato. Il prossimo avvio del gioco richiede circa un minuto (solo la prima volta).",
               bep_failed_log="{err} Puoi giocare comunque senza; il launcher riproverà la prossima volta.",
               bep_wait="In attesa che finisca l'installazione di BepInEx…",
               bep_setup="Preparazione di BepInEx…"),
    "de": dict(bep_installing_log="BepInEx, der Mod-Loader, wird installiert (34 MB Download, nur beim ersten Mal)…",
               bep_ready_log="BepInEx installiert. Der nächste Spielstart dauert etwa eine Minute (nur beim ersten Mal).",
               bep_failed_log="{err} Du kannst trotzdem ohne spielen; der Launcher versucht es beim nächsten Mal erneut.",
               bep_wait="Warte, bis BepInEx fertig installiert ist…",
               bep_setup="BepInEx wird eingerichtet…"),
    "pt": dict(bep_installing_log="Instalando o BepInEx, o carregador de mods (download de 34 MB, só na primeira vez)…",
               bep_ready_log="BepInEx instalado. A próxima abertura do jogo leva cerca de um minuto (só na primeira vez).",
               bep_failed_log="{err} Você pode jogar sem ele mesmo assim; o lançador vai tentar de novo da próxima vez.",
               bep_wait="Aguardando o BepInEx terminar de instalar…",
               bep_setup="Preparando o BepInEx…"),
    "ru": dict(bep_installing_log="Установка BepInEx, загрузчика модов (загрузка 34 МБ, только в первый раз)…",
               bep_ready_log="BepInEx установлен. Следующий запуск игры займёт около минуты (только в первый раз).",
               bep_failed_log="{err} Играть можно и без него; лаунчер попробует снова в следующий раз.",
               bep_wait="Ожидание завершения установки BepInEx…",
               bep_setup="Настройка BepInEx…"),
    "ja": dict(bep_installing_log="MODローダーのBepInExをインストール中（34 MBのダウンロード、初回のみ）…",
               bep_ready_log="BepInExをインストールしました。次のゲーム起動には約1分かかります（初回のみ）。",
               bep_failed_log="{err} BepInExなしでも遊べます。次回またインストールを試します。",
               bep_wait="BepInExのインストール完了を待っています…",
               bep_setup="BepInExを準備中…"),
    "ko": dict(bep_installing_log="모드 로더 BepInEx 설치 중(34 MB 다운로드, 처음 한 번만)…",
               bep_ready_log="BepInEx를 설치했습니다. 다음 게임 시작은 약 1분 걸립니다(처음 한 번만).",
               bep_failed_log="{err} 없어도 플레이할 수 있습니다. 런처가 다음에 다시 시도합니다.",
               bep_wait="BepInEx 설치가 끝나기를 기다리는 중…",
               bep_setup="BepInEx 준비 중…"),
    "zh-CN": dict(bep_installing_log="正在安装模组加载器 BepInEx（下载 34 MB，仅首次）…",
                  bep_ready_log="已安装 BepInEx。下次启动游戏大约需要一分钟（仅首次）。",
                  bep_failed_log="{err} 没有它也可以游玩；启动器下次会再试。",
                  bep_wait="正在等待 BepInEx 安装完成…",
                  bep_setup="正在准备 BepInEx…"),
    "zh-TW": dict(bep_installing_log="正在安裝模組載入器 BepInEx（下載 34 MB，僅首次）…",
                  bep_ready_log="已安裝 BepInEx。下次啟動遊戲大約需要一分鐘（僅首次）。",
                  bep_failed_log="{err} 沒有它也可以遊玩；啟動器下次會再試。",
                  bep_wait="正在等待 BepInEx 安裝完成…",
                  bep_setup="正在準備 BepInEx…"),
}
for _l, _d in _BEP_AUTO.items():
    S[_l].update(_d)

_TXT = {
    "en": ("Messages", "Stamp messages", "The message shown in the match when you send each stamp. Any character works: ¿?¡!:\"*… Leave it empty for no message.", "Saved"),
    "es": ("Mensajes", "Mensajes de los stickers", "Lo que sale en la partida al mandar cada sticker. Puedes usar cualquier carácter: ¿?¡!:\"*… Si lo dejas vacío, no sale ningún mensaje.", "Guardado"),
    "fr": ("Messages", "Messages des stickers", "Ce qui s'affiche en partie quand vous envoyez chaque sticker. Tous les caractères sont permis : ¿?¡!:\"*… Laissez vide pour n'afficher aucun message.", "Enregistré"),
    "it": ("Messaggi", "Messaggi degli sticker", "Ciò che compare in partita quando invii ogni sticker. Puoi usare qualsiasi carattere: ¿?¡!:\"*… Se lo lasci vuoto, non compare nessun messaggio.", "Salvato"),
    "de": ("Nachrichten", "Sticker-Nachrichten", "Was im Spiel erscheint, wenn du den Sticker sendest. Alle Zeichen sind erlaubt: ¿?¡!:\"*… Leer lassen, damit keine Nachricht erscheint.", "Gespeichert"),
    "pt": ("Mensagens", "Mensagens dos emojis", "O que aparece na partida ao enviar cada emoji. Você pode usar qualquer caractere: ¿?¡!:\"*… Deixe vazio para não mostrar nenhuma mensagem.", "Salvo"),
    "ru": ("Сообщения", "Сообщения шаблонов", "Что появляется в матче, когда вы отправляете шаблон. Можно использовать любые символы: ¿?¡!:\"*… Оставьте пустым, чтобы сообщения не было.", "Сохранено"),
    "ja": ("メッセージ", "スタンプのメッセージ", "スタンプを送ったときに試合中に表示される文です。どんな文字でも使えます：？！：\"*… 空欄にするとメッセージは表示されません。", "保存しました"),
    "ko": ("메시지", "스탬프 메시지", "스탬프를 보낼 때 게임에 표시되는 문구입니다. 어떤 문자든 쓸 수 있습니다: ?!:\"*… 비워 두면 메시지가 표시되지 않습니다.", "저장했습니다"),
    "zh-CN": ("消息", "表情消息", "发送每个表情时在对局中显示的文字。可以使用任何字符：？！：\"*… 留空则不显示消息。", "已保存"),
    "zh-TW": ("訊息", "貼圖訊息", "傳送每個貼圖時在對局中顯示的文字。可以使用任何字元：？！：\"*… 留空則不顯示訊息。", "已儲存"),
}
for _l, (_b, _ti, _d, _s) in _TXT.items():
    S[_l].update(mods_texts_btn=_b, mods_texts_title=_ti, mods_texts_desc=_d, mods_text_saved=_s)

# Which game sticker each mod sticker is equivalent to (so the AIs reply to it)
_MEANS = {
    "en": ("The picture on the right of each stamp says which game stamp it counts as, so the AIs can reply to it. Leave it empty and they won't reply.", "Counts as…", "None"),
    "es": ("La imagen a la derecha de cada sticker dice a qué sticker del juego equivale, para que las IA puedan contestarle. Si la dejas vacía, no le contestan.", "Equivale a…", "Ninguno"),
    "fr": ("L'image à droite de chaque sticker indique à quel sticker du jeu il correspond, pour que les IA puissent y répondre. Laissez-la vide et elles n'y répondront pas.", "Correspond à…", "Aucun"),
    "it": ("L'immagine a destra di ogni sticker indica a quale sticker del gioco corrisponde, così le IA possono rispondergli. Se la lasci vuota, non rispondono.", "Corrisponde a…", "Nessuno"),
    "de": ("Das Bild rechts neben jedem Sticker gibt an, welchem Sticker des Spiels er entspricht, damit die KIs darauf antworten können. Bleibt es leer, antworten sie nicht.", "Entspricht…", "Keinem"),
    "pt": ("A imagem à direita de cada emoji diz a qual emoji do jogo ele equivale, para que as IAs possam responder. Se ficar vazia, elas não respondem.", "Equivale a…", "Nenhum"),
    "ru": ("Картинка справа от шаблона показывает, какому шаблону игры он соответствует, чтобы ИИ могли на него ответить. Если оставить её пустой, ИИ не ответят.", "Соответствует…", "Ничему"),
    "ja": ("各スタンプの右の画像は、それがゲームのどのスタンプに当たるかを示します。AIが返事できるようになります。空欄のままだとAIは返事をしません。", "相当するスタンプ…", "なし"),
    "ko": ("각 스탬프 오른쪽 그림은 그 스탬프가 게임의 어떤 스탬프에 해당하는지 나타냅니다. 그래야 AI가 답할 수 있습니다. 비워 두면 AI는 답하지 않습니다.", "해당 스탬프…", "없음"),
    "zh-CN": ("每个表情右边的图片表示它相当于游戏中的哪个表情，这样AI才能回应。留空的话，AI不会回应。", "相当于…", "无"),
    "zh-TW": ("每個貼圖右邊的圖片表示它相當於遊戲中的哪個貼圖，這樣AI才能回應。留空的話，AI不會回應。", "相當於…", "無"),
}
for _l, (_d, _tip, _none) in _MEANS.items():
    S[_l].update(mods_means_desc=_d, mods_means_tip=_tip, mods_means_none=_none)

_MANUAL = {
    "en": "You can download it yourself from {url} and put the file in {folder}, then press “Turn on” again.",
    "es": "Puedes descargarlo tú desde {url} y poner el archivo en {folder}; después pulsa «Activar» otra vez.",
    "fr": "Vous pouvez le télécharger vous-même depuis {url} et placer le fichier dans {folder}, puis appuyer de nouveau sur « Activer ».",
    "it": "Puoi scaricarlo tu da {url} e mettere il file in {folder}; poi premi di nuovo “Attiva”.",
    "de": "Du kannst es selbst von {url} herunterladen und die Datei in {folder} legen; dann erneut auf „Aktivieren“ klicken.",
    "pt": "Você pode baixá-lo de {url} e colocar o arquivo em {folder}; depois clique em “Ativar” de novo.",
    "ru": "Можно скачать его самостоятельно с {url} и положить файл в {folder}, а затем снова нажать «Включить».",
    "ja": "{url} から自分でダウンロードし、ファイルを {folder} に置いてから、もう一度「オンにする」を押してください。",
    "ko": "{url}에서 직접 내려받아 파일을 {folder}에 넣은 뒤 “켜기”를 다시 누르세요.",
    "zh-CN": "你可以自行从 {url} 下载，把文件放到 {folder}，然后再次点击“开启”。",
    "zh-TW": "你可以自行從 {url} 下載，把檔案放到 {folder}，然後再次點選「開啟」。",
}
for _l, _v in _MANUAL.items():
    S[_l]["bep_manual"] = _v

# --- mods of the players who join ---------------------------------------------------------
_OFFER = {
    "en": dict(mods_offer_title="{player} has mods",
               mods_offer_text="{player} wants to use their own stamps and avatars in your room. If you download them, everyone in the room will see them. They're temporary and are deleted when the room closes.",
               mods_offer_yes="Download", mods_offer_no="No thanks",
               mods_offer_sent="Your mods were sent to the host. If they accept, everyone will see them.",
               mods_offer_waiting="Waiting for the host to answer before opening the game (up to a minute)…",
               mods_offer_ok="✓ The host accepted your mods: you'll see them in the room.",
               mods_offer_timeout="The host didn't answer in time, so you're joining with the room's mods. If they accept later, your stamps will appear, but you may need to add them to your wheel again.",
               host_left_win="The host left mid-match: it counts as a win for you (+{points} points).",
               mods_offer_accepted="{player}'s mods were added to the room.",
               mods_offer_need_live="{player} has mods: turn on hot reload (in the Mods window) to use them in your room.",
               mods_confirm_text="The host uses custom stamps and avatars. To join you need to download them: they're temporary and get deleted when you leave. Your own mods are offered to the host: if they accept, everyone will see them."),
    "es": dict(mods_offer_title="{player} lleva mods",
               mods_offer_text="{player} quiere usar sus stickers y avatares en tu sala. Si los descargas, los verá todo el mundo en la sala; son temporales y se borran al cerrarla.",
               mods_offer_yes="Descargar", mods_offer_no="No, gracias",
               mods_offer_sent="Tus mods se han enviado al anfitrión: si los acepta, los veréis todos.",
               mods_offer_waiting="Esperando a que conteste el anfitrión antes de abrir el juego (hasta un minuto)…",
               mods_offer_ok="✓ El anfitrión ha aceptado tus mods: los verás en la sala.",
               mods_offer_timeout="El anfitrión no ha contestado a tiempo: entras con los mods de la sala. Si los acepta después, tus stickers aparecerán, pero puede que tengas que volver a ponerlos en tu rueda.",
               host_left_win="El anfitrión ha desaparecido a mitad de partida: cuenta como victoria para ti (+{points} puntos).",
               mods_offer_accepted="Mods de {player} añadidos a la sala.",
               mods_offer_need_live="{player} lleva mods: activa la recarga en caliente (ventana de Mods) para usarlos en tu sala.",
               mods_confirm_text="El anfitrión usa stickers y avatares personalizados. Para unirte tienes que descargarlos: son temporales y se borran al salir. Tus mods se le ofrecen al anfitrión: si los acepta, los veréis todos."),
    "fr": dict(mods_offer_title="{player} apporte des mods",
               mods_offer_text="{player} veut utiliser ses propres stickers et avatars dans votre salon. Si vous les téléchargez, tout le salon les verra ; ils sont temporaires et supprimés à la fermeture du salon.",
               mods_offer_yes="Télécharger", mods_offer_no="Non merci",
               mods_offer_sent="Vos mods ont été envoyés à l'hôte : s'il les accepte, tout le monde les verra.",
               mods_offer_waiting="En attente de la réponse de l'hôte avant d'ouvrir le jeu (jusqu'à une minute)…",
               mods_offer_ok="✓ L'hôte a accepté vos mods : vous les verrez dans le salon.",
               mods_offer_timeout="L'hôte n'a pas répondu à temps : vous entrez avec les mods du salon. S'il les accepte plus tard, vos stickers apparaîtront, mais il faudra peut-être les remettre dans votre roue.",
               host_left_win="L'hôte a disparu en pleine partie : cela compte comme une victoire pour vous (+{points} points).",
               mods_offer_accepted="Mods de {player} ajoutés au salon.",
               mods_offer_need_live="{player} apporte des mods : activez le rechargement à chaud (fenêtre Mods) pour les utiliser dans votre salon.",
               mods_confirm_text="L'hôte utilise des stickers et des avatars personnalisés. Pour rejoindre, vous devez les télécharger : ils sont temporaires et supprimés quand vous partez. Vos propres mods sont proposés à l'hôte : s'il les accepte, tout le monde les verra."),
    "it": dict(mods_offer_title="{player} porta dei mod",
               mods_offer_text="{player} vuole usare i suoi sticker e avatar nella tua stanza. Se li scarichi, li vedranno tutti nella stanza; sono temporanei e vengono eliminati alla chiusura.",
               mods_offer_yes="Scarica", mods_offer_no="No, grazie",
               mods_offer_sent="I tuoi mod sono stati inviati all'host: se li accetta, li vedrete tutti.",
               mods_offer_waiting="In attesa della risposta dell'host prima di aprire il gioco (fino a un minuto)…",
               mods_offer_ok="✓ L'host ha accettato i tuoi mod: li vedrai nella stanza.",
               mods_offer_timeout="L'host non ha risposto in tempo: entri con i mod della stanza. Se li accetta dopo, i tuoi sticker appariranno, ma potresti doverli rimettere nella tua ruota.",
               host_left_win="L'host è sparito a metà partita: conta come una vittoria per te (+{points} punti).",
               mods_offer_accepted="Mod di {player} aggiunti alla stanza.",
               mods_offer_need_live="{player} porta dei mod: attiva la ricarica a caldo (finestra Mod) per usarli nella tua stanza.",
               mods_confirm_text="L'host usa sticker e avatar personalizzati. Per entrare devi scaricarli: sono temporanei e vengono eliminati quando esci. I tuoi mod vengono offerti all'host: se li accetta, li vedrete tutti."),
    "de": dict(mods_offer_title="{player} bringt Mods mit",
               mods_offer_text="{player} möchte eigene Sticker und Avatare in deinem Raum nutzen. Wenn du sie herunterlädst, sieht sie der ganze Raum; sie sind temporär und werden beim Schließen gelöscht.",
               mods_offer_yes="Herunterladen", mods_offer_no="Nein, danke",
               mods_offer_sent="Deine Mods wurden an den Host geschickt: Wenn er sie annimmt, sehen sie alle.",
               mods_offer_waiting="Warte auf die Antwort des Hosts, bevor das Spiel startet (bis zu einer Minute)…",
               mods_offer_ok="✓ Der Host hat deine Mods angenommen: Du siehst sie im Raum.",
               mods_offer_timeout="Der Host hat nicht rechtzeitig geantwortet: Du trittst mit den Mods des Raums bei. Nimmt er sie später an, erscheinen deine Sticker, aber du musst sie eventuell wieder in dein Rad legen.",
               host_left_win="Der Host ist mitten im Spiel verschwunden: Das zählt als Sieg für dich (+{points} Punkte).",
               mods_offer_accepted="Mods von {player} zum Raum hinzugefügt.",
               mods_offer_need_live="{player} bringt Mods mit: Aktiviere Hot Reload (Mods-Fenster), um sie in deinem Raum zu nutzen.",
               mods_confirm_text="Der Host nutzt eigene Sticker und Avatare. Zum Beitreten musst du sie herunterladen: Sie sind temporär und werden beim Verlassen gelöscht. Deine eigenen Mods werden dem Host angeboten: Wenn er sie annimmt, sehen sie alle."),
    "pt": dict(mods_offer_title="{player} traz mods",
               mods_offer_text="{player} quer usar seus próprios emojis e avatares na sua sala. Se você baixá-los, todos na sala vão vê-los; são temporários e apagados quando a sala fecha.",
               mods_offer_yes="Baixar", mods_offer_no="Não, obrigado",
               mods_offer_sent="Seus mods foram enviados ao anfitrião: se ele aceitar, todos vão vê-los.",
               mods_offer_waiting="Aguardando a resposta do anfitrião antes de abrir o jogo (até um minuto)…",
               mods_offer_ok="✓ O anfitrião aceitou seus mods: você vai vê-los na sala.",
               mods_offer_timeout="O anfitrião não respondeu a tempo: você entra com os mods da sala. Se ele aceitar depois, seus emojis vão aparecer, mas talvez você precise colocá-los de novo na sua roda.",
               host_left_win="O anfitrião sumiu no meio da partida: conta como vitória para você (+{points} pontos).",
               mods_offer_accepted="Mods de {player} adicionados à sala.",
               mods_offer_need_live="{player} traz mods: ative a recarga instantânea (janela Mods) para usá-los na sua sala.",
               mods_confirm_text="O anfitrião usa emojis e avatares personalizados. Para entrar, você precisa baixá-los: são temporários e apagados quando você sai. Seus mods são oferecidos ao anfitrião: se ele aceitar, todos vão vê-los."),
    "ru": dict(mods_offer_title="{player} принёс моды",
               mods_offer_text="{player} хочет использовать свои шаблоны и аватары в вашей комнате. Если вы их скачаете, их увидят все в комнате; они временные и удаляются при закрытии комнаты.",
               mods_offer_yes="Скачать", mods_offer_no="Нет, спасибо",
               mods_offer_sent="Ваши моды отправлены хосту: если он их примет, их увидят все.",
               mods_offer_waiting="Ждём ответа хоста перед запуском игры (до минуты)…",
               mods_offer_ok="✓ Хост принял ваши моды: вы увидите их в комнате.",
               mods_offer_timeout="Хост не ответил вовремя: вы входите с модами комнаты. Если он примет их позже, ваши шаблоны появятся, но, возможно, их придётся снова поставить в колесо.",
               host_left_win="Хост пропал посреди матча: это засчитывается вам как победа (+{points} очков).",
               mods_offer_accepted="Моды игрока {player} добавлены в комнату.",
               mods_offer_need_live="{player} принёс моды: включите горячую перезагрузку (окно модов), чтобы использовать их в своей комнате.",
               mods_confirm_text="Хост использует свои шаблоны и аватары. Чтобы присоединиться, их нужно скачать: они временные и удаляются, когда вы выходите. Ваши моды предлагаются хосту: если он их примет, их увидят все."),
    "ja": dict(mods_offer_title="{player} がMODを持っています",
               mods_offer_text="{player} が自分のスタンプとアバターをあなたのルームで使いたがっています。ダウンロードするとルームの全員に表示されます。一時的なもので、ルームを閉じると削除されます。",
               mods_offer_yes="ダウンロード", mods_offer_no="いいえ",
               mods_offer_sent="あなたのMODをホストに送りました。承認されると全員に表示されます。",
               mods_offer_waiting="ゲームを開く前にホストの返事を待っています（最大1分）…",
               mods_offer_ok="✓ ホストがあなたのMODを承認しました。ルームで表示されます。",
               mods_offer_timeout="ホストが時間内に応答しませんでした。ルームのMODで参加します。後で承認されるとスタンプが表示されますが、ホイールに付け直す必要があるかもしれません。",
               host_left_win="試合中にホストがいなくなりました。あなたの勝利になります（+{points}ポイント）。",
               mods_offer_accepted="{player} のMODをルームに追加しました。",
               mods_offer_need_live="{player} がMODを持っています。ルームで使うにはホットリロード（MODウィンドウ）をオンにしてください。",
               mods_confirm_text="ホストはオリジナルのスタンプとアバターを使用しています。参加するにはダウンロードが必要です。これらは一時的なもので、退出すると削除されます。あなたのMODはホストに提案され、承認されると全員に表示されます。"),
    "ko": dict(mods_offer_title="{player} 님이 모드를 가져왔습니다",
               mods_offer_text="{player} 님이 자신의 스탬프와 아바타를 내 방에서 쓰고 싶어 합니다. 내려받으면 방의 모두에게 보이며, 임시 파일이라 방을 닫으면 삭제됩니다.",
               mods_offer_yes="내려받기", mods_offer_no="괜찮습니다",
               mods_offer_sent="내 모드를 호스트에게 보냈습니다: 수락하면 모두에게 보입니다.",
               mods_offer_waiting="게임을 열기 전에 호스트의 응답을 기다리는 중입니다(최대 1분)…",
               mods_offer_ok="✓ 호스트가 내 모드를 수락했습니다: 방에서 보입니다.",
               mods_offer_timeout="호스트가 제시간에 응답하지 않았습니다: 방의 모드로 입장합니다. 나중에 수락되면 스티커가 나타나지만 휠에 다시 넣어야 할 수 있습니다.",
               host_left_win="경기 도중 호스트가 사라졌습니다: 당신의 승리로 기록됩니다 (+{points}점).",
               mods_offer_accepted="{player} 님의 모드를 방에 추가했습니다.",
               mods_offer_need_live="{player} 님이 모드를 가져왔습니다: 내 방에서 쓰려면 실시간 반영(모드 창)을 켜세요.",
               mods_confirm_text="호스트가 커스텀 스탬프와 아바타를 사용합니다. 참가하려면 내려받아야 하며, 임시 파일이라 나가면 삭제됩니다. 내 모드는 호스트에게 제안되며, 수락하면 모두에게 보입니다."),
    "zh-CN": dict(mods_offer_title="{player} 带来了模组",
               mods_offer_text="{player} 想在你的房间里使用自己的表情和头像。下载后房间里的所有人都能看到；它们是临时的，房间关闭时会被删除。",
               mods_offer_yes="下载", mods_offer_no="不用了",
               mods_offer_sent="你的模组已发送给房主：如果对方接受，所有人都能看到。",
               mods_offer_waiting="打开游戏前正在等待房主回复（最多一分钟）…",
               mods_offer_ok="✓ 房主接受了你的模组：你会在房间里看到它们。",
               mods_offer_timeout="房主没有及时回复：你将使用房间的模组加入。如果对方之后接受，你的贴纸会出现，但可能需要重新放到轮盘上。",
               host_left_win="房主在对局中途消失了：算作你获胜（+{points} 分）。",
               mods_offer_accepted="已将 {player} 的模组加入房间。",
               mods_offer_need_live="{player} 带来了模组：开启热重载（模组窗口）即可在你的房间中使用。",
               mods_confirm_text="房主使用了自定义表情和头像。要加入就需要下载它们：这些是临时文件，离开后会被删除。你的模组会提供给房主：如果对方接受，所有人都能看到。"),
    "zh-TW": dict(mods_offer_title="{player} 帶來了模組",
               mods_offer_text="{player} 想在你的房間裡使用自己的貼圖和頭像。下載後房間裡的所有人都能看到；它們是暫時的，房間關閉時會被刪除。",
               mods_offer_yes="下載", mods_offer_no="不用了",
               mods_offer_sent="你的模組已傳送給房主：如果對方接受，所有人都能看到。",
               mods_offer_waiting="開啟遊戲前正在等待房主回覆（最多一分鐘）…",
               mods_offer_ok="✓ 房主接受了你的模組：你會在房間裡看到它們。",
               mods_offer_timeout="房主沒有及時回覆：你將使用房間的模組加入。如果對方之後接受，你的貼圖會出現，但可能需要重新放到輪盤上。",
               host_left_win="房主在對局中途消失了：算作你獲勝（+{points} 分）。",
               mods_offer_accepted="已將 {player} 的模組加入房間。",
               mods_offer_need_live="{player} 帶來了模組：開啟熱重載（模組視窗）即可在你的房間中使用。",
               mods_confirm_text="房主使用了自訂貼圖和頭像。要加入就需要下載它們：這些是暫時檔案，離開後會被刪除。你的模組會提供給房主：如果對方接受，所有人都能看到。"),
}
for _l, _d in _OFFER.items():
    S[_l].update(_d)

# --- host: what to do with the guests' mods (ask or always accept) -------------
_GUEST = {
    "en": dict(guest_mods_title="Guests' mods", guest_mods_ask="Ask me", guest_mods_always="Always accept",
               guest_mods_desc="For when you host and someone joins with their own stamps or avatars. You're asked in the game and in the launcher; with \"Always accept\" they're added right away.",
               mods_offer_always="Always accept", mods_offer_auto="{player}'s mods were added to the room (you always accept them)."),
    "es": dict(guest_mods_title="Mods de los invitados", guest_mods_ask="Preguntarme", guest_mods_always="Aceptar siempre",
               guest_mods_desc="Cuando hosteas y alguien entra con sus propios stickers o avatares. Se te pregunta en el juego y en el lanzador; con «Aceptar siempre» se añaden sin preguntar.",
               mods_offer_always="Aceptar siempre", mods_offer_auto="Mods de {player} añadidos a la sala (los aceptas siempre)."),
    "fr": dict(guest_mods_title="Mods des invités", guest_mods_ask="Me demander", guest_mods_always="Toujours accepter",
               guest_mods_desc="Quand vous hébergez et que quelqu'un rejoint avec ses propres stickers ou avatars. On vous le demande dans le jeu et dans le lanceur ; avec « Toujours accepter » ils sont ajoutés directement.",
               mods_offer_always="Toujours accepter", mods_offer_auto="Mods de {player} ajoutés au salon (vous les acceptez toujours)."),
    "it": dict(guest_mods_title="Mod degli ospiti", guest_mods_ask="Chiedimelo", guest_mods_always="Accetta sempre",
               guest_mods_desc="Quando ospiti e qualcuno entra con i propri sticker o avatar. Ti viene chiesto nel gioco e nel launcher; con «Accetta sempre» vengono aggiunti subito.",
               mods_offer_always="Accetta sempre", mods_offer_auto="Mod di {player} aggiunti alla stanza (li accetti sempre)."),
    "de": dict(guest_mods_title="Mods der Gäste", guest_mods_ask="Nachfragen", guest_mods_always="Immer annehmen",
               guest_mods_desc="Wenn du hostest und jemand mit eigenen Stickern oder Avataren beitritt. Du wirst im Spiel und im Launcher gefragt; mit „Immer annehmen“ werden sie direkt hinzugefügt.",
               mods_offer_always="Immer annehmen", mods_offer_auto="Mods von {player} zum Raum hinzugefügt (du nimmst sie immer an)."),
    "pt": dict(guest_mods_title="Mods dos convidados", guest_mods_ask="Perguntar", guest_mods_always="Aceitar sempre",
               guest_mods_desc="Quando você hospeda e alguém entra com emojis ou avatares próprios. Você é perguntado no jogo e no launcher; com \"Aceitar sempre\" eles são adicionados na hora.",
               mods_offer_always="Aceitar sempre", mods_offer_auto="Mods de {player} adicionados à sala (você sempre aceita)."),
    "ru": dict(guest_mods_title="Моды гостей", guest_mods_ask="Спрашивать", guest_mods_always="Всегда принимать",
               guest_mods_desc="Когда вы хост и кто-то заходит со своими шаблонами или аватарами. Вопрос появится в игре и в лаунчере; с «Всегда принимать» они добавляются сразу.",
               mods_offer_always="Всегда принимать", mods_offer_auto="Моды {player} добавлены в комнату (вы всегда их принимаете)."),
    "ja": dict(guest_mods_title="ゲストのMOD", guest_mods_ask="毎回確認", guest_mods_always="常に受け入れる",
               guest_mods_desc="ホスト中に誰かが自分のスタンプやアバターを持って参加したとき。ゲーム内とランチャーで確認されます。「常に受け入れる」ならすぐに追加されます。",
               mods_offer_always="常に受け入れる", mods_offer_auto="{player} のMODをルームに追加しました（常に受け入れる設定）。"),
    "ko": dict(guest_mods_title="게스트 모드", guest_mods_ask="매번 묻기", guest_mods_always="항상 수락",
               guest_mods_desc="호스트 중 누군가 자신의 스탬프나 아바타를 가지고 들어올 때입니다. 게임과 런처에서 물어보며, '항상 수락'이면 바로 추가됩니다.",
               mods_offer_always="항상 수락", mods_offer_auto="{player} 님의 모드를 방에 추가했습니다(항상 수락)."),
    "zh-CN": dict(guest_mods_title="访客的模组", guest_mods_ask="每次询问", guest_mods_always="总是接受",
               guest_mods_desc="当你做房主、有人带着自己的表情或头像加入时。会在游戏内和启动器中询问你；选择“总是接受”则直接加入。",
               mods_offer_always="总是接受", mods_offer_auto="已将 {player} 的模组加入房间（你设置为总是接受）。"),
    "zh-TW": dict(guest_mods_title="訪客的模組", guest_mods_ask="每次詢問", guest_mods_always="總是接受",
               guest_mods_desc="當你當房主、有人帶著自己的貼圖或頭像加入時。會在遊戲內和啟動器中詢問你；選擇「總是接受」則直接加入。",
               mods_offer_always="總是接受", mods_offer_auto="已將 {player} 的模組加入房間（你設定為總是接受）。"),
}
for _l, _d in _GUEST.items():
    S[_l].update(_d)

# mods window with tabs
_MODTABS = {
    "en": dict(mods_tab_general="General", mods_tab_stickers="Stamps", mods_tab_avatars="Avatars",
               mods_none_stickers="You don't have any stamps yet.", mods_none_avatars="You don't have any avatars yet.",
               mods_toggle_note="Turning mods on or off affects both your stamps and your avatars."),
    "es": dict(mods_tab_general="General", mods_tab_stickers="Stickers", mods_tab_avatars="Avatares",
               mods_none_stickers="Todavía no tienes stickers.", mods_none_avatars="Todavía no tienes avatares.",
               mods_toggle_note="Activar o desactivar los mods afecta a tus stickers y a tus avatares a la vez."),
    "fr": dict(mods_tab_general="Général", mods_tab_stickers="Stickers", mods_tab_avatars="Avatars",
               mods_none_stickers="Vous n'avez encore aucun sticker.", mods_none_avatars="Vous n'avez encore aucun avatar.",
               mods_toggle_note="Activer ou désactiver les mods s'applique à la fois à vos stickers et à vos avatars."),
    "it": dict(mods_tab_general="Generale", mods_tab_stickers="Sticker", mods_tab_avatars="Avatar",
               mods_none_stickers="Non hai ancora nessuno sticker.", mods_none_avatars="Non hai ancora nessun avatar.",
               mods_toggle_note="Attivare o disattivare i mod vale sia per i tuoi sticker sia per i tuoi avatar."),
    "de": dict(mods_tab_general="Allgemein", mods_tab_stickers="Sticker", mods_tab_avatars="Avatare",
               mods_none_stickers="Du hast noch keine Sticker.", mods_none_avatars="Du hast noch keine Avatare.",
               mods_toggle_note="Mods ein- oder auszuschalten gilt für deine Sticker und deine Avatare zugleich."),
    "pt": dict(mods_tab_general="Geral", mods_tab_stickers="Emojis", mods_tab_avatars="Avatares",
               mods_none_stickers="Você ainda não tem emojis.", mods_none_avatars="Você ainda não tem avatares.",
               mods_toggle_note="Ativar ou desativar os mods vale para seus emojis e seus avatares ao mesmo tempo."),
    "ru": dict(mods_tab_general="Общее", mods_tab_stickers="Шаблоны", mods_tab_avatars="Аватары",
               mods_none_stickers="У вас пока нет шаблонов.", mods_none_avatars="У вас пока нет аватаров.",
               mods_toggle_note="Включение и выключение модов действует сразу и на шаблоны, и на аватары."),
    "ja": dict(mods_tab_general="全般", mods_tab_stickers="スタンプ", mods_tab_avatars="アバター",
               mods_none_stickers="スタンプはまだありません。", mods_none_avatars="アバターはまだありません。",
               mods_toggle_note="MODのオン・オフはスタンプとアバターの両方に適用されます。"),
    "ko": dict(mods_tab_general="일반", mods_tab_stickers="스탬프", mods_tab_avatars="아바타",
               mods_none_stickers="아직 스탬프가 없습니다.", mods_none_avatars="아직 아바타가 없습니다.",
               mods_toggle_note="모드를 켜거나 끄면 스탬프와 아바타 모두에 적용됩니다."),
    "zh-CN": dict(mods_tab_general="常规", mods_tab_stickers="表情", mods_tab_avatars="头像",
               mods_none_stickers="你还没有表情。", mods_none_avatars="你还没有头像。",
               mods_toggle_note="开启或关闭模组会同时作用于你的表情和头像。"),
    "zh-TW": dict(mods_tab_general="一般", mods_tab_stickers="貼圖", mods_tab_avatars="頭像",
               mods_none_stickers="你還沒有貼圖。", mods_none_avatars="你還沒有頭像。",
               mods_toggle_note="開啟或關閉模組會同時作用於你的貼圖和頭像。"),
}
for _l, _d in _MODTABS.items():
    S[_l].update(_d)

# 3D models (swap one character for another)
_MODELS = {
    "en": dict(mods_tab_models="Models", models_original="Original", models_now="Looks like {name}",
               models_desc="Swap a character's 3D model for another character's from the game (Sherlock and Moriarty too). They keep their own animations and behaviour; only the look changes. Only you see it, and the 2D portraits don't change.",
               models_need_bep="Requires hot reload (BepInEx), in the General tab.",
               models_survivor="Victim", models_traitor="Traitor"),
    "es": dict(mods_tab_models="Modelos", models_original="Original", models_now="Se ve como {name}",
               models_desc="Cambia el modelo 3D de un personaje por el de otro del juego (también Sherlock y Moriarty). Conserva sus animaciones y su forma de actuar; solo cambia su aspecto. Solo lo ves tú, y los retratos 2D no cambian.",
               models_need_bep="Necesita la recarga en caliente (BepInEx), en la pestaña General.",
               models_survivor="Víctima", models_traitor="Traidor"),
    "fr": dict(mods_tab_models="Modèles", models_original="Original", models_now="À l'apparence de {name}",
               models_desc="Remplacez le modèle 3D d'un personnage par celui d'un autre personnage du jeu (Sherlock et Moriarty aussi). Il garde ses animations et son comportement ; seule son apparence change. Vous seul le voyez, et les portraits 2D ne changent pas.",
               models_need_bep="Nécessite le rechargement à chaud (BepInEx), dans l'onglet Général.",
               models_survivor="Victime", models_traitor="Traître"),
    "it": dict(mods_tab_models="Modelli", models_original="Originale", models_now="Ha l'aspetto di {name}",
               models_desc="Sostituisci il modello 3D di un personaggio con quello di un altro personaggio del gioco (anche Sherlock e Moriarty). Mantiene le sue animazioni e il suo comportamento; cambia solo l'aspetto. Lo vedi solo tu e i ritratti 2D non cambiano.",
               models_need_bep="Serve il ricaricamento a caldo (BepInEx), nella scheda Generale.",
               models_survivor="Vittima", models_traitor="Traditore"),
    "de": dict(mods_tab_models="Modelle", models_original="Original", models_now="Sieht aus wie {name}",
               models_desc="Ersetze das 3D-Modell einer Figur durch das einer anderen Figur des Spiels (auch Sherlock und Moriarty). Sie behält ihre Animationen und ihr Verhalten; nur das Aussehen ändert sich. Nur du siehst es, und die 2D-Porträts ändern sich nicht.",
               models_need_bep="Braucht Hot Reload (BepInEx), im Tab Allgemein.",
               models_survivor="Opfer", models_traitor="Verräter"),
    "pt": dict(mods_tab_models="Modelos", models_original="Original", models_now="Aparece como {name}",
               models_desc="Troque o modelo 3D de um personagem pelo de outro personagem do jogo (Sherlock e Moriarty também). Ele mantém as animações e o comportamento; só muda a aparência. Só você vê, e os retratos 2D não mudam.",
               models_need_bep="Precisa da recarga a quente (BepInEx), na aba Geral.",
               models_survivor="Vítima", models_traitor="Traidor"),
    "ru": dict(mods_tab_models="Модели", models_original="Оригинал", models_now="Выглядит как {name}",
               models_desc="Замените 3D-модель персонажа на модель другого персонажа игры (в том числе Шерлока и Мориарти). Анимации и поведение остаются прежними, меняется только внешний вид. Видите это только вы, 2D-портреты не меняются.",
               models_need_bep="Нужна горячая перезагрузка (BepInEx) на вкладке «Общее».",
               models_survivor="Жертва", models_traitor="Предатель"),
    "ja": dict(mods_tab_models="モデル", models_original="オリジナル", models_now="{name} の見た目",
               models_desc="キャラクターの3Dモデルを、ゲーム内の別のキャラクター（シャーロックやモリアーティも）のものに変更します。アニメーションや行動はそのままで、見た目だけが変わります。見えるのはあなただけで、2Dの肖像は変わりません。",
               models_need_bep="「全般」タブのホットリロード（BepInEx）が必要です。",
               models_survivor="遭難者", models_traitor="トレイター"),
    "ko": dict(mods_tab_models="모델", models_original="원래 모델", models_now="{name}의 모습",
               models_desc="캐릭터의 3D 모델을 게임 속 다른 캐릭터(셜록과 모리아티 포함)의 모델로 바꿉니다. 애니메이션과 행동은 그대로이고 겉모습만 바뀝니다. 나에게만 보이며 2D 초상화는 바뀌지 않습니다.",
               models_need_bep="'일반' 탭의 핫 리로드(BepInEx)가 필요합니다.",
               models_survivor="조난자", models_traitor="배신자"),
    "zh-CN": dict(mods_tab_models="模型", models_original="原样", models_now="外观为 {name}",
               models_desc="把角色的3D模型换成游戏里另一个角色的模型（也包括夏洛克和莫里亚蒂）。动作和行为保持不变，只改变外观。只有你能看到，2D头像不会改变。",
               models_need_bep="需要“常规”页中的热重载（BepInEx）。",
               models_survivor="外来受困者", models_traitor="背叛者"),
    "zh-TW": dict(mods_tab_models="模型", models_original="原樣", models_now="外觀為 {name}",
               models_desc="把角色的3D模型換成遊戲裡另一個角色的模型（也包括夏洛克和莫里亞蒂）。動作和行為保持不變，只改變外觀。只有你看得到，2D頭像不會改變。",
               models_need_bep="需要「一般」頁中的熱重載（BepInEx）。",
               models_survivor="遇難者", models_traitor="背叛者"),
}
for _l, _d in _MODELS.items():
    S[_l].update(_d)

# Custom 3D models (.glb): folder, skeletons and instructions (README.txt in the models folder)
_MODELS_CUSTOM = {
    "en": dict(models_custom_title="Your own 3D models",
               models_custom_desc="Put a .glb file in the models folder and it appears in the lists above with its file name. To make one, open a character's skeleton (\"skeletons\" folder) in Blender, fit your model to it and export it as glTF Binary (.glb). The README in the folder explains the steps.",
               models_open="Open models folder", models_custom_tag="{name} (yours)",
               models_skel_ok="{n} skeletons ready in the \"skeletons\" folder.",
               models_skel_wait="The skeletons appear after you open the game once with hot reload (BepInEx)."),
    "es": dict(models_custom_title="Tus propios modelos 3D",
               models_custom_desc="Pon un archivo .glb en la carpeta de modelos y aparece en las listas de arriba con su nombre de archivo. Para hacer uno, abre en Blender el esqueleto de un personaje (carpeta \"skeletons\"), ajusta tu modelo a él y expórtalo como glTF Binary (.glb). El README de la carpeta explica los pasos.",
               models_open="Abrir carpeta de modelos", models_custom_tag="{name} (tuyo)",
               models_skel_ok="{n} esqueletos listos en la carpeta \"skeletons\".",
               models_skel_wait="Los esqueletos aparecen después de abrir el juego una vez con la recarga en caliente (BepInEx)."),
    "fr": dict(models_custom_title="Vos propres modèles 3D",
               models_custom_desc="Placez un fichier .glb dans le dossier des modèles et il apparaît dans les listes ci-dessus avec son nom de fichier. Pour en créer un, ouvrez le squelette d'un personnage (dossier « skeletons ») dans Blender, ajustez-y votre modèle et exportez-le en glTF Binary (.glb). Le README du dossier explique les étapes.",
               models_open="Ouvrir le dossier des modèles", models_custom_tag="{name} (le vôtre)",
               models_skel_ok="{n} squelettes prêts dans le dossier « skeletons ».",
               models_skel_wait="Les squelettes apparaissent après avoir lancé le jeu une fois avec le rechargement à chaud (BepInEx)."),
    "it": dict(models_custom_title="I tuoi modelli 3D",
               models_custom_desc="Metti un file .glb nella cartella dei modelli e comparirà negli elenchi qui sopra con il nome del file. Per crearne uno, apri in Blender lo scheletro di un personaggio (cartella \"skeletons\"), adattaci il tuo modello ed esportalo come glTF Binary (.glb). Il README della cartella spiega i passaggi.",
               models_open="Apri cartella dei modelli", models_custom_tag="{name} (tuo)",
               models_skel_ok="{n} scheletri pronti nella cartella \"skeletons\".",
               models_skel_wait="Gli scheletri compaiono dopo aver aperto il gioco una volta con il ricaricamento a caldo (BepInEx)."),
    "de": dict(models_custom_title="Eigene 3D-Modelle",
               models_custom_desc="Lege eine .glb-Datei in den Modellordner, dann erscheint sie mit ihrem Dateinamen in den Listen oben. Um eins zu machen, öffne das Skelett einer Figur (Ordner „skeletons“) in Blender, passe dein Modell daran an und exportiere es als glTF Binary (.glb). Die README im Ordner erklärt die Schritte.",
               models_open="Modellordner öffnen", models_custom_tag="{name} (deins)",
               models_skel_ok="{n} Skelette bereit im Ordner „skeletons“.",
               models_skel_wait="Die Skelette erscheinen, nachdem du das Spiel einmal mit Hot Reload (BepInEx) geöffnet hast."),
    "pt": dict(models_custom_title="Seus próprios modelos 3D",
               models_custom_desc="Coloque um arquivo .glb na pasta de modelos e ele aparece nas listas acima com o nome do arquivo. Para fazer um, abra no Blender o esqueleto de um personagem (pasta \"skeletons\"), ajuste seu modelo a ele e exporte como glTF Binary (.glb). O README da pasta explica os passos.",
               models_open="Abrir pasta de modelos", models_custom_tag="{name} (seu)",
               models_skel_ok="{n} esqueletos prontos na pasta \"skeletons\".",
               models_skel_wait="Os esqueletos aparecem depois de abrir o jogo uma vez com a recarga a quente (BepInEx)."),
    "ru": dict(models_custom_title="Свои 3D-модели",
               models_custom_desc="Положите файл .glb в папку моделей, и он появится в списках выше под своим именем. Чтобы сделать модель, откройте в Blender скелет персонажа (папка «skeletons»), подгоните под него свою модель и экспортируйте как glTF Binary (.glb). Шаги описаны в README в папке.",
               models_open="Открыть папку моделей", models_custom_tag="{name} (ваша)",
               models_skel_ok="{n} скелетов готово в папке «skeletons».",
               models_skel_wait="Скелеты появятся, когда вы один раз откроете игру с горячей перезагрузкой (BepInEx)."),
    "ja": dict(models_custom_title="自作の3Dモデル",
               models_custom_desc="モデルフォルダーに .glb ファイルを置くと、ファイル名で上のリストに表示されます。作るには、Blenderでキャラクターの骨格（「skeletons」フォルダー）を開き、モデルを合わせて glTF Binary (.glb) で書き出します。手順はフォルダー内の README にあります。",
               models_open="モデルフォルダーを開く", models_custom_tag="{name}（自作）",
               models_skel_ok="「skeletons」フォルダーに骨格が {n} 個あります。",
               models_skel_wait="骨格は、ホットリロード（BepInEx）でゲームを一度起動すると作られます。"),
    "ko": dict(models_custom_title="나만의 3D 모델",
               models_custom_desc="모델 폴더에 .glb 파일을 넣으면 위 목록에 파일 이름으로 나타납니다. 만들려면 Blender에서 캐릭터의 뼈대(\"skeletons\" 폴더)를 열고 모델을 맞춘 뒤 glTF Binary(.glb)로 내보내세요. 단계는 폴더의 README에 있습니다.",
               models_open="모델 폴더 열기", models_custom_tag="{name} (내 모델)",
               models_skel_ok="\"skeletons\" 폴더에 뼈대 {n}개가 준비되었습니다.",
               models_skel_wait="뼈대는 핫 리로드(BepInEx)로 게임을 한 번 실행하면 생깁니다."),
    "zh-CN": dict(models_custom_title="你自己的3D模型",
               models_custom_desc="把 .glb 文件放进模型文件夹，它就会以文件名出现在上面的列表里。制作方法：在 Blender 中打开角色的骨架（“skeletons”文件夹），把你的模型对齐到骨架上，再导出为 glTF Binary (.glb)。文件夹里的 README 有详细步骤。",
               models_open="打开模型文件夹", models_custom_tag="{name}（自制）",
               models_skel_ok="“skeletons”文件夹中已有 {n} 个骨架。",
               models_skel_wait="用热重载（BepInEx）启动一次游戏后就会生成骨架。"),
    "zh-TW": dict(models_custom_title="你自己的3D模型",
               models_custom_desc="把 .glb 檔案放進模型資料夾，它就會以檔名出現在上面的清單裡。製作方法：在 Blender 中開啟角色的骨架（「skeletons」資料夾），把你的模型對齊到骨架上，再匯出為 glTF Binary (.glb)。資料夾裡的 README 有詳細步驟。",
               models_open="開啟模型資料夾", models_custom_tag="{name}（自製）",
               models_skel_ok="「skeletons」資料夾中已有 {n} 個骨架。",
               models_skel_wait="用熱重載（BepInEx）啟動一次遊戲後就會產生骨架。"),
}
for _l, _d in _MODELS_CUSTOM.items():
    S[_l].update(_d)

# Models in .fbx (converted automatically) and models with another skeleton (adapted automatically)
_MODELS_FBX = {
    "en": dict(models_custom_desc="Put a .fbx or .glb file in the models folder (or a subfolder with the model and its textures) and it appears in the lists above. Humanoid models from Mixamo, VRChat, VRoid, Blender, 3ds Max or MMD are fitted to the character's skeleton automatically. For a perfect fit, build it on one of the skeletons in the \"skeletons\" folder. The README in the folder explains everything.",
               models_convert_error="Couldn't read this model: {err}"),
    "es": dict(models_custom_desc="Pon un archivo .fbx o .glb en la carpeta de modelos (o una subcarpeta con el modelo y sus texturas) y aparece en las listas de arriba. Los modelos humanoides de Mixamo, VRChat, VRoid, Blender, 3ds Max o MMD se adaptan solos al esqueleto del personaje. Para que encaje perfecto, hazlo sobre uno de los esqueletos de la carpeta \"skeletons\". El README de la carpeta lo explica todo.",
               models_convert_error="No he podido leer este modelo: {err}"),
    "fr": dict(models_custom_desc="Placez un fichier .fbx ou .glb dans le dossier des modèles (ou un sous-dossier avec le modèle et ses textures) et il apparaît dans les listes ci-dessus. Les modèles humanoïdes de Mixamo, VRChat, VRoid, Blender, 3ds Max ou MMD s'adaptent automatiquement au squelette du personnage. Pour un ajustement parfait, créez-le sur l'un des squelettes du dossier « skeletons ». Le README du dossier explique tout.",
               models_convert_error="Impossible de lire ce modèle : {err}"),
    "it": dict(models_custom_desc="Metti un file .fbx o .glb nella cartella dei modelli (o una sottocartella con il modello e le sue texture) e comparirà negli elenchi qui sopra. I modelli umanoidi di Mixamo, VRChat, VRoid, Blender, 3ds Max o MMD si adattano da soli allo scheletro del personaggio. Per un adattamento perfetto, crealo su uno degli scheletri della cartella \"skeletons\". Il README della cartella spiega tutto.",
               models_convert_error="Non riesco a leggere questo modello: {err}"),
    "de": dict(models_custom_desc="Lege eine .fbx- oder .glb-Datei in den Modellordner (oder einen Unterordner mit dem Modell und seinen Texturen), dann erscheint sie in den Listen oben. Humanoide Modelle aus Mixamo, VRChat, VRoid, Blender, 3ds Max oder MMD werden automatisch an das Skelett der Figur angepasst. Für eine perfekte Passform baue es auf einem der Skelette im Ordner „skeletons“. Die README im Ordner erklärt alles.",
               models_convert_error="Dieses Modell konnte nicht gelesen werden: {err}"),
    "pt": dict(models_custom_desc="Coloque um arquivo .fbx ou .glb na pasta de modelos (ou uma subpasta com o modelo e suas texturas) e ele aparece nas listas acima. Modelos humanoides do Mixamo, VRChat, VRoid, Blender, 3ds Max ou MMD se ajustam sozinhos ao esqueleto do personagem. Para um encaixe perfeito, faça-o sobre um dos esqueletos da pasta \"skeletons\". O README da pasta explica tudo.",
               models_convert_error="Não consegui ler este modelo: {err}"),
    "ru": dict(models_custom_desc="Положите файл .fbx или .glb в папку моделей (или подпапку с моделью и её текстурами), и он появится в списках выше. Человекоподобные модели из Mixamo, VRChat, VRoid, Blender, 3ds Max или MMD сами подгоняются под скелет персонажа. Для идеальной посадки делайте модель на одном из скелетов из папки «skeletons». Всё описано в README в папке.",
               models_convert_error="Не удалось прочитать эту модель: {err}"),
    "ja": dict(models_custom_desc="モデルフォルダーに .fbx か .glb ファイル（またはモデルとテクスチャを入れたサブフォルダー）を置くと、上のリストに表示されます。Mixamo、VRChat、VRoid、Blender、3ds Max、MMD の人型モデルは、キャラクターの骨格に自動で合わせられます。ぴったり合わせるには「skeletons」フォルダーの骨格を使って作ってください。詳しくはフォルダー内の README を見てください。",
               models_convert_error="このモデルを読み込めませんでした: {err}"),
    "ko": dict(models_custom_desc="모델 폴더에 .fbx 또는 .glb 파일(또는 모델과 텍스처가 든 하위 폴더)을 넣으면 위 목록에 나타납니다. Mixamo, VRChat, VRoid, Blender, 3ds Max, MMD의 인간형 모델은 캐릭터 뼈대에 자동으로 맞춰집니다. 완벽하게 맞추려면 \"skeletons\" 폴더의 뼈대 위에서 만드세요. 자세한 내용은 폴더의 README에 있습니다.",
               models_convert_error="이 모델을 읽을 수 없습니다: {err}"),
    "zh-CN": dict(models_custom_desc="把 .fbx 或 .glb 文件（或装有模型及其贴图的子文件夹）放进模型文件夹，它就会出现在上面的列表里。来自 Mixamo、VRChat、VRoid、Blender、3ds Max 或 MMD 的人形模型会自动适配角色的骨架。想要完美贴合，请在“skeletons”文件夹中的骨架上制作。文件夹里的 README 有详细说明。",
               models_convert_error="无法读取这个模型：{err}"),
    "zh-TW": dict(models_custom_desc="把 .fbx 或 .glb 檔案（或裝有模型及其貼圖的子資料夾）放進模型資料夾，它就會出現在上面的清單裡。來自 Mixamo、VRChat、VRoid、Blender、3ds Max 或 MMD 的人形模型會自動配合角色的骨架。想要完美貼合，請在「skeletons」資料夾中的骨架上製作。資料夾裡的 README 有詳細說明。",
               models_convert_error="無法讀取這個模型：{err}"),
}
for _l, _d in _MODELS_FBX.items():
    S[_l].update(_d)

# notices of the .fbx to .glb conversion (fbx2glb.py)
_MODELS_FBX_NOTES = {
    'en': dict(models_tex_missing='Texture not found: {name} (put it next to the model)', models_tex_bad="Couldn't read the texture {name}: save it as PNG", models_mesh_static="The part {name} has no bones, so it won't move",
               models_fbx_old="it's a very old FBX: export it again as FBX 2014 or later", models_fbx_empty="there's no 3D model inside"),
    'es': dict(models_tex_missing='No encuentro la textura {name} (ponla junto al modelo)', models_tex_bad='No puedo leer la textura {name}: guárdala como PNG', models_mesh_static='La pieza {name} no tiene huesos, así que no se moverá',
               models_fbx_old='es un FBX muy antiguo: vuelve a exportarlo como FBX 2014 o posterior', models_fbx_empty='no hay ningún modelo 3D dentro'),
    'fr': dict(models_tex_missing='Texture introuvable : {name} (placez-la à côté du modèle)', models_tex_bad='Impossible de lire la texture {name} : enregistrez-la en PNG', models_mesh_static="La pièce {name} n'a pas d'os, elle ne bougera pas",
               models_fbx_old="c'est un FBX très ancien : réexportez-le en FBX 2014 ou plus récent", models_fbx_empty="il n'y a aucun modèle 3D dedans"),
    'it': dict(models_tex_missing='Texture non trovata: {name} (mettila accanto al modello)', models_tex_bad='Non riesco a leggere la texture {name}: salvala come PNG', models_mesh_static='Il pezzo {name} non ha ossa, quindi non si muoverà',
               models_fbx_old='è un FBX molto vecchio: esportalo di nuovo come FBX 2014 o successivo', models_fbx_empty='non contiene nessun modello 3D'),
    'de': dict(models_tex_missing='Textur nicht gefunden: {name} (lege sie neben das Modell)', models_tex_bad='Die Textur {name} kann nicht gelesen werden: speichere sie als PNG', models_mesh_static='Das Teil {name} hat keine Knochen und bewegt sich daher nicht',
               models_fbx_old='das ist ein sehr altes FBX: exportiere es erneut als FBX 2014 oder neuer', models_fbx_empty='es enthält kein 3D-Modell'),
    'pt': dict(models_tex_missing='Textura não encontrada: {name} (coloque-a junto ao modelo)', models_tex_bad='Não consigo ler a textura {name}: salve-a como PNG', models_mesh_static='A peça {name} não tem ossos, então não vai se mexer',
               models_fbx_old='é um FBX muito antigo: exporte de novo como FBX 2014 ou posterior', models_fbx_empty='não há nenhum modelo 3D dentro'),
    'ru': dict(models_tex_missing='Текстура не найдена: {name} (положите её рядом с моделью)', models_tex_bad='Не удалось прочитать текстуру {name}: сохраните её в PNG', models_mesh_static='У части {name} нет костей, она не будет двигаться',
               models_fbx_old='это очень старый FBX: экспортируйте его заново как FBX 2014 или новее', models_fbx_empty='внутри нет 3D-модели'),
    'ja': dict(models_tex_missing='テクスチャ {name} が見つかりません（モデルと同じ場所に置いてください）', models_tex_bad='テクスチャ {name} を読み込めません：PNG で保存してください', models_mesh_static='パーツ {name} にはボーンがないので動きません',
               models_fbx_old='とても古い FBX です：FBX 2014 以降で書き出し直してください', models_fbx_empty='3Dモデルが入っていません'),
    'ko': dict(models_tex_missing='텍스처를 찾을 수 없습니다: {name} (모델 옆에 두세요)', models_tex_bad='텍스처 {name}을(를) 읽을 수 없습니다: PNG로 저장하세요', models_mesh_static='{name} 부분에는 뼈가 없어 움직이지 않습니다',
               models_fbx_old='아주 오래된 FBX입니다: FBX 2014 이상으로 다시 내보내세요', models_fbx_empty='3D 모델이 들어 있지 않습니다'),
    'zh-CN': dict(models_tex_missing='找不到贴图 {name}（请放在模型旁边）', models_tex_bad='无法读取贴图 {name}：请另存为 PNG', models_mesh_static='部件 {name} 没有骨骼，所以不会动',
               models_fbx_old='这是很旧的 FBX：请重新导出为 FBX 2014 或更新版本', models_fbx_empty='里面没有3D模型'),
    'zh-TW': dict(models_tex_missing='找不到貼圖 {name}（請放在模型旁邊）', models_tex_bad='無法讀取貼圖 {name}：請另存為 PNG', models_mesh_static='部件 {name} 沒有骨骼，所以不會動',
               models_fbx_old='這是很舊的 FBX：請重新匯出為 FBX 2014 或更新版本', models_fbx_empty='裡面沒有3D模型'),
}
for _l, _d in _MODELS_FBX_NOTES.items():
    S[_l].update(_d)

# custom animations (idle, walk, run) per character
_MODELS_ANIMS = {
    "en": dict(models_anims_title="Animations", models_anims_desc="Replace a character's idle, walk or run with your own animation (.fbx or .glb, e.g. from Mixamo) from the \"animations\" folder. Any humanoid animation works: it's fitted to the character's skeleton. Works with both the game's models and yours.", models_anims_open="Open animations folder", models_anims_none="No animations yet: put .fbx or .glb files in the \"animations\" folder and press Reload.", models_anim_idle="Idle", models_anim_walk="Walk", models_anim_run="Run", models_anim_game="Game default"),
    "es": dict(models_anims_title="Animaciones", models_anims_desc="Cambia el reposo, el andar o el correr de un personaje por una animación tuya (.fbx o .glb, por ejemplo de Mixamo) de la carpeta \"animations\". Vale cualquier animación humanoide: se adapta al esqueleto del personaje. Funciona con los modelos del juego y con los tuyos.", models_anims_open="Abrir carpeta de animaciones", models_anims_none="Aún no hay animaciones: pon archivos .fbx o .glb en la carpeta \"animations\" y pulsa refrescar.", models_anim_idle="Reposo", models_anim_walk="Andar", models_anim_run="Correr", models_anim_game="La del juego"),
    "fr": dict(models_anims_title="Animations", models_anims_desc="Remplacez la pose de repos, la marche ou la course d'un personnage par votre propre animation (.fbx ou .glb, par ex. de Mixamo) du dossier « animations ». Toute animation humanoïde convient : elle s'adapte au squelette du personnage. Fonctionne avec les modèles du jeu et les vôtres.", models_anims_open="Ouvrir le dossier des animations", models_anims_none="Aucune animation pour l'instant : placez des fichiers .fbx ou .glb dans le dossier « animations » et actualisez.", models_anim_idle="Repos", models_anim_walk="Marche", models_anim_run="Course", models_anim_game="Celle du jeu"),
    "it": dict(models_anims_title="Animazioni", models_anims_desc="Sostituisci la posa di riposo, la camminata o la corsa di un personaggio con una tua animazione (.fbx o .glb, ad es. da Mixamo) della cartella \"animations\". Va bene qualsiasi animazione umanoide: si adatta allo scheletro del personaggio. Funziona con i modelli del gioco e con i tuoi.", models_anims_open="Apri cartella delle animazioni", models_anims_none="Non ci sono ancora animazioni: metti file .fbx o .glb nella cartella \"animations\" e aggiorna.", models_anim_idle="Riposo", models_anim_walk="Camminata", models_anim_run="Corsa", models_anim_game="Quella del gioco"),
    "de": dict(models_anims_title="Animationen", models_anims_desc="Ersetze das Stehen, Gehen oder Laufen einer Figur durch eine eigene Animation (.fbx oder .glb, z. B. von Mixamo) aus dem Ordner „animations“. Jede humanoide Animation geht: Sie wird an das Skelett der Figur angepasst. Funktioniert mit den Modellen des Spiels und mit deinen.", models_anims_open="Animationsordner öffnen", models_anims_none="Noch keine Animationen: Lege .fbx- oder .glb-Dateien in den Ordner „animations“ und aktualisiere.", models_anim_idle="Stehen", models_anim_walk="Gehen", models_anim_run="Laufen", models_anim_game="Die des Spiels"),
    "pt": dict(models_anims_title="Animações", models_anims_desc="Troque o repouso, o andar ou o correr de um personagem por uma animação sua (.fbx ou .glb, por exemplo do Mixamo) da pasta \"animations\". Qualquer animação humanoide serve: ela se ajusta ao esqueleto do personagem. Funciona com os modelos do jogo e com os seus.", models_anims_open="Abrir pasta de animações", models_anims_none="Ainda não há animações: coloque arquivos .fbx ou .glb na pasta \"animations\" e atualize.", models_anim_idle="Repouso", models_anim_walk="Andar", models_anim_run="Correr", models_anim_game="A do jogo"),
    "ru": dict(models_anims_title="Анимации", models_anims_desc="Замените стойку, ходьбу или бег персонажа своей анимацией (.fbx или .glb, например из Mixamo) из папки «animations». Подойдёт любая человекоподобная анимация: она подгоняется под скелет персонажа. Работает и с моделями игры, и с вашими.", models_anims_open="Открыть папку анимаций", models_anims_none="Анимаций пока нет: положите файлы .fbx или .glb в папку «animations» и обновите.", models_anim_idle="Стойка", models_anim_walk="Ходьба", models_anim_run="Бег", models_anim_game="Из игры"),
    "ja": dict(models_anims_title="アニメーション", models_anims_desc="キャラクターの待機・歩き・走りを、「animations」フォルダーにある自分のアニメーション（.fbx か .glb、例えば Mixamo のもの）に置き換えます。人型のアニメーションならどれでも、キャラクターの骨格に合わせられます。ゲームのモデルにも自作モデルにも使えます。", models_anims_open="アニメーションフォルダーを開く", models_anims_none="まだアニメーションがありません。「animations」フォルダーに .fbx か .glb を置いて更新してください。", models_anim_idle="待機", models_anim_walk="歩き", models_anim_run="走り", models_anim_game="ゲームのもの"),
    "ko": dict(models_anims_title="애니메이션", models_anims_desc="캐릭터의 대기, 걷기, 달리기를 \"animations\" 폴더에 있는 나만의 애니메이션(.fbx 또는 .glb, 예: Mixamo)으로 바꿉니다. 인간형 애니메이션이면 무엇이든 캐릭터 뼈대에 맞춰집니다. 게임 모델과 내 모델 모두에서 작동합니다.", models_anims_open="애니메이션 폴더 열기", models_anims_none="아직 애니메이션이 없습니다. \"animations\" 폴더에 .fbx 또는 .glb 파일을 넣고 새로 고치세요.", models_anim_idle="대기", models_anim_walk="걷기", models_anim_run="달리기", models_anim_game="게임 기본"),
    "zh-CN": dict(models_anims_title="动画", models_anims_desc="用“animations”文件夹里你自己的动画（.fbx 或 .glb，例如来自 Mixamo）替换角色的待机、行走或奔跑。任何人形动画都可以，会自动适配角色的骨架。游戏模型和你的模型都适用。", models_anims_open="打开动画文件夹", models_anims_none="还没有动画：把 .fbx 或 .glb 文件放进“animations”文件夹，然后刷新。", models_anim_idle="待机", models_anim_walk="行走", models_anim_run="奔跑", models_anim_game="游戏原版"),
    "zh-TW": dict(models_anims_title="動畫", models_anims_desc="用「animations」資料夾裡你自己的動畫（.fbx 或 .glb，例如來自 Mixamo）替換角色的待機、行走或奔跑。任何人形動畫都可以，會自動配合角色的骨架。遊戲模型和你的模型都適用。", models_anims_open="開啟動畫資料夾", models_anims_none="還沒有動畫：把 .fbx 或 .glb 檔案放進「animations」資料夾，然後重新整理。", models_anim_idle="待機", models_anim_walk="行走", models_anim_run="奔跑", models_anim_game="遊戲原版"),
}
for _l, _d in _MODELS_ANIMS.items():
    S[_l].update(_d)

# 3D models and animations shared with the room (like the stickers)
_MODELS_SYNC = {
    "en": dict(models_room_entry="3D models and animations", models_room_count="{models} models · {anims} animations · {mb} MB",
               models_offer_text="{player} wants to use their own 3D models and animations in your room ({mb} MB). If you accept, everyone in the room will see them on the characters you haven't changed. They're temporary and are deleted when the room closes.",
               models_offer_sent="Your 3D models were offered to the host: if they accept, they'll be sent and everyone will see them.",
               models_offer_ok="✓ The host accepted your 3D models: you'll see them in the room.",
               models_downloading="Downloading the room's 3D models ({mb} MB)…", models_uploading="Sending your 3D models to the host ({mb} MB)…",
               models_download_failed="Couldn't download the room's 3D models ({err}).", models_upload_failed="Couldn't send your 3D models ({err}).",
               models_live_updated="3D models updated in the game.",
               models_desc="Change a character's 3D model and animations, to another character from the game or to your own model. In your room, everyone sees your choices (plus any guests' choices you accept, on characters you haven't changed). In someone else's room you see theirs, and yours come back when you leave. The 2D portraits don't change.",
               mods_confirm_text="The host is using mods (stamps, avatars or 3D models). To join, you need to download them: they're temporary and are deleted when you leave. Your own mods are paused in the meantime."),
    "es": dict(models_room_entry="Modelos 3D y animaciones", models_room_count="{models} modelos · {anims} animaciones · {mb} MB",
               models_offer_text="{player} quiere usar sus propios modelos 3D y animaciones en tu sala ({mb} MB). Si aceptas, los verá todo el mundo en la sala en los personajes que tú no hayas cambiado; son temporales y se borran al cerrarla.",
               models_offer_sent="Tus modelos 3D se han ofrecido al anfitrión: si los acepta, se le envían y los veréis todos.",
               models_offer_ok="✓ El anfitrión ha aceptado tus modelos 3D: los verás en la sala.",
               models_downloading="Descargando los modelos 3D de la sala ({mb} MB)…", models_uploading="Enviando tus modelos 3D al anfitrión ({mb} MB)…",
               models_download_failed="No he podido descargar los modelos 3D de la sala ({err}).", models_upload_failed="No he podido enviar tus modelos 3D ({err}).",
               models_live_updated="Modelos 3D actualizados en el juego.",
               models_desc="Cambia el modelo 3D y las animaciones de un personaje: por otro personaje del juego o por un modelo tuyo. En tu sala lo ven todos (y también lo de los invitados que aceptes, en los personajes que no hayas cambiado); en la sala de otro ves lo suyo, y lo tuyo vuelve al salir. Los retratos 2D no cambian.",
               mods_confirm_text="El anfitrión usa mods (stickers, avatares o modelos 3D). Para unirte tienes que descargarlos: son temporales y se borran al salir. Mientras tanto, tus propios mods se apartan."),
    "fr": dict(models_room_entry="Modèles 3D et animations", models_room_count="{models} modèles · {anims} animations · {mb} Mo",
               models_offer_text="{player} veut utiliser ses propres modèles 3D et animations dans votre salon ({mb} Mo). Si vous acceptez, tout le salon les verra sur les personnages que vous n'avez pas changés ; ils sont temporaires et supprimés à la fermeture du salon.",
               models_offer_sent="Vos modèles 3D ont été proposés à l'hôte : s'il les accepte, ils lui seront envoyés et tout le monde les verra.",
               models_offer_ok="✓ L'hôte a accepté vos modèles 3D : vous les verrez dans le salon.",
               models_downloading="Téléchargement des modèles 3D du salon ({mb} Mo)…", models_uploading="Envoi de vos modèles 3D à l'hôte ({mb} Mo)…",
               models_download_failed="Impossible de télécharger les modèles 3D du salon ({err}).", models_upload_failed="Impossible d'envoyer vos modèles 3D ({err}).",
               models_live_updated="Modèles 3D mis à jour dans le jeu.",
               models_desc="Changez le modèle 3D et les animations d'un personnage : par un autre personnage du jeu ou par votre propre modèle. Dans votre salon, tout le monde voit vos choix (et ceux des invités que vous acceptez, sur les personnages que vous n'avez pas changés) ; dans le salon d'un autre, vous voyez les siens, et les vôtres reviennent en partant. Les portraits 2D ne changent pas.",
               mods_confirm_text="L'hôte utilise des mods (stickers, avatars ou modèles 3D). Pour rejoindre, vous devez les télécharger : ils sont temporaires et supprimés en partant. Vos propres mods sont mis de côté en attendant."),
    "it": dict(models_room_entry="Modelli 3D e animazioni", models_room_count="{models} modelli · {anims} animazioni · {mb} MB",
               models_offer_text="{player} vuole usare i propri modelli 3D e animazioni nella tua stanza ({mb} MB). Se accetti, tutti nella stanza li vedranno sui personaggi che non hai cambiato; sono temporanei e si cancellano alla chiusura della stanza.",
               models_offer_sent="I tuoi modelli 3D sono stati offerti all'host: se li accetta, gli verranno inviati e li vedrete tutti.",
               models_offer_ok="✓ L'host ha accettato i tuoi modelli 3D: li vedrai nella stanza.",
               models_downloading="Download dei modelli 3D della stanza ({mb} MB)…", models_uploading="Invio dei tuoi modelli 3D all'host ({mb} MB)…",
               models_download_failed="Impossibile scaricare i modelli 3D della stanza ({err}).", models_upload_failed="Impossibile inviare i tuoi modelli 3D ({err}).",
               models_live_updated="Modelli 3D aggiornati nel gioco.",
               models_desc="Cambia il modello 3D e le animazioni di un personaggio: con un altro personaggio del gioco o con un tuo modello. Nella tua stanza tutti vedono le tue scelte (e quelle degli ospiti che accetti, sui personaggi che non hai cambiato); nella stanza di un altro vedi le sue, e le tue tornano quando esci. I ritratti 2D non cambiano.",
               mods_confirm_text="L'host usa delle mod (sticker, avatar o modelli 3D). Per unirti devi scaricarle: sono temporanee e si cancellano quando esci. Nel frattempo le tue mod vengono messe da parte."),
    "de": dict(models_room_entry="3D-Modelle und Animationen", models_room_count="{models} Modelle · {anims} Animationen · {mb} MB",
               models_offer_text="{player} möchte eigene 3D-Modelle und Animationen in deinem Raum verwenden ({mb} MB). Wenn du zustimmst, sieht sie jeder im Raum an den Figuren, die du nicht geändert hast; sie sind vorübergehend und werden beim Schließen des Raums gelöscht.",
               models_offer_sent="Deine 3D-Modelle wurden dem Host angeboten: Wenn er zustimmt, werden sie ihm geschickt und alle sehen sie.",
               models_offer_ok="✓ Der Host hat deine 3D-Modelle angenommen: Du siehst sie im Raum.",
               models_downloading="Lade die 3D-Modelle des Raums herunter ({mb} MB)…", models_uploading="Sende deine 3D-Modelle an den Host ({mb} MB)…",
               models_download_failed="Die 3D-Modelle des Raums konnten nicht geladen werden ({err}).", models_upload_failed="Deine 3D-Modelle konnten nicht gesendet werden ({err}).",
               models_live_updated="3D-Modelle im Spiel aktualisiert.",
               models_desc="Ändere das 3D-Modell und die Animationen einer Figur: in eine andere Figur des Spiels oder in dein eigenes Modell. In deinem Raum sehen alle deine Auswahl (und die der Gäste, die du annimmst, an den Figuren, die du nicht geändert hast); im Raum eines anderen siehst du seine, und deine kommen zurück, wenn du gehst. Die 2D-Porträts ändern sich nicht.",
               mods_confirm_text="Der Host nutzt Mods (Sticker, Avatare oder 3D-Modelle). Um beizutreten, musst du sie herunterladen: Sie sind vorübergehend und werden gelöscht, wenn du gehst. Deine eigenen Mods werden solange beiseitegelegt."),
    "pt": dict(models_room_entry="Modelos 3D e animações", models_room_count="{models} modelos · {anims} animações · {mb} MB",
               models_offer_text="{player} quer usar seus próprios modelos 3D e animações na sua sala ({mb} MB). Se você aceitar, todos na sala os verão nos personagens que você não mudou; são temporários e apagados ao fechar a sala.",
               models_offer_sent="Seus modelos 3D foram oferecidos ao anfitrião: se ele aceitar, serão enviados e todos os verão.",
               models_offer_ok="✓ O anfitrião aceitou seus modelos 3D: você os verá na sala.",
               models_downloading="Baixando os modelos 3D da sala ({mb} MB)…", models_uploading="Enviando seus modelos 3D ao anfitrião ({mb} MB)…",
               models_download_failed="Não foi possível baixar os modelos 3D da sala ({err}).", models_upload_failed="Não foi possível enviar seus modelos 3D ({err}).",
               models_live_updated="Modelos 3D atualizados no jogo.",
               models_desc="Mude o modelo 3D e as animações de um personagem: por outro personagem do jogo ou por um modelo seu. Na sua sala todos veem suas escolhas (e as dos convidados que você aceitar, nos personagens que você não mudou); na sala de outro você vê as dele, e as suas voltam ao sair. Os retratos 2D não mudam.",
               mods_confirm_text="O anfitrião usa mods (emojis, avatares ou modelos 3D). Para entrar você precisa baixá-los: são temporários e apagados ao sair. Enquanto isso, seus próprios mods ficam de lado."),
    "ru": dict(models_room_entry="3D-модели и анимации", models_room_count="моделей: {models} · анимаций: {anims} · {mb} МБ",
               models_offer_text="{player} хочет использовать в вашей комнате свои 3D-модели и анимации ({mb} МБ). Если вы согласитесь, их увидят все в комнате на тех персонажах, которых вы не меняли; они временные и удалятся при закрытии комнаты.",
               models_offer_sent="Ваши 3D-модели предложены хосту: если он согласится, они будут отправлены и их увидят все.",
               models_offer_ok="✓ Хост принял ваши 3D-модели: вы увидите их в комнате.",
               models_downloading="Загрузка 3D-моделей комнаты ({mb} МБ)…", models_uploading="Отправка ваших 3D-моделей хосту ({mb} МБ)…",
               models_download_failed="Не удалось загрузить 3D-модели комнаты ({err}).", models_upload_failed="Не удалось отправить ваши 3D-модели ({err}).",
               models_live_updated="3D-модели обновлены в игре.",
               models_desc="Меняйте 3D-модель и анимации персонажа: на другого персонажа игры или на свою модель. В вашей комнате ваш выбор видят все (и выбор гостей, которых вы примете, на персонажах, которых вы не меняли); в чужой комнате вы видите выбор хозяина, а ваш вернётся, когда выйдете. 2D-портреты не меняются.",
               mods_confirm_text="Хост использует моды (шаблоны, аватары или 3D-модели). Чтобы войти, их нужно скачать: они временные и удалятся, когда вы выйдете. Ваши собственные моды пока отключаются."),
    "ja": dict(models_room_entry="3Dモデルとアニメーション", models_room_count="モデル {models} 個 · アニメーション {anims} 個 · {mb} MB",
               models_offer_text="{player} さんが自分の3Dモデルとアニメーションをあなたのルームで使いたがっています（{mb} MB）。受け入れると、あなたが変えていないキャラクターでルームの全員に表示されます。一時的なもので、ルームを閉じると削除されます。",
               models_offer_sent="あなたの3Dモデルをホストに提案しました。受け入れられると送信され、全員に表示されます。",
               models_offer_ok="✓ ホストがあなたの3Dモデルを受け入れました。ルームで表示されます。",
               models_downloading="ルームの3Dモデルをダウンロード中（{mb} MB）…", models_uploading="あなたの3Dモデルをホストに送信中（{mb} MB）…",
               models_download_failed="ルームの3Dモデルをダウンロードできませんでした（{err}）。", models_upload_failed="あなたの3Dモデルを送信できませんでした（{err}）。",
               models_live_updated="ゲーム内の3Dモデルを更新しました。",
               models_desc="キャラクターの3Dモデルとアニメーションを、ゲームの別のキャラクターや自作モデルに変えます。自分のルームでは全員にあなたの選択が表示されます（受け入れたゲストのものも、あなたが変えていないキャラクターに）。他人のルームではその人の選択が表示され、退出するとあなたの選択に戻ります。2D の顔アイコンは変わりません。",
               mods_confirm_text="ホストはMOD（スタンプ、アバター、3Dモデル）を使っています。参加するにはダウンロードが必要です。一時的なもので、退出すると削除されます。その間、あなた自身のMODは外されます。"),
    "ko": dict(models_room_entry="3D 모델과 애니메이션", models_room_count="모델 {models}개 · 애니메이션 {anims}개 · {mb} MB",
               models_offer_text="{player} 님이 자신의 3D 모델과 애니메이션을 방에서 쓰고 싶어 합니다({mb} MB). 수락하면 당신이 바꾸지 않은 캐릭터에서 방의 모두가 보게 됩니다. 임시이며 방을 닫으면 삭제됩니다.",
               models_offer_sent="내 3D 모델을 호스트에게 제안했습니다. 수락하면 전송되고 모두가 보게 됩니다.",
               models_offer_ok="✓ 호스트가 내 3D 모델을 수락했습니다. 방에서 보입니다.",
               models_downloading="방의 3D 모델을 내려받는 중({mb} MB)…", models_uploading="내 3D 모델을 호스트에게 보내는 중({mb} MB)…",
               models_download_failed="방의 3D 모델을 내려받지 못했습니다({err}).", models_upload_failed="내 3D 모델을 보내지 못했습니다({err}).",
               models_live_updated="게임 속 3D 모델을 업데이트했습니다.",
               models_desc="캐릭터의 3D 모델과 애니메이션을 게임의 다른 캐릭터나 내 모델로 바꿉니다. 내 방에서는 모두가 내 선택을 봅니다(수락한 손님의 것도, 내가 바꾸지 않은 캐릭터에). 다른 사람의 방에서는 그 사람의 선택이 보이고, 나가면 내 것이 돌아옵니다. 2D 초상화는 바뀌지 않습니다.",
               mods_confirm_text="호스트가 모드(스티커, 아바타, 3D 모델)를 사용합니다. 참가하려면 내려받아야 합니다. 임시이며 나가면 삭제됩니다. 그동안 내 모드는 잠시 빠집니다."),
    "zh-CN": dict(models_room_entry="3D 模型和动画", models_room_count="{models} 个模型 · {anims} 个动画 · {mb} MB",
               models_offer_text="{player} 想在你的房间里使用自己的 3D 模型和动画（{mb} MB）。如果你接受，房间里的所有人都会在你没有更改的角色上看到它们；它们是临时的，房间关闭时会删除。",
               models_offer_sent="你的 3D 模型已提供给房主：如果房主接受，就会发送过去，大家都能看到。",
               models_offer_ok="✓ 房主接受了你的 3D 模型：你会在房间里看到它们。",
               models_downloading="正在下载房间的 3D 模型（{mb} MB）…", models_uploading="正在把你的 3D 模型发送给房主（{mb} MB）…",
               models_download_failed="无法下载房间的 3D 模型（{err}）。", models_upload_failed="无法发送你的 3D 模型（{err}）。",
               models_live_updated="游戏中的 3D 模型已更新。",
               models_desc="更换角色的 3D 模型和动画：换成游戏里的另一个角色或你自己的模型。在你的房间里所有人都能看到你的选择（以及你接受的客人的选择，用在你没改的角色上）；在别人的房间里你看到的是对方的，离开后恢复你的。2D 头像不会改变。",
               mods_confirm_text="房主使用了模组（贴纸、头像或 3D 模型）。要加入需要下载它们：它们是临时的，离开时会删除。在此期间你自己的模组会暂时停用。"),
    "zh-TW": dict(models_room_entry="3D 模型與動畫", models_room_count="{models} 個模型 · {anims} 個動畫 · {mb} MB",
               models_offer_text="{player} 想在你的房間裡使用自己的 3D 模型和動畫（{mb} MB）。如果你接受，房間裡的所有人都會在你沒有更改的角色上看到它們；它們是暫時的，房間關閉時會刪除。",
               models_offer_sent="你的 3D 模型已提供給房主：如果房主接受，就會傳送過去，大家都看得到。",
               models_offer_ok="✓ 房主接受了你的 3D 模型：你會在房間裡看到它們。",
               models_downloading="正在下載房間的 3D 模型（{mb} MB）…", models_uploading="正在把你的 3D 模型傳送給房主（{mb} MB）…",
               models_download_failed="無法下載房間的 3D 模型（{err}）。", models_upload_failed="無法傳送你的 3D 模型（{err}）。",
               models_live_updated="遊戲中的 3D 模型已更新。",
               models_desc="更換角色的 3D 模型和動畫：換成遊戲裡的另一個角色或你自己的模型。在你的房間裡所有人都看得到你的選擇（以及你接受的客人的選擇，用在你沒改的角色上）；在別人的房間裡你看到的是對方的，離開後恢復你的。2D 頭像不會改變。",
               mods_confirm_text="房主使用了模組（貼紙、頭像或 3D 模型）。要加入需要下載它們：它們是暫時的，離開時會刪除。在此期間你自己的模組會暫時停用。"),
}
for _l, _d in _MODELS_SYNC.items():
    S[_l].update(_d)
S['en']["models_offer_timeout"] = "The host didn't answer in time, so you're joining with the room's 3D models. If they accept later, yours will appear automatically."
S['es']["models_offer_timeout"] = 'El anfitrión no ha contestado a tiempo: entras con los modelos 3D de la sala. Si los acepta después, los tuyos aparecerán solos.'
S['fr']["models_offer_timeout"] = "L'hôte n'a pas répondu à temps : vous rejoignez avec les modèles 3D du salon. S'il les accepte plus tard, les vôtres apparaîtront d'eux-mêmes."
S['it']["models_offer_timeout"] = "L'host non ha risposto in tempo: entri con i modelli 3D della stanza. Se li accetta dopo, i tuoi compariranno da soli."
S['de']["models_offer_timeout"] = 'Der Host hat nicht rechtzeitig geantwortet: Du trittst mit den 3D-Modellen des Raums bei. Nimmt er sie später an, erscheinen deine von selbst.'
S['pt']["models_offer_timeout"] = 'O anfitrião não respondeu a tempo: você entra com os modelos 3D da sala. Se ele aceitar depois, os seus aparecerão sozinhos.'
S['ru']["models_offer_timeout"] = 'Хост не ответил вовремя: вы входите с 3D-моделями комнаты. Если он примет ваши позже, они появятся сами.'
S['ja']["models_offer_timeout"] = 'ホストが時間内に答えませんでした。ルームの3Dモデルで参加します。後で受け入れられると、あなたのモデルが自動で表示されます。'
S['ko']["models_offer_timeout"] = '호스트가 제때 답하지 않았습니다. 방의 3D 모델로 참가합니다. 나중에 수락하면 내 모델이 저절로 나타납니다.'
S['zh-CN']["models_offer_timeout"] = '房主没有及时回应：你将使用房间的 3D 模型加入。如果房主之后接受，你的模型会自动出现。'
S['zh-TW']["models_offer_timeout"] = '房主沒有及時回應：你將使用房間的 3D 模型加入。如果房主之後接受，你的模型會自動出現。'

# new characters (slots) and Character Selector
_CHARS = {
    "en": dict(chars_title="New characters", chars_desc="A new character doesn't replace anyone: it joins the draw of each match, with the same chance as the originals (choose who can appear with the in-game \"Character Selection\" in the waiting room). Without a name, animations or lines of its own it uses those of the character whose place it takes, and it always plays like that character. For a skin that always replaces a character, use the list above.",
               chars_add="Add character", chars_edit="Edit", chars_delete="Remove", chars_images_open="Open images folder",
               chars_none="No new characters yet.", chars_name="Name", chars_name_keep="(uses the name of the character whose slot it takes)",
               chars_model="3D model", chars_role="Type", chars_role_pawn="Character", chars_role_traitor="Traitor",
               chars_image="Image (portraits)", chars_image_none="Generate from the model", chars_anims="Animations",
               chars_talk="Lines", chars_talk_hint="Only fill in the ones you want to change; empty ones keep the lines of the character whose slot it takes. Traitors don't speak.",
               chars_talk_keep="(keeps the original line)", chars_save="Save", chars_cancel="Cancel", chars_active_on="On: shared with the rooms you join or host, and it can appear in matches.", chars_active_off="Off: not shared with any room (nothing is uploaded) and it never appears.", chars_need_model="Choose a 3D model from the models folder.",
               chars_has_anims="custom animations", chars_has_talk="{n} lines", chars_has_image="image", roster_saved="Character Selection saved."),
    "es": dict(chars_title="Personajes nuevos", chars_desc="Un personaje nuevo no sustituye a nadie: entra en el sorteo de cada partida con la misma probabilidad que los originales (eliges quién puede salir con la «Selección de personajes» de la sala de espera del juego). Si no tiene nombre, animaciones o frases propias, usa los del personaje cuyo sitio ocupa, y siempre juega como él. Para una skin que sustituya siempre a un personaje, usa la lista de arriba.",
               chars_add="Añadir personaje", chars_edit="Editar", chars_delete="Quitar", chars_images_open="Abrir carpeta de imágenes",
               chars_none="Aún no hay personajes nuevos.", chars_name="Nombre", chars_name_keep="(se queda el del sitio que ocupe)",
               chars_model="Modelo 3D", chars_role="Tipo", chars_role_pawn="Personaje", chars_role_traitor="Traidor",
               chars_image="Imagen (retratos)", chars_image_none="Sacarla del modelo", chars_anims="Animaciones",
               chars_talk="Frases", chars_talk_hint="Escribe solo las que quieras cambiar; las vacías se quedan con las del personaje cuyo sitio ocupe. Un traidor no habla.",
               chars_talk_keep="(se queda la frase original)", chars_save="Guardar", chars_cancel="Cancelar", chars_active_on="Activado: se comparte con las salas en las que entras o que creas, y puede salir en las partidas.", chars_active_off="Desactivado: no se comparte con ninguna sala (no se sube nada) y no sale nunca.", chars_need_model="Elige un modelo 3D de la carpeta de modelos.",
               chars_has_anims="animaciones propias", chars_has_talk="{n} frases", chars_has_image="imagen", roster_saved="Selección de personajes guardada."),
    "fr": dict(chars_title="Nouveaux personnages", chars_desc="Un nouveau personnage ne remplace personne : il entre dans le tirage de chaque partie, avec la même chance que les originaux (choisissez qui peut apparaître avec la « Sélection des personnages » de la salle d'attente). Sans nom, animations ou répliques à lui, il utilise ceux du personnage dont il prend la place, et joue toujours comme lui. Pour un skin qui remplace toujours un personnage, utilisez la liste ci-dessus.",
               chars_add="Ajouter un personnage", chars_edit="Modifier", chars_delete="Retirer", chars_images_open="Ouvrir le dossier des images",
               chars_none="Aucun nouveau personnage pour l'instant.", chars_name="Nom", chars_name_keep="(garde le nom de la place prise)",
               chars_model="Modèle 3D", chars_role="Type", chars_role_pawn="Personnage", chars_role_traitor="Traître",
               chars_image="Image (portraits)", chars_image_none="La tirer du modèle", chars_anims="Animations",
               chars_talk="Répliques", chars_talk_hint="N'écrivez que celles à changer ; les vides gardent celles du personnage dont il prend la place. Un traître ne parle pas.",
               chars_talk_keep="(garde la réplique d'origine)", chars_save="Enregistrer", chars_cancel="Annuler", chars_active_on="Activé : partagé avec les salons que vous rejoignez ou créez, et il peut apparaître dans les parties.", chars_active_off="Désactivé : il n'est partagé avec aucun salon (rien n'est envoyé) et il n'apparaît jamais.", chars_need_model="Choisissez un modèle 3D du dossier des modèles.",
               chars_has_anims="animations propres", chars_has_talk="{n} répliques", chars_has_image="image", roster_saved="Sélection des personnages enregistrée."),
    "it": dict(chars_title="Nuovi personaggi", chars_desc="Un nuovo personaggio non sostituisce nessuno: entra nel sorteggio di ogni partita, con la stessa probabilità degli originali (scegli chi può comparire con la «Selezione dei personaggi» della sala d'attesa). Senza nome, animazioni o battute proprie usa quelli del personaggio di cui prende il posto, e gioca sempre come lui. Per una skin che sostituisce sempre un personaggio, usa l'elenco qui sopra.",
               chars_add="Aggiungi personaggio", chars_edit="Modifica", chars_delete="Rimuovi", chars_images_open="Apri cartella delle immagini",
               chars_none="Ancora nessun nuovo personaggio.", chars_name="Nome", chars_name_keep="(resta quello del posto che occupa)",
               chars_model="Modello 3D", chars_role="Tipo", chars_role_pawn="Personaggio", chars_role_traitor="Traditore",
               chars_image="Immagine (ritratti)", chars_image_none="Ricavarla dal modello", chars_anims="Animazioni",
               chars_talk="Battute", chars_talk_hint="Scrivi solo quelle da cambiare; quelle vuote restano quelle del personaggio di cui prende il posto. Un traditore non parla.",
               chars_talk_keep="(resta la battuta originale)", chars_save="Salva", chars_cancel="Annulla", chars_active_on="Attivo: condiviso con le stanze in cui entri o che crei, e può apparire nelle partite.", chars_active_off="Disattivato: non è condiviso con nessuna stanza (non si carica nulla) e non appare mai.", chars_need_model="Scegli un modello 3D dalla cartella dei modelli.",
               chars_has_anims="animazioni proprie", chars_has_talk="{n} battute", chars_has_image="immagine", roster_saved="Selezione dei personaggi salvata."),
    "de": dict(chars_title="Neue Figuren", chars_desc="Eine neue Figur ersetzt niemanden: Sie kommt in die Auslosung jeder Partie, mit derselben Chance wie die Originale (wer erscheinen darf, wählst du mit der „Figurenauswahl“ im Warteraum). Ohne eigenen Namen, Animationen oder Sätze nutzt sie die der Figur, deren Platz sie einnimmt, und spielt immer wie diese. Für einen Skin, der eine Figur immer ersetzt, nimm die Liste oben.",
               chars_add="Figur hinzufügen", chars_edit="Bearbeiten", chars_delete="Entfernen", chars_images_open="Bilderordner öffnen",
               chars_none="Noch keine neuen Figuren.", chars_name="Name", chars_name_keep="(behält den Namen des Platzes)",
               chars_model="3D-Modell", chars_role="Typ", chars_role_pawn="Figur", chars_role_traitor="Verräter",
               chars_image="Bild (Porträts)", chars_image_none="Aus dem Modell erzeugen", chars_anims="Animationen",
               chars_talk="Sätze", chars_talk_hint="Schreib nur die, die du ändern willst; leere behalten die Sätze der Figur, deren Platz sie einnimmt. Ein Verräter spricht nicht.",
               chars_talk_keep="(behält den Originalsatz)", chars_save="Speichern", chars_cancel="Abbrechen", chars_active_on="An: wird mit den Räumen geteilt, denen du beitrittst oder die du erstellst, und kann in Partien vorkommen.", chars_active_off="Aus: wird mit keinem Raum geteilt (nichts wird hochgeladen) und kommt nie vor.", chars_need_model="Wähle ein 3D-Modell aus dem Modellordner.",
               chars_has_anims="eigene Animationen", chars_has_talk="{n} Sätze", chars_has_image="Bild", roster_saved="Figurenauswahl gespeichert."),
    "pt": dict(chars_title="Novos personagens", chars_desc="Um novo personagem não substitui ninguém: entra no sorteio de cada partida, com a mesma chance dos originais (escolha quem pode aparecer com a «Seleção de personagens» da sala de espera). Sem nome, animações ou falas próprios, usa os do personagem cujo lugar ocupa, e sempre joga como ele. Para uma skin que substitui sempre um personagem, use a lista acima.",
               chars_add="Adicionar personagem", chars_edit="Editar", chars_delete="Remover", chars_images_open="Abrir pasta de imagens",
               chars_none="Ainda não há novos personagens.", chars_name="Nome", chars_name_keep="(fica o do lugar que ocupar)",
               chars_model="Modelo 3D", chars_role="Tipo", chars_role_pawn="Personagem", chars_role_traitor="Traidor",
               chars_image="Imagem (retratos)", chars_image_none="Tirar do modelo", chars_anims="Animações",
               chars_talk="Falas", chars_talk_hint="Escreva só as que quer mudar; as vazias ficam com as do personagem cujo lugar ocupa. Um traidor não fala.",
               chars_talk_keep="(fica a fala original)", chars_save="Salvar", chars_cancel="Cancelar", chars_active_on="Ativado: é compartilhado com as salas em que você entra ou que cria, e pode aparecer nas partidas.", chars_active_off="Desativado: não é compartilhado com nenhuma sala (nada é enviado) e nunca aparece.", chars_need_model="Escolha um modelo 3D da pasta de modelos.",
               chars_has_anims="animações próprias", chars_has_talk="{n} falas", chars_has_image="imagem", roster_saved="Seleção de personagens salva."),
    "ru": dict(chars_title="Новые персонажи", chars_desc="Новый персонаж никого не заменяет: он участвует в жеребьёвке каждого матча с тем же шансом, что и оригиналы (кто может появиться, выбирается в «Выборе персонажей» в зале ожидания). Без своего имени, анимаций или реплик он использует те, что у персонажа, чьё место занимает, и всегда играет как он. Для скина, который всегда заменяет персонажа, используйте список выше.",
               chars_add="Добавить персонажа", chars_edit="Изменить", chars_delete="Убрать", chars_images_open="Открыть папку изображений",
               chars_none="Новых персонажей пока нет.", chars_name="Имя", chars_name_keep="(остаётся имя занятого места)",
               chars_model="3D-модель", chars_role="Тип", chars_role_pawn="Персонаж", chars_role_traitor="Предатель",
               chars_image="Изображение (портреты)", chars_image_none="Сделать из модели", chars_anims="Анимации",
               chars_talk="Реплики", chars_talk_hint="Пишите только те, что хотите изменить; пустые остаются репликами персонажа, чьё место он занимает. Предатель не говорит.",
               chars_talk_keep="(остаётся исходная реплика)", chars_save="Сохранить", chars_cancel="Отмена", chars_active_on="Вкл.: передаётся в комнаты, в которые вы входите или которые создаёте, и может появиться в матче.", chars_active_off="Выкл.: не передаётся ни в одну комнату (ничего не загружается) и никогда не появляется.", chars_need_model="Выберите 3D-модель из папки моделей.",
               chars_has_anims="свои анимации", chars_has_talk="реплик: {n}", chars_has_image="изображение", roster_saved="Выбор персонажей сохранён."),
    "ja": dict(chars_title="新キャラクター", chars_desc="新キャラクターは誰とも入れ替わりません。毎試合の抽選にオリジナルと同じ確率で加わります（出場できるキャラはゲームの待機ルームの「キャラクター選択」で選びます）。名前・アニメーション・セリフがなければ、入った枠のキャラクターのものを使い、プレイも常にそのキャラクターと同じです。常に特定のキャラを置き換えるスキンは上のリストを使ってください。",
               chars_add="キャラクターを追加", chars_edit="編集", chars_delete="削除", chars_images_open="画像フォルダーを開く",
               chars_none="新キャラクターはまだいません。", chars_name="名前", chars_name_keep="（入った枠の名前のまま）",
               chars_model="3Dモデル", chars_role="種類", chars_role_pawn="キャラクター", chars_role_traitor="裏切り者",
               chars_image="画像（顔アイコン）", chars_image_none="モデルから作る", chars_anims="アニメーション",
               chars_talk="セリフ", chars_talk_hint="変えたいものだけ書いてください。空欄は入った枠のキャラクターのセリフのままです。裏切り者は話しません。",
               chars_talk_keep="（元のセリフのまま）", chars_save="保存", chars_cancel="キャンセル", chars_active_on="オン：参加・作成するルームに共有され、試合に登場することがあります。", chars_active_off="オフ：どのルームにも共有されず（何もアップロードされません）、登場しません。", chars_need_model="モデルフォルダーの3Dモデルを選んでください。",
               chars_has_anims="独自アニメーション", chars_has_talk="セリフ {n} 件", chars_has_image="画像", roster_saved="キャラクター選択を保存しました。"),
    "ko": dict(chars_title="새 캐릭터", chars_desc="새 캐릭터는 누구도 대체하지 않습니다. 매 판 추첨에 원래 캐릭터와 같은 확률로 들어갑니다(누가 나올 수 있는지는 대기실의 \"캐릭터 선택\"에서 고릅니다). 자기 이름·애니메이션·대사가 없으면 들어간 자리 캐릭터의 것을 쓰고, 플레이도 항상 그 캐릭터와 같습니다. 항상 특정 캐릭터를 대체하는 스킨은 위 목록을 쓰세요.",
               chars_add="캐릭터 추가", chars_edit="편집", chars_delete="제거", chars_images_open="이미지 폴더 열기",
               chars_none="아직 새 캐릭터가 없습니다.", chars_name="이름", chars_name_keep="(들어간 자리의 이름 유지)",
               chars_model="3D 모델", chars_role="종류", chars_role_pawn="캐릭터", chars_role_traitor="배신자",
               chars_image="이미지(초상화)", chars_image_none="모델에서 만들기", chars_anims="애니메이션",
               chars_talk="대사", chars_talk_hint="바꾸고 싶은 것만 쓰세요. 빈칸은 들어간 자리 캐릭터의 대사를 유지합니다. 배신자는 말하지 않습니다.",
               chars_talk_keep="(원래 대사 유지)", chars_save="저장", chars_cancel="취소", chars_active_on="켜짐: 참가하거나 만드는 방에 공유되며 경기에 나올 수 있습니다.", chars_active_off="꺼짐: 어떤 방에도 공유되지 않고(아무것도 업로드되지 않음) 나오지 않습니다.", chars_need_model="모델 폴더의 3D 모델을 고르세요.",
               chars_has_anims="자체 애니메이션", chars_has_talk="대사 {n}개", chars_has_image="이미지", roster_saved="캐릭터 선택을 저장했습니다."),
    "zh-CN": dict(chars_title="新角色", chars_desc="新角色不替换任何人：它会以与原角色相同的概率加入每局的抽选（在游戏等待室的“角色选择”里决定谁可以出场）。没有自己的名字、动画或台词时，就使用它所占位置的角色的，玩法也始终与该角色相同。想要始终替换某个角色的皮肤，请用上面的列表。",
               chars_add="添加角色", chars_edit="编辑", chars_delete="移除", chars_images_open="打开图片文件夹",
               chars_none="还没有新角色。", chars_name="名字", chars_name_keep="（沿用所占位置的名字）",
               chars_model="3D 模型", chars_role="类型", chars_role_pawn="角色", chars_role_traitor="叛徒",
               chars_image="图片（头像）", chars_image_none="从模型生成", chars_anims="动画",
               chars_talk="台词", chars_talk_hint="只写想改的；空着的沿用所占位置角色的台词。叛徒不说话。",
               chars_talk_keep="（沿用原台词）", chars_save="保存", chars_cancel="取消", chars_active_on="已启用：会共享给你加入或创建的房间，并可能在对局中出现。", chars_active_off="已停用：不共享给任何房间（不上传任何内容），也不会出现。", chars_need_model="请从模型文件夹选择一个 3D 模型。",
               chars_has_anims="自带动画", chars_has_talk="{n} 句台词", chars_has_image="图片", roster_saved="角色选择已保存。"),
    "zh-TW": dict(chars_title="新角色", chars_desc="新角色不替換任何人：它會以與原角色相同的機率加入每局的抽選（在遊戲等待室的「角色選擇」裡決定誰可以出場）。沒有自己的名字、動畫或台詞時，就使用它所佔位置的角色的，玩法也始終與該角色相同。想要始終替換某個角色的造型，請用上面的清單。",
               chars_add="新增角色", chars_edit="編輯", chars_delete="移除", chars_images_open="開啟圖片資料夾",
               chars_none="還沒有新角色。", chars_name="名字", chars_name_keep="（沿用所佔位置的名字）",
               chars_model="3D 模型", chars_role="類型", chars_role_pawn="角色", chars_role_traitor="叛徒",
               chars_image="圖片（頭像）", chars_image_none="從模型產生", chars_anims="動畫",
               chars_talk="台詞", chars_talk_hint="只寫想改的；空著的沿用所佔位置角色的台詞。叛徒不說話。",
               chars_talk_keep="（沿用原台詞）", chars_save="儲存", chars_cancel="取消", chars_active_on="已啟用：會分享給你加入或建立的房間，並可能在對局中出現。", chars_active_off="已停用：不分享給任何房間（不上傳任何內容），也不會出現。", chars_need_model="請從模型資料夾選擇一個 3D 模型。",
               chars_has_anims="自帶動畫", chars_has_talk="{n} 句台詞", chars_has_image="圖片", roster_saved="角色選擇已儲存。"),
}
for _l, _d in _CHARS.items():
    S[_l].update(_d)

# which game character a new character takes its animations from
_ANIMFROM = {
    "en": ("Animations of", "{n}'s animations", "Without its own animations, it moves like the character chosen in \"Animations of\" (not the one whose slot it takes). Your own idle/walk/run animations replace those."),
    "es": ("Animaciones de", "animaciones de {n}", "Sin animaciones propias se mueve como el personaje elegido en «Animaciones de» (no como el del sitio que ocupa). Tus animaciones de reposo/andar/correr sustituyen a esas."),
    "fr": ("Animations de", "animations de {n}", "Sans animations propres, il bouge comme le personnage choisi dans « Animations de » (pas comme celui dont il prend la place). Vos animations repos/marche/course remplacent celles-ci."),
    "it": ("Animazioni di", "animazioni di {n}", "Senza animazioni proprie si muove come il personaggio scelto in «Animazioni di» (non come quello di cui prende il posto). Le tue animazioni di riposo/camminata/corsa sostituiscono quelle."),
    "de": ("Animationen von", "Animationen von {n}", "Ohne eigene Animationen bewegt sie sich wie die bei „Animationen von“ gewählte Figur (nicht wie die, deren Platz sie einnimmt). Deine eigenen Ruhe-/Geh-/Lauf-Animationen ersetzen diese."),
    "pt": ("Animações de", "animações de {n}", "Sem animações próprias, move-se como o personagem escolhido em «Animações de» (não como o do lugar que ocupa). Suas animações de repouso/andar/correr substituem essas."),
    "ru": ("Анимации от", "анимации: {n}", "Без своих анимаций двигается как персонаж, выбранный в «Анимации от» (а не как тот, чьё место занимает). Ваши анимации покоя/ходьбы/бега заменяют их."),
    "ja": ("アニメーション元", "{n}のアニメーション", "独自アニメーションがない場合は「アニメーション元」で選んだキャラクターと同じ動きをします（入った枠のキャラではありません）。自分の待機/歩き/走りアニメーションはそれより優先されます。"),
    "ko": ("애니메이션 원본", "{n}의 애니메이션", "자체 애니메이션이 없으면 \"애니메이션 원본\"에서 고른 캐릭터처럼 움직입니다(들어간 자리의 캐릭터가 아님). 직접 넣은 대기/걷기/달리기 애니메이션이 우선합니다."),
    "zh-CN": ("动画来源", "{n}的动画", "没有自带动画时，按“动画来源”中选择的角色来动（而不是所占位置的角色）。你自己的待机/行走/奔跑动画会替换它们。"),
    "zh-TW": ("動畫來源", "{n}的動畫", "沒有自帶動畫時，按「動畫來源」中選擇的角色來動（而不是所佔位置的角色）。你自己的待機/行走/奔跑動畫會替換它們。"),
}
for _l, (_a, _b, _c) in _ANIMFROM.items():
    S[_l].update(chars_anim_from=_a, chars_anim_from_short=_b, chars_anims_hint=_c)
S["es"]["chars_desc"] = ("Un personaje nuevo no sustituye a nadie: entra en el sorteo de cada partida con la misma probabilidad que los "
                         "originales (eliges quién puede salir con la «Selección de personajes» de la sala de espera del juego). Juega "
                         "como el personaje cuyo sitio ocupa, pero se mueve como el que elijas en «Animaciones de» (o con tus animaciones). "
                         "Sin nombre o frases propias usa los del sitio que ocupa. Para una skin que sustituya siempre a un personaje, usa la lista de arriba.")
S["en"]["chars_desc"] = ("A new character doesn't replace anyone: it's added to the pool for each match, with the same chance of appearing as the originals (choose who can appear with the \"Character Selection\" in the game's waiting room). It plays like the character whose slot it takes, but moves like the one you pick in \"Animations of\" (or with your own animations). If it has no name or lines of its own, it uses those of the character whose slot it takes. For a skin that always replaces a character, use the list above.")

# dialogue images (per reaction and per line)
_TALKIMG = {
    "en": ("Image when worried", "Image when attacked", "In the game each character makes a face in some lines: worried (gas, danger, injured, hungry, dying) and attacked. Pick an image for each, or for any single line in Lines; without one, the main image is used.", "worried", "attacked", "(main image)", "(image of its reaction)"),
    "es": ("Imagen preocupado", "Imagen atacado", "En el juego cada personaje pone cara en algunas frases: preocupado (gas, peligro, herido, hambre, moribundo) y atacado. Elige una imagen para cada una, o para cualquier frase en Frases; sin ella se usa la imagen principal.", "preocupado", "atacado", "(imagen principal)", "(imagen de su reacción)"),
    "fr": ("Image inquiet", "Image attaqué", "Dans le jeu, chaque personnage fait une tête dans certaines répliques : inquiet (gaz, danger, blessé, faim, mourant) et attaqué. Choisissez une image pour chacune, ou pour n'importe quelle réplique dans Répliques ; sinon, l'image principale est utilisée.", "inquiet", "attaqué", "(image principale)", "(image de sa réaction)"),
    "it": ("Immagine preoccupato", "Immagine attaccato", "Nel gioco ogni personaggio fa una faccia in alcune battute: preoccupato (gas, pericolo, ferito, fame, morente) e attaccato. Scegli un'immagine per ciascuna, o per qualsiasi battuta in Battute; senza, si usa l'immagine principale.", "preoccupato", "attaccato", "(immagine principale)", "(immagine della sua reazione)"),
    "de": ("Bild besorgt", "Bild angegriffen", "Im Spiel macht jede Figur in manchen Sätzen ein Gesicht: besorgt (Gas, Gefahr, verletzt, hungrig, sterbend) und angegriffen. Wähle für jedes ein Bild oder für einzelne Sätze unter Sätze; sonst wird das Hauptbild genutzt.", "besorgt", "angegriffen", "(Hauptbild)", "(Bild seiner Reaktion)"),
    "pt": ("Imagem preocupado", "Imagem atacado", "No jogo cada personagem faz uma cara em algumas falas: preocupado (gás, perigo, ferido, fome, morrendo) e atacado. Escolha uma imagem para cada, ou para qualquer fala em Falas; sem ela, usa-se a imagem principal.", "preocupado", "atacado", "(imagem principal)", "(imagem da sua reação)"),
    "ru": ("Изображение: встревожен", "Изображение: под атакой", "В игре каждый персонаж меняет выражение лица в некоторых репликах: встревожен (газ, опасность, ранен, голоден, при смерти) и под атакой. Выберите изображение для каждого или для любой реплики в «Реплики»; без него используется основное.", "встревожен", "под атакой", "(основное изображение)", "(изображение реакции)"),
    "ja": ("焦り顔の画像", "襲われた顔の画像", "ゲームでは一部のセリフでキャラクターの表情が変わります：焦り（ガス・危険・負傷・空腹・瀕死）と襲われた時。それぞれ、またはセリフごとに画像を選べます。未設定ならメイン画像です。", "焦り", "襲われた", "（メイン画像）", "（表情の画像）"),
    "ko": ("걱정 표정 이미지", "공격받은 표정 이미지", "게임에서는 일부 대사에서 캐릭터의 표정이 바뀝니다: 걱정(가스, 위험, 부상, 배고픔, 빈사)과 공격받음. 각각 또는 대사별로 이미지를 고르세요. 없으면 기본 이미지를 씁니다.", "걱정", "공격받음", "(기본 이미지)", "(표정 이미지)"),
    "zh-CN": ("担忧时的图片", "被袭击时的图片", "游戏中每个角色在部分台词里会换表情：担忧（毒气、危险、受伤、饥饿、濒死）和被袭击。可分别选图片，也可在“台词”里为单句选图；不选则用主图片。", "担忧", "被袭击", "（主图片）", "（表情图片）"),
    "zh-TW": ("擔憂時的圖片", "被襲擊時的圖片", "遊戲中每個角色在部分台詞裡會換表情：擔憂（毒氣、危險、受傷、飢餓、瀕死）和被襲擊。可分別選圖片，也可在「台詞」裡為單句選圖；不選則用主圖片。", "擔憂", "被襲擊", "（主圖片）", "（表情圖片）"),
}
for _l, (_w, _a, _h, _rw, _ra, _m, _r) in _TALKIMG.items():
    S[_l].update(chars_img_worried=_w, chars_img_attacked=_a, chars_img_hint=_h, chars_react_worried=_rw,
                 chars_react_attacked=_ra, chars_img_main=_m, chars_img_by_react=_r)
# the line situations (our own description; not the game's text)
_TALK_LABELS = {
    "en": ["Searches and finds nothing", "Breathes in gas", "Danger enters the room", "Breaks the fuse box", "Finds a secret passage", "Finds a note", "Finds a fuse box", "Can't carry more items", "Can't carry more weapons", "Picks up food", "Picks up medicine", "Picks up a weapon", "Alone with someone (both suspects)", "Alone with the killer", "Alone with the victim", "Match starts", "Gets attacked", "Gets attacked on the last day", "Healed by someone else", "Repairs the fuse box", "Acts while dying", "Acts while hungry", "Acts while injured", "Walks into a dark room", "Uses a secret passage", "Gives food to someone", "Uses medicine on themselves", "Gives medicine to someone"],
    "es": ["Busca y no encuentra nada", "Respira gas", "Un peligro ha entrado en la sala", "Rompe la caja de fusibles",
           "Descubre un pasadizo secreto", "Descubre una nota", "Descubre una caja de fusibles", "No puede llevar más objetos",
           "No puede llevar más armas", "Coge comida", "Coge un medicamento", "Coge un arma",
           "A solas con alguien (los dos sospechosos)", "A solas con el asesino", "A solas con la víctima",
           "Empieza la partida", "Le atacan", "Le atacan el último día", "Otro le cura", "Arregla la caja de fusibles",
           "Actúa estando moribundo", "Actúa con hambre", "Actúa estando herido", "Entra en una sala a oscuras", "Usa un pasadizo secreto",
           "Da comida a alguien", "Se toma un medicamento", "Da un medicamento a alguien"],
    "fr": ["Fouille et ne trouve rien", "Respire du gaz", "Un danger entre dans la salle", "Casse la boîte à fusibles", "Trouve un passage secret", "Trouve une note", "Trouve une boîte à fusibles", "Ne peut pas porter plus d'objets", "Ne peut pas porter plus d'armes", "Ramasse de la nourriture", "Ramasse un médicament", "Ramasse une arme", "Seul avec quelqu'un (tous deux suspects)", "Seul avec le tueur", "Seul avec la victime", "Début de la partie", "Se fait attaquer", "Se fait attaquer le dernier jour", "Soigné par quelqu'un d'autre", "Répare la boîte à fusibles", "Agit en étant mourant", "Agit en ayant faim", "Agit en étant blessé", "Entre dans une salle plongée dans le noir", "Utilise un passage secret", "Donne de la nourriture à quelqu'un", "Prend un médicament", "Donne un médicament à quelqu'un"],
    "it": ["Cerca e non trova niente", "Respira gas", "Un pericolo entra nella stanza", "Rompe la scatola dei fusibili", "Trova un passaggio segreto", "Trova un biglietto", "Trova una scatola dei fusibili", "Non può portare altri oggetti", "Non può portare altre armi", "Raccoglie cibo", "Raccoglie una medicina", "Raccoglie un'arma", "Solo con qualcuno (entrambi sospettati)", "Solo con l'assassino", "Solo con la vittima", "Inizio della partita", "Viene attaccato", "Viene attaccato l'ultimo giorno", "Curato da qualcun altro", "Ripara la scatola dei fusibili", "Agisce mentre sta morendo", "Agisce affamato", "Agisce ferito", "Entra in una stanza al buio", "Usa un passaggio segreto", "Dà cibo a qualcuno", "Prende una medicina", "Dà una medicina a qualcuno"],
    "de": ["Sucht und findet nichts", "Atmet Gas ein", "Eine Gefahr dringt in den Raum ein", "Zerstört den Sicherungskasten", "Entdeckt einen Geheimgang", "Entdeckt eine Notiz", "Entdeckt einen Sicherungskasten", "Kann keine Gegenstände mehr tragen", "Kann keine Waffen mehr tragen", "Hebt Essen auf", "Hebt Medizin auf", "Hebt eine Waffe auf", "Allein mit jemandem (beide verdächtig)", "Allein mit dem Mörder", "Allein mit dem Opfer", "Spielbeginn", "Wird angegriffen", "Wird am letzten Tag angegriffen", "Von jemand anderem geheilt", "Repariert den Sicherungskasten", "Handelt im Sterben", "Handelt hungrig", "Handelt verletzt", "Betritt einen dunklen Raum", "Benutzt einen Geheimgang", "Gibt jemandem Essen", "Nimmt Medizin", "Gibt jemandem Medizin"],
    "pt": ["Procura e não encontra nada", "Respira gás", "Um perigo entra na sala", "Quebra a caixa de fusíveis", "Descobre uma passagem secreta", "Descobre um bilhete", "Descobre uma caixa de fusíveis", "Não consegue carregar mais itens", "Não consegue carregar mais armas", "Pega comida", "Pega um remédio", "Pega uma arma", "Sozinho com alguém (ambos suspeitos)", "Sozinho com o assassino", "Sozinho com a vítima", "Início da partida", "É atacado", "É atacado no último dia", "Curado por outra pessoa", "Conserta a caixa de fusíveis", "Age enquanto está morrendo", "Age com fome", "Age ferido", "Entra em uma sala escura", "Usa uma passagem secreta", "Dá comida a alguém", "Toma um remédio", "Dá um remédio a alguém"],
    "ru": ["Ищет и ничего не находит", "Вдыхает газ", "В комнату проникла опасность", "Ломает щиток", "Находит тайный ход", "Находит записку", "Находит щиток", "Не может нести больше предметов", "Не может нести больше оружия", "Подбирает еду", "Подбирает лекарство", "Подбирает оружие", "Наедине с кем-то (оба под подозрением)", "Наедине с убийцей", "Наедине с жертвой", "Начало матча", "Подвергается нападению", "Подвергается нападению в последний день", "Его лечит другой", "Чинит щиток", "Действует при смерти", "Действует голодным", "Действует раненым", "Входит в тёмную комнату", "Использует тайный ход", "Даёт кому-то еду", "Принимает лекарство", "Даёт кому-то лекарство"],
    "ja": ["探索して何も見つからない", "ガスを吸う", "部屋に危険が侵入した", "配電盤を壊す", "隠し通路を見つける", "メモを見つける", "配電盤を見つける", "これ以上アイテムを持てない", "これ以上武器を持てない", "食料を拾う", "薬を拾う", "武器を拾う", "誰かと二人きり（どちらも怪しい）", "殺人鬼と二人きり", "被害者と二人きり", "試合開始", "襲われる", "最終日に襲われる", "他の人に治療される", "配電盤を直す", "瀕死の状態で行動する", "空腹の状態で行動する", "負傷した状態で行動する", "暗い部屋に入る", "隠し通路を使う", "誰かに食料をあげる", "自分に薬を使う", "誰かに薬をあげる"],
    "ko": ["수색했지만 아무것도 없음", "가스를 들이마심", "방에 위험이 침입함", "배전반을 부숨", "비밀 통로를 발견함", "메모를 발견함", "배전반을 발견함", "아이템을 더 들 수 없음", "무기를 더 들 수 없음", "음식을 주움", "약을 주움", "무기를 주움", "누군가와 단둘이 (둘 다 수상함)", "살인마와 단둘이", "피해자와 단둘이", "게임 시작", "공격당함", "마지막 날에 공격당함", "다른 사람이 치료해 줌", "배전반을 고침", "빈사 상태로 행동함", "배고픈 상태로 행동함", "부상 상태로 행동함", "어두운 방에 들어감", "비밀 통로를 사용함", "누군가에게 음식을 줌", "스스로 약을 씀", "누군가에게 약을 줌"],
    "zh-CN": ["搜索但一无所获", "吸入毒气", "危险闯入了房间", "破坏配电箱", "发现密道", "发现纸条", "发现配电箱", "拿不下更多道具", "拿不下更多武器", "捡到食物", "捡到药品", "捡到武器", "与某人独处（两人都可疑）", "与杀手独处", "与受害者独处", "对局开始", "遭到袭击", "最后一天遭到袭击", "被别人治疗", "修好配电箱", "濒死时行动", "饥饿时行动", "受伤时行动", "走进黑暗的房间", "使用密道", "把食物给别人", "自己用药", "把药给别人"],
    "zh-TW": ["搜索但一無所獲", "吸入毒氣", "危險闖入了房間", "破壞配電箱", "發現密道", "發現紙條", "發現配電箱", "拿不下更多道具", "拿不下更多武器", "撿到食物", "撿到藥品", "撿到武器", "與某人獨處（兩人都可疑）", "與殺手獨處", "與受害者獨處", "對局開始", "遭到襲擊", "最後一天遭到襲擊", "被別人治療", "修好配電箱", "瀕死時行動", "飢餓時行動", "受傷時行動", "走進黑暗的房間", "使用密道", "把食物給別人", "自己用藥", "把藥給別人"],
}
for _l, _labels in _TALK_LABELS.items():
    for _k, _v in zip(("cannotGetAnything", "damagedByGasRoom", "dangerHasInvaded", "destroySwitchboard", "discoverBypass",
                       "discoverNote", "discoverSwitchboard", "fullItem", "fullWeapon", "getFood", "getMedicine", "getWeapon",
                       "killCheckKillerEachOther", "killCheckKillerOnlyOne", "killCheckTarget", "pawnGameStart", "raid",
                       "raidFinalDay", "recoveredByOtherUsingMedicine", "repairSwitchboard", "startAction_statusDying",
                       "startAction_statusHunger", "startAction_statusInjury", "stepIntoBlackoutRoom", "useBypass",
                       "useFoodForOther", "useMedicineForMyself", "useMedicineForOther"), _labels):
        S[_l]["talk_" + _k] = _v

_GAME_OPEN = {
    "en": "CRIMESIGHT is already open. Close it and press the button again: the launcher will open it for you, already connected.",
    "es": "CRIMESIGHT ya está abierto. Ciérralo y vuelve a pulsar el botón: el lanzador lo abre por ti, ya conectado.",
    "fr": "CRIMESIGHT est déjà ouvert. Fermez-le et appuyez de nouveau sur le bouton : le lanceur l'ouvre pour vous, déjà connecté.",
    "it": "CRIMESIGHT è già aperto. Chiudilo e premi di nuovo il pulsante: il launcher lo apre per te, già connesso.",
    "de": "CRIMESIGHT ist bereits geöffnet. Schließe es und drücke den Knopf erneut: Der Launcher öffnet es für dich, schon verbunden.",
    "pt": "O CRIMESIGHT já está aberto. Feche-o e aperte o botão de novo: o launcher abre para você, já conectado.",
    "ru": "CRIMESIGHT уже открыта. Закройте её и нажмите кнопку ещё раз: лаунчер сам откроет игру, уже с подключением.",
    "ja": "CRIMESIGHTはすでに起動しています。終了してからもう一度ボタンを押してください。ランチャーが接続済みの状態で起動します。",
    "ko": "CRIMESIGHT가 이미 실행 중입니다. 종료한 뒤 버튼을 다시 누르세요. 런처가 연결된 상태로 실행해 줍니다.",
    "zh-CN": "CRIMESIGHT 已经在运行。请先关闭它，再按一次按钮：启动器会帮你打开并自动连接。",
    "zh-TW": "CRIMESIGHT 已經在執行。請先關閉它，再按一次按鈕：啟動器會幫你開啟並自動連線。",
}
for _l, _v in _GAME_OPEN.items():
    S[_l]["err_game_open"] = _v

_LOCKED = {
    "en": "Windows won't let the launcher change the game's files ({path}). Make sure the game is closed. If you use \"Controlled folder access\" in Windows Security, allow the launcher there. You can also fix damaged files in Steam → CRIMESIGHT → Properties → Installed Files → \"Verify integrity of game files\".",
    "es": "Windows no deja al lanzador modificar los archivos del juego ({path}). Comprueba que el juego está cerrado. Si usas el «Acceso controlado a carpetas» de Seguridad de Windows, permite ahí el lanzador. En Steam → CRIMESIGHT → Propiedades → Archivos instalados → «Verificar integridad» también se arreglan archivos dañados.",
    "fr": "Windows n'autorise pas le lanceur à modifier les fichiers du jeu ({path}). Vérifiez que le jeu est fermé. Si vous utilisez « Dispositif d'accès contrôlé aux dossiers » de Sécurité Windows, autorisez-y le lanceur. Steam → CRIMESIGHT → Propriétés → Fichiers installés → « Vérifier l'intégrité » répare aussi les fichiers endommagés.",
    "it": "Windows non permette al launcher di modificare i file del gioco ({path}). Assicurati che il gioco sia chiuso. Se usi «Accesso alle cartelle controllato» di Sicurezza di Windows, consenti lì il launcher. Steam → CRIMESIGHT → Proprietà → File installati → «Verifica integrità» ripara anche i file danneggiati.",
    "de": "Windows lässt den Launcher die Spieldateien nicht ändern ({path}). Prüfe, ob das Spiel geschlossen ist. Wenn du in der Windows-Sicherheit den „Überwachten Ordnerzugriff“ nutzt, erlaube dort den Launcher. Steam → CRIMESIGHT → Eigenschaften → Installierte Dateien → „Dateien auf Fehler überprüfen“ repariert beschädigte Dateien.",
    "pt": "O Windows não deixa o launcher modificar os arquivos do jogo ({path}). Verifique se o jogo está fechado. Se você usa o \"Acesso controlado a pastas\" da Segurança do Windows, permita o launcher lá. Steam → CRIMESIGHT → Propriedades → Arquivos instalados → \"Verificar integridade\" também corrige arquivos danificados.",
    "ru": "Windows не даёт лаунчеру изменить файлы игры ({path}). Убедитесь, что игра закрыта. Если включён «Контролируемый доступ к папкам» в Безопасности Windows, разрешите там лаунчер. Steam → CRIMESIGHT → Свойства → Установленные файлы → «Проверить целостность» также исправит повреждённые файлы.",
    "ja": "Windowsがランチャーによるゲームファイルの変更を許可していません（{path}）。ゲームが閉じているか確認してください。Windowsセキュリティの「コントロールされたフォルダーアクセス」を使っている場合は、ランチャーを許可してください。Steam → CRIMESIGHT → プロパティ → インストール済みファイル →「整合性を確認」で破損ファイルも直ります。",
    "ko": "Windows가 런처의 게임 파일 수정을 허용하지 않습니다({path}). 게임이 종료되어 있는지 확인하세요. Windows 보안의 '제어된 폴더 액세스'를 사용 중이라면 런처를 허용하세요. Steam → CRIMESIGHT → 속성 → 설치된 파일 → '무결성 확인'으로 손상된 파일도 복구됩니다.",
    "zh-CN": "Windows 不允许启动器修改游戏文件（{path}）。请确认游戏已关闭。如果你开启了 Windows 安全中心的“受控文件夹访问”，请在其中允许启动器。在 Steam → CRIMESIGHT → 属性 → 已安装文件 →“验证完整性”也能修复损坏的文件。",
    "zh-TW": "Windows 不允許啟動器修改遊戲檔案（{path}）。請確認遊戲已關閉。如果你開啟了 Windows 安全性的「受控制的資料夾存取」，請在其中允許啟動器。在 Steam → CRIMESIGHT → 內容 → 已安裝檔案 →「驗證完整性」也能修復損壞的檔案。",
}
for _l, _v in _LOCKED.items():
    S[_l]["err_game_locked"] = _v

# --- updating with the game, a session or another launcher open ------------------------------------
_UPD_CLOSE = {
    "en": dict(update_confirm_close="To update, the game, the current session and any other open launchers will be closed. If you're in a match, this counts as leaving it.",
               update_close_btn="Close everything and update", update_closing="Closing the game and the session to update…"),
    "es": dict(update_confirm_close="Para actualizar se cerrarán el juego, la sesión en marcha y cualquier otro lanzador abierto. Si estás en mitad de una partida, contará como abandono.",
               update_close_btn="Cerrar todo y actualizar", update_closing="Cerrando el juego y la sesión para actualizar…"),
    "fr": dict(update_confirm_close="Pour mettre à jour, le jeu, la session en cours et tout autre lanceur ouvert seront fermés. Si vous êtes en pleine partie, cela compte comme un abandon.",
               update_close_btn="Tout fermer et mettre à jour", update_closing="Fermeture du jeu et de la session pour la mise à jour…"),
    "it": dict(update_confirm_close="Per aggiornare verranno chiusi il gioco, la sessione in corso e qualsiasi altro launcher aperto. Se sei a metà partita, conta come abbandono.",
               update_close_btn="Chiudi tutto e aggiorna", update_closing="Chiusura del gioco e della sessione per l'aggiornamento…"),
    "de": dict(update_confirm_close="Zum Aktualisieren werden das Spiel, die laufende Sitzung und alle anderen offenen Launcher geschlossen. Mitten in einer Partie zählt das als Verlassen.",
               update_close_btn="Alles schließen und aktualisieren", update_closing="Spiel und Sitzung werden für das Update geschlossen…"),
    "pt": dict(update_confirm_close="Para atualizar, o jogo, a sessão em andamento e qualquer outro launcher aberto serão fechados. Se você estiver no meio de uma partida, conta como abandono.",
               update_close_btn="Fechar tudo e atualizar", update_closing="Fechando o jogo e a sessão para atualizar…"),
    "ru": dict(update_confirm_close="Для обновления будут закрыты игра, текущий сеанс и другие открытые лаунчеры. Если вы посреди матча, это засчитается как выход.",
               update_close_btn="Закрыть всё и обновить", update_closing="Закрываю игру и сеанс для обновления…"),
    "ja": dict(update_confirm_close="アップデートのため、ゲーム・実行中のセッション・ほかに開いているランチャーを閉じます。対戦中の場合は途中退出になります。",
               update_close_btn="すべて閉じてアップデート", update_closing="アップデートのためゲームとセッションを終了しています…"),
    "ko": dict(update_confirm_close="업데이트하려면 게임, 진행 중인 세션, 열려 있는 다른 런처가 모두 종료됩니다. 대전 중이라면 이탈로 처리됩니다.",
               update_close_btn="모두 닫고 업데이트", update_closing="업데이트를 위해 게임과 세션을 종료하는 중…"),
    "zh-CN": dict(update_confirm_close="更新时会关闭游戏、正在进行的会话以及其他打开的启动器。如果你正在对局中，将算作中途退出。",
                  update_close_btn="全部关闭并更新", update_closing="正在关闭游戏和会话以进行更新…"),
    "zh-TW": dict(update_confirm_close="更新時會關閉遊戲、正在進行的工作階段以及其他開啟的啟動器。如果你正在對局中，將算作中途退出。",
                  update_close_btn="全部關閉並更新", update_closing="正在關閉遊戲和工作階段以進行更新…"),
}
for _l, _d in _UPD_CLOSE.items():
    S[_l].update(_d)

_LINUX = {
    "en": "Linux / Steam Deck: also add this to CRIMESIGHT's launch options in Steam (Properties → General), or BepInEx won't load: {opt}",
    "es": "Linux / Steam Deck: añade también esto a las opciones de lanzamiento de CRIMESIGHT en Steam (Propiedades → General), o BepInEx no se cargará: {opt}",
    "fr": "Linux / Steam Deck : ajoutez aussi ceci aux options de lancement de CRIMESIGHT dans Steam (Propriétés → Général), sinon BepInEx ne se chargera pas : {opt}",
    "it": "Linux / Steam Deck: aggiungi anche questo alle opzioni di avvio di CRIMESIGHT su Steam (Proprietà → Generali), altrimenti BepInEx non si caricherà: {opt}",
    "de": "Linux / Steam Deck: Füge das auch zu den Startoptionen von CRIMESIGHT in Steam hinzu (Eigenschaften → Allgemein), sonst lädt BepInEx nicht: {opt}",
    "pt": "Linux / Steam Deck: adicione também isto às opções de inicialização do CRIMESIGHT na Steam (Propriedades → Geral), ou o BepInEx não carregará: {opt}",
    "ru": "Linux / Steam Deck: добавьте также это в параметры запуска CRIMESIGHT в Steam (Свойства → Общие), иначе BepInEx не загрузится: {opt}",
    "ja": "Linux / Steam Deck：SteamでCRIMESIGHTの起動オプション（プロパティ → 一般）にこれも追加してください。追加しないとBepInExが読み込まれません：{opt}",
    "ko": "Linux / Steam Deck: Steam에서 CRIMESIGHT 실행 옵션(속성 → 일반)에 이것도 추가하세요. 그렇지 않으면 BepInEx가 로드되지 않습니다: {opt}",
    "zh-CN": "Linux / Steam Deck：还需在 Steam 中 CRIMESIGHT 的启动选项（属性 → 通用）里加上这一行，否则 BepInEx 不会加载：{opt}",
    "zh-TW": "Linux / Steam Deck：還需在 Steam 中 CRIMESIGHT 的啟動選項（內容 → 一般）加上這一行，否則 BepInEx 不會載入：{opt}",
}
for _l, _v in _LINUX.items():
    S[_l]["bep_linux_note"] = _v

_lang = "en"



# stage creator (for now in English and Spanish; the other languages use English)
S["en"].update(
    stage_btn='Scenario Creator',
    stage_title='Scenario Creator',
    stage_desc="Rearrange the rooms of one of the game's scenarios. Each scenario you save shows up in the game's scenario list as a new one; the game's own scenarios are never changed.",
    stage_reading='Reading the scenarios from your game… {pct}%',
    stage_base='Base scenario',
    stage_name='Name',
    stage_name_ph='My scenario',
    stage_mine='My scenarios',
    stage_original="Reset to original",
    stage_save='Save',
    stage_saved='Saved. To play it, turn on hot reload (BepInEx) in Mods.',
    stage_delete='Delete',
    stage_test='Quick test',
    stage_test_ok="Ready. In the game, create a room and choose “Test Stage (CSR)”. You don't need to restart the game or save.",
    stage_test_stop='Stop testing',
    stage_test_off="The test stage is back to being an exact copy of scenario 01.",
    stage_need_bep="To test a scenario, you need hot reload (BepInEx). Turn it on in Mods.",
    stage_need_name='Give your scenario a name first.',
    stage_fix_first='Fix the problems marked in red first.',
    stage_tool_move='Rooms and doors',
    stage_tool_gas='Gas',
    stage_tool_spawn='Starting cells',
    stage_rotate='Rotate',
    stage_remove='Remove',
    stage_add='Add a room',
    stage_help_move="Drag a room to move it. R rotates it and Del removes it. Click a door to change it (door → furniture → secret passage), or click a window to let wolves in through it.",
    stage_help_gas='Click inside a room to add or remove a gas point.',
    stage_help_spawn='Click a cell to add or remove a starting cell for the characters.',
    stage_l_door='Door',
    stage_l_blocked='Blocked by furniture',
    stage_l_byway='Secret passage',
    stage_l_window='Window',
    stage_l_wolf='Wolf entrance',
    stage_l_entrance='Front door',
    stage_l_gas='Gas',
    stage_l_spawn='Starting cell',
    stage_ok='No problems.',
    stage_active="Currently in the test stage: {name}",
    stage_active_none="Currently in the test stage: copy of scenario 01",
    stage_stats='{rooms} rooms · {doors} doors · {wolves} wolf entrances · {gas} gas · {byways} passages',
    stage_only_host="When joining a room, everyone downloads the host's scenarios. Custom scenarios require every player to have hot reload (BepInEx): until everyone has it, the match can't start, and the room shows a note next to the names of the players missing it.",
    stage_p_no_rooms='Add at least one room.',
    stage_p_out_of_bounds='Room {room} is partly off the grid.',
    stage_p_overlap='Rooms {room} and {other} overlap.',
    stage_p_unreachable="Room {room} can't be reached from room 1: connect it with a door.",
    stage_p_entrance_blocked='The front door of room {room} is covered by another room.',
    stage_p_no_spawns='Choose at least one starting cell.',
    stage_p_spawn_outside='A starting cell is outside the rooms.',
    stage_p_spawn_blocked='A starting cell is on top of furniture.',
    stage_p_gas_outside='A gas point is outside the rooms.',
    stage_p_few_wolves="Wolf entrances: {n}. The game's scenarios have {want}.",
    stage_p_few_gas="Gas points: {n}. The game's scenarios have at least {want}.",
    stage_p_few_byways="Secret passages: {n}. The game's scenarios have at least {want}.",
    stage_p_no_entrance='There is no entrance hall.',
    stage_saved_live="Saved. It now appears in the game's scenario list under its name.",
    stage_saved_errors="Saved, but it won't show up in the game until you fix the problems marked in red.",
    stage_room_need_bep="This room has custom scenarios. Without hot reload (BepInEx) you can't play them: the host can't start one while you're in the room.",
    stage_room_synced="The room's scenarios are ready in your game: {n}.",
    stage_room_failed="Couldn't prepare the custom scenarios ({err}). You can still play the normal ones.",
    stage_import_bad="That file isn't a CRIMESIGHT Revival scenario, or it's for another version of the game.",
    stage_imported="Scenario imported. It's already in your list.",
    stage_exported="Scenario saved to {path}. You can send that file to anyone.",
    stage_too_many="The game's list has room for {n} of your scenarios. Turn one off first.",
    stage_saved_off="Saved, but turned off: you already have {n} scenarios turned on. Turn one off to use this one.",
    stage_import='Import',
    stage_export='Export',
    stage_none="You haven't saved any scenarios yet.",
)
S["es"].update(
    stage_btn='Creador de escenarios',
    stage_title='Creador de escenarios',
    stage_desc='Recoloca las habitaciones de un escenario del juego. Cada escenario que guardes aparece en la lista de escenarios del juego como uno nuevo; los del juego no se tocan nunca.',
    stage_reading='Leyendo los escenarios de tu juego… {pct}%',
    stage_base='Escenario base',
    stage_name='Nombre',
    stage_name_ph='Mi escenario',
    stage_mine='Mis escenarios',
    stage_original='Volver al original',
    stage_save='Guardar',
    stage_saved='Guardado. Para jugarlo, activa la recarga en caliente (BepInEx) en Mods.',
    stage_delete='Borrar',
    stage_test='Prueba rápida',
    stage_test_ok='Listo. En el juego, crea una sala y elige «Escenario de pruebas (CSR)». No hace falta reiniciar el juego ni guardar.',
    stage_test_stop='Dejar de probar',
    stage_test_off='El escenario de pruebas vuelve a ser una copia exacta del 01.',
    stage_need_bep='Para probar un escenario hace falta la recarga en caliente (BepInEx). Actívala en Mods.',
    stage_need_name='Primero ponle un nombre a tu escenario.',
    stage_fix_first='Primero arregla los problemas marcados en rojo.',
    stage_tool_move='Habitaciones y puertas',
    stage_tool_gas='Gas',
    stage_tool_spawn='Casillas de salida',
    stage_rotate='Girar',
    stage_remove='Quitar',
    stage_add='Añadir una habitación',
    stage_help_move='Arrastra una habitación para moverla. R la gira y Supr la quita. Haz clic en una puerta para cambiarla (puerta → muebles → pasadizo) o en una ventana para que entren lobos por ella.',
    stage_help_gas='Haz clic dentro de una habitación para poner o quitar un punto de gas.',
    stage_help_spawn='Haz clic en una casilla para poner o quitar una casilla de salida de los personajes.',
    stage_l_door='Puerta',
    stage_l_blocked='Tapado con muebles',
    stage_l_byway='Pasadizo',
    stage_l_window='Ventana',
    stage_l_wolf='Entrada de lobos',
    stage_l_entrance='Puerta principal',
    stage_l_gas='Gas',
    stage_l_spawn='Casilla de salida',
    stage_ok='Sin problemas.',
    stage_active='Ahora en el escenario de pruebas: {name}',
    stage_active_none='Ahora en el escenario de pruebas: copia del 01',
    stage_stats='{rooms} habitaciones · {doors} puertas · {wolves} entradas de lobos · {gas} de gas · {byways} pasadizos',
    stage_only_host='En una sala, todos se bajan los escenarios del anfitrión al unirse. Un escenario personalizado necesita que todos los jugadores tengan la recarga en caliente (BepInEx): mientras a alguien le falte, la sala no deja empezar la partida y lo indica junto a su nombre.',
    stage_p_no_rooms='Añade al menos una habitación.',
    stage_p_out_of_bounds='La habitación {room} se sale de la cuadrícula.',
    stage_p_overlap='Las habitaciones {room} y {other} se pisan.',
    stage_p_unreachable='No se puede llegar a la habitación {room} desde la 1: únela con una puerta.',
    stage_p_entrance_blocked='La puerta principal de la habitación {room} queda tapada por otra habitación.',
    stage_p_no_spawns='Elige al menos una casilla de salida.',
    stage_p_spawn_outside='Una casilla de salida está fuera de las habitaciones.',
    stage_p_spawn_blocked='Una casilla de salida cae encima de un mueble.',
    stage_p_gas_outside='Un punto de gas está fuera de las habitaciones.',
    stage_p_few_wolves='Entradas de lobos: {n}. Los escenarios del juego tienen {want}.',
    stage_p_few_gas='Puntos de gas: {n}. Los escenarios del juego tienen al menos {want}.',
    stage_p_few_byways='Pasadizos: {n}. Los escenarios del juego tienen al menos {want}.',
    stage_p_no_entrance='No hay recibidor (habitación de entrada).',
    stage_saved_live='Guardado. Ya sale en la lista de escenarios del juego, con su nombre.',
    stage_saved_errors='Guardado, pero no saldrá en el juego hasta que arregles los problemas marcados en rojo.',
    stage_room_need_bep='Esta sala tiene escenarios personalizados. Sin la recarga en caliente (BepInEx) no puedes jugarlos: el anfitrión no podrá empezar con uno de ellos mientras estés en la sala.',
    stage_room_synced='Escenarios de la sala listos en tu juego: {n}.',
    stage_room_failed='No he podido preparar los escenarios personalizados ({err}). Puedes jugar los normales.',
    stage_import_bad='Ese archivo no es un escenario de CRIMESIGHT Revival, o es de otra versión del juego.',
    stage_imported='Escenario importado. Ya está en tu lista.',
    stage_exported='Escenario guardado en {path}. Pásale ese archivo a quien quieras.',
    stage_too_many='En la lista del juego caben {n} escenarios tuyos. Desactiva antes alguno.',
    stage_saved_off='Guardado, pero desactivado: ya tienes {n} escenarios activos. Desactiva alguno para usar este.',
    stage_import='Importar',
    stage_export='Exportar',
    stage_none='Aún no has guardado ningún escenario.',
)
S["fr"].update(
    stage_btn='Créateur de scénarios',
    stage_title='Créateur de scénarios',
    stage_desc="Réorganisez les pièces d'un des scénarios du jeu. Chaque scénario enregistré apparaît dans la liste des scénarios du jeu comme un nouveau ; ceux du jeu ne sont jamais modifiés.",
    stage_reading='Lecture des scénarios de votre jeu… {pct}%',
    stage_base='Scénario de base',
    stage_name='Nom',
    stage_name_ph='Mon scénario',
    stage_mine='Mes scénarios',
    stage_original="Revenir à l'original",
    stage_save='Enregistrer',
    stage_saved='Enregistré. Pour y jouer, activez le rechargement à chaud (BepInEx) dans Mods.',
    stage_delete='Supprimer',
    stage_test='Test rapide',
    stage_test_ok="Prêt. En jeu, créez un salon et choisissez « Scénario de test (CSR) ». Inutile de redémarrer le jeu ou d'enregistrer.",
    stage_test_stop='Arrêter le test',
    stage_test_off='Le scénario de test est de nouveau une copie exacte du scénario 01.',
    stage_need_bep='Pour tester un scénario, il faut le rechargement à chaud (BepInEx). Activez-le dans Mods.',
    stage_need_name="Donnez d'abord un nom à votre scénario.",
    stage_fix_first="Corrigez d'abord les problèmes signalés en rouge.",
    stage_tool_move='Pièces et portes',
    stage_tool_gas='Gaz',
    stage_tool_spawn='Cases de départ',
    stage_rotate='Tourner',
    stage_remove='Retirer',
    stage_add='Ajouter une pièce',
    stage_help_move='Faites glisser une pièce pour la déplacer. R la tourne, Suppr la retire. Cliquez sur une porte pour la changer (porte → meubles → passage secret) ou sur une fenêtre pour que les loups entrent par là.',
    stage_help_gas='Cliquez dans une pièce pour ajouter ou retirer un point de gaz.',
    stage_help_spawn='Cliquez sur une case pour ajouter ou retirer une case de départ des personnages.',
    stage_l_door='Porte',
    stage_l_blocked='Bloquée par des meubles',
    stage_l_byway='Passage secret',
    stage_l_window='Fenêtre',
    stage_l_wolf='Entrée des loups',
    stage_l_entrance="Porte d'entrée",
    stage_l_gas='Gaz',
    stage_l_spawn='Case de départ',
    stage_ok='Aucun problème.',
    stage_active='Dans le scénario de test : {name}',
    stage_active_none='Dans le scénario de test : copie du scénario 01',
    stage_stats='{rooms} pièces · {doors} portes · {wolves} entrées de loups · {gas} gaz · {byways} passages',
    stage_only_host="Dans un salon, chacun télécharge les scénarios de l'hôte en rejoignant. Un scénario personnalisé exige que tous les joueurs aient le rechargement à chaud (BepInEx) : tant qu'il manque à quelqu'un, le salon empêche de lancer la partie et l'indique à côté de son nom.",
    stage_p_no_rooms='Ajoutez au moins une pièce.',
    stage_p_out_of_bounds='La pièce {room} dépasse de la grille.',
    stage_p_overlap='Les pièces {room} et {other} se chevauchent.',
    stage_p_unreachable='La pièce {room} est inaccessible depuis la pièce 1 : reliez-la par une porte.',
    stage_p_entrance_blocked="La porte d'entrée de la pièce {room} est couverte par une autre pièce.",
    stage_p_no_spawns='Choisissez au moins une case de départ.',
    stage_p_spawn_outside='Une case de départ est hors des pièces.',
    stage_p_spawn_blocked='Une case de départ est sur un meuble.',
    stage_p_gas_outside='Un point de gaz est hors des pièces.',
    stage_p_few_wolves='Entrées de loups : {n}. Les scénarios du jeu en ont {want}.',
    stage_p_few_gas='Points de gaz : {n}. Les scénarios du jeu en ont au moins {want}.',
    stage_p_few_byways='Passages secrets : {n}. Les scénarios du jeu en ont au moins {want}.',
    stage_p_no_entrance="Il n'y a pas de hall d'entrée.",
    stage_saved_live='Enregistré. Il est maintenant dans la liste des scénarios du jeu, avec son nom.',
    stage_saved_errors="Enregistré, mais il n'apparaîtra pas en jeu tant que les problèmes signalés en rouge ne sont pas corrigés.",
    stage_room_need_bep="Ce salon a des scénarios personnalisés. Sans le rechargement à chaud (BepInEx), vous ne pouvez pas y jouer : l'hôte ne pourra pas lancer l'un d'eux tant que vous êtes dans le salon.",
    stage_room_synced='Scénarios du salon prêts dans votre jeu : {n}.',
    stage_room_failed='Impossible de préparer les scénarios personnalisés ({err}). Vous pouvez jouer aux scénarios normaux.',
    stage_import_bad="Ce fichier n'est pas un scénario CRIMESIGHT Revival, ou il est pour une autre version du jeu.",
    stage_imported='Scénario importé. Il est déjà dans votre liste.',
    stage_exported='Scénario enregistré dans {path}. Envoyez ce fichier à qui vous voulez.',
    stage_too_many="La liste du jeu accepte {n} de vos scénarios. Désactivez-en un d'abord.",
    stage_saved_off='Enregistré, mais désactivé : vous avez déjà {n} scénarios activés. Désactivez-en un pour utiliser celui-ci.',
    stage_import='Importer',
    stage_export='Exporter',
    stage_none="Vous n'avez encore enregistré aucun scénario.",
)
S["it"].update(
    stage_btn='Creatore di scenari',
    stage_title='Creatore di scenari',
    stage_desc="Riorganizza le stanze di uno degli scenari del gioco. Ogni scenario che salvi compare nell'elenco degli scenari del gioco come uno nuovo; quelli del gioco non vengono mai modificati.",
    stage_reading='Lettura degli scenari dal tuo gioco… {pct}%',
    stage_base='Scenario di base',
    stage_name='Nome',
    stage_name_ph='Il mio scenario',
    stage_mine='I miei scenari',
    stage_original="Torna all'originale",
    stage_save='Salva',
    stage_saved='Salvato. Per giocarci, attiva la ricarica a caldo (BepInEx) in Mod.',
    stage_delete='Elimina',
    stage_test='Prova rapida',
    stage_test_ok='Pronto. Nel gioco, crea una stanza e scegli «Scenario di prova (CSR)». Non serve riavviare il gioco né salvare.',
    stage_test_stop='Interrompi la prova',
    stage_test_off='Lo scenario di prova è di nuovo una copia esatta dello scenario 01.',
    stage_need_bep='Per provare uno scenario serve la ricarica a caldo (BepInEx). Attivala in Mod.',
    stage_need_name='Dai prima un nome al tuo scenario.',
    stage_fix_first='Correggi prima i problemi segnati in rosso.',
    stage_tool_move='Stanze e porte',
    stage_tool_gas='Gas',
    stage_tool_spawn='Caselle iniziali',
    stage_rotate='Ruota',
    stage_remove='Rimuovi',
    stage_add='Aggiungi una stanza',
    stage_help_move='Trascina una stanza per spostarla. R la ruota, Canc la rimuove. Clicca su una porta per cambiarla (porta → mobili → passaggio segreto) o su una finestra per far entrare i lupi da lì.',
    stage_help_gas='Clicca dentro una stanza per aggiungere o togliere un punto del gas.',
    stage_help_spawn='Clicca su una casella per aggiungere o togliere una casella iniziale dei personaggi.',
    stage_l_door='Porta',
    stage_l_blocked='Bloccata dai mobili',
    stage_l_byway='Passaggio segreto',
    stage_l_window='Finestra',
    stage_l_wolf='Ingresso dei lupi',
    stage_l_entrance="Porta d'ingresso",
    stage_l_gas='Gas',
    stage_l_spawn='Casella iniziale',
    stage_ok='Nessun problema.',
    stage_active='Nello scenario di prova ora: {name}',
    stage_active_none='Nello scenario di prova ora: copia dello scenario 01',
    stage_stats='{rooms} stanze · {doors} porte · {wolves} ingressi dei lupi · {gas} gas · {byways} passaggi',
    stage_only_host="In una stanza, tutti scaricano gli scenari dell'host quando entrano. Uno scenario personalizzato richiede che tutti i giocatori abbiano la ricarica a caldo (BepInEx): finché a qualcuno manca, la stanza non lascia iniziare la partita e lo indica accanto al suo nome.",
    stage_p_no_rooms='Aggiungi almeno una stanza.',
    stage_p_out_of_bounds='La stanza {room} esce in parte dalla griglia.',
    stage_p_overlap='Le stanze {room} e {other} si sovrappongono.',
    stage_p_unreachable='La stanza {room} non è raggiungibile dalla stanza 1: collegala con una porta.',
    stage_p_entrance_blocked="La porta d'ingresso della stanza {room} è coperta da un'altra stanza.",
    stage_p_no_spawns='Scegli almeno una casella iniziale.',
    stage_p_spawn_outside='Una casella iniziale è fuori dalle stanze.',
    stage_p_spawn_blocked='Una casella iniziale è sopra un mobile.',
    stage_p_gas_outside='Un punto del gas è fuori dalle stanze.',
    stage_p_few_wolves='Ingressi dei lupi: {n}. Gli scenari del gioco ne hanno {want}.',
    stage_p_few_gas='Punti del gas: {n}. Gli scenari del gioco ne hanno almeno {want}.',
    stage_p_few_byways='Passaggi segreti: {n}. Gli scenari del gioco ne hanno almeno {want}.',
    stage_p_no_entrance="Manca l'atrio d'ingresso.",
    stage_saved_live="Salvato. Ora è nell'elenco degli scenari del gioco, con il suo nome.",
    stage_saved_errors='Salvato, ma non comparirà nel gioco finché non correggi i problemi segnati in rosso.',
    stage_room_need_bep="Questa stanza ha scenari personalizzati. Senza la ricarica a caldo (BepInEx) non puoi giocarci: l'host non potrà avviarne uno finché sei nella stanza.",
    stage_room_synced='Scenari della stanza pronti nel tuo gioco: {n}.',
    stage_room_failed='Impossibile preparare gli scenari personalizzati ({err}). Puoi giocare a quelli normali.',
    stage_import_bad="Quel file non è uno scenario di CRIMESIGHT Revival, oppure è per un'altra versione del gioco.",
    stage_imported='Scenario importato. È già nel tuo elenco.',
    stage_exported='Scenario salvato in {path}. Manda quel file a chi vuoi.',
    stage_too_many="Nell'elenco del gioco entrano {n} tuoi scenari. Disattivane prima uno.",
    stage_saved_off='Salvato, ma disattivato: hai già {n} scenari attivi. Disattivane uno per usare questo.',
    stage_import='Importa',
    stage_export='Esporta',
    stage_none='Non hai ancora salvato nessuno scenario.',
)
S["de"].update(
    stage_btn='Szenario-Editor',
    stage_title='Szenario-Editor',
    stage_desc='Ordne die Räume eines Szenarios des Spiels neu an. Jedes gespeicherte Szenario erscheint in der Szenarioliste des Spiels als neues; die Szenarien des Spiels werden nie verändert.',
    stage_reading='Szenarien aus deinem Spiel werden gelesen… {pct}%',
    stage_base='Basisszenario',
    stage_name='Name',
    stage_name_ph='Mein Szenario',
    stage_mine='Meine Szenarien',
    stage_original='Zurück zum Original',
    stage_save='Speichern',
    stage_saved='Gespeichert. Zum Spielen aktiviere Hot Reload (BepInEx) unter Mods.',
    stage_delete='Löschen',
    stage_test='Schnelltest',
    stage_test_ok='Fertig. Erstelle im Spiel einen Raum und wähle „Testszenario (CSR)“. Kein Neustart des Spiels und kein Speichern nötig.',
    stage_test_stop='Test beenden',
    stage_test_off='Das Testszenario ist wieder eine exakte Kopie von Szenario 01.',
    stage_need_bep='Zum Testen eines Szenarios brauchst du Hot Reload (BepInEx). Aktiviere es unter Mods.',
    stage_need_name='Gib deinem Szenario zuerst einen Namen.',
    stage_fix_first='Behebe zuerst die rot markierten Probleme.',
    stage_tool_move='Räume und Türen',
    stage_tool_gas='Gas',
    stage_tool_spawn='Startfelder',
    stage_rotate='Drehen',
    stage_remove='Entfernen',
    stage_add='Raum hinzufügen',
    stage_help_move='Ziehe einen Raum, um ihn zu verschieben. R dreht ihn, Entf entfernt ihn. Klicke auf eine Tür, um sie zu ändern (Tür → Möbel → Geheimgang), oder auf ein Fenster, damit Wölfe dort hereinkommen.',
    stage_help_gas='Klicke in einen Raum, um einen Gaspunkt hinzuzufügen oder zu entfernen.',
    stage_help_spawn='Klicke auf ein Feld, um ein Startfeld der Figuren hinzuzufügen oder zu entfernen.',
    stage_l_door='Tür',
    stage_l_blocked='Von Möbeln versperrt',
    stage_l_byway='Geheimgang',
    stage_l_window='Fenster',
    stage_l_wolf='Wolfseingang',
    stage_l_entrance='Haustür',
    stage_l_gas='Gas',
    stage_l_spawn='Startfeld',
    stage_ok='Keine Probleme.',
    stage_active='Im Testszenario jetzt: {name}',
    stage_active_none='Im Testszenario jetzt: Kopie von Szenario 01',
    stage_stats='{rooms} Räume · {doors} Türen · {wolves} Wolfseingänge · {gas} Gas · {byways} Geheimgänge',
    stage_only_host='In einem Raum laden alle beim Beitreten die Szenarien des Hosts herunter. Für ein eigenes Szenario brauchen alle Spieler Hot Reload (BepInEx): Solange es jemandem fehlt, lässt der Raum das Match nicht starten und zeigt es neben dem Namen an.',
    stage_p_no_rooms='Füge mindestens einen Raum hinzu.',
    stage_p_out_of_bounds='Raum {room} ragt über das Raster hinaus.',
    stage_p_overlap='Die Räume {room} und {other} überlappen sich.',
    stage_p_unreachable='Raum {room} ist von Raum 1 aus nicht erreichbar: Verbinde ihn mit einer Tür.',
    stage_p_entrance_blocked='Die Haustür von Raum {room} wird von einem anderen Raum verdeckt.',
    stage_p_no_spawns='Wähle mindestens ein Startfeld.',
    stage_p_spawn_outside='Ein Startfeld liegt außerhalb der Räume.',
    stage_p_spawn_blocked='Ein Startfeld liegt auf einem Möbelstück.',
    stage_p_gas_outside='Ein Gaspunkt liegt außerhalb der Räume.',
    stage_p_few_wolves='Wolfseingänge: {n}. Die Szenarien des Spiels haben {want}.',
    stage_p_few_gas='Gaspunkte: {n}. Die Szenarien des Spiels haben mindestens {want}.',
    stage_p_few_byways='Geheimgänge: {n}. Die Szenarien des Spiels haben mindestens {want}.',
    stage_p_no_entrance='Es gibt keine Eingangshalle.',
    stage_saved_live='Gespeichert. Es steht jetzt mit seinem Namen in der Szenarioliste des Spiels.',
    stage_saved_errors='Gespeichert, erscheint aber erst im Spiel, wenn die rot markierten Probleme behoben sind.',
    stage_room_need_bep='Dieser Raum hat eigene Szenarien. Ohne Hot Reload (BepInEx) kannst du sie nicht spielen: Der Host kann keines davon starten, solange du im Raum bist.',
    stage_room_synced='Szenarien des Raums in deinem Spiel bereit: {n}.',
    stage_room_failed='Die eigenen Szenarien konnten nicht vorbereitet werden ({err}). Die normalen kannst du spielen.',
    stage_import_bad='Diese Datei ist kein CRIMESIGHT-Revival-Szenario oder gehört zu einer anderen Spielversion.',
    stage_imported='Szenario importiert. Es steht schon in deiner Liste.',
    stage_exported='Szenario gespeichert unter {path}. Schick die Datei, wem du willst.',
    stage_too_many='In die Liste des Spiels passen {n} deiner Szenarien. Schalte zuerst eines aus.',
    stage_saved_off='Gespeichert, aber ausgeschaltet: Du hast schon {n} Szenarien an. Schalte eines aus, um dieses zu nutzen.',
    stage_import='Importieren',
    stage_export='Exportieren',
    stage_none='Du hast noch kein Szenario gespeichert.',
)
S["pt"].update(
    stage_btn='Criador de cenários',
    stage_title='Criador de cenários',
    stage_desc='Reorganize as salas de um dos cenários do jogo. Cada cenário que você salvar aparece na lista de cenários do jogo como um novo; os do jogo nunca são alterados.',
    stage_reading='Lendo os cenários do seu jogo… {pct}%',
    stage_base='Cenário base',
    stage_name='Nome',
    stage_name_ph='Meu cenário',
    stage_mine='Meus cenários',
    stage_original='Voltar ao original',
    stage_save='Salvar',
    stage_saved='Salvo. Para jogá-lo, ative a recarga instantânea (BepInEx) em Mods.',
    stage_delete='Excluir',
    stage_test='Teste rápido',
    stage_test_ok='Pronto. No jogo, crie uma sala e escolha “Cenário de testes (CSR)”. Não precisa reiniciar o jogo nem salvar.',
    stage_test_stop='Parar o teste',
    stage_test_off='O cenário de testes voltou a ser uma cópia exata do cenário 01.',
    stage_need_bep='Para testar um cenário é preciso a recarga instantânea (BepInEx). Ative-a em Mods.',
    stage_need_name='Dê primeiro um nome ao seu cenário.',
    stage_fix_first='Corrija primeiro os problemas marcados em vermelho.',
    stage_tool_move='Salas e portas',
    stage_tool_gas='Gás',
    stage_tool_spawn='Casas iniciais',
    stage_rotate='Girar',
    stage_remove='Remover',
    stage_add='Adicionar uma sala',
    stage_help_move='Arraste uma sala para movê-la. R gira, Del remove. Clique em uma porta para mudá-la (porta → móveis → passagem secreta) ou em uma janela para os lobos entrarem por ela.',
    stage_help_gas='Clique dentro de uma sala para adicionar ou remover um ponto de gás.',
    stage_help_spawn='Clique em uma casa para adicionar ou remover uma casa inicial dos personagens.',
    stage_l_door='Porta',
    stage_l_blocked='Bloqueada por móveis',
    stage_l_byway='Passagem secreta',
    stage_l_window='Janela',
    stage_l_wolf='Entrada dos lobos',
    stage_l_entrance='Porta da frente',
    stage_l_gas='Gás',
    stage_l_spawn='Casa inicial',
    stage_ok='Nenhum problema.',
    stage_active='No cenário de testes agora: {name}',
    stage_active_none='No cenário de testes agora: cópia do cenário 01',
    stage_stats='{rooms} salas · {doors} portas · {wolves} entradas de lobos · {gas} gás · {byways} passagens',
    stage_only_host='Em uma sala, todos baixam os cenários do anfitrião ao entrar. Um cenário personalizado exige que todos os jogadores tenham a recarga instantânea (BepInEx): enquanto faltar para alguém, a sala não deixa começar a partida e indica isso ao lado do nome.',
    stage_p_no_rooms='Adicione pelo menos uma sala.',
    stage_p_out_of_bounds='A sala {room} está parcialmente fora da grade.',
    stage_p_overlap='As salas {room} e {other} se sobrepõem.',
    stage_p_unreachable='Não dá para chegar à sala {room} a partir da sala 1: conecte-a com uma porta.',
    stage_p_entrance_blocked='A porta da frente da sala {room} está coberta por outra sala.',
    stage_p_no_spawns='Escolha pelo menos uma casa inicial.',
    stage_p_spawn_outside='Uma casa inicial está fora das salas.',
    stage_p_spawn_blocked='Uma casa inicial está em cima de um móvel.',
    stage_p_gas_outside='Um ponto de gás está fora das salas.',
    stage_p_few_wolves='Entradas de lobos: {n}. Os cenários do jogo têm {want}.',
    stage_p_few_gas='Pontos de gás: {n}. Os cenários do jogo têm pelo menos {want}.',
    stage_p_few_byways='Passagens secretas: {n}. Os cenários do jogo têm pelo menos {want}.',
    stage_p_no_entrance='Não há hall de entrada.',
    stage_saved_live='Salvo. Agora está na lista de cenários do jogo, com o nome dele.',
    stage_saved_errors='Salvo, mas só vai aparecer no jogo quando você corrigir os problemas marcados em vermelho.',
    stage_room_need_bep='Esta sala tem cenários personalizados. Sem a recarga instantânea (BepInEx) você não pode jogá-los: o anfitrião não vai conseguir começar com um deles enquanto você estiver na sala.',
    stage_room_synced='Cenários da sala prontos no seu jogo: {n}.',
    stage_room_failed='Não foi possível preparar os cenários personalizados ({err}). Você pode jogar os normais.',
    stage_import_bad='Esse arquivo não é um cenário do CRIMESIGHT Revival, ou é de outra versão do jogo.',
    stage_imported='Cenário importado. Já está na sua lista.',
    stage_exported='Cenário salvo em {path}. Mande esse arquivo para quem quiser.',
    stage_too_many='Na lista do jogo cabem {n} cenários seus. Desative algum antes.',
    stage_saved_off='Salvo, mas desativado: você já tem {n} cenários ativos. Desative algum para usar este.',
    stage_import='Importar',
    stage_export='Exportar',
    stage_none='Você ainda não salvou nenhum cenário.',
)
S["ru"].update(
    stage_btn='Редактор сценариев',
    stage_title='Редактор сценариев',
    stage_desc='Переставляйте комнаты одного из сценариев игры. Каждый сохранённый сценарий появляется в списке сценариев игры как новый; сценарии самой игры никогда не меняются.',
    stage_reading='Чтение сценариев из вашей игры… {pct}%',
    stage_base='Базовый сценарий',
    stage_name='Название',
    stage_name_ph='Мой сценарий',
    stage_mine='Мои сценарии',
    stage_original='Вернуть оригинал',
    stage_save='Сохранить',
    stage_saved='Сохранено. Чтобы сыграть, включите горячую перезагрузку (BepInEx) в разделе «Моды».',
    stage_delete='Удалить',
    stage_test='Быстрый тест',
    stage_test_ok='Готово. В игре создайте комнату и выберите «Тестовый сценарий (CSR)». Перезапускать игру и сохранять не нужно.',
    stage_test_stop='Закончить тест',
    stage_test_off='Тестовый сценарий снова точная копия сценария 01.',
    stage_need_bep='Для теста сценария нужна горячая перезагрузка (BepInEx). Включите её в разделе «Моды».',
    stage_need_name='Сначала дайте сценарию название.',
    stage_fix_first='Сначала исправьте проблемы, отмеченные красным.',
    stage_tool_move='Комнаты и двери',
    stage_tool_gas='Газ',
    stage_tool_spawn='Стартовые клетки',
    stage_rotate='Повернуть',
    stage_remove='Убрать',
    stage_add='Добавить комнату',
    stage_help_move='Перетащите комнату, чтобы переместить её. R — повернуть, Del — убрать. Щёлкните по двери, чтобы изменить её (дверь → мебель → тайный ход), или по окну, чтобы через него входили волки.',
    stage_help_gas='Щёлкните внутри комнаты, чтобы добавить или убрать точку газа.',
    stage_help_spawn='Щёлкните по клетке, чтобы добавить или убрать стартовую клетку персонажей.',
    stage_l_door='Дверь',
    stage_l_blocked='Заставлена мебелью',
    stage_l_byway='Тайный ход',
    stage_l_window='Окно',
    stage_l_wolf='Вход для волков',
    stage_l_entrance='Входная дверь',
    stage_l_gas='Газ',
    stage_l_spawn='Стартовая клетка',
    stage_ok='Проблем нет.',
    stage_active='Сейчас в тестовом сценарии: {name}',
    stage_active_none='Сейчас в тестовом сценарии: копия сценария 01',
    stage_stats='Комнат: {rooms} · дверей: {doors} · входов для волков: {wolves} · газ: {gas} · ходов: {byways}',
    stage_only_host='В комнате все скачивают сценарии хоста при входе. Для своего сценария горячая перезагрузка (BepInEx) нужна всем игрокам: пока у кого-то её нет, комната не даёт начать матч и показывает это рядом с именем игрока.',
    stage_p_no_rooms='Добавьте хотя бы одну комнату.',
    stage_p_out_of_bounds='Комната {room} частично выходит за сетку.',
    stage_p_overlap='Комнаты {room} и {other} пересекаются.',
    stage_p_unreachable='В комнату {room} нельзя попасть из комнаты 1: соедините её дверью.',
    stage_p_entrance_blocked='Входная дверь комнаты {room} закрыта другой комнатой.',
    stage_p_no_spawns='Выберите хотя бы одну стартовую клетку.',
    stage_p_spawn_outside='Стартовая клетка находится вне комнат.',
    stage_p_spawn_blocked='Стартовая клетка стоит на мебели.',
    stage_p_gas_outside='Точка газа находится вне комнат.',
    stage_p_few_wolves='Входов для волков: {n}. В сценариях игры их {want}.',
    stage_p_few_gas='Точек газа: {n}. В сценариях игры их не меньше {want}.',
    stage_p_few_byways='Тайных ходов: {n}. В сценариях игры их не меньше {want}.',
    stage_p_no_entrance='Нет прихожей.',
    stage_saved_live='Сохранено. Сценарий уже в списке сценариев игры под своим названием.',
    stage_saved_errors='Сохранено, но в игре он не появится, пока не исправлены проблемы, отмеченные красным.',
    stage_room_need_bep='В этой комнате есть свои сценарии. Без горячей перезагрузки (BepInEx) вы не сможете в них играть: пока вы в комнате, хост не сможет запустить ни один из них.',
    stage_room_synced='Сценарии комнаты готовы в вашей игре: {n}.',
    stage_room_failed='Не удалось подготовить свои сценарии ({err}). Обычные сценарии доступны.',
    stage_import_bad='Этот файл не является сценарием CRIMESIGHT Revival или предназначен для другой версии игры.',
    stage_imported='Сценарий импортирован. Он уже в вашем списке.',
    stage_exported='Сценарий сохранён в {path}. Отправьте этот файл кому хотите.',
    stage_too_many='В список игры помещается {n} ваших сценариев. Сначала отключите один.',
    stage_saved_off='Сохранено, но отключено: у вас уже включено сценариев: {n}. Отключите один, чтобы использовать этот.',
    stage_import='Импорт',
    stage_export='Экспорт',
    stage_none='Вы ещё не сохранили ни одного сценария.',
)
S["ja"].update(
    stage_btn='ステージクリエイター',
    stage_title='ステージクリエイター',
    stage_desc='ゲームのステージの部屋を並べ替えられます。保存したステージは、ゲームのステージ一覧に新しいステージとして表示されます。ゲーム本来のステージは一切変更されません。',
    stage_reading='ゲームからステージを読み込み中… {pct}%',
    stage_base='ベースのステージ',
    stage_name='名前',
    stage_name_ph='マイステージ',
    stage_mine='マイステージ一覧',
    stage_original='元に戻す',
    stage_save='保存',
    stage_saved='保存しました。遊ぶには「MOD」でホットリロード（BepInEx）をオンにしてください。',
    stage_delete='削除',
    stage_test='クイックテスト',
    stage_test_ok='準備完了。ゲームでルームを作成し、「テスト用ステージ (CSR)」を選んでください。ゲームの再起動や保存は不要です。',
    stage_test_stop='テストを終了',
    stage_test_off='テスト用ステージをステージ01の完全なコピーに戻しました。',
    stage_need_bep='ステージのテストにはホットリロード（BepInEx）が必要です。「MOD」でオンにしてください。',
    stage_need_name='先にステージに名前を付けてください。',
    stage_fix_first='先に赤で示された問題を修正してください。',
    stage_tool_move='部屋とドア',
    stage_tool_gas='ガス',
    stage_tool_spawn='スタートマス',
    stage_rotate='回転',
    stage_remove='削除',
    stage_add='部屋を追加',
    stage_help_move='部屋をドラッグして移動します。Rで回転、Delで削除。ドアをクリックすると切り替わります（ドア → 家具 → 隠し通路）。窓をクリックすると、そこからオオカミが入ってきます。',
    stage_help_gas='部屋の中をクリックして、ガスの地点を追加・削除します。',
    stage_help_spawn='マスをクリックして、キャラクターのスタートマスを追加・削除します。',
    stage_l_door='ドア',
    stage_l_blocked='家具でふさがれている',
    stage_l_byway='隠し通路',
    stage_l_window='窓',
    stage_l_wolf='オオカミの侵入口',
    stage_l_entrance='玄関',
    stage_l_gas='ガス',
    stage_l_spawn='スタートマス',
    stage_ok='問題ありません。',
    stage_active='現在のテスト用ステージ：{name}',
    stage_active_none='現在のテスト用ステージ：ステージ01のコピー',
    stage_stats='部屋 {rooms} · ドア {doors} · オオカミの侵入口 {wolves} · ガス {gas} · 通路 {byways}',
    stage_only_host='ルームでは、参加時に全員がホストのステージをダウンロードします。カスタムステージで遊ぶには全員にホットリロード（BepInEx）が必要です。持っていない人がいる間は試合を開始できず、その人の名前の横に表示されます。',
    stage_p_no_rooms='部屋を1つ以上追加してください。',
    stage_p_out_of_bounds='部屋{room}がグリッドからはみ出しています。',
    stage_p_overlap='部屋{room}と部屋{other}が重なっています。',
    stage_p_unreachable='部屋{room}に部屋1から行けません。ドアでつないでください。',
    stage_p_entrance_blocked='部屋{room}の玄関が別の部屋でふさがれています。',
    stage_p_no_spawns='スタートマスを1つ以上選んでください。',
    stage_p_spawn_outside='スタートマスが部屋の外にあります。',
    stage_p_spawn_blocked='スタートマスが家具の上にあります。',
    stage_p_gas_outside='ガスの地点が部屋の外にあります。',
    stage_p_few_wolves='オオカミの侵入口：{n}。ゲームのステージは{want}です。',
    stage_p_few_gas='ガスの地点：{n}。ゲームのステージは{want}以上です。',
    stage_p_few_byways='隠し通路：{n}。ゲームのステージは{want}以上です。',
    stage_p_no_entrance='玄関ホールがありません。',
    stage_saved_live='保存しました。ゲームのステージ一覧にその名前で追加されました。',
    stage_saved_errors='保存しましたが、赤で示された問題を修正するまでゲームには表示されません。',
    stage_room_need_bep='このルームにはカスタムステージがあります。ホットリロード（BepInEx）がないと遊べません。あなたがルームにいる間、ホストはカスタムステージで開始できません。',
    stage_room_synced='ルームのステージをゲームに用意しました：{n}',
    stage_room_failed='カスタムステージを準備できませんでした（{err}）。通常のステージは遊べます。',
    stage_import_bad='このファイルは CRIMESIGHT Revival のステージではないか、別のバージョンのゲーム用です。',
    stage_imported='ステージを読み込みました。一覧に追加されています。',
    stage_exported='ステージを {path} に保存しました。このファイルを好きな人に送ってください。',
    stage_too_many='ゲームの一覧に入れられるマイステージは{n}個までです。先にどれかをオフにしてください。',
    stage_saved_off='保存しましたが、オフになっています。すでに{n}個のステージがオンです。使うにはどれかをオフにしてください。',
    stage_import='読み込む',
    stage_export='書き出す',
    stage_none='まだステージを保存していません。',
)
S["ko"].update(
    stage_btn='스테이지 제작기',
    stage_title='스테이지 제작기',
    stage_desc='게임 스테이지의 방을 다시 배치합니다. 저장한 스테이지는 게임의 스테이지 목록에 새 스테이지로 나타납니다. 게임의 원래 스테이지는 절대 바뀌지 않습니다.',
    stage_reading='게임에서 스테이지를 읽는 중… {pct}%',
    stage_base='기본 스테이지',
    stage_name='이름',
    stage_name_ph='내 스테이지',
    stage_mine='내 스테이지',
    stage_original='원래대로',
    stage_save='저장',
    stage_saved="저장했습니다. 플레이하려면 '모드'에서 실시간 반영(BepInEx)을 켜세요.",
    stage_delete='삭제',
    stage_test='빠른 테스트',
    stage_test_ok='준비 완료. 게임에서 방을 만들고 “테스트 스테이지 (CSR)”를 선택하세요. 게임을 다시 시작하거나 저장할 필요가 없습니다.',
    stage_test_stop='테스트 종료',
    stage_test_off='테스트 스테이지가 다시 스테이지 01의 정확한 복사본이 되었습니다.',
    stage_need_bep="스테이지를 테스트하려면 실시간 반영(BepInEx)이 필요합니다. '모드'에서 켜세요.",
    stage_need_name='먼저 스테이지에 이름을 지어 주세요.',
    stage_fix_first='먼저 빨간색으로 표시된 문제를 고치세요.',
    stage_tool_move='방과 문',
    stage_tool_gas='가스',
    stage_tool_spawn='시작 칸',
    stage_rotate='회전',
    stage_remove='제거',
    stage_add='방 추가',
    stage_help_move='방을 끌어서 옮깁니다. R로 회전, Del로 제거합니다. 문을 클릭하면 바뀝니다(문 → 가구 → 비밀 통로). 창문을 클릭하면 그곳으로 늑대가 들어옵니다.',
    stage_help_gas='방 안을 클릭해 가스 지점을 추가하거나 제거합니다.',
    stage_help_spawn='칸을 클릭해 캐릭터의 시작 칸을 추가하거나 제거합니다.',
    stage_l_door='문',
    stage_l_blocked='가구로 막힘',
    stage_l_byway='비밀 통로',
    stage_l_window='창문',
    stage_l_wolf='늑대 입구',
    stage_l_entrance='현관문',
    stage_l_gas='가스',
    stage_l_spawn='시작 칸',
    stage_ok='문제 없음.',
    stage_active='현재 테스트 스테이지: {name}',
    stage_active_none='현재 테스트 스테이지: 스테이지 01의 복사본',
    stage_stats='방 {rooms} · 문 {doors} · 늑대 입구 {wolves} · 가스 {gas} · 통로 {byways}',
    stage_only_host='방에 참가하면 모두가 호스트의 스테이지를 내려받습니다. 커스텀 스테이지는 모든 플레이어에게 실시간 반영(BepInEx)이 있어야 합니다. 없는 사람이 있는 동안에는 게임을 시작할 수 없고, 그 사람 이름 옆에 표시됩니다.',
    stage_p_no_rooms='방을 하나 이상 추가하세요.',
    stage_p_out_of_bounds='방 {room}이(가) 격자 밖으로 나갔습니다.',
    stage_p_overlap='방 {room}과(와) 방 {other}이(가) 겹칩니다.',
    stage_p_unreachable='방 1에서 방 {room}(으)로 갈 수 없습니다. 문으로 연결하세요.',
    stage_p_entrance_blocked='방 {room}의 현관문이 다른 방에 가려져 있습니다.',
    stage_p_no_spawns='시작 칸을 하나 이상 고르세요.',
    stage_p_spawn_outside='시작 칸이 방 밖에 있습니다.',
    stage_p_spawn_blocked='시작 칸이 가구 위에 있습니다.',
    stage_p_gas_outside='가스 지점이 방 밖에 있습니다.',
    stage_p_few_wolves='늑대 입구: {n}. 게임의 스테이지에는 {want}개가 있습니다.',
    stage_p_few_gas='가스 지점: {n}. 게임의 스테이지에는 최소 {want}개가 있습니다.',
    stage_p_few_byways='비밀 통로: {n}. 게임의 스테이지에는 최소 {want}개가 있습니다.',
    stage_p_no_entrance='현관 홀이 없습니다.',
    stage_saved_live='저장했습니다. 이제 게임의 스테이지 목록에 그 이름으로 나타납니다.',
    stage_saved_errors='저장했지만, 빨간색으로 표시된 문제를 고치기 전에는 게임에 나타나지 않습니다.',
    stage_room_need_bep='이 방에는 커스텀 스테이지가 있습니다. 실시간 반영(BepInEx)이 없으면 플레이할 수 없습니다. 당신이 방에 있는 동안 호스트는 커스텀 스테이지로 시작할 수 없습니다.',
    stage_room_synced='방의 스테이지가 게임에 준비되었습니다: {n}',
    stage_room_failed='커스텀 스테이지를 준비하지 못했습니다({err}). 일반 스테이지는 플레이할 수 있습니다.',
    stage_import_bad='이 파일은 CRIMESIGHT Revival 스테이지가 아니거나 다른 버전의 게임용입니다.',
    stage_imported='스테이지를 가져왔습니다. 이미 목록에 있습니다.',
    stage_exported='스테이지를 {path}에 저장했습니다. 원하는 사람에게 이 파일을 보내세요.',
    stage_too_many='게임 목록에는 내 스테이지가 {n}개까지 들어갑니다. 먼저 하나를 끄세요.',
    stage_saved_off='저장했지만 꺼져 있습니다. 이미 스테이지 {n}개가 켜져 있습니다. 이 스테이지를 쓰려면 하나를 끄세요.',
    stage_import='가져오기',
    stage_export='내보내기',
    stage_none='아직 저장한 스테이지가 없습니다.',
)
S["zh-CN"].update(
    stage_btn='场景编辑器',
    stage_title='场景编辑器',
    stage_desc='重新摆放游戏中某个场景的房间。你保存的每个场景都会作为新场景出现在游戏的场景列表中；游戏自带的场景绝不会被改动。',
    stage_reading='正在读取你游戏中的场景… {pct}%',
    stage_base='基础场景',
    stage_name='名称',
    stage_name_ph='我的场景',
    stage_mine='我的场景',
    stage_original='恢复原样',
    stage_save='保存',
    stage_saved='已保存。要游玩它，请在“模组”中开启热重载（BepInEx）。',
    stage_delete='删除',
    stage_test='快速测试',
    stage_test_ok='准备就绪。在游戏中创建房间并选择“测试场景 (CSR)”。无需重启游戏，也无需保存。',
    stage_test_stop='停止测试',
    stage_test_off='测试场景已恢复为场景 01 的完整副本。',
    stage_need_bep='测试场景需要热重载（BepInEx）。请在“模组”中开启。',
    stage_need_name='请先给你的场景起个名字。',
    stage_fix_first='请先修复标红的问题。',
    stage_tool_move='房间和门',
    stage_tool_gas='煤气',
    stage_tool_spawn='起始格',
    stage_rotate='旋转',
    stage_remove='移除',
    stage_add='添加房间',
    stage_help_move='拖动房间来移动它。R 旋转，Del 移除。点击一扇门可切换它（门 → 家具 → 密道），点击一扇窗可让狼从那里进入。',
    stage_help_gas='在房间内点击以添加或移除煤气点。',
    stage_help_spawn='点击格子以添加或移除角色的起始格。',
    stage_l_door='门',
    stage_l_blocked='被家具挡住',
    stage_l_byway='密道',
    stage_l_window='窗户',
    stage_l_wolf='狼的入口',
    stage_l_entrance='正门',
    stage_l_gas='煤气',
    stage_l_spawn='起始格',
    stage_ok='没有问题。',
    stage_active='当前测试场景：{name}',
    stage_active_none='当前测试场景：场景 01 的副本',
    stage_stats='{rooms} 个房间 · {doors} 扇门 · {wolves} 个狼入口 · {gas} 个煤气点 · {byways} 条密道',
    stage_only_host='在房间里，所有人加入时都会下载主机的场景。自定义场景需要所有玩家都开启热重载（BepInEx）：只要有人没有，房间就不允许开始对局，并在其名字旁标出。',
    stage_p_no_rooms='请至少添加一个房间。',
    stage_p_out_of_bounds='房间 {room} 有一部分超出了网格。',
    stage_p_overlap='房间 {room} 和房间 {other} 重叠了。',
    stage_p_unreachable='从房间 1 无法到达房间 {room}：请用一扇门把它连起来。',
    stage_p_entrance_blocked='房间 {room} 的正门被另一个房间挡住了。',
    stage_p_no_spawns='请至少选择一个起始格。',
    stage_p_spawn_outside='有一个起始格在房间外。',
    stage_p_spawn_blocked='有一个起始格在家具上。',
    stage_p_gas_outside='有一个煤气点在房间外。',
    stage_p_few_wolves='狼的入口：{n}。游戏的场景有 {want} 个。',
    stage_p_few_gas='煤气点：{n}。游戏的场景至少有 {want} 个。',
    stage_p_few_byways='密道：{n}。游戏的场景至少有 {want} 条。',
    stage_p_no_entrance='没有门厅。',
    stage_saved_live='已保存。它现在以自己的名字出现在游戏的场景列表中。',
    stage_saved_errors='已保存，但在修复标红的问题之前，它不会出现在游戏中。',
    stage_room_need_bep='这个房间有自定义场景。没有热重载（BepInEx）就无法游玩：只要你在房间里，主机就无法用自定义场景开始。',
    stage_room_synced='房间的场景已在你的游戏中就绪：{n}',
    stage_room_failed='无法准备自定义场景（{err}）。你仍可以玩普通场景。',
    stage_import_bad='该文件不是 CRIMESIGHT Revival 场景，或者属于其他版本的游戏。',
    stage_imported='场景已导入，已在你的列表中。',
    stage_exported='场景已保存到 {path}。把这个文件发给任何你想发的人。',
    stage_too_many='游戏列表最多容纳你的 {n} 个场景。请先停用一个。',
    stage_saved_off='已保存，但处于停用状态：你已启用 {n} 个场景。停用其中一个才能使用这个。',
    stage_import='导入',
    stage_export='导出',
    stage_none='你还没有保存任何场景。',
)
S["zh-TW"].update(
    stage_btn='場景編輯器',
    stage_title='場景編輯器',
    stage_desc='重新擺放遊戲中某個場景的房間。你儲存的每個場景都會以新場景的形式出現在遊戲的場景清單中；遊戲內建的場景絕不會被更動。',
    stage_reading='正在讀取你遊戲中的場景… {pct}%',
    stage_base='基礎場景',
    stage_name='名稱',
    stage_name_ph='我的場景',
    stage_mine='我的場景',
    stage_original='恢復原樣',
    stage_save='儲存',
    stage_saved='已儲存。要遊玩它，請在「模組」中開啟熱重載（BepInEx）。',
    stage_delete='刪除',
    stage_test='快速測試',
    stage_test_ok='準備就緒。在遊戲中建立房間並選擇「測試場景 (CSR)」。不需重啟遊戲，也不需儲存。',
    stage_test_stop='停止測試',
    stage_test_off='測試場景已恢復為場景 01 的完整複本。',
    stage_need_bep='測試場景需要熱重載（BepInEx）。請在「模組」中開啟。',
    stage_need_name='請先替你的場景取個名字。',
    stage_fix_first='請先修正標紅的問題。',
    stage_tool_move='房間和門',
    stage_tool_gas='瓦斯',
    stage_tool_spawn='起始格',
    stage_rotate='旋轉',
    stage_remove='移除',
    stage_add='新增房間',
    stage_help_move='拖曳房間來移動它。R 旋轉，Del 移除。點擊一扇門可切換它（門 → 家具 → 密道），點擊一扇窗可讓狼從那裡進入。',
    stage_help_gas='在房間內點擊以新增或移除瓦斯點。',
    stage_help_spawn='點擊格子以新增或移除角色的起始格。',
    stage_l_door='門',
    stage_l_blocked='被家具擋住',
    stage_l_byway='密道',
    stage_l_window='窗戶',
    stage_l_wolf='狼的入口',
    stage_l_entrance='正門',
    stage_l_gas='瓦斯',
    stage_l_spawn='起始格',
    stage_ok='沒有問題。',
    stage_active='目前的測試場景：{name}',
    stage_active_none='目前的測試場景：場景 01 的複本',
    stage_stats='{rooms} 個房間 · {doors} 扇門 · {wolves} 個狼入口 · {gas} 個瓦斯點 · {byways} 條密道',
    stage_only_host='在房間裡，所有人加入時都會下載主機的場景。自訂場景需要所有玩家都開啟熱重載（BepInEx）：只要有人沒有，房間就不允許開始對局，並在其名字旁標示。',
    stage_p_no_rooms='請至少新增一個房間。',
    stage_p_out_of_bounds='房間 {room} 有一部分超出了格線。',
    stage_p_overlap='房間 {room} 和房間 {other} 重疊了。',
    stage_p_unreachable='從房間 1 無法到達房間 {room}：請用一扇門把它連起來。',
    stage_p_entrance_blocked='房間 {room} 的正門被另一個房間擋住了。',
    stage_p_no_spawns='請至少選擇一個起始格。',
    stage_p_spawn_outside='有一個起始格在房間外。',
    stage_p_spawn_blocked='有一個起始格在家具上。',
    stage_p_gas_outside='有一個瓦斯點在房間外。',
    stage_p_few_wolves='狼的入口：{n}。遊戲的場景有 {want} 個。',
    stage_p_few_gas='瓦斯點：{n}。遊戲的場景至少有 {want} 個。',
    stage_p_few_byways='密道：{n}。遊戲的場景至少有 {want} 條。',
    stage_p_no_entrance='沒有門廳。',
    stage_saved_live='已儲存。它現在以自己的名字出現在遊戲的場景清單中。',
    stage_saved_errors='已儲存，但在修正標紅的問題之前，它不會出現在遊戲中。',
    stage_room_need_bep='這個房間有自訂場景。沒有熱重載（BepInEx）就無法遊玩：只要你在房間裡，主機就無法用自訂場景開始。',
    stage_room_synced='房間的場景已在你的遊戲中就緒：{n}',
    stage_room_failed='無法準備自訂場景（{err}）。你仍可以玩一般場景。',
    stage_import_bad='該檔案不是 CRIMESIGHT Revival 場景，或者屬於其他版本的遊戲。',
    stage_imported='場景已匯入，已在你的清單中。',
    stage_exported='場景已儲存到 {path}。把這個檔案傳給任何你想傳的人。',
    stage_too_many='遊戲清單最多容納你的 {n} 個場景。請先停用一個。',
    stage_saved_off='已儲存，但處於停用狀態：你已啟用 {n} 個場景。停用其中一個才能使用這個。',
    stage_import='匯入',
    stage_export='匯出',
    stage_none='你還沒有儲存任何場景。',
)
# ---- launcher update: offered with its release notes
S["en"].update(update_title='New version available', update_ver='You have {cur}. The latest is {v}.', update_changes="What's new", update_no_notes='No notes for this version.', update_now='Update now', update_later='Not now', update_hint="To play with others, it's best if everyone has the same version.", update_pill='Update available: {v}')
S["es"].update(update_title='Nueva versión disponible', update_ver='Tienes la {cur}. La última es la {v}.', update_changes='Novedades', update_no_notes='Esta versión no trae notas.', update_now='Actualizar ahora', update_later='Ahora no', update_hint='Para jugar con otras personas, lo mejor es que todos tengáis la misma versión.', update_pill='Actualización disponible: {v}')
S["fr"].update(update_title='Nouvelle version disponible', update_ver='Vous avez la {cur}. La dernière est la {v}.', update_changes='Nouveautés', update_no_notes='Pas de notes pour cette version.', update_now='Mettre à jour', update_later='Pas maintenant', update_hint="Pour jouer avec d'autres personnes, mieux vaut que tout le monde ait la même version.", update_pill='Mise à jour disponible : {v}')
S["it"].update(update_title='Nuova versione disponibile', update_ver="Hai la {cur}. L'ultima è la {v}.", update_changes='Novità', update_no_notes='Nessuna nota per questa versione.', update_now='Aggiorna ora', update_later='Non ora', update_hint='Per giocare con altre persone è meglio che tutti abbiano la stessa versione.', update_pill='Aggiornamento disponibile: {v}')
S["de"].update(update_title='Neue Version verfügbar', update_ver='Du hast {cur}. Die neueste ist {v}.', update_changes='Neuerungen', update_no_notes='Keine Hinweise zu dieser Version.', update_now='Jetzt aktualisieren', update_later='Nicht jetzt', update_hint='Zum Spielen mit anderen sollten alle dieselbe Version haben.', update_pill='Update verfügbar: {v}')
S["pt"].update(update_title='Nova versão disponível', update_ver='Você tem a {cur}. A mais recente é a {v}.', update_changes='Novidades', update_no_notes='Sem notas para esta versão.', update_now='Atualizar agora', update_later='Agora não', update_hint='Para jogar com outras pessoas, o ideal é que todos tenham a mesma versão.', update_pill='Atualização disponível: {v}')
S["ru"].update(update_title='Доступна новая версия', update_ver='У вас {cur}. Последняя — {v}.', update_changes='Что нового', update_no_notes='Для этой версии нет заметок.', update_now='Обновить сейчас', update_later='Не сейчас', update_hint='Чтобы играть с другими, лучше, чтобы у всех была одна и та же версия.', update_pill='Доступно обновление: {v}')
S["ja"].update(update_title='新しいバージョンがあります', update_ver='現在のバージョンは {cur}、最新は {v} です。', update_changes='更新内容', update_no_notes='このバージョンのメモはありません。', update_now='今すぐ更新', update_later='あとで', update_hint='他の人と遊ぶには、全員が同じバージョンにするのがおすすめです。', update_pill='更新があります：{v}')
S["ko"].update(update_title='새 버전이 있습니다', update_ver='현재 버전은 {cur}, 최신 버전은 {v}입니다.', update_changes='변경 사항', update_no_notes='이 버전에는 메모가 없습니다.', update_now='지금 업데이트', update_later='나중에', update_hint='다른 사람과 플레이하려면 모두 같은 버전을 쓰는 것이 좋습니다.', update_pill='업데이트 가능: {v}')
S["zh-CN"].update(update_title='有新版本可用', update_ver='你当前是 {cur}，最新版本是 {v}。', update_changes='更新内容', update_no_notes='此版本没有说明。', update_now='立即更新', update_later='暂不更新', update_hint='要和其他人一起玩，最好所有人使用相同版本。', update_pill='有可用更新：{v}')
S["zh-TW"].update(update_title='有新版本可用', update_ver='你目前是 {cur}，最新版本是 {v}。', update_changes='更新內容', update_no_notes='此版本沒有說明。', update_now='立即更新', update_later='暫不更新', update_hint='要和其他人一起玩，最好所有人使用相同版本。', update_pill='有可用更新：{v}')


def set_lang(lang):
    global _lang
    _lang = lang if lang in S else "en"


def get_lang():
    return _lang


def t(key, **kw):
    text = S.get(_lang, {}).get(key) or S["en"].get(key) or key
    try:
        return text.format(**kw)
    except (KeyError, IndexError, ValueError):
        return text


def table():
    """All the texts of the current language (with English fallback) for the interface."""
    out = dict(S["en"])
    out.update(S.get(_lang, {}))
    return out


def from_game_code(code):
    return GAME_CODES.get(str(code or "").upper())


def from_steam(name):
    return STEAM_CODES.get(str(name or "").lower())


# --- server lines shown in the launcher's log -------------------------
_EVENTS = [
    (re.compile(r"empieza la partida"), lambda m: t("ev_start")),
    (re.compile(r": (.+?) \([a-z]+\) GANA, \+(\d+)"), lambda m: t("ev_win", name=m.group(1), pts=m.group(2))),
    (re.compile(r": (.+?) \([a-z]+\) PIERDE, \+(\d+)"), lambda m: t("ev_lose", name=m.group(1), pts=m.group(2))),
    (re.compile(r": (.+?) \([a-z]+\) EMPATA, \+(\d+)"), lambda m: t("ev_draw", name=m.group(1), pts=m.group(2))),
    (re.compile(r": (.+?) \([a-z]+\) ABANDONA"), lambda m: t("ev_quit", name=m.group(1))),
    (re.compile(r"la victima ha muerto"), lambda m: t("ev_kill")),
    (re.compile(r"turno final sin asesinato"), lambda m: t("ev_arrest")),
    (re.compile(r"aparece una amenaza"), lambda m: t("ev_threat")),
    (re.compile(r"aparece un escape de gas"), lambda m: t("ev_gas")),
    (re.compile(r"Perfil sincronizado"), lambda m: t("ev_synced")),
]


def server_event(msg):
    """Translates a server log line, or None if it doesn't matter to the player."""
    for rx, fn in _EVENTS:
        m = rx.search(msg)
        if m:
            return fn(m)
    return None


# ------------------------------------------------------------------ READMEs of the mods folders
# README.txt of mods\, mods\models\ and mods\cursor\, written in the launcher's language (core.mods_dir,
# models_dir and cursor_dir). The three share one layout: title, what's in the folder, then short sections.
# "[Modelos]", "CSR_borra_esta_malla" and "[Cursor] el juego usa el cursor" stay as they are: that is how they
# appear in the game's log and in Blender.
_READMES = {
    "en": ("""CRIMESIGHT Revival - mods
=========================

This is your mods folder. You manage everything in it from the launcher's Mods window.

  stamps\\      your stamp images
  avatars\\     your avatar images (to use as your profile picture)
  mod.json     optional: the name and author shown for your mods
  models\\      your 3D models and animations (see the README.txt inside)
  cursor\\      your custom cursor (see the README.txt inside)
  stages\\      the scenarios you save in the Scenario Creator

Stamps and avatars
 - PNG, JPG, WEBP... Any size works: they're adjusted automatically.
 - They're added as new ones: the game's own stamps and avatars are never changed.
 - In your room everyone sees them (in someone else's room you see theirs).
 - A stamp shows no message in the match unless you give it one with the "Messages" button
   (Mods > Stamps). A number at the start of the file name (01_) only sets the order.
 - Changes appear the next time you open the game from the launcher, or right away with
   Hot reload (BepInEx) on, in Mods > General.""",
           """CRIMESIGHT Revival - 3D models
==============================

Your own 3D models and animations. You manage them from the launcher, in Mods > Models.
They need Hot reload (BepInEx) on, in Mods > General.

  .fbx / .glb    your models; a subfolder with a model and its textures also works (handy for
                 downloads: unzip them here). The subfolder's name becomes the model's name.
  animations\\    your animations (see "Animations" below)
  images\\        portrait images for new characters (see "New characters" below)
  skeletons\\     one skeleton per character, for a perfect fit (see below)

Models
 - Give a model to a character in Mods > Models and it replaces that character's look.
 - In your room everyone sees them (in someone else's room you see theirs).
 - The game's animations play on your model.
 - Humanoid models (Mixamo, VRChat/Unity, VRoid, Blender, 3ds Max Biped, DAZ, MMD...) are fitted
   automatically: their bones are recognised by name, and the model is turned upright, scaled to the
   character and put in the game's T pose. Hair, skirts and other extra bones follow the nearest body
   bone (they don't swing).
 - Textures: the colour texture of each material, inside the model file or next to it
   (PNG, JPG, TGA, BMP, PSD...).
 - Keep each model under about 60,000 triangles.
 - If the game is open, changes appear right away (press "Reload" after exporting a model again).
 - If something looks wrong, BepInEx/LogOutput.log has lines starting with [Modelos] that say
   which bones were recognised.

For a perfect fit (optional, Blender 3.6 or later)
 1. Open the game once with Hot reload on. The "skeletons" folder then gets one skeleton per
    character (Agatha.glb, Berkeley.glb..., plus Traitor.glb and Victim.glb). They only contain
    bones, made from your own copy of the game.
 2. In Blender: File > Import > glTF 2.0, pick the skeleton and delete the tiny mesh
    "CSR_borra_esta_malla".
 3. Fit your model over the bones. Select the model, then the armature (Shift+click), and press
    Ctrl+P > With Automatic Weights. Don't rename the bones.
 4. File > Export > glTF 2.0 (.glb) or FBX, into this folder.

New characters (Mods > Models > New characters)
 - Instead of always replacing someone, a new character joins the draw of every match: each match
   picks 6 of the enabled characters, and original and new ones have the same chance. Choose who
   can appear with the "Character Selection" button in the game's waiting room (the host decides
   for their room; at least 6).
 - It needs a 3D model. Everything else is optional:
     name and lines: without them, it uses those of the character whose place it takes;
     image: put it in the "images" folder; without one, it's generated from the model;
     animations: without its own, it moves like the character chosen in "Animations of".
 - It always plays like the character whose place it takes.
 - Characters of the "Traitor" type don't appear in matches yet.

Animations (folder "animations")
 - Put .fbx or .glb animations here (from Mixamo: choose "FBX Binary" and "Without Skin", and
   "In Place" for walks and runs). Any humanoid animation works: it's fitted to the character.
 - In Mods > Models > Animations, choose for each character which animation replaces its idle,
   walk or run. It works with both the game's models and yours.
 - The first animation in each file is used; the game still decides when each one plays.""",
           """CRIMESIGHT Revival - custom cursor
==================================

Your own mouse cursor. The easiest way is to use the launcher: Mods > Custom cursor >
"Choose image...", then pick the click point. You can also put the files here yourself:

  cursor.png     the normal cursor, in menus and in matches. A PNG with a transparent background,
                 ideally 32x32 or 64x64 pixels.
  hotspot.txt    optional: the point of cursor.png that clicks, as "x,y" in pixels from the
                 top-left corner (0,0 by default, like an arrow). For a centred 32x32
                 crosshair: 16,16
  other .png     optional: each one replaces the game cursor with the same name (move, run,
                 attack...). The names appear in BepInEx/LogOutput.log, in the lines
                 "[Cursor] el juego usa el cursor ...".

 - Only you see it.
 - It needs Hot reload (BepInEx) on, in Mods > General.
 - It's applied when you open the game from the launcher, or within a few seconds if it's
   already open.
 - To go back to the game's cursor, press "Turn off" in the launcher or empty this folder."""),

    "es": ("""CRIMESIGHT Revival - mods
=========================

Esta es tu carpeta de mods. Todo lo que hay en ella se gestiona desde la ventana Mods del lanzador.

  stamps\\      las imágenes de tus stickers
  avatars\\     las imágenes de tus avatares (para usarlas como foto de perfil)
  mod.json     opcional: el nombre y el autor que se muestran para tus mods
  models\\      tus modelos 3D y animaciones (mira el README.txt de dentro)
  cursor\\      tu cursor propio (mira el README.txt de dentro)
  stages\\      los escenarios que guardas en el Creador de escenarios

Stickers y avatares
 - PNG, JPG, WEBP... Sirve cualquier tamaño: se ajustan solos.
 - Se añaden como nuevos: los stickers y avatares del juego no se cambian nunca.
 - En tu sala los ven todos (en la sala de otro ves los suyos).
 - Un sticker no muestra ningún mensaje en la partida salvo que le pongas uno con el botón
   "Mensajes" (Mods > Stickers). Un número al principio del nombre del archivo (01_) solo sirve
   para ordenar.
 - Los cambios se ven la próxima vez que abras el juego desde el lanzador, o al momento con la
   Recarga en caliente (BepInEx) activada, en Mods > General.""",
           """CRIMESIGHT Revival - modelos 3D
===============================

Tus propios modelos 3D y animaciones. Se gestionan desde el lanzador, en Mods > Modelos.
Necesitan la Recarga en caliente (BepInEx) activada, en Mods > General.

  .fbx / .glb    tus modelos; también vale una subcarpeta con un modelo y sus texturas (útil para
                 lo que descargues: descomprímelo aquí). El nombre de la subcarpeta es el del modelo.
  animations\\    tus animaciones (mira "Animaciones" más abajo)
  images\\        imágenes de retrato para personajes nuevos (mira "Personajes nuevos" más abajo)
  skeletons\\     un esqueleto por personaje, para un ajuste perfecto (mira más abajo)

Modelos
 - Asigna un modelo a un personaje en Mods > Modelos y este sustituirá su aspecto.
 - En tu sala los ven todos (en la sala de otro ves los suyos).
 - En tu modelo se ven las animaciones del juego.
 - Los modelos humanoides (Mixamo, VRChat/Unity, VRoid, Blender, 3ds Max Biped, DAZ, MMD...) se
   ajustan solos: sus huesos se reconocen por el nombre, y el modelo se pone de pie, se escala al
   personaje y se coloca en la pose en T del juego. El pelo, las faldas y otros huesos extra siguen
   al hueso del cuerpo más cercano (no se balancean).
 - Texturas: la textura de color de cada material, dentro del archivo del modelo o a su lado
   (PNG, JPG, TGA, BMP, PSD...).
 - Procura que cada modelo tenga menos de unos 60.000 triángulos.
 - Si el juego está abierto, los cambios se ven al momento (pulsa "Recargar" después de volver a
   exportar un modelo).
 - Si algo se ve mal, BepInEx/LogOutput.log tiene líneas que empiezan por [Modelos] que dicen qué
   huesos se han reconocido.

Para un ajuste perfecto (opcional, Blender 3.6 o posterior)
 1. Abre el juego una vez con la Recarga en caliente activada. La carpeta "skeletons" recibe
    entonces un esqueleto por personaje (Agatha.glb, Berkeley.glb..., además de Traitor.glb y
    Victim.glb). Solo contienen huesos, sacados de tu propia copia del juego.
 2. En Blender: Archivo > Importar > glTF 2.0, elige el esqueleto y borra la malla pequeñita
    "CSR_borra_esta_malla".
 3. Ajusta tu modelo sobre los huesos. Selecciona el modelo, luego el esqueleto (Mayús+clic), y
    pulsa Ctrl+P > Con pesos automáticos. No cambies el nombre de los huesos.
 4. Archivo > Exportar > glTF 2.0 (.glb) o FBX, en esta carpeta.

Personajes nuevos (Mods > Modelos > Personajes nuevos)
 - En vez de sustituir siempre a alguien, un personaje nuevo entra en el sorteo de cada partida: en
   cada partida salen 6 de los personajes activados, y los originales y los nuevos tienen la misma
   probabilidad. Elige quién puede salir con el botón "Selección de personajes" de la sala de
   espera del juego (decide el anfitrión para su sala; mínimo 6).
 - Necesita un modelo 3D. Todo lo demás es opcional:
     nombre y frases: sin ellos, usa los del personaje cuyo sitio ocupa;
     imagen: ponla en la carpeta "images"; sin ella, se genera a partir del modelo;
     animaciones: sin las suyas, se mueve como el personaje elegido en "Animaciones de".
 - Siempre juega como el personaje cuyo sitio ocupa.
 - Los personajes de tipo "Traidor" todavía no salen en las partidas.

Animaciones (carpeta "animations")
 - Pon aquí animaciones .fbx o .glb (de Mixamo: elige "FBX Binary" y "Without Skin", e
   "In Place" para andar y correr). Sirve cualquier animación humanoide: se ajusta al personaje.
 - En Mods > Modelos > Animaciones, elige para cada personaje qué animación sustituye a su
   reposo, su andar o su correr. Funciona con los modelos del juego y con los tuyos.
 - Se usa la primera animación de cada archivo; el juego sigue decidiendo cuándo se ve cada una.""",
           """CRIMESIGHT Revival - cursor propio
==================================

Tu propio cursor del ratón. Lo más fácil es usar el lanzador: Mods > Cursor propio >
"Elegir imagen...", y luego elegir el punto de clic. También puedes poner los archivos aquí tú mismo:

  cursor.png     el cursor normal, en los menús y en la partida. Un PNG con fondo transparente,
                 mejor de 32x32 o 64x64 píxeles.
  hotspot.txt    opcional: el punto de cursor.png que hace clic, como "x,y" en píxeles desde la
                 esquina de arriba a la izquierda (0,0 por defecto, como una flecha). Para una
                 mira centrada de 32x32: 16,16
  otros .png     opcional: cada uno sustituye al cursor del juego que se llama igual (moverse,
                 correr, atacar...). Los nombres salen en BepInEx/LogOutput.log, en las líneas
                 "[Cursor] el juego usa el cursor ...".

 - Solo lo ves tú.
 - Necesita la Recarga en caliente (BepInEx) activada, en Mods > General.
 - Se aplica al abrir el juego desde el lanzador, o en unos segundos si ya está abierto.
 - Para volver al cursor del juego, pulsa "Desactivar" en el lanzador o vacía esta carpeta."""),

    "fr": ("""CRIMESIGHT Revival - mods
=========================

Ceci est votre dossier de mods. Tout ce qu'il contient se gère depuis la fenêtre Mods du lanceur.

  stamps\\      les images de vos stickers
  avatars\\     les images de vos avatars (à utiliser comme photo de profil)
  mod.json     facultatif : le nom et l'auteur affichés pour vos mods
  models\\      vos modèles 3D et animations (voir le README.txt à l'intérieur)
  cursor\\      votre curseur personnalisé (voir le README.txt à l'intérieur)
  stages\\      les scénarios que vous enregistrez dans le Créateur de scénarios

Stickers et avatars
 - PNG, JPG, WEBP... Toutes les tailles conviennent : ils sont ajustés automatiquement.
 - Ils sont ajoutés en plus : les stickers et avatars du jeu ne sont jamais modifiés.
 - Dans votre salon, tout le monde les voit (dans le salon de quelqu'un d'autre, vous voyez les siens).
 - Un sticker n'affiche aucun message en partie, sauf si vous lui en donnez un avec le bouton
   « Messages » (Mods > Stickers). Un numéro au début du nom du fichier (01_) sert seulement à l'ordre.
 - Les changements apparaissent la prochaine fois que vous ouvrez le jeu depuis le lanceur, ou tout
   de suite avec le Rechargement à chaud (BepInEx) activé, dans Mods > Général.""",
           """CRIMESIGHT Revival - modèles 3D
===============================

Vos propres modèles 3D et animations. Ils se gèrent depuis le lanceur, dans Mods > Modèles.
Ils nécessitent le Rechargement à chaud (BepInEx) activé, dans Mods > Général.

  .fbx / .glb    vos modèles ; un sous-dossier avec un modèle et ses textures fonctionne aussi
                 (pratique pour les téléchargements : décompressez-les ici). Le nom du sous-dossier
                 devient le nom du modèle.
  animations\\    vos animations (voir « Animations » plus bas)
  images\\        images de portrait pour les nouveaux personnages (voir « Nouveaux personnages »)
  skeletons\\     un squelette par personnage, pour un ajustement parfait (voir plus bas)

Modèles
 - Donnez un modèle à un personnage dans Mods > Modèles et il remplace l'apparence de ce personnage.
 - Dans votre salon, tout le monde les voit (dans le salon de quelqu'un d'autre, vous voyez les siens).
 - Les animations du jeu sont jouées sur votre modèle.
 - Les modèles humanoïdes (Mixamo, VRChat/Unity, VRoid, Blender, 3ds Max Biped, DAZ, MMD...) sont
   ajustés automatiquement : leurs os sont reconnus par leur nom, et le modèle est redressé, mis à
   l'échelle du personnage et placé dans la pose en T du jeu. Les cheveux, les jupes et les autres
   os supplémentaires suivent l'os du corps le plus proche (ils ne se balancent pas).
 - Textures : la texture de couleur de chaque matériau, dans le fichier du modèle ou à côté
   (PNG, JPG, TGA, BMP, PSD...).
 - Restez sous environ 60 000 triangles par modèle.
 - Si le jeu est ouvert, les changements apparaissent tout de suite (appuyez sur « Actualiser »
   après avoir réexporté un modèle).
 - Si quelque chose cloche, BepInEx/LogOutput.log contient des lignes commençant par [Modelos]
   qui indiquent quels os ont été reconnus.

Pour un ajustement parfait (facultatif, Blender 3.6 ou plus récent)
 1. Ouvrez le jeu une fois avec le Rechargement à chaud activé. Le dossier « skeletons » reçoit
    alors un squelette par personnage (Agatha.glb, Berkeley.glb..., plus Traitor.glb et
    Victim.glb). Ils ne contiennent que des os, créés à partir de votre propre copie du jeu.
 2. Dans Blender : Fichier > Importer > glTF 2.0, choisissez le squelette et supprimez le petit
    maillage « CSR_borra_esta_malla ».
 3. Placez votre modèle sur les os. Sélectionnez le modèle, puis l'armature (Maj+clic), et faites
    Ctrl+P > Avec poids automatiques. Ne renommez pas les os.
 4. Fichier > Exporter > glTF 2.0 (.glb) ou FBX, dans ce dossier.

Nouveaux personnages (Mods > Modèles > Nouveaux personnages)
 - Au lieu de toujours remplacer quelqu'un, un nouveau personnage entre dans le tirage de chaque
   partie : chaque partie tire 6 des personnages activés, et les originaux et les nouveaux ont la
   même chance. Choisissez qui peut apparaître avec le bouton « Sélection des personnages » du
   salon d'attente du jeu (l'hôte décide pour son salon ; au moins 6).
 - Il lui faut un modèle 3D. Tout le reste est facultatif :
     nom et répliques : sans eux, il utilise ceux du personnage dont il prend la place ;
     image : mettez-la dans le dossier « images » ; sans image, elle est créée à partir du modèle ;
     animations : sans les siennes, il bouge comme le personnage choisi dans « Animations de ».
 - Il joue toujours comme le personnage dont il prend la place.
 - Les personnages de type « Traître » n'apparaissent pas encore en partie.

Animations (dossier « animations »)
 - Mettez ici des animations .fbx ou .glb (depuis Mixamo : choisissez « FBX Binary » et
   « Without Skin », et « In Place » pour les marches et les courses). Toute animation humanoïde
   convient : elle est ajustée au personnage.
 - Dans Mods > Modèles > Animations, choisissez pour chaque personnage quelle animation remplace
   son attente, sa marche ou sa course. Cela fonctionne avec les modèles du jeu comme avec les vôtres.
 - La première animation de chaque fichier est utilisée ; c'est toujours le jeu qui décide quand
   chacune est jouée.""",
           """CRIMESIGHT Revival - curseur personnalisé
=========================================

Votre propre curseur de souris. Le plus simple est de passer par le lanceur : Mods > Curseur perso >
« Choisir une image... », puis choisissez le point de clic. Vous pouvez aussi mettre les fichiers
ici vous-même :

  cursor.png     le curseur normal, dans les menus et en partie. Un PNG à fond transparent,
                 idéalement de 32x32 ou 64x64 pixels.
  hotspot.txt    facultatif : le point de cursor.png qui clique, sous la forme « x,y » en pixels
                 depuis le coin en haut à gauche (0,0 par défaut, comme une flèche). Pour un
                 viseur centré de 32x32 : 16,16
  autres .png    facultatif : chacun remplace le curseur du jeu qui porte le même nom (se
                 déplacer, courir, attaquer...). Les noms apparaissent dans
                 BepInEx/LogOutput.log, dans les lignes « [Cursor] el juego usa el cursor ... ».

 - Vous seul le voyez.
 - Il nécessite le Rechargement à chaud (BepInEx) activé, dans Mods > Général.
 - Il s'applique quand vous ouvrez le jeu depuis le lanceur, ou en quelques secondes s'il est
   déjà ouvert.
 - Pour revenir au curseur du jeu, appuyez sur « Désactiver » dans le lanceur ou videz ce dossier."""),

    "it": ("""CRIMESIGHT Revival - mod
========================

Questa è la tua cartella dei mod. Tutto quello che contiene si gestisce dalla finestra Mod del launcher.

  stamps\\      le immagini dei tuoi sticker
  avatars\\     le immagini dei tuoi avatar (da usare come immagine del profilo)
  mod.json     facoltativo: il nome e l'autore mostrati per i tuoi mod
  models\\      i tuoi modelli 3D e animazioni (vedi il README.txt all'interno)
  cursor\\      il tuo cursore personalizzato (vedi il README.txt all'interno)
  stages\\      gli scenari che salvi nel Creatore di scenari

Sticker e avatar
 - PNG, JPG, WEBP... Va bene qualsiasi dimensione: vengono adattati in automatico.
 - Vengono aggiunti come nuovi: gli sticker e gli avatar del gioco non vengono mai modificati.
 - Nella tua stanza li vedono tutti (nella stanza di un altro vedi i suoi).
 - Uno sticker non mostra nessun messaggio in partita, a meno che tu non gliene assegni uno con il
   pulsante "Messaggi" (Mod > Sticker). Un numero all'inizio del nome del file (01_) serve solo
   per l'ordine.
 - Le modifiche compaiono la prossima volta che apri il gioco dal launcher, o subito con la
   Ricarica a caldo (BepInEx) attiva, in Mod > Generale.""",
           """CRIMESIGHT Revival - modelli 3D
===============================

I tuoi modelli 3D e animazioni. Si gestiscono dal launcher, in Mod > Modelli.
Richiedono la Ricarica a caldo (BepInEx) attiva, in Mod > Generale.

  .fbx / .glb    i tuoi modelli; va bene anche una sottocartella con un modello e le sue texture
                 (comodo per i download: estraili qui). Il nome della sottocartella diventa il
                 nome del modello.
  animations\\    le tue animazioni (vedi "Animazioni" più sotto)
  images\\        immagini per i ritratti dei nuovi personaggi (vedi "Nuovi personaggi" più sotto)
  skeletons\\     uno scheletro per personaggio, per un adattamento perfetto (vedi più sotto)

Modelli
 - Assegna un modello a un personaggio in Mod > Modelli e sostituirà l'aspetto di quel personaggio.
 - Nella tua stanza li vedono tutti (nella stanza di un altro vedi i suoi).
 - Sul tuo modello vengono riprodotte le animazioni del gioco.
 - I modelli umanoidi (Mixamo, VRChat/Unity, VRoid, Blender, 3ds Max Biped, DAZ, MMD...) vengono
   adattati in automatico: le ossa vengono riconosciute dal nome, e il modello viene raddrizzato,
   portato alla scala del personaggio e messo nella posa a T del gioco. Capelli, gonne e altre ossa
   extra seguono l'osso del corpo più vicino (non oscillano).
 - Texture: la texture di colore di ogni materiale, dentro il file del modello o accanto
   (PNG, JPG, TGA, BMP, PSD...).
 - Tieni ogni modello sotto i 60.000 triangoli circa.
 - Se il gioco è aperto, le modifiche compaiono subito (premi "Ricarica" dopo aver riesportato
   un modello).
 - Se qualcosa non va, BepInEx/LogOutput.log contiene righe che iniziano con [Modelos] e indicano
   quali ossa sono state riconosciute.

Per un adattamento perfetto (facoltativo, Blender 3.6 o successivo)
 1. Apri il gioco una volta con la Ricarica a caldo attiva. La cartella "skeletons" riceve allora
    uno scheletro per personaggio (Agatha.glb, Berkeley.glb..., più Traitor.glb e Victim.glb).
    Contengono solo ossa, create dalla tua copia del gioco.
 2. In Blender: File > Importa > glTF 2.0, scegli lo scheletro ed elimina la piccola mesh
    "CSR_borra_esta_malla".
 3. Adatta il tuo modello alle ossa. Seleziona il modello, poi l'armatura (Maiusc+clic), e premi
    Ctrl+P > Con pesi automatici. Non rinominare le ossa.
 4. File > Esporta > glTF 2.0 (.glb) o FBX, in questa cartella.

Nuovi personaggi (Mod > Modelli > Nuovi personaggi)
 - Invece di sostituire sempre qualcuno, un nuovo personaggio entra nel sorteggio di ogni partita:
   ogni partita sceglie 6 dei personaggi attivati, e originali e nuovi hanno la stessa probabilità.
   Scegli chi può comparire con il pulsante "Selezione dei personaggi" nella sala d'attesa del
   gioco (decide l'host per la sua stanza; almeno 6).
 - Serve un modello 3D. Tutto il resto è facoltativo:
     nome e battute: senza, usa quelli del personaggio di cui prende il posto;
     immagine: mettila nella cartella "images"; senza, viene creata dal modello;
     animazioni: senza le sue, si muove come il personaggio scelto in "Animazioni di".
 - Gioca sempre come il personaggio di cui prende il posto.
 - I personaggi di tipo "Traditore" non compaiono ancora nelle partite.

Animazioni (cartella "animations")
 - Metti qui animazioni .fbx o .glb (da Mixamo: scegli "FBX Binary" e "Without Skin", e
   "In Place" per camminate e corse). Va bene qualsiasi animazione umanoide: viene adattata al
   personaggio.
 - In Mod > Modelli > Animazioni, scegli per ogni personaggio quale animazione sostituisce la sua
   posa d'attesa, la camminata o la corsa. Funziona sia con i modelli del gioco sia con i tuoi.
 - Viene usata la prima animazione di ogni file; è sempre il gioco a decidere quando viene
   riprodotta ciascuna.""",
           """CRIMESIGHT Revival - cursore personalizzato
===========================================

Il tuo cursore del mouse. Il modo più semplice è usare il launcher: Mod > Cursore personalizzato >
"Scegli immagine...", poi scegli il punto del clic. Puoi anche mettere i file qui a mano:

  cursor.png     il cursore normale, nei menu e in partita. Un PNG con sfondo trasparente,
                 meglio se 32x32 o 64x64 pixel.
  hotspot.txt    facoltativo: il punto di cursor.png che fa clic, come "x,y" in pixel
                 dall'angolo in alto a sinistra (0,0 di base, come una freccia). Per un mirino
                 centrato di 32x32: 16,16
  altri .png     facoltativo: ognuno sostituisce il cursore del gioco con lo stesso nome
                 (muoversi, correre, attaccare...). I nomi compaiono in BepInEx/LogOutput.log,
                 nelle righe "[Cursor] el juego usa el cursor ...".

 - Lo vedi solo tu.
 - Richiede la Ricarica a caldo (BepInEx) attiva, in Mod > Generale.
 - Si applica quando apri il gioco dal launcher, o in pochi secondi se è già aperto.
 - Per tornare al cursore del gioco, premi "Disattiva" nel launcher o svuota questa cartella."""),

    "de": ("""CRIMESIGHT Revival - Mods
=========================

Das ist dein Mods-Ordner. Alles darin verwaltest du im Mods-Fenster des Launchers.

  stamps\\      deine Sticker-Bilder
  avatars\\     deine Avatar-Bilder (als Profilbild)
  mod.json     optional: der Name und Autor, die für deine Mods angezeigt werden
  models\\      deine 3D-Modelle und Animationen (siehe die README.txt darin)
  cursor\\      dein eigener Cursor (siehe die README.txt darin)
  stages\\      die Szenarien, die du im Szenario-Editor speicherst

Sticker und Avatare
 - PNG, JPG, WEBP... Jede Größe funktioniert: Sie werden automatisch angepasst.
 - Sie werden als neue hinzugefügt: Die Sticker und Avatare des Spiels werden nie verändert.
 - In deinem Raum sehen sie alle (im Raum eines anderen siehst du seine).
 - Ein Sticker zeigt in der Partie keine Nachricht, es sei denn, du gibst ihm eine über die Schaltfläche
   "Nachrichten" (Mods > Sticker). Eine Zahl am Anfang des Dateinamens (01_) legt nur die
   Reihenfolge fest.
 - Änderungen erscheinen, wenn du das Spiel das nächste Mal über den Launcher startest, oder sofort
   mit eingeschaltetem Hot Reload (BepInEx), unter Mods > Allgemein.""",
           """CRIMESIGHT Revival - 3D-Modelle
===============================

Deine eigenen 3D-Modelle und Animationen. Du verwaltest sie im Launcher unter Mods > Modelle.
Sie brauchen eingeschaltetes Hot Reload (BepInEx), unter Mods > Allgemein.

  .fbx / .glb    deine Modelle; ein Unterordner mit einem Modell und seinen Texturen klappt auch
                 (praktisch für Downloads: hier entpacken). Der Name des Unterordners wird zum
                 Namen des Modells.
  animations\\    deine Animationen (siehe "Animationen" unten)
  images\\        Porträtbilder für neue Figuren (siehe "Neue Figuren" unten)
  skeletons\\     ein Skelett pro Figur, für eine perfekte Anpassung (siehe unten)

Modelle
 - Gib einer Figur unter Mods > Modelle ein Modell, und es ersetzt das Aussehen dieser Figur.
 - In deinem Raum sehen sie alle (im Raum eines anderen siehst du seine).
 - Die Animationen des Spiels laufen auf deinem Modell.
 - Humanoide Modelle (Mixamo, VRChat/Unity, VRoid, Blender, 3ds Max Biped, DAZ, MMD...) werden
   automatisch angepasst: Ihre Knochen werden am Namen erkannt, und das Modell wird aufgerichtet,
   auf die Größe der Figur skaliert und in die T-Pose des Spiels gebracht. Haare, Röcke und andere
   zusätzliche Knochen folgen dem nächsten Körperknochen (sie schwingen nicht).
 - Texturen: die Farbtextur jedes Materials, in der Modelldatei oder daneben
   (PNG, JPG, TGA, BMP, PSD...).
 - Bleib pro Modell unter etwa 60.000 Dreiecken.
 - Ist das Spiel offen, erscheinen Änderungen sofort (nach erneutem Export eines Modells
   "Neu laden" drücken).
 - Wenn etwas falsch aussieht, stehen in BepInEx/LogOutput.log Zeilen mit [Modelos], die zeigen,
   welche Knochen erkannt wurden.

Für eine perfekte Anpassung (optional, Blender 3.6 oder neuer)
 1. Starte das Spiel einmal mit eingeschaltetem Hot Reload. Der Ordner "skeletons" bekommt dann
    ein Skelett pro Figur (Agatha.glb, Berkeley.glb..., dazu Traitor.glb und Victim.glb). Sie
    enthalten nur Knochen, erstellt aus deiner eigenen Kopie des Spiels.
 2. In Blender: Datei > Importieren > glTF 2.0, wähle das Skelett und lösche das winzige Mesh
    "CSR_borra_esta_malla".
 3. Passe dein Modell an die Knochen an. Wähle das Modell aus, dann das Armature (Umschalt+Klick),
    und drücke Strg+P > Mit automatischen Gewichten. Benenne die Knochen nicht um.
 4. Datei > Exportieren > glTF 2.0 (.glb) oder FBX, in diesen Ordner.

Neue Figuren (Mods > Modelle > Neue Figuren)
 - Statt immer jemanden zu ersetzen, nimmt eine neue Figur an der Auslosung jeder Partie teil:
   Jede Partie wählt 6 der aktivierten Figuren, und Originale und neue haben die gleiche Chance.
   Wer erscheinen kann, legst du mit der Schaltfläche "Figurenauswahl" im Warteraum des Spiels
   fest (der Host entscheidet für seinen Raum; mindestens 6).
 - Sie braucht ein 3D-Modell. Alles andere ist optional:
     Name und Sätze: ohne sie nutzt sie die der Figur, deren Platz sie einnimmt;
     Bild: lege es in den Ordner "images"; ohne Bild wird es aus dem Modell erzeugt;
     Animationen: ohne eigene bewegt sie sich wie die Figur, die unter "Animationen von" gewählt ist.
 - Sie spielt sich immer wie die Figur, deren Platz sie einnimmt.
 - Figuren vom Typ "Verräter" erscheinen noch nicht in Partien.

Animationen (Ordner "animations")
 - Lege hier .fbx- oder .glb-Animationen ab (von Mixamo: "FBX Binary" und "Without Skin" wählen,
   und für Gehen und Laufen "In Place"). Jede humanoide Animation funktioniert: Sie wird an
   die Figur angepasst.
 - Unter Mods > Modelle > Animationen wählst du für jede Figur, welche Animation ihr Stehen,
   Gehen oder Laufen ersetzt. Das funktioniert mit den Modellen des Spiels und mit deinen.
 - Verwendet wird die erste Animation jeder Datei; wann welche läuft, entscheidet weiterhin das Spiel.""",
           """CRIMESIGHT Revival - eigener Cursor
===================================

Dein eigener Mauszeiger. Am einfachsten geht es im Launcher: Mods > Eigener Cursor >
"Bild wählen...", dann den Klickpunkt wählen. Du kannst die Dateien auch selbst hier ablegen:

  cursor.png     der normale Cursor, in Menüs und in Partien. Ein PNG mit transparentem
                 Hintergrund, am besten 32x32 oder 64x64 Pixel.
  hotspot.txt    optional: der Punkt von cursor.png, der klickt, als "x,y" in Pixeln von der
                 oberen linken Ecke (standardmäßig 0,0, wie ein Pfeil). Für ein zentriertes
                 32x32-Fadenkreuz: 16,16
  andere .png    optional: jede ersetzt den gleichnamigen Cursor des Spiels (bewegen, rennen,
                 angreifen...). Die Namen stehen in BepInEx/LogOutput.log, in den Zeilen
                 "[Cursor] el juego usa el cursor ...".

 - Nur du siehst ihn.
 - Er braucht eingeschaltetes Hot Reload (BepInEx), unter Mods > Allgemein.
 - Er wird angewendet, wenn du das Spiel über den Launcher startest, oder nach ein paar Sekunden,
   wenn es schon offen ist.
 - Um zum Cursor des Spiels zurückzukehren, drücke im Launcher "Ausschalten" oder leere diesen
   Ordner."""),

    "pt": ("""CRIMESIGHT Revival - mods
=========================

Esta é a sua pasta de mods. Tudo o que há nela é gerenciado pela janela Mods do launcher.

  stamps\\      as imagens dos seus emojis
  avatars\\     as imagens dos seus avatares (para usar como foto de perfil)
  mod.json     opcional: o nome e o autor mostrados para os seus mods
  models\\      seus modelos 3D e animações (veja o README.txt lá dentro)
  cursor\\      seu cursor próprio (veja o README.txt lá dentro)
  stages\\      os cenários que você salva no Criador de cenários

Emojis e avatares
 - PNG, JPG, WEBP... Qualquer tamanho serve: eles são ajustados automaticamente.
 - Eles são adicionados como novos: os emojis e avatares do jogo nunca são alterados.
 - Na sua sala todos os veem (na sala de outra pessoa, você vê os dela).
 - Um emoji não mostra nenhuma mensagem na partida, a menos que você defina uma com o botão
   "Mensagens" (Mods > Emojis). Um número no início do nome do arquivo (01_) só define a ordem.
 - As mudanças aparecem na próxima vez que você abrir o jogo pelo launcher, ou na hora com a
   Recarga instantânea (BepInEx) ativada, em Mods > Geral.""",
           """CRIMESIGHT Revival - modelos 3D
===============================

Seus próprios modelos 3D e animações. Eles são gerenciados pelo launcher, em Mods > Modelos.
Precisam da Recarga instantânea (BepInEx) ativada, em Mods > Geral.

  .fbx / .glb    seus modelos; uma subpasta com um modelo e suas texturas também serve (prático
                 para downloads: descompacte-os aqui). O nome da subpasta vira o nome do modelo.
  animations\\    suas animações (veja "Animações" mais abaixo)
  images\\        imagens de retrato para novos personagens (veja "Novos personagens" mais abaixo)
  skeletons\\     um esqueleto por personagem, para um ajuste perfeito (veja mais abaixo)

Modelos
 - Dê um modelo a um personagem em Mods > Modelos e ele substitui a aparência desse personagem.
 - Na sua sala todos os veem (na sala de outra pessoa, você vê os dela).
 - As animações do jogo são reproduzidas no seu modelo.
 - Modelos humanoides (Mixamo, VRChat/Unity, VRoid, Blender, 3ds Max Biped, DAZ, MMD...) são
   ajustados automaticamente: os ossos são reconhecidos pelo nome, e o modelo é endireitado,
   colocado na escala do personagem e posto na pose em T do jogo. Cabelo, saias e outros ossos
   extras seguem o osso do corpo mais próximo (não balançam).
 - Texturas: a textura de cor de cada material, dentro do arquivo do modelo ou ao lado dele
   (PNG, JPG, TGA, BMP, PSD...).
 - Mantenha cada modelo abaixo de uns 60.000 triângulos.
 - Se o jogo estiver aberto, as mudanças aparecem na hora (aperte "Recarregar" depois de
   exportar um modelo de novo).
 - Se algo parecer errado, BepInEx/LogOutput.log tem linhas começando com [Modelos] que dizem
   quais ossos foram reconhecidos.

Para um ajuste perfeito (opcional, Blender 3.6 ou mais recente)
 1. Abra o jogo uma vez com a Recarga instantânea ativada. A pasta "skeletons" recebe então um
    esqueleto por personagem (Agatha.glb, Berkeley.glb..., além de Traitor.glb e Victim.glb).
    Eles só têm ossos, feitos a partir da sua própria cópia do jogo.
 2. No Blender: Arquivo > Importar > glTF 2.0, escolha o esqueleto e apague a pequena malha
    "CSR_borra_esta_malla".
 3. Ajuste seu modelo sobre os ossos. Selecione o modelo, depois a armação (Shift+clique), e
    aperte Ctrl+P > Com pesos automáticos. Não renomeie os ossos.
 4. Arquivo > Exportar > glTF 2.0 (.glb) ou FBX, para esta pasta.

Novos personagens (Mods > Modelos > Novos personagens)
 - Em vez de sempre substituir alguém, um novo personagem entra no sorteio de cada partida: cada
   partida escolhe 6 dos personagens ativados, e os originais e os novos têm a mesma chance.
   Escolha quem pode aparecer com o botão "Seleção de personagens" na sala de espera do jogo
   (o anfitrião decide pela sua sala; pelo menos 6).
 - Ele precisa de um modelo 3D. Todo o resto é opcional:
     nome e falas: sem eles, usa os do personagem cujo lugar ocupa;
     imagem: coloque-a na pasta "images"; sem ela, é gerada a partir do modelo;
     animações: sem as próprias, ele se move como o personagem escolhido em "Animações de".
 - Ele sempre joga como o personagem cujo lugar ocupa.
 - Personagens do tipo "Traidor" ainda não aparecem nas partidas.

Animações (pasta "animations")
 - Coloque aqui animações .fbx ou .glb (do Mixamo: escolha "FBX Binary" e "Without Skin", e
   "In Place" para caminhadas e corridas). Qualquer animação humanoide serve: ela é ajustada ao
   personagem.
 - Em Mods > Modelos > Animações, escolha para cada personagem qual animação substitui sua pose
   parada, caminhada ou corrida. Funciona com os modelos do jogo e com os seus.
 - É usada a primeira animação de cada arquivo; o jogo continua decidindo quando cada uma é
   reproduzida.""",
           """CRIMESIGHT Revival - cursor próprio
===================================

Seu próprio cursor do mouse. O jeito mais fácil é usar o launcher: Mods > Cursor próprio >
"Escolher imagem...", e depois escolha o ponto de clique. Você também pode colocar os arquivos
aqui manualmente:

  cursor.png     o cursor normal, nos menus e nas partidas. Um PNG com fundo transparente, de
                 preferência de 32x32 ou 64x64 pixels.
  hotspot.txt    opcional: o ponto de cursor.png que clica, como "x,y" em pixels a partir do
                 canto superior esquerdo (0,0 por padrão, como uma seta). Para uma mira
                 centralizada de 32x32: 16,16
  outros .png    opcional: cada um substitui o cursor do jogo com o mesmo nome (mover, correr,
                 atacar...). Os nomes aparecem em BepInEx/LogOutput.log, nas linhas
                 "[Cursor] el juego usa el cursor ...".

 - Só você o vê.
 - Precisa da Recarga instantânea (BepInEx) ativada, em Mods > Geral.
 - É aplicado quando você abre o jogo pelo launcher, ou em poucos segundos se ele já estiver aberto.
 - Para voltar ao cursor do jogo, aperte "Desativar" no launcher ou esvazie esta pasta."""),

    "ru": ("""CRIMESIGHT Revival — моды
=========================

Это ваша папка модов. Всё, что в ней лежит, настраивается в окне «Моды» лаунчера.

  stamps\\      картинки ваших шаблонов
  avatars\\     картинки ваших аватаров (для фото профиля)
  mod.json     необязательно: имя и автор, которые показываются для ваших модов
  models\\      ваши 3D-модели и анимации (см. README.txt внутри)
  cursor\\      ваш курсор (см. README.txt внутри)
  stages\\      сценарии, которые вы сохраняете в «Редакторе сценариев»

Шаблоны и аватары
 - PNG, JPG, WEBP... Подходит любой размер: они подгоняются автоматически.
 - Они добавляются как новые: шаблоны и аватары игры никогда не меняются.
 - В вашей комнате их видят все (в чужой комнате вы видите шаблоны и аватары хозяина).
 - Шаблон не показывает сообщение в матче, если вы не зададите его кнопкой «Сообщения»
   (Моды > Шаблоны). Число в начале имени файла (01_) задаёт только порядок.
 - Изменения появятся, когда вы в следующий раз откроете игру из лаунчера, или сразу, если включена
   «Горячая перезагрузка» (BepInEx) в разделе Моды > Общее.""",
           """CRIMESIGHT Revival — 3D-модели
==============================

Ваши собственные 3D-модели и анимации. Они настраиваются в лаунчере, в разделе Моды > Модели.
Им нужна включённая «Горячая перезагрузка» (BepInEx) в разделе Моды > Общее.

  .fbx / .glb    ваши модели; подойдёт и подпапка с моделью и её текстурами (удобно для
                 скачанного: распакуйте сюда). Имя подпапки становится именем модели.
  animations\\    ваши анимации (см. «Анимации» ниже)
  images\\        картинки портретов для новых персонажей (см. «Новые персонажи» ниже)
  skeletons\\     по скелету на каждого персонажа, для идеальной подгонки (см. ниже)

Модели
 - Назначьте модель персонажу в разделе Моды > Модели, и она заменит его внешний вид.
 - В вашей комнате их видят все (в чужой комнате вы видите модели хозяина).
 - На вашей модели проигрываются анимации игры.
 - Человекоподобные модели (Mixamo, VRChat/Unity, VRoid, Blender, 3ds Max Biped, DAZ, MMD...)
   подгоняются автоматически: кости распознаются по названиям, а модель ставится вертикально,
   масштабируется под персонажа и приводится к T-позе игры. Волосы, юбки и другие лишние кости
   следуют за ближайшей костью тела (не качаются).
 - Текстуры: цветовая текстура каждого материала, внутри файла модели или рядом с ним
   (PNG, JPG, TGA, BMP, PSD...).
 - Держите каждую модель в пределах примерно 60 000 треугольников.
 - Если игра открыта, изменения видны сразу (после повторного экспорта модели нажмите «Обновить»).
 - Если что-то выглядит не так, в BepInEx/LogOutput.log есть строки, начинающиеся с [Modelos], —
   там видно, какие кости распознаны.

Для идеальной подгонки (необязательно, Blender 3.6 или новее)
 1. Один раз запустите игру с включённой «Горячей перезагрузкой». В папке «skeletons» появится по
    скелету на каждого персонажа (Agatha.glb, Berkeley.glb..., а также Traitor.glb и Victim.glb).
    В них только кости, созданные из вашей копии игры.
 2. В Blender: Файл > Импорт > glTF 2.0, выберите скелет и удалите крошечный меш
    «CSR_borra_esta_malla».
 3. Подгоните модель под кости. Выделите модель, затем арматуру (Shift+щелчок) и нажмите
    Ctrl+P > С автоматическими весами. Не переименовывайте кости.
 4. Файл > Экспорт > glTF 2.0 (.glb) или FBX, в эту папку.

Новые персонажи (Моды > Модели > Новые персонажи)
 - Вместо того чтобы всегда кого-то заменять, новый персонаж участвует в жеребьёвке каждого
   матча: в каждом матче выбираются 6 из включённых персонажей, и у оригинальных и новых шансы
   равны. Кто может появиться, выбирается кнопкой «Выбор персонажей» в зале ожидания игры (решает
   хозяин комнаты; минимум 6).
 - Нужна 3D-модель. Всё остальное необязательно:
     имя и реплики: без них используются те, что у персонажа, чьё место он занимает;
     изображение: положите его в папку «images»; без него оно создаётся из модели;
     анимации: без своих он двигается как персонаж, выбранный в «Анимации от».
 - Играет он всегда как персонаж, чьё место занимает.
 - Персонажи типа «Предатель» пока не появляются в матчах.

Анимации (папка «animations»)
 - Положите сюда анимации .fbx или .glb (из Mixamo: выберите «FBX Binary» и «Without Skin», а для
   ходьбы и бега — «In Place»). Подходит любая человекоподобная анимация: она подгоняется под
   персонажа.
 - В разделе Моды > Модели > Анимации выберите для каждого персонажа, какая анимация заменит его
   стойку, ходьбу или бег. Это работает и с моделями игры, и с вашими.
 - Используется первая анимация в каждом файле; когда какая проигрывается, по-прежнему решает игра.""",
           """CRIMESIGHT Revival — свой курсор
================================

Ваш собственный курсор мыши. Проще всего сделать это через лаунчер: Моды > Свой курсор >
«Выбрать картинку...», затем выберите точку нажатия. Файлы можно положить сюда и вручную:

  cursor.png     обычный курсор, в меню и в матче. PNG с прозрачным фоном, лучше 32x32 или
                 64x64 пикселя.
  hotspot.txt    необязательно: точка cursor.png, которая нажимает, в виде «x,y» в пикселях от
                 левого верхнего угла (по умолчанию 0,0, как у стрелки). Для прицела 32x32 по
                 центру: 16,16
  другие .png    необязательно: каждый заменяет курсор игры с тем же именем (движение, бег,
                 атака...). Имена есть в BepInEx/LogOutput.log, в строках
                 «[Cursor] el juego usa el cursor ...».

 - Видите его только вы.
 - Нужна включённая «Горячая перезагрузка» (BepInEx) в разделе Моды > Общее.
 - Применяется, когда вы открываете игру из лаунчера, или через несколько секунд, если игра уже
   открыта.
 - Чтобы вернуть курсор игры, нажмите «Выключить» в лаунчере или очистите эту папку."""),

    "ja": ("""CRIMESIGHT Revival - MOD
========================

ここはあなたのMODフォルダーです。中身はすべてランチャーの「MOD」ウィンドウで管理します。

  stamps\\      スタンプの画像
  avatars\\     アバターの画像（プロフィール画像に使います）
  mod.json     任意：あなたのMODに表示される名前と作者
  models\\      3Dモデルとアニメーション（中の README.txt を参照）
  cursor\\      カーソル変更（中の README.txt を参照）
  stages\\      ステージクリエイターで保存したステージ

スタンプとアバター
 - PNG、JPG、WEBP など。サイズは自由で、自動で調整されます。
 - 新しく追加されるので、ゲーム本来のスタンプやアバターは変更されません。
 - 自分の部屋では全員に見えます（他の人の部屋ではその人のものが見えます）。
 - スタンプは「メッセージ」ボタン（MOD > スタンプ）で設定しない限り、試合中にメッセージを
   表示しません。ファイル名の先頭の番号（01_）は並び順にだけ使われます。
 - 変更は次にランチャーからゲームを開いたときに反映されます。MOD > 全般 の
   「ホットリロード」（BepInEx）がオンなら、すぐに反映されます。""",
           """CRIMESIGHT Revival - 3Dモデル
=============================

自作の3Dモデルとアニメーションです。ランチャーの MOD > モデル で管理します。
MOD > 全般 の「ホットリロード」（BepInEx）をオンにする必要があります。

  .fbx / .glb    モデル。モデルとテクスチャを入れたサブフォルダーでもかまいません（ダウンロード
                 したものはここに展開すると便利です）。サブフォルダーの名前がモデルの名前になります。
  animations\\    アニメーション（下の「アニメーション」を参照）
  images\\        新キャラクターの肖像画像（下の「新キャラクター」を参照）
  skeletons\\     キャラクターごとの骨格。ぴったり合わせるときに使います（下を参照）

モデル
 - MOD > モデル でキャラクターにモデルを割り当てると、そのキャラクターの見た目が変わります。
 - 自分の部屋では全員に見えます（他の人の部屋ではその人のものが見えます）。
 - モデルにはゲームのアニメーションが再生されます。
 - 人型モデル（Mixamo、VRChat/Unity、VRoid、Blender、3ds Max Biped、DAZ、MMD など）は自動で
   合わせられます。ボーンは名前で認識され、モデルはまっすぐ立てられ、キャラクターの大きさに
   合わせてゲームのTポーズになります。髪やスカートなどの追加ボーンは、いちばん近い体の
   ボーンに付いて動きます（揺れません）。
 - テクスチャ：各マテリアルのカラーテクスチャを、モデルファイルの中かその横に
   （PNG、JPG、TGA、BMP、PSD など）。
 - モデル1つにつき三角形は約 60,000 以下にしてください。
 - ゲームが開いていれば変更はすぐに反映されます（モデルをエクスポートし直したら
   「再読み込み」を押してください）。
 - おかしく見えるときは、BepInEx/LogOutput.log の [Modelos] で始まる行に、どのボーンが
   認識されたかが出ています。

ぴったり合わせるには（任意、Blender 3.6 以降）
 1. 「ホットリロード」をオンにしてゲームを一度開きます。「skeletons」フォルダーに
    キャラクターごとの骨格（Agatha.glb、Berkeley.glb など。ほかに Traitor.glb と Victim.glb）が
    できます。中身はボーンだけで、あなたのゲームから作られています。
 2. Blender で：ファイル > インポート > glTF 2.0 で骨格を選び、小さなメッシュ
    「CSR_borra_esta_malla」を削除します。
 3. モデルをボーンに合わせます。モデルを選択してからアーマチュアを選択（Shift+クリック）し、
    Ctrl+P > 自動のウェイトで を押します。ボーンの名前は変えないでください。
 4. ファイル > エクスポート > glTF 2.0 (.glb) または FBX で、このフォルダーに保存します。

新キャラクター（MOD > モデル > 新キャラクター）
 - 新キャラクターは誰かを常に置き換えるのではなく、毎試合の抽選に加わります。毎試合、有効な
   キャラクターから6人が選ばれ、元のキャラクターと新キャラクターの確率は同じです。出られる
   キャラクターはゲームの待合室の「キャラクター選択」ボタンで選びます（部屋ごとにホストが
   決めます。最低6人）。
 - 3Dモデルが必要です。それ以外はすべて任意です：
     名前とセリフ：ない場合は、入れ替わるキャラクターのものを使います。
     画像：「images」フォルダーに入れます。ない場合はモデルから作られます。
     アニメーション：ない場合は「アニメーション元」で選んだキャラクターと同じ動きをします。
 - プレイはいつも、入れ替わるキャラクターと同じです。
 - 種類が「裏切り者」のキャラクターは、まだ試合に登場しません。

アニメーション（「animations」フォルダー）
 - .fbx か .glb のアニメーションを入れます（Mixamo では「FBX Binary」と「Without Skin」を選び、
   歩きと走りは「In Place」にします）。人型のアニメーションならどれでも使え、キャラクターに
   合わせられます。
 - MOD > モデル > アニメーション で、キャラクターごとに待機・歩き・走りをどのアニメーションに
   置き換えるか選びます。ゲームのモデルにも自作のモデルにも使えます。
 - 各ファイルの最初のアニメーションが使われます。いつ再生するかは今まで通りゲームが決めます。""",
           """CRIMESIGHT Revival - カーソル変更
=================================

自分だけのマウスカーソルです。いちばん簡単なのはランチャーを使う方法です：MOD > カーソル変更 >
「画像を選ぶ...」で画像を選び、クリックする点を選びます。ファイルを自分でここに置くこともできます：

  cursor.png     通常のカーソル（メニューと試合中）。背景が透明な PNG で、32x32 か 64x64
                 ピクセルがおすすめです。
  hotspot.txt    任意：cursor.png のクリックする点。左上の角からのピクセルで "x,y"
                 （初期値は矢印と同じ 0,0）。32x32 の中央の照準なら：16,16
  ほかの .png    任意：それぞれ、同じ名前のゲームのカーソル（移動、走る、攻撃など）を置き換えます。
                 名前は BepInEx/LogOutput.log の "[Cursor] el juego usa el cursor ..." の行に出ます。

 - 見えるのは自分だけです。
 - MOD > 全般 の「ホットリロード」（BepInEx）をオンにする必要があります。
 - ランチャーからゲームを開いたときに反映されます。すでに開いていれば数秒で反映されます。
 - ゲームのカーソルに戻すには、ランチャーで「オフにする」を押すか、このフォルダーを空にしてください。"""),

    "ko": ("""CRIMESIGHT Revival - 모드
=========================

이곳은 내 모드 폴더입니다. 안에 있는 모든 것은 런처의 "모드" 창에서 관리합니다.

  stamps\\      스탬프 이미지
  avatars\\     아바타 이미지(프로필 사진으로 사용)
  mod.json     선택: 내 모드에 표시되는 이름과 제작자
  models\\      3D 모델과 애니메이션(안의 README.txt 참고)
  cursor\\      커서 변경(안의 README.txt 참고)
  stages\\      스테이지 제작기에서 저장한 스테이지

스탬프와 아바타
 - PNG, JPG, WEBP 등. 크기는 상관없으며 자동으로 맞춰집니다.
 - 새것으로 추가되므로 게임 원래의 스탬프와 아바타는 바뀌지 않습니다.
 - 내 방에서는 모두가 봅니다(다른 사람의 방에서는 그 사람의 것이 보입니다).
 - 스탬프는 "메시지" 버튼(모드 > 스탬프)으로 설정하지 않으면 게임 중에 메시지를 보여 주지
   않습니다. 파일 이름 앞의 번호(01_)는 순서를 정할 때만 쓰입니다.
 - 변경 사항은 다음에 런처에서 게임을 열 때 반영됩니다. 모드 > 일반의 "실시간 반영"(BepInEx)을
   켜 두면 바로 반영됩니다.""",
           """CRIMESIGHT Revival - 3D 모델
============================

나만의 3D 모델과 애니메이션입니다. 런처의 모드 > 모델에서 관리합니다.
모드 > 일반의 "실시간 반영"(BepInEx)을 켜야 합니다.

  .fbx / .glb    모델. 모델과 텍스처가 든 하위 폴더도 됩니다(내려받은 파일은 여기에 압축을
                 풀면 편합니다). 하위 폴더의 이름이 모델의 이름이 됩니다.
  animations\\    애니메이션(아래 "애니메이션" 참고)
  images\\        새 캐릭터의 초상화 이미지(아래 "새 캐릭터" 참고)
  skeletons\\     캐릭터별 골격. 완벽하게 맞출 때 씁니다(아래 참고)

모델
 - 모드 > 모델에서 캐릭터에게 모델을 지정하면 그 캐릭터의 모습이 바뀝니다.
 - 내 방에서는 모두가 봅니다(다른 사람의 방에서는 그 사람의 것이 보입니다).
 - 모델에는 게임의 애니메이션이 재생됩니다.
 - 사람형 모델(Mixamo, VRChat/Unity, VRoid, Blender, 3ds Max Biped, DAZ, MMD 등)은 자동으로
   맞춰집니다. 본은 이름으로 인식되고, 모델은 똑바로 세워져 캐릭터 크기에 맞춰지고 게임의
   T 포즈가 됩니다. 머리카락, 치마 등 추가 본은 가장 가까운 몸 본을 따라갑니다(흔들리지 않습니다).
 - 텍스처: 각 머티리얼의 색상 텍스처를 모델 파일 안이나 그 옆에(PNG, JPG, TGA, BMP, PSD 등).
 - 모델 하나당 삼각형은 약 60,000개 이하로 하세요.
 - 게임이 열려 있으면 변경 사항이 바로 반영됩니다(모델을 다시 내보낸 뒤에는 "새로고침"을
   누르세요).
 - 이상해 보이면 BepInEx/LogOutput.log의 [Modelos]로 시작하는 줄에 어떤 본이 인식됐는지
   나옵니다.

완벽하게 맞추려면(선택 사항, Blender 3.6 이상)
 1. "실시간 반영"을 켜고 게임을 한 번 여세요. 그러면 "skeletons" 폴더에 캐릭터별 골격
    (Agatha.glb, Berkeley.glb 등, 그리고 Traitor.glb와 Victim.glb)이 생깁니다. 본만 들어 있으며,
    내 게임에서 만들어집니다.
 2. Blender에서: 파일 > 가져오기 > glTF 2.0으로 골격을 고르고, 작은 메시
    "CSR_borra_esta_malla"를 지우세요.
 3. 모델을 본에 맞추세요. 모델을 선택한 다음 아마추어를 선택(Shift+클릭)하고
    Ctrl+P > 자동 웨이트로를 누르세요. 본 이름은 바꾸지 마세요.
 4. 파일 > 내보내기 > glTF 2.0 (.glb) 또는 FBX로 이 폴더에 저장하세요.

새 캐릭터(모드 > 모델 > 새 캐릭터)
 - 새 캐릭터는 늘 누군가를 대체하는 것이 아니라 매 판의 추첨에 들어갑니다. 매 판 켜 둔 캐릭터 중
   6명이 뽑히며, 원래 캐릭터와 새 캐릭터의 확률은 같습니다. 누가 나올 수 있는지는 게임
   대기실의 "캐릭터 선택" 버튼으로 고릅니다(방마다 방장이 정합니다. 최소 6명).
 - 3D 모델이 필요합니다. 나머지는 모두 선택 사항입니다:
     이름과 대사: 없으면 자리를 대신하는 캐릭터의 것을 씁니다.
     이미지: "images" 폴더에 넣으세요. 없으면 모델에서 만듭니다.
     애니메이션: 없으면 "애니메이션 원본"에서 고른 캐릭터처럼 움직입니다.
 - 플레이는 항상 자리를 대신하는 캐릭터와 같습니다.
 - 종류가 "배신자"인 캐릭터는 아직 게임에 나오지 않습니다.

애니메이션("animations" 폴더)
 - .fbx 또는 .glb 애니메이션을 넣으세요(Mixamo에서는 "FBX Binary"와 "Without Skin"을 고르고,
   걷기와 달리기는 "In Place"로). 사람형 애니메이션이면 무엇이든 되며, 캐릭터에 맞춰집니다.
 - 모드 > 모델 > 애니메이션에서 캐릭터마다 대기, 걷기, 달리기를 어떤 애니메이션으로 바꿀지
   고르세요. 게임의 모델에도 내 모델에도 쓸 수 있습니다.
 - 각 파일의 첫 번째 애니메이션이 쓰이며, 언제 재생할지는 여전히 게임이 정합니다.""",
           """CRIMESIGHT Revival - 커서 변경
==============================

나만의 마우스 커서입니다. 가장 쉬운 방법은 런처를 쓰는 것입니다: 모드 > 커서 변경 > "이미지 선택..."으로
이미지를 고르고 클릭 지점을 고르세요. 파일을 직접 여기에 넣을 수도 있습니다:

  cursor.png     일반 커서(메뉴와 게임 중). 배경이 투명한 PNG, 32x32 또는 64x64 픽셀 권장.
  hotspot.txt    선택: cursor.png에서 클릭되는 지점, 왼쪽 위 모서리부터의 픽셀로 "x,y"
                 (기본값은 화살표처럼 0,0). 가운데에 있는 32x32 조준점이라면: 16,16
  다른 .png      선택: 각각 이름이 같은 게임 커서(이동, 달리기, 공격 등)를 바꿉니다. 이름은
                 BepInEx/LogOutput.log의 "[Cursor] el juego usa el cursor ..." 줄에 나옵니다.

 - 나만 볼 수 있습니다.
 - 모드 > 일반의 "실시간 반영"(BepInEx)을 켜야 합니다.
 - 런처에서 게임을 열 때 반영되며, 이미 열려 있으면 몇 초 안에 반영됩니다.
 - 게임 커서로 돌아가려면 런처에서 "끄기"를 누르거나 이 폴더를 비우세요."""),

    "zh-CN": ("""CRIMESIGHT Revival - 模组
=========================

这是你的模组文件夹。里面的一切都在启动器的"模组"窗口中管理。

  stamps\\      你的表情图片
  avatars\\     你的头像图片（用作个人资料图片）
  mod.json     可选：为你的模组显示的名称和作者
  models\\      你的 3D 模型和动画（见里面的 README.txt）
  cursor\\      你的自定义光标（见里面的 README.txt）
  stages\\      你在场景编辑器中保存的场景

表情和头像
 - PNG、JPG、WEBP 等。任何尺寸都可以：会自动调整。
 - 它们会作为新的添加进来：游戏自带的表情和头像永远不会被修改。
 - 在你的房间里所有人都能看到（在别人的房间里你看到的是对方的）。
 - 表情在对局中不会显示消息，除非你用"消息"按钮（模组 > 表情）给它设置一条。
   文件名开头的数字（01_）只用来排序。
 - 更改会在下次从启动器打开游戏时生效；如果在 模组 > 常规 中开启了"热重载"（BepInEx），
   会立即生效。""",
              """CRIMESIGHT Revival - 3D 模型
============================

你自己的 3D 模型和动画。在启动器的 模组 > 模型 中管理。
需要在 模组 > 常规 中开启"热重载"（BepInEx）。

  .fbx / .glb    你的模型；也可以是装有模型及其贴图的子文件夹（下载的东西直接解压到这里很方便）。
                 子文件夹的名字就是模型的名字。
  animations\\    你的动画（见下面的"动画"）
  images\\        新角色的肖像图片（见下面的"新角色"）
  skeletons\\     每个角色一个骨架，用于完美贴合（见下文）

模型
 - 在 模组 > 模型 中把模型分配给一个角色，它就会替换那个角色的外观。
 - 在你的房间里所有人都能看到（在别人的房间里你看到的是对方的）。
 - 你的模型会播放游戏的动画。
 - 人形模型（Mixamo、VRChat/Unity、VRoid、Blender、3ds Max Biped、DAZ、MMD 等）会自动适配：
   按名字识别骨骼，把模型摆正，缩放到角色的大小，并摆成游戏的 T 字姿势。头发、裙子等额外的
   骨骼会跟随最近的身体骨骼（不会摆动）。
 - 贴图：每个材质的颜色贴图，放在模型文件里面或旁边（PNG、JPG、TGA、BMP、PSD 等）。
 - 每个模型请控制在约 60,000 个三角面以内。
 - 如果游戏开着，更改会立即生效（重新导出模型后请按"重新加载"）。
 - 如果看起来不对，BepInEx/LogOutput.log 中以 [Modelos] 开头的行会显示识别了哪些骨骼。

想要完美贴合（可选，Blender 3.6 或更新版本）
 1. 开启"热重载"后打开一次游戏。之后 "skeletons" 文件夹里会有每个角色的骨架
    （Agatha.glb、Berkeley.glb 等，另外还有 Traitor.glb 和 Victim.glb）。里面只有骨骼，
    由你自己的游戏生成。
 2. 在 Blender 中：文件 > 导入 > glTF 2.0，选择骨架，并删除小网格 "CSR_borra_esta_malla"。
 3. 把你的模型对准骨骼。先选中模型，再选中骨架（Shift+点击），然后按 Ctrl+P > 附带自动权重。
    不要重命名骨骼。
 4. 文件 > 导出 > glTF 2.0 (.glb) 或 FBX，保存到这个文件夹。

新角色（模组 > 模型 > 新角色）
 - 新角色不会总是替换某个人，而是参加每局的抽选：每局从已启用的角色中选出 6 人，原有角色和
   新角色的机会相同。能出场的角色在游戏等候室的"角色选择"按钮里选择（由房主为自己的房间
   决定；至少 6 名）。
 - 需要一个 3D 模型。其他都是可选的：
     名字和台词：没有的话，使用它所顶替的角色的；
     图片：放进 "images" 文件夹；没有的话从模型生成；
     动画：没有自己的动画时，它的动作和"动画来源"中选择的角色一样。
 - 它的玩法总是和它所顶替的角色一样。
 - 类型为"叛徒"的角色暂时还不会在对局中出现。

动画（"animations" 文件夹）
 - 在这里放 .fbx 或 .glb 动画（从 Mixamo 下载时选择 "FBX Binary" 和 "Without Skin"，
   走路和跑步选择 "In Place"）。任何人形动画都可以：会自动适配到角色上。
 - 在 模组 > 模型 > 动画 中，为每个角色选择用哪个动画替换它的待机、走路或跑步。
   游戏的模型和你的模型都可以使用。
 - 使用每个文件中的第一个动画；什么时候播放哪个仍由游戏决定。""",
              """CRIMESIGHT Revival - 自定义光标
===============================

你自己的鼠标光标。最简单的方法是用启动器：模组 > 自定义光标 > "选择图片..."，
然后选择点击位置。你也可以自己把文件放在这里：

  cursor.png     普通光标，用于菜单和对局中。背景透明的 PNG，最好是 32x32 或 64x64 像素。
  hotspot.txt    可选：cursor.png 中点击的位置，从左上角算起的像素 "x,y"
                 （默认 0,0，和箭头一样）。居中的 32x32 准星：16,16
  其他 .png      可选：每个都会替换游戏中同名的光标（移动、跑步、攻击等）。名字可以在
                 BepInEx/LogOutput.log 中 "[Cursor] el juego usa el cursor ..." 这几行里看到。

 - 只有你自己能看到。
 - 需要在 模组 > 常规 中开启"热重载"（BepInEx）。
 - 从启动器打开游戏时生效；如果游戏已经开着，几秒钟内生效。
 - 要恢复游戏的光标，在启动器中按"关闭"，或清空这个文件夹。"""),

    "zh-TW": ("""CRIMESIGHT Revival - 模組
=========================

這是你的模組資料夾。裡面的一切都在啟動器的「模組」視窗中管理。

  stamps\\      你的貼圖圖片
  avatars\\     你的頭像圖片（用作個人資料圖片）
  mod.json     選用：為你的模組顯示的名稱和作者
  models\\      你的 3D 模型和動畫（見裡面的 README.txt）
  cursor\\      你的自訂游標（見裡面的 README.txt）
  stages\\      你在場景編輯器中儲存的場景

貼圖和頭像
 - PNG、JPG、WEBP 等。任何尺寸都可以：會自動調整。
 - 它們會作為新的加入：遊戲內建的貼圖和頭像永遠不會被修改。
 - 在你的房間裡所有人都看得到（在別人的房間裡你看到的是對方的）。
 - 貼圖在對局中不會顯示訊息，除非你用「訊息」按鈕（模組 > 貼圖）幫它設定一則。
   檔名開頭的數字（01_）只用來排序。
 - 變更會在下次從啟動器開啟遊戲時生效；如果在 模組 > 一般 中開啟了「熱重載」（BepInEx），
   會立即生效。""",
              """CRIMESIGHT Revival - 3D 模型
============================

你自己的 3D 模型和動畫。在啟動器的 模組 > 模型 中管理。
需要在 模組 > 一般 中開啟「熱重載」（BepInEx）。

  .fbx / .glb    你的模型；也可以是裝有模型及其貼圖的子資料夾（下載的東西直接解壓縮到這裡很方便）。
                 子資料夾的名稱就是模型的名稱。
  animations\\    你的動畫（見下面的「動畫」）
  images\\        新角色的肖像圖片（見下面的「新角色」）
  skeletons\\     每個角色一個骨架，用於完美貼合（見下文）

模型
 - 在 模組 > 模型 中把模型分配給一個角色，它就會取代那個角色的外觀。
 - 在你的房間裡所有人都看得到（在別人的房間裡你看到的是對方的）。
 - 你的模型會播放遊戲的動畫。
 - 人形模型（Mixamo、VRChat/Unity、VRoid、Blender、3ds Max Biped、DAZ、MMD 等）會自動適配：
   依名稱辨識骨骼，把模型擺正，縮放到角色的大小，並擺成遊戲的 T 字姿勢。頭髮、裙子等額外的
   骨骼會跟隨最近的身體骨骼（不會擺動）。
 - 貼圖：每個材質的顏色貼圖，放在模型檔案裡面或旁邊（PNG、JPG、TGA、BMP、PSD 等）。
 - 每個模型請控制在約 60,000 個三角面以內。
 - 如果遊戲開著，變更會立即生效（重新匯出模型後請按「重新載入」）。
 - 如果看起來不對，BepInEx/LogOutput.log 中以 [Modelos] 開頭的行會顯示辨識了哪些骨骼。

想要完美貼合（選用，Blender 3.6 或更新版本）
 1. 開啟「熱重載」後開啟一次遊戲。之後 "skeletons" 資料夾裡會有每個角色的骨架
    （Agatha.glb、Berkeley.glb 等，另外還有 Traitor.glb 和 Victim.glb）。裡面只有骨骼，
    由你自己的遊戲產生。
 2. 在 Blender 中：檔案 > 匯入 > glTF 2.0，選擇骨架，並刪除小網格 "CSR_borra_esta_malla"。
 3. 把你的模型對準骨骼。先選取模型，再選取骨架（Shift+點擊），然後按 Ctrl+P > 附帶自動權重。
    不要重新命名骨骼。
 4. 檔案 > 匯出 > glTF 2.0 (.glb) 或 FBX，儲存到這個資料夾。

新角色（模組 > 模型 > 新角色）
 - 新角色不會總是取代某個人，而是參加每局的抽選：每局從已啟用的角色中選出 6 人，原有角色和
   新角色的機會相同。能出場的角色在遊戲等候室的「角色選擇」按鈕裡選擇（由房主為自己的房間
   決定；至少 6 名）。
 - 需要一個 3D 模型。其他都是選用的：
     名稱和台詞：沒有的話，使用它所取代的角色的；
     圖片：放進 "images" 資料夾；沒有的話從模型產生；
     動畫：沒有自己的動畫時，它的動作和「動畫來源」中選擇的角色一樣。
 - 它的玩法總是和它所取代的角色一樣。
 - 類型為「叛徒」的角色暫時還不會在對局中出現。

動畫（"animations" 資料夾）
 - 在這裡放 .fbx 或 .glb 動畫（從 Mixamo 下載時選擇 "FBX Binary" 和 "Without Skin"，
   走路和跑步選擇 "In Place"）。任何人形動畫都可以：會自動適配到角色上。
 - 在 模組 > 模型 > 動畫 中，為每個角色選擇用哪個動畫取代它的待機、走路或跑步。
   遊戲的模型和你的模型都可以使用。
 - 使用每個檔案中的第一個動畫；什麼時候播放哪個仍由遊戲決定。""",
              """CRIMESIGHT Revival - 自訂游標
=============================

你自己的滑鼠游標。最簡單的方法是用啟動器：模組 > 自訂游標 > 「選擇圖片...」，
然後選擇點擊位置。你也可以自己把檔案放在這裡：

  cursor.png     一般游標，用於選單和對局中。背景透明的 PNG，最好是 32x32 或 64x64 像素。
  hotspot.txt    選用：cursor.png 中點擊的位置，從左上角算起的像素 "x,y"
                 （預設 0,0，和箭頭一樣）。置中的 32x32 準星：16,16
  其他 .png      選用：每個都會取代遊戲中同名的游標（移動、跑步、攻擊等）。名稱可以在
                 BepInEx/LogOutput.log 中 "[Cursor] el juego usa el cursor ..." 這幾行裡看到。

 - 只有你自己看得到。
 - 需要在 模組 > 一般 中開啟「熱重載」（BepInEx）。
 - 從啟動器開啟遊戲時生效；如果遊戲已經開著，幾秒鐘內生效。
 - 要恢復遊戲的游標，在啟動器中按「關閉」，或清空這個資料夾。"""),
}
for _l, (_mods, _models, _cursor) in _READMES.items():
    S[_l]["mods_readme"] = _mods
    S[_l]["models_readme"] = _models
    S[_l]["cursor_readme"] = _cursor
