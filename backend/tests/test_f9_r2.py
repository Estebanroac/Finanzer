"""
F9 · R2 (revisión externa de NU; decisión del PM del 27-oct, opción a):

- La fortaleza «Sensibilidad baja al mercado» y la lectura «Defensiva» solo con la beta propia que pasa los filtros de
  E1 y por debajo de beta_low. El texto dice lo que mide la beta («sus movimientos dependen poco del mercado»), nunca
  «se mueve menos» ni nada de volatilidad.
- Una sola beta en todas las capas: la del Ke. NU decía «Perfil defensivo — Beta 0.40» porque las alertas leían la
  beta de Yahoo de `ratios` (anterior a la tabla regional), con un Ke de β 0,60.
"""
import re

import pytest

import alert_interpretations as ai
import display as dp


def _beta_signal(source, r2, beta=0.40):
    ctx = ai.Ctx({}, {"beta": beta, "beta_source": source, "beta_r2": r2}, sector="default",
                 real_sector="Financial Services")
    return ai._beta(ctx)


def test_own_beta_is_low_market_sensitivity():
    s = _beta_signal("propia", 0.34, beta=0.55)
    assert s["reason"] == "Sensibilidad baja al mercado — β propia 0.55"
    assert s["detail"] == "β propia 0.55 (R² 0.34): sus movimientos dependen poco del mercado."


def test_industry_beta_never_gives_the_strength():
    assert _beta_signal("sector", None) is None          # NU: la propia (R² 0.17) no pasa E1
    assert _beta_signal("fuente", None) is None


def test_report_reading_follows_the_same_rule():
    assert dp.read_beta(0.55, None, "propia", 0.34) == ("Defensiva", "pos", "β propia 0.55 (R² 0.34): sus movimientos "
                                                                           "dependen poco del mercado")
    lab, tone, txt = dp.read_beta(0.60, None, "sector")
    assert (lab, tone) == ("Beta baja", "neu") and "de su industria" in txt and "no pasa los filtros" in txt
    for t in (txt, dp.read_beta(0.40)[2]):
        assert "amortigua" not in t and "se mueve menos" not in t
    assert dp.read_beta(1.5, None, "sector")[0] != "Beta baja"           # solo toca la banda baja


_BETA_TXT = re.compile(r"(?:\bbeta|\bBeta|β propia|β de la industria|β ajustada|β media de la industria) (\d+\.\d\d)\b")


def test_one_beta_in_every_layer(outputs_by_env):
    """Las alertas, las lecturas (las mismas que pinta el PDF), la serie del gráfico y los ratios muestran la beta del Ke
    (`wacc.beta`). La bruta solo sale rotulada como «bruta» en el detalle del WACC."""
    for env in ("panel", "local"):
        for sym, (a, pdf) in outputs_by_env(env).items():
            ke = (a.get("wacc") or {}).get("beta")
            if ke is None:
                continue
            km = a["key_metrics"]
            for name, v in (("key_metrics.beta_ke", km.get("beta_ke")), ("ratios.beta", (a.get("ratios") or {}).get("beta")),
                            ("price_history.beta", (a.get("price_history") or {}).get("beta"))):
                assert v == pytest.approx(ke, abs=5e-4), (sym, name, v, ke)
            d = a.get("display") or {}
            texts = [x["reason"] + " " + x["detail"] for k in ("red_flags", "warnings", "strengths")
                     for x in (a.get("alerts") or {}).get(k, [])]
            texts.append(((d.get("readings") or {}).get("beta") or {}).get("text") or "")
            for t in texts:
                for m in _BETA_TXT.findall(t):
                    assert float(m) == pytest.approx(ke, abs=0.006), (sym, t)
