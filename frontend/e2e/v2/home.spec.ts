import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { symmetryProblems } from "./checks";

/** P8: valores del cintillo por lista (backend [trending] top_n). */
const LIST_SIZE = 30;

/** El cintillo con sus valores y sus mini-gráficas. */
async function stripReady(page: Page) {
  await expect(page.getByTestId("ticker-item")).toHaveCount(LIST_SIZE, { timeout: 30_000 });
  await expect(page.getByTestId("ticker-item").getByTestId("spark")).toHaveCount(LIST_SIZE, { timeout: 30_000 });
}

test("portada: titular, buscador y cintillo con mini-gráficas y el motor en caché", async ({ page }) => {
  await page.goto("/v2");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Entiende una empresa antes de invertir");
  await stripReady(page);
  const aapl = page.locator("[data-testid=ticker-item][data-symbol=AAPL]");
  await expect(aapl).toHaveAttribute("href", "/v2/AAPL");
  await expect(aapl).toContainText("$343.46");
  await expect(aapl.locator(".tk-chg")).toHaveText("▲ 0.43%");
  // El replay analiza las más negociadas en segundo plano: «Calidad N · Precio N» aparece cuando están en caché.
  await expect(aapl.locator(".tk-eng")).toHaveText(/^Calidad \d+ · Precio \d+$/, { timeout: 90_000 });
  // Un valor sin análisis en caché lleva la misma línea con «Ver análisis →» (color de enlace): sin hueco. META no
  // está grabada en el replay (V4b: TSLA sí, como rival, en tests/fixtures/peers).
  const noEngine = page.locator("[data-testid=ticker-item][data-symbol=META] .tk-eng");
  await expect(noEngine).toHaveText("Ver análisis →");
  expect(await noEngine.evaluate((e) => getComputedStyle(e).fontSize))
    .toBe(await aapl.locator(".tk-eng").evaluate((e) => getComputedStyle(e).fontSize));
  await expect(page.getByTestId("ticker-context")).toHaveText(
    /^Más negociadas en 1 día \(del 15-oct-2026 al 16-oct-2026\) · universo: S&P 500 y ADR principales · 30 valores$/);
  await expect(page.getByRole("heading", { name: "Datos oficiales de la SEC" })).toBeVisible();
});

/** Dónde va el cintillo: su scrollLeft (con ratón) o el desplazamiento de la pista (transform, pantallas táctiles). */
const scrollX = (page: Page) => page.getByTestId("ticker").evaluate((e) =>
  e.scrollLeft - new DOMMatrix(getComputedStyle(e.querySelector(".track")!).transform).m41);

test("P8b: el cintillo avanza solo, sin botón; quieto con el foco del teclado y de nuevo en marcha al salir (WCAG 2.2.2)", async ({ page, isMobile }) => {
  await page.goto("/v2");
  await stripReady(page);
  const tape = page.getByTestId("ticker");
  await expect(tape).toHaveAttribute("data-mode", "animado");
  await expect(page.getByRole("button", { name: /Pausar|Reanudar/ })).toHaveCount(0);
  const a = await scrollX(page);
  await expect.poll(() => scrollX(page)).toBeGreaterThan(a);              // avanza solo (scrollLeft)
  if (!isMobile) {
    // foco de teclado dentro: parado; al salir el foco, arranca en el acto (V4b)
    await page.getByTestId("period-6M").focus();
    await page.getByTestId("period-1D").focus();
    await page.keyboard.press("Tab");
    while (!(await page.evaluate(() => document.activeElement?.getAttribute("data-testid") === "ticker-item"))) {
      await page.keyboard.press("Tab");
    }
    await expect(tape).toHaveAttribute("data-mode", "pausado");
    const b = await scrollX(page);
    await page.waitForTimeout(2000);
    expect(await scrollX(page)).toBe(b);
    await page.getByTestId("period-1D").focus();                            // el foco sale del cintillo
    await expect(tape).toHaveAttribute("data-mode", "animado", { timeout: 500 });
  }
  // La copia que cierra el bucle no se lee ni recibe el foco (aria-hidden y tabIndex −1 en sus enlaces).
  await expect(page.locator(".run[aria-hidden=true]")).toHaveCount(1);
  const copyLinks = page.locator(".run[aria-hidden=true] a");
  expect(await copyLinks.evaluateAll((as) => as.every((a) => a.getAttribute("tabindex") === "-1"))).toBe(true);
  // Sin barra visible y con los bordes en degradado
  const css = await tape.evaluate((e) => ({ ox: getComputedStyle(e).overflowX, sb: getComputedStyle(e).scrollbarWidth,
    mask: getComputedStyle(e).maskImage || getComputedStyle(e).webkitMaskImage }));
  // con ratón, desplazamiento nativo; en pantallas táctiles (v4 cintillo), la pista se mueve con transform y el dedo
  expect(css.ox).toBe(isMobile ? "hidden" : "auto");
  expect(css.sb).toBe("none");
  expect(css.mask).toContain("linear-gradient");
});

