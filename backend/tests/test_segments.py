"""Rediseño E2b (Task 2): ingresos por segmento desde la instancia XBRL del último 10-K/20-F (lib/segments.py,
sec_edgar.parse_segments / labels). Sin red: instancias sintéticas y fixtures capturados (tests/fixtures/segments)."""
import json
import os

import pytest

import sec_edgar as edgar
import segments
from settings import cfg

FIX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "segments")
REV = tuple(cfg("market.segments.revenue_concepts"))
AXES = tuple(cfg("market.segments.axes")) + tuple(cfg("market.segments.geographic_axes"))
NEUTRAL = tuple(cfg("market.segments.neutral_members"))
GEO_AXES = tuple(cfg("market.segments.geographic_axes"))
ELIMS = tuple(cfg("market.segments.elimination_members"))
REDUNDANT = tuple(cfg("market.segments.redundant_axes"))

YEARS = [("2022-10-01", "2023-09-30"), ("2023-10-01", "2024-09-28"), ("2024-09-29", "2025-09-27")]


def _ctx(cid, start, end, members=()):
    seg = ""
    if members:
        seg = "<xbrli:segment>" + "".join(
            f'<xbrldi:explicitMember dimension="{d}">{m}</xbrldi:explicitMember>' for d, m in members) + \
            "</xbrli:segment>"
    period = (f"<xbrli:period><xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate>"
              "</xbrli:period>") if start else f"<xbrli:period><xbrli:instant>{end}</xbrli:instant></xbrli:period>"
    return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1'
            f"</xbrli:identifier>{seg}</xbrli:entity>{period}</xbrli:context>")


def instance(total, business, geo, product=None, concept="RevenueFromContractWithCustomerExcludingAssessedTax",
             crossed=None, elims=None, raw=None, ext_totals=None, total_concept=None):
    """Instancia mínima: total sin dimensión, segmentos de negocio (con el miembro neutro de ASU 2023-07),
    geográficos (una sola dimensión) y, opcional, productos con un agregado. Valores por año (lista de 3)."""
    ctxs, facts, n = [], [], [0]

    def fact(vals, members, con=concept):
        for (s, e), v in zip(YEARS, vals):
            n[0] += 1
            cid = f"c{n[0]}"
            ctxs.append(_ctx(cid, s, e, members))
            facts.append(f'<us-gaap:{con} contextRef="{cid}" unitRef="usd" decimals="-6">{v}</us-gaap:{con}>')
    if total is not None:
        fact(total, (), total_concept or concept)
    for mem, vals in business.items():
        fact(vals, [("srt:ConsolidationItemsAxis", "us-gaap:OperatingSegmentsMember"),
                    ("us-gaap:StatementBusinessSegmentsAxis", mem)])
    for mem, vals in geo.items():
        fact(vals, [("srt:StatementGeographicalAxis", mem)])
    for mem, vals in (product or {}).items():
        fact(vals, [("srt:ProductOrServiceAxis", mem)])
    for (mem, zone), vals in (crossed or {}).items():            # segmento × zona (XOM)
        fact(vals, [("srt:StatementGeographicalAxis", zone), ("us-gaap:StatementBusinessSegmentsAxis", mem)])
    for members, vals in (raw or []):                           # contextos con dimensiones a medida
        fact(vals, members)
    ext = "".join(f'<bank:{name} contextRef="c1" unitRef="usd" decimals="-6">{v}</bank:{name}>'
                  for name, v in (ext_totals or {}).items())   # c1: el total sin dimensión del primer año
    for (mem, zone), vals in (elims or {}).items():              # eliminaciones entre segmentos, por zona
        fact(vals, [("srt:ConsolidationItemsAxis", "us-gaap:IntersegmentEliminationMember"),
                    ("srt:StatementGeographicalAxis", zone), ("us-gaap:StatementBusinessSegmentsAxis", mem)])
    # dos dimensiones no neutras: se ignora
    fact([1, 1, 1], [("srt:ProductOrServiceAxis", "x:AMember"), ("srt:StatementGeographicalAxis", "country:US")])
    # trimestre: no es un periodo anual
    ctxs.append(_ctx("q1", "2025-06-29", "2025-09-27", [("srt:StatementGeographicalAxis", "country:US")]))
    facts.append(f'<us-gaap:{concept} contextRef="q1" unitRef="usd" decimals="-6">5</us-gaap:{concept}>')
    return ('<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:iso4217="http://www.xbrl.org/2003/iso4217" '
            'xmlns:us-gaap="http://fasb.org/us-gaap/2025" xmlns:bank="http://www.example-bank.com/20251231">'
            '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
            + "".join(ctxs) + "".join(facts) + ext + "</xbrli:xbrl>").encode()


