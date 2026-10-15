"""
Afirmaciones declaradas por los generadores de texto (fase 1 del plan de fiabilidad, guardián narrativo).

Cada generador que escribe una frase con una afirmación sobre la empresa ("EBIT negativo", "caja neta", "se
contraen un 5.0%"…) la declara junto al texto: `record(texto, claim(...), ...)`. El guardián
(`tests/guardian.py`) comprueba cada afirmación contra el dato estructurado del análisis y rastrea cada palabra de
afirmación del informe (web y PDF) hasta una frase con afirmaciones declaradas.

Inerte en producción: sin un colector activo (`collecting()`, solo en los tests), `record` devuelve el texto tal
cual y no guarda nada. No cambia ninguna salida.
"""
import contextlib
import contextvars
import functools
from typing import Any, Callable, Dict, List, Optional

_COLLECTOR: contextvars.ContextVar = contextvars.ContextVar("finanzer_claims", default=None)


def claim(kind: str, **data: Any) -> Dict[str, Any]:
    """Afirmación estructurada: `kind` (ver tests/guardian.py, PREDICATES) y sus datos (valor declarado, cita…)."""
    return {"kind": kind, **data}


def active() -> bool:
    return _COLLECTOR.get() is not None


def record(text: Optional[str], *claims: Dict[str, Any], source: str = "") -> Optional[str]:
    """Registra `text` con sus afirmaciones si hay colector activo. Devuelve `text` sin cambios."""
    sink = _COLLECTOR.get()
    if sink is not None and text:
        sink.append({"text": str(text), "claims": [c for c in claims if c], "source": source})
    return text


def declares(builder: Callable[..., List[Dict[str, Any]]], source: str = ""):
    """Decorador para los lectores que devuelven (etiqueta, tono, frase, ...): registra la etiqueta y la frase con
    las afirmaciones que `builder(*args, **kwargs, result=...)` construye con los mismos argumentos."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            res = fn(*args, **kwargs)
            if res is not None and active():
                cl = builder(*args, result=res, **kwargs) or []
                src = source or fn.__name__
                for txt in res[:3:2] if isinstance(res, tuple) else ():
                    record(txt, *cl, source=src)
            return res
        return wrapper
    return deco


@contextlib.contextmanager
def collecting():
    """Activa el colector (solo tests). Devuelve la lista de registros {text, claims, source}."""
    sink: List[Dict[str, Any]] = []
    token = _COLLECTOR.set(sink)
    try:
        yield sink
    finally:
        _COLLECTOR.reset(token)
