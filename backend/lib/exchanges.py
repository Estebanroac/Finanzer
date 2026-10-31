"""Rediseño E2a: nombre legible de la bolsa a partir del código del proveedor (config/market.toml [exchanges])."""
import logging
from typing import Optional

from settings import cfg

logger = logging.getLogger(__name__)


def name(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    out = (cfg("market.exchanges") or {}).get(str(code))
    if out is None:
        logger.info(f"[exchanges] código sin nombre: {code}")
        return str(code)
    return out
