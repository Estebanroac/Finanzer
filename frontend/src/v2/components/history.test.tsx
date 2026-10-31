import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import AAPL from "@/v2/__fixtures__/AAPL.json";
import type { StockAnalysis } from "@/lib/api";
import HistoryChart from "./HistoryChart";
import SegmentsChart from "./SegmentsChart";

const a = AAPL as unknown as StockAnalysis;

describe("HistoryChart", () => {
  it("diez ejercicios; el último elegido; clic y flechas cambian el año con los textos del motor", () => {
    const h = a.history_10y!;
    const txt = a.display.extended!.history_10y.rows;
    const rows = h.rows.map((r) => ({ ...r, txt: txt.find((t) => t.year === r.year) }));
    render(<HistoryChart rows={rows} currency={h.currency} />);
    const years = screen.getByRole("group", { name: "Elegir ejercicio" }).querySelectorAll("button");
    expect(years.length).toBe(10);
    const card = screen.getByTestId("history-year");
    expect(card.textContent).toContain(`Ejercicio ${h.rows[9].year}`);
    fireEvent.click(years[0]);
    expect(card.textContent).toContain(`Ejercicio ${h.rows[0].year}`);
    expect(card.textContent).toContain(txt[0].revenue_txt);
    fireEvent.keyDown(years[0], { key: "ArrowRight" });
    expect(card.textContent).toContain(`Ejercicio ${h.rows[1].year}`);
  });
});

describe("SegmentsChart", () => {
  it("barras con el peso del motor, tabla por ejercicio y la diferencia si no concilia", () => {
    const axis = { axis_label: "segmentos de negocio", reconciles: false, gap_pct: -0.0213, notes: ["nota del motor"],
      segments: [{ member: "a", label: "Banca", values: { "2024": 7e10, "2025": 8e10 }, share_last: 0.6 },
                 { member: "b", label: "Gestión", values: { "2024": 5e10, "2025": 5.3e10 }, share_last: 0.4 }] };
    render(<SegmentsChart axis={axis} years={["2024", "2025"]} currency="GBP" />);
    const card = screen.getByTestId("segments-axis");
    expect(card.textContent).toContain("60.0%");
    expect(card.textContent).toContain("GBP 80.00B");
    expect(card.textContent).toContain("un 2.1% menos que");
    expect(card.textContent).toContain("nota del motor");
  });
});
