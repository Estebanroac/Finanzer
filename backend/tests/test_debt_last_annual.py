"""
Fase 3 (T1b): el "último informe anual" de un componente de la deuda (2b, T5) es solo el último.

Con la historia larga de EDGAR, BAC traía una deuda subordinada de 2012 y ASML un arrendamiento operativo de 2023
para cortes de 2026. En producción ya pasaba: el companyfacts vivo trae toda la historia.
"""
import sec_edgar as edgar


def _stock(end, val, form="10-K"):
    return {"end": end, "val": val, "filed": end[:4] + "-12-31", "form": form, "accn": f"x{end}"}


def test_debt_part_last_annual_is_only_the_latest_annual_report():
    """BAC: `SubordinatedDebt` solo hasta 2012. Con la historia larga, el "último anual" no puede ser el de 2012."""
    facts = {"facts": {"us-gaap": {
        "Assets": {"units": {"USD": [_stock("2012-12-31", 1), _stock("2025-12-31", 1)]}},
        "SubordinatedDebt": {"units": {"USD": [_stock("2012-12-31", 12.4)]}}}}}
    assert edgar.debt_part(facts, "subordinated", edgar._date("2026-03-31"), 14, latest_before=True) is None


def test_debt_part_last_annual_still_serves_duk():
    """DUK: arrendamientos solo en el 10-K; el del último 10-K vale para el corte de junio, con aviso de fecha."""
    facts = {"facts": {"us-gaap": {
        "Assets": {"units": {"USD": [_stock("2025-12-31", 1), _stock("2026-06-30", 1, "10-Q")]}},
        "FinanceLeaseLiability": {"units": {"USD": [_stock("2025-12-31", 576)]}}}}}
    r = edgar.debt_part(facts, "finance_leases", edgar._date("2026-06-30"), 14, latest_before=True)
    assert r["value"] == 576 and r["basis"] == "ultimo_anual"
