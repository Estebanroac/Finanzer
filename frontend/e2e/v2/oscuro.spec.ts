import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// E4 Task 4: modo oscuro completo. Sin parpadeo (el primer fotograma ya sale en su tema, guardado o del sistema),
// y contraste AA en oscuro con axe en todas las páginas, también con el tooltip «?» y la hoja inferior abiertos.
const DARK_PAPER = "rgb(22, 24, 27)", LIGHT_PAPER = "rgb(247, 246, 242)";
const CHAPTERS = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];

/** Fondo de body y de .fz2 en el primer fotograma (antes de que React hidrate y antes de que llegue el análisis). */
async function firstFrame(page: Page, url: string) {
  await page.addInitScript(() => {
    const w = window as unknown as { __first?: unknown };
    requestAnimationFrame(() => {
      const fz = document.querySelector(".fz2");
      w.__first = { body: getComputedStyle(document.body).backgroundColor, fz2: fz ? getComputedStyle(fz).backgroundColor : null };
    });
  });
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => (window as unknown as { __first?: unknown }).__first);
  return page.evaluate(() => (window as unknown as { __first: { body: string; fz2: string | null } }).__first);
}

test("sin parpadeo: el tema guardado (oscuro) desde el primer fotograma", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("finanzer.v2.theme", "dark"));
  const f = await firstFrame(page, "/v2/AAPL/calidad");
  expect(f.body).toBe(DARK_PAPER);
  if (f.fz2) expect(f.fz2).toBe(DARK_PAPER);
});

test("la primera vez sigue al sistema (oscuro) sin parpadeo; lo guardado manda después", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  const f = await firstFrame(page, "/v2/AAPL");
  expect(f.body).toBe(DARK_PAPER);
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  await expect(page.locator(".fz2")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: /modo claro/i }).click();
  await expect(page.locator(".fz2")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  await expect(page.locator(".fz2")).toHaveAttribute("data-theme", "light");
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe(LIGHT_PAPER);
});

async function serious(page: Page) {
  const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).exclude("nextjs-portal").analyze();
  return res.violations.filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${v.id} (${v.nodes.length}) ${v.nodes[0]?.target.join(" ")}`);
}

test("oscuro: AA en las 9 secciones (AAPL, BCS)", async ({ page }, info) => {
  test.setTimeout(240_000);
  test.skip(info.project.name === "mobile", "Chromium ya lo cubre en escritorio; aquí van WebKit y tableta");
  await page.addInitScript(() => localStorage.setItem("finanzer.v2.theme", "dark"));
  const bad: string[] = [];
  for (const t of info.project.name === "desktop" ? ["AAPL", "BCS"] : ["AAPL"]) {
    for (const ch of CHAPTERS) {
      await page.goto(`/v2/${t}/${ch}`);
      await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
      await page.waitForTimeout(400);
      (await serious(page)).forEach((x) => bad.push(`${t}/${ch}: ${x}`));
    }
  }
  expect(bad).toEqual([]);
});

test("oscuro: AA con el tooltip «?», el escenario y la hoja inferior abiertos", async ({ page }, info) => {
  await page.addInitScript(() => localStorage.setItem("finanzer.v2.theme", "dark"));
  await page.goto("/v2/AAPL/valor");
  await page.waitForSelector("[data-testid=scenario-value]", { timeout: 30_000 });
  await page.getByRole("button", { name: "Optimista" }).click();
  await page.waitForTimeout(800);
  const tip = page.locator(".techtable .tip-btn").first();
  await tip.scrollIntoViewIfNeeded();
  await tip.click();
  await expect(page.locator('[role="dialog"]').first()).toBeVisible();
  // v4.1: a mitad de su fundido de entrada el contraste aún no es el final: se mide al terminar
  await expect.poll(() => page.locator('[role="dialog"]').first().evaluate((el) =>
    el.getAnimations({ subtree: true }).filter((a) => a.playState === "running").length)).toBe(0);
  expect(await serious(page)).toEqual([]);
  await page.keyboard.press("Escape");
});
