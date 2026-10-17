"""
Invariantes GENÉRICOS: valen para cualquier ticker (fase 0 del plan de fiabilidad).

Cada función comprueba un análisis (`a`, la salida de _compute_analysis) y el texto de su PDF (`text`), y
lanza AssertionError si el invariante no se cumple. Son el cuerpo, sin cambios, de tests que antes recorrían
solo los juegos local/prod; esos tests siguen existiendo y llaman a estas funciones (más sus comprobaciones
atadas a tickers concretos, que se quedan en su archivo). `test_panel_invariants.py` las corre sobre los 31
tickers del panel.

Regla: aquí solo entra lo que no depende del ticker ni del entorno. Lo que menciona un ticker, un valor
concreto o la ruta de datos de un juego es un test ATADO y se queda en su archivo.
"""
import json
import re

import display as dp
import plain_language as pl
from settings import cfg

TONES = {"pos", "neg", "warn", "neu", None}
CHART_STATES = {"con_dato", "sin_dato", "no_aplica", "no_significativo"}
PROVENANCE_VOCAB = {"yahoo_quotesummary", "yfinance_statements", "finnhub", "derivado", "sec_edgar",
                    "recalculado_por_validacion", "politica_arquetipo", "sin_dato"}

# test_display (9b): código de arquetipo en el texto visible
_CODE = re.compile(r"\b(FINANCIAL|GROWTH_PRE_PROFIT|CYCLICAL|MATURE)\b")
_TECH_KEYS = {"archetype", "na_keys", "annex", "reasons", "dimensions", "thresholds_key", "wacc_note"}
# test_panel_cases (antes test_muestra, 11b): códigos (incluido UTILITY) y signo después del símbolo
CODES = re.compile(r"\b(FINANCIAL|GROWTH_PRE_PROFIT|CYCLICAL|MATURE|UTILITY)\b")
BAD_SIGN = re.compile(r"\$\s*[-−]")
NOT_PROSE = (".archetype", ".na_keys", ".annex", ".thresholds_key")
ANNEX_TITLE = "Detalle técnico para auditoría"   # D1: los códigos solo desde aquí hasta el final del PDF


def reading_text(text):
    """Texto del PDF sin el anexo técnico final (D1)."""
    i = text.find(ANNEX_TITLE)
    return text if i < 0 else text[:i]


def _rows(d):
    S = d["sections"]
    yield from S["valuation"]["rows"]
    yield from S["valuation"]["intrinsic"]["rows"]
    yield from S["profitability"]["rows"]
    yield from S["solvency"]["rows"]
    yield from S["growth"]["rows"]


