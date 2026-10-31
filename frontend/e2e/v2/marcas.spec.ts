import { test, expect, type Page } from "@playwright/test";

// Marcas de las escalas (encargo del PM tras la pre-pasada V4): en la tarjeta de ~229 px del iPad, las cuatro marcas a
// 12 px se pisaban (calidad 6,6 px; precio 15–17 px; con «excelente» desde 85, fuera de la tarjeta). Ahora, bajo sus
// tramos mientras quepan y, si no, una leyenda (scaleFit.ts + consulta de contenedor). En cada tamaño, en la cabecera
// y en «La empresa»: ninguna marca pisa a otra ni sale de su tarjeta, ninguna por debajo de 12 px, todas a la vista,
// las tres tarjetas en la misma forma y la base de las tres a la misma altura (la subgrid sigue).
type Row = { mode: "leyenda" | "proporcion"; problems: string[]; bases: number[] };

async function marks(page: Page, sel: string): Promise<Row> {
  return page.locator(sel).first().evaluate((row) => {
    const problems: string[] = [];
    const modes = new Set<string>();
    const bases: number[] = [];
    for (const card of row.querySelectorAll<HTMLElement>(".score")) {
      const ticks = card.querySelector<HTMLElement>(".ticks");
      const base = card.querySelector<HTMLElement>(".base");
      if (base) bases.push(Math.round(base.getBoundingClientRect().top));
      if (!ticks || !ticks.offsetParent) { problems.push("marcas ocultas"); continue; }
      const cr = card.getBoundingClientRect();
      const boxes = [...ticks.children].map((s) => {
        const r = document.createRange(); r.selectNodeContents(s); const b = r.getBoundingClientRect();
        return { t: s.textContent ?? "", b, fs: parseFloat(getComputedStyle(s).fontSize) };
      });
      // Leyenda: una fila por tramo (cada marca empieza más abajo que la anterior); en proporción, todas en la misma.
      modes.add(boxes.every((x, i) => i === 0 || x.b.top > boxes[i - 1].b.top + 1) ? "leyenda" : "proporcion");
      boxes.forEach((x, i) => {
        if (x.fs < 12) problems.push(`${x.t}: ${x.fs}px`);
        if (!x.b.width || !x.b.height) problems.push(`${x.t}: sin tamaño`);
        if (x.b.left < cr.left - 0.5 || x.b.right > cr.right + 0.5) problems.push(`${x.t}: fuera de la tarjeta`);
        for (const y of boxes.slice(i + 1)) {
          const ox = Math.min(x.b.right, y.b.right) - Math.max(x.b.left, y.b.left);
          const oy = Math.min(x.b.bottom, y.b.bottom) - Math.max(x.b.top, y.b.top);
          if (ox > 0.5 && oy > 0.5) problems.push(`${x.t} pisa ${y.t} (${ox.toFixed(1)} px)`);
        }
      });
    }
    if (modes.size > 1) problems.push("las tarjetas no comparten la forma de las marcas");
    return { mode: [...modes][0] as Row["mode"], problems, bases };
  });
}

for (const theme of ["light", "dark"] as const) {
  test(`marcas de las escalas · cabecera y «La empresa» · ${theme}`, async ({ page }, info) => {
    await page.emulateMedia({ colorScheme: theme });
    await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
    await page.goto("/v2/AAPL");
    await page.waitForSelector(".depth .scores .ticks", { timeout: 30_000 });
    const mobile = info.project.name.startsWith("mobile");
    // En el móvil, la cabecera enseña cifra y banda (sin marcas): el desglose con sus marcas va en «La empresa».
    const rows = mobile ? [".depth .scores"] : [".company-header:not(.compact) .scores", ".depth .scores"];
    for (const sel of rows) {
      const r = await marks(page, sel);
      expect(r.problems, sel).toEqual([]);
      if (!mobile) expect(new Set(r.bases).size, `${sel}: la base de las tres tarjetas a la misma altura`).toBe(1);
      // El iPad (tarjetas de 229 px) en leyenda; el escritorio a 1440 en proporción, como antes.
      if (info.project.name === "tablet") expect(r.mode, sel).toBe("leyenda");
      if (info.project.name === "desktop") expect(r.mode, sel).toBe("proporcion");
    }
    // En la leyenda, el tramo de la empresa resaltado (el de calidad de AAPL: «sólida»).
    const on = page.locator(".depth .scores .score").first().locator(".ticks > span.on");
    await expect(on).toHaveCount(1);
    await expect(on).toContainText("sólida");
  });
}