// P8b (fallo del usuario): tras pasar el ratón, arrastrar o usar el trackpad, el cintillo se quedaba parado para
// siempre. V4b (el usuario: «que arranque apenas quito el mouse»): en el acto al sacar el ratón; tras arrastrar o
// desplazar, al terminar la inercia, sin espera extra; nunca con el ratón encima.
test.describe("P8b: el cintillo vuelve a arrancar solo", () => {
  test.skip(({ isMobile }) => isMobile, "ratón: escritorio y tableta con ratón");
  const outside = async (page: Page) => {
    const box = (await page.getByTestId("ticker").boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, Math.max(box.y - 150, 5));
  };
  const over = async (page: Page, dx = 0) => {
    const box = (await page.getByTestId("ticker").boundingBox())!;
    await page.mouse.move(box.x + box.width / 2 + dx, box.y + box.height / 2);
  };

  test("1 · ratón encima y fuera: arranca en el acto", async ({ page }) => {
    await page.goto("/v2");
    await stripReady(page);
    await over(page);
    await expect(page.getByTestId("ticker")).toHaveAttribute("data-mode", "pausado");
    const a = await scrollX(page);
    await outside(page);
    await expect(page.getByTestId("ticker")).toHaveAttribute("data-mode", "animado", { timeout: 300 });
    await expect.poll(() => scrollX(page), { timeout: 600 }).toBeGreaterThan(a);
  });

  test("2 · arrastrar y salir: arranca al terminar la inercia (el foco del clic no lo deja parado)", async ({ page }) => {
    await page.goto("/v2");
    await stripReady(page);
    await over(page, 150);
    await page.mouse.down();
    for (let i = 1; i <= 10; i++) await over(page, 150 - i * 30);
    await page.mouse.up();
    await outside(page);
    // la inercia (como mucho ~1,3 s desde la velocidad tope) y, sin espera extra, el avance
    await expect(page.getByTestId("ticker")).toHaveAttribute("data-mode", "animado", { timeout: 2_000 });
    const a = await scrollX(page);
    await expect.poll(() => scrollX(page), { timeout: 600 }).toBeGreaterThan(a);
  });

  test("3 · rueda horizontal (trackpad) y salir: arranca al terminar el desplazamiento", async ({ page, browserName }) => {
    test.skip(browserName === "webkit", "rueda horizontal sintética: Chromium");
    await page.goto("/v2");
    await stripReady(page);
    await over(page);
    await page.mouse.wheel(300, 0);
    await outside(page);
    // el desplazamiento suave de la rueda dura unos cientos de ms; al acabar (scrollend), arranca
    await expect(page.getByTestId("ticker")).toHaveAttribute("data-mode", "animado", { timeout: 1_500 });
    const a = await scrollX(page);
    await expect.poll(() => scrollX(page), { timeout: 600 }).toBeGreaterThan(a);
  });

  test("4 · con el ratón encima no avanza nunca (ni pasado el temporizador)", async ({ page }) => {
    await page.goto("/v2");
    await stripReady(page);
    await over(page);
    await page.mouse.wheel(300, 0);
    await page.waitForTimeout(800);
    const a = await scrollX(page);
    await page.waitForTimeout(4000);
    expect(await scrollX(page)).toBe(a);
    await expect(page.getByTestId("ticker")).toHaveAttribute("data-mode", "pausado");
  });
});

