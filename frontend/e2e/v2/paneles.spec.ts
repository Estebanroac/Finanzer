import { test, expect, type Page } from "@playwright/test";

// V7 (PM): el panel de un «?», el desglose de una puntuación y su «Qué es cada fila» nunca ocupan la zona de la barra
// fija de capítulos, ni por delante ni por detrás: entero dentro del viewport y sin cruzarse con la barra (también
// tras desplazar la página). En móvil, hoja inferior bajo la barra, que sigue visible.
const TICKERS = ["AAPL", "JPM", "PLTR"];
const PANEL = ".tip-box:not([hidden])";

/** Problemas del panel abierto ahora mismo (o null si no hay ninguno a la vista). Un panel sin sitio útil (el «?» pegado
 *  arriba con la barra justo debajo) queda oculto (visibility: hidden) hasta que vuelve a haber sitio: no cuenta. */
async function panelProblems(page: Page, label: string): Promise<string[] | null> {
  return page.evaluate(([sel, label]) => {
    const p = [...document.querySelectorAll<HTMLElement>(sel)].find((e) => getComputedStyle(e).visibility !== "hidden");
    if (!p) return null;
    const out: string[] = [];
    const r = p.getBoundingClientRect();
    const vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
    if (r.top < -0.5 || r.left < -0.5 || r.bottom > vh + 0.5 || r.right > vw + 0.5)
      out.push(`${label}: fuera del viewport (${Math.round(r.left)},${Math.round(r.top)} → ${Math.round(r.right)},${Math.round(r.bottom)})`);
    const bar = document.querySelector("nav.chapterbar")?.getBoundingClientRect();
    if (bar && bar.height > 0 && bar.bottom > 0 && bar.top < vh && r.bottom > bar.top + 0.5 && r.top < bar.bottom - 0.5)
      out.push(`${label}: se cruza con la barra (${Math.round(r.top)}–${Math.round(r.bottom)} frente a ${Math.round(bar.top)}–${Math.round(bar.bottom)})`);
    return out;
  }, [PANEL, label] as const);
}

async function closeAll(page: Page) {
  await page.keyboard.press("Escape");
  // el foco vuelve al «?», y una tarjeta enfocada enseña su desglose (como siempre): se quita el foco y el ratón
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  if (page.viewportSize()!.width >= 768) await page.mouse.move(1, 1);
}

for (const t of TICKERS) {
  test(`paneles fuera de la barra de capítulos · ${t}`, async ({ page }, info) => {
    test.setTimeout(240_000);
    const mobile = (page.viewportSize()?.width ?? 1440) < 768;
    const problems: string[] = [];
    for (const path of [`/v2/${t}`, `/v2/${t}/calidad`]) {
      await page.goto(path);
      await page.waitForSelector(".depth-body .dsec", { timeout: 60_000 });
      const n = await page.locator("button.tip-btn:visible").count();
      expect(n, `${path}: «?» visibles`).toBeGreaterThan(0);
      for (let i = 0; i < n; i++) {
        const btn = page.locator("button.tip-btn:visible").nth(i);
        await btn.evaluate((b) => b.scrollIntoView({ block: "center" }));
        await btn.click();
        await expect(page.locator(PANEL).first()).toBeVisible();
        const label = `${path} «?» ${await btn.getAttribute("data-tip")}`;
        problems.push(...((await panelProblems(page, label)) ?? []));
        // V7 (PM): el texto de los «?» no habla del «motor»
        const said = (await page.locator(PANEL).first().innerText()).match(/[^.\n]{0,40}\bmotor\b[^.\n]{0,30}/);
        if (said) problems.push(`${label}: «${said[0]}»`);
        if (mobile) {
          await expect(page.locator(PANEL).first()).toHaveClass(/\bsheet\b/);
        } else {
          // con scroll: o se cierra (el «?» entra bajo la barra o sale) o sigue sin cruzarse con la barra
          for (const dy of [120, 240]) {
            await page.evaluate((y) => window.scrollBy(0, y), dy);
            await page.waitForTimeout(150);
            problems.push(...((await panelProblems(page, `${label} tras ${dy}px`)) ?? []));
          }
        }
        await closeAll(page);
        await expect.poll(() => page.evaluate((sel) => [...document.querySelectorAll(sel)].map((e) => `${e.className}#${e.id}`), PANEL),
          { message: `${label}: sigue abierto` }).toEqual([]);
      }
    }
    expect(problems).toEqual([]);
  });
}
