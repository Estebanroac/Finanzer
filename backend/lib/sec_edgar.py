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
import contextlib
import gzip
import json
import pickle
import logging
import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
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
QUARTERLY_FORMS = {"10-Q", "10-Q/A", "6-K", "6-K/A"}       # F10: nunca presentan un ejercicio (sec_edgar._flow_groups)
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
    # F10 · B2 (decisión del PM): el beneficio del accionista común en todas partes, como el del corte
    # (lib/ordinary.py): EIX, IVZ y APA etiquetan los dos y la historia y el gráfico usaban uno cada uno.
    "net_income": ("flow", 1, (
        "NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss",
        "NetIncomeLossAvailableToCommonStockholdersDiluted"),
        ("ProfitLossAttributableToOrdinaryEquityHoldersOfParentEntity", "ProfitLossAttributableToOwnersOfParent",
         "ProfitLoss")),
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
    # Fase 7 (decisión de método, registro #36): ganancias de inversiones en el resultado (realizadas y no realizadas,
    # ASC 321), antes de impuestos. Las aseguradoras y los conglomerados las excluyen de su beneficio operativo.
    "investment_gains": ("flow", 1, ("GainLossOnInvestments", "RealizedInvestmentGainsLosses",
                                     "DebtAndEquitySecuritiesGainLoss", "EquitySecuritiesFvNiGainLoss"), ()),
    "total_assets": ("stock", 1, ("Assets",), ("Assets",)),
    "current_assets": ("stock", 1, ("AssetsCurrent",), ("CurrentAssets",)),
    "current_liabilities": ("stock", 1, ("LiabilitiesCurrent",), ("CurrentLiabilities",)),
    "total_liabilities": ("stock", 1, ("Liabilities",), ("Liabilities",)),
    "retained_earnings": ("stock", 1, ("RetainedEarningsAccumulatedDeficit",), ("RetainedEarnings",)),
    "inventories": ("stock", 1, ("InventoryNet", "InventoryFinishedGoodsNetOfReserves"), ("Inventories",)),
    "equity_parent": ("stock", 1, ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
                      ("EquityAttributableToOwnersOfParent", "Equity")),
}
# F10 · cargos con etiquetas estándar (Plan, 29-oct): lo que presenta el emisor y las filas de Yahoo no recogen (GIS,
# ABBV, INTC). Solo etiquetas estándar us-gaap e IFRS, nunca las propias del emisor. Cada parte: alternativas en orden
# (la primera con dato); la paraguas, si el emisor la presenta, manda sobre sus partes (pueden solaparse: INTC).
# Importe del cargo en positivo; las ventas, con su signo (ganancia +).
CHARGES_US = {
    "fondo_de_comercio_e_intangibles": (("GoodwillAndIntangibleAssetImpairment",), (
        ("GoodwillImpairmentLoss",),
        ("ImpairmentOfIntangibleAssetsExcludingGoodwill", "ImpairmentOfIntangibleAssetsIndefinitelivedExcludingGoodwill",
         "ImpairmentOfIntangibleAssetsFinitelived"))),
    "reestructuracion_y_activos": (("RestructuringSettlementAndImpairmentProvisions",), (
        ("AssetImpairmentCharges", "ImpairmentOfLongLivedAssetsHeldForUse", "ImpairmentOfLongLivedAssetsToBeDisposedOf",
         "OtherAssetImpairmentCharges", "ImpairmentOfOilAndGasProperties"),
        ("RestructuringCharges", "RestructuringCosts"))),
    "litigios": ((), (("LitigationSettlementExpense", "LossContingencyLossInPeriod"),)),
    "id_adquirida": ((), (("ResearchAndDevelopmentInProcess",
                           "ResearchAndDevelopmentAssetAcquiredOtherThanThroughBusinessCombinationWrittenOff"),)),
}
SALES_US = ("GainLossOnSaleOfBusiness", "DisposalGroupNotDiscontinuedOperationGainLossOnDisposal",
            "GainLossOnDispositionOfAssets", "GainLossOnSaleOfPropertyPlantEquipment")
CHARGES_IFRS = {
    "deterioros": ((), (("ImpairmentLossRecognisedInProfitOrLossGoodwill",),
                        ("ImpairmentLossRecognisedInProfitOrLossIntangibleAssetsOtherThanGoodwill",),
                        ("ImpairmentLossRecognisedInProfitOrLossPropertyPlantAndEquipment",))),
}
SALES_IFRS = ("GainsLossesOnDisposalsOfPropertyPlantAndEquipment",)

# Escalera de márgenes de NFLX (30-oct): respaldo de EDGAR de la amortización de intangibles del D&A de la fuente (el
# EBITDA no lleva amortizaciones de activos operativos recurrentes: contenido, software capitalizado). Los paraguas no
# son un total fiable (MCD etiqueta una partida parcial con uno; 36 emisores solo `Depreciation`): se toma el mayor.
DA_SPLIT: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "us-gaap": {"umbrella": ("DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
                             "DepreciationAmortizationAndAccretionNet"),
                "amortization": ("AmortizationOfIntangibleAssets",)},
    "ifrs-full": {"umbrella": ("DepreciationAndAmortisationExpense",), "amortization": ()},
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
# Fase 3 (T1b): historia anual larga (10+ ejercicios) para clasificar por la historia real (D4) y para el ciclo
# medio. Campo → (unidad: "money" = moneda de los estados, "per_share" = moneda/acción, "shares" = acciones;
# alternativas us-gaap; alternativas ifrs-full), en orden de preferencia. Cada ejercicio toma el primer concepto que
# lo tenga: las etiquetas cambian con los años (ASC 606 en 2018: `SalesRevenueNet` → `RevenueFromContract…`).
HISTORY: Dict[str, Tuple[str, Tuple[str, ...], Tuple[str, ...]]] = {
    "revenue": ("money", CONCEPTS["revenue"][2], CONCEPTS["revenue"][3] + ("RevenueAndOperatingIncome",)),
    "operating_income": ("money", CONCEPTS["operating_income"][2], CONCEPTS["operating_income"][3]),
    "net_income": ("money", CONCEPTS["net_income"][2], CONCEPTS["net_income"][3]),
    "diluted_eps": ("per_share", ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"),
                    ("DilutedEarningsLossPerShare", "BasicAndDilutedEarningsLossPerShare")),
    "diluted_shares": ("shares", ("WeightedAverageNumberOfDilutedSharesOutstanding",),
                       ("AdjustedWeightedAverageShares",)),
    "operating_cash_flow": ("money", CONCEPTS["operating_cash_flow"][2], CONCEPTS["operating_cash_flow"][3]),
    "capex": ("money", CONCEPTS["capex"][2], CONCEPTS["capex"][3]),
    # T2: ciclicidad sin el cambio de perímetro (resultado de operaciones discontinuadas) y subtipo financiero (los
    # ingresos de contratos con clientes excluyen los contratos de seguro por norma, ASC 606 / NIIF 15: en una
    # aseguradora son los negocios no aseguradores).
    "discontinued": ("money", ("IncomeLossFromDiscontinuedOperationsNetOfTax",
                               "IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToReportingEntity"),
                     ("ProfitLossFromDiscontinuedOperations",)),
    "contract_revenue": ("money", ("RevenueFromContractWithCustomerExcludingAssessedTax",
                                   "RevenueFromContractWithCustomerIncludingAssessedTax"),
                         ("RevenueFromContractsWithCustomers",)),
    # F8 · E4: compras de licencias de espectro de una telecom (lib/telecom_spectrum.py), en actividades de inversión.
    "spectrum_purchases": ("money", ("PaymentsToAcquireIntangibleAssets",), ()),
}
# Campos cuya definición no cambia de forma material entre US GAAP e IFRS: con el cambio de norma (TM, IFRS desde el
# FY2021) la historia anterior se completa con la otra taxonomía y se declara.
HISTORY_CROSS_TAXONOMY = ("revenue", "diluted_eps")
# F8 (historia de 10 años en cascada): campos en los que la otra taxonomía completa los ejercicios anteriores al cambio
# de norma solo si, en un ejercicio que presentan las dos, coinciden (± `history_relay_rel_tol`). TM: el resultado
# operativo y el beneficio de FY2020 coinciden (−1,8 % y −1,9 %); el flujo operativo no (−33 %: la NIIF reclasifica los
# cobros de la financiera), así que ese no se completa.
HISTORY_CROSS_VERIFIED = ("operating_income", "net_income", "operating_cash_flow", "capex")
# F10 · B2 (NTAP): campos cuyo total es el mayor de los conceptos que llegan al último ejercicio. NTAP etiqueta desde
# FY2024 `Revenues` con una parte de los ingresos (5,907 frente a 6,572 millones de USD en FY2025) y, por el orden de
# CONCEPTS, la historia tomaba esa parte; una parte nunca supera al total.
HISTORY_TOTAL_FIRST = ("revenue",)
# F10 · B2: campos en los que un concepto completa los ejercicios de otro solo si coinciden en el último ejercicio
# común (misma definición): el beneficio de los propietarios frente al del común difiere en lo que cobran los
# preferentes (EIX, BAC). En los ingresos las etiquetas de ASC 606 difieren unos puntos sin cambiar de definición (FCX:
# 2.8 % entre `Revenues` y los de contratos con clientes) y el relevo sigue como estaba.
HISTORY_SAME_DEFINITION = ("net_income",)
# Dos ejercicios se solapan si uno acaba más de una semana después de que empiece el siguiente (los de 52/53 semanas
# se tocan en unos días).
HISTORY_OVERLAP_DAYS = 7
# Relevo de conceptos (us-gaap, ifrs-full): un concepto que el emisor usa en lugar de los de HISTORY. Toma los
# ejercicios que faltan solo si es el único que usa el emisor, o si coincide con la serie en el último ejercicio común
# (y entonces solo los posteriores: es la continuación). LLY presenta su capex como
# PaymentsToAcquireOtherPropertyPlantAndEquipment (2007–2025); VZ, desde 2017, como
# PaymentsToAcquireOtherProductiveAssets (igual que PaymentsToAcquireProductiveAssets en 2017 y 2018; antes era una
# partida menor). El BPA de operaciones continuadas (SHEL) entra en cada ejercicio solo si cuadra con beneficio neto /
# acciones diluidas (± `history_relay_rel_tol` o `history_eps_abs_tol`): con discontinuadas no cuadra y no entra.
HISTORY_RELAY: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]] = {
    "capex": (("PaymentsToAcquireOtherPropertyPlantAndEquipment", "PaymentsToAcquireOtherProductiveAssets"), ()),
    "diluted_eps": (("IncomeLossFromContinuingOperationsPerDilutedShare",),
                    ("DilutedEarningsLossPerShareFromContinuingOperations",)),
}
# Por qué falta un campo entero de la historia (ningún concepto estándar ni relevo verificado).
HISTORY_MISSING = {
    "operating_income": "el emisor no presenta un resultado operativo con el concepto XBRL estándar",
    "capex": "el emisor presenta el capex con conceptos propios (extensiones XBRL) que la SEC no publica en companyfacts",
    "diluted_eps": ("el emisor no presenta un BPA diluido sin dimensiones (lo da por clase de acción o por acción "
                    "equivalente), que la SEC no publica en companyfacts"),
}
HISTORY_SCALE_JUMP = 100   # un salto de acciones o BPA de más de 100 veces entre dos ejercicios es un error de escala

