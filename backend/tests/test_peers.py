"""Rediseño E2b (Task 3): rivales automáticos y editables, analizados con el motor completo en segundo plano
(lib/peers.py). Sin red: universo y Damodaran sintéticos, capitalizaciones de fixture y un análisis falso."""
import json
import os
import threading
import time

import pytest

import analysis_queue as AQ
import industry_bench as IB
import peers
import universe
from settings import cfg

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(TESTS_DIR, "golden", "panel")


def golden(sym):
    with open(os.path.join(GOLDEN, f"{sym}.json"), encoding="utf-8") as fh:
        return json.load(fh)


UNIVERSE = """# GENERADO por tools/build_universe.py el 2026-10-17 desde https://example.org
symbol\tname\torigin\tgics_sector\tdamodaran_industry\tcik
AAPL\tApple\tsp500\tIT\tComputers/Peripherals\t320193
DELL\tDell\tsp500\tIT\tComputers/Peripherals\t1571996
HPQ\tHP\tsp500\tIT\tComputers/Peripherals\t47217
GOOGL\tAlphabet A\tsp500\tCS\tSoftware (Entertainment)\t1652044
GOOG\tAlphabet C\tsp500\tCS\tSoftware (Entertainment)\t1652044
"""
FIRMS = {"symbol": {"AAPL": ("Computers/Peripherals", "us"), "DELL": ("Computers/Peripherals", "us"),
                    "HPQ": ("Computers/Peripherals", "us"), "SMCI": ("Computers/Peripherals", "us"),
                    "LOGI": ("Computers/Peripherals", "europe"), "ZZZ": ("Computers/Peripherals", "us"),
                    "GOOGL": ("Software (Entertainment)", "us"), "BRK-A": ("Diversified", "us"),
                    "BRK-B": ("Diversified", "us"), "MKL": ("Diversified", "us")},
         "name": {}}


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    p = tmp_path / "universe.tsv"
    p.write_text(UNIVERSE, encoding="utf-8")
    monkeypatch.setattr(universe, "UNIVERSE_FILE", str(p))
    universe.reset()
    monkeypatch.setattr(IB, "_load_firms", lambda: FIRMS)
    import main  # noqa: F401  (conecta el motor real al importarse: cada test lo sustituye después)
    peers.reset()
    yield monkeypatch
    peers.reset()
    universe.reset()


# ─────────────────────────── candidatos y orden ───────────────────────────
def test_candidates_universe_first_without_self_or_other_classes(synthetic):
    assert peers.candidates("AAPL", "Computers/Peripherals", "us") == ["DELL", "HPQ", "SMCI", "ZZZ", "LOGI"]
    assert peers.candidates("GOOGL", "Software (Entertainment)", "us") == []            # GOOG: misma empresa
    assert peers.candidates("BRK-B", "Diversified", "us") == ["MKL"]                    # BRK-A: otra clase
    assert peers.candidates("AAPL", "Computers/Peripherals", None) == ["DELL", "HPQ", "LOGI", "SMCI", "ZZZ"]
    assert peers.candidates("AAPL", None, "us") == [] and peers.candidates("AAPL", "", "us") == []


def test_candidates_widen_to_other_regions_only_when_short(synthetic):
    """Con 5 o más en la propia región, nada de fuera; con menos, se añaden las demás regiones (LOGI, Europa)."""
    synthetic.setitem(peers._limits, "peers_count", 4)
    assert "LOGI" not in peers.candidates("AAPL", "Computers/Peripherals", "us")
    synthetic.setitem(peers._limits, "peers_count", 5)
    assert peers.candidates("AAPL", "Computers/Peripherals", "us") == ["DELL", "HPQ", "SMCI", "ZZZ", "LOGI"]


def test_rank_by_closeness_of_market_cap(synthetic):
    caps = {"AAPL": 3000e9, "DELL": 90e9, "HPQ": 30e9, "SMCI": 25e9, "ZZZ": None, "X1": 2500e9, "X2": 1e9}
    r = peers.rank("AAPL", ["DELL", "HPQ", "SMCI", "ZZZ", "X1", "X2"], caps)
    assert r["rivals"] == ["X1", "DELL", "HPQ", "SMCI", "X2"] and r["note"] is None
    r2 = peers.rank("AAPL", ["DELL", "ZZZ"], caps)
    assert r2["rivals"] == ["DELL"]                            # sin capitalización no entra
    assert r2["note"] == "menos de 3 comparables en su industria"


