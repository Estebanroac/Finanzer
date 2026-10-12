"""frontend/src/lib/generated/backendConfig.ts debe coincidir con backend/config/.

Si falla: python3 backend/tools/gen_frontend_config.py (y reconstruir
frontend/out si los valores cambiaron)."""
import importlib.util
import os

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")


def _gen():
    spec = importlib.util.spec_from_file_location("gen_frontend_config", os.path.join(TOOLS, "gen_frontend_config.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_generated_frontend_config_in_sync():
    gen = _gen()
    assert os.path.exists(gen.OUT), f"falta {gen.OUT}: ejecuta backend/tools/gen_frontend_config.py"
    with open(gen.OUT, encoding="utf-8") as fh:
        on_disk = fh.read()
    assert on_disk == gen.render(), ("backendConfig.ts desincronizado con backend/config: "
                                     "ejecuta python3 backend/tools/gen_frontend_config.py")


def test_frontend_sources_import_generated_values():
    """sectorBench.ts y metricScale.ts no deben volver a tener copias a mano."""
    lib = os.path.dirname(_gen().OUT).rsplit(os.sep, 1)[0]
    for name in ("sectorBench.ts", "metricScale.ts"):
        src = open(os.path.join(lib, name), encoding="utf-8").read()
        assert "./generated/backendConfig" in src, name
    sb = open(os.path.join(lib, "sectorBench.ts"), encoding="utf-8").read()
    assert "pe: 22" not in sb and "technology:" not in sb


def test_benchmarks_match_main_py():
    """La UI y el PDF usan exactamente las mismas medianas."""
    import main
    gen = _gen()
    from settings import cfg
    for sector in list(cfg("sectors.benchmarks.sectors")) + ["unknown"]:
        expected = {**dict(cfg("sectors.benchmarks.default")),
                    **dict(cfg("sectors.benchmarks.sectors").get(sector, {}))}
        assert main._get_sector_benchmarks(sector) == expected
    assert "SECTOR_DEFAULTS" in gen.render()