test("V6b: con la copia del bucle a la vista, sus tarjetas se pulsan (no es inert)", async ({ page, isMobile }) => {
  test.skip(isMobile, "ratón: escritorio y tableta");
  await page.goto("/v2");
  await stripReady(page);
  const tape = page.getByTestId("ticker");
  const w = await tape.evaluate((e) => (e.querySelector(".run") as HTMLElement).offsetWidth);
  const box = (await tape.boundingBox())!;
  const x = box.x + 200, y = box.y + box.height / 2;
  // Por estado, no por tiempo: el ratón ya en el punto del clic para el cintillo (como a quien va a pulsar). Sin eso,
  // tras mover a la copia el avance se reanuda (es un gesto) y la posición vuelve al tramo original, idéntico a la
  // vista: la tarjeta bajo el puntero dejaba de ser la de la copia (3 de cada 6 veces).
  await page.mouse.move(x, y);
  await expect(tape).toHaveAttribute("data-mode", "pausado");
  await tape.evaluate((e, w) => { e.scrollLeft = w; }, w);                  // media vuelta: se ve la copia
  await expect.poll(() => scrollX(page)).toBe(w);                           // quieto en la copia
  await expect(tape).toHaveAttribute("data-mode", "pausado");
  const target = await page.evaluate(([x, y]) => {
    const a = document.elementFromPoint(x, y)?.closest("a");
    return a ? { href: a.getAttribute("href"), copy: !!a.closest("[data-copy]") } : null;
  }, [x, y]);
  expect(target?.copy).toBe(true);
  await page.mouse.click(x, y);
  await expect(page).toHaveURL(new RegExp(`${target!.href}/?$`));
});

test("P8b: arrastrar con el ratón desplaza el cintillo y no abre la tarjeta", async ({ page, isMobile }) => {
  test.skip(isMobile, "ratón: escritorio y tableta");
  await page.goto("/v2");
  await stripReady(page);
  const tape = page.getByTestId("ticker");
  await tape.hover();                                                       // quieto mientras se mide
  await expect(tape).toHaveAttribute("data-mode", "pausado");
  const before = await scrollX(page);
  const box = (await tape.boundingBox())!;
  const y = box.y + box.height / 2;
  await page.mouse.move(box.x + box.width / 2, y);
  await page.mouse.down();
  await expect(tape).not.toHaveClass(/dragging/);
  for (let i = 1; i <= 10; i++) await page.mouse.move(box.x + box.width / 2 - i * 30, y);
  await expect(tape).toHaveClass(/dragging/);
  await page.mouse.up();
  await expect(page).toHaveURL(/\/v2\/?$/);                                 // no abrió la tarjeta al soltar
  expect(await scrollX(page)).toBeGreaterThan(before + 200);
  await expect(tape).not.toHaveClass(/dragging/);
  // un clic sin arrastre sí abre la tarjeta
  await page.getByTestId("ticker-item").first().click();
  await expect(page).toHaveURL(/\/v2\/[A-Z.\-]+\/?$/);
});

