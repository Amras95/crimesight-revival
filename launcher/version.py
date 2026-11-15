# La version la escribe GitHub Actions al compilar cada release ("dev" = sin compilar).
VERSION = "dev"
# Repositorio del que el lanzador descarga sus actualizaciones.
REPO = "Amras95/crimesight-revival"
# Archivo de la release que corresponde a este sistema (Windows o Linux / Steam Deck).
ASSET = "CrimeSightRevival.exe" if __import__("os").name == "nt" else "CrimeSightRevival-linux"