def _visible_strings(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in _TECH_KEYS:
                yield from _visible_strings(v, f"{p}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _visible_strings(v, f"{p}[{i}]")
    elif isinstance(o, str):
        yield p, o


def _walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, f"{p}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, f"{p}[{i}]")
    else:
        yield p, o


def _prose_strings(display):
    for path, v in _walk(display):
        if isinstance(v, str) and not any(re.sub(r"\[\d+\]", "", path).endswith(x) or f"{x}[" in path
                                           or f"{x}." in path for x in NOT_PROSE):
            yield path, v


def _zone_of(zones, v):
    for z in zones:
        if z["from"] <= v <= z["to"]:
            return z
    return zones[0] if v < zones[0]["from"] else zones[-1]


# ═══════════════════════ test_coverage ═══════════════════════

def piotroski_state_is_structured(a, text):
    """'passed' sale del estado, no del texto; sin puntuación cuando no aplica."""
    pf = a["piotroski_f"]
    for key, c in pf["details"].items():
        assert c["state"] in {"cumple", "no_cumple", "sin_dato"}, key
        assert c["passed"] == (c["state"] == "cumple")
    n_eval = sum(1 for c in pf["details"].values() if c["state"] != "sin_dato")
    assert pf["evaluated"] == n_eval
    if pf.get("applicable") is False:
        assert pf["score"] is None and pf["scaled_score"] is None
        return
    assert pf["score"] == sum(1 for c in pf["details"].values() if c["state"] == "cumple")


# ═══════════════════════ test_display ═══════════════════════

def display_contract(a, text):
    d = a["display"]
    json.dumps(d, allow_nan=False)
    assert d["archetype"] == a["classification"]["archetype"]
    for r in _rows(d):
        assert r["state"] in dp.STATES, r
        assert r["tone"] in TONES, r
        if r["state"] == "no_aplica":
            assert r["reading"].startswith(("No aplica", dp.DE_NOT_APPLICABLE)), r
    for c in d["summary"]["cards"]:
        assert c["tone"] in TONES and c["state"] in dp.STATES
    for h in d["cover"]["highlights"]:
        assert h["tone"] in TONES - {None} and h["text"]
    assert [h["kicker"] for h in d["cover"]["highlights"]][:2] == ["FORTALEZA CLAVE", "A VIGILAR"]
    assert len(d["cover"]["kpis"]) == 8
    blob = json.dumps(d, ensure_ascii=False)
    assert "score total" not in blob.lower() and "puntuación total" not in blob.lower()


def institutional_not_applicable_never_zero(a, text):
    cards = {c["key"]: c for c in a["display"]["sections"]["institutional"]["cards"]}
    if a["altman_z"].get("applicable") is False:
        assert a["altman_z"]["z_score"] is None
        assert cards["altman"]["state"] == "no_aplica" and cards["altman"]["value"] == "n/a"
    if a["piotroski_f"].get("applicable") is False:
        assert a["piotroski_f"]["score"] is None
        assert cards["piotroski"]["state"] == "no_aplica"


def confidence_reasons_translated(a, text):
    for r in pl.confidence_reasons(a.get("confidence")):
        assert pl.has_translation(r["detail"]), f"motivo sin traducción: {r['detail']!r}"
    d = a["display"]
    for txt in d["cover"]["confidence_reasons"]:
        assert "Finnhub" not in txt and "TTM" not in txt and "^TNX" not in txt
    assert d["cover"]["confidence_reasons"] == pl.plain_reasons(a.get("confidence"))[:3]


def tooltips_only_applied_bands(a, text):
    d = a["display"]
    tips = d["tooltips"]
    na = set(d["na_keys"])
    if "pe" in na:
        assert not tips["pe"]["tables"] and "No aplica" in tips["pe"]["note"]
    if "roe" in na:
        assert all("score" not in t["title"] for t in tips["roe"]["tables"])
    if d["archetype"] == "REIT":
        assert tips["net_debt_to_ebitda"]["tables"][0]["title"] == "Bandas de REIT"
        assert not tips["de"]["tables"]
    for t in tips.values():
        for tb in t["tables"]:
            assert tb["bands"] and all(b["tone"] in TONES - {None} for b in tb["bands"])


def visible_texts_without_jargon_or_bad_formats(a, text):
    for p, t in _visible_strings(a["display"]):
        assert not _CODE.search(t), (p, t)
        assert "$-" not in t and "— -" not in t, (p, t)
    assert all("<" not in n and ">" not in n for n in a["display"]["cover"]["classification_notes"])
    for ln in text.splitlines():
        assert "$-" not in ln and "— -" not in ln, ln
    cover = text.split("===== página 2")[0]
    assert not _CODE.search(cover), cover


def cites_growth(block, raw):
    """La cifra que puntúa está citada: literal ('-5.0%') o con el signo dicho por el verbo ('se contraen un
    5.0%'). Fase 1 (T3.5)."""
    block = block or ""
    lit = re.escape(f"{abs(raw) * 100:.1f}%")
    by_verb = re.search(rf"se contraen? un {lit}", block) is not None
    if raw < 0:
        return f"-{abs(raw) * 100:.1f}%" in block or by_verb
    return re.search(rf"(?<![-−\d.]){lit}", block) is not None and not by_verb


def growth_texts_cite_the_scored_figure(a, text):
    d = a["display"]
    adj = {x["metric"]: x for x in a["score"]["breakdown"]["Crecimiento"]["adjustments"]}
    scored = (adj.get("Crecimiento Ingresos 3Y") or adj.get("Retorno total (dividendo + FFO por acción)") or {})
    rows = {r["key"]: r for r in d["sections"]["growth"]["rows"]}
    if scored.get("raw") is not None:
        key = "total_return" if d["archetype"] == "REIT" else "revenue_growth"
        assert rows[key]["value"] == dp.fv(scored["raw"], "pct")
        card = next(c for c in d["summary"]["cards"] if c["key"] == "revenue_growth")
        assert card["value"] == f"{scored['raw'] * 100:.1f}"
        if d["archetype"] != "REIT":
            assert cites_growth(d["sections"]["growth"]["intro"], scored["raw"]), d["sections"]["growth"]["intro"]
            exec_g = next(e["text"] for e in d["summary"]["exec_items"] if e["label"] == "CRECIMIENTO Y RETORNO")
            assert cites_growth(exec_g, scored["raw"]), exec_g
    yoy = a["key_metrics"].get("revenue_growth")
    if yoy is not None:
        assert rows["revenue_growth_yoy"]["label"].endswith("(último ejercicio)")   # fase 2b, T7
        assert rows["revenue_growth_yoy"]["tone"] is None


def piotroski_criteria_in_spanish(a, text):
    eng = re.compile(r"\b(CFO|Net Income|earnings|LP|asset turnover|Cash Flow)\b")
    for c in a["display"]["sections"]["institutional"]["piotroski_criteria"]:
        assert not eng.search(c["label"] + " " + c["detail"]), c


def price_wording_without_jargon(a, text):
    note = a["display"]["cover"]["price"]["note"]
    blob = json.dumps(a["display"]["summary"], ensure_ascii=False)
    assert "crudo" not in blob and "contraído por" not in blob
    if a["price_attractiveness"].get("contracted"):
        pa = a["price_attractiveness"]
        # Fase 4 (T2): tras la contracción puede ir el aviso de frontera ("; en la frontera con «…»").
        assert note.startswith(f"sin ajustar {pa['score_raw']} → ajustado a {pa['score']} "
                               f"por confianza {pa['confidence']}")


# ═══════════════════════ test_quality_price ═══════════════════════

def verdict_in_pdf(a, text):
    v = a["verdict"]
    assert v["text"].startswith("Calidad ") and " · precio " in v["text"]
    assert v["text"] in text.replace("\n", " ")
    for banned in ("score total", "puntuación global", "Puntuación propietaria"):
        assert banned not in text.lower(), banned
    assert "total_score" not in a["score"] and "max_score" not in a["score"]


def price_excludes_quality_built_bonuses(a, text):
    metrics = {x["metric"] for x in a["score"]["breakdown"]["Valoración"]["adjustments"]}
    assert not metrics & {"Perfil GARP", "Growth Quality", "Ajuste Growth", "Ajuste Crecimiento"}


def eps_vs_revenue_growth_is_informative_only(a, text):
    e = a.get("eps_vs_revenue_growth")
    metrics = {x["metric"] for c in a["score"]["breakdown"].values() for x in c["adjustments"]}
    assert not any("frente a ingresos" in m for m in metrics)
    if e:
        assert e["scored"] is False and "Dato informativo, no puntúa" in text.replace("\n", " ")


def multiples_block_averages_members_and_caps_at_max(a, text):
    by_n = cfg("thresholds.score.valoracion.multiples_block_max_by_members")
    val = a["score"]["breakdown"]["Valoración"]
    members = [x for x in val["adjustments"] if x.get("in_block")]
    blk = [x for x in val["adjustments"] if x["metric"].startswith("Bloque")]
    if not members:
        assert not blk
        return
    # Fase 3 (T4): un banco tiene dos bloques (P/B y P/TBV frente a sus justificados; múltiplos frente al sector,
    # con el P/E que sí le aplica): cada miembro pertenece a uno y cada bloque se comprueba con los suyos.
    assert blk and sum(len(b["block_members"]) for b in blk) == len(members)
    for b in blk:
        n = len(b["block_members"])
        M = by_n[min(n, len(by_n)) - 1]
        assert b["block_max"] == M
        raw = b["block_mean"] * M
        assert abs(b["adjustment"]) <= M
        assert b["adjustment"] == int(abs(raw) + 0.5) * (1 if raw >= 0 else -1)
    counted = sum(x["adjustment"] for x in val["adjustments"] if not x.get("in_block"))
    assert val["score"] == max(0, min(20, 10 + counted))


def normalized_figures_are_labelled(a, text):
    metrics = [x["metric"] for c in a["score"]["breakdown"].values() for x in c["adjustments"]]
    if not (a.get("earnings_normalization") or {}).get("differs"):
        assert not any("normalizado" in m and "EV/EBITDA" not in m and "P/FCF" not in m for m in metrics)
        return
    en = a["earnings_normalization"]
    if any(i.get("applied") and i["type"] == "estructural" for i in en.get("items") or []):
        # Fase 7 (registro #36): una aseguradora se valora sobre su beneficio operativo: el P/E del análisis ya es el
        # operativo (rotulado así) y la rentabilidad solo lleva "normalizado" si OTRAS partidas la cambian.
        assert a["key_metrics"].get("pe_basis") in ("operativo", "operativo_negativo")
        assert "P/E operativo" in text
        assert ("ROE normalizado" in metrics) == bool(en.get("quality_differs") and a["key_metrics"].get("roe") is not None)
        return
    assert "ROE" not in metrics and "Margen Neto" not in metrics
    if "ROE normalizado" in metrics:
        assert all("ROE" not in x["reason"].split(" — ")[0] or "normalizado" in x["reason"]
                   for k in ("red_flags", "warnings", "strengths") for x in a["alerts"][k]
                   if x["category"] == "Rentabilidad" and x["reason"].startswith("ROE"))
    cover = text.split("===== página 2")[0]
    if a["classification"]["archetype"] not in ("REIT", "GROWTH_PRE_PROFIT"):
        assert "REPORTADO" in cover


def range_52w_is_position_only(a, text):
    assert "PRECIO · 52 SEM." not in text and "¿Cara o barata hoy?" not in text
    for line in text.splitlines():
        if "52 semanas" in line or "52 SEM" in line:
            assert not re.search(r"\bcara\b|barata", line, re.I), line


def no_text_cites_a_not_applicable_metric(a, text):
    na = set(cfg(f"sectors.archetypes.not_applicable.{a['classification']['archetype']}"))
    flat = text.replace("\n", " ")
    if "pe" in na:
        assert "Número de Graham" not in flat and "número de Graham" not in flat
        assert not re.search(r"el mercado paga [\d.]+x beneficios", flat, re.I)
    if "eps_growth" in na:
        assert "Crecimiento de beneficios" not in flat
    alerts = " ".join(x["reason"] for k in ("red_flags", "warnings", "strengths") for x in a["alerts"][k])
    if "roe" in na:
        assert not alerts.startswith("ROE") and " ROE " not in f" {alerts} "


def cover_fits_one_page(a, text):
    p2 = text.split("===== página 2 =====")[1].split("===== página 3")[0]
    assert "FORTALEZA CLAVE" not in p2 and "VEREDICTO" not in p2[:400]


# ═══════════════════════ test_validation ═══════════════════════

def provenance_in_vocabulary(a, text):
    """La parte genérica: la ruta (local = quoteSummary, prod = plan B) es atada al juego."""
    dp_ = a["data_provenance"]
    assert dp_["fields"]
    assert {v["source"] for v in dp_["fields"].values()} <= PROVENANCE_VOCAB
    assert isinstance(a["data_validation"], list)
    for f in a["data_validation"]:
        assert f["action"] in {"recalculado", "sin_dato", "aviso", "politica", "invalido"} and f["reason"], f


# ═══════════════════════ test_panel_cases (antes test_muestra) ═══════════════════════

def no_archetype_codes_nor_sign_after_symbol(a, text):
    bad = [f"{path}: {v[:120]}" for path, v in _prose_strings(a["display"]) if CODES.search(v) or BAD_SIGN.search(v)]
    for line in reading_text(text).splitlines():
        if CODES.search(line) or BAD_SIGN.search(line):
            bad.append(f"PDF: {line[:120]}")
    assert not bad, "\n".join(bad[:30])


def dcf_never_negative_fair_value(a, text):
    fv = (a.get("dcf") or {}).get("fair_value")
    assert fv is None or fv > 0, fv


# ═══════════════════════ test_display_charts ═══════════════════════

def chart_gauges_marker_in_reading_zone(a, text):
    """Devuelve cuántos marcadores comprobó (el test agregado exige un mínimo)."""
    checked = 0
    for g in a["display"]["charts"]["solvency"]["gauges"]:
        assert g["state"] in CHART_STATES, g
        if g["state"] != "con_dato" or g.get("informative") or g.get("net_cash") or g.get("negative") or g.get("no_burden"):
            assert g["state"] == "con_dato" or g.get("text") or g["state"] == "sin_dato", g
            continue
        z = _zone_of(g["zones"], g["value"])
        assert g["reading"].startswith(z["label"]), (g["key"], g["value"], z, g["reading"])
        assert z["tone"] == g["tone"] or g["reading"] != z["label"], g["key"]
        checked += 1
    return checked


def chart_fair_value_in_badge_zone(a, text):
    fv = a["display"]["charts"]["valuation"]["fair_value"]
    assert fv["state"] in CHART_STATES
    if fv["state"] != "con_dato":
        assert fv["state"] == "sin_dato" or fv.get("text"), fv
        return 0
    z = _zone_of(fv["zones"], fv["price"])
    assert fv["badge"]["label"].replace(" (fiabilidad baja)", "") == z["label"], (fv["price"], z, fv["badge"])
    lo, hi = fv["axis"]
    assert lo < fv["price"] < hi and lo < fv["fair_value"] < hi
    return 1


def chart_altman_in_model_zone(a, text):
    al = a["display"]["charts"]["institutional"]["altman"]
    if al["state"] == "con_dato":
        assert _zone_of(al["zones"], al["value"])["label"] == al["zone"], al
    else:
        assert al["state"] in CHART_STATES and al.get("text"), al


def chart_comparison_only_applicable_metrics(a, text):
    c = a["display"]["charts"]["comparison"]
    na = set(a["display"]["na_keys"])
    keys = {i["key"] for g in c["groups"] for i in g["items"]}
    if "pe" in na:
        assert "pe" not in keys
    if "roe" in na:
        assert "roe" not in keys
    assert c["total"] == len(keys) and 0 <= c["better"] <= c["total"]
    assert c["note"]
    for g in c["groups"]:
        for i in g["items"]:
            assert (i["tone"] == "pos") == (i["reading"] in ("Muy superior", "Superior", "Descuento profundo",
                                                              "Descuento")), i


def chart_multiples_role_matches_breakdown(a, text):
    V = a["display"]["charts"]["valuation"]
    adj = a["score"]["breakdown"]["Valoración"]["adjustments"]
    n_members = sum(1 for x in adj if x.get("in_block"))
    shown = [m for m in V["multiples"] if m["role"] == "block"] + [s for s in V["scored"] if s["in_block"]]
    assert len(shown) == n_members, (n_members, shown)
    if n_members:
        assert V["block"] and V["block"]["label"].startswith("Bloque")


def chart_upside_phrase_follows_grid(a, text):
    blob = json.dumps({"d": a["display"], "al": a.get("alerts")}, ensure_ascii=False)
    assert "muy optimistas" not in blob
    fv = a["display"]["charts"]["valuation"]["fair_value"]
    rel = (a.get("dcf") or {}).get("reliability") or {}
    if fv["state"] != "con_dato" or not fv.get("badge") or \
            not fv["badge"]["label"].startswith(("Prima", "Sobrevalorada")):
        return
    assert fv["method"] == "DCF"
    if rel.get("grid_contains_price") is True and rel.get("level") != "baja":
        assert "exigentes pero posibles" in fv["text"], fv["text"]
    if rel.get("grid_contains_price") is False:
        assert "exigentes pero posibles" not in fv["text"] and "ningún supuesto razonable" in fv["text"]


# Catálogo: nombre -> (función, archivo de origen). Lo recorre test_panel_invariants.
GENERIC = {f.__name__: f for f in (
    piotroski_state_is_structured, display_contract, institutional_not_applicable_never_zero,
    confidence_reasons_translated, tooltips_only_applied_bands, visible_texts_without_jargon_or_bad_formats,
    growth_texts_cite_the_scored_figure, piotroski_criteria_in_spanish, price_wording_without_jargon,
    verdict_in_pdf, price_excludes_quality_built_bonuses, eps_vs_revenue_growth_is_informative_only,
    multiples_block_averages_members_and_caps_at_max, normalized_figures_are_labelled,
    range_52w_is_position_only, no_text_cites_a_not_applicable_metric, cover_fits_one_page,
    provenance_in_vocabulary, no_archetype_codes_nor_sign_after_symbol, dcf_never_negative_fair_value,
    chart_gauges_marker_in_reading_zone, chart_fair_value_in_badge_zone, chart_altman_in_model_zone,
    chart_comparison_only_applicable_metrics, chart_multiples_role_matches_breakdown,
    chart_upside_phrase_follows_grid,
)}
