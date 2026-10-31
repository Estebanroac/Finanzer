import { test, expect } from "@playwright/test";

/**
 * Verificación de la v4 (V5 · producción simulada): la web actual (/ y /stock/AAPL) servida por el backend es idéntica
 * píxel a píxel a la de main.
 *   1. Con el frontend/out de main (git checkout <main> -- frontend/out):  npm run legado:base
 *   2. Con el build de la rama (npm run build):                            npm run legado:comparar
 * Las capturas de referencia quedan en frontend/.legacy-snapshots/ (ignorada).
 * E6 · paso 2: la portada actual está en /clasica (en / va la de la v4) y /stock/{T} lleva el aviso «Prueba la nueva
 * versión →», en el margen y sin mover nada: se tapa en la captura y el resto sigue idéntico a main.
 */
for (const [name, path] of [["portada", "/clasica"], ["stock-AAPL", "/stock/AAPL"]] as const) {
  test(`web actual idéntica a main · ${name}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    if (path !== "/clasica") await expect(page.getByText("Apple Inc.").first()).toBeVisible({ timeout: 30_000 });
    await page.addStyleTag({ content: "*{animation:none!important;transition:none!important;caret-color:transparent!important}" });
    await page.waitForTimeout(3000);
    const shot = await page.screenshot({ fullPage: true, mask: [page.getByTestId("try-v4")], maskColor: "#050507" });
    expect(shot).toMatchSnapshot(`${name}.png`, { maxDiffPixels: 0 });
  });
}
