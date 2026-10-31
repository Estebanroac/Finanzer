"""
F10 · margen operativo con una sola verdad, reglas del constructor del TTM de EDGAR (verificación de «Modelo general»,
29-oct: docs/modelo/VERIF_MARGEN_OPERATIVO_2026-10-29.md). El TTM es el ejercicio + el acumulado del año − el acumulado
del año anterior (`sec_edgar.flow_ttm`), y dos de las 28 empresas lo tenían mal:
  1. FIX: su 10-Q del 1T de 2026 etiqueta el trimestre comparativo de 2025 (209 M$) con el periodo del ejercicio
     entero; por ser posterior al 10-K (1.315 M$), ganaba. Un ejercicio (≥ 350 días) nunca sale de un informe
     trimestral; si hay varios, el informe anual manda (VRSN: su ejercicio solo va en el DEF 14A).
  2. IFF: el acumulado del año anterior era el comparativo reexpresado de un 10-Q posterior (+320 M$) con un ejercicio
     sin reexpresar (−382 M$): −291 M$ frente a 754 M$. Cada pieza en la base del ejercicio: el acumulado del año
     anterior es el último presentado no después que el ejercicio (`basis="ejercicio"`).
  3. Perímetro (Plan, 29-oct): por defecto, cada periodo con el filing más reciente que lo presenta (el comparativo
     reexpresado). El TTM tiene que cuadrar con la suma de sus 4 trimestres (± 1 pp de los ingresos); si no, el de la
     base del ejercicio; si ninguno cuadra, el TTM de EDGAR no es homogéneo (HON: perímetros mezclados) y no se usa.
"""
import datetime as dt

import pytest

import sec_edgar as edgar


def D(s):
    return dt.date.fromisoformat(s)


def _f(start, end, val, filed, form="10-Q", accn="a"):
    return {"start": start, "end": end, "val": val, "filed": filed, "form": form, "accn": accn}


def test_a_fiscal_year_only_comes_from_an_annual_report():
    # FIX: el 10-Q de mayo de 2026 trae el comparativo del 1T de 2025 etiquetado como el ejercicio 2025
    fs = [_f("2025-01-01", "2025-12-31", 1315, "2026-02-20", "10-K", "10k"),
          _f("2025-01-01", "2025-12-31", 209, "2026-05-01", "10-Q", "10q-mal"),
          _f("2026-01-01", "2026-06-30", 980, "2026-08-01", "10-Q", "h1-26"),
          _f("2025-01-01", "2025-06-30", 400, "2025-08-01", "10-Q", "h1-25")]
    r = edgar.flow_ttm(fs, D("2026-06-30"), 14)
    assert r["value"] == 1315 + 980 - 400
    assert "10q-mal" not in r["accns"]


def test_a_fiscal_year_repeated_in_a_proxy_statement_still_counts():
    # VRSN («Modelo general», 29-oct): su beneficio anual también va en el DEF 14A (tablas de pay versus performance),
    # posterior al 10-K; un ejercicio solo se descarta si viene de un informe trimestral
    # VRSN: en companyfacts, el NetIncomeLoss anual solo aparece con el DEF 14A
    fs = [_f("2024-01-01", "2024-12-31", 785.7, "2025-04-10", "DEF 14A", "proxy"),
          _f("2025-01-01", "2025-09-30", 619.5, "2025-10-24", "10-Q", "q3-25"),
          _f("2024-01-01", "2024-09-30", 594.2, "2024-10-25", "10-Q", "q3-24")]
    r = edgar.flow_ttm(fs, D("2025-09-30"), 14)
    assert r is not None and r["value"] == pytest.approx(811.0)


def test_the_annual_report_wins_over_other_forms_for_the_same_fiscal_year():
    fs = [_f("2025-01-01", "2025-12-31", 1000, "2026-02-14", "10-K", "10k"),
          _f("2025-01-01", "2025-12-31", 990, "2026-04-10", "DEF 14A", "proxy")]
    r = edgar.flow_ttm(fs, D("2025-12-31"), 14)
    assert r["value"] == 1000 and r["accns"] == ["10k"]


def test_a_fiscal_year_ending_at_the_cut_only_from_an_annual_report():
    fs = [_f("2025-01-01", "2025-12-31", 1315, "2026-02-20", "10-K", "10k"),
          _f("2025-01-01", "2025-12-31", 209, "2026-05-01", "10-Q", "10q-mal")]
    r = edgar.flow_ttm(fs, D("2025-12-31"), 14)
    assert r["value"] == 1315 and r["accns"] == ["10k"]