def label_linkbase(labels):
    locs, labs, arcs = [], [], []
    for i, (qn, text) in enumerate(labels.items()):
        pfx, loc = qn.split(":")
        locs.append(f'<link:loc xlink:type="locator" xlink:href="x.xsd#{pfx}_{loc}" xlink:label="loc{i}"/>')
        labs.append(f'<link:label xlink:type="resource" xlink:label="lab{i}" '
                    f'xlink:role="http://www.xbrl.org/2003/role/label" xml:lang="en-US">{text}</link:label>')
        labs.append(f'<link:label xlink:type="resource" xlink:label="lab{i}" '
                    f'xlink:role="http://www.xbrl.org/2003/role/terseLabel" xml:lang="en-US">corto</link:label>')
        arcs.append(f'<link:labelArc xlink:type="arc" xlink:from="loc{i}" xlink:to="lab{i}" '
                    'xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"/>')
    return ('<?xml version="1.0"?><link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" '
            'xmlns:xlink="http://www.w3.org/1999/xlink"><link:labelLink xlink:type="extended">'
            + "".join(locs + labs + arcs) + "</link:labelLink></link:linkbase>").encode()


BUSINESS = {"x:AmericasMember": [160, 167, 178], "x:EuropeMember": [94, 101, 111], "x:ChinaMember": [72, 67, 64]}
GEO = {"country:US": [138, 142, 151], "x:OtherCountriesMember": [188, 193, 202]}
TOTAL = [326, 335, 353]
BUSINESS_1000 = {"x:UpMember": [600, 600, 600], "x:DownMember": [400, 400, 400]}


# ─────────────────────────── parse_segments / labels ───────────────────────────
def test_parse_segments_axes_periods_and_neutral_member():
    out = edgar.parse_segments(instance(TOTAL, BUSINESS, GEO), AXES, REV, NEUTRAL, GEO_AXES, ELIMS)
    c = "RevenueFromContractWithCustomerExcludingAssessedTax"
    bus = out["axes"]["StatementBusinessSegmentsAxis"][c]
    assert set(bus) == set(BUSINESS)
    assert bus["x:EuropeMember"] == {"2022-10-01/2023-09-30": 94.0, "2023-10-01/2024-09-28": 101.0,
                                     "2024-09-29/2025-09-27": 111.0}
    geo = out["axes"]["StatementGeographicalAxis"][c]
    assert set(geo) == set(GEO) and "2025-06-29/2025-09-27" in geo["country:US"]     # el filtro anual va en build
    assert "x:AMember" not in out["axes"].get("ProductOrServiceAxis", {}).get(c, {})  # dos dimensiones: fuera
    assert out["totals"][c]["2024-09-29/2025-09-27"] == 353.0
    assert out["units"][c] == "USD"


def test_labels_standard_role_without_member_suffix():
    lab = label_linkbase({"x:AmericasMember": "Americas [Member]", "us-gaap:ServiceMember": "Service [Member]",
                          "x:Other": "Otro"})
    assert edgar.labels(lab, {"x:AmericasMember", "us-gaap:ServiceMember"}) == {
        "x:AmericasMember": "Americas", "us-gaap:ServiceMember": "Service"}


# ─────────────────────────── build con un FETCHER falso ───────────────────────────
def fake_fetcher(xml, lab=b"", size=None, form="10-K", annual=True):
    sub = {"cik": 1, "filings": {"recent": {
        "form": [form if annual else "10-Q"], "filingDate": ["2025-10-31"], "reportDate": ["2025-09-27"],
        "accessionNumber": ["0000000001-25-000001"], "isXBRL": [1], "primaryDocument": ["x-20250927.htm"]},
        "files": []}}
    idx = {"directory": {"item": [{"name": "x-20250927_htm.xml", "size": str(size or len(xml))},
                                  {"name": "x-20250927_lab.xml", "size": str(len(lab))}]}}
    resp = {edgar.TICKERS_URL: {"0": {"cik_str": 1, "ticker": "TEST", "title": "Test Inc"}},
            edgar.SUBMISSIONS_URL.format(cik=1): sub,
            edgar.ARCHIVE_URL.format(cik=1, acc="000000000125000001", name="index.json"): idx}
    raw = {edgar.ARCHIVE_URL.format(cik=1, acc="000000000125000001", name="x-20250927_htm.xml"): xml,
           edgar.ARCHIVE_URL.format(cik=1, acc="000000000125000001", name="x-20250927_lab.xml"): lab}

    def fetch(url, timeout):
        if url in raw:
            return raw[url], 200
        if url in resp:
            return json.dumps(resp[url]).encode(), 200
        return None, 404
    return fetch


@pytest.fixture
def fresh(monkeypatch):
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "test test@example.invalid")
    monkeypatch.setattr(edgar.time, "sleep", lambda *_a: None)        # el ritmo de la SEC no aplica sin red
    edgar.reset()
    segments.reset()
    monkeypatch.setattr(segments, "INSURER", lambda sym: False)       # sin Yahoo: los conceptos de siempre
    yield monkeypatch
    edgar.reset()
    segments.reset()


