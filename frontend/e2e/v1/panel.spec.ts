import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import * as fs from "node:fs";
import * as path from "node:path";
import { smallTexts, symmetryProblems } from "../v2/checks";

// Verificación V1 de la v4: cada ticker del panel (los fixtures del replay: 37, con MC.PA y SPY), la historia y sus 9
// páginas, en claro y en oscuro, sin red (toda petición fuera de localhost se corta y se anota). Por página: sin
// errores de consola, sin excepciones, sin peticiones fallidas inesperadas, simetría (huecos internos y
// desbordamiento, también dentro de las tarjetas), letra ≥ 12 px y axe sin infracciones graves. Cada test deja su
// fila en V1_OUT (JSON) para la matriz; falla si alguna página falla.
const FIXTURES = path.resolve(__dirname, "../../../backend/tests/fixtures/panel");
const TICKERS = (process.env.V1_TICKERS?.split(",") ?? fs.readdirSync(FIXTURES).filter((d) => !d.startsWith("."))).sort();
const PAGES = ["", "empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];
const OUT = path.resolve(__dirname, "../../", process.env.V1_OUT || "v1-results");
// SPY es un ETF: el motor no lo analiza y cada página muestra su motivo (la respuesta 422 del análisis es la esperada).
const ETF = new Set(["SPY"]);

type Check = "consola" | "excepciones" | "red" | "simetria" | "letra" | "axe" | "carga";
type PageResult = { page: string; ok: boolean; problems: Partial<Record<Check, string[]>>; blocked: string[] };

async function seriousAxe(page: Page): Promise<string[]> {
  const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).exclude("nextjs-portal").analyze();
  return res.violations.filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${v.id} (${v.nodes.length}) ${v.nodes[0]?.target.join(" ")}`);
}

for (const t of TICKERS) {
  for (const theme of ["light", "dark"] as const) {
    test(`V1 · ${t} · ${theme}`, async ({ page }, info) => {
      const etf = ETF.has(t);
      await page.emulateMedia({ colorScheme: theme });
      await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);

      // Registro por página (se vacía al empezar cada una)
      let consoleErr: string[] = [], pageErr: string[] = [], netBad: string[] = [], blocked: string[] = [];
      page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) consoleErr.push(m.text().slice(0, 200)); });
      page.on("pageerror", (e) => pageErr.push(String(e).slice(0, 200)));
      const local = (u: string) => /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?\//.test(u);
      await page.route((u) => !local(u.href) && !u.href.startsWith("data:") && !u.href.startsWith("blob:"), (r) => {
        blocked.push(new URL(r.request().url()).host);
        return r.abort("internetdisconnected");
      });
      page.on("requestfailed", (r) => {
        if (local(r.url()) && !/ERR_ABORTED|NS_BINDING_ABORTED|cancelled/i.test(r.failure()?.errorText ?? "")) netBad.push(`${r.failure()?.errorText} ${r.url().replace(/^https?:\/\/[^/]+/, "")}`);
      });
      page.on("response", (r) => {
        if (!local(r.url()) || r.status() < 400) return;
        const p = r.url().replace(/^https?:\/\/[^/]+/, "");
        if (etf && r.status() === 422 && p === `/api/analysis/${t}`) return;
        netBad.push(`${r.status()} ${p}`);
      });

      const results: PageResult[] = [];
      for (const pg of PAGES) {
        consoleErr = []; pageErr = []; netBad = []; blocked = [];
        const problems: PageResult["problems"] = {};
        const url = `/v2/${t}${pg ? `/${pg}` : ""}`;
        try {
          await page.goto(url);
          if (etf) {
            await expect(page.locator("main [role=alert]")).toContainText(`${t} es un ETF`, { timeout: 30_000 });
          } else {
            await page.waitForSelector(".depth-body .dsec", { timeout: 30_000 });
            // La gráfica de precio solo está en «La acción» (V4b): la de la historia ya no existe. Con el selector viejo
            // (price-chart) cada test perdía 2 × 30 s y los tickers lentos pasaban de los 300 s (cierre de la v4).
            if (pg === "accion") await page.waitForSelector("[data-testid=price-chart-full] canvas", { timeout: 30_000 }).catch(() => undefined);
          }
          await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
          await page.waitForTimeout(300);
          const sym = await symmetryProblems(page);
          if (sym.length) problems.simetria = sym;
          const small = await smallTexts(page);
          if (small.length) problems.letra = small;
          const axe = await seriousAxe(page);
          if (axe.length) problems.axe = axe;
        } catch (e) {
          problems.carga = [String(e).replace(/\u001b\[\d+m/g, "").split("\n")[0].slice(0, 200)];
        }
        if (consoleErr.length) problems.consola = [...new Set(consoleErr)];
        if (pageErr.length) problems.excepciones = [...new Set(pageErr)];
        if (netBad.length) problems.red = [...new Set(netBad)];
        results.push({ page: pg || "historia", ok: !Object.keys(problems).length, problems, blocked: [...new Set(blocked)] });
      }

      fs.mkdirSync(OUT, { recursive: true });
      fs.writeFileSync(path.join(OUT, `${t}__${info.project.name}__${theme}.json`),
        JSON.stringify({ ticker: t, project: info.project.name, theme, results }, null, 1));
      const bad = results.filter((r) => !r.ok).map((r) => `${r.page}: ${JSON.stringify(r.problems)}`);
      expect(bad).toEqual([]);
    });
  }
}