test("P8b: el trackpad (deltaX) desplaza el cintillo; la rueda vertical sigue moviendo la página", async ({ page, isMobile, browserName }) => {
  test.skip(isMobile || browserName === "webkit", "rueda: Chromium de escritorio y tableta");
  await page.setViewportSize({ width: 1280, height: 600 });
  await page.goto("/v2");
  await stripReady(page);
  const tape = page.getByTestId("ticker");
  const box = (await tape.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await expect(tape).toHaveAttribute("data-mode", "pausado");
  const x0 = await scrollX(page);
  await page.mouse.wheel(400, 0);                                           // dos dedos en horizontal
  await expect.poll(() => scrollX(page)).toBeGreaterThan(x0 + 100);
  const y0 = await page.evaluate(() => window.scrollY);
  // bucle hacia atrás: un desplazamiento nativo que llega al principio sigue por la copia
  await tape.evaluate((e) => { e.scrollLeft = 0; });
  await expect.poll(() => scrollX(page)).toBeGreaterThan(0);
  let x1 = -1;                                                              // quieto (sin animación de la rueda)
  await expect.poll(async () => { const v = await scrollX(page); const same = v === x1; x1 = v; return same; }).toBe(true);
  await page.mouse.wheel(0, 300);                                           // rueda vertical sobre el cintillo
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(y0);
  expect(await scrollX(page)).toBe(x1);                                     // no se la traga el cintillo
});

test("con «reducir movimiento», sin animación: fila deslizable con imán y sin copia", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/v2");
  await expect(page.getByTestId("ticker-item")).toHaveCount(LIST_SIZE, { timeout: 30_000 });
  const tape = page.getByTestId("ticker");
  await expect(tape).toHaveAttribute("data-mode", "reducido");
  await expect(page.locator(".run[aria-hidden=true]")).toHaveCount(0);
  const css = await tape.evaluate((e) => ({ ox: getComputedStyle(e).overflowX, snap: getComputedStyle(e).scrollSnapType }));
  expect(css).toEqual({ ox: "auto", snap: "x mandatory" });
  // P8b: sin avance automático
  const x0 = await tape.evaluate((e) => e.scrollLeft);
  await page.waitForTimeout(1500);
  expect(await tape.evaluate((e) => e.scrollLeft)).toBe(x0);
  // v4 cintillo: tampoco en pantallas táctiles (sin pista movida por transform)
  expect(await tape.evaluate((e) => [e.classList.contains("tx"), getComputedStyle(e.querySelector(".track")!).transform]))
    .toEqual([false, "none"]);
  // V6b: y sin bucle de fotogramas (requestAnimationFrame) que no hace nada
  const frames = await page.evaluate(() => new Promise<number>((res) => {
    let n = 0;
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = (cb) => { n++; return raf(cb); };
    setTimeout(() => res(n), 1000);
  }));
  expect(frames).toBeLessThan(5);
  await tape.evaluate((e) => { e.scrollLeft = 400; });
  expect(await tape.evaluate((e) => e.scrollLeft)).toBeGreaterThan(0);
});

/** «▲ 1.92%» / «▼ 5.63%» como la tarjeta (tickerModel.changeLabel). */
const chg = (c: number) => `${c > 0 ? "▲ " : c < 0 ? "▼ " : ""}${(Math.abs(c) * 100).toFixed(2)}%`;

test("P8b: el periodo cambia la lista, las gráficas y la variación; cada % es el de su lista", async ({ page, isMobile }) => {
  test.skip(isMobile, "el mismo cálculo en móvil");
  await page.goto("/v2");
  await stripReady(page);
  // la API, en el replay (con el build servido por el backend es el mismo origen y el mismo puerto)
  const api = await (await page.request.get(`http://localhost:${process.env.REPLAY_PORT || 8767}/api/v2/trending`)).json();
  const aapl = page.locator("[data-testid=ticker-item][data-symbol=AAPL]");
  const path1d = await aapl.locator("[data-testid=spark] .spark-line").getAttribute("d");
  for (const p of ["1D", "1S", "1M", "6M"]) {
    await page.getByTestId(`period-${p}`).click();
    await expect(page.getByTestId(`period-${p}`)).toHaveAttribute("aria-pressed", "true");
    const info = api.data.periods[p];
    const [y, m, d] = (info.from as string).split("-").map(Number);
    const mon = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"][m - 1];
    await expect(page.getByTestId("ticker-context")).toContainText(`Más negociadas en ${info.label} (del ${d}-${mon}-${y} al `);
    const list = api.data.lists[p].most_traded as Array<{ symbol: string; change_pct: number }>;
    await expect(page.getByTestId("ticker-item")).toHaveCount(list.length);
    await expect(page.getByTestId("ticker-item").first()).toHaveAttribute("data-symbol", list[0].symbol);
    for (const x of list) {     // el % de cada tarjeta es exactamente el que ordena su lista
      await expect(page.locator(`[data-testid=ticker-item][data-symbol="${x.symbol}"] .tk-chg`)).toHaveText(chg(x.change_pct));
    }
  }
  await expect(page.getByTestId("ticker-item").getByTestId("spark")).toHaveCount(LIST_SIZE, { timeout: 30_000 });
  expect(await aapl.locator("[data-testid=spark] .spark-line").getAttribute("d")).not.toBe(path1d);
});

