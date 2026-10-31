import { test, expect } from "@playwright/test";
import { CHAPTER_SLUGS } from "../../src/v2/lib/routes";

// V7 (PM): «motor» no aparece en el texto visible de /v2, salvo en la metodología, donde se explica cómo funciona. Mira
// la historia y las páginas de profundidad, con el texto que llega del backend ya pintado. El código lo mira
// `npm run check` (scripts/check-v2-wording.mjs) y el PDF nuevo, backend/tests/test_pdf_v2_contenido.py.
const TICKERS = ["AAPL", "JPM", "PLTR"];
/** «Motor» con otro sentido, que no es el del análisis (una frase de alerta). */
const OTHER_SENSE = /motor de creación de valor/g;

for (const t of TICKERS) {
  test(`sin «motor» en el texto visible · ${t}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop", "el texto no depende del tamaño");
    test.setTimeout(180_000);
    const found: string[] = [];
    for (const slug of [null, ...CHAPTER_SLUGS]) {
      const path = slug ? `/v2/${t}/${slug}` : `/v2/${t}`;
      await page.goto(path);
      await page.waitForSelector(".depth-body", { timeout: 60_000 });
      const text = await page.evaluate(() => {
        const main = document.querySelector("main")!.cloneNode(true) as HTMLElement;
        main.querySelectorAll(".methodology").forEach((m) => m.remove());
        return main.innerText;
      });
      for (const m of text.replace(OTHER_SENSE, "").matchAll(/[^.\n]{0,50}\bmotor\b[^.\n]{0,30}/g)) found.push(`${path}: ${m[0]}`);
    }
    expect(found).toEqual([]);
  });
}

test("sin «motor» en el texto visible · portada", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "el texto no depende del tamaño");
  await page.goto("/v2");
  await page.waitForSelector("[data-testid=ticker-item]", { timeout: 60_000 });
  const text = await page.locator("body").innerText();
  expect([...text.replace(OTHER_SENSE, "").matchAll(/[^.\n]{0,50}\bmotor\b[^.\n]{0,30}/g)].map((m) => m[0])).toEqual([]);
});
