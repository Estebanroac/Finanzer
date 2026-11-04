"""
Logotipo de cada empresa, como en los brókers: GET /api/v2/logo/{símbolo} (PNG cuadrado) y, en el análisis, `logo`
({url, source} o null si no hay).

Fuentes, gratuitas y en este orden (medidas el 4-nov-2026; números en archivo-historico/evidencias-de-pruebas/
logos_2026-11-04):
  1. Parqet (`parqet_url`: assets.parqet.com/logos/symbol/<símbolo de Yahoo>, PNG de 200 px, 6,7 KB de media): sin
     clave ni cupo. Universo (S&P 500 + ADR): 530/543 (97,6 %); 100 europeas de Damodaran al azar: 76; BRK-B y BF-B,
     con guion.
  2. Finnhub /stock/profile2 (`logo`), solo si Parqet no lo tiene y el símbolo no lleva sufijo de bolsa: el plan
     gratuito responde 403 fuera de EE. UU. (0/12: MC.PA, SAP.DE, NESN.SW…). De los 13 que faltan en Parqet, 11. Gasta
     cupo (≤ 60/min, compartido con métricas, noticias y rivales): con la pausa de los rivales
     (finnhub_fallback.paced_get), sin esperarla más de `finnhub_wait_s` y como mucho `finnhub_max_per_hour` consultas
     por hora. Su PNG es de 1000 px (15–130 KB): se reduce a `size_px` con Pillow.
  Juntas: 541/543 del universo (99,6 %).

Por el backend y no directo del navegador: el navegador no habla con terceros (ni la IP ni qué empresa mira el usuario
salen de Finanzer); la URL de Finnhub solo se conoce con la clave; lo que llega se comprueba (PNG, tamaño) y una imagen
caída o rara es un 204 (sin contenido; la web pone la placa), nunca una imagen rota; misma procedencia (la CSP no
cambia) y caché del navegador larga (`browser_max_age_s`; con ?v=<versión>, inmutable). Memoria: caché por símbolo con
tope de entradas y de bytes (`cache_max_entries`, `cache_max_bytes`: 300 logotipos de Parqet ocupan ≈ 2 MB); la
ausencia se recuerda `miss_ttl_s` y un fallo de la fuente, `fail_ttl_s`.
Una sola descarga por símbolo aunque lleguen varias peticiones a la vez. FETCH es inyectable (tests y replay).
"""
import hashlib
import io
import logging
import re
import struct
import threading
import time
from typing import Callable, Dict, NamedTuple, Optional, Tuple
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from settings import cfg

logger = logging.getLogger(__name__)

_SYMBOL = re.compile(r"^[A-Z0-9.\-]{1,10}$")     # la misma regla que el resto de /v2 (main._V2_SYMBOL)
_PNG = b"\x89PNG\r\n\x1a\n"
_UA = {"User-Agent": "finanzer/1.0"}


class Logo(NamedTuple):
    data: bytes          # PNG
    version: str         # huella del contenido (va en ?v= y en el ETag)
    source: str          # "Parqet" o "Finnhub"


class SourceError(Exception):
    """La fuente no respondió (red, 5xx): se reintenta pasado `fail_ttl_s`, no se da por ausente."""


def _limits():
    return cfg("data.logos")


def png_size(data: bytes) -> Optional[Tuple[int, int]]:
    """Ancho y alto de un PNG (cabecera IHDR), o None si no lo es."""
    if len(data) < 24 or not data.startswith(_PNG) or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def acceptable(data: Optional[bytes]) -> bool:
    """Un PNG de verdad, cuadrado o casi, ni diminuto ni enorme: lo que no, se trata como sin logotipo."""
    L = _limits()
    if not data or len(data) > L["max_bytes"]:
        return False
    wh = png_size(data)
    if not wh or min(wh) < L["min_px"]:
        return False
    return max(wh) / min(wh) <= L["max_aspect"]