def test_build_business_axis_order_share_secondary_and_reconcile(fresh):
    lab = label_linkbase({"x:AmericasMember": "Americas [Member]", "x:EuropeMember": "Europe [Member]",
                          "x:ChinaMember": "Greater China [Member]", "country:US": "UNITED STATES"})
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(TOTAL, BUSINESS, GEO), lab))
    r = segments.build("TEST")
    assert r["status"] == "ok" and r["axis"] == "StatementBusinessSegmentsAxis"
    assert r["fiscal_years"] == ["2023", "2024", "2025"]
    assert [s["member"] for s in r["segments"]] == ["x:AmericasMember", "x:EuropeMember", "x:ChinaMember"]
    assert [s["label"] for s in r["segments"]] == ["Americas", "Europe", "Greater China"]
    assert r["segments"][0]["values"] == {"2023": 160.0, "2024": 167.0, "2025": 178.0}
    assert abs(sum(s["share_last"] for s in r["segments"]) - 1) < 1e-9
    assert r["total_reported"] == {"2023": 326.0, "2024": 335.0, "2025": 353.0}
    assert r["reconciles"] is True and abs(r["gap_pct"]) < 1e-9
    assert r["secondary"]["axis"] == "StatementGeographicalAxis"
    assert [s["member"] for s in r["secondary"]["segments"]] == ["x:OtherCountriesMember", "country:US"]
    assert r["secondary"]["segments"][1]["label"] == "United States"      # en mayúsculas en el XBRL: mayúscula inicial
    assert r["others"] == []
    assert r["currency"] == "USD"
    assert r["source"] == {"form": "10-K", "filed": "2025-10-31", "accn": "0000000001-25-000001",
                           "period_end": "2025-09-27"}


def test_build_gap_is_published_not_hidden(fresh):
    total = [round(v / 1.05, 3) for v in (326, 335, 353)]
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(total, BUSINESS, GEO)))
    r = segments.build("TEST")
    assert r["status"] == "ok" and r["reconciles"] is False
    assert r["gap_pct"] == pytest.approx(0.05, abs=1e-3)
    assert len(r["segments"]) == 3


def test_build_drops_aggregate_members_and_humanizes_labels(fresh):
    """ProductOrServiceAxis de Apple: Product (agregado) + iPhone, Mac + Service. Se queda el detalle."""
    product = {"us-gaap:ProductMember": [230, 239, 243], "x:IPhoneMember": [200, 201, 209],
               "x:MacMember": [30, 38, 34], "us-gaap:ServiceMember": [96, 96, 110]}
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(TOTAL, {}, {}, product)))
    r = segments.build("TEST")
    assert r["axis"] == "ProductOrServiceAxis" and r["reconciles"] is True
    assert [s["member"] for s in r["segments"]] == ["x:IPhoneMember", "us-gaap:ServiceMember", "x:MacMember"]
    assert r["segments"][0]["label"] == "IPhone"        # sin linkbase: el nombre del miembro, legible
    assert r["secondary"] is None and r["others"] == []


def test_build_segments_crossed_with_geography_net_of_eliminations(fresh):
    """XOM: Upstream y Downstream solo por zona (EE. UU. / fuera), brutos, con las ventas entre segmentos aparte.
    Bruto no concilia; la suma de zonas neta de eliminaciones sí, y se dice."""
    crossed = {("x:UpMember", "country:US"): [50, 52, 51], ("x:UpMember", "us-gaap:NonUsMember"): [55, 57, 56],
               ("x:DownMember", "country:US"): [120, 118, 119], ("x:DownMember", "us-gaap:NonUsMember"): [170, 175, 173]}
    elims = {("x:UpMember", "country:US"): [-25, -26, -25], ("x:UpMember", "us-gaap:NonUsMember"): [-36, -37, -37],
             ("x:DownMember", "country:US"): [-19, -20, -19], ("x:DownMember", "us-gaap:NonUsMember"): [-26, -27, -27]}
    total = [289, 292, 291]
    xml = instance(total, {}, {}, crossed=crossed, elims=elims)
    parsed = edgar.parse_segments(xml, AXES, REV, NEUTRAL, GEO_AXES, ELIMS)
    c = "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert parsed["by_geo"]["StatementBusinessSegmentsAxis"][c]["x:UpMember"]["2024-09-29/2025-09-27"] == {
        "country:US": 51.0, "us-gaap:NonUsMember": 56.0}
    assert "StatementBusinessSegmentsAxis" not in parsed["axes"]
    fresh.setattr(segments, "FETCHER", fake_fetcher(xml))
    r = segments.build("TEST")
    assert r["status"] == "ok" and r["axis"] == "StatementBusinessSegmentsAxis" and r["reconciles"] is True
    assert r["segments"][0]["values"]["2025"] == 119 + 173 - 19 - 27
    assert r["segments"][1]["values"]["2025"] == 51 + 56 - 25 - 37
    assert len(r["notes"]) == 2 and "zonas" in r["notes"][0] and "entre segmentos" in r["notes"][1]


