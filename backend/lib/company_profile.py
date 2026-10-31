"""Rediseño E2a: ficha legible de la empresa (capítulo 1) desde EDGAR submissions. Solo datos, sin lecturas."""
from typing import Any, Dict, Optional

from numfmt import MESES
from settings import cfg

SOURCE = "SEC EDGAR (submissions del emisor)"


def _fye(mmdd: Optional[str]) -> Optional[str]:
    """Cierre del ejercicio de EDGAR ("0926") → "26 de septiembre"."""
    if not mmdd or len(mmdd) != 4 or not mmdd.isdigit() or not 1 <= int(mmdd[:2]) <= 12:
        return None
    return f"{int(mmdd[2:])} de {MESES[int(mmdd[:2]) - 1]}"


def _title(s: Optional[str]) -> Optional[str]:
    return " ".join(w.capitalize() for w in s.split()) if s else None


def _state(v: Optional[str]) -> Optional[str]:
    """Un estado o territorio de EE. UU. en código de EDGAR ("DE") con su nombre ("Delaware"); lo demás, tal cual."""
    if v and len(v) == 2 and v.isalpha() and v.isupper():
        return (cfg("market.us_states") or {}).get(v, v)
    return v


def _category(raw: Optional[str]) -> Optional[str]:
    """La categoría de la SEC puede venir combinada ("Non-accelerated filer<br>Smaller reporting company")."""
    if not raw:
        return None
    cats = cfg("market.filer_categories") or {}
    parts = [p.strip() for p in raw.split("<br>") if p.strip()]
    return " · ".join(cats.get(p.lower(), p) for p in parts) or None


def build(ed_profile: Optional[Dict[str, Any]], profile: Dict[str, Any], edgar_status: Optional[str] = None,
          edgar_reason: Optional[str] = None) -> Dict[str, Any]:
    if not ed_profile:
        reason = ("el emisor no presenta en la SEC: sin ficha oficial" if edgar_status in (None, "sin_cik")
                  # Verificación de la v4 (V3): el motivo de EDGAR ya se explica solo ("sin User-Agent…", "no respondió a
                  # tiempo…"); antes se anteponía siempre "EDGAR no respondió:", también cuando estaba desactivado.
                  else edgar_reason or f"EDGAR no respondió ({edgar_status})")
        return {"status": "sin_dato", "rows": [], "source": SOURCE, "reason": reason}
    p = ed_profile
    city, region = _title(p.get("city")), _state(p.get("state_or_country"))
    if city and region and region.lower() in city.lower():   # EDGAR a veces repite el país en la ciudad (Toyota: "JAPAN")
        region = None
    hq = ", ".join(x for x in (city, region) if x) or None
    sic = " · ".join(x for x in (p.get("sic"), p.get("sic_description")) if x) or None
    cand = [("sic", "Industria (código SIC)", sic), ("hq", "Sede", hq),
            ("incorporation", "Constituida en", _state(p.get("state_of_incorporation"))),
            ("fiscal_year_end", "Cierre del ejercicio", _fye(p.get("fiscal_year_end"))),
            ("category", "Tipo de emisor", _category(p.get("category"))),
            ("website", "Web", p.get("website"))]
    rows = [{"key": k, "label": lab, "value": v} for k, lab, v in cand if v]
    return {"status": "ok" if rows else "sin_dato", "rows": rows, "source": SOURCE,
            "reason": None if rows else "EDGAR no trae la ficha del emisor"}
