import { describe, it, expect } from "vitest";
import { tileRows } from "./tileRows";

describe("tileRows: fichas de dos en dos sin huecos", () => {
  it("de dos en dos; si quedan impares, la última ocupa la fila", () => {
    expect(tileRows([false, false, false, false])).toEqual(["half", "half", "half", "half"]);
    expect(tileRows([false, false, false])).toEqual(["half", "half", "full"]);
  });
  it("una cifra que no cabe ocupa la fila y las demás se emparejan después", () => {
    expect(tileRows([true, false, false, false, false])).toEqual(["full", "half", "half", "half", "half"]);
    expect(tileRows([true, false, false, false])).toEqual(["full", "half", "half", "full"]);
  });
  it("la que se quedaría sola delante de una ficha a lo ancho, también a lo ancho", () => {
    expect(tileRows([false, true, false, false])).toEqual(["full", "full", "half", "half"]);
    expect(tileRows([false, false, false, true, false])).toEqual(["half", "half", "full", "full", "full"]);
  });
});
