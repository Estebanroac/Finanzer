"""
F8 · E6 (auditoría externa del 26-oct-2026): frescura de los estados.

Si EDGAR tiene un 10-Q (o un 10-K) de un periodo posterior al corte del análisis, los estados están desfasados y se
dice; con más de `stale_coverage_days` días desde el cierre del corte, la cobertura de datos baja a «media».
Casos: AMZN y BA, con el corte de Yahoo al 31-mar-2026 y sus 10-Q del 30-jun-2026 en EDGAR desde el 31-jul y el
28-jul (registro F8_INDEPENDIENTES §E6).
"""
import datetime as _dt

import edgar_backup
from valuation_confidence import coverage_dimension


def _f(form, report, filed, accn="0001-26-1", items=None):
    return {"form": form, "reportDate": report, "filingDate": filed, "accessionNumber": accn, "isXBRL": True,
            "items": items}


AMZN = [_f("8-K", "2026-09-14", "2026-09-14", items="7.01"), _f("10-Q", "2026-06-30", "2026-07-31", "0001018724-26-26"),
        _f("8-K", "2026-07-30", "2026-07-30", items="2.02,9.01"), _f("10-Q", "2026-03-31", "2026-05-01")]


def test_amzn_desfasado_y_cobertura_media():
    s = edgar_backup.staleness("2026-03-31", AMZN, _dt.date(2026, 10, 26))
    assert s["status"] == "desfasado" and s["days_since_cut"] == 209
    assert s["edgar_latest"]["form"] == "10-Q" and s["edgar_latest"]["report_date"] == "2026-06-30"
    assert s["coverage_capped"] is True
    assert "al 30 de junio de 2026" in s["text"] and "209 días" in s["text"]


def test_al_dia_si_el_corte_es_el_ultimo_10q():
    s = edgar_backup.staleness("2026-06-30", AMZN, _dt.date(2026, 10, 26))
    assert s["status"] == "al_dia" and s["coverage_capped"] is False and s["text"] is None


def test_un_8k_no_desfasa():
    """El comunicado de resultados (8-K 2.02) no trae estados: se avisa aparte (pending_results), no desfasa."""
    fl = [_f("8-K", "2026-10-23", "2026-10-23", items="2.02"), _f("10-Q", "2026-06-30", "2026-07-31")]
    assert edgar_backup.staleness("2026-06-30", fl, _dt.date(2026, 10, 26))["status"] == "al_dia"


def test_desfasado_reciente_no_baja_la_cobertura():
    """Con un 10-Q posterior pero menos de 100 días desde el cierre del corte: desfasado, sin bajar la cobertura."""
    fl = [_f("10-Q", "2026-06-30", "2026-07-20")]
    s = edgar_backup.staleness("2026-04-30", fl, _dt.date(2026, 7, 25))
    assert s["status"] == "desfasado" and s["days_since_cut"] == 86 and s["coverage_capped"] is False


def test_tolerancia_de_fechas():
    """Yahoo fecha el trimestre a fin de mes y EDGAR al cierre real (JNJ: 28-jun): no es un periodo posterior."""
    fl = [_f("10-Q", "2026-06-28", "2026-07-20")]
    assert edgar_backup.staleness("2026-06-30", fl, _dt.date(2026, 10, 26))["status"] == "al_dia"


def test_sin_edgar_sin_dato():
    s = edgar_backup.staleness("2026-03-31", None, _dt.date(2026, 10, 26))
    assert s["status"] == "sin_dato" and s["coverage_capped"] is False


def test_cobertura_media_con_estados_desfasados():
    cov = {"solidez": {"components": 4, "evaluated": 4}, "rentabilidad": {"components": 5, "evaluated": 5}}
    assert coverage_dimension(cov, [])["level"] == "alta"
    s = edgar_backup.staleness("2026-03-31", AMZN, _dt.date(2026, 10, 26))
    d = coverage_dimension(cov, [], staleness=s)
    assert d["level"] == "media" and any("desfasados" in r for r in d["reasons"])
    # Nunca sube: con cobertura baja sigue baja.
    low = {"solidez": {"components": 10, "evaluated": 3}}
    assert coverage_dimension(low, [], staleness=s)["level"] == "baja"


def test_aviso_de_estados_desfasados_en_lugar_de_resultados_pendientes():
    import display
    s = edgar_backup.staleness("2026-03-31", AMZN, _dt.date(2026, 10, 26))
    pr = {"date": "2026-07-31", "form": "10-Q", "accn": "x", "as_of": "2026-03-31"}
    notes = display.data_notices({"data_provenance": {"staleness": s, "pending_results": pr}})
    assert notes[0].startswith("Estados desfasados") and "10-Q al 30 de junio de 2026" in notes[0]
    assert not any("publicó resultados" in n for n in notes)
    # Al día: el aviso de resultados pendientes (un 8-K posterior) sigue como antes.
    s = edgar_backup.staleness("2026-06-30", AMZN, _dt.date(2026, 10, 26))
    notes = display.data_notices({"data_provenance": {"staleness": s, "pending_results": pr}})
    assert any("publicó resultados" in n for n in notes)
