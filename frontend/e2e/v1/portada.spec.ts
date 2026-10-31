import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import * as fs from "node:fs";
import * as path from "node:path";
import { smallTexts, symmetryProblems } from "../v2/checks";

// Verificación V1 de la v4, la portada (tras fusionar P8b): el cintillo en sus 3 listas × 4 periodos, en claro y en
// oscuro, sin red. Por combinación, las mismas comprobaciones que panel.spec.ts (consola, excepciones, red, simetría,
// letra ≥ 12 px, axe) y además: «Bajan más» solo trae valores que bajan y «Suben más» solo los que suben, en cada
// periodo (también «Bajan más · 6 meses»). Deja su fila en V1_OUT con el ticker «PORTADA» para la matriz.
const OUT = path.resolve(__dirname, "../../", process.env.V1_OUT || "v1-results");
const LISTS = ["most_traded", "gainers", "losers"] as const;
const PERIODS = ["1D", "1S", "1M", "6M"] as const;
const SIGN: Record<string, RegExp | null> = { most_traded: null, gainers: /^▲ /, losers: /^▼ / };

type Check = "consola" | "excepciones" | "red" | "simetria" | "letra" | "axe" | "carga" | "signo";
type PageResult = { page: string; ok: boolean; problems: Partial<Record<Check, string[]>>; blocked: string[] };

async function seriousAxe(page: Page): Promise<string[]> {
  const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).exclude("nextjs-portal").analyze();
  return res.violations.filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${v.id} (${v.nodes.length}) ${v.nodes[0]?.target.join(" ")}`);
}

for (const theme of ["light", "dark"] as const) {
  test(`V1 · portada · ${theme}`, async ({ page }, info) => {
    await page.emulateMedia({ colorScheme: theme });
    await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
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
    page.on("response", (r) => { if (local(r.url()) && r.status() >= 400) netBad.push(`${r.status()} ${r.url().replace(/^https?:\/\/[^/]+/, "")}`); });

    await page.goto("/v2");
    await expect(page.getByTestId("ticker-item").first()).toBeVisible({ timeout: 60_000 });
    const results: PageResult[] = [];
    for (const per of PERIODS) {
      for (const list of LISTS) {
        consoleErr = []; pageErr = []; netBad = []; blocked = [];
        const problems: PageResult["problems"] = {};
        try {
          await page.getByTestId(`period-${per}`).click();
          await page.getByTestId(`list-${list}`).click();
          await expect(page.getByTestId(`list-${list}`)).toHaveAttribute("aria-pressed", "true");
          await expect(page.getByTestId("ticker-item").first()).toBeVisible({ timeout: 30_000 });
          await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
          await page.waitForTimeout(300);
          const sign = SIGN[list];
          if (sign) {
            const wrong = (await page.getByTestId("ticker-item").locator(".tk-chg").allTextContents())
              .map((s) => s.trim()).filter((s) => !sign.test(s));
            if (wrong.length) problems.signo = wrong.slice(0, 5);
          }
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
        results.push({ page: `${list}·${per}`, ok: !Object.keys(problems).length, problems, blocked: [...new Set(blocked)] });
      }
    }
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, `PORTADA__${info.project.name}__${theme}.json`),
      JSON.stringify({ ticker: "PORTADA", project: info.project.name, theme, results }, null, 1));
    expect(results.filter((r) => !r.ok).map((r) => `${r.page}: ${JSON.stringify(r.problems)}`)).toEqual([]);
  });
}
