"""
Rediseño E5: significado llano de cada métrica para la tabla técnica del PDF.

Las definiciones se escriben una vez, en el frontend (`frontend/src/lib/tooltips.ts`), y
`backend/tools/gen_metric_definitions.py` las vuelca a `backend/assets/metric_definitions.json`
(tests/test_metric_definitions.py falla si el JSON se desincroniza). Aquí solo se leen.
"""
import json
import os
import re
from functools import lru_cache
from typing import Dict, Optional

PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets",
                                     "metric_definitions.json"))


@lru_cache(maxsize=1)
def definitions() -> Dict[str, Dict[str, str]]:
    with open(PATH, encoding="utf-8") as fh:
        return json.load(fh)["definitions"]


def first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.:])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])", (text or "").strip(), maxsplit=1)
    return parts[0] if parts else ""


def meaning(key: str, label: str = "") -> Optional[str]:
    """Primera frase de la descripción de la métrica (como la tabla técnica de la web, E3); None si no hay
    definición para esa clave."""
    d = definitions().get(key or "")
    return first_sentence(d["description"]) if d and d.get("description") else None


def definition(key: str) -> Optional[Dict[str, str]]:
    return definitions().get(key or "")
