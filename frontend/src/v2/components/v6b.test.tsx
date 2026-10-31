import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { useRef } from "react";
import Floating from "./Floating";
import MetricTip from "./depth/MetricTip";
import { companyShort } from "@/v2/lib/companyName";

// V6b (revisión de código del delta final): los hallazgos E2, E3, E4, E8 y E9, con su comportamiento en el DOM. Los de
// navegador (E1, E5, E6, E7, E11) van en e2e/v2/v6b.spec.ts.

vi.mock("@/v2/lib/companyData", () => ({
  fetchSegments: vi.fn(async () => ({
    status: "ok", reason: null,
    summary: { top: { label: "iPhone", share_txt: "51%", axis_label: "Producto" }, fy: "2025", prev_fy: null,
      concept_label: "Ingresos", falling: [], coverage_note: null, source: null },
  })),
}));

/** La hoja (`sheet`) depende de la media query del móvil: aquí se fija. */
function setSheetQuery(on: boolean) {
  vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("max-width") ? on : false, media: q,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, onchange: null, dispatchEvent: () => false }));
}
afterEach(() => vi.unstubAllGlobals());

function Sheet({ onClose, sheet }: { onClose: () => void; sheet?: boolean }) {
  const anchor = useRef<HTMLButtonElement>(null);
  return (
    <div className="fz2">
      <button ref={anchor} type="button">ancla</button>
      <Floating anchor={anchor} open onClose={onClose} role="dialog" className="tip-box" sheet={sheet}>
        <p>contenido largo</p>
      </Floating>
    </div>
  );
}
const swipeDown = (el: Element) => {
  fireEvent.touchStart(el, { touches: [{ clientY: 100 }] });
  fireEvent.touchMove(el, { touches: [{ clientY: 260 }] });
  fireEvent.touchEnd(el);
};

describe("V6b · hoja inferior y panel (Floating, MetricTip)", () => {
  it("E2: el gesto hacia abajo cierra la hoja solo si está arriba del todo, no con su contenido desplazado", async () => {
    setSheetQuery(true);
    const onClose = vi.fn();
    render(<Sheet onClose={onClose} sheet />);
    const sheet = await screen.findByRole("dialog");
    const body = sheet.querySelector(".float-body") as HTMLElement;   // v4: lo que se desplaza es el cuerpo
    body.scrollTop = 120;                           // desplazada: arrastrar hacia abajo es volver arriba
    swipeDown(body);
    expect(onClose).not.toHaveBeenCalled();
    body.scrollTop = 0;
    swipeDown(body);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("E4: hoja o panel lo decide quien abre (prop `sheet`), no la media query en cada render", async () => {
    setSheetQuery(false);                          // ancho de escritorio (una tableta girada) con la hoja abierta
    render(<Sheet onClose={() => {}} sheet />);
    expect((await screen.findByRole("dialog")).className).toContain("sheet");
  });

  it("E3: al cerrar la hoja de un «?» con el gesto, el foco vuelve al «?»", async () => {
    setSheetQuery(true);
    render(<div className="fz2"><MetricTip metricKey="roic" label="ROIC" /></div>);
    const q = screen.getByRole("button", { name: "Qué es ROIC" });
    await act(async () => { q.click(); });
    const sheet = await screen.findByRole("dialog");
    expect(sheet.className).toContain("sheet");
    swipeDown(sheet);                              // cada evento, su propio act (como en el navegador)
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(q);
  });
});

describe("V6b · E8 y E9", () => {
  it("E8: sin el ejercicio anterior no se pinta «FY → FY2025»", async () => {
    const { default: Concentration } = await import("./Concentration");
    render(<Concentration symbol="AAPL" />);
    expect(await screen.findByText("Bajan en el último ejercicio")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/FY\s*→/);
  });

  it("E9: un nombre que coincide con una clave del prototipo se queda como está", () => {
    for (const n of ["constructor", "__proto__", "toString", "hasOwnProperty"]) expect(companyShort(n)).toBe(n);
  });
});
