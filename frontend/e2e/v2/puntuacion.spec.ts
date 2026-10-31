import { test, expect, type Page } from "@playwright/test";

/** V7 (puntuación del motor): al unir frases no aparecen «.;», «;.» ni «..» en ninguna página, ni en la web actual
 *  ni en /v2 (mismo patrón que la regla `puntuacion_doble` del guardián, backend/lib/prose.py). KO es el caso que lo
 *  destapó («…en 3 de 5 ejercicios.; en la frontera con «sólida»…»). */
const TICKERS = ["KO", "PGR", "AAPL", "JPM", "O", "TM", "RIVN"];
const CHAPTERS = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];
const OLD_TABS = ["Valoración", "Rentabilidad", "Solidez", "Crecimiento", "Comparativa", "Histórico",
  "Evaluación institucional", "Alertas", "Contexto de mercado"];
const DOUBLE = /\.;|;\.|(?<![.…])\.\.(?!\.)/g;

async function doubles(page: Page, where: string): Promise<string[]> {
  const text = await page.locator("body").innerText();
  expect(text.length, `${where}: página sin contenido`).toBeGreaterThan(500);
  return [...text.matchAll(DOUBLE)].map((m) => `${where}: «…${text.slice(Math.max(0, m.index! - 60), m.index! + 20)}…»`);
}

for (const t of TICKERS) {
  test(`puntuación · ${t}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop", "el texto es el mismo en móvil");
    test.setTimeout(240_000);
    const found: string[] = [];
    await page.goto(`/stock/${t}`);
    await page.getByRole("button", { name: OLD_TABS[0], exact: true }).waitFor({ timeout: 60_000 });
    for (const tab of OLD_TABS) {
      await page.getByRole("button", { name: tab, exact: true }).click();
      await page.waitForTimeout(300);
      found.push(...await doubles(page, `web actual · ${tab}`));
    }
    await page.goto(`/v2/${t}`);
    await page.waitForSelector(".depth-body .dsec", { timeout: 60_000 });
    found.push(...await doubles(page, "/v2"));
    for (const ch of CHAPTERS) {
      await page.goto(`/v2/${t}/${ch}`);
      await page.waitForSelector(".depth-body .dsec", { timeout: 60_000 });
      found.push(...await doubles(page, `/v2/${ch}`));
    }
    // Una nota une el ajuste por confianza y la frontera con «; » y acaba en punto. F9 · R3: con el P/B del balance del
    // corte, PGR (78) ya no está en la frontera de «excelente»; el caso es la nota del precio de JPM (46, a 2 puntos de
    // «exigente»). F9 (fusión con f9-motor): con la prima de riesgo país y el forward creíble, JPM queda en 42
    // «exigente», fuera de la frontera; el caso es TM (31, a 2 puntos de «muy exigente»). F10 · N2: sin sus cifras a
    // la fecha del conjunto (20-F), su referencia es la mediana de sus pares: TM queda en 46, a 2 puntos de «exigente».
    // F10 · B1: su P/FCF con FCF negativo es «n. s.» y la cobertura sube a alta, pero la convergencia media la deja en media.
    if (t === "TM") {
      await page.goto(`/v2/${t}`);
      await expect(page.locator("body")).toContainText("confianza media; en la frontera con «exigente»");
    }
    expect(found).toEqual([]);
  });
}
