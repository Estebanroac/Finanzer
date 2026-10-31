"""
F10 · B2 (escaneo del modelo general, 28-oct-2026: 11 empresas con cifras dobles, todas de la historia de 10 años
frente al gráfico). Una sola serie FY de EDGAR para historia, gráfico y crecimiento:

- EIX, IVZ, APA: el beneficio disponible para el accionista común (decisión del PM) en todas partes; un concepto que
  completa años de otro solo si coincide con él en el último ejercicio común;
- TKO (constituida en 2023): los ejercicios anteriores a su primer informe anual no son suyos: sin dato;
- NTAP: el total de los ingresos, no `Revenues` (una parte);
- LHX y KDP: el cambio de ejercicio deja dos periodos anuales solapados; manda el más reciente;
- IDXX: la puntuación usa el ROE reportado si el normalizado no se distingue (sin la etiqueta «normalizado»).
"""
import edgar_primary
import sec_edgar


def _f(concepts, form="10-K"):
    """companyfacts us-gaap: {concepto: [(inicio, fin, valor[, presentado])]}."""
    out = {"facts": {"us-gaap": {}}}
    for c, rows in {**concepts, "Assets": concepts.get("Assets", [(None, "2025-12-31", 1.0)])}.items():
        out["facts"]["us-gaap"][c] = {"units": {"USD": [
            {"start": r[0], "end": r[1], "val": r[2], "form": form, "accn": r[1],
             "filed": r[3] if len(r) > 3 else f"{int(r[1][:4]) + 1}-02-20"} for r in rows]}}
    return out


def _y(e, v):
    return (f"{e[:4]}-01-01", e, v)


def test_common_shareholders_first_and_a_different_definition_does_not_fill():
    """EIX: el disponible para el común en todos los años; NetIncomeLoss (propietarios) no rellena si difiere."""
    f = _f({"NetIncomeLossAvailableToCommonStockholdersBasic": [_y("2025-12-31", 4457), _y("2022-12-31", 612)],
            "NetIncomeLoss": [_y("2025-12-31", 4459), _y("2022-12-31", 824), _y("2021-12-31", 925)]})
    h = sec_edgar.annual_history(f, "net_income")
    assert [(v["fy_end"][:4], v["value"]) for v in h["values"]] == [("2025", 4457), ("2022", 612), ("2021", 925)]
    # 2025 coincide (±2 %): misma definición, rellena 2021; con preferentes no coincidiría y no rellenaría
    f2 = _f({"NetIncomeLossAvailableToCommonStockholdersBasic": [_y("2025-12-31", 4000)],
             "NetIncomeLoss": [_y("2025-12-31", 4459), _y("2024-12-31", 1284)]})
    h2 = sec_edgar.annual_history(f2, "net_income")
    assert [v["fy_end"][:4] for v in h2["values"]] == ["2025"] and h2["concepts_rejected"]


def test_relay_of_the_same_definition_is_one_series():
    """IVZ: el disponible para el común desde 2023 y NetIncomeLoss antes, iguales en los años comunes: una serie."""
    f = _f({"NetIncomeLossAvailableToCommonStockholdersBasic": [_y("2025-12-31", -726.3), _y("2024-12-31", 538.0)],
            "NetIncomeLoss": [_y("2024-12-31", 538.0), _y("2023-12-31", -333.7)]})
    info = {"sector": "Financial Services", "industry": "Asset Management", "_statements_fy": {
        "inc_ends": ["2025-12-31", "2024-12-31", "2023-12-31"], "revenue": [None] * 3,
        "net_income": [-281.7, 774.8, -96.9]}}
    log = {}
    edgar_primary._apply_fy_series(info, f, [], None, 14, log)
    assert info["_statements_fy"]["net_income"] == [-726.3, 538.0, -333.7]
    assert next(s for s in log["series"] if s["field"] == "net_income")["source"] == "sec_edgar"


def test_years_before_the_first_annual_report_are_not_the_issuer():
    """TKO: su primer 10-K es el de 2023; el 2022 de la fuente es de la predecesora."""
    f = _f({"NetIncomeLoss": [_y("2025-12-31", 195.4), _y("2024-12-31", 9.4), (*_y("2023-12-31", -35.2), "2024-02-27")],
            "Assets": [(None, "2023-12-31", 1.0, "2024-02-27"), (None, "2025-12-31", 1.0)]})
    info = {"sector": "Communication Services", "industry": "Entertainment", "_statements_fy": {
        "inc_ends": ["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"], "revenue": [None] * 4,
        "net_income": [500.0, 40.0, 223.5, 180.0]}}
    log = {}
    edgar_primary._apply_fy_series(info, f, [], None, 14, log)
    assert info["_statements_fy"]["net_income"] == [195.4, 9.4, -35.2, None]
    assert log["before_first_filing"][0]["years"] == ["2022-12-31"]
    assert log["before_first_filing"][0]["reason"] == "la empresa presenta sus cuentas en la SEC desde 2023"


