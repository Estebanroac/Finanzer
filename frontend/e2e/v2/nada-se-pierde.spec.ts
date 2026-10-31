import { test, expect, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { openSection, SECTIONS } from "./checks";

// E3 · Task 12 — "Nada se pierde": toda cifra que muestra hoy la web actual (/stock, sus 9 pestañas y sus
// desplegables abiertos) aparece en /v2 (V4b: en alguna de sus 9 secciones). Y cada métrica con tooltip en el motor
// (display.tooltips) tiene su "?" en alguna sección de /v2. El informe JSON dice en qué sección está cada cifra.
// Verificación V1: NADA_TICKERS=panel lo pasa por todo el panel (los fixtures del replay; SPY no, es un ETF que ninguna
// de las dos webs analiza: las dos muestran el motivo), o por una lista separada por comas.
const PANEL_DIR = path.resolve(__dirname, "../../../backend/tests/fixtures/panel");
const TICKERS = process.env.NADA_TICKERS === "panel"
  ? fs.readdirSync(PANEL_DIR).filter((d) => !d.startsWith(".") && d !== "SPY").sort()
  : process.env.NADA_TICKERS?.split(",") ?? ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];
const OLD_TABS = ["Valoración", "Rentabilidad", "Solidez", "Crecimiento", "Comparativa", "Histórico",
  "Evaluación institucional", "Alertas", "Contexto de mercado"];
const API = `http://localhost:${process.env.REPLAY_PORT || 8767}`;

/** Cifra con forma: con unidad, con decimales o con símbolo de moneda (B, T y M solo como unidad, no la inicial de
 *  la palabra siguiente: "$116.08 Muy infravalorada") (los enteros sueltos —años, recuentos,
 *  puntuaciones "x/20"— no se comparan: ver EXCEPTIONS). */
const TOKEN = /[-−+]?(?:US)?\$?\d[\d,]*(?:\.\d+)?(?:\s?(?:%|x|pp)|\s?(?:mil M|B|T|M)(?![A-Za-zÀ-ÿ]))?/g;
const norm = (t: string) => t.replace(/−/g, "-").replace(/^\+/, "").replace(/\s+/g, "").replace(/,/g, "");
const meaningful = (t: string) => /[.%$xBTM]|pp/.test(t);

/** Excepciones justificadas (las revisa el PM): una cifra de la web actual se excusa si TODAS sus apariciones van
 *  precedidas de uno de estos contextos. */
const EXCEPTIONS: Array<{ before: RegExp; token?: RegExp; why: string }> = [
  { before: /de cada\s*$/, why: "etiqueta de la escalera de márgenes («de cada $1 de ingreso»), no una cifra del análisis" },
  { before: /(Ingresos\s*\S+|base:)\s*$/i, token: /^100%$/, why: "base de la escalera de márgenes y del flujo de resultados de la web actual (los ingresos son el 100 %)" },
  { before: /Otros pasivos\s*$/, why: "la web actual calculaba en el navegador «otros pasivos» = 100 − deuda − patrimonio; /v2 no calcula en el navegador y muestra deuda, patrimonio y caja con su % del motor" },
  { before: /Deuda\s*$/, token: /^\$0+%$/, why: "lectura pegada del importe y el % de la deuda en la web actual («$0» y «0%», ambos en /v2)" },
];


async function openAll(page: Page) {
  await page.evaluate(() => document.querySelectorAll("details").forEach((d) => ((d as HTMLDetailsElement).open = true)));
  await page.waitForTimeout(150);
}
const texts: string[] = [];
async function tokensOf(page: Page, root: string): Promise<Set<string>> {
  await openAll(page);
  const text = await page.locator(root).first().innerText();
  texts.push(text);
  return new Set((text.match(TOKEN) ?? []).map(norm).filter(meaningful));
}

for (const t of TICKERS) {
  test(`nada se pierde · ${t}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop", "el contenido es el mismo en móvil");
    test.setTimeout(240_000);
    // 1) La web actual: cabecera + cada pestaña con sus desplegables abiertos
    await page.goto(`/stock/${t}`);
    await page.getByRole("button", { name: OLD_TABS[0], exact: true }).waitFor({ timeout: 60_000 });
    const old = new Set<string>();
    texts.length = 0;
    for (const tab of OLD_TABS) {
      await page.getByRole("button", { name: tab, exact: true }).click();
      await page.waitForTimeout(500);
      (await tokensOf(page, "main")).forEach((x) => old.add(x));
    }
    // 2) /v2: las nueve secciones (cabecera incluida)
    const oldText = texts.join("\n");
    const v2 = new Set<string>();
    const tips = new Set<string>();
    const bySection: Record<string, number> = {};
    for (const ch of SECTIONS) {
      await openSection(page, t, ch);
      const got = await tokensOf(page, ".fz2");
      bySection[ch] = got.size;
      got.forEach((x) => v2.add(x));
      (await page.$$eval("[data-tip]", (bs) => bs.map((b) => b.getAttribute("data-tip")!))).forEach((k) => tips.add(k));
    }
    const excused = (m: string) => {
      const hits = [...oldText.matchAll(TOKEN)].filter((x) => norm(x[0]) === m);
      return hits.length > 0 && hits.every((h) => EXCEPTIONS.some((e) =>
        (!e.token || e.token.test(m)) && e.before.test(oldText.slice(Math.max(0, h.index! - 40), h.index!))));
    };
    // V4 · moneda (E4): la web actual pone «$» a todo importe; /v2 da el de los estados en su moneda («EUR 10.60B», MC.PA),
    // que el token recoge sin el código: la misma cifra, no una perdida
    const sameAmount = (x: string) => /^\$[\d.]+(?:B|T|M|milM)$/.test(x) && v2.has(x.slice(1));
    const missing = [...old].filter((x) => !v2.has(x) && !sameAmount(x) && !excused(x)).sort();
    // 3) Tooltips del motor
    const analysis = await (await page.request.get(`${API}/api/analysis/${t}`)).json();
    // Solo las métricas que el análisis muestra (fuera de `tooltips`): el motor manda bandas también de métricas que
    // no aplican a esta empresa (p. ej. payout de una empresa sin beneficio) y que ninguna web enseña
    const { tooltips, ...shown } = analysis.display;
    const shownTxt = JSON.stringify(shown);
    const tipKeys = Object.keys(tooltips ?? {}).filter((k) => new RegExp(`"(key|metric)":"${k}"`).test(shownTxt) || ["quality", "category", "pos52", "beta"].includes(k));
    const noTip = tipKeys.filter((k) => !tips.has(k)).sort();
    const out = path.join(info.outputDir, `nada-se-pierde-${t}.json`);
    fs.mkdirSync(info.outputDir, { recursive: true });
    fs.writeFileSync(out, JSON.stringify({ old: old.size, v2: v2.size, bySection, missing, noTip,
      context: Object.fromEntries(missing.map((m) => {
        const hits = [...oldText.matchAll(TOKEN)].filter((x) => norm(x[0]) === m).slice(0, 3);
        return [m, hits.map((h) => oldText.slice(Math.max(0, h.index! - 70), h.index! + 40).replace(/\s+/g, " "))];
      })) }, null, 1));
    expect(missing, `cifras de /stock/${t} que no aparecen en /v2`).toEqual([]);
    expect(noTip, `tooltips del motor sin "?" en /v2 (${t})`).toEqual([]);
  });
}
