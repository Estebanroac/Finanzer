"""Rendimiento (rama rendimiento/v4f8-memoria): menos peticiones a EDGAR por análisis, con el mismo resultado.

  · lib/sec_edgar._cached: una sola descarga por clave a la vez; la espera detrás de otro no gasta presupuesto.
  · lib/segments.last_annual: la lista de informes anuales sale de sec_edgar.submissions (la misma respuesta que el
    análisis), sin otra descarga del mismo JSON.
  · lib/segments.prefetch: la descarga anticipada del informe anual la toma build; cada archivo se pide una vez y el
    resultado es el mismo que sin ella.
Sin red: el descargador de sec_edgar (FETCHER) es uno falso que cuenta las peticiones."""
import threading
import time
from collections import Counter

import pytest

import sec_edgar as edgar
import segments
from test_segments import BUSINESS, GEO, TOTAL, fake_fetcher, instance, label_linkbase

ACC = "000000000125000001"


@pytest.fixture
def prod(monkeypatch):
    """El camino de producción (segments.FETCHER = None) con el descargador de sec_edgar falso y contado."""
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "test test@example.invalid")
    monkeypatch.setattr(edgar.time, "sleep", lambda *_a: None)
    monkeypatch.setattr(segments, "INSURER", lambda sym: False)
    monkeypatch.setattr(segments, "FETCHER", None)
    edgar.reset()
    segments.reset()
    calls: Counter = Counter()
    lab = label_linkbase({"x:AmericasMember": "Americas [Member]", "x:EuropeMember": "Europe [Member]",
                          "x:ChinaMember": "Greater China [Member]"})
    inner = fake_fetcher(instance(TOTAL, BUSINESS, GEO), lab)

    def fetch(url, timeout):
        calls[url] += 1
        return inner(url, timeout)
    monkeypatch.setattr(edgar, "FETCHER", fetch)
    yield calls
    edgar.reset()
    segments.reset()


def test_cached_single_flight_and_forgiven_wait(monkeypatch):
    edgar.reset()
    started, release, made = threading.Event(), threading.Event(), []

    def make():
        made.append(1)
        started.set()
        release.wait(5)
        return {"v": 1}
    out, b2 = {}, edgar.Budget(3.0)
    t1 = threading.Thread(target=lambda: out.setdefault("a", edgar._cached("k:1", 60, make, edgar.Budget(3.0))))
    t1.start()
    started.wait(5)
    t2 = threading.Thread(target=lambda: out.setdefault("b", edgar._cached("k:1", 60, make, b2)))
    t2.start()
    time.sleep(0.3)                     # el segundo espera la descarga del primero
    release.set()
    t1.join(5)
    t2.join(5)
    assert len(made) == 1 and out["a"] is out["b"] == {"v": 1}
    assert b2.queued_s >= 0.2           # su espera fue cola perdonada, no presupuesto gastado
    edgar.reset()


def test_cached_waiter_retries_when_the_other_fails():
    edgar.reset()
    started, release, calls = threading.Event(), threading.Event(), []

    def failing():
        calls.append("falla")
        started.set()
        release.wait(5)
        raise edgar.Unavailable("EDGAR respondió 503")
    res = {}
    t1 = threading.Thread(target=lambda: res.setdefault("a", _try(lambda: edgar._cached("k:2", 60, failing))))
    t1.start()
    started.wait(5)
    t2 = threading.Thread(target=lambda: res.setdefault("b", edgar._cached("k:2", 60, lambda: calls.append("ok") or 7)))
    t2.start()
    time.sleep(0.2)
    release.set()
    t1.join(5)
    t2.join(5)
    assert isinstance(res["a"], edgar.Unavailable) and res["b"] == 7 and calls == ["falla", "ok"]
    edgar.reset()


def _try(f):
    try:
        return f()
    except Exception as e:  # noqa: BLE001
        return e


def test_last_annual_reuses_the_submissions_of_the_analysis(prod):
    b = edgar.Budget(8.0)
    edgar.submissions(1, b)                                   # lo que ya hizo el análisis
    f = segments.last_annual(1, b)
    assert f["accessionNumber"] == "0000000001-25-000001" and f["form"] == "10-K"
    assert prod[edgar.SUBMISSIONS_URL.format(cik=1)] == 1     # una sola descarga del JSON de submissions


def test_last_annual_same_as_its_own_download(prod, monkeypatch):
    """El mismo informe que con su propia descarga (el camino del replay, segments.FETCHER)."""
    new = segments.last_annual(1, edgar.Budget(8.0))
    segments.reset()
    edgar.reset()
    monkeypatch.setattr(segments, "FETCHER", edgar.FETCHER)
    assert segments.last_annual(1, edgar.Budget(8.0)) == new


def test_prefetch_is_taken_by_build_once_each_file(prod):
    segments._prefetch("TEST")                                # síncrono: en producción va en su hilo
    assert segments._pre["0000000001-25-000001"]["done"].is_set()
    r = segments.build("TEST")
    assert r["status"] == "ok" and [s["label"] for s in r["segments"]] == ["Americas", "Europe", "Greater China"]
    assert not segments._pre                                  # tomada y su archivo cerrado
    for name in ("index.json", "x-20250927_htm.xml", "x-20250927_lab.xml"):
        assert prod[edgar.ARCHIVE_URL.format(cik=1, acc=ACC, name=name)] == 1, name
    segments.reset()
    edgar.reset()
    assert segments.build("TEST") == r                        # sin descarga anticipada: el mismo resultado


def test_prefetch_skips_what_is_already_read(prod):
    segments.build("TEST")
    before = sum(prod.values())
    segments._prefetch("TEST")
    assert not segments._pre and sum(prod.values()) == before


