import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// E3 · Task 13: las pruebas de diseño de E1 aplicadas a las páginas de profundidad. Accesibilidad (axe, sin
// infracciones graves) en claro y oscuro, y zoom de 200 % / texto grande sin desbordamiento horizontal.
const CHAPTERS = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];

for (const theme of ["light", "dark"] as const) {
  for (const t of ["AAPL", "JPM"]) {
    test(`accesibilidad de la profundidad · ${t} · ${theme}`, async ({ page }, info) => {
      test.skip(info.project.name !== "desktop", "axe en escritorio");
      test.setTimeout(180_000);
      await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
      const bad: string[] = [];
      for (const ch of CHAPTERS) {
        await page.goto(`/v2/${t}/${ch}`);
        await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
        await page.waitForTimeout(400);
        const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).exclude("nextjs-portal").analyze();
        res.violations.filter((v) => v.impact === "serious" || v.impact === "critical")
          .forEach((v) => bad.push(`${ch}: ${v.id} (${v.nodes.length}) ${v.nodes[0]?.target.join(" ")}`));
      }
      expect(bad).toEqual([]);
    });
  }
}

test("200 % de zoom y texto grande en la profundidad: sin desbordamiento horizontal", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "se simula desde el escritorio");
  test.setTimeout(300_000);
  const problems: string[] = [];
  for (const [width, rootPx] of [[720, 16], [720, 20]] as const) {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript((px) => { document.documentElement.style.fontSize = `${px}px`; }, rootPx);
    for (const t of ["AAPL", "JPM", "BCS"]) {
      for (const ch of CHAPTERS) {
        await page.goto(`/v2/${t}/${ch}`);
        await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
        await page.waitForTimeout(300);
        if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) problems.push(`${t}/${ch} a ${width}px y ${rootPx}px`);
      }
    }
  }
  expect(problems).toEqual([]);
});