def _download(url: str, max_bytes: int) -> Optional[bytes]:
    """Cuerpo de `url`; None si es un 404 (no lo tiene). Otro fallo: SourceError."""
    try:
        with urlopen(Request(url, headers=_UA), timeout=_limits()["timeout_s"]) as r:
            if getattr(r, "status", 200) != 200:
                raise SourceError(f"HTTP {r.status}")
            return r.read(max_bytes + 1)
    except SourceError:
        raise
    except Exception as e:
        if getattr(e, "code", None) in (403, 404, 410):
            return None
        raise SourceError(type(e).__name__) from None


def _parqet(symbol: str) -> Optional[bytes]:
    L = _limits()
    return _download(L["parqet_url"].format(symbol=quote(symbol, safe=""), size=L["size_px"]), L["max_bytes"])


def _shrink(data: bytes) -> Optional[bytes]:
    """El PNG de Finnhub (1000 px), a `size_px` y optimizado (≈ 1/5 del peso)."""
    from PIL import Image
    n = _limits()["size_px"]
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
        im.thumbnail((n, n), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="PNG", optimize=True)
    return out.getvalue()


_hourly: Dict[str, float] = {"start": 0.0, "count": 0}


def _finnhub_budget() -> bool:
    """Una consulta más de Finnhub para logotipos en la hora en curso (`finnhub_max_per_hour`)."""
    now = time.monotonic()
    with _lock:
        if now - _hourly["start"] >= 3600:
            _hourly.update(start=now, count=0)
        if _hourly["count"] >= _limits()["finnhub_max_per_hour"]:
            return False
        _hourly["count"] += 1
        return True


def _finnhub(symbol: str) -> Optional[bytes]:
    import finnhub_fallback as fh
    L = _limits()
    if not fh.is_enabled() or "." in symbol or not _finnhub_budget():
        return None
    data = fh.paced_get("/stock/profile2", {"symbol": fh.provider_symbol(symbol)}, L["finnhub_min_interval_s"],
                        max_wait_s=L["finnhub_wait_s"])
    if data is fh.BUSY:
        raise SourceError("cupo de Finnhub ocupado")
    url = str((data or {}).get("logo") or "")
    parts = urlsplit(url)
    # solo el almacén de imágenes de Finnhub (nunca una URL cualquiera que viniera en la respuesta)
    if parts.scheme != "https" or not re.fullmatch(L["finnhub_logo_host"], parts.hostname or ""):
        return None
    head, _, name = url.rpartition("/")
    raw = _download(f"{head}/{quote(name)}", L["finnhub_max_bytes"])
    if not raw or len(raw) > L["finnhub_max_bytes"] or not png_size(raw):
        return None
    return _shrink(raw)


def fetch_sources(symbol: str) -> Optional[Tuple[bytes, str]]:
    """(PNG, fuente) de la primera fuente que lo tenga; None si ninguna; SourceError si alguna no respondió y ninguna
    lo dio."""
    failed = None
    for name, fn in (("Parqet", _parqet), ("Finnhub", _finnhub)):
        try:
            data = fn(symbol)
        except SourceError as e:
            failed = failed or f"{name}: {e}"
            continue
        except Exception as e:                      # nunca rompe la petición: se recuerda como fallo
            failed = failed or f"{name}: {type(e).__name__}"
            continue
        if acceptable(data):
            return data, name
    if failed:
        raise SourceError(failed)
    return None


FETCH: Callable[[str], Optional[Tuple[bytes, str]]] = fetch_sources

_lock = threading.Lock()
# símbolo -> (caduca, Logo o None); orden de inserción = antigüedad (se sacan las más viejas)
_cache: Dict[str, Tuple[float, Optional[Logo]]] = {}
_bytes = [0]
_inflight: Dict[str, threading.Event] = {}


def reset() -> None:
    with _lock:
        _cache.clear()
        _inflight.clear()
        _bytes[0] = 0
        _hourly.update(start=0.0, count=0)