def test_overlapping_members_use_the_partition_that_reconciles(fresh):
    """RIVN: Automotive = Vehicles + Regulatory Credits (no exacto: no lo detecta la regla de agregados) y "Software
    and Services" dos veces. La suma es ~2× los ingresos: se elige el subconjunto que concilia, el de más miembros y
    sin etiquetas casi duplicadas."""
    product = {"x:AutomotiveMember": [3700, 4500, 3880], "x:VehiclesMember": [3550, 4300, 3700],
               "x:RegulatoryCreditsMember": [120, 190, 200], "x:SoftwareAndServicesMember": [600, 870, 1590],
               "x:SoftwareAndServicesRevenueMember": [598, 868, 1585]}
    total = [4300, 5370, 5470]
    lab = label_linkbase({"x:AutomotiveMember": "Automotive", "x:VehiclesMember": "Vehicles",
                          "x:RegulatoryCreditsMember": "Regulatory Credits",
                          "x:SoftwareAndServicesMember": "Software and Services",
                          "x:SoftwareAndServicesRevenueMember": "Software And Services Revenue"})
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(total, {}, {}, product), lab))
    r = segments.build("TEST")
    assert r["axis"] == "ProductOrServiceAxis" and r["reconciles"] is True
    labels = [s["label"] for s in r["segments"]]
    assert len(labels) == 3 and {"Vehicles", "Regulatory Credits"} <= set(labels)
    assert sum(lab.lower().startswith("software and services") for lab in labels) == 1     # una sola de las dos
    assert abs(sum(s["share_last"] for s in r["segments"]) - 1) < 1e-9
    # v4 (PM): en lenguaje claro y sin afirmar el porqué (el código solo sabe que juntos suman más que el total)
    assert any(n.startswith("Algunos segmentos se solapan") and "queda fuera Automotive" in n and "suele pasar" in n
               for n in r["notes"])


def test_overlapping_members_without_partition_are_flagged(fresh):
    product = {"x:AMember": [60, 60, 60], "x:BMember": [70, 70, 70], "x:CMember": [80, 80, 80]}
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance([100, 100, 100], {}, {}, product)))
    r = segments.build("TEST")
    assert r["reconciles"] is False and len(r["segments"]) == 3
    assert any("ninguna combinación suma los ingresos de la empresa" in n for n in r["notes"])


def test_axis_dominated_by_one_member_is_dropped(fresh):
    """XOM: "Sales and other operating revenue" 97,5 % no son segmentos sino componentes del ingreso."""
    product = {"x:SalesMember": [975, 975, 975], "x:EquityMember": [15, 15, 15], "x:OtherMember": [10, 10, 10]}
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance([1000, 1000, 1000], BUSINESS_1000, {}, product)))
    r = segments.build("TEST")
    assert r["axis"] == "StatementBusinessSegmentsAxis" and r["others"] == []
    assert r["dropped_axes"] == [{"axis": "ProductOrServiceAxis", "axis_label": "productos y servicios",
                                  "reason": "«Sales» es el 97.5% del total: son componentes del ingreso, no segmentos"}]


def test_legal_entity_repeating_the_segment_is_not_a_second_dimension(fresh):
    """NEE: el segmento FPL lleva además LegalEntityAxis = FPL; NEER no. Concepto de eléctricas reguladas."""
    c = "RegulatedAndUnregulatedOperatingRevenue"
    raw = [([("srt:ConsolidationItemsAxis", "us-gaap:OperatingSegmentsMember"),
             ("us-gaap:StatementBusinessSegmentsAxis", "nee:FloridaPowerLightCompanyMember"),
             ("dei:LegalEntityAxis", "nee:FloridaPowerLightCompanyMember")], [17000, 16500, 18300]),
           ([("srt:ConsolidationItemsAxis", "us-gaap:OperatingSegmentsMember"),
             ("us-gaap:StatementBusinessSegmentsAxis", "nee:NEERSegmentMember")], [11000, 8300, 9000])]
    xml = instance([28000, 24800, 27300], {}, {}, concept=c, raw=raw)
    parsed = edgar.parse_segments(xml, AXES, REV, NEUTRAL, GEO_AXES, ELIMS, REDUNDANT)
    assert set(parsed["axes"]["StatementBusinessSegmentsAxis"][c]) == {"nee:FloridaPowerLightCompanyMember",
                                                                       "nee:NEERSegmentMember"}
    fresh.setattr(segments, "FETCHER", fake_fetcher(xml))
    r = segments.build("TEST")
    assert r["status"] == "ok" and r["concept"] == c and r["reconciles"] is True and len(r["segments"]) == 2


def test_parse_segments_reads_from_a_file(tmp_path):
    p = tmp_path / "inst.xml"
    p.write_bytes(instance(TOTAL, BUSINESS, GEO))
    with open(p, "rb") as fh:
        assert edgar.parse_segments(fh, AXES, REV, NEUTRAL, GEO_AXES, ELIMS) == \
            edgar.parse_segments(p.read_bytes(), AXES, REV, NEUTRAL, GEO_AXES, ELIMS)


def test_get_to_file_streams_without_holding_the_body(fresh, tmp_path):
    """Con el descargador real, el cuerpo va al archivo en trozos (aquí, un servidor local con gzip)."""
    import gzip
    import http.server
    import threading
    body = b"<x>" + b"a" * 3_000_000 + b"</x>"

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            z = gzip.compress(body)
            self.send_response(200)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(z)))
            self.end_headers()
            self.wfile.write(z)

        def log_message(self, *a):
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        fresh.setattr(edgar, "FETCHER", edgar.urllib_fetcher)
        with open(tmp_path / "out.xml", "w+b") as fh:
            n = edgar._get_to_file(f"http://127.0.0.1:{srv.server_port}/x", edgar.Budget(10.0), fh)
            fh.seek(0)
            assert n == len(body) and fh.read() == body
    finally:
        srv.shutdown()


