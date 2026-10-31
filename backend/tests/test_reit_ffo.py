"""
F8 · E3 (auditoría externa del 26-oct-2026): FFO de los REIT según Nareit (lib/reit_ffo.py).

FFO = beneficio neto + D&A − ventas de inmuebles + deterioros, con los ajustes del estado de flujos que presentó el
emisor (conceptos estándar o propios), conciliado con el flujo de operaciones de EDGAR. Antes era beneficio + D&A.
Cifras de los casos: PLD y O, 10-K de 2025 y 10-Q del 2T-2026 (registro F8_INDEPENDIENTES §E3).
"""
import pytest

import archetype_metrics
import reit_ffo as rf
from classify import REIT, reit_industry


# ───────────────────────── partidas ─────────────────────────

def test_pld_partidas_propias():
    """PLD etiqueta sus ventas con conceptos propios: las de inmuebles de inversión se restan; las de promociones y
    terrenos (opcionales en Nareit) se quedan dentro, como en el FFO Nareit que publica PLD."""
    assert rf.item_of("pld_GainsOnOtherDispositionsOfInvestmentsInRealEstateNet") == rf.GAINS
    assert rf.item_of("pld_GainsOnDispositionsOfDevelopmentPropertiesAndLandNet") is None
    assert rf.item_of("pld_StraightLineRentsAndAmortizationOfAboveAndBelowMarketLeases") == rf.STRAIGHT_LINE
    assert rf.item_of("pld_PaymentForPropertyImprovements") == rf.RECURRING_CAPEX
    assert rf.item_of("us-gaap_PaymentsForLeasingCostsCommissionsAndTenantImprovements") == rf.RECURRING_CAPEX


def test_partidas_estandar_y_exclusiones():
    assert rf.item_of("us-gaap_GainLossOnSaleOfProperties") == rf.GAINS                      # O
    assert rf.item_of("us-gaap_GainsLossesOnSalesOfInvestmentRealEstate") == rf.GAINS
    assert rf.item_of("us-gaap_ImpairmentOfRealEstate") == rf.IMPAIRMENT                    # O
    assert rf.item_of("us-gaap_RestructuringCostsAndAssetImpairmentCharges") == rf.IMPAIRMENT  # AMT
    # Venta y deterioro en una partida: ganancia neta (IRM, ELS).
    assert rf.item_of("us-gaap_GainLossOnSalesOfAssetsAndAssetImpairmentCharges") == rf.GAINS
    # SPG: venta de participaciones en inmuebles sí; en negocios que no son inmuebles (minoristas), no.
    assert rf.item_of("spg_AcquisitionOfControllingInterestSaleOrDisposalOfOrRecoveryOnAssetsAndInterestsIn"
                      "UnconsolidatedEntitiesGainOrLossAndImpairmentNet") == rf.GAINS
    assert rf.item_of("spg_GainLossOnDisposalExchangeOrEvaluationOfEquityInterests") is None
    for c in ("us-gaap_GainsLossesOnExtinguishmentOfDebt", "us-gaap_ForeignCurrencyTransactionGainLossUnrealized",
              "us-gaap_ProvisionForLoanLossesExpensed", "us-gaap_PaymentsToDevelopRealEstateAssets",
              "us-gaap_DiscontinuedOperationGainLossOnDisposalOfDiscontinuedOperationNetOfTax",
              "amt_LossGainOnInvestmentsAndOtherNonCashIncomeExpense", "us-gaap_GoodwillImpairmentLoss",
              "us-gaap_ProfitLoss"):
        assert rf.item_of(c) is None, c
    assert rf.keep("us-gaap_NetCashProvidedByUsedInOperatingActivities")
    assert rf.keep("us-gaap_IncomeLossFromEquityMethodInvestments")


def test_industria_reit():
    assert reit_industry("REIT—Industrial") and reit_industry("REIT - Retail")
    assert not reit_industry("Real Estate Services") and not reit_industry(None)


# ───────────────────────── TTM y conciliación ─────────────────────────

