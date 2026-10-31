import { test, expect, type Page } from "@playwright/test";

// v4 (PM): el texto de un «?» más largo que el sitio disponible se cortaba por abajo y no se podía desplazar (el propio
// desplazamiento del panel lo recolocaba y lo devolvía arriba). Regla: el panel nunca sale de la ventana, se lee entero
// desplazándose por dentro (rueda, dedo o teclado) y «Cerrar» queda siempre a la vista. En móvil, hoja inferior.
const PANEL = ".tip-box:not([data-state=closed])";
// Beta ajustada de NVDA: descripción, fórmula, umbrales y nota (la más larga de las cifras clave)
const PATH = "/v2/NVDA/empresa";
const TIP = 'button.tip-btn[data-tip="beta"]';

/** Abre el «?» de la beta con el ancla a la altura `at` de la ventana (0 arriba, 1 abajo). */
async function openTip(page: Page, at = 0.5) {
  await page.goto(PATH);
  const btn = page.locator(TIP).first();
  await btn.waitFor({ timeout: 60_000 });
  await btn.evaluate((b, at) => {
    b.scrollIntoView({ block: "center" });
    window.scrollBy(0, b.getBoundingClientRect().top - window.innerHeight * at);
  }, at);
  await page.waitForTimeout(200);              // la cabecera fija entra un fotograma después
  await btn.click();
  const box = page.locator(PANEL);
  await expect(box).toBeVisible();
  return { btn, box, body: box.locator(".float-body") };
}

/** Dentro de la ventana (con medio píxel de redondeo). */
async function inWindow(page: Page, sel: string): Promise<string | null> {
  return page.evaluate((sel) => {
    const el = document.querySelector<HTMLElement>(sel);
    if (!el) return `${sel}: no está`;
    const r = el.getBoundingClientRect(), vh = document.documentElement.clientHeight, vw = document.documentElement.clientWidth;
    return r.top < -0.5 || r.left < -0.5 || r.bottom > vh + 0.5 || r.right > vw + 0.5
      ? `${sel}: ${Math.round(r.left)},${Math.round(r.top)} → ${Math.round(r.right)},${Math.round(r.bottom)} en ${vw}×${vh}` : null;
  }, sel);
}

async function readToTheEnd(page: Page, wheel: boolean) {
  const { box, body } = await openTip(page);
  const closeBtn = box.getByRole("button", { name: "Cerrar" });
  // el texto no cabe: el cuerpo se desplaza y, por eso, se puede enfocar (teclado y lector de pantalla)
  const m0 = await body.evaluate((b) => ({ sh: b.scrollHeight, ch: b.clientHeight }));
  expect(m0.sh, "el texto debe ser más largo que el sitio (si no, la prueba no prueba nada)").toBeGreaterThan(m0.ch);
  await expect(body).toHaveAttribute("tabindex", "0");
  await expect(body).toHaveAttribute("role", "region");
  await expect(body).toHaveAttribute("aria-label", /.+/);
  const pageY = await page.evaluate(() => window.scrollY);
  if (wheel) {
    await body.hover();
    for (let i = 0; i < 8; i++) { await page.mouse.wheel(0, 400); await page.waitForTimeout(60); }
  } else {
    await body.focus();
    await page.keyboard.press("End");
  }
  await expect.poll(() => body.evaluate((b) => Math.ceil(b.scrollTop + b.clientHeight) >= b.scrollHeight - 1),
    { message: "se llega al final del texto" }).toBe(true);
  await page.waitForTimeout(250);               // si algo lo recolocara, volvería arriba
  expect(await body.evaluate((b) => b.scrollTop), "sigue donde lo dejó el usuario").toBeGreaterThan(0);
  // la última línea, a la vista dentro del cuerpo; «Cerrar», visible y dentro de la ventana; el panel, también
  const last = await body.evaluate((b) => {
    const kids = b.querySelectorAll(".float-content > *");
    const l = kids[kids.length - 1].getBoundingClientRect(), r = b.getBoundingClientRect();
    return l.bottom <= r.bottom + 1;
  });
  expect(last, "la última línea se ve").toBe(true);
  await expect(closeBtn).toBeInViewport({ ratio: 1 });
  expect(await inWindow(page, PANEL)).toBeNull();
  if (wheel) expect(await page.evaluate(() => window.scrollY), "la rueda no arrastra la página").toBe(pageY);
  await closeBtn.click();
  await expect(page.locator(PANEL)).toHaveCount(0);
}

test("ventana baja y texto largo: se lee hasta el final y «Cerrar» sigue a la vista", async ({ page }, info) => {
  const vp = page.viewportSize()!;
  await page.setViewportSize({ width: vp.width, height: vp.width < 768 ? 560 : 520 });
  await readToTheEnd(page, info.project.name === "desktop");
  if (info.project.name !== "desktop") return;
  await readToTheEnd(page, false);               // también con el teclado
});

test("zoom al 200 % (1280×600 → 640×300 px CSS): hoja inferior que se lee entera", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "el tamaño se fija a mano");
  await page.setViewportSize({ width: 640, height: 300 });
  const { box, body } = await openTip(page);
  await expect(box).toHaveClass(/\bsheet\b/);
  await body.focus();
  await page.keyboard.press("End");
  await expect.poll(() => body.evaluate((b) => Math.ceil(b.scrollTop + b.clientHeight) >= b.scrollHeight - 1)).toBe(true);
  await expect(box.getByRole("button", { name: "Cerrar" })).toBeInViewport({ ratio: 1 });
  expect(await inWindow(page, PANEL)).toBeNull();
});

test("si abajo no cabe, abre hacia arriba (el lado con más sitio)", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "en móvil es una hoja inferior");
  const { btn, box } = await openTip(page, 0.85);
  const a = (await btn.boundingBox())!, b = (await box.boundingBox())!;
  expect(b.y + b.height, "el panel queda por encima del «?»").toBeLessThanOrEqual(a.y + 1);
  expect(await inWindow(page, PANEL)).toBeNull();
});

test("tabla apilada (móvil): el «?» de una columna, el del ETF del sector, se ve encima de las filas y se abre", async ({ page }) => {
  await page.goto("/v2/NVDA/accion");
  const btn = page.getByTestId("returns-by-period").locator('button.tip-btn[data-tip="sector_etf"]');
  await btn.scrollIntoViewIfNeeded({ timeout: 60_000 });
  await btn.click();                              // en móvil la tapaban las filas: el clic no le llegaba
  await expect(page.locator(PANEL)).toBeVisible();
  // v4.1: el panel entra con una transición; se mide al terminarla (de forma determinista, no con una espera fija: si al
  // colocarse se reinicia, se espera a la nueva)
  await expect.poll(() => page.locator(PANEL).evaluate((el) =>
    el.getAnimations({ subtree: true }).filter((a) => a.playState === "running").length)).toBe(0);
  await expect(page.locator(PANEL).getByRole("button", { name: "Cerrar" })).toBeInViewport({ ratio: 1 });
});
