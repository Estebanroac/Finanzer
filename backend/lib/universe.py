"""
Rediseño E2b (Task 1): universo de valores de la portada (tendencias del día) y de los rivales preferentes: el S&P 500
(instantánea fechada de la tabla pública de constituyentes) más los ADR principales de `market.universe.adrs`, con el
sector GICS y la industria de Damodaran (la misma clasificación que la referencia del sector, industry_bench.firm).

El archivo config/universe.tsv lo genera tools/build_universe.py (herramienta local, con red); la app solo lo lee, una
vez por proceso. Su cabecera dice la fecha y la fuente. Símbolos en formato Yahoo (BRK-B, no BRK.B).
"""
import os
import re
import threading
from typing import Any, Dict, List, Optional

import names

UNIVERSE_FILE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config",
                                              "universe.tsv"))
COLUMNS = ("symbol", "name", "origin", "gics_sector", "damodaran_industry", "cik", "damodaran_region")
_HEADER = re.compile(r"#\s*GENERADO por \S+ el (\d{4}-\d{2}-\d{2}) desde (\S+)")

_state: Dict[str, Any] = {}
_lock = threading.Lock()


def norm_symbol(symbol: Optional[str]) -> str:
    """Formato de Yahoo: mayúsculas y la clase con guion (BRK.B -> BRK-B). V6 (B6): solo las clases conocidas
    (`market.universe.share_classes`); un sufijo de bolsa se queda con su punto (BARC.L, MC.PA, 7203.T)."""
    from settings import cfg
    sym = str(symbol or "").strip().upper()
    head, dot, tail = sym.rpartition(".")
    if dot and head and tail in cfg("market.universe.share_classes"):
        return f"{head}-{tail}"
    return sym


def _read() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    date = source = None
    if os.path.isfile(UNIVERSE_FILE):
        with open(UNIVERSE_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if line.startswith("#"):
                    m = _HEADER.match(line)
                    if m:
                        date, source = m.group(1), m.group(2)
                    continue
                if not line or line.startswith("symbol\t"):
                    continue
                vals = (line.split("\t") + [""] * len(COLUMNS))[:len(COLUMNS)]
                row = {k: (v.strip() or None) for k, v in zip(COLUMNS, vals)}
                row["symbol"] = norm_symbol(row["symbol"])
                # P8: nombre corto para mostrar (sin forma jurídica); "name" sigue siendo el legal
                row["display_name"] = names.company(row["name"])
                rows.append(row)
    return {"rows": rows, "by_symbol": {r["symbol"]: r for r in rows}, "date": date, "source": source}


def _data() -> Dict[str, Any]:
    with _lock:
        if not _state:
            _state.update(_read())
        return _state


def reset() -> None:
    """Olvida el archivo leído (tests)."""
    with _lock:
        _state.clear()


def load() -> List[Dict[str, Any]]:
    return list(_data()["rows"])


def get(symbol: Optional[str]) -> Optional[Dict[str, Any]]:
    return _data()["by_symbol"].get(norm_symbol(symbol))


def symbols(origin: Optional[str] = None) -> List[str]:
    return [r["symbol"] for r in _data()["rows"] if origin is None or r["origin"] == origin]


def by_industry(industry: str) -> List[str]:
    return [r["symbol"] for r in _data()["rows"] if r["damodaran_industry"] == industry]


def meta() -> Dict[str, Any]:
    d = _data()
    return {"date": d["date"], "source": d["source"], "count": len(d["rows"])}
