"""
Rediseño E5 (Task 7): GET /api/v2/pdf/{symbol}. Mismo semáforo y mismo nombre de archivo que /api/pdf; usa la serie
de /api/v2/prices y, si falla, el informe sale igual y lo dice. /api/pdf no cambia.
"""
import re

import pytest

import pdf_inspect as pi
import pdf_v2_samples as S


class _Slots:
    """Doble de _ANALYSIS_SLOTS: cuenta los turnos y, al pedir uno, cuántos usuarios constan esperando."""

    def __init__(self):
        self.entered = 0
        self.waiting_seen = []

    def acquire(self):
        import main
        self.entered += 1
        self.waiting_seen.append(main._users_waiting())

    def release(self):
        pass

    def __enter__(self):
        self.acquire()

    def __exit__(self, *a):
        return False


@pytest.fixture
def patched(monkeypatch):
    import main
    slots = _Slots()
    monkeypatch.setattr(main, "_ANALYSIS_SLOTS", slots)
    monkeypatch.setattr(main, "_compute_analysis", lambda sym: S.analysis(sym))
    monkeypatch.setattr(main, "_prices_v2_payload", lambda sym, sector: S.prices(sym))
    # F10 · N5: sin cola ni Finnhub en estos tests (los rivales del PDF tienen los suyos en test_peers.py)
    import peers
    monkeypatch.setattr(peers, "start", lambda sym, analysis, client=None: None)
    monkeypatch.setattr(peers, "for_pdf", lambda sym, client=None: None)
    return main, slots


def test_route_is_registered():
    import main
    paths = {getattr(r, "path", None) for r in main.app.routes}
    assert "/api/v2/pdf/{symbol}" in paths and "/api/pdf/{symbol}" in paths


def test_pdf_v2_response(patched):
    main, slots = patched
    r = main._pdf_v2_response(" aapl ")
    assert slots.entered == 2           # F10 · N5: el análisis y el PDF, con la espera de los rivales entre los dos
    assert r.media_type == "application/pdf" and r.body.startswith(b"%PDF")
    assert re.fullmatch(r'attachment; filename="Informe Finanzer AAPL \d{4}-\d{2}-\d{2}\.pdf"',
                        r.headers["content-disposition"])
    texts = pi.page_texts(r.body)
    assert "Apple Inc." in texts[0] and "S&P 500" in texts[0]


def test_pdf_v2_waits_as_a_user(patched):
    """Verificación de la v4 (V4): el PDF nuevo pide su turno como usuario (main._slot): mientras espera, la cola de
    fondo (rivales y precalentado) no toma turnos. Antes entraba directo al semáforo y no contaba como esperando."""
    main, slots = patched
    main._pdf_v2_response("AAPL")
    assert slots.waiting_seen == [1, 1] and main._users_waiting() == 0


def test_pdf_v2_waits_for_rivals_outside_the_slot(patched, monkeypatch):
    """F10 · N5: la espera acotada de los rivales va entre los dos turnos, nunca dentro: mientras el PDF espera, la
    cola de fondo puede analizar a los rivales."""
    import peers
    main, slots = patched
    seen = []
    monkeypatch.setattr(peers, "start", lambda sym, analysis, client=None: seen.append(("start", slots.entered)))
    monkeypatch.setattr(peers, "for_pdf", lambda sym, client=None: seen.append(("espera", slots.entered)))
    main._pdf_v2_response("AAPL")
    assert seen == [("start", 1), ("espera", 1)] and slots.entered == 2


def test_without_price_series_the_report_still_comes_out(patched, monkeypatch):
    main, _ = patched

    def boom(sym, sector):
        raise RuntimeError("Yahoo caído")
    monkeypatch.setattr(main, "_prices_v2_payload", boom)
    r = main._pdf_v2_response("JPM")
    assert "la serie de precios no respondió" in " ".join(pi.page_texts(r.body)[0].split())


def test_an_etf_gets_the_reason_not_a_report(monkeypatch):
    """Verificación V1: SPY (un ETF) no tiene informe; /api/v2/pdf responde 422 con el motivo del motor, como /api/analysis."""
    import main
    import yf_adapter
    from fastapi import HTTPException
    monkeypatch.setattr(main, "_ANALYSIS_SLOTS", _Slots())
    monkeypatch.setattr(yf_adapter, "get_ticker_info", lambda sym: {"quoteType": "ETF"})
    with pytest.raises(HTTPException) as e:
        main._pdf_v2_response("spy")
    assert e.value.status_code == 422
    assert e.value.detail == main.not_a_stock_message("SPY", "ETF") and "SPY es un ETF" in e.value.detail


def test_rivals_ready_painted_and_missing_ones_named(patched, monkeypatch):
    """Revisión V6 (encargo del PM) y F10 · N5: el PDF nuevo pinta los rivales listos (peers.for_pdf, tras su espera
    acotada) y nombra los que faltan con su motivo; sin ninguno, una línea que dice por qué y remite a la web."""
    import analysis_queue as AQ
    import peers
    main, _ = patched
    monkeypatch.setattr(peers, "for_pdf", lambda sym, client=None: {
        "symbol": "AAPL", "rivals": [], "note": None, "industry": None, "ranked": False, "waited_s": 30})
    text = " ".join(" ".join(pi.page_texts(main._pdf_v2_response("AAPL").body)).split())
    assert "consulta la web" in text and "clasificación de sus rivales por tamaño" in text and "30 s" in text
    msft = S.analysis("MSFT")
    cached = {"symbol": "AAPL", "industry": "x", "note": None, "source": "automaticos", "ranked": True,
              "waited_s": 30,
              "rivals": [{"symbol": "MSFT", "status": "listo", "summary": AQ.summary(msft)},
                         {"symbol": "DELL", "status": "en_cola"},
                         {"symbol": "HPQ", "status": "fallo", "reason": "Yahoo respondió 500"}]}
    monkeypatch.setattr(peers, "for_pdf", lambda sym, client=None: cached)
    text = " ".join(" ".join(pi.page_texts(main._pdf_v2_response("AAPL").body)).split())
    assert "Rivales de la misma industria" in text and "(MSFT)" in text and "(DELL)" not in text
    assert "DELL: aún en cola" in text and "HPQ: no se pudo analizar (Yahoo respondió 500)" in text
    # V7 · P5: la propia empresa en la primera fila de la tabla, y «agregado», no «mediana»
    assert "(AAPL) · esta empresa" in text and text.index("esta empresa") < text.index("(MSFT)")
    assert "Frente al agregado de su referencia" in text and "mediana de su referencia" not in text
    # un fallo leyendo la caché nunca tumba el informe
    def boom(sym, client=None):
        raise RuntimeError("caché rota")
    monkeypatch.setattr(peers, "for_pdf", boom)
    assert main._pdf_v2_response("AAPL").body.startswith(b"%PDF")


def test_pdf_v2_takes_segments_only_from_cache(patched, monkeypatch):
    """V6 (B9): dentro del turno del análisis no se descargan segmentos (instancia XBRL): solo los de la caché."""
    import segments
    main, _ = patched
    monkeypatch.setattr(segments, "build", lambda sym: (_ for _ in ()).throw(AssertionError("descarga en el turno")))
    asked = []
    monkeypatch.setattr(segments, "cached", lambda sym: asked.append(sym))
    r = main._pdf_v2_response("AAPL")
    assert r.body.startswith(b"%PDF") and asked == ["AAPL"]
