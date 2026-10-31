"""V6 (revisión de código y seguridad del PM): la capa HTTP probada como la vería un atacante, con un uvicorn real y
`http.client` (el entorno no trae httpx). B1/B4: /api/v2/scenario valida el cuerpo (422 en milisegundos); B5: 413 por
encima de `max_body_bytes`."""
import copy
import glob
import http.client
import json
import socket
import threading
import time

import pytest

import main
import scenario
from settings import cfg

SI = {"status": "ok", "reason": None, "fcf": 100.0e9, "shares_outstanding": 10.0e9, "net_debt": 0.0, "price": 100.0,
      "currency": "USD", "base": {"high_growth_rate": 0.1, "high_growth_years": 5, "transition_years": 5,
                                  "terminal_growth": 0.025, "discount_rate": 0.09, "decay_type": "step"}}
FAST_S = 0.1


@pytest.fixture(scope="module")
def web():
    import uvicorn
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)

    def req(method, path, body=None, headers=None, raw=None, binary=False):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        h = {"Content-Type": "application/json", **(headers or {})}
        c.request(method, path, body=data, headers=h, encode_chunked="Transfer-Encoding" in h)
        r = c.getresponse()
        payload = r.read()
        out = r.status, (payload if binary else payload.decode("utf-8", "replace")), dict(r.getheaders())
        c.close()
        return out
    yield req
    server.should_exit = True
    th.join(timeout=5)


def _post(web, body):
    t0 = time.monotonic()
    st, text, _h = web("POST", "/api/v2/scenario", body)
    return st, text, time.monotonic() - t0


def test_scenario_ok_over_http(web):
    st, text, _ = _post(web, {"inputs": SI, "assumptions": {"discount_rate": 0.11}})
    assert st == 200 and json.loads(text)["status"] == "ok"


def _with(path, value):
    si = copy.deepcopy(SI)
    d = si
    for k in path[:-1]:
        d = d[k]
    if value is KeyError:
        del d[path[-1]]
    else:
        d[path[-1]] = value
    return si


BAD = {
    "años enormes (B1)": {"inputs": _with(("base", "high_growth_years"), 20_000_000)},
    "transición enorme": {"inputs": _with(("base", "transition_years"), 20_000_000)},
    "años negativos": {"inputs": _with(("base", "high_growth_years"), -1)},
    "años en el supuesto": {"inputs": SI, "assumptions": {"high_growth_years": 20_000_000}},
    "NaN (B4)": {"inputs": _with(("base", "discount_rate"), float("nan"))},
    "infinito": {"inputs": _with(("fcf",), float("inf"))},
    "NaN en el supuesto": {"inputs": SI, "assumptions": {"discount_rate": float("nan")}},
    "texto en vez de número": {"inputs": _with(("fcf",), "100")},
    "booleano": {"inputs": _with(("base", "high_growth_years"), True)},
    "lista": {"inputs": SI, "assumptions": {"high_growth_rate": [0.1]}},
    "clave de más": {"inputs": _with(("hack",), 1)},
    "clave de más en base": {"inputs": _with(("base", "x"), 1)},
    "clave de más en supuestos": {"inputs": SI, "assumptions": {"x": 1}},
    "clave de más arriba": {"inputs": SI, "otra": 1},
    "falta una clave de base": {"inputs": _with(("base", "discount_rate"), KeyError)},
    "falta base": {"inputs": _with(("base",), KeyError)},
    "sin inputs": {"assumptions": {}},
    "decay_type raro": {"inputs": _with(("base", "decay_type"), "exponential")},
    "acciones minúsculas": {"inputs": _with(("shares_outstanding",), 1e-9)},
    "acciones cero": {"inputs": _with(("shares_outstanding",), 0)},
    "importe enorme": {"inputs": _with(("fcf",), 1e300)},
    "tasa absurda": {"inputs": _with(("base", "high_growth_rate"), 1e6)},
    "texto largo": {"inputs": _with(("reason",), "x" * 5000)},
    "cuerpo que no es objeto": [1, 2, 3],
}


