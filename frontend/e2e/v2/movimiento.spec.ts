import { test, expect, type Page } from "@playwright/test";

// v4.1 · movimiento (el usuario: «suave, sutil, sensación de iPhone; que no todo sea de golpe»). El movimiento nunca
// rompe el foco ni los anclajes, conserva dónde se leía cada pestaña y, con «reducir movimiento», no hay desplazamientos
// ni escalas (fundidos breves o nada).
/** Espera a que no quede ninguna animación en curso en `sel` (si una se reinicia, a la nueva). */
const settle = (page: Page, sel: string) => expect.poll(() => page.locator(sel).first().evaluate((el) =>
  el.getAnimations({ subtree: true }).filter((a) => a.playState === "running").length)).toBe(0);
/** Anota cada valor que toma html[data-page-dir] (la marca dura lo que la entrada: se lee al cambiar, no después). */
const watchDir = (page: Page) => page.evaluate(() => {
  const w = window as unknown as { __dirs: string[] };
  w.__dirs = [];
  new MutationObserver(() => { const d = document.documentElement.dataset.pageDir; if (d) w.__dirs.push(d); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ["data-page-dir"] });
});
const dirs = (page: Page) => page.evaluate(() => (window as unknown as { __dirs: string[] }).__dirs);
const chapter = (page: Page, name: string) => page.locator(".chapterbar a", { hasText: name }).first();

test.describe("cambio de pestaña", () => {
  test("la sección entra desde el lado del cambio; el foco va a su título y la marca activa llega a la pestaña", async ({ page }) => {
    await page.goto("/v2/NVDA");
    await page.locator(".chapterbar a").first().waitFor({ timeout: 90_000 });
    await watchDir(page);
    await page.evaluate(() => {
      const w = window as unknown as { __anim: string[] };
      w.__anim = [];
      document.addEventListener("animationstart", (e) => w.__anim.push(e.animationName));
    });
    await chapter(page, "Calidad").click();
    await expect.poll(() => dirs(page)).toEqual(["fwd"]);
    await expect.poll(() => page.evaluate(() => (window as unknown as { __anim: string[] }).__anim)).toContain("fz2-page-in");
    await expect(page.locator(".chapterbar a[aria-current=page]")).toHaveText("Calidad");
    await expect.poll(() => page.evaluate(() => document.activeElement?.hasAttribute("data-page-title") ?? false)).toBe(true);
    await settle(page, ".chapterbar");
    const [ink, tab] = await Promise.all([page.locator(".chapter-ink").boundingBox(), chapter(page, "Calidad").boundingBox()]);
    expect(Math.abs(ink!.x - tab!.x)).toBeLessThanOrEqual(1);
    expect(Math.abs(ink!.width - tab!.width)).toBeLessThanOrEqual(1);
    await chapter(page, "La empresa").click();
    await expect.poll(() => dirs(page)).toEqual(["fwd", "back"]);
  });

  test("volver a una pestaña la abre donde se leía; atrás y adelante del navegador, también", async ({ page }) => {
    await page.goto("/v2/NVDA/calidad");
    await page.locator(".depth-body .dsec").first().waitFor({ timeout: 90_000 });
    await page.evaluate(() => window.scrollTo(0, 1600));
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(1000);
    await page.waitForTimeout(150);                 // el último «scroll» ya se anotó
    const y = await page.evaluate(() => window.scrollY);
    await chapter(page, "Riesgos").click();
    await expect(page.locator(".chapterbar a[aria-current=page]")).toHaveText("Riesgos");
    await chapter(page, "Calidad").click();
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(y);
    await page.goBack();
    await expect(page.locator(".chapterbar a[aria-current=page]")).toHaveText("Riesgos");
    await page.goForward();
    await expect(page.locator(".chapterbar a[aria-current=page]")).toHaveText("Calidad");
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(y);
  });
});

test("las píldoras llevan al apartado (suave), lo dejan bajo las barras, marcan la URL sin añadir historia", async ({ page }) => {
  await page.goto("/v2/NVDA/negocio");
  const pills = page.locator("nav.pillindex a.pillnav");
  await pills.first().waitFor({ timeout: 90_000 });
  const before = await page.evaluate(() => history.length);
  const target = await pills.nth(2).getAttribute("href");
  await pills.nth(2).click();
  await expect(pills.nth(2)).toHaveAttribute("aria-current", "location");      // activa desde el toque
  await expect(page).toHaveURL(new RegExp(`${target}$`));
  expect(await page.evaluate(() => history.length)).toBe(before);
  // al terminar el desplazamiento, el apartado queda justo bajo las barras fijas
  await expect.poll(async () => {
    const r = await page.evaluate((id) => {
      const el = document.getElementById(id)!, bar = document.querySelector(".pillindex")!.getBoundingClientRect();
      return Math.round(el.getBoundingClientRect().top - bar.bottom);
    }, target!.slice(1));
    return r >= -2 && r <= 64;
  }, { timeout: 5_000 }).toBe(true);
});

