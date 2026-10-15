"""
Fase 1 del plan de fiabilidad: el guardián narrativo (tests/guardian.py) sobre los 30 informes del panel y los 6
del juego local. Un test por (regla, juego, ticker).

PANEL_KNOWN_FAILURES es el inventario de lo que hoy falla, con su causa: entra como xfail ESTRICTO. Cada arreglo de
T3 lo convierte en XPASS, que rompe la suite a propósito: entonces se quita su entrada.
"""
import pytest

import fixture_backend as fb
import guardian as g

CASES = ([("panel", t) for t in fb.PANEL_TICKERS if t != "SPY"] if fb.panel_available() else []) + \
        [("local", t) for t in fb.TICKERS]
RULES = sorted(set(g.PREDICATES) | {"sin_respaldo", "ingles", "codigo_interno", "referencia_mercado", "veredicto",
                                     "base_ttm", "moneda"})

_CYC = "cota del crecimiento de ciclo medio presentada como dato medido (−5% / +10%)"
_BASIS = "'(3 años)' en una cifra de ciclo medio (CYCLICAL)"
_known = {}
for env, t in (("panel", "ASML"), ("panel", "DOW"), ("panel", "FCX"), ("panel", "MU"), ("panel", "XOM"),
               ("local", "FCX")):
    _known[("growth", env, t)] = _CYC
    _known[("basis", env, t)] = _BASIS
_known.update({
    ("referencia_mercado", "panel", "V"): "'múltiplos frente al sector' en la confianza con benchmark de mercado",
    ("referencia_mercado", "local", "V"): "'múltiplos frente al sector' en la confianza con benchmark de mercado",
    ("base_ttm", "panel", "BRK-B"): "'P/E (TTM)' con base anual (faltan trimestres)",
    ("share_dilution_3y", "panel", "AMT"): "atribuye la caída del FFO por acción a la emisión de acciones con las "
                                           "acciones planas en 3 años (+0.05% anual)",
})
PANEL_KNOWN_FAILURES = _known


@pytest.fixture(scope="session")
def guardian_failures():
    out = {}
    for env, t in CASES:
        a, txt, recs = g.run(t, env)
        out[(env, t)] = g.check(a, txt, recs)
    return out


def _params():
    for rule in RULES:
        for env, t in CASES:
            reason = PANEL_KNOWN_FAILURES.get((rule, env, t))
            marks = [pytest.mark.xfail(strict=True, raises=AssertionError, reason=reason)] if reason else []
            yield pytest.param(rule, env, t, marks=marks, id=f"{rule}-{env}-{t}")


@pytest.mark.parametrize("rule,env,sym", list(_params()))
def test_guardian(rule, env, sym, guardian_failures):
    bad = [f for f in guardian_failures[(env, sym)] if f["rule"].split(":")[0] == rule]
    assert not bad, "\n".join(f"{f['rule']}: {f['detail']}" for f in bad[:8])


def test_known_failures_table_is_well_formed():
    for (rule, env, t), reason in PANEL_KNOWN_FAILURES.items():
        assert rule in RULES and (env, t) in CASES and reason, (rule, env, t)


def test_every_failing_rule_is_a_known_rule(guardian_failures):
    """Ningún fallo cae fuera de RULES (si no, no tendría test que lo recoja)."""
    for fails in guardian_failures.values():
        for f in fails:
            assert f["rule"].split(":")[0] in RULES, f
