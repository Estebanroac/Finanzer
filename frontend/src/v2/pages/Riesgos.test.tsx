import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import NEE from "@/v2/__fixtures__/NEE.json";
import type { StockAnalysis } from "@/lib/api";
import Riesgos from "./Riesgos";

// La concentración de los ingresos se pide aparte (/api/v2/segments): aquí no hace falta
vi.mock("@/v2/components/Concentration", () => ({ default: () => null }));

describe("Riesgos · riesgos del sector (F13 · paso 10)", () => {
  it("los enseña aparte, con su nivel y la etiqueta de los de la industria", () => {
    const a = structuredClone(NEE) as unknown as StockAnalysis;
    a.display.sections.sector_risks = {
      items: [{ level: "industria", key: "huracanes", title: "Huracanes", label: "riesgo de la industria, no verificado en esta empresa",
                text: "Las utilities de la costa del golfo reparan su red tras cada huracán." }],
      note: "Aparte y sin puntuar: ni la calidad ni el precio los cuentan.", not_measured: "concentración en un inquilino o en un producto",
    };
    render(<Riesgos analysis={a} symbol="NEE" />);
    expect(screen.getByText("Riesgos del sector (no puntúan)")).toBeTruthy();
    expect(screen.getByText("De la industria")).toBeTruthy();
    expect(screen.getByText("riesgo de la industria, no verificado en esta empresa")).toBeTruthy();
    expect(screen.getByText(/No medido: concentración/)).toBeTruthy();
  });

  it("sin riesgos lo dice, sin un hueco", () => {
    const a = structuredClone(NEE) as unknown as StockAnalysis;
    a.display.sections.sector_risks = { items: [], note: null, not_measured: null };
    render(<Riesgos analysis={a} symbol="NEE" />);
    expect(screen.getByText(/ningún dato dispara un riesgo de la empresa/)).toBeTruthy();
  });
});