@pytest.mark.parametrize("case", list(BAD))
def test_bad_bodies_are_422_fast(web, case):
    body = BAD[case]
    if "NaN" in case or "infinito" in case:
        raw = json.dumps(body, allow_nan=True).encode()          # NaN / Infinity, como los mandaría un atacante
        t0 = time.monotonic()
        st, text, _h = web("POST", "/api/v2/scenario", raw=raw)
        dt = time.monotonic() - t0
    else:
        st, text, dt = _post(web, body)
    assert st == 422, (case, st, text[:200])
    assert dt < FAST_S, (case, dt)
    assert "Traceback" not in text


def test_engine_inputs_of_the_whole_panel_pass_and_give_the_same_value():
    """Lo que manda la web (scenario_inputs del análisis) pasa la validación y da exactamente lo mismo que antes."""
    n = 0
    for path in sorted(glob.glob("tests/golden/panel/*.json")):
        a = json.load(open(path, encoding="utf-8"))
        si = a.get("scenario_inputs")
        if not si:
            continue
        inputs, assumptions = scenario.parse_request({"inputs": si, "assumptions": {}})
        r = scenario.run(inputs, assumptions)
        if si.get("status") == "ok":
            assert r["clamped"] == [], path
            assert r == scenario.run(si, {}), path
            n += 1
    assert n >= 20


def test_base_from_the_client_is_clamped_like_the_assumptions():
    si = _with(("base", "high_growth_rate"), 0.9)
    inputs, assumptions = scenario.parse_request({"inputs": si})
    r = scenario.run(inputs, assumptions)
    assert r["assumptions_used"]["high_growth_rate"] == cfg("valuation.scenario.growth_max")
    assert "high_growth_rate" in r["clamped"]


def test_never_a_non_finite_value():
    import math
    si = _with(("fcf",), 1e15)
    si["shares_outstanding"] = 1e8
    si["price"] = 1e7
    r = scenario.run(*scenario.parse_request({"inputs": si}))
    for v in [r["fair_value"], r["upside"], *(x for row in r["sensitivity"]["values"] for x in row)]:
        assert v is None or math.isfinite(v)
    json.dumps(r, allow_nan=False)


def test_scenario_has_its_own_slots(monkeypatch):
    """B1: el cálculo pasa por un turno propio (`scenario_concurrency`), no por los de los análisis."""
    taken = []

    class Slots:
        def __enter__(self):
            taken.append(1)

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(main, "_SCENARIO_SLOTS", Slots())
    assert main.scenario_v2({"inputs": SI})["status"] == "ok" and taken == [1]


# ── B5: cuerpo máximo ──
def test_body_over_the_limit_is_413(web):
    big = {"inputs": SI, "pad": "x" * (cfg("data.server.max_body_bytes") + 10)}
    st, text, _h = web("POST", "/api/v2/scenario", big)
    assert st == 413 and "KB" in json.loads(text)["detail"]


def test_chunked_body_over_the_limit_is_413(web):
    """Sin Content-Length (chunked), se cuenta lo recibido."""
    st, text, _h = web("POST", "/api/v2/scenario", raw=iter([b"{" + b" " * 20000, b" " * 20000 + b"}"]),
                        headers={"Transfer-Encoding": "chunked"})
    assert st == 413, (st, text[:200])


def test_body_under_the_limit_passes(web):
    st, _text, _h = web("POST", "/api/v2/scenario", {"inputs": SI, "assumptions": {}})
    assert st == 200


# ── F23: cabeceras de seguridad ──
def test_security_headers_on_api_responses(web):
    st, _text, h = web("GET", "/api/health")
    h = {k.lower(): v for k, v in h.items()}
    assert st == 200 and h["x-content-type-options"] == "nosniff"
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"
    pol = h["content-security-policy"]
    assert "frame-ancestors 'none'" in pol and "script-src 'self'" in pol and "img-src 'self' https:" in pol


