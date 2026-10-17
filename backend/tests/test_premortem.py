"""Fase 4 (T3): pre-mortem, "Esta lectura sería errónea si…" (lib/premortem.py). Sin red."""
import premortem as P


def _a(level, **kw):
    a = {"price_attractiveness": {"level": level}, "quality": {"level": "excelente"},
         "classification": {"archetype": "MATURE"}, "key_metrics": {"operating_margin": 0.30}}
    a.update(kw)
    return a


RV = {"main": {"state": "ok", "g10": 0.089, "flow_label": "FCF − SBC",
               "own_growth": {"cagr": 0.01, "years": 10, "label": "sus ingresos por acción"}}}


def test_price_condition_follows_the_level():
    t = P.build(_a("muy exigente", reverse_dcf=RV))["items"][0]["text"]
    assert "al menos un 8.9% anual durante 10 años, como exige el precio" in t and "1.0% anual en 10 años" in t
    t = P.build(_a("razonable", reverse_dcf=RV))["items"][0]["text"]
    assert "menos del 8.9% anual durante 10 años que ya descuenta el precio" in t


def test_margin_above_its_history_and_high_debt():
    hist = {"revenue": {"values": [{"fy_end": f"{2015 + i}-12-31", "value": 100.0} for i in range(10)]},
            "operating_income": {"values": [{"fy_end": f"{2015 + i}-12-31", "value": 20.0} for i in range(10)]}}
    a = _a("razonable", key_metrics={"operating_margin": 0.30, "net_debt_to_ebitda": 4.4})
    items = P.build(a, hist)["items"]
    assert [i["kind"] for i in items] == ["margen", "deuda"]
    assert "mediana de 10 ejercicios (20.0% frente al 30.0% de hoy)" in items[0]["text"]
    assert "4.4 veces el EBITDA" in items[1]["text"]
    # Margen en línea con su historia y deuda baja: nada que decir.
    assert P.build(_a("razonable", key_metrics={"operating_margin": 0.21, "net_debt_to_ebitda": 1.0}), hist) is None


def test_bank_implied_return():
    a = _a("exigente", classification={"archetype": "FINANCIAL"},
           archetype_metrics={"implied": {"metric": "ROTE", "implied": 0.257, "own": 0.20}})
    t = P.build(a)["items"][0]["text"]
    assert t == "la entidad sostuviera un ROTE de al menos el 25.7% que descuenta el precio (obtiene un 20.0%)"


def test_out_of_range_condition_follows_the_level():
    """Revisión de código F4 (hallazgo 3): fuera de rango, el sentido también sigue al nivel de precio."""
    rv = {"main": {"state": "fuera_de_rango", "side": "superior", "flow_label": "FCF − SBC"}}
    assert "como exige el precio" in P.build(_a("muy exigente", reverse_dcf=rv))["items"][0]["text"]
    t = P.build(_a("razonable", reverse_dcf=rv))["items"][0]["text"]
    assert "creciera menos de un 60.0%" in t and "como exige" not in t
