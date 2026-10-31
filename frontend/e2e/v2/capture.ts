import type { Page } from "@playwright/test";

/** Carpeta de las capturas de cada pasada del e2e: dentro de test-results (ignorada por git; Playwright la vacía al
 *  empezar cada pasada). Para versionar las de una etapa: `npm run capturas:etapa -- <etapa> [prefijo]`. */
export const CAPTURES_DIR = "test-results/capturas";

/** Captura de página completa sin el indicador de desarrollo de Next (solo existe en `next dev`). */
export async function capture(page: Page, name: string): Promise<void> {
  await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
  await page.screenshot({ path: `${CAPTURES_DIR}/${name}.png`, fullPage: true });
}

/** Captura de un elemento (p. ej. `.depth`, la página de profundidad sin la cabecera), a la misma carpeta. */
export async function captureElement(page: Page, selector: string, name: string): Promise<void> {
  await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
  await page.locator(selector).first().screenshot({ path: `${CAPTURES_DIR}/${name}.png` });
}
