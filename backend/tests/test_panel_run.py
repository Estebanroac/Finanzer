"""Fase 0 del plan de fiabilidad: tests de la herramienta panel_run (sobre el juego local, sin red)."""
import copy
import csv
import os

import panel_run as pr


def test_summary_has_all_columns_and_files(tmp_path):
    rows, changes, live = pr.run("replay", str(tmp_path), ["JPM", "NFLX"], env="local")
    assert changes is None and live is None
    with open(tmp_path / "resumen.csv", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == pr.COLUMNS
        got = list(reader)
    assert [r["ticker"] for r in got] == ["JPM", "NFLX"]
    for r in got:
        assert r["arquetipo"] and r["calidad_nivel"] and r["precio_nivel"] and r["confianza"]
        n = int(r["paginas_pdf"])
        assert n > 0 and all((tmp_path / f"{r['ticker']}.p{i}.png").is_file() for i in range(1, n + 1))
        assert (tmp_path / f"{r['ticker']}.pdf.txt").read_text(encoding="utf-8").startswith("===== página 1")
    md = (tmp_path / "resumen.md").read_text(encoding="utf-8")
    assert "## Veredicto" in md and "## Datos, DCF y tiempos" in md and "| JPM |" in md


def test_compare_detects_an_injected_change(tmp_path):
    prev = tmp_path / "antes"
    rows, _, _ = pr.run("replay", str(prev), ["JPM", "NFLX"], env="local")
    with open(prev / "resumen.csv", encoding="utf-8") as fh:
        old = list(csv.DictReader(fh))
    old[1]["precio_nivel"] = "muy exigente"            # cambio inyectado en NFLX
    with open(prev / "resumen.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=pr.COLUMNS)
        w.writeheader()
        w.writerows(old)
    _, changes, _ = pr.run("replay", str(tmp_path / "ahora"), ["JPM", "NFLX"], env="local", compare=str(prev))
    assert changes == [("NFLX", "precio_nivel", "muy exigente", rows[1]["precio_nivel"])]
    assert "## Cambios frente a" in (tmp_path / "ahora" / "resumen.md").read_text(encoding="utf-8")


def test_rejected_ticker_row():
    r = pr.summarize("SPY", {"__http_error__": 422, "detail": "Es un ETF"})
    assert r["http"] == 422 and r["coincide"] == "sí" and r["arquetipo"] == "" and "ETF" in r["errores"]


def test_expected_table_marks_doubtful_and_undecided():
    assert pr._match("BRK-B", "FINANCIAL", 200) == "dudoso"
    assert pr._match("TSM", "CYCLICAL", 200) == "a decidir"
    assert pr._match("PLTR", "MATURE", 200) == "no"
    assert set(pr.EXPECTED) == set(pr.fb.PANEL_TICKERS)


def test_live_diffs_separate_rf_price_and_real():
    """Un 'live' fabricado con otra Rf, otro precio y un cambio real: cada grupo recoge lo suyo."""
    base = pr._replay_with("NFLX", "local")
    live = pr._replay_with("NFLX", "local", rf={"value": 0.04, "as_of": "2026-10-14"}, price=base["price"] * 1.01)
    assert live["risk_free"]["value"] == 0.04
    live = copy.deepcopy(live)
    live["quality"]["score"] += 1                       # diferencia real inyectada
    d = pr.classify_live_diffs("NFLX", live, env="local")
    assert d["solo_rf"] and d["solo_precio"]
    assert list(d["reales"]) == ["quality.score"]
    assert d["rf_replay"] != d["rf_live"] == 0.04


def test_live_section_in_summary(tmp_path):
    rows = [pr.summarize("NFLX", pr._replay_with("NFLX", "local"))]
    diffs = {"NFLX": {"rf_replay": 0.0529, "rf_live": 0.0519, "rf_live_source": "^TNX", "price_replay": 1,
                      "price_live": 2, "solo_rf": {"a": (1, 2)}, "solo_precio": {}, "reales": {"b": (1, 3)}}}
    pr.write_summary(str(tmp_path), rows, {"mode": "live"}, live_diffs=diffs)
    md = (tmp_path / "resumen.md").read_text(encoding="utf-8")
    assert "### Solo Rf" in md and "### Solo precio intradía" in md and "### Diferencias reales" in md
    assert os.path.isfile(tmp_path / "live_vs_replay.json")
