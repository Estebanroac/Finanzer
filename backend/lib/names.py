"""V7 (nombres en español): el nombre en español de una industria, un sector o un país de las fuentes (config/names.toml).

La prosa y las fichas de la web y de los PDF usan el nombre en español; el original solo queda en la metodología y en
el anexo («industria de referencia: Computers/Peripherals, Damodaran»). Sin traducción, se devuelve el original (el
análisis nunca se bloquea): tests/test_names.py exige que el universo y el panel estén traducidos, y el guardián
(regla `industria_en_ingles`) detecta un nombre original en la prosa.
"""
import re
from typing import Optional

from settings import cfg

_DASH = re.compile(r"\s*[—–]\s*|\s+-\s+")


def _key(name: str) -> str:
    """Yahoo escribe «Beverages—Non-Alcoholic» o «Beverages - Non-Alcoholic»: la clave usa « - »."""
    return _DASH.sub(" - ", name.strip())


def damodaran(name: Optional[str]) -> Optional[str]:
    """Industria de A. Damodaran («Computers/Peripherals» → «Ordenadores y periféricos»)."""
    if not name:
        return name
    return cfg("names.damodaran").get(name.strip(), name)


def sector(name: Optional[str]) -> Optional[str]:
    """Sector de Yahoo Finance o GICS («Consumer Defensive» → «Consumo defensivo»)."""
    if not name:
        return name
    n = name.strip()
    return cfg("names.yahoo_sectors").get(n) or cfg("names.gics_sectors").get(n) or name


def industry(name: Optional[str]) -> Optional[str]:
    """Industria de Yahoo Finance («Beverages—Non-Alcoholic» → «Bebidas sin alcohol»)."""
    if not name:
        return name
    return cfg("names.yahoo_industries").get(_key(name)) or name


def country(name: Optional[str]) -> Optional[str]:
    """País del emisor de Yahoo Finance («United States» → «Estados Unidos»)."""
    if not name:
        return name
    return cfg("names.countries").get(name.strip()) or name


def translated(kind: str, name: str) -> bool:
    """Si `name` tiene traducción en la tabla `kind` (damodaran, sector, industry o country). Un país puede escribirse
    igual en los dos idiomas («Argentina»): cuenta con estar en la tabla."""
    if kind == "country":
        return (name or "").strip() in cfg("names.countries")
    fn = {"damodaran": damodaran, "sector": sector, "industry": industry, "country": country}[kind]
    return fn(name) != name


def originals():
    """Todos los nombres originales (con « - » y con raya), del más largo al más corto: para el guardián."""
    out = set(cfg("names.damodaran")) | set(cfg("names.yahoo_sectors")) | set(cfg("names.gics_sectors"))
    for k in cfg("names.yahoo_industries"):
        out |= {k, k.replace(" - ", "—")}
    return sorted(out, key=len, reverse=True)


def inline(name: Optional[str]) -> str:
    """El nombre a mitad de frase: «Electrónica de consumo» → «electrónica de consumo»; las siglas se quedan («REIT
    de locales comerciales»)."""
    n = (name or "").strip()
    return n[0].lower() + n[1:] if len(n) > 1 and n[1].islower() else n


def _company_patterns():
    C = cfg("names.company")
    alt = lambda xs: "|".join(map(re.escape, sorted(xs, key=len, reverse=True)))   # noqa: E731
    return (re.compile(C["edgar_state"]),
            re.compile(r",?\s+(?:" + alt(C["suffixes_ci"]) + r")$", re.I),
            re.compile(r",?\s+(?:" + alt(C["suffixes"]) + r")$"),
            re.compile(r",\s*(?:" + alt(C["after_comma"]) + r")$"),
            re.compile(r"\s*\((?:The|Class [ABC])\)$|\s+Class [ABC]$"))


def company(name: Optional[str]) -> Optional[str]:
    """P8: nombre corto de la empresa, sin forma jurídica final («Apple Inc.» → «Apple», «Tesla, Inc.» → «Tesla»,
    «Home Depot (The)» → «Home Depot»); las excepciones de config mandan («The Coca-Cola Company» → «Coca-Cola»).
    Nunca vacío: si la regla se lo comiera todo, el nombre legal."""
    if not name or not name.strip():
        return name
    raw = name.strip()
    exc = cfg("names.company.exceptions")
    if raw in exc:
        return exc[raw]
    state, ci, cs, comma, tail = _company_patterns()
    n = state.sub("", raw).strip()
    while True:
        prev = n
        for rx in (tail, ci, cs, comma):
            n = rx.sub("", n).rstrip(" ,")
        if n == prev:
            break
    return n or raw
