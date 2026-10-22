"""Client address for throttling, trusting X-Forwarded-For only from the proxy.

``X-Forwarded-For`` is honoured only when ``REMOTE_ADDR`` belongs to
``settings.TRUSTED_PROXY_HOSTS`` (IPs, CIDRs or hostnames; default ``proxy``,
the Compose service). Hostnames are resolved and cached for
``_RESOLVE_TTL_SECONDS``; an unresolvable name trusts nothing. Any other
caller (e.g. the web container reaching ``api:8000`` directly) is identified by
``REMOTE_ADDR`` and cannot choose its throttle key.
"""

import ipaddress
import socket
import time

from django.conf import settings
from django.http import HttpRequest

Network = ipaddress.IPv4Network | ipaddress.IPv6Network

_RESOLVE_TTL_SECONDS = 60.0
_cache: dict[tuple[str, ...], tuple[float, tuple[Network, ...]]] = {}


def _resolve(entry: str) -> list[Network]:
    try:
        return [ipaddress.ip_network(entry, strict=False)]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(entry, None, proto=socket.IPPROTO_TCP)
    except OSError:
        return []
    return [ipaddress.ip_network(str(info[4][0])) for info in infos]


def trusted_proxy_networks() -> tuple[Network, ...]:
    hosts = tuple(settings.TRUSTED_PROXY_HOSTS)
    now = time.monotonic()
    cached = _cache.get(hosts)
    if cached is not None and now - cached[0] < _RESOLVE_TTL_SECONDS:
        return cached[1]
    networks = tuple(net for entry in hosts for net in _resolve(entry))
    _cache[hosts] = (now, networks)
    return networks


def _parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def client_ip(request: HttpRequest) -> str:
    remote = str(request.META.get("REMOTE_ADDR", ""))
    remote_ip = _parse_ip(remote)
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if remote_ip is None or not isinstance(forwarded, str) or not forwarded.strip():
        return remote
    if not any(remote_ip in net for net in trusted_proxy_networks()):
        return remote
    # Caddy (no trusted_proxies configured) replaces inbound XFF with the peer
    # address, so the last entry is the client it saw.
    last = _parse_ip(forwarded.split(",")[-1])
    return str(last) if last is not None else remote
