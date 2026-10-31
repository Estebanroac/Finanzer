import type { Page } from "@playwright/test";

/** Escala de espaciado de la spec en px a 16 px de base (en la página va en rem: con el texto ampliado crece igual). */
export const SPACING_PX = [0, 4, 8, 12, 16, 24, 32, 48];
/** Hueco al pie de una tarjeta de una fila (contenido que no llega al borde inferior): como mucho 4 px. */
export const MAX_CARD_FOOT = 4;
/** Dentro de una tarjeta, hueco vertical entre hijos consecutivos: como mucho 24 px (--s5). */
export const MAX_INNER_GAP = 24;

/** Comprobaciones de simetría sobre la página cargada; devuelve la lista de problemas (vacía = bien). */
export async function symmetryProblems(page: Page): Promise<string[]> {
  return page.evaluate(({ spacing, maxFoot, maxGap }) => {
    const problems: string[] = [];
    const unit = parseFloat(getComputedStyle(document.documentElement).fontSize) / 16;   // rem actual / 16 px
    const scale = spacing.map((x) => Math.round(x * unit));
    document.querySelectorAll<HTMLElement>("[data-sym-row]").forEach((row, i) => {
      const disp = getComputedStyle(row).display;
      if (disp !== "grid" && !(disp === "flex" && row.classList.contains("flow"))) return;   // .flow: filas que se rellenan
      const kids = Array.from(row.children) as HTMLElement[];
      const tops = new Map<number, number[]>();
      kids.forEach((k) => { const r = k.getBoundingClientRect(); const top = Math.round(r.top); tops.set(top, [...(tops.get(top) ?? []), Math.round(r.height)]); });
      tops.forEach((hs) => { if (Math.max(...hs) - Math.min(...hs) > 1) problems.push(`fila ${i} (${row.className}): alturas ${hs.join("/")}`); });
      const gap = parseFloat(getComputedStyle(row).rowGap || "0");
      if (!scale.includes(Math.round(gap))) problems.push(`fila ${i}: gap ${gap}px fuera de la escala`);
      // Huecos internos: el contenido de cada tarjeta de la fila llega a su pie.
      kids.forEach((slot) => {
        // Un envoltorio de un solo hijo (.cardslot) no es la tarjeta: se mira la de dentro
        let card = slot;
        while (card.children.length === 1 && !card.matches(".card, .surface") && card.firstElementChild instanceof HTMLElement) card = card.firstElementChild;
        if (!card.children.length) return;
        const inFlow = Array.from(card.children).filter((k) => getComputedStyle(k).position !== "absolute");
        const bottom = Math.max(...inFlow.map((k) => k.getBoundingClientRect().bottom));
        const cs = getComputedStyle(card);
        const foot = card.getBoundingClientRect().bottom - parseFloat(cs.paddingBottom) - parseFloat(cs.borderBottomWidth) - bottom;
        if (foot > maxFoot) problems.push(`fila ${i} (${row.className}): hueco de ${Math.round(foot)}px al pie de una tarjeta`);
        const boxes = inFlow.map((k) => k.getBoundingClientRect()).filter((r) => r.height > 0).sort((a, b) => a.top - b.top);
        for (let j = 1; j < boxes.length; j++) {
          const gapIn = boxes[j].top - Math.max(...boxes.slice(0, j).map((r) => r.bottom));
          if (gapIn > maxGap) problems.push(`fila ${i} (${row.className}): hueco de ${Math.round(gapIn)}px dentro de una tarjeta`);
        }
        // Dentro de cada bloque que se estira (.fill) el espacio sobrante va repartido entre sus filas, no concentrado
        // en un hueco (dos hijos con un hueco grande, o un hueco mucho mayor que los demás) ni al pie
        card.querySelectorAll<HTMLElement>(".fill").forEach((fill) => {
          const els = Array.from(fill.children).filter((k) => getComputedStyle(k).position !== "absolute"
            && k.getBoundingClientRect().height > 0) as HTMLElement[];
          if (!els.length) return;
          const inner = els.map((k) => k.getBoundingClientRect());
          const fr = fill.getBoundingClientRect();
          const top = inner[0].top - fr.top, foot = fr.bottom - Math.max(...inner.map((r) => r.bottom));
          const gaps = inner.slice(1).map((r, j) => r.top - inner[j].bottom);
          const name = (card.querySelector("h4, h3, .tile-label, .eyebrow")?.textContent ?? card.className).trim().slice(0, 40);
          // Filas iguales (li, tr, filas de datos): vale repartir el espacio, siempre que sea uniforme y no se
          // acumule arriba o al pie más que entre filas
          const rows = els.length > 1 && els.every((k) => k.tagName === els[0].tagName && k.className === els[0].className);
          const edge = Math.max(top, foot), mid = gaps.length ? Math.max(...gaps) : 0;
          const spread = gaps.length > 1 ? Math.max(...gaps) - Math.min(...gaps) : 0;
          if (rows) {
            if (spread > maxGap) problems.push(`fila ${i} (${row.className}): reparto desigual de ${Math.round(spread)}px entre filas («${name}»)`);
            if (edge - mid > maxGap) problems.push(`fila ${i} (${row.className}): hueco de ${Math.round(edge)}px al borde de un bloque («${name}»)`);
            return;
          }
          if (foot > maxGap) problems.push(`fila ${i} (${row.className}): hueco de ${Math.round(foot)}px al pie de un bloque («${name}»)`);
          if (mid > maxGap) problems.push(`fila ${i} (${row.className}): hueco de ${Math.round(mid)}px dentro de un bloque («${name}»)`);
        });
      });
    });
    if (document.documentElement.scrollWidth > window.innerWidth) problems.push("desbordamiento horizontal");
    // También dentro (revisión del PM): ninguna tarjeta ni tabla corta su contenido. Las tablas anchas que se
    // desplazan a propósito (historia anual de 10 columnas, comparador de rivales) lo declaran con data-scroll-ok.
    document.querySelectorAll<HTMLElement>(".fz2 .card, .fz2 .surface, .fz2 .techtable-wrap, .fz2 .sens-wrap, .fz2 table").forEach((el) => {
      if (el.closest("[data-scroll-ok]") || el.closest("[aria-hidden], .chart, .breakdown, .tip-box") || !el.offsetParent) return;
      if (el.scrollWidth > el.clientWidth + 1) {
        const name = (el.querySelector("h4, caption, .eyebrow")?.textContent ?? el.className).trim().slice(0, 40);
        problems.push(`desbordamiento dentro de ${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0]} («${name}»): ${el.scrollWidth} > ${el.clientWidth}`);
      }
    });
    // En móvil, un desbordamiento ensancha el visor (el navegador aleja la página): innerWidth ya no lo delata
    if (window.visualViewport && window.visualViewport.scale < 0.99) problems.push("desbordamiento horizontal (el visor se aleja)");
    return problems;
  }, { spacing: SPACING_PX, maxFoot: MAX_CARD_FOOT, maxGap: MAX_INNER_GAP });
}