def test_coverage_against_consolidated_revenue(fresh):
    r_ok = None
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(TOTAL, BUSINESS, GEO)))
    r_ok = segments.build("TEST")
    assert r_ok["concept_label"] == "Ingresos" and r_ok["coverage"] == pytest.approx(1.0)
    assert r_ok["covers_total"] is True and r_ok["coverage_note"] is None
    assert r_ok["coverage_source"] == {"concept": "RevenueFromContractWithCustomerExcludingAssessedTax",
                                       "from": "instancia", "value": 353.0}


def test_coverage_uses_a_broader_standard_total_first(fresh):
    """Segmentos en ingresos de contratos con clientes; el total estándar `Revenues` es mayor: cubren el 80 %."""
    xml = instance(TOTAL, BUSINESS, GEO).replace(b"</xbrli:xbrl>", b"")
    extra = instance([400, 420, 441.25], {}, {}, concept="Revenues")
    # el segundo documento aporta sus contextos y hechos con otros ids
    body = extra.split(b"</xbrli:unit>", 1)[1].replace(b'id="c', b'id="r').replace(b'contextRef="c', b'contextRef="r')
    fresh.setattr(segments, "FETCHER", fake_fetcher(xml + body))
    r = segments.build("TEST")
    assert r["coverage_source"]["concept"] == "Revenues" and r["coverage"] == pytest.approx(353 / 441.25)
    assert r["covers_total"] is False and r["concept_label"] == "Ingresos de contratos con clientes"
    assert r["coverage_note"] == "Ingresos de contratos con clientes · cubren el 80% de los ingresos consolidados"


def test_coverage_with_the_issuer_own_total_only_if_not_smaller(fresh):
    """Banco NIIF: sin total estándar más amplio, el total propio del emisor (OperatingIncome) si no es menor que los
    segmentos; un 'OperatingIncome' menor (beneficio operativo de una no financiera) no vale."""
    xml = instance(TOTAL, BUSINESS, GEO, ext_totals={"OperatingIncome": 1300})   # c1 = primer año… usa el último
    parsed = edgar.parse_segments(xml, AXES, REV, NEUTRAL, GEO_AXES, ELIMS, REDUNDANT, ("OperatingIncome",))
    assert parsed["ext_totals"]["OperatingIncome"] == {"2022-10-01/2023-09-30": 1300.0}
    # total propio del último año, sin total estándar
    x2 = instance(None, BUSINESS, GEO)
    ctx_last = b'<xbrli:context id="tl"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1' \
               b'</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:startDate>2024-09-29</xbrli:startDate>' \
               b'<xbrli:endDate>2025-09-27</xbrli:endDate></xbrli:period></xbrli:context>'
    big = x2.replace(b"</xbrli:xbrl>", ctx_last + b'<bank:OperatingIncome contextRef="tl" unitRef="usd">1000'
                     b'</bank:OperatingIncome></xbrli:xbrl>')
    fresh.setattr(segments, "FETCHER", fake_fetcher(big))
    r = segments.build("TEST")
    assert r["coverage"] == pytest.approx(353 / 1000) and r["coverage_source"]["from"].startswith("instancia (")
    small = x2.replace(b"</xbrli:xbrl>", ctx_last + b'<bank:OperatingIncome contextRef="tl" unitRef="usd">90'
                       b'</bank:OperatingIncome></xbrli:xbrl>')
    segments.reset()
    fresh.setattr(segments, "FETCHER", fake_fetcher(small))
    r = segments.build("TEST")                     # ni estándar ni propio válido: companyfacts (404 aquí) -> sin total
    assert r["coverage"] is None and r["covers_total"] is False
    assert r["coverage_note"] == "sin ingresos consolidados con los que comparar"


def test_real_bcs_fees_cover_part_of_the_bank_income(fresh):
    _replay(fresh)
    r = segments.build("BCS")
    assert r["status"] == "ok" and r["concept"] == "RevenueFromContractsWithCustomers"
    assert r["concept_label"] == "Comisiones" and r["covers_total"] is False
    assert 0.3 < r["coverage"] < 0.45 and r["coverage_source"]["concept"] == "OperatingIncome"
    assert r["coverage_note"].startswith("Comisiones · cubren el ") and r["currency"] == "GBP"


@pytest.mark.parametrize("sym", ["AAPL", "NEE", "XOM", "PLTR", "RIVN"])
def test_real_segments_cover_consolidated_revenue(fresh, sym):
    _replay(fresh)
    r = segments.build(sym)
    assert r["covers_total"] is True and r["coverage_note"] is None and r["concept_label"]


def test_clean_labels():
    assert segments._clean_label("Americas Segment") == "Americas"
    assert segments._clean_label("Government Operating Segment") == "Government"
    assert segments._clean_label("Product and Service, Retail") == "Retail"
    assert segments._clean_label("Segment") == "Segment"


def test_build_without_dimensions_is_sin_dato(fresh):
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(TOTAL, {}, {})))
    r = segments.build("TEST")
    assert r["status"] == "sin_dato" and r["reason"] == "el informe anual (10-K) no desglosa los ingresos por segmento en un formato que se pueda leer automáticamente"
    assert r["segments"] == []


