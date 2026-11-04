"""Process-wide denial of non-loopback socket traffic, installed before app import.

Defense in depth for trusted application code, not a sandbox for malicious code.
The parser retains its separate, stricter subprocess network prohibition.
"""

import ipaddress
import socket


def allowed(address):
    if not isinstance(address, tuple):
        return False
    try:
        return ipaddress.ip_address(address[0]).is_loopback
    except ValueError:
        return False


def install():
    if getattr(socket, "_portfolio_guard", False):
        return
    socket._portfolio_guard = True
    for name in ("connect", "connect_ex", "sendto"):
        original = getattr(socket.socket, name)

        def guarded(self, *args, _original=original, _name=name):
            address = args[-1] if _name == "sendto" else args[0]
            if not allowed(address):
                raise OSError("Portfolio demo blocks outbound network")
            return _original(self, *args)

        setattr(socket.socket, name, guarded)
    original_dns = socket.getaddrinfo

    def local_dns(host, *args, **kwargs):
        if host is not None and not allowed((host, 0)):
            raise OSError("Portfolio demo blocks external DNS")
        return original_dns(host, *args, **kwargs)

    socket.getaddrinfo = local_dns
    for name in ("gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
        original = getattr(socket, name)

        def local_host(host, _original=original):
            if not allowed((host, 0)):
                raise OSError("Portfolio demo blocks external DNS")
            return _original(host)

        setattr(socket, name, local_host)
