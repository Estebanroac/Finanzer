"""
Fase 2b (T5): deuda coherente con el EBITDA (F2_PRECEDENCIA §2.3): un arrendamiento entra en la deuda si y solo si su
coste no está restado del EBITDA. Componentes separados; bancos fuera de las ratios de apalancamiento; cautiva
declarada; Altman X4 sin el arrendamiento operativo en US GAAP.
"""
import pytest

import debt
import fixture_backend as fb
import f2b_fixtures as ff
import sec_edgar as edgar


def _f(end, val, form="10-Q", filed="2026-08-01", accn="q"):
    return {"end": end, "val": val, "form": form, "filed": filed, "accn": accn}


def _ed(concepts, tax="us-gaap", unit="USD"):
    base = {"Assets": {"units": {unit: [_f("2025-12-31", 1, "10-K", "2026-02-01", "k")]}}}
    facts = {"facts": {tax: {**base, **{c: {"units": {unit: fs}} for c, fs in concepts.items()}}}}
    return {"status": "ok", "facts_status": "ok", "facts": edgar._index_facts(facts)}


def _info(total, clo=None, cut="2026-06-30", clo_end=None):
    fields = {"totalDebt": {"period_end": cut, "period_type": "balance"}}
    if clo is not None:
        fields["capitalLeaseObligations"] = {"period_end": clo_end or cut, "period_type": "balance"}
    return {"currency": "USD", "totalDebt": total, "capitalLeaseObligations": clo, "_provenance": {},
            "_as_of": {"type": "ttm", "date": cut, "fields": fields}}


def test_us_gaap_operating_out_finance_in():
    ed = _ed({"OperatingLeaseLiabilityNoncurrent": [_f("2026-06-30", 16.5)],
              "OperatingLeaseLiabilityCurrent": [_f("2026-06-30", 5.4)],
              "FinanceLeaseLiability": [_f("2026-06-30", 66.6)]})
    info = _info(56.8, clo=16.5)
    out = debt.apply(info, ed)
    assert info["totalDebt"] == pytest.approx(40.3 + 66.6)
    c = out["components"]
    assert c["borrowings"]["value"] == pytest.approx(40.3) and c["finance_leases"]["in_rule_debt"]
    assert c["operating_leases"]["value"] == pytest.approx(21.9) and not c["operating_leases"]["in_rule_debt"]
    assert info["_provenance"]["totalDebt"]["source"] == "derivado"


def test_finance_lease_only_in_the_10k_is_used_with_its_date():
    ed = _ed({"FinanceLeaseLiability": [_f("2025-12-31", 0.576, "10-K", "2026-02-20", "k")]})
    info = _info(92.206, clo=0.968)
    out = debt.apply(info, ed)
    fl = out["components"]["finance_leases"]
    assert fl["basis"] == "ultimo_anual" and "2025-12-31" in fl["note"]
    assert info["totalDebt"] == pytest.approx(92.206 - 0.968 + 0.576)


def test_lease_row_of_another_period_is_not_subtracted():
    out = debt.apply(_info(45.1, clo=0.9, clo_end="2025-12-31"), _ed({}))
    assert out["total"] == pytest.approx(45.1) and "otro periodo" in out["notes"][0]


def test_ifrs_keeps_the_source_debt():
    ed = _ed({"LeaseLiabilities": [_f("2026-06-30", 1.5, "6-K")]}, tax="ifrs-full", unit="EUR")
    info = _info(32.4)
    info["currency"] = "EUR"
    out = debt.apply(info, ed)
    assert info["totalDebt"] == 32.4 and not out["applied"] and out["components"]["leases_ifrs16"]["in_rule_debt"]


def test_without_edgar_the_debt_is_the_source_one():
    info = _info(10.0, clo=1.0)
    out = debt.apply(info, {"status": "desactivado"})
    assert info["totalDebt"] == 10.0 and not out["applied"] and "sin desglose oficial" in out["notes"][0]


def test_parse_segment_reads_the_captive_member_only():
    xml = ff.instance_xml({"facts": {}}, {"axis": "ProductOrServiceAxis", "member": "FinancialProductsMember",
                                          "by_date": {"2026-06-30": {"ShortTermBorrowings": 5046e6,
                                                                     "LongTermDebtAndCapitalLeaseObligations": 21384e6}}})
    got = edgar.parse_segment(xml.encode(), "ProductOrServiceAxis", "FinancialProductsMember",
                              edgar.CAPTIVE_DEBT_CONCEPTS)
    assert got == {"2026-06-30": {"ShortTermBorrowings": 5046e6, "LongTermDebtAndCapitalLeaseObligations": 21384e6}}
    assert edgar.parse_segment(xml.encode(), "ProductOrServiceAxis", "MachineryMember",
                               edgar.CAPTIVE_DEBT_CONCEPTS) == {}


needs_panel = pytest.mark.skipif(not fb.panel_available() or not ff.available(), reason="sin fixtures del panel")


def _run(sym):
    with fb.replay(fb.fixtures_dir("panel")) as store:
        return fb.run_analysis(sym, store)


@needs_panel
def test_msft_finance_leases_enter_the_debt():
    a = _run("MSFT")
    assert a["key_metrics"]["total_debt"] == pytest.approx(106.888e9, rel=1e-3)     # what-if de la 2a: 106.9


@needs_panel
def test_amzn_operating_leases_leave_the_debt():
    a = _run("AMZN")
    # 2a: 136.1 con la deuda de EDGAR; Yahoo no recoge la parte corriente de la deuda a largo plazo (3.6)
    assert a["key_metrics"]["total_debt"] == pytest.approx(132.4e9, rel=1e-3)


@needs_panel
def test_bank_leverage_ratios_do_not_apply():
    a = _run("BCS")
    km, fields = a["key_metrics"], a["data_provenance"]["fields"]
    assert km["de"] is None and km["enterprise_value"] is None and km["net_debt"] is None
    assert fields["key_metrics.de"]["source"] == "politica_arquetipo"
    assert a["data_provenance"]["debt"]["components"]["subordinated"]["value"] > 0


@needs_panel
def test_cat_captive_is_declared_not_used():
    a = _run("CAT")
    d = a["data_provenance"]["debt"]
    assert d["components"]["captive"]["value"] == pytest.approx(34.456e9, rel=1e-3)
    assert a["key_metrics"]["total_debt"] == pytest.approx(d["source_total"])


@needs_panel
def test_altman_x4_without_operating_leases_in_us_gaap():
    a = _run("NVDA")
    assert a["altman_z"]["operating_leases_excluded"] and a["altman_z"]["z_score"] > 12.85