/** Zoom de texto del navegador (como el ajuste de tamaño de letra de Chrome o Safari): cambia el tamaño base, así que
 *  los rem y los cortes en em responden igual que en un navegador real. */
export async function setTextZoom(page: Page, percent: number): Promise<void> {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Page.enable");
  await cdp.send("Page.setFontSizes", { fontSizes: { standard: Math.round((16 * percent) / 100), fixed: Math.round((13 * percent) / 100) } });
}

/** Textos visibles por debajo de 12 px (spec §5 revisada); los de las gráficas y los ocultos no cuentan. */
export async function smallTexts(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const small: string[] = [];
    const walker = document.createTreeWalker(document.querySelector(".fz2")!, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const el = n.parentElement!;
      if (!n.textContent?.trim() || el.closest(".sr-only, [aria-hidden], .chart, details:not([open])")) continue;
      const fs = parseFloat(getComputedStyle(el).fontSize);
      if (fs < 12) small.push(`${el.tagName}.${el.className}: ${fs}px «${n.textContent.trim().slice(0, 24)}»`);
    }
    return [...new Set(small)].slice(0, 10);
  });
}

/** Errores de consola de la página, sin los de recursos externos (imágenes de noticias de otros dominios). */
export function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  return errors;
}

/** Las nueve secciones del análisis (V4b), en orden. */
export const SECTIONS = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"] as const;
export type Section = (typeof SECTIONS)[number];

/** Abre una sección y espera a que esté entera: su detalle, la gráfica en «La acción» y lo que llega aparte (rivales,
 *  segmentos). «La empresa» por su ruta corta, /v2/{T}, que es la que abre. */
export async function openSection(page: Page, symbol: string, section: Section = "empresa") {
  await page.goto(section === "empresa" ? `/v2/${symbol}` : `/v2/${symbol}/${section}`);
  await page.waitForSelector(`.depth[data-chapter=${section}] .depth-body .dsec`, { timeout: 60_000 });
  if (section === "accion") await page.waitForSelector("[data-testid=price-chart-full] canvas", { timeout: 30_000 });
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
}