def test_rank_prefers_own_region_within_the_size_band(synthetic, tmp_path):
    """BCS (58 B$, Europa): dentro de la banda 1/3–3 veces, los bancos europeos primero (ING, SAN, BBVA) y después el
    resto por cercanía (NU, FITB…); HSBC (4,2 veces) queda fuera de la banda y va por cercanía con los demás."""
    p = tmp_path / "u.tsv"
    p.write_text("# GENERADO por tools/build_universe.py el 2026-10-17 desde x\n"
                 "symbol\tname\torigin\tgics_sector\tdamodaran_industry\tcik\tdamodaran_region\n"
                 + "".join(f"{s}\t{s}\t{o}\t\tBank (Money Center)\t{i}\t{r}\n" for i, (s, o, r) in enumerate([
                     ("FITB", "sp500", "us"), ("NU", "adr", "emerging"), ("PNC", "sp500", "us"),
                     ("BCS", "adr", "europe"), ("ING", "adr", "europe"), ("SAN", "adr", "europe"),
                     ("BBVA", "adr", "europe"), ("HSBC", "adr", "europe")])), encoding="utf-8")
    synthetic.setattr(universe, "UNIVERSE_FILE", str(p))
    universe.reset()
    caps = {"BCS": 58e9, "NU": 70e9, "FITB": 46e9, "PNC": 87e9, "ING": 83e9, "SAN": 170e9, "BBVA": 120e9,
            "HSBC": 244e9}
    r = peers.rank("BCS", ["FITB", "NU", "PNC", "ING", "SAN", "BBVA", "HSBC"], caps, "europe")
    assert r["rivals"] == ["ING", "BBVA", "SAN", "NU", "FITB"]
    assert peers.rank("BCS", ["FITB", "NU", "PNC", "ING"], caps)["rivals"] == ["NU", "FITB", "ING", "PNC"]  # sin región
    synthetic.setitem(peers._limits, "size_band_high", 2.0)            # BBVA (2,07 veces) sale de la banda
    assert peers.rank("BCS", ["NU", "ING", "SAN", "BBVA"], caps, "europe")["rivals"] == ["ING", "NU", "BBVA", "SAN"]
    assert peers.region_of("ING") == "europe" and peers.region_of("SMCI") == "us"     # universo / fila de Damodaran


def test_cap_lookups_universe_first_then_own_region(synthetic):
    """El tope de consultas no se gasta en cotizaciones locales sin capitalización: universo primero (su región
    delante) y después el resto."""
    order = peers.lookup_order(["DELL", "HPQ", "LOGI", "SMCI"], "europe")
    assert order == ["DELL", "HPQ", "LOGI", "SMCI"]                 # universo (DELL, HPQ) antes que LOGI (Europa)


def test_rank_without_own_cap_keeps_candidate_order(synthetic):
    r = peers.rank("AAPL", ["DELL", "HPQ", "SMCI"], {"DELL": 1.0})
    assert r["rivals"] == ["DELL", "HPQ", "SMCI"]


# ─────────────────────────── resumen compacto ───────────────────────────
@pytest.mark.parametrize("sym", ["AAPL", "JPM", "O", "MC.PA"])
def test_summary_has_same_figures_as_the_page(sym):
    a = golden(sym)
    s = peers.summary(a)
    comp = {i["key"]: i for g in a["display"]["charts"]["comparison"]["groups"] for i in g["items"]}
    # V4b: además del comparador, las columnas de la tabla de rivales (con la cifra de la página o con el motivo)
    assert set(comp) | {"market_cap"} <= set(s["metrics"]) <= set(comp) | {"market_cap"} | set(cfg("market.peers.summary_columns"))
    for k, item in comp.items():
        assert s["metrics"][k] == {"value": item["value"], "value_txt": item["value_txt"]}
    assert s["symbol"] == sym and s["name"] == a["profile"]["name"] and s["price"] == a["price"]
    assert s["quality"] == {"score": a["quality"]["score"], "level": a["quality"]["level"]}
    assert s["price_score"] == {"score": a["price_attractiveness"]["score"], "level": a["price_attractiveness"]["level"]}
    assert s["consistency"] == a["verdict"]["consistency"]
    assert s["metrics"]["market_cap"]["value"] == a["profile"]["market_cap"]
    assert len(json.dumps(s)) < 3000                       # compacto: no el análisis entero (memoria)
    ind = a["benchmark"]["industry"]
    assert s["reference"] == {"industry": ind["damodaran"], "region": ind.get("home_region") or ind["region"],
                              "basis": ind["basis"]}


def test_reference_of_an_adr_resolved_by_legal_name():
    """BCS: industry_bench.firm("BCS") es None (ADR), pero el análisis la resolvió por nombre legal y país."""
    import industry_bench
    assert industry_bench.firm("BCS") is None
    assert peers.reference(golden("BCS")) == {"industry": "Bank (Money Center)", "region": "europe",
                                              "basis": "industria"}
    assert peers.reference({"benchmark": {"industry": {"basis": "mercado", "damodaran": "Total Market"}}}) is None
    assert peers.reference({"benchmark": {"industry": None}}) is None


def test_summary_revenue_growth_is_the_page_row():
    """E3 (Rivales): la columna de crecimiento de ingresos es la fila "Crecimiento de ingresos (CAGR 3 años)"."""
    a = golden("AAPL")
    row = next(r for r in a["display"]["sections"]["growth"]["rows"] if r["key"] == "revenue_growth")
    m = peers.summary(a)["metrics"]["revenue_growth"]
    assert m["value_txt"] == row["value"] and m["value"] == pytest.approx(a["classification"]["inputs"]["revenue_cagr_3y"])


def test_summary_market_cap_text():
    assert peers.summary(golden("AAPL"))["metrics"]["market_cap"]["value_txt"] == "$5.01T"
    assert peers.summary(golden("MC.PA"))["metrics"]["market_cap"]["value_txt"].startswith("EUR ")   # como el motor


# ─────────────────────────── cola de análisis ───────────────────────────
class FakeEngine:
    def __init__(self, delay=0.05, fail=(), base=None, no_industry=()):
        self.base = base or {}
        self.no_industry = set(no_industry)
        self.calls = []
        self.delay = delay
        self.fail = set(fail)
        self.gate = threading.Event()
        self.gate.set()

    def __call__(self, sym):
        self.gate.wait(5)
        self.calls.append(sym)
        time.sleep(self.delay)
        if sym in self.fail:
            raise RuntimeError(f"{sym} sin datos")
        a = golden(self.base.get(sym, "AAPL"))
        a["symbol"] = sym
        if sym in self.no_industry:
            a["benchmark"] = {**a["benchmark"], "industry": None}
        return a