test("P8b: «Bajan más · 6 meses» solo trae valores que bajan, y «Suben más» solo los que suben", async ({ page }) => {
  await page.goto("/v2");
  await stripReady(page);
  await page.getByTestId("period-6M").click();
  await page.getByTestId("list-losers").click();
  await expect(page.getByTestId("ticker-context")).toContainText(/^Bajan más en 6 meses \(del \d+-[a-z]{3}-\d{4} al 16-oct-2026\)/);
  for (const t of await page.getByTestId("ticker-item").locator(".tk-chg").allTextContents()) expect(t).toMatch(/^▼ /);
  await page.getByTestId("list-gainers").click();
  for (const t of await page.getByTestId("ticker-item").locator(".tk-chg").allTextContents()) expect(t).toMatch(/^▲ /);
  // el grupo de listas se llama «Listas» y el periodo, «Periodo» (uno solo para las listas y las gráficas)
  await expect(page.locator(".fgroup-day .glabel")).toHaveText("Listas");
  await expect(page.locator(".fgroup-period .glabel")).toHaveText("Periodo");
});

test("cambiar de lista o de sector cambia el cintillo y la línea de contexto", async ({ page }) => {
  await page.goto("/v2");
  await stripReady(page);
  await page.getByTestId("list-losers").click();
  await expect(page.getByTestId("list-losers")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("ticker-context")).toContainText(/^Bajan más en 1 día \(del/);
  await expect(page.getByTestId("ticker-item").first().locator(".tk-chg")).toContainText("▼");
  await page.getByTestId("sector-Energy").click();
  await expect(page.getByTestId("list-losers")).toHaveAttribute("aria-pressed", "false");    // una sola selección
  await expect(page.getByTestId("ticker-context")).toContainText(/^Energía, las más negociadas del sector, en 1 día \(del/);
  await expect(page.getByTestId("ticker-item").first()).toHaveAttribute("data-symbol", "XOM");
  // «Más ▾»: menú con los otros tres sectores
  await page.getByTestId("sector-more").click();
  const menu = page.getByRole("menu", { name: "Más sectores" });
  await expect(menu.getByRole("menuitemradio")).toHaveText(["Materiales", "Servicios públicos", "Inmobiliario"]);
  await menu.getByRole("menuitemradio", { name: "Inmobiliario" }).click();
  await expect(page.getByTestId("sector-more")).toContainText("Inmobiliario");
  await expect(page.getByTestId("ticker-context")).toContainText(/^Inmobiliario, las más negociadas del sector,/);
});

test("teclado: chips, menú y foco en los valores del cintillo", async ({ page, isMobile }) => {
  test.skip(isMobile, "teclado: en escritorio y tableta");
  await page.goto("/v2");
  await stripReady(page);
  await page.getByTestId("list-gainers").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("list-gainers")).toHaveAttribute("aria-pressed", "true");
  await page.getByTestId("sector-more").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("menuitemradio", { name: "Materiales" })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("menuitemradio", { name: "Servicios públicos" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("menu")).toHaveCount(0);
  await expect(page.getByTestId("sector-more")).toBeFocused();
  // El primer valor del cintillo recibe el foco: el cintillo deja de moverse, el valor queda a la vista y con su marco.
  await page.getByTestId("ticker-item").first().focus();
  await expect(page.getByTestId("ticker")).toHaveAttribute("data-mode", "pausado");
  const first = page.getByTestId("ticker-item").first();
  await expect(first).toBeInViewport();
  expect(await first.evaluate((e) => getComputedStyle(e).outlineStyle)).toBe("solid");
  await page.keyboard.press("Tab");
  await expect(page.getByTestId("ticker-item").nth(1)).toBeFocused();
  await expect(page.getByTestId("ticker-item").nth(1)).toBeInViewport();
  // P8b: flechas con el foco: la siguiente y la anterior, a la vista (el cintillo se desplaza)
  const x0 = await scrollX(page);
  for (let i = 0; i < 6; i++) await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("ticker-item").nth(7)).toBeFocused();
  await expect(page.getByTestId("ticker-item").nth(7)).toBeInViewport();
  expect(await scrollX(page)).toBeGreaterThan(x0);
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByTestId("ticker-item").nth(6)).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/v2\/[A-Z.\-]+\/?$/);
});

