"""
F14 · paso 1: el par Rf–prima de config/valuation.toml es la fila de su fecha en la hoja mensual de Damodaran
(tests/fixtures/damodaran/erp_by_month.csv, escrita por tools/damodaran_erp.py). Sin red.

El 1-nov-2026 la portada de Damodaran repetía el Rf de octubre (5,29 %) y su hoja decía 4,94 %: copiar a mano la
portada metió 35 pb de más en todo el universo. Si el par se cambia sin pasar por la herramienta, esto falla.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import damodaran_erp as de  # noqa: E402
from settings import cfg  # noqa: E402


def _row(month):
    return next((r for r in de.read_fixture() if r[0] == month), None)


def test_config_pair_is_the_monthly_sheet_row_of_its_date():
    month = cfg("valuation.capm.pair_as_of")
    row = _row(month)
    assert row, f"la hoja mensual no tiene la fila {month}: actualizar con tools/damodaran_erp.py --write"
    assert cfg("valuation.capm.risk_free_rate") == pytest.approx(row[1], abs=1e-6)
    assert cfg("valuation.capm.market_risk_premium") == pytest.approx(row[2], abs=1e-6)


def test_review_dates_follow_the_pair():
    month = cfg("valuation.capm.pair_as_of")
    for name in ("risk_free_rate", "market_risk_premium"):
        assert cfg("review.parameters")[name]["published"] == month


def test_november_2026_uses_the_sheet_not_the_home_page_text():
    # la portada decía 5,29 %; la hoja con la que se calculó la prima del 4,41 %, 4,94 %
    assert _row("2026-11-01")[1:] == (0.0494, 0.0441)
    assert _row("2026-10-01")[1:] == (0.0529, 0.042)


def test_an_rf_repeated_from_the_previous_month_is_flagged():
    assert de.unchanged_rf([("2026-10-01", 0.0529, 0.042), ("2026-11-01", 0.0529, 0.0441)])
    assert not de.unchanged_rf(de.read_fixture())


def test_the_reader_handles_1904_dates(tmp_path):
    import io
    import zipfile
    sheet = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
             '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c></row>'
             '<row r="2"><c r="A2"><v>44865</v></c><c r="B2"><v>0.0494</v></c><c r="C2"><v>0.0441</v></c></row>'
             '</sheetData></worksheet>')
    ss = ('<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
          + "".join(f"<si><t>{t}</t></si>" for t in ("Start of month", "T.Bond Rate",
                                                       "ERP (T12 m with sustainable payout)")) + "</sst>")
    wb = ('<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><workbookPr date1904="1"/>'
          '<sheets><sheet name="Historical ERP" sheetId="1" r:id="rId1"/></sheets></workbook>')
    rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/sharedStrings.xml", ss)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    assert de.monthly_series(buf.getvalue()) == [("2026-11-01", 0.0494, 0.0441)]