def test_html_gets_the_hashes_of_its_own_inline_scripts(web, tmp_path, monkeypatch):
    """En el HTML, script-src lleva el sha256 de cada script en línea del documento (el de tema de /v2 y los de Next);
    un script con src o de datos (JSON) no."""
    import base64
    import hashlib
    v2 = tmp_path / "v2"
    v2.mkdir()
    theme = "document.documentElement.dataset.theme='dark'"
    (v2 / "index.html").write_text(
        f"<html><head><script>{theme}</script><script src='/a.js'></script>"
        "<script type='application/ld+json'>{\"a\":1}</script></head><body><script>self.__next_f=[]</script>"
        "</body></html>", encoding="utf-8")
    monkeypatch.setattr(main, "_frontend_dir", str(tmp_path))
    st, text, h = web("GET", "/v2")
    pol = {k.lower(): v for k, v in h.items()}["content-security-policy"]
    want = ["'sha256-" + base64.b64encode(hashlib.sha256(x.encode()).digest()).decode() + "'"
            for x in (theme, "self.__next_f=[]")]
    script_src = next(d for d in pol.split("; ") if d.startswith("script-src"))
    assert st == 200 and theme in text
    assert script_src == "script-src 'self' " + " ".join(want)


def test_inline_script_hashes_of_the_real_build():
    """Con el `out/` compilado (si está): cada página con scripts en línea los lleva todos en la política."""
    import os
    import web_guard
    out = os.path.join(os.path.dirname(main.__file__), "..", "frontend", "out")
    pages = [p for p in ("index.html", "stock/index.html", "v2/index.html", "v2/_/index.html")
             if os.path.isfile(os.path.join(out, p))]
    if not pages:
        pytest.skip("sin frontend/out")
    for p in pages:
        html = open(os.path.join(out, p), "rb").read()
        n = html.count(b"<script>")
        assert len(web_guard.inline_script_hashes(html)) >= 1 and n >= 1, p


# ── B15: CORS solo fuera de Render ──
def test_cors_only_outside_render():
    import importlib
    import os
    import subprocess
    import sys
    code = ("import main; from starlette.middleware.cors import CORSMiddleware; "
            "print(any(m.cls is CORSMiddleware for m in main.app.user_middleware))")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {k: v for k, v in os.environ.items() if k != "RENDER_EXTERNAL_URL"}
    env["PYTHONPATH"] = os.pathsep.join([here, os.path.join(here, "lib")])
    local = subprocess.run([sys.executable, "-c", code], cwd=here, env=env, capture_output=True, text=True)
    render = subprocess.run([sys.executable, "-c", code], cwd=here, capture_output=True, text=True,
                            env={**env, "RENDER_EXTERNAL_URL": "https://finanzer.onrender.com"})
    assert local.stdout.strip().endswith("True"), local.stderr[-500:]
    assert render.stdout.strip().endswith("False"), render.stderr[-500:]


# ── B16: un 500 no enseña la excepción ──
def test_500_does_not_leak_the_exception(web, monkeypatch):
    def boom(sym):
        raise RuntimeError("/Users/secreto/ruta.py: clave=XYZ")
    monkeypatch.setattr(main, "_compute_analysis", boom)
    st, text, _h = web("GET", "/api/analysis/ZZZZ")
    assert st == 500 and "secreto" not in text
    from fastapi import HTTPException
    for fn in (main._pdf_response, main._pdf_v2_response):
        with pytest.raises(HTTPException) as e:
            fn("ZZZZ")
        assert e.value.status_code == 500 and e.value.detail == main.INTERNAL_ERROR


# ── B17: enlaces de titulares solo http(s) ──
def test_news_urls_only_http():
    import market_context as mc
    assert mc.safe_url("https://example.com/a") == "https://example.com/a"
    assert mc.safe_url("HTTP://example.com") == "HTTP://example.com"
    for bad in ("javascript:alert(1)", " JavaScript:alert(1)", "data:text/html,x", "//evil.com", "ftp://x", None,
                "https://" + "a" * 3000):
        assert mc.safe_url(bad) is None, bad


