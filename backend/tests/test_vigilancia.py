"""Fase 7 (vigilancia semanal): la lógica de comparación sobre corridas sintéticas, sin red.

Detecta una rotura de fuente, un error y una regresión de latencia; no alerta por un cambio de precio, de Rf
(efecto frontera contrastado), de código ni de datos nuevos; sin commit degrada a aviso."""
import copy
import datetime as _dt

import vigilancia as vg

COMMIT_A = "a" * 40


def _analysis(price=100.0, rf=0.05, balance="2026-06-30", revenue=1e9, eps=5.0):
    return {
        "price": price,
        "risk_free": {"value": rf, "source": "^TNX"},
        "key_metrics": {"revenue": revenue, "net_income": 1e8, "total_debt": 5e8, "eps": eps, "beta": 1.1,
                        "dividend_yield": 0.02},
        "yearly_financials": [{"year": 2024, "revenue": revenue}, {"year": 2025, "revenue": revenue}],
        "data_provenance": {"path": "plan_b_yfinance", "ttm": {"balance_date": balance, "basis": "ttm"},
                            "fields": {"beta": {"source": "finnhub"}}},
        "altman_z": {"available": True}, "piotroski_f": {"available": True}, "dcf": {"available": True},
    }


def _row(sym, http=200, level="razonable", t=5.0, t_pdf=8.0, pages=8, errores=""):
    return {"ticker": sym, "http": str(http), "arquetipo": "MATURE", "calidad_nivel": "sólida",
            "precio_nivel": level, "confianza": "media", "tiempo_s": str(t), "tiempo_pdf_s": str(t_pdf),
            "paginas_pdf": "" if pages is None else str(pages), "errores": errores}


def _run(path="run", commit=COMMIT_A, **tickers):
    """tickers: sym -> (row, analysis)."""
    return {"path": path, "meta": {"commit": commit, "fecha": "2026-10-17T09:00:00"},
            "rows": {s: r for s, (r, _) in tickers.items()},
            "analyses": {s: a for s, (_, a) in tickers.items() if a is not None}}


def _pair(prev_level="razonable", cur_level="razonable", prev_a=None, cur_a=None, commit_prev=COMMIT_A,
          commit_cur=COMMIT_A, extra_cur=None):
    prev = _run("antes", commit_prev, KO=(_row("KO", level=prev_level), prev_a or _analysis()))
    cur_t = {"KO": (_row("KO", level=cur_level), cur_a or _analysis())}
    cur_t.update(extra_cur or {})
    cur = _run("ahora", commit_cur, **cur_t)
    return prev, cur


def _compare(prev, cur, counterfactual=None):
    return vg.compare(prev, cur, code_cmp=lambda a, b: a == b, counterfactual=counterfactual)


def test_detecta_rotura_de_fuente_con_todo_lo_demas_igual():
    prev, cur = _pair("razonable", "exigente", cur_a=_analysis(price=100.2, eps=4.0))   # +0.2%: no cuenta
    res = _compare(prev, cur)
    assert [(a["tipo"], a["ticker"]) for a in res["alertas"]] == [("rotura de fuente", "KO")]
    causa = res["alertas"][0]["causa"]
    assert "rotura de fuente" in causa and "key_metrics.eps" in causa     # dice qué fuente cambió


def test_rotura_cuando_la_rf_no_reproduce_el_cambio_en_el_replay():
    prev, cur = _pair("razonable", "exigente", cur_a=_analysis(rf=0.051))
    sin_mov = lambda s, a0, a1: {k: ("x", "x") for k in vg.LEVEL_KEYS}  # noqa: E731
    res = _compare(prev, cur, counterfactual=sin_mov)
    assert [a["tipo"] for a in res["alertas"]] == ["rotura de fuente"]
    assert "no lo reproducen" in res["alertas"][0]["causa"]


def test_no_alerta_por_un_cambio_de_precio():
    prev, cur = _pair("razonable", "exigente", cur_a=_analysis(price=112.0))
    res = _compare(prev, cur)
    assert res["alertas"] == []
    assert [n["tipo"] for n in res["avisos"]] == ["cambio explicado"]
    assert "precio 100.00 → 112.00" in res["avisos"][0]["causa"]


def test_no_alerta_por_un_cambio_de_rf_contrastado_en_el_replay():
    prev, cur = _pair("razonable", "atractivo", cur_a=_analysis(rf=0.0519))
    frontera = lambda s, a0, a1: {**{k: ("x", "x") for k in vg.LEVEL_KEYS},  # noqa: E731
                                  "precio_nivel": ("razonable", "atractivo")}
    res = _compare(prev, cur, counterfactual=frontera)
    assert res["alertas"] == []
    assert "efecto frontera" in res["avisos"][0]["causa"]


def test_no_alerta_por_un_cambio_de_rf_sin_fixture_para_contrastar():
    prev, cur = _pair("razonable", "atractivo", cur_a=_analysis(rf=0.0519))
    res = _compare(prev, cur, counterfactual=lambda *a: None)
    assert res["alertas"] == [] and "atribuible a la Rf" in res["avisos"][0]["causa"]


