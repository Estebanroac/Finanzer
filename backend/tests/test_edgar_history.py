"""
Fase 3 (T1b): historia anual larga de EDGAR (10+ ejercicios) y caché en memoria con tope y semáforo
(F3_T1_PARADA1 §2; aprobación del usuario en el registro #25 de la bitácora).
"""
import threading
import time

import pytest

import sec_edgar as edgar


def _f(start, end, val, filed, form="10-K", accn="a"):
    out = {"end": end, "val": val, "filed": filed, "form": form, "accn": accn}
    if start:
        out["start"] = start
    return out


def _facts(tax="us-gaap", unit="USD", assets_end="2025-12-31", **concepts):
    f = {tax: {"Assets": {"units": {unit: [_f(None, assets_end, 1, "2026-02-01")]}}}}
    for c, node in concepts.items():
        tx, name = c.split("__") if "__" in c else (tax, c)
        f.setdefault(tx, {})[name] = node
    return {"facts": f}


def _years(concept_values, unit="USD"):
    return {"units": {unit: [_f(f"{y}-01-01", f"{y}-12-31", v, f"{y + 1}-02-01", "10-K", f"k{y}")
                             for y, v in concept_values]}}


def test_history_chains_concepts_across_label_changes():
    """ASC 606 (2018): `SalesRevenueNet` deja de usarse; la serie sigue con `RevenueFromContract…`."""
    facts = _facts(SalesRevenueNet=_years([(2015, 10), (2016, 11), (2017, 12)]),
                   RevenueFromContractWithCustomerExcludingAssessedTax=_years([(2018, 13), (2019, 14)]))
    h = edgar.annual_history(facts, "revenue")
    assert [v["fy_end"][:4] for v in h["values"]] == ["2019", "2018", "2017", "2016", "2015"]
    assert h["values"][0]["concept"].endswith("RevenueFromContractWithCustomerExcludingAssessedTax")
    assert h["values"][-1]["concept"].endswith("SalesRevenueNet") and h["unit"] == "USD"


def test_history_uses_the_latest_filing_of_each_year():
    node = {"units": {"USD": [_f("2024-01-01", "2024-12-31", 100, "2025-02-01", "10-K", "a"),
                              _f("2024-01-01", "2024-12-31", 90, "2026-02-01", "10-K", "b")]}}
    h = edgar.annual_history(_facts(Revenues=node), "revenue")
    assert h["values"][0]["value"] == 90, "reexpresión: manda el filing más reciente"


def test_history_ignores_quarters_and_quarterly_forms():
    node = {"units": {"USD": [_f("2025-01-01", "2025-12-31", 400, "2026-02-01", "10-K"),
                              _f("2025-01-01", "2025-06-30", 200, "2025-08-01", "10-Q"),
                              _f("2024-07-01", "2025-06-30", 380, "2025-08-01", "10-Q")]}}
    h = edgar.annual_history(_facts(Revenues=node), "revenue")
    assert [v["value"] for v in h["values"]] == [400]


def test_history_per_share_and_shares_units():
    facts = _facts(EarningsPerShareDiluted=_years([(2025, 6.1)], unit="USD/shares"),
                   WeightedAverageNumberOfDilutedSharesOutstanding=_years([(2025, 1.5e9)], unit="shares"))
    assert edgar.annual_history(facts, "diluted_eps")["values"][0]["value"] == 6.1
    assert edgar.annual_history(facts, "diluted_shares")["values"][0]["value"] == 1.5e9


def test_history_capex_has_the_sign_of_the_source():
    h = edgar.annual_history(_facts(PaymentsToAcquirePropertyPlantAndEquipment=_years([(2025, 300)])), "capex")
    assert h["values"][0]["value"] == -300


