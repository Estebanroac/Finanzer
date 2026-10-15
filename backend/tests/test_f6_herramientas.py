"""Fase 6 (diagnóstico): las herramientas de medida, sin red."""
import pytest

import medir_concurrencia as mc
import perfil_local as pl


def _r(t0, t1):
    return {"inicio": t0, "fin": t1, "s": t1 - t0, "status": 200}


def _ticker(*spans):
    keys = ("analisis_frio", "analisis_caliente", "pdf_caliente")
    return {"ticker": "X", **{k: _r(*s) for k, s in zip(keys, spans)}}


def test_solape_cero_en_serie_y_total_en_paralelo():
    serie = [_ticker((0, 1), (1, 2), (2, 3)), _ticker((3, 4), (4, 5), (5, 6))]
    assert mc.overlap(serie) == 0.0
    paralelo = [_ticker((0, 1), (1, 2), (2, 3)), _ticker((0, 1), (1, 2), (2, 3))]
    assert mc.overlap(paralelo) == 1.0


def test_medida_se_niega_a_12_simultaneas_contra_produccion():
    with pytest.raises(SystemExit):
        mc.main(["--out", "/nunca", "--concurrency", "12"])


def test_modulo_de_cada_archivo():
    assert pl.module_of("/x/finanzer_next/backend/lib/pdf_report.py") == "lib/pdf_report.py"
    assert pl.module_of("/x/finanzer_next/backend/main.py") == "main.py"
    assert pl.module_of("/x/site-packages/reportlab/pdfbase/pdfutils.py") == "reportlab"
    assert pl.module_of("~") == "builtins"


def test_llamadas_externas_de_un_ticker_del_panel():
    calls = pl.count_external_calls(["JPM"])["JPM"]
    assert calls["finnhub:/stock/metric"] == 1 and calls["yahoo_http:quoteSummary"] == 2
    assert all(calls.get(f"yfinance:{a}", 0) >= 1 for a in ("income_stmt", "balance_sheet", "cashflow", "fast_info"))
