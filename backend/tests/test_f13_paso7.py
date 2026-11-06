"""
F13 · paso 7 (revisión de 110 empresas, familia E): el perímetro corta la historia larga (GE), el FFO resta la venta de
participaciones inmobiliarias (PSA) y parte del beneficio continuado (CCI), y la conciliación con EDGAR no falla por un
informe que aún no le ha llegado (PLD). Cifras del banco congelado del 5-nov-2026.
"""
import perimeter
import reit_ffo


def _hist():
    ends = [f"{y}-12-31" for y in range(2010, 2026)]
    return {"revenue": {"values": [{"fy_end": e, "value": 100.0} for e in ends]},
            "net_income": {"values": [{"fy_end": e, "value": 10.0} for e in ends]}, "source": "EDGAR"}


def test_big_restatement_cuts_the_long_history():
    """GE: −62 % al quitar GE HealthCare y GE Vernova; lo anterior a 2022 es el conglomerado."""
    h = perimeter.homogeneous_history(_hist(), {"history_break": "2022-12-31"})
    assert [v["fy_end"][:4] for v in h["revenue"]["values"]] == ["2022", "2023", "2024", "2025"]
    assert h["source"] == "EDGAR" and h["_perimeter_cut"] == "2022-12-31"


def test_without_break_the_history_is_the_same():
    h = _hist()
    assert perimeter.homogeneous_history(h, {"history_break": None}) is h
    assert perimeter.homogeneous_history(h, None) is h


def test_gain_on_selling_a_real_estate_stake_is_not_ffo():
    """PSA 2022: 2.129 M$ por PS Business Parks (concepto estándar); SPG, en minoristas, con su concepto propio, no."""
    assert reit_ffo.item_of("us-gaap_EquityMethodInvestmentRealizedGainLossOnDisposal") == reit_ffo.GAINS
    assert reit_ffo.item_of("spg_GainLossOnDisposalExchangeOrEvaluationOfEquityInterests") is None


def _facts(ocf_rows):
    return {"facts": {"us-gaap": {
        "Assets": {"units": {"USD": [{"end": "2025-12-31", "val": 1e11, "filed": "2026-02-13"}]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            {"start": s, "end": e, "val": v, "filed": f, "form": "10-Q", "accn": f"a-{e}"} for s, e, v, f in ocf_rows]}}}}}


def _entry(start, end, ocf, filed):
    return {"start": start, "end": end, "filed": filed, "accn": f"x-{end}",
            "lines": [{"concept": "us-gaap_NetCashProvidedByUsedInOperatingActivities", "value": ocf}]}


def test_statement_newer_than_edgar_is_pending_not_missing():
    """PLD: el 10-Q nuevo llega a la fuente antes que a companyfacts; el FFO no puede salir o no según el día."""
    f = _facts([("2025-01-01", "2025-12-31", 5.0e9, "2026-02-13"), ("2025-01-01", "2025-09-30", 3.85e9, "2025-10-28")])
    entries = [_entry("2025-01-01", "2025-12-31", 5.0e9, "2026-02-13"),
               _entry("2026-01-01", "2026-09-30", 4.39e9, "2026-10-29"),
               _entry("2025-01-01", "2025-09-30", 3.85e9, "2025-10-28")]
    r = reit_ffo._reconcile(f, entries, 7)
    assert r["status"] == "conciliado_parcial" and "2026-10-29" in r["detail"][1]["pending"]


def test_old_statement_missing_from_edgar_still_fails():
    f = _facts([("2025-01-01", "2025-12-31", 5.0e9, "2026-02-13")])
    entries = [_entry("2025-01-01", "2025-12-31", 5.0e9, "2026-02-13"),
               _entry("2025-01-01", "2025-09-30", 3.85e9, "2025-10-28")]
    assert reit_ffo._reconcile(f, entries, 7)["status"] == "sin_hecho_edgar"


def test_mismatch_still_fails():
    f = _facts([("2025-01-01", "2025-12-31", 5.0e9, "2026-02-13")])
    assert reit_ffo._reconcile(f, [_entry("2025-01-01", "2025-12-31", 4.0e9, "2026-02-13")], 7)["status"] == \
        "no_conciliado"
