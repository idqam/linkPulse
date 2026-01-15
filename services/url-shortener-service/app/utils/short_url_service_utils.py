import ipaddress
import socket
from pydantic import HttpUrl
import validators
import secrets
import string

from urllib.parse import urlparse, urlunparse

DEFAULT_SCHEME = "https"
BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase


def normalize_url(raw_url: str) -> str:
    if not raw_url or not raw_url.strip():
        raise ValueError("Empty URL")

    raw_url = raw_url.strip()

    if "://" not in raw_url:
        raw_url = f"{DEFAULT_SCHEME}://{raw_url}"

    parsed = urlparse(raw_url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if (scheme == "http" and netloc.endswith(":80")) or \
       (scheme == "https" and netloc.endswith(":443")):
        netloc = netloc.rsplit(":", 1)[0]

    return urlunparse((
        scheme,
        netloc,
        parsed.path or "/",
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))


def validate_syntax(url: str) -> None:
    if not validators.url(url):
        raise ValueError("Invalid URL format")


def validate_dns_and_ip(url: str) -> None:
    hostname = urlparse(url).hostname
    if not hostname:
        raise ValueError("Missing hostname")

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError("Hostname does not resolve")

    for _, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])

        if (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_multicast or
            ip.is_reserved
        ):
            raise ValueError("Disallowed IP address")


def prepare_url(raw_url: HttpUrl | str | None) -> str:
    normalized = normalize_url(str(raw_url))
    validate_syntax(normalized)
    validate_dns_and_ip(normalized)
    return normalized


def generate_short_code(length: int | None = None) -> str:
    if length is None:
        length = secrets.choice(range(6, 9))

    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))
