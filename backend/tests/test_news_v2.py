"""Rediseño E2a (T8): noticias con resumen, imagen (solo https), categoría, fecha y hora, e idioma original; hasta
`news_max_v2` en el análisis, y la web actual sigue con `news_max` (display)."""
import finnhub_fallback as fh
import market_context as mc
from settings import cfg

LONG = ("Apple unveiled a new line of products on Tuesday, including updated laptops and tablets, as the company "
        "seeks to revive demand ahead of the holiday season. Analysts said the launch could lift revenue in the "
        "December quarter, although supply constraints remain a concern for several key components and markets.")


def _raw():
    out = []
    for i in range(8):
        out.append({"datetime": 1760000000 + i * 3600, "headline": f"Apple titular {i}", "related": "AAPL",
                    "source": "Reuters", "url": f"https://x/{i}", "summary": LONG if i % 2 else "Corto.",
                    "image": "http://img/insegura.jpg" if i == 7 else f"https://img/{i}.jpg", "category": "company"})
    return out


def test_campos_nuevos_y_corte(monkeypatch):
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: _raw())
    n = mc.news("AAPL", "Apple Inc.")
    C = cfg("market.context")
    assert len(n["items"]) == C["news_max_v2"] == 6
    first = n["items"][0]
    assert first["headline"] == "Apple titular 7" and first["image"] is None          # http:// no se publica
    assert n["items"][1]["image"] == "https://img/6.jpg"
    assert first["datetime"] == "2025-10-09T15:53:20Z" and first["date"] == "2025-10-09"
    assert first["lang"] == C["news_lang"] == "en" and first["category"] == "company"
    s = first["summary"]
    assert len(s) <= C["news_summary_chars"] + 1 and s.endswith("…") and not s[:-1].endswith(" ")
    assert LONG.startswith(s[:-1])
    assert n["items"][1]["summary"] == "Corto."


def test_la_web_actual_sigue_con_news_max(monkeypatch):
    import display
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: _raw())
    blk = display._market_block({"market_context": {"news": mc.news("AAPL", "Apple Inc."), "readings": [], "behavioral": []}})
    assert len(blk["news"]) == cfg("market.context.news_max") == 5
    assert set(blk["news"][0]) == {"date", "source", "headline", "url"}


def test_una_imagen_repetida_es_el_logo_del_medio(monkeypatch):
    """Yahoo publica su logotipo genérico como imagen de muchos titulares: una imagen que se repite en titulares
    distintos no es una foto de la noticia y no se publica."""
    raw = _raw()
    for x in raw[:4]:
        x["image"] = "https://s.yimg.com/logo_generico.png"
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: raw)
    imgs = {x["headline"]: x["image"] for x in mc.news("AAPL", "Apple Inc.")["items"]}
    assert all(imgs[f"Apple titular {i}"] is None for i in range(4) if f"Apple titular {i}" in imgs)
    assert imgs["Apple titular 6"] == "https://img/6.jpg"


def _item(i, headline, summary="", related="AAPL"):
    return {"datetime": 1760000000 + i * 3600, "headline": headline, "summary": summary, "related": related,
            "source": "Yahoo", "url": f"https://x/{i}", "image": None, "category": "company"}


def test_solo_titulares_que_mencionan_a_la_empresa(monkeypatch):
    """Revisión del PM: Finnhub pone AAPL en `related` de noticias generales del mercado. Una noticia entra solo si el
    titular o el resumen nombran a la empresa (ticker como palabra o nombre corto sin sufijos societarios)."""
    raw = [_item(1, "CPI Pressures Markets And Fed Reserve's Move On Interest Rates", "Hot CPI report upends markets."),
           _item(2, "Reese Witherspoon Buys Back Production Firm With Mediawan", "Bloomberg's Chris Palmeri joins…"),
           _item(3, "Apple Stock May Be Peaking After Hitting New All-Time Highs"),
           _item(4, "Tech stocks to watch", "Shares of AAPL and MSFT moved after the open."),
           _item(5, "Pineapple prices rise", "AAPLX is not a ticker")]
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: raw)
    n = mc.news("AAPL", "Apple Inc.")
    assert [x["headline"] for x in n["items"]] == ["Tech stocks to watch",
                                                  "Apple Stock May Be Peaking After Hitting New All-Time Highs"]
    assert n["total"] == 2


def test_ticker_de_una_letra_y_nombre_de_palabras_comunes(monkeypatch):
    """O (Realty Income): ni una «O» suelta ni «Realty» o «Income» solas cuentan; sí el nombre completo o «(O)»."""
    raw = [_item(1, "Plan O for the Fed", "Option O is on the table", related="O"),
           _item(2, "Realty stocks rally on lower rates", "Income investors pile in", related="O"),
           _item(3, "Better High-Yield Dividend Stock: Realty Income vs. Crown Castle", related="O"),
           _item(4, "3 REITs to buy now", "including Realty (O) and others", related="O")]
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: raw)
    n = mc.news("O", "Realty Income Corporation")
    assert [x["headline"] for x in n["items"]] == ["3 REITs to buy now",
                                                  "Better High-Yield Dividend Stock: Realty Income vs. Crown Castle"]


def test_nombre_corto_de_la_empresa():
    assert mc.mention_terms("XOM", "Exxon Mobil Corporation") >= {"exxon mobil", "exxonmobil", "exxon"}
    assert mc.mention_terms("JPM", "JPMorgan Chase & Co.") >= {"jpmorgan chase", "jpmorgan"}
    assert mc.mention_terms("O", "Realty Income Corporation") == {"realty income", "realtyincome"}
    assert mc.mention_terms("BCS", "Barclays PLC") == {"barclays"}


def test_sin_titulares_de_la_empresa_dice_por_que(monkeypatch):
    monkeypatch.setattr(fh, "is_enabled", lambda: True)
    monkeypatch.setattr(fh, "company_news", lambda s, a, b: [_item(1, "CPI Pressures Markets")])
    n = mc.news("AAPL", "Apple Inc.")
    assert n["items"] == [] and n["total"] == 0 and "menciona a la empresa" in n["reason"]
