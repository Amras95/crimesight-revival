"""
CRIMESIGHT Revival - conexiones HTTPS fiables en cualquier PC.

El Python del lanzador usa el almacen de certificados de Windows, y en algunos PCs le faltan
certificados raiz (Windows los descarga solo cuando los necesita un programa suyo, no el nuestro).
Eso hace fallar descargas como la de BepInEx con "CERTIFICATE_VERIFY_FAILED". Aqui se anaden
tambien los certificados de certifi (los mismos que usa Firefox/Mozilla) para todas las descargas.
"""
import ssl, urllib.request

_done = False


def context():
    ctx = ssl.create_default_context()          # almacen del sistema
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:  # noqa: BLE001 - sin certifi, solo el del sistema
        pass
    return ctx


def install():
    """Hace que todos los urllib.request.urlopen del lanzador usen ese contexto."""
    global _done
    if not _done:
        urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=context())))
        _done = True
