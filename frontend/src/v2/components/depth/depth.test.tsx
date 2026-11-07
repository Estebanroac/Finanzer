import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import AAPL from "@/v2/__fixtures__/AAPL.json";
import type { StockAnalysis } from "@/lib/api";
import TechTable from "./TechTable";
import MetricTip from "./MetricTip";
import AuditAnnex from "./AuditAnnex";
import Methodology from "./Methodology";
import PillIndex from "./PillIndex";
import { Missing } from "./Section";

const a = AAPL as unknown as StockAnalysis;
const prof = a.display.sections.profitability;

describe("TechTable", () => {
  it("nombre técnico con su significado, cifras del motor y lectura en pastilla con su tono", () => {
    render(<TechTable rows={prof.rows} refLabel="Industria" tooltips={a.display.tooltips} />);
    // La referencia de AAPL es su industria global de Damodaran (F14/F15; antes la mediana de sus pares): el margen neto la tiene
    const nm = document.querySelector<HTMLElement>('tr[data-key="net_margin"]')!;
    const r = prof.rows.find((x) => x.key === "net_margin")!;
    expect(within(nm).getByRole("rowheader").textContent).toContain("Margen neto");
    expect(nm.querySelector(".metric-sub")?.textContent?.length).toBeGreaterThan(0);
    expect(nm.textContent).toContain(r.value);
    expect(nm.querySelector(".pill")?.textContent).toBe(r.reading);
    const [withRef, noRef] = Array.from(document.querySelectorAll("table.techtable"));
    expect(within(withRef as HTMLElement).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Métrica", "Empresa", "Industria", "Brecha", "Lectura"]);
    // V4b · 4 (PM): las filas sin referencia (ROA y ROCE en AAPL), aparte y de tres columnas, nombradas en una nota
    expect(within(noRef as HTMLElement).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Métrica", "Empresa", "Lectura"]);
    expect(screen.getByTestId("no-ref-note").textContent).toBe("Sin referencia de industria publicada para: ROA, ROCE (EBIT / capital empleado).");
    // ninguna celda con «—» ni vacía; la cifra sin lectura lo dice en gris
    for (const td of Array.from(document.querySelectorAll("td"))) expect(td.textContent?.trim(), td.outerHTML.slice(0, 80)).not.toMatch(/^(|—)$/);
    const roa = document.querySelector('tr[data-key="roa"]')!;
    expect(roa.querySelector(".pill.neutral")?.textContent).toBe("Sin referencia");
    expect(roa.querySelector("td.num")?.className).toContain("tone-neutral");
  });
  it("V4b · 4: con las tres columnas del motor (solidez), tres columnas y la referencia que haya, bajo la cifra", () => {
    const solv = a.display.sections.solvency;
    render(<TechTable rows={solv.rows} refLabel="Industria" tooltips={a.display.tooltips} columns={solv.columns} />);
    expect(document.querySelectorAll("table.techtable")).toHaveLength(1);
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Métrica", "Empresa", "Lectura"]);
    expect(document.querySelector('tr[data-key="de"] td.num')?.textContent).toMatch(/Industria 0\.39x · \+106%/)   // industria global de Damodaran;
    expect(document.querySelector('tr[data-key="quick_ratio"] .pill.neutral')?.textContent).toBe("Informativa");
  });
  it("una fila sin dato dice su motivo (nunca una celda vacía)", () => {
    const rows = [{ key: "x", label: "Métrica X", value: "", bench: null, gap: null, reading: "Sin dato", tone: null,
                    state: "sin_dato" as const, text: "el proveedor no la da" }];
    render(<TechTable rows={rows} refLabel="Industria" tooltips={{}} />);
    expect(document.querySelector(".row-missing")?.textContent).toBe("Sin dato · el proveedor no la da");
  });
});

describe("MetricTip", () => {
  it("abre con definición, fórmula y la banda del motor marcada como «Tu valor»; Esc cierra", () => {
    const r = prof.rows.find((x) => x.key === "net_margin")!;   // F10 · N2: el ROIC de AAPL no tiene referencia
    render(<MetricTip metricKey="net_margin" label="Margen neto" value={r.value} reading={r.reading} bands={a.display.tooltips.net_margin} />);
    const btn = screen.getByRole("button", { name: "Qué es Margen neto" });
    fireEvent.click(btn);
    const dlg = screen.getByRole("dialog");
    expect(dlg.querySelector(".formula")?.textContent?.length).toBeGreaterThan(0);
    const mine = dlg.querySelector("li.mine")!;
    expect(mine.textContent).toContain(r.reading);
    expect(mine.textContent).toContain(`Tu valor ${r.value}`);
    expect(dlg.querySelectorAll("li.mine").length).toBe(1);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("AuditAnnex, Methodology, PillIndex y Missing", () => {
  it("el anexo enseña los códigos del motor a la vista, sin desplegable (V4b)", () => {
    render(<AuditAnnex annex={a.display.annex} />);
    expect(document.querySelectorAll("details").length).toBe(0);
    expect(screen.getByText("Detalle técnico para auditoría")).toBeTruthy();
    expect(document.querySelectorAll(".annex dt").length).toBe(a.display.annex.items.length);
  });
  it("la metodología omite lo vacío y no pinta nada si no hay texto", () => {
    const { container } = render(<Methodology items={[{ label: "A", text: "uno" }, { label: "B", text: null }]} />);
    expect(container.querySelectorAll("dt").length).toBe(1);
    const empty = render(<Methodology items={[{ label: "B", text: " " }]} />);
    expect(empty.container.innerHTML).toBe("");
  });
  it("las píldoras son anclas a sus secciones", () => {
    render(<PillIndex items={[{ id: "a", label: "Uno" }, { id: "b", label: "Dos" }]} />);
    expect(screen.getAllByRole("link").map((l) => l.getAttribute("href"))).toEqual(["#a", "#b"]);
  });
  it("un dato ausente es una línea con título y motivo", () => {
    render(<Missing title="Ficha" reason="el emisor no presenta en la SEC" />);
    expect(document.querySelector("[data-missing]")?.textContent).toBe("Ficha: el emisor no presenta en la SEC");
  });
});
