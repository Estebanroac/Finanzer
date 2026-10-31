"""
F9 · R3 (revisión externa de NU, 27-oct-2026): una sola verdad por cifra en todo el informe, web y PDF.

Recorre el `display` de cada golden (la base de la web y de los dos PDF) y el texto de sus PDF, y falla si una misma
métrica del mismo periodo aparece con dos valores (tests/coherence.py). Casos de la revisión: P/B 5.34x en la portada
frente a 4.55x en la tabla; CAGR de ingresos 52.3% frente a 52.9% en el gráfico; crecimientos en USD frente a la moneda
de los estados; EV/EBITDA «No aplica» con cifra de industria; cifras TTM con el título «del ejercicio».
"""
import glob
import json
import os

import pytest

import coherence as C
import display

HERE = os.path.dirname(__file__)
GOLDEN = sorted(p for env in ("panel", "local", "forzados") for p in glob.glob(os.path.join(HERE, "golden", env, "*.json")))


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _id(p):
    return f"{os.path.basename(os.path.dirname(p))}-{os.path.basename(p)[:-5]}"


@pytest.mark.parametrize("path", GOLDEN, ids=_id)
def test_una_sola_cifra_por_metrica_en_el_display(path):
    a = _load(path)
    if "display" not in a:
        pytest.skip("sin display")
    bad = C.conflicts(C.display_figures(a))
    assert not bad, "\n".join(f"{x[0]} ({x[2]}): {x[3]:g} en {x[5]} frente a {y[3]:g} en {y[5]}" for x, y in bad[:10])


@pytest.mark.parametrize("path", [p for p in GOLDEN if "/forzados/" not in p], ids=_id)
def test_la_portada_del_pdf_dice_la_cifra_del_display(path):
    a = _load(path)
    if "display" not in a:
        pytest.skip("sin display")
    env, t = os.path.basename(os.path.dirname(path)), os.path.basename(path)[:-5]
    bad = []
    for pdf, above in ((os.path.join(HERE, "golden", env, f"{t}.pdf.txt"), True),
                       (os.path.join(HERE, "golden", f"{env}_pdf_v2", f"{t}.pdf.txt"), False)):
        if os.path.exists(pdf):
            with open(pdf, encoding="utf-8") as fh:
                bad += [(os.path.basename(os.path.dirname(pdf)), *c) for c in C.pdf_conflicts(fh.read(), a, above)]
    assert not bad, "\n".join(f"{x[0]}: {x[1]} {x[3]:g}{x[2]} en el display, {x[4]} en el PDF" for x in bad[:10])


# ── Las piezas ──

def test_el_detector_ve_la_contradiccion_de_nu():
    """La del P/B de NU tal como la vio la revisión: 5.33x en la portada y 4.54x en la tabla."""
    a = {"display": {"cover": {"kpis": [{"key": "pb", "label": "P/B", "value": "5.33x"}]},
                     "sections": {"valuation": {"rows": [{"key": "pb", "label": "P/B", "value": "4.54x"}]}}}}
    assert C.conflicts(C.display_figures(a))
    a["display"]["cover"]["kpis"][0]["value"] = "4.54x"
    assert not C.conflicts(C.display_figures(a))


def test_redondeo_no_es_contradiccion():
    a = {"display": {"cover": {"kpis": [{"key": "pb", "label": "P/B", "value": "4.55x"}]},
                     "summary": {"cards": [{"key": "pb", "label": "P/B", "value": "4.5", "unit": "x"}]}}}
    assert not C.conflicts(C.display_figures(a))


def test_no_aplica_deja_vacia_la_columna_de_industria():
    """NU: EV/EBITDA «No aplica» con 69.37x de industria."""
    r = display._row("ev_ebitda", "EV/EBITDA", "12.0x", "No aplica", state="no_aplica", bench="69.37x", gap="+10%")
    assert (r["value"], r["bench"], r["gap"]) == ("—", "—", "—")


@pytest.mark.parametrize("ao,title", [
    ({"type": "ttm", "date": "2026-06-30"}, "Cifras de los últimos doce meses (TTM, a 30 de junio de 2026)"),
    ({"type": "fy", "date": "2025-12-31"}, "Cifras del ejercicio cerrado el 31 de diciembre de 2025 (FY)"),
])
def test_el_titulo_de_las_cifras_dice_su_periodo(ao, title):
    """NU: «Cifras del ejercicio» con los ingresos de los últimos doce meses."""
    assert f"Cifras {display.period_basis(ao)['of']}" == title


# ── Opción A (decisión del PM): EDGAR es la serie FY única si cubre los ejercicios de los estados ──
import edgar_primary
import sec_edgar


