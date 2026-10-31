import { test } from "@playwright/test";
import { openSection, SECTIONS } from "./checks";

// V4b · 1: capturas de las nueve secciones de AAPL (escritorio y móvil) para el PM. Solo con CAPTURAS_V4B=<carpeta>.
const OUT = process.env.CAPTURAS_V4B;

test("capturas de las nueve secciones de AAPL", async ({ page }, info) => {
  test.skip(!OUT || !["desktop", "mobile"].includes(info.project.name), "solo a petición (CAPTURAS_V4B)");
  test.setTimeout(300_000);
  for (const [i, s] of SECTIONS.entries()) {
    await openSection(page, "AAPL", s);
    await page.waitForTimeout(800);
    await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
    await page.screenshot({ path: `${OUT}/${info.project.name}-${i + 1}-${s}.png`, fullPage: true });
  }
});
