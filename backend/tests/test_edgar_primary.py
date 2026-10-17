"""
Fase 3 (T1b): SEC EDGAR como fuente principal, campo a campo (D2), con las definiciones aprobadas en la parada 1
(F3_T1_PARADA1 §1, registro #25 de la bitácora):

  · EBIT: el resultado operativo que presenta el emisor (no el que construye Yahoo), en el corte y en las filas
    anuales; el EBITDA se mueve con él (la D&A no cambia). Bancos: no aplica (no se toca);
  · ingresos de aseguradoras y conglomerados (BRK-B): sin ganancias de inversión;
  · ingresos de bancos de EE. UU.: ingresos netos totales;
  · capex de emisores con financiera cautiva (CAT): sin el equipo que la cautiva arrienda a terceros.
"""
import datetime as dt

import pytest

import edgar_primary
import sec_edgar as edgar


def _f(start, end, val, filed, form="10-Q", accn="a"):
    out = {"end": end, "val": val, "filed": filed, "form": form, "accn": accn}
    if start:
        out["start"] = start
    return out


def _ed(concepts, unit="USD", tax="us-gaap"):
    facts = {"facts": {tax: {"Assets": {"units": {unit: [_f(None, "2025-12-31", 10, "2026-02-01", "10-K", "k")]}},
                             **concepts}}}
    return {"status": "ok", "facts_status": "ok", "facts": edgar._index_facts(facts)}


def _fy(concept, values, unit="USD"):
    """Ejercicios naturales 2025, 2024, … con su valor (10-K)."""
    return {concept: {"units": {unit: [_f(f"{2025 - i}-01-01", f"{2025 - i}-12-31", v, f"{2026 - i}-02-01", "10-K",
                                          f"k{i}") for i, v in enumerate(values)]}}}


def _info(cut="2025-12-31", **kw):
    info = {"symbol": "ZZZ", "currency": "USD", "_as_of": {"type": "ttm", "date": cut, "fields": {}},
            "_provenance": {}}
    info.update(kw)
    return info


def _fields(info, *keys, end="2025-12-31"):
    for k in keys:
        info["_as_of"]["fields"][k] = {"period_end": end, "period_type": "ttm"}


# ───────────── EBIT reportado ─────────────

def test_ebit_of_the_cut_is_the_reported_one_and_ebitda_is_ebit_plus_da():
    ed = _ed(_fy("OperatingIncomeLoss", [13762]))
    info = _info(operatingIncome=14911.0, ebitda=16000.0, depreciation=-1100.0)
    _fields(info, "operatingIncome", "ebitda")
    log = edgar_primary.apply(info, ed)
    assert info["operatingIncome"] == 13762
    assert info["ebitda"] == 13762 + 1100, "parada 1b (opción a): EBITDA = EBIT del emisor + D&A"
    assert info["_provenance"]["ebitda"]["source"] == "derivado"
    assert info["_provenance"]["operatingIncome"]["source"] == "sec_edgar"
    assert info["_as_of"]["fields"]["operatingIncome"]["source"] == "sec_edgar"
    assert [x["field"] for x in log["cut"]] == ["operatingIncome"]
    assert log["cut"][0]["replaced"] == 14911.0


def test_ebit_annual_rows_are_the_reported_ones():
    ed = _ed(_fy("OperatingIncomeLoss", [13762, 9992, 11311]))
    st = {"inc_ends": ["2025-12-31", "2024-12-31", "2023-12-31"], "operating_income": [14911.0, 14022.0, 13098.0],
          "ebit": [14911.0, 14022.0, 13098.0], "ebitda": [16000.0, 15100.0, 14200.0],
          "cf_ends": ["2025-12-31", "2024-12-31"], "depreciation_amortization": [-1100.0, -1050.0]}
    info = _info(_statements_fy=st)
    edgar_primary.apply(info, ed)
    assert st["operating_income"] == [13762, 9992, 11311]
    assert st["ebit"] == [14911.0, 14022.0, 13098.0], "la fila EBIT de Yahoo (con lo no operativo) no cambia: ROCE"
    assert st["ebitda"] == [13762 + 1100, 9992 + 1050, 14200.0], "sin la D&A del ejercicio, el EBITDA no cambia"


def test_ebit_without_the_cut_in_edgar_stays_with_the_source():
    """20-F sin trimestres: el TTM de Yahoo se queda (ebit_check lo marcará "estimado por la fuente")."""
    ed = _ed(_fy("OperatingIncomeLoss", [100]))
    info = _info(cut="2026-06-30", operatingIncome=120.0)
    _fields(info, "operatingIncome", end="2026-06-30")
    log = edgar_primary.apply(info, ed)
    assert info["operatingIncome"] == 120.0
    assert any(x["field"] == "operatingIncome" and "no lo tiene" in x["reason"] for x in log["skipped"])


def test_bank_ebit_is_not_touched():
    ed = _ed(_fy("OperatingIncomeLoss", [5]))
    info = _info(operatingIncome=7.0, sector="Financial Services", industry="Banks - Diversified")
    _fields(info, "operatingIncome")
    log = edgar_primary.apply(info, ed)
    assert info["operatingIncome"] == 7.0
    assert any("no aplica" in x["reason"] for x in log["skipped"])


def test_same_value_is_not_logged_as_a_replacement():
    ed = _ed(_fy("OperatingIncomeLoss", [100]))
    info = _info(operatingIncome=100.4)
    _fields(info, "operatingIncome")
    log = edgar_primary.apply(info, ed)
    assert info["operatingIncome"] == 100, "manda EDGAR aunque coincida"
    assert log["cut"][0]["replaced"] == 100.4


