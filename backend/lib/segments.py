"""
Rediseño E2b (Task 2; spec §4, dato 3): ingresos por segmento con historia, de la instancia XBRL del último informe
anual (10-K, 20-F o 40-F) presentado en la SEC.

  · Filing: el último anual con XBRL del emisor (o de su predecesor: XOM, `data.edgar.predecessors`). La lista
    `recent` de submissions trae los últimos ~1000 filings; si no hay un anual en ella, se miran las páginas antiguas.
  · Ejes (`market.segments`): el primero utilizable de `axes` es el principal; el geográfico, `secondary`; el resto
    de ejes utilizables, `others` (Apple: segmentos geográficos de gestión, países y productos).
  · Un miembro que es la suma de otros del mismo eje (Product = iPhone + Mac + iPad + Wearables) es un agregado y sale.
  · Conciliación: suma de los segmentos del último ejercicio frente al ingreso consolidado del mismo periodo (el mismo
    concepto sin dimensión). Si no concilia (eliminaciones entre segmentos, partidas corporativas) se publica igual con
    `reconciles: false` y `gap_pct` = suma / total − 1: nunca se esconde.

Endpoint perezoso (/api/v2/segments): fuera del camino del análisis, con su propio presupuesto de tiempo
(`segments_budget_s`) y su caché por número de filing (`segments_ttl_s`, como mucho `segments_cache_max`). La SEC se
consulta con el ritmo y el User-Agent de lib/sec_edgar.py. Una instancia mayor que `max_instance_mb` (BCS: 47 MB) no se
descarga (memoria de Render): sin_dato con el motivo. `FETCHER` inyectable (tests y replay).
"""
import datetime as _dt
import logging
import re
import tempfile
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple
from xml.etree.ElementTree import ParseError

import bounded
import sec_edgar as edgar
from settings import cfg

logger = logging.getLogger(__name__)

FETCHER: Optional[Callable[[str, float], Tuple[Optional[bytes], int]]] = None    # None: el de sec_edgar
SUBMISSIONS_PAGE_URL = "https://data.sec.gov/submissions/{name}"
AXIS_LABELS = {"StatementBusinessSegmentsAxis": "segmentos de negocio", "SegmentsAxis": "segmentos de negocio",
               "ProductOrServiceAxis": "productos y servicios", "ProductsAndServicesAxis": "productos y servicios",
               "StatementGeographicalAxis": "zonas geográficas", "GeographicalAreasAxis": "zonas geográficas"}
NO_SEC = "no presenta estados en la SEC"
# v4 (PM): en lenguaje claro, sin «XBRL», «instancia», «miembros» ni «conciliar»
NO_DIMS = "el informe anual (10-K) no desglosa los ingresos por segmento en un formato que se pueda leer automáticamente"

_cache: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()     # accn -> (hora, resultado)
_lock = threading.Lock()


def reset() -> None:
    with _lock:
        _cache.clear()
        _by_symbol.clear()
        _gate.clear()
        for rec in _pre.values():
            if rec["done"].is_set():
                _drop(rec)
        _pre.clear()


def _empty(reason: str, **extra) -> Dict[str, Any]:
    out = {"status": "sin_dato", "fiscal_years": [], "axis": None, "axis_label": None, "concept": None,
           "concept_label": None, "coverage": None, "covers_total": False, "coverage_source": None,
           "coverage_note": None,
           "segments": [], "total_reported": {}, "reconciles": False, "gap_pct": None, "notes": [], "secondary": None,
           "others": [], "dropped_axes": [], "currency": None, "source": None, "reason": reason}
    out.update(extra)
    return out


# ───────────────────────── el último informe anual ─────────────────────────

def _cik(symbol: str, budget: edgar.Budget) -> Optional[int]:
    if FETCHER is None:                    # producción: la tabla de tickers compartida con el análisis
        hit = edgar.cik_for(symbol, budget)
        return hit["cik"] if hit else None
    table = edgar._get_json(edgar.TICKERS_URL, budget, FETCHER) or {}
    key = symbol.upper().replace(".", "-")
    return next((int(v["cik_str"]) for v in table.values() if str(v.get("ticker")).upper() == key), None)


_annual_in = edgar.annual_xbrl


def _annual_order(f: Dict[str, Any]):
    """El ejercicio más reciente (fecha del periodo; sin ella, la de presentación) y, dentro de él, el informe original
    antes que su enmienda. V2 (fuentes reales): CRCL presentó su 10-K de 2025 en marzo y un 10-K/A (solo la Parte III,
    sin estados) en julio; el /A ganaba por fecha y los segmentos salían «el 10-K/A no desglosa ingresos»."""
    return (f.get("reportDate") or f["filingDate"], not f["form"].endswith("/A"), f["filingDate"], f["accessionNumber"])


