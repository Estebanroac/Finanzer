"""Rediseño E2a (T1): textos del motor corregidos en origen — el spread ROIC − WACC es una diferencia de porcentajes
(«pp») y la frase de frontera de nivel empieza con mayúscula cuando va sola."""
import numfmt
from alert_interpretations import Ctx, _spread
from display import read_spread
from verdict import border


def test_pp_formatea_diferencias_de_porcentajes():
    assert numfmt.pp(0.884) == "+88.4 pp"
    assert numfmt.pp(-0.02) == "−2.0 pp"
    assert numfmt.pp(0.0) == "0.0 pp"
    assert numfmt.pp(None) == "—"


def test_spread_en_puntos_porcentuales():
    label, tone, text = read_spread(0.884, 0.98, 0.096)
    assert "+88.4 pp" in text and "%:" not in text
    _, _, text2 = read_spread(0.03, 0.12, 0.09)
    assert "en +3.0 pp" in text2


def test_alerta_de_spread_en_puntos_porcentuales():
    fuerte = _spread(Ctx({"roic": 0.98, "wacc": 0.096}, {}, sector="default", real_sector="", roic_wacc_spread=0.884))
    assert fuerte["reason"] == "Crea mucho valor — spread +88.4 pp"
    neg = _spread(Ctx({"roic": 0.05, "wacc": 0.09}, {}, sector="default", real_sector="", roic_wacc_spread=-0.04))
    assert neg["reason"].endswith("spread −4.0 pp")


def test_frontera_empieza_con_mayuscula():
    b = border(46, [65, 45, 30], ["atractivo", "razonable", "exigente", "muy exigente"])
    assert b is not None and b["text"].startswith("En la frontera con «exigente»")
