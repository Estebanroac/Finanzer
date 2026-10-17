"""
Fase 4/7 (F4_PARADA §5; permiso del usuario del 2026-10-17): referencia de la empresa por industria y región, de los
conjuntos de datos de A. Damodaran (config/industries.toml, generado por tools/damodaran_import.py).

  · región: la del país del emisor (sectors.benchmarks.regions); fuera de las listas, la tabla global;
  · industria: la de Damodaran que corresponde a la de Yahoo (betas.yahoo_industries, el mismo mapa que la beta del
    sector). Si la fila de su región no es representativa (menos de `min_firms` empresas, o dominada por pocas de
    múltiplo extremo: sectors.benchmarks.industry), la misma industria a escala global;
  · sin industria en el mapa: media de las industrias de su sector (betas.yahoo_sectors) ponderada por número de
    empresas, como la beta del sector;
  · el mercado amplio de la región (perfil market): "Total Market (without financials)".

Las cifras son agregados de la industria (la definición de cada una, en la cabecera de la herramienta), no medianas.
"""
import math
import gzip
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from beta import _norm
from settings import cfg

MARKET_ROW = "Total Market (without financials)"
FIRMS_FILE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config",
                                           "damodaran_firms.tsv.gz"))
BROAD_GROUPS = {"United States": "us", "Developed Europe": "europe", "Japan": "japan", "Emerging Markets": "emerging",
                "Australia, NZ and Canada": "global"}
_LEGAL = re.compile(r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|sa|s a|nv|n v|ag|as|a s|asa|"
                    r"se|spa|s p a|ab|oyj|holding|holdings|group|the|de|cv|sab|kk|tbk|bhd|berhad|pcl|llc|lp)\b")


def norm_name(name: Optional[str]) -> str:
    """Nombre legal sin la forma jurídica ni la puntuación: "TAIWAN SEMICONDUCTOR MANUFACTURING CO LTD" y "Taiwan
    Semiconductor Manufacturing Company Limited (TWSE:2330)" -> "taiwan semiconductor manufacturing"."""
    s = re.sub(r"\([^)]*\)", " ", str(name or "")).lower()
    s = re.sub(r"[^a-z0-9& ]+", " ", s.replace("/", " "))
    s = _LEGAL.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


_firms: Dict[str, Any] = {}
_firms_lock = threading.Lock()


def _load_firms() -> Dict[str, Dict[str, Tuple[str, str]]]:
    """{"symbol": {símbolo de Yahoo: (industria, región)}, "name": {"nombre|país": (industria, región)}} del archivo
    generado por tools/damodaran_import.py (se lee una vez por proceso)."""
    with _firms_lock:
        if not _firms:
            sym, names = {}, {}
            if os.path.isfile(FIRMS_FILE):
                with gzip.open(FIRMS_FILE, "rt", encoding="utf-8") as fh:
                    for line in fh:
                        if line.startswith("#"):
                            continue
                        kind, key, ind, reg = line.rstrip("\n").split("\t")
                        (sym if kind == "S" else names)[key] = (ind, reg)
            _firms.update(symbol=sym, name=names)
        return _firms


def firm(symbol: Optional[str], title: Optional[str] = None,
         country: Optional[str] = None) -> Optional[Dict[str, str]]:
    """La clasificación de la propia empresa en Damodaran ("Companies in each industry"): por su símbolo (la otra clase
    de acciones si solo figura una: BRK-B -> BRK.A) o, para un ADR, por el nombre legal de EDGAR y el país (un
    emparejamiento exacto y único). None si no figura."""
    F = _load_firms()
    s = str(symbol or "").upper()
    hit = F["symbol"].get(s)
    m = re.fullmatch(r"(.+)-([A-Z])", s)
    if hit is None and m:
        hit = next((F["symbol"][f"{m.group(1)}-{c}"] for c in "ABC" if f"{m.group(1)}-{c}" in F["symbol"]), None)
    if hit is not None:
        return {"industry": hit[0], "region": hit[1], "how": "símbolo"}
    if title and country and country != "United States":
        hit = F["name"].get(f"{norm_name(title)}|{country}")
        if hit is not None:
            return {"industry": hit[0], "region": hit[1], "how": "nombre legal (ADR)"}
    return None


