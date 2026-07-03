"""
Per-client rate limiting for the public API.

There is no auth, so "a user" is identified by client IP. The app runs behind
Caddy, so request.client.host is the proxy, not the visitor. Caddy appends the
real client->Caddy address as the LAST entry of X-Forwarded-For, so with a
single trusted proxy that last hop is the most reliable client identity.
(The leftmost XFF entry is client-supplied and therefore spoofable.)

In-memory storage is fine for a single web container. To run multiple web
replicas, point `storage_uri` at Redis (e.g. "redis://redis:6379") so counters
are shared.

Limits are applied explicitly per-route via @limiter.limit(...). We intentionally
do NOT set default_limits, since slowapi would then try to enforce them on every
route (including ones without a `request` parameter, like index/chunks) and fail
at request time.
"""
from slowapi import Limiter
from starlette.requests import Request


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # last hop = address Caddy saw the connection come from
        return xff.split(",")[-1].strip()
    return request.client.host if request.client else "anonymous"


limiter = Limiter(key_func=client_ip)
