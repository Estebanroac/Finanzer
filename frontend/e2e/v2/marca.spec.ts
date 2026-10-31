import { test, expect, type Page } from "@playwright/test";

// Marca (el logo del usuario, en sus colores originales y en los dos temas): una sola forma, el logo en su placa nocturna
// (en claro, el menta sin ella no llega a 3:1 con el papel), y «Finanzer» en Manrope 700 autoalojada; «Descargar PDF»
// como botón principal en menta con el texto en la noche del logo; el favicon (16 y 32 dibujados), el apple-touch, el
// manifiesto con sus iconos y el theme-color. Los verdes de lectura (--good) no cambian.
const MINT = "#94E8A5";
const GOOD = { light: "rgb(22, 121, 74)", dark: "rgb(79, 158, 116)" };   // --good de hoy: la marca no los toca

type RGB = [number, number, number];
const rgb = (s: string): RGB => (s.match(/[\d.]+/g) ?? []).slice(0, 3).map(Number) as RGB;
const lum = ([r, g, b]: RGB) => [r, g, b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; })
  .reduce((acc, v, i) => acc + v * [0.2126, 0.7152, 0.0722][i], 0);
const contrast = (a: string, b: string) => { const [x, y] = [lum(rgb(a)), lum(rgb(b))].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const token = (page: Page, name: string) => page.evaluate((n) => {
  const probe = document.createElement("i");
  probe.style.color = `var(${n})`;
  document.querySelector(".fz2")!.appendChild(probe);
  const c = getComputedStyle(probe).color; probe.remove(); return c;
}, name);
const hex2rgb = (h: string) => `rgb(${[1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)).join(", ")})`;

for (const scheme of ["light", "dark"] as const) {
  test.describe(`marca · ${scheme}`, () => {
    test.use({ colorScheme: scheme });

    test("cabecera: el logo en su placa y «Finanzer» en Manrope, como un solo enlace a la portada", async ({ page }) => {
      await page.goto("/v2");
      const brand = page.locator(".topbar .brand");
      await expect(brand).toHaveAccessibleName("Finanzer");
      await expect(brand).toHaveAttribute("href", /^\/v2\/?$/);
      const shown = "img.brand-logo";
      await expect(brand.locator("img")).toHaveCount(1);
      await expect(brand.locator(shown)).toBeVisible();
      await expect(brand.locator(shown)).toHaveAttribute("src", "/brand/finanzer-logo.svg");
      const w = await brand.locator(shown).evaluate(async (i: HTMLImageElement) => { await i.decode(); return i.naturalWidth; });
      expect(w, "el SVG del logo carga").toBeGreaterThan(0);
      const word = brand.locator(".brand-word");
      await expect(word).toHaveText("Finanzer");
      await page.evaluate(() => document.fonts.ready);
      const font = await word.evaluate((e) => ({ family: getComputedStyle(e).fontFamily, weight: getComputedStyle(e).fontWeight, color: getComputedStyle(e).color,
        loaded: [...document.fonts].some((f) => /manrope/i.test(f.family) && f.status === "loaded") }));
      expect(font.family).toMatch(/manrope/i);
      expect(font.weight).toBe("700");
      expect(font.loaded, "Manrope cargada desde el propio sitio").toBe(true);
      expect(font.color, "el nombre, en tinta").toBe(await token(page, "--ink"));
      // logo y nombre centrados en la misma línea
      const [a, b] = await Promise.all([brand.locator(shown).boundingBox(), word.boundingBox()]);
      expect(Math.abs((b!.y + b!.height / 2) - (a!.y + a!.height / 2))).toBeLessThanOrEqual(a!.height * 0.1);
    });

    test("«Descargar PDF», botón principal en menta con texto oscuro y su filo, con contraste; los verdes de lectura, sin tocar", async ({ page }) => {
      await page.goto("/v2/NVDA");
      const btn = page.locator(".topbar .pdf-btn");
      await btn.waitFor({ timeout: 90_000 });
      const st = await btn.evaluate((e) => ({ bg: getComputedStyle(e).backgroundColor, fg: getComputedStyle(e).color, edge: getComputedStyle(e).borderTopColor }));
      expect(st.bg).toBe(hex2rgb(MINT));
      expect(await token(page, "--brand")).toBe(hex2rgb(MINT));
      expect(contrast(st.fg, st.bg), "texto del botón").toBeGreaterThanOrEqual(4.5);
      expect(contrast(st.edge, await token(page, "--surface")), "el botón (su filo) frente a la cabecera").toBeGreaterThanOrEqual(3);
      expect(contrast(await token(page, "--brand-ink"), await token(page, "--paper")), "texto de marca sobre el papel").toBeGreaterThanOrEqual(4.5);
      expect(await token(page, "--good")).toBe(GOOD[scheme]);
    });
  });
}

test("favicon, apple-touch, manifiesto y theme-color", async ({ page, request }) => {
  await page.goto("/v2");
  const head = await page.evaluate(() => ({
    icons: [...document.querySelectorAll<HTMLLinkElement>("link[rel~=icon]")].map((l) => l.getAttribute("href")!),
    apple: document.querySelector<HTMLLinkElement>("link[rel=apple-touch-icon]")?.getAttribute("href") ?? null,
    manifest: document.querySelector<HTMLLinkElement>("link[rel=manifest]")?.getAttribute("href") ?? null,
    theme: document.querySelector<HTMLMetaElement>("meta[name=theme-color]")?.content ?? null,
  }));
  expect(head.icons.some((h) => h.startsWith("/favicon.ico")), `iconos ${head.icons}`).toBe(true);
  expect(head.icons).toContain("/brand/icon-32.png");
  expect(head.apple).toBe("/brand/apple-touch-icon.png");
  expect(head.manifest).toBe("/manifest.webmanifest");
  expect(head.theme?.toUpperCase()).toBe(MINT);
  for (const [href, type] of [["/favicon.ico", /icon/], ["/brand/icon-32.png", /image\/png/], ["/brand/apple-touch-icon.png", /image\/png/],
    ["/brand/finanzer-logo.svg", /image\/svg\+xml/]] as const) {
    const r = await request.get(href);
    expect(r.status(), href).toBe(200);
    expect(r.headers()["content-type"], href).toMatch(type);
  }
  const m = await request.get("/manifest.webmanifest");
  expect(m.status()).toBe(200);
  expect(m.headers()["content-type"]).toContain("application/manifest+json");
  const manifest = await m.json();
  expect(manifest.name).toBe("Finanzer");
  expect(manifest.theme_color.toUpperCase()).toBe(MINT);
  expect(manifest.icons.map((i: { sizes: string }) => i.sizes)).toEqual(expect.arrayContaining(["192x192", "512x512"]));
  for (const icon of manifest.icons) expect((await request.get(icon.src)).status(), icon.src).toBe(200);
});

test("móvil: el lockup cabe en la cabecera junto a los botones", async ({ page, isMobile }) => {
  test.skip(!isMobile, "móvil");
  await page.goto("/v2/NVDA");
  await page.locator(".topbar .pdf-btn").waitFor({ timeout: 90_000 });
  const brand = page.locator(".topbar .brand");
  await expect(brand.locator("img.brand-logo")).toBeVisible();
  const [b, btn] = await Promise.all([brand.boundingBox(), page.locator(".topbar .btn").first().boundingBox()]);
  expect(b!.x + b!.width).toBeLessThan(btn!.x);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
});