# F9 · R6 (riesgo de crédito de un banco, lib/credit_risk.py): campo -> (stock | flow, conceptos us-gaap, ifrs-full), del
# preferido al último. Solo los totales sin dimensiones (los que publica companyfacts). En IFRS la cartera es la neta de
# provisiones (no hay un concepto estándar de la bruta ni de la provisión): se dice.
CREDIT: Dict[str, Tuple[str, Tuple[str, ...], Tuple[str, ...]]] = {
    "loans": ("stock", ("FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss",
                        "LoansAndLeasesReceivableGrossCarryingAmount", "FinancingReceivableRecordedInvestment"),
              ("LoansAndAdvancesToCustomersAtAmortisedCost", "LoansAndAdvancesToCustomers")),
    "allowance": ("stock", ("FinancingReceivableAllowanceForCreditLossExcludingAccruedInterest",
                            "FinancingReceivableAllowanceForCreditLosses", "LoansAndLeasesReceivableAllowance"), ()),
    "credit_loss_expense": ("flow", ("FinancingReceivableExcludingAccruedInterestCreditLossExpenseReversal",
                                     "FinancingReceivableCreditLossExpenseReversal", "ProvisionForLoanAndLeaseLosses",
                                     "ProvisionForLoanLeaseAndOtherLosses"),
                            ("AdjustmentsForImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLossLoansAndAdvances",
                             "AdjustmentsForImpairmentLossesReversalOfImpairmentLossesRecognisedInProfitOrLossFinancialAssets")),
    "past_due_90": ("stock", ("FinancingReceivableExcludingAccruedInterest90DaysOrMorePastDueStillAccruing",
                              "FinancingReceivableRecordedInvestment90DaysPastDueAndStillAccruing"), ()),
    "nonaccrual": ("stock", ("FinancingReceivableExcludingAccruedInterestNonaccrual",
                             "FinancingReceivableRecordedInvestmentNonaccrualStatus"), ()),
    "net_charge_offs": ("flow", ("FinancingReceivableExcludingAccruedInterestAllowanceForCreditLossWriteoffAfterRecovery",
                                 "FinancingReceivableAllowanceForCreditLossesWriteOffsNet"), ()),
}

_WANTED = {"us-gaap": {c for v in CONCEPTS.values() for c in v[2]} | {c for v in DEBT_PARTS["us-gaap"].values() for c in v}
           | {c for v in HISTORY.values() for c in v[1]} | {c for v in HISTORY_RELAY.values() for c in v[0]}
           | {c for v in CREDIT.values() for c in v[1]}
           | {c for umb, parts in CHARGES_US.values() for c in (*umb, *(x for p in parts for x in p))} | set(SALES_US)
           | {c for v in DA_SPLIT["us-gaap"].values() for c in v},
           "ifrs-full": {c for v in CONCEPTS.values() for c in v[3]}
           | {c for v in DEBT_PARTS["ifrs-full"].values() for c in v} | {c for v in HISTORY.values() for c in v[2]}
           | {c for v in HISTORY_RELAY.values() for c in v[1]} | {c for v in CREDIT.values() for c in v[2]}
           | {c for umb, parts in CHARGES_IFRS.values() for c in (*umb, *(x for p in parts for x in p))}
           | set(SALES_IFRS) | {c for v in DA_SPLIT["ifrs-full"].values() for c in v}}
# Deuda de la financiera cautiva (T5): solo va con dimensiones en la instancia del filing.
CAPTIVE_DEBT_CONCEPTS = ("LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsCurrent",
                         "LongTermDebtNoncurrent", "LongTermDebtCurrent", "ShortTermBorrowings", "CommercialPaper")
_FACT_KEYS = ("start", "end", "val", "filed", "form", "accn")

_cache: "OrderedDict[str, Tuple[float, Any]]" = OrderedDict()   # LRU: lo más reciente al final
_lock = threading.Lock()
_parse_lock: Optional[threading.BoundedSemaphore] = None      # lecturas grandes a la vez (pico de memoria)
_segments_lock: Optional[threading.BoundedSemaphore] = None   # V6 (B2): lecturas de segmentos, aparte
_rate_lock = threading.Lock()
_last = [0.0]
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="edgar")
_inflight: Dict[str, Future] = {}        # ticker -> etapa 1 del análisis en curso (emisor, filings, portada)
_fetching: Dict[str, threading.Event] = {}   # clave de _cache -> descarga en marcha (una por clave)


class Unavailable(RuntimeError):
    """EDGAR no disponible para este análisis (sin User-Agent, presupuesto agotado o la SEC falla)."""


class NotFound(Unavailable):
    """La SEC responde 404: el recurso no existe (p. ej. companyfacts de un CIK sin estados XBRL)."""


def user_agent() -> Optional[str]:
    ua = (os.environ.get(cfg("data.edgar.user_agent_env")) or "").strip()
    return ua if "@" in ua else None


def env_check() -> Dict[str, bool]:
    """Diagnóstico de la variable del User-Agent para /api/health, sin exponer su valor ni otros nombres: si existe
    con el nombre exacto, si lleva un correo y si hay otra variable de nombre casi igual (espacios o mayúsculas)."""
    name = cfg("data.edgar.user_agent_env")
    raw = os.environ.get(name)
    near = any(k != name and k.strip().upper() == name.upper() for k in os.environ)
    return {"enabled": user_agent() is not None, "present": raw is not None and bool(raw.strip()),
            "has_contact": "@" in (raw or ""), "near_miss": near}


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
    """Tiempo de EDGAR que le queda a un análisis. Fase 6 (revisión de código, hallazgo 2): la espera en cola detrás de
    OTROS análisis (el turno de las lecturas grandes y el ritmo de la SEC) no gasta el presupuesto: con varios análisis
    a la vez, el segundo perdía EDGAR y su resultado dependía de la carga (BRK-B: P/E 13.24 o 16.96)."""

    def __init__(self, seconds: Optional[float] = None):
        self.total = cfg("data.edgar.budget_s") if seconds is None else seconds
        self.deadline = time.monotonic() + self.total
        self.queued_s = 0.0

    def left(self) -> float:
        return self.deadline - time.monotonic()

    def add_queue(self, seconds: float) -> None:
        """La cola se perdona hasta `queue_max_s` en total: con una carga extrema (12 análisis en frío a la vez son ≈ 50
        peticiones al ritmo de la SEC) EDGAR se agota por carga y el análisis lo dice, en vez de esperar sin límite."""
        seconds = min(max(seconds, 0.0), cfg("data.edgar.queue_max_s") - self.queued_s)
        if seconds > 0:
            self.deadline += seconds
            self.queued_s += seconds

    @contextlib.contextmanager
    def turn(self, sem):
        """Espera el turno de `sem` sin gastar presupuesto. V6 (revisión de seguridad, B2): la espera se suma a
        `queued_s` mientras se espera, a tramos de `turn_poll_s`, no al conseguir el turno: quien espera el resultado
        (collect) alarga su plazo a la vez. Si la cola perdonada (`queue_max_s`) se agota antes del turno, EDGAR no
        está disponible para este análisis y se dice."""
        poll = cfg("data.edgar.turn_poll_s")
        t = time.monotonic()
        while not sem.acquire(timeout=poll):
            now = time.monotonic()
            self.add_queue(now - t)
            t = now
            if self.queued_s >= cfg("data.edgar.queue_max_s"):
                raise Unavailable(f"EDGAR ocupado: más de {cfg('data.edgar.queue_max_s'):g} s en cola")
        self.add_queue(time.monotonic() - t)
        try:
            yield
        finally:
            sem.release()


def _pace(budget: Budget) -> float:
    """Ritmo de la SEC (≤ 10 peticiones/s) sin gastar presupuesto; devuelve el tiempo que queda."""
    E = cfg("data.edgar")
    if not user_agent():
        raise Unavailable(status()["reason"])
    t0 = time.monotonic()
    with _rate_lock:
        wait = _last[0] + E["min_interval_s"] - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
    budget.add_queue(time.monotonic() - t0)
    left = budget.left()
    if left <= 0:
        # Verificación de la v4 (V3): el presupuesto de quien llama (segmentos: 8 s), no siempre el del análisis.
        raise Unavailable(f"presupuesto de EDGAR agotado ({budget.total:g} s)")
    return left


def _no_answer(e: BaseException) -> str:
    """Verificación de la v4 (V3): "EDGAR no respondió a tiempo" en lugar de "(TimeoutError)"; el resto, con su tipo."""
    if isinstance(e, TimeoutError) or "timed out" in str(e).lower():
        return "EDGAR no respondió a tiempo"
    return f"EDGAR no respondió ({type(e).__name__})"


def _get(url: str, budget: Budget, fetcher: Optional[Callable[[str, float], Tuple[Optional[bytes], int]]] = None
         ) -> bytes:
    """`fetcher`: otro descargador para un llamador concreto (rediseño E2b: el replay de los segmentos); por defecto,
    FETCHER."""
    left = _pace(budget)
    try:
        body, code = (fetcher or FETCHER)(url, min(cfg("data.edgar.timeout_s"), left))
    except Exception as e:  # red, tiempo de espera, TLS…: se registra el tipo
        raise Unavailable(_no_answer(e)) from e
    if code == 404:
        raise NotFound("EDGAR respondió 404")
    if body is None or code != 200:
        raise Unavailable(f"EDGAR respondió {code}")
    return body


_CHUNK = 1 << 20


def _get_to_file(url: str, budget: Budget, fh, fetcher=None, max_bytes: Optional[int] = None,
                 whole_budget: bool = True) -> int:
    """Rediseño E2b: descarga a un archivo abierto (`fh`, binario) en trozos, sin tener el cuerpo entero en memoria
    (instancias XBRL de bancos: BCS 44 MB). Con otro descargador (replay, tests) escribe su cuerpo. Devuelve los bytes
    escritos. V6 (B14): a cada trozo cuenta los bytes (ya descomprimidos: un gzip que se infla no pasa de `max_bytes`)
    y el presupuesto (la descarga entera, no solo cada lectura, dentro del tiempo de quien llama).
    Rendimiento (v4f8): `whole_budget=False` es la descarga de _get en trozos, con sus mismas reglas (el tiempo de
    espera por lectura; ni el presupuesto de la descarga entera ni otro código que 200): solo cambia dónde quedan los
    bytes (las instancias pendientes del análisis, C 10-Q: 48 MB de pico en memoria)."""
    if fetcher is not None or FETCHER is not urllib_fetcher:
        body = _get(url, budget, fetcher)
        if max_bytes is not None and len(body) > max_bytes:
            raise Unavailable(f"el archivo de EDGAR supera {max_bytes // (1 << 20)} MB")
        fh.write(body)
        return len(body)
    left = _pace(budget)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent() or "", "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=min(cfg("data.edgar.timeout_s"), left)) as r:
            if not whole_budget and r.status != 200:
                raise Unavailable(f"EDGAR respondió {r.status}")
            src = gzip.GzipFile(fileobj=r) if r.headers.get("Content-Encoding") == "gzip" else r
            n = 0
            while True:
                chunk = src.read(_CHUNK)
                if not chunk:
                    return n
                n += len(chunk)
                if max_bytes is not None and n > max_bytes:
                    raise Unavailable(f"el archivo de EDGAR supera {max_bytes // (1 << 20)} MB")
                if whole_budget and budget.left() <= 0:
                    raise Unavailable(f"presupuesto de EDGAR agotado ({budget.total:g} s)")
                fh.write(chunk)
    except (Unavailable, NotFound):
        raise
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise NotFound("EDGAR respondió 404") from e
        raise Unavailable(f"EDGAR respondió {e.code}") from e
    except Exception as e:  # red, tiempo de espera, TLS…: se registra el tipo
        raise Unavailable(_no_answer(e)) from e


def _get_json(url: str, budget: Budget, fetcher=None) -> Any:
    return json.loads(_get(url, budget, fetcher))


