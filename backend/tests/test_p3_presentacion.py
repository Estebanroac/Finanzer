"""
F8 · P3 (auditoría externa del 26-oct-2026, «Presentación»): lo que el informe enseña, sin cambiar puntuaciones.
"""
import pytest

import validate


# ───────────── 1. ROE no significativo con patrimonio ≤ 0 (MCD) ─────────────

def test_roe_con_patrimonio_negativo_es_no_significativo():
    """MCD: patrimonio −1.022 millones, ROE −859,8 % (y una brecha de −859.885 % frente a la industria). Regla M: no es
    una cifra que leer; sale «no significativo» con su motivo. Va después del score: no cambia la puntuación."""
    r = {"key_metrics": {"roe": -8.5978, "total_equity": -1.022e9}, "ratios": {"roe": -8.5978}}
    flags = validate.validate_outputs(r)
    assert r["key_metrics"]["roe"] is None and r["ratios"]["roe"] is None
    f = next(f for f in flags if f["field"] == "key_metrics.roe")
    assert f["rule"] == "ratio_no_significativa" and "patrimonio es negativo" in f["reason"] and f["old"] == -8.5978


def test_roe_con_patrimonio_positivo_no_cambia():
    r = {"key_metrics": {"roe": 0.35, "total_equity": 5e9}, "ratios": {"roe": 0.35}}
    assert not [f for f in validate.validate_outputs(r) if f["field"].endswith(".roe")]
    assert r["key_metrics"]["roe"] == 0.35


# ───────────── 2. Valor justo redondeado, rango del bloque central y margen de seguridad ─────────────
import display
import numfmt


def test_valor_justo_a_dos_cifras_significativas():
    assert [numfmt.estimate(v) for v in (116.08, 7.13, 503.25, 14.8, 1234.5)] == ["$120", "$7.1", "$500", "$15",
                                                                                  "$1,200"]
    assert numfmt.estimate(None) == "—"


def test_rango_del_bloque_central_declarado():
    """AAPL (panel): caso base en la casilla (2, 2); el bloque central (crecimiento ± 2,5 pp, WACC ± 1 pp) va de
    88,39 a 156,47. Es el mínimo y el máximo de esas 9 casillas, no un p10–p90, y lo dice."""
    m = [[119.96, 100.9, 87.2, 76.86, 68.77], [139.6, 116.93, 100.65, 88.39, 78.82],
         [162.22, 135.35, 116.08, 101.59, 90.29], [188.21, 156.47, 133.74, 116.66, 103.36],
         [218.01, 180.64, 153.9, 133.84, 118.24]]
    s = {"matrix": m, "base_growth_idx": 2, "base_discount_idx": 2,
         "growth_rates": [-0.0319, -0.0069, 0.0181, 0.0431, 0.0681],
         "discount_rates": [0.0756, 0.0856, 0.0956, 0.1056, 0.1156]}
    r = display.dcf_central_range(s)
    assert r["low"] == 88.39 and r["high"] == 156.47
    assert "$88–$160" in r["text"] and "± 2,5 pp" in r["text"] and "± 1 pp" in r["text"] and "no un p10–p90" in r["text"]
    assert display.dcf_central_range(None) is None


def test_margen_de_seguridad_con_dcf_de_fiabilidad_baja(outputs_by_env):
    """CAT y DOW (panel): DCF de fiabilidad baja → el margen de seguridad es «No significativo», con el motivo; con
    fiabilidad media o alta, a la unidad (sin decimales)."""
    out = outputs_by_env("panel")
    for sym in ("CAT", "DOW"):
        a = out[sym][0]
        assert a["dcf"]["reliability"]["level"] == "baja"
        r = {x["key"]: x for x in a["display"]["sections"]["valuation"]["intrinsic"]["rows"]}
        assert r["margin_of_safety"]["state"] == "no_significativo" and "fiabilidad baja" in r["margin_of_safety"]["text"]
        assert r["dcf_fair_value"]["value"].count(".") <= 1 and "bloque central" in r["dcf_fair_value"]["text"]
    a = out["AAPL"][0]
    r = {x["key"]: x for x in a["display"]["sections"]["valuation"]["intrinsic"]["rows"]}
    # F10 (beta con semanas completas): −195 % → −197 %. Revisión de COST (hallazgo 6): fuera de ±100 %, la cota y la
    # cifra exacta en el detalle.
    assert r["margin_of_safety"]["value"] == "< −100%" and "−197%" in r["margin_of_safety"]["text"]
    assert r["dcf_fair_value"]["value"] == "$120"


# ───────────── 3. Una sola ventana de fuerza relativa (la de la tabla de rentabilidades) ─────────────
import numpy as np
import pandas as pd

import market_signals as ms
import price_returns as pr


def test_fuerza_relativa_con_la_regla_de_la_tabla():
    """MSFT (auditoría): +3,2 % frente a +29,6 % en un sitio y +1,0 % frente a +25,3 % en otro, los dos «a 12 meses».
    La señal usa ahora la regla de la tabla de rentabilidades de la web y del PDF (lib/price_returns): con la misma
    serie, las dos cifras son la misma."""
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2023-01-02", periods=900)
    co = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 900))), index=idx)
    etf = pd.Series(50 * np.exp(np.cumsum(rng.normal(0, 0.01, 900))), index=idx)
    r = ms.relative_strength(co, etf)
    end = idx[-1].date()
    pts = lambda s: [(d.date(), float(v)) for d, v in s.items()]   # noqa: E731
    for key, days in (("6M", 182), ("1A", 365)):
        start = pr.start_of(end, days)
        w = r["windows"][key]
        assert w["company"] == pytest.approx(pr.period_return(pts(co), start, end))
        assert w["sector"] == pytest.approx(pr.period_return(pts(etf), start, end))
    assert r["value"] == pytest.approx(r["windows"]["1A"]["difference"])


