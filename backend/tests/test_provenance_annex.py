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
