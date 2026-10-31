import { describe, it, expect } from "vitest";
import { changeTone, smoothPath, sparkGeometry, SPARK_H, SPARK_W, staleToRefresh, type SparkItem } from "./sparklines";

/** Un punto [índice, cierre] (helper: el control de literales de análisis no lee los datos de prueba como bandas). */
const P = (i: number, v: number): [number, number] => [i, v];
const item = (pts: Array<[number, number]>, ref: number, n?: number, change?: number): SparkItem => ({
  status: "ok", reason: null, points: pts, n: n ?? pts.length, ref, change_pct: change ?? pts[pts.length - 1][1] / ref - 1,
});

describe("mini-gráfica (P8)", () => {
  it("curva Catmull-Rom → Bézier: empieza en el primer punto y acaba en el último", () => {
    const d = smoothPath([{ x: 0, y: 10 }, { x: 10, y: 0 }, { x: 20, y: 10 }]);
    expect(d.startsWith("M0.0,10.0 C")).toBe(true);
    expect(d.endsWith("20.0,10.0")).toBe(true);
    expect(d.match(/C/g)).toHaveLength(2);
  });
  it("la escala incluye la referencia aunque quede fuera de los precios", () => {
    const g = sparkGeometry(item([P(0, 110), P(1, 112), P(2, 115)], 100))!;
    expect(g.refY).toBeGreaterThan(g.dot.y);                    // 100 por debajo de todos los precios: abajo
    expect(g.refY).toBeLessThanOrEqual(SPARK_H);
    expect(g.tone).toBe("good");
  });
  it("el eje x es el índice de la barra original (LTTB deja huecos) y el último punto deja sitio a su halo", () => {
    const g = sparkGeometry(item([P(0, 10), P(40, 12), P(77, 9)], 10, 78))!;
    expect(g.dot.x).toBeLessThan(SPARK_W);
    expect(g.dot.x).toBeCloseTo(SPARK_W - 6, 0);
    expect(g.area.endsWith("Z")).toBe(true);
    expect(g.tone).toBe("bad");
  });
  it("sin serie o con un punto: sin geometría; color neutro con variación 0", () => {
    expect(sparkGeometry({ status: "sin_dato", reason: "Yahoo no respondió" })).toBeNull();
    expect(sparkGeometry(item([P(0, 10)], 10))).toBeNull();
    expect(changeTone(0)).toBe("neutral");
    expect(sparkGeometry(item([P(0, 10), P(1, 10)], 10))!.tone).toBe("neutral");     // serie plana: no divide por 0
  });
});

describe("staleToRefresh (portada rápida)", () => {
  const ok = { status: "ok" as const, reason: null };
  it("pide otra vez solo las caducadas, una vez por periodo y valor", () => {
    const items = { A: { ...ok, stale: true }, B: ok, C: { ...ok, stale: true } };
    expect(staleToRefresh(items, new Set(), "1D")).toEqual(["A", "C"]);
    expect(staleToRefresh(items, new Set(["1D:A"]), "1D")).toEqual(["C"]);
    expect(staleToRefresh(items, new Set(["1S:A"]), "1D")).toEqual(["A", "C"]);
    expect(staleToRefresh({ B: ok }, new Set(), "1D")).toEqual([]);
  });
});
