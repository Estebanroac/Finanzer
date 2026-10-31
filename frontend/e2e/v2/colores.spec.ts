import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { openSection, SECTIONS } from "./checks";

// V4b · 4 (literal del usuario: «Muchos cuadros sin colores o bien indicados»): en las nueve secciones de AAPL, JPM,
// PLTR, O y BCS, todo valor con lectura lleva su tono (verde, ámbar, teja o gris neutro explícito) y una pastilla o un
// texto que lo diga. Lo que se busca en el DOM:
//  - pastillas sin tono;
//  - en una fila con lectura (pastilla), la cifra sin tono;
//  - filas de tabla técnica con cifra y la lectura vacía (sin pastilla ni texto que diga por qué);
//  - tarjetas con cifra y pastilla de lectura y la cifra sin tono.
// El informe (con cada caso y su sección) queda en test-results/colores-<ticker>.json.
const TICKERS = ["AAPL", "JPM", "PLTR", "O", "BCS"];
const TONES = ["good", "warn", "bad", "neutral"];

for (const t of TICKERS) {
  test(`colores: ningún valor con lectura sin tono · ${t}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop", "los tonos no dependen del tamaño");
    test.setTimeout(240_000);
    const problems: string[] = [];
    for (const s of SECTIONS) {
      await openSection(page, t, s);
      problems.push(...(await page.evaluate((tones) => {
        const out: string[] = [];
        const toned = (el: Element | null) => !!el && [...el.classList].some((c) => tones.includes(c.replace(/^tone-/, "")) && (c.startsWith("tone-") || el.classList.contains("pill")));
        const name = (el: Element) => (el.closest("tr")?.querySelector("th, .metric-name")?.textContent ?? el.closest(".card, .tile, .figure, .score")?.querySelector("h4, .eyebrow, .muted, .tile-label")?.textContent ?? "").trim().slice(0, 40);
        const scope = document.querySelector("main")!;
        // 1) toda pastilla, con tono
        scope.querySelectorAll(".pill").forEach((p) => { if (!toned(p)) out.push(`pastilla sin tono: «${p.textContent?.trim()}» (${name(p)})`); });
        // 2) fila de tabla con lectura: su primera cifra, con tono
        scope.querySelectorAll("tr").forEach((tr) => {
          if (!tr.querySelector(".pill")) return;
          const v = tr.querySelector("td.num");
          if (v && v.textContent?.trim() && !toned(v)) out.push(`cifra sin tono junto a su lectura: ${name(tr)} = ${v.textContent?.trim()}`);
        });
        // 3) tabla técnica: con cifra, la lectura no queda vacía
        scope.querySelectorAll("table.techtable.metrics tr").forEach((tr) => {
          const v = tr.querySelector("td.num"), r = tr.querySelector("td.reading");
          if (v && r && v.textContent?.trim() && !r.textContent?.trim()) out.push(`cifra sin lectura: ${name(tr)} = ${v.textContent?.trim()}`);
        });
        // 4) tarjetas y fichas con cifra y pastilla de lectura: la cifra, con tono
        scope.querySelectorAll(".tile, .card").forEach((c) => {
          const pill = c.querySelector(":scope > .pill, .tile-foot .pill");
          const v = c.querySelector(".tile-value, .big, .gauge-value");
          if (pill && v && v.textContent?.trim() && !toned(v)) out.push(`cifra de tarjeta sin tono: ${name(c)} = ${v.textContent?.trim()}`);
        });
        return out;
      }, TONES)).map((p) => `${s}: ${p}`));
    }
    const uniq = [...new Set(problems)];
    fs.mkdirSync(info.outputDir, { recursive: true });
    fs.writeFileSync(path.join(info.outputDir, `colores-${t}.json`), JSON.stringify(uniq, null, 1));
    expect(uniq).toEqual([]);
  });
}

// V4b · 4 (regla 6 del PM): en la sensibilidad del escenario, una celda sin valor dice por qué («≤ 0» o «fuera», del
// motor) y la nota lo explica; nunca un «—». DOW tiene celdas con el valor por acción ≤ 0; en AAPL se fuerza una «fuera».
test("sensibilidad del escenario: cada celda vacía dice por qué", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "el contenido no depende del tamaño");
  const cells = async () => page.getByTestId("scenario-sensitivity").locator("tbody td").allInnerTexts();
  await page.goto("/v2/DOW/valor");
  await expect(page.getByTestId("scenario-sensitivity")).toBeVisible({ timeout: 30_000 });
  let texts = await cells();
  expect(texts.filter((t) => !t.trim() || t.trim() === "—")).toEqual([]);
  expect(texts).toContain("≤ 0");
  await expect(page.getByTestId("scenario")).toContainText("«≤ 0»: con esos supuestos el valor por acción sale cero o negativo");

  await page.route("**/api/v2/scenario", async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    body.sensitivity.values[0][0] = null;
    body.sensitivity.why[0][0] = "fuera";
    return route.fulfill({ response: res, json: body });
  });
  await page.goto("/v2/AAPL/valor");
  await expect(page.getByTestId("scenario-sensitivity")).toBeVisible({ timeout: 30_000 });
  texts = await cells();
  expect(texts[0].trim()).toBe("fuera");
  await expect(page.getByTestId("scenario")).toContainText("«fuera»: crecimiento o coste del capital fuera de los límites del análisis");
});