def test_build_large_instance_is_sin_dato_without_download(fresh):
    xml = instance(TOTAL, BUSINESS, GEO)
    big = int((cfg("market.segments.max_instance_mb") + 1) * 1024 * 1024)
    calls = []
    base = fake_fetcher(xml, size=big)

    def fetch(url, timeout):
        calls.append(url)
        return base(url, timeout)
    fresh.setattr(segments, "FETCHER", fetch)
    r = segments.build("TEST")
    assert r["status"] == "sin_dato" and "MB" in r["reason"]
    assert not any(u.endswith("_htm.xml") for u in calls)


def test_build_without_annual_filing_or_cik(fresh):
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(TOTAL, BUSINESS, GEO), annual=False))
    assert segments.build("TEST")["status"] == "sin_dato"
    assert segments.build("NOPE")["reason"] == "no presenta estados en la SEC"


def test_build_is_cached_by_filing(fresh):
    calls = []
    base = fake_fetcher(instance(TOTAL, BUSINESS, GEO))

    def fetch(url, timeout):
        calls.append(url)
        return base(url, timeout)
    fresh.setattr(segments, "FETCHER", fetch)
    a = segments.build("TEST")
    n = len(calls)
    assert segments.build("TEST") == a and len([u for u in calls[n:] if u.endswith("_htm.xml")]) == 0


# ─────────────────────────── fixtures reales (capturados) ───────────────────────────
def _replay(fresh):
    import capture_segments
    fresh.setattr(segments, "FETCHER", capture_segments.replay_fetcher(FIX_DIR))


@pytest.mark.parametrize("sym", ["AAPL", "JPM", "XOM"])
def test_real_filings_have_segments(fresh, sym):
    _replay(fresh)
    r = segments.build(sym)
    assert r["status"] == "ok", r["reason"]
    assert len(r["segments"]) >= 2
    assert abs(sum(s["share_last"] for s in r["segments"]) - 1) < 1e-9


def test_real_aapl_products_or_regions(fresh):
    _replay(fresh)
    r = segments.build("AAPL")
    assert r["axis"] == "StatementBusinessSegmentsAxis" and r["reconciles"] is True
    assert {"Americas", "Europe", "Greater China"} <= {s["label"] for s in r["segments"]}
    assert r["secondary"]["axis"] == "StatementGeographicalAxis"
    products = next(o for o in r["others"] if o["axis"] == "ProductOrServiceAxis")
    assert {"iPhone", "Mac", "iPad", "Service"} <= {s["label"] for s in products["segments"]}
    assert "Products" not in {s["label"] for s in products["segments"]}     # el agregado sale


def test_real_non_sec_issuer_is_sin_dato(fresh):
    _replay(fresh)
    r = segments.build("MC.PA")
    assert r["status"] == "sin_dato" and r["reason"] == "no presenta estados en la SEC"


# ─────────────────────────── endpoint ───────────────────────────
def test_endpoint_returns_build_and_rejects_bad_symbols(fresh):
    import asyncio
    from fastapi import HTTPException
    import main
    _replay(fresh)
    r = asyncio.run(main.segments_v2_endpoint("pltr"))
    assert r["status"] == "ok" and [s["label"] for s in r["segments"]] == ["Government", "Commercial"]
    for bad in ("AAPL;rm", "ABCDEFGHIJK", "A/B"):
        with pytest.raises(HTTPException) as e:
            asyncio.run(main.segments_v2_endpoint(bad))
        assert e.value.status_code == 422


def test_labels_in_capitals_get_initial_capitals():
    """Revisión del PM (E3): una etiqueta toda en mayúsculas del XBRL pasa a mayúscula inicial por palabra; las siglas
    de config (US, UK, EU, EMEA, APAC…) se conservan y las palabras de enlace van en minúscula."""
    assert segments._clean_label("UNITED STATES") == "United States"
    assert segments._clean_label("CHINA") == "China"
    assert segments._clean_label("REST OF ASIA PACIFIC") == "Rest of Asia Pacific"
    assert segments._clean_label("EMEA") == "EMEA"
    assert segments._clean_label("US AND CANADA") == "US and Canada"
    assert segments._clean_label("NON-US") == "Non-US"
    assert segments._clean_label("Greater China") == "Greater China"       # con minúsculas: no se toca
    assert segments._clean_label("iPhone") == "iPhone"
    assert segments._clean_label("FPL SEGMENT") == "FPL"                  # sigla corta de una palabra: se deja
    assert segments._clean_label("NEER") == "NEER"


