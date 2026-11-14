"""
Apertura automatica de puertos en el router (UPnP IGD), sin dependencias.

Solo se usa en "Ser anfitrion": pide al router que reenvie el puerto del servidor a este PC
para que los amigos puedan entrar. Si el router no tiene UPnP, no pasa nada: se explica como
abrirlo a mano o usar una red privada (Tailscale, ZeroTier, Radmin VPN).
"""
import re, socket, urllib.request
from urllib.parse import urljoin

SSDP_ADDR = ("239.255.255.250", 1900)
SERVICES = ("urn:schemas-upnp-org:service:WANIPConnection:1",
            "urn:schemas-upnp-org:service:WANIPConnection:2",
            "urn:schemas-upnp-org:service:WANPPPConnection:1")


def _discover(timeout=3.0):
    msg = ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\n"
           "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n\r\n").encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.settimeout(timeout)
    locations = []
    try:
        s.sendto(msg, SSDP_ADDR)
        while True:
            data, _ = s.recvfrom(4096)
            m = re.search(rb"(?im)^location:\s*(\S+)", data)
            if m and m.group(1).decode() not in locations:
                locations.append(m.group(1).decode())
    except OSError:
        pass
    finally:
        s.close()
    return locations


def _control(location):
    xml = urllib.request.urlopen(location, timeout=4).read().decode("utf-8", "replace")
    base = re.search(r"<URLBase>\s*(\S+?)\s*</URLBase>", xml)
    base = base.group(1) if base else location
    for svc in SERVICES:
        block = re.search(r"<service>(?:(?!</service>).)*?" + re.escape(svc) + r"(?:(?!</service>).)*?</service>",
                          xml, re.S)
        if block:
            ctrl = re.search(r"<controlURL>\s*(\S+?)\s*</controlURL>", block.group(0))
            if ctrl:
                return urljoin(base, ctrl.group(1)), svc
    return None


def _soap(url, svc, action, args):
    body = "".join(f"<{k}>{v}</{k}>" for k, v in args.items())
    env = (f'<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
           f's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
           f'<u:{action} xmlns:u="{svc}">{body}</u:{action}></s:Body></s:Envelope>').encode()
    req = urllib.request.Request(url, env, {"Content-Type": 'text/xml; charset="utf-8"',
                                            "SOAPAction": f'"{svc}#{action}"'})
    return urllib.request.urlopen(req, timeout=5).read().decode("utf-8", "replace")


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class PortMapping:
    def __init__(self, port, description="CRIMESIGHT Revival"):
        self.port, self.description = port, description
        self.ctrl = None
        self.external_ip = None

    def open(self):
        """Devuelve True si el router acepto el reenvio."""
        for loc in _discover():
            try:
                found = _control(loc)
                if not found:
                    continue
                url, svc = found
                _soap(url, svc, "AddPortMapping", {
                    "NewRemoteHost": "", "NewExternalPort": self.port, "NewProtocol": "TCP",
                    "NewInternalPort": self.port, "NewInternalClient": local_ip(), "NewEnabled": 1,
                    "NewPortMappingDescription": self.description, "NewLeaseDuration": 0})
                self.ctrl = (url, svc)
                try:
                    r = _soap(url, svc, "GetExternalIPAddress", {})
                    m = re.search(r"<NewExternalIPAddress>\s*([\d.]+)\s*<", r)
                    self.external_ip = m.group(1) if m else None
                except OSError:
                    pass
                return True
            except OSError:
                continue
        return False

    def close(self):
        if not self.ctrl:
            return
        url, svc = self.ctrl
        try:
            _soap(url, svc, "DeletePortMapping", {"NewRemoteHost": "", "NewExternalPort": self.port,
                                                  "NewProtocol": "TCP"})
        except OSError:
            pass
        self.ctrl = None
