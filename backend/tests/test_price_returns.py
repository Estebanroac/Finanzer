"""
Revisión V6 (F1): rentabilidad por periodo, base 100 y marcas en el backend (lib/price_returns), una sola
implementación para la web (/api/v2/prices) y el PDF nuevo: los mismos números en los dos.
"""
from datetime import date, timedelta

import pandas as pd
import pytest

import pdf_inspect as pi
import pdf_v2_samples as S
import price_returns as PR
from pdf_v2 import parts as P


def _serie(start: date, n: int, c0=100.0, step=1.0, div_every=None, symbol="X"):
    pts, a, c = [], c0, c0
    for i in range(n):
        d = start + timedelta(days=i)
        pts.append({"t": d.isoformat(), "c": c, "a": a, "v": 1.0})
        c += step
        a += step * 1.01      # el ajustado sube un poco más (dividendos)
    return {"symbol": symbol, "status": "ok", "points": pts, "events": []}


def test_ranges_come_from_config():
    keys = [r["key"] for r in PR.ranges()]
    assert keys == ["1S", "1M", "3M", "6M", "YTD", "1A", "3A", "5A"]
    assert all(r["label"] for r in PR.ranges())


def test_returns_price_and_total_text_and_tone():
    end = date(2026, 10, 16)
    s = _serie(end - timedelta(days=400), 401)
    out = PR.returns({"company": s})["company"]
    one = out["1A"]
    first = next(p for p in s["points"] if p["t"] >= (end - timedelta(days=365)).isoformat())
    last = s["points"][-1]
    assert one["price"] == pytest.approx(last["c"] / first["c"] - 1)
    assert one["total"] == pytest.approx(last["a"] / first["a"] - 1)
    assert one["total"] > one["price"] > 0
    assert one["price_txt"] == PR.fmt(one["price"]) and one["total_txt"].startswith("+") and one["tone"] == "pos"
    # 3 años no están cubiertos (la serie empieza hace 400 días): sin dato, nunca la cifra de un periodo más corto
    assert out["3A"] == {"price": None, "total": None, "price_txt": "—", "total_txt": "—",
                         "price_tone": "neutral", "tone": "neutral"}


def test_fmt_and_tone():
    assert PR.fmt(0.1234) == "+12.3%" and PR.fmt(-0.05) == "−5.0%" and PR.fmt(0) == "0.0%" and PR.fmt(None) == "—"
    assert (PR.tone(0.1), PR.tone(-0.1), PR.tone(0), PR.tone(None)) == ("pos", "neg", "neutral", "neutral")


def test_ytd_starts_on_january_first():
    end = date(2026, 3, 1)
    s = _serie(date(2025, 12, 1), (end - date(2025, 12, 1)).days + 1)
    ytd = PR.returns({"company": s})["company"]["YTD"]
    first = next(p for p in s["points"] if p["t"] >= "2026-01-01")
    assert ytd["total"] == pytest.approx(s["points"][-1]["a"] / first["a"] - 1)


def test_for_web_chart_is_base_100_aligned_to_each_series_points():
    end = date(2026, 10, 16)
    co = _serie(end - timedelta(days=500), 501, symbol="CO")
    mk = _serie(end - timedelta(days=600), 601, c0=50, step=0.5, symbol="^GSPC")   # otro calendario
    co["events"] = [{"t": (end - timedelta(days=10)).isoformat(), "kind": "dividend", "value": 1, "label": "Dividendo"},
                    {"t": (end - timedelta(days=10)).isoformat(), "kind": "dividend", "value": 1, "label": "Dividendo"},
                    {"t": "no-es-fecha", "kind": "split", "value": 2, "label": "Split"}]
    out = PR.for_web({"symbol": "CO", "company": co, "market": mk,
                      "sector": {"symbol": None, "status": "sin_dato", "points": [], "events": []}})
    assert [r["key"] for r in out["ranges"]] == [r["key"] for r in PR.ranges()]
    ch = out["chart"]["1M"]
    assert ch["status"] == "ok" and ch["covered"]
    for role, serie in (("company", co), ("market", mk)):
        win = ch["series"][role]
        pts = serie["points"][win["i0"]:win["i0"] + len(win["values"])]
        assert pts[0]["t"] == ch["start"] and pts[-1]["t"] == ch["end"]
        assert win["values"][0] == 100
        assert win["values"][-1] == pytest.approx(100 * pts[-1]["a"] / pts[0]["a"], abs=0.01)
    # una marca por sesión y tipo; la fecha rota no tumba nada
    assert ch["marks"] == [{"t": (end - timedelta(days=10)).isoformat(), "kind": "dividend", "label": "Dividendo"}]
    # 3 años: la ventana común empieza tarde y lo dice
    assert out["chart"]["3A"]["covered"] is False and "empieza" in out["chart"]["3A"]["reason"]
    assert out["company"]["returns"]["1M"]["total_txt"].startswith("+")
    assert out["sector"]["returns"] == {}


