# The version is written by GitHub Actions when building each release ("dev" = not built).
VERSION = "dev"
# Repository the launcher downloads its updates from.
REPO = "Amras95/crimesight-revival"
# Release file matching this system (Windows or Linux / Steam Deck).
ASSET = "CrimeSightRevival.exe" if __import__("os").name == "nt" else "CrimeSightRevival-linux"