def _cached(key: str, ttl: float, make: Callable[[], Any], budget: Optional[Budget] = None) -> Any:
    """Caché por proceso con caducidad y tope por tipo (`facts:`, `inst:`, `sub:`…): con más de
    `cache_max_issuers` entradas de un tipo sale la usada hace más tiempo (fase 3, T1b: la historia larga vive en
    memoria y Render tiene 512 MB; con disco efímero no hay caché en disco).
    Rendimiento (v4f8): una sola descarga por clave a la vez. Quien llega mientras otro descarga la misma clave
    (company_tickers.json en cuatro análisis en frío; el companyfacts de un rival que se analiza a la vez) espera su
    resultado en vez de repetirla; esa espera es cola detrás de otro análisis y no gasta su presupuesto (como el turno
    de las lecturas grandes, Budget.turn). Si la descarga de otro falla, quien esperaba descarga por su cuenta."""
    while True:
        now = time.time()
        with _lock:
            ent = _cache.get(key)
            if ent and now - ent[0] < ttl:
                _cache.move_to_end(key)
                return ent[1]
            running = _fetching.get(key)
            if running is None:
                running = _fetching[key] = threading.Event()
                break
        _wait_other(running, budget)
        with _lock:
            ent = _cache.get(key)
            if ent and time.time() - ent[0] < ttl:
                _cache.move_to_end(key)
                return ent[1]
        with _lock:                     # la descarga del otro falló: esta llamada lo intenta por su cuenta
            if key not in _fetching:
                running = _fetching[key] = threading.Event()
                break
    try:
        val = make()
    finally:
        with _lock:
            _fetching.pop(key, None)
        running.set()
    with _lock:
        _cache[key] = (now, val)
        _cache.move_to_end(key)
        kind = key.split(":", 1)[0]
        if kind != "tickers":
            same = [k for k in _cache if k.split(":", 1)[0] == kind]
            for k in same[:max(0, len(same) - _cache_cap(kind))]:
                del _cache[k]
    return val


def _wait_other(ev: threading.Event, budget: Optional[Budget]) -> None:
    """Espera la descarga de otro llamador; con presupuesto, como cola perdonada (a tramos de `turn_poll_s`, hasta
    `queue_max_s` en total, como Budget.turn)."""
    if budget is None:
        ev.wait()
        return
    poll = cfg("data.edgar.turn_poll_s")
    t = time.monotonic()
    while not ev.wait(poll):
        now = time.monotonic()
        budget.add_queue(now - t)
        t = now
        if budget.queued_s >= cfg("data.edgar.queue_max_s"):
            raise Unavailable(f"EDGAR ocupado: más de {cfg('data.edgar.queue_max_s'):g} s en cola")
    budget.add_queue(time.monotonic() - t)


def _cache_cap(kind: str) -> int:
    n = cfg("data.edgar.cache_max_issuers")
    return n * cfg("data.edgar.max_pending_filings") if kind == "inst" else n


def _parsing():
    """Semáforo de las lecturas grandes (companyfacts de 6–8 MB e instancias de hasta 15 MB): el pico de memoria de
    una lectura es de 80–116 MB (F3_T1_PARADA1 §2.2) y la concurrencia de producción, 3."""
    global _parse_lock
    with _lock:
        if _parse_lock is None:
            _parse_lock = threading.BoundedSemaphore(cfg("data.edgar.parse_concurrency"))
    return _parse_lock


def _segments_parsing():
    """V6 (revisión de seguridad, B2): turno propio de la lectura de segmentos (/api/v2/segments). Compartía el de
    _parsing() con el análisis: mientras se leía una instancia, un análisis concurrente perdía EDGAR y salía con las
    cifras de Yahoo. La lectura de segmentos va en flujo (la memoria no depende del tamaño de la instancia)."""
    global _segments_lock
    with _lock:
        if _segments_lock is None:
            _segments_lock = threading.BoundedSemaphore(cfg("data.edgar.segments_parse_concurrency"))
    return _segments_lock


def cik_for(ticker: str, budget: Budget) -> Optional[Dict[str, Any]]:
    """{cik, title} del ticker en company_tickers.json de la SEC, o None si no está registrado."""
    E = cfg("data.edgar")
    table = _cached("tickers", E["tickers_ttl_s"], lambda: {
        str(v["ticker"]).upper(): {"cik": int(v["cik_str"]), "title": v.get("title")}
        for v in (_get_json(TICKERS_URL, budget) or {}).values()}, budget)
    return table.get(ticker.upper().replace(".", "-"))


def issuer_country(sub: Dict[str, Any]) -> Optional[str]:
    """Fase 4/7: país de la dirección comercial del emisor en EDGAR (si no, la postal). Un código de dos letras es un
    estado o territorio de EE. UU.; uno con dígito (P7, X0…) es extranjero y vale su descripción; la dirección
    extranjera nueva trae `country` (TSM: Taiwan)."""
    for kind in ("business", "mailing"):
        a = (sub.get("addresses") or {}).get(kind) or {}
        if a.get("country"):
            return str(a["country"])
        code, desc = a.get("stateOrCountry"), a.get("stateOrCountryDescription")
        if code and re.fullmatch(r"[A-Z]{2}", str(code)):
            return "United States"
        if desc:
            return str(desc)
    return None


def submission_profile(sub: Dict[str, Any]) -> Dict[str, Any]:
    """Rediseño E2a: ficha del emisor en EDGAR (submissions), sin red adicional: viene en la misma respuesta."""
    b = (sub.get("addresses") or {}).get("business") or {}

    def v(x):
        return (str(x).strip() or None) if x is not None else None
    return {"sic": v(sub.get("sic")), "sic_description": v(sub.get("sicDescription")),
            "state_of_incorporation": v(sub.get("stateOfIncorporationDescription") or sub.get("stateOfIncorporation")),
            "fiscal_year_end": v(sub.get("fiscalYearEnd")), "city": v(b.get("city")),
            # la dirección extranjera nueva trae `country` y no `stateOrCountry` (TSM: Taiwan), como en issuer_country
            "state_or_country": v(b.get("stateOrCountryDescription") or b.get("country") or b.get("stateOrCountry")),
            "category": v(sub.get("category")), "website": v(sub.get("website"))}


_RECENT_USED = ("form", "filingDate", "reportDate", "items", "accessionNumber", "isXBRL")


def submissions_json(body: bytes) -> Any:
    """json.loads(body) del JSON de submissions sin las columnas de `filings.recent` que nadie lee (solo
    _RECENT_USED): cada una se lee y se suelta. Rendimiento (v4f8): JPM trae 16 columnas de 26.501 filings (folletos
    424B2), 22 MB de pico al leerlo entero. Lo demás, como json.loads (una clave repetida vale la última vez); una
    forma que no es la esperada, json.loads."""
    text = body.decode(json.detect_encoding(body), "surrogatepass")
    top: Dict[str, Any] = {}

    def recent(k: str, i: int) -> int:
        val, end = _DECODER.raw_decode(text, i)
        if k in _RECENT_USED:
            out_recent[k] = val
        else:
            out_recent.pop(k, None)
        return end

    def filings(k: str, i: int) -> int:
        if k == "recent" and text[i] == "{":
            out_recent.clear()
            end = _members(text, i, recent)
            out_filings[k] = dict(out_recent)
            return end
        val, end = _DECODER.raw_decode(text, i)
        out_filings[k] = val
        return end

    def member(k: str, i: int) -> int:
        if k == "filings" and text[i] == "{":
            out_filings.clear()
            end = _members(text, i, filings)
            top[k] = dict(out_filings)
            return end
        val, end = _DECODER.raw_decode(text, i)
        top[k] = val
        return end
    out_recent: Dict[str, Any] = {}
    out_filings: Dict[str, Any] = {}
    try:
        i = _WS.match(text, 0).end()
        if text[i] != "{":
            return json.loads(body)
        end = _WS.match(text, _members(text, i, member)).end()
    except (IndexError, ValueError):            # JSON roto: el error de siempre, el de json.loads
        return json.loads(body)
    if end != len(text):
        return json.loads(body)
    return top


def submissions(cik: int, budget: Budget) -> Dict[str, Any]:
    """{filings, country, profile} del CIK: filings recientes (desde `since`, del más reciente al más antiguo), el país
    del emisor (issuer_country) y su ficha (submission_profile, rediseño E2a)."""
    E = cfg("data.edgar")

    def make():
        raw = submissions_json(_get(SUBMISSIONS_URL.format(cik=cik), budget)) or {}
        r = (raw.get("filings") or {}).get("recent") or {}
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
        return {"filings": sorted(out, key=lambda f: (f["filingDate"], f["accessionNumber"]), reverse=True),
                "country": issuer_country(raw), "profile": submission_profile(raw),
                # Rendimiento (v4f8): lo que lib/segments.last_annual buscaba en una segunda descarga de este mismo
                # JSON (JPM: ~0,5 MB comprimido, ~20 MB al leerlo), con la misma respuesta.
                "annual_xbrl": annual_xbrl(r),
                "older_pages": [p["name"] for p in (raw.get("filings") or {}).get("files") or [] if p.get("name")]}
    return _cached(f"sub:{cik}", E["submissions_ttl_s"], make, budget)


