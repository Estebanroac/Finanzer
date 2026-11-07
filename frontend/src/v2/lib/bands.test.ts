import { describe, it, expect } from "vitest";
import { SCORE_BANDS } from "@/lib/generated/backendConfig";

describe("SCORE_BANDS (generado desde thresholds.toml)", () => {
  it("trae las bandas y rótulos de calidad del motor", () => {
    expect(SCORE_BANDS.quality.labels).toEqual(["excelente", "sólida", "media", "débil"]);
    expect(SCORE_BANDS.quality.bands.length).toBe(SCORE_BANDS.quality.labels.length - 1);
  });
  it("trae las bandas y rótulos de precio del motor", () => {
    expect(SCORE_BANDS.price.labels).toEqual(["atractivo", "razonable", "exigente"]);   // F16: regla L1
    expect(SCORE_BANDS.price.bands.length).toBe(SCORE_BANDS.price.labels.length - 1);
  });
});

describe("SCORE_BANDS.confidence (niveles de la consistencia)", () => {
  it("trae los dos niveles, del mejor al peor (lib/consistency.LEVELS)", () => {
    expect(SCORE_BANDS.confidence.labels).toEqual(["consistente", "mixta"]);
  });
});