def wait_done(sym, rivals, timeout=5.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        r = peers.request(sym, rivals)
        if all(x["status"] in ("listo", "fallo") for x in r["rivals"]):
            return r
        time.sleep(0.02)
    raise AssertionError(r)


def test_queue_states_and_no_duplicates(synthetic):
    eng = FakeEngine()
    eng.gate.clear()
    synthetic.setattr(AQ, "ANALYZE", eng)
    r1 = peers.request("AAPL", ["DELL", "HPQ"])
    assert r1["status"] == "calculando" and r1["rivals"][1]["status"] == "en_cola"
    assert r1["rivals"][0]["status"] in ("en_cola", "analizando")      # el hilo puede haberlo tomado ya
    r2 = peers.request("MSFT", ["HPQ", "DELL"])
    assert {x["status"] for x in r2["rivals"]} <= {"en_cola", "analizando"}
    eng.gate.set()
    done = wait_done("AAPL", ["DELL", "HPQ"])
    assert done["status"] == "listo" and all(x["status"] == "listo" for x in done["rivals"])
    assert done["rivals"][0]["summary"]["symbol"] == "DELL"
    assert sorted(eng.calls) == ["DELL", "HPQ"]                  # cada rival, una sola vez
    assert done["poll_s"] == cfg("market.peers.poll_s")


def test_queue_state_goes_through_analizando(synthetic):
    eng = FakeEngine(delay=0.3)
    synthetic.setattr(AQ, "ANALYZE", eng)
    peers.request("AAPL", ["DELL"])
    seen = set()
    t0 = time.monotonic()
    while time.monotonic() - t0 < 3:
        st = peers.request("AAPL", ["DELL"])["rivals"][0]["status"]
        seen.add(st)
        if st == "listo":
            break
        time.sleep(0.01)
    assert {"analizando", "listo"} <= seen


def test_failure_is_reported_and_queue_keeps_working(synthetic):
    eng = FakeEngine(fail={"HPQ"})
    synthetic.setattr(AQ, "ANALYZE", eng)
    done = wait_done("AAPL", ["HPQ", "DELL"])
    hpq, dell = done["rivals"]
    assert hpq["status"] == "fallo" and "HPQ sin datos" in hpq["reason"]
    assert dell["status"] == "listo"


def test_queue_full_is_retried_not_fallo(synthetic):
    """V6 (B7): con la cola llena el rival no es "fallo" (la tabla quedaba lista y el cliente dejaba de preguntar):
    "en_cola" con `retry`, la respuesta sigue "calculando" y una consulta posterior lo encola."""
    eng = FakeEngine()
    eng.gate.clear()
    synthetic.setattr(AQ, "ANALYZE", eng)
    synthetic.setitem(AQ._limits, "max_queue", 2)
    r = peers.request("AAPL", ["A1", "A2", "A3", "A4"])
    last = r["rivals"][-1]
    assert r["status"] == "calculando" and "fallo" not in [x["status"] for x in r["rivals"]]
    assert last["status"] == "en_cola" and last["reason"] == "cola llena" and last["retry"] is True
    assert "A4" not in AQ._state                                  # sin estado guardado: se reintenta
    eng.gate.set()
    done = wait_done("AAPL", ["A1", "A2", "A3", "A4"])
    assert {x["status"] for x in done["rivals"]} == {"listo"}


def test_one_client_cannot_fill_the_queue(synthetic):
    """V6 (B7): un cliente tiene como mucho `max_per_client` trabajos esperando; otro cliente sigue entrando."""
    eng = FakeEngine()
    eng.gate.clear()
    synthetic.setattr(AQ, "ANALYZE", eng)
    synthetic.setitem(AQ._limits, "max_per_client", 3)
    r = peers.request("AAPL", ["B1", "B2", "B3", "B4", "B5"], client="1.1.1.1")
    retry = [x["symbol"] for x in r["rivals"] if x.get("retry")]
    assert len(retry) >= 1 and set(retry) <= {"B4", "B5"}
    other = peers.request("MSFT", ["C1"], client="2.2.2.2")
    assert other["rivals"][0]["status"] in ("en_cola", "analizando") and not other["rivals"][0].get("retry")
    eng.gate.set()
    wait_done("AAPL", ["B1", "B2", "B3", "B4", "B5"])
    assert AQ._by_client == {}                                    # al salir de la cola, el cupo se devuelve


def test_rivals_wait_while_users_wait(synthetic):
    eng = FakeEngine()
    busy = {"on": True}
    synthetic.setattr(AQ, "ANALYZE", eng)
    synthetic.setattr(AQ, "BUSY", lambda: busy["on"])
    synthetic.setitem(AQ._limits, "busy_wait_s", 0.02)
    peers.request("AAPL", ["DELL"])
    time.sleep(0.2)
    assert eng.calls == []                                      # hay usuarios esperando turno: el rival espera
    busy["on"] = False
    assert wait_done("AAPL", ["DELL"])["rivals"][0]["status"] == "listo"


def test_no_thread_until_first_request(synthetic):
    assert not AQ._workers
    synthetic.setattr(AQ, "ANALYZE", FakeEngine())
    peers.request("AAPL", ["DELL"])
    assert AQ._workers and all(t.daemon for t in AQ._workers)


# ─────────────────────────── automáticos (orden en segundo plano) ───────────────────────────
def _wait_auto(sym, timeout=5.0):
    t0 = time.monotonic()
    while True:
        r = peers.peers_for(sym)
        if r["status"] != "calculando":
            return r
        assert time.monotonic() - t0 < timeout, r
        time.sleep(0.02)


def test_automatic_peers_use_the_industry_of_the_analysis(synthetic):
    caps = {"AAPL": 3000e9, "DELL": 90e9, "HPQ": 30e9, "SMCI": 25e9, "ZZZ": 1e9}
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: caps.get(s))
    eng = FakeEngine()
    synthetic.setattr(AQ, "ANALYZE", eng)
    first = peers.peers_for("AAPL")
    assert first["status"] == "calculando" and first["rivals"] == [] and first["company"] is None
    r = _wait_auto("AAPL")
    assert eng.calls[0] == "AAPL"                              # primero, el análisis de la propia empresa
    r = wait_done("AAPL", [x["symbol"] for x in r["rivals"]]) and peers.peers_for("AAPL")
    assert [x["symbol"] for x in r["rivals"]] == ["DELL", "HPQ", "SMCI", "ZZZ"]
    assert r["industry"] == "Computers/Peripherals" and r["source"] == "automaticos" and r["note"] is None
    assert r["company"]["symbol"] == "AAPL" and r["company"]["reference"]["industry"] == "Computers/Peripherals"


