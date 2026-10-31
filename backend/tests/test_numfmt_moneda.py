"""Fiabilidad (V4 · moneda): los importes del motor se escriben en la moneda de la cifra (la del precio en el análisis;
la de los estados en la historia de EDGAR). En USD, «$»; en otra, su código delante, como la cabecera de /v2."""
import numfmt


def test_usd_is_unchanged():
    assert numfmt.money(45.18e9) == "$45.18B" and numfmt.price(-1.1) == "−$1.10" and numfmt.whole(142.4) == "$142"
    assert numfmt.amount(2.5) == "$2.50 por acción"


def test_other_currency_writes_its_code():
    with numfmt.currency("EUR"):
        assert numfmt.money(195.71e9) == "EUR 195.71B" and numfmt.price(397) == "EUR 397.00"
        assert numfmt.price(-1.1) == "−EUR 1.10" and numfmt.whole(872) == "EUR 872"
        assert numfmt.money(41.27e9, "GBP") == "GBP 41.27B"          # la moneda explícita manda (estados en GBP)
        assert numfmt.money(1e9, "USD") == "$1.00B"
    assert numfmt.price(397) == "$397.00"                               # al salir, la de antes


def test_analysis_does_not_leak_its_currency(monkeypatch):
    """Tras un análisis en EUR (aunque falle), el hilo vuelve a USD: el resumen de la cola formatea después."""
    import main

    def body(sym):
        numfmt.set_currency("EUR")
        assert numfmt.price(1) == "EUR 1.00"
        raise RuntimeError("alto")
    monkeypatch.setattr(main, "_compute_analysis_body", body)
    try:
        main._compute_analysis("MC.PA")
    except RuntimeError:
        pass
    assert numfmt.price(1) == "$1.00"


def test_queue_summary_cap_in_euros():
    import analysis_queue as AQ
    assert AQ._cap_txt(195.71e9, "EUR") == "EUR 195.71B" and AQ._cap_txt(3e12, "USD") == "$3.00T"
    assert AQ._cap_txt(None, "EUR") == "N/A"
