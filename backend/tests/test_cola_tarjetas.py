"""
E6 (31-oct): las tarjetas de la portada del día tienen prioridad en la caché de resúmenes de la cola. En producción,
10 empresas con sus 50 rivales dejaron 7 de 30 tarjetas con «Calidad · Precio»: los rivales las expulsaban y el
precalentado ya había gastado su cupo del día. Ahora los rivales solo compiten entre ellos; el tope no cambia.
"""
import analysis_queue as AQ
import trending
from settings import cfg
from test_trending import fresh  # noqa: F401 — fixture

CARDS = [f"C{i:02d}" for i in range(cfg("market.trending.prewarm_max"))]


def _put(sym):
    with AQ._lock:
        AQ._put(sym, {"quality": {"score": 50}})


def _day(cards):
    rows = [{"symbol": s} for s in cards]
    return {"lists": {"1D": {"most_traded": rows, "gainers": [], "losers": []}}}


def test_fifty_new_rivals_evict_no_card_of_the_day(fresh):  # noqa: F811
    AQ.pin(CARDS)
    for s in CARDS:
        _put(s)
    rivals = [f"R{i:02d}" for i in range(50)]
    for s in rivals:
        _put(s)
    assert all(AQ.cached(s) is not None for s in CARDS)
    cap = cfg("market.analysis_queue.summary_cache_max")
    kept = [s for s in rivals if AQ.cached(s) is not None]
    assert len(AQ._summaries) == cap                          # el tope no cambia
    assert kept == rivals[-(cap - len(CARDS)):]               # entre ellos, los rivales usados hace menos


def test_without_pinned_cards_it_is_a_plain_lru(fresh):  # noqa: F811
    for s in CARDS + [f"R{i:02d}" for i in range(50)]:
        _put(s)
    cap = cfg("market.analysis_queue.summary_cache_max")
    assert sum(AQ.cached(s) is not None for s in CARDS) == cap - 50


def test_the_prewarm_pins_the_cards_it_scores(fresh):  # noqa: F811
    many = CARDS + ["X1", "X2"]                               # más símbolos que el cupo del precalentado
    trending.prewarm(_day(many), today="2026-10-31")
    assert AQ._pinned == set(CARDS)