def test_adr_peers_come_from_its_legal_name_industry(synthetic):
    """BCS: la industria sale de su análisis (Bank (Money Center), Europa), no del símbolo; nunca candidatos al azar."""
    fake_firms = {"symbol": {"BARC.L": ("Bank (Money Center)", "europe"), "HSBA.L": ("Bank (Money Center)", "europe"),
                             "ECHO": ("Semiconductor", "us")}, "name": {}}
    synthetic.setattr(IB, "_load_firms", lambda: fake_firms)
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: {"BCS": 58e9, "HSBA.L": 200e9}.get(s))
    synthetic.setattr(AQ, "ANALYZE", FakeEngine(base={"BCS": "BCS"}))
    r = _wait_auto("BCS")
    assert r["industry"] == "Bank (Money Center)"
    assert [x["symbol"] for x in r["rivals"]] == ["HSBA.L"] and r["note"] == peers.NOTE_FEW   # BARC.L (ella misma) no
    assert "ECHO" not in [x["symbol"] for x in r["rivals"]]


def test_company_without_reference_industry_has_no_automatic_peers(synthetic):
    synthetic.setattr(AQ, "ANALYZE", FakeEngine(no_industry={"NOPE"}))
    r = _wait_auto("NOPE")
    assert r["status"] == "sin_dato" and r["rivals"] == []
    assert r["note"] == "sin industria de referencia para proponer rivales (puedes añadirlos a mano)"


def test_company_that_cannot_be_analyzed_has_no_automatic_peers(synthetic):
    synthetic.setattr(AQ, "ANALYZE", FakeEngine(fail={"NOPE"}))
    r = _wait_auto("NOPE")
    assert r["status"] == "sin_dato" and r["rivals"] == [] and "NOPE sin datos" in r["note"]


def test_chosen_symbols_replace_automatic(synthetic):
    synthetic.setattr(AQ, "ANALYZE", FakeEngine())
    r = peers.peers_for("AAPL", ["MSFT", "DELL"])
    assert [x["symbol"] for x in r["rivals"]] == ["MSFT", "DELL"] and r["source"] == "elegidos"


# ─────────────────────────── endpoint ───────────────────────────
def test_endpoint_validates_symbols(synthetic):
    import asyncio
    from fastapi import HTTPException
    import main
    synthetic.setattr(AQ, "ANALYZE", FakeEngine())
    out = asyncio.run(main.peers_v2_endpoint("aapl", symbols="msft,dell"))
    assert [x["symbol"] for x in out["rivals"]] == ["MSFT", "DELL"]
    for bad in ("MSFT,DE LL", "A;B", ",".join(f"S{i}" for i in range(cfg("market.peers.peers_count") + 1)), ""):
        with pytest.raises(HTTPException) as e:
            asyncio.run(main.peers_v2_endpoint("AAPL", symbols=bad))
        assert e.value.status_code == 422


def test_main_wires_engine_and_user_priority():
    import main
    assert AQ.ANALYZE is not None and AQ.BUSY() is False
    assert main._users_waiting() == 0


def test_chosen_list_note_and_max(monkeypatch):
    """E3 (Rivales): la lista elegida a mano también avisa con menos de 3 comparables; la respuesta dice el máximo."""
    monkeypatch.setattr(peers, "request", lambda sym, rivals, note=None, client=None: {"status": "listo", "symbol": sym,
                        "rivals": [], "note": note, "poll_s": 4, "max_symbols": cfg("market.peers.peers_count")})
    r = peers.peers_for("AAPL", ["MSFT", "GOOGL"])
    assert r["note"] == peers.NOTE_FEW_CHOSEN and r["max_symbols"] == cfg("market.peers.peers_count")
    assert peers.peers_for("AAPL", ["MSFT", "GOOGL", "META"])["note"] is None


def test_cached_for_reads_the_cache_without_queueing(synthetic):
    """Revisión V6 (encargo del PM): el PDF nuevo lee los rivales de la caché compartida sin encolar nada; sin
    clasificación hecha, None (el informe lo dice en una línea)."""
    caps = {"AAPL": 3000e9, "DELL": 90e9, "HPQ": 30e9, "SMCI": 25e9, "ZZZ": 1e9}
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: caps.get(s))
    eng = FakeEngine()
    synthetic.setattr(AQ, "ANALYZE", eng)
    assert peers.cached_for("AAPL") is None
    assert AQ.stats()["user"] == 0 and not AQ._workers and eng.calls == []      # no encoló ni arrancó nada
    r = _wait_auto("AAPL")
    wait_done("AAPL", [x["symbol"] for x in r["rivals"]])
    c = peers.cached_for("AAPL")
    assert [x["symbol"] for x in c["rivals"]] == ["DELL", "HPQ", "SMCI", "ZZZ"]
    assert all(x["status"] == "listo" and x["summary"]["symbol"] == x["symbol"] for x in c["rivals"])
    assert c["industry"] == "Computers/Peripherals"
    n = len(eng.calls)
    peers.cached_for("AAPL")
    assert len(eng.calls) == n                                                     # leer no analiza otra vez


