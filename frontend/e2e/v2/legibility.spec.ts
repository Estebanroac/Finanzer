import { test, expect } from "@playwright/test";
import { openSection, SECTIONS, symmetryProblems, setTextZoom } from "./checks";

// Spec §5 revisada (2026-10-17, petición del usuario): ningún texto por debajo de 12 px; el zoom con los dedos
// nunca se bloquea; la página sigue usable sin desbordamiento horizontal a 200 % de zoom (WCAG 1.4.4) y con el
// texto grande del sistema.
const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];
const MIN_TEXT_PX = 12;

const report = () => {
  const small: string[] = [];
  const walker = document.createTreeWalker(document.querySelector(".fz2")!, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const el = n.parentElement!;
    if (!n.textContent?.trim() || el.closest(".sr-only, [aria-hidden], .chart")) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < 12) small.push(`${el.tagName}.${el.className}: ${fs}px «${n.textContent.trim().slice(0, 24)}»`);
  }
  const meta = document.querySelector('meta[name="viewport"]')?.getAttribute("content") ?? "";
  return { small: [...new Set(small)].slice(0, 10), meta, overflow: document.documentElement.scrollWidth > window.innerWidth };
};

for (const t of TICKERS) {
  test(`legibilidad · ${t}`, async ({ page }) => {
    await page.goto(`/v2/${t}`);
    await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
    const r = await page.evaluate(report);
    expect(r.small, `textos de menos de ${MIN_TEXT_PX} px`).toEqual([]);
    expect(r.meta).not.toMatch(/maximum-scale|user-scalable\s*=\s*no/);
    expect(r.overflow).toBe(false);
  });
}

test("200 % de zoom y texto grande del sistema: sin desbordamiento horizontal", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "se simula desde el escritorio");
  // 200 % de zoom en una ventana de 1440 px = 720 px CSS de ancho; texto grande = raíz a 20 px (125 %).
  for (const [width, rootPx] of [[720, 16], [1440, 20], [720, 20]] as const) {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript((px) => { document.documentElement.style.fontSize = `${px}px`; }, rootPx);
    for (const t of TICKERS) {
      await page.goto(`/v2/${t}`);
      await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
      await page.evaluate((px) => { document.documentElement.style.fontSize = `${px}px`; }, rootPx);
      await page.waitForTimeout(300);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `${t} a ${width}px y raíz ${rootPx}px`).toBeLessThanOrEqual(0);
    }
  }
});

test("zoom de texto al 200 %: sin desbordamiento y la simetría sigue pasando", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "se comprueba en escritorio");
  await setTextZoom(page, 200);
  test.setTimeout(240_000);
  // V4b: las nueve secciones de AAPL y «La empresa» (con la cabecera) de los demás
  for (const t of TICKERS) for (const s of t === "AAPL" ? SECTIONS : (["empresa"] as const)) {
    await openSection(page, t, s);
    await page.waitForTimeout(500);
    // El 200 % vive en la raíz (1rem = 32 px); el cuerpo de /v2 puede ser mayor si la página pasa a una columna (17/16).
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).fontSize)).toBe("32px");
    expect(await symmetryProblems(page), `${t}/${s} con el texto al 200 %`).toEqual([]);
  }
});
