"""
SEC EDGAR en el camino del análisis (fase 2b; D2: verificación y respaldo, nunca fuente principal en la 2b).

Lo que da:
  · el emisor (ticker → CIK, `company_tickers.json`; regla de sucesión de `data.edgar.predecessors`) y su lista de
    filings (`submissions`): aviso de resultados publicados y aún no incorporados (T3, F2_PRECEDENCIA §1.1) y D7
    (emisor sin estados en la SEC, F2_PRECEDENCIA §4);
  · el factor ADR de la portada del 20-F (`dei:Security12bTitle`, página R1 del filing; T4, regla B aprobada en el
    punto de parada 1) para los ADR que no están en `config/adr.toml`;
  · los hechos XBRL de los estados (`companyfacts`, solo los conceptos de CONCEPTS) más los de los filings con XBRL
    que companyfacts aún no trae, leídos de su instancia (F2_PRECEDENCIA §3.1). Con ellos, lib/edgar_backup.py
    respalda lo que Yahoo no da del mismo corte (T4).

Reglas de la SEC: `User-Agent` con nombre y correo de contacto y ≤ 10 peticiones por segundo. El User-Agent llega SOLO
por la variable de entorno `data.edgar.user_agent_env` (en Render la pone el usuario en el panel; aquí nunca se
escribe ni se registra). Sin ella el cliente se desactiva y lo declara.

Nunca bloquea el análisis: todo lo de EDGAR de un análisis corre en un hilo (`start`), con un presupuesto de tiempo
(`budget_s`); si se agota o la SEC falla, el análisis sigue sin EDGAR (o sin la parte que faltó) y lo dice
(`status`, `reason`). El hilo publica primero el emisor, sus filings y la portada (etapa 1: la necesita el factor ADR
mientras se descargan los estados de Yahoo) y después los hechos (etapa 2). Cachés por proceso: company_tickers y
companyfacts un día, submissions unas horas, instancias y portadas por número de filing. Solo se guardan los
conceptos que se usan (Render tiene 512 MB).

El descargador es inyectable (`FETCHER`): en producción, urllib; en los tests, el replay de los fixtures.
"""
import datetime as _dt
import gzip
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

from settings import cfg

logger = logging.getLogger(__name__)

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{name}"
PERIODIC_FORMS = {"10-Q", "10-Q/A", "10-K", "10-K/A", "10-KT", "20-F", "20-F/A", "40-F", "40-F/A", "6-K", "6-K/A"}
ANNUAL_OR_QUARTERLY = PERIODIC_FORMS - {"6-K", "6-K/A"}
ANNUAL_FORMS = {"10-K", "10-K/A", "10-KT", "20-F", "20-F/A", "40-F", "40-F/A"}
FOREIGN_ANNUAL_FORMS = {"20-F", "20-F/A", "40-F", "40-F/A"}
USED_FORMS = PERIODIC_FORMS | {"8-K", "8-K/A"}
FINANCIAL_TAXONOMIES = ("us-gaap", "ifrs-full")

# Conceptos XBRL de los campos que EDGAR puede respaldar (portados de la tabla de la 2a, tests/edgar.py; T2 §3).
# campo → (tipo, signo frente a Yahoo, alternativas us-gaap, alternativas ifrs-full), en orden de preferencia.
# Tipo: "flow" (periodo con inicio y fin) o "stock" (saldo a una fecha). Signo: +1, el mismo que Yahoo; −1, XBRL da
# el pago en positivo y Yahoo como salida de caja. La deuda no está: su definición (componentes, arrendamientos,
# cautivas) es la T5.
CONCEPTS: Dict[str, Tuple[str, int, Tuple[str, ...], Tuple[str, ...]]] = {
    "revenue": ("flow", 1, (
        "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet",
        "RevenuesNetOfInterestExpense", "RegulatedAndUnregulatedOperatingRevenue",
        "OperatingLeasesIncomeStatementLeaseRevenue", "PremiumsEarnedNet"),
        ("Revenue", "RevenueFromContractsWithCustomers")),
    "gross_profit": ("flow", 1, ("GrossProfit",), ("GrossProfit",)),
    "operating_income": ("flow", 1, ("OperatingIncomeLoss",), ("ProfitLossFromOperatingActivities",)),
    "net_income": ("flow", 1, (
        "NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic",
        "NetIncomeLossAvailableToCommonStockholdersDiluted"),
        ("ProfitLossAttributableToOwnersOfParent", "ProfitLoss")),
    "interest_expense": ("flow", 1, (
        "InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestAndDebtExpense",
        "InterestExpenseNet"), ("FinanceCosts", "InterestExpense")),
    "depreciation": ("flow", 1, (
        "DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet",
        "Depreciation", "DepreciationAmortizationAndOther"), (
        "DepreciationAndAmortisationExpense", "AdjustmentsForDepreciationAndAmortisationExpense",
        "DepreciationPropertyPlantAndEquipmentIncludingRightofuseAssets", "DepreciationExpense",
        "DepreciationAmortisationAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss",
        "AdjustmentsForDepreciationAmortisationAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss",
        "AdjustmentsForDepreciationAndAmortisationExpenseAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss")),
    "operating_cash_flow": ("flow", 1, (
        "NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
        ("CashFlowsFromUsedInOperatingActivities", "CashFlowsFromUsedInOperations")),
    "capex": ("flow", -1, (
        "PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
        "PaymentsForCapitalImprovements", "PaymentsToAcquireRealEstate"), (
        "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        "PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets",
        "PurchaseOfPropertyPlantAndEquipment", "PurchaseOfOtherLongtermAssetsClassifiedAsInvestingActivities")),
    "dividends_paid": ("flow", -1, (
        "PaymentsOfDividendsCommonStock", "PaymentsOfDividends", "PaymentsOfOrdinaryDividends"), (
        "DividendsPaidClassifiedAsFinancingActivities", "DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities",
        "DividendsPaid")),
    "total_assets": ("stock", 1, ("Assets",), ("Assets",)),
    "current_assets": ("stock", 1, ("AssetsCurrent",), ("CurrentAssets",)),
    "current_liabilities": ("stock", 1, ("LiabilitiesCurrent",), ("CurrentLiabilities",)),
    "total_liabilities": ("stock", 1, ("Liabilities",), ("Liabilities",)),
    "retained_earnings": ("stock", 1, ("RetainedEarningsAccumulatedDeficit",), ("RetainedEarnings",)),
    "inventories": ("stock", 1, ("InventoryNet", "InventoryFinishedGoodsNetOfReserves"), ("Inventories",)),
    "equity_parent": ("stock", 1, ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
                      ("EquityAttributableToOwnersOfParent", "Equity")),
}
# Componentes de la deuda (T5, F2_PRECEDENCIA §2.3): saldos de balance, el total o sus partes corriente y no
# corriente. Solo pasivos ya en balance: los arrendamientos firmados y aún no iniciados van en notas (MSFT: 329.1 mil
# millones de USD solo en texto) y no tienen estos conceptos.
DEBT_PARTS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "us-gaap": {
        "operating_leases": ("OperatingLeaseLiability", "OperatingLeaseLiabilityCurrent",
                             "OperatingLeaseLiabilityNoncurrent"),
        "finance_leases": ("FinanceLeaseLiability", "FinanceLeaseLiabilityCurrent", "FinanceLeaseLiabilityNoncurrent"),
        "subordinated": ("SubordinatedDebt",),
        # El emisor presenta su deuda con el arrendamiento financiero dentro (XOM, MU): no se vuelve a sumar.
        "debt_with_finance_leases": ("LongTermDebtAndCapitalLeaseObligations",
                                     "LongTermDebtAndCapitalLeaseObligationsCurrent", "DebtAndCapitalLeaseObligations"),
    },
    "ifrs-full": {
        "leases": ("LeaseLiabilities", "CurrentLeaseLiabilities", "NoncurrentLeaseLiabilities"),
        "subordinated": ("SubordinatedLiabilities",),
    },
}
_WANTED = {"us-gaap": {c for v in CONCEPTS.values() for c in v[2]} | {c for v in DEBT_PARTS["us-gaap"].values() for c in v},
           "ifrs-full": {c for v in CONCEPTS.values() for c in v[3]}
           | {c for v in DEBT_PARTS["ifrs-full"].values() for c in v}}