def test_pe_out_of_range_is_not_meaningful_in_the_summary():
    """V7 · P5: un P/E por encima de [peers] pe_meaningful_max (CRWD, 4366x) sale «n. s.» con la cifra en la nota; uno
    normal (AAPL) no cambia."""
    from settings import cfg
    crwd = AQ.summary(golden("CRWD"))["metrics"]["pe"]
    assert crwd["value"] > cfg("market.peers.pe_meaningful_max")
    assert crwd["value_txt"] == "n. s." and "4366" in crwd["note"] and "no es significativo" in crwd["note"]
    aapl = AQ.summary(golden("AAPL"))["metrics"]["pe"]
    assert aapl["value_txt"].endswith("x") and "note" not in aapl


# ─────────────────────────── V6 (revisión de seguridad): B3, B10, B11 ───────────────────────────
def test_failed_company_ranking_is_kept_only_fail_ttl(synthetic):
    """B3: si el análisis de la propia empresa falló, el ranking vacío se recuerda `fail_ttl_s`, no 7 días."""
    synthetic.setattr(AQ, "ANALYZE", FakeEngine(fail={"NOPE"}))
    _wait_auto("NOPE")
    t, _res, ttl = peers._rankings["NOPE"]
    assert ttl == cfg("market.peers.fail_ttl_s") < cfg("market.peers.caps_ttl_s")
    peers._rankings["NOPE"] = (t - ttl - 1, _res, ttl)            # pasado ese plazo, se vuelve a calcular
    assert peers.peers_for("NOPE")["status"] == "calculando"


def test_ranking_without_own_cap_is_kept_only_fail_ttl(synthetic):
    caps = {"DELL": 90e9, "HPQ": 30e9}                              # Finnhub no dio la de AAPL
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: caps.get(s))
    synthetic.setattr(AQ, "ANALYZE", FakeEngine())
    _wait_auto("AAPL")
    assert peers._rankings["AAPL"][2] == cfg("market.peers.fail_ttl_s")


def test_good_ranking_is_kept_seven_days(synthetic):
    caps = {"AAPL": 3000e9, "DELL": 90e9, "HPQ": 30e9}
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: caps.get(s))
    synthetic.setattr(AQ, "ANALYZE", FakeEngine())
    _wait_auto("AAPL")
    assert peers._rankings["AAPL"][2] == cfg("market.peers.caps_ttl_s")


def test_missing_cap_is_retried_after_fail_ttl(synthetic):
    """B3: una capitalización None (Finnhub caído o sin dato) no se guarda 7 días."""
    calls = []
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: calls.append(s))
    assert peers._cap("DELL") is None and peers._cap("DELL") is None and calls == ["DELL"]
    t, v, ttl = peers._caps["DELL"]
    assert ttl == cfg("market.peers.fail_ttl_s")
    peers._caps["DELL"] = (t - ttl - 1, v, ttl)
    peers._cap("DELL")
    assert calls == ["DELL", "DELL"]


def test_caps_and_rankings_are_bounded(synthetic):
    """B10: las cachés de capitalizaciones y rankings tienen tope."""
    synthetic.setitem(peers._limits, "caps_cache_max", 5)
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: 1e9)
    for i in range(12):
        peers._cap(f"S{i}")
    assert list(peers._caps) == [f"S{i}" for i in range(7, 12)]
    synthetic.setitem(peers._limits, "rankings_cache_max", 3)
    synthetic.setattr(AQ, "summary_for", lambda sym, stop: (None, "sin datos"))
    for i in range(6):
        peers._rank_now(f"R{i}", threading.Event())
    assert list(peers._rankings) == ["R3", "R4", "R5"]


def test_concurrent_requests_launch_one_ranking(synthetic):
    """B11: dos consultas a la vez de la misma empresa encolan un solo ranking (mirar y marcar, en una sección)."""
    submits = []
    gate = threading.Event()

    def submit(sym, fn, prio, client=None):
        submits.append(sym)
        gate.wait(2)
        return True
    synthetic.setattr(AQ, "submit", submit)
    ts = [threading.Thread(target=peers.peers_for, args=("AAPL",)) for _ in range(8)]
    [t.start() for t in ts]
    time.sleep(0.2)
    gate.set()
    [t.join(5) for t in ts]
    assert submits == ["AAPL"]


def test_norm_symbol_only_converts_known_share_classes():
    """B6: BRK.B → BRK-B (clase), pero BARC.L, MC.PA o 7203.T son bolsas y conservan su punto."""
    assert universe.norm_symbol(" brk.b ") == "BRK-B" and universe.norm_symbol("BF.B") == "BF-B"
    assert universe.norm_symbol("BRK-B") == "BRK-B" and universe.norm_symbol("aapl") == "AAPL"
    for sym in ("BARC.L", "MC.PA", "7203.T", "SHOP.TO", "HSBA.L"):
        assert universe.norm_symbol(sym) == sym
    assert universe.norm_symbol(None) == "" and universe.norm_symbol(".B") == ".B"


