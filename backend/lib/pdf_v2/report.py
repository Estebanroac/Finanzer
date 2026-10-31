"""
Rediseño E5: ensamblado del informe PDF nuevo.

    build_pdf(analysis, prices=None, today=None) -> bytes

`analysis` es la salida de /api/analysis (con `display`); `prices`, la de GET /api/v2/prices/{symbol} (serie de la
empresa, del S&P 500 y del ETF de su sector) o None si no llegó: la portada lo dice en el hueco de la gráfica.
`segments` (GET /api/v2/segments, E2b) y `peers` (rivales en caché, E2b) son opcionales: sin ellos, su bloque dice
el motivo.
`today` fija la fecha del informe (pruebas y golden). Nada se recalcula: el informe maqueta `display`.
"""
import io
from datetime import date
from typing import Any, Dict, Optional

from reportlab.platypus import PageBreak

from numfmt import date_long
from . import chapters as C
from . import cover as CV
from . import methodology as M
from .doc import DocMeta, ReportDoc, start_on


def build_pdf(analysis: Dict[str, Any], prices: Optional[Dict[str, Any]] = None,
              segments: Optional[Dict[str, Any]] = None, peers: Optional[Dict[str, Any]] = None,
              today: Optional[date] = None) -> bytes:
    a = analysis
    prof = a.get("profile") or {}
    sym = a.get("symbol") or ""
    meta = DocMeta(name=prof.get("name") or sym, symbol=sym,
                   report_date=date_long((today or date.today()).isoformat()), data_note=CV.data_note(a),
                   title=f"Informe Finanzer {sym}")
    ctx = {"prices": prices, "segments": segments, "peers": peers}
    buf = io.BytesIO()
    doc = ReportDoc(buf, meta)
    story = [*CV.cover_story(a, prices), start_on("index"), PageBreak(),
             *CV.index_story(a), *C.chapters(a, ctx), *M.methodology(a, ctx), *M.annex(a), *M.glossary()]
    doc.render(story)
    return buf.getvalue()