def _e(form, accn, start, end, filed, **lines):
    return {"form": form, "accn": accn, "start": start, "end": end, "filed": filed,
            "lines": [{"concept": c.replace("us_gaap_", "us-gaap_"), "label": c, "value": v, "unit": "u_usd"}
                      for c, v in lines.items()]}


# PLD, del estado de flujos presentado (USD).
PLD_ANNUAL = [_e("10-K", "K25", "2025-01-01", "2025-12-31", "2026-02-13",
                 pld_GainsOnOtherDispositionsOfInvestmentsInRealEstateNet=685831000,
                 pld_GainsOnDispositionsOfDevelopmentPropertiesAndLandNet=257731000,
                 pld_StraightLineRentsAndAmortizationOfAboveAndBelowMarketLeases=691090000,
                 us_gaap_PaymentsForLeasingCostsCommissionsAndTenantImprovements=562197000,
                 pld_PaymentForPropertyImprovements=327355000,
                 us_gaap_IncomeLossFromEquityMethodInvestments=402531000, us_gaap_ProfitLoss=3565299000,
                 us_gaap_NetCashProvidedByUsedInOperatingActivities=5008434000),
              _e("10-K", "K24", "2024-01-01", "2024-12-31", "2025-02-14",
                 pld_GainsOnOtherDispositionsOfInvestmentsInRealEstateNet=904136000,
                 us_gaap_NetCashProvidedByUsedInOperatingActivities=1)]
PLD_QUARTERLY = [_e("10-Q", "Q226", "2026-01-01", "2026-06-30", "2026-07-29",
                    pld_GainsOnOtherDispositionsOfInvestmentsInRealEstateNet=303489000,
                    pld_StraightLineRentsAndAmortizationOfAboveAndBelowMarketLeases=326901000,
                    us_gaap_PaymentsForLeasingCostsCommissionsAndTenantImprovements=257775000,
                    pld_PaymentForPropertyImprovements=97283000,
                    us_gaap_IncomeLossFromEquityMethodInvestments=240766000, us_gaap_ProfitLoss=2168769000,
                    us_gaap_NetCashProvidedByUsedInOperatingActivities=2635011000),
                 _e("10-Q", "Q225", "2025-01-01", "2025-06-30", "2025-07-30",
                    pld_GainsOnOtherDispositionsOfInvestmentsInRealEstateNet=83843000,
                    pld_StraightLineRentsAndAmortizationOfAboveAndBelowMarketLeases=368162000,
                    us_gaap_PaymentsForLeasingCostsCommissionsAndTenantImprovements=275365000,
                    pld_PaymentForPropertyImprovements=103139000,
                    us_gaap_IncomeLossFromEquityMethodInvestments=175582000, us_gaap_ProfitLoss=1261824000,
                    us_gaap_NetCashProvidedByUsedInOperatingActivities=2402470000)]


def _facts(ocf):
    """companyfacts mínimo: Assets (taxonomía y moneda) y el flujo de operaciones de cada periodo."""
    return {"facts": {"us-gaap": {
        "Assets": {"units": {"USD": [{"end": "2026-06-30", "val": 1, "form": "10-Q", "filed": "2026-07-29",
                                      "accn": "Q226"}]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            {"start": s, "end": e, "val": v, "form": "10-K", "filed": "2026-07-29", "accn": "x"}
            for (s, e), v in ocf.items()]}}}}}


PLD_OCF = {("2025-01-01", "2025-12-31"): 5008434000, ("2026-01-01", "2026-06-30"): 2635011000,
           ("2025-01-01", "2025-06-30"): 2402470000}
INFO = {"_as_of": {"type": "ttm", "date": "2026-06-30"}, "_currency": {"statements": "USD"}}


def _fetch(annual, quarterly):
    return lambda _s, freq: annual if freq == "annual" else quarterly


