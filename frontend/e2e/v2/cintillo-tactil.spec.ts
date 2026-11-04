import { test, expect, type Page } from "@playwright/test";

// v4 cintillo (PM; el usuario en el iPhone 17 Pro Max: «el cintillo no se mueve solo en el iPhone. Parece que se
// desplaza por secciones, por acción, y no de manera continua como en la página»). En pantallas táctiles: avance
// continuo (transform sobre la pista, sin imán), el dedo lo para y lo arrastra 1:1 y arranca ~2,5 s después desde donde
// quedó; fuera de la vista, quieto; sin bucle con «reducir movimiento» (home.spec).
// v4.1 (el usuario: «pasa como a un lugar en el que deba estar… quiero algo que se mueva sin restricciones»): al soltar
// no hay imán. En reposo, se queda donde quedó; con velocidad, inercia libre que decae (como el scroll de iOS) y para
// donde pare, sin acabar en el margen de una tarjeta.
test.skip(({ isMobile }) => !isMobile, "pantallas táctiles");

const RESUME_MS = 2500;   // useCarousel.TOUCH_RESUME_MS

/** Lo que ha avanzado la pista (px). */
const pos = (page: Page) => page.getByTestId("ticker").evaluate((e) =>
  e.scrollLeft - new DOMMatrix(getComputedStyle(e.querySelector(".track")!).transform).m41);
/** Un dedo sobre el cintillo (eventos de puntero táctiles, como los manda Safari iOS). */
const finger = (page: Page, type: "pointerdown" | "pointermove" | "pointerup", x: number, y: number) =>
  page.evaluate(([type, x, y]) => {
    const t = document.elementFromPoint(x as number, y as number)!;
    t.dispatchEvent(new PointerEvent(type as string, { pointerId: 7, pointerType: "touch", isPrimary: true, bubbles: true,
      cancelable: true, clientX: x as number, clientY: y as number, button: 0, buttons: type === "pointerup" ? 0 : 1 }));
  }, [type, x, y] as const);

/** Distancia (px) de la tarjeta más cercana al margen del cintillo: 0 si una tarjeta queda justo en él (el imán). */
const offMargin = (page: Page) => page.getByTestId("ticker").evaluate((e) => {
  const g = parseFloat(getComputedStyle(e).paddingLeft), left = e.getBoundingClientRect().left;
  return Math.min(...[...e.querySelectorAll(".tk-cell")].map((c) => Math.abs(c.getBoundingClientRect().left - left - g)));
});
/** Cada fotograma durante `n` fotogramas: la posición de la pista. */
const frames = (page: Page, n: number) => page.getByTestId("ticker").evaluate((e, n) => new Promise<number[]>((res) => {
  const t = e.querySelector(".track")!, out: number[] = [];
  const f = (k: number) => requestAnimationFrame(() => { out.push(-new DOMMatrix(getComputedStyle(t).transform).m41); if (k) f(k - 1); else res(out); });
  f(n);
}), n);

async function ready(page: Page) {
  await page.goto("/v2");
  const tape = page.getByTestId("ticker");
  await expect(page.getByTestId("ticker-item").first()).toBeVisible({ timeout: 60_000 });
  await expect(tape).toHaveClass(/\btx\b/);
  await tape.evaluate((e) => e.scrollIntoView({ block: "center" }));
  return tape;
}

test("avanza solo y en continuo, por la GPU y sin imán", async ({ page }) => {
  const tape = await ready(page);
  await expect(tape).toHaveAttribute("data-mode", "animado");
  const css = await tape.evaluate((e) => ({ snap: getComputedStyle(e).scrollSnapType, touch: getComputedStyle(e).touchAction,
    will: getComputedStyle(e.querySelector(".track")!).willChange }));
  expect(css).toEqual({ snap: "none", touch: "pan-y", will: "transform" });
  // fotograma a fotograma: siempre hacia delante y sin paradas (el avance por tarjetas se quedaba quieto 4 s en cada una)
  const steps = await tape.evaluate((e) => new Promise<number[]>((res) => {
    const t = e.querySelector(".track")!;
    const x = () => -new DOMMatrix(getComputedStyle(t).transform).m41;
    const out: number[] = [];
    let prev = x();
    const f = (n: number) => requestAnimationFrame(() => { const v = x(); out.push(v - prev); prev = v; if (n) f(n - 1); else res(out); });
    f(60);
  }));
  // ~1 s: cada fotograma avanza algo (salvo el bucle, que vuelve una copia atrás) y nunca un salto
  expect(steps.filter((d) => d > 0).length).toBeGreaterThanOrEqual(steps.length - 2);
  expect(Math.max(...steps.filter((d) => d > 0))).toBeLessThan(8);
});

