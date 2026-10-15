"""
Fase 2a: piezas de la herramienta de EDGAR (tests/edgar.py) con hechos sintéticos, sin red.
"""
import edgar as E


def _f(val, end, start=None, form="10-K", filed="2026-02-01", accn="a"):
    d = {"val": val, "end": end, "form": form, "filed": filed, "accn": accn}
    if start:
        d["start"] = start
    return d


def test_span_classifies_fy_quarter_and_cumulative():
    assert E.span(_f(1, "2025-12-31", "2025-01-01")) == "FY"
    assert E.span(_f(1, "2025-06-30", "2025-04-01")) == "Q"
    assert E.span(_f(1, "2025-06-30", "2025-01-01")) == "6M"
    assert E.span(_f(1, "2025-09-30", "2025-01-01")) == "9M"
    assert E.span(_f(1, "2025-12-31")) == "instant"


def test_current_value_is_the_latest_filing_and_restatement_is_measured():
    g = [_f(100, "2024-12-31", "2024-01-01", filed="2025-02-01", accn="x"),
         _f(87, "2024-12-31", "2024-01-01", filed="2026-02-01", accn="y")]
    assert E.current(g)["val"] == 87 and E.original(g)["val"] == 100
    assert abs(E.restated(g) - 0.13) < 1e-9
    assert E.restated(g[:1]) is None


def test_taxonomy_follows_the_latest_balance_not_the_concept_count():
    """TM: más conceptos us-gaap (historia) pero el último balance en ifrs-full."""
    facts = {"facts": {
        "us-gaap": {f"C{i}": {} for i in range(50)} | {
            "Assets": {"units": {"JPY": [_f(1, "2020-03-31", form="20-F")]}}},
        "ifrs-full": {"Assets": {"units": {"JPY": [_f(1, "2025-03-31", form="20-F")]}}}}}
    assert E.taxonomy(facts) == "ifrs-full"
    assert E.reporting_unit(facts, "ifrs-full") == "JPY"


def test_resolve_picks_the_concept_reaching_the_latest_year_and_flags_stale():
    facts = {"facts": {"us-gaap": {
        "Assets": {"units": {"USD": [_f(10, "2025-12-31")]}},
        "Revenues": {"units": {"USD": [_f(5, "2019-12-31", "2019-01-01")]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            _f(7, "2025-12-31", "2025-01-01")]}},
        "GrossProfit": {"units": {"USD": [_f(3, "2020-12-31", "2020-01-01")]}},
    }}}
    r = E.resolve(facts, "revenue", "us-gaap", "USD")
    assert r["concept"] == "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" and not r["stale"]
    g = E.resolve(facts, "gross_profit", "us-gaap", "USD")
    assert g["concept"] == "us-gaap:GrossProfit" and g["stale"]
    assert E.resolve(facts, "inventories", "us-gaap", "USD")["concept"] is None


def test_per_share_unit_follows_the_statement_currency():
    facts = {"facts": {"ifrs-full": {
        "Assets": {"units": {"GBP": [_f(1, "2025-12-31", form="20-F")]}},
        "DilutedEarningsLossPerShare": {"units": {"GBP/shares": [
            _f(0.4, "2025-12-31", "2025-01-01", form="20-F")]}}}}}
    r = E.resolve(facts, "diluted_eps", "ifrs-full", "GBP")
    assert r["unit"] == "GBP/shares"


def test_predecessor_history_is_merged_and_the_newest_filing_wins():
    new = {"cik": 2, "facts": {"us-gaap": {"Assets": {"units": {"USD": [
        _f(30, "2026-06-30", form="10-Q", filed="2026-08-03", accn="n")]}}}}}
    old = {"cik": 1, "facts": {"us-gaap": {"Assets": {"units": {"USD": [
        _f(20, "2025-12-31", filed="2026-02-18", accn="o")]}}}}}
    m = E.merge_facts(new, old)
    ends = sorted(f["end"] for f in m["facts"]["us-gaap"]["Assets"]["units"]["USD"])
    assert ends == ["2025-12-31", "2026-06-30"] and m["predecessor"]["cik"] == 1
