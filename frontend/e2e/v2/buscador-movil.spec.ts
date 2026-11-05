import { test, expect, type Page } from "@playwright/test";

// Buscador en el móvil (4-nov-2026). El usuario: «se borró la barra de búsqueda luego de que ya busqué una acción… me
// tengo que devolver para buscar otra». En el móvil, la barra lleva una lupa que despliega bajo ella una fila con el
// buscador a todo el ancho (foco puesto: en iOS sale el teclado); se cierra con «Cerrar», Escape, al elegir y al cambiar
// de página. Para que quepa (medido a 320, 375 y 402 px), el modo claro/oscuro es un sol o una luna y, por debajo de
// 400 px, la marca es solo el logo.
const phones = ["mobile", "mobile-webkit"];
const phoneOnly = (name: string) => test.skip(!phones.includes(name), "teléfonos");
const lupa = (page: Page) => page.getByRole("button", { name: "Buscar empresa o ticker" });
const box = (page: Page) => page.locator(".topbar").getByRole("combobox", { name: "Buscar empresa o ticker" });

/** La fila, ya colocada (su entrada dura 220 ms). */
async function settled(page: Page) {
  await expect.poll(() => page.locator(".search-row").evaluate((e) => getComputedStyle(e).transform)).toBe("none");
}

/** La página, asentada: la sección pintada, la transición de la carga acabada y la vista colocada (placeView). */
async function ready(page: Page, url = "/v2/AAPL") {
  await page.goto(url);
  await page.locator(".topbar .pdf-btn").waitFor({ timeout: 90_000 });
  await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
  await page.waitForTimeout(800);
}

test("desde la página de una acción se busca otra sin volver a la portada", async ({ page }, info) => {
  phoneOnly(info.project.name);
  await ready(page);
  await expect(box(page)).toBeHidden();
  await expect(lupa(page)).toHaveAttribute("aria-expanded", "false");
  const r = (await lupa(page).boundingBox())!;
  expect(r.width).toBeGreaterThanOrEqual(44);
  expect(r.height).toBeGreaterThanOrEqual(44);

  await lupa(page).tap();
  await expect(box(page)).toBeVisible();
  await expect(box(page)).toBeFocused();
  await expect(lupa(page)).toHaveAttribute("aria-expanded", "true");
  await settled(page);
  // la fila, a todo el ancho bajo la barra
  const [bar, row] = await Promise.all([page.locator(".topbar").boundingBox(), page.locator(".search-row").boundingBox()]);
  expect(Math.abs(row!.y - (bar!.y + bar!.height))).toBeLessThanOrEqual(1);
  expect(row!.width).toBeCloseTo(page.viewportSize()!.width, 0);

  await box(page).fill("microsoft");
  const first = page.getByRole("option").first();
  await expect(first).toContainText("MSFT");
  // las sugerencias, bajo la fila y dentro de sus márgenes
  const [list, input] = await Promise.all([page.getByRole("listbox").boundingBox(), box(page).boundingBox()]);
  expect(list!.x).toBeCloseTo(input!.x, 0);
  expect(list!.x + list!.width).toBeLessThanOrEqual(page.viewportSize()!.width - input!.x + 1);
  expect(list!.y).toBeGreaterThan(input!.y + input!.height);
  // las sugerencias se ven: dentro de la pantalla y nada encima
  const seen = await first.evaluate((e) => {
    const b = e.getBoundingClientRect(), hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return b.top >= 0 && b.bottom <= innerHeight && !!hit && e.contains(hit);
  });
  expect(seen).toBe(true);
  await first.tap();
  await expect(page).toHaveURL(/\/v2\/MSFT\/?$/);
  await page.locator(".topbar .pdf-btn").waitFor({ timeout: 90_000 });
  await expect(box(page)).toBeHidden();
  await expect(lupa(page)).toBeVisible();
});

test("la fila se cierra con «Cerrar» y con Escape, y el foco vuelve a la lupa", async ({ page }, info) => {
  phoneOnly(info.project.name);
  await ready(page);
  await lupa(page).tap();
  await expect(box(page)).toBeFocused();
  await settled(page);
  await page.getByRole("button", { name: "Cerrar" }).tap();
  await expect(box(page)).toBeHidden();
  await expect(lupa(page)).toBeFocused();
  await expect(lupa(page)).toHaveAttribute("aria-expanded", "false");

  await lupa(page).tap();
  await box(page).fill("jpm");
  await expect(page.getByRole("option").first()).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(box(page)).toBeHidden();
  await expect(lupa(page)).toBeFocused();
});