def test_summary_product_first_geography_second_top_and_falling(fresh):
    """V7 · P2 y P4: el resumen que pintan la historia (capítulo 2), Riesgos («Concentración») y el PDF, con los
    fixtures capturados de la SEC: hechos del informe anual, sin interpretación."""
    import capture_segments
    fresh.setattr(segments, "FETCHER", capture_segments.replay_fetcher())
    aapl = segments.summary(segments.build("AAPL"))
    assert aapl["fy"] == "2025" and aapl["prev_fy"] == "2024"
    assert aapl["first"]["axis"] == "ProductOrServiceAxis" and aapl["first"]["items"][0]["label"] == "iPhone"
    assert aapl["first"]["items"][0]["share_txt"] == "50%"
    assert aapl["second"]["axis"] == "StatementGeographicalAxis"
    assert aapl["top"]["label"] == "iPhone" and aapl["top"]["axis_label"] == "productos y servicios"
    assert [f["label"] for f in aapl["falling"]] == ["China"] and aapl["falling"][0]["change_txt"] == "−3.8%"
    assert aapl["text"] == ("En FY2025, iPhone aporta el 50% de sus ingresos, seguido de Service (26%) y "
                            "Wearables, Home and Accessories (8.6%).")
    assert aapl["second_text"] == "Por zonas geográficas: Other Countries 48%, United States 36%, China 15%."
    # sin eje de producto, el principal; la cobertura parcial se dice (BCS: solo comisiones)
    jpm = segments.summary(segments.build("JPM"))
    assert jpm["first"]["axis"] == "StatementBusinessSegmentsAxis" and jpm["second"]["axis"] == "StatementGeographicalAxis"
    bcs = segments.summary(segments.build("BCS"))
    assert "38%" in bcs["coverage_note"] and bcs["covers_total"] is False
    assert segments.summary({"status": "sin_dato", "segments": []}) is None


def test_endpoint_carries_the_summary(fresh):
    import asyncio
    import capture_segments
    import main
    fresh.setattr(segments, "FETCHER", capture_segments.replay_fetcher())
    out = asyncio.run(main.segments_v2_endpoint("AAPL"))
    assert out["status"] == "ok" and out["summary"]["top"]["label"] == "iPhone"


def test_product_view_puts_the_product_axis_first(fresh):
    """V7 · P4: el PDF pinta el desglose por producto si el emisor lo publica (Apple), y si no el eje principal."""
    import capture_segments
    fresh.setattr(segments, "FETCHER", capture_segments.replay_fetcher())
    aapl = segments.build("AAPL")
    view = segments.product_view(aapl)
    assert view["axis"] == "ProductOrServiceAxis" and view["axis_label"] == "productos y servicios"
    assert {s["label"] for s in view["segments"]} >= {"iPhone", "Service", "Mac", "iPad"}
    assert view["fiscal_years"] == aapl["fiscal_years"] and view["source"] == aapl["source"]
    jpm = segments.build("JPM")
    assert segments.product_view(jpm) is jpm
    assert segments.product_view(None) is None


def test_pdf_chapter_two_opens_with_the_segments(fresh):
    """V7 · P4: el capítulo 2 del PDF abre con la misma lectura que la web (producto y geografía) y pinta el desglose
    por producto; el DuPont ya no abre el capítulo (va en Calidad)."""
    import pdf_inspect as pi
    import pdf_v2_samples as S
    text = " ".join(" ".join(pi.page_texts(S.build("AAPL"))).split())
    ch2 = text[text.find("2 · CÓMO GANA DINERO"):text.find("3 · LA ACCIÓN")]
    assert ch2.startswith("2 · CÓMO GANA DINERO De dónde vienen sus ingresos En FY2025, iPhone aporta el 50% de sus "
                          "ingresos, seguido de Service (26%)")
    assert "Por zonas geográficas: Other Countries 48%, United States 36%, China 15%." in ch2
    assert "Productos y servicios · ejercicio 2025" in ch2 and "iPhone 50% · $209.59B" in ch2
    assert "DuPont" not in ch2


# ─────────────────────────── V6 (revisión de seguridad): B8, B9, B14 ───────────────────────────
def _pause(s):
    """`fresh` anula time.sleep (el ritmo de la SEC): las esperas de estos tests van con un Event."""
    import threading
    threading.Event().wait(s)


def _gzip_server(body, delay_per_chunk=0.0):
    import gzip
    import http.server
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            z = gzip.compress(body)
            self.send_response(200)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(z)))
            self.end_headers()
            step = max(len(z) // 8, 1)
            for i in range(0, len(z), step):
                self.wfile.write(z[i:i + step])
                self.wfile.flush()
                _pause(delay_per_chunk)

        def log_message(self, *a):
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_download_stops_at_max_bytes_even_if_gzip_inflates(fresh, tmp_path):
    """B14: un gzip pequeño que se infla (3 MB aquí) no pasa de `max_bytes` ya descomprimido."""
    srv = _gzip_server(b"a" * 3_000_000)
    try:
        fresh.setattr(edgar, "FETCHER", edgar.urllib_fetcher)
        with open(tmp_path / "out.xml", "w+b") as fh:
            with pytest.raises(edgar.Unavailable, match="supera"):
                edgar._get_to_file(f"http://127.0.0.1:{srv.server_port}/x", edgar.Budget(10.0), fh,
                                   max_bytes=1 << 20)
            assert fh.tell() <= 1 << 20
    finally:
        srv.shutdown()


def test_download_counts_the_budget_while_it_streams(fresh, tmp_path):
    """B14: la descarga entera cabe en el presupuesto (antes, el plazo solo valía por lectura de socket)."""
    import os
    srv = _gzip_server(os.urandom(4_000_000), delay_per_chunk=0.15)
    try:
        fresh.setattr(edgar, "FETCHER", edgar.urllib_fetcher)
        with open(tmp_path / "out.xml", "w+b") as fh:
            with pytest.raises(edgar.Unavailable, match="presupuesto"):
                edgar._get_to_file(f"http://127.0.0.1:{srv.server_port}/x", edgar.Budget(0.4), fh)
    finally:
        srv.shutdown()


def test_build_never_raises(fresh):
    """B14: un error inesperado (aquí, el parseo) es sin_dato con motivo genérico, no un 500."""
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(TOTAL, BUSINESS, GEO)))
    fresh.setattr(segments, "_from_filing", lambda *a: (_ for _ in ()).throw(KeyError("raro")))
    r = segments.build("TEST")
    assert r["status"] == "sin_dato" and r["reason"] == "no se pudieron leer los segmentos del informe anual"


