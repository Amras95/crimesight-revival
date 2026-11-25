"""
CRIMESIGHT Revival - reliable HTTPS connections on any PC.

The launcher's Python uses the Windows certificate store, and on some PCs it is missing
root certificates (Windows downloads them only when one of its own programs needs them, not ours).
That makes downloads like BepInEx's fail with "CERTIFICATE_VERIFY_FAILED". Here certifi's
certificates (the same Firefox/Mozilla uses) are added too, for every download.
"""
import ssl, urllib.request

_done = False


def context():
    ctx = ssl.create_default_context()          # system store
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:  # noqa: BLE001 - without certifi, only the system one
        pass
    return ctx


def install():
    """Makes every urllib.request.urlopen in the launcher use that context."""
    global _done
    if not _done:
        urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=context())))
        _done = True
