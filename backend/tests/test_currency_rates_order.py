"""
Los tipos de cambio usados por estado (`data_provenance.currency.rates`) salen con las claves ordenadas: los estados se
convierten desde descargas paralelas y el orden de llegada no debe cambiar el JSON (reexportar los fixtures de /v2,
BCS.json, no ensucia el árbol).
"""
from currency import StatementContext


def test_rates_keys_do_not_depend_on_conversion_order():
    a = StatementContext("BCS", "USD", "GBP", "test", None, ticker_cls=None)
    b = StatementContext("BCS", "USD", "GBP", "test", None, ticker_cls=None)
    q = {"2026-06-30": 1.34}
    a.rates.update(quarterly_income_stmt=q, quarterly_balance_sheet=q)    # como llegan si termina antes la de resultados
    b.rates.update(quarterly_balance_sheet=q, quarterly_income_stmt=q)
    assert list(a.summary()["rates"]) == list(b.summary()["rates"]) == ["quarterly_balance_sheet", "quarterly_income_stmt"]