def _store(sym: str, logo: Optional[Logo], ttl: float) -> None:
    L = _limits()
    with _lock:
        old = _cache.pop(sym, None)
        if old and old[1]:
            _bytes[0] -= len(old[1].data)
        _cache[sym] = (time.monotonic() + ttl, logo)
        _bytes[0] += len(logo.data) if logo else 0
        while _cache and (len(_cache) > L["cache_max_entries"] or _bytes[0] > L["cache_max_bytes"]):
            _, gone = _cache.pop(next(iter(_cache)))
            _bytes[0] -= len(gone.data) if gone else 0


def _cached(sym: str) -> Tuple[bool, Optional[Logo]]:
    with _lock:
        hit = _cache.get(sym)
    if hit and hit[0] > time.monotonic():
        return True, hit[1]
    return False, None


def valid(symbol: str) -> bool:
    return bool(_SYMBOL.match(symbol or ""))


def _claim(sym: str) -> Tuple[threading.Event, bool]:
    """El aviso de la descarga en curso de `sym` y si la hace quien llama (la primera petición)."""
    with _lock:
        ev = _inflight.get(sym)
        if ev is not None:
            return ev, False
        ev = _inflight[sym] = threading.Event()
        return ev, True


def _resolve(sym: str, ev: threading.Event) -> None:
    L = _limits()
    try:
        try:
            got = FETCH(sym)
        except SourceError as e:
            logger.info(f"[LOGO] {sym}: fuente sin respuesta ({e})")
            _store(sym, None, L["fail_ttl_s"])
            return
        if got:
            data, source = got
            _store(sym, Logo(data, hashlib.sha256(data).hexdigest()[:L["version_chars"]], source), L["ttl_s"])
        else:
            _store(sym, None, L["miss_ttl_s"])
    except Exception as e:                          # nunca deja a nadie esperando: se recuerda como fallo
        logger.warning(f"[LOGO] {sym}: {type(e).__name__}")
        _store(sym, None, L["fail_ttl_s"])
    finally:
        with _lock:
            _inflight.pop(sym, None)
        ev.set()


def get(symbol: str, wait_s: Optional[float] = None, background: bool = False) -> Tuple[bool, Optional[Logo]]:
    """(resuelto, logotipo). Resuelto con None: no hay (o la fuente falló hace poco). Sin resolver: se está
    descargando y no llegó en `wait_s` (None: lo que tarde). `background`: la descarga va en su hilo (quien llama solo
    espera `wait_s`)."""
    sym = str(symbol or "").upper()
    if not valid(sym):
        return True, None
    hit, logo = _cached(sym)
    if hit:
        return True, logo
    ev, owner = _claim(sym)
    if owner:
        if background:
            threading.Thread(target=_resolve, args=(sym, ev), name=f"logo-{sym}", daemon=True).start()
        else:
            _resolve(sym, ev)
    if not ev.wait(wait_s):
        return False, None
    return _cached(sym)


def prefetch(symbol: str) -> None:
    """Descarga el logotipo en su hilo (el análisis lo lanza al empezar y lo recoge con `meta` al terminar)."""
    get(symbol, wait_s=0, background=True)


def url(symbol: str, version: Optional[str] = None) -> str:
    return f"/api/v2/logo/{quote(str(symbol).upper(), safe='.-')}" + (f"?v={version}" if version else "")


def meta(symbol: str) -> Optional[Dict[str, Optional[str]]]:
    """El logotipo en los datos de la acción: {url (con su versión), source}, o None si no hay. Si aún se descarga
    pasado `meta_wait_s`, la URL sin versión y `source` null (la web la pide y, si no hay, pone la placa)."""
    sym = str(symbol or "").upper()
    done, logo = get(sym, wait_s=_limits()["meta_wait_s"], background=True)
    if not done:
        return {"url": url(sym), "source": None}
    return {"url": url(sym, logo.version), "source": logo.source} if logo else None
