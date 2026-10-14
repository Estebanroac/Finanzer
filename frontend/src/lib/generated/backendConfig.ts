// GENERADO por backend/tools/gen_frontend_config.py desde backend/.
// NO EDITAR A MANO: cambia el backend y vuelve a ejecutar el generador.
// tests/test_frontend_config_sync.py falla si este archivo se desincroniza.

/** Arquetipos del clasificador único (sectors.toml [archetypes.not_applicable]). */
export type Archetype = "FINANCIAL" | "REIT" | "GROWTH_PRE_PROFIT" | "CYCLICAL" | "UTILITY" | "MATURE";

/** Rótulo de cada estado de una métrica (lib/display.py STATE_LABELS). */
export const STATE_LABELS = {
  con_dato: "Con dato",
  sin_dato: "Sin dato",
  no_aplica: "No aplica",
  no_significativo: "No significativo",
} as const;