# ───────────── 4. Nota del Piotroski condicionada al dato de la empresa ─────────────
import business_model as bm

_FLAT = {"current_assets": [68, 68, 68, 68], "current_liabilities": [100, 100, 100, 100]}


def test_piotroski_nota_con_circulante_negativo_dice_su_dato():
    """PG (0,68x, industria de circulante negativo estructural): la nota sale y cita su current ratio."""
    t = bm.piotroski_caveat(bm.current_ratio_context("Household & Personal Products", _FLAT, 0.68), 0.68)
    assert t and "0.68x" in t and "margen" not in t


@pytest.mark.parametrize("industry,cr,st", [
    ("Software - Infrastructure", 1.23, None),            # MSFT (auditoría): current ratio 1,23
    ("Software - Infrastructure", 7.23, None),            # PLTR: 7,2
    ("Household & Personal Products", 0.94,               # SNOW-like: < 1 pero empeorando frente a su historia
     {"current_assets": [94, 160, 170, 150], "current_liabilities": [100, 100, 100, 100]}),
    ("Steel", 0.68, _FLAT),                                # industria sin circulante negativo estructural
])
def test_piotroski_sin_nota_si_el_dato_no_la_justifica(industry, cr, st):
    assert bm.piotroski_caveat(bm.current_ratio_context(industry, st, cr), cr) is None


@pytest.mark.parametrize("t,expected", [("PG", "0.68x"), ("UL", "0.79x"), ("MSFT", None), ("PLTR", None),
                                        ("SNOW", None), ("AMZN", None), ("KO", None), ("CRWD", None)])
def test_piotroski_nota_en_el_panel(t, expected):
    """Antes salía en las 8 por su industria; ahora solo en PG y UL, las que tienen current ratio < 1 sin empeorar."""
    import json, os
    a = json.load(open(os.path.join(os.path.dirname(__file__), "golden", "panel", f"{t}.json"), encoding="utf-8"))
    cav = (a.get("business_model") or {}).get("piotroski_caveat")
    assert (cav is None) if expected is None else (expected in cav)


# ───────────── 5. Etiquetas coherentes: β de CB y crecimiento de MRNA ─────────────
import display


def _golden(env, t):
    import json, os
    return json.load(open(os.path.join(os.path.dirname(__file__), "golden", env, f"{t}.json"), encoding="utf-8"))


@pytest.mark.parametrize("t,label", [("PGR", "β de la industria 0.48, sin Blume"),   # aseguradora, como CB
                                     ("BRK-B", "β de la industria 0.67, sin Blume"),
                                     ("BAC", "β ajustada 1.09"), ("JPM", "β ajustada 1.06")])
def test_beta_del_pb_justificado_dice_su_fuente(t, label):
    """CB (auditoría): el P/B justificado decía «β ajustada 0.48» y la tabla del WACC, «β media de la industria … sin
    Blume». La de la industria entra sin Blume: ya no se llama «ajustada»."""
    a = _golden("panel", t)
    reasons = [x["reason"] for x in a["score"]["breakdown"]["Valoración"]["adjustments"] if "justificado" in x["reason"]]
    assert reasons and all(label in r for r in reasons)
    assert (a.get("beta") or {}).get("source") == ("sector" if "industria" in label else "propia")


def test_categoria_no_concluyente_no_ensena_puntos():
    """MRNA (auditoría): la portada mostraba «Crecimiento 6/20» y el desglose la excluía por no concluyente."""
    assert display.category_score_txt(6, 20, False) == "no concluyente"
    assert display.category_score_txt(12, 20, True) == "12 / 20"
    d = _golden("forzados", "SNOW_no_concluyente")["display"]
    cover = [i for g in d["cover"]["categories"] for i in g["items"]]
    bd = d["sections"]["institutional"]["breakdown"]["categories"]
    assert any(not i["conclusive"] for i in cover)
    for c in cover + bd:
        assert c["score_txt"] == ("no concluyente" if not c["conclusive"] else f"{c['score']} / {c['max']}")
        if not c["conclusive"]:
            assert c["tone"] == "neu"


# ───────────── Clasificación del anexo: una sola etiqueta y frases completas (repaso de E2b) ─────────────
import prose


def test_prose_sentences_mayuscula_y_punto():
    assert prose.sentences(["Arquetipo X: por industria Bancos (banco)", "su historia muestra ciclo", None]) == \
        "Arquetipo X: por industria Bancos (banco). Su historia muestra ciclo."
    assert prose.sentences(["arquetipo X (banco)"]) == "Arquetipo X (banco)"    # cerrada sola, como en prose.close
    assert prose.sentences([]) is None


@pytest.mark.parametrize("t", ["HSBC", "RIVN", "AAPL"])
def test_clasificacion_del_anexo_una_etiqueta_y_frases(t):
    """HSBC: «Clasificación» se repetía en cada línea y la segunda empezaba en minúscula («su historia (11 ejercicios…»)."""
    import re
    items = [x for x in _golden("panel", t)["display"]["annex"]["items"] if x["label"] == "Clasificación"]
    assert len(items) == 1
    for s in re.split(r"(?<=[.…?!])\s+", items[0]["text"]):
        assert s[0].isupper() and s[-1] in ".…?!)", s
