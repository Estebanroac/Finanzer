"""Ramas por arquetipo (etapa 6) sobre los fixtures reales de ambos entornos."""
import pytest

import fixture_backend as fb
from settings import cfg

PRIMARY_FCF_PE = ("P/E", "P/FCF", "Free Cash Flow", "FCF / Net Income", "Cash Flow Operativo", "Piotroski")


def _envs():
    import conftest
    return conftest.ENVS


def _metrics(a, cat):
    return [x["metric"] for x in a["score"]["breakdown"][cat]["adjustments"] if x["metric"] != "No aplica"]


def _alert_reasons(a):
    return [x["reason"] for k in ("red_flags", "warnings", "strengths") for x in a["alerts"][k]]


def _bank_outputs(outputs_by_env):
    out = [(env, outputs_by_env(env)["JPM"][0]) for env in _envs()]
    with fb.replay(fb.fixtures_dir("local")) as store:            # aseguradora (solo local)
        out.append(("local", fb.run_analysis("TRV", store)))
    return out


# ─────────────────────────── criterio de aceptación del cambio 1 ───────────────────────────
def test_bank_never_gets_fcf_or_pe_as_primary_reading(outputs_by_env):
    """Spec cambio 1: un banco nunca recibe lectura de FCF ni P/E como métrica primaria."""
    for env, a in _bank_outputs(outputs_by_env):
        assert a["classification"]["archetype"] == "FINANCIAL", (env, a["symbol"])
        for cat in a["score"]["breakdown"]:
            for m in _metrics(a, cat):
                assert not any(m.startswith(p) for p in PRIMARY_FCF_PE), (env, a["symbol"], cat, m)
        val = a["score_coverage"]["valoracion"]
        assert {"P/E", "P/FCF", "EV/EBITDA", "PEG"} <= set(val["not_applicable"])
        assert any(m.startswith("P/B frente a ROE") for m in _metrics(a, "Valoración")) or \
            "P/B frente a ROE" in val["missing"]
        for r in _alert_reasons(a):
            assert "P/E" not in r and "FCF" not in r and "flujo de caja" not in r.lower(), (env, a["symbol"], r)
        assert a.get("dcf") is None and "dcf" in a["not_applicable"]
        assert a.get("graham_number") is None and "graham" in a["not_applicable"]
        assert a["piotroski_f"]["applicable"] is False and a["altman_z"]["applicable"] is False


def test_bank_quality_uses_what_applies(outputs_by_env):
    for env in _envs():
        cal = outputs_by_env(env)["JPM"][0]["score_coverage"]["calidad"]
        assert cal["components"] == 3 and cal["coverage"] == 1.0
        assert set(cal["not_applicable"]) == {"Piotroski F", "Flujo operativo", "FCF", "FCF / beneficio neto"}


def test_bank_revenue_growth_always_from_statements(outputs_by_env):
    """RECON §7.8: en FINANCIAL el crecimiento sale de los estados, no de Finnhub (prod 3.4% -> 7.3%)."""
    stmt_yoy = 181.85 / 169.44 - 1
    for env in _envs():
        a = outputs_by_env(env)["JPM"][0]
        assert a["key_metrics"]["revenue_growth"] == pytest.approx(stmt_yoy, abs=5e-4), env


