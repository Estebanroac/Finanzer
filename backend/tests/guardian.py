"""
Guardián narrativo (fase 1 del plan de fiabilidad; diseño en docs/fiabilidad/F1_DISENO_GUARDIAN.md).

Comprueba que cada afirmación del informe es verdad según el dato estructurado:

  1. Predicados: cada afirmación declarada por un generador (lib/claims.py) se verifica contra el análisis.
     Solo se evalúan las de frases que llegan al informe (texto de `display` o del PDF).
  2. Red de seguridad: cada palabra de afirmación (KEYWORDS) que aparece en el texto de `display` o en el PDF
     normalizado tiene que rastrearse hasta una frase con una afirmación de su tipo; si no, "sin respaldo".
  3. Lista negra: inglés y códigos internos fuera del anexo técnico (D1).
  4. Reglas estructurales: referencia "mercado"/"sector" (#6), base temporal (#20), tarjetas y veredicto (#7, #9),
     métricas que no aplican (#10), moneda (#17).

`check(a, pdf_text, records)` devuelve una lista de fallos {rule, detail}. `run(sym, env)` produce sus entradas.
No toca el motor: el colector solo se activa aquí.
"""
import re
import unicodedata

import claims
import fixture_backend as fb
from settings import cfg

# ═══════════════════════════ entradas ═══════════════════════════

def run(sym, env):
    """(análisis, texto del PDF, registros de afirmaciones) de `sym` desde los fixtures de `env`."""
    from fastapi import HTTPException
    with claims.collecting() as recs:
        with fb.replay(fb.fixtures_dir(env)) as store:
            try:
                a = fb.run_analysis(sym, store)
            except HTTPException as e:          # rechazo (SPY): no hay informe que comprobar
                return {"__http_error__": e.status_code, "detail": e.detail}, "", []
            pdf = fb.build_pdf_bytes(a, fb.capture_date(store.meta[sym.upper()]))
    return a, fb.pdf_text(pdf), list(recs)


