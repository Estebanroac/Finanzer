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


_INSTANCE = b"""<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:iso4217="http://www.xbrl.org/2003/iso4217"
  xmlns:ifrs-full="https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full" xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
  xmlns:dei="http://xbrl.sec.gov/dei/2025">
 <xbrli:context id="fy"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period>
 </xbrli:context>
 <xbrli:context id="seg"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier>
  <xbrli:segment><xbrldi:explicitMember dimension="a">b</xbrldi:explicitMember></xbrli:segment></xbrli:entity>
  <xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period>
 </xbrli:context>
 <xbrli:context id="i"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
 <xbrli:unit id="twd"><xbrli:measure>iso4217:TWD</xbrli:measure></xbrli:unit>
 <xbrli:unit id="eps"><xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:TWD</xbrli:measure></xbrli:unitNumerator>
  <xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>
 <ifrs-full:Revenue contextRef="fy" unitRef="twd" decimals="-5">3809054000000</ifrs-full:Revenue>
 <ifrs-full:Revenue contextRef="seg" unitRef="twd" decimals="-5">100</ifrs-full:Revenue>
 <ifrs-full:Assets contextRef="i" unitRef="twd" decimals="-5">7932842500000</ifrs-full:Assets>
 <ifrs-full:DilutedEarningsLossPerShare contextRef="fy" unitRef="eps" decimals="2">65.46</ifrs-full:DilutedEarningsLossPerShare>
</xbrli:xbrl>"""


def test_instance_facts_without_dimensions_in_companyfacts_shape():
    d = E.parse_instance(_INSTANCE, "20-F", "2026-04-16", "acc")
    rev = d["ifrs-full"]["Revenue"]["units"]["TWD"]
    assert rev == [{"start": "2025-01-01", "end": "2025-12-31", "val": 3809054000000, "form": "20-F",
                    "filed": "2026-04-16", "accn": "acc"}]          # el hecho por segmento queda fuera
    assert d["ifrs-full"]["Assets"]["units"]["TWD"][0]["end"] == "2025-12-31"
    assert d["ifrs-full"]["DilutedEarningsLossPerShare"]["units"]["TWD/shares"][0]["val"] == 65.46
