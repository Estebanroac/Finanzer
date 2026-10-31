import { test, expect, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { WEB } from "../../src/lib/generated/backendConfig";

// V4b · 3 (literal del usuario: «mucho lag cuando entro a una sección… Veo mucho lag en varios sitios»): las medidas
// que el PM fijó, contra el build de producción, con los umbrales de la config (WEB.perf):
//  - cambio de sección con el análisis ya cargado ≤ sectionChangeMs hasta el contenido pintado;
//  - INP p75 ≤ inpP75Ms en las interacciones (pestañas, «?», periodo de la gráfica, escenario, carrusel);
//  - ninguna tarea larga > longTaskMs durante una interacción;
//  - desplazar sin tareas largas (> scrollLongTaskMs).
// Chromium mide tareas largas (longtask) e interacciones (Event Timing); WebKit no tiene ninguna de las dos APIs: allí la
// interacción es del evento de entrada al siguiente fotograma pintado y la «tarea larga», un hueco entre fotogramas.
// Cada pasada deja su informe en test-results/perf/<proyecto>.json (y una traza de Chromium de los cambios de sección).
const P = WEB.perf;
const SYMBOL = "AAPL";
const SECTIONS = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"] as const;
const LABELS = ["La empresa", "Cómo gana dinero", "La acción", "Calidad", "Cuánto vale", "Rivales", "Riesgos", "Actualidad", "Conclusión"];
const OUT = path.resolve(__dirname, "../../test-results/perf");

type Span = { start: number; dur: number };
type Probe = { long: Span[]; gaps: Span[]; events: Array<{ id: number; start: number; dur: number; name: string }>; t0: number | null };
declare global { interface Window { __perf: Probe } }

/** Sondas en la página desde el primer momento: tareas largas, interacciones y huecos entre fotogramas. */
async function installProbes(page: Page, gapMs: number) {
  await page.addInitScript((gap) => {
    const p: Probe = { long: [], gaps: [], events: [], t0: null };
    window.__perf = p;
    const types = PerformanceObserver.supportedEntryTypes ?? [];
    if (types.includes("longtask"))
      new PerformanceObserver((l) => l.getEntries().forEach((e) => p.long.push({ start: e.startTime, dur: e.duration })))
        .observe({ type: "longtask", buffered: true });
    if (types.includes("event"))
      new PerformanceObserver((l) => l.getEntries().forEach((e) => {
        const ev = e as PerformanceEventTiming & { interactionId?: number };
        if (ev.interactionId) p.events.push({ id: ev.interactionId, start: ev.startTime, dur: ev.duration, name: ev.name });
      })).observe({ type: "event", buffered: true, durationThreshold: 16 } as PerformanceObserverInit);
    let last = performance.now();
    const tick = (t: number) => { if (t - last > gap) p.gaps.push({ start: last, dur: t - last }); last = t; requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
    // el momento de la entrada (pointerdown o tecla) de la interacción que se mide
    const mark = (e: Event) => { if (p.t0 === null) p.t0 = e.timeStamp; };
    addEventListener("pointerdown", mark, { capture: true });
    addEventListener("pointerup", mark, { capture: true });         // el soltar del carrusel (el clic marca antes su pointerdown)
    addEventListener("keydown", mark, { capture: true });
  }, gapMs);
}

/** Lo que dice que la interacción terminó: un selector presente, ausente, o el botón con ese texto pulsado. */
type Ready = { sel: string } | { gone: string } | { pressed: string };

/** Una interacción medida: de la entrada a que `ready` se cumple y el fotograma siguiente se pinta. Devuelve su duración
 *  y las tareas largas (o huecos) que la solapan. */
async function measure(page: Page, act: () => Promise<void>, ready: Ready) {
  await page.evaluate(() => { window.__perf.t0 = null; });
  await act();
  return page.evaluate(async ({ ready, timeout }) => {
    const p = window.__perf;
    const done = () => "sel" in ready ? !!document.querySelector(ready.sel)
      : "gone" in ready ? !document.querySelector(ready.gone)
      : [...document.querySelectorAll("button[aria-pressed=true]")].some((b) => b.textContent?.trim() === ready.pressed);
    const end0 = performance.now() + timeout;
    while (!done() && performance.now() < end0) await new Promise((r) => requestAnimationFrame(r));
    // el contenido está en el DOM: el fotograma que lo pinta es el siguiente
    await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)));
    const t0 = p.t0 ?? performance.now(), t1 = performance.now();
    const over = (s: Span) => s.start + s.dur > t0 && s.start < t1;
    return { ms: Math.round(t1 - t0), found: done(),
      long: p.long.filter(over).map((s) => Math.round(s.dur)), gaps: p.gaps.filter(over).map((s) => Math.round(s.dur)) };
  }, { ready, timeout: 10_000 });
}

