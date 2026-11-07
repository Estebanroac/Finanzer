"""
Fase 1 · pendientes de la prueba hacia atrás (decisión del usuario, 7-nov-2026): la «confianza del veredicto» pasa a
«consistencia», con dos niveles y sin el nivel alto.

La prueba hacia atrás (corte 5-nov-2025) mostró que la confianza no ordenaba los aciertos (alta, n = 5): no debe
sugerir una probabilidad de acierto. La consistencia dice solo dos cosas medibles del propio análisis:

  · si los métodos de valoración coinciden (la convergencia de lib/valuation_confidence.py), y
  · si la cobertura de datos es suficiente (su cobertura).

  consistente = los métodos coinciden del todo (convergencia «alta») y la cobertura no es baja;
  mixta       = cualquier otro caso (coincidencia parcial o discrepancia, un solo método, o cobertura baja).

El resto de dimensiones de la confianza (fuente, estabilidad, fuente oficial, tasas base, Ke) siguen en el cálculo
técnico (`confidence`) pero no forman la consistencia ni se muestran como «confianza». Ni la consistencia ni la
confianza mueven el precio (F16) ni la calidad (desde este cambio).
"""
from typing import Any, Dict, List, Optional

LEVELS = ("consistente", "mixta")
TONE = {"consistente": "pos", "mixta": "warn"}
_NAMES = {"DCF": "el DCF directo", "múltiplos frente al sector": "los múltiplos",
          "P/B justificado (Gordon)": "el P/B justificado", "P/B frente al sector": "el P/B del sector"}
_COVERAGE = {"alta": "completa", "media": "suficiente", "baja": "parcial"}


def _pair(conv: Dict[str, Any]) -> str:
    ev = [m for m in conv.get("methods") or [] if m.get("evaluable")]
    return " y ".join(_NAMES.get(m["method"], m["method"]) for m in ev)


def compute(conf: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """{level, tone, phrase, methods: {level, text}, coverage: {level, text}, reasons: [...]} o None sin confianza."""
    c = conf or {}
    dims = c.get("dimensions") or {}
    if not dims:
        return None
    conv, cov = dims.get("convergence") or {}, dims.get("coverage") or {}
    lc, lv = conv.get("level"), cov.get("level")
    pair = _pair(conv)
    if lc == "alta":
        mtxt = f"{pair} coinciden" if pair else "los métodos coinciden"
    elif lc == "media":
        ev = [m for m in conv.get("methods") or [] if m.get("evaluable")]
        dirs = [m.get("direction") for m in ev]
        if len(set(dirs)) > 1 and all(dirs):
            mtxt = " y ".join(f"{_NAMES.get(m['method'], m['method'])} {'la ve ' if i == 0 else ''}{m['direction']}"
                              for i, m in enumerate(ev))
        else:
            mtxt = f"{pair} coinciden en dirección pero no en magnitud" if pair else "los métodos coinciden en parte"
    elif lc == "baja":
        mtxt = f"{pair} discrepan" if pair else "los métodos discrepan"
    else:
        mtxt = "un solo método de valoración evaluable, sin contraste"
    ctxt = f"cobertura de datos {_COVERAGE.get(lv, 'sin medir')}"
    level = "consistente" if (lc == "alta" and lv in ("alta", "media")) else "mixta"
    reasons: List[str] = []
    if lc != "alta":
        reasons.append(mtxt)
    if lv not in ("alta", "media"):
        reasons.append(ctxt)
    # consistente: la cobertura ya es suficiente por definición; la frase dice solo los métodos
    phrase = mtxt if level == "consistente" else "; ".join(reasons)
    return {"level": level, "tone": TONE[level], "phrase": phrase,
            "methods": {"level": lc, "text": mtxt}, "coverage": {"level": lv, "text": ctxt}, "reasons": reasons}


def text(cons: Optional[Dict[str, Any]]) -> Optional[str]:
    """«(consistencia mixta: el DCF directo y los múltiplos discrepan)» para el veredicto."""
    return f"(consistencia {cons['level']}: {cons['phrase']})" if cons and cons.get("level") else None


EXPLAIN = "No es una probabilidad de acierto."
