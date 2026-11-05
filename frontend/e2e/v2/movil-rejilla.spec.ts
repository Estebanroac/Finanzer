import { test, expect, type Page } from "@playwright/test";

// v4 móvil (PM; el usuario en el iPhone 17 Pro Max: «desalineado, terrible organización y distribución»): una sola
// rejilla. Todos los bloques en el mismo margen; las filas deslizables empiezan en él, encajan con imán y dejan asomar
// la siguiente sin cortar la primera; las tablas numéricas, con la cabecera una vez y las cifras en columna; las filas
// con barra, todas iguales; lo que se toca, ≥ 44 px; nada bajo la barra inferior al final de la página.
test.beforeEach(({ page }) => {
  test.skip((page.viewportSize()?.width ?? 0) >= 768, "rejilla de móvil");
});

const PX = 1;   // redondeo del navegador
type Box = { left: number; right: number; top: number; bottom: number; width: number; height: number };
const box = (page: Page, sel: string): Promise<Box> => page.locator(sel).first().evaluate((e) => {
  const r = e.getBoundingClientRect();
  return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height };
});
const gutter = (page: Page) => page.locator(".fz2").first().evaluate((e) =>
  parseFloat(getComputedStyle(e).getPropertyValue("--gutter")) || parseFloat(getComputedStyle(e.querySelector(".wrap")!).paddingLeft));
const noHorizontalScroll = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

test("portada: todos los bloques en el mismo margen y la primera tarjeta del cintillo entera, en él", async ({ page }) => {
  await page.goto("/v2");
  await page.getByTestId("ticker").waitFor({ timeout: 60_000 });
  expect(await noHorizontalScroll(page)).toBe(0);
  const vw = page.viewportSize()!.width;
  const g = await page.locator(".fz2 .wrap").first().evaluate((e) => parseFloat(getComputedStyle(e).paddingLeft));
  for (const sel of [".home-hero input", ".fgroup-day .chip", ".per", ".fgroup-sectors .chip", ".trust-card"]) {
    const b = await box(page, sel);
    expect(Math.abs(b.left - g), `${sel} empieza en el margen`).toBeLessThanOrEqual(PX);
  }
  for (const sel of [".home-hero input", ".per", ".trust-card"]) {
    const b = await box(page, sel);
    expect(Math.abs(vw - b.right - g), `${sel} acaba en el margen`).toBeLessThanOrEqual(PX);
  }
  // los sectores se deslizan en una fila sin empujar la página: el primero en el margen
  const sec = page.locator(".fgroup-sectors .fchips");
  expect(await sec.evaluate((e) => e.scrollWidth > e.clientWidth)).toBe(true);
  // el cintillo: la primera tarjeta empieza en el margen (descontado lo que ya avanzó solo), se ve entera y la siguiente asoma
  const tape = page.getByTestId("ticker");
  const m = await tape.evaluate((e) => {
    const shift = e.scrollLeft - new DOMMatrix(getComputedStyle(e.querySelector(".track")!).transform).m41;
    const [a, b] = [...e.querySelectorAll(".tk-cell")].map((c) => c.getBoundingClientRect());
    return { left: a.left + shift, right: a.right + shift, next: b.left + shift };
  });
  expect(Math.abs(m.left - g)).toBeLessThanOrEqual(PX);
  expect(m.right).toBeLessThanOrEqual(vw);
  expect(m.next).toBeLessThan(vw);
});

// v4 (usuario: «esas dos cosas quítalas, que no estén»): sin los rótulos «Listas» y «Sectores», sin hueco en su lugar
// (buscador, listas, periodo, sectores y cintillo al mismo paso) y con su nombre para el lector de pantalla
test("portada: sin rótulos de los grupos, mismo aire entre filas y los grupos con nombre", async ({ page }) => {
  await page.goto("/v2");
  await page.getByTestId("ticker").waitFor({ timeout: 60_000 });
  for (const l of await page.locator(".glabel").all()) await expect(l).toBeHidden();
  await expect(page.getByRole("group", { name: "Listas", exact: true })).toBeVisible();
  await expect(page.getByRole("group", { name: "Sectores", exact: true })).toBeVisible();
  const gaps = await page.evaluate(() => {
    const r = (s: string) => document.querySelector(s)!.getBoundingClientRect();
    return ([[".home-hero input", ".fgroup-day .fchips"], [".fgroup-day .fchips", ".per"], [".per", ".fgroup-sectors .fchips"],
      [".fgroup-sectors .fchips", ".tape"]] as const).map(([a, b]) => Math.round(r(b).top - r(a).bottom));
  });
  expect(Math.max(...gaps) - Math.min(...gaps), `huecos ${gaps}`).toBeLessThanOrEqual(PX);
});