test("la fila se cierra al cambiar de página (atrás entre secciones)", async ({ page }, info) => {
  phoneOnly(info.project.name);
  await ready(page);
  await page.locator(".chapterbar a", { hasText: "Calidad" }).first().tap();
  await expect(page).toHaveURL(/\/calidad\/?$/);
  await page.evaluate(() => window.scrollTo(0, 0));
  await lupa(page).tap();
  await expect(box(page)).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/v2\/AAPL\/?$/);
  await expect(box(page)).toBeHidden();
});

for (const width of [320, 375, 402]) {
  test(`a ${width} px caben marca, lupa, tema y «Descargar PDF»: sin desbordar y texto ≥ 12 px`, async ({ page }, info) => {
    phoneOnly(info.project.name);
    await page.setViewportSize({ width, height: 760 });
    await ready(page);
    await page.evaluate(() => document.fonts.ready);
    const m = await page.evaluate(() => {
      const q = (s: string) => document.querySelector(s)!.getBoundingClientRect();
      const parts = [q(".topbar .brand-logo"), q(".search-toggle"), q(".theme-btn"), q(".topbar .pdf-btn")];
      const texts = [...document.querySelectorAll(".topbar .wrap *")].filter((e) => e.getClientRects().length
        && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent!.trim()) && e.getBoundingClientRect().width > 1);
      return {
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        inside: parts.every((r) => r.left >= 0 && r.right <= innerWidth),
        ordered: parts.every((r, i) => i === 0 || r.left >= parts[i - 1].right),
        sizes: [parts[1], parts[2]].map((r) => [Math.round(r.width), Math.round(r.height)]),
        minFont: Math.min(...texts.map((e) => parseFloat(getComputedStyle(e).fontSize))),
        word: q(".brand-word").width,
      };
    });
    expect(m.overflow).toBe(0);
    expect(m.inside, "todo dentro de la pantalla").toBe(true);
    expect(m.ordered, "sin pisarse").toBe(true);
    expect(m.sizes).toEqual([[44, 44], [44, 44]]);
    expect(m.minFont).toBeGreaterThanOrEqual(12);
    if (width < 400) expect(m.word, "por debajo de 400 px, la marca es solo el logo").toBeLessThanOrEqual(1);
    else expect(m.word).toBeGreaterThan(40);
    await expect(page.locator(".topbar .brand")).toHaveAccessibleName("Finanzer");
  });
}

test("el modo claro/oscuro, un sol o una luna con su nombre y su estado", async ({ page }, info) => {
  phoneOnly(info.project.name);
  await ready(page);
  const toDark = page.getByRole("button", { name: "Modo oscuro" });
  await expect(toDark).toHaveAttribute("aria-pressed", "false");
  await expect(toDark.locator("svg.theme-to-dark")).toBeVisible();
  await expect(toDark.locator("svg.theme-to-light")).toBeHidden();
  await toDark.tap();
  const toLight = page.getByRole("button", { name: "Modo claro" });
  await expect(toLight).toHaveAttribute("aria-pressed", "true");
  await expect(toLight.locator("svg.theme-to-light")).toBeVisible();
  await expect(toLight.locator("svg.theme-to-dark")).toBeHidden();
});

test("la fila se pliega al desplazar la página (la barra no pasa sobre la franja de la barra de estado)", async ({ page }, info) => {
  phoneOnly(info.project.name);
  await ready(page);
  await lupa(page).tap();
  await settled(page);
  await page.evaluate(() => window.scrollTo(0, 4));
  await page.waitForTimeout(200);
  await expect(box(page), "unos px (el ajuste del teclado) no la cierran").toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 120));
  await expect(box(page)).toBeHidden();
  await expect(lupa(page)).toHaveAttribute("aria-expanded", "false");
});

test("con «reducir movimiento», la fila solo se funde (sin desplazarse)", async ({ page }, info) => {
  phoneOnly(info.project.name);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await ready(page);
  await lupa(page).tap();
  const st = await page.locator(".search-row").evaluate((e) => {
    const s = getComputedStyle(e);
    return { transform: s.transform, dur: s.transitionDuration };
  });
  expect(st.transform).toBe("none");
  expect(st.dur.split(",").map((d) => parseFloat(d) * (d.includes("ms") ? 1 : 1000)).every((d) => d <= 150)).toBe(true);
});

test("escritorio y portada: sin lupa", async ({ page }, info) => {
  if (phones.includes(info.project.name)) {
    await page.goto("/v2");
    await expect(page.locator(".topbar .theme-btn")).toBeVisible();
    await expect(lupa(page)).toHaveCount(0);       // la portada lleva su buscador grande
    return;
  }
  await ready(page);
  await expect(page.locator(".search-toggle")).toBeHidden();
  await expect(page.getByRole("button", { name: "Cerrar" })).toBeHidden();
  await expect(box(page)).toBeVisible();
  await expect(page.locator(".topbar .theme-btn svg").first()).toBeHidden();
});
