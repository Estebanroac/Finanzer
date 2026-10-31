"""Rediseño E2b (Task 1): universo de valores de la portada y de los rivales preferentes (S&P 500 + ADR principales,
config/universe.tsv, generado por tools/build_universe.py). Sin red."""
import pytest

import universe
from settings import cfg

SAMPLE = """# GENERADO por tools/build_universe.py el 2026-10-17 desde https://example.org/sp500
symbol\tname\torigin\tgics_sector\tdamodaran_industry
AAPL\tApple Inc.\tsp500\tInformation Technology\tComputers/Peripherals
BRK.B\tBerkshire Hathaway\tsp500\tFinancials\tInsurance (Prop/Cas.)
DELL\tDell Technologies\tsp500\tInformation Technology\tComputers/Peripherals
TSM\tTaiwan Semiconductor\tadr\t\tSemiconductor
"""


@pytest.fixture
def fake_universe(tmp_path, monkeypatch):
    p = tmp_path / "universe.tsv"
    p.write_text(SAMPLE, encoding="utf-8")
    monkeypatch.setattr(universe, "UNIVERSE_FILE", str(p))
    universe.reset()
    yield p
    universe.reset()


def test_symbols_and_origin(fake_universe):
    assert universe.symbols() == ["AAPL", "BRK-B", "DELL", "TSM"]
    assert universe.symbols("adr") == ["TSM"]
    assert universe.symbols("sp500") == ["AAPL", "BRK-B", "DELL"]


def test_by_industry(fake_universe):
    assert universe.by_industry("Computers/Peripherals") == ["AAPL", "DELL"]
    assert universe.by_industry("Nada") == []


def test_meta_from_header(fake_universe):
    m = universe.meta()
    assert m == {"date": "2026-10-17", "source": "https://example.org/sp500", "count": 4}


def test_dot_symbol_normalized_and_rows(fake_universe):
    rows = {r["symbol"]: r for r in universe.load()}
    assert "BRK-B" in rows and "BRK.B" not in rows
    assert rows["TSM"]["gics_sector"] is None and rows["TSM"]["origin"] == "adr"
    assert universe.get("brk.b")["name"] == "Berkshire Hathaway"


def test_config_adrs_cover_adr_factors():
    """Cada ADR con factor en config/adr.toml está en la lista de ADR principales del universo."""
    adrs = set(cfg("market.universe.adrs"))
    factors = {s for s in cfg("adr.factors") if s != "BRK-B"}    # BRK-B no es un ADR (clase B; ya va en el S&P 500)
    assert factors <= adrs, sorted(factors - adrs)


def test_real_universe_file_is_dated_and_large():
    universe.reset()
    m = universe.meta()
    assert m["date"] and m["count"] >= 500
    assert len(universe.symbols("adr")) == len(cfg("market.universe.adrs"))
    assert all("." not in s for s in universe.symbols())


def test_every_symbol_has_a_sector():
    """P8: la portada lista por sector; ningún valor del universo real queda sin sector GICS (los ADR, de
    market.universe.adr_sectors), y la tabla de los ADR cubre todos los de market.universe.adrs con claves GICS."""
    universe.reset()
    rows = universe.load()
    assert [r["symbol"] for r in rows if not r.get("gics_sector")] == []
    gics = set(cfg("market.trending.sectors"))
    assert {r["gics_sector"] for r in rows} <= gics
    table = cfg("market.universe.adr_sectors")
    assert {universe.norm_symbol(s) for s in cfg("market.universe.adrs")} <= set(table)
    assert set(table.values()) <= gics
