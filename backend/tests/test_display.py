"""Etapa 9b: capa de presentación compartida (lib/display.py) y motivos en lenguaje llano.

El PDF y la web leen el mismo bloque `display`; estos tests fijan su contrato:
estados y tonos válidos, serializable a JSON, motivos traducidos, y que las bandas
de los tooltips (decisión C) son exactamente las de los lectores.
"""
import json
import re

import pytest

import display as dp
import plain_language as pl
import invariants as inv
from conftest import ENV_TICKERS, env_id
from settings import cfg


@pytest.mark.parametrize("env_sym", ENV_TICKERS, ids=env_id)
def test_display_contract(env_sym, outputs_by_env):
    env, sym = env_sym
    inv.display_contract(outputs_by_env(env)[sym][0], None)


@pytest.mark.parametrize("env_sym", ENV_TICKERS, ids=env_id)
def test_institutional_not_applicable_never_zero(env_sym, outputs_by_env):
    """Altman / Piotroski "no aplica": tarjeta "No aplica" y z_score/score null, nunca 0."""
    env, sym = env_sym
    inv.institutional_not_applicable_never_zero(outputs_by_env(env)[sym][0], None)


@pytest.mark.parametrize("env_sym", ENV_TICKERS, ids=env_id)
def test_every_confidence_reason_has_plain_translation(env_sym, outputs_by_env):
    env, sym = env_sym
    inv.confidence_reasons_translated(outputs_by_env(env)[sym][0], None)


def test_plain_language_examples():
    t = pl.translate
    assert t("sin TTM: estados anuales (hasta 12 meses de retraso)") == (
        "Se usan los estados del último ejercicio anual (pueden tener hasta 12 meses de antigüedad).")
    assert t("12 campos de Finnhub en lugar de los estados") == "Parte de los datos proviene de una fuente secundaria."
    assert t("^TNX no disponible: valor de config") is None
    assert t("validación: revenueGrowth (crecimiento_artefacto)").startswith(
        "El crecimiento reportado por la fuente era incoherente y se recalculó con los estados")
    assert t("12 de 20 componentes del score con dato (60%)") == (
        "Faltan datos en parte del análisis (12 de 20 indicadores con dato).")


def test_plain_reasons_cover_every_dimension_first():
    conf = {"level": "baja", "reasons": [], "dimensions": {
        "convergence": {"level": "no_evaluable", "reasons": [
            "un solo método evaluable (múltiplos frente al sector): no hay contraste",
            "no evaluable: DCF (fiabilidad baja)"]},
        "source": {"level": "baja", "reasons": ["sin TTM: estados anuales (hasta 12 meses de retraso)",
                                                 "17 campos de Finnhub en lugar de los estados"]},
        "stability": {"level": "baja", "reasons": ["arquetipo CYCLICAL: resultados ligados a la fase del ciclo"]}}}
    top3 = pl.plain_reasons(conf)[:3]
    assert top3[2].startswith("Empresa cíclica")
    assert len(pl.plain_reasons(conf)) == 5


# ── decisión C: bandas del tooltip == bandas del lector ──
def _samples_desc(bounds, eps):
    """Un valor dentro de cada tramo de una escala descendente (≥ b0, b1–b0, …, < b_last)."""
    b = list(bounds)
    return [b[0] + eps] + [(b[i] + b[i - 1]) / 2 for i in range(1, len(b))] + [b[-1] - eps]


def _samples_asc(bounds, eps):
    b = list(bounds)
    return [b[0] - eps] + [(b[i] + b[i - 1]) / 2 for i in range(1, len(b))] + [b[-1] + eps]


def _labels(bands):
    return [x["label"] for x in bands]