def last_annual(cik: int, budget: edgar.Budget) -> Optional[Dict[str, Any]]:
    """El anual con XBRL más reciente del CIK: primero en `recent`; si no está, en las páginas antiguas. En producción,
    `recent` sale de sec_edgar.submissions, la misma respuesta (y caché) que el análisis (rendimiento v4f8: antes se
    descargaba y leía otra vez)."""
    def make():
        if FETCHER is None:
            sub = edgar.submissions(cik, budget)
            found, pages = sub["annual_xbrl"], sub["older_pages"]
        else:
            raw = edgar._get_json(edgar.SUBMISSIONS_URL.format(cik=cik), budget, FETCHER) or {}
            found = _annual_in((raw.get("filings") or {}).get("recent") or {})
            pages = [p["name"] for p in (raw.get("filings") or {}).get("files") or []]
        for name in [] if found else pages:
            found = _annual_in(edgar._get_json(SUBMISSIONS_PAGE_URL.format(name=name), budget, FETCHER) or {})
            if found:
                break
        return max(found, key=_annual_order) if found else None
    if FETCHER is not None:
        return make()
    return edgar._cached(f"segann:{cik}", cfg("data.edgar.submissions_ttl_s"), make, budget)


# ───────────────────────── cálculo sobre los hechos ─────────────────────────

def _days(period: str) -> int:
    a, b = period.split("/")
    return (_dt.date.fromisoformat(b) - _dt.date.fromisoformat(a)).days


def _annual_periods(periods) -> Dict[str, str]:
    """{FY: periodo} de los periodos de ~1 año; FY = año del fin. Dos periodos del mismo FY: el más largo."""
    out: Dict[str, str] = {}
    for p in periods:
        if _days(p) >= cfg("market.segments.min_period_days"):
            fy = p.split("/")[1][:4]
            if fy not in out or _days(p) > _days(out[fy]):
                out[fy] = p
    return out


def _aggregates(vals: Dict[str, float], tol: float) -> set:
    """Miembros cuyo valor es la suma de dos o más de los demás (a `tol` relativa)."""
    flagged = set()
    for m, target in vals.items():
        others = [v for k, v in vals.items() if k != m and v <= target * (1 + tol)]
        if len(others) < 2 or target <= 0:
            continue
        unit = target * tol / 4                           # resolución: el margen de la tolerancia en 4 unidades
        lo, hi = round(target * (1 - tol) / unit), round(target * (1 + tol) / unit)
        ge1, ge2 = 0, 0                                     # bitsets de sumas con ≥ 1 y ≥ 2 sumandos
        for v in others:
            w = round(v / unit)
            ge2 |= (ge2 << w) | (ge1 << w)
            ge1 |= (ge1 << w) | (1 << w)
            ge2 &= (1 << (hi + 1)) - 1
            ge1 &= (1 << (hi + 1)) - 1
        if ge2 >> lo:
            flagged.add(m)
    return flagged


def _axis_view(axis: str, by_concept: Dict[str, Dict[str, Dict[str, float]]], totals: Dict[str, Dict[str, float]],
               names: Dict[str, str], concepts: Optional[Tuple[str, ...]] = None) -> Optional[Dict[str, Any]]:
    """El eje con el primer concepto (por prioridad) que concilia; si ninguno concilia, el primero con ≥ 2
    segmentos. None si el eje no tiene dos segmentos en el último ejercicio."""
    S = cfg("market.segments")
    concepts = concepts or tuple(S["revenue_concepts"])
    first = None
    for concept in concepts:
        members = by_concept.get(concept)
        if not members:
            continue
        fys = _annual_periods({p for vals in members.values() for p in vals})
        if not fys:
            continue
        last = max(fys)
        lastp = fys[last]
        cur = {m: v[lastp] for m, v in members.items() if v.get(lastp, 0) > 0}
        keep = set(cur) - _aggregates(cur, S["aggregate_tolerance"])
        if len(keep) < 2:
            continue
        tot_series = totals.get(concept) or next((totals[c] for c in concepts
                                                  if lastp in (totals.get(c) or {})), {})
        total = {fy: tot_series[p] for fy, p in sorted(fys.items()) if p in tot_series}
        notes: List[str] = []
        if total.get(last) and sum(cur[m] for m in keep) > total[last] * (1 + S["reconcile_tolerance"]):
            part = _partition({m: cur[m] for m in keep}, total[last], names)
            if part is None:
                notes.append("Algunos segmentos se solapan y ninguna combinación suma los ingresos de la empresa: se muestran "
                             "tal como los publica.")
            else:
                left_out = sorted(keep - part, key=lambda m: -cur[m])
                keep = part
                # el código solo sabe que juntos suman más que el total, no por qué: «suele pasar», no lo afirma
                notes.append("Algunos segmentos se solapan: juntos suman más que los ingresos de la empresa (suele pasar "
                             "cuando uno vende a otros de la propia empresa). Se muestran los que suman el total; queda "
                             "fuera " + ", ".join(_clean_label(names.get(m) or _humanize(m)) for m in left_out) + ".")
        ssum = sum(cur[m] for m in keep)
        gap = ssum / total[last] - 1 if total.get(last) else None
        segs = [{"member": m, "label": _clean_label(names.get(m) or _humanize(m)),
                 "values": {fy: members[m][p] for fy, p in sorted(fys.items()) if p in members[m]},
                 "share_last": cur[m] / ssum} for m in keep]
        segs.sort(key=lambda s: (-cur[s["member"]], s["member"]))
        view = {"axis": axis, "axis_label": AXIS_LABELS.get(axis, axis), "concept": concept,
                "fiscal_years": sorted(fys), "segments": segs, "total_reported": total,
                "reconciles": gap is not None and abs(gap) <= S["reconcile_tolerance"], "gap_pct": gap,
                "period_end": lastp.split("/")[1], "period": lastp, "notes": notes}
        if view["reconciles"]:
            return view
        first = first or view
    return first


