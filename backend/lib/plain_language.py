"""
Motivos en lenguaje llano (etapa 9b): UNA sola tabla de traducción para el PDF y la web.

Los motivos de la confianza del veredicto (lib/valuation_confidence.py) son
técnicos ("sin TTM: estados anuales", "12 campos de Finnhub en lugar de los
estados"…). Para el usuario se traducen con esta tabla; el texto técnico se
conserva como detalle (web: desplegable "Detalle técnico"; PDF: solo en la
sección "Confianza del veredicto").

Cada entrada es (patrón sobre el motivo técnico, texto llano). Texto llano None =
el motivo no se muestra al usuario (queda solo en el detalle técnico). Un motivo
sin entrada se muestra tal cual: tests/test_display.py exige que todos los motivos
de los golden tengan traducción.
"""
import re
from typing import Any, Dict, List, Optional

# Reglas de validación de entrada (lib/validate.py) -> texto llano.
VALIDATION_RULES = {
    "crecimiento_incoherente": ("El crecimiento que reporta la fuente difiere mucho del de los estados anuales; "
                                "se mantiene, pero conviene tomarlo con cautela."),
    "crecimiento_artefacto": ("El crecimiento reportado por la fuente era incoherente y se recalculó con los "
                              "estados (o se descartó si no había estados)."),
    "fcf_le_ocf": "El flujo de caja libre de la fuente era incoherente y se recalculó con los estados.",
    "valor_imposible": "Un dato de la fuente era imposible y se recalculó o se descartó.",
    "margen_fuera_de_rango": "Un margen de la fuente estaba fuera de rango y se descartó.",
    "unidades": "Un dato de la fuente venía en unidades incoherentes y se corrigió o se descartó.",
    "base_de_split": "Los datos del ejercicio anterior no reflejaban un split y se corrigieron.",
    "salto_interanual": "Un dato del ejercicio anterior tenía un salto incoherente y se descartó.",
    "beta_discrepante": ("La beta calculada con dos años de cotizaciones difiere mucho de la del proveedor de datos; "
                         "se usa la calculada."),
}
_VALIDATION_DEFAULT = "Un dato de la fuente no superó la validación y se corrigió o se descartó."

# (patrón, texto llano o None). El orden importa: gana la primera coincidencia.
TABLE = [
    # ── calidad de fuente ──
    (r"^sin TTM: estados anuales",
     "Se usan los estados del último ejercicio anual (pueden tener hasta 12 meses de antigüedad)."),
    (r"^\d+ campos? de Finnhub en lugar de los estados",
     "Parte de los datos proviene de una fuente secundaria."),
    (r"^beneficio normalizado con ítems inferidos",
     "El beneficio se ajustó por partidas extraordinarias identificadas de forma indirecta."),
    (r"\^TNX no disponible", None),          # Rf de config: detalle técnico, no se muestra
    # ── convergencia entre métodos ──
    (r"^un solo método evaluable",
     "Solo un método de valoración da una señal utilizable: no hay otro con el que contrastarlo."),
    (r"^ningún método evaluable", "Ningún método de valoración da una señal utilizable."),
    (r"^no evaluable: DCF \(fiabilidad baja\)",
     "El DCF no concilia con el precio y no se usa para contrastar."),
    (r"^no evaluable: ", "Uno de los métodos de valoración tiene fiabilidad baja y no se usa para contrastar."),
    (r"^direcciones opuestas",
     "Los métodos de valoración se contradicen: uno ve la acción barata y otro cara."),
    (r"^uno lo ve en precio y otro con dirección",
     "Los métodos de valoración no coinciden del todo: uno ve la acción en precio y otro no."),
    (r"^coinciden \([^)]*\) pero la distancia",
     "Los métodos de valoración coinciden en la dirección, pero con intensidad distinta."),
    (r"^coinciden \([^)]*\) con distancia", "Los métodos de valoración coinciden."),
    # ── cobertura ──
    (r"^categorías excluidas por cobertura: (.+)$", "Faltan datos para evaluar: {0}."),
    (r"^sin componentes evaluables", "No hay datos suficientes para evaluar el negocio."),
    (r"^(\d+) de (\d+) componentes del score con dato",
     "Faltan datos en parte del análisis ({0} de {1} indicadores con dato)."),
    # ── estabilidad ──
    (r"^(arquetipo CYCLICAL|empresa cíclica)", "Empresa cíclica: sus resultados dependen de la fase del ciclo."),
    (r"^alerta de posible cíclica",
     "La empresa podría ser cíclica: sus resultados actuales pueden no ser representativos."),
    (r"^clasificación ambigua", "El tipo de empresa no está claro, lo que hace menos fiable la comparación."),
    (r"^clasificación de frontera", "El tipo de empresa está en la frontera entre dos: un cambio pequeño en un umbral "
                                    "lo cambiaría, lo que hace menos fiable la comparación."),
    (r"^ciclicidad sin medir: (\d+) ejercicios en EDGAR \(hacen falta (\d+)\)",
     "No hay historia suficiente para medir si la empresa es cíclica ({0} ejercicios en la SEC; hacen falta {1})."),
    # ── fuente oficial (fase 2b, D7) ──
    (r"^el emisor no presenta estados en la SEC",
     "La empresa no presenta sus cuentas ante la SEC: las cifras vienen de proveedores de datos y no se han podido "
     "contrastar con una fuente oficial."),
    # ── techo de la confianza: redundante con el motivo de su dimensión ──
    (r"^techo en ", None),
]
_COMPILED = [(re.compile(p), t) for p, t in TABLE]
_VALIDATION_RE = re.compile(r"^validación: (\S+) \(([a-z_]+)\)")


