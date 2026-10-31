"""
F9 · R1 (revisión externa del informe de NU, 27-oct-2026): prima de riesgo país en el Ke.

    Ke = Rf + β·ERP + λ·CRP          (y después, los pisos de F8 · E1)

  ERP  la implícita de EE. UU. de Damodaran (valuation.capm): ya incluye el riesgo de EE. UU.
  CRP  lo que una economía añade sobre EE. UU., ponderado por DÓNDE OPERA la empresa:
         CRP = Σ w_x · máx(0, ERP_x − ERP_EE.UU.)
       con ERP_x la prima total de Damodaran del país o de la región (config/country_risk.toml, ctryprem.xlsx, con su
       fecha). El máx(0, ·) evita restar riesgo a los países con mejor rating que EE. UU. (Aa1): nuestra ERP es la de
       EE. UU. y la del mercado maduro se queda en ella.
  w_x  la geografía de los ingresos del último informe anual en XBRL (lib/segments.py). Decisión del PM (27-oct,
       «(b) ampliada»), sin inventar exposición:
         · un país identificado, su prima;
         · un agregado regional con nombre («Europe», «EMEA», «Latin America», «Asia-Pacific»), la media ponderada por
           PIB que Damodaran publica para esa región;
         · un cubo vago («Non-US», «Other countries», «Rest of world») o varias regiones sin media publicada («Asia
           Pacific and Africa»): no atribuido, aporta 0 y se declara (presupuesto 0: no se aproxima con la media Global).
       Si los países y las regiones con nombre cubren menos de `geo_min_coverage` de los ingresos, se usa el país de la
       SEDE OPERATIVA (dirección comercial del emisor en EDGAR o, sin la SEC, el país de la ficha), nunca el domicilio
       legal: NU está constituida en Caimán y opera en Brasil, México y Colombia. El aviso del no atribuido se mantiene.
  λ    `lambda` = 1: la ponderación por ingresos ya mide la exposición de la empresa (es el enfoque de Damodaran por
       países de operación); un λ por empresa necesitaría la exposición media de las empresas de cada país, que no hay
       gratis, y la contaría dos veces.

Parámetros: valuation.country_risk.
"""
import re
from typing import Any, Dict, List, Optional

from settings import cfg

GEO_AXES = ("StatementGeographicalAxis", "GeographicalAreasAxis")
UNATTRIBUTED = "no atribuido"


def _table() -> Dict[str, Any]:
    return cfg("country_risk")


def country_name(label: Optional[str]) -> Optional[str]:
    """El nombre de la tabla de Damodaran para un país (el de EDGAR o el de un miembro del XBRL), o None."""
    if not label:
        return None
    erp = _table()["erp"]
    alias = cfg("valuation.country_risk.aliases")
    s = str(label).strip()
    for cand in (s, alias.get(s), s.title(), alias.get(s.title())):
        if cand and cand in erp:
            return cand
    low = s.lower()
    return next((c for c in erp if c.lower() == low), None)


def premium(erp_x: float) -> float:
    """Lo que añade una economía sobre EE. UU.: máx(0, ERP_x − ERP_EE.UU.)."""
    return max(0.0, erp_x - _table()["us_erp"])


def _member(label: str, member: str = "", hq: Optional[str] = None) -> Dict[str, Any]:
    """Un miembro de la geografía: país, región con nombre o no atribuido (erp None). El «país de domicilio» de la NIIF 8
    (ifrs-full:CountryOfDomicileMember, UL) es el país de origen del emisor: el de su sede operativa."""
    C, T = cfg("valuation.country_risk"), _table()
    label = re.sub(r"\s*\[member\]\s*$", "", label, flags=re.I).strip()
    if member.endswith("CountryOfDomicileMember") and hq:
        return {"label": label, "kind": "país", "name": hq, "erp": T["erp"][hq]}
    c = country_name(label)
    if c:
        return {"label": label, "kind": "país", "name": c, "erp": T["erp"][c]}
    low = label.lower()
    # Las agrupaciones que Damodaran publica tal cual (EMEA…) van antes en la lista y ganan; un miembro que nombra
    # varias regiones sin media publicada («Asia Pacific and Africa») queda sin atribuir, como «Non-US».
    found = list(dict.fromkeys(r for kw, r in C["region_keywords"] if kw in low))
    region = found[0] if found and (found[0] in C["region_groups"] or len(found) == 1) else None
    if region:
        return {"label": label, "kind": "región", "name": region, "erp": T["region_erp"][region]}
    return {"label": label, "kind": UNATTRIBUTED, "name": None, "erp": None}


