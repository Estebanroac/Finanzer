"""V6 (revisión de código y seguridad del PM): defensas de la capa HTTP de main.py, como middleware ASGI puro.

- BodyLimit (B5): un cuerpo de más de `max_body_bytes` ([server]) se responde con 413 sin leer el resto: por la
  cabecera Content-Length si viene y, si no (chunked), leyendo como mucho ese tamaño antes de pasarlo a la app.
- SecurityHeaders (hallazgo F23 del frontend, que va en el backend): en cada respuesta, la política de contenido
  (`[server] csp`, con `frame-ancestors 'none'`), `X-Content-Type-Options: nosniff` y `Referrer-Policy`. En el HTML,
  `script-src` lleva además el sha256 de cada script en línea del propio documento: el script de tema del layout de
  /v2 y los que exporta Next (la carga de la página en la web actual y en /v2); nada más se ejecuta en línea.
- Compress (V4, encargo del PM): GZipMiddleware de Starlette para la API y los estáticos de /v2 y /, a partir de
  `gzip_minimum_bytes` y con `gzip_level` (5: casi la compresión del 9 por un quinto de CPU). Los PDF
  (`gzip_exclude_paths`) van tal cual: ya vienen comprimidos. Va por fuera de SecurityHeaders: la CSP calcula los
  hashes sobre el HTML sin comprimir.
"""
import base64
import hashlib
import json
import re
from typing import Any, Callable, Dict, List


async def _send_json(send: Callable, status: int, detail: str) -> None:
    body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8"),
                            (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


class BodyLimit:
    def __init__(self, app: Any, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        detail = f"cuerpo de más de {self.max_bytes // 1024} KB"
        length = dict(scope.get("headers") or []).get(b"content-length")
        if length is not None:
            try:
                too_big = int(length) > self.max_bytes
            except ValueError:
                return await _send_json(send, 400, "Content-Length no válido")
            if too_big:
                return await _send_json(send, 413, detail)
            return await self.app(scope, receive, send)
        if scope.get("method") in ("GET", "HEAD", "OPTIONS"):
            return await self.app(scope, receive, send)
        # Sin Content-Length (chunked): se lee el cuerpo aquí, como mucho `max_bytes`, y se le pasa entero a la app.
        chunks, seen = [], 0
        while True:
            msg = await receive()
            if msg["type"] != "http.request":
                return
            chunk = msg.get("body") or b""
            seen += len(chunk)
            if seen > self.max_bytes:
                return await _send_json(send, 413, detail)
            chunks.append(chunk)
            if not msg.get("more_body"):
                break
        body, sent = b"".join(chunks), [False]

        async def replay():
            if not sent[0]:
                sent[0] = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()
        await self.app(scope, replay, send)


_INLINE_SCRIPT = re.compile(rb"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)
_SRC_ATTR = re.compile(rb"\bsrc\s*=", re.I)
_TYPE_ATTR = re.compile(rb"""\btype\s*=\s*["']?([^"' >]+)""", re.I)
_JS_TYPES = {b"", b"text/javascript", b"application/javascript", b"module"}


def inline_script_hashes(html: bytes) -> List[str]:
    """'sha256-…' de cada script en línea ejecutable del documento (sin `src`, de tipo JavaScript), en orden y sin
    repetir."""
    out: List[str] = []
    for m in _INLINE_SCRIPT.finditer(html):
        attrs = m.group("attrs")
        t = _TYPE_ATTR.search(attrs)
        if _SRC_ATTR.search(attrs) or (t and t.group(1).lower() not in _JS_TYPES):
            continue
        h = "'sha256-" + base64.b64encode(hashlib.sha256(m.group("body")).digest()).decode() + "'"
        if h not in out:
            out.append(h)
    return out


def csp(directives: List[str], script_hashes: List[str]) -> str:
    """La política con los hashes añadidos a `script-src`."""
    out = []
    for d in directives:
        if script_hashes and d.split(" ", 1)[0] == "script-src":
            d = " ".join([d] + script_hashes)
        out.append(d)
    return "; ".join(out)


class SecurityHeaders:
    def __init__(self, app: Any, directives: List[str], referrer_policy: str):
        self.app = app
        self.directives = list(directives)
        self.referrer = referrer_policy.encode()

    def _headers(self, headers: List, hashes: List[str]) -> List:
        drop = {b"content-security-policy", b"x-content-type-options", b"referrer-policy"}
        out = [(k, v) for k, v in headers if k.lower() not in drop]
        out += [(b"content-security-policy", csp(self.directives, hashes).encode()),
                (b"x-content-type-options", b"nosniff"), (b"referrer-policy", self.referrer)]
        return out

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        start: Dict[str, Any] = {}
        chunks: List[bytes] = []

        async def wrapped(msg):
            if msg["type"] == "http.response.start":
                ctype = dict(msg.get("headers") or []).get(b"content-type", b"")
                if ctype.lower().startswith(b"text/html") and scope.get("method") != "HEAD":
                    start.update(msg)               # el HTML se retiene hasta tener el cuerpo: sus hashes van en la cabecera
                    return
                await send({**msg, "headers": self._headers(list(msg.get("headers") or []), [])})
                return
            if msg["type"] == "http.response.body" and start:
                chunks.append(msg.get("body") or b"")
                if msg.get("more_body"):
                    return
                body = b"".join(chunks)
                await send({**start, "headers": self._headers(list(start.get("headers") or []),
                                                              inline_script_hashes(body))})
                await send({"type": "http.response.body", "body": body, "more_body": False})
                return
            await send(msg)

        await self.app(scope, receive, wrapped)


class Compress:
    def __init__(self, app: Any, minimum_size: int, level: int, exclude_paths: List[str]):
        from starlette.middleware.gzip import GZipMiddleware
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=minimum_size, compresslevel=level)
        self.exclude = tuple(exclude_paths)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not str(scope.get("path") or "").startswith(self.exclude):
            return await self.gzip(scope, receive, send)
        return await self.app(scope, receive, send)
