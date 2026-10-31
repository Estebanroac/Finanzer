"""
F9 · R4 (revisión externa de NU, 27-oct): en un banco, el margen neto sobre «ingresos» no puntúa, no genera alerta y
no se compara con su industria. Los ingresos de un banco no tienen una definición común: NU calcula 27,4 % sobre
ingresos brutos (con los intereses cobrados) y se comparaba con el 41 % de bancos que reportan netos, −2 puntos sin
fundamento. Solo el subtipo «banco» (sectors.archetypes.not_applicable_subtype); aseguradoras y conglomerados lo
conservan.
"""
import alert_interpretations as ai
from classify import FINANCIAL, not_applicable
from financial_ratios import score_rentabilidad
from settings import cfg


def test_config_only_banks():
    assert {k: list(v) for k, v in cfg("sectors.archetypes.not_applicable_subtype").items()} == {"banco": ["net_margin"]}
    assert not_applicable(FINANCIAL, "net_margin", "banco").startswith("No aplica a bancos: sus ingresos no tienen")
    assert not_applicable(FINANCIAL, "net_margin", "aseguradora") is None
    assert not_applicable(FINANCIAL, "net_margin") is None


def _rent(subtype):
    """NU (vivo, 27-oct): ROE 27,2 %, ROA 4,4 %, margen neto 27,4 % frente al 41 % de su industria."""
    return score_rentabilidad(0.272, 0.044, None, 0.274, sector_roe_threshold=0.06, sector_roa_threshold=0.005,
                              sector_roe_high=0.12, sector_roa_high=0.015, archetype=FINANCIAL,
                              industry_net_margin=0.41, subtype=subtype)


def test_bank_net_margin_does_not_score():
    bank, ins = _rent("banco"), _rent("aseguradora")
    assert not [x for x in bank["adjustments"] if x["metric"] == "Margen neto"]
    assert "Margen neto" in bank["coverage"]["not_applicable"]
    assert [x["adjustment"] for x in ins["adjustments"] if x["metric"] == "Margen neto"] == [-2]
    assert bank["score"] == ins["score"] + 2


def test_bank_net_margin_raises_no_alert():
    for sub, n in (("banco", 0), ("aseguradora", 1)):
        # F10 · B3: la alerta del margen lee la referencia de su fila (la industria), no la tabla del sector
        ctx = ai.Ctx({"net_margin": 0.317}, {"subtype": sub, "industry_net_margin": 0.15}, sector="financials",
                     real_sector="Financial Services", archetype=FINANCIAL)
        sig = ai._margins(ctx)
        assert (sig is not None and "Margen neto" in sig["reason"]) == bool(n), sub
