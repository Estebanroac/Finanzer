import { describe, it, expect } from "vitest";
import { buildReadings, CHAPTER_ORDER, FIGURES_PER_CHAPTER } from "./story";
import type { StockAnalysis } from "@/lib/api";

const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"] as const;

describe.each(TICKERS)("buildReadings(%s)", (t) => {
  it("da la lectura de las 9 secciones, en orden y sin huecos", async () => {
    const a = (await import(`@/v2/__fixtures__/${t}.json`)).default as unknown as StockAnalysis;
    const story = buildReadings(a);
    expect(story.map((c) => c.id)).toEqual(CHAPTER_ORDER);
    for (const c of story) {
      expect(c.lead.trim().length, `${t}/${c.id} lead`).toBeGreaterThan(0);
      // V4b · 4 (PM): las que haya (sin cajas de relleno «— / Sin dato»), como mucho tres
      expect(c.figures.length, `${t}/${c.id} figuras`).toBeLessThanOrEqual(FIGURES_PER_CHAPTER);
      for (const f of c.figures) expect(f.value.trim(), `${t}/${c.id}/${f.label}`).not.toMatch(/^(|—|Sin dato)$/);
    }
  });
});

describe("buildReadings(AAPL) contenido", () => {
  it("la conclusión lee el veredicto", async () => {
    const a = (await import("@/v2/__fixtures__/AAPL.json")).default as unknown as StockAnalysis;
    expect(buildReadings(a).find((c) => c.id === "conclusion")!.lead).toContain(a.display.cover.verdict.text);
  });
});

describe("buildReadings(PLTR): la nota de la puntuación de calidad", () => {
  it("no va en la lectura (está en la cabecera, con la puntuación)", async () => {
    const a = (await import("@/v2/__fixtures__/PLTR.json")).default as unknown as StockAnalysis;
    expect(a.display.cover.quality.note!).toContain("persistencia");
    expect(buildReadings(a).find((c) => c.id === "calidad")!.lead).not.toContain("persistencia");
  });
});

describe("buildReadings: rivales (V7 · P5)", () => {
  // F10 · N2: AAPL es el 91 % de su industria de Damodaran; su referencia es la mediana de sus pares (abajo)
  it("«agregado», no «mediana»; una métrica mejor y una peor", async () => {
    const a = (await import("@/v2/__fixtures__/JPM.json")).default as unknown as StockAnalysis;
    const riv = buildReadings(a).find((c) => c.id === "rivales")!;
    expect(riv.lead).toContain("agregado");
    expect(riv.lead).not.toContain("mediana");
    const [count, best, worst] = riv.figures;
    expect(count.label).toBe("Mejor que el agregado");
    expect(best.label).toMatch(/^Mejor · /);
    expect(best.tone).toBe("good");
    expect(worst.label).toMatch(/^Peor · /);
    expect(worst.tone).toBe("bad");
  });
});

describe.each(TICKERS)("buildReadings(%s) sin repeticiones ni contenido fuera de lugar", (t) => {
  it("lecturas distintas y riesgos sin fortalezas", async () => {
    const a = (await import(`@/v2/__fixtures__/${t}.json`)).default as unknown as StockAnalysis;
    const story = buildReadings(a);
    const leads = story.map((c) => c.lead);
    expect(new Set(leads).size, `${t}: lecturas repetidas`).toBe(leads.length);
    const strengths = a.display.sections.alerts.groups.filter((g) => g.tone === "pos").flatMap((g) => g.items.map((i) => i.reason));
    for (const f of story.find((c) => c.id === "riesgos")!.figures) expect(strengths, `${t}: fortaleza en riesgos`).not.toContain(f.value);
  });
});

describe("buildReadings(AAPL) con los datos de E2a (display.extended)", () => {
  it("actualidad: próximos resultados en las cifras", async () => {
    const a = structuredClone((await import("@/v2/__fixtures__/AAPL.json")).default) as unknown as StockAnalysis;
    const c = buildReadings(a).find((x) => x.id === "actualidad")!;
    expect(c.figures[0]).toEqual({ label: "Próximos resultados", value: "2 de noviembre de 2026 · anunciada", tone: "neutral" });
  });
});

describe("buildReadings(AAPL): rivales frente a la mediana de sus pares (F10 · N2)", () => {
  it("«la mediana de sus pares», no «agregado»", async () => {
    const a = (await import("@/v2/__fixtures__/AAPL.json")).default as unknown as StockAnalysis;
    const riv = buildReadings(a).find((c) => c.id === "rivales")!;
    expect(riv.lead).toContain("Comparada con la mediana de sus pares del universo");
    expect(riv.lead).not.toContain("agregado");
    expect(riv.figures[0].label).toBe("Mejor que la mediana");
  });
});