def test_for_web_without_company_uses_the_market_as_reference():
    end = date(2026, 10, 16)
    mk = _serie(end - timedelta(days=100), 101, symbol="^GSPC")
    out = PR.for_web({"symbol": "X", "company": {"symbol": "X", "status": "sin_dato", "points": [], "events": [],
                                                  "reason": "Yahoo caído"}, "market": mk,
                      "sector": {"symbol": None, "status": "sin_dato", "points": [], "events": []}})
    assert out["chart"]["1M"]["status"] == "ok" and list(out["chart"]["1M"]["series"]) == ["market"]
    assert out["chart"]["1M"]["marks"] == [] and out["company"]["returns"] == {}


def test_for_web_without_any_series():
    empty = {"symbol": None, "status": "sin_dato", "points": [], "events": []}
    out = PR.for_web({"symbol": "X", "company": dict(empty, reason="sin serie"), "market": dict(empty), "sector": dict(empty)})
    assert all(c["status"] == "sin_dato" and c["series"] == {} for c in out["chart"].values())


@pytest.mark.parametrize("sym", S.panel_symbols()[:12])
def test_web_and_pdf_show_the_same_returns(sym):
    """La tabla de rentabilidades del PDF y la de la web (/api/v2/prices) salen del mismo cálculo: mismas cifras."""
    prices = S.prices(sym)
    if prices is None:
        pytest.skip("sin series grabadas")
    web = PR.for_web({k: (dict(v) if isinstance(v, dict) else v) for k, v in prices.items()})
    pdf = P.period_returns(prices)
    labels = {r["label"]: r["key"] for r in PR.ranges()}
    for label, vals in pdf["rows"]:
        for role, v in vals.items():
            assert web[role]["returns"][labels[label]]["total"] == v
    # y el texto del informe lleva esas cifras
    text = " ".join(" ".join(pi.page_texts(S.build(sym))).split())
    co = web["company"]["returns"]
    for key in ("1A", "YTD"):
        if co[key]["total"] is not None:
            assert co[key]["total_txt"] in text


def test_endpoint_adds_returns_and_chart(monkeypatch):
    import main
    import price_history
    import prices_v2
    idx = pd.date_range("2025-01-01", periods=400, freq="D")
    frame = pd.DataFrame({"close": [100 + i for i in range(400)], "adj_close": [100 + i for i in range(400)],
                          "volume": [1.0] * 400}, index=idx)
    monkeypatch.setattr(price_history, "chart", lambda sym: {"symbol": sym, "frame": frame})
    monkeypatch.setattr(price_history, "chart_market", lambda: {"symbol": "^GSPC", "frame": frame})
    monkeypatch.setattr(prices_v2, "earnings_events", lambda sym, first: ([], None))
    out = main._prices_v2_payload("AAPL", None)
    assert out["company"]["returns"]["1A"]["total_txt"] and out["chart"]["1A"]["status"] == "ok"
    assert [r["key"] for r in out["ranges"]] == [r["key"] for r in PR.ranges()]


def test_market_without_the_total_return_series_says_sin_dato():
    """V7 (M7), del test de E4 en el navegador (chartEvents.test.ts), aquí tras la fusión (V6, F1: las rentabilidades
    se calculan en el backend): sin la serie con dividendos del mercado (`total_status` "sin_dato"), la rentabilidad
    con dividendos es «—» («Sin dato» en la web), nunca la de precio con otra etiqueta; con ella, las dos."""
    end = date(2026, 10, 16)
    mk = _serie(end - timedelta(days=400), 401, symbol="^GSPC")
    ok = PR.returns({"market": dict(mk, total_status="ok", total_symbol="SPY")})["market"]["1A"]
    assert ok["total"] is not None and ok["price"] is not None
    no = PR.returns({"market": dict(mk, total_status="sin_dato", total_note="sin la serie con dividendos (Yahoo caído)")})
    assert no["market"]["1A"]["total"] is None and no["market"]["1A"]["total_txt"] == "—"
    assert no["market"]["1A"]["price"] == ok["price"]