def _facts(concepts, unit="USD", tax="ifrs-full"):
    form = "20-F" if tax == "ifrs-full" else "10-K"
    f = {"facts": {tax: {}}}
    for c, rows in {**concepts, "Assets": [("2025-12-31", 1.0)]}.items():
        f["facts"][tax][c] = {"units": {unit: [{"start": f"{e[:4]}-01-01", "end": e, "val": v, "form": form,
                                                "filed": f"{int(e[:4]) + 1}-03-01", "accn": e} for e, v in rows]}}
    return f


def _info(rev, industry="Software—Infrastructure", sector="Technology"):
    return {"sector": sector, "industry": industry, "_statements_fy": {
        "inc_ends": ["2025-12-31", "2024-12-31"], "revenue": list(rev), "net_income": [None, None]}}


def test_la_serie_fy_es_la_de_edgar_si_cubre_los_ejercicios():
    info, log = _info([10.63, 8.27]), {}
    f = _facts({"Revenue": [("2025-12-31", 15.77), ("2024-12-31", 11.52)]})
    edgar_primary._apply_fy_series(info, f, [], None, 14, log)
    assert info["_statements_fy"]["revenue"] == [15.77, 11.52]
    assert {r["fy_end"] for r in log["reconciliation"]} == {"2025-12-31", "2024-12-31"}   # difieren más de un 2%


def test_sin_un_ejercicio_manda_la_fuente_entera():
    """Un hueco dentro de la historia del emisor (presentaba ya en 2024: Liabilities de ese ejercicio), no un ejercicio
    anterior a su primer informe (F10 · B2, TKO: test_f10_cifras_unicas.py)."""
    info, log = _info([10.63, 8.27]), {}
    f = _facts({"Revenue": [("2025-12-31", 15.77)], "Liabilities": [("2024-12-31", 1.0)]})
    edgar_primary._apply_fy_series(info, f, [], None, 14, log)
    assert info["_statements_fy"]["revenue"] == [10.63, 8.27]
    assert any(s["source"] == "fuente" and "2024-12-31" in s["reason"] for s in log["series"])


def test_banco_ifrs_las_comisiones_no_son_sus_ingresos():
    """BCS: EDGAR solo etiqueta RevenueFromContractsWithCustomers (NIIF 15: comisiones)."""
    info, log = _info([38.4, 33.5], industry="Banks—Diversified", sector="Financial Services"), {}
    f = _facts({"RevenueFromContractsWithCustomers": [("2025-12-31", 11.1), ("2024-12-31", 10.7)]}, unit="GBP")
    edgar_primary._apply_fy_series(info, f, [], None, 14, log)
    assert info["_statements_fy"]["revenue"] == [38.4, 33.5]
    hist = sec_edgar.history(f)
    edgar_primary.bank_history(info, hist)
    assert hist["revenue"]["values"] == [] and "NIIF 15" in hist["revenue"]["reason"]


def test_una_sola_definicion_por_serie():
    """HSBC: el atribuible hasta 2022 y ProfitLoss después; la serie es la del concepto del último ejercicio."""
    f = _facts({"ProfitLossAttributableToOwnersOfParent": [("2022-12-31", 16.0)],
                "ProfitLoss": [("2023-12-31", 24.6), ("2022-12-31", 16.3)]})
    vals = sec_edgar.annual_history(f, "net_income")["values"]
    assert {v["concept"] for v in vals} == {"ifrs-full:ProfitLoss"} and [v["value"] for v in vals] == [24.6, 16.3]


# ── Repaso de E2b: una etiqueta y una precisión por métrica en la web (cifras clave) y el PDF (tarjetas) ──

@pytest.mark.parametrize("path", [p for p in GOLDEN if "/forzados/" not in p], ids=_id)
def test_tarjetas_y_cifras_clave_con_la_misma_etiqueta_y_precision(path):
    d = _load(path).get("display")
    if not d:
        pytest.skip("sin display")
    kp = {k["key"]: k for k in d["cover"]["kpis"]}
    for c in d["summary"]["cards"]:
        k = kp.get(c["key"])
        if not k or c.get("state") != "con_dato" or k.get("state") != "con_dato":
            continue
        assert c["label"] == k["label"], c["key"]
        assert f"{c['value']}{c['unit']}" == k["value"], c["key"]


# ── F10 · B2: también sobre los análisis guardados del escaneo del modelo general (FINANZER_SCAN_CACHE) ──
SCAN = C.scan_files()


@pytest.mark.skipif(not SCAN, reason=f"sin escaneo ({C.SCAN_ENV} no apunta a una carpeta con análisis guardados)")
@pytest.mark.parametrize("path", SCAN, ids=lambda p: os.path.basename(p).split(".")[0])
def test_una_sola_cifra_en_el_escaneo(path):
    bad = C.scan_conflicts(path)
    assert not bad, "\n".join(bad[:10])