def test_prefetch_failure_falls_back_to_the_normal_download(prod, monkeypatch):
    real = edgar.FETCHER
    monkeypatch.setattr(edgar, "FETCHER", lambda url, t: (None, 503) if url.endswith("_htm.xml") else real(url, t))
    segments._prefetch("TEST")
    monkeypatch.setattr(edgar, "FETCHER", real)
    r = segments.build("TEST")
    assert r["status"] == "ok" and not segments._pre


def test_unclaimed_prefetch_expires(prod, monkeypatch):
    segments._prefetch("TEST")
    rec = segments._pre["0000000001-25-000001"]
    rec["t"] -= segments.cfg("market.segments.prefetch_ttl_s") + 1
    with segments._lock:
        segments._expire_prefetched()
    assert not segments._pre and rec["tmp"] is None


def test_xbrl_reader_drops_only_unread_text_and_matches_iterparse():
    """La lectura selectiva (sec_edgar.xbrl_top_elements) da lo mismo que iterparse en parse_segments y
    parse_instance, también con una nota de texto enorme que nadie lee (como las de BCS)."""
    import io
    import xml.etree.ElementTree as ET
    from test_segments import AXES, ELIMS, GEO_AXES, NEUTRAL, REV
    note = '<us-gaap:SegmentReportingDisclosureTextBlock contextRef="c1">' + "&lt;p&gt;Ñandú — £" * 50000 + \
        "</us-gaap:SegmentReportingDisclosureTextBlock>"
    xml = instance(TOTAL, BUSINESS, GEO).replace(b"</xbrli:xbrl>", note.encode() + b"</xbrli:xbrl>")
    kept = [(el.tag.rsplit("}", 1)[-1], el.text) for el in
            edgar.xbrl_top_elements(io.BytesIO(xml), lambda n: n in REV)]
    assert ("SegmentReportingDisclosureTextBlock", None) in kept               # la nota, sin su texto
    assert any(t == "RevenueFromContractWithCustomerExcludingAssessedTax" and v for t, v in kept)
    assert sum(1 for t, _ in kept if t == "context") == xml.count(b"<xbrli:context ")

    def old_top(src):                       # el recorrido de antes: iterparse a profundidad 1
        depth = 0
        for ev, el in ET.iterparse(src, events=("start", "end")):
            depth += 1 if ev == "start" else -1
            if ev == "end" and depth == 1:
                yield el
    real = edgar.xbrl_top_elements
    new_seg = edgar.parse_segments(xml, AXES, REV, NEUTRAL, GEO_AXES, ELIMS)
    new_inst = edgar.parse_instance(xml, "10-K", "2025-10-31", "a")
    try:
        edgar.xbrl_top_elements = lambda src, keep: old_top(src)
        assert edgar.parse_segments(xml, AXES, REV, NEUTRAL, GEO_AXES, ELIMS) == new_seg
        assert edgar.parse_instance(xml, "10-K", "2025-10-31", "a") == new_inst
    finally:
        edgar.xbrl_top_elements = real


def test_pending_instance_goes_through_a_file_with_the_same_facts(prod):
    """La instancia pendiente del análisis se descarga a un archivo temporal (C 10-Q: 48 → 3 MB de pico) y da los
    mismos hechos que leída desde sus bytes."""
    xml = instance(TOTAL, BUSINESS, GEO)
    filing = {"form": "10-K", "filingDate": "2025-10-31", "accessionNumber": "0000000001-25-000001"}
    got = edgar.instance_facts(1, filing, edgar.Budget(8.0))
    assert got == edgar.parse_instance(xml, "10-K", "2025-10-31", "0000000001-25-000001")
    assert got["facts"] and prod[edgar.ARCHIVE_URL.format(cik=1, acc=ACC, name="x-20250927_htm.xml")] == 1


def test_submissions_json_keeps_what_is_read_as_json_loads():
    """sec_edgar.submissions_json: json.loads sin las columnas de filings.recent que nadie lee (JPM: 16 columnas de
    26.501 filings, 22 → 11,5 MB de pico); lo demás igual, también con claves repetidas y formas raras."""
    import json as _json
    doc = {"cik": "1", "name": "X", "addresses": {"business": {"city": "NY"}}, "flags": "",
           "filings": {"recent": {"accessionNumber": ["a", "b"], "filingDate": ["2026-01-01", "2025-01-01"],
                                  "reportDate": ["", "2024-12-31"], "acceptanceDateTime": ["x", "y"],
                                  "form": ["8-K", "10-K"], "items": ["2.02", ""], "size": [1, 2],
                                  "isXBRL": [0, 1], "primaryDocument": ["p", "q"]},
                       "files": [{"name": "CIK1-submissions-001.json"}]}}
    body = _json.dumps(doc, indent=1).encode()
    exp = _json.loads(body)
    exp["filings"]["recent"] = {k: v for k, v in exp["filings"]["recent"].items() if k in edgar._RECENT_USED}
    assert edgar.submissions_json(body) == exp
    dup = b'{"name": "a", "filings": {"recent": {"form": ["1"]}, "recent": {"form": ["2"], "size": [3]}}, "name": "b"}'
    assert edgar.submissions_json(dup) == {"name": "b", "filings": {"recent": {"form": ["2"]}}}
    for odd in (b'[1, 2]', b'{"filings": [1]}', b'{"filings": {"recent": 3}}'):
        assert edgar.submissions_json(odd) == _json.loads(odd)
    with pytest.raises(ValueError):
        edgar.submissions_json(b'{"filings": {"recent": {"form": [')
