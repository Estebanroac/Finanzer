"""
Fase 2a (T3): piezas de la verificación frente a EDGAR (tests/edgar_verify.py) con hechos sintéticos, sin red.
"""
import edgar_verify as V


def _f(val, end, start=None, form="10-Q", filed="2026-08-01"):
    d = {"val": val, "end": end, "form": form, "filed": filed, "accn": f"{form}-{end}"}
    if start:
        d["start"] = start
    return d


def _ed(facts):
    return V.Edgar({"taxonomy": "us-gaap", "facts": {"us-gaap": {
        "Assets": {"units": {"USD": [_f(100, "2025-12-31", form="10-K")]}}, **facts}}})


def test_ttm_is_fy_plus_ytd_minus_prior_ytd():
    rev = [_f(400, "2025-12-31", "2025-01-01", form="10-K"),
           _f(210, "2026-06-30", "2026-01-01"), _f(190, "2025-06-30", "2025-01-01")]
    ed = _ed({"Revenues": {"units": {"USD": rev}}})
    v, det, _ = ed.ttm(rev, "2026-06-30")
    assert v == 420 and "FY 2025-12-31" in det


def test_ttm_tolerates_yahoo_month_end_dates():
    """Yahoo etiqueta el trimestre a fin de mes (JNJ 2026-06-30) y EDGAR a su fecha real (2026-06-28)."""
    rev = [_f(400, "2025-12-28", "2024-12-30", form="10-K"),
           _f(210, "2026-06-28", "2025-12-29"), _f(190, "2025-06-29", "2024-12-30")]
    ed = _ed({"Revenues": {"units": {"USD": rev}}})
    assert ed.ttm(rev, "2026-06-30")[0] == 420


def test_ttm_without_cumulative_period_is_missing():
    rev = [_f(400, "2025-12-31", "2025-01-01", form="10-K"), _f(110, "2026-06-30", "2026-04-01")]
    ed = _ed({"Revenues": {"units": {"USD": rev}}})
    assert ed.ttm(rev, "2026-06-30")[0] is None


def test_total_debt_needs_its_long_term_piece():
    """Sin la deuda a largo plazo en esa fecha no se da por total el papel comercial suelto (caso O)."""
    ed = _ed({"CommercialPaper": {"units": {"USD": [_f(14, "2026-06-30")]}},
              "LongTermDebt": {"units": {"USD": [_f(300, "2025-12-31", form="10-K")]}}})
    assert V.debt_total(ed, ("instant", "2026-06-30"))[0] is None
    ed = _ed({"CommercialPaper": {"units": {"USD": [_f(14, "2026-06-30")]}},
              "LongTermDebt": {"units": {"USD": [_f(300, "2026-06-30")]}}})
    assert V.debt_total(ed, ("instant", "2026-06-30"))[0] == 314


def test_classify_returns_the_first_matching_explanation():
    cands = [("periodo", "otro trimestre", 120.0), ("unidad", "×100", 10000.0)]
    assert V.classify(10010.0, cands, 0.01) == ("unidad", "×100")
    assert V.classify(500.0, cands, 0.01) is None


def test_signs_are_kept_except_for_payments():
    """Una pérdida es negativa en las dos fuentes; el capex y los dividendos se comparan en valor absoluto."""
    assert "capex" in V.ABS_FIELDS and "dividends_paid" in V.ABS_FIELDS
    assert "net_income" not in V.ABS_FIELDS and "operating_income" not in V.ABS_FIELDS
    assert V.rel(-1.8, -1.83) is not None and abs(V.rel(-1.8, -1.83)) < 0.02