test("el dedo lo para y lo arrastra; soltado en reposo a media tarjeta, se queda ahí y, ~2,5 s después, sigue desde ahí", async ({ page }) => {
  const tape = await ready(page);
  const box = (await tape.boundingBox())!;
  const y = box.y + box.height / 2, x = box.x + box.width * 0.6;
  await finger(page, "pointerdown", x, y);
  await expect(tape).toHaveAttribute("data-mode", "pausado");
  const p0 = await pos(page);
  await page.waitForTimeout(600);
  expect(await pos(page), "quieto con el dedo apoyado").toBeCloseTo(p0, 0);
  // arrastre hacia la izquierda: la pista avanza lo mismo que el dedo (pasado el umbral de 10 px)
  for (let i = 1; i <= 8; i++) await finger(page, "pointermove", x - i * 20, y);
  // a media tarjeta: si el arrastre dejó una justo en el margen, unos px más (si no, no se distinguiría del imán)
  let end = x - 160;
  if (await offMargin(page) < 20) { end -= 40; await finger(page, "pointermove", end, y); }
  const dragged = await pos(page);
  expect(dragged - p0).toBeGreaterThan(120);
  await page.waitForTimeout(150);                                       // dedo quieto antes de soltar: sin inercia
  await finger(page, "pointerup", end, y);
  await expect(page).toHaveURL(/\/v2\/?$/);                             // soltar tras arrastrar no abre la tarjeta
  // se queda exactamente donde quedó: ni muelle ni tarjeta destino
  const still = await frames(page, 45);
  expect(Math.max(...still) - Math.min(...still), "quieto tras soltar en reposo").toBe(0);
  expect(await pos(page)).toBe(dragged);
  expect(await offMargin(page), "a media tarjeta (sin imán)").toBeGreaterThan(10);
  await expect(tape).toHaveAttribute("data-mode", "pausado");
  const settled = await pos(page);
  await page.waitForTimeout(RESUME_MS - 1000);
  expect(await pos(page), "aún quieto antes de ~2,5 s").toBeCloseTo(settled, 0);
  await expect(tape).toHaveAttribute("data-mode", "animado", { timeout: 3_000 });
  // reanuda desde donde quedó, sin saltos
  const resumed = await pos(page);
  expect(resumed - settled).toBeGreaterThanOrEqual(0);
  expect(resumed - settled).toBeLessThan(60);
  await expect.poll(() => pos(page)).toBeGreaterThan(resumed);
});

test("soltado con velocidad: sigue con inercia que decae, sin imán, y para donde pare", async ({ page }) => {
  const tape = await ready(page);
  const box = (await tape.boundingBox())!;
  const y = box.y + box.height / 2, x = box.x + box.width * 0.85;
  await finger(page, "pointerdown", x, y);
  // un lanzamiento: movimientos seguidos (sin pausa antes de soltar)
  for (let i = 1; i <= 10; i++) { await finger(page, "pointermove", x - i * 25, y); await page.waitForTimeout(16); }
  const released = await pos(page);
  await finger(page, "pointerup", x - 250, y);
  // tras soltar sigue avanzando, cada vez menos (decae), hasta pararse
  const glide = await frames(page, 30);
  const steps = glide.slice(1).map((v, i) => v - glide[i]).filter((d) => Math.abs(d) < 200);   // sin la vuelta del bucle
  expect(glide[0] - released, "sigue con la inercia del dedo").toBeGreaterThan(0);
  expect(steps.filter((d) => d > 0).length, "avanza en cada fotograma").toBeGreaterThanOrEqual(steps.length - 2);
  expect(steps.at(-1)!, "decae").toBeLessThan(steps[0]);
  await expect.poll(async () => { const f = await frames(page, 10); return Math.max(...f) - Math.min(...f); }, { timeout: 6_000 }).toBe(0);
  expect(await offMargin(page), "para donde pare, no en el margen de una tarjeta").toBeGreaterThan(1);
  await expect(tape).toHaveAttribute("data-mode", "pausado");
  await expect(page).toHaveURL(/\/v2\/?$/);
});

test("un toque sin arrastrar abre la tarjeta", async ({ page }) => {
  const tape = await ready(page);
  const box = (await tape.boundingBox())!;                              // se mueve: se toca donde esté
  await page.touchscreen.tap(box.x + box.width * 0.3, box.y + box.height / 2);
  await expect(page).toHaveURL(/\/v2\/[A-Z.\-]+\/?$/);
});

test("fuera de la vista, quieto (sin fotogramas); al volver, sigue desde donde estaba", async ({ page }) => {
  const tape = await ready(page);
  await expect(tape).toHaveAttribute("data-mode", "animado");
  // la portada del móvil es corta: espacio al final para que el cintillo salga de la vista
  await page.evaluate(() => { document.querySelector("main")!.append(Object.assign(document.createElement("div"), { style: "height:200vh" }));
    window.scrollTo(0, document.documentElement.scrollHeight); });
  await expect(tape).toHaveAttribute("data-mode", "pausado");
  const p0 = await pos(page);
  await page.waitForTimeout(1500);
  expect(await pos(page)).toBe(p0);
  await tape.evaluate((e) => e.scrollIntoView({ block: "center" }));
  await expect(tape).toHaveAttribute("data-mode", "animado");
  const p1 = await pos(page);
  expect(Math.abs(p1 - p0), "sin saltar lo que habría avanzado").toBeLessThan(60);
});
