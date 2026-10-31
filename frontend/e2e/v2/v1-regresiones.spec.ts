import { test, expect } from "@playwright/test";
import { symmetryProblems } from "./checks";

// Verificación V1 de la v4: los casos del panel que fallaron la simetría a 1440 px, cada uno con su arreglo en origen.
//  - Historia: la nota de la puntuación de calidad alargaba la lectura frente a un visual fijo (ASML, NVDA, TSM, MU,
//    NFLX) → va con las barras; qué es la referencia de rivales, igual (SNOW) → bajo la tabla; las cifras clave no
//    cabían en ningún lado con una tabla corta (MU, «Cuánto vale») → al visual, que se recorta (fit.figuresPlace).
//  - Calidad: «Lo que puntúa en Crecimiento» con una sola entrada junto a 3 filas de crecimiento (AMZN, BRK-B, TM)
//    → una debajo de otra.
//  - Empresa: una etiqueta de cifra clave en dos líneas dejaba 25 px en las fichas vecinas (UL) → ficha ancha.
const CASES: Array<[string, string]> = [
  ["ASML", ""], ["NVDA", ""], ["TSM", ""], ["MU", ""], ["NFLX", ""], ["SNOW", ""],
  ["AMZN", "calidad"], ["BRK-B", "calidad"], ["TM", "calidad"], ["UL", "empresa"],
];

for (const [t, pg] of CASES) {
  test(`V1 · simetría a 1440 · ${t} · ${pg || "empresa"}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop", "los fallos eran del escritorio (a dos columnas)");
    await page.goto(`/v2/${t}${pg ? `/${pg}` : ""}`);
    await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
    await page.waitForTimeout(500);
    expect(await symmetryProblems(page)).toEqual([]);
    if (pg === "empresa") {
      // Ninguna etiqueta de cifra clave partida en dos líneas
      const lines = await page.locator(".tiles.flow .tile-label").evaluateAll((els) =>
        els.map((e) => Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight))));
      expect(lines.every((n) => n === 1)).toBe(true);
    }
  });
}

// Pre-pasada final de la v4 (V4_PREPASADA.md), a 375 px: el anexo de HSBC desbordaba con una etiqueta XBRL sin cortes
// (Chromium y WebKit) y la cabecera de MC.PA, con el precio y la variación en euros en una pieza sin partir (WebKit).
const MOVIL: Array<[string, string]> = [["HSBC", "conclusion"], ["MC.PA", "empresa"], ["MC.PA", "conclusion"]];
for (const [t, pg] of MOVIL) {
  test(`Pre-pasada · sin desbordamiento en móvil · ${t} · ${pg}`, async ({ page }, info) => {
    test.skip(!info.project.name.startsWith("mobile"), "los fallos eran del móvil (375 px)");
    await page.setViewportSize({ width: 375, height: 812 });   // el iPhone 15 mide 393: a 375, como V1
    await page.goto(`/v2/${t}/${pg}`);
    await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
    await page.waitForTimeout(500);
    expect((await symmetryProblems(page)).filter((p) => p.startsWith("desbordamiento"))).toEqual([]);
  });
}

// Y a dos columnas (tableta y escritorio): el precio y su variación en una línea, sin meterse bajo la conclusión. Con
// la cotización en euros, MC.PA medía 361 px en una columna de 268 en el iPad y pisaba la conclusión.
for (const t of ["MC.PA", "AAPL"]) {
  test(`Pre-pasada · precio y variación en una línea, sin pisar la conclusión · ${t}`, async ({ page }, info) => {
    test.skip(info.project.name.startsWith("mobile"), "en el móvil, la conclusión va debajo");
    await page.goto(`/v2/${t}`);
    const head = page.locator(".company-header:not(.compact)");
    await expect(head.getByTestId("day-change")).toBeVisible({ timeout: 30_000 });
    const [p, d, v] = await Promise.all([head.getByTestId("price").boundingBox(), head.getByTestId("day-change").boundingBox(),
      head.getByTestId("verdict").boundingBox()]);
    expect(Math.abs((p!.y + p!.height) - (d!.y + d!.height))).toBeLessThan(12);
    expect(d!.x + d!.width).toBeLessThanOrEqual(v!.x);
  });
}

// Cierre de la v4 (V1 a 1024 px): la tabla de rivales (11 columnas) no cabía por unos px en el escritorio estrecho
// (AAPL: 981 en 974). A 1024, sin desbordamiento en «Rivales».
for (const t of ["AAPL", "NVDA", "BRK-B"]) {
  test(`Cierre · rivales a 1024 sin desbordamiento · ${t}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop", "el escritorio estrecho");
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto(`/v2/${t}/rivales`);
    await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
    await expect(page.locator(".peerstable tbody tr").first()).toBeVisible({ timeout: 60_000 });
    // la tabla completa: sin esqueletos (filas en cola) y con las cifras que llegan después (capitalizaciones)
    await expect(page.locator(".peerstable .skel")).toHaveCount(0, { timeout: 60_000 });
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
    expect((await symmetryProblems(page)).filter((p) => p.startsWith("desbordamiento"))).toEqual([]);
  });
}
