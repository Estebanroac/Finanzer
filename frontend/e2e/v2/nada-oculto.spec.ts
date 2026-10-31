import { test, expect } from "@playwright/test";
import { openSection, SECTIONS } from "./checks";

// V4b · 2 (literal del usuario: «no quiero subsecciones ocultas, las quiero fijas y sin lag»): en las nueve secciones,
// nada de contenido detrás de un gesto. El desglose de las tres puntuaciones, a la vista sin tocar nada en «La empresa»
// (y en cada sección, su enlace bajo las tres puntuaciones de la cabecera; PM: nada de 1.590 px de cabecera en el móvil); ningún
// desplegable, «Ver más» ni «Ver detalle»; ningún texto cortado; nada que solo se lea al pasar el ratón. Los «?» se
// quedan (son ayuda, no contenido) y abren en el siguiente fotograma.
const TICKERS = ["AAPL", "JPM"];

for (const t of TICKERS) {
  test(`nada oculto en las nueve secciones · ${t}`, async ({ page }) => {
    test.setTimeout(240_000);
    const problems: string[] = [];
    for (const s of SECTIONS) {
      await openSection(page, t, s);
      // el desglose de las tres puntuaciones, sin tocar nada, en «La empresa»; en todas, el enlace hasta él
      if (s === "empresa") for (const id of ["breakdown-quality", "breakdown-price", "breakdown-confidence"]) await expect(page.locator("#desglose").getByTestId(id), `${s}: ${id}`).toBeVisible();
      await expect(page.getByTestId("bd-link"), `${s}: enlace al desglose`).toHaveAttribute("href", `/v2/${t}/empresa#desglose`);
      problems.push(...(await page.evaluate(() => {
        const out: string[] = [];
        const main = document.querySelector("main")!;
        if (main.querySelector("details, summary")) out.push("un desplegable (<details>)");
        if (/\b(Ver más|Ver menos|Ver detalle|Mostrar más)\b/.test(main.innerText)) out.push("un «Ver más / Ver detalle»");
        // controles que esconden y enseñan algo: solo los «?» (ayuda)
        main.querySelectorAll("[aria-expanded]").forEach((el) => { if (!el.classList.contains("tip-btn")) out.push(`aria-expanded en ${el.tagName.toLowerCase()}.${el.className}`); });
        // textos cortados: líneas limitadas o puntos suspensivos que tapan contenido
        main.querySelectorAll<HTMLElement>("*").forEach((el) => {
          const cs = getComputedStyle(el);
          if (!el.closest(".stuck-head, [aria-hidden]") && el.offsetParent) {
            if (cs.webkitLineClamp && cs.webkitLineClamp !== "none") out.push(`texto cortado a ${cs.webkitLineClamp} líneas: ${el.className}`);
            if (cs.textOverflow === "ellipsis" && el.scrollWidth > el.clientWidth + 1) out.push(`texto cortado con «…»: ${(el.textContent ?? "").slice(0, 40)}`);
          }
        });
        // nada que solo se lea al pasar el ratón (los botones de periodo llevan su nombre largo como ayuda del control)
        main.querySelectorAll("[title]").forEach((el) => { if (el.tagName !== "BUTTON" && !el.closest(".stuck-head")) out.push(`title= en ${el.tagName.toLowerCase()}: ${el.getAttribute("title")?.slice(0, 50)}`); });
        return out;
      })).map((p) => `${s}: ${p}`));
    }
    expect([...new Set(problems)]).toEqual([]);
  });
}

test("los «?» abren al instante (en el siguiente fotograma) y la cabecera no tiene paneles ni hojas propias", async ({ page }) => {
  await openSection(page, "AAPL", "calidad");
  for (const sel of [".company-header .tip-btn", ".depth-body .techtable .tip-btn"]) {
    const opened = await page.locator(sel).first().evaluate(async (b) => {
      (b as HTMLElement).scrollIntoView({ block: "center" });
      await new Promise((r) => requestAnimationFrame(() => r(null)));
      (b as HTMLElement).click();
      await new Promise((r) => requestAnimationFrame(() => r(null)));
      return !!document.querySelector(".tip-box:not([hidden])");
    });
    expect(opened, `${sel}: el «?» abre en el siguiente fotograma`).toBe(true);
    await page.keyboard.press("Escape");
    await expect(page.locator(".tip-box:not([hidden])")).toHaveCount(0);
  }
  // pasar el ratón o tocar la tarjeta no abre nada: el desglose ya está ahí
  await page.getByTestId("score-quality").locator(".score-value").click();
  await expect(page.locator(".tip-box:not([hidden]), [role=dialog]")).toHaveCount(0);
});
