import { API_BASE } from "@/v2/lib/http";
import { describe, expect, it } from "vitest";
import { fireEvent, render } from "@testing-library/react";
import CompanyLogo from "./CompanyLogo";

const plate = (c: HTMLElement) => c.querySelector<HTMLElement>("[data-testid=company-logo]")!;

describe("CompanyLogo", () => {
  it("mientras carga, la placa vacía del mismo tamaño; al llegar, la imagen", () => {
    const { container } = render(<CompanyLogo symbol="NFLX" name="Netflix" size="lg" />);
    const p = plate(container);
    expect(p.className).toContain("co-logo-lg");
    expect(p.getAttribute("aria-hidden")).toBe("true");
    const img = p.querySelector("img")!;
    expect(img.getAttribute("src")).toBe(`${API_BASE}/api/v2/logo/NFLX`);
    expect(img.getAttribute("alt")).toBe("");
    fireEvent.load(img);
    expect(p.dataset.state).toBe("ok");
    expect(p.textContent).toBe("");
  });

  it("si la imagen falla, las iniciales y ninguna imagen rota", () => {
    const { container } = render(<CompanyLogo symbol="JPM" name="JPMorgan Chase & Co." />);
    fireEvent.error(plate(container).querySelector("img")!);
    expect(plate(container).dataset.state).toBe("fail");
    expect(plate(container).querySelector("img")).toBeNull();
    expect(plate(container).textContent).toBe("JC");
  });

  it("sin logotipo según el análisis, la placa sin pedir nada", () => {
    const { container } = render(<CompanyLogo symbol="MC.PA" logo={null} size="sm" />);
    expect(plate(container).querySelector("img")).toBeNull();
    expect(plate(container).textContent).toBe("MC");
  });

  it("al cambiar de empresa vuelve a cargar", () => {
    const { container, rerender } = render(<CompanyLogo symbol="AAA" name="Aaa" />);
    fireEvent.error(plate(container).querySelector("img")!);
    rerender(<CompanyLogo symbol="BBB" name="Bbb" />);
    expect(plate(container).dataset.state).toBe("loading");
    expect(plate(container).querySelector("img")!.getAttribute("src")).toBe(`${API_BASE}/api/v2/logo/BBB`);
  });
});