# Deuda de la financiera cautiva (T5): solo va con dimensiones en la instancia del filing.
CAPTIVE_DEBT_CONCEPTS = ("LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsCurrent",
                         "LongTermDebtNoncurrent", "LongTermDebtCurrent", "ShortTermBorrowings", "CommercialPaper")
_FACT_KEYS = ("start", "end", "val", "filed", "form", "accn")

_cache: Dict[str, Tuple[float, Any]] = {}
_lock = threading.Lock()
_rate_lock = threading.Lock()
_last = [0.0]
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="edgar")
_inflight: Dict[str, Future] = {}        # ticker -> etapa 1 del análisis en curso (emisor, filings, portada)


class Unavailable(RuntimeError):
    """EDGAR no disponible para este análisis (sin User-Agent, presupuesto agotado o la SEC falla)."""


class NotFound(Unavailable):
    """La SEC responde 404: el recurso no existe (p. ej. companyfacts de un CIK sin estados XBRL)."""


def user_agent() -> Optional[str]:
    ua = (os.environ.get(cfg("data.edgar.user_agent_env")) or "").strip()
    return ua if "@" in ua else None


def status() -> Dict[str, Any]:
    if user_agent():
        return {"enabled": True, "reason": None}
    return {"enabled": False,
            "reason": (f"sin User-Agent de la SEC (variable {cfg('data.edgar.user_agent_env')}): verificación oficial "
                       "no disponible")}


