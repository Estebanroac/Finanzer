"""
Arnés de carga (tools/load_test.py y tools/memory_profile.py): las tarjetas del precalentado se leen con la forma de
/api/v2/trending de P8b (`lists[periodo][lista]`). Con la forma de antes el arnés veía 0 tarjetas y dejaba de esperar
al precalentado, que caía dentro de la carga.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import load_test as LT  # noqa: E402
import memory_profile as MP  # noqa: E402


def _card(sym, status):
    return {"symbol": sym, "engine": {"status": status} if status else None}


def _resp(day, other=None):
    """Respuesta de /api/v2/trending sin `period`: todas las listas por periodo, 1D primero (orden de config)."""
    lists = {"1D": day, "1S": other or {"most_traded": [_card("ZZZ", "en_cola")], "gainers": [], "losers": []}}
    return {"status": "listo", "refreshing": False, "data": {"lists": lists}}


def test_prewarm_cards_reads_the_1d_lists_of_p8b():
    day = {"most_traded": [_card("AAA", "listo"), _card("BBB", "en_cola")], "gainers": [_card("CCC", "analizando")],
           "losers": [_card("DDD", None)]}
    cards = LT.prewarm_cards(_resp(day))
    assert [c["symbol"] for c in cards] == ["AAA", "BBB", "CCC", "DDD"]     # solo 1D: ZZZ (1S) no se precalienta


def test_prewarm_cards_without_data_is_empty():
    assert LT.prewarm_cards({"status": "calculando", "data": None}) == []


def test_memory_profile_waits_while_a_1d_card_is_being_analysed():
    busy = {"most_traded": [_card("AAA", "analizando")], "gainers": [], "losers": []}
    done = {"most_traded": [_card("AAA", "listo")], "gainers": [], "losers": [_card("BBB", "fallo")]}
    assert MP._settled(_resp(busy)) is False
    assert MP._settled(_resp(done, other=done)) is True