def test_no_alerta_por_datos_nuevos_ni_por_codigo_distinto():
    prev, cur = _pair("razonable", "exigente", cur_a=_analysis(balance="2026-09-30", revenue=1.1e9))
    res = _compare(prev, cur)
    assert res["alertas"] == [] and "datos nuevos de los estados" in res["avisos"][0]["causa"]
    prev, cur = _pair("razonable", "exigente", cur_a=_analysis(eps=4.0), commit_cur="b" * 40)
    res = _compare(prev, cur)
    assert res["alertas"] == [] and "cambio de código" in res["avisos"][0]["causa"]


def test_campo_de_los_estados_que_aparece_no_se_lee_como_cifra_distinta():
    prev_a = _analysis()
    prev_a["key_metrics"]["net_interest_income"] = None
    cur_a = _analysis()
    cur_a["key_metrics"]["net_interest_income"] = 1e6
    prev, cur = _pair("razonable", "exigente", prev_a=prev_a, cur_a=cur_a, commit_cur="b" * 40)
    causa = _compare(prev, cur)["avisos"][0]["causa"]
    assert "aparecen o desaparecen (key_metrics.net_interest_income)" in causa and "otras cifras" not in causa


def test_sin_commit_degrada_a_aviso_y_lo_dice():
    prev, cur = _pair("razonable", "exigente", commit_prev=None)
    res = _compare(prev, cur)
    assert res["alertas"] == []
    assert res["codigo"]["estado"] == "desconocido"
    assert "no se puede distinguir" in res["avisos"][0]["causa"]


def test_commits_distintos_con_el_mismo_codigo_cuentan_como_igual():
    prev, cur = _pair("razonable", "exigente", commit_cur="b" * 40)
    res = vg.compare(prev, cur, code_cmp=lambda a, b: True, counterfactual=None)
    assert res["codigo"]["estado"] == "igual"
    assert [a["tipo"] for a in res["alertas"]] == ["rotura de fuente"]


def test_detecta_errores_y_spy_espera_422():
    extra = {
        "JPM": (_row("JPM", http=500, errores="boom"), None),
        "PG": (_row("PG", errores="altman_z: sin dato"), _analysis()),
        "AAPL": (_row("AAPL", pages=None), _analysis()),
        "SPY": (_row("SPY", http=422, pages=None), None),
    }
    prev, cur = _pair(extra_cur=extra)
    res = _compare(prev, cur)
    errs = {(a["ticker"], a["causa"].split(":")[0]) for a in res["alertas"] if a["tipo"] == "error"}
    assert errs == {("JPM", "HTTP 500"), ("PG", "el análisis trae errores"), ("AAPL", "el PDF no se generó")}
    prev, cur = _pair(extra_cur={"SPY": (_row("SPY", http=200), _analysis())})
    assert [a["ticker"] for a in _compare(prev, cur)["alertas"]] == ["SPY"]


def test_detecta_regresion_de_latencia_y_no_la_por_debajo_del_50():
    def runs(t_cur):
        prev = _run("antes", **{s: (_row(s, t=5.0), _analysis()) for s in ("A", "B", "C")})
        cur = _run("ahora", **{s: (_row(s, t=t_cur), _analysis()) for s in ("A", "B", "C")})
        return prev, cur
    res = _compare(*runs(8.0))
    assert [n["tipo"] for n in res["avisos"]] == ["latencia"] and "/api/analysis" in res["avisos"][0]["causa"]
    assert _compare(*runs(7.4))["avisos"] == []
    assert res["alertas"] == []


def test_campo_que_pasa_a_sin_dato_es_aviso():
    cur_a = _analysis()
    cur_a["key_metrics"]["dividend_yield"] = None
    cur_a["altman_z"]["available"] = False
    prev, cur = _pair(cur_a=cur_a)
    res = _compare(prev, cur)
    assert res["alertas"] == []
    assert res["avisos"][0]["tipo"] == "sin dato"
    assert "key_metrics.dividend_yield" in res["avisos"][0]["causa"] and "altman_z.available" in res["avisos"][0]["causa"]


def test_ventana_prohibida_y_concurrencia():
    t = lambda h, m: _dt.datetime(2026, 10, 15, h, m)  # noqa: E731
    assert not vg.in_forbidden_window(t(15, 54))
    assert vg.in_forbidden_window(t(15, 55)) and vg.in_forbidden_window(t(16, 15)) and vg.in_forbidden_window(t(16, 45))
    assert not vg.in_forbidden_window(t(16, 46))
    for kw in ({"now": t(16, 0)}, {"concurrency": 4, "now": t(10, 0)}):
        try:
            vg.run_live("/nunca", **kw)
        except SystemExit:
            continue
        raise AssertionError(f"run_live debió negarse con {kw}")


def test_alertas_md_resumen_arriba(tmp_path):
    prev, cur = _pair("razonable", "exigente", cur_a=_analysis(eps=4.0))
    res = _compare(prev, cur)
    vg.write_outputs(str(tmp_path), res)
    md = (tmp_path / "alertas.md").read_text(encoding="utf-8")
    first = md.splitlines()[2]
    assert "HAY ALERTAS" in first and "1 rotura(s) de fuente" in first
    assert "## Latencias (s)" in md and "| /api/analysis | actual |" in md
    assert (tmp_path / "comparacion.json").is_file()


def test_compare_no_toca_las_corridas():
    prev, cur = _pair("razonable", "exigente", cur_a=_analysis(price=112.0))
    before = copy.deepcopy((prev, cur))
    _compare(prev, cur)
    assert (prev, cur) == before
