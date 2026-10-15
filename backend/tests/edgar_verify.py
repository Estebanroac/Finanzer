"""
Fase 2a (T3): verificación del pipeline frente a SEC EDGAR (la medida de F1, "dato correcto").

Para cada ticker del panel con extracto de EDGAR (tests/fixtures/edgar/<T>.json) corre el pipeline en replay de sus
fixtures, captura lo que usa (FinancialStatements, info y data_provenance) y lo compara campo a campo con EDGAR
**en el mismo periodo**:

  · flujos en TTM → FY + acumulado del año − el mismo acumulado del año anterior (o el FY si coincide);
  · flujos del último ejercicio → el FY de EDGAR que termina ese año;
  · saldos → el balance a la misma fecha (±14 días: Yahoo redondea al fin de mes);
  · por acción y acciones → en la clase del precio (ADR) con el factor OFICIAL del depositario (F2_EDGAR_DIAGNOSTICO
    §5), en la moneda de los estados.

La conversión de moneda del pipeline se deshace con sus propios tipos (data_provenance.currency): el saldo con el de
su fecha, el ejercicio con el de su año, el TTM con `ttm_rate` (media de los 4 trimestres; aproximación ≤ 0.5% en
los extranjeros con TTM).

Tolerancias (PLAN §3): ±1% estados y acciones; ±2% BPA y dividendo por acción; ratios ±2% relativo o ±0.5 pp.
Cada discrepancia se clasifica buscando qué valor de EDGAR sí coincide: otro periodo (periodo), otra etiqueta o
combinación (definición), el valor antes de la reexpresión (perímetro), ×/÷ 100 o 1000 (unidad), otro factor de
clase (factor ADR); si ninguno coincide, el valor no existe en los estados (fuente errónea). Sin dato en EDGAR para
ese periodo: "EDGAR falta" (fuera del porcentaje).

Efecto en el veredicto (--whatif): repite el análisis sustituyendo, en lo que lee el pipeline (info), los campos
fuera de tolerancia por el valor de EDGAR (convertido con los mismos tipos y el factor oficial), y compara los
niveles de calidad y de precio, la confianza y el arquetipo.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/edgar_verify.py --whatif --out <dir>      # resultado.json + resumen.md

No toca el motor: todo es replay de fixtures con envoltorios de lectura.
"""
import argparse
import copy
import datetime as dt
import json
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edgar as E  # noqa: E402
import fixture_backend as fb  # noqa: E402

# Acciones ordinarias por unidad que cotiza (F2_EDGAR_DIAGNOSTICO §5: 20-F y F-6; BRK-B: clase B = 1/1500 de A).
OFFICIAL_FACTOR = {"TSM": 5, "ASML": 1, "NVO": 1, "BCS": 4, "HSBC": 5, "SHEL": 2, "UL": 1, "TM": 10,
                   "BRK-B": 1 / 1500}
FOREIGN = {"TSM", "ASML", "NVO", "BCS", "HSBC", "SHEL", "UL", "TM"}
TOL = {"estado": 0.01, "acciones": 0.01, "por_accion": 0.02, "ratio": 0.02}
RATIO_ABS_PP = 0.005
DAY_TOL = 14

# campo del pipeline → (atributo de FinancialStatements, clave de info, campo de EDGAR, tipo, grupo)
FIELDS = [
    ("revenue", "revenue", "totalRevenue", "revenue", "flow", "estado"),
    ("gross_profit", "gross_profit", "grossProfits", "gross_profit", "flow", "estado"),
    ("operating_income", "operating_income", "operatingIncome", "operating_income", "flow", "estado"),
    ("net_income", "net_income", "netIncome", "net_income", "flow", "estado"),
    ("interest_expense", "interest_expense", "interestExpense", "interest_expense", "flow", "estado"),
    ("depreciation", "depreciation", "depreciation", "depreciation", "flow", "estado"),
    ("operating_cash_flow", "operating_cash_flow", "operatingCashflow", "operating_cash_flow", "flow", "estado"),
    ("capex", "capex", "capitalExpenditures", "capex", "flow", "estado"),
    ("dividends_paid", "dividends_paid", "dividendsPaid", "dividends_paid", "flow", "estado"),
    ("total_assets", "total_assets", "totalAssets", "total_assets", "stock", "estado"),
    ("current_assets", "current_assets", "totalCurrentAssets", "current_assets", "stock", "estado"),
    ("cash", "cash", "cash", "cash", "stock", "estado"),
    ("inventories", "inventories", "inventory", "inventories", "stock", "estado"),
    ("total_liabilities", "total_liabilities", "totalLiab", "total_liabilities", "stock", "estado"),
    ("current_liabilities", "current_liabilities", "totalCurrentLiabilities", "current_liabilities", "stock",
     "estado"),
    ("long_term_debt", "long_term_debt", "longTermDebt", "long_term_debt", "stock", "estado"),
    ("total_debt", "total_debt", "totalDebt", "total_debt", "stock", "estado"),
    ("total_equity", "total_equity", "totalStockholderEquity", "equity_parent", "stock", "estado"),
    ("retained_earnings", "retained_earnings", "retainedEarnings", "retained_earnings", "stock", "estado"),
    ("eps", "eps", "trailingEps", "diluted_eps", "per_share", "por_accion"),
    ("dividend_per_share", "dividend_per_share", "dividendRate", "dividend_per_share", "per_share", "por_accion"),
    ("shares_outstanding", "shares_outstanding", "sharesOutstanding", "shares_outstanding", "shares", "acciones"),
]
# Series anuales (_statements_fy): las que usan Piotroski, Altman, el CAGR y el histórico. Índices 0 y 1 (FY0, FY1).
FY_SERIES = [
    ("revenue", "revenue", "flow"), ("gross_profit", "gross_profit", "flow"),
    ("operating_income", "operating_income", "flow"), ("net_income", "net_income", "flow"),
    ("diluted_eps", "diluted_eps", "per_share"), ("operating_cash_flow", "operating_cash_flow", "flow"),
    ("capital_expenditure", "capex", "flow"), ("total_assets", "total_assets", "stock"),
    ("current_assets", "current_assets", "stock"), ("current_liabilities", "current_liabilities", "stock"),
    ("total_liabilities", "total_liabilities", "stock"), ("stockholders_equity", "equity_parent", "stock"),
    ("retained_earnings", "retained_earnings", "stock"), ("ordinary_shares", "shares_outstanding", "shares"),
]
# Campos que XBRL da como pago positivo y Yahoo como salida negativa: se comparan en valor absoluto. El resto conserva
# el signo (una pérdida es negativa en las dos fuentes).
ABS_FIELDS = {"capex", "dividends_paid", "interest_expense", "at1_coupons", "buybacks"}

RATIO_INPUTS = {"gross_margin": ["gross_profit", "revenue"], "operating_margin": ["operating_income", "revenue"],
                "net_margin": ["net_income", "revenue"], "roe": ["net_income", "total_equity"],
                "roa": ["net_income", "total_assets"], "current_ratio": ["current_assets", "current_liabilities"],
                "debt_to_equity": ["total_debt", "total_equity"], "payout_ratio": ["dividends_paid", "net_income"],
                "dividend_yield": ["dividend_per_share"]}
RATIOS = ["gross_margin", "operating_margin", "net_margin", "roe", "roa", "current_ratio", "debt_to_equity",
          "payout_ratio", "dividend_yield"]


# ───────────────────────────── EDGAR: valores por periodo ─────────────────────────────

def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def _near(a: str, b, days=DAY_TOL) -> bool:
    return abs((_d(a) - (_d(b) if isinstance(b, str) else b)).days) <= days