def _geo_view(segs: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not segs or segs.get("status") != "ok":
        return None
    for v in (segs, segs.get("secondary"), *(segs.get("others") or [])):
        if v and v.get("axis") in GEO_AXES and v.get("segments"):
            return v
    return None


def exposure(segs: Optional[Dict[str, Any]], hq_country: Optional[str]) -> Dict[str, Any]:
    """{crp, basis, weights, country, identified, unattributed, reason}: la prima de riesgo país del Ke y de dónde
    sale. `basis`: «geografía», «sede» o «sin_dato»; `unattributed`: la parte de los ingresos sin país ni región con
    nombre y sus etiquetas (se declara también cuando manda la sede)."""
    C, T = cfg("valuation.country_risk"), _table()
    lam = C["lambda"]
    hq = country_name(hq_country)
    out: Dict[str, Any] = {"crp": 0.0, "lambda": lam, "basis": None, "weights": [], "country": hq,
                           "identified": None, "unattributed": None, "as_of": T["updated"], "source": T["source"],
                           "reason": None}
    view = _geo_view(segs)
    gap = (view or {}).get("gap_pct")
    if view is not None and not view.get("reconciles") and gap is None:
        out["reason"] = "los ingresos por país no suman un total comparable con el de la empresa: se usa la sede"
        view = None
    if view is not None:
        # `share_last` es la parte de la suma de los segmentos; si no concilia y se queda corta, se lleva al total
        # consolidado y lo que falta queda sin atribuir («sin desglose»).
        f = 1.0 if view.get("reconciles") else min(1.0, 1.0 + gap)
        rows = [(s.get("label") or s.get("member") or "", s.get("member") or "", (s.get("share_last") or 0.0) * f)
                for s in view["segments"]]
        members = [{**_member(label, mem, hq), "share": w} for label, mem, w in rows if w > 0]
        if f < 1.0:
            members.append({"label": "sin desglose", "kind": UNATTRIBUTED, "name": None, "erp": None,
                            "share": 1.0 - f})
        idf = sum(m["share"] for m in members if m["erp"] is not None)
        vague = [m for m in members if m["erp"] is None]
        out["identified"] = idf
        out["geo"] = [{k: m[k] for k in ("label", "kind", "name", "share")} for m in members]
        if vague:
            out["unattributed"] = {"share": sum(m["share"] for m in vague), "labels": [m["label"] for m in vague]}
        if idf >= C["geo_min_coverage"]:
            ws: List[Dict[str, Any]] = [{**m, "add": premium(m["erp"]) if m["erp"] is not None else 0.0}
                                        for m in members]
            out.update(basis="geografía", weights=ws, crp=lam * sum(x["share"] * x["add"] for x in ws),
                       fiscal_year=(view.get("fiscal_years") or segs.get("fiscal_years") or [None])[-1])
            return out
        out["reason"] = (f"los países y las regiones con nombre cubren el {idf:.0%} de los ingresos (menos del "
                         f"{C['geo_min_coverage']:.0%}): se usa la sede operativa")
    if hq:
        add = premium(T["erp"][hq])
        out.update(basis="sede", crp=lam * add,
                   weights=[{"label": hq, "kind": "sede", "name": hq, "erp": T["erp"][hq], "share": 1.0, "add": add}])
        out["reason"] = out["reason"] or "sin geografía de los ingresos en XBRL: país de la sede operativa"
        return out
    out.update(basis="sin_dato", reason="sin geografía de los ingresos ni país de la sede: sin prima de riesgo país")
    return out


def source_label(e: Optional[Dict[str, Any]]) -> Optional[str]:
    """De dónde sale la prima, para la tabla por empresa: «país», «región», «país y región», «sede» o «sin dato»."""
    if not e:
        return None
    if e["basis"] != "geografía":
        return {"sede": "sede", "sin_dato": "sin dato"}.get(e["basis"])
    kinds = {w["kind"] for w in e["weights"] if w["add"] > 0} or {w["kind"] for w in e["weights"]} - {UNATTRIBUTED}
    return " y ".join(k for k in ("país", "región") if k in kinds) or "país"


def _month(as_of: str) -> str:
    m = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")[int(as_of[5:7]) - 1]
    return f"{m} de {as_of[:4]}"


def unattributed_text(e: Optional[Dict[str, Any]]) -> Optional[str]:
    """«el 60% de los ingresos no tiene país identificado («Non-US»)», o None."""
    u = (e or {}).get("unattributed")
    if not u or u["share"] <= 0:
        return None
    return (f"el {u['share']:.0%} de los ingresos no tiene país identificado ("
            + ", ".join(f"«{x}»" for x in u["labels"]) + ")")


def text(e: Optional[Dict[str, Any]]) -> Optional[str]:
    """«prima de riesgo país 3.01 pp (Brasil, sede operativa; Damodaran, enero de 2026)», o None si es 0 y no hay
    nada sin atribuir que declarar."""
    if not e or e["basis"] == "sin_dato":
        return None
    from names import country as _es
    un = unattributed_text(e)
    if not e.get("crp") and not un:
        return None
    if e["basis"] == "sede":
        where = f"{_es(e['weights'][0]['name']) or e['weights'][0]['name']}, sede operativa"
    else:
        top = sorted((x for x in e["weights"] if x["add"] > 0), key=lambda x: -x["share"] * x["add"])
        where = "ingresos por geografía: " + ", ".join(
            f"{(_es(x['name']) if x['kind'] == 'país' else None) or x['label']} {x['share']:.0%}" for x in top[:3])
    head = f"prima de riesgo país {e['crp'] * 100:.2f} pp ({where}; Damodaran, {_month(e['as_of'])})"
    return head + (f"; {un}" if un else "")


def _group(kind: str, name: Optional[str]) -> Optional[str]:
    """«emerging», «europe» o None para un país o una región con nombre (F9 · R2b, market.beta_choice)."""
    if not name:
        return None
    B = cfg("market.beta_choice")
    region = _table()["country_region"].get(name) if kind in ("país", "sede") else name
    if kind in ("país", "sede") and region == "Asia":
        return "emerging" if name in B["emerging_asia"] else None
    if region in B["emerging_regions"]:
        return "emerging"
    if region in B["europe_regions"]:
        return "europe"
    return None


def beta_region(e: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """F9 · R2b (decisión del PM del 27-oct): la región de la tabla de betas de Damodaran para la beta de abajo hacia
    arriba. Emergentes si la sede operativa o más de `region_majority` de los ingresos identificados (países y regiones
    con nombre) están en emergentes; si no, Europa con la misma regla; si no, EE. UU. {region, reason}."""
    B = cfg("market.beta_choice")
    e = e or {}
    hq_group = _group("sede", e.get("country"))
    geo = [g for g in e.get("geo") or [] if g["kind"] in ("país", "región")]
    idf = sum(g["share"] for g in geo)
    share = {k: (sum(g["share"] for g in geo if _group(g["kind"], g["name"]) == k) / idf if idf else 0.0)
             for k in ("emerging", "europe")}
    names = {"emerging": "mercados emergentes", "europe": "Europa"}
    for k in ("emerging", "europe"):
        if hq_group == k:
            return {"region": k, "reason": f"sede operativa en {names[k]}"}
        if share[k] > B["region_majority"]:
            return {"region": k, "reason": f"el {share[k]:.0%} de los ingresos identificados, en {names[k]}"}
    return {"region": "us", "reason": None}

