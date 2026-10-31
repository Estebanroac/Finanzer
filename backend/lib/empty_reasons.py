"""
F10 · B1 (escaneo del modelo general, 28-oct-2026: 289 vacíos sin motivo en 97 empresas, el 59 % en 10 campos): ningún
vacío se muestra sin motivo. Una sola regla, aquí, para la puntuación (financial_ratios.CategoryCoverage) y para el
display (web y PDF, `fill_display`):

- si el denominador de la métrica es ≤ 0 (patrimonio, beneficio, FCF, EBITDA, FFO), la métrica no es significativa
  («n. s.») y lo dice: «patrimonio negativo», «beneficio negativo»…;
- si falta el denominador, «sin dato» y qué falta;
- si no, el motivo que ya trae el análisis (`<clave>_reason` de key_metrics) o, como último recurso, que la fuente no
  da la cifra.

`reason(metric, inputs)` -> (estado, motivo) o None si la regla no decide. `inputs`: ratios y key_metrics del análisis
(o el contexto de la puntuación), donde están las entradas de cada denominador.
"""
import contextvars
from typing import Any, Dict, Iterable, Optional, Tuple

from historical_metrics import is_anomalous_not_significant

NOT_SIGNIFICANT, NO_DATA, NOT_APPLICABLE = "no_significativo", "sin_dato", "no_aplica"
EMPTY_STATES = (NOT_APPLICABLE, NO_DATA, NOT_SIGNIFICANT)
GENERIC = "la fuente no da la cifra"

# Denominador → (entradas donde buscarlo, en orden; motivo si es ≤ 0; motivo si falta).
_DENOMINATORS: Dict[str, Tuple[Tuple[str, ...], str, str]] = {
    "equity": (("common_equity", "total_equity"), "patrimonio negativo", "sin el patrimonio en las fuentes"),
    "earnings": (("net_income",), "beneficio negativo", "sin el beneficio neto en las fuentes"),
    "fcf": (("free_cash_flow", "fcf"), "flujo de caja libre negativo", "sin el flujo de caja libre en las fuentes"),
    "ebitda": (("ebitda",), "EBITDA negativo", "sin el EBITDA en las fuentes"),
    "ffo": (("ffo",), "FFO negativo", "sin el FFO en las fuentes"),
}
# Métrica (nombre de la puntuación o clave del display) → su denominador.
_METRICS: Dict[str, str] = {
    "ROE": "equity", "roe": "equity", "D/E": "equity", "de": "equity", "debt_to_equity": "equity",
    "P/E": "earnings", "pe": "earnings", "pe_normalized": "earnings", "FCF / beneficio neto": "earnings",
    "fcf_to_net_income": "earnings", "payout_ratio": "earnings",
    "P/FCF": "fcf", "pfcf": "fcf", "p_fcf": "fcf", "p_fcf_normalized": "fcf",
    "EV/EBITDA": "ebitda", "ev_ebitda": "ebitda", "Deuda neta/EBITDA": "ebitda", "net_debt_to_ebitda": "ebitda",
    "P/FFO": "ffo", "p_ffo": "ffo", "Payout sobre FFO": "ffo", "ffo_payout": "ffo",
}
# Sin denominador que mirar: lo que falta, dicho para el lector.
_MISSING: Dict[str, str] = {
    "Cobertura de intereses": "la empresa no presenta gasto por intereses en sus estados",
    "interest_coverage": "la empresa no presenta gasto por intereses en sus estados",
    "dividend_yield": "la fuente no da dividendo por acción",
    "fcf_yield": "sin el flujo de caja libre en las fuentes",
    "FCF": "sin el flujo de caja libre en las fuentes",
    "revenue_growth": "sin ingresos de los ejercicios de la ventana",
}

# La puntuación fija aquí sus entradas (calculate_score_v2) y CategoryCoverage las lee al registrar un componente.
INPUTS: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar("empty_reasons_inputs", default={})


