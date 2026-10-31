import { describe, expect, it } from "vitest";
import { WEB } from "@/lib/generated/backendConfig";
import { advance, startPace, stationFill, type PaceConfig, type PaceState } from "./loadingPace";

const FRAME = 1000 / 60;
const CFG: PaceConfig = { stations: 5, expectedMs: 8430, fastMs: 180, stallFill: 0.95 };
const T = CFG.expectedMs;
const D = T / CFG.stations;
const LAST = CFG.stations - 1;
const ARRIVE_MS = 1_000;
const HALF = 0.5, ONE_HALF = 1.5;

/** Lo que vería la pantalla, fotograma a fotograma, con el análisis llegando en `arrivedAt` (ms desde la petición). */
function run(arrivedAt: number | null, until: number, cfg = CFG) {
  let s: PaceState = startPace(cfg);
  const frames: Array<{ t: number; index: number; fill: number; stalled: boolean; done: boolean }> = [];
  for (let t = 0; t <= until; t += FRAME) {
    s = advance(s, cfg, t, arrivedAt !== null && t >= arrivedAt ? arrivedAt : null);
    frames.push({ t, index: s.index, fill: stationFill(s, cfg, t), stalled: s.stalled, done: s.done });
    if (s.done) break;
  }
  return { s, frames };
}
/** Duración de cada estación: de su comienzo (0 o el fin de la anterior) a su fin. */
const durations = (ends: number[]) => ends.map((e, i) => e - (i ? ends[i - 1] : 0));

describe("ritmo de la pantalla de carga (V4, PM): cinco estaciones iguales, d = T_est / 5", () => {
  it("T_est sale de la config: el p95 medido (data.toml [web] loading_expected_s)", () => {
    expect(WEB.loading.expectedMs).toBe(CFG.expectedMs);
    expect(WEB.loading.fastMs).toBe(CFG.fastMs);
  });

  it("con datos a 0,5·T: se completan las cinco; la en curso y las que faltan, a d_fast cada una", () => {
    const { s } = run(HALF * T, 20_000);
    expect(s.done).toBe(true);
    const durs = durations(s.ends);
    // 0,5·T cae en la tercera (entre 2d y 3d): las dos primeras duran d; la tercera acaba d_fast después de los datos
    expect(durs[0]).toBeCloseTo(D, 6);
    expect(durs[1]).toBeCloseTo(D, 6);
    expect(s.ends[2]).toBeCloseTo(HALF * T + CFG.fastMs, 6);
    for (const d of durs.slice(3)) expect(d).toBeCloseTo(CFG.fastMs, 6);
  });

  it("con datos a T: cada estación dura d (± 1 fotograma)", () => {
    const { s } = run(T, 20_000);
    expect(s.done).toBe(true);
    for (const d of durations(s.ends)) expect(Math.abs(d - D)).toBeLessThanOrEqual(FRAME);
  });

  it("con datos a 1,5·T: cuatro estaciones de d; la quinta, d hasta el 95 % y la espera con «Últimos ajustes…»", () => {
    const { s, frames } = run(ONE_HALF * T, 20_000);
    expect(s.done).toBe(true);
    const durs = durations(s.ends);
    for (const d of durs.slice(0, LAST)) expect(d).toBeCloseTo(D, 6);
    const stalled = frames.filter((f) => f.index === LAST && f.stalled);
    expect(stalled.length).toBeGreaterThan(0);
    expect(new Set(stalled.map((f) => f.fill))).toEqual(new Set([CFG.stallFill]));
    expect(stalled[0].t).toBeGreaterThanOrEqual(T - FRAME);                     // la espera empieza al final de su d
    expect(s.ends[LAST]).toBeCloseTo(ONE_HALF * T + CFG.fastMs, 6);           // y acaba d_fast después de los datos
    // la barra nunca retrocede
    for (let i = 1; i < frames.length; i++)
      if (frames[i].index === frames[i - 1].index) expect(frames[i].fill).toBeGreaterThanOrEqual(frames[i - 1].fill - 1e-9);
  });

  it("una estación que empieza tarde (pestaña en segundo plano) sigue durando d: sin reajustes", () => {
    let s = startPace(CFG);
    s = advance(s, CFG, 3 * D + 10, null);
    expect(s.index).toBe(3);
    expect(s.duration).toBeCloseTo(D, 6);
  });

  it("cada tramo se llena de forma lineal y la barra no salta al llegar los datos", () => {
    const { frames } = run(ARRIVE_MS, 20_000);
    // hasta que llegan los datos (con T_est de Render, d > ARRIVE_MS: llegan dentro de la primera estación)
    for (const f of frames.filter((x) => x.index === 0 && x.t > 0 && x.t < ARRIVE_MS)) expect(f.fill).toBeCloseTo(f.t / D, 6);
    const at = frames.findIndex((f) => f.t >= ARRIVE_MS);
    expect(Math.abs(frames[at].fill - frames[at - 1].fill)).toBeLessThan(0.1);
  });
});