test("sin desplazamiento horizontal y el periodo siempre a la vista (375 px)", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/v2");
  await stripReady(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
  const per = page.getByRole("group", { name: "Periodo de las listas y las gráficas" });
  for (const p of ["1D", "1S", "1M", "6M"]) {
    const b = await page.getByTestId(`period-${p}`).boundingBox();
    expect(b!.x).toBeGreaterThanOrEqual(0);
    expect(b!.x + b!.width).toBeLessThanOrEqual(375);
    expect(b!.height).toBeGreaterThanOrEqual(44);                              // objetivo táctil
  }
  await expect(per).toBeVisible();
  // Las filas de chips se deslizan dentro de su fila, no la página.
  // v4 móvil (PM): la etiqueta encima; lo que se desliza es la fila de fichas, no el grupo
  const sectors = page.getByRole("group", { name: "Sectores" }).locator(".fchips");
  expect(await sectors.evaluate((e) => e.scrollWidth > e.clientWidth && getComputedStyle(e).overflowX === "auto")).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
});

test("un sector con pocos valores: chip deshabilitado con su motivo, sin ocultarlo", async ({ page }) => {
  await page.route("**/api/v2/trending*", async (r) => {
    const res = await r.fetch();
    const j = await res.json();
    if (j.data?.sector_status) {
      j.data.sector_status["1D"].Energy = { ...j.data.sector_status["1D"].Energy, available: false,
        reason: "solo 4 valores del sector con cotización en el periodo (mínimo 6)" };
    }
    await r.fulfill({ json: j });
  });
  await page.goto("/v2");
  await expect(page.getByTestId("ticker-item")).toHaveCount(LIST_SIZE, { timeout: 30_000 });
  const chip = page.getByTestId("sector-Energy");
  await expect(chip).toBeVisible();
  await expect(chip).toHaveAttribute("aria-disabled", "true");
  await expect(chip).toHaveAttribute("title", "Energía: solo 4 valores del sector con cotización en el periodo (mínimo 6)");
  await chip.click({ force: true });                 // aria-disabled: Playwright no lo pulsa si no se le fuerza
  await expect(page.getByTestId("list-most_traded")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("ticker-context")).toContainText(/^Más negociadas/);
});

test("buscar «apple» → AAPL → /v2/AAPL (teclado)", async ({ page }) => {
  await page.goto("/v2");
  const box = page.getByRole("combobox", { name: "Buscar empresa o ticker" });
  await box.fill("apple");
  const first = page.getByRole("option").first();
  await expect(first).toContainText("Apple Inc.");
  await expect(first).toContainText("AAPL");
  await expect(first).toContainText("Nasdaq");
  await box.press("ArrowDown");
  await expect(first).toHaveAttribute("aria-selected", "true");
  await box.press("Enter");
  await expect(page).toHaveURL(/\/v2\/AAPL\/?$/);
  await expect(page.getByTestId("company-name")).toHaveText("Apple Inc.", { timeout: 30_000 });
});

test("Enter con un ticker exacto va a su página", async ({ page }) => {
  await page.goto("/v2");
  const box = page.getByRole("combobox", { name: "Buscar empresa o ticker" });
  await box.fill("jpm");
  await expect(page.getByRole("option").first()).toContainText("JPM");
  await box.press("Enter");
  await expect(page).toHaveURL(/\/v2\/JPM\/?$/);
});

