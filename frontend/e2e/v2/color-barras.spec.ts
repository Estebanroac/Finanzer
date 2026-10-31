import { test, expect, type Page } from "@playwright/test";

// v4 (PM; el usuario: «a las barras que miden o indican una posición les hacen falta colores; todo es gris»). Regla:
// - con juicio, el marcador en el color del tramo donde cae (el tono lo da el motor) y siempre con su etiqueta;
// - sin juicio, posición en un degradado neutro (azul pizarra) y composición en una paleta categórica, nunca rojo/verde;
// - contraste ≥ 3:1 de cada marca o relleno con la superficie (gráficos, WCAG 1.4.11), en claro y en oscuro.
test.skip(({ browserName }) => browserName !== "chromium", "colores calculados: basta un motor");

const MIN_GRAPHIC = 3;
type RGB = [number, number, number];
const rgb = (s: string): RGB => (s.match(/[\d.]+/g) ?? []).slice(0, 3).map(Number) as RGB;
const lum = ([r, g, b]: RGB) => [r, g, b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; })
  .reduce((acc, v, i) => acc + v * [0.2126, 0.7152, 0.0722][i], 0);
const contrast = (a: string, b: string) => { const [x, y] = [lum(rgb(a)), lum(rgb(b))].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
/** El color de un token de /v2 (custom property de .fz2) ya resuelto. */
const token = (page: Page, name: string) => page.evaluate((n) => {
  const probe = document.createElement("i");
  probe.style.color = `var(${n})`;
  document.querySelector(".fz2")!.appendChild(probe);
  const c = getComputedStyle(probe).color; probe.remove(); return c;
}, name);
const bg = (page: Page, sel: string) => page.locator(sel).first().evaluate((e) => getComputedStyle(e).backgroundColor);
const TONE_TOKEN: Record<string, string> = { good: "--good", warn: "--warn", bad: "--bad", neutral: "--ink" };

for (const scheme of ["light", "dark"] as const) {
  test.describe(`barras de posición · ${scheme}`, () => {
    test.use({ colorScheme: scheme });

    test("rango de 52 semanas: degradado neutro y marca en tinta con aro", async ({ page }) => {
      await page.goto("/v2/NVDA/accion");
      const r52 = page.locator(".r52").first();
      await r52.waitFor({ timeout: 60_000 });
      const st = await r52.evaluate((e) => ({ img: getComputedStyle(e).backgroundImage,
        zones: [...e.querySelectorAll(".r52-zone")].map((z) => getComputedStyle(z).backgroundColor) }));
      expect(st.img).toContain("linear-gradient");
      expect(st.zones.every((z) => z === "rgba(0, 0, 0, 0)"), "tramos sin relleno gris propio").toBe(true);
      const [a, b] = [await token(page, "--pos-a"), await token(page, "--pos-b")];
      expect(contrast(a, b), "el degradado se distingue de extremo a extremo").toBeGreaterThanOrEqual(MIN_GRAPHIC);
      const mark = await page.locator(".r52-mark").evaluate((e) => ({ c: getComputedStyle(e).backgroundColor, ring: getComputedStyle(e).boxShadow }));
      expect(mark.c).toBe(await token(page, "--ink"));
      expect(mark.ring).not.toBe("none");
    });

    test("solidez y Altman: el marcador en el color del tramo de su lectura, con contraste", async ({ page }) => {
      await page.goto("/v2/NVDA/calidad");
      await page.locator(".gauge-mark").first().waitFor({ timeout: 60_000 });
      const surface = await token(page, "--surface");
      for (const m of await page.locator(".gauge-mark").all()) {
        const tone = await m.evaluate((e) => ["good", "warn", "bad", "neutral"].find((t) => e.classList.contains(t)) ?? "");
        expect(tone, "cada marcador declara su tramo").not.toBe("");
        const c = await m.evaluate((e) => getComputedStyle(e).backgroundColor);
        expect(c).toBe(await token(page, TONE_TOKEN[tone]));
        expect(contrast(c, surface)).toBeGreaterThanOrEqual(MIN_GRAPHIC);
      }
    });

    test("DCF y escenario: el precio y el valor del escenario, en el color de su tramo y con su etiqueta", async ({ page }) => {
      const surface = async () => token(page, "--surface");
      for (const [tk, label, tone] of [["SHEL", "Muy infravalorada", "good"], ["AAPL", "Sobrevalorada", "bad"], ["NVDA", "Precio justo", "neutral"]] as const) {
        await page.goto(`/v2/${tk}/valor`);
        await page.getByTestId("scenario-reading").waitFor({ timeout: 90_000 });
        await expect(page.getByTestId("scenario-reading")).toHaveText(label);
        const val = page.locator(".vb.val").first();
        expect(await val.evaluate((e, t) => e.classList.contains(t), tone), `${tk}: barra del valor con su tramo`).toBe(true);
        const c = await val.evaluate((e) => getComputedStyle(e).backgroundColor);
        expect(c).toBe(await token(page, tone === "neutral" ? "--scale-neutral" : TONE_TOKEN[tone]));
        if (tone !== "neutral") expect(contrast(c, await surface())).toBeGreaterThanOrEqual(MIN_GRAPHIC);
        // la marca del precio en la escala del DCF, en el tono de su lectura; la del valor, la referencia en pizarra
        const price = page.locator("[data-testid=fair-value] .fv-mark.price");
        if (await price.count()) {
          expect(await price.evaluate((e) => getComputedStyle(e).backgroundColor)).toBe(await token(page, TONE_TOKEN[tone]));
          expect(await bg(page, "[data-testid=fair-value] .fv-mark.fv")).toBe(await token(page, "--pos"));
        }
      }
    });

    test("escalera de márgenes: cada barra con tono y lectura o, sin ella, pizarra y «Sin referencia»", async ({ page }) => {
      await page.goto("/v2/NVDA/negocio");
      await page.locator(".ladder").first().waitFor({ timeout: 60_000 });
      const pos = await token(page, "--pos"), surface = await token(page, "--surface");
      const rows = await page.locator(".ladder > li:not([data-missing])").evaluateAll((lis) => lis.map((li) => ({
        label: li.querySelector(".seg-label")?.textContent ?? "",
        fill: getComputedStyle(li.querySelector(".seg-fill")!).backgroundColor,
        pill: li.querySelector(".pill")?.textContent ?? null,
        toned: ["good", "warn", "bad"].some((t) => li.querySelector(".seg-fill")!.classList.contains(t)) })));
      for (const r of rows) {
        if (r.toned) expect(r.pill, `${r.label}: color con su lectura`).toBeTruthy();
        else {
          expect(r.fill, `${r.label}: sin tono, pizarra`).toBe(pos);
          if (r.label !== "Ingresos") expect(r.pill, `${r.label}: dice por qué no tiene color de lectura`).toBe("Sin referencia");
        }
        expect(contrast(r.fill, surface)).toBeGreaterThanOrEqual(MIN_GRAPHIC);
      }
    });

    test("estructura del balance: paleta categórica (ni rojo ni verde), distinta y con contraste", async ({ page }) => {
      await page.goto("/v2/NVDA/calidad");
      await page.locator(".stackbar").first().waitFor({ timeout: 60_000 });
      const surface = await token(page, "--surface");
      const judged = await Promise.all(["--good", "--bad", "--warn"].map((t) => token(page, t)));
      const parts = await page.locator(".stackbar .sb").evaluateAll((sb) => sb.map((e) => getComputedStyle(e).backgroundColor));
      expect(new Set(parts).size, "cada parte, su color").toBe(parts.length);
      for (const c of parts) {
        expect(judged, "sin colores de juicio").not.toContain(c);
        expect(contrast(c, surface)).toBeGreaterThanOrEqual(MIN_GRAPHIC);
      }
      // y cada color con su nombre en la leyenda
      for (const k of ["Deuda", "Patrimonio", "Caja"]) await expect(page.locator(".kv-tight dt", { hasText: k }).first()).toBeVisible();
    });
  });
}
