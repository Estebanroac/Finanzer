import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CompanyHeader, { PRICE_NOTE, QUALITY_NOTE, ScoreBreakdowns } from "./CompanyHeader";
import AAPL from "@/v2/__fixtures__/AAPL.json";
import DOW from "@/v2/__fixtures__/DOW.json";
import PLTR from "@/v2/__fixtures__/PLTR.json";
import type { StockAnalysis } from "@/lib/api";

describe("CompanyHeader (AAPL)", () => {
  it("muestra precio, las dos puntuaciones con su escala y la confianza", () => {
    render(<CompanyHeader analysis={AAPL as unknown as StockAnalysis} />);
    expect(screen.getByTestId("price").textContent).toMatch(/^\$\d/);
    const q = screen.getByTestId("score-quality");
    expect(q.textContent).toContain("/ 100");
    expect(q.querySelectorAll("[data-segment]").length).toBe(4);
    expect(screen.getByTestId("score-price").querySelectorAll("[data-segment]").length).toBe(4);
    expect(screen.getByTestId("confidence").textContent?.length).toBeGreaterThan(0);
  });
  it("el desglose de calidad lista sus categorías con puntos sobre 20", () => {
    render(<ScoreBreakdowns analysis={AAPL as unknown as StockAnalysis} />);
    const rows = screen.getByTestId("breakdown-quality").querySelectorAll("li[data-cat]");
    expect(rows.length).toBe(4);
  });
  it("V7 (PM): los desgloses explican el cálculo en palabras, con las cifras de la config", () => {
    expect(QUALITY_NOTE).toBe("La calidad suma cuatro categorías de 20 puntos y se expresa sobre 100. "
      + "Excelente desde 85, sólida desde 65, media desde 45; débil por debajo.");
    expect(PRICE_NOTE).toBe("El atractivo del precio parte de 10 sobre 20 y suma lo que dicen los múltiplos y el DCF; se "
      + "expresa sobre 100 y, cuanto menor es la confianza, más se acerca a 50. Atractivo desde 65, razonable desde 45, "
      + "exigente desde 30; muy exigente por debajo.");
    render(<ScoreBreakdowns analysis={AAPL as unknown as StockAnalysis} />);
    for (const id of ["breakdown-quality", "breakdown-price"]) {
      const t = screen.getByTestId(id).textContent ?? "";
      expect(t).not.toMatch(/motor|reescal|factor/i);
    }
    expect(screen.getByTestId("breakdown-quality").textContent).toContain(QUALITY_NOTE);
  });
  it("la cifra lleva el tono del motor y la confianza su escala de tres niveles", () => {
    render(<CompanyHeader analysis={AAPL as unknown as StockAnalysis} />);
    expect(screen.getByTestId("score-quality").querySelector(".big")?.className).toContain("tone-good");
    expect(screen.getByTestId("confidence").querySelectorAll("[data-segment]").length).toBe(3);
  });
  it("el precio y la confianza explican su cálculo con datos del motor", () => {
    render(<ScoreBreakdowns analysis={AAPL as unknown as StockAnalysis} />);
    const price = screen.getByTestId("breakdown-price");
    expect(price.textContent).toContain("Bloque de múltiplos");
    expect(price.textContent).toContain("−5");
    expect(screen.getByTestId("breakdown-confidence").querySelectorAll("li[data-cat]").length).toBe(4);
  });
  it("la conclusión del motor está siempre visible en la cabecera", () => {
    render(<CompanyHeader analysis={AAPL as unknown as StockAnalysis} />);
    expect(screen.getByTestId("verdict").textContent).toContain((AAPL as unknown as StockAnalysis).display.cover.verdict.text);
  });
  it("V4b (nada oculto): el desglose completo de las tres, a la vista en «La empresa», sin hoja ni panel", () => {
    render(<ScoreBreakdowns analysis={AAPL as unknown as StockAnalysis} />);
    // sin el «?» de cada etiqueta (V7 · P3), que se prueba aparte
    const mini = (id: string) => Array.from(screen.getByTestId(id).querySelectorAll(".mini li"))
      .map((li) => (li.textContent ?? "").replace("?", ""));
    // F8 · E10: Altman por SIC (3571, Z original), zona segura con su peso de +3: solidez 10 → 16
    expect(mini("desglose-quality")).toEqual(["Solidez financiera16 / 20", "Rentabilidad20 / 20", "Calidad de ganancias20 / 20", "Crecimiento10 / 20"]);
    expect(mini("desglose-price").join(" | ")).toContain("Bloque de múltiplos · 5 múltiplos−5");
    expect(mini("desglose-confidence").length).toBe(4);
    // el total, las notas y el título del cálculo, en la tarjeta; ningún botón «Ver detalle» ni tarjeta que se abra
    expect(screen.getByTestId("desglose-price").textContent).toContain("Valoración");
    expect(screen.getByTestId("desglose-price").textContent).toContain(PRICE_NOTE);
    expect(screen.getByTestId("desglose-quality").textContent).toContain("Cómo sale el");
    expect(screen.queryByRole("button", { name: /Ver detalle/ })).toBeNull();
    for (const id of ["desglose-quality", "desglose-price", "desglose-confidence"]) expect(screen.getByTestId(id).getAttribute("tabindex")).toBeNull();
  });

  it("V4b (PM): la cabecera enseña cifra, banda y base de las tres, sin las filas del desglose, y enlaza a «La empresa»", () => {
    render(<CompanyHeader analysis={AAPL as unknown as StockAnalysis} />);
    expect(document.querySelector(".company-header .bd, .company-header [data-testid^=breakdown-]")).toBeNull();
    expect(screen.getByTestId("score-quality").querySelector(".big")?.textContent).toBe("82");   // F8 · E10 (antes 75)
    const link = screen.getByTestId("bd-link");
    expect(link.textContent).toBe("Ver desglose en La empresa →");
    expect(link.getAttribute("href")).toBe("/v2/AAPL/empresa#desglose");
  });
  it("V7 · P3: cada etiqueta del desglose lleva su «?» con la definición que la explica", () => {
    render(<ScoreBreakdowns analysis={AAPL as unknown as StockAnalysis} />);
    const tips = (id: string) => Array.from(screen.getByTestId(id).querySelectorAll(".bd [data-tip]")).map((b) => b.getAttribute("data-tip"));
    expect(tips("desglose-quality")).toEqual(["cat_solidez", "cat_rentabilidad", "cat_calidad_ganancias", "cat_crecimiento"]);
    // F8 · E8: con la fiabilidad del DCF por sus insumos, en AAPL puntúa el DCF directo; el caso del inverso es DOW
    expect(tips("desglose-price")).not.toContain("reverse_dcf");
    expect(tips("desglose-confidence")).toEqual(["conf_convergence", "conf_coverage", "conf_source", "conf_stability"]);
    expect(screen.getByRole("button", { name: "Qué es Calidad de ganancias" })).toBeTruthy();
  });

  it("V7 · P3 (M5): con el DCF directo descartado puntúa el inverso, con su propia definición (DOW; F8 · E8)", () => {
    render(<ScoreBreakdowns analysis={DOW as unknown as StockAnalysis} />);
    const tips = Array.from(screen.getByTestId("desglose-price").querySelectorAll(".bd [data-tip]")).map((b) => b.getAttribute("data-tip"));
    expect(tips).toContain("reverse_dcf");
  });

  it("V7 · P1: «?» en las tres puntuaciones; la compacta (V4b, la fija al bajar) es solo visual: sin «?» y oculta", () => {
    const { unmount } = render(<CompanyHeader analysis={AAPL as unknown as StockAnalysis} />);
    for (const [id, key] of [["score-quality", "quality"], ["score-price", "price"], ["confidence", "confidence"]])
      expect(screen.getByTestId(id).querySelector(`.eyebrow [data-tip="${key}"]`)).toBeTruthy();
    unmount();
    const { container } = render(<CompanyHeader analysis={AAPL as unknown as StockAnalysis} compact />);
    const head = container.querySelector(".company-header.compact")!;
    expect(head.getAttribute("aria-hidden")).toBe("true");
    expect(head.querySelector(".scores-line")!.textContent).toMatch(/Calidad.*Precio.*Confianza/);
    expect(head.querySelectorAll("button, a[href], [tabindex], [data-testid]")).toHaveLength(0);
  });
  it("V4-F8 (PM): la cabecera resume la nota (forma corta) y «La empresa» la detalla (frase completa)", () => {
    // F8 (fusión): AAPL (82) ya no lleva nota de persistencia; el caso es PLTR (F10: 94 → 90, antes 99 → 95)
    const { unmount } = render(<CompanyHeader analysis={PLTR as unknown as StockAnalysis} />);
    const head = screen.getByTestId("score-quality").textContent ?? "";
    expect(head).toContain("Exige persistencia (94 → 90)");
    expect(head).not.toContain("Rentabilidad: margen operativo");
    unmount();
    render(<ScoreBreakdowns analysis={PLTR as unknown as StockAnalysis} />);
    expect(screen.getByTestId("desglose-quality").textContent).toContain(
      "Por encima de 80 (umbral de persistencia; «excelente» empieza en 85), la calidad exige persistencia: 94 → 90. Rentabilidad: margen operativo");
  });
});