def test_failures_are_remembered_and_one_query_per_symbol(fresh):
    """B8: un sin dato se recuerda `segments_fail_ttl_s`; consultas simultáneas del mismo símbolo, una sola."""
    import threading
    calls = []

    def slow(sym):
        calls.append(sym)
        _pause(0.2)
        return segments._empty("EDGAR caído")
    fresh.setattr(segments, "_build", slow)
    ts = [threading.Thread(target=segments.build, args=("TEST",)) for _ in range(6)]
    [t.start() for t in ts]
    [t.join(5) for t in ts]
    assert calls == ["TEST"]
    assert segments.build("TEST")["reason"] == "EDGAR caído" and calls == ["TEST"]


def test_at_most_n_queries_at_once(fresh):
    import threading
    from settings import cfg
    now, peak, lock = [0], [0], threading.Lock()

    def slow(sym):
        with lock:
            now[0] += 1
            peak[0] = max(peak[0], now[0])
        _pause(0.1)
        with lock:
            now[0] -= 1
        return segments._empty("x")
    fresh.setattr(segments, "_build", slow)
    ts = [threading.Thread(target=segments.build, args=(f"S{i}",)) for i in range(8)]
    [t.start() for t in ts]
    [t.join(5) for t in ts]
    assert peak[0] == cfg("market.segments.segments_concurrency")


def test_cached_has_no_network(fresh):
    """B9: `cached` (lo que usa el PDF dentro de su turno) solo lee la caché."""
    assert segments.cached("TEST") is None
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(TOTAL, BUSINESS, GEO)))
    r = segments.build("TEST")
    assert r["status"] == "ok" and segments.cached("test") == r


def test_last_annual_prefers_the_original_over_its_amendment():
    """V2 (fuentes reales): en el mismo ejercicio, el 10-K original antes que un 10-K/A posterior (CRCL: solo la Parte
    III); un ejercicio más reciente gana aunque sea una enmienda; sin fecha de periodo, la de presentación."""
    f = lambda form, filed, rep, acc: {"form": form, "filingDate": filed, "reportDate": rep, "accessionNumber": acc}  # noqa: E731
    orig, amend = f("10-K", "2026-03-09", "2025-12-31", "a"), f("10-K/A", "2026-07-13", "2025-12-31", "b")
    assert max([amend, orig], key=segments._annual_order) is orig
    newer = f("10-K/A", "2027-03-01", "2026-12-31", "c")
    assert max([orig, amend, newer], key=segments._annual_order) is newer
    assert max([f("20-F", "2025-04-01", None, "d"), f("20-F", "2026-04-01", None, "e")],
               key=segments._annual_order)["accessionNumber"] == "e"


def test_insurer_without_revenue_segments_uses_premiums(fresh):
    """V2 (decisión del PM): una aseguradora que desglosa primas y no ingresos (CB) tiene segmentos «Primas», con la
    cobertura frente a los ingresos consolidados (como BCS). Solo si es aseguradora: si no, sin_dato como antes."""
    xml = instance([400, 410, 420], BUSINESS, {}, concept="PremiumsEarnedNet", total_concept="Revenues")
    fresh.setattr(segments, "FETCHER", fake_fetcher(xml))
    assert segments.build("TEST")["status"] == "sin_dato"
    segments.reset()
    fresh.setattr(segments, "INSURER", lambda sym: True)
    r = segments.build("TEST")
    assert r["status"] == "ok" and r["concept"] == "PremiumsEarnedNet" and r["concept_label"] == "Primas"
    assert r["coverage"] == pytest.approx((178 + 111 + 64) / 420) and r["covers_total"] is False
    assert r["coverage_note"].startswith("Primas · cubren el 84%")


def test_insurer_with_revenue_segments_keeps_them(fresh):
    """Las primas son el último recurso: una aseguradora con ingresos por segmento (TRV, MET, BRK-B) no cambia."""
    fresh.setattr(segments, "FETCHER", fake_fetcher(instance(TOTAL, BUSINESS, GEO)))
    fresh.setattr(segments, "INSURER", lambda sym: True)
    assert segments.build("TEST")["concept_label"] == "Ingresos"


def test_segment_prefix_label_is_cleaned():
    assert segments._clean_label("Segment Life") == "Life"
    assert segments._clean_label("Segment Insurance Overseas General") == "Insurance Overseas General"
    assert segments._clean_label("Americas Segment") == "Americas" and segments._clean_label("Segment") == "Segment"