class Edgar:
    def __init__(self, ext: Dict[str, Any]):
        self.ext = ext
        self.tax = ext.get("taxonomy") or E.taxonomy(ext)
        self.unit = E.reporting_unit(ext, self.tax)

    # hechos de un concepto "tax:Concepto" en la unidad que toca
    def facts(self, concept: str, kind: str) -> List[Dict[str, Any]]:
        tx, c = concept.split(":")
        units = self.ext.get("facts", {}).get(tx, {}).get(c, {}).get("units", {})
        if kind == "shares":
            return units.get("shares", [])
        if kind == "per_share":
            return units.get(f"{self.unit}/shares", [])
        return units.get(self.unit, [])

    def concepts(self, field: str) -> List[str]:
        spec = E.CONCEPTS[field]
        alts = [f"{self.tax}:{c}" for c in spec.get("us" if self.tax == "us-gaap" else "ifrs", [])]
        alts += [f"dei:{c}" for c in spec.get("dei", [])]
        return [c for c in alts if self.facts(c, spec["kind"])]

    def _period(self, fs, start: Optional[str], end: str):
        """Grupo de hechos de un periodo (inicio y fin ±14 días; sin inicio = saldo)."""
        g = [f for f in fs if _near(f["end"], end) and
             ((start is None and not f.get("start")) or (start and f.get("start") and _near(f["start"], start)))]
        return g or None

    def fy(self, fs, label_year: Optional[int] = None, end: Optional[str] = None):
        """Ejercicio: el FY que termina en el año de la etiqueta de Yahoo (ventana 15-ene a 15-ene) o cerca de `end`."""
        cand = {}
        for f in fs:
            if f.get("start") and E.span(f) == "FY" and f.get("form") in E.ANNUAL_FORMS:
                e = _d(f["end"])
                ok = (_near(f["end"], end) if end else
                      dt.date(label_year, 1, 15) < e <= dt.date(label_year + 1, 1, 15))
                if ok:
                    cand.setdefault((f["start"], f["end"]), []).append(f)
        if not cand:
            return None
        return cand[max(cand)]

    def ttm(self, fs, end: str):
        """TTM que termina en `end`: FY si coincide; si no, FY anterior + acumulado − acumulado del año previo."""
        fys = sorted({(f["start"], f["end"]) for f in fs if f.get("start") and E.span(f) == "FY"}, key=lambda p: p[1])
        same = [p for p in fys if _near(p[1], end)]
        if same:
            g = self._period(fs, *same[-1])
            return E.current(g)["val"], f"FY {same[-1][1]}", [g]
        prev = [p for p in fys if _d(p[1]) < _d(end) - dt.timedelta(days=DAY_TOL)]
        if not prev:
            return None, "sin FY previo", []
        fy_s, fy_e = prev[-1]
        ytd_start = (_d(fy_e) + dt.timedelta(days=1)).isoformat()
        ytd = self._period(fs, ytd_start, end)
        if not ytd:
            return None, f"sin acumulado {ytd_start}→{end}", []
        ytd_f = E.current(ytd)
        n_days = E.days(ytd_f)
        p_end = (_d(ytd_f["end"]) - dt.timedelta(days=364)).isoformat()
        p_start = (_d(ytd_f["start"]) - dt.timedelta(days=364)).isoformat()
        prior = self._period(fs, p_start, p_end)
        fy_g = self._period(fs, fy_s, fy_e)
        if not prior or not fy_g:
            return None, f"sin acumulado del año anterior ({p_start}→{p_end})", []
        v = E.current(fy_g)["val"] + ytd_f["val"] - E.current(prior)["val"]
        return v, f"FY {fy_e} + {n_days}d a {ytd_f['end']} − {n_days}d a {E.current(prior)['end']}", [fy_g, ytd, prior]

    def fy_end(self, label_year: Optional[int]) -> Optional[str]:
        """Fecha de cierre del ejercicio de esa etiqueta, con cualquier concepto de flujos que la traiga (un emisor
        puede cambiar de etiqueta de un año a otro: TSM pasó de Revenue a RevenueFromContractsWithCustomers)."""
        if not label_year:
            return None
        for f in ("revenue", "net_income", "operating_cash_flow", "pretax_income"):
            for c in self.concepts(f):
                g = self.fy(self.facts(c, "flow"), label_year=label_year)
                if g:
                    return E.current(g)["end"]
        return None

    def shares_latest(self):
        """Acciones en circulación más recientes entre todos los conceptos (portada o balance), > 0."""
        best = None
        for c in self.concepts("shares_outstanding"):
            for f in self.facts(c, "shares"):
                if f.get("val") and f["val"] > 0 and not f.get("start"):
                    k = (f["end"], f.get("filed", ""))
                    if best is None or k > best[0]:
                        best = (k, f["val"], c)
        return (best[1], best[2], f"a {best[0][0]}") if best else (None, None, "")

    def shares_at(self, date: Optional[str]):
        """Acciones en circulación al cierre: concepto del balance o, si no, la portada (dei) de hasta 120 días
        después (en los 20-F la portada es la fecha de cierre)."""
        if not date:
            return None, None, ""
        for c in self.concepts("shares_outstanding"):
            fs = self.facts(c, "shares")
            if c.startswith("dei"):
                g = [f for f in fs if 0 <= (_d(f["end"]) - _d(date)).days <= 120]
                if g:
                    f = min(g, key=lambda f: f["end"])
                    return f["val"], c, f"portada a {f['end']}"
            else:
                v, g = self.instant(fs, date)
                if v is not None:
                    return v, c, f"saldo a {date}"
        return None, None, "sin acciones al cierre"

    def at1_coupons(self, period) -> Optional[float]:
        """Cupones AT1: etiquetados, o beneficio de los propietarios − beneficio del accionista ordinario (IFRS)."""
        v, _, _, _ = self.value("at1_coupons", period)
        if v is not None:
            return abs(v)
        own = f"{self.tax}:ProfitLossAttributableToOwnersOfParent"
        ordi = f"{self.tax}:ProfitLossAttributableToOrdinaryEquityHoldersOfParentEntity"
        if self.facts(own, "flow") and self.facts(ordi, "flow"):
            a, _, _, _ = self.value("net_income", period, concept=own)
            b, _, _, _ = self.value("net_income", period, concept=ordi)
            if a is not None and b is not None and a - b > 0:
                return a - b
        return None

    def shares_avg(self, period) -> Optional[float]:
        """Acciones medias diluidas del último FY que termina antes o en el periodo."""
        for c in self.concepts("diluted_shares"):
            fs = [f for f in self.facts(c, "shares") if f.get("start") and E.span(f) == "FY"]
            if period[0] in ("ttm", "instant") and period[1]:
                fs = [f for f in fs if _d(f["end"]) <= _d(period[1]) + dt.timedelta(days=DAY_TOL)]
            if fs:
                return E.current([max(fs, key=lambda f: (f["end"], f.get("filed", "")))])["val"]
        return None

    def last_quarter(self, field: str, end: str) -> Optional[float]:
        """Valor del trimestre (3 meses) que termina en `end` (para el dividendo indicado = trimestral × 4)."""
        kind = E.CONCEPTS[field]["kind"]
        for c in self.concepts(field):
            g = [f for f in self.facts(c, kind) if f.get("start") and E.span(f) == "Q" and _near(f["end"], end)]
            if g:
                return E.current(g)["val"]
        return None

    def instant(self, fs, date: str):
        g = self._period(fs, None, date)
        return (E.current(g)["val"], g) if g else (None, None)

    def value(self, field: str, period: Tuple[str, Any], concept: Optional[str] = None):
        """(valor, concepto, detalle, grupos) del campo en el periodo, con la primera alternativa que lo tenga."""
        kind = E.CONCEPTS[field]["kind"]
        for c in ([concept] if concept else self.concepts(field)):
            fs = self.facts(c, kind)
            v, det, groups = self._at(fs, kind, period)
            if v is not None:
                return v, c, det, groups
        return None, None, "sin hecho en EDGAR para el periodo", []

    def _at(self, fs, kind, period):
        typ, ref = period
        if kind == "stock" or (kind == "shares" and typ != "dei"):
            if typ != "instant" or not ref:
                return None, "saldo sin fecha", []      # quien llama traduce el FY a su fecha de cierre
            v, g = self.instant(fs, ref)
            return v, f"saldo a {ref}", [g] if g else []
        if typ == "dei":
            if not fs:
                return None, "", []
            last = max(fs, key=lambda f: (f["end"], f.get("filed", "")))
            return last["val"], f"portada a {last['end']}", [[last]]
        if typ == "ttm":
            v, det, gs = self.ttm(fs, ref)
            return v, det, gs
        if typ == "fy":
            g = self.fy(fs, end=ref) if isinstance(ref, str) else self.fy(fs, label_year=ref)
            return (E.current(g)["val"], f"FY {E.current(g)['end']}", [g]) if g else (None, "", [])
        return None, "", []