def test_endpoint_passes_the_client(synthetic):
    """B7: el endpoint pasa quién pide (cabecera del proxy o IP del socket) a la cola."""
    import asyncio
    import main
    seen = []
    synthetic.setattr(peers, "peers_for", lambda sym, chosen, client=None: seen.append(client) or {})

    class Req:
        def __init__(self, headers, host):
            self.headers = headers
            self.client = type("C", (), {"host": host})()
    asyncio.run(main.peers_v2_endpoint("AAPL", None, Req({"cf-connecting-ip": "9.9.9.9"}, "10.0.0.1")))
    asyncio.run(main.peers_v2_endpoint("AAPL", None, Req({}, "10.0.0.1")))
    assert seen == ["9.9.9.9", "10.0.0.1"]


# ─────────────────────────── V2 (decisión del PM): rival que la fuente ya no tiene ───────────────────────────
class GoneEngine(FakeEngine):
    """ACLX y ZZZ ya no están en Yahoo («No data found»); OTHER falla por otra cosa."""

    def __call__(self, sym):
        if sym in ("ACLX", "ZZZ"):
            self.calls.append(sym)
            raise RuntimeError(f"No data found for {sym}")
        if sym == "OTHER":
            self.calls.append(sym)
            raise RuntimeError("Yahoo respondió 500")
        return super().__call__(sym)


def _auto(synthetic, caps, engine):
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: caps.get(s))
    synthetic.setattr(AQ, "ANALYZE", engine)
    synthetic.setitem(peers._limits, "peers_count", 2)
    r = _wait_auto("AAPL")
    t0 = time.monotonic()
    while time.monotonic() - t0 < 5:
        r = peers.peers_for("AAPL")
        if r["status"] == "listo":
            return r
        time.sleep(0.02)
    raise AssertionError(r)


def test_gone_rival_is_replaced_by_the_next_in_the_ranking(synthetic):
    """ACLX (Yahoo ya no lo tiene) se cambia por el siguiente del ranking y la nota lo dice."""
    synthetic.setattr(IB, "_load_firms", lambda: {"symbol": {
        "AAPL": ("Computers/Peripherals", "us"), "DELL": ("Computers/Peripherals", "us"),
        "ACLX": ("Computers/Peripherals", "us"), "HPQ": ("Computers/Peripherals", "us"),
        "SMCI": ("Computers/Peripherals", "us")}, "name": {}})
    caps = {"AAPL": 3000e9, "DELL": 90e9, "ACLX": 80e9, "HPQ": 30e9, "SMCI": 25e9}
    r = _auto(synthetic, caps, GoneEngine())
    assert [x["symbol"] for x in r["rivals"]] == ["DELL", "HPQ"]
    assert {x["status"] for x in r["rivals"]} == {"listo"}
    assert "sustituidos (la fuente ya no los tiene): ACLX → HPQ" in r["note"]


def test_at_most_two_substitutions_and_only_for_no_data(synthetic):
    synthetic.setattr(IB, "_load_firms", lambda: {"symbol": {s: ("Computers/Peripherals", "us") for s in (
        "AAPL", "ACLX", "ZZZ", "OTHER", "HPQ", "SMCI", "DELL")}, "name": {}})
    caps = {"AAPL": 3000e9, "ACLX": 90e9, "OTHER": 85e9, "ZZZ": 80e9, "HPQ": 30e9, "SMCI": 25e9, "DELL": 1e9}
    synthetic.setitem(peers._limits, "max_substitutions", 2)
    r = _auto(synthetic, caps, GoneEngine())
    # ranking: ACLX, OTHER | reserva: ZZZ, HPQ. ACLX → ZZZ (tampoco existe) → HPQ: dos sustituciones, el tope
    assert [(x["symbol"], x["status"]) for x in r["rivals"]] == [("HPQ", "listo"), ("OTHER", "fallo")]
    assert "ACLX → ZZZ; ZZZ → HPQ" in r["note"]               # OTHER falló por otra cosa: se queda, con su motivo


def test_chosen_list_is_never_substituted(synthetic):
    synthetic.setattr(AQ, "ANALYZE", GoneEngine())
    t0 = time.monotonic()
    while time.monotonic() - t0 < 5:
        r = peers.peers_for("AAPL", ["ACLX", "DELL"])
        if r["status"] == "listo":
            break
        time.sleep(0.02)
    assert [x["symbol"] for x in r["rivals"]] == ["ACLX", "DELL"] and r["rivals"][0]["status"] == "fallo"


# ─────────────────────────── V4b: auditoría de información faltante ───────────────────────────
def test_summary_keeps_why_a_rival_column_has_no_figure():
    """V4b (b): las columnas del comparador sin cifra decían «Sin dato» aunque el análisis sabía el motivo (no aplica a
    su tipo de empresa, o no es significativa). El resumen lo lleva en `value_txt` y `note`, como el «n. s.» del P/E."""
    asml = AQ.summary(golden("ASML"))["metrics"]                       # cíclica, con caja neta
    assert asml["pe"]["value"] is None and asml["pe"]["value_txt"] == "No aplica"
    assert asml["pe"]["note"].startswith("No aplica a empresas cíclicas")
    assert asml["de"]["value"] is None and asml["de"]["value_txt"] == "n. s."
    assert "caja neta" in asml["de"]["note"] and "0.13x" in asml["de"]["note"]
    jpm = AQ.summary(golden("JPM"))["metrics"]                         # banco
    for k in ("ev_ebitda", "roic", "de"):
        assert jpm[k]["value"] is None and jpm[k]["value_txt"] == "No aplica" and jpm[k]["note"]
    assert "banco" in jpm["de"]["note"].lower() or "financiera" in jpm["de"]["note"].lower()
    o = AQ.summary(golden("O"))["metrics"]                             # REIT: su crecimiento es el retorno total
    assert o["revenue_growth"]["value_txt"] == "No aplica" and "retorno total" in o["revenue_growth"]["note"]
    # lo que ya salía del comparador no cambia
    aapl = AQ.summary(golden("AAPL"))["metrics"]
    assert "note" not in aapl["roic"] and aapl["roic"]["value_txt"].endswith("%")