def region(country: Optional[str]) -> str:
    for key, countries in cfg("sectors.benchmarks.regions").items():
        if str(country or "") in countries:
            return key
    return "global"


def _row(reg: str, industry: str) -> Optional[Dict[str, Any]]:
    I = cfg("industries")
    vals = (I["regions"][reg]["industries"]).get(industry)
    if vals is None:
        return None
    cols = I["columns"]
    out = {c: float(v) for c, v in zip(cols, vals) if c != "firms" and math.isfinite(float(v))}
    avg = out.pop("pe_avg", None)            # solo para la prueba de dominio: no es una referencia
    return {"firms": int(vals[0]), "values": out, "pe_avg": avg}


def _why_not(row: Optional[Dict[str, Any]]) -> Optional[str]:
    """Por qué la fila no es representativa (None si lo es)."""
    P = cfg("sectors.benchmarks.industry")
    if not row or row["firms"] < P["min_firms"]:
        return f"{row['firms'] if row else 0} empresas"
    pe, avg = row["values"].get("pe"), row.get("pe_avg")
    if pe and avg and pe >= P["dominance_ratio"] * avg:
        return (f"dominada por pocas empresas de múltiplo extremo: P/E agregado {pe:.1f}x frente a {avg:.1f}x de "
                "media")
    return None


def _meta(reg: str) -> Dict[str, Any]:
    I = cfg("industries")
    return {"region": reg, "region_label": I["regions"][reg]["label"], "source": I["source"], "url": I["url"],
            "as_of": I["as_of"]}


def industry(sector: Optional[str], yahoo_industry: Optional[str], country: Optional[str],
             symbol: Optional[str] = None, title: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """{values, basis (industria | industria_global | sector), damodaran, firms, region, region_label, source, url,
    as_of, classified} o None si ni la empresa, ni su industria, ni su sector están en las tablas. `classified`: cómo
    se eligió la industria (la clasificación de la propia empresa en Damodaran, o el mapa de la industria de Yahoo)."""
    reg = region(country)
    I, B = cfg("industries"), cfg("betas")
    f = firm(symbol, title, country)
    if f is not None and f["industry"] in I["regions"][f["region"]]["industries"]:
        ind, reg = f["industry"], f["region"]
        classified = f"Damodaran clasifica a la empresa en esa industria ({f['how']})"
    else:
        ind = B["yahoo_industries"].get(_norm(yahoo_industry))
        classified = "industria de Yahoo, por el mapa a las de Damodaran"
    if ind:
        row = _row(reg, ind)
        why = _why_not(row)
        if why is None:
            return {**_meta(reg), "values": row["values"], "basis": "industria", "damodaran": ind,
                    "firms": row["firms"], "classified": classified}
        glob = _row("global", ind)
        if _why_not(glob) is None:
            return {**_meta("global"), "values": glob["values"], "basis": "industria_global", "damodaran": ind,
                    "firms": glob["firms"], "home_region": reg, "home_label": I["regions"][reg]["label"],
                    "home_why": why, "classified": classified}
    group: List[str] = list(B["yahoo_sectors"].get(str(sector or "")) or [])
    rows = [r for r in (_row(reg, g) for g in group) if r and r["firms"] > 0]
    if not rows:
        return None
    values: Dict[str, float] = {}
    for c in I["columns"][1:]:
        pts = [(r["firms"], r["values"][c]) for r in rows if c in r["values"]]
        n = sum(w for w, _ in pts)
        if n:
            values[c] = sum(w * v for w, v in pts) / n
    return {**_meta(reg), "values": values, "basis": "sector", "damodaran": group,
            "firms": sum(r["firms"] for r in rows), "classified": "sector de Yahoo (su industria no está en el mapa)"}


def market(country: Optional[str]) -> Dict[str, Any]:
    """El mercado amplio de la región sin financieras (perfil market)."""
    reg = region(country)
    row = _row(reg, MARKET_ROW)
    return {**_meta(reg), "values": row["values"], "basis": "mercado", "damodaran": MARKET_ROW, "firms": row["firms"]}
