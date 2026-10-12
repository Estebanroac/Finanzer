"""
Genera frontend/src/lib/generated/backendConfig.ts desde backend/config/.

El frontend (export estático de Next.js) usa las medianas sectoriales y las
bandas de color de las métricas. En lugar de mantener copias a mano, este
script las vuelca desde la config única del backend:

    python3 backend/tools/gen_frontend_config.py          # escribe el .ts
    python3 backend/tools/gen_frontend_config.py --check  # 1 si está desincronizado

tests/test_frontend_config_sync.py falla si el .ts no coincide con la config.
Tras regenerar con valores distintos hay que reconstruir frontend/out (build.sh
no lo hace en Render).
"""
import json
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BACKEND, "lib"))
OUT = os.path.normpath(os.path.join(BACKEND, "..", "frontend", "src", "lib", "generated", "backendConfig.ts"))

from settings import cfg  # noqa: E402


def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"valor no numérico en la config del frontend: {v!r}")
    return repr(v)


def _obj(d, indent="  "):
    items = [f"{indent}{k}: {_num(v)}," for k, v in d.items()]
    return "{\n" + "\n".join(items) + "\n" + indent[:-2] + "}"


def _pairs(d):
    return "{\n" + "\n".join(f"  {k}: [{', '.join(_num(x) for x in v)}]," for k, v in d.items()) + "\n}"


def render() -> str:
    bench = cfg("sectors.benchmarks")
    lv = cfg("thresholds.score.total.level_bands")
    pio = cfg("valuation.models.piotroski.bands")
    ms = cfg("thresholds.ui.metric_scale")
    sectors = "{\n" + "\n".join(
        f"  {name}: {{ " + ", ".join(f"{k}: {_num(v)}" for k, v in vals.items()) + " },"
        for name, vals in bench["sectors"].items()) + "\n}"
    keys = " ".join(f"{k}: number;" for k in bench["default"])
    return f"""// GENERADO por backend/tools/gen_frontend_config.py desde backend/config/.
// NO EDITAR A MANO: cambia el TOML y vuelve a ejecutar el generador.
// tests/test_frontend_config_sync.py falla si este archivo se desincroniza.

/** Medianas sectoriales PROVISIONALES (sectors.toml [benchmarks]). */
export interface SectorBenchmarks {{ {keys} }}

export const SECTOR_DEFAULTS: SectorBenchmarks = {_obj(bench["default"])};

export const SECTOR_MAP: Record<string, Partial<SectorBenchmarks>> = {sectors};

/** Niveles del score: Excelente / Favorable / Neutral / Precaución / Evitar (thresholds.toml [score.total]). */
export const SCORE_LEVEL_BANDS = [{', '.join(_num(x) for x in lv)}] as const;

/** Piotroski F-Score: Fuerte / Bueno / Neutral / Débil / Crítico (valuation.toml [models.piotroski]). */
export const PIOTROSKI_BANDS = [{', '.join(_num(x) for x in pio)}] as const;

/** Bandas de color de la UI (thresholds.toml [ui.metric_scale]). */
export const METRIC_SCALE_HIGHER: Record<string, [number, number]> = {_pairs(ms["higher"])};

export const METRIC_SCALE_LOWER: Record<string, [number, number]> = {_pairs(ms["lower"])};

export const METRIC_SCALE_SPECIAL = {{
  dividend_yield: [{', '.join(_num(x) for x in ms["special"]["dividend_yield"])}] as const,
  payout_ratio: [{', '.join(_num(x) for x in ms["special"]["payout_ratio"])}] as const,
  buyback_yield: [{', '.join(_num(x) for x in ms["special"]["buyback_yield"])}] as const,
  shareholder_yield: [{', '.join(_num(x) for x in ms["special"]["shareholder_yield"])}] as const,
  beta: [{', '.join(_num(x) for x in ms["special"]["beta"])}] as const,
}};
"""


def main():
    content = render()
    current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
    if "--check" in sys.argv:
        if current != content:
            print(f"DESINCRONIZADO: {OUT}\n  ejecuta: python3 backend/tools/gen_frontend_config.py")
            sys.exit(1)
        print("sincronizado")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"escrito {OUT}")


if __name__ == "__main__":
    main()