test("el buscador de la barra general también funciona", async ({ page, isMobile }) => {
  test.skip(isMobile, "en el móvil la barra no lleva buscador: se usa el de la portada");
  await page.goto("/v2/AAPL");
  const box = page.getByRole("combobox", { name: "Buscar empresa o ticker" });
  await box.fill("microsoft");
  await expect(page.getByRole("option").first()).toContainText("MSFT");
  await page.getByRole("option").first().click();
  await expect(page).toHaveURL(/\/v2\/MSFT\/?$/);
});

test("cintillo simétrico y sin huecos", async ({ page }) => {
  await page.goto("/v2");
  await stripReady(page);
  expect(await symmetryProblems(page)).toEqual([]);
  const heights = await page.locator(".run:not([aria-hidden]) .tk-item").evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().height)));
  expect(Math.max(...heights) - Math.min(...heights)).toBeLessThanOrEqual(1);
});

test("calculando: esqueleto del cintillo y aviso para lectores de pantalla", async ({ page }) => {
  await page.route("**/api/v2/trending*", (r) => r.fulfill({ json: { status: "calculando", data: null, refreshing: true, reason: null, poll_s: 5 } }));
  await page.goto("/v2");
  await expect(page.locator(".ticker [role=status]")).toHaveText("Calculando los valores de la sesión…");
  await expect(page.locator(".tape.skeleton")).toBeVisible();
});

test("sin dato: el motivo en una línea", async ({ page }) => {
  await page.route("**/api/v2/trending*", (r) => r.fulfill({ json: { status: "sin_dato", data: null, refreshing: false, reason: "no se pudieron calcular las tendencias: Yahoo no devolvió cotizaciones del universo (6 de 6 lotes fallidos)", poll_s: 5 } }));
  await page.goto("/v2");
  await expect(page.getByText("No hay valores de la sesión ahora mismo. No se pudieron calcular las tendencias: Yahoo no devolvió cotizaciones del universo (6 de 6 lotes fallidos).")).toBeVisible();
  await expect(page.locator(".tape.skeleton")).toHaveCount(0);
});

test("Yahoo caído para las mini-gráficas: cada valor sin gráfica y la portada sigue", async ({ page }) => {
  await page.route("**/api/v2/sparklines**", async (r) => {
    const u = new URL(r.request().url());
    const items = Object.fromEntries((u.searchParams.get("symbols") ?? "").split(",").map((s) => [s, { status: "sin_dato", reason: "Yahoo no respondió (ConnectionError)" }]));
    await r.fulfill({ json: { period: "1D", label: "1 día", interval: "5m", as_of: null, items } });
  });
  await page.goto("/v2");
  await expect(page.getByTestId("ticker-item")).toHaveCount(LIST_SIZE, { timeout: 30_000 });
  await expect(page.getByTestId("ticker-item").getByTestId("spark-empty")).toHaveCount(LIST_SIZE);
  await expect(page.locator("[data-testid=ticker-item][data-symbol=AAPL] .tk-chg")).toHaveText("▲ 0.43%");   // la de la sesión
  await expect(page.getByRole("combobox", { name: "Buscar empresa o ticker" })).toBeEnabled();
});

for (const theme of ["light", "dark"] as const) {
  test(`portada sin infracciones de accesibilidad graves · ${theme}`, async ({ page }) => {
    await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
    await page.goto("/v2");
    await stripReady(page);
    await page.getByRole("combobox", { name: "Buscar empresa o ticker" }).fill("apple");
    await expect(page.getByRole("option").first()).toBeVisible();
    const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    const serious = res.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
  });
}

test("P8: todas las tarjetas del cintillo miden lo mismo y tienen su línea inferior", async ({ page }) => {
  await page.goto("/v2");
  await stripReady(page);
  const cards = page.getByTestId("ticker-item");
  // Cada tarjeta lleva su línea de abajo: «Calidad N · Precio N» o «Ver análisis →».
  await expect(cards.locator(".tk-eng")).toHaveCount(LIST_SIZE);
  for (const t of await cards.locator(".tk-eng").allTextContents()) {
    expect(t).toMatch(/^(Calidad \d+ · Precio \d+|Ver análisis →)$/);
  }
  const heights = await cards.evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().height)));
  expect(new Set(heights).size, `altos: ${[...new Set(heights)].join(", ")}`).toBe(1);
});

