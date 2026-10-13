"""frontend/src/lib/generated/backendConfig.ts debe coincidir con el backend.

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


def test_frontend_has_no_band_or_median_copies():
    """Etapa 9b: las bandas y las medianas llegan en `display`; el frontend no guarda
    copias (ni generadas ni a mano): sin sectorBench.ts / metricScale.ts y sin
    `thresholds` en las definiciones de tooltips.ts."""
    lib = os.path.dirname(_gen().OUT).rsplit(os.sep, 1)[0]
    for name in ("sectorBench.ts", "metricScale.ts"):
        assert not os.path.exists(os.path.join(lib, name)), name
    tips = open(os.path.join(lib, "tooltips.ts"), encoding="utf-8").read()
    assert "thresholds" not in tips
    assert "SECTOR_DEFAULTS" not in _gen().render() and "METRIC_SCALE" not in _gen().render()


def test_benchmarks_match_main_py():
    """El PDF y la web usan exactamente las mismas medianas (las de main, vía display)."""
    import main
    from settings import cfg
    for sector in list(cfg("sectors.benchmarks.sectors")) + ["unknown"]:
        expected = {**dict(cfg("sectors.benchmarks.default")),
                    **dict(cfg("sectors.benchmarks.sectors").get(sector, {}))}
        assert main._get_sector_benchmarks(sector) == expected
