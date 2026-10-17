"""Fase 6: el anexo técnico dice qué fuente aportó cada campo (data_provenance.fields). Sin red."""
import display


def _a(fields):
    return {"data_provenance": {"fields": {k: {"source": s, "detail": "x"} for k, s in fields.items()}}}


def test_annex_groups_fields_by_source_with_readable_names():
    a = _a({"totalRevenue": "sec_edgar", "operatingIncome": "yfinance_statements",
            "_prior_year.operatingIncome": "yfinance_statements", "netIncome": "yfinance_statements",
            "forwardPE": "finnhub", "_yahoo_ratios.forwardPE": "finnhub", "totalCash": "sin_dato"})
    row = display.provenance_annex(a)
    assert row["label"].startswith("Procedencia de los datos")
    t = row["text"]
    # el mismo dato en dos rutas cuenta una vez; los estados, por número; el resto, con su nombre
    assert "estados de Yahoo (yfinance): 2 campos" in t
    assert "SEC EDGAR: 1 (ingresos)" in t and "Finnhub: 1 (P/E adelantado)" in t
    assert "sin dato utilizable" in t and "caja total" in t
    assert t.index("estados de Yahoo") < t.index("SEC EDGAR") < t.index("Finnhub") < t.index("sin dato")


def test_long_lists_are_cut():
    a = _a({f"f{i}": "finnhub" for i in range(12)})
    assert "y 4 más" in display.provenance_annex(a)["text"]


def test_without_provenance_there_is_no_row():
    assert display.provenance_annex({}) is None


def test_edgar_fiscal_year_backup_has_readable_names():
    a = {"data_provenance": {"edgar": {"backup": {"fy": [
        {"field": "FY.retained_earnings", "fy_end": "2025-12-31", "concept": "us-gaap:RetainedEarningsAccumulatedDeficit"}]}}}}
    row = [r for r in display.official_source_annex(a) if r["label"].startswith("Respaldo")][0]
    assert "beneficios retenidos del ejercicio cerrado el 2025-12-31" in row["text"] and "retained_earnings " not in row["text"]


def test_same_field_under_two_internal_names_counts_once_and_every_fy_row_is_named():
    """Revisión de F6, hallazgo 4: "liquidez corriente" salía dos veces (BRK-B, PGR); capex y amortizaciones de las
    filas anuales, con su código."""
    a = _a({"_yahoo_ratios.currentRatio": "finnhub", "_piotroski_current.current_ratio": "finnhub"})
    assert "Finnhub: 1 (liquidez corriente)" in display.provenance_annex(a)["text"]
    import edgar_backup
    for row in edgar_backup.FY_ROWS:
        assert display._fy_field_name(f"FY.{row}") != row, row