def test_change_of_standard_is_declared_and_only_for_comparable_fields():
    """TM: US GAAP hasta el FY2020, IFRS desde el FY2021 (ejercicio a marzo)."""
    ifrs = {"units": {"JPY": [_f(f"{y - 1}-04-01", f"{y}-03-31", y, f"{y}-06-20", "20-F", f"i{y}")
                              for y in (2022, 2023, 2024)]}}
    us = {"units": {"JPY": [_f(f"{y - 1}-04-01", f"{y}-03-31", y, f"{y}-06-20", "20-F", f"u{y}")
                            for y in (2019, 2020, 2021, 2022)]}}
    us_oi = {"units": {"JPY": [_f("2020-04-01", "2021-03-31", 5, "2021-06-20", "20-F")]}}
    facts = _facts(tax="ifrs-full", unit="JPY", assets_end="2024-03-31",
                   **{"ifrs-full__Revenue": ifrs, "us-gaap__Revenues": us,
                      "ifrs-full__ProfitLossFromOperatingActivities": ifrs, "us-gaap__OperatingIncomeLoss": us_oi,
                      "us-gaap__Assets": {"units": {"JPY": [_f(None, "2021-03-31", 1, "2021-06-20")]}}})
    rev = edgar.annual_history(facts, "revenue")
    assert [v["fy_end"][:4] for v in rev["values"]] == ["2024", "2023", "2022", "2021", "2020", "2019"]
    assert rev["values"][2]["taxonomy"] == "ifrs-full", "en el año que solapa manda la norma vigente"
    assert rev["cross_taxonomy"] == {"taxonomy": "us-gaap", "until": "2021-03-31", "years": 3}
    oi = edgar.annual_history(facts, "operating_income")
    assert len(oi["values"]) == 3 and oi["cross_taxonomy"] is None, "el EBIT cambia de definición con la norma"


def test_history_without_facts_is_empty():
    assert edgar.annual_history({"facts": {}}, "revenue") == {"values": [], "unit": None, "cross_taxonomy": None}


def test_history_concepts_are_kept_by_the_reduced_extract():
    raw = {"cik": 1, "entityName": "X", "facts": _facts(
        EarningsPerShareDiluted=_years([(2025, 1.0)], unit="USD/shares"),
        WeightedAverageNumberOfDilutedSharesOutstanding=_years([(2025, 2.0)], unit="shares"),
        SomethingElse=_years([(2025, 3.0)]))["facts"]}
    red = edgar.reduce_facts(raw)
    kept = set(red["facts"]["us-gaap"])
    assert {"EarningsPerShareDiluted", "WeightedAverageNumberOfDilutedSharesOutstanding"} <= kept
    assert "SomethingElse" not in kept


# ───────────── caché con tope y semáforo ─────────────

@pytest.fixture
def clean_cache(monkeypatch):
    monkeypatch.setattr(edgar, "_cache", edgar.OrderedDict())
    yield edgar._cache


def test_cache_evicts_the_least_recently_used_issuer(clean_cache, monkeypatch):
    monkeypatch.setattr(edgar, "_cache_cap", lambda kind: 2)
    for cik in (1, 2):
        edgar._cached(f"facts:{cik}", 3600, lambda c=cik: c)
    assert edgar._cached("facts:1", 3600, lambda: "nuevo") == 1, "acierto: pasa a ser el más reciente"
    edgar._cached("facts:3", 3600, lambda: 3)
    assert set(clean_cache) == {"facts:1", "facts:3"}, "sale el 2, el usado hace más tiempo"


def test_cache_cap_is_per_kind(clean_cache, monkeypatch):
    monkeypatch.setattr(edgar, "_cache_cap", lambda kind: 1)
    edgar._cached("facts:1", 3600, lambda: 1)
    edgar._cached("sub:1", 3600, lambda: 1)
    edgar._cached("tickers", 3600, lambda: {})
    assert set(clean_cache) == {"facts:1", "sub:1", "tickers"}


def test_cache_cap_from_config():
    from settings import cfg
    assert edgar._cache_cap("facts") == cfg("data.edgar.cache_max_issuers")
    assert edgar._cache_cap("inst") == cfg("data.edgar.cache_max_issuers") * cfg("data.edgar.max_pending_filings")