def annual_xbrl(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Informes anuales (10-K, 20-F, 40-F y sus enmiendas) con XBRL de un bloque de submissions (`recent` o una página
    antigua), en el orden en que vienen."""
    out = []
    for i, form in enumerate(block.get("form") or []):
        if form in ANNUAL_FORMS and (block.get("isXBRL") or [0] * (i + 1))[i]:
            out.append({"form": form, "filingDate": block["filingDate"][i],
                        "reportDate": (block.get("reportDate") or [""] * (i + 1))[i] or None,
                        "accessionNumber": block["accessionNumber"][i]})
    return out


def filings(cik: int, budget: Budget) -> List[Dict[str, Any]]:
    """Filings recientes del CIK (desde `since`), del más reciente al más antiguo."""
    return submissions(cik, budget)["filings"]


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


def _slim_fact(f: Dict[str, Any], memo: Dict[str, str]) -> Dict[str, Any]:
    """Un hecho con solo _FACT_KEYS. V4 · memoria: las cadenas que se repiten miles de veces por emisor (accn, form,
    filed, start, end) se comparten (`memo`): mismos valores, un solo objeto. La caché de hechos pasaba de 1,4 MB por
    emisor."""
    out = {}
    for k in _FACT_KEYS:
        v = f.get(k)
        if v is not None:
            out[k] = memo.setdefault(v, v) if isinstance(v, str) else v
    return out


_WS = re.compile(r"[ \t\n\r]*")
_DECODER = json.JSONDecoder()


def _members(text: str, i: int, value: Callable[[str, int], int]) -> int:
    """Recorre el objeto JSON que empieza en text[i] ('{'): para cada miembro llama a value(clave, inicio del valor),
    que devuelve dónde acaba ese valor. Devuelve el índice tras la '}' de cierre."""
    if text[i] != "{":
        raise ValueError(f"se esperaba un objeto en la posición {i}")
    i = _WS.match(text, i + 1).end()
    if text[i] == "}":
        return i + 1
    while True:
        key, i = _DECODER.raw_decode(text, i)
        if not isinstance(key, str):
            raise ValueError(f"clave que no es una cadena en la posición {i}")
        i = _WS.match(text, i).end()
        if text[i] != ":":
            raise ValueError(f"se esperaba ':' en la posición {i}")
        i = value(key, _WS.match(text, i + 1).end())
        i = _WS.match(text, i).end()
        if text[i] == "}":
            return i + 1
        if text[i] != ",":
            raise ValueError(f"se esperaba ',' en la posición {i}")
        i = _WS.match(text, i + 1).end()


def reduce_facts_stream(body: bytes) -> Dict[str, Any]:
    """Lo mismo que reduce_facts(json.loads(body)), leyendo concepto a concepto: nunca existe el árbol entero (6–8 MB
    de JSON son ~100 MB de objetos pequeños). V4 · memoria: ese árbol era el mayor transitorio del análisis y, al
    soltarse, dejaba arenas a medio usar que el proceso ya no devolvía. Como json.loads, una clave repetida vale la
    última vez."""
    text = body.decode(json.detect_encoding(body), "surrogatepass")
    top: Dict[str, Any] = {}
    wanted: Dict[str, Dict[str, Any]] = {}          # taxonomía -> concepto -> nodo (solo los de _WANTED)
    seen: Dict[Tuple[str, str], Tuple[set, str]] = {}   # (taxonomía financiera, concepto) -> (accns, último filed)
    has_facts = [False]

    def concept(tx: str):
        names = _WANTED.get(tx, ())

        def value(c: str, i: int) -> int:
            node, end = _DECODER.raw_decode(text, i)
            if tx in FINANCIAL_TAXONOMIES:
                acc, last = set(), ""
                for fs in node.get("units", {}).values():
                    for f in fs:
                        acc.add(f.get("accn"))
                        last = max(last, f.get("filed") or "")
                seen[(tx, c)] = (acc, last)
            if c in names:
                wanted.setdefault(tx, {})[c] = node
            else:
                wanted.get(tx, {}).pop(c, None)
            return end
        return value

    def taxonomy(tx: str, i: int) -> int:
        for k in [k for k in seen if k[0] == tx]:       # taxonomía repetida: vale la última
            del seen[k]
        wanted.pop(tx, None)
        if text[i] != "{":                               # no es un objeto: lo que haría reduce_facts con él
            val, end = _DECODER.raw_decode(text, i)
            top.setdefault("_odd_tx", {})[tx] = val
            return end
        return _members(text, i, concept(tx))

    def member(k: str, i: int) -> int:
        if k == "facts" and text[i] == "{":
            has_facts[0] = True
            seen.clear()
            wanted.clear()
            top.pop("_odd_tx", None)
            return _members(text, i, taxonomy)
        val, end = _DECODER.raw_decode(text, i)
        top[k] = val
        if k == "facts":
            has_facts[0] = False
        return end

    i = _WS.match(text, 0).end()
    try:
        end = _WS.match(text, _members(text, i, member)).end()
    except IndexError:              # se acabó el texto a medias: JSON truncado (json.loads también da ValueError)
        raise ValueError("JSON truncado") from None
    if end != len(text):
        raise ValueError(f"datos de más tras el JSON en la posición {end}")
    if not has_facts[0] or top.get("_odd_tx"):
        # forma rara (sin "facts" como objeto, o una taxonomía que no es objeto): el camino de siempre
        return reduce_facts(json.loads(body))
    accns, last = set(), ""
    for tx in FINANCIAL_TAXONOMIES:
        for (t, _c), (acc, lf) in seen.items():
            if t == tx:
                accns |= acc
                last = max(last, lf)
    out: Dict[str, Any] = {"cik": top.get("cik"), "entityName": top.get("entityName"), "facts": {}}
    memo: Dict[str, str] = {}
    for tx, names in _WANTED.items():
        cs = wanted.get(tx) or {}
        for c in sorted(names):
            node = cs.get(c)
            if node:
                out["facts"].setdefault(tx, {})[c] = {"units": {
                    u: [_slim_fact(f, memo) for f in fs]
                    for u, fs in (node.get("units") or {}).items()}}
    out["accns"], out["last_filed"] = sorted(a for a in accns if a), last or None
    return out


def _compact(reduce: Callable[[Any], Any], raw: Any) -> Any:
    """`reduce(raw)` rehecho en memoria nueva y contigua, con los mismos valores. V4 · memoria: lo reducido (lo que
    queda en caché) nacía intercalado con el árbol de la lectura grande (companyfacts: ~100 MB de objetos pequeños por
    6–8 MB de JSON) y dejaba esas arenas a medio usar, que el proceso ya no devolvía: unos 4 MB retenidos por emisor
    además de su caché. Soltar el árbol y rehacer lo reducido (ida y vuelta por pickle: dict, listas, cadenas y
    números idénticos) deja las arenas viejas libres del todo."""
    out = reduce(raw)
    del raw
    blob = pickle.dumps(out, protocol=pickle.HIGHEST_PROTOCOL)
    del out
    return pickle.loads(blob)


def reduce_facts(raw: Dict[str, Any]) -> Dict[str, Any]:
    """companyfacts con solo los conceptos de CONCEPTS (y los filings que traen estados, contados sobre todos)."""
    idx = _index_facts({"facts": raw.get("facts") or {}})
    out: Dict[str, Any] = {"cik": raw.get("cik"), "entityName": raw.get("entityName"), "facts": {}}
    memo: Dict[str, str] = {}
    for tx, names in _WANTED.items():
        cs = (raw.get("facts") or {}).get(tx) or {}
        for c in sorted(names):
            node = cs.get(c)
            if node:
                out["facts"].setdefault(tx, {})[c] = {"units": {
                    u: [_slim_fact(f, memo) for f in fs]
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


def _recent_only(facts: Dict[str, Any]) -> Dict[str, Any]:
    """F10 · Plan, 29-oct (memoria): de las etiquetas de cargos y ventas (CHARGES_*, SALES_*), solo los hechos de los
    periodos que se usan: el TTM y la ventana de recurrencia, más dos años de margen (los ejercicios desfasados), contados
    desde el hecho más reciente de esas etiquetas. Los demás conceptos no se tocan."""
    years = cfg("thresholds.normalization.recurrence_window") + 2
    for tx, (charges, sales) in (("us-gaap", (CHARGES_US, SALES_US)), ("ifrs-full", (CHARGES_IFRS, SALES_IFRS))):
        node = (facts.get("facts") or {}).get(tx) or {}
        names = {c for umb, parts in charges.values() for c in (*umb, *(x for p in parts for x in p))} | set(sales)
        units = [u for c in names if c in node for u in node[c].get("units", {}).values()]
        last = max((f["end"] for fs in units for f in fs), default=None)
        if last is None:
            continue
        cut = f"{int(last[:4]) - years}{last[4:]}"
        for c in names & set(node):
            for u, fs in node[c].get("units", {}).items():
                node[c]["units"][u] = [f for f in fs if f["end"] >= cut]
    return facts


def company_facts(cik: int, budget: Budget) -> Dict[str, Any]:
    """companyfacts reducido del CIK (caché diaria). NotFound si el CIK no tiene estados XBRL."""
    def make():
        body = _get(FACTS_URL.format(cik=cik), budget)          # la descarga, fuera del turno (solo el parseo pesa)
        with budget.turn(_parsing()):
            return _compact(lambda b: _recent_only(reduce_facts_stream(b)), body)
    return _cached(f"facts:{cik}", cfg("data.edgar.facts_ttl_s"), make, budget)


def _tax_of(ns: str) -> Optional[str]:
    ns = ns.split("://", 1)[-1]          # IFRS usa https, la FASB http
    if ns.startswith("fasb.org/us-gaap/"):
        return "us-gaap"
    if ns.startswith("xbrl.ifrs.org/taxonomy/"):
        return "ifrs-full"
    return None


_XBRL_CHUNK = 1 << 16
_XBRLI = "{http://www.xbrl.org/2003/instance}"


def xbrl_top_elements(source, keep_text: Callable[[str], bool]):
    """Rendimiento (v4f8): los elementos hijos de la raíz de una instancia XBRL (`source`: archivo binario abierto),
    completos y de uno en uno, como iterparse a profundidad 1, salvo una cosa: de un hecho (un hijo de la raíz que no
    es de xbrli: context, unit) cuyo nombre local no pasa `keep_text`, no se guarda el texto (queda None). Las
    instancias de los bancos NIIF llevan los textos de las notas como hechos (BCS: uno de 8,6 millones de caracteres,
    ~17 MB en memoria; 39 MB de pico al leer la instancia de 44 MB): quien lee solo unos conceptos no necesita ese
    texto. Cada elemento sale de la raíz al entregarse: en memoria, uno a la vez."""
    import xml.etree.ElementTree as ET
    out: List[Any] = []

    class _Builder(ET.TreeBuilder):
        def __init__(self):
            super().__init__()
            self.depth = 0
            self.mute = False
            self.root = None

        def start(self, tag, attrs):
            el = super().start(tag, attrs)
            self.depth += 1
            if self.depth == 1:
                self.root = el
            elif self.depth == 2:
                self.mute = not tag.startswith(_XBRLI) and not keep_text(tag.rsplit("}", 1)[-1])
            return el

        def data(self, text):
            if not self.mute:
                super().data(text)

        def end(self, tag):
            el = super().end(tag)
            self.depth -= 1
            if self.depth == 1:
                self.mute = False
                self.root.remove(el)        # el último hijo: la raíz no guarda los ya entregados
                out.append(el)
            return el

    parser = ET.XMLParser(target=_Builder())
    while True:
        chunk = source.read(_XBRL_CHUNK)
        if not chunk:
            break
        parser.feed(chunk)
        yield from out
        out.clear()
    parser.close()
    yield from out


def parse_instance(xml, form: str, filed: str, accn: str) -> Dict[str, Any]:
    """Hechos sin dimensiones de una instancia XBRL, solo los conceptos de CONCEPTS, con la forma de companyfacts.
    Lectura en flujo (iterparse): una instancia de 15 MB (HSBC) no se carga entera en memoria. `xml`: los bytes o un
    archivo binario abierto (rendimiento v4f8: la instancia pendiente se descarga a un archivo temporal)."""
    import io
    import xml.etree.ElementTree as ET
    X = "{http://www.xbrl.org/2003/instance}"
    ctx: Dict[str, Optional[Dict[str, str]]] = {}
    units: Dict[str, str] = {}
    raw: List[Tuple[str, str, str, str, str]] = []
    wanted = set().union(*_WANTED.values())
    source = io.BytesIO(xml) if isinstance(xml, (bytes, bytearray)) else xml
    for el in xbrl_top_elements(source, lambda name: name in wanted):
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


_STANDARD_NS = re.compile(r"(xbrl\.sec\.gov/dei|fasb\.org/srt|xbrl\.org/)")


def parse_segments(xml, axes: Tuple[str, ...], concepts: Tuple[str, ...], neutral: Tuple[str, ...] = (),
                   geo_axes: Tuple[str, ...] = (), eliminations: Tuple[str, ...] = (),
                   redundant: Tuple[str, ...] = (), extension_totals: Tuple[str, ...] = ()) -> Dict[str, Any]:
    """Rediseño E2b: hechos de DURACIÓN de `concepts` (us-gaap o ifrs-full) con una sola dimensión cuyo eje está en
    `axes` (nombres locales), más los mismos conceptos sin dimensión (el total consolidado). Un miembro de `neutral`
    ("Eje=Miembro", p. ej. ConsolidationItemsAxis=OperatingSegmentsMember de ASU 2023-07) no cuenta como dimensión.
    Además, para los ejes de `axes` que no están en `geo_axes` (los de negocio):
      · `by_geo`: el segmento cruzado con un eje geográfico y nada más (XOM: Upstream × EE. UU. / fuera de EE. UU.);
      · `elims`: las eliminaciones entre segmentos (miembro de `eliminations`) de cada segmento, sin geografía ("") o
        por zona.
    Un miembro de un eje de `redundant` (LegalEntityAxis) que repite el miembro de otra dimensión del mismo contexto
    (NEE: segmento FPL y entidad legal FPL) no cuenta. `ext_totals`: hechos sin dimensión de los conceptos PROPIOS del
    emisor (fuera de us-gaap, ifrs-full, dei y srt) con nombre local en `extension_totals` (el total de ingresos de un
    banco NIIF: bcs:OperatingIncome), como {nombre local: {periodo: valor}}. `xml`: los bytes o la ruta de un archivo (la instancia
    descargada en streaming no se carga entera en memoria). Lectura en flujo, como parse_instance.

    {"axes": {eje: {concepto: {miembro (qname): {"inicio/fin": valor}}}}, "totals": {concepto: {"inicio/fin": valor}},
     "by_geo" y "elims": {eje: {concepto: {miembro: {"inicio/fin": {zona o "": valor}}}}}, "units": {concepto: unidad}}"""
    import io
    import xml.etree.ElementTree as ET
    X = "{http://www.xbrl.org/2003/instance}"
    XD = "{http://xbrl.org/2006/xbrldi}"
    neutral_set = {tuple(n.split("=", 1)) for n in neutral}
    elim_set = {tuple(n.split("=", 1)) for n in eliminations}
    redundant_set = set(redundant)
    business = set(axes) - set(geo_axes)
    # id -> (tipo, eje, miembro, zona, periodo); tipo: total | axis | by_geo | elims
    ctx: Dict[str, Tuple[str, Optional[str], Optional[str], str, str]] = {}
    units: Dict[str, str] = {}
    raw: List[Tuple[str, str, str, str]] = []
    if isinstance(xml, (bytes, bytearray)):
        source = io.BytesIO(xml)
    elif isinstance(xml, (str, os.PathLike)):
        with open(xml, "rb") as fh:
            return parse_segments(fh, axes, concepts, neutral, geo_axes, eliminations, redundant, extension_totals)
    else:
        source = xml
    named = set(concepts) | set(extension_totals)
    for el in xbrl_top_elements(source, lambda name: name in named):
        tag = el.tag
        if tag == X + "context":
            p = el.find(X + "period")
            st, en = p.find(X + "startDate"), p.find(X + "endDate")
            if st is not None and en is not None and el.find(f".//{XD}typedMember") is None \
                    and el.find(X + "scenario") is None:
                mem = [(m.get("dimension", "").split(":")[-1], (m.text or "").strip())
                       for m in el.iter(XD + "explicitMember")]
                mem = [(d, m) for d, m in mem if (d, m.split(":")[-1]) not in neutral_set]
                mem = [(d, m) for d, m in mem
                       if not (d in redundant_set and any(m == m2 for d2, m2 in mem if d2 != d))]
                elim = [(d, m) for d, m in mem if (d, m.split(":")[-1]) in elim_set]
                mem = [x for x in mem if x not in elim]
                period = f"{st.text.strip()[:10]}/{en.text.strip()[:10]}"
                bus = [x for x in mem if x[0] in business]
                geo = [x for x in mem if x[0] in geo_axes]
                kind = None
                if not elim and not mem:
                    kind, ax, mb, zone = "total", None, None, ""
                elif not elim and len(mem) == 1 and mem[0][0] in axes:
                    kind, ax, mb, zone = "axis", mem[0][0], mem[0][1], ""
                elif len(elim) == 1 and len(bus) == 1 and len(mem) == 1 + len(geo) and len(geo) <= 1:
                    kind, ax, mb, zone = "elims", bus[0][0], bus[0][1], (geo[0][1] if geo else "")
                elif not elim and len(mem) == 2 and len(bus) == 1 and len(geo) == 1:
                    kind, ax, mb, zone = "by_geo", bus[0][0], bus[0][1], geo[0][1]
                if kind:
                    ctx[el.get("id")] = (kind, ax, mb, zone, period)
        elif tag == X + "unit":
            meas = [m.text.split(":")[-1] for m in el.iter(X + "measure")]
            units[el.get("id")] = "/".join(meas) if el.find(X + "divide") is not None else (meas[0] if meas else "")
        elif tag.startswith("{") and el.get("contextRef") and el.text:
            ns, name = tag[1:].split("}")
            if name in concepts and _tax_of(ns):
                raw.append((name, el.get("contextRef"), el.get("unitRef") or "", el.text.strip()))
            elif name in extension_totals and not _tax_of(ns) and not _STANDARD_NS.search(ns):
                raw.append(("ext:" + name, el.get("contextRef"), el.get("unitRef") or "", el.text.strip()))
        el.clear()
    out: Dict[str, Any] = {"axes": {}, "totals": {}, "by_geo": {}, "elims": {}, "units": {}, "ext_totals": {}}
    for name, cref, uref, text in raw:
        c = ctx.get(cref)
        if c is None:
            continue
        try:
            val = float(text)
        except ValueError:
            continue
        kind, axis, member, zone, period = c
        if name.startswith("ext:"):
            if kind == "total":
                out["ext_totals"].setdefault(name[4:], {}).setdefault(period, val)
            continue
        if kind == "total":
            out["totals"].setdefault(name, {}).setdefault(period, val)
        elif kind == "axis":
            out["axes"].setdefault(axis, {}).setdefault(name, {}).setdefault(member, {}).setdefault(period, val)
        else:
            (out[kind].setdefault(axis, {}).setdefault(name, {}).setdefault(member, {}).setdefault(period, {})
             .setdefault(zone, val))
        if uref in units:
            out["units"].setdefault(name, units[uref])
    return out


def labels(xml_lab: bytes, qnames) -> Dict[str, str]:
    """Rediseño E2b: etiqueta estándar (role/label, en inglés) de cada qname ("aapl:IPhoneMember") del linkbase de
    etiquetas del filing (`*_lab.xml`), sin el sufijo " [Member]"."""
    import io
    import xml.etree.ElementTree as ET
    L = "{http://www.xbrl.org/2003/linkbase}"
    XL = "{http://www.w3.org/1999/xlink}"
    want = set(qnames)
    loc: Dict[str, str] = {}            # etiqueta xlink del locator -> qname
    res: Dict[str, str] = {}            # etiqueta xlink del recurso -> texto (rol estándar)
    arcs: List[Tuple[str, str]] = []
    for _ev, el in ET.iterparse(io.BytesIO(xml_lab), events=("end",)):
        if el.tag == L + "loc":
            frag = (el.get(XL + "href") or "").split("#")[-1]
            qn = frag.replace("_", ":", 1)
            if qn in want:
                loc[el.get(XL + "label")] = qn
        elif el.tag == L + "label":
            if el.get(XL + "role", "http://www.xbrl.org/2003/role/label") == "http://www.xbrl.org/2003/role/label":
                res.setdefault(el.get(XL + "label"), (el.text or "").strip())
            el.clear()
        elif el.tag == L + "labelArc":
            arcs.append((el.get(XL + "from"), el.get(XL + "to")))
    out: Dict[str, str] = {}
    for fr, to in arcs:
        if fr in loc and to in res and res[to]:
            out.setdefault(loc[fr], re.sub(r"\s*\[Member\]$", "", res[to]))
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
    by_date = _cached(f"captive:{acc}:{spec['member']}", cfg("data.edgar.facts_ttl_s"), make, budget)
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
            return {"facts": {}, "accns": [], "last_filed": None, "reason": "el informe no publica sus cifras en un formato que se pueda leer automáticamente"}
        # Rendimiento (v4f8): a un archivo temporal, no a memoria (C 10-Q: 48 MB de pico; HSBC 6-K: 45 MB).
        with tempfile.TemporaryFile(suffix=".xml") as tmp:
            _get_to_file(ARCHIVE_URL.format(cik=cik, acc=acc, name=inst), budget, tmp, whole_budget=False)
            tmp.seek(0)
            with budget.turn(_parsing()):
                return _compact(lambda x: parse_instance(x, filing["form"], filing["filingDate"],
                                                         filing["accessionNumber"]), tmp)
    return _cached(f"inst:{acc}", cfg("data.edgar.facts_ttl_s"), make, budget)


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


def _flow_groups(fs: List[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    """Hechos de flujo por periodo (inicio, fin). Un ejercicio (≥ 350 días) nunca sale de un informe trimestral: un
    10-Q no presenta ejercicios, y si trae uno es un error de etiquetado del emisor (FIX: el comparativo del 1T de 2025,
    209 M$, con el periodo del ejercicio entero, ganaba al 10-K por ser posterior). Si hay varios formularios, manda el
    informe anual; si no lo hay, los demás valen (VRSN: su beneficio anual solo va en el DEF 14A, las tablas de pay
    versus performance; «Modelo general», 29-oct)."""
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for f in fs:
        if f.get("start"):
            groups.setdefault((f["start"], f["end"]), []).append(f)

    def fiscal_year(g):
        g = [f for f in g if f.get("form") not in QUARTERLY_FORMS]
        return [f for f in g if f.get("form") in ANNUAL_FORMS] or g
    return {k: g for k, g in ((k, fiscal_year(g) if 350 <= _kdays(k) <= 380 else g) for k, g in groups.items()) if g}


def _kdays(k: Tuple[str, str]) -> int:
    return (_date(k[1]) - _date(k[0])).days


def flow_ttm(fs: List[Dict[str, Any]], end: _dt.date, tol: int, basis: str = "reciente") -> Optional[Dict[str, Any]]:
    """Doce meses que acaban en `end` (± tol días): el ejercicio que acaba ahí o, si no, el ejercicio anterior más el
    acumulado del año hasta `end` menos el mismo acumulado del año anterior (la práctica estándar con 10-Q y 6-K).

    F10 · margen operativo (verificación de «Modelo general» y Plan, 29-oct). Cada periodo con su hecho:
      · `basis="reciente"` (por defecto, Plan): el del filing más reciente que lo presenta, es decir, el comparativo
        reexpresado del último 10-Q o 10-K;
      · `basis="ejercicio"`: el acumulado del año anterior en la base del ejercicio, el último presentado no después
        que él (IFF: el comparativo reexpresado con un ejercicio sin reexpresar daba −291 M$ frente a 754 M$).
    `checked_flow_ttm` elige entre las dos con la suma de los trimestres."""
    groups = _flow_groups(fs)
    cur = {k: _current(g) for k, g in groups.items()}

    def as_of(k, filed):
        """El hecho del periodo `k` en la base de un informe presentado el `filed`: el último no posterior a él."""
        up_to = [f for f in groups[k] if (f.get("filed") or "") <= (filed or "")]
        return _current(up_to) if up_to else cur[k]
    fy = [k for k in cur if _near(k[1], end, tol) and 350 <= _kdays(k) <= 380]
    if fy:
        k = min(fy, key=lambda k: (abs((_date(k[1]) - end).days), -int(cur[k].get("filed", "0").replace("-", "") or 0)))
        f = cur[k]
        return {"value": f["val"], "period": f"{k[0]}/{k[1]}", "how": f"ejercicio {k[0]} a {k[1]}", "accns": [f["accn"]]}
    ytd = sorted((k for k in cur if _near(k[1], end, tol) and 80 <= _kdays(k) < 350), key=_kdays, reverse=True)
    for k in ytd:
        s = _date(k[0])
        prev_fy = [p for p in cur if 350 <= _kdays(p) <= 380 and _near(p[1], s - _dt.timedelta(days=1), tol)]
        prev_ytd = [p for p in cur if abs(_kdays(p) - _kdays(k)) <= tol
                    and _near(p[1], _date(k[1]) - _dt.timedelta(days=365), tol)
                    and _near(p[0], s - _dt.timedelta(days=365), tol)]
        if prev_fy and prev_ytd:
            a, b = cur[prev_fy[0]], cur[k]
            c = as_of(prev_ytd[0], a.get("filed")) if basis == "ejercicio" else cur[prev_ytd[0]]
            return {"value": a["val"] + b["val"] - c["val"], "period": f"TTM a {k[1]}",
                    "how": (f"ejercicio {prev_fy[0][0]} a {prev_fy[0][1]} + acumulado {k[0]} a {k[1]} − acumulado "
                            f"{prev_ytd[0][0]} a {prev_ytd[0][1]}"
                            + (" (en la base del ejercicio)" if basis == "ejercicio" else "")),
                    "accns": sorted({a["accn"], b["accn"], c["accn"]})}
    return None


def quarters_ttm(fs: List[Dict[str, Any]], end: _dt.date, tol: int, basis: str = "reciente") -> Optional[Dict[str, Any]]:
    """La suma de los 4 trimestres que acaban en `end`: el hecho de 3 meses o, si el emisor no lo presenta, el periodo
    más largo que acaba ahí menos el acumulado de 3 meses menos del mismo inicio (el 4T = ejercicio − 9 meses). Cada
    trimestre del filing más reciente que lo presenta (`basis="reciente"`) o como se presentó por primera vez
    (`basis="original"`: DLR reexpresa el 2T de 2025 en el 10-Q de julio de 2026, después del ejercicio). Un «trimestre»
    con el valor del ejercicio que acaba esa misma fecha es un error de etiquetado y se deriva (LHX: 2.110 M$ en el
    «4T»). None si falta alguno (un 20-F con semestres)."""
    groups = _flow_groups(fs)
    pick = _current if basis == "reciente" else (lambda g: min(g, key=lambda f: (f.get("filed") or "", f.get("accn") or "")))
    cur = {k: pick(g) for k, g in groups.items()}
    fy_end = {k[1]: cur[k]["val"] for k in cur if 350 <= _kdays(k) <= 380}
    total, how, at = 0.0, [], end
    for _ in range(4):
        q = [k for k in cur if 80 <= _kdays(k) <= 100 and _near(k[1], at, tol) and cur[k]["val"] != fy_end.get(k[1])]
        if q:
            total += cur[q[0]]["val"]
            how.append(f"{q[0][0]} a {q[0][1]}")
            at = _date(q[0][0]) - _dt.timedelta(days=1)
            continue
        got = None
        for k in sorted((k for k in cur if _kdays(k) > 100 and _near(k[1], at, tol)), key=_kdays):
            short = [p for p in cur if p[0] == k[0] and 80 <= _kdays(k) - _kdays(p) <= 100]
            if short:
                p = max(short, key=_kdays)
                got = (cur[k]["val"] - cur[p]["val"], f"{p[1]} a {k[1]} ({k[0]} a {k[1]} − {p[0]} a {p[1]})", _date(p[1]))
                break
        if got is None:
            return None
        total += got[0]
        how.append(got[1])
        at = got[2]
    return {"value": total, "how": "; ".join(how)}


def checked_flow_ttm(fs: List[Dict[str, Any]], end: _dt.date, tol: int, scale: float) -> Dict[str, Any]:
    """F10 · perímetro (Plan, 29-oct): el TTM tiene que cuadrar con la suma de sus 4 trimestres (± `ttm_quarters_
    tolerance` de `scale`, los ingresos), con los trimestres más recientes o con los presentados por primera vez (DLR). Primero el del filing más reciente de cada periodo; si no cuadra, el de la base
    del ejercicio; si ninguno cuadra, el TTM de EDGAR no es homogéneo (HON: el ejercicio con lo escindido y los
    acumulados sin ello) y no se usa (value None, con el motivo). Sin los 4 trimestres (20-F semestral), el más
    reciente sin comprobar: la comprobación queda «no disponible» y no tumba el TTM (Plan, 29-oct). -> {value, basis,
    quarters, candidates, reason, check: cuadra | no_disponible | no_homogeneo, …el resto de flow_ttm}."""
    lim = cfg("data.edgar.ttm_quarters_tolerance") * abs(scale or 0.0)
    qs = [x for x in (quarters_ttm(fs, end, tol, "reciente"), quarters_ttm(fs, end, tol, "original")) if x]
    q = qs[0] if qs else None
    cands = {b: flow_ttm(fs, end, tol, basis=b) for b in ("reciente", "ejercicio")}
    out = {"quarters": q["value"] if q else None, "quarters_how": q["how"] if q else None,
           "candidates": {b: (r or {}).get("value") for b, r in cands.items()}}
    for b in ("reciente", "ejercicio"):
        r = cands[b]
        hit = next((x for x in qs if abs(r["value"] - x["value"]) <= lim), None) if r is not None else None
        if r is not None and (not qs or hit):
            return {**r, **out, **({"quarters": hit["value"], "quarters_how": hit["how"]} if hit else {}),
                    "basis": b, "reason": None, "check": "cuadra" if hit else "no_disponible"}
    if cands["reciente"] is None:
        return {**out, "value": None, "basis": None, "reason": "sin el periodo en EDGAR", "check": None}
    return {**out, "value": None, "basis": None, "check": "no_homogeneo",
            "reason": (f"TTM de EDGAR no homogéneo: ni el del filing más reciente ({cands['reciente']['value']:,.0f}) ni "
                       f"el de la base del ejercicio ({(cands['ejercicio'] or {}).get('value') or 0:,.0f}) cuadran con la "
                       f"suma de sus trimestres ({q['value']:,.0f}); perímetros o bases mezclados")}


def discontinued_ttm(facts: Dict[str, Any], at: _dt.date, tol: int) -> Optional[Dict[str, Any]]:
    """F10 · N1b: resultado de operaciones discontinuadas (neto de impuestos) de los doce meses que acaban en `at`, del
    primer concepto de HISTORY["discontinued"] que los tenga (el corte de EDGAR no trae el desglose de Yahoo). None sin
    el hecho: sin discontinuadas declaradas en el periodo."""
    tax = taxonomy(facts)
    unit = reporting_unit(facts, tax)
    if tax is None or unit is None:
        return None
    _kind, us, ifrs = HISTORY["discontinued"]
    for c in (us if tax == "us-gaap" else ifrs):
        fs = (facts.get("facts") or {}).get(tax, {}).get(c, {}).get("units", {}).get(unit) or []
        got = flow_ttm(fs, at, tol) if fs else None
        if got is not None:
            return {**got, "concept": f"{tax}:{c}"}
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


def da_split_ttm(facts: Dict[str, Any], at: _dt.date, tol: int) -> Dict[str, Optional[float]]:
    """Doce meses que acaban en `at` (moneda de los estados) del D&A de EDGAR por partes (DA_SPLIT): {"umbrella": el
    mayor de los paraguas, "amortization": la amortización de intangibles adquiridos}; None la que no etiqueta."""
    out: Dict[str, Optional[float]] = {"umbrella": None, "amortization": None}
    tax = taxonomy(facts)
    unit = reporting_unit(facts, tax)
    if tax not in DA_SPLIT or unit is None:
        return out
    node = (facts.get("facts") or {}).get(tax) or {}
    for part, concepts in DA_SPLIT[tax].items():
        vals = [r["value"] for c in concepts
                for r in [flow_ttm(node.get(c, {}).get("units", {}).get(unit) or [], at, tol)] if r is not None]
        out[part] = max(vals) if vals else None
    return out


def charges_ttm(facts: Dict[str, Any], at: _dt.date, tol: int) -> Optional[Dict[str, Any]]:
    """F10 · cargos con etiquetas estándar (Plan, 29-oct): los cargos y las ventas de los doce meses que acaban en `at`
    con las etiquetas estándar (CHARGES_US/SALES_US o las IFRS), y la serie de los últimos ejercicios para la prueba de
    recurrencia. -> {neg (efecto de los cargos y las pérdidas por venta sobre el beneficio, ≤ 0), pos (ganancias por
    venta, ≥ 0), charges (solo los cargos, ≤ 0: gastos operativos por naturaleza), detail: {concepto: importe}, annual: [{end, neg, pos}] (el más reciente primero)} o None sin ninguna
    etiqueta con dato."""
    tax = taxonomy(facts)
    unit = reporting_unit(facts, tax)
    if tax is None or unit is None:
        return None
    charges, sales = (CHARGES_US, SALES_US) if tax == "us-gaap" else (CHARGES_IFRS, SALES_IFRS)
    node = (facts.get("facts") or {}).get(tax, {})

    def fs(c):
        return node.get(c, {}).get("units", {}).get(unit) or []

    def first(alts, value_of):
        for c in alts:
            v = value_of(c)
            if v is not None:
                return c, v
        return None, None

    def measure(value_of):
        detail, neg, pos = {}, 0.0, 0.0
        for umb, parts in charges.values():
            cu, vu = first(umb, value_of)
            sub = [first(p, value_of) for p in parts]
            total = sum(v for _c, v in sub if v is not None)
            if vu is not None:      # la paraguas manda: sus partes pueden solaparse (INTC)
                detail[cu], neg = vu, neg - vu
            else:
                for c, v in sub:
                    if v is not None:
                        detail[c], neg = v, neg - v
        charges_only = neg
        cs, vs = first(sales, value_of)
        if vs is not None:
            detail[cs] = vs
            neg, pos = (neg + vs, pos) if vs < 0 else (neg, pos + vs)
        return detail, neg, pos, charges_only

    detail, neg, pos, charges_only = measure(lambda c: (flow_ttm(fs(c), at, tol) or {}).get("value") if fs(c) else None)
    if not detail:
        return None
    ends = sorted({f["end"] for umb, parts in charges.values() for c in (*umb, *(x for p in parts for x in p), *sales)
                   for f in fs(c) if f.get("start") and f.get("form") in ANNUAL_FORMS
                   and 350 <= _days(f) <= 380 and _date(f["end"]) <= at + _dt.timedelta(days=tol)}, reverse=True)
    annual = []
    for e in ends[:cfg("thresholds.normalization.recurrence_window")]:
        d, n, p, _c = measure(lambda c: next((f["val"] for f in sorted(
            (f for f in fs(c) if f.get("start") and f["end"] == e and f.get("form") in ANNUAL_FORMS
             and 350 <= _days(f) <= 380), key=lambda f: f.get("filed") or "", reverse=True)), None))
        annual.append({"end": e, "neg": n, "pos": p})
    return {"neg": neg, "pos": pos, "charges": charges_only, "detail": detail, "annual": annual}


def checked_field_value(facts: Dict[str, Any], field: str, at: _dt.date, tol: int,
                        scale: Optional[float]) -> Dict[str, Any]:
    """`field_value` de un flujo con la comprobación de `checked_flow_ttm` (F10 · perímetro): {value: None, reason} si
    el TTM de EDGAR no es homogéneo o no tiene el periodo. Sin `scale` (sin ingresos del corte), `field_value`."""
    kind, sign = CONCEPTS[field][0], CONCEPTS[field][1]
    if kind != "flow" or not scale:
        r = field_value(facts, field, at, tol)
        return r if r is not None else {"value": None, "reason": "sin el periodo en EDGAR"}
    cands = candidates(facts, field)
    if not cands:
        return {"value": None, "reason": "sin el concepto en EDGAR"}
    concept, fs = cands[0]
    r = checked_flow_ttm(fs, at, tol, scale)
    if r["value"] is None:
        return {**r, "concept": concept}
    r["value"] = sign * r["value"]
    r.update(concept=concept, unit=reporting_unit(facts, taxonomy(facts)))
    return r


def debt_part(facts: Dict[str, Any], part: str, at: _dt.date, tol: int,
              latest_before: bool = False) -> Optional[Dict[str, Any]]:
    """Saldo de un componente de la deuda (DEBT_PARTS) a la fecha `at`: el total etiquetado o la suma de corriente y
    no corriente. Con `latest_before`, si no hay saldo a esa fecha, el del último informe ANUAL anterior (DUK solo
    etiqueta sus arrendamientos en el 10-K), y solo ese."""
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
        # Solo el ÚLTIMO informe anual anterior al corte (el balance anual más reciente del emisor). Si el componente
        # no está en él, el emisor ya no lo presenta: no se busca más atrás (con la historia larga, BAC traía una
        # deuda subordinada de 2012; fase 3, T1b).
        annual = sorted({f["end"] for f in (facts.get("facts") or {}).get(tax, {}).get("Assets", {}).get("units", {})
                         .get(unit) or [] if f.get("form") in ANNUAL_FORMS and _date(f["end"]) <= at}, reverse=True)
        if annual:
            r = at_date(_date(annual[0]), annual_only=True)
            if r is not None:
                basis = "ultimo_anual"
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


def annual_history(facts: Dict[str, Any], field: str) -> Dict[str, Any]:
    """Serie anual larga del campo (fase 3, T1b): {"values": [{fy_end, value, concept, taxonomy}, …] del ejercicio
    más reciente al más antiguo, "unit", "cross_taxonomy"}. Solo ejercicios enteros (350–380 días) de formularios
    anuales, el filing más reciente de cada periodo (reexpresiones) y, por ejercicio, el primer concepto de HISTORY
    que lo tenga. En la moneda de los estados, sin convertir. Con cambio de norma (HISTORY_CROSS_TAXONOMY), los
    ejercicios anteriores al primero de la taxonomía vigente salen de la otra y se declaran."""
    tax = taxonomy(facts)
    money = reporting_unit(facts, tax)
    kind, us, ifrs = HISTORY[field]
    out: Dict[str, Any] = {"values": [], "unit": None, "cross_taxonomy": None}
    if tax is None or money is None:
        return out
    unit = {"money": money, "per_share": f"{money}/shares", "shares": "shares"}[kind]
    out["unit"] = unit

    def years(tx: str, concepts) -> Dict[str, Dict[str, Any]]:
        by_end: Dict[str, Dict[str, Any]] = {}

        def annual(c) -> Dict[Tuple[str, str], Dict[str, Any]]:
            fs = (facts.get("facts") or {}).get(tx, {}).get(c, {}).get("units", {}).get(unit) or []
            cur: Dict[Tuple[str, str], Dict[str, Any]] = {}
            for f in fs:
                if f.get("form") in ANNUAL_FORMS and f.get("start") and 350 <= (_days(f) or 0) <= 380:
                    k = (f["start"], f["end"])
                    if k not in cur or (f.get("filed") or "") > (cur[k].get("filed") or ""):
                        cur[k] = f
            return cur
        per = {c: annual(c) for c in concepts}

        def rank(i, c):
            # F9 · R3 (una sola definición por serie): como `candidates`, primero el concepto que llega al ejercicio
            # más reciente; los demás solo completan los ejercicios que le faltan. HSBC: el beneficio atribuible
            # hasta 2022 y, desde 2023, solo ProfitLoss (con minoritarios); por prioridad, la serie mezclaba los dos.
            last = max((e for _s, e in per[c]), default="")
            total = max((f["val"] for (_s, e), f in per[c].items() if e == last), default=0.0) \
                if field in HISTORY_TOTAL_FIRST else 0.0
            return last, total, -i
        concepts = [c for *_k, c in sorted(((*rank(i, c), c) for i, c in enumerate(concepts)), reverse=True)]
        first = None
        for c in concepts:
            if not per[c]:
                continue
            if first is not None and field in HISTORY_SAME_DEFINITION:
                # F10 · B2: un concepto completa los ejercicios del primero solo si es la misma definición: si los dos
                # están en algún ejercicio, coinciden en el último común (EIX: NetIncomeLoss es el de los
                # propietarios y difiere del disponible para el común en los años con preferentes).
                common = sorted(e for _s, e in per[c] if e in by_end)
                if common:
                    f = next(f for (_s, e), f in per[c].items() if e == common[-1])
                    if not _close(f["val"], by_end[common[-1]]["value"]):
                        out.setdefault("concepts_rejected", []).append(
                            {"concept": f"{tx}:{c}", "fy_end": common[-1], "value": f["val"],
                             "series": by_end[common[-1]]["value"]})
                        continue
            for (s, e), f in per[c].items():
                by_end.setdefault(e, {"fy_end": e, "start": s, "value": f["val"], "concept": f"{tx}:{c}",
                                      "taxonomy": tx, "definition": f"{tx}:{first or c}"})
            first = first or c
        return by_end
    sign = CONCEPTS["capex"][1] if field == "capex" else 1
    main = years(tax, us if tax == "us-gaap" else ifrs)
    if kind in ("per_share", "shares") and main:
        _adjust_splits(main, facts, tax, us if tax == "us-gaap" else ifrs, unit, kind)
    if main and field in HISTORY_CROSS_VERIFIED:
        _cross_verified(main, years, tax, us, ifrs, out)
    if field in HISTORY_RELAY:
        _relay(field, main, years, tax, facts, out)
    if main and field in HISTORY_CROSS_TAXONOMY:
        other = "ifrs-full" if tax == "us-gaap" else "us-gaap"
        first = min(main)
        oth = years(other, ifrs if other == "ifrs-full" else us)
        older = {e: v for e, v in oth.items() if e < first}
        if older and kind == "per_share":
            # Split entre taxonomías (TM: 5:1 en 2021, el año del paso a NIIF): las acciones de la taxonomía vigente
            # no llegan a antes del split. El ejercicio que las dos presentan da el factor: FY2020 de TM, 720.3 en US
            # GAAP (antes del split) frente a 144.05 en NIIF (reexpresado).
            both = sorted(e for e in oth if e in main)
            r = _split_ratio(oth[both[-1]]["value"] / main[both[-1]]["value"]) if both and main[both[-1]]["value"] \
                else None
            if r is not None:
                for v in older.values():
                    v["value"] = v["value"] / r
                    v["split_adjusted"] = r
                out["cross_taxonomy_split"] = r
        if older:
            main.update(older)
            out["cross_taxonomy"] = {"taxonomy": other, "until": max(older), "years": len(older)}
    vals = [dict(v, value=sign * v["value"]) for _e, v in sorted(main.items(), reverse=True)]
    # F10 · B2 (LHX, KDP): un cambio de ejercicio deja dos periodos anuales que se solapan (LHX: julio 2018–junio
    # 2019 de Harris y el año natural 2019 tras la fusión); los dos salían como FY2019. Manda el más reciente.
    kept, overlap = [], []
    for v in vals:
        if kept and v.get("start") and kept[-1].get("start") and \
                _date(v["fy_end"]) > _date(kept[-1]["start"]) + _dt.timedelta(days=HISTORY_OVERLAP_DAYS):
            overlap.append(v["fy_end"])
            continue
        kept.append(v)
    vals = kept
    out["dropped_overlap"] = overlap or None
    if kind in ("per_share", "shares"):
        # Errores de escala de los primeros XBRL (NVDA FY2008: acciones en miles, 1,000 veces menos): un valor que
        # salta más de `HISTORY_SCALE_JUMP` veces frente al ejercicio siguiente no es un dato; se descarta y se dice.
        kept, dropped = [], []
        for i, v in enumerate(vals):
            nxt = kept[-1]["value"] if kept else None
            if nxt and v["value"] and not (1 / HISTORY_SCALE_JUMP < abs(v["value"] / nxt) < HISTORY_SCALE_JUMP):
                dropped.append(v["fy_end"])
                continue
            kept.append(v)
        vals = kept
        out["dropped_scale_errors"] = dropped or None
    out["values"] = vals
    if not vals:
        out["reason"] = HISTORY_MISSING.get(field)
    return out


def first_annual_period(facts: Dict[str, Any]) -> Optional[str]:
    """F10 · B2: cierre del ejercicio corriente del primer informe anual del emisor en la SEC (el mayor `end` de los
    hechos presentados con la fecha de presentación anual más antigua). TKO, constituida en 2023: 2023-12-31."""
    tax = taxonomy(facts)
    fs = [f for c in ((facts.get("facts") or {}).get(tax) or {}).values() for u in (c.get("units") or {}).values()
          for f in u if f.get("form") in ANNUAL_FORMS and f.get("filed") and f.get("end")]
    if not fs:
        return None
    first = min(f["filed"] for f in fs)
    return max(f["end"] for f in fs if f["filed"] == first)


def _close(a: float, b: float, abs_tol: float = 0.0) -> bool:
    return abs(a - b) <= max(cfg("data.edgar.history_relay_rel_tol") * abs(b), abs_tol)


def _cross_verified(main: Dict[str, Dict[str, Any]], years, tax: str, us, ifrs, out: Dict[str, Any]) -> None:
    """Ejercicios anteriores al cambio de norma desde la otra taxonomía, si coinciden en el último ejercicio común."""
    other = "ifrs-full" if tax == "us-gaap" else "us-gaap"
    oth = years(other, ifrs if other == "ifrs-full" else us)
    common = sorted(e for e in oth if e in main)
    older = {e: v for e, v in oth.items() if e < min(main)}
    if not older or not common:
        return
    last = common[-1]
    if not _close(oth[last]["value"], main[last]["value"]):
        out["cross_taxonomy_rejected"] = {"taxonomy": other, "fy_end": last, "value": oth[last]["value"],
                                          "current": main[last]["value"]}
        return
    main.update(older)
    out["cross_taxonomy"] = {"taxonomy": other, "until": max(older), "years": len(older), "verified_on": last}


def _relay(field: str, main: Dict[str, Dict[str, Any]], years, tax: str, facts: Dict[str, Any],
           out: Dict[str, Any]) -> None:
    """Relevo de conceptos (HISTORY_RELAY), in situ en `main`; lo declara en out["relay"]."""
    concepts = HISTORY_RELAY[field][0 if tax == "us-gaap" else 1]
    if field == "diluted_eps":
        ni = {v["fy_end"]: v["value"] for v in annual_history(facts, "net_income")["values"]}
        sh = {v["fy_end"]: v["value"] for v in annual_history(facts, "diluted_shares")["values"]}
    for c in concepts:
        cand = {e: v for e, v in years(tax, (c,)).items() if e not in main}
        if not cand:
            continue
        if field == "diluted_eps":
            # Cada ejercicio, solo si cuadra con beneficio neto / acciones diluidas.
            ok = {e: v for e, v in cand.items() if ni.get(e) is not None and sh.get(e)
                  and _close(v["value"], ni[e] / sh[e], cfg("data.edgar.history_eps_abs_tol"))}
            how = "cuadra con beneficio neto / acciones diluidas en cada ejercicio"
        elif not main:
            ok, how = cand, "único concepto con el que el emisor presenta el dato"
        else:
            both = {e: v for e, v in years(tax, (c,)).items() if e in main}
            last = max(both) if both else None
            if last is None or not _close(both[last]["value"], main[last]["value"]):
                continue
            ok = {e: v for e, v in cand.items() if e > max(main)}
            how = f"coincide con {main[last]['concept']} en el ejercicio {last[:4]}; toma los posteriores"
        if ok:
            main.update(ok)
            out.setdefault("relay", []).append({"concept": f"{tax}:{c}", "years": len(ok), "first": min(ok),
                                                "last": max(ok), "how": how})


def _split_ratio(r: float) -> Optional[float]:
    """Un cociente entre dos presentaciones del mismo periodo que es un split (2:1, 3:2, 4:1, 7:1, 20:1…) o un
    contrasplit; None si no lo parece (una reexpresión normal mueve el BPA unos puntos, no lo multiplica)."""
    for x, inv in ((r, False), (1.0 / r if r else 0.0, True)):
        if x >= 1.4 and abs(x * 2 - round(x * 2)) <= 0.06 * x:
            return round(x * 2) / 2 if not inv else 1.0 / (round(x * 2) / 2)
    return None


def _adjust_splits(main: Dict[str, Dict[str, Any]], facts: Dict[str, Any], tx: str, concepts, unit: str,
                   kind: str) -> None:
    """Ajusta por splits las series por acción y de acciones de la historia (fase 3, T2). companyfacts guarda cada
    ejercicio con la cifra de su informe; tras un split, solo los ejercicios que el emisor vuelve a presentar salen
    reexpresados (AAPL: 7:1 en 2014 y 4:1 en 2020). El factor sale de esas reexpresiones de las ACCIONES: el mismo
    periodo presentado antes y después del split. Cada ejercicio cuya cifra vigente se presentó antes del filing que reexpresa se ajusta
    con el producto de los splits posteriores (acciones × factor; BPA ÷ factor)."""
    events: List[Tuple[str, float]] = []
    # Los splits se leen SOLO en las acciones: un BPA se reexpresa también por cambios contables (AAPL reexpresó
    # 2007–2008 en 2009 por la contabilidad del iPhone, un cociente cercano a 3:2), las acciones no.
    share_concepts = HISTORY["diluted_shares"][1] if tx == "us-gaap" else HISTORY["diluted_shares"][2]
    for c in share_concepts:
        fs = (facts.get("facts") or {}).get(tx, {}).get(c, {}).get("units", {}).get("shares") or []
        by: Dict[Tuple[Optional[str], str], List[Dict[str, Any]]] = {}
        for f in fs:
            by.setdefault((f.get("start"), f["end"]), []).append(f)
        for g in by.values():
            g = sorted(g, key=lambda f: f.get("filed") or "")
            for a, b in zip(g, g[1:]):
                if a["val"] and b["val"]:
                    r = _split_ratio(b["val"] / a["val"])
                    if r is not None:
                        events.append((b.get("filed") or "", r))
    if not events:
        return
    # Un split aparece en muchos periodos: una vez por factor, con el primer filing que lo reexpresa.
    uniq: List[Tuple[str, float]] = []
    for fd, r in sorted(events):
        if not any(abs(r - r0) < 1e-9 and abs((_date(fd) - _date(f0)).days) <= 400 for f0, r0 in uniq):
            uniq.append((fd, r))
    filed_of: Dict[str, str] = {}
    for c in concepts:
        for f in (facts.get("facts") or {}).get(tx, {}).get(c, {}).get("units", {}).get(unit) or []:
            if f["end"] in main and f"{tx}:{c}" == main[f["end"]]["concept"] and f["val"] == main[f["end"]]["value"]:
                filed_of[f["end"]] = max(filed_of.get(f["end"], ""), f.get("filed") or "")
    for end, v in main.items():
        fv = filed_of.get(end, "")
        factor = 1.0
        for fd, r in uniq:
            if fd > fv:
                factor *= r
        if factor != 1.0:
            v["value"] = v["value"] * factor if kind == "shares" else v["value"] / factor
            v["split_adjusted"] = factor


def history(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Historia anual de todos los campos de HISTORY: {campo: annual_history}."""
    return {f: annual_history(facts, f) for f in HISTORY}


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


def _cover_of(cik: int, f: Dict[str, Any], budget: Budget) -> Optional[Dict[str, Any]]:
    acc = f["accessionNumber"].replace("-", "")
    found = _cached(f"cover:{acc}", cfg("data.edgar.facts_ttl_s"), lambda: parse_cover(
        _get(ARCHIVE_URL.format(cik=cik, acc=acc, name="R1.htm"), budget).decode("utf-8", "replace")), budget)
    if found is None:
        return None
    return {**found, "form": f["form"], "date": f["filingDate"], "accn": f["accessionNumber"]}


def cover_factor(cik: int, fl: List[Dict[str, Any]], budget: Budget) -> Optional[Dict[str, Any]]:
    """Factor de la portada del último 20-F/40-F del emisor (caché por número de filing), o None. V2 (decisión del
    PM): del ejercicio más reciente, el informe original, salvo que una enmienda posterior traiga la portada completa
    (con el factor): un 20-F/A de solo la Parte III no tiene los títulos del 12(b) y tapaba la portada del 20-F."""
    annual = [f for f in fl or [] if f["form"] in FOREIGN_ANNUAL_FORMS]
    if not annual:
        return None
    period = annual[0].get("reportDate")
    same = [f for f in annual if period and f.get("reportDate") == period] or annual[:1]
    originals = [f for f in same if not f["form"].endswith("/A")]
    amendments = [f for f in same if f["form"].endswith("/A")]
    if not originals:                       # solo hay enmiendas de ese ejercicio: la más reciente, como antes
        return _cover_of(cik, annual[0], budget)
    orig = originals[0]
    for a in amendments:                    # las posteriores al original, de la más reciente a la más antigua
        if (a["filingDate"], a["accessionNumber"]) > (orig["filingDate"], orig["accessionNumber"]):
            found = _cover_of(cik, a, budget)
            if found is not None:
                return found
    return _cover_of(cik, orig, budget)


# ───────────────────────── el análisis: etapa 1 y etapa 2 en un hilo ─────────────────────────

def _predecessors(ticker: str) -> Tuple[int, ...]:
    return tuple(int(c) for c in (cfg("data.edgar.predecessors") or {}).get(ticker.upper(), []))


def fetch(ticker: str, stage1: Optional[Future] = None, budget: Optional["Budget"] = None) -> Dict[str, Any]:
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
    budget = budget or Budget()
    res: Dict[str, Any] = {"status": "no_disponible", "reason": None, "cik": None, "filings": None}
    try:
        ent = cik_for(ticker, budget)
        if ent is None:
            return publish({"status": "sin_cik", "reason": "el ticker no figura en la lista de emisores de la SEC",
                            "cik": None, "filings": None, "latency_s": time.monotonic() - t0})
        _sub = submissions(ent["cik"], budget)
        fl = _sub["filings"]
        res = {"status": "ok", "reason": None, "cik": ent["cik"], "title": ent.get("title"), "filings": fl,
               "country": _sub["country"], "profile": _sub.get("profile"), "cover": None, "cover_reason": None}
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
    budget = Budget() if status()["enabled"] else None
    fut = _pool.submit(fetch, ticker, stage1, budget)
    fut.edgar_budget = budget            # collect espera también lo que el análisis estuvo en cola
    return fut


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
        b = getattr(future, "edgar_budget", None)
        end = time.monotonic() + _wait_s()
        while True:
            # la espera se alarga con la cola que el presupuesto no cuenta (hallazgo 2 de la revisión de F6)
            left = end + (b.queued_s if b else 0.0) - time.monotonic()
            try:
                res = future.result(timeout=max(min(left, 0.5), 0.0))
                break
            except FutureTimeout:
                if end + (b.queued_s if b else 0.0) - time.monotonic() <= 0:
                    raise
    except Exception as e:  # tiempo agotado u otro fallo del hilo
        res = {"status": "no_disponible", "reason": failure_reason(e), "cik": None, "filings": None}
    return retry_if_transient(res, ticker)


def transient(res: Dict[str, Any]) -> bool:
    """EDGAR no respondió (tiempo agotado, presupuesto, red), no «no existe»: sin_cik, sin_estados y desactivado no lo
    son."""
    return (res or {}).get("status") == "no_disponible" or (res or {}).get("facts_status") == "no_disponible"


def retry_if_transient(res: Dict[str, Any], ticker: Optional[str], fetcher=None) -> Dict[str, Any]:
    """F10 (PM, 29-oct; ENB y RL): un tiempo agotado de EDGAR no cambia el análisis en silencio. Un reintento con su
    propio presupuesto (`data.edgar.retry_s`); si una descarga del primer intento sigue en curso, la caché hace que se
    espere su resultado en vez de repetirla. Se queda el mejor de los dos y `retried` lo dice."""
    if not ticker or not transient(res):
        return res
    try:
        again = (fetcher or fetch)(ticker, None, Budget(cfg("data.edgar.retry_s")))
    except Exception as e:  # el reintento nunca rompe el análisis
        again = {"status": "no_disponible", "reason": failure_reason(e)}
    better = not transient(again) or (res.get("status") != "ok" and again.get("status") == "ok")
    return {**(again if better else res), "retried": True,
            "retry_reason": (res.get("facts_reason") or res.get("reason"))}


def failure_reason(e: BaseException) -> str:
    """Motivo legible de un fallo de EDGAR. Verificación de la v4 (V3): el tiempo agotado llegaba como
    "TimeoutError: " (el error de concurrent.futures no trae mensaje) y así se mostraba en la página."""
    if isinstance(e, (TimeoutError, FutureTimeout)):
        return f"EDGAR no respondió a tiempo (presupuesto de {cfg('data.edgar.budget_s'):g} s agotado)"
    msg = str(e).strip()
    return f"{type(e).__name__}: {msg}" if msg else type(e).__name__


def summary(ed: Dict[str, Any]) -> Dict[str, Any]:
    """Registro para data_provenance.edgar (sin los hechos ni la lista de filings)."""
    out = {k: ed.get(k) for k in ("status", "reason", "cik", "title")}
    for k in ("facts_status", "facts_reason", "pending_filings", "cover", "cover_reason", "captive", "country",
              "profile"):
        if ed.get(k) is not None:
            out[k] = ed[k]
    return out


def report_date(f: Dict[str, Any]) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(f["reportDate"]) if f.get("reportDate") else None
    except ValueError:
        return None


def with_statements(f: Dict[str, Any]) -> bool:
    """Filing periódico con estados: 10-Q/10-K/20-F/40-F, o un 6-K con XBRL."""
    return f["form"] in ANNUAL_OR_QUARTERLY or (f["form"].startswith("6-K") and bool(f.get("isXBRL")))


def newer_statements(fl: Optional[List[Dict[str, Any]]], cut: str) -> List[Dict[str, Any]]:
    """Filings con estados de un periodo posterior al corte (más allá de la tolerancia de fechas)."""
    c = _dt.date.fromisoformat(cut) + _dt.timedelta(days=cfg("data.edgar.report_date_tolerance_days"))
    return [f for f in fl or [] if with_statements(f) and report_date(f) and report_date(f) > c]


def pending_results(fl: Optional[List[Dict[str, Any]]], cut: Optional[str]) -> Optional[Dict[str, Any]]:
    """F2_PRECEDENCIA §1.1: resultados publicados después del corte y aún no incorporados.

    Un 10-Q/10-K/20-F/40-F (o un 6-K con XBRL) cuyo periodo es posterior al corte, o un 8-K del apartado 2.02
    (Results of Operations) presentado después del filing periódico que cubre el corte (sin ese filing, después del
    corte). Un 8-K no avanza el corte: solo se avisa. Devuelve el más reciente o None."""
    if not fl or not cut:
        return None
    tol = _dt.timedelta(days=cfg("data.edgar.report_date_tolerance_days"))
    c = _dt.date.fromisoformat(cut)
    rd = report_date
    covering = [f for f in fl if with_statements(f) and rd(f) and abs(rd(f) - c) <= tol]
    base = max([f["filingDate"] for f in covering] + [cut])
    newer = newer_statements(fl, cut)
    # Fase 6: un 8-K de resultados dentro de `calendar_min_lag_days` del corte es el comunicado del propio corte, aunque
    # llegue después de su 10-Q (BRK-B: 10-Q el 2026-08-10, 8-K el 08-11). Los del trimestre siguiente llegan después.
    own = (c + _dt.timedelta(days=cfg("data.edgar.calendar_min_lag_days"))).isoformat()
    results_8k = [f for f in fl if f["form"] in ("8-K", "8-K/A") and "2.02" in (f.get("items") or "")
                  and f["filingDate"] > max(base, own)]
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
        _fetching.clear()
