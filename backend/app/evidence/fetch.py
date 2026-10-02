"""Fetch the readable text of a public article. News APIs only return headlines and ~200-character snippets; the body is
where the facts are. Safe by construction: http(s) only, public addresses only, size and time limits, no cookies."""
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

MAX_BYTES = 1_500_000
TIMEOUT_S = 5.0
UA = "Mozilla/5.0 (compatible; FakeNewsEvidenceVerifier/0.1; university NLP lab project)"


def is_public_url(url: str) -> bool:
    """Reject non-http(s) URLs and anything resolving to a private/loopback/link-local address (SSRF guard)."""
    try:
        p = urlparse(url)
    except ValueError:
        return False
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return bool(infos)


def extract_text(html: str) -> str:
    import trafilatura

    return (trafilatura.extract(html, include_comments=False, include_tables=False, favor_precision=True) or "").strip()


def fetch_article(url: str, max_chars: int = 6000) -> str:
    """Main text of the page, or '' when it cannot be fetched/parsed (paywall, blocked, not HTML...)."""
    if not is_public_url(url):
        return ""
    try:
        with httpx.stream("GET", url, headers={"User-Agent": UA}, timeout=TIMEOUT_S, follow_redirects=True) as r:
            if r.status_code >= 400 or "html" not in r.headers.get("content-type", "html").lower():
                return ""
            if not is_public_url(str(r.url)):  # a redirect must not lead somewhere private
                return ""
            data = b""
            for chunk in r.iter_bytes():
                data += chunk
                if len(data) > MAX_BYTES:
                    break
            html = data.decode(r.encoding or "utf-8", errors="replace")
    except (httpx.HTTPError, OSError):
        return ""
    return extract_text(html)[:max_chars]