def test_bands_match_readers():
    th = dp.ThresholdConfig()
    T = cfg("thresholds.score")
    P = cfg("thresholds.pdf")
    # ROE
    roe_b = [th.roe_high * T["rentabilidad"]["roe_high_mult"], th.roe_high, th.roe_low,
             T["rentabilidad"]["roe_floor"], 0]
    got = [dp.read_roe(v, None, th)[0] for v in _samples_desc(roe_b, 0.01)]
    assert got == _labels(dp.score_bands("roe", th=th))
    # spread, current, coverage
    for key, reader, bounds, eps in (
            ("roic_wacc_spread", lambda v: dp.read_spread(v, 0.1, 0.08), T["rentabilidad"]["spread_bounds"], 0.01),
            ("current_ratio", dp.read_current, T["solidez"]["current_bounds"], 0.1),
            ("interest_coverage", dp.read_coverage, T["solidez"]["coverage_bounds"], 0.5)):
        assert [reader(v)[0] for v in _samples_desc(bounds, eps)] == _labels(dp.score_bands(key)), key
    # D/E (con cobertura baja: sin mitigación)
    t = th.debt_equity_high
    m = T["solidez"]["de_mults"]
    de_b = [t * m[0], t, t * m[1], t * m[2]]
    got = ["Equity negativo"] + [dp.read_de(v, t, 1.0)[0] for v in _samples_asc(de_b, 0.05)]
    assert [x.split(" (")[0] for x in _labels(dp.score_bands("de", de_threshold=t))] == got
    # deuda neta/EBITDA (REIT y general)
    got = ["Caja neta"] + [dp.read_nde(v, reit=True)[0] for v in _samples_asc(T["solidez"]["reit_nde_bounds"], 0.1)]
    assert got == _labels(dp.score_bands("net_debt_to_ebitda", reit=True))
    got = ["Caja neta"] + [dp.read_nde(v)[0] for v in _samples_asc(P["nde_bounds"], 0.1)]
    assert got == _labels(dp.score_bands("net_debt_to_ebitda"))
    # runway
    got = ["Autofinanciada"] + [dp.read_runway({"state": "runway", "years": v})[0]
                                for v in _samples_desc(T["solidez"]["runway_bounds"], 0.2)]
    assert got == _labels(dp.score_bands("runway"))
    # payout (FFO y beneficio)
    got = ["FFO negativo"] + [dp.read_payout(v, "ffo")[0]
                              for v in _samples_asc(T["calidad"]["reit_ffo_payout_bounds"], 0.02)]
    assert got == _labels(dp.score_bands("payout_ratio", ffo=True))
    got = ["Con pérdidas"] + [dp.read_payout(v)[0] for v in _samples_asc(P["payout_bounds"], 0.05)]
    assert got == _labels(dp.score_bands("payout_ratio"))
    # crecimiento (interanual y ciclo medio), con la tolerancia de estancamiento
    tol = T["crecimiento"]["flat_tolerance"]
    for kind, what in (("revenue", "los ingresos"), ("eps", "el BPA")):
        b = T["crecimiento"][f"{kind}_bounds"]
        vals = _samples_desc(b, 0.01)[:-1] + [-tol / 2, -tol - 0.01]
        assert [dp.read_growth(v, what, kind)[0] for v in vals] == _labels(dp.score_bands(
            "revenue_growth", kind=kind))
        vals = _samples_desc(b[1:], 0.01)[:-1] + [-tol / 2, -tol - 0.01]
        assert [dp.read_growth(v, what, kind, cycle=True)[0] for v in vals] == _labels(dp.score_bands(
            "revenue_growth", kind=kind, cycle=True))
    # DCF, Graham, beta, 52 semanas, recompras, FCF yield
    up = [x * 100 for x in T["valoracion"]["dcf_upside_bounds"]]
    assert [dp.read_upside(v)[0] for v in _samples_desc(up, 1)] == _labels(dp.score_bands("dcf_upside"))
    assert [dp.read_graham(v)[0] for v in _samples_desc([P["graham_discount"], 0], 0.05)] == _labels(
        dp.score_bands("graham"))
    assert [dp.read_beta(v)[0] for v in _samples_asc(P["beta_bounds"], 0.1)] == _labels(dp.score_bands("beta"))
    e = [0, *P["pos52_bounds"], 100]
    assert [dp.read_pos52((lo + hi) / 2)[0] for lo, hi in zip(e, e[1:])] == _labels(dp.score_bands("pos52"))
    b = P["buyback_bounds"]
    assert [dp.read_buyback(v)[0] for v in (b[0] + 0.01, (b[0] + b[1]) / 2, 0, -b[1] - 0.01)] == _labels(
        dp.score_bands("buyback_yield"))
    b = P["fcf_yield_bounds"]
    assert [dp.read_fcf_yield(v)[0] for v in (-0.01, b[0] / 2, *[(b[i] + b[i - 1]) / 2 for i in (1, 2)],
                                              b[2] + 0.01)] == _labels(dp.score_bands("fcf_yield"))