def _norm_label(label: str) -> str:
    return " ".join(re.sub(r"\b(revenues?|sales|net|total)\b", " ", re.sub(r"[^a-z0-9]+", " ", label.lower())).split())


def _near_duplicates(members, names: Dict[str, str]) -> int:
    """Pares de miembros con la misma etiqueta salvo palabras como "revenue" ("Software and Services" y "Software And
    Services Revenue")."""
    labs = [_norm_label(_clean_label(names.get(m) or _humanize(m))) for m in members]
    return sum(1 for i in range(len(labs)) for j in range(i + 1, len(labs)) if labs[i] == labs[j])


def _partition(cur: Dict[str, float], total: float, names: Dict[str, str]) -> Optional[set]:
    """El subconjunto de miembros cuya suma concilia con el total: el de más miembros; a igualdad, el de menos
    etiquetas casi duplicadas y después el de menor diferencia. None si ninguno (o si hay demasiados miembros)."""
    import itertools
    S = cfg("market.segments")
    ms = sorted(cur)
    if len(ms) > S["max_subset_members"]:
        return None
    best, best_key = None, None
    for k in range(len(ms), 1, -1):
        for combo in itertools.combinations(ms, k):
            gap = abs(sum(cur[m] for m in combo) / total - 1)
            if gap <= S["reconcile_tolerance"]:
                key = (_near_duplicates(combo, names), gap)
                if best_key is None or key < best_key:
                    best, best_key = set(combo), key
        if best is not None:
            return best
    return None


