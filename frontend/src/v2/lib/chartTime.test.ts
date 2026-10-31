import { describe, it, expect } from "vitest";
import { TickMarkType } from "lightweight-charts";
import { tickLabel } from "./chartTime";

describe("tickLabel (eje de la gráfica en español)", () => {
  it("meses abreviados en español", () => {
    expect(tickLabel({ year: 2026, month: 1, day: 5 }, TickMarkType.Month)).toBe("Ene");
    expect(tickLabel("2026-05-14", TickMarkType.Month)).toBe("May");
    expect(tickLabel("2026-09-01", TickMarkType.Month)).toBe("Sep");
  });
  it("año y día del mes", () => {
    expect(tickLabel("2026-01-02", TickMarkType.Year)).toBe("2026");
    expect(tickLabel({ year: 2026, month: 8, day: 21 }, TickMarkType.DayOfMonth)).toBe("21 Ago");
  });
});
