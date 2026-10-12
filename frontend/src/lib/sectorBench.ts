// Benchmarks sectoriales aproximados usados para contextualizar métricas en la
// UI. Los valores vienen GENERADOS desde backend/config/sectors.toml (la misma
// fuente que _get_sector_benchmarks de main.py): ver
// backend/tools/gen_frontend_config.py. PROVISIONALES: no son comparables reales.
import { SECTOR_DEFAULTS, SECTOR_MAP, type SectorBenchmarks } from "./generated/backendConfig";

export type { SectorBenchmarks };

export function getSectorBenchmarks(sector: string): SectorBenchmarks {
  const key = sector.toLowerCase().replace(/[\s-]+/g, "_");
  return { ...SECTOR_DEFAULTS, ...(SECTOR_MAP[key] || {}) };
}