def translate(technical: str) -> Optional[str]:
    """Motivo técnico -> texto llano; None si no se muestra al usuario. Sin entrada
    en la tabla, el propio motivo técnico (con mayúscula y punto)."""
    m = _VALIDATION_RE.match(technical)
    if m:
        return VALIDATION_RULES.get(m.group(2), _VALIDATION_DEFAULT)
    for rx, txt in _COMPILED:
        m = rx.search(technical)
        if m:
            return txt.format(*m.groups()) if txt else None
    t = technical.strip().rstrip(".")
    return (t[0].upper() + t[1:] + ".") if t else None


def has_translation(technical: str) -> bool:
    return bool(_VALIDATION_RE.match(technical)) or any(rx.search(technical) for rx, _ in _COMPILED)


_DIM_LABELS = {"convergence": "convergencia", "coverage": "cobertura", "source": "calidad de fuente",
               "stability": "estabilidad", "fuente_oficial": "fuente oficial"}


def confidence_reasons(confidence: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Motivos de la confianza del veredicto, uno por motivo técnico atómico de cada
    dimensión que no es "alta" (mismo orden que confidence.reasons), más el techo.
    [{dimension, level, text (llano o None), detail (técnico)}]."""
    out: List[Dict[str, Any]] = []
    c = confidence or {}
    for key, d in (c.get("dimensions") or {}).items():
        if d.get("level") == "alta":
            continue
        for r in d.get("reasons") or []:
            out.append({"dimension": _DIM_LABELS.get(key, key), "level": d.get("level"),
                        "text": translate(r), "detail": r})
    for r in c.get("reasons") or []:
        if r.startswith("techo en "):
            out.append({"dimension": "techo", "level": c.get("level"), "text": translate(r), "detail": r})
    return out


def plain_reasons(confidence: Optional[Dict[str, Any]]) -> List[str]:
    """Textos llanos únicos, sin los ocultos: primero el primer motivo de cada dimensión
    (en su orden), luego los demás, para que un resumen de N motivos cubra el máximo de
    dimensiones (la portada muestra 3)."""
    rank, seen_dim = [], {}
    for i, r in enumerate(confidence_reasons(confidence)):
        if not r["text"]:
            continue
        k = seen_dim.get(r["dimension"], 0)
        seen_dim[r["dimension"]] = k + 1
        rank.append((k, i, r["text"]))
    seen, out = set(), []
    for _, _, t in sorted(rank):
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out
