"""
V4-F8 (PM, 27-oct-2026): la cabecera resume y la sección detalla. Cada nota de una puntuación (persistencia, frontera,
baja confianza, ajuste por confianza) tiene una forma corta (`note_short`) para la cabecera; la frase completa (`note`)
sigue en el desglose de «La empresa». Genérico: cualquier nota nueva aporta sus dos formas.
"""
import display


def test_note_short_une_las_piezas_cortas():
    assert display.note_short([None, ""]) is None
    assert display.note_short(["exige persistencia (88 → 87)."]) == "Exige persistencia (88 → 87)"
    assert display.note_short(["ajustado de 45 a 46 por confianza media",
                               display.border_short({"neighbor": "exigente", "points": 2})]) == (
        "Ajustado de 45 a 46 por confianza media · en la frontera con «exigente» (a 2 puntos)")
    assert display.border_short({"neighbor": "media", "points": 1}) == "en la frontera con «media» (a 1 punto)"
    assert display.border_short(None) is None


def test_cabecera_corta_y_seccion_completa(outputs_by_env):
    """PLTR (panel): la cabecera dice «Exige persistencia (94 → 90)» (F10: el crecimiento del FCF desde un año base
    anómalo ya no puntúa; antes 99 → 95); la frase completa, con la categoría y los
    ejercicios, sigue en `note`. La corta nunca es más larga que la completa. F8 (fusión): antes, AAPL (88 → 87); con
    el peso nuevo de Altman su calidad queda en 82 y la persistencia no corta."""
    a = outputs_by_env("panel")["PLTR"][0]
    q = a["display"]["cover"]["quality"]
    assert q["note_short"] == "Exige persistencia (94 → 90)"
    assert q["note"].startswith("Por encima de 80 (umbral de persistencia; «excelente» empieza en 85), la calidad exige persistencia: 94 → 90.") and "ejercicios" in q["note"]
    for sym, (x, _pdf) in outputs_by_env("panel").items():
        if "display" not in x:          # SPY (ETF): sin puntuaciones
            continue
        for part in ("quality", "price"):
            c = x["display"]["cover"][part]
            assert (c.get("note") is None) == (c.get("note_short") is None), (sym, part)
            if c.get("note"):
                assert len(c["note_short"]) <= len(c["note"]), (sym, part)