# ─────────────────────────── REIT ───────────────────────────
def test_reit_branch(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["O"][0]
        val = a["score_coverage"]["valoracion"]
        assert {"P/E", "P/FCF", "PEG"} <= set(val["not_applicable"])
        assert "P/FFO (REIT)" in _metrics(a, "Valoración")
        assert "Rentabilidad por dividendo (REIT)" in _metrics(a, "Valoración")
        assert "Perfil GARP" not in _metrics(a, "Valoración")
        sol = a["score_coverage"]["solidez"]
        assert "Altman Z" in sol["not_applicable"] and "D/E" not in sol["not_applicable"] \
            and "Cobertura de intereses" not in sol["not_applicable"]
        assert a.get("dcf") is None and "dcf" in a["not_applicable"]
        assert "piotroski" in a["not_applicable"] and "Piotroski F" in a["score_coverage"]["calidad"]["not_applicable"]


def test_reit_current_ratio_not_applicable(outputs_by_env):
    """Etapa 7 (omisión de la 6): el current ratio no aplica a REIT, como en FINANCIAL:
    no puntúa, no cuenta en la cobertura y el PDF lo muestra como "No aplica"."""
    for env in _envs():
        a, pdf = outputs_by_env(env)["O"]
        sol = a["score_coverage"]["solidez"]
        assert "Current ratio" in sol["not_applicable"] and "Current ratio" not in sol.get("missing", [])
        assert "Current Ratio" not in _metrics(a, "Solidez Financiera")
        na = next(x for x in a["score"]["breakdown"]["Solidez Financiera"]["adjustments"] if x["metric"] == "No aplica")
        assert "Current ratio: No aplica a REIT: activos inmobiliarios" in na["reason"]
        text = fb.pdf_text(pdf)
        assert "Current ratio\n—\nNo aplica" in text and "El current ratio de" not in text


# ─────────────────────────── GROWTH_PRE_PROFIT ───────────────────────────
def test_growth_pre_profit_valuation_is_conclusive(outputs_by_env):
    """SNOW: Valoración deja de ser no concluyente por falta de P/E (RECON §7.10)."""
    for env in _envs():
        a = outputs_by_env(env)["SNOW"][0]
        val = a["score_coverage"]["valoracion"]
        assert val["conclusive"] and {"P/E", "PEG"} <= set(val["not_applicable"])
        assert {"EV/Ventas", "Regla de 40"} <= set(_metrics(a, "Valoración"))
        assert a["score"]["excluded_categories"] == [] and a["score"]["partial"] is False
        assert a.get("graham_number") is None and "graham" in a["not_applicable"]
        assert a.get("dcf") is not None          # FCF positivo: el DCF sí aplica
        assert "Crecimiento del BPA" in a["score_coverage"]["crecimiento"]["not_applicable"]


# ─────────────────────────── CYCLICAL ───────────────────────────
def test_cyclical_growth_is_normalized_not_the_single_year(outputs_by_env):
    """FCX: el −24.2% de Finnhub (prod) y el +1.6% local se sustituyen por el promedio
    interanual de los 4 ejercicios, acotado; el resultado ya no depende del entorno."""
    rev = [25.91, 25.45, 22.86, 22.78]
    avg = sum(rev[i] / rev[i + 1] - 1 for i in range(3)) / 3
    lo, hi = cfg("valuation.archetypes.cyclical_growth_bounds")
    for env in _envs():
        a = outputs_by_env(env)["FCX"][0]
        xm = a["archetype_metrics"]
        assert xm["revenue_growth_normalized"] == pytest.approx(min(hi, max(lo, avg)), abs=1e-3)
        assert xm["cycle_years"] == 4 and xm["cycle_incomplete"] is True
        cre = next(x for x in a["score"]["breakdown"]["Crecimiento"]["adjustments"]
                   if x["metric"] == "Crecimiento Ingresos 3Y")
        assert "normalizado de ciclo medio" in cre["reason"] and "ciclo incompleto" in cre["reason"]
        assert "Crecimiento del FCF" in a["score_coverage"]["crecimiento"]["not_applicable"]
        assert a["dcf"]["growth_rate"] == pytest.approx(xm["revenue_growth_normalized"])
        assert a["dcf"]["normalized"]["fcf"] == pytest.approx(xm["fcf_normalized"])
        assert any(m.startswith("EV/EBITDA normalizado") for m in _metrics(a, "Valoración"))


def test_cyclical_negative_fcf_trend_does_not_penalize(outputs_by_env):
    for env in _envs():
        adj = _metrics(outputs_by_env(env)["FCX"][0], "Crecimiento")
        assert "Crecimiento FCF 3Y" not in adj


# ─────────────────────────── MATURE dentro de Financial Services ───────────────────────────
def test_payment_network_is_valued_as_mature(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["V"][0]
        assert a["classification"]["archetype"] == "MATURE"
        assert a["altman_z"]["applicable"] is True and a["dcf"] is not None
        assert a["score"]["breakdown"]["Solidez Financiera"].get("adjustments")[0]["metric"] != "Solidez Bancaria"


# ─────────────────────────── PDF ───────────────────────────
def _pdf_text(pdf):
    return fb.pdf_text(pdf) if isinstance(pdf, bytes) else pdf


def test_pdf_shows_archetype_and_reason(outputs_by_env):
    for env in _envs():
        txt = _pdf_text(outputs_by_env(env)["O"][1])
        assert "REIT  ·  Clasificada como REIT por industria REIT - Retail" in txt


def test_bank_pdf_never_reads_pe_or_fcf_as_primary(outputs_by_env):
    """En el PDF de un banco P/E, P/FCF y FCF yield solo aparecen como "No aplica"."""
    with fb.replay(fb.fixtures_dir("local")) as store:
        trv = fb.run_analysis("TRV", store)
        trv_pdf = fb.build_pdf_bytes(trv, fb.capture_date(store.meta["TRV"]))
    pdfs = [(env, outputs_by_env(env)["JPM"][1]) for env in _envs()] + [("local", trv_pdf)]
    for env, pdf in pdfs:
        lines = _pdf_text(pdf).splitlines()
        for i, ln in enumerate(lines):
            if ln.strip() in ("P/E (TTM)", "Forward P/E", "P/FCF", "FCF Yield", "PEG", "EV/EBITDA"):
                assert any(x.startswith("No aplica a FINANCIAL") for x in lines[i + 1:i + 5]), (env, ln, lines[i:i + 5])
        txt = "\n".join(lines)
        assert "VALORACIÓN\nP/B frente a ROE" in txt, env
        cover = txt.split("===== página 2")[0]
        assert "FCF YIELD" not in cover and "P/E (TTM)" not in cover and "P/B" in cover, env


def test_pdf_roce_rows(outputs_by_env):
    for env in _envs():
        out = outputs_by_env(env)
        assert "ROCE (EBIT / capital empleado)" in _pdf_text(out["NFLX"][1])
        fcx = _pdf_text(out["FCX"][1])
        assert "ROCE promedio (4 ejercicios, ciclo incompleto)" in fcx
        jpm = _pdf_text(out["JPM"][1]).splitlines()
        i = jpm.index("ROCE")
        assert "No aplica a FINANCIAL" in jpm[i + 1:i + 6]


# ─────────────────────────── correcciones de la etapa 6 ───────────────────────────
def test_reit_growth_is_per_share(outputs_by_env):
    """O: FFO agregado +12.2% anual, pero por acción −0.1% (acciones +12.3% anual)."""
    for env in _envs():
        a = outputs_by_env(env)["O"][0]
        xm = a["archetype_metrics"]
        assert xm["ffo_cagr_3y"] == pytest.approx(0.1215, abs=1e-3)
        assert xm["shares_cagr_3y"] == pytest.approx(0.1225, abs=1e-3)
        assert xm["ffo_per_share_cagr_3y"] == pytest.approx(-0.0009, abs=1e-3)
        m = _metrics(a, "Crecimiento")
        assert "Crecimiento FFO por acción 3Y" in m and "Crecimiento Ingresos 3Y" not in m
        assert "Crecimiento FCF por acción 3Y" in m
        assert "Crecimiento del BPA" in a["score_coverage"]["crecimiento"]["not_applicable"]


def test_growth_pre_profit_ev_ebitda_not_applicable_without_ebitda(outputs_by_env):
    """SNOW: EBITDA <= 0 -> EV/EBITDA "no aplica" (no "sin dato"): no reescala Valoración."""
    for env in _envs():
        a = outputs_by_env(env)["SNOW"][0]
        val = a["score_coverage"]["valoracion"]
        assert "EV/EBITDA" in val["not_applicable"] and "EV/EBITDA" not in val["missing"]
        assert val["coverage"] == 1.0
        assert "Cobertura" not in _metrics(a, "Valoración")


# ─────────────────────────── etapa 7: runway y payout REIT ───────────────────────────
def test_runway_states_and_bands():
    from archetype_metrics import runway
    from financial_ratios import score_solidez_financiera
    assert tuple(cfg("thresholds.score.solidez.runway_bounds")) == (3.0, 2.0, 1.0)
    assert runway(1.2e9, 2.3e9)["state"] == "autofinanciada"
    assert runway(0.0, None)["state"] == "autofinanciada"                 # FCF >= 0: autofinanciada
    assert runway(-1e9, 2.5e9)["years"] == pytest.approx(2.5)
    assert runway(-1e9, -5.0)["years"] == 0.0
    assert runway(-1e9, None)["state"] == "sin_dato" and runway(None, 1e9)["state"] == "sin_dato"
    pts = cfg("thresholds.score.solidez.runway_points")

    def adj(rw):
        s = score_solidez_financiera(None, "N/A", None, None, None, archetype="GROWTH_PRE_PROFIT", runway=rw)
        return next((a["adjustment"] for a in s["adjustments"] if a["metric"] == "Runway"), None), s
    assert adj(runway(1e9, 1e9))[0] == pts[0]                              # autofinanciada = mejor tramo
    assert [adj(runway(-1e9, y * 1e9))[0] for y in (3.5, 2.5, 1.5, 0.5)] == list(pts)
    a, s = adj(runway(None, None))
    assert a is None and "Runway" in s["coverage"]["missing"]
    # fuera de GROWTH_PRE_PROFIT no existe el componente
    s = score_solidez_financiera(5.0, "SAFE", 2.0, 0.3, 20.0, archetype="MATURE", runway=runway(-1e9, 1e8))
    assert all(a["metric"] != "Runway" for a in s["adjustments"])


def test_growth_pre_profit_solidez_uses_runway_not_altman(outputs_by_env):
    for env in _envs():
        a, pdf = outputs_by_env(env)["SNOW"]
        assert a["classification"]["archetype"] == "GROWTH_PRE_PROFIT"
        assert a["altman_z"]["applicable"] is False and "Altman Z" in a["score_coverage"]["solidez"]["not_applicable"]
        rw = a["archetype_metrics"]["runway"]
        assert rw["state"] == "autofinanciada" and rw["fcf"] > 0
        row = next(x for x in a["score"]["breakdown"]["Solidez Financiera"]["adjustments"] if x["metric"] == "Runway")
        assert row["value"] == "Autofinanciada" and row["adjustment"] == cfg("thresholds.score.solidez.runway_points")[0]
        assert "Autofinanciada — FCF TTM positivo" in _alert_reasons(a)
        text = fb.pdf_text(pdf)
        assert "Runway\nAutofinanciada\nAutofinanciada" in text and "Altman Z de" not in text


def test_reit_payout_on_ffo(outputs_by_env):
    """Etapa 7 (omisión de la 6): en REIT el payout es dividendos / FFO; la lectura usa sus tramos."""
    for env in _envs():
        a, pdf = outputs_by_env(env)["O"]
        km = a["key_metrics"]
        assert km["payout_basis"] == "ffo" and km["payout_ratio"] == km["ffo_payout"] < 1
        assert km["payout_ratio_net_income"] > 2                            # 236-276% sobre el beneficio neto
        text = fb.pdf_text(pdf)
        assert "Payout sobre FFO\n" in text and "Insostenible" not in text and "supera el beneficio" not in text
    assert outputs_by_env("local")["NFLX"][0]["key_metrics"]["payout_basis"] == "beneficio_neto"