def test_the_prior_ytd_is_in_the_basis_of_the_fiscal_year():
    # IFF: H1 2025 original −705 (10-Q de 2025), reexpresado +320 en el 10-Q de 2026; el ejercicio del 10-K, sin
    # reexpresar (−382)
    fs = [_f("2025-01-01", "2025-12-31", -382, "2026-02-25", "10-K", "10k"),
          _f("2026-01-01", "2026-06-30", 431, "2026-08-05", "10-Q", "h1-26"),
          _f("2025-01-01", "2025-06-30", -705, "2025-08-05", "10-Q", "h1-25-original"),
          _f("2025-01-01", "2025-06-30", 320, "2026-08-05", "10-Q", "h1-26")]
    r = edgar.flow_ttm(fs, D("2026-06-30"), 14, basis="ejercicio")
    assert r["value"] == -382 + 431 + 705
    assert "h1-25-original" in r["accns"]


def test_a_restated_fiscal_year_takes_the_prior_ytd_filed_up_to_it():
    # si el ejercicio se reexpresó (10-K/A posterior), el acumulado del año anterior es el último no posterior a él
    fs = [_f("2025-01-01", "2025-12-31", -382, "2026-02-25", "10-K", "10k"),
          _f("2025-01-01", "2025-12-31", 600, "2026-09-01", "10-K/A", "10ka"),
          _f("2026-01-01", "2026-06-30", 431, "2026-08-05", "10-Q", "h1-26"),
          _f("2025-01-01", "2025-06-30", -705, "2025-08-05", "10-Q", "h1-25-original"),
          _f("2025-01-01", "2025-06-30", 320, "2026-08-05", "10-Q", "h1-26")]
    r = edgar.flow_ttm(fs, D("2026-06-30"), 14, basis="ejercicio")
    assert r["value"] == 600 + 431 - 320


def test_without_an_earlier_prior_ytd_the_only_one_is_used():
    fs = [_f("2025-01-01", "2025-12-31", 1000, "2026-02-10", "20-F", "fy"),
          _f("2026-01-01", "2026-06-30", 600, "2026-07-28", "6-K", "h1"),
          _f("2025-01-01", "2025-06-30", 450, "2026-07-28", "6-K", "h1")]
    assert edgar.flow_ttm(fs, D("2026-06-30"), 14)["value"] == 1150


# ── 3. Perímetro: el filing más reciente, comprobado con la suma de los trimestres ──

def _q(start, end, val, filed, accn="q"):
    return _f(start, end, val, filed, "10-Q", accn)


IFF = [_f("2025-01-01", "2025-12-31", -382, "2026-02-25", "10-K", "10k"),
       _q("2025-01-01", "2025-03-31", -1000, "2025-05-05"), _q("2025-04-01", "2025-06-30", 295, "2025-08-05"),
       _q("2025-01-01", "2025-06-30", -705, "2025-08-05", "h1-25-original"),
       _q("2025-07-01", "2025-09-30", 200, "2025-11-05"), _q("2025-01-01", "2025-09-30", -505, "2025-11-05"),
       _q("2025-01-01", "2025-03-31", 25, "2026-05-05", "q1-26"), _q("2026-01-01", "2026-03-31", 211, "2026-05-05", "q1-26"),
       _q("2025-04-01", "2025-06-30", 295, "2026-08-05", "h1-26"), _q("2026-04-01", "2026-06-30", 220, "2026-08-05", "h1-26"),
       _q("2025-01-01", "2025-06-30", 320, "2026-08-05", "h1-26"), _q("2026-01-01", "2026-06-30", 431, "2026-08-05", "h1-26")]


def test_the_default_is_the_latest_filing_for_each_period():
    assert edgar.flow_ttm(IFF, D("2026-06-30"), 14)["value"] == -382 + 431 - 320


def test_the_quarters_of_the_ttm_add_up_from_their_latest_filings():
    # 2T-26 220 + 1T-26 211 + 4T-25 (ejercicio − 9 meses: −382 − (−505) = 123) + 3T-25 200
    r = edgar.quarters_ttm(IFF, D("2026-06-30"), 14)
    assert r["value"] == 220 + 211 + 123 + 200


def test_a_ttm_that_does_not_add_up_takes_the_basis_of_the_fiscal_year():
    # IFF: el más reciente (−291) no cuadra con sus trimestres (754); el de la base del ejercicio (754) sí
    r = edgar.checked_flow_ttm(IFF, D("2026-06-30"), 14, scale=10_000)
    assert r["value"] == -382 + 431 + 705 and r["basis"] == "ejercicio"


def test_the_latest_filing_wins_when_it_adds_up():
    fs = [_f("2025-01-01", "2025-12-31", 1000, "2026-02-20", "10-K", "10k"),
          _q("2026-01-01", "2026-06-30", 600, "2026-08-01"), _q("2025-01-01", "2025-06-30", 450, "2025-08-01"),
          _q("2025-01-01", "2025-06-30", 470, "2026-08-01"),
          _q("2026-04-01", "2026-06-30", 300, "2026-08-01"), _q("2026-01-01", "2026-03-31", 300, "2026-05-01"),
          _q("2025-07-01", "2025-09-30", 260, "2025-11-01"), _q("2025-01-01", "2025-09-30", 730, "2025-11-01")]
    r = edgar.checked_flow_ttm(fs, D("2026-06-30"), 14, scale=10_000)
    assert r["value"] == 1000 + 600 - 470 and r["basis"] == "reciente"


