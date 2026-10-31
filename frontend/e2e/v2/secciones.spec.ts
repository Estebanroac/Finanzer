import { test, expect } from "@playwright/test";
import { openSection, SECTIONS } from "./checks";

// V4b · 1 (cambio de spec, literal del usuario: «quiero mi análisis seccionado y el detalle dentro de la sección»):
// nueve secciones con ruta propia, /v2/{T} abre «La empresa», la cabecera queda fija arriba (compacta al bajar) con la
// barra de secciones debajo, cada sección abre con su lectura y acaba en «Siguiente sección →», y ya no hay una página
// que lo enseñe todo.
const LABELS = ["La empresa", "Cómo gana dinero", "La acción", "Calidad", "Cuánto vale", "Rivales", "Riesgos", "Actualidad", "Conclusión"];

test("cada sección tiene su ruta, su pestaña activa, su lectura y el paso a la siguiente", async ({ page }) => {
  test.setTimeout(240_000);
  for (const [i, s] of SECTIONS.entries()) {
    await openSection(page, "AAPL", s);
    await expect(page.locator(".depth")).toHaveCount(1);                       // una sección, nunca todas
    await expect(page.locator(".depth")).toHaveAttribute("data-chapter", s);
    await expect(page.locator("nav.chapterbar a")).toHaveText(LABELS);
    await expect(page.locator("nav.chapterbar a[aria-current=page]")).toHaveText(LABELS[i]);
    await expect(page).toHaveTitle(new RegExp(`^${LABELS[i]} · Apple Inc\\. \\(AAPL\\) · Finanzer$`));
    const intro = page.getByTestId("section-intro");
    await expect(intro.locator(".eyebrow").first()).toHaveText(`${i + 1} · ${LABELS[i]}`);
    await expect(intro.locator("h2")).not.toBeEmpty();
    await expect(intro.locator(".lead")).not.toBeEmpty();
    await expect(intro.locator(".figure")).toHaveCount(3);
    // la cabecera completa (identidad, precio, conclusión y las tres puntuaciones) en todas
    for (const id of ["price", "verdict", "score-quality", "score-price", "confidence"]) await expect(page.getByTestId(id)).toBeVisible();
    const next = page.getByTestId("next-section");
    if (i < SECTIONS.length - 1) await expect(next).toHaveText(`Siguiente sección → ${LABELS[i + 1]}`);
    else await expect(next).toHaveCount(0);
  }
});

test("«Siguiente sección →» lleva al principio de la siguiente, bajo la cabecera fija", async ({ page }) => {
  await openSection(page, "AAPL", "calidad");
  await page.getByTestId("next-section").scrollIntoViewIfNeeded();
  await page.getByTestId("next-section").click();
  await expect(page).toHaveURL(/\/v2\/AAPL\/valor\/?$/);
  await page.waitForSelector(".depth[data-chapter=valor] .depth-body .dsec");
  await expect(page.locator("[data-page-title]")).toBeFocused();
  await expect.poll(async () => page.evaluate(() => {
    const bar = document.querySelector("nav.chapterbar")!.getBoundingClientRect();
    return Math.abs(Math.round(document.querySelector(".depth")!.getBoundingClientRect().top - bar.bottom));
  })).toBe(0);
});

test("la cabecera queda fija al bajar: aparece la compacta, con la barra de secciones debajo", async ({ page }) => {
  await openSection(page, "AAPL", "calidad");
  const head = page.locator(".stuck-head");
  await expect(head).toBeHidden();
  await page.evaluate(() => window.scrollTo(0, document.querySelector(".depth")!.getBoundingClientRect().top + window.scrollY + 600));
  await expect(head).toBeVisible();
  await expect(head.locator(".scores-line")).toContainText(/Calidad.*Precio.*Confianza/);
  await expect(head.locator(".company-header")).toHaveAttribute("aria-hidden", "true");
  // (en WebKit el visor visual empieza unos px más abajo que el de la ventana al desplazar: se mide desde el visor)
  const rects = () => page.evaluate(() => [document.querySelector(".stuck-head")!.getBoundingClientRect(),
    document.querySelector("nav.chapterbar")!.getBoundingClientRect()].map((r) => ({
    top: Math.round(r.top + (visualViewport?.offsetTop ?? 0)), bottom: Math.round(r.bottom + (visualViewport?.offsetTop ?? 0)) })));
  await expect.poll(async () => (await rects())[0].top).toBe(0);       // entra deslizándose (0,15 s)
  const [h, bar] = await rects();
  expect(bar.top).toBe(h.bottom);
  // en el móvil, lo justo: la fija no se come la pantalla (≤ 15 % del alto)
  const vh = await page.evaluate(() => window.innerHeight);
  expect(h.bottom).toBeLessThanOrEqual(Math.max(140, vh * 0.15));
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(head).toBeHidden();
});

test("los enlaces de la antigua página-historia (/v2/{T}#capítulo) llevan a la sección", async ({ page }) => {
  await page.goto("/v2/AAPL#riesgos");
  await expect(page).toHaveURL(/\/v2\/AAPL\/riesgos\/?$/);
  await page.waitForSelector(".depth[data-chapter=riesgos] .depth-body .dsec", { timeout: 60_000 });
  // y un ancla de una sección sigue llevando a su apartado
  await page.goto("/v2/AAPL/calidad#piotroski");
  await page.waitForSelector(".depth[data-chapter=calidad] .depth-body .dsec", { timeout: 60_000 });
  await expect(page.locator("#piotroski")).toBeInViewport();
});

test("PM: en el móvil, al navegar entre secciones el título queda en la primera pantalla y la cabecera, ya compacta", async ({ page }, info) => {
  test.skip(!["mobile", "mobile-webkit"].includes(info.project.name), "teléfonos");
  test.setTimeout(180_000);
  await openSection(page, "AAPL", "empresa");
  const titleTop = () => page.evaluate(() => document.querySelector("[data-page-title]")!.getBoundingClientRect().top);
  // entrar directo: el título, en la primera pantalla
  expect(await titleTop()).toBeLessThanOrEqual(await page.evaluate(() => innerHeight));
  for (const [i, s] of SECTIONS.entries()) {
    if (i === 0) continue;
    // con la barra de secciones y, la última vez, con «Siguiente sección»
    if (i < SECTIONS.length - 1) await page.locator("nav.chapterbar").getByRole("link", { name: LABELS[i], exact: true }).click();
    else await page.getByTestId("next-section").click();
    await page.waitForSelector(`.depth[data-chapter=${s}] .depth-body .dsec`);
    await expect.poll(titleTop).toBeGreaterThanOrEqual(0);
    expect(await titleTop(), `${s}: el título en la primera pantalla`).toBeLessThanOrEqual(await page.evaluate(() => innerHeight));
    await expect(page.locator(".stuck-head"), `${s}: la cabecera, compacta`).toBeVisible();
  }
});
