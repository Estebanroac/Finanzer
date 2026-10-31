import { test, expect } from "@playwright/test";

/**
 * V6 (hallazgo F23): con la política de contenido del backend (lib/web_guard.py), la web actual y /v2 cargan sin
 * ninguna violación: ni un script en línea bloqueado (sus hashes van en la cabecera), ni estilos, imágenes o fuentes.
 * Sobre lo que sirve el backend (playwright.legado.config.ts: el replay sirve frontend/out y la API).
 */
const PAGES: Array<[string, string, string | null]> = [
  ["portada (v4, E6)", "/", null],
  ["portada actual", "/clasica", null],
  ["empresa actual", "/stock/AAPL", "Apple Inc."],
  ["portada v2", "/v2", null],
  ["historia v2", "/v2/AAPL", "Apple"],
  ["valor v2", "/v2/AAPL/valor", "Apple"],
];

for (const [name, path, text] of PAGES) {
  test(`sin violaciones de la CSP · ${name}`, async ({ page }) => {
    const violations: string[] = [];
    page.on("console", (m) => {
      if (/Content Security Policy|Refused to (execute|load|apply)/i.test(m.text())) violations.push(m.text());
    });
    await page.addInitScript(() => {
      document.addEventListener("securitypolicyviolation", (e) =>
        console.error(`Content Security Policy: ${e.violatedDirective} ${e.blockedURI}`));
    });
    const res = await page.goto(path);
    const csp = res?.headers()["content-security-policy"] ?? "";
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toMatch(/script-src 'self'( 'sha256-[A-Za-z0-9+/=]+')+/);
    expect(res?.headers()["x-content-type-options"]).toBe("nosniff");
    await page.waitForLoadState("networkidle");
    if (text) await expect(page.getByText(text).first()).toBeVisible({ timeout: 30_000 });
    await page.waitForTimeout(1500);
    expect(violations).toEqual([]);
  });
}