def urllib_fetcher(url: str, timeout: float) -> Tuple[Optional[bytes], int]:
    """Descarga real con el User-Agent de la SEC (nunca se registra)."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent() or "", "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            body = gzip.decompress(raw) if r.headers.get("Content-Encoding") == "gzip" else raw
            return body, r.status
    except urllib.error.HTTPError as e:
        return None, e.code


FETCHER: Callable[[str, float], Tuple[Optional[bytes], int]] = urllib_fetcher


class Budget:
    """Tiempo de EDGAR que le queda a un análisis."""

    def __init__(self, seconds: Optional[float] = None):
        self.deadline = time.monotonic() + (cfg("data.edgar.budget_s") if seconds is None else seconds)

    def left(self) -> float:
        return self.deadline - time.monotonic()


def _get(url: str, budget: Budget) -> bytes:
    E = cfg("data.edgar")
    if not user_agent():
        raise Unavailable(status()["reason"])
    with _rate_lock:
        wait = _last[0] + E["min_interval_s"] - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
    left = budget.left()
    if left <= 0:
        raise Unavailable(f"presupuesto de EDGAR agotado ({E['budget_s']:g} s)")
    try:
        body, code = FETCHER(url, min(E["timeout_s"], left))
    except Exception as e:  # red, tiempo de espera, TLS…: se registra el tipo
        raise Unavailable(f"EDGAR no respondió ({type(e).__name__})") from e
    if code == 404:
        raise NotFound("EDGAR respondió 404")
    if body is None or code != 200:
        raise Unavailable(f"EDGAR respondió {code}")
    return body


def _get_json(url: str, budget: Budget) -> Any:
    return json.loads(_get(url, budget))


def _cached(key: str, ttl: float, make: Callable[[], Any]) -> Any:
    now = time.time()
    with _lock:
        ent = _cache.get(key)
        if ent and now - ent[0] < ttl:
            return ent[1]
    val = make()
    with _lock:
        _cache[key] = (now, val)
    return val


def cik_for(ticker: str, budget: Budget) -> Optional[Dict[str, Any]]:
    """{cik, title} del ticker en company_tickers.json de la SEC, o None si no está registrado."""
    E = cfg("data.edgar")
    table = _cached("tickers", E["tickers_ttl_s"], lambda: {
        str(v["ticker"]).upper(): {"cik": int(v["cik_str"]), "title": v.get("title")}
        for v in (_get_json(TICKERS_URL, budget) or {}).values()})
    return table.get(ticker.upper().replace(".", "-"))


def filings(cik: int, budget: Budget) -> List[Dict[str, Any]]:
    """Filings recientes del CIK (desde `since`), del más reciente al más antiguo."""
    E = cfg("data.edgar")

    def make():
        r = (_get_json(SUBMISSIONS_URL.format(cik=cik), budget).get("filings") or {}).get("recent") or {}
        out = []
        for i, form in enumerate(r.get("form") or []):
            fd = r["filingDate"][i]
            # Solo los formularios que se usan (JPM presenta decenas de miles de folletos 424B2: la caché por
            # proceso no debe crecer con ellos; Render tiene 512 MB).
            if fd < E["since"] or form not in USED_FORMS:
                continue
            out.append({"form": form, "filingDate": fd, "reportDate": (r.get("reportDate") or [""] * (i + 1))[i] or None,
                        "items": (r.get("items") or [""] * (i + 1))[i] or "",
                        "accessionNumber": r["accessionNumber"][i],
                        "isXBRL": bool((r.get("isXBRL") or [0] * (i + 1))[i])})
        return sorted(out, key=lambda f: (f["filingDate"], f["accessionNumber"]), reverse=True)
    return _cached(f"sub:{cik}", E["submissions_ttl_s"], make)


# ───────────────────────── hechos XBRL: companyfacts e instancias ─────────────────────────

def _index_facts(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Añade a unos hechos (forma de companyfacts) los filings que traen estados (`accns`) y el último presentado."""
    accns, last = set(), ""
    for tx in FINANCIAL_TAXONOMIES:
        for node in (facts.get("facts") or {}).get(tx, {}).values():
            for fs in node.get("units", {}).values():
                for f in fs:
                    accns.add(f.get("accn"))
                    last = max(last, f.get("filed") or "")
    facts["accns"] = sorted(a for a in accns if a)
    facts["last_filed"] = last or None
    return facts


def reduce_facts(raw: Dict[str, Any]) -> Dict[str, Any]:
    """companyfacts con solo los conceptos de CONCEPTS (y los filings que traen estados, contados sobre todos)."""
    idx = _index_facts({"facts": raw.get("facts") or {}})
    out: Dict[str, Any] = {"cik": raw.get("cik"), "entityName": raw.get("entityName"), "facts": {}}
    for tx, names in _WANTED.items():
        cs = (raw.get("facts") or {}).get(tx) or {}
        for c in sorted(names):
            node = cs.get(c)
            if node:
                out["facts"].setdefault(tx, {})[c] = {"units": {
                    u: [{k: f[k] for k in _FACT_KEYS if f.get(k) is not None} for f in fs]
                    for u, fs in (node.get("units") or {}).items()}}
    out["accns"], out["last_filed"] = idx["accns"], idx["last_filed"]
    return out