def test_pld_ttm_y_conciliacion():
    res = rf.resolve("PLD", INFO, _facts(PLD_OCF), fetch=_fetch(PLD_ANNUAL, PLD_QUARTERLY))
    assert res["status"] == "ok" and res["reconciliation"]["status"] == "conciliado"
    # TTM = ejercicio 2025 + acumulado 2026 − acumulado 2025
    assert res["items"][rf.GAINS]["value"] == 685831000 + 303489000 - 83843000
    assert res["items"][rf.IMPAIRMENT]["value"] == 0.0          # partida ausente del estado completo: 0
    assert res["items"][rf.RECURRING_CAPEX]["value"] == (562197000 + 327355000 + 257775000 + 97283000
                                                         - 275365000 - 103139000)
    assert res["equity_method_income"] == 402531000 + 240766000 - 175582000
    assert "10-K K25" in res["period"]["how"] and "10-Q Q226" in res["period"]["how"]
    assert res["fy"]["2025-12-31"][rf.GAINS] == 685831000


def test_pld_ffo_nareit_dentro_de_10pct_del_publicado():
    """Afirmación de la auditoría (§6): FFO de PLD a ±10 % del publicado. FFO Nareit de PLD, TTM al 2T-2026:
    5.679,5 + 3.367,8 − 2.598,0 = 6.449,3 millones (comunicados del 4T-2025 y del 2T-2026)."""
    res = rf.resolve("PLD", INFO, _facts(PLD_OCF), fetch=_fetch(PLD_ANNUAL, PLD_QUARTERLY))
    out = rf.compute(4202444000, 2737773000, res)        # beneficio y D&A TTM del motor
    assert abs(out["ffo"] / 6449.3e6 - 1) <= 0.10
    assert abs(out["ffo"] - (4202444000 + 2737773000 - 905477000)) < 1
    assert "participadas" in out["equity_method_warning"]          # participadas: 7,8 % del FFO
    assert "minoritarios" not in out["equity_method_warning"]      # 270 millones: 4,5 %, por debajo del 5 %
    assert out["minority_income"] == pytest.approx(3565299000 + 2168769000 - 1261824000 - 4202444000)
    assert out["affo"] == out["ffo"] - res["items"][rf.STRAIGHT_LINE]["value"] - res["items"][rf.RECURRING_CAPEX]["value"]
    assert "−" in out["formula_values"] and out["affo_formula"]


def test_sin_conciliar_no_hay_ffo():
    bad = dict(PLD_OCF)
    bad[("2026-01-01", "2026-06-30")] = 2000000000                     # no coincide con el estado presentado
    res = rf.resolve("PLD", INFO, _facts(bad), fetch=_fetch(PLD_ANNUAL, PLD_QUARTERLY))
    assert res["status"] == "sin_dato" and res["reconciliation"]["status"] == "no_conciliado"
    missing = {k: v for k, v in PLD_OCF.items() if k[0] != "2025-01-01" or k[1] != "2025-06-30"}
    res = rf.resolve("PLD", INFO, _facts(missing), fetch=_fetch(PLD_ANNUAL, PLD_QUARTERLY))
    assert res["status"] == "sin_dato" and res["reconciliation"]["status"] == "sin_hecho_edgar"
    assert rf.resolve("PLD", INFO, None, fetch=_fetch(PLD_ANNUAL, PLD_QUARTERLY))["status"] == "sin_dato"
    assert rf.resolve("PLD", INFO, _facts(PLD_OCF), fetch=_fetch(None, None))["status"] == "sin_dato"


def test_corte_de_ejercicio():
    info = {"_as_of": {"type": "fy", "date": "2025-12-31"}, "_currency": {"statements": "USD"}}
    res = rf.resolve("PLD", info, _facts(PLD_OCF), fetch=_fetch(PLD_ANNUAL, []))
    assert res["status"] == "ok" and res["items"][rf.GAINS]["value"] == 685831000


def test_sin_ajustes_no_hay_ffo_ni_affo():
    out = rf.compute(100.0, 50.0, rf.no_data("sin clave de Finnhub"))
    assert out["ffo"] is None and "sin clave de Finnhub" in out["ffo_reason"] and out["affo"] is None


