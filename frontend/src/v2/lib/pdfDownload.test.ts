import { describe, expect, it } from "vitest";
import { pdfFilename, pdfStatusText } from "./pdfDownload";

describe("descarga del PDF (PDF rápido)", () => {
  it("usa el nombre que da el servidor y, sin él, uno con el símbolo", () => {
    expect(pdfFilename('attachment; filename="Informe Finanzer HD 2026-10-30.pdf"', "HD"))
      .toBe("Informe Finanzer HD 2026-10-30.pdf");
    expect(pdfFilename("attachment; filename*=UTF-8''Informe%20Finanzer%20MC.PA.pdf", "MC.PA"))
      .toBe("Informe Finanzer MC.PA.pdf");
    expect(pdfFilename(null, "HD")).toBe("Informe Finanzer HD.pdf");
    expect(pdfFilename("attachment", "HD")).toBe("Informe Finanzer HD.pdf");
  });

  it("dice qué pasa y por qué: preparando (las comparables), el fallo con su motivo, nada en reposo", () => {
    expect(pdfStatusText("HD", { kind: "preparing" }))
      .toBe("Preparando el PDF de HD: espera a que estén las comparables de su industria. Se descargará solo.");
    expect(pdfStatusText("HD", { kind: "error", reason: "HTTP 503" }))
      .toBe("No se pudo preparar el PDF de HD (HTTP 503). Vuelve a intentarlo.");
    expect(pdfStatusText("HD", { kind: "idle" })).toBe("");
  });
});
