import { describe, it, expect } from "vitest";
import { newsCard, safeNewsUrl } from "./news";

describe("tarjeta de noticia", () => {
  it("fecha dd/mm/aaaa, medio, imagen con el titular como texto alternativo e idioma", () => {
    const c = newsCard({ date: "2026-10-14", source: "Reuters", headline: "Titular", url: "https://x", summary: "Resumen…",
      image: "https://img/1.jpg", lang: "en" });
    expect(c.meta).toBe("14/10/2026 · Reuters");
    expect(c.image).toEqual({ src: "https://img/1.jpg", alt: "" });   // decorativa: el titular ya es el texto (V6, F24)
    expect(c.lang).toBe("En inglés");
    expect(c.summary).toBe("Resumen…");
  });
  it("sin imagen https ni idioma conocido", () => {
    const c = newsCard({ date: null, source: "X", headline: "T", url: null, image: "http://img/1.jpg", lang: "fr" });
    expect(c.image).toBeNull();
    expect(c.lang).toBeNull();
    expect(c.meta).toBe("X");
  });
  it("revisión V6 (F3): solo enlaces http(s); cualquier otro esquema es una tarjeta sin enlace", () => {
    const base = { date: null, source: "X", headline: "T", image: null, lang: null };
    expect(newsCard({ ...base, url: "https://www.reuters.com/a?b=1" }).url).toBe("https://www.reuters.com/a?b=1");
    expect(newsCard({ ...base, url: "HTTP://x.com/a" }).url).toBe("http://x.com/a");
    for (const bad of ["javascript:alert(1)", " javascript:alert(1)", "data:text/html,<b>", "//evil.com", "/relativa", "https://", "ftp://x"]) {
      expect(safeNewsUrl(bad)).toBeNull();
    }
  });
});
