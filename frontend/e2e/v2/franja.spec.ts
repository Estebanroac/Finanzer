import { test, expect, type Page } from "@playwright/test";

// La franja de la barra de estado (el usuario, en su iPhone con Safari 26, tras cambiar de pestaña: «queda la barra de
// colores arriba»). Safari pinta esa franja con el fondo de un elemento fijo que toque el borde superior y tenga algo de
// alto (con 8 px lo hace; con 1–4 px, no); si no lo hay, o no lo encuentra cuando muestrea, deja ver la página. En
// pantallas táctiles hay siempre una banda fija del color de la cabecera en ese borde, fuera de lo que se funde al cambiar
// de pestaña; la barra superior empieza bajo ella y la cabecera compacta la tapa.
const SAFARI_MIN_PX = 8;           // alto con el que Safari 26 (iPhone, simulador iOS 26.5) ya tiñe la franja

/** La banda del borde superior: fija, arriba del todo, con alto suficiente y del color de la cabecera (--surface). */
const band = (page: Page) => page.evaluate(() => {
  const fz = document.querySelector<HTMLElement>(".fz2")!, el = fz.querySelector<HTMLElement>(".status-edge")!, b = getComputedStyle(el);
  const probe = document.createElement("div");
  probe.style.background = "var(--surface)";
  fz.appendChild(probe);
  const surface = getComputedStyle(probe).backgroundColor;
  probe.remove();
  // Safari busca el color con el elemento que hay en el borde: tiene que recibir los toques
  // (WebKit de escritorio retrasa 17 px su viewport visual al bajar y deja la banda fuera de él: ahí no se puede tocar y
  // la comprobación queda para Chromium móvil; no es la página la que se mueve)
  const top = el.getBoundingClientRect().top;
  const hit = top < 0 ? null : document.elementFromPoint(window.innerWidth / 2, top + 1);
  return { position: b.position, top: b.top, height: parseFloat(b.height), bg: b.backgroundColor, surface, opacity: Number(b.opacity),
           pointer: b.pointerEvents, hit: top < 0 ? null : hit === el || !!hit?.closest(".stuck-head") };
});
const expectBand = async (page: Page, cuando: string) => {
  const b = await band(page);
  expect(b.position, cuando).toBe("fixed");
  expect(b.top, cuando).toBe("0px");
  expect(b.height, cuando).toBeGreaterThanOrEqual(SAFARI_MIN_PX);
  expect(b.bg, cuando).toBe(b.surface);
  expect(b.opacity, cuando).toBe(1);
  expect(b.pointer, cuando).not.toBe("none");
  expect(b.hit, cuando).not.toBe(false);
};

test.beforeEach(async ({ page }, info) => {
  test.skip(info.project.name === "desktop", "la franja de estado solo existe en pantallas táctiles");
  await page.goto("about:blank");
  expect(await page.evaluate(() => matchMedia("(hover: none) and (pointer: coarse)").matches)).toBe(true);
});

for (const tema of ["light", "dark"] as const) {
  test(`la franja de estado es siempre del color de la cabecera · ${tema}`, async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem("finanzer.v2.theme", t), tema);
    await page.goto("/v2/NVDA");
    await page.locator(".depth-body .dsec").first().waitFor({ timeout: 90_000 });
    // arriba del todo: la barra superior empieza bajo la banda (no la tapa)
    await expectBand(page, "arriba");
    const wrapTop = await page.locator(".topbar .wrap").evaluate((el) => el.getBoundingClientRect().top);
    expect(wrapTop).toBeGreaterThanOrEqual((await band(page)).height);
    // a media cabecera (sin compactar): la página pasa bajo la banda
    await page.evaluate(() => window.scrollTo(0, 200));
    await expect(page.locator(".fz2[data-stuck]")).toHaveCount(0);
    await expectBand(page, "a media cabecera");
    // cambio de pestaña desde arriba: la banda no se funde con la página en ningún fotograma
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.evaluate(() => {
      const w = window as unknown as { __op: number[]; __stop: boolean };
      w.__op = []; w.__stop = false;
      const tick = () => {
        let o = 1;
        for (let e: Element | null = document.querySelector(".status-edge"); e; e = e.parentElement) o *= Number(getComputedStyle(e).opacity);
        w.__op.push(o);
        if (!w.__stop) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    await page.locator(".chapterbar a", { hasText: "Conclusión" }).first().click();
    await expect(page.locator(".fz2[data-stuck]")).toHaveCount(1);
    await expect(page.locator(".chapterbar a[aria-current=page]")).toHaveText("Conclusión");
    await page.waitForTimeout(600);
    const op = await page.evaluate(() => { const w = window as unknown as { __op: number[]; __stop: boolean }; w.__stop = true; return w.__op; });
    expect(Math.min(...op)).toBe(1);
    // con la cabecera compacta: la tapa y empieza en el borde (Safari muestrea la de más arriba: las dos, del mismo color)
    // (en coordenadas de la página: WebKit retrasa 17 px su viewport visual al bajar)
    await expectBand(page, "pegada");
    const head = await page.locator(".stuck-head").evaluate((el) => ({ top: el.getBoundingClientRect().top + (window.visualViewport?.offsetTop ?? 0), z: Number(getComputedStyle(el).zIndex) }));
    expect(head.top).toBe(0);
    expect(head.z).toBeGreaterThan(Number(await page.locator(".status-edge").evaluate((el) => getComputedStyle(el).zIndex)));
  });
}

test("portada: la banda también está y la barra superior empieza bajo ella", async ({ page }) => {
  await page.goto("/v2");
  await page.locator(".topbar .wrap").waitFor({ timeout: 90_000 });
  await expectBand(page, "portada");
  const wrapTop = await page.locator(".topbar .wrap").evaluate((el) => el.getBoundingClientRect().top);
  expect(wrapTop).toBeGreaterThanOrEqual((await band(page)).height);
});