@pytest.mark.parametrize("sym", sorted(f[:-5] for f in os.listdir(GOLDEN) if f.endswith(".json")))
def test_every_rival_column_has_a_figure_or_a_reason(sym):
    """V4b: en el panel, ninguna columna de la tabla de rivales queda en «Sin dato» sin motivo."""
    a = golden(sym)
    if "display" not in a:
        pytest.skip("golden sin análisis completo")
    m = AQ.summary(a)["metrics"]
    for k in cfg("market.peers.summary_columns"):
        assert k in m, f"{sym}: {k} sin cifra ni motivo"
        assert m[k]["value"] is not None or m[k].get("note"), f"{sym}: {k} sin cifra ni motivo"


@pytest.mark.parametrize("sym", sorted(f[:-5] for f in os.listdir(GOLDEN) if f.endswith(".json")))
def test_rival_growth_value_is_the_figure_it_shows(sym):
    """V4b: la columna de crecimiento llevaba como `value` la CAGR agregada de 3 años y como texto la cifra que puntúa
    (ciclo medio en una cíclica, por acción si hay emisión): FCX +4.4% con el texto −7.39%. Ahora las dos son la de
    la fila de la página."""
    a = golden(sym)
    if "display" not in a:
        pytest.skip("golden sin análisis completo")
    m = AQ.summary(a)["metrics"].get("revenue_growth") or {}
    if m.get("value") is None or not str(m.get("value_txt", "")).endswith("%"):
        return
    assert m["value"] * 100 == pytest.approx(float(m["value_txt"].rstrip("%")), abs=0.006), m


# ─────────────────────────── F10 · N5: rivales con el análisis y en el PDF ───────────────────────────
CAPS = {"AAPL": 3000e9, "DELL": 90e9, "HPQ": 30e9, "SMCI": 25e9, "ZZZ": 1e9}