# ───────────── ingresos ─────────────

def test_conglomerate_revenue_excludes_investment_gains():
    ed = _ed({**_fy("Revenues", [371444]), **_fy("GainLossOnInvestments", [39078])})
    info = _info(totalRevenue=410522.0, sector="Financial Services", industry="Insurance - Diversified")
    _fields(info, "totalRevenue")
    edgar_primary.apply(info, ed)
    assert info["totalRevenue"] == 371444


def test_us_bank_revenue_is_net_revenue():
    ed = _ed(_fy("RevenuesNetOfInterestExpense", [182447]))
    info = _info(totalRevenue=170000.0, sector="Financial Services", industry="Banks - Diversified")
    _fields(info, "totalRevenue")
    edgar_primary.apply(info, ed)
    assert info["totalRevenue"] == 182447


def test_ifrs_bank_revenue_stays_with_the_source():
    """BCS: "Total income" no tiene etiqueta estándar en IFRS (parada 1, §1.2)."""
    ed = _ed({"RevenueFromContractsWithCustomers": {"units": {"GBP": [
        _f("2025-01-01", "2025-12-31", 11110, "2026-02-10", "20-F")]}}}, unit="GBP", tax="ifrs-full")
    info = _info(totalRevenue=29140.0, sector="Financial Services", industry="Banks - Diversified",
                 _currency={"statements": "GBP"})
    _fields(info, "totalRevenue")
    edgar_primary.apply(info, ed)
    assert info["totalRevenue"] == 29140.0


def test_industrial_revenue_stays_with_the_source():
    ed = _ed(_fy("Revenues", [332238]))
    info = _info(totalRevenue=323900.0, sector="Energy", industry="Oil & Gas Integrated")
    _fields(info, "totalRevenue")
    edgar_primary.apply(info, ed)
    assert info["totalRevenue"] == 323900.0


# ───────────── capex con cautiva ─────────────

def test_captive_capex_excludes_equipment_leased_to_others():
    ed = _ed({**_fy("PaymentsToAcquirePropertyPlantAndEquipment", [2821, 1988]),
              **_fy("PaymentsToAcquireEquipmentOnLease", [1465, 1227])})
    st = {"cf_ends": ["2025-12-31", "2024-12-31"], "capital_expenditure": [-4286.0, -3215.0],
          "operating_cash_flow": [12000.0, 11000.0], "free_cash_flow": [7714.0, 7785.0]}
    info = _info(symbol="CAT", capitalExpenditures=-4286.0, operatingCashflow=12000.0, freeCashflow=7714.0,
                 _statements_fy=st)
    _fields(info, "capitalExpenditures", "operatingCashflow", "freeCashflow")
    edgar_primary.apply(info, ed)
    assert info["capitalExpenditures"] == -2821
    assert info["freeCashflow"] == 12000 - 2821
    assert st["capital_expenditure"] == [-2821, -1988] and st["free_cash_flow"] == [12000 - 2821, 11000 - 1988]


def test_capex_without_captive_stays_with_the_source():
    ed = _ed(_fy("PaymentsToAcquirePropertyPlantAndEquipment", [302]))
    info = _info(symbol="CRWD", capitalExpenditures=-371.0)
    _fields(info, "capitalExpenditures")
    edgar_primary.apply(info, ed)
    assert info["capitalExpenditures"] == -371.0, "el software capitalizado es capex (definición aprobada)"


# ───────────── degradación ─────────────

def test_without_edgar_nothing_changes():
    info = _info(operatingIncome=1.0)
    log = edgar_primary.apply(info, {"status": "desactivado", "reason": "sin User-Agent"})
    assert info["operatingIncome"] == 1.0 and log["cut"] == [] and log["reason"] == "sin User-Agent"


def test_currencies_are_not_mixed():
    ed = _ed(_fy("OperatingIncomeLoss", [5], unit="EUR"), unit="EUR")
    info = _info(operatingIncome=7.0, _currency={"statements": "USD"})
    _fields(info, "operatingIncome")
    log = edgar_primary.apply(info, ed)
    assert info["operatingIncome"] == 7.0 and "no se mezclan" in log["reason"]


def test_converted_like_the_source_when_the_quote_is_in_another_currency():
    class Ctx:
        convert_currency = True

        def convert_amount(self, v, kind, end):
            return v * 1.1
    ed = _ed(_fy("ProfitLossFromOperatingActivities", [100], unit="EUR"), unit="EUR", tax="ifrs-full")
    info = _info(operatingIncome=130.0, _currency={"statements": "EUR"})
    _fields(info, "operatingIncome")
    edgar_primary.apply(info, ed, Ctx())
    assert info["operatingIncome"] == pytest.approx(110)


def test_industry_with_an_em_dash_is_normalised_like_the_classifier():
    """BRK-B: Yahoo da "Insurance—Diversified" (raya), no "Insurance - Diversified"."""
    ed = _ed(_fy("Revenues", [371444]))
    info = _info(totalRevenue=410522.0, sector="Financial Services", industry="Insurance—Diversified")
    _fields(info, "totalRevenue")
    edgar_primary.apply(info, ed)
    assert info["totalRevenue"] == 371444


def test_without_da_the_ebitda_of_the_cut_stays():
    ed = _ed(_fy("OperatingIncomeLoss", [100]))
    info = _info(operatingIncome=120.0, ebitda=150.0)
    _fields(info, "operatingIncome")
    edgar_primary.apply(info, ed)
    assert info["ebitda"] == 150.0