def _sum_parts(ed: Edgar, period, parts: List[str]):
    tot, used = 0.0, []
    for c in parts:
        fs = ed.facts(c, "stock")
        if not fs:
            continue
        v, g = ed.instant(fs, period[1]) if period[0] == "instant" else (None, None)
        if v is not None:
            tot += abs(v)
            used.append(c.split(":")[1])
    return (tot if used else None), used


def debt_total(ed: Edgar, period):
    """Deuda financiera en EDGAR: largo plazo con su parte corriente + papel comercial + préstamos a corto (o, si el
    emisor solo etiqueta el total corriente, `DebtCurrent`, que ya los incluye). Los arrendamientos van aparte
    (`lease_parts`): la regla de coherencia con el EBITDA decide cuáles entran (F2_PRECEDENCIA §2.3). Sin la pieza de
    largo plazo en esa fecha no se inventa un total."""
    t = ed.tax

    def first(cs):
        for c in cs:
            v, _ = _sum_parts(ed, period, [f"{t}:{c}"])
            if v is not None:
                return v, [c]
        return None, []
    if t == "us-gaap":
        whole, u = first(["LongTermDebt"])
        if whole is not None:
            st, u2 = _sum_parts(ed, period, [f"{t}:CommercialPaper", f"{t}:ShortTermBorrowings",
                                              f"{t}:OtherShortTermBorrowings"])
            return whole + (st or 0), " + ".join(u + u2), f"saldo a {period[1]}"
        for nonc, cur in (("LongTermDebtNoncurrent", "LongTermDebtCurrent"),
                          ("LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsCurrent"),
                          ("NotesPayable", "LoansPayable"), ("SeniorNotes", None), ("UnsecuredDebt", "SecuredDebt")):
            nv, u1 = first([nonc])
            if nv is None:
                continue
            dc, u3 = first(["DebtCurrent"])
            if dc is not None:                       # el total corriente ya lleva papel comercial y préstamos
                return nv + dc, " + ".join(u1 + u3), f"saldo a {period[1]}"
            cv, u2 = first([cur]) if cur else (None, [])
            st, u4 = _sum_parts(ed, period, [f"{t}:CommercialPaper", f"{t}:ShortTermBorrowings",
                                              f"{t}:OtherShortTermBorrowings"])
            return nv + (cv or 0) + (st or 0), " + ".join(u1 + u2 + u4), f"saldo a {period[1]}"
    else:
        whole, u = first(["Borrowings"])
        if whole is not None:
            return whole, u[0], f"saldo a {period[1]}"
        for parts in (["NoncurrentPortionOfNoncurrentBorrowings", "CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings"],
                      ["LongtermBorrowings", "ShorttermBorrowings"]):
            nv, u1 = first(parts[:1])
            if nv is None:
                continue
            tot, used = _sum_parts(ed, period, [f"{t}:{c}" for c in parts])
            return tot, " + ".join(used), f"saldo a {period[1]}"
    v, c, det, _ = ed.value("total_debt_reported", period)
    return v, c, det


def cash_total(ed: Edgar, period):
    """La fila de Yahoo que usa el motor: caja + inversiones a corto plazo (o su total etiquetado)."""
    t = ed.tax
    tot, used = _sum_parts(ed, period, [f"{t}:CashCashEquivalentsAndShortTermInvestments"])
    if tot is not None:
        return tot, "CashCashEquivalentsAndShortTermInvestments", f"saldo a {period[1]}"
    c, cc, det, _ = ed.value("cash", period)
    sti, c2, _, _ = ed.value("short_term_investments", period)
    if c is not None and sti is not None:
        return c + sti, f"{cc} + {c2}", det
    return c, cc, det


def lease_parts(ed: Edgar, period) -> Dict[str, float]:
    """Pasivos por arrendamiento EN BALANCE a esa fecha (conceptos de balance: el total o corriente + no corriente).
    Por norma excluyen los arrendamientos firmados y aún no iniciados, que van en notas o en compromisos (MSFT:
    329.1 mil millones de USD solo en texto; AMZN: tabla de compromisos). No usar las tablas de pagos futuros."""
    t = ed.tax
    out = {}
    if t == "us-gaap":
        for lab, whole, parts in (("operativos", "OperatingLeaseLiability", ("OperatingLeaseLiabilityCurrent",
                                                                             "OperatingLeaseLiabilityNoncurrent")),
                                  ("financieros", "FinanceLeaseLiability", ("FinanceLeaseLiabilityCurrent",
                                                                            "FinanceLeaseLiabilityNoncurrent"))):
            v, _ = _sum_parts(ed, period, [f"{t}:{whole}"])
            if v is None:
                v, _ = _sum_parts(ed, period, [f"{t}:{x}" for x in parts])
            if v:
                out[lab] = v
    else:
        v, _ = _sum_parts(ed, period, [f"{t}:LeaseLiabilities"])
        if v is None:
            v, _ = _sum_parts(ed, period, [f"{t}:CurrentLeaseLiabilities", f"{t}:NoncurrentLeaseLiabilities"])
        if v:
            out["arrendamientos"] = v
    return out


def leases(ed: Edgar, period):
    t = ed.tax
    parts = ([f"{t}:OperatingLeaseLiability", f"{t}:FinanceLeaseLiability"] if t == "us-gaap"
             else [f"{t}:LeaseLiabilities"])
    v, used = _sum_parts(ed, period, parts)
    if v is None and t == "us-gaap":
        v, used = _sum_parts(ed, period, [f"{t}:OperatingLeaseLiabilityCurrent", f"{t}:OperatingLeaseLiabilityNoncurrent",
                                          f"{t}:FinanceLeaseLiabilityCurrent", f"{t}:FinanceLeaseLiabilityNoncurrent"])
    return v


class RawIndex:
    """Todos los conceptos del emisor (companyfacts crudo de la caché + filings que le faltan), para buscar en qué
    etiqueta está un valor del pipeline que no casa con la tabla. Solo lectura de la caché de tests/edgar.py."""

    def __init__(self):
        self._by_sym: Dict[str, Optional[Edgar]] = {}

    def _load(self, sym: str, ed: Edgar) -> Optional[Edgar]:
        if sym in self._by_sym:
            return self._by_sym[sym]
        cik = ed.ext.get("cik")
        full = None
        try:
            if cik:
                full, _ = E.company_facts(int(cik))
                for pc in E.PREDECESSORS.get(sym, []):
                    older, _ = E.company_facts(pc)
                    if older:
                        full = E.merge_facts(full, older) if full else older
                if full:
                    full, _ = E.supplement(int(cik), full)
                    full["taxonomy"] = ed.tax
        except Exception:
            full = None
        self._by_sym[sym] = Edgar(full) if full else None
        return self._by_sym[sym]

    KW = {"revenue": "Revenue|Income|Sales", "gross_profit": "Gross|Profit", "operating_income": "Operat|Profit",
          "net_income": r"^(?!.*Comprehensive).*(Profit|Income|Earnings)", "interest_expense": "Interest|FinanceCost",
          "depreciation": "Depreciat|Amorti", "operating_cash_flow": "Operat|CashFlow",
          "capex": "Purchase|Payment|Acquire|Capital|Additions", "dividends_paid": "Dividend|Distribution",
          "total_assets": "Assets", "current_assets": "Current|Assets", "cash": "Cash|Bank|Deposit",
          "inventories": "Inventor", "total_liabilities": "Liabilit", "current_liabilities": "Current|Liabilit",
          "long_term_debt": "Debt|Borrow|Notes|Bond|Subordinat", "total_debt": "Debt|Borrow|Notes|Bond|Subordinat",
          "equity_parent": "Equity", "retained_earnings": "Retained|Reserve|Earnings|Accumulated"}

    def search(self, sym: str, ed: Edgar, period, p: float, tol: float, efield: str = "") -> List[str]:
        raw = self._load(sym, ed)
        if raw is None or p is None:
            return []
        hits = []
        for tx in (raw.tax,):
            import re
            kw = self.KW.get(efield)
            for c, node in raw.ext.get("facts", {}).get(tx, {}).items():
                if kw and not re.search(kw, c):
                    continue
                fs = node.get("units", {}).get(raw.unit) or []
                if not fs:
                    continue
                typ, ref = period
                if typ == "instant":
                    v, _ = raw.instant(fs, ref)
                elif typ == "ttm":
                    v, _, _ = raw.ttm(fs, ref)
                elif typ == "fy":
                    g = raw.fy(fs, label_year=ref) if isinstance(ref, int) else None
                    v = E.current(g)["val"] if g else None
                else:
                    v = None
                if v is not None and v != 0 and within(p, abs(v) if efield in ABS_FIELDS else v, tol):
                    hits.append(c)
        return hits