# ── V2 (fuentes reales): la clase con punto es la de Yahoo con guion ──
def test_dotted_share_class_is_the_yahoo_symbol(monkeypatch):
    """BF.B y BRK.B daban 404 "No data found" (en Yahoo son BF-B y BRK-B); BARC.L es una bolsa y no se toca."""
    import yf_adapter
    seen = []

    def stop(sym, *a, **k):
        seen.append(sym)
        raise RuntimeError("alto")
    monkeypatch.setattr(yf_adapter, "get_ticker_info", stop)
    monkeypatch.setattr(main.data_service, "get_complete_analysis_data", stop)
    for sym in ("bf.b", "BRK.B", "BARC.L"):
        try:
            main._compute_analysis(sym)
        except Exception:  # noqa: BLE001 — solo importa el símbolo que llegó a los datos
            pass
    assert main._v2_symbol("brk.b") == "BRK-B" and main._v2_symbol("BARC.L") == "BARC.L"
    assert seen and set(seen) == {"BF-B", "BRK-B", "BARC.L"} and "BF.B" not in seen


# ── V4 (encargo del PM): compresión gzip ──
def _hdr(h):
    return {k.lower(): v for k, v in h.items()}


def test_api_responses_are_gzipped_when_asked(web, monkeypatch):
    """Un JSON de más de gzip_minimum_bytes va comprimido si el cliente lo admite, y se descomprime en el mismo JSON."""
    import gzip
    series = {"symbol": "AAPL", "company": {"points": [{"t": f"2026-01-{i % 28 + 1:02d}", "c": 100.0 + i}
                                                       for i in range(500)]}}
    monkeypatch.setattr(main, "_prices_v2_payload", lambda sym, sector: series)
    st, plain, h0 = web("GET", "/api/v2/prices/AAPL", binary=True)
    st2, z, h = web("GET", "/api/v2/prices/AAPL", headers={"Accept-Encoding": "gzip"}, binary=True)
    assert len(plain) > cfg("data.server.gzip_minimum_bytes")
    assert st == st2 == 200 and "content-encoding" not in _hdr(h0)
    assert _hdr(h)["content-encoding"] == "gzip" and len(z) < len(plain)
    assert json.loads(gzip.decompress(z)) == json.loads(plain)


def test_small_responses_are_not_gzipped(web):
    st, _b, h = web("GET", "/api/health", headers={"Accept-Encoding": "gzip"})
    assert st == 200 and "content-encoding" not in _hdr(h)


def test_pdf_is_not_gzipped(web, monkeypatch):
    """Los PDF van tal cual (ya vienen comprimidos): ni CPU de más ni un PDF roto para el navegador."""
    from fastapi.responses import Response
    pdf = b"%PDF-1.4\n" + b"x" * 50_000
    monkeypatch.setattr(main, "_pdf_v2_response", lambda sym, client=None: Response(pdf, media_type="application/pdf"))
    st, b, h = web("GET", "/api/v2/pdf/AAPL", headers={"Accept-Encoding": "gzip"}, binary=True)
    assert st == 200 and "content-encoding" not in _hdr(h) and b == pdf


def test_gzipped_html_keeps_the_hashes_of_its_scripts(web, tmp_path, monkeypatch):
    """El HTML de /v2 va comprimido y la CSP sigue llevando el hash de su script (calculado sin comprimir)."""
    import base64
    import gzip
    import hashlib
    v2 = tmp_path / "v2"
    v2.mkdir()
    theme = "document.documentElement.dataset.theme='dark'"
    (v2 / "index.html").write_text(f"<html><head><script>{theme}</script></head><body>{'x' * 5000}</body></html>",
                                   encoding="utf-8")
    monkeypatch.setattr(main, "_frontend_dir", str(tmp_path))
    st, z, h = web("GET", "/v2", headers={"Accept-Encoding": "gzip"}, binary=True)
    hh = _hdr(h)
    want = "'sha256-" + base64.b64encode(hashlib.sha256(theme.encode()).digest()).decode() + "'"
    assert st == 200 and hh["content-encoding"] == "gzip" and theme in gzip.decompress(z).decode()
    assert want in hh["content-security-policy"]
