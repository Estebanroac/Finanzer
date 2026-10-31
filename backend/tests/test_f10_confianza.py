"""
F10 · N6 (revisión externa de NVDA, 28-oct-2026): el resumen de la confianza decía «techo en baja: techo de la
confianza», que no explica nada: la confianza de NVDA sería alta por sus dimensiones, la convergencia media la deja en
media y la dependencia de Ke la baja a baja. Ahora dice qué la limita, en orden y con el nivel de cada paso
(plain_language.confidence_limits).
"""
import glob
import json
import os

import pytest

from plain_language import confidence_limits

HERE = os.path.dirname(__file__)
NVDA = {"level": "baja", "capped_from": "alta",
        "reasons": ["convergencia media: uno lo ve en precio y otro con dirección: no coinciden, sin oponerse",
                    "techo en media: la convergencia es media: alta exige convergencia alta",
                    "veredicto dependiente de Ke: el nivel de precio pasa de «razonable» a «atractivo» con Ke − 1 pp: "
                    "confianza media → baja"],
        "ke_dependent": {"from": "media", "to": "baja",
                         "reason": "veredicto dependiente de Ke: el nivel de precio pasa de «razonable» a «atractivo» "
                                   "con Ke − 1 pp"}}


def test_nvda_says_what_limits_it():
    assert confidence_limits(NVDA) == (
        "por sus dimensiones sería alta; la limitan: la convergencia es media —alta exige convergencia alta—, hasta "
        "media; el veredicto depende de Ke —el nivel de precio pasa de «razonable» a «atractivo» con Ke − 1 pp—")


def test_only_ke_or_nothing():
    only_ke = {**NVDA, "capped_from": None, "reasons": NVDA["reasons"][-1:]}
    assert confidence_limits(only_ke).startswith("por sus dimensiones sería media; la limita: el veredicto depende")
    assert confidence_limits({"level": "alta", "reasons": []}) is None
    already_low = {"level": "baja", "reasons": [], "ke_dependent": {"from": "baja", "to": "baja", "reason": "x: y"}}
    assert confidence_limits(already_low) is None


def test_base_rate_step_goes_between_ceilings_and_ke():
    """Fusión de N4 (f10-motor) con N6: el escalón de las tasas base es un límite más, en el orden en que se aplica."""
    c = {**NVDA, "capped_from": "alta", "base_rate_step": {"share": 0.004, "from": "media", "to": "baja"},
         "ke_dependent": {"from": "baja", "to": "baja", "reason": "x: y"}}
    assert confidence_limits(c) == (
        "por sus dimensiones sería alta; la limitan: la convergencia es media —alta exige convergencia alta—, hasta "
        "media; las tasas base —solo el 0.40% de las comparables sostuvo el crecimiento que exige el precio; no "
        "contrae el precio—")
    only = {"level": "baja", "reasons": [], "base_rate_step": {"share": 0.004, "from": "media", "to": "baja"}}
    assert confidence_limits(only).startswith("por sus dimensiones sería media; la limita: las tasas base")


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(HERE, "golden", "*", "*.json"))),
                         ids=lambda p: f"{os.path.basename(os.path.dirname(p))}-{os.path.basename(p)[:-5]}")
def test_no_summary_hides_its_limit(path):
    d = json.load(open(path, encoding="utf-8")).get("display") or {}
    s = (d.get("confidence") or {}).get("summary")
    if not s:
        pytest.skip("sin confianza")
    assert "techo de la confianza" not in s and "techo en" not in s


def test_base_rate_step_already_low_is_not_a_limit():
    """F10 · N4 (E2a): si la confianza ya estaba en baja, el escalón de las tasas base no la baja y no es un límite."""
    already = {"level": "baja", "reasons": ["un escalón menos por las tasas base: x (< 5%); ya estaba en baja"],
               "base_rate_step": {"share": 0.01, "from": "baja", "to": "baja"}}
    assert confidence_limits(already) is None