@pytest.mark.parametrize("higher,fmt", [(True, "pct"), (False, "mult")])
def test_vs_bench_bands_match_reader(higher, fmt):
    bench = 0.2 if fmt == "pct" else 20.0
    b0, b1 = cfg("thresholds.pdf.vs_sector_bounds")
    diffs = ([b0 + 5, (b0 + b1) / 2, 0, -(b0 + b1) / 2, -b0 - 5] if higher
             else [-b0 - 5, -(b0 + b1) / 2, 0, (b0 + b1) / 2, b0 + 5])
    got = [dp.read_vs_sector("x", bench * (1 + d / 100), bench, higher, fmt)[0] for d in diffs]
    assert got == _labels(dp.vs_bench_bands(bench, higher, fmt))


@pytest.mark.parametrize("env_sym", ENV_TICKERS, ids=env_id)
def test_tooltips_only_applied_bands(env_sym, outputs_by_env):
    """El tooltip no ofrece bandas de lo que no aplica al arquetipo."""
    env, sym = env_sym
    inv.tooltips_only_applied_bands(outputs_by_env(env)[sym][0], None)


# ── Revisión de capturas (etapa 9b) ──


@pytest.mark.parametrize("env_sym", ENV_TICKERS, ids=env_id)
def test_visible_texts_without_jargon_or_bad_formats(env_sym, outputs_by_env):
    """Sin código de arquetipo fuera del detalle técnico, sin "<=" en la clasificación, signo
    antes del símbolo ($) y sin doble guion ("— -33%")."""
    import fixture_backend as fb
    env, sym = env_sym
    a, pdf = outputs_by_env(env)[sym]
    inv.visible_texts_without_jargon_or_bad_formats(a, fb.pdf_text(pdf))


@pytest.mark.parametrize("env_sym", ENV_TICKERS, ids=env_id)
def test_growth_texts_cite_the_scored_figure(env_sym, outputs_by_env):
    """Resumen e intro de Crecimiento citan la cifra que puntúa (CAGR 3 años, ciclo medio o
    retorno total REIT), no el interanual; el interanual queda en la tabla rotulado."""
    env, sym = env_sym
    inv.growth_texts_cite_the_scored_figure(outputs_by_env(env)[sym][0], None)


def test_financial_not_applicable_figures(outputs_by_env):
    for env in [e for e in ("local", "prod") if e in __import__("conftest").ENVS]:
        d = outputs_by_env(env)["JPM"][0]["display"]
        fig = {r[0]: r[1] for r in d["sections"]["profitability"]["figures"]}
        fig.update({r[2]: r[3] for r in d["sections"]["profitability"]["figures"]})
        assert fig["Flujo de caja operativo"] == fig["Flujo de caja libre"] == "No aplica a bancos y aseguradoras"
        gm = next(r for r in d["sections"]["profitability"]["rows"] if r["key"] == "gross_margin")
        assert gm["state"] == "no_aplica" and gm["bench"] == "—"
        assert d["sections"]["historical"]["not_applicable"]["free_cash_flow"] == "No aplica a bancos y aseguradoras"


def test_piotroski_criteria_in_spanish(outputs_by_env):
    for env in [e for e in ("local", "prod") if e in __import__("conftest").ENVS]:
        for sym, (a, _) in outputs_by_env(env).items():
            inv.piotroski_criteria_in_spanish(a, None)


def test_money_format_sign_before_symbol():
    import numfmt
    assert dp.fv(-147.78e9, "money") == "−$147.78B"
    assert numfmt.amount(-1.0987) == "−$1.10 por acción"
    assert numfmt.amount(-365_734_000) == "−$365.73M"
    assert numfmt.signed_pct(-33.2) == "−33%"


def test_price_wording_without_jargon(outputs_by_env):
    for env in [e for e in ("local", "prod") if e in __import__("conftest").ENVS]:
        for sym, (a, _) in outputs_by_env(env).items():
            inv.price_wording_without_jargon(a, None)