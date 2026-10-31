"""
El D&A del EBITDA sin amortizaciones de activos operativos recurrentes (escalera de márgenes de NFLX, 30-oct).

NFLX, ingresos TTM 49,73 B$: margen bruto 50,7 % y margen EBITDA 67,3 %. El D&A sumado era el de Yahoo (17,92 B$), y su
«Amortization Of Intangibles» (17,53) es la amortización del contenido: un coste operativo recurrente que va en el coste
de ventas y se paga cada año. TTWO, lo mismo con el software capitalizado (1,17 de 1,33).

Los conceptos de D&A de EDGAR no sirven como total (36 emisores solo etiquetan `Depreciation`; MCD usa el paraguas para una
partida parcial). Pero el desglose de Yahoo cuadra con EDGAR en casi todos: su amortización de intangibles es la de los
intangibles adquiridos (`AmortizationOfIntangibleAssets`). Regla (decisión del PM, 30-oct):
  · respaldo de EDGAR de la amortización = el mayor de `AmortizationOfIntangibleAssets` y paraguas − depreciación;
  · la amortización de Yahoo sin ese respaldo, si pasa de la materialidad de N1 (`nonoperating_tolerance_revenue` de los
    ingresos), sale del D&A del EBITDA y se nombra;
  · por debajo, no se toca y se declara «no verificable» (puede ser etiquetado parcial de EDGAR: KDP, MTD…).
"""
import edgar_primary
import sec_edgar as edgar


def _f(start, end, val, filed, form="10-K", accn="k"):
    out = {"end": end, "val": val, "filed": filed, "form": form, "accn": accn}
    if start:
        out["start"] = start
    return out


def _ed(concepts):
    facts = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [_f(None, "2025-12-31", 10, "2026-02-01")]}},
                                   **concepts}}}
    return {"status": "ok", "facts_status": "ok", "facts": edgar._index_facts(facts)}


def _fy(concept, value):
    return {concept: {"units": {"USD": [_f("2025-01-01", "2025-12-31", value, "2026-02-01")]}}}


def _info(da, dep, amort, rev=49730.0, ebit=15565.0):
    info = {"symbol": "ZZZ", "currency": "USD", "_as_of": {"type": "ttm", "date": "2025-12-31", "fields": {}},
            "_provenance": {}, "totalRevenue": rev, "operatingIncome": ebit, "depreciation": da,
            "ebitda": ebit + da, "_da_split": {"total": da, "depreciation": dep, "amortization": amort}}
    for k in ("operatingIncome", "depreciation", "ebitda", "totalRevenue"):
        info["_as_of"]["fields"][k] = {"period_end": "2025-12-31", "period_type": "ttm"}
    return info


def _log(log):
    return log.get("da") or {}


def test_content_amortization_without_edgar_support_leaves_the_ebitda():
    """NFLX: EDGAR presenta 0,39 de D&A en total (paraguas) y nada de intangibles adquiridos."""
    ed = _ed(_fy("DepreciationDepletionAndAmortization", 392.0))
    info = _info(17921.0, 392.0, 17529.0)
    log = edgar_primary.apply(info, ed)
    assert info["depreciation"] == 392.0
    assert info["ebitda"] == 15565.0 + 392.0
    d = _log(log)
    assert d["status"] == "excluido" and d["excluded"] == 17529.0
    assert "amortización de activos operativos recurrentes" in d["reason"]
    assert info["_provenance"]["depreciation"]["source"] == "derivado"


def test_acquired_intangibles_amortization_with_edgar_support_stays():
    """ABBV: la amortización de Yahoo (7,09) es la de EDGAR (AmortizationOfIntangibleAssets 7,09)."""
    ed = _ed({**_fy("Depreciation", 780.0), **_fy("AmortizationOfIntangibleAssets", 7090.0)})
    info = _info(7870.0, 780.0, 7090.0, rev=60000.0, ebit=15000.0)
    log = edgar_primary.apply(info, ed)
    assert info["depreciation"] == 7870.0 and info["ebitda"] == 15000.0 + 7870.0
    assert _log(log)["status"] == "respaldado"


def test_unsupported_amortization_below_materiality_is_declared_not_verifiable():
    """MTD: 0,05 sin respaldo sobre 4 de ingresos (1,2 %): puede ser etiquetado parcial; no se toca."""
    ed = _ed({**_fy("Depreciation", 50.0), **_fy("AmortizationOfIntangibleAssets", 30.0)})
    info = _info(130.0, 50.0, 80.0, rev=4000.0, ebit=1200.0)
    log = edgar_primary.apply(info, ed)
    assert info["depreciation"] == 130.0
    d = _log(log)
    assert d["status"] == "no_verificable" and d["unsupported"] == 50.0


def test_umbrella_above_the_tag_is_the_support():
    """HON: el paraguas − la depreciación (1,17) respalda más que la etiqueta (0,56): manda el mayor."""
    ed = _ed({**_fy("DepreciationDepletionAndAmortization", 1370.0), **_fy("AmortizationOfIntangibleAssets", 560.0)})
    info = _info(910.0, 200.0, 710.0, rev=40000.0, ebit=8000.0)
    log = edgar_primary.apply(info, ed)
    assert info["depreciation"] == 910.0 and _log(log)["status"] == "respaldado"


def test_without_edgar_tags_the_source_stays_not_verifiable():
    ed = _ed({})
    info = _info(880.0, 190.0, 690.0, rev=17000.0, ebit=5000.0)
    log = edgar_primary.apply(info, ed)
    assert info["depreciation"] == 880.0 and _log(log)["status"] == "no_verificable"


def test_without_the_split_of_the_source_nothing_is_done():
    ed = _ed(_fy("DepreciationDepletionAndAmortization", 392.0))
    info = _info(17921.0, None, None)
    log = edgar_primary.apply(info, ed)
    assert info["depreciation"] == 17921.0 and not _log(log)


def test_ttm_keeps_the_split_of_the_da_of_the_cut():
    import pandas as pd
    from ttm import build_ttm

    def q(rows):
        return pd.DataFrame(rows, index=pd.to_datetime(Q4)).T
    Q4 = ["2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31"]
    inc = q({"Total Revenue": [12, 12, 12, 13], "Net Income": [3, 3, 3, 3]})
    cf = q({"Operating Cash Flow": [5, 5, 5, 5], "Depreciation And Amortization": [4.4, 4.4, 4.3, 4.8],
            "Depreciation": [0.1, 0.1, 0.1, 0.1], "Amortization Of Intangibles": [4.3, 4.3, 4.2, 4.7]})
    bs = q({"Total Assets": [90, 80, 70, 60]})
    sp = build_ttm(inc, cf, bs)["da_split"]
    assert round(sp["total"], 6) == 17.9 and round(sp["depreciation"], 6) == 0.4 and round(sp["amortization"], 6) == 17.5
    del cf  # sin la fila de amortización no hay desglose
    cf2 = q({"Operating Cash Flow": [5, 5, 5, 5], "Depreciation And Amortization": [1, 1, 1, 1]})
    assert "da_split" not in build_ttm(inc, cf2, bs)


# ── invariante del mecanismo (model_invariants.ebitda_sin_amortizacion_operativa) ──

def _a(da, rev=49730.0, arch="MATURE"):
    return {"classification": {"archetype": arch}, "key_metrics": {"revenue": rev},
            "data_provenance": {"edgar": {"primary": ({"da": da} if da is not None else {})}}}


def test_invariant_ok_when_excluded_supported_or_declared():
    import model_invariants as inv
    for da in ({"status": "excluido", "excluded": 17529.0}, {"status": "respaldado"},
               {"status": "no_verificable", "unsupported": 50.0, "support": 30.0},
               {"status": "no_verificable", "unsupported": 17529.0}):          # sin etiquetas en EDGAR: declarado
        assert inv.ebitda_sin_amortizacion_operativa(_a(da), {})["state"] == inv.OK, da


def test_invariant_flags_material_unsupported_amortization_left_in_the_ebitda():
    import model_invariants as inv
    r = inv.ebitda_sin_amortizacion_operativa(_a({"status": "no_verificable", "unsupported": 17529.0,
                                                 "support": 0.0}), {})
    assert r["state"] == inv.VIOLATION and "sin respaldo" in r["violations"][0]["detail"]


def test_invariant_not_evaluable_without_split_and_not_applicable_to_financials():
    import model_invariants as inv
    assert inv.ebitda_sin_amortizacion_operativa(_a(None), {})["state"] == inv.NOT_EVALUABLE
    assert inv.ebitda_sin_amortizacion_operativa(_a(None, arch="FINANCIAL"), {})["state"] == inv.NOT_APPLICABLE


def test_financials_are_not_touched():
    """MTB (banco): el EBITDA no aplica a una financiera; su D&A no se toca."""
    ed = _ed(_fy("DepreciationDepletionAndAmortization", 40.0))
    info = _info(160.0, 40.0, 120.0, rev=1600.0, ebit=500.0)
    info.update(sector="Financial Services", industry="Banks - Regional")
    log = edgar_primary.apply(info, ed)
    assert info["depreciation"] == 160.0 and not _log(log)


# ── filas anuales: la misma regla por ejercicio (PM, 30-oct: NFLX no puede enseñar 32 % en el TTM y 67 % en su historia)

def _fy2(concept, values):
    return {concept: {"units": {"USD": [_f(f"{2025 - i}-01-01", f"{2025 - i}-12-31", v, f"{2026 - i}-02-01", "10-K",
                                           f"k{i}") for i, v in enumerate(values)]}}}


def test_annual_rows_leave_the_unsupported_amortization_of_each_year():
    ed = _ed(_fy2("DepreciationDepletionAndAmortization", [333.0, 329.0]))
    st = {"inc_ends": ["2025-12-31", "2024-12-31"], "cf_ends": ["2025-12-31", "2024-12-31"],
          "revenue": [45183.0, 39001.0], "operating_income": [13499.0, 10684.0], "ebitda": [30255.0, 26315.0],
          "depreciation_amortization": [16756.0, 15630.0], "da_depreciation": [333.0, 329.0],
          "da_amortization": [16422.0, 15302.0]}
    info = _info(17921.0, None, None)
    info["_statements_fy"] = st
    log = edgar_primary.apply(info, ed)
    assert st["depreciation_amortization"] == [16756.0 - 16422.0, 15630.0 - 15302.0]   # el total sin lo quitado
    assert st["ebitda"] == [30255.0 - 16422.0, 26315.0 - 15302.0]
    assert [x["status"] for x in log["da_fy"]] == ["excluido", "excluido"]


def test_annual_rows_without_edgar_for_a_year_are_declared_not_verifiable():
    ed = _ed(_fy2("DepreciationDepletionAndAmortization", [333.0]))
    st = {"inc_ends": ["2025-12-31", "2024-12-31"], "cf_ends": ["2025-12-31", "2024-12-31"],
          "revenue": [45183.0, 39001.0], "operating_income": [13499.0, 10684.0], "ebitda": [30255.0, 26315.0],
          "depreciation_amortization": [16756.0, 15630.0], "da_depreciation": [333.0, 329.0],
          "da_amortization": [16422.0, 15302.0]}
    info = _info(17921.0, None, None)
    info["_statements_fy"] = st
    log = edgar_primary.apply(info, ed)
    assert st["ebitda"] == [30255.0 - 16422.0, 26315.0]
    assert [(x["fy_end"], x["status"]) for x in log["da_fy"]] == [("2025-12-31", "excluido"),
                                                                  ("2024-12-31", "no_verificable")]


# ── EV/EBITDA con un EBITDA casi nulo (TTWO: 1035,7x): «> 100x» y la cifra exacta en el detalle; no puntúa distinto ──

def test_ev_ebitda_above_the_cap_is_shown_bounded():
    import numfmt
    assert numfmt.ev_ebitda(1035.75) == "> 100x" and numfmt.ev_ebitda(31.04) == "31.04x"
    assert numfmt.ev_ebitda_detail(1035.75, 0.005) == "cifra exacta 1035.8x: EBITDA casi nulo (0.5% de los ingresos)"
    assert numfmt.ev_ebitda_detail(177.8, 0.30) == "cifra exacta 177.8x: múltiplo extremo"     # PLTR: no es casi nulo
    assert numfmt.ev_ebitda_detail(190.3, use_context=False) == "cifra exacta 190.3x"         # el normalizado de HAS
    assert numfmt.ev_ebitda_detail(99.0) is None


def test_ev_ebitda_score_keeps_its_points_and_shows_the_bound():
    import financial_ratios as fr
    v = fr.score_valoracion(pe=30.0, p_fcf=25.0, ev_ebitda=1035.75, peg=None, sector_pe=25.0, sector_ev_ebitda=16.5,
                            archetype="MATURE")
    adj = next(x for x in v["adjustments"] if x["metric"].startswith("EV/EBITDA"))
    ref = fr.score_valoracion(pe=30.0, p_fcf=25.0, ev_ebitda=99.0, peg=None, sector_pe=25.0, sector_ev_ebitda=16.5,
                              archetype="MATURE")
    assert adj["adjustment"] == next(x for x in ref["adjustments"] if x["metric"].startswith("EV/EBITDA"))["adjustment"]
    assert adj["value"] == "> 100x" and "> 100x" in adj["reason"] and "cifra exacta 1035.8x" in adj["reason"]


def test_ev_ebitda_bound_in_the_display(outputs_by_env):
    import copy
    import main
    from display import build_display
    a = copy.deepcopy(outputs_by_env("panel")["KO"][0])
    a["key_metrics"]["ev_ebitda"], a["key_metrics"]["ebitda_margin"] = 1035.75, 0.005
    D = build_display(a, main._pdf_benchmark(a))
    row = next(r for r in D["sections"]["valuation"]["rows"] if r["key"] == "ev_ebitda")
    assert row["value"] == "> 100x" and "cifra exacta 1035.8x: EBITDA casi nulo" in (row["text"] or "")
    for g in D["charts"]["comparison"]["groups"]:
        for it in g["items"]:
            if it["key"] == "ev_ebitda":
                assert it["value_txt"] == "> 100x"