def _settled(sym, timeout=5.0):
    """Espera sin consultar peers_for (que encola): solo lee la caché, como un PDF sin web abierta."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        c = peers.cached_for(sym)
        if c and c["rivals"] and all(x["status"] in ("listo", "fallo") for x in c["rivals"]):
            return c
        time.sleep(0.02)
    raise AssertionError(peers.cached_for(sym))


def test_the_ranking_queues_its_rivals_without_another_request(synthetic):
    """NVDA (revisión del 28-oct): los rivales esperaban a la siguiente consulta de la página Rivales; sin ella, el
    PDF no los tenía nunca. Con el ranking hecho, van a la cola enseguida."""
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: CAPS.get(s))
    eng = FakeEngine()
    synthetic.setattr(AQ, "ANALYZE", eng)
    peers.peers_for("AAPL")                                      # una sola consulta
    c = _settled("AAPL")
    assert [x["symbol"] for x in c["rivals"]] == ["DELL", "HPQ", "SMCI", "ZZZ"]
    assert all(x["status"] == "listo" for x in c["rivals"])


def test_start_with_the_analysis_reuses_it_and_launches_the_rivals(synthetic):
    """El análisis que se sirve al usuario deja su resumen en la cola (la clasificación no lo repite) y pone en marcha
    a sus rivales con prioridad `user`."""
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: CAPS.get(s))
    eng = FakeEngine()
    synthetic.setattr(AQ, "ANALYZE", eng)
    own = golden("AAPL")
    peers.start("aapl", own)
    c = _settled("AAPL")
    assert "AAPL" not in eng.calls and sorted(eng.calls) == ["DELL", "HPQ", "SMCI", "ZZZ"]
    assert AQ.cached("AAPL")["symbol"] == "AAPL" and c["industry"] == "Computers/Peripherals"


def test_start_can_be_switched_off(synthetic):
    eng = FakeEngine()
    synthetic.setattr(AQ, "ANALYZE", eng)
    synthetic.setitem(peers._limits, "start_with_analysis", False)
    peers.start("AAPL", golden("AAPL"))
    assert AQ.cached("AAPL") is None and not AQ._workers and peers.cached_for("AAPL") is None


def test_pdf_waits_a_bounded_time_and_says_how_long(synthetic):
    """El PDF espera como mucho `pdf_wait_s`: con los rivales listos dentro del plazo, los trae; si no, sale con lo
    que haya y cuánto esperó. Con todo listo, no espera."""
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: CAPS.get(s))
    eng = FakeEngine()
    synthetic.setattr(AQ, "ANALYZE", eng)
    synthetic.setitem(peers._limits, "pdf_poll_s", 0.02)
    r = peers.for_pdf("AAPL")
    assert r["ranked"] and [x["status"] for x in r["rivals"]] == ["listo"] * 4
    slept = []
    r = peers.for_pdf("AAPL", sleep=slept.append)
    assert slept == [] and r["waited_s"] == 0                    # ya estaban: ni un segundo


def test_pdf_wait_is_capped_and_reports_the_ranking_missing(synthetic):
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: CAPS.get(s))
    eng = FakeEngine()
    eng.gate.clear()                                             # el motor no termina mientras el PDF espera
    synthetic.setattr(AQ, "ANALYZE", eng)
    synthetic.setitem(peers._limits, "pdf_wait_s", 1)
    synthetic.setitem(peers._limits, "pdf_poll_s", 0.05)
    t0 = time.monotonic()
    r = peers.for_pdf("AAPL")
    assert time.monotonic() - t0 < 2 and r == {"symbol": "AAPL", "rivals": [], "note": None, "industry": None,
                                               "source": "automaticos", "ranked": False, "waited_s": 1}
    eng.gate.set()


def test_analysis_endpoint_starts_the_rivals(synthetic):
    """main: /api/analysis pone en marcha los rivales de la empresa con quien pide (su cupo de la cola)."""
    import asyncio
    import main
    seen = []
    synthetic.setattr(main, "_compute_limited", lambda sym: {"symbol": sym})
    synthetic.setattr(peers, "start", lambda sym, analysis, client=None: seen.append((sym, analysis, client)))

    class Req:
        headers = {}
        client = type("C", (), {"host": "10.0.0.2"})()
    assert asyncio.run(main.analyze_stock("NVDA", Req())) == {"symbol": "NVDA", "logo": None}   # logotipo: lib/logos.py
    assert seen == [("NVDA", {"symbol": "NVDA"}, "10.0.0.2")]
    synthetic.setattr(peers, "start", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("cola rota")))
    assert asyncio.run(main.analyze_stock("NVDA", Req())) == {"symbol": "NVDA", "logo": None}   # logotipo: lib/logos.py     # nunca rompe el análisis



# ─────────────────────────── PDF rápido: capitalizaciones en una sola petición ───────────────────────────
def test_caps_come_in_one_batch_and_finnhub_only_for_the_missing(synthetic):
    """El ranking pide las capitalizaciones de todos los candidatos en una sola petición (Yahoo, `CAPS_BATCH`); Finnhub
    (de uno en uno, con su pausa) solo para las que no trae. Antes: 12 capitalizaciones de Finnhub para HD, 16,7 s."""
    caps = {"AAPL": 3000e9, "DELL": 90e9, "HPQ": 30e9, "SMCI": 25e9, "ZZZ": 1e9}
    asked, finnhub = [], []
    synthetic.setattr(peers, "CAPS_BATCH", lambda syms: (asked.append(list(syms)),
                                                         {s: caps[s] for s in syms if s in caps and s != "ZZZ"})[1])
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: (finnhub.append(s), caps.get(s))[1])
    synthetic.setattr(AQ, "ANALYZE", FakeEngine())
    r = _wait_auto("AAPL")
    assert len(asked) == 1 and asked[0][0] == "AAPL" and set(asked[0]) >= {"DELL", "HPQ", "SMCI", "ZZZ"}
    assert sorted(finnhub) == ["LOGI", "ZZZ"]                  # solo las que no trajo (LOGI no tiene en ninguna)
    assert [x["symbol"] for x in r["rivals"]] == ["DELL", "HPQ", "SMCI", "ZZZ"]   # el mismo orden que con Finnhub


def test_caps_batch_failure_falls_back_to_finnhub(synthetic):
    caps = {"AAPL": 3000e9, "DELL": 90e9, "HPQ": 30e9, "SMCI": 25e9, "ZZZ": 1e9}
    finnhub = []

    def down(syms):
        raise RuntimeError("Yahoo no responde")
    synthetic.setattr(peers, "CAPS_BATCH", down)
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: (finnhub.append(s), caps.get(s))[1])
    synthetic.setattr(AQ, "ANALYZE", FakeEngine())
    r = _wait_auto("AAPL")
    assert set(finnhub) >= {"AAPL", "DELL", "HPQ", "SMCI", "ZZZ"}
    assert [x["symbol"] for x in r["rivals"]] == ["DELL", "HPQ", "SMCI", "ZZZ"]


def test_yahoo_caps_only_in_dollars():
    """La capitalización de Yahoo va en la moneda de la cotización: solo vale la que está en dólares. Una cotizada en
    otra moneda queda sin capitalización sin preguntar a Finnhub (que no da las de fuera de EE. UU.)."""
    resp = {"quoteResponse": {"result": [
        {"symbol": "HD", "marketCap": 390e9, "currency": "USD"},
        {"symbol": "KER.PA", "marketCap": 30e9, "currency": "EUR"},
        {"symbol": "SNBR", "currency": "USD"},
        {"symbol": "TSM", "marketCap": 1.5e12, "currency": "USD"},
    ]}}
    assert peers.caps_from_quote(resp) == {"HD": 390e9, "KER.PA": None, "TSM": 1.5e12}   # SNBR: sin cifra, a Finnhub
    assert peers.caps_from_quote({}) == {} and peers.caps_from_quote({"quoteResponse": None}) == {}


def test_quoted_in_another_currency_does_not_ask_finnhub(synthetic):
    """MC.PA tardaba lo mismo que antes: sus candidatos europeos (en euros en Yahoo) iban a Finnhub de uno en uno, con
    su pausa, para no recibir nada. Ahora quedan sin capitalización sin esa espera (el mismo resultado)."""
    finnhub = []
    synthetic.setattr(peers, "CAPS_BATCH", lambda syms: {s: (3000e9 if s == "AAPL" else None) for s in syms})
    synthetic.setattr(peers, "CAPS_FETCHER", lambda s: finnhub.append(s))
    synthetic.setattr(AQ, "ANALYZE", FakeEngine())
    _wait_auto("AAPL")
    assert finnhub == []