RAW = RawIndex()
CTX: Dict[str, Any] = {}      # contexto del ticker en curso para las explicaciones (acciones actuales del pipeline)

# Causas que no se pueden derivar de una etiqueta: comprobadas a mano en los hechos crudos (F2_DISCREPANCIAS §4).
MANUAL = {
    ("BCS", "revenue"): ("definición", "ingresos totales del banco (margen de intereses + comisiones + resto); "
                         "EDGAR no los etiqueta: RevenueFromContractsWithCustomers son solo comisiones"),
    ("HSBC", "revenue"): ("definición", "ingresos totales del banco; EDGAR no los etiqueta"),
    ("BCS", "shares_outstanding"): ("periodo", "acciones de hoy tras las recompras (capitalización / precio = 13,331 "
                                    "millones de ordinarias) frente a la portada del 20-F a 2025-12-31 (13,867); la media "
                                    "del 1S-2026 ya es 13,645. El factor 4.154 del motor sale de este desfase"),
    ("NFLX", "depreciation"): ("definición", "Yahoo suma la amortización de contenidos (≈17 mil millones), que NFLX "
                               "etiqueta con un concepto propio; EDGAR solo publica la D&A de inmovilizado"),
    ("MSFT", "depreciation"): ("definición", "Yahoo suma amortizaciones que MSFT etiqueta con un concepto propio; "
                               "EDGAR solo publica la depreciación (34.3 mil millones en FY2026)"),
    ("BAC", "eps"): ("fuente errónea", "Finnhub 4.509 no es ningún TTM de EDGAR: a junio 4.33 diluido y 4.40 básico; "
                     "con el 3T-2026 del 8-K del 14-oct (0.91; ajustado 1.08) en lugar del 3T-2025 (1.06), 4.18 y "
                     "4.35"),
    ("V", "dividend_per_share"): ("definición", "dividendo indicado = 0.67 × 4 = 2.68. El TTM de EDGAR (0.67) no es "
                                  "fiable: V etiqueta el acumulado del año con el importe de un trimestre"),
    ("HSBC", "dividend_per_share"): ("unidad + factor ADR", "Finnhub 55.67 = peniques por acción ordinaria (línea de "
                                     "Londres), leído como USD por ADR. En USD por ADR: 0.5567 GBP × 1.34 × 5 ≈ 3.73 "
                                     "(DPA pagado de 2025 en EDGAR: 0.66 USD × 5 = 3.30)"),
    ("SHEL", "dividend_per_share"): ("unidad + factor ADR", "Finnhub 112.82 = peniques por acción ordinaria (Londres). En "
                                     "USD por ADR: 1.1282 GBP × 1.34 × 2 ≈ 3.02 (EDGAR: 1.432 USD × 2 = 2.86)"),
    ("UL", "dividend_per_share"): ("unidad + factor ADR", "Finnhub 164.99 = peniques por acción ordinaria (Londres). En "
                                   "USD por ADR: 1.6499 GBP × 1.34 ≈ 2.21 (EDGAR: 2.03 EUR × 1.13 = 2.29)"),
    ("TM", "shares_outstanding"): ("fuente errónea", "Yahoo: capitalización / precio = 1,178 millones de ADR = 11,778 "
                                   "millones de acciones, frente a 13,034 en circulación en el 20-F (2026-03-31) y en "
                                   "la portada. De ahí el factor implícito 11.07 frente al oficial 10"),
    ("UL", "FY1.ordinary_shares"): ("periodo", "consolidación de acciones con la escisión de helados (8 por 9: 2,452 "
                                    "millones a 2025-06-30 → 2,180 a 2025-12-31); Yahoo la aplica a 2024 (2,476 × 8/9 "
                                    "= 2,201)"),
    ("SHEL", "long_term_debt"): ("definición", "probable: préstamos a largo plazo (66,515 millones de USD, que en IFRS "
                                 "incluyen arrendamientos) sin la parte no corriente de los arrendamientos (≈ 24,300 = "
                                 "28,933 de arrendamientos totales − la corriente). SHEL solo etiqueta el total"),
    ("TSM", "retained_earnings"): ("definición", "utilidades no asignadas: sin la reserva legal ni la especial, que "
                                   "RetainedEarnings de la 20-F sí incluye (diferencia 398 mil millones de TWD)"),
}


# ───────────────────────────── pipeline (replay) ─────────────────────────────