def _collapse(by_concept: Dict[str, Dict[str, Dict[str, Dict[str, float]]]]) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Segmento × zona -> segmento: la suma de las zonas de cada periodo (sin las zonas que son agregado de otras)."""
    tol = cfg("market.segments.aggregate_tolerance")
    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for concept, members in by_concept.items():
        for m, periods in members.items():
            for p, zones in periods.items():
                agg = _aggregates(zones, tol) if all(v > 0 for v in zones.values()) else set()
                out.setdefault(concept, {}).setdefault(m, {})[p] = sum(v for z, v in zones.items() if z not in agg)
    return out


def _net(base: Dict[str, Dict[str, Dict[str, float]]], elims: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """El ingreso de cada segmento neto de sus eliminaciones entre segmentos (sin zona, o la suma de las zonas)."""
    out, hit = {}, False
    for concept, members in base.items():
        for m, periods in members.items():
            for p, v in periods.items():
                e = ((elims.get(concept) or {}).get(m) or {}).get(p)
                if e:
                    hit = True
                    v = v + (e[""] if "" in e else sum(e.values()))
                out.setdefault(concept, {}).setdefault(m, {})[p] = v
    return out if hit else None


def _best_view(axis: str, parsed: Dict[str, Any], names: Dict[str, str],
               concepts: Optional[Tuple[str, ...]] = None) -> Optional[Dict[str, Any]]:
    """Por orden: el eje tal cual; neto de eliminaciones; la suma de zonas (segmento × geografía); y esa suma neta.
    La primera vista que concilia; si ninguna, la primera que haya."""
    direct = parsed["axes"].get(axis) or {}
    by_geo = _collapse(parsed.get("by_geo", {}).get(axis) or {})
    elims = parsed.get("elims", {}).get(axis) or {}
    cands = []
    for base, notes in ((direct, []), (by_geo, ["suma de las zonas geográficas de cada segmento"])):
        if base:
            cands.append((base, notes))
            net = _net(base, elims)
            if net is not None:
                cands.append((net, notes + ["neto de las ventas entre segmentos (ingresos de clientes externos)"]))
    first = None
    for base, notes in cands:
        v = _axis_view(axis, base, parsed["totals"], names, concepts)
        if v:
            v["notes"] = notes + v["notes"]
            if v["reconciles"]:
                return v
            first = first or v
    return first


_LABEL_CUTS = (re.compile(r"\s+(operating\s+|reportable\s+)?segments?$", re.I),
               re.compile(r"^products?\s+and\s+services?\s*,\s*", re.I),
               re.compile(r"^segments?\s+(?=\S)", re.I))      # V2: «Segment Life» (CB) -> «Life»


def _clean_label(label: str) -> str:
    """"Americas Segment" -> "Americas"; "Segment Life" -> "Life"; "Product and Service, Retail" -> "Retail";
    "UNITED STATES" -> "United States"."""
    out = label
    for rx in _LABEL_CUTS:
        out = rx.sub("", out).strip()
    return _uncaps(out or label)


def _uncaps(label: str) -> str:
    """Una etiqueta toda en mayúsculas (algunos emisores la publican así en el XBRL) pasa a mayúscula inicial por
    palabra; las siglas de `upper_words` se conservan y las palabras de enlace de `lower_words` van en minúscula
    (salvo la primera). Una etiqueta con minúsculas no se toca."""
    if not any(ch.isalpha() for ch in label) or label != label.upper():
        return label
    S = cfg("market.segments")
    keep = {w.upper() for w in S["upper_words"]}
    low = {w.lower() for w in S["lower_words"]}

    words = label.split()
    if len(words) == 1 and len(re.sub(r"[^A-Z0-9]", "", label)) <= S["acronym_max_len"]:
        return label        # una sola palabra corta en mayúsculas es una sigla del emisor (FPL, NEER)

    def part(p: str) -> str:
        return p if re.sub(r"[^A-Z0-9]", "", p) in keep else p[:1] + p[1:].lower()

    def word(w: str, first: bool) -> str:
        if not first and re.sub(r"[^A-Z0-9]", "", w).lower() in low:
            return w.lower()
        return "-".join(part(p) for p in w.split("-"))
    return " ".join(word(w, i == 0) for i, w in enumerate(words))


def _humanize(qname: str) -> str:
    local = re.sub(r"Member$", "", qname.split(":")[-1])
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", local).strip() or qname


def compute(parsed: Dict[str, Any], names: Dict[str, str],
            concepts: Optional[Tuple[str, ...]] = None) -> Optional[Dict[str, Any]]:
    """Principal, secundario (geográfico) y otros ejes desde la salida de sec_edgar.parse_segments, con los conceptos
    de `concepts` (por defecto, `revenue_concepts`)."""
    S = cfg("market.segments")
    views, dropped = {}, []
    for axis in list(S["axes"]) + list(S["geographic_axes"]):
        v = _best_view(axis, parsed, names, concepts)
        if not v:
            continue
        top = max(v["segments"], key=lambda x: x["share_last"])
        if top["share_last"] > S["max_single_share"]:
            dropped.append({"axis": axis, "axis_label": v["axis_label"],
                            "reason": f"«{top['label']}» es el {top['share_last']:.1%} del total: son componentes del "
                                      "ingreso, no segmentos"})
            continue
        views[axis] = v
    if not views:
        return {"main": None, "dropped_axes": dropped} if dropped else None
    order = [a for a in S["axes"] if a in views]
    geo = [a for a in S["geographic_axes"] if a in views]
    main = views[(order or geo)[0]]
    secondary = views[geo[0]] if order and geo else None
    rest = [views[a] for a in order[1:] + geo[1:]]
    # Un eje con exactamente los mismos miembros que otro ya mostrado (IFRS y US GAAP a la vez) no se repite.
    shown = [{s["member"] for s in main["segments"]}] + ([{s["member"] for s in secondary["segments"]}]
                                                          if secondary else [])
    others = []
    for v in rest:
        ms = {s["member"] for s in v["segments"]}
        if ms not in shown:
            shown.append(ms)
            others.append(_public(v))
    return {"main": main, "secondary": _public(secondary) if secondary else None, "others": others,
            "dropped_axes": dropped, "currency": parsed["units"].get(main["concept"])}


def _public(v: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v[k] for k in ("axis", "axis_label", "concept", "segments", "reconciles", "gap_pct", "notes")}


# ───────────────────────── cobertura frente a los ingresos consolidados ─────────────────────────

def _consolidated(period: str, seg_sum: float, parsed: Dict[str, Any], cik: int,
                  budget: edgar.Budget) -> Optional[Dict[str, Any]]:
    """Ingresos consolidados del emisor en `period` (ver `market.segments`): total estándar de la instancia, total propio
    del emisor no menor que los segmentos, o `revenue` de companyfacts."""
    S = cfg("market.segments")
    for c in S["total_revenue_concepts"]:
        v = (parsed["totals"].get(c) or {}).get(period)
        if v and v > 0:
            return {"value": v, "concept": c, "from": "instancia"}
    for c in S["extension_total_concepts"]:
        v = ((parsed.get("ext_totals") or {}).get(c) or {}).get(period)
        if v and v >= seg_sum * (1 - S["reconcile_tolerance"]):
            return {"value": v, "concept": c, "from": "instancia (concepto propio del emisor)"}
    try:
        if FETCHER is None:
            facts = edgar.company_facts(cik, budget)
        else:
            facts = edgar.reduce_facts(edgar._get_json(edgar.FACTS_URL.format(cik=cik), budget, FETCHER))
        r = edgar.field_value(facts, "revenue", _dt.date.fromisoformat(period.split("/")[1]),
                              cfg("data.edgar.report_date_tolerance_days"))
    except edgar.Unavailable:
        return None
    if not r or not r.get("value") or r["value"] <= 0:
        return None
    return {"value": r["value"], "concept": r["concept"].split(":")[-1], "from": "companyfacts"}


def _coverage(m: Dict[str, Any], parsed: Dict[str, Any], cik: int, budget: edgar.Budget) -> Dict[str, Any]:
    """concept_label, coverage (segmentos del último ejercicio / ingresos consolidados), covers_total, coverage_source
    y coverage_note (la frase para el lector cuando no los cubren)."""
    S = cfg("market.segments")
    last = m["fiscal_years"][-1]
    seg_sum = sum(s["values"].get(last, 0.0) for s in m["segments"])
    period = m["period"]
    tot = _consolidated(period, seg_sum, parsed, cik, budget)
    cov = seg_sum / tot["value"] if tot else None
    covers = cov is not None and abs(cov - 1) <= S["reconcile_tolerance"]
    labels = S["concept_labels"] if covers or cov is None else {**S["concept_labels"], **S["partial_concept_labels"]}
    label = labels.get(m["concept"], m["concept"])
    if cov is None:
        note = "sin ingresos consolidados con los que comparar"
    elif covers:
        note = None
    else:
        note = f"{label} · cubren el {cov:.0%} de los ingresos consolidados"
    return {"concept_label": label, "coverage": cov, "covers_total": covers,
            "coverage_source": ({"concept": tot["concept"], "from": tot["from"], "value": tot["value"]} if tot
                                else None), "coverage_note": note}


# ───────────────────────── el endpoint ─────────────────────────

def _instance_and_labels(items: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """La instancia (`*_htm.xml`, con su tamaño) y el nombre del linkbase de etiquetas (`*_lab.xml`) del índice."""
    inst = next((i for i in items if str(i.get("name", "")).endswith("_htm.xml")), None)
    lab = next((i["name"] for i in items if str(i.get("name", "")).endswith("_lab.xml")), None)
    return inst, lab


def _download_instance(cik: int, acc: str, inst: Dict[str, Any], budget: edgar.Budget, tmp) -> None:
    edgar._get_to_file(edgar.ARCHIVE_URL.format(cik=cik, acc=acc, name=inst["name"]), budget, tmp, FETCHER,
                       max_bytes=int(cfg("market.segments.max_instance_mb") * (1 << 20)))


# ───────────────────────── descarga anticipada (rendimiento v4f8) ─────────────────────────
# accn -> {"t", "done" (Event), "items", "tmp" (archivo temporal con la instancia, o None), "lab" (bytes o None)}
_pre: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_pre_pool: List[Any] = []


def _drop(rec: Dict[str, Any]) -> None:
    if rec.get("tmp") is not None:
        rec["tmp"].close()
        rec["tmp"] = None


def _expire_prefetched() -> None:
    """Con `_lock`: fuera las descargas terminadas que nadie tomó en `prefetch_ttl_s` y las que pasan de `prefetch_max`
    (la más antigua primero)."""
    S = cfg("market.segments")
    now = time.time()
    for k in [k for k, r in _pre.items() if r["done"].is_set() and now - r["t"] > S["prefetch_ttl_s"]]:
        _drop(_pre.pop(k))
    for k in [k for k, r in _pre.items() if r["done"].is_set()][:max(0, len(_pre) - S["prefetch_max"])]:
        _drop(_pre.pop(k))


def _take_prefetched(accn: str, budget: edgar.Budget) -> Optional[Dict[str, Any]]:
    """La descarga anticipada de `accn` (esperando, dentro del presupuesto, a la que está en marcha), o None: entonces
    _from_filing descarga como siempre. Quien la toma cierra su archivo."""
    with _lock:
        rec = _pre.get(accn)
    if rec is None or not rec["done"].wait(max(budget.left(), 0.0)):
        return None
    with _lock:
        if _pre.get(accn) is not rec:
            return None
        del _pre[accn]
    return rec if rec.get("items") is not None else None


def _prefetch_run(sym: str, rec: Dict[str, Any], cik: int, filing: Dict[str, Any], budget: edgar.Budget) -> None:
    S = cfg("market.segments")
    acc = filing["accessionNumber"].replace("-", "")
    tmp = None
    try:
        idx = edgar._get_json(edgar.ARCHIVE_URL.format(cik=cik, acc=acc, name="index.json"), budget, FETCHER)
        items = ((idx or {}).get("directory") or {}).get("item") or []
        inst, lab = _instance_and_labels(items)
        if inst is not None and int(inst.get("size") or 0) / (1024 * 1024) <= S["max_instance_mb"]:
            tmp = tempfile.TemporaryFile(suffix=".xml")
            _download_instance(cik, acc, inst, budget, tmp)
            if lab:
                try:
                    rec["lab"] = edgar._get(edgar.ARCHIVE_URL.format(cik=cik, acc=acc, name=lab), budget, FETCHER)
                except edgar.Unavailable:       # las etiquetas, en su sitio (_from_filing las vuelve a pedir)
                    pass
        rec["tmp"], tmp = tmp, None
        rec["items"] = items
    except Exception as e:  # noqa: BLE001 — sin descarga anticipada: _from_filing descarga como siempre
        logger.info("[SEGMENTS] %s: descarga anticipada: %s: %s", sym, type(e).__name__, e)
    finally:
        if tmp is not None:
            tmp.close()
        rec["t"] = time.time()
        rec["done"].set()


def _prefetch(sym: str) -> None:
    if not edgar.user_agent() and FETCHER is None:
        return
    budget = edgar.Budget(cfg("market.segments.segments_budget_s"))
    try:
        cik = _cik(sym, budget)
        filing, owner = None, cik
        for c in ((cik,) + edgar._predecessors(sym)) if cik is not None else ():
            f = last_annual(c, budget)
            if f and (filing is None or f["filingDate"] > filing["filingDate"]):
                filing, owner = f, c
    except edgar.Unavailable:
        return
    if filing is None:
        return
    accn = filing["accessionNumber"]
    now = time.time()
    ttl = cfg("market.segments.segments_ttl_s")
    with _lock:
        if any((h := _cache.get(accn + sfx)) and now - h[0] < ttl for sfx in ("", "|primas")) or accn in _pre:
            return                                      # ya leído (o descargándose): nada que adelantar
        _expire_prefetched()
        rec = {"t": now, "done": threading.Event(), "items": None, "tmp": None, "lab": None}
        _pre[accn] = rec
    _prefetch_run(sym, rec, owner, filing, budget)


def prefetch(symbol: str) -> None:
    """Rendimiento (v4f8): descarga en segundo plano el último informe anual de `symbol` (ver `prefetch_ttl_s` en
    config/market.toml). Nunca lanza ni espera."""
    from concurrent.futures import ThreadPoolExecutor
    sym = symbol.upper().strip()
    with _lock:
        if not _pre_pool:
            _pre_pool.append(ThreadPoolExecutor(max_workers=cfg("market.segments.prefetch_concurrency"),
                                                thread_name_prefix="segments_pre"))
        pool = _pre_pool[0]
    pool.submit(_prefetch_safe, sym)


def _prefetch_safe(sym: str) -> None:
    try:
        _prefetch(sym)
    except Exception as e:  # noqa: BLE001 — un caso no previsto: sin descarga anticipada
        logger.warning("[SEGMENTS] %s: descarga anticipada: %s: %s", sym, type(e).__name__, e)


def _from_filing(cik: int, filing: Dict[str, Any], budget: edgar.Budget, insurer: bool = False) -> Dict[str, Any]:
    S = cfg("market.segments")
    premiums = tuple(S["premium_concepts"]) if insurer else ()
    acc = filing["accessionNumber"].replace("-", "")
    source = {"form": filing["form"], "filed": filing["filingDate"], "accn": filing["accessionNumber"],
              "period_end": filing.get("reportDate")}
    pre = _take_prefetched(filing["accessionNumber"], budget)
    try:
        if pre is not None:
            items = pre["items"]
        else:
            idx = edgar._get_json(edgar.ARCHIVE_URL.format(cik=cik, acc=acc, name="index.json"), budget, FETCHER)
            items = ((idx or {}).get("directory") or {}).get("item") or []
        inst, lab = _instance_and_labels(items)
        if inst is None:
            return _empty(f"el {filing['form']} no publica sus cifras en un formato que se pueda leer automáticamente", source=source)
        size_mb = int(inst.get("size") or 0) / (1024 * 1024)
        if size_mb > S["max_instance_mb"]:
            return _empty(f"el archivo de cifras del {filing['form']} pesa {size_mb:.0f} MB (más de "
                          f"{S['max_instance_mb']} MB: no se descarga)", source=source)
        # En streaming a un archivo temporal (borrado al salir) y lectura en flujo: la memoria no depende del tamaño.
        with (pre["tmp"] if pre is not None and pre.get("tmp") is not None
              else tempfile.TemporaryFile(suffix=".xml")) as tmp:
            if pre is None or pre.get("tmp") is None:
                _download_instance(cik, acc, inst, budget, tmp)
            tmp.seek(0)
            with budget.turn(edgar._segments_parsing()):      # V6 (B2): no el turno de lecturas del análisis
                parsed = edgar.parse_segments(tmp, tuple(S["axes"]) + tuple(S["geographic_axes"]),
                                              tuple(S["revenue_concepts"]) + premiums, tuple(S["neutral_members"]),
                                              tuple(S["geographic_axes"]), tuple(S["elimination_members"]),
                                              tuple(S["redundant_axes"]), tuple(S["extension_total_concepts"]))
        members = {m for part in ("axes", "by_geo") for ax in parsed[part].values() for ms in ax.values() for m in ms}
        names: Dict[str, str] = {}
        if lab and members:
            try:
                xml_lab = (pre or {}).get("lab")
                if xml_lab is None:
                    xml_lab = edgar._get(edgar.ARCHIVE_URL.format(cik=cik, acc=acc, name=lab), budget, FETCHER)
                names = edgar.labels(xml_lab, members)
            except (edgar.Unavailable, ParseError):     # sin etiquetas: el nombre del miembro, legible
                names = {}
    finally:
        if pre is not None and pre.get("tmp") is not None:
            pre["tmp"].close()
    res = compute(parsed, names)
    if (res is None or res["main"] is None) and premiums:
        # V2 (decisión del PM): una aseguradora que no desglosa ingresos por segmento desglosa primas (CB). Solo si
        # ningún concepto de ingresos da segmentos: las que sí los dan (BRK-B) no cambian.
        res = compute(parsed, names, premiums) or res
    if res is None or res["main"] is None:
        return _empty(NO_DIMS.replace("10-K", filing["form"]), source=source,
                      dropped_axes=(res or {}).get("dropped_axes") or [])
    m = res["main"]
    source["period_end"] = m["period_end"]
    cov = _coverage(m, parsed, cik, budget)
    return {"status": "ok", "fiscal_years": m["fiscal_years"], "axis": m["axis"], "axis_label": m["axis_label"],
            "concept": m["concept"], **cov, "segments": m["segments"], "total_reported": m["total_reported"],
            "reconciles": m["reconciles"], "gap_pct": m["gap_pct"], "notes": m["notes"], "secondary": res["secondary"],
            "others": res["others"], "dropped_axes": res["dropped_axes"], "currency": res["currency"], "source": source,
            "reason": None}


_gate: List[Any] = []
_by_symbol: "OrderedDict[str, str]" = OrderedDict()     # símbolo -> accn de su último resultado (para `cached`)


def _segments_gate():
    """V6 (B8): como mucho `segments_concurrency` consultas a la vez, una por símbolo; sin dato, se recuerda
    `segments_fail_ttl_s`."""
    import lazy_gate
    with _lock:
        if not _gate:
            S = cfg("market.segments")
            _gate.append(lazy_gate.Gate(S["segments_concurrency"], S["segments_fail_ttl_s"], S["segments_cache_max"]))
        return _gate[0]


def build(symbol: str) -> Dict[str, Any]:
    """Ingresos por segmento del último informe anual del emisor (ver la cabecera). Nunca lanza: sin_dato + motivo."""
    sym = symbol.upper().strip()
    return _segments_gate().run(sym, lambda: _build_safe(sym), lambda r: r.get("status") != "ok")


def cached(symbol: str) -> Optional[Dict[str, Any]]:
    """V6 (B9): el último resultado de `symbol` si está en la caché y no ha caducado; None si no (sin red: el PDF lo
    usa dentro de su turno de análisis y no descarga instancias XBRL ahí)."""
    sym = symbol.upper().strip()
    now = time.time()
    with _lock:
        key = _by_symbol.get(sym)
        hit = _cache.get(key) if key else None
        if hit and now - hit[0] < cfg("market.segments.segments_ttl_s"):
            return hit[1]
    return None


def _build_safe(sym: str) -> Dict[str, Any]:
    """V6 (B14): build nunca lanza, tampoco con un error inesperado (XML roto, un caso no previsto): sin_dato con un
    motivo genérico y el detalle al registro."""
    try:
        return _build(sym)
    except Exception as e:  # noqa: BLE001
        logger.warning("[SEGMENTS] %s: %s: %s", sym, type(e).__name__, e)
        return _empty("no se pudieron leer los segmentos del informe anual")


def is_insurer(sym: str) -> bool:
    """La misma regla que el motor para la rama de aseguradoras de FINANCIAL (classify: industria de Yahoo con un
    prefijo de `sectors.archetypes.insurance_prefixes`), con la info en caché del análisis. Sin Yahoo: no."""
    try:
        import yf_adapter
        ind = str((yf_adapter.get_ticker_info(sym) or {}).get("industry") or "").lower()
    except Exception:  # noqa: BLE001 — sin la industria no se decide nada: los conceptos de siempre
        return False
    return any(ind.startswith(p) for p in cfg("sectors.archetypes.insurance_prefixes"))


INSURER = is_insurer        # inyectable (tests y replay)


def _build(sym: str) -> Dict[str, Any]:
    S = cfg("market.segments")
    insurer = bool(INSURER(sym))
    if not edgar.user_agent():
        return _empty(edgar.status()["reason"])
    budget = edgar.Budget(S["segments_budget_s"])
    try:
        cik = _cik(sym, budget)
        if cik is None:
            return _empty(NO_SEC)
        filing, owner = None, cik
        for c in (cik,) + edgar._predecessors(sym):
            f = last_annual(c, budget)
            if f and (filing is None or f["filingDate"] > filing["filingDate"]):
                filing, owner = f, c
        if filing is None:
            return _empty("sin informe anual (10-K, 20-F o 40-F) en la SEC con las cifras en un formato que se pueda leer automáticamente")
        key = filing["accessionNumber"] + ("|primas" if insurer else "")
        now = time.time()
        with _lock:
            hit = _cache.get(key)
            if hit and now - hit[0] < S["segments_ttl_s"]:
                _cache.move_to_end(key)
                bounded.put(_by_symbol, sym, key, S["segments_cache_max"])
                return hit[1]
        res = _from_filing(owner, filing, budget, insurer)
        with _lock:
            _cache[key] = (now, res)
            _cache.move_to_end(key)
            bounded.put(_by_symbol, sym, key, S["segments_cache_max"])
            while len(_cache) > S["segments_cache_max"]:
                _cache.popitem(last=False)
        return res
    except edgar.NotFound:
        return _empty(NO_SEC)
    except edgar.Unavailable as e:          # presupuesto agotado o la SEC falla: no se guarda en caché
        return _empty(str(e))


# ───────────────────────── resumen para la historia, Riesgos y el PDF (V7 · P2, P4) ─────────────────────────

def _pct_txt(x: float) -> str:
    return f"{x * 100:.0f}%" if x >= 0.095 else f"{x * 100:.1f}%"


def _axis_line(ax: Dict[str, Any], fy: str, n: int) -> Dict[str, Any]:
    segs = sorted([x for x in ax.get("segments") or [] if x.get("share_last") is not None],
                  key=lambda x: -x["share_last"])
    return {"axis": ax.get("axis"), "axis_label": ax.get("axis_label"),
            "items": [{"label": x["label"], "share": x["share_last"], "share_txt": _pct_txt(x["share_last"])}
                      for x in segs[:n]],
            "more": max(len(segs) - n, 0)}


def _axes(res: Dict[str, Any]):
    """(eje principal, eje de producto si el emisor lo publica o si no el principal, todos los ejes con segmentos)."""
    S = cfg("market.segments")
    main = {k: res.get(k) for k in ("axis", "axis_label", "concept", "segments", "reconciles", "gap_pct", "notes")}
    axes = [main] + ([res["secondary"]] if res.get("secondary") else []) + list(res.get("others") or [])
    axes = [a for a in axes if a and a.get("segments")]
    first = next((a for a in axes if a.get("axis") in S["product_axes"]), None) or main
    return main, first, axes


def product_view(res: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """V7 · P4: la respuesta de /api/v2/segments con el desglose por producto como eje principal (el que pinta el PDF),
    si el emisor lo publica; si no, tal cual."""
    if not res or res.get("status") != "ok" or not res.get("segments"):
        return res
    main, first, _ = _axes(res)
    if first is main:
        return res
    return {**res, **{k: first.get(k) for k in ("axis", "axis_label", "concept", "segments", "reconciles", "gap_pct",
                                                 "notes")}}


def summary(res: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Hechos de los segmentos, ya formateados, para el capítulo 2 de la historia (de dónde vienen los ingresos), el
    bloque «Concentración» de Riesgos y el PDF: cifras del informe anual, sin interpretación. None sin segmentos.
      - `first`: el desglose por producto si el emisor lo publica (Apple: iPhone, Services…) y si no el eje principal;
      - `second`: la geografía (o, sin ella, el eje principal si `first` es el de producto);
      - `top`: el mayor segmento de `first` con su peso;
      - `falling`: los segmentos de la geografía (o del eje principal) cuyos ingresos bajaron en el último ejercicio."""
    if not res or res.get("status") != "ok" or not res.get("fiscal_years") or not res.get("segments"):
        return None
    S = cfg("market.segments")
    n, fy = S["summary_items_max"], res["fiscal_years"]
    last, prev = fy[-1], (fy[-2] if len(fy) > 1 else None)
    main, first, axes = _axes(res)
    geo = next((a for a in axes if a.get("axis") in S["geographic_axes"] and a is not first), None)
    second = geo or (main if first is not main else None)
    falling_from = geo or (main if first is not main else None)
    falling = []
    if falling_from and prev:
        for x in falling_from["segments"]:
            a, b = (x.get("values") or {}).get(prev), (x.get("values") or {}).get(last)
            if a and b is not None and a > 0 and b < a:
                ch = b / a - 1
                falling.append({"label": x["label"], "change": ch, "change_txt": f"−{abs(ch) * 100:.1f}%",
                                "axis_label": falling_from.get("axis_label")})
        falling.sort(key=lambda f: f["change"])
    f_line = _axis_line(first, last, n)
    s_line = _axis_line(second, last, n) if second else None
    top = f_line["items"][0] if f_line["items"] else None
    what = (res.get("concept_label") or "ingresos").lower()
    if top:
        rest = f_line["items"][1:3]
        text = (f"En FY{last}, {top['label']} aporta el {top['share_txt']} de sus {what}"
                + (", seguido de " + " y ".join(f"{x['label']} ({x['share_txt']})" for x in rest) if rest else "") + ".")
    else:
        text = None
    second_text = (f"Por {s_line['axis_label']}: " + ", ".join(f"{x['label']} {x['share_txt']}" for x in s_line["items"]) + "."
                   if s_line and s_line["items"] else None)
    return {"fy": last, "prev_fy": prev, "concept_label": res.get("concept_label"),
            # si los segmentos no cubren los ingresos consolidados (BCS: solo comisiones), se dice con la cifra
            "covers_total": res.get("covers_total"), "coverage_note": res.get("coverage_note"),
            "first": f_line, "second": s_line, "text": text, "second_text": second_text,
            "top": {**top, "axis_label": first.get("axis_label")} if top else None,
            "falling": falling, "source": res.get("source")}