test("P8: el texto de ayuda del buscador cabe (corto en móvil, largo en escritorio)", async ({ page, isMobile }, info) => {
  await page.goto("/v2");
  const box = page.getByRole("combobox", { name: "Buscar empresa o ticker" });
  const narrow = (page.viewportSize()?.width ?? 0) < 768;
  await expect(box).toHaveAttribute("placeholder",
    narrow ? "Empresa o ticker" : "Buscar empresa o ticker… (Apple, AAPL, Coca-Cola)");
  // El texto de ayuda no se corta: su ancho cabe en el del campo (menos el relleno).
  const fits = await box.evaluate((el: HTMLInputElement) => {
    const cs = getComputedStyle(el);
    const ctx = document.createElement("canvas").getContext("2d")!;
    ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const room = el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    return ctx.measureText(el.placeholder).width <= room;
  });
  expect(fits, `${info.project.name}${isMobile ? " (móvil)" : ""}`).toBe(true);
});

test("V6b: si el servidor no devuelve la gráfica de un valor, no se vuelve a pedir en bucle", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "una vez basta");
  const calls: string[] = [];
  await page.route("**/api/v2/sparklines*", async (r) => {
    calls.push(r.request().url());
    const j = await (await r.fetch()).json();
    delete j.items.MU;                                                    // el servidor «olvida» un valor
    await r.fulfill({ json: j });
  });
  await page.goto("/v2");
  await expect(page.getByTestId("ticker-item")).toHaveCount(LIST_SIZE, { timeout: 30_000 });
  await page.waitForTimeout(2000);
  expect(calls).toHaveLength(1);
  await expect(page.locator("[data-testid=ticker-item][data-symbol=MU] [data-testid=spark-empty]")).toHaveCount(1);
});

test("portada guardada en el navegador: al volver se ve al momento, con su hora, hasta que llega la del servidor", async ({ page }) => {
  // Primera visita: la portada del servidor (listas de 1D y sus mini-gráficas) queda guardada en este navegador.
  await page.goto("/v2");
  await stripReady(page);
  await expect.poll(() => page.evaluate(() => {
    const c = JSON.parse(localStorage.getItem("finanzer.v2.portada") ?? "null");
    return c ? Object.keys(c.sparks).length : 0;
  })).toBe(LIST_SIZE);
  // Vuelve con el servidor recién arrancado («calculando»): la guardada, sin esqueleto, con sus mini-gráficas y su hora.
  let calculating = true;
  await page.route("**/api/v2/trending*", (r) => (calculating
    ? r.fulfill({ json: { status: "calculando", data: null, refreshing: true, reason: null, poll_s: 1 } })
    : r.fallback()));
  // las mini-gráficas del servidor no llegan mientras calcula: las que se ven son las guardadas
  await page.route("**/api/v2/sparklines*", async (r) => {
    while (calculating) await new Promise((res) => setTimeout(res, 100));
    await r.fallback();
  });
  await page.reload();
  await expect(page.getByTestId("ticker-item")).toHaveCount(LIST_SIZE);
  await expect(page.getByTestId("ticker-item").getByTestId("spark")).toHaveCount(LIST_SIZE);
  await expect(page.locator(".tape.skeleton")).toHaveCount(0);
  await expect(page.getByTestId("ticker-cached")).toHaveText(
    /^Guardado en este navegador: datos (de las|del .+ a las) \d\d:\d\d \(Nueva York\)\. Actualizando…$/);
  // Llega la del servidor: manda ella y el aviso se va.
  calculating = false;
  await expect(page.getByTestId("ticker-cached")).toHaveCount(0, { timeout: 15_000 });
  await expect(page.getByTestId("ticker-item")).toHaveCount(LIST_SIZE);
});