const p75 = (xs: number[]) => { if (!xs.length) return 0; const s = [...xs].sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.ceil(0.75 * s.length) - 1)]; };

test("rendimiento: secciones, interacciones y desplazamiento", async ({ page, browserName }, info) => {
  const chromium = browserName === "chromium";
  await installProbes(page, P.longTaskMs);
  if (chromium) {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: P.cpuThrottle });
  }
  const report: Record<string, unknown> = { project: info.project.name, cpuThrottle: chromium ? P.cpuThrottle : 1, thresholds: P };
  const problems: string[] = [];

  // 1) Entrada: el análisis llega (replay) y queda en la caché de la sesión
  await page.goto(`/v2/${SYMBOL}`);
  await page.waitForSelector(".depth[data-chapter=empresa] .depth-body .dsec", { timeout: 120_000 });
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForTimeout(1000);

  // 2) Cambio de sección (pestañas), las nueve, con traza de Chromium
  if (chromium) await page.context().browser()!.startTracing(page, { path: path.join(OUT, `traza-secciones-${info.project.name}.json`), screenshots: false });
  const tabs: Array<{ section: string; ms: number; long: number[]; gaps: number[] }> = [];
  for (const [i, s] of SECTIONS.entries()) {
    if (i === 0) continue;
    const r = await measure(page, () => page.locator("nav.chapterbar").getByRole("link", { name: LABELS[i], exact: true }).click(),
      { sel: `.depth[data-chapter=${s}] .depth-body .dsec` });
    tabs.push({ section: s, ms: r.ms, long: r.long, gaps: r.gaps });
    if (!r.found) problems.push(`${s}: la sección no llegó`);
  }
  // y de vuelta a una ya visitada (su fragmento ya está descargado)
  const back = await measure(page, () => page.locator("nav.chapterbar").getByRole("link", { name: LABELS[3], exact: true }).click(),
    { sel: ".depth[data-chapter=calidad] .depth-body .dsec" });
  tabs.push({ section: "calidad (otra vez)", ms: back.ms, long: back.long, gaps: back.gaps });
  if (chromium) await page.context().browser()!.stopTracing();
  report.tabs = tabs;
  for (const t of tabs) if (t.ms > P.sectionChangeMs) problems.push(`cambio a ${t.section}: ${t.ms} ms > ${P.sectionChangeMs} ms`);

  // 3) Otras interacciones: «?», periodo de la gráfica, escenario
  const other: Array<{ what: string; ms: number; long: number[]; gaps: number[] }> = [];
  await page.goto(`/v2/${SYMBOL}/calidad`);
  await page.waitForSelector(".depth-body .dsec");
  for (const sel of [".company-header .tip-btn", ".depth-body .techtable .tip-btn"]) {
    const btn = page.locator(sel).first();
    await btn.scrollIntoViewIfNeeded();
    const r = await measure(page, () => btn.click(), { sel: ".tip-box:not([hidden])" });
    other.push({ what: `«?» ${sel.split(" ")[1]}`, ...r });
    const c = await measure(page, () => page.keyboard.press("Escape"), { gone: ".tip-box:not([hidden])" });
    other.push({ what: "cerrar «?»", ...c });
  }
  await page.goto(`/v2/${SYMBOL}/accion`);
  await page.waitForSelector("[data-testid=price-chart-full] canvas", { timeout: 30_000 });
  for (const range of ["5A", "1M", "1A"]) {
    const btn = page.getByRole("button", { name: range, exact: true }).first();
    const r = await measure(page, () => btn.click(), { pressed: range });
    other.push({ what: `periodo ${range}`, ...r });
  }
  await page.goto(`/v2/${SYMBOL}/valor`);
  await page.waitForSelector("[data-testid=scenario-value]", { timeout: 30_000 });
  for (const sc of ["Optimista", "Pesimista", "Base"]) {
    const btn = page.getByRole("button", { name: sc, exact: true }).first();
    if (!(await btn.count())) continue;
    await btn.scrollIntoViewIfNeeded();
    const r = await measure(page, () => btn.click(), { pressed: sc });
    other.push({ what: `escenario ${sc}`, ...r });
  }
  // carrusel de la portada: arrastrar y soltar (se mide del soltar al fotograma siguiente; el arrastre, en su INP)
  await page.goto("/v2");
  await page.waitForSelector("[data-testid=ticker-item]", { timeout: 60_000 });
  const strip = page.locator(".ticker").first();
  const box = await strip.boundingBox();
  if (box) {
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    for (let k = 1; k <= 10; k++) await page.mouse.move(box.x + box.width / 2 - k * 30, box.y + box.height / 2);
    const r = await measure(page, () => page.mouse.up(), { sel: "[data-testid=ticker-item]" });
    other.push({ what: "carrusel (soltar)", ...r });
  }
  report.other = other;

  // INP: por interacción, su evento más largo (Chromium, Event Timing); en WebKit, la medida de entrada a pintado
  const evs = await page.evaluate(() => window.__perf.events);
  const byId = new Map<number, number>();
  for (const e of evs) byId.set(e.id, Math.max(byId.get(e.id) ?? 0, e.dur));
  const inpSamples = chromium && byId.size ? [...byId.values()] : [...tabs, ...other].map((x) => x.ms);
  report.inp = { source: chromium && byId.size ? "event-timing" : "entrada→pintado", samples: inpSamples.length, p75: p75(inpSamples), max: Math.max(0, ...inpSamples) };
  if (p75(inpSamples) > P.inpP75Ms) problems.push(`INP p75 ${p75(inpSamples)} ms > ${P.inpP75Ms} ms`);
  for (const x of [...tabs, ...other]) {
    const worst = Math.max(0, ...x.long, ...(chromium ? [] : x.gaps));
    if (worst > P.longTaskMs) problems.push(`${"section" in x ? `cambio a ${x.section}` : x.what}: tarea larga de ${worst} ms > ${P.longTaskMs} ms`);
  }

  // 4) Desplazamiento por las secciones más largas, con la rueda
  const scroll: Array<{ section: string; long: number[]; gaps: number[] }> = [];
  for (const s of ["calidad", "valor", "negocio"]) {
    await page.goto(`/v2/${SYMBOL}/${s}`);
    await page.waitForSelector(".depth-body .dsec");
    await page.waitForLoadState("networkidle").catch(() => undefined);
    await page.waitForTimeout(800);
    const t0 = await page.evaluate(() => performance.now());
    await page.mouse.move(700, 450);
    for (let k = 0; k < 30; k++) { await page.mouse.wheel(0, 300); await page.waitForTimeout(30); }
    await page.waitForTimeout(300);
    const r = await page.evaluate(({ t0, lim }) => {
      const p = window.__perf, over = (x: Span) => x.start + x.dur > t0;
      return { long: p.long.filter(over).map((x) => Math.round(x.dur)), gaps: p.gaps.filter(over).filter((x) => x.dur > lim).map((x) => Math.round(x.dur)) };
    }, { t0, lim: P.scrollLongTaskMs });
    scroll.push({ section: s, ...r });
    const worst = Math.max(0, ...r.long.filter((d) => d > P.scrollLongTaskMs), ...(chromium ? [] : r.gaps));
    if (worst) problems.push(`desplazar ${s}: tarea larga de ${worst} ms > ${P.scrollLongTaskMs} ms`);
  }
  report.scroll = scroll;

  // 5) En reposo en una sección, nada trabaja (p. ej. el cintillo de la portada no sigue animándose)
  const idle = await page.evaluate(async () => {
    let frames = 0; const t0 = performance.now(); const before = window.__perf.long.length;
    await new Promise<void>((r) => { const f = () => { frames++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else r(); }; requestAnimationFrame(f); });
    return { long: window.__perf.long.slice(before).map((x) => Math.round(x.dur)), frames };
  });
  report.idle = idle;
  if (idle.long.length) problems.push(`en reposo hay tareas largas: ${idle.long.join(", ")} ms`);

  report.problems = problems;
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, `${info.project.name}.json`), JSON.stringify(report, null, 1));
  console.log(JSON.stringify({ project: info.project.name, tabs: tabs.map((t) => `${t.section} ${t.ms}`), inp: report.inp, problems }, null, 1));
  expect(problems).toEqual([]);
});