test("final de la página: lo último queda por encima del borde inferior, con aire", async ({ page }) => {
  for (const path of ["/v2", "/v2/NVDA/conclusion"]) {
    await page.goto(path);
    await page.waitForSelector(path === "/v2" ? "[data-testid=ticker]" : ".depth-body .dsec", { timeout: 60_000 });
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await page.waitForTimeout(300);
    const pad = await page.locator("main").evaluate((e) => parseFloat(getComputedStyle(e).paddingBottom));
    expect(pad, `${path}: margen inferior del main`).toBeGreaterThanOrEqual(32);
  }
});

test("tablas numéricas por periodo: cabecera una sola vez y cifras en columna", async ({ page }) => {
  for (const [path, sel] of [["/v2/NVDA/accion", "[data-testid=returns-by-period]"], ["/v2/NVDA/negocio", "[data-testid=segments-axis] table"],
    ["/v2/NVDA/negocio", "[data-testid=annual]"]] as const) {
    await page.goto(path);
    const t = page.locator(sel).first();
    await t.waitFor({ timeout: 60_000 });
    const r = await t.evaluate((t: HTMLTableElement) => {
      const head = t.tHead!.getBoundingClientRect();
      const labelled = [...t.querySelectorAll("td[data-label]")].some((c) => getComputedStyle(c, "::before").content !== "none"
        && getComputedStyle(c, "::before").display !== "none");
      // borde derecho de cada columna numérica, fila a fila (las filas de nota ocupan toda la fila)
      const rows = [...t.tBodies[0].rows].filter((r) => !r.classList.contains("row-note") && r.cells.length > 2);
      const rights = rows.map((r) => [...r.cells].slice(1).map((c) => Math.round(c.getBoundingClientRect().right)));
      const aligned = rights.every((rr) => rr.every((x, i) => Math.abs(x - rights[0][i]) <= 1));
      return { headVisible: head.height > 8, labelled, aligned, rows: rows.length };
    });
    expect(r.headVisible, `${sel}: cabecera visible`).toBe(true);
    expect(r.labelled, `${sel}: sin etiqueta repetida en cada cifra`).toBe(false);
    expect(r.aligned, `${sel}: cifras en columna`).toBe(true);
    expect(await noHorizontalScroll(page), `${path}: sin desplazamiento de página`).toBe(0);
  }
});

test("filas con barra: todas las barras miden lo mismo y todas las filas de la escalera tienen la misma altura", async ({ page }) => {
  await page.goto("/v2/NVDA/negocio");
  const ladder = page.locator(".ladder").first();
  await ladder.waitFor({ timeout: 60_000 });
  const m = await ladder.evaluate((u) => {
    const rows = [...u.querySelectorAll(":scope > li:not([data-missing])")];
    return { tracks: rows.map((li) => Math.round(li.querySelector(".seg-track")!.getBoundingClientRect().width)),
      heights: rows.map((li) => Math.round(li.getBoundingClientRect().height)) };
  });
  expect(new Set(m.tracks).size, `barras ${m.tracks}`).toBe(1);
  expect(Math.max(...m.heights) - Math.min(...m.heights), `alturas ${m.heights}`).toBeLessThanOrEqual(PX);
  const segs = await page.locator("[data-testid=segments-axis] .segbars").first().evaluate((u) =>
    [...u.querySelectorAll(".seg-track")].map((t) => Math.round(t.getBoundingClientRect().width)));
  expect(new Set(segs).size, `segmentos ${segs}`).toBe(1);
});

test("lo que se toca mide ≥ 44 px (área táctil, sin cambiar su aspecto) y el «?» no se separa de su etiqueta", async ({ page }) => {
  await page.goto("/v2/NVDA");
  await page.locator(".company-header").first().waitFor({ timeout: 60_000 });
  for (const sel of [".topbar .actions .btn:visible", ".company-header .tip-btn", "[data-testid=bd-link]"]) {
    const el = page.locator(sel).first();
    const ok = await el.evaluate((e) => {
      const r = e.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2, half = 21;
      return [[cx, cy - half], [cx, cy + half]].every(([x, y]) => { const hit = document.elementFromPoint(x, y); return !!hit && (hit === e || e.contains(hit)); });
    });
    expect(ok, `${sel}: 44 px de alto al tacto`).toBe(true);
  }
  // cada «?» de las puntuaciones va pegado a la última palabra de su etiqueta
  const glued = await page.locator(".company-header .score .eyebrow").evaluateAll((els) => els.every((e) => {
    const tip = e.querySelector(".tip-btn");
    return !tip || !!tip.closest(".nobr");
  }));
  expect(glued).toBe(true);
});

