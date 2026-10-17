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
from typing import Any, Dict, List, Optional

from beta import _norm
from settings import cfg

MARKET_ROW = "Total Market (without financials)"


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


def industry(sector: Optional[str], yahoo_industry: Optional[str], country: Optional[str]) -> Optional[Dict[str, Any]]:
    """{values, basis (industria | industria_global | sector), damodaran, firms, region, region_label, source, url,
    as_of} o None si ni la industria ni el sector están en el mapa."""
    reg = region(country)
    I, B = cfg("industries"), cfg("betas")
    ind = B["yahoo_industries"].get(_norm(yahoo_industry))
    if ind:
        row = _row(reg, ind)
        why = _why_not(row)
        if why is None:
            return {**_meta(reg), "values": row["values"], "basis": "industria", "damodaran": ind,
                    "firms": row["firms"]}
        glob = _row("global", ind)
        if _why_not(glob) is None:
            return {**_meta("global"), "values": glob["values"], "basis": "industria_global", "damodaran": ind,
                    "firms": glob["firms"], "home_region": reg, "home_label": I["regions"][reg]["label"],
                    "home_why": why}
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
            "firms": sum(r["firms"] for r in rows)}


def market(country: Optional[str]) -> Dict[str, Any]:
    """El mercado amplio de la región sin financieras (perfil market)."""
    reg = region(country)
    row = _row(reg, MARKET_ROW)
    return {**_meta(reg), "values": row["values"], "basis": "mercado", "damodaran": MARKET_ROW, "firms": row["firms"]}