test.describe("con «reducir movimiento»", () => {
  test.use({ reducedMotion: "reduce" });
  test("sin entrada de la sección ni desplazamiento suave; las ayudas, sin escala", async ({ page }) => {
    await page.goto("/v2/NVDA");
    await page.locator(".chapterbar a").first().waitFor({ timeout: 90_000 });
    await watchDir(page);
    await chapter(page, "Cómo gana dinero").click();
    await expect(page.locator(".chapterbar a[aria-current=page]")).toHaveText("Cómo gana dinero");
    expect(await dirs(page)).toEqual([]);
    expect(await page.locator(".chapter-ink").evaluate((e) => getComputedStyle(e).transitionDuration)).toMatch(/^0s/);
    const pills = page.locator("nav.pillindex a.pillnav");
    const id = (await pills.nth(2).getAttribute("href"))!.slice(1);
    await pills.nth(2).click();
    // sin suavizado: en el mismo fotograma ya está en su sitio
    const top = await page.evaluate((i) => document.getElementById(i)!.getBoundingClientRect().top, id);
    await page.waitForTimeout(300);
    expect(Math.abs(top - await page.evaluate((i) => document.getElementById(i)!.getBoundingClientRect().top, id))).toBeLessThanOrEqual(1);
    const tip = page.locator(".depth-body .tip-btn:visible").first();
    if (await tip.count()) {
      await tip.click();
      const box = page.locator(".tip-box:not([data-state=closed])");
      await expect(box).toBeVisible();
      expect(await box.evaluate((e) => getComputedStyle(e).transform)).toBe("none");
    }
  });
});

test.describe("hoja inferior (móvil)", () => {
  test.beforeEach(({ page }) => { test.skip((page.viewportSize()?.width ?? 0) >= 768, "solo la hoja del móvil"); });
  test("sube, se cierra con Escape por el mismo camino y devuelve el foco a su «?»", async ({ page }) => {
    await page.goto("/v2/NVDA/calidad");
    const btn = page.locator(".depth-body .tip-btn:visible").first();
    await btn.waitFor({ timeout: 90_000 });
    await btn.click();
    const sheet = page.locator(".tip-box.sheet");
    await expect(sheet).toHaveAttribute("data-state", "open");
    await settle(page, ".tip-box.sheet");
    expect(await sheet.evaluate((e) => new DOMMatrix(getComputedStyle(e).transform).m42)).toBe(0);
    await page.keyboard.press("Escape");
    await expect(sheet).toHaveAttribute("data-state", "closed");          // sale (mientras, inerte)
    await expect(btn).toBeFocused();
    await expect(sheet).toHaveCount(0, { timeout: 2_000 });
  });
});

test("portada: al cambiar de periodo el cintillo nunca se vacía y la página no salta", async ({ page }) => {
  await page.goto("/v2");
  const tape = page.getByTestId("ticker");
  await tape.waitFor({ timeout: 60_000 });
  const h0 = (await tape.boundingBox())!.height;
  await page.evaluate(() => {
    const w = window as unknown as { __min: number };
    w.__min = Infinity;
    const t = document.querySelector("[data-testid=ticker]")!;
    const tick = () => { w.__min = Math.min(w.__min, t.querySelectorAll(".run:not([data-copy]) .tk-cell").length); requestAnimationFrame(tick); };
    tick();
  });
  await page.getByTestId("period-1M").click();
  await expect(page.getByTestId("period-1M")).toHaveAttribute("aria-pressed", "true");
  await expect(tape).not.toHaveAttribute("data-pending", "", { timeout: 30_000 });
  expect(await page.evaluate(() => (window as unknown as { __min: number }).__min)).toBeGreaterThan(0);
  expect(Math.abs((await tape.boundingBox())!.height - h0)).toBeLessThanOrEqual(1);
});

test("«Precio» en Cifras clave no abre la ayuda del atractivo del precio", async ({ page }) => {
  await page.goto("/v2/NVDA/empresa");
  const tile = page.locator(".tiles.flow .tile", { has: page.locator(".tile-label", { hasText: /^Precio/ }) }).first();
  await tile.waitFor({ timeout: 90_000 });
  const tip = tile.locator(".tip-btn");
  if (await tip.count()) {
    await tip.click();
    await expect(page.locator(".tip-box:not([data-state=closed])")).not.toContainText("Atractivo del precio");
  }
});