def test_a_ttm_that_never_adds_up_is_not_homogeneous():
    # HON (10-Q de octubre de 2026): los 9 meses de 2026 y de 2025 ya sin lo escindido; el ejercicio 2025 y los
    # trimestres de 3 meses de 2026 anteriores, con ello. Ninguna base cuadra con los trimestres: perímetros mezclados
    fs = [_f("2025-01-01", "2025-12-31", 8000, "2026-02-10", "10-K", "10k"),
          _q("2025-01-01", "2025-09-30", 6000, "2025-10-23"), _q("2025-01-01", "2025-09-30", 2500, "2026-10-22"),
          _q("2025-07-01", "2025-09-30", 800, "2026-10-22"),
          _q("2026-01-01", "2026-03-31", 2100, "2026-04-23"), _q("2026-04-01", "2026-06-30", 2200, "2026-07-23"),
          _q("2026-07-01", "2026-09-30", 1000, "2026-10-22"), _q("2026-01-01", "2026-09-30", 3000, "2026-10-22")]
    r = edgar.checked_flow_ttm(fs, D("2026-09-30"), 14, scale=10_000)
    assert r["value"] is None and "no homogéneo" in r["reason"] and r["check"] == "no_homogeneo"
    assert r["candidates"] == {"reciente": 8000 + 3000 - 2500, "ejercicio": 8000 + 3000 - 6000}
    assert r["quarters"] == 1000 + 2200 + 2100 + (8000 - 2500)


def test_without_the_quarters_there_is_nothing_to_check():
    # un 20-F con semestres: sin trimestres que sumar, el más reciente
    fs = [_f("2025-01-01", "2025-12-31", 1000, "2026-02-10", "20-F", "fy"),
          _f("2026-01-01", "2026-06-30", 600, "2026-07-28", "6-K", "h1"),
          _f("2025-01-01", "2025-06-30", 450, "2026-07-28", "6-K", "h1")]
    r = edgar.checked_flow_ttm(fs, D("2026-06-30"), 14, scale=10_000)
    assert r["value"] == 1150 and r["basis"] == "reciente" and r["quarters"] is None
    # Plan, 29-oct: sin 4 trimestres válidos (de 80 a 100 días), la comprobación queda «no disponible» y no tumba el TTM
    assert r["check"] == "no_disponible"


# ── «Modelo general», comprobación de 030b30ad: falsos «no homogéneo» (DLR, LHX) ──

def test_a_quarter_restated_after_the_fiscal_year_does_not_break_the_check():
    # DLR (corte 2026-03-31): el 10-Q de julio de 2026 reexpresa el 2T de 2025 (212 → 1.144 M$); con los trimestres
    # como se presentaron, la suma (730) cuadra con el TTM (729)
    fs = [_f("2025-01-01", "2025-12-31", 658, "2026-02-13", "10-K", "10k"),
          _q("2025-01-01", "2025-03-31", 197, "2025-05-01"), _q("2025-04-01", "2025-06-30", 212, "2025-08-01"),
          _q("2025-04-01", "2025-06-30", 1144, "2026-07-31", "q2-26"), _q("2025-07-01", "2025-09-30", 138, "2025-10-31"),
          _q("2025-01-01", "2025-09-30", 546, "2025-10-31"), _q("2026-01-01", "2026-03-31", 268, "2026-05-01")]
    r = edgar.checked_flow_ttm(fs, D("2026-03-31"), 14, scale=6_340)
    assert r["value"] == 658 + 268 - 197 and r["basis"] == "reciente" and r["check"] == "cuadra"


def test_a_quarter_labelled_with_the_fiscal_year_value_is_derived():
    # LHX: un «trimestre» de 3 meses que acaba al cierre del ejercicio con el valor del ejercicio entero (2.110 M$):
    # error de etiquetado; el 4T es ejercicio − 9 meses (393 M$)
    fs = [_f("2025-01-04", "2026-01-02", 2110, "2026-02-14", "10-K", "10k"),
          _q("2025-10-04", "2026-01-02", 2110, "2026-02-14"),
          _q("2025-01-04", "2025-10-03", 1717, "2025-10-30"), _q("2025-07-05", "2025-10-03", 560, "2025-10-30"),
          _q("2026-01-03", "2026-04-03", 610, "2026-04-30"), _q("2026-04-04", "2026-07-03", 757, "2026-07-30"),
          _q("2026-01-03", "2026-07-03", 1367, "2026-07-30"), _q("2025-01-04", "2025-07-04", 1157, "2025-07-30")]
    r = edgar.quarters_ttm(fs, D("2026-07-03"), 14)
    assert r["value"] == 757 + 610 + (2110 - 1717) + 560
    c = edgar.checked_flow_ttm(fs, D("2026-07-03"), 14, scale=22_932)
    assert c["value"] == 2110 + 1367 - 1157
