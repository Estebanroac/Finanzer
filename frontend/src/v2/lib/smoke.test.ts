import { describe, it, expect } from "vitest";

describe("entorno de tests de /v2", () => {
  it("ejecuta TypeScript con jsdom", () => {
    expect(typeof document).toBe("object");
  });
});
