import { API_BASE } from "@/v2/lib/http";
import { describe, expect, it } from "vitest";
import { fireEvent, render } from "@testing-library/react";
import NewsCard from "./NewsCard";

const base = { date: "2026-11-03", source: "Yahoo", headline: "Titular", url: "https://x.com/a", summary: "Resumen", lang: "en" };

describe("portada de la noticia sin foto", () => {
  it("el logotipo de la empresa (el del análisis) y el medio debajo, sin el ticker en texto", () => {
    const { container } = render(<NewsCard n={{ ...base, image: null }} symbol="TM" name="Toyota Motor Corporation"
      logo={{ url: "/api/v2/logo/TM?v=abc", source: "Parqet" }} />);
    const cover = container.querySelector(".news-img-empty")!;
    const logo = cover.querySelector<HTMLElement>("[data-testid=news-logo]")!;
    expect(logo.className).toContain("co-logo-lg");
    expect(logo.querySelector("img")!.getAttribute("src")).toBe(`${API_BASE}/api/v2/logo/TM?v=abc`);
    expect(cover.querySelector(".news-ph-src")!.textContent).toBe("Yahoo Finance");
    expect(cover.textContent).not.toContain("TM");
  });

  it("sin logotipo, la placa con las iniciales de la empresa", () => {
    const { container } = render(<NewsCard n={{ ...base, image: null }} symbol="UL" name="Unilever PLC" logo={null} />);
    const logo = container.querySelector<HTMLElement>(".news-img-empty [data-testid=news-logo]")!;
    expect(logo.dataset.state).toBe("fail");
    expect(logo.textContent).toBe("U");
  });

  it("si la foto de la noticia falla al cargar, la misma portada con el logotipo", () => {
    const { container } = render(<NewsCard n={{ ...base, image: "https://img/1.jpg" }} symbol="NVO" name="Novo Nordisk" />);
    fireEvent.error(container.querySelector("img.news-img")!);
    expect(container.querySelector(".news-img-empty [data-testid=news-logo]")).not.toBeNull();
    expect(container.querySelector("img.news-img")).toBeNull();
  });
});
