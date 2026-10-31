import { describe, expect, it } from "vitest";
import { COMPANY_NAMES } from "@/lib/generated/backendConfig";
import { companyShort } from "./companyName";

describe("nombre corto de la empresa (P8: la misma regla que el backend)", () => {
  it("da lo mismo que backend/lib/names.py `company` en las muestras generadas", () => {
    const samples: Record<string, string> = COMPANY_NAMES.samples;
    expect(Object.keys(samples).length).toBeGreaterThan(20);
    for (const [name, short] of Object.entries(samples)) expect(companyShort(name), name).toBe(short);
  });
  it("sin nombre, nada", () => {
    expect(companyShort(null)).toBeNull();
    expect(companyShort("")).toBe("");
  });
});
