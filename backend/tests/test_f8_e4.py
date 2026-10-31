"""
F8 · E4 y E5 (auditoría externa del 26-oct-2026, §3 E4 y E5): etiquetas e incoherencias de VZ y anclaje en el P/E que
el motor descarta.

- el titular de crecimiento cita el de los ingresos (el del DCF), no el retorno total; este, en su fila;
- PEG n.s. si el crecimiento del BPA del informe es ≤ 0 o si, con él, la lectura del PEG de la fuente cambia de tramo;
- convergencia «alta» solo si ningún múltiplo individual contradice la dirección común con lectura extrema (±1);
- telecom: FCF − media de 10 años de las compras de espectro (EDGAR; mínimo 5), o sin dato declarado;
- E5: con el P/E reportado no fiable, la lectura de la portada y el resumen es la del normalizado.
Las afirmaciones sobre el replay de las 25 empresas: tests/test_f8_referencia.py.
"""
import pytest

import financial_ratios as fr
import telecom_spectrum
import valuation_confidence as vc
from display import read_pe
from settings import cfg


# ── PEG ──

@pytest.mark.parametrize("pe,peg,eps,src,ns", [
    (11.2, 0.80, -0.071, True, "≤ 0"),          # VZ: PEG de la fuente con el BPA en −7,1 %
    (13.2, 2.74, -0.017, True, "≤ 0"),          # UL
    (27.6, 3.22, 0.116, True, "lectura cambia"),     # KO: 2,38 con el crecimiento del informe (otro tramo)
    (39.3, 2.55, 0.069, True, None),                 # AAPL: 5,7 con el del informe, el mismo tramo (muy caro)
    (29.7, 1.30, 0.229, False, None),                # MSFT: PEG propio a 3 años
    (20.0, 1.44, None, True, None),                  # AMZN: sin crecimiento del informe, sin contraste
])
def test_peg_not_significant(pe, peg, eps, src, ns):
    got = fr.peg_not_significant(pe, peg, eps, from_source=src)
    assert (got is None) if ns is None else (ns in got)


def test_peg_bands_are_the_score_ones():
    b = cfg("thresholds.score.valoracion.peg_bounds")
    assert [fr.peg_band(x) for x in (b[0], b[0] + 1e-9, b[-1] + 1e-9)] == [0, 1, len(b)]


def test_not_significant_peg_leaves_the_block_without_counting_as_missing():
    v = fr.score_valoracion(pe=11.2, p_fcf=8.9, ev_ebitda=7.2, peg=None, sector_pe=8.0, sector_ev_ebitda=7.2,
                            archetype="MATURE", peg_not_significant="el crecimiento del BPA del informe es ≤ 0")
    cov = v["coverage"]
    assert cov["not_significant"] == {"PEG": "el crecimiento del BPA del informe es ≤ 0"} and "PEG" not in cov["missing"]
    block = next(x for x in v["adjustments"] if x["metric"] == "Bloque de múltiplos")
    assert "PEG" not in block["reason"]


# ── convergencia ──

def _methods(readings, dcf=0.6, mult=0.4):
    return [{"method": "DCF", "kind": "intrínseco", "signal": dcf, "reliability": "alta"},
            {"method": "múltiplos frente al sector", "kind": "relativo", "signal": mult, "readings": readings}]


def test_convergence_extreme_contrary_multiple_blocks_alta():
    """VZ (26-oct): DCF barata y múltiplos +0,40 (barata), pero el P/E en −1,00 («muy caro»)."""
    c = vc.convergence(_methods({"P/E": -1.0, "Forward P/E": 1.0, "P/FCF": 1.0, "EV/EBITDA": 0.0, "PEG": 1.0}))
    assert c["level"] == "media" and c["contrary_extremes"] == {"P/E": -1.0} and "lectura extrema" in c["reasons"][0]


def test_convergence_without_extreme_contrary_stays_alta():
    c = vc.convergence(_methods({"P/E": -0.5, "Forward P/E": 1.0, "P/FCF": 1.0}))
    assert c["level"] == "alta"


def test_multiples_signal_keeps_each_reading():
    s = vc.multiples_signal([("Bloque de múltiplos", 6, -6, 2.4), ("P/FFO", 4, -4, -2)],
                            members={"P/E": -1.0, "P/FCF": 1.0})
    assert s["readings"] == {"P/E": -1.0, "P/FCF": 1.0, "P/FFO": -0.5} and s["components"] == 2


# ── espectro ──

def _hist(years, spectrum):
    return {"revenue": {"values": [{"fy_end": f"{y}-12-31", "value": 1.0} for y in years]},
            "spectrum_purchases": {"values": [{"fy_end": f"{y}-12-31", "value": v,
                                               "concept": "us-gaap:PaymentsToAcquireIntangibleAssets"}
                                              for y, v in spectrum.items()]}}


VZ = {2025: 0.45e9, 2024: 0.9e9, 2023: 5.8e9, 2022: 3.65e9, 2021: 47.6e9, 2020: 3.9e9, 2019: 0.9e9, 2018: 1.43e9,
      2017: 0.58e9, 2016: 0.53e9}


def test_spectrum_ten_year_average_from_edgar():
    """PM, 27-oct: 10 años, el ciclo completo de subastas (con 5, la banda C de 2021 dominaba: 11,68 frente a 6,57)."""
    h = _hist(range(2025, 2013, -1), VZ)
    r = telecom_spectrum.adjustment(h, "Telecom Services")
    assert r["status"] == "ok" and r["years"] == [str(y) for y in range(2025, 2015, -1)] and r["window"] == 10
    assert r["average"] == pytest.approx(sum(VZ.values()) / 10) and r["average"] == pytest.approx(6.574e9, rel=1e-3)


def test_spectrum_with_fewer_years_uses_those_available_down_to_five():
    """Menos de 10 ejercicios con el dato: los que haya, con un mínimo de 5; no se suponen ceros."""
    h = _hist(range(2025, 2013, -1), {y: VZ[y] for y in range(2025, 2019, -1) if y != 2023})   # 5 de 10
    r = telecom_spectrum.adjustment(h, "Telecom Services")
    assert r["status"] == "ok" and len(r["years"]) == 5 and "2023" not in r["years"]
    assert r["average"] == pytest.approx(sum(VZ[y] for y in (2025, 2024, 2022, 2021, 2020)) / 5)
    h = _hist(range(2025, 2013, -1), {y: VZ[y] for y in range(2025, 2021, -1)})                 # 4 de 10
    r = telecom_spectrum.adjustment(h, "Telecom Services")
    assert r["status"] == "sin_dato" and "4 de los 10" in r["reason"] and "al menos 5" in r["reason"]
    assert telecom_spectrum.adjustment({}, "Telecom Services")["status"] == "sin_dato"


def test_spectrum_only_for_telecom():
    assert telecom_spectrum.adjustment(_hist(range(2025, 2017, -1), {}), "Software—Infrastructure") is None


# ── E5 ──

def test_normalized_pe_reading_says_so():
    """GOOGL (26-oct): P/E reportado 15,9x (no fiable, 49 % no recurrente) y normalizado 31,4x frente a 29,6x."""
    r = read_pe(31.4, 29.6, None, ref="de su industria", normalized=True)
    assert "31.4x el beneficio normalizado" in r[2] and "+6%" in r[2] and "descuento" not in r[2]