test("Cifras clave de dos en dos", async ({ page }) => {
  await page.goto("/v2/NVDA/empresa");
  const tiles = page.locator(".tiles.flow").first().locator(".tile");
  await tiles.first().waitFor({ timeout: 60_000 });
  const [a, b] = [await tiles.nth(0).boundingBox(), await tiles.nth(1).boundingBox()];
  expect(Math.abs(a!.y - b!.y)).toBeLessThanOrEqual(PX);
  expect(Math.abs(a!.width - b!.width)).toBeLessThanOrEqual(PX);
});

// v4 (PM; V1 a 375 px): MC.PA cotiza en euros y «EUR 397.00» con su «?» no cabía en media fila: la ficha del precio
// pasaba a dos líneas y la cifra de «Market cap», su vecina, bajaba 34 px. Regla general: la cifra nunca se parte, el «?»
// va con la etiqueta y, si una cifra no cabe, su ficha ocupa la fila entera (sin dejar sola a ninguna otra).
const rowsOk = (page: Page) => page.locator(".tiles.flow").first().evaluate((g) => {
  const tiles = [...g.querySelectorAll<HTMLElement>(":scope > .tile")];
  const gw = g.getBoundingClientRect().width;
  const out = tiles.map((t) => {
    const r = t.getBoundingClientRect(), v = t.querySelector<HTMLElement>(".tile-value")!, l = t.querySelector<HTMLElement>(".tile-label")!;
    const vr = v.getBoundingClientRect(), lr = l.getBoundingClientRect();
    const lh = parseFloat(getComputedStyle(v).lineHeight);
    return { label: l.textContent, top: Math.round(r.top), full: r.width > gw * 0.75, valueTop: vr.top, valueLines: Math.round(vr.height / lh),
      gap: vr.top - lr.bottom, tipInLabel: !t.querySelector(".tip-btn") || !!l.querySelector(".tip-btn"),
      fits: (() => { const rg = document.createRange(); rg.selectNodeContents(v); return rg.getBoundingClientRect().right <= r.right + 0.5; })() };
  });
  const byRow = new Map<number, typeof out>();
  for (const t of out) byRow.set(t.top, [...(byRow.get(t.top) ?? []), t]);
  return { tiles: out, rows: [...byRow.values()] };
});

for (const path of ["/v2/MC.PA/empresa", "/v2/MC.PA"]) {
  test(`cifras clave en otra moneda (${path}): la cifra en una línea, el «?» con la etiqueta y sin huecos`, async ({ page }) => {
    await page.goto(path);
    const grid = page.locator(".tiles.flow").first();
    await grid.waitFor({ timeout: 60_000 });
    await grid.scrollIntoViewIfNeeded();
    await page.evaluate(() => document.fonts.ready);
    await expect(grid.locator(".tile-value").first()).toContainText("EUR");
    const { tiles, rows } = await rowsOk(page);
    for (const t of tiles) {
      expect(t.valueLines, `${t.label}: la cifra en una línea`).toBe(1);
      expect(t.fits, `${t.label}: la cifra cabe en su ficha`).toBe(true);
      expect(t.tipInLabel, `${t.label}: el «?» va con la etiqueta`).toBe(true);
    }
    for (const r of rows) {
      expect(r.length === 2 || r[0].full, `fila sin hueco: ${r.map((t) => t.label)}`).toBe(true);
      if (r.length === 2) {
        expect(Math.abs(r[0].valueTop - r[1].valueTop), `cifras a la misma altura: ${r.map((t) => t.label)}`).toBeLessThanOrEqual(PX);
        for (const t of r) expect(t.gap, `${t.label}: de la etiqueta a la cifra`).toBeLessThanOrEqual(24);
      }
    }
    expect(await noHorizontalScroll(page)).toBe(0);
  });
}

test("una cifra larga (JPY de diez cifras) no se parte: su ficha ocupa la fila entera y las demás siguen de dos en dos", async ({ page }) => {
  await page.goto("/v2/MC.PA/empresa");
  const grid = page.locator(".tiles.flow").first();
  await grid.waitFor({ timeout: 60_000 });
  await grid.locator(".tile-value").nth(1).evaluate((v) => { v.textContent = "JPY 1,234,567,890.00"; });
  const vp = page.viewportSize()!;
  await page.setViewportSize({ width: vp.width - 1, height: vp.height });   // vuelve a medir (ResizeObserver)
  await expect.poll(async () => (await rowsOk(page)).tiles[1].full).toBe(true);
  const { tiles, rows } = await rowsOk(page);
  expect(tiles[1].valueLines).toBe(1);
  expect(tiles[1].fits).toBe(true);
  for (const r of rows) expect(r.length === 2 || r[0].full, `fila sin hueco: ${r.map((t) => t.label)}`).toBe(true);
  expect(await noHorizontalScroll(page)).toBe(0);
});
