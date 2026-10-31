"""V7 (puntuación del motor): uniones sin «.;» y frases con su punto final (lib/prose.py)."""
import prose

KO_PERSIST = ("Por encima de 80 (umbral de persistencia; «excelente» empieza en 85), la calidad exige persistencia: 82 → 81. Rentabilidad: margen operativo positivo en 4 "
              "de 5 ejercicios; calidad de ganancias: FCF positivo en 3 de 5 ejercicios.")
KO_BORDER = ("En la frontera con «sólida» (a 2 puntos): un cambio pequeño en los datos o en los supuestos cambiaría "
             "el nivel")


def test_ko_quality_note_joins_without_dot_semicolon():
    """KO: «…en 3 de 5 ejercicios.; en la frontera con «sólida»… cambiaría el nivel» (sin punto final)."""
    t = prose.join_clauses([KO_PERSIST, KO_BORDER])
    assert ".;" not in t and ";." not in t and ".." not in t
    assert t.endswith("cambiaría el nivel.")
    assert "ejercicios; en la frontera con «sólida»" in t


def test_join_clauses_edge_cases():
    assert prose.join_clauses([None, ""]) is None
    assert prose.join_clauses(["ajustado de 65 a 61 por confianza media"]) == "ajustado de 65 a 61 por confianza media."
    assert prose.join_clauses(["Uno…", "Dos."]) == "Uno…; dos."


def test_close():
    assert prose.close("cambiaría el nivel") == "cambiaría el nivel."
    assert prose.close("cambiaría el nivel.") == "cambiaría el nivel."
    assert prose.close("(confianza alta)") == "(confianza alta)"
    assert prose.close("con «sólida»") == "con «sólida»"
    assert prose.close("sigue:") == "sigue."
    assert prose.close("") == ""


def test_kind_declares_labels_headlines_and_sentences():
    k = prose.kind
    assert k(".cover.quality.note", KO_BORDER) == "frase"
    assert k(".sections.profitability.rows[].text", "ROE (TTM) de 48.6% frente a 41.1% de su industria") == "frase"
    assert k(".sections.profitability.rows[].label", "Margen FCF − SBC") == "etiqueta"
    assert k(".sections.alerts.groups[].items[].reason", "Autofinanciada en caja — FCF TTM positivo") == "titular"
    assert k(".methodology.models_text", "Altman (1968), Piotroski (2000), un DCF multietapa") == "fragmento"
    assert k(".extended.news[].headline", "Better High-Yield Dividend Stock: Realty Income vs. Clorox") == "externo"
    assert k(".nuevo.campo_largo", "un texto largo que nadie ha declarado") is None
    assert k(".nuevo.campo_corto", "Corto sin declarar") == "etiqueta"


def test_close_sentences_closes_only_sentences():
    d = {"cover": {"quality": {"note": KO_BORDER, "title": "CALIDAD DEL NEGOCIO"},
                   "highlights": [{"text": "Crea mucho valor — spread +54.1 pp", "kicker": "FORTALEZA CLAVE"}]},
         "methodology": {"models_text": "Altman (1968), Piotroski (2000), un DCF multietapa"}}
    prose.close_sentences(d)
    assert d["cover"]["quality"]["note"].endswith("el nivel.")
    assert d["cover"]["highlights"][0]["text"] == "Crea mucho valor — spread +54.1 pp"
    assert d["methodology"]["models_text"].endswith("multietapa")
