"""V7 (nombres en español): ninguna industria ni sector del universo, de las referencias de Damodaran ni del panel
queda sin traducción (config/names.toml, lib/names.py)."""
import csv
import re
import glob
import json
import os

import pytest
import tomllib

import names
from settings import cfg

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "..", "config")


def _universe():
    with open(os.path.join(CONFIG, "universe.tsv"), encoding="utf-8") as fh:
        return list(csv.DictReader((ln for ln in fh if not ln.startswith("#")), delimiter="\t"))


def test_every_universe_industry_and_sector_is_translated():
    rows = _universe()
    assert rows
    missing = sorted({r["damodaran_industry"] for r in rows if r["damodaran_industry"]
                      and not names.translated("damodaran", r["damodaran_industry"])}
                     | {r["gics_sector"] for r in rows if not names.translated("sector", r["gics_sector"])})
    assert not missing, missing


def test_every_damodaran_industry_is_translated():
    with open(os.path.join(CONFIG, "industries.toml"), "rb") as fh:
        regions = tomllib.load(fh)["regions"]
    every = {i for r in regions.values() for i in r["industries"]}
    assert not sorted(i for i in every if not names.translated("damodaran", i))
    assert not sorted(set(cfg("names.damodaran")) - every), "traducciones de industrias que ya no existen"


@pytest.mark.parametrize("env", ["panel", "local"])
def test_every_panel_profile_is_translated(env):
    seen = 0
    for f in glob.glob(os.path.join(HERE, "golden", env, "*.json")):
        with open(f, encoding="utf-8") as fh:
            p = json.load(fh).get("profile") or {}
        for kind, v in (("sector", p.get("sector")), ("industry", p.get("industry"))):
            if v:
                seen += 1
                assert names.translated(kind, v), f"{os.path.basename(f)}: {kind} «{v}» sin traducción"
    assert seen


def test_dash_forms_and_inline():
    assert names.industry("Beverages—Non-Alcoholic") == names.industry("Beverages - Non-Alcoholic") == "Bebidas sin alcohol"
    assert names.sector("Consumer Defensive") == "Consumo defensivo"
    assert names.sector("Consumer Staples") == "Consumo básico"
    assert names.damodaran("Computers/Peripherals") == "Ordenadores y periféricos"
    assert names.industry("Industria inventada") == "Industria inventada"   # sin traducción: el original, sin bloquear
    assert names.inline("Electrónica de consumo") == "electrónica de consumo"
    assert names.inline("REIT de locales comerciales") == "REIT de locales comerciales"


# P8 (retoque 2): las formas jurídicas que el cintillo no muestra (Co., Company y Holdings, solo tras coma)
_LEGAL_END = re.compile(r"(?:,?\s+(?:Inc\.?|Corp\.?|Corporation|plc|PLC|p\.l\.c\.|N\.?V\.?|S\.A\.|AG|SE|Ltd\.?|LTD|"
                        r"Limited|A S|A/S|Class [ABC])|,\s*(?:Co\.?|Company|Holdings)|\s*\((?:The|Class [ABC])\))$")


def test_universe_display_names_have_no_legal_form():
    import universe
    rows = universe.load()
    assert len(rows) > 500
    bad = [(r["symbol"], r["display_name"]) for r in rows if not (r["display_name"] or "").strip()
           or _LEGAL_END.search(r["display_name"]) or r["display_name"].rstrip().endswith((",", "/"))]
    assert not bad, bad
    # sin nombres en mayúsculas de EDGAR («TOYOTA MOTOR CORP/»): las siglas cortas sí («ASML», «BBVA»)
    shouty = [(r["symbol"], r["display_name"]) for r in rows
              if sum(1 for w in r["display_name"].split() if len(w) >= 6 and w.isupper()) >= 1
              and len(r["display_name"].split()) > 1]
    assert not shouty, shouty


def test_company_rule_and_exceptions():
    assert names.company("Apple Inc.") == "Apple"
    assert names.company("Tesla, Inc.") == "Tesla"
    assert names.company("Alphabet Inc. (Class A)") == "Alphabet"
    assert names.company("Home Depot (The)") == "Home Depot"
    assert names.company("Chubb Limited") == "Chubb"
    assert names.company("Deere & Company") == "Deere & Company"       # «Company» sin coma: es parte del nombre
    assert names.company("Booking Holdings") == "Booking Holdings"     # «Holdings» sin coma, también
    assert names.company("Foo Bar, Holdings") == "Foo Bar"
    assert names.company("The Coca-Cola Company") == "Coca-Cola"       # excepción de config
    assert names.company("TOYOTA MOTOR CORP/") == "Toyota"
    assert names.company("Inc.") == "Inc."                              # nunca vacío


def test_every_country_is_translated():
    """País del emisor en español (PM, rediseño v4): todos los países de las regiones de referencia y del panel."""
    every = {c for cs in cfg("sectors.benchmarks.regions").values() for c in cs}
    for env in ("panel", "local"):
        for f in glob.glob(os.path.join(HERE, "golden", env, "*.json")):
            with open(f, encoding="utf-8") as fh:
                c = (json.load(fh).get("profile") or {}).get("country")
            if c:
                every.add(c)
    assert "United States" in every and "Taiwan" in every
    assert not sorted(c for c in every if not names.translated("country", c))
    assert names.country("United States") == "Estados Unidos"
    assert names.country("Netherlands") == "Países Bajos"
    assert names.country(" Taiwan ") == "Taiwán"
    assert names.country("Atlantis") == "Atlantis"                   # sin traducción: el original, sin bloquear
    assert names.country(None) is None