def merge_facts(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    """Une hechos de la misma forma (otro CIK de la sucesión o una instancia); en un mismo periodo quedan los dos
    filings y manda el más reciente por `filed`, como en una reexpresión."""
    out = {k: v for k, v in base.items() if k not in ("facts", "accns", "last_filed")}
    out["facts"] = {}
    for src in (base, extra):
        for tx, cs in (src.get("facts") or {}).items():
            for c, node in cs.items():
                dst = out["facts"].setdefault(tx, {}).setdefault(c, {"units": {}})
                for u, fs in (node.get("units") or {}).items():
                    lst = dst["units"].setdefault(u, [])
                    lst.extend(f for f in fs if f not in lst)
    return _index_facts(out)


def company_facts(cik: int, budget: Budget) -> Dict[str, Any]:
    """companyfacts reducido del CIK (caché diaria). NotFound si el CIK no tiene estados XBRL."""
    return _cached(f"facts:{cik}", cfg("data.edgar.facts_ttl_s"),
                   lambda: reduce_facts(_get_json(FACTS_URL.format(cik=cik), budget)))


def _tax_of(ns: str) -> Optional[str]:
    ns = ns.split("://", 1)[-1]          # IFRS usa https, la FASB http
    if ns.startswith("fasb.org/us-gaap/"):
        return "us-gaap"
    if ns.startswith("xbrl.ifrs.org/taxonomy/"):
        return "ifrs-full"
    return None


def parse_instance(xml: bytes, form: str, filed: str, accn: str) -> Dict[str, Any]:
    """Hechos sin dimensiones de una instancia XBRL, solo los conceptos de CONCEPTS, con la forma de companyfacts.
    Lectura en flujo (iterparse): una instancia de 15 MB (HSBC) no se carga entera en memoria."""
    import io
    import xml.etree.ElementTree as ET
    X = "{http://www.xbrl.org/2003/instance}"
    ctx: Dict[str, Optional[Dict[str, str]]] = {}
    units: Dict[str, str] = {}
    raw: List[Tuple[str, str, str, str, str]] = []
    depth = 0
    for ev, el in ET.iterparse(io.BytesIO(xml), events=("start", "end")):
        if ev == "start":
            depth += 1
            continue
        depth -= 1
        if depth != 1:
            continue
        tag = el.tag
        if tag == X + "context":
            if el.find(f"{X}entity/{X}segment") is not None or el.find(X + "scenario") is not None:
                ctx[el.get("id")] = None
            else:
                p = el.find(X + "period")
                inst, st, en = p.find(X + "instant"), p.find(X + "startDate"), p.find(X + "endDate")
                ctx[el.get("id")] = ({"end": inst.text.strip()[:10]} if inst is not None else
                                     {"start": st.text.strip()[:10], "end": en.text.strip()[:10]})
        elif tag == X + "unit":
            meas = [m.text.split(":")[-1] for m in el.iter(X + "measure")]
            units[el.get("id")] = "/".join(meas) if el.find(X + "divide") is not None else (meas[0] if meas else "")
        elif tag.startswith("{") and el.get("contextRef") and el.get("unitRef") and el.text:
            ns, name = tag[1:].split("}")
            tx = _tax_of(ns)
            if tx and name in _WANTED[tx]:
                raw.append((tx, name, el.get("contextRef"), el.get("unitRef"), el.text.strip()))
        el.clear()
    out: Dict[str, Any] = {"facts": {}}
    for tx, name, cref, uref, text in raw:
        c = ctx.get(cref)
        if not c or uref not in units:
            continue
        try:
            val = float(text)
        except ValueError:
            continue
        f = {**c, "val": int(val) if val.is_integer() else val, "filed": filed, "form": form, "accn": accn}
        lst = out["facts"].setdefault(tx, {}).setdefault(name, {"units": {}})["units"].setdefault(units[uref], [])
        if f not in lst:
            lst.append(f)
    return _index_facts(out)


def parse_segment(xml: bytes, axis: str, member: str, concepts: Tuple[str, ...]) -> Dict[str, Dict[str, float]]:
    """Saldos de `concepts` (us-gaap) con UNA sola dimensión, `axis` = `member` (la cautiva de CAT:
    ProductOrServiceAxis = FinancialProductsMember): {fecha: {concepto: valor}}."""
    import io
    import xml.etree.ElementTree as ET
    X = "{http://www.xbrl.org/2003/instance}"
    XD = "{http://xbrl.org/2006/xbrldi}"
    ctx: Dict[str, str] = {}
    raw: List[Tuple[str, str, str]] = []
    depth = 0
    for ev, el in ET.iterparse(io.BytesIO(xml), events=("start", "end")):
        if ev == "start":
            depth += 1
            continue
        depth -= 1
        if depth != 1:
            continue
        if el.tag == X + "context":
            mem = list(el.iter(XD + "explicitMember"))
            inst = el.find(f"{X}period/{X}instant")
            if (inst is not None and len(mem) == 1 and mem[0].get("dimension", "").split(":")[-1] == axis
                    and (mem[0].text or "").split(":")[-1] == member):
                ctx[el.get("id")] = inst.text.strip()[:10]
        elif el.tag.startswith("{") and el.get("contextRef") and el.text:
            ns, name = el.tag[1:].split("}")
            if _tax_of(ns) == "us-gaap" and name in concepts:
                raw.append((name, el.get("contextRef"), el.text.strip()))
        el.clear()
    out: Dict[str, Dict[str, float]] = {}
    for name, cref, text in raw:
        if cref in ctx:
            try:
                out.setdefault(ctx[cref], {})[name] = float(text)
            except ValueError:
                continue
    return out


def captive_debt(cik: int, fl: List[Dict[str, Any]], budget: Budget, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Deuda de la financiera cautiva en el último 10-Q/10-K (instancia con dimensiones; caché por filing)."""
    per = [f for f in fl or [] if f["form"] in ANNUAL_OR_QUARTERLY and f["isXBRL"] and f.get("reportDate")]
    if not per:
        return {"status": "sin_dato", "reason": "sin 10-Q/10-K con XBRL"}
    f = per[0]
    acc = f["accessionNumber"].replace("-", "")

    def make():
        idx = _get_json(ARCHIVE_URL.format(cik=cik, acc=acc, name="index.json"), budget)
        names = [i.get("name") for i in ((idx or {}).get("directory") or {}).get("item") or []]
        inst = next((n for n in names if n and n.endswith("_htm.xml")), None)
        if inst is None:
            return {}
        return parse_segment(_get(ARCHIVE_URL.format(cik=cik, acc=acc, name=inst), budget), spec["axis"],
                             spec["member"], CAPTIVE_DEBT_CONCEPTS)
    by_date = _cached(f"captive:{acc}:{spec['member']}", cfg("data.edgar.facts_ttl_s"), make)
    at = f["reportDate"]
    vals = by_date.get(at) or {}
    if not vals:
        return {"status": "sin_dato", "reason": f"el {f['form']} del {f['filingDate']} no trae la deuda de "
                                                f"{spec['name']} a {at}"}
    return {"status": "ok", "name": spec["name"], "date": at, "form": f["form"], "accn": f["accessionNumber"],
            "parts": vals, "value": sum(vals.values())}


def pending_filings(fl: Optional[List[Dict[str, Any]]], facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """F2_PRECEDENCIA §3.1: filings con XBRL de estados presentados después del último que trae companyfacts y que
    no aparecen en él (del más antiguo al más reciente)."""
    have, last = set(facts.get("accns") or []), facts.get("last_filed") or ""
    out = [f for f in fl or [] if f["isXBRL"] and (f["form"] in ANNUAL_OR_QUARTERLY or f["form"].startswith("6-K"))
           and f["accessionNumber"] not in have and f["filingDate"] > last]
    return sorted(out, key=lambda f: (f["filingDate"], f["accessionNumber"]))


def instance_facts(cik: int, filing: Dict[str, Any], budget: Budget) -> Dict[str, Any]:
    """Hechos de la instancia XBRL de un filing (`<x>_htm.xml` de su índice), en caché por número de filing."""
    acc = filing["accessionNumber"].replace("-", "")

    def make():
        idx = _get_json(ARCHIVE_URL.format(cik=cik, acc=acc, name="index.json"), budget)
        names = [i.get("name") for i in ((idx or {}).get("directory") or {}).get("item") or []]
        inst = next((n for n in names if n and n.endswith("_htm.xml")), None)
        if inst is None:
            return {"facts": {}, "accns": [], "last_filed": None, "reason": "el filing no publica la instancia XBRL"}
        return parse_instance(_get(ARCHIVE_URL.format(cik=cik, acc=acc, name=inst), budget), filing["form"],
                              filing["filingDate"], filing["accessionNumber"])
    return _cached(f"inst:{acc}", cfg("data.edgar.facts_ttl_s"), make)


def facts_with_pending(cik: int, fl: List[Dict[str, Any]], budget: Budget,
                       predecessors: Tuple[int, ...] = ()) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """companyfacts (con la historia de los predecesores) más los filings pendientes que dé tiempo a leer.
    Devuelve los hechos y el registro de los pendientes ({form, date, accn, read, reason})."""
    facts = None
    for pc in predecessors:
        try:
            older = company_facts(pc, budget)
        except NotFound:
            continue
        facts = older if facts is None else merge_facts(facts, older)
    try:
        own = company_facts(cik, budget)
        facts = own if facts is None else merge_facts(facts, own)
    except NotFound:
        if facts is None:
            raise
    log = []
    pend = pending_filings(fl, facts)
    for f in pend[-cfg("data.edgar.max_pending_filings"):]:
        rec = {"form": f["form"], "date": f["filingDate"], "accn": f["accessionNumber"],
               "report_date": f.get("reportDate"), "read": False, "reason": None}
        try:
            extra = instance_facts(cik, f, budget)
        except Unavailable as e:
            rec["reason"] = str(e)
            log.append(rec)
            continue
        if extra.get("facts"):
            facts = merge_facts(facts, extra)
            rec["read"] = True
        else:
            rec["reason"] = extra.get("reason") or "la instancia no trae hechos de los estados"
        log.append(rec)
    for f in pend[:-cfg("data.edgar.max_pending_filings")]:
        log.append({"form": f["form"], "date": f["filingDate"], "accn": f["accessionNumber"],
                    "report_date": f.get("reportDate"), "read": False,
                    "reason": f"más de {cfg('data.edgar.max_pending_filings')} filings pendientes: solo los últimos"})
    return facts, sorted(log, key=lambda r: (r["date"], r["accn"]))


# ───────────────────────── resolución de un campo por periodo ─────────────────────────

def _date(s: str) -> _dt.date:
    return _dt.date.fromisoformat(s)


def _days(f: Dict[str, Any]) -> Optional[int]:
    return (_date(f["end"]) - _date(f["start"])).days if f.get("start") else None


def taxonomy(facts: Dict[str, Any]) -> Optional[str]:
    """Taxonomía de los estados vigentes: la del `Assets` más reciente (TM pasó de us-gaap a ifrs-full)."""
    f = facts.get("facts") or {}
    last = {tx: max((x["end"] for fs in f.get(tx, {}).get("Assets", {}).get("units", {}).values() for x in fs),
                    default="") for tx in FINANCIAL_TAXONOMIES}
    best = max(FINANCIAL_TAXONOMIES, key=lambda tx: (last[tx], len(f.get(tx, {}))))
    return best if f.get(best) else None


def reporting_unit(facts: Dict[str, Any], tax: Optional[str]) -> Optional[str]:
    """Moneda de los estados: la unidad de `Assets` con los hechos más recientes."""
    units = (facts.get("facts") or {}).get(tax or "", {}).get("Assets", {}).get("units", {})
    best = max(units.items(), key=lambda kv: max((x["end"] for x in kv[1]), default=""), default=None)
    return best[0] if best else None


def candidates(facts: Dict[str, Any], field: str) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """[(concepto, hechos en la moneda de los estados)] del campo, del preferido al último: primero el que llega al
    ejercicio más reciente (un concepto que dejó de etiquetarse queda detrás), a igualdad el orden de CONCEPTS."""
    tax = taxonomy(facts)
    unit = reporting_unit(facts, tax)
    if tax is None or unit is None:
        return []
    kind, _sign, us, ifrs = CONCEPTS[field]
    out = []
    for i, c in enumerate(us if tax == "us-gaap" else ifrs):
        fs = (facts.get("facts") or {}).get(tax, {}).get(c, {}).get("units", {}).get(unit) or []
        if not fs:
            continue
        ann = [f for f in fs if f.get("form") in ANNUAL_FORMS and (kind == "stock" or 350 <= (_days(f) or 0) <= 380)]
        out.append((max((f["end"] for f in (ann or fs)), default=""), -i, f"{tax}:{c}", fs))
    return [(c, fs) for _e, _i, c, fs in sorted(out, reverse=True)]


def _current(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    return max(group, key=lambda f: (f.get("filed") or "", f.get("accn") or ""))


def _near(a: str, b: _dt.date, tol: int) -> bool:
    return abs((_date(a) - b).days) <= tol


def stock_at(fs: List[Dict[str, Any]], at: _dt.date, tol: int) -> Optional[Dict[str, Any]]:
    """Saldo a la fecha `at` (± tol días; el más cercano y, en él, el filing más reciente)."""
    near = [f for f in fs if not f.get("start") and _near(f["end"], at, tol)]
    if not near:
        return None
    best = min(abs((_date(f["end"]) - at).days) for f in near)
    f = _current([f for f in near if abs((_date(f["end"]) - at).days) == best])
    return {"value": f["val"], "period": f["end"], "how": f"saldo al {f['end']}", "accns": [f["accn"]]}


def flow_ttm(fs: List[Dict[str, Any]], end: _dt.date, tol: int) -> Optional[Dict[str, Any]]:
    """Doce meses que acaban en `end` (± tol días): el ejercicio que acaba ahí o, si no, el ejercicio anterior más el
    acumulado del año hasta `end` menos el mismo acumulado del año anterior (la práctica estándar con 10-Q y 6-K)."""
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for f in fs:
        if f.get("start"):
            groups.setdefault((f["start"], f["end"]), []).append(f)
    cur = {k: _current(g) for k, g in groups.items()}

    def dur(k):
        return (_date(k[1]) - _date(k[0])).days
    fy = [k for k in cur if _near(k[1], end, tol) and 350 <= dur(k) <= 380]
    if fy:
        k = min(fy, key=lambda k: (abs((_date(k[1]) - end).days), -int(cur[k].get("filed", "0").replace("-", "") or 0)))
        f = cur[k]
        return {"value": f["val"], "period": f"{k[0]}/{k[1]}", "how": f"ejercicio {k[0]} a {k[1]}", "accns": [f["accn"]]}
    ytd = sorted((k for k in cur if _near(k[1], end, tol) and 80 <= dur(k) < 350), key=dur, reverse=True)
    for k in ytd:
        s = _date(k[0])
        prev_fy = [p for p in cur if 350 <= dur(p) <= 380 and _near(p[1], s - _dt.timedelta(days=1), tol)]
        prev_ytd = [p for p in cur if abs(dur(p) - dur(k)) <= tol
                    and _near(p[1], _date(k[1]) - _dt.timedelta(days=365), tol)
                    and _near(p[0], s - _dt.timedelta(days=365), tol)]
        if prev_fy and prev_ytd:
            a, b, c = cur[prev_fy[0]], cur[k], cur[prev_ytd[0]]
            return {"value": a["val"] + b["val"] - c["val"], "period": f"TTM a {k[1]}",
                    "how": (f"ejercicio {prev_fy[0][0]} a {prev_fy[0][1]} + acumulado {k[0]} a {k[1]} − acumulado "
                            f"{prev_ytd[0][0]} a {prev_ytd[0][1]}"),
                    "accns": sorted({a["accn"], b["accn"], c["accn"]})}
    return None


def field_value(facts: Dict[str, Any], field: str, at: _dt.date, tol: int) -> Optional[Dict[str, Any]]:
    """Valor del campo para el periodo que acaba en `at` (flujo: doce meses; saldo: a esa fecha), en la moneda de
    los estados y con el signo de Yahoo, del concepto preferido (`candidates`). No se salta a otro concepto si al
    preferido le falta el periodo: las alternativas no siempre son la misma definición (HSBC: la amortización del
    inmovilizado solo va en el 20-F; la del 6-K semestral incluye deterioros)."""
    kind, sign = CONCEPTS[field][0], CONCEPTS[field][1]
    cands = candidates(facts, field)
    if not cands:
        return None
    concept, fs = cands[0]
    r = stock_at(fs, at, tol) if kind == "stock" else flow_ttm(fs, at, tol)
    if r is None:
        return None
    r["value"] = sign * r["value"]
    r.update(concept=concept, unit=reporting_unit(facts, taxonomy(facts)))
    return r


def debt_part(facts: Dict[str, Any], part: str, at: _dt.date, tol: int,
              latest_before: bool = False) -> Optional[Dict[str, Any]]:
    """Saldo de un componente de la deuda (DEBT_PARTS) a la fecha `at`: el total etiquetado o la suma de corriente y
    no corriente. Con `latest_before`, si no hay saldo a esa fecha, el del último informe ANUAL anterior (DUK solo
    etiqueta sus arrendamientos en el 10-K)."""
    tax = taxonomy(facts)
    unit = reporting_unit(facts, tax)
    names = DEBT_PARTS.get(tax or "", {}).get(part)
    if not names or unit is None:
        return None

    def fs(c):
        return (facts.get("facts") or {}).get(tax, {}).get(c, {}).get("units", {}).get(unit) or []

    def at_date(d, annual_only=False):
        sel = (lambda L: [f for f in L if f.get("form") in ANNUAL_FORMS]) if annual_only else (lambda L: L)
        whole = stock_at(sel(fs(names[0])), d, tol)
        if whole is not None:
            return whole["value"], [names[0]], whole["period"], whole["accns"]
        parts = [stock_at(sel(fs(c)), d, tol) for c in names[1:]]
        got = [(c, p) for c, p in zip(names[1:], parts) if p is not None]
        if not got:
            return None
        return (sum(p["value"] for _c, p in got), [c for c, _p in got], got[0][1]["period"],
                sorted({a for _c, p in got for a in p["accns"]}))
    r = at_date(at)
    basis = "corte"
    if r is None and latest_before:
        ends = sorted({f["end"] for c in names for f in fs(c) if not f.get("start") and f.get("form") in ANNUAL_FORMS
                       and _date(f["end"]) <= at}, reverse=True)
        for e in ends:
            r = at_date(_date(e), annual_only=True)
            if r is not None:
                basis = "ultimo_anual"
                break
    if r is None:
        return None
    v, used, period, accns = r
    return {"value": v, "concepts": [f"{tax}:{c}" for c in used], "period": period, "basis": basis,
            "accns": accns, "unit": unit}


def latest_fy_end(facts: Dict[str, Any]) -> Optional[str]:
    """Fin del último ejercicio con balance anual en los hechos (Assets de un formulario anual)."""
    tax = taxonomy(facts)
    fs = (facts.get("facts") or {}).get(tax or "", {}).get("Assets", {}).get("units", {}).get(
        reporting_unit(facts, tax) or "", [])
    return max((f["end"] for f in fs if f.get("form") in ANNUAL_FORMS), default=None)


# ───────────────────────── portada del 20-F: factor ADR (regla B) ─────────────────────────

_NUM_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
              "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
              "twenty-five": 25, "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100}
_FRACTIONS = {"half": 2, "third": 3, "quarter": 4, "fourth": 4, "fifth": 5, "tenth": 10, "twentieth": 20}
_RATIO_RE = re.compile(
    r"represent(?:s|ing|ed)?\s*(?:by\s*)?"
    r"(?P<n>\d+(?:\.\d+)?|[a-z]+(?:-[a-z]+)?)(?:\s*\(\d+(?:\.\d+)?\))?"
    r"(?:[\s-]+(?P<frac>half|third|quarter|fourth|fifth|tenth|twentieth)s?\s+of\s+(?:one|an?))?"
    r"\s+(?P<rest>[^.;]{0,80}?)\bshares?")
_TITLE_RE = re.compile(r"Title of 12\(b\) Security\s+(.*?)(?=\s+(?:Trading Symbol|No Trading Symbol Flag|"
                       r"Security Exchange Name|Document|Entity|Title of 12\(b\) Security|American Depositary "
                       r"Shares \[Member\])|$)")


def parse_ratio(title: str) -> Optional[float]:
    """Acciones ordinarias por ADS en un título del 12(b) ("American Depositary Shares, each representing four 25p
    ordinary shares" → 4; "… one half of one ordinary share" → 0.5). None si el título no lo dice."""
    m = _RATIO_RE.search(title.lower())
    if not m:
        return None
    n = m.group("n")
    num = float(n) if n[0].isdigit() else _NUM_WORDS.get(n)
    if num is None or num <= 0:
        return None
    if m.group("frac"):
        num = num / _FRACTIONS[m.group("frac")]
    return num


def parse_cover(html_text: str) -> Optional[Dict[str, Any]]:
    """Factor ADR de la página de portada (R1) de un 20-F/40-F: el de los títulos del 12(b) que son depositary
    shares; None si ninguno lo dice o si dicen factores distintos."""
    import html as _html
    text = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", html_text)))
    titles = [t.strip() for t in _TITLE_RE.findall(text) if "depositary" in t.lower()]
    found = {}
    for t in titles:
        r = parse_ratio(t)
        if r is not None:
            found.setdefault(r, t)
    if len(found) != 1:
        return None
    (factor, title), = found.items()
    return {"factor": factor, "title": title}


def cover_factor(cik: int, fl: List[Dict[str, Any]], budget: Budget) -> Optional[Dict[str, Any]]:
    """Factor de la portada del último 20-F/40-F del emisor (caché por número de filing), o None."""
    annual = [f for f in fl or [] if f["form"] in FOREIGN_ANNUAL_FORMS]
    if not annual:
        return None
    f = annual[0]
    acc = f["accessionNumber"].replace("-", "")
    found = _cached(f"cover:{acc}", cfg("data.edgar.facts_ttl_s"), lambda: parse_cover(
        _get(ARCHIVE_URL.format(cik=cik, acc=acc, name="R1.htm"), budget).decode("utf-8", "replace")))
    if found is None:
        return None
    return {**found, "form": f["form"], "date": f["filingDate"], "accn": f["accessionNumber"]}


# ───────────────────────── el análisis: etapa 1 y etapa 2 en un hilo ─────────────────────────

def _predecessors(ticker: str) -> Tuple[int, ...]:
    return tuple(int(c) for c in (cfg("data.edgar.predecessors") or {}).get(ticker.upper(), []))


def fetch(ticker: str, stage1: Optional[Future] = None) -> Dict[str, Any]:
    """Todo lo de EDGAR de un análisis, dentro del presupuesto. Etapa 1 (se publica en `stage1` en cuanto está):
    {status, reason, cik, title, filings, cover}. Etapa 2: `facts` (companyfacts y los pendientes leídos),
    `facts_status` (ok | sin_estados | no_disponible), `facts_reason` y `pending_filings`."""
    t0 = time.monotonic()

    def publish(res):
        if stage1 is not None and not stage1.done():
            stage1.set_result({k: v for k, v in res.items() if k != "facts"})
        return res
    st = status()
    if not st["enabled"]:
        return publish({"status": "desactivado", "reason": st["reason"], "cik": None, "filings": None})
    budget = Budget()
    res: Dict[str, Any] = {"status": "no_disponible", "reason": None, "cik": None, "filings": None}
    try:
        ent = cik_for(ticker, budget)
        if ent is None:
            return publish({"status": "sin_cik", "reason": "el ticker no figura en la lista de emisores de la SEC",
                            "cik": None, "filings": None, "latency_s": time.monotonic() - t0})
        fl = filings(ent["cik"], budget)
        res = {"status": "ok", "reason": None, "cik": ent["cik"], "title": ent.get("title"), "filings": fl,
               "cover": None, "cover_reason": None}
        from currency import official_factor
        if official_factor(ticker) is None and foreign_filer(fl):
            try:
                res["cover"] = cover_factor(ent["cik"], fl, budget)
                if res["cover"] is None:
                    res["cover_reason"] = "la portada del 20-F no dice cuántas acciones representa cada ADS"
            except Unavailable as e:
                res["cover_reason"] = str(e)
        publish(res)
        spec = (cfg("data.edgar.captive") or {}).get(ticker.upper())
        if spec:
            try:
                res["captive"] = captive_debt(ent["cik"], fl, budget, spec)
            except Unavailable as e:
                res["captive"] = {"status": "no_disponible", "reason": str(e)}
        try:
            res["facts"], res["pending_filings"] = facts_with_pending(ent["cik"], fl, budget, _predecessors(ticker))
            res["facts_status"], res["facts_reason"] = "ok", None
        except NotFound:
            res["facts"], res["facts_status"] = None, "sin_estados"
            res["facts_reason"] = "el emisor no tiene estados XBRL en EDGAR (companyfacts no existe)"
        except Unavailable as e:
            res["facts"], res["facts_status"], res["facts_reason"] = None, "no_disponible", str(e)
        res["latency_s"] = time.monotonic() - t0
        logger.info(f"[EDGAR] {ticker}: CIK {ent['cik']}, {len(fl)} filings, hechos {res['facts_status']} "
                    f"en {res['latency_s']:.2f}s")
        return res
    except Unavailable as e:
        res.update(status="no_disponible", reason=str(e), latency_s=time.monotonic() - t0)
        return publish(res)
    except Exception as e:  # una respuesta inesperada de la SEC no rompe el análisis
        logger.warning(f"[EDGAR] {ticker}: {type(e).__name__}: {e}")
        res.update(status="no_disponible", reason=f"respuesta inesperada de EDGAR ({type(e).__name__})",
                   latency_s=time.monotonic() - t0)
        return publish(res)


def start(ticker: str):
    stage1: Future = Future()
    with _lock:
        _inflight[ticker.upper()] = stage1
    return _pool.submit(fetch, ticker, stage1)


def _wait_s() -> float:
    return cfg("data.edgar.budget_s") + cfg("data.edgar.timeout_s")


def cover_factor_for(ticker: str) -> Optional[Dict[str, Any]]:
    """Factor de la portada del 20-F del análisis en curso de `ticker` (espera a la etapa 1), o None."""
    with _lock:
        fut = _inflight.get(ticker.upper())
    if fut is None:
        return None
    try:
        return (fut.result(timeout=_wait_s()) or {}).get("cover")
    except Exception:  # tiempo agotado: el factor sale de la regla A
        return None


def collect(future, ticker: Optional[str] = None) -> Dict[str, Any]:
    if ticker:
        with _lock:
            _inflight.pop(ticker.upper(), None)
    if future is None:
        return {"status": "no_disponible", "reason": "no se lanzó la consulta", "cik": None, "filings": None}
    try:
        return future.result(timeout=_wait_s())
    except Exception as e:  # tiempo agotado u otro fallo del hilo
        return {"status": "no_disponible", "reason": f"{type(e).__name__}: {e}", "cik": None, "filings": None}


def summary(ed: Dict[str, Any]) -> Dict[str, Any]:
    """Registro para data_provenance.edgar (sin los hechos ni la lista de filings)."""
    out = {k: ed.get(k) for k in ("status", "reason", "cik", "title")}
    for k in ("facts_status", "facts_reason", "pending_filings", "cover", "cover_reason", "captive"):
        if ed.get(k) is not None:
            out[k] = ed[k]
    return out


def pending_results(fl: Optional[List[Dict[str, Any]]], cut: Optional[str]) -> Optional[Dict[str, Any]]:
    """F2_PRECEDENCIA §1.1: resultados publicados después del corte y aún no incorporados.

    Un 10-Q/10-K/20-F/40-F (o un 6-K con XBRL) cuyo periodo es posterior al corte, o un 8-K del apartado 2.02
    (Results of Operations) presentado después del filing periódico que cubre el corte (sin ese filing, después del
    corte). Un 8-K no avanza el corte: solo se avisa. Devuelve el más reciente o None."""
    if not fl or not cut:
        return None
    tol = _dt.timedelta(days=cfg("data.edgar.report_date_tolerance_days"))
    c = _dt.date.fromisoformat(cut)

    def rd(f):
        try:
            return _dt.date.fromisoformat(f["reportDate"]) if f.get("reportDate") else None
        except ValueError:
            return None
    covering = [f for f in fl if (f["form"] in ANNUAL_OR_QUARTERLY or (f["form"].startswith("6-K") and f["isXBRL"]))
                and rd(f) and abs(rd(f) - c) <= tol]
    base = max([f["filingDate"] for f in covering] + [cut])
    newer = [f for f in fl if (f["form"] in ANNUAL_OR_QUARTERLY or (f["form"].startswith("6-K") and f["isXBRL"]))
             and rd(f) and rd(f) > c + tol]
    results_8k = [f for f in fl if f["form"] in ("8-K", "8-K/A") and "2.02" in (f.get("items") or "")
                  and f["filingDate"] > base]
    cands = newer + results_8k
    if not cands:
        return None
    f = max(cands, key=lambda x: (x["filingDate"], x["accessionNumber"]))
    return {"date": f["filingDate"], "form": f["form"], "items": f.get("items") or None,
            "accn": f["accessionNumber"], "report_date": f.get("reportDate"), "as_of": cut, "source": "SEC EDGAR"}


def foreign_filer(fl: Optional[List[Dict[str, Any]]]) -> bool:
    """El emisor presenta 20-F/40-F (sus resultados van por 6-K, sin el apartado 2.02 de un 8-K)."""
    return any(f["form"] in ("20-F", "20-F/A", "40-F", "40-F/A") for f in fl or [])


def pending_from_calendar(entries: Optional[List[Dict[str, Any]]], cut: Optional[str],
                          today: _dt.date) -> Optional[Dict[str, Any]]:
    """F2_PRECEDENCIA §1.1, paso 2: sin 8-K, la fecha de resultados del proveedor. Una publicación con resultados
    (`epsActual`) más de `calendar_min_lag_days` días después del corte y no posterior a hoy es de un periodo que el
    análisis aún no tiene."""
    if not entries or not cut:
        return None
    c = _dt.date.fromisoformat(cut)
    lag = _dt.timedelta(days=cfg("data.edgar.calendar_min_lag_days"))
    hits = []
    for e in entries:
        try:
            d = _dt.date.fromisoformat(str(e.get("date")))
        except ValueError:
            continue
        if c + lag < d <= today and e.get("epsActual") is not None:
            hits.append(d)
    if not hits:
        return None
    return {"date": max(hits).isoformat(), "form": None, "items": None, "accn": None, "as_of": cut,
            "source": "calendario de resultados del proveedor (Finnhub)"}


def reset() -> None:
    """Vacía las cachés (tests)."""
    with _lock:
        _cache.clear()
        _inflight.clear()