def test_affo_sin_capex_recurrente_es_sin_dato():
    q = [dict(e, lines=[ln for ln in e["lines"] if rf.item_of(ln["concept"]) != rf.RECURRING_CAPEX])
         for e in PLD_QUARTERLY]
    a = [dict(e, lines=[ln for ln in e["lines"] if rf.item_of(ln["concept"]) != rf.RECURRING_CAPEX])
         for e in PLD_ANNUAL]
    res = rf.resolve("PLD", INFO, _facts(PLD_OCF), fetch=_fetch(a, q))
    out = rf.compute(4202444000, 2737773000, res)
    assert out["ffo"] is not None and out["affo"] is None and "capex recurrente" in out["affo_reason"]


def test_aviso_de_participadas_solo_si_pesan():
    res = rf.resolve("PLD", INFO, _facts(PLD_OCF), fetch=_fetch(PLD_ANNUAL, PLD_QUARTERLY))
    res = dict(res, equity_method_income=10.58e6, consolidated_net_income=1267577000)   # O: 0,3 % del FFO
    assert rf.compute(1267577000, 2542368000, res)["equity_method_warning"] is None


def _spg_res(jv):
    """SPG, TTM al 2T-2026 (estado presentado, conciliado con EDGAR): ventas 2.952,7 millones, sin deterioros."""
    items = {it: {"value": 0.0, "lines": []} for it in rf.ITEMS}
    items[rf.GAINS] = {"value": 2952657000.0, "lines": [{"concept": "spg_GainOnSale", "value": 1}]}
    return {"status": "ok", "items": items, "fy": {}, "equity_method_income": jv, "consolidated_net_income": None,
            "period": {"cut": "2026-06-30"}, "reconciliation": {"status": "conciliado"}}


def test_participadas_materiales_dan_sin_dato():
    """Decisión del 27-oct-2026: SPG tiene participadas por 448,7 millones en el TTM (el 12,7 % del FFO calculado,
    3.526): su parte de la D&A, que Nareit suma y el XBRL no separa, deja el FFO un 25 % por debajo del publicado. El
    FFO es «sin dato» (no un FFO con aviso), igual que el AFFO, y el P/FFO no puntúa."""
    out = rf.compute(4617151000.0, 1861509000.0, _spg_res(448733000.0))
    assert out["ffo"] is None and out["affo"] is None and out["jv_material"]
    assert rf.JV_REASON in out["ffo_reason"] and "12,7 %" in out["ffo_reason"] and "10 %" in out["ffo_reason"]
    ratios, km = {"ffo": 6.4e9, "p_ffo": 14.0, "ffo_payout": 0.5, "ebitda": None}, {"ffo": 6.4e9, "p_ffo": 14.0}
    d = {"net_income": 4617151000.0, "depreciation": 1861509000.0, "shares_outstanding": 326e6, "price": 180.0,
         "dividends_paid": 2.9e9}
    rf.apply(ratios, km, d, _spg_res(448733000.0))
    assert ratios["p_ffo"] is None and km["p_ffo"] is None and km["ffo"] is None and km["p_affo"] is None
    # Por debajo del umbral, FFO con su aviso (PLD: 7,8 %).
    out = rf.compute(4617151000.0, 1861509000.0, _spg_res(0.08 * 3526003000.0))
    assert out["ffo"] == pytest.approx(3526003000.0) and "participadas" in out["equity_method_warning"]


