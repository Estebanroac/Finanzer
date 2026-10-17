"""
Fase 3 (T1b): el cambio de perímetro (2b, T7) solo mira los ejercicios que usa el análisis.

Con la historia larga de EDGAR (companyfacts trae desde 2007), una reexpresión de 2015 (XOM) o de 2017 (KO, JPM) no
cambia el perímetro de la serie que usa el motor (FY0–FY3 de Yahoo). En producción ya pasaba: el companyfacts vivo
trae toda la historia; el juego de la 2b solo guardaba desde 2019.
"""
import perimeter
import sec_edgar as edgar


def _f(start, end, val, filed, accn):
    return {"start": start, "end": end, "val": val, "filed": filed, "form": "10-K", "accn": accn}


def _ed(facts):
    base = {"Assets": {"units": {"USD": [{"end": "2025-12-31", "val": 1, "filed": "2026-02-01", "form": "10-K",
                                          "accn": "k"}]}}}
    return {"status": "ok", "facts": edgar._index_facts({"facts": {"us-gaap": {**base, "Revenues": facts}}})}


def _st(ends, revenue):
    return {"inc_ends": ends, "revenue": revenue}


def test_old_restatement_outside_the_analysis_window_is_ignored():
    rev = {"units": {"USD": [
        _f("2015-01-01", "2015-12-31", 259.0, "2016-02-20", "a15"),
        _f("2015-01-01", "2015-12-31", 239.0, "2018-02-20", "a17"),         # reexpresión de 2015 (-7.6%)
        *[_f(f"{y}-01-01", f"{y}-12-31", 300.0 + y - 2022, f"{y + 1}-02-20", f"a{y}") for y in (2022, 2023, 2024, 2025)],
    ]}}
    info = {"_statements_fy": _st(["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"], [303.0, 302.0, 301.0, 300.0])}
    out = perimeter.detect(info, _ed(rev))
    assert out["restated"] == [] and out["changed"] is False


def test_restatement_inside_the_window_is_still_declared():
    rev = {"units": {"USD": [
        _f("2024-01-01", "2024-12-31", 607.0, "2025-02-20", "b24"),
        _f("2024-01-01", "2024-12-31", 524.0, "2026-02-20", "b25"),          # UL: escisión, 2024 reexpresado
        _f("2025-01-01", "2025-12-31", 520.0, "2026-02-20", "b25"),
    ]}}
    info = {"_statements_fy": _st(["2025-12-31", "2024-12-31"], [520.0, 524.0])}
    out = perimeter.detect(info, _ed(rev))
    assert [r["fy_end"] for r in out["restated"]] == ["2024-12-31"] and out["changed"] is True