def capture(sym: str, patch: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Análisis en replay + lo que usó el pipeline. `patch`: claves de info a sustituir (what-if)."""
    import data_fetcher
    import yf_adapter
    cap: Dict[str, Any] = {}
    with fb.replay(fb.fixtures_dir("panel")) as store:
        orig_info = yf_adapter.get_ticker_info
        orig_fd = data_fetcher.YahooFinanceFetcher.get_financial_data

        def info_wrap(s, *a, **kw):
            r = orig_info(s, *a, **kw)
            if patch and isinstance(r, dict) and s.upper() == sym:
                r.update(patch)
            cap.setdefault("info", r)
            return r

        def fd_wrap(self, s):
            r = orig_fd(self, s)
            cap["fs"] = r
            return r
        yf_adapter.get_ticker_info = info_wrap
        data_fetcher.get_ticker_info = info_wrap
        data_fetcher.YahooFinanceFetcher.get_financial_data = fd_wrap
        try:
            cap["analysis"] = fb.run_analysis(sym, store)
        finally:
            yf_adapter.get_ticker_info = orig_info
            data_fetcher.get_ticker_info = orig_info
            data_fetcher.YahooFinanceFetcher.get_financial_data = orig_fd
    return cap


def _rate_at(rates: Dict[str, float], date: str) -> Optional[float]:
    best = [(abs((_d(k) - _d(date)).days), v) for k, v in (rates or {}).items()]
    best = [b for b in best if b[0] <= DAY_TOL]
    return min(best)[1] if best else None


def _rate_year(rates: Dict[str, float], year: int) -> Optional[float]:
    c = [(k, v) for k, v in (rates or {}).items()
         if dt.date(year, 1, 15) < _d(k) <= dt.date(year + 1, 1, 15)]
    return c[-1][1] if c else None


def pipeline_period(key: str, src_stmt: str, prov: Dict[str, Any], ttm: Dict[str, Any], fy0: Optional[int]):
    """Periodo que usa el pipeline para una clave de info: ("ttm", fin) | ("fy", año) | ("instant", fecha)."""
    q = ttm.get("quarters") or {}
    end = (q.get(src_stmt) or q.get("inc") or [None])[0]
    if key in (ttm.get("ttm_fields") or []) and end:
        return ("ttm", end)
    if key in (ttm.get("last_quarter_fields") or []) and ttm.get("balance_date"):
        return ("instant", ttm["balance_date"])
    det = (prov.get(key) or {}).get("detail") or ""
    src = (prov.get(key) or {}).get("source")
    if "último trimestre (" in det:
        return ("instant", det.split("último trimestre (")[1][:10])
    if "TTM" in det and end:
        return ("ttm", end)
    if src == "finnhub":
        return ("ttm", end) if end else ("fy", fy0)
    return ("fy", fy0)


# ───────────────────────────── comparación ─────────────────────────────

def rel(a, b) -> Optional[float]:
    if a is None or b is None:
        return None
    if b == 0:
        return 0.0 if a == 0 else math.inf
    return (a - b) / abs(b)


def within(a, b, tol) -> bool:
    r = rel(a, b)
    return r is not None and abs(r) <= tol + 1e-9


def classify(p: float, cands: List[Tuple[str, str, Optional[float]]], tol: float):
    """Primera explicación (causa, detalle) cuyo valor de EDGAR coincide con el del pipeline."""
    for cause, label, v in cands:
        if v is not None and v != 0 and within(p, v, tol):
            return cause, label
    return None


def compare_ticker(sym: str, ext: Dict[str, Any], cap: Dict[str, Any]) -> List[Dict[str, Any]]:
    a, fs, info = cap["analysis"], cap["fs"], cap["info"]
    ed = Edgar(ext)
    dp = a.get("data_provenance") or {}
    cur, ttm, prov = dp.get("currency") or {}, dp.get("ttm") or {}, dp.get("fields") or {}
    converted = bool(cur.get("converted"))
    rates = cur.get("rates") or {}
    sfy = info.get("_statements_fy") or {}
    fy0 = int(sfy["inc_years"][0]) if sfy.get("inc_years") else None
    fy_years = [int(y) for y in sfy.get("inc_years") or []]
    bs_years = [int(y) for y in sfy.get("bs_years") or []]
    factor = OFFICIAL_FACTOR.get(sym, 1)
    eng_class = (cur.get("share_class") or {})
    eng_factor = eng_class.get("factor") if eng_class.get("applied") else 1
    price = getattr(fs, "price", None)
    rows: List[Dict[str, Any]] = []
    CTX.clear()
    if getattr(fs, "shares_outstanding", None):
        CTX["shares_ordinary_now"] = fs.shares_outstanding * factor

    def rate_for(period, kind_stmt):
        if not converted:
            return 1.0
        typ, ref = period
        if typ == "instant":
            return _rate_at(rates.get("quarterly_balance_sheet"), ref) or _rate_at(rates.get("balance_sheet"), ref)
        if typ == "fy":
            return _rate_year(rates.get("balance_sheet" if kind_stmt == "bs" else "income_stmt"), ref) \
                if isinstance(ref, int) else None
        return cur.get("ttm_rate")

    # ── campos de FinancialStatements ──
    pv_by_field: Dict[str, Tuple[Optional[float], Any, Optional[float]]] = {}
    for name, attr, key, efield, kind, group in FIELDS:
        raw = getattr(fs, attr, None) if fs is not None else None
        src_stmt = "cf" if key in ("depreciation", "operatingCashflow", "capitalExpenditures", "freeCashflow",
                                   "dividendsPaid") else "inc"
        if kind == "stock":
            period = pipeline_period(key, src_stmt, prov, ttm, fy0)
            if period[0] == "fy":
                # saldo del último ejercicio: la fecha de cierre del FY de EDGAR para ese año
                end = ed.fy_end(period[1])
                period = ("instant", end) if end else period
        elif kind == "shares":
            period = ("dei", None)
        elif name == "eps":
            period = ("ttm", ((ttm.get("quarters") or {}).get("inc") or [None])[0]) if ttm.get("eps") == "ttm" \
                else pipeline_period(key, "inc", prov, ttm, fy0)
        elif name == "dividend_per_share":
            q_end = ((ttm.get("quarters") or {}).get("inc") or [None])[0]
            period = ("ttm", q_end) if q_end else ("fy", fy0)
        else:
            period = pipeline_period(key, src_stmt, prov, ttm, fy0)
        rate = rate_for(period, "bs" if kind == "stock" else "inc")
        source = (prov.get(key) or {}).get("source")
        row = {"ticker": sym, "campo": name, "grupo": group, "periodo": f"{period[0]} {period[1] or ''}".strip(),
               "fuente": source, "moneda": ed.unit}
        # pipeline en moneda de los estados (y por acción en la clase del precio)
        if raw is None:
            p = None
        elif kind in ("flow", "stock"):
            p = (abs(raw) if efield in ABS_FIELDS else raw) / rate if rate else None
        elif kind == "per_share":
            p = raw / rate if rate else None
        else:
            p = raw
        # EDGAR
        if efield == "total_debt":
            e, econcept, edet = debt_total(ed, period)
        elif efield == "cash":
            e, econcept, edet = cash_total(ed, period)
        elif efield == "total_liabilities":
            e, econcept, edet, _ = ed.value("total_liabilities", period)
            if e is None:
                le, c1, edet, _ = ed.value("liabilities_and_equity", period)
                eq_tot = None
                for c in (f"{ed.tax}:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                          f"{ed.tax}:Equity"):
                    if ed.facts(c, "stock"):
                        eq_tot, _, _, _ = ed.value("equity_parent", period, concept=c)
                        if eq_tot is not None:
                            break
                if le is not None and eq_tot is not None:
                    e, econcept = le - eq_tot, f"{c1} − patrimonio total"
        elif kind == "shares":
            e, econcept, edet = ed.shares_latest()
        elif efield == "dividend_per_share":
            e, econcept, edet, _ = ed.value("dividend_per_share", period)
            if e is None:
                dv, c1, edet, _ = ed.value("dividends_paid", period)
                sh = ed.shares_avg(period)
                if dv is not None and sh:
                    e, econcept = abs(dv) / sh, f"{c1} / acciones medias del último FY (derivado)"
        else:
            e, econcept, edet, _ = ed.value(efield, period)
        if e is not None and efield in ABS_FIELDS:
            e = abs(e)
        if e is not None and kind == "per_share":
            e = e * factor
        if e is not None and kind == "shares":
            e = e / factor
        row.update(pipeline=p, edgar=e, concepto=econcept, detalle_edgar=edet,
                   tol=TOL[group], tasa=rate)
        pv_by_field[name] = (p, period, e)
        rows.append(_judge(row, sym, ed, efield, kind, period, p, e, factor, eng_factor, raw, rate, fy_years))

    # ── series anuales (FY0, FY1) ──
    for skey, efield, kind in FY_SERIES:
        vals = sfy.get(skey) or []
        years = bs_years if kind in ("stock", "shares") else fy_years
        for i in (0, 1):
            if i >= len(years):
                continue
            y = years[i]
            raw = vals[i] if i < len(vals) else None
            fy_end = ed.fy_end(y)
            period = ("instant", fy_end) if kind in ("stock", "shares") else ("fy", y)
            if kind in ("stock", "shares") and not fy_end:
                period = ("fy", y)
            if not converted:
                rate = 1.0
            else:
                rate = _rate_year(rates.get("balance_sheet" if kind in ("stock", "shares") else "income_stmt"), y)
            if raw is None:
                p = None
            elif kind in ("flow", "stock"):
                p = (abs(raw) if efield in ABS_FIELDS else raw) / rate if rate else None
            elif kind == "per_share":
                p = raw / rate if rate else None
            else:
                p = raw
            if kind == "shares":
                e, econcept, edet = ed.shares_at(fy_end)
            elif efield == "total_liabilities":
                e, econcept, edet, _ = ed.value(efield, period)
            else:
                e, econcept, edet, _ = ed.value(efield, period)
            if e is not None and efield in ABS_FIELDS:
                e = abs(e)
            if e is not None and kind == "per_share":
                e = e * factor
            if e is not None and kind == "shares":
                e = e / factor
            group = {"per_share": "por_accion", "shares": "acciones"}.get(kind, "estado")
            row = {"ticker": sym, "campo": f"FY{i}.{skey}", "grupo": group, "periodo": f"FY {y}",
                   "fuente": "yfinance_statements", "moneda": ed.unit, "pipeline": p, "edgar": e,
                   "concepto": econcept, "detalle_edgar": edet, "tol": TOL[group], "tasa": rate}
            rows.append(_judge(row, sym, ed, efield, kind, period, p, e, factor, eng_factor, raw, rate, fy_years))

    # ── ratios (con los valores de EDGAR en los periodos del pipeline) ──
    R = a.get("ratios") or {}
    field_state = {r["campo"]: r["estado"] for r in rows}
    ev = {k: v[2] for k, v in pv_by_field.items()}
    dps_e = ev.get("dividend_per_share")
    ttm_rate = cur.get("ttm_rate") if converted else 1.0
    e_ratio = {
        "gross_margin": _div(ev.get("gross_profit"), ev.get("revenue")),
        "operating_margin": _div(ev.get("operating_income"), ev.get("revenue")),
        "net_margin": _div(ev.get("net_income"), ev.get("revenue")),
        "roe": _div(ev.get("net_income"), ev.get("total_equity")),
        "roa": _div(ev.get("net_income"), ev.get("total_assets")),
        "current_ratio": _div(ev.get("current_assets"), ev.get("current_liabilities")),
        "debt_to_equity": _div(ev.get("total_debt"), ev.get("total_equity")),
        "payout_ratio": _div(ev.get("dividends_paid"), ev.get("net_income")),
        "dividend_yield": _div(dps_e * ttm_rate if (dps_e is not None and ttm_rate) else None, price),
    }
    for k in RATIOS:
        p, e = R.get(k), e_ratio.get(k)
        row = {"ticker": sym, "campo": f"ratio.{k}", "grupo": "ratio", "periodo": "los del pipeline",
               "fuente": (prov.get(k) or {}).get("source"), "moneda": None, "pipeline": p, "edgar": e,
               "concepto": "recalculado con EDGAR", "detalle_edgar": "", "tol": TOL["ratio"], "tasa": None}
        if p is None and e is None:
            row.update(estado="ninguno", causa=None)
        elif e is None:
            row.update(estado="edgar_falta", causa="EDGAR falta")
        elif p is None:
            row.update(estado="pipeline_sin_dato", causa=None)
        elif within(p, e, TOL["ratio"]) or abs(p - e) <= RATIO_ABS_PP:
            row.update(estado="ok", causa=None)
        else:
            bad = [f for f in RATIO_INPUTS[k] if field_state.get(f) not in ("ok", None)]
            if bad:
                row.update(estado="fuera", causa="hereda", detalle="hereda la discrepancia de " + ", ".join(bad))
            else:
                row.update(estado="fuera", causa="fuente errónea",
                           detalle="sus campos cuadran con EDGAR: el ratio viene de otra fuente o de otra fórmula")
        row["dif"] = rel(p, e)
        rows.append(row)
    return rows


def econcept_is(ed: Edgar, period, field: str, concept: str) -> bool:
    """¿El valor principal del campo sale de ese concepto (p. ej. ProfitLoss, que incluye minoritarios)?"""
    _, c, _, _ = ed.value(field, period)
    return bool(c) and c.endswith(":" + concept)


def _div(a, b):
    return a / b if (a is not None and b) else None


def _judge(row, sym, ed: Edgar, efield, kind, period, p, e, factor, eng_factor, raw, rate, fy_years):
    tol = row["tol"]
    row["dif"] = rel(p, e)
    if p is None and e is None:
        row.update(estado="ninguno", causa=None)
        return row
    if e is None:
        row.update(estado="edgar_falta", causa="EDGAR falta")
        return row
    if p is None:
        row.update(estado="pipeline_sin_dato", causa=None)
        return row
    if within(p, e, tol):
        row.update(estado="ok", causa=None)
        return row
    base = row["campo"].split(".", 1)[-1] if row["campo"].startswith("FY") else row["campo"]
    base = {"capital_expenditure": "capex", "stockholders_equity": "total_equity"}.get(base, base)
    mk = (sym, row["campo"]) if (sym, row["campo"]) in MANUAL else (sym, base)
    if mk in MANUAL:
        row.update(estado="fuera", causa=MANUAL[mk][0], detalle=MANUAL[mk][1])
        return row
    cands = explanations(ed, efield, kind, period, e, factor, eng_factor, raw, rate, fy_years)
    hit = classify(p, cands, tol)
    if not hit and row["campo"] == "dividend_per_share" and row.get("fuente") == "finnhub" and e and 1 < p / e <= 1.15:
        hit = ("periodo", "dividendo indicado con una subida declarada después del último trimestre de EDGAR "
                          f"(+{p / e - 1:.1%}; probable, no verificable aún en EDGAR)")
    if not hit and kind in ("flow", "stock"):
        found = RAW.search(sym, ed, period, p, tol, efield)
        if found:
            hit = ("definición", "el valor está en EDGAR con otra etiqueta: " + ", ".join(found[:3]))
    if not hit and kind in ("flow", "stock") and abs(p - e) > 0.02 * abs(e):
        # la diferencia es exactamente otra partida (Yahoo suma o resta un concepto que la tabla no tiene)
        found = RAW.search(sym, ed, period, abs(p - e), 0.005, "")
        if found:
            sign = "+" if p > e else "−"
            hit = ("definición", f"probable: EDGAR {sign} {', '.join(found[:2])} (la diferencia coincide al 0.5%)")
    if hit:
        row.update(estado="fuera", causa=hit[0], detalle=hit[1])
    else:
        src = row.get("fuente") or ""
        row.update(estado="fuera", causa="fuente errónea",
                   detalle=f"ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da {p:,.4g}; fuente {src}")
    return row


def explanations(ed: Edgar, efield, kind, period, e, factor, eng_factor, raw, rate, fy_years):
    """Valores de EDGAR (en la unidad de la comparación) que explicarían el del pipeline, con su causa."""
    out: List[Tuple[str, str, Optional[float]]] = []
    scale = (lambda v: (abs(v) if efield in ABS_FIELDS else v) if v is not None else None) \
        if kind in ("flow", "stock") else \
        (lambda v: v * factor if v is not None else None) if kind == "per_share" else \
        (lambda v: v / factor if v is not None else None)
    typ, ref = period
    # factor ADR: el del motor en lugar del oficial
    if kind in ("per_share", "shares") and eng_factor and factor and abs(eng_factor / factor - 1) > 1e-4:
        k = eng_factor / factor
        out.append(("factor ADR", f"factor del motor {eng_factor:.4g} en vez del oficial {factor:.4g}",
                    e * k if kind == "per_share" else e / k))
    # unidad
    for k, lab in ((100, "×100 (peniques/céntimos)"), (0.01, "÷100"), (1000, "×1000 (miles)"), (0.001, "÷1000")):
        out.append(("unidad", lab, e * k))
        if kind == "per_share" and factor != 1:
            out.append(("unidad + factor ADR", f"{lab} y por acción ordinaria (sin ×{factor:g})", e * k / factor))
    if kind in ("per_share", "shares"):
        for k in (2, 3, 4, 5, 10, 15, 20):
            out.append(("periodo", f"split {k}:1 posterior al filing (Yahoo ya lo aplica)",
                        e / k if kind == "per_share" else e * k))
    if kind == "per_share" and factor != 1:
        out.append(("factor ADR", f"por acción ordinaria (sin ×{factor:g})", e / factor))
    if kind == "shares" and factor != 1:
        out.append(("factor ADR", f"acciones ordinarias (sin ÷{factor:g})", e * factor))
    own = efield in E.CONCEPTS          # total_debt es una suma: sus piezas van en "deuda" más abajo
    # definición: otras etiquetas del mismo campo y combinaciones conocidas
    for c in (ed.concepts(efield) if own else []):
        v, _, det, _ = ed.value(efield, period, concept=c)
        out.append(("definición", f"etiqueta {c} ({det})", scale(v)))
    if efield == "dividend_per_share" and typ == "ttm" and ref:
        q = ed.last_quarter("dividend_per_share", ref)
        if q is not None:
            out.append(("definición", "dividendo anual indicado (último trimestral × 4) frente a pagado TTM",
                        q * 4 * factor))
        for y in fy_years[:2]:
            v, _, det, _ = ed.value("dividend_per_share", ("fy", y))
            out.append(("periodo", f"dividendo por acción del FY {y}", scale(v)))
    if efield == "diluted_eps":
        ni, _, _, _ = ed.value("net_income", period)
        for c in (f"{ed.tax}:ProfitLossAttributableToOrdinaryEquityHoldersOfParentEntity",
                  f"{ed.tax}:NetIncomeLossAvailableToCommonStockholdersDiluted"):
            if ed.facts(c, "flow"):
                v, _, _, _ = ed.value("net_income", period, concept=c)
                ni_ord = v
                break
        else:
            ni_ord = None
        sh_dei, _, _, _ = ed.value("shares_outstanding", ("dei", None))
        sh_avg = ed.shares_avg(period)
        sh_now = CTX.get("shares_ordinary_now")
        for lab, num in (("beneficio total", ni), ("beneficio del accionista ordinario", ni_ord)):
            for slab, sh in (("acciones de portada", sh_dei), ("acciones medias del FY", sh_avg),
                             ("acciones actuales (capitalización / precio × factor oficial)", sh_now)):
                if num is not None and sh:
                    out.append(("definición", f"BPA derivado: {lab} / {slab}", num / sh * factor))
    if efield == "capex":
        for c in (f"{ed.tax}:PaymentsToAcquireIntangibleAssets",
                  f"{ed.tax}:PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities",
                  f"{ed.tax}:PaymentsToAcquireEquipmentOnLease", f"{ed.tax}:PaymentsToDevelopSoftware",
                  f"{ed.tax}:PaymentsForSoftware"):
            if ed.facts(c, "flow"):
                v, _, _, _ = ed.value("capex", period, concept=c)
                if v is not None:
                    out.append(("definición", f"capex + {c.split(':')[1]}", e + abs(v)))
    if efield in ("long_term_debt", "total_debt") and typ == "instant" and ed.tax == "ifrs-full":
        ls = lease_parts(ed, period).get("arrendamientos")
        if ls:
            out.append(("definición", "deuda sin arrendamientos (en IFRS los préstamos etiquetados los incluyen)", e - ls))
    if efield in ("long_term_debt", "total_debt") and typ == "instant":
        lp = lease_parts(ed, period)
        for lab, v in lp.items():
            out.append(("definición", "deuda con arrendamientos (IFRS 16)" if lab == "arrendamientos"
                        else f"deuda con arrendamientos {lab}", e + v))
        if len(lp) > 1:
            out.append(("definición", "deuda con todos los arrendamientos", e + sum(lp.values())))
        tr, ctr, _, _ = ed.value("total_debt_reported", period)
        if tr:
            out.append(("definición", f"deuda total etiquetada ({ctr})", abs(tr)))
            for lab, v in lp.items():
                out.append(("definición", f"deuda total etiquetada + arrendamientos {lab}", abs(tr) + v))
        sub, _ = _sum_parts(ed, period, [f"{ed.tax}:SubordinatedLiabilities"])
        if sub:
            out.append(("definición", "deuda con pasivos subordinados", e + sub))
    if efield == "net_income":
        for c in (f"{ed.tax}:ProfitLossAttributableToOrdinaryEquityHoldersOfParentEntity",
                  f"{ed.tax}:NetIncomeLossAvailableToCommonStockholdersDiluted"):
            if ed.facts(c, "flow"):
                v, _, _, _ = ed.value("net_income", period, concept=c)
                out.append(("definición", "beneficio del accionista ordinario (sin AT1/preferentes)", scale(v)))
        for c in (f"{ed.tax}:IncomeLossFromContinuingOperations", f"{ed.tax}:ProfitLossFromContinuingOperations"):
            if ed.facts(c, "flow"):
                v, _, _, _ = ed.value("net_income", period, concept=c)
                out.append(("perímetro", "beneficio de las operaciones continuadas", scale(v)))
        if econcept_is(ed, period, "net_income", "ProfitLoss"):
            mi, _, _, _ = ed.value("net_income_minorities", period)
            if mi:
                out.append(("definición", "beneficio atribuido a la dominante (ProfitLoss − minoritarios)", e - mi))
        for c in (f"{ed.tax}:ProfitLoss",):
            if ed.facts(c, "flow"):
                v, _, _, _ = ed.value("net_income", period, concept=c)
                out.append(("definición", "incluye minoritarios (ProfitLoss)", scale(v)))
        ni, _, _, _ = ed.value("net_income", period)
        dis, _, _, _ = ed.value("discontinued_ops", period)
        if ni is not None and dis:
            out.append(("perímetro", "sin operaciones discontinuadas (beneficio de las continuadas)", abs(ni - dis)))
        cp = ed.at1_coupons(period)
        if ni is not None and cp:
            out.append(("definición", "menos cupones AT1", abs(ni - cp)))
    if efield == "equity_parent":
        at1, _, _, _ = ed.value("at1_equity", period)
        if at1:
            out.append(("definición", "sin instrumentos AT1", abs(e - at1)))
        mi, _, _, _ = ed.value("minority_interest", period)
        if mi:
            out.append(("definición", "con minoritarios", abs(e + mi)))
    if efield == "dividends_paid":
        cp = ed.at1_coupons(period)
        if cp:
            out.append(("definición", "con cupones AT1 (beneficio de los propietarios − del accionista ordinario)",
                        e + abs(cp)))
    if efield in ("long_term_debt", "total_debt"):
        for f2 in ("long_term_debt", "short_term_debt", "total_debt_reported"):
            for c in ed.concepts(f2):
                v, _, det, _ = ed.value(f2, period, concept=c)
                out.append(("definición", f"deuda: {c}", abs(v) if v is not None else None))
    if efield == "cash" and typ == "instant":
        c0, _, _, _ = ed.value("cash", period)
        stis = []
        for c in ed.concepts("short_term_investments"):
            v, _ = ed.instant(ed.facts(c, "stock"), ref)
            if v:
                stis.append((c.split(":")[1], v))
                if c0 is not None:
                    out.append(("definición", f"caja + {c.split(':')[1]}", c0 + v))
        if c0 is not None and len(stis) > 1:
            out.append(("definición", "caja + todas las inversiones a corto plazo", c0 + sum(v for _, v in stis)))
        for f2 in ("cash", "short_term_investments"):
            for c in ed.concepts(f2):
                v, _, _, _ = ed.value(f2, period, concept=c)
                out.append(("definición", f"caja: solo {c}", abs(v) if v is not None else None))
    # periodo: otros cortes del mismo campo
    alt_periods = []
    if typ == "ttm":
        alt_periods += [("fy", y) for y in fy_years[:2]]
        alt_periods.append(("ttm", (_d(ref) + dt.timedelta(days=91)).isoformat()))   # la fuente ya tiene el siguiente
        for back in (91, 182):
            alt_periods.append(("ttm", (_d(ref) - dt.timedelta(days=back)).isoformat()))
    elif typ == "fy":
        alt_periods += [("fy", y) for y in fy_years[:3] if y != ref]
        if fy_years:
            alt_periods.append(("ttm", None))
    elif typ == "instant" and ref:
        for back in (91, 182, 365):
            alt_periods.append(("instant", (_d(ref) - dt.timedelta(days=back)).isoformat()))
    for ap in (alt_periods if own else []):
        if ap == ("ttm", None):
            continue
        v, c, det, _ = ed.value(efield, ap)
        out.append(("periodo", f"{ap[0]} {ap[1]} ({det})", scale(v)))
    # moneda: solo con tipos lejos de 1 (con EUR/USD ≈ 1.13 una diferencia real del 12% coincidía por azar: UL)
    if rate and not 0.8 < rate < 1.25:
        out.append(("unidad", "moneda sin convertir", e * rate))
        out.append(("unidad", "moneda convertida dos veces", e / rate))
    # perímetro / reexpresión: el valor original del mismo periodo
    v, c, det, groups = ed.value(efield, period) if own else (None, None, "", [])
    for g in groups or []:
        if g and E.restated(g):
            o = E.original(g)
            out.append(("perímetro", f"valor original antes de la reexpresión ({o['form']} {o['filed']})",
                        scale(o["val"])))
    return out


# ───────────────────────────── what-if ─────────────────────────────

INFO_SIGN_NEG = {"capitalExpenditures", "dividendsPaid"}


ERROR_CAUSES = {"fuente errónea", "unidad", "unidad + factor ADR", "factor ADR", "periodo"}


def whatif_patch(rows: List[Dict[str, Any]], cap: Dict[str, Any], sym: str,
                 causes: Optional[set] = None) -> Dict[str, float]:
    """Claves de info a sustituir por EDGAR (en USD y en la clase del precio) para los campos fuera de tolerancia."""
    info = cap["info"]
    key_of = {f[0]: (f[2], f[4]) for f in FIELDS}
    patch: Dict[str, float] = {}
    for r in rows:
        if r["estado"] != "fuera" or r["campo"] not in key_of or r.get("edgar") is None:
            continue
        if causes is not None and r.get("causa") not in causes:
            continue
        key, kind = key_of[r["campo"]]
        rate = r.get("tasa") or 1.0
        v = r["edgar"]
        if kind in ("flow", "stock", "per_share"):
            v = v * rate
        orig = info.get(key)
        if isinstance(orig, (int, float)) and orig < 0 or (orig is None and key in INFO_SIGN_NEG):
            v = -abs(v)
        patch[key] = v
    return patch


def levels(a: Dict[str, Any]) -> Dict[str, Any]:
    return {"arquetipo": (a.get("classification") or {}).get("archetype"),
            "calidad": (a.get("quality") or {}).get("level"),
            "calidad_score": (a.get("quality") or {}).get("score"),
            "precio": (a.get("price_attractiveness") or {}).get("level"),
            "precio_score": (a.get("price_attractiveness") or {}).get("score"),
            "confianza": (a.get("confidence") or {}).get("level")}


# ───────────────────────────── CLI ─────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--whatif", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report-only", action="store_true", help="rehace resumen.md desde resultado.json")
    args = ap.parse_args()
    if args.report_only:
        o = Path(os.path.expanduser(args.out))
        res = json.loads((o / "resultado.json").read_text())
        (o / "resumen.md").write_text(summary_md(res) + "\n\n## Detalle (filas fuera de tolerancia)\n\n"
                                      + detail_md(res) + "\n")
        print((o / "resumen.md").read_text()[:6000])
        return
    logging.disable(logging.CRITICAL)
    out = Path(os.path.expanduser(args.out))
    out.mkdir(parents=True, exist_ok=True)
    tickers = args.tickers or [t for t in fb.env_tickers("panel") if (E.EDGAR_DIR / f"{t}.json").exists()]
    all_rows, verdicts = [], {}
    for t in tickers:
        ext_path = E.EDGAR_DIR / f"{t}.json"
        if not ext_path.exists():
            print(f"{t}: sin extracto de EDGAR", flush=True)
            continue
        ext = json.loads(ext_path.read_text())
        cap = capture(t)
        if cap.get("fs") is None:
            print(f"{t}: el pipeline no construyó estados", flush=True)
            continue
        rows = compare_ticker(t, ext, cap)
        arch = (cap["analysis"].get("classification") or {}).get("archetype")
        for r in rows:
            r["arquetipo"] = arch
            r["origen"] = "extranjero" if t in FOREIGN else "EE. UU."
        all_rows += rows
        base = levels(cap["analysis"])
        verdicts[t] = {"base": base}
        if args.whatif:
            # A: todo lo que está fuera de tolerancia pasa al valor de EDGAR (EDGAR principal, tabla tal cual).
            # B: solo los errores de dato (fuente, unidad, factor, periodo); las diferencias de definición se quedan.
            for tag, causes in (("A", None), ("B", ERROR_CAUSES)):
                patch = whatif_patch(rows, cap, t, causes)
                if patch:
                    alt = capture(t, patch)
                    verdicts[t][tag] = {"niveles": levels(alt["analysis"]), "sustituidos": sorted(patch)}
        n_ok = sum(1 for r in rows if r["estado"] == "ok")
        n_cmp = sum(1 for r in rows if r["estado"] in ("ok", "fuera"))
        print(f"{t:6} {n_ok}/{n_cmp} dentro de tolerancia"
              + "".join(f"  {k}: {verdicts[t][k]['niveles']}" for k in ("A", "B") if verdicts[t].get(k)), flush=True)
    res = {"filas": all_rows, "veredictos": verdicts}
    (out / "resultado.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    (out / "resumen.md").write_text(summary_md(res) + "\n\n## Detalle (filas fuera de tolerancia)\n\n"
                                    + detail_md(res) + "\n")
    print(f"\n{len(all_rows)} filas → {out / 'resultado.json'}")



# ───────────────────────────── resumen (tablas del informe) ─────────────────────────────

def _pct(ok, n):
    return f"{ok}/{n} ({100 * ok / n:.1f}%)" if n else "—"


def summary_md(res: Dict[str, Any]) -> str:
    """Tablas de F2_DISCREPANCIAS: % dentro de tolerancia por campo, ticker, arquetipo y origen; causas."""
    import collections
    F = res["filas"]
    data = [r for r in F if r["grupo"] != "ratio"]
    cmp_ = [r for r in data if r["estado"] in ("ok", "fuera")]
    lines = []
    ok = sum(r["estado"] == "ok" for r in cmp_)
    lines.append(f"**Campos comparables:** {_pct(ok, len(cmp_))} dentro de tolerancia "
                 f"(sin contar {sum(r['estado'] == 'edgar_falta' for r in data)} sin dato en EDGAR, "
                 f"{sum(r['estado'] == 'pipeline_sin_dato' for r in data)} sin dato en el pipeline y "
                 f"{sum(r['estado'] == 'ninguno' for r in data)} sin dato en ninguno).\n")
    rat = [r for r in F if r["grupo"] == "ratio" and r["estado"] in ("ok", "fuera")]
    lines.append(f"**Ratios recalculados con EDGAR:** {_pct(sum(r['estado'] == 'ok' for r in rat), len(rat))}.\n")

    def table(key, title, order=None):
        g = collections.defaultdict(list)
        for r in cmp_:
            g[key(r)].append(r)
        keys = order or sorted(g)
        out = [f"| {title} | Dentro de tolerancia | Fuera | Causas de las que quedan fuera |", "|---|---|---|---|"]
        for k in keys:
            rs = g.get(k, [])
            if not rs:
                continue
            c = collections.Counter(r["causa"] for r in rs if r["estado"] == "fuera")
            out.append(f"| {k} | {_pct(sum(r['estado'] == 'ok' for r in rs), len(rs))} | "
                       f"{sum(r['estado'] == 'fuera' for r in rs)} | "
                       f"{', '.join(f'{n} {x}' for x, n in c.most_common()) or '—'} |")
        return "\n".join(out)

    def fld(r):
        return r["campo"].split(".", 1)[1] + " (FY0/FY1)" if r["campo"].startswith("FY") else r["campo"]
    lines += ["### Por campo", table(fld, "Campo"), "", "### Por ticker", table(lambda r: r["ticker"], "Ticker"), "",
              "### Por arquetipo", table(lambda r: r.get("arquetipo") or "—", "Arquetipo"), "",
              "### EE. UU. frente a extranjeros", table(lambda r: r["origen"], "Origen"), "",
              "### Por tipo de dato", table(lambda r: {"estado": "estado (último corte)", "por_accion": "por acción",
                                                         "acciones": "acciones"}[r["grupo"]]
                                            if not r["campo"].startswith("FY") else "serie anual (FY0, FY1)", "Tipo")]
    c = collections.Counter(r["causa"] for r in F if r["estado"] == "fuera")
    lines += ["", "### Causas (todas las filas fuera, ratios incluidos)", "| Causa | Filas |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in c.most_common()]
    return "\n".join(lines)


def detail_md(res: Dict[str, Any]) -> str:
    def f(x):
        if x is None:
            return "—"
        return f"{x:,.4g}" if isinstance(x, (int, float)) else str(x)
    out = ["| Ticker | Campo | Periodo | Pipeline | EDGAR | Dif. | Fuente | Causa | Detalle |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in res["filas"]:
        if r["estado"] != "fuera" or r.get("causa") == "hereda":
            continue
        dif = f"{r['dif']:+.1%}" if isinstance(r.get("dif"), (int, float)) and math.isfinite(r["dif"]) else "—"
        det = (r.get("detalle") or "").replace("|", "/")
        out.append(f"| {r['ticker']} | {r['campo']} | {r['periodo']} | {f(r['pipeline'])} | {f(r['edgar'])} | {dif} | "
                   f"{r.get('fuente') or '—'} | {r['causa']} | {det} |")
    return "\n".join(out)


if __name__ == "__main__":
    main()
