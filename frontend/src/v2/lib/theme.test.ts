import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { readTheme, writeTheme } from "./theme";

describe("tema de /v2", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());
  it("por defecto es claro (sistema claro o sin preferencia)", () => {
    expect(readTheme()).toBe("light");
  });
  it("la primera vez sigue al sistema", () => {
    vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("dark"), addEventListener() {}, removeEventListener() {} }));
    expect(readTheme()).toBe("dark");
  });
  it("recuerda la elección por encima del sistema y la deja en el documento", () => {
    vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("dark"), addEventListener() {}, removeEventListener() {} }));
    writeTheme("light");
    expect(readTheme()).toBe("light");
    expect(document.documentElement.dataset.v2theme).toBe("light");
    writeTheme("dark");
    expect(readTheme()).toBe("dark");
  });
  it("no falla si el almacenamiento lanza", () => {
    const orig = Storage.prototype.getItem;
    Storage.prototype.getItem = () => { throw new Error("bloqueado"); };
    expect(readTheme()).toBe("light");
    Storage.prototype.getItem = orig;
  });
});
