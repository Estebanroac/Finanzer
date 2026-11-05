import { API_BASE } from "@/v2/lib/http";
import { describe, expect, it } from "vitest";
import { fireEvent, render } from "@testing-library/react";
import AnalyzeLoading from "./AnalyzeLoading";

const show = () => render(<AnalyzeLoading symbol="NFLX" name="Netflix" startedAt={performance.now()} arrivedAt={null}
  onFinished={() => {}} />);
const mark = (c: HTMLElement) => c.querySelector<HTMLElement>("[data-testid=al-mark]")!;
const loaded = (img: HTMLImageElement, w: number) => {
  Object.defineProperty(img, "naturalWidth", { value: w, configurable: true });
  fireEvent.load(img);
};

describe("pantalla de carga: el logotipo del anillo", () => {
  it("el de Finanzer mientras el de la empresa no carga; la URL sale del símbolo, sin esperar al análisis", () => {
    const { container } = show();
    expect(mark(container).dataset.mark).toBe("finanzer");
    expect(mark(container).querySelector(".al-brand")!.getAttribute("src")).toBe("/brand/finanzer-logo.svg");
    expect(mark(container).querySelector(".al-co")!.getAttribute("src")).toBe(`${API_BASE}/api/v2/logo/NFLX`);
    expect(container.querySelector(".co-logo-ph")).toBeNull();          // nunca la placa de iniciales
  });

  it("cuando el de la empresa carga de verdad, lo sustituye", () => {
    const { container } = show();
    loaded(mark(container).querySelector<HTMLImageElement>(".al-co")!, 200);
    expect(mark(container).dataset.mark).toBe("empresa");
  });

  it("sin logotipo (204: la imagen falla) o una imagen vacía, se queda el de Finanzer y no queda imagen rota", () => {
    const a = show();
    fireEvent.error(mark(a.container).querySelector(".al-co")!);
    expect(mark(a.container).dataset.mark).toBe("sin-logo");
    expect(mark(a.container).querySelector(".al-co")).toBeNull();
    expect(mark(a.container).querySelector(".al-brand")).not.toBeNull();
    a.unmount();
    const b = show();
    loaded(mark(b.container).querySelector<HTMLImageElement>(".al-co")!, 0);
    expect(mark(b.container).dataset.mark).toBe("sin-logo");
  });
});
