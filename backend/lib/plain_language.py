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
    (r"^beneficio por encima de lo que explica la operación sin partida que lo nombre",
     "Parte del beneficio no la explica el negocio y no se ha podido identificar de dónde sale: no se descuenta, pero "
     "resta certeza."),
    (r"bono del Tesoro de EE\. UU\. a 10 años no está disponible", None),   # Rf de referencia: detalle técnico
    # ── base del veredicto (F13 · paso 3: valuation_confidence.fragility_dimension) ──
    (r"^caja libre negativa \(",
     "La empresa invierte más caja de la que genera: su valor depende de que esa inversión rinda."),
    (r"^Altman Z \S+ en zona de peligro",
     "La fórmula de Altman sitúa a la empresa en la zona de riesgo de quiebra."),
    (r"^el beneficio normalizado y el esperado no cuadran",
     "El beneficio sin partidas extraordinarias y el que esperan los analistas no cuadran: una de las dos bases puede "
     "estar equivocada."),
    # ── convergencia entre métodos ──
    (r"^un solo método evaluable",
     "Solo un método de valoración da una señal utilizable: no hay otro con el que contrastarlo."),
    (r"^ningún método evaluable", "Ningún método de valoración da una señal utilizable."),
    (r"^no evaluable: DCF \(fiabilidad baja\)",
     "Los datos del DCF directo no lo sostienen y no se usa para contrastar."),
    (r"^no evaluable: ", "Uno de los métodos de valoración tiene fiabilidad baja y no se usa para contrastar."),
    (r"^direcciones opuestas",
     "Los métodos de valoración se contradicen: uno ve la acción barata y otro cara."),
    (r"^uno lo ve en precio y otro con dirección",
     "Los métodos de valoración no coinciden del todo: uno ve la acción en precio y otro no."),
    (r"^coinciden \([^)]*\), pero lo contradicen? con lectura extrema",
     "Los métodos de valoración coinciden en la dirección, pero algún múltiplo dice con fuerza lo contrario."),
    (r"^coinciden \([^)]*\) pero la distancia",
     "Los métodos de valoración coinciden en la dirección, pero con intensidad distinta."),
    (r"^coinciden \([^)]*\) con distancia", "Los métodos de valoración coinciden."),
    # F11 · T2: dos métodos que dependen de la misma referencia
    (r"^coinciden \(([^)]*)\), pero (.+) comparten la referencia",
     "Los métodos coinciden, pero dependen de la misma referencia de industria: no se confirman entre sí."),
    # ── cobertura ──
    (r"^categorías excluidas por cobertura: (.+)$", "Faltan datos para evaluar: {0}."),
    (r"^sin componentes evaluables", "No hay datos suficientes para evaluar el negocio."),
    # F8 · E6: estados desfasados frente a EDGAR (lib/edgar_backup.staleness)
    (r"^estados desfasados: corte del (.+?) \((\d+) días\) y EDGAR ya tiene el (\S+) del periodo cerrado el (.+)$",
     "Hay estados más recientes en la SEC ({2} al {3})."),
    # F11 · T5: la beta de la industria (la del coste del capital) frente a la propia
    (r"^beta sustituta ([\d.]+) fuera de la propia ([\d.]+)",
     "El coste del capital usa la beta de su industria ({0}), que no encaja con cómo se ha movido la acción frente al "
     "mercado (la suya: {1})."),
    # F11 · T3: la variable crítica de su tipo sin medir (el riesgo de crédito de un banco)
    (r"^sin medir: (.+)$", "Falta medir {0}, la variable clave de este tipo de empresa."),
    (r"^(\d+) de (\d+) componentes del score con dato",
     "Faltan datos en parte del análisis ({0} de {1} indicadores con dato)."),
    # ── estabilidad ──
    # F13 · 3c (opción (a) con matiz): lo que el ciclo hizo en sus cifras
    (r"^empresa cíclica: en sus (\d+) ejercicios, (.+)$",
     "Empresa cíclica: sus resultados dependen de la fase del ciclo (en sus {0} ejercicios, {1})."),
    (r"^empresa cíclica sin una caída real del beneficio en sus (\d+) ejercicios",
     "Empresa cíclica: en sus {0} ejercicios el beneficio aún no ha caído con el ciclo, así que su resultado de hoy "
     "puede estar en la parte alta."),
    (r"^productora de materias primas", "Produce materias primas: su resultado depende del precio de lo que vende, "
                                        "no de su gestión."),
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


_CEILING_RE = re.compile(r"^techo en ([a-z_]+): (.+)$")


def confidence_limits(confidence: Optional[Dict[str, Any]]) -> Optional[str]:
    """F10 · N6 (revisión de NVDA: «techo en baja: techo de la confianza» no explicaba nada): qué limita la confianza,
    para el lector. El nivel que tendría por la media de sus dimensiones y cada límite, en el orden en que se aplicó, con
    el nivel hasta el que la baja (el del último es el final): los techos (lib/valuation_confidence.py), el escalón de las
    tasas base (F10 · N4) y la dependencia de Ke (lib/ke_sensitivity.py). Va entre paréntesis tras el nivel, en la primera frase del resumen (la portada la omite:
    repite el nivel de la tarjeta), así que los incisos van entre rayas. None si nada la limita."""
    c = confidence or {}
    steps = []
    for r in c.get("reasons") or []:
        m = _CEILING_RE.match(r)
        if m:
            head, _, why = m.group(2).partition(": ")
            steps.append((f"{head} —{why}—" if why else head, m.group(1)))
    # F10 · N4: el escalón de las tasas base va tras los techos (lib/valuation_confidence.py lo aplica después); baja
    # la confianza, no el precio, y se dice
    br = c.get("base_rate_step") or {}
    if br.get("to") and br["to"] != br.get("from"):
        steps.append((f"las tasas base —solo el {br.get('share') or 0:.2%} de las comparables sostuvo el crecimiento "
                      "que exige el precio; "
                      # revisión de COST: contrae solo si contradice el veredicto (verdict.price_contraction_basis)
                      + ("contradice un precio atractivo y lo contrae—" if br.get("contracts") else
                         "no contrae el precio—"), br["to"]))
    kd = c.get("ke_dependent") or {}
    if kd.get("to") and kd["to"] != kd.get("from"):
        why = str(kd.get("reason") or "").partition(": ")[2]
        steps.append(("el veredicto depende de Ke" + (f" —{why}—" if why else ""), kd["to"]))
    start = c.get("capped_from") or br.get("from") or kd.get("from")
    if not steps or not start:
        return None
    # el último paso deja el nivel que ya dice la frase: sin «hasta»
    return (f"por sus dimensiones sería {start}; la {'limitan' if len(steps) > 1 else 'limita'}: "
            + "; ".join(w if i == len(steps) - 1 else f"{w}, hasta {lvl}" for i, (w, lvl) in enumerate(steps)))


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