def test_participadas_materiales_en_la_serie_anual():
    st = {"net_income": [100.0, 90.0, 80.0, 70.0], "depreciation_amortization": [-50.0] * 4,
          "ordinary_shares": [10.0] * 4, "inc_ends": ["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"]}
    zero = {rf.GAINS: 0.0, rf.IMPAIRMENT: 0.0, "equity_method": 1.0}
    res = {"status": "ok", "fy": {"2025-12-31": dict(zero, equity_method=30.0), "2024-12-31": zero,
                                  "2023-12-31": zero, "2022-12-31": zero}}
    v = archetype_metrics.compute(REIT, st, {}, reit_ffo=res)
    assert v["ffo_series"] == [None, 140.0, 130.0, 120.0]       # 2025: 30 de 150 (20 %), sin dato
    assert v["ffo_per_share_cagr_3y"] is None and rf.JV_REASON in v["ffo_per_share_cagr_3y_reason"]


def test_aviso_de_minoritarios():
    """AMT: la parte de los minoritarios en el beneficio (beneficio consolidado − el de los accionistas) pesa: Nareit
    resta su parte de la D&A, que el XBRL no separa."""
    res = rf.resolve("PLD", INFO, _facts(PLD_OCF), fetch=_fetch(PLD_ANNUAL, PLD_QUARTERLY))
    res = dict(res, equity_method_income=0.0, consolidated_net_income=3401e6 + 500e6)
    out = rf.compute(3401e6, 2071e6, res)
    assert out["minority_income"] == 500e6 and "minoritarios" in out["equity_method_warning"]
    assert "participadas" not in out["equity_method_warning"]


def test_apply_sustituye_ffo_pffo_y_payout():
    res = rf.resolve("PLD", INFO, _facts(PLD_OCF), fetch=_fetch(PLD_ANNUAL, PLD_QUARTERLY))
    ratios = {"ffo": 6940217000.0, "p_ffo": 17.69, "ffo_payout": 0.56, "ebitda": None}
    km = dict(ratios)
    d = {"net_income": 4202444000, "depreciation": 2737773000, "shares_outstanding": 972091372, "price": 126.31,
         "dividends_paid": 3885000000}
    out = rf.apply(ratios, km, d, res)
    assert ratios["ffo"] == km["ffo"] == out["ffo"] < 6940217000.0
    assert abs(km["p_ffo"] - 126.31 / (out["ffo"] / 972091372)) < 1e-9 and km["p_ffo"] > 17.69
    assert km["affo"] == out["affo"] and km["p_affo"] > km["p_ffo"]
    rf.apply(ratios, km, d, rf.no_data("x"))
    assert ratios["p_ffo"] is None and km["ffo"] is None


# ───────────────────────── serie anual ─────────────────────────

def test_ffo_anual_nareit():
    """FFO anual = beneficio + D&A − ventas + deterioros de cada ejercicio (la misma definición que el TTM)."""
    st = {"net_income": [100.0, 90.0, 80.0, 70.0], "depreciation_amortization": [-50.0, -50.0, -50.0, -50.0],
          "ebitda": [999.0] * 4, "ebit": [1.0] * 4, "ordinary_shares": [10.0] * 4,
          "inc_ends": ["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"]}
    res = {"status": "ok", "fy": {"2025-12-31": {rf.GAINS: 20.0, rf.IMPAIRMENT: 5.0},
                                  "2024-12-31": {rf.GAINS: 0.0, rf.IMPAIRMENT: 0.0},
                                  "2022-12-31": {rf.GAINS: 10.0, rf.IMPAIRMENT: 0.0}}}
    v = archetype_metrics.compute(REIT, st, {}, reit_ffo=res)
    assert v["ffo_series"] == [135.0, 140.0, None, 110.0]     # 2023: sin el 10-K en la fuente, sin dato


def test_ffo_anual_sin_ajustes_es_sin_dato():
    st = {"net_income": [100.0, 90.0, 80.0, 70.0], "depreciation_amortization": [-50.0] * 4,
          "ordinary_shares": [10.0] * 4, "inc_ends": ["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"]}
    v = archetype_metrics.compute(REIT, st, {}, reit_ffo=rf.no_data("sin clave de Finnhub"))
    assert v["ffo_series"] == [None] * 4
    assert v["ffo_per_share_cagr_3y"] is None and "sin clave de Finnhub" in v["ffo_per_share_cagr_3y_reason"]