def test_large_reads_are_serialised(clean_cache, monkeypatch):
    monkeypatch.setattr(edgar, "_parse_lock", None)
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "Test test@example.com")
    monkeypatch.setattr(edgar, "_get", lambda url, budget: b"{}")
    state = {"now": 0, "max": 0}
    lock = threading.Lock()

    def slow_reduce(raw):
        with lock:
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
        time.sleep(0.05)
        with lock:
            state["now"] -= 1
        return {"facts": {}}
    monkeypatch.setattr(edgar, "reduce_facts", slow_reduce)
    ts = [threading.Thread(target=edgar.company_facts, args=(cik, edgar.Budget())) for cik in (1, 2, 3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert state["max"] == 1


# ─────────────── V4 · memoria: companyfacts leído concepto a concepto (mismo resultado que json.loads) ───────────────
def _same(body: bytes):
    import json as _json
    want = edgar.reduce_facts(_json.loads(body))
    got = edgar.reduce_facts_stream(body)
    assert got == want
    assert _json.dumps(got) == _json.dumps(want)            # también el orden de las claves


def test_stream_reducer_equals_json_loads_on_every_fixture():
    import glob
    import os
    files = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "f2b", "edgar",
                                          "companyfacts", "*.json")))
    assert len(files) >= 40
    for f in files:
        _same(open(f, "rb").read())


def test_stream_reducer_edge_cases():
    import json as _json
    tx = edgar.FINANCIAL_TAXONOMIES[0]
    wanted = sorted(edgar._WANTED[tx])[0]
    fact = {"start": "2024-01-01", "end": "2024-12-31", "val": 1.5, "filed": "2025-02-01", "form": "10-K",
            "accn": "0001-25-000001", "fy": 2024, "fp": "FY", "frame": "CY2024"}
    other = {**fact, "accn": "0001-25-000009", "filed": "2025-03-01"}
    base = {"cik": 1, "entityName": "Ñandú “Corp” \\u00e9", "facts": {
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{**fact, "accn": "DEI", "filed": "2099-01-01"}]}}},
        tx: {"Unwanted": {"label": "x", "units": {"USD": [other]}}, wanted: {"label": "y", "units": {"USD": [fact]}}}}}
    _same(_json.dumps(base).encode())
    _same(_json.dumps(base, indent=2).encode())                                    # espacios y saltos de línea
    _same(("﻿" + _json.dumps(base)).encode("utf-8"))                         # BOM
    _same(b'{"cik": 1, "facts": {}}')
    _same(b'{"cik": 1}')
    dup = _json.dumps(base)[:-2] + ', "' + tx + '": {"' + wanted + '": {"units": {"USD": [' + _json.dumps(other) + "]}}}}}"
    _same(dup.encode())                                                            # taxonomía repetida: vale la última
    import pytest
    with pytest.raises(AttributeError):                                           # forma rara: el mismo error que antes
        edgar.reduce_facts(_json.loads(b'{"facts": [1, 2], "cik": 3}'))
    with pytest.raises(AttributeError):
        edgar.reduce_facts_stream(b'{"facts": [1, 2], "cik": 3}')
    _same(b'{"facts": {"dei": [1]}, "cik": 3}')                                   # taxonomía no financiera rara
    for bad in (b'{"facts": {', b'{"a": 1} x', b'{1: 2}'):
        with pytest.raises(ValueError):
            edgar.reduce_facts_stream(bad)


def test_reduced_facts_share_repeated_strings():
    """V4 · memoria: en lo reducido, cada accn / form / filed / fecha repetida es un solo objeto (mismos valores)."""
    import glob
    import os
    f = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "f2b", "edgar",
                                      "companyfacts", "*.json")), key=os.path.getsize)[-1]
    red = edgar._compact(edgar.reduce_facts_stream, open(f, "rb").read())
    by_value = {}
    for cs in red["facts"].values():
        for node in cs.values():
            for fs in node["units"].values():
                for fact in fs:
                    for k in ("accn", "form", "filed", "end"):
                        if k in fact:
                            by_value.setdefault(fact[k], set()).add(id(fact[k]))
    assert by_value and all(len(ids) == 1 for ids in by_value.values())