def _first(inputs: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    for k in keys:
        v = inputs.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def reason(metric: str, inputs: Optional[Dict[str, Any]] = None) -> Optional[Tuple[str, str]]:
    """(estado, motivo) de una métrica vacía según su denominador; None si la regla no decide."""
    inputs = INPUTS.get() if inputs is None else inputs
    den = _DENOMINATORS.get(_METRICS.get(metric, ""))
    if den is not None:
        keys, negative, missing = den
        v = _first(inputs, keys)
        if v is None:
            return NO_DATA, missing
        if v <= 0:
            return NOT_SIGNIFICANT, negative
        return None
    if metric in _MISSING:
        return NO_DATA, _MISSING[metric]
    return None


def for_component(name: str, inputs: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """El de un componente de la puntuación sin dato y sin motivo: la regla o, si no decide, el genérico."""
    return reason(name, inputs) or (NO_DATA, GENERIC)


# ── El display (web y PDF) ──
# Campos de un bloque que no son su motivo (rótulos, cifras, tono): lo que no esté aquí y sea texto, sí lo es.
# La línea de referencia (`bench`) y la lectura sí pueden llevarlo: la tarjeta de lo que no aplica lo dice allí.
_NOT_REASON = {"key", "label", "title", "value", "value_txt", "state", "tone", "unit", "pill", "kicker", "kind",
               "subtitle", "delta", "gap", "format", "fmt", "role", "method", "zone", "basis", "higher_is_better"}
_GENERIC_TEXT = ("—", "-", "n/a", "na", "no aplica", "sin dato", "no significativo", "n. s.", "n.s.")
MIN_REASON_CHARS = 8


def has_reason(node: Dict[str, Any]) -> bool:
    for k, v in node.items():
        if k in _NOT_REASON or not isinstance(v, str):
            continue
        t = v.strip()
        if len(t) >= MIN_REASON_CHARS and t.lower().rstrip(".") not in _GENERIC_TEXT and any(c.isalpha() for c in t):
            return True
    return False


def analysis_inputs(a: Dict[str, Any]) -> Dict[str, Any]:
    return {**(a.get("ratios") or {}), **(a.get("key_metrics") or {})}


def fill_display(display: Any, a: Dict[str, Any], na_text: Optional[str] = None) -> int:
    """Da su motivo (`text`) a cada bloque vacío del display que no lo tenga; si el denominador es ≤ 0, el bloque pasa
    a «no significativo». Lo que no aplica dice a qué no aplica (`na_text`). Devuelve cuántos tocó."""
    inputs = analysis_inputs(a)
    km = a.get("key_metrics") or {}
    # Los motivos de la puntuación, por el nombre del componente («Retorno total» → «Retorno total por acción»)
    scored: Dict[str, str] = {}
    for c in (a.get("score_coverage") or {}).values():
        for d in ((c or {}).get("missing_reasons"), (c or {}).get("not_significant"), (c or {}).get("not_applicable")):
            scored.update({k: v for k, v in (d or {}).items() if isinstance(v, str) and v.strip()})

    def by_label(label: str) -> Optional[str]:
        return next((v for k, v in sorted(scored.items(), key=lambda kv: -len(kv[0]))
                     if label and (label == k or label.startswith(k + " "))), None)
    n = [0]

    def walk(o):
        if isinstance(o, dict):
            if o.get("state") in EMPTY_STATES and not has_reason(o):
                key = o.get("key") or ""
                r = (NOT_APPLICABLE, na_text) if o["state"] == NOT_APPLICABLE and na_text else reason(key, inputs)
                own = km.get(f"{key}_reason") if key else None
                if r is not None and r[0] == NOT_SIGNIFICANT and o["state"] == NO_DATA:
                    o["state"] = NOT_SIGNIFICANT
                first = r[1] if r is not None and r[0] != NO_DATA else None
                o["text"] = first or by_label(o.get("label") or "") or (own if isinstance(own, str) and own else None) \
                    or (r[1] if r is not None else None) or GENERIC
                if o["state"] == NO_DATA and is_anomalous_not_significant(o["text"]):
                    o["state"] = NOT_SIGNIFICANT     # F10: crecimiento desde una base anómala sin serie larga robusta
                o["text"] = o["text"][:1].upper() + o["text"][1:]
                n[0] += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(display)
    return n[0]