def norm(s):
    """Minúsculas, NFC, sin guion blando, signo menos tipográfico → '-', espacios colapsados."""
    s = unicodedata.normalize("NFC", s or "").replace("­", "").replace("−", "-").replace("‑", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


# Rutas de `display` que no son prosa sobre la empresa: escalas de bandas (tooltips) y detalle técnico.
SKIP_PATHS = (".tooltips", ".na_keys", ".archetype", ".annex", ".thresholds_key", ".version",
              ".key", ".state", ".tone", ".unit", ".kicker", ".method", ".role", ".zones",
              ".confidence.reasons[].level")
ANNEX_TITLE = "detalle técnico para auditoría"


def display_strings(display, p=""):
    if isinstance(display, dict):
        for k, v in display.items():
            q = f"{p}.{k}"
            qq = re.sub(r"\[\d+\]", "[]", q)
            if not any(qq.endswith(x) or f"{x}." in qq or f"{x}[" in qq for x in SKIP_PATHS):
                yield from display_strings(v, q)
    elif isinstance(display, list):
        for i, v in enumerate(display):
            yield from display_strings(v, f"{p}[{i}]")
    elif isinstance(display, str):
        yield p, display


def pdf_reading_text(pdf_text):
    """Texto del PDF que lee el usuario: sin el anexo técnico (D1), normalizado."""
    t = norm(pdf_text.replace("\n", " "))
    i = t.find(ANNEX_TITLE)
    return t if i < 0 else t[:i]


# ═══════════════════════════ red de seguridad ═══════════════════════════

# (nombre, regex sobre texto normalizado, tipos de afirmación que la respaldan)
KEYWORDS = [
    ("ebit_negativo", r"ebit negativo|ebit < 0|resultado operativo (?:es )?negativo", {"ebit_negative"}),
    ("caja_neta", r"caja neta", {"net_cash"}),
    ("sin_carga_financiera", r"sin carga financiera", {"no_interest_burden"}),
    ("roce", r"\broce\b", {"roce"}),
    ("deuda_neta_afirmada", r"(?:tiene|con) deuda neta", {"net_debt"}),
    ("maximos_minimos", r"en (?:la zona de )?m[aá]ximos|en (?:la zona de )?m[ií]nimos|zona de m[aá]ximos|zona de m[ií]nimos",
     {"pos52"}),
    # "recompras" como nombre de métrica ("Buyback yield (recompras netas)", "o recompras") no afirma nada.
    ("recompras", r"recompró|retiró un|diluy[óe]|\bdilución\b",
     {"buyback", "runway", "piotroski", "eps_vs_revenue", "share_dilution_3y"}),
    # "contrae el atractivo del precio" y "la calidad no se contrae" hablan de la confianza, no del crecimiento.
    ("crecimiento", r"\bcrecen?\b|(?<!no )se contraen?\b(?! el atractivo)|prácticamente plan",
     {"growth", "eps_vs_revenue"}),
    # "prima implícita" (de riesgo del mercado) y "tasa de descuento" no comparan la empresa con nada.
    ("vs_referencia", r"\b(?:muy )?superior\b|\b(?:muy )?inferior\b|\bprima\b(?! (?:de mercado )?implícita)"
                      r"|(?<!tasa de )\bdescuento\b",
     {"vs_bench", "dcf_upside", "graham"}),
    ("autofinanciada", r"autofinanciad", {"runway"}),
    ("valor_economico", r"crea (?:mucho )?valor|destruye valor", {"spread"}),
    ("fiabilidad_dcf", r"fiabilidad (?:alta|media|baja)", {"dcf_rel"}),
    ("zona_altman", r"zona (?:segura|gris|de riesgo|de peligro)", {"altman_zone"}),
    ("contraccion_precio", r"sin ajustar", {"price_contraction"}),
    # Fase 3 (T3): la frase del DCF inverso afirma un crecimiento exigido y lo compara con la historia.
    ("crecimiento_exigido", r"el precio actual (?:exige|se justifica)", {"implied_growth"}),
    ("retorno_implicito", r"el precio descuenta un (?:rote|roe)", {"implied_return"}),
    # Fase 4 (T1): la calidad limitada por la persistencia cita el antes y el después.
    ("persistencia_calidad", r"exige persistencia", {"quality_persistence"}),
    ("base_temporal", r"\binteranual\b|anual en 3 años|\(3 años\)|anual de ciclo medio",
     {"growth", "basis", "eps_vs_revenue"}),
]

ENGLISH = re.compile(r"\b(STRONG|GOOD|NEUTRAL|WEAK|MODERATE|POOR|EXCELLENT|MATURE|CYCLICAL|FINANCIAL|UTILITY|"
                     r"GROWTH_PRE_PROFIT|N/A)\b")
CODE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")   # snake_case: por_defecto, industria_banco, pe_implausible…


def _fragments(records):
    out = []
    for r in records:
        t = norm(r["text"])
        if t:
            out.append((t, r["claims"], r.get("source", "")))
    return out


def _covered_in_string(s, i, j, frags, kinds):
    """¿La ocurrencia s[i:j] está dentro de una frase registrada con una afirmación de `kinds`?"""
    for t, cl, _ in frags:
        if not any(c["kind"] in kinds for c in cl) or len(t) < j - i:
            continue
        k = s.find(t)
        while k >= 0:
            if k <= i and j <= k + len(t):
                return True
            k = s.find(t, k + 1)
    return False


def _covered_in_pdf(s, i, j, frags, kinds):
    """En el PDF (columnas que pueden intercalarse): la palabra y una vecina deben estar juntas en una frase."""
    kw = s[i:j]
    probes = [s[max(0, i - k):j] for k in (12, 6)] + [s[i:j + k] for k in (12, 6)]
    for t, cl, _ in frags:
        if not any(c["kind"] in kinds for c in cl) or kw not in t:
            continue
        if len(t) <= len(kw) + 25 or any(p in t for p in probes if p != kw):
            return True
    return False


# ═══════════════════════════ predicados ═══════════════════════════

def _get(a, path):
    """Valor de una ruta "a.b.c" del análisis ("score.breakdown.Crecimiento[Métrica].raw" para el desglose)."""
    m = re.match(r"score\.breakdown\.([^\[]+)\[(.+)\]\.(\w+)$", path)
    if m:
        cat, metric, key = m.groups()
        for x in (a.get("score", {}).get("breakdown", {}).get(cat, {}) or {}).get("adjustments") or []:
            if x.get("metric") == metric:
                return x.get(key)
        return None
    if path == "pos52":
        km = a.get("key_metrics") or {}
        hi, lo, px = km.get("price_52w_high"), km.get("price_52w_low"), a.get("price")
        return None if None in (hi, lo, px) or hi <= lo else (px - lo) / (hi - lo) * 100
    d = a
    for k in path.split("."):
        d = d.get(k) if isinstance(d, dict) else None
    return d


def _same(x, y, rel=1e-9):
    if x is None or y is None:
        return x is y
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return abs(x - y) <= 1e-12 + rel * max(abs(x), abs(y))
    return x == y


def _p_value(a, c, text):
    """El valor declarado es el del campo que dice respaldarlo."""
    if "value" in c and c.get("field") and not _same(c["value"], _get(a, c["field"])):
        return f"{c['field']}: declarado {c['value']!r}, en el análisis {_get(a, c['field'])!r}"


def _p_ebit_negative(a, c, text):
    oi = (a.get("key_metrics") or {}).get("operating_income")
    if oi is None:
        return "dice EBIT negativo sin operating_income para respaldarlo"
    if oi >= 0:
        return f"dice EBIT negativo con operating_income = {oi / 1e9:+.2f} B"


def _p_no_interest_burden(a, c, text):
    """'Sin carga financiera neta': EBIT > 0 y resultado financiero neto >= 0 (o inferido y marcado)."""
    km = a.get("key_metrics") or {}
    oi, nii = km.get("operating_income"), km.get("net_interest_income")
    inferred = "key_metrics.interest_coverage_state" in ((a.get("data_provenance") or {}).get("fields") or {})
    if oi is None or oi <= 0:
        return f"dice sin carga financiera con operating_income = {oi!r}"
    if nii is None and not inferred:
        return "dice sin carga financiera sin resultado financiero neto ni marca de inferido"
    if nii is not None and nii < 0:
        return f"dice sin carga financiera con resultado financiero neto {nii / 1e6:+.1f} M"


def _p_roce(a, c, text):
    """Fase 1 (punto 9): la cifra de ROCE citada = key_metrics.roce (y el promedio del ciclo = roce_avg), redondeada
    como se imprime. Una celda con la cifra sola se compara con el campo que declara la afirmación."""
    km = a.get("key_metrics") or {}
    cites = [("roce_avg", m) for m in re.findall(r"roce promedio(?: del ciclo)?[^%]*?\b(-?\d+\.\d+)%", text)]
    cites += [("roce", m) for m in re.findall(r"\broce (?:de )?(-?\d+\.\d+)%", text)]
    bare = re.fullmatch(r"\s*(-?\d+\.\d+)%\s*", text)
    if bare and c.get("field"):
        cites.append((c["field"].split(".")[-1], bare.group(1)))
    for fld, s in cites:
        v = km.get(fld)
        if v is None:
            return f"cita ROCE {s}% sin {fld}"
        d = len(s.split(".")[1])
        if abs(round(v * 100, d) - float(s)) > 1e-9:
            return f"cita {s}% con {fld} = {v * 100:.{d + 2}f}%"


def _p_net_cash(a, c, text):
    nd = (a.get("key_metrics") or {}).get("net_debt")
    if nd is None or nd >= 0:
        return f"dice caja neta con net_debt = {nd!r}"


def _p_net_debt(a, c, text):
    nd = (a.get("key_metrics") or {}).get("net_debt")
    if nd is None or nd <= 0:
        return f"dice deuda neta con net_debt = {nd!r}"


def _p_pos52(a, c, text):
    p = _get(a, "pos52")
    if p is None:
        return "posición en el rango sin dato"
    b = cfg("thresholds.pdf.pos52_bounds")
    if re.search(r"m[ií]nimos", text) and not p < b[0]:
        return f"dice mínimos con posición {p:.0f}%"
    if re.search(r"m[aá]ximos", text) and not p >= b[3]:
        return f"dice máximos con posición {p:.0f}%"
    m = re.search(r"en el (\d+)% del rango", text)
    if not 0 <= p <= 100 or (m and not 0 <= int(m.group(1)) <= 100):   # fase 1: XOM "101%"
        return f"posición en el rango fuera de 0–100% ({p:.1f}%)"
    if m and abs(int(m.group(1)) - p) > 0.5 + 1e-9:
        return f"cita {m.group(1)}% con posición {p:.1f}%"


def _p_buyback(a, c, text):
    by = (a.get("key_metrics") or {}).get("buyback_yield")
    if by is None:
        return "habla de recompras sin buyback_yield"
    if re.search(r"recompr|retiró", text) and by <= 0:
        return f"dice recompras con buyback_yield = {by:.4f}"
    if re.search(r"dilu", text) and by >= 0:
        return f"dice dilución con buyback_yield = {by:.4f}"


def _p_growth(a, c, text):
    g = c.get("value")
    if g is None:
        return None
    subj = r"(?:ingresos|bpa|ffo|fcf|beneficio)[^.:;()]*?"
    if re.search(subj + r"\bse contraen?\b", text) and g >= 0:
        return f"dice que se contrae con {g:+.4f}"
    if re.search(subj + r"\bcrecen?\b", text) and g < 0:
        return f"dice que crece con {g:+.4f}"
    if c.get("cycle") and re.search(r"ciclo medio|anual", text):
        lo, hi = cfg("valuation.archetypes.cyclical_growth_bounds")
        if (abs(g - lo) < 1e-12 or abs(g - hi) < 1e-12) and not re.search(r"acotad|cota|tope|límite", text):
            return f"crecimiento de ciclo medio en la cota del modelo ({g:+.1%}) presentado como dato medido"
    # #20 base temporal: lo que dice el texto frente a cómo se calculó la cifra
    if c.get("cycle") and ("anual en 3 años" in text or "(3 años)" in text):
        return "dice '3 años' de una cifra de ciclo medio"
    if c.get("cagr") and "ciclo medio" in text:
        return "dice 'ciclo medio' de una CAGR a 3 años"


def _p_vs_bench(a, c, text):
    v, b = c.get("value"), c.get("bench")
    if v is None or b in (None, 0):
        return None
    diff = (v - b) / abs(b)
    up = bool(re.search(r"superior|prima", text))
    down = bool(re.search(r"inferior|descuento", text))
    if up and diff <= 0:
        return f"dice superior/prima con brecha {diff:+.1%}"
    if down and diff >= 0:
        return f"dice inferior/descuento con brecha {diff:+.1%}"
    prof = (a.get("benchmark") or {}).get("profile")
    if prof == "market" and re.search(r"\bsector\b", text):
        return "benchmark de mercado nombrado como 'sector'"


def _p_spread(a, c, text):
    s = (a.get("key_metrics") or {}).get("roic_wacc_spread")
    if s is None:
        return None
    if re.search(r"crea (mucho )?valor", text) and s <= 0:
        return f"dice que crea valor con spread {s:+.2%}"
    if "destruye valor" in text and s >= 0:
        return f"dice que destruye valor con spread {s:+.2%}"


def _p_dcf_upside(a, c, text):
    u = (a.get("dcf") or {}).get("upside")
    if u is None:
        return None
    if re.search(r"\bprima\b|excede en|sobrevalorad", text) and u >= 0:
        return f"dice prima con upside {u:+.1f}%"
    if re.search(r"potencial teórico de \+|infravalorad", text) and u <= 0:
        return f"dice potencial con upside {u:+.1f}%"


def _p_dcf_rel(a, c, text):
    lvl = ((a.get("dcf") or {}).get("reliability") or {}).get("level")
    m = re.search(r"fiabilidad (alta|media|baja)", text)
    if m and m.group(1) != lvl:
        return f"dice fiabilidad {m.group(1)} con {lvl!r}"


def _p_implied_growth(a, c, text):
    """El crecimiento exigido de la frase es el CAGR equivalente de la lectura (main o ttm) y la historia citada es
    la de la lectura."""
    parts = (c.get("field") or "reverse_dcf.main.g10").split(".")
    key = parts[1] if len(parts) > 1 else "main"
    x = ((a.get("reverse_dcf") or {}).get(key)) or {}
    m = re.search(r"(?:crezca|caiga) un (−?\d+(?:[.,]\d+)?)%", text)
    if m and x.get("g10") is not None:
        said = float(m.group(1).replace("−", "-").replace(",", ".")) / 100
        real = x["g10"] if "crezca" in m.group(0) else -x["g10"]
        if abs(said - real) > 0.0006:
            return f"dice {said:+.1%} exigido con g10 {x['g10']:+.2%}"
    if m and x.get("g10") is None:
        return "afirma un crecimiento exigido sin lectura del DCF inverso"
    o = x.get("own_growth") or {}
    h = re.search(r"(crecieron|creció|cayeron|cayó) un (\d+(?:[.,]\d+)?)% anual", text)
    if h and o.get("cagr") is not None:
        val = float(h.group(2).replace(",", ".")) / 100 * (-1 if h.group(1).startswith("cay") else 1)
        if abs(val - o["cagr"]) > 0.0006:
            return f"dice historia {val:+.1%} con {o['cagr']:+.2%}"
    if c.get("band") is not None and c.get("band") != x.get("band"):
        return f"banda declarada {c.get('band')!r} con {x.get('band')!r}"


def _p_implied_return(a, c, text):
    """El ROTE/ROE que descuenta el precio y el que obtiene la entidad son los del análisis."""
    x = (a.get("archetype_metrics") or {}).get("implied") or {}
    m = re.search(r"sostenido del (−?\d+(?:\.\d+)?)%", text)
    if m and x.get("implied") is not None and abs(float(m.group(1).replace("−", "-")) / 100 - x["implied"]) > 0.0006:
        return f"dice implícito {m.group(1)}% con {x['implied']:.4f}"
    o = re.search(r"obtu?v?(?:o|iene) un (−?\d+(?:\.\d+)?)%", text)
    if o and x.get("own") is not None and abs(float(o.group(1).replace("−", "-")) / 100 - x["own"]) > 0.0006:
        return f"dice obtenido {o.group(1)}% con {x['own']:.4f}"


def _p_quality_persistence(a, c, text):
    """"X → Y" es la calidad antes de la persistencia y la mostrada, y solo se dice si se aplicó."""
    q = a.get("quality") or {}
    pq = q.get("persistence") or {}
    m = re.search(r"persistencia: (\d+) → (\d+)", text)
    if not pq.get("applied"):
        return "dice que la persistencia limita la calidad y no se aplicó"
    if m and (int(m.group(1)) != pq.get("score_before") or int(m.group(2)) != q.get("score")):
        return f"dice {m.group(1)} → {m.group(2)} con {pq.get('score_before')} → {q.get('score')}"


def _p_altman(a, c, text):
    z = {"safe": "segura", "grey": "gris", "distress": "de riesgo"}.get((a.get("altman_z") or {}).get("zone"))
    m = re.search(r"zona (segura|gris|de riesgo|de peligro)", text)
    if m and m.group(1).replace("de peligro", "de riesgo") != z:
        return f"dice zona {m.group(1)} con zona {z!r}"


def _p_runway(a, c, text):
    rw = (a.get("archetype_metrics") or {}).get("runway") or {}
    if "autofinanciad" in text and rw.get("state") != "autofinanciada":
        return f"dice autofinanciada con runway {rw.get('state')!r}"


def _p_price_contraction(a, c, text):
    pa, conf = a.get("price_attractiveness") or {}, (a.get("confidence") or {}).get("level")
    want = (pa.get("score_raw"), pa.get("score"), pa.get("confidence"))
    if ("raw" in c and (c.get("raw"), c.get("score"), c.get("confidence")) != want) or pa.get("confidence") != conf:
        return f"declara {c.get('raw')}→{c.get('score')} ({c.get('confidence')}); análisis {want}, confianza {conf}"
    m = re.search(r"sin ajustar (\d+) → ajustado a (\d+)(?: por confianza (\w+))?", text)
    if m and (int(m.group(1)), int(m.group(2))) != want[:2]:
        return f"el texto dice {m.group(0)!r} y el análisis {want}"
    if m and m.group(3) and m.group(3) != want[2]:
        return f"el texto dice confianza {m.group(3)!r} y el análisis {want[2]!r}"
    f = re.search(r"factor (\d+(?:\.\d+)?)", text)
    if f and pa.get("factor") is not None and abs(float(f.group(1)) - pa["factor"]) > 1e-9:
        return f"el texto dice factor {f.group(1)} y el análisis {pa['factor']}"


def _p_basis(a, c, text):
    """#20: "(3 años)" solo para una CAGR a 3 años; en CYCLICAL la cifra que puntúa es de ciclo medio."""
    arch = (a.get("classification") or {}).get("archetype")
    key = str(c.get("metric") or "")
    if c.get("per") == "3 años" and arch == "CYCLICAL" and re.search(r"revenue_growth|eps|ingresos|bpa", key, re.I):
        return f"rotula '(3 años)' una cifra de ciclo medio (CYCLICAL), métrica {key}"


def _p_eps_vs_revenue(a, c, text):
    e, r = c.get("eps"), c.get("revenue")
    if e is None or r is None:
        return None
    if "crece más rápido que los ingresos" in text and not e > r:
        return f"dice que el BPA crece más rápido con BPA {e:+.3f} e ingresos {r:+.3f}"
    if "crece más despacio" in text and not e < r:
        return f"dice que el BPA crece más despacio con BPA {e:+.3f} e ingresos {r:+.3f}"


def _p_share_dilution_3y(a, c, text):
    """'La emisión de acciones ... diluye al accionista' en 3 años: las acciones tienen que haber crecido de
    verdad, al menos el umbral con el que el propio motor pasa a medir por acción."""
    sh = (a.get("growth_basis") or {}).get("shares_cagr_3y")
    thr = cfg("thresholds.growth.per_share_min_shares_cagr")
    if re.search(r"emisión de acciones|diluye", text) and (sh is None or sh < thr):
        return f"atribuye la caída a la emisión de acciones con acciones {sh:+.2%} anual en 3 años (umbral {thr:.0%})"


PREDICATES = {
    "roce": _p_roce,
    "no_interest_burden": _p_no_interest_burden,
    "share_dilution_3y": _p_share_dilution_3y,
    "basis": _p_basis, "eps_vs_revenue": _p_eps_vs_revenue,
    "ebit_negative": _p_ebit_negative, "net_cash": _p_net_cash, "net_debt": _p_net_debt, "pos52": _p_pos52,
    "buyback": _p_buyback, "growth": _p_growth, "vs_bench": _p_vs_bench, "spread": _p_spread,
    "dcf_upside": _p_dcf_upside, "dcf_rel": _p_dcf_rel, "altman_zone": _p_altman, "runway": _p_runway,
    "price_contraction": _p_price_contraction, "implied_growth": _p_implied_growth,
    "implied_return": _p_implied_return,
    "quality_persistence": _p_quality_persistence,
}


# ═══════════════════════════ reglas estructurales ═══════════════════════════

def cards(d):
    """Todas las tarjetas de portada y resumen: (ruta, tarjeta)."""
    for i, c in enumerate((d.get("cover") or {}).get("kpis") or []):
        yield f".cover.kpis[{i}]", c
    for i, c in enumerate((d.get("summary") or {}).get("cards") or []):
        yield f".summary.cards[{i}]", c


def table_rows(d):
    """Todas las filas de las tablas de las secciones: (ruta, fila). Fase 1: la regla #10 vale también aquí
    (decisión del usuario, registro #14)."""
    for sec, blk in ((d.get("sections") or {}).items()):
        for k, rows in (blk or {}).items() if isinstance(blk, dict) else ():
            if isinstance(rows, list):
                for i, r in enumerate(rows):
                    if isinstance(r, dict) and "state" in r and "value" in r:
                        yield f".sections.{sec}.{k}[{i}]", r


def _structural(a, strings, pdf):
    out = []
    km = a.get("key_metrics") or {}
    d = a.get("display") or {}
    # #10 lo que no aplica no se cita con cifra (fase 1: faltaba; AMT y SNOW pintaban "No aplica" y el valor)
    for p, c in list(cards(d)) + list(table_rows(d)):
        na = (c.get("state") == "no_aplica" or norm(str(c.get("pill") or "")) == "no aplica"
              or norm(str(c.get("reading") or "")).startswith("no aplica"))
        if na and re.search(r"\d", f"{c.get('value') or ''}"):
            out.append(("no_aplica_con_cifra", f"{p} {c.get('label')!r}: 'no aplica' con valor {c.get('value')!r}"))
        # ningún múltiplo negativo se presenta como nivel en una tarjeta (PLTR "Deuda neta/EBITDA −3.45x")
        if p.startswith((".cover", ".summary")) and re.match(r"\s*[-−]\s*\d[\d.,]*\s*x\s*$", f"{c.get('value') or ''}{c.get('unit') or ''}"):
            out.append(("ratio_negativo_en_tarjeta", f"{p} {c.get('label')!r}: {c.get('value')!r}"))
    # #6 referencia: con el perfil market, el texto dice "mercado", no "sector".
    if (a.get("benchmark") or {}).get("profile") == "market":
        # Solo frases de comparación (la nota de referencia explica el sector de Yahoo y es legítima).
        pat = re.compile(r"\bvs sector\b|frente al sector|mediana del sector|(?:\d|x|%) del sector\b"
                         r"|rango alto sector|para su sector")
        for p, s in strings:
            if pat.search(s):
                out.append(("referencia_mercado", f"{p}: {s[:110]}"))
        for m in pat.finditer(pdf):
            out.append(("referencia_mercado", f"PDF: …{pdf[max(0, m.start() - 50):m.end() + 30]}…"))
    # #7 veredicto en la portada = verdict
    v, cv = a.get("verdict") or {}, (d.get("cover") or {}).get("verdict") or {}
    if cv.get("text") != v.get("text") or (v.get("text") and norm(v["text"]) not in pdf):
        out.append(("veredicto", f"portada {cv.get('text')!r} / análisis {v.get('text')!r}"))
    # #20 "TTM" en el texto ⇒ base TTM ("sin TTM", que dice la base anual, no cuenta: UL, fase 2a)
    ttm = ((a.get("data_provenance") or {}).get("ttm") or {}).get("basis")
    if ttm != "ttm" and re.search(r"(?<!sin )\bttm\b", pdf):
        out.append(("base_ttm", f"el PDF dice TTM con base {ttm!r}"))
    # #17 moneda
    cur = (a.get("data_provenance") or {}).get("currency") or {}
    note = (d.get("cover") or {}).get("currency_note") or ""
    m = re.search(r"(\b[A-Z]{3}) convertidos a (\b[A-Z]{3})", note)
    if m and (m.group(1), m.group(2), True) != (cur.get("statements"), cur.get("price"), cur.get("converted")):
        out.append(("moneda", f"{note!r} frente a {cur.get('statements')}→{cur.get('price')}"))
    return out


# ═══════════════════════════ identidades (datos frente a datos) ═══════════════════════════

def identities(a):
    """Identidades entre cifras del análisis, sin texto. [(regla, detalle)].

    Fase 2b (F2_PRECEDENCIA §2.2): el dividendo se compara con magnitudes equivalentes y en los dos sentidos.
    · identidad_dividendo:
        - unidad: dividend yield = dividendo indicado / precio (los dos en la moneda y la clase del precio);
        - hacia arriba: el indicado no supera `dividend_identity_max_ratio` veces lo cobrado por título en 12 meses
          salvo una subida verificada (último pago × frecuencia; NVDA 0.25 × 4); y el yield no supera esas veces
          payout × E/P (lo pagado según los estados, la vía de la fase 1) salvo esa misma subida;
        - hacia abajo: un indicado menor que lo cobrado / `dividend_identity_max_ratio` lleva su explicación
          (extraordinario separado, PGR; recorte; o la nota de que es menos de la mitad).
    · identidad_shareholder: shareholder yield = dividend yield + buyback yield; sin dividend yield de una empresa
      que paga (regla dividendo_sin_fuente), sin dato (no las recompras solas).
    · identidad_no_puntua: un yield invalidado no aparece en el desglose del score ni en la salud bancaria."""
    out = []
    km = a.get("key_metrics") or {}
    dv = (a.get("data_provenance") or {}).get("dividend") or {}
    pay = dv.get("payments") or {}
    dy, po, ey = km.get("dividend_yield"), km.get("payout_ratio"), km.get("earnings_yield")
    sy, by = km.get("shareholder_yield"), km.get("buyback_yield")
    k = cfg("validation.thresholds.dividend_identity_max_ratio")
    rate, price = dv.get("rate"), a.get("price")
    raised = (dv.get("change") or {}).get("kind") == "aumento"
    if dy is not None and rate is not None and price and abs(dy - rate / price) > 1e-9 * max(1.0, abs(dy)):
        out.append(("identidad_dividendo", f"dividend yield {dy:.4%} ≠ indicado {rate} / precio {price}"))
    ttm = pay.get("ttm_total")
    if rate and ttm:
        if rate > k * ttm and not raised:
            out.append(("identidad_dividendo", f"indicado {rate:g} frente a {ttm:g} cobrados en 12 meses "
                                               f"({rate / ttm:.1f} veces) sin una subida verificada"))
        explained = bool(pay.get("extraordinary")) or (dv.get("change") or {}).get("kind") == "recorte" or \
            any("menos de la mitad" in n for n in dv.get("notes") or [])
        if rate < ttm / k and not explained:
            out.append(("identidad_dividendo", f"indicado {rate:g} frente a {ttm:g} cobrados en 12 meses "
                                               "sin extraordinario ni recorte dichos"))
    # En REIT el payout se mide sobre el FFO: lo pagado es payout × FFO / capitalización = payout / P/FFO.
    ffo = km.get("payout_basis") == "ffo"
    base = (1.0 / km["p_ffo"]) if ffo and km.get("p_ffo") else (None if ffo else ey)
    what = "payout / P/FFO" if ffo else "payout × E/P"
    if dy is not None and dy > 0 and po is not None and po > 0 and base is not None and base > 0 \
            and dy > k * po * base and not raised:
        out.append(("identidad_dividendo", f"dividend yield {dy:.2%} frente a {what} {po * base:.2%} "
                                           f"({dy / (po * base):.1f} veces; tolerancia {k:g})"))
    bad = [f for f in a.get("data_validation") or [] if f.get("rule") in ("identidad_dividendo",
                                                                          "dividendo_sin_fuente")]
    if bad and sy is not None:
        out.append(("identidad_shareholder", f"shareholder yield {sy:.2%} sin dividend yield de una empresa que paga"))
    elif sy is not None and abs(sy - ((dy or 0.0) + (by or 0.0))) > 1e-9:
        out.append(("identidad_shareholder", f"shareholder yield {sy:.4%} ≠ dividendo {dy} + recompras {by}"))
    for f in bad:
        old = f.get("old")
        txt = repr((a.get("score") or {}).get("breakdown")) + repr(a.get("financial_health"))
        if old is not None and re.search(rf"(?<![\d.])({re.escape(f'{old * 100:.2f}%')}|{re.escape(f'{old:.1%}')})", txt):
            out.append(("identidad_no_puntua", f"el yield invalidado {old:.2%} aparece en el score"))
    return out


# ═══════════════════════════ comprobación ═══════════════════════════

def check(a, pdf_text, records):
    """Fallos del guardián para un análisis: [{rule, detail}]."""
    if a.get("__http_error__"):
        return []
    fails = []
    frags = _fragments(records)
    strings = [(p, norm(s)) for p, s in display_strings(a.get("display") or {})]
    pdf = pdf_reading_text(pdf_text)
    raw_pdf = pdf_text.replace("\n", " ")
    # 1. predicados de las frases que llegan al informe
    seen = set()
    for t, cl, src in frags:
        if t in seen or not (any(t in s for _, s in strings) or t in pdf):
            continue
        seen.add(t)
        for c in cl:
            for fn in (PREDICATES.get(c["kind"]), _p_value):
                err = fn(a, c, t) if fn else None
                if err:
                    fails.append({"rule": c["kind"], "detail": f"{err} · «{t[:120]}»"})
    # 2. red de seguridad
    for name, rx, kinds in KEYWORDS:
        pat = re.compile(rx)
        for p, s in strings:
            for m in pat.finditer(s):
                if not _covered_in_string(s, m.start(), m.end(), frags, kinds):
                    fails.append({"rule": f"sin_respaldo:{name}", "detail": f"{p}: «{s[:140]}»"})
        for m in pat.finditer(pdf):
            if not _covered_in_pdf(pdf, m.start(), m.end(), frags, kinds):
                fails.append({"rule": f"sin_respaldo:{name}",
                              "detail": f"PDF: «…{pdf[max(0, m.start() - 60):m.end() + 40]}…»"})
    # 3. lista negra (sobre el texto original: mayúsculas)
    raw_strings = list(display_strings(a.get("display") or {}))
    cut = raw_pdf.lower().find(ANNEX_TITLE)
    reading_pdf = raw_pdf if cut < 0 else raw_pdf[:cut]
    for where, s in [(p, s) for p, s in raw_strings] + [("PDF", reading_pdf)]:
        for m in ENGLISH.finditer(s):
            fails.append({"rule": "ingles", "detail": f"{where}: {m.group(0)} «…{s[max(0, m.start() - 40):m.end() + 20]}…»"})
        for m in CODE.finditer(s):
            fails.append({"rule": "codigo_interno",
                          "detail": f"{where}: {m.group(0)} «…{s[max(0, m.start() - 40):m.end() + 20]}…»"})
    # 4. estructurales
    for rule, det in _structural(a, strings, pdf):
        fails.append({"rule": rule, "detail": det})
    # 5. identidades entre datos (fase 1)
    for rule, det in identities(a):
        fails.append({"rule": rule, "detail": det})
    return fails
