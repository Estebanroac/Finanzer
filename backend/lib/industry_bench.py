"""
Fase 4/7 (F4_PARADA §5; permiso del usuario del 2026-10-17): referencia de la empresa por industria y región, de los
conjuntos de datos de A. Damodaran (config/industries.toml, generado por tools/damodaran_import.py).

  · región: la del país del emisor (sectors.benchmarks.regions); fuera de las listas, la tabla global;
  · industria: la de Damodaran que corresponde a la de Yahoo (betas.yahoo_industries, el mismo mapa que la beta del
    sector). Si la fila de su región no es representativa (menos de `min_firms` empresas, o dominada por pocas de
    múltiplo extremo: sectors.benchmarks.industry), la misma industria a escala global;
  · sin industria en el mapa: media de las industrias de su sector (betas.yahoo_sectors) ponderada por número de
    empresas, como la beta del sector;
  · el mercado amplio de la región (perfil market): "Total Market (without financials)";
  · F10 · N2: sin la propia empresa (lib/self_exclusion.py): el agregado menos ella, con sus cifras a la fecha del
    conjunto, o la mediana de los pares del universo si no hay cifras o lo que queda no es representativo; declarado.

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


def lenient_name(name: Optional[str]) -> str:
    """Nombre legal más tolerante que norm_name: sin los sufijos de EDGAR (/ON/, /UK) ni letras sueltas ("BP p.l.c." de
    Damodaran -> "bp", como "BP PLC" de EDGAR; "ARM HOLDINGS PLC /UK" -> "arm")."""
    base = norm_name(re.sub(r"/[A-Z]{1,3}/?", " ", str(name or "")))
    return " ".join(w for w in base.split() if len(w) > 1)


def country_key(country: Optional[str]) -> str:
    """País como lo escribe Damodaran: EDGAR da a veces la provincia delante ("Ontario, Canada" -> "Canada")."""
    return str(country or "").split(",")[-1].strip()


_firms: Dict[str, Any] = {}
_firms_lock = threading.Lock()
_lenient: Dict[Tuple[str, str], Tuple[str, str]] = {}


def _lenient_index() -> Dict[Tuple[str, str], Tuple[str, str]]:
    """{(nombre tolerante, país): (industria, región)}: solo los emparejamientos ÚNICOS (dos empresas de Damodaran con
    el mismo nombre tolerante en el mismo país y distinta clasificación no emparejan: sería una conjetura)."""
    F = _load_firms()
    with _firms_lock:
        if not _lenient:
            seen: Dict[Tuple[str, str], Tuple[str, str]] = {}
            dup = set()
            for key, val in F["name"].items():
                name, _, country = key.rpartition("|")
                k = (lenient_name(name), country)
                if k in seen and seen[k] != val:
                    dup.add(k)
                seen.setdefault(k, val)
            _lenient.update({k: v for k, v in seen.items() if k not in dup and k[0]})
        return _lenient


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
    if title and country and country_key(country) != "United States":
        hit = F["name"].get(f"{norm_name(title)}|{country}") or F["name"].get(f"{norm_name(title)}|{country_key(country)}")
        if hit is not None:
            return {"industry": hit[0], "region": hit[1], "how": "nombre legal (ADR)"}
        # Rediseño E2b (aprobado por el PM): nombre tolerante, solo si el emparejamiento es único (BP: "BP PLC" de
        # EDGAR y "BP p.l.c." de Damodaran).
        hit = _lenient_index().get((lenient_name(title), country_key(country)))
        if hit is not None:
            return {"industry": hit[0], "region": hit[1], "how": "nombre legal tolerante (ADR)"}
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


def _pct(w: float) -> str:
    return f"el {w * 100:.0f} %" if w >= 0.005 else "menos del 1 %"


def _self(values: Dict[str, float], reg: str, ind: str, firms: int, symbol: Optional[str], title: Optional[str],
          country: Optional[str], company: Optional[Dict[str, Any]], name: Optional[str],
          member: Optional[bool] = None) -> Dict[str, Any]:
    """F10 · N2: {values, self_exclusion} de la fila (reg, ind) sin la propia empresa. `member`: si Damodaran la cuenta
    en ese agregado (por defecto, si la clasifica en esa industria y región; la global las incluye todas)."""
    import self_exclusion as SE
    I, P = cfg("industries"), cfg("sectors.benchmarks.industry")
    who = name or symbol or "la empresa"
    if member is None:
        f = firm(symbol, title, country)
        member = f is not None and f["industry"] == ind and reg in (f["region"], "global")
    if not member:
        return {"values": values, "self_exclusion": {
            "method": "no_figura", "weight": None,
            "declaration": f"la referencia no incluye a {who}: Damodaran no la cuenta en este agregado",
            "reason": "Damodaran no clasifica a la empresa en esta industria y región"}}
    dollars = dict(zip(I["dollar_columns"], I["regions"][reg]["dollars"].get(ind) or ()))
    fig = company or {"status": "sin_dato", "reason": "sin cifras de la empresa"}
    det: Dict[str, Any] = {"date": I["dollar_as_of"], "source": I["dollar_source"], "cut": fig.get("cut"),
                           "figures": fig.get("values"), "session": fig.get("session"),
                           # F10 (PM, 29-oct): cifras de la caché tras un tiempo agotado de EDGAR, dicho
                           **({"cache_note": fig["cache_note"]} if fig.get("from_cache") else {})}
    weight = None
    why = few = None
    if fig.get("status") != "ok":
        import numfmt
        why = f"sin sus cifras al {numfmt.date_long(I['dollar_as_of'])}: {fig.get('reason')}"
    elif not dollars.get("mcap"):
        why = "sin los totales de la industria en el conjunto de Damodaran"
    else:
        wo = SE.without(values, dollars, fig)
        weight = wo["weight"]
        if weight is not None and weight >= P["self_max_weight"]:
            why = (f"la industria de Damodaran es casi solo {who} ({weight * 100:.0f} % de la capitalización): sin "
                   "ella quedan restos")
        elif firms - 1 < P["min_firms"]:
            why = few = f"sin {who} quedan {firms - 1} empresas (menos de {P['min_firms']})"
    if why is None:
        cols = wo["columns"]
        out = dict(wo["values"])
        gaps = [c for c, d in cols.items() if d["how"] == "sin_dato"]
        if gaps:
            pm = SE.peer_median(ind, symbol, gaps)
            for c in gaps:
                cols[c].update(pm["columns"][c])
                if pm["columns"][c]["after"] is not None:
                    out[c] = pm["columns"][c]["after"]
            det["peers_date"] = pm["date"]
        return {"values": out, "self_exclusion": {
            **det, "method": "sin_empresa", "weight": weight, "columns": cols,
            "declaration": f"referencia de la industria sin {who}, que pesa {_pct(weight)}"}}
    pm = SE.peer_median(ind, symbol, [c for c in values if c in SE.PARTS])
    out = {c: v for c, v in values.items() if c not in SE.PARTS}
    out.update(pm["values"])
    cols = {c: {"before": values[c], **pm["columns"][c]} for c in values if c in SE.PARTS}
    # F10 (PM, 29-oct): si es por un tiempo agotado de EDGAR (no por la empresa), la referencia está DEGRADADA y lo dice
    # (la fila, la nota y la confianza), nunca un respaldo silencioso.
    deg = bool(fig.get("degraded"))
    return {"values": out, "self_exclusion": {
        **det, "method": "mediana_pares", "weight": weight, "columns": cols, "n_peers": pm["n_peers"],
        "peers_date": pm["date"], "reason": why, "few_firms": few, "degraded": deg,
        "declaration": (f"referencia degradada: mediana de {pm['n_peers']} pares del universo; {why}" if deg else
                        f"referencia: mediana de {pm['n_peers']} pares del universo; {why}")}}


def _meta(reg: str) -> Dict[str, Any]:
    I = cfg("industries")
    return {"region": reg, "region_label": I["regions"][reg]["label"], "source": I["source"], "url": I["url"],
            "as_of": I["as_of"]}


def industry(sector: Optional[str], yahoo_industry: Optional[str], country: Optional[str],
             symbol: Optional[str] = None, title: Optional[str] = None, company: Optional[Dict[str, Any]] = None,
             name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """{values, basis (industria | industria_global | sector), damodaran, firms, region, region_label, source, url,
    as_of, classified} o None si ni la empresa, ni su industria, ni su sector están en las tablas. `classified`: cómo
    se eligió la industria (la clasificación de la propia empresa en Damodaran, o el mapa de la industria de Yahoo)."""
    reg = region(country)
    I, B = cfg("industries"), cfg("betas")
    f = firm(symbol, title, country)
    mapped = B["yahoo_industries"].get(_norm(yahoo_industry))
    if f is not None and f["industry"] in I["regions"][f["region"]]["industries"]:
        ind, reg = f["industry"], f["region"]
        classified = f"Damodaran clasifica a la empresa en esa industria ({f['how']})"
        # F9 · R3: la del perfil (la de la cabecera) es otra industria de Damodaran: el informe lo dice (NU: «Bancos
        # regionales» en la cabecera y «Grandes bancos» en la referencia, sin explicar el cruce).
        profile_differs = bool(yahoo_industry) and mapped != ind
    else:
        ind, profile_differs = mapped, False
        classified = "industria de Yahoo, por el mapa a las de Damodaran"
    if ind:
        row = _row(reg, ind)
        why = _why_not(row)
        glob = _row("global", ind)
        if why is None:
            se = _self(row["values"], reg, ind, row["firms"], symbol, title, country, company, name)
            # F10 · N2: sin la empresa la fila de su región no llega a `min_firms`: como cualquier fila con pocas
            # empresas, la misma industria a escala global (sin ella); si tampoco sirve, la mediana de los pares
            few = se["self_exclusion"].get("few_firms")
            if not (few and reg != "global" and _why_not(glob) is None):
                return {**_meta(reg), **se, "published": row["values"], "basis": "industria", "damodaran": ind,
                        "firms": row["firms"], "classified": classified, "profile_differs": profile_differs}
            seg = _self(glob["values"], "global", ind, glob["firms"], symbol, title, country, company, name)
            if seg["self_exclusion"]["method"] == "sin_empresa":
                return {**_meta("global"), **seg, "published": glob["values"], "basis": "industria_global",
                        "damodaran": ind, "firms": glob["firms"], "home_region": reg,
                        "home_label": I["regions"][reg]["label"], "home_why": few, "classified": classified,
                        "profile_differs": profile_differs}
            return {**_meta(reg), **se, "published": row["values"], "basis": "industria", "damodaran": ind,
                    "firms": row["firms"], "classified": classified, "profile_differs": profile_differs}
        if _why_not(glob) is None:
            se = _self(glob["values"], "global", ind, glob["firms"], symbol, title, country, company, name)
            return {**_meta("global"), **se, "published": glob["values"], "basis": "industria_global",
                    "damodaran": ind, "firms": glob["firms"], "home_region": reg,
                    "home_label": I["regions"][reg]["label"], "home_why": why, "classified": classified,
                    "profile_differs": profile_differs}
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
            "firms": sum(r["firms"] for r in rows), "classified": "sector de Yahoo (su industria no está en el mapa)",
            "self_exclusion": {"method": "no_figura", "weight": None,
                               "declaration": "la referencia es la media de las industrias de su sector, donde "
                                              "Damodaran no clasifica a la empresa",
                               "reason": "Damodaran no clasifica a la empresa en ninguna de esas industrias"}}


def market(country: Optional[str], symbol: Optional[str] = None, title: Optional[str] = None,
           company: Optional[Dict[str, Any]] = None, name: Optional[str] = None) -> Dict[str, Any]:
    """El mercado amplio de la región sin financieras (perfil market). F10 · N2: sin la propia empresa si Damodaran la
    cuenta en él (está en la región y no es una financiera)."""
    reg = region(country)
    row = _row(reg, MARKET_ROW)
    out = {**_meta(reg), "values": row["values"], "published": row["values"], "basis": "mercado",
           "damodaran": MARKET_ROW, "firms": row["firms"]}
    f = firm(symbol, title, country)
    if f is not None and reg in (f["region"], "global") and f["industry"] not in cfg("betas.yahoo_sectors").get(
            "Financial Services", ()):
        out.update(_self(row["values"], reg, MARKET_ROW, row["firms"], symbol, title, country, company, name,
                         member=True))
    else:
        out["self_exclusion"] = {"method": "no_figura", "weight": None,
                                 "declaration": "la referencia no incluye a la empresa: Damodaran no la cuenta en el "
                                                "mercado sin financieras de su región",
                                 "reason": "financiera, de otra región o sin clasificar en Damodaran"}
    return out


def global_roe(industry_name: Optional[str], symbol: Optional[str] = None, title: Optional[str] = None,
               country: Optional[str] = None, company: Optional[Dict[str, Any]] = None,
               name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """F10 · N2b (decisión del PM): el ROE estable del P/B en dos etapas converge a la industria GLOBAL sin la empresa
    (la convergencia a largo plazo no es regional; un resto regional pequeño no representa nada: CB, 18 aseguradoras
    europeas con un ROE del 30 %). {value, basis, text} o None (sin industria de Damodaran, o sin ROE global)."""
    if not isinstance(industry_name, str):
        return None
    glob = _row("global", industry_name)
    if not glob or "roe" not in glob["values"]:
        return None
    se = _self(glob["values"], "global", industry_name, glob["firms"], symbol, title, country, company, name)
    x = se["self_exclusion"]
    roe = se["values"].get("roe")
    if roe is None:
        return None
    from names import damodaran as _es
    where = f"«{_es(industry_name)}» global"
    if x["method"] == "sin_empresa":
        text = f"industria {where} sin la empresa, que pesa {_pct(x['weight'])}"
    elif x["method"] == "mediana_pares":
        text = f"mediana de {x.get('n_peers')} pares del universo de la industria {where}"
    else:
        text = f"industria {where}"
    return {"value": roe, "basis": x["method"], "text": text}