def test_revenue_is_the_total_not_a_part():
    """NTAP: `Revenues` (una parte) y el ingreso de contratos (el total) llegan al mismo ejercicio: el total."""
    f = _f({"Revenues": [("2025-04-26", "2026-04-24", 6237.0), ("2024-04-27", "2025-04-25", 5907.0)],
            "RevenueFromContractWithCustomerExcludingAssessedTax": [("2025-04-26", "2026-04-24", 6925.0),
                                                                    ("2024-04-27", "2025-04-25", 6572.0)]})
    h = sec_edgar.annual_history(f, "revenue")
    assert [v["value"] for v in h["values"]] == [6925.0, 6572.0]


def test_overlapping_fiscal_years_keep_the_latest():
    """LHX: julio 2018–junio 2019 (Harris) y el año 2019 tras la fusión; los dos salían como FY2019."""
    f = _f({"RevenueFromContractWithCustomerExcludingAssessedTax": [
        ("2019-01-04", "2020-01-03", 18194.0), ("2018-12-29", "2020-01-03", 12856.0)][1:] + [
        ("2018-06-30", "2019-06-28", 6801.0), ("2017-07-01", "2018-06-29", 6182.0)]})
    h = sec_edgar.annual_history(f, "revenue")
    assert [(v["fy_end"], v["value"]) for v in h["values"]] == [("2020-01-03", 12856.0), ("2018-06-29", 6182.0)]
    assert h["dropped_overlap"] == ["2019-06-28"]


def test_years_edgar_lacks_come_from_the_source_if_the_definition_is_the_same():
    """BE: EDGAR sin el beneficio de 2025; en los comunes coincide con la fuente (±2 %): EDGAR los suyos y la fuente el
    que falta. Con una definición distinta (el R3 de F9), la fuente entera."""
    f = _f({"NetIncomeLoss": [_y("2024-12-31", -302.1), _y("2023-12-31", -301.7)],
            "Assets": [(None, "2023-12-31", 1.0, "2024-02-20"), (None, "2025-12-31", 1.0)]})
    info = {"sector": "Industrials", "industry": "Electrical Equipment", "_statements_fy": {
        "inc_ends": ["2025-12-31", "2024-12-31", "2023-12-31"], "revenue": [None] * 3,
        "net_income": [-90.0, -302.0, -301.4]}}
    log = {}
    edgar_primary._apply_fy_series(info, f, [], None, 14, log)
    assert info["_statements_fy"]["net_income"] == [-90.0, -302.1, -301.7]
    assert log["filled_from_source"][0]["years"] == ["2025-12-31"]


import glob
import json
import os

import pytest

_GOLDEN = sorted(p for env in ("panel", "local") for p in
                 glob.glob(os.path.join(os.path.dirname(__file__), "golden", env, "*.json")))


@pytest.mark.parametrize("path", _GOLDEN, ids=lambda p: f"{os.path.basename(os.path.dirname(p))}-{os.path.basename(p)[:-5]}")
def test_score_breakdown_and_table_say_the_same_figure(path):
    """IDXX: «ROE 70.6%» en el desglose de la puntuación frente a «70.67%» en la tabla: una sola precisión (la de la
    tabla, como las tarjetas y las cifras clave de R3)."""
    with open(path, encoding="utf-8") as fh:
        a = json.load(fh)
    d = a.get("display")
    if not d:
        pytest.skip("sin display")
    rows = {r["label"]: r["value"] for s in d["sections"].values() if isinstance(s, dict)
            for r in s.get("rows") or [] if r.get("state") == "con_dato"}
    bad = []
    for cat in (a.get("score") or {}).get("breakdown", {}).values() if isinstance(a.get("score"), dict) else []:
        for x in (cat or {}).get("adjustments") or []:
            m, v = x.get("metric"), x.get("value")
            if m in ("ROE", "ROA", "Margen neto", "Margen operativo") and m in rows and isinstance(v, str) \
                    and v.endswith("%") and v != rows[m]:
                bad.append(f"{m}: {v} en la puntuación, {rows[m]} en la tabla")
    assert not bad, "\n".join(bad)
