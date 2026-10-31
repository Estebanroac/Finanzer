/**
 * V4 (PM): el ritmo de la pantalla de carga. Cinco estaciones que duran exactamente lo mismo mientras se calcula, para
 * que se perciba trabajo rápido y ordenado en cada área. Módulo puro (sin React ni reloj): el componente le pasa el
 * tiempo (ms desde que empezó la petición) y cuándo llegó el análisis.
 *
 *  - Cada estación dura `d = T_est / 5` y su tramo de la barra se llena de forma lineal en `d`. La última, al mismo
 *    ritmo, se queda en `stallFill` (95 %) hasta que hay datos.
 *  - Si el análisis llega antes, la estación en curso y las que faltan se completan a `fastMs` cada una (la en curso,
 *    desde donde estaba, en `fastMs` o en lo que le quedaba a su ritmo si es menos) y después viene la disolución:
 *    las cinco pasan rápidas y parejas, sin saltos.
 *  - Si se llega al final de la última sin datos, su tramo se queda en `stallFill` (95 %) y el título pasa a «Últimos
 *    ajustes…», hasta que llegue o hasta el tiempo agotado, que lleva al estado de error (`fetchAnalysisV2`). T_est es
 *    el p95 medido: esa espera es solo del 5 % más lento.
 */
export interface PaceConfig {
  stations: number;
  /** T_est: tiempo estimado de un análisis sin caché (ms). */
  expectedMs: number;
  /** Duración de cada estación que queda cuando el análisis ya llegó (ms). */
  fastMs: number;
  /** Relleno de la última estación mientras espera (0–1). */
  stallFill: number;
}

export interface PaceState {
  /** Estación en curso (0…stations−1). */
  index: number;
  /** Comienzo y duración de la estación en curso (ms). */
  start: number;
  duration: number;
  /** Relleno de la estación en curso cuando empezó su tramo actual (0, o donde estaba al llegar el análisis). */
  base: number;
  /** El análisis ya llegó: lo que queda va a `fastMs`. */
  fast: boolean;
  /** La última estación llegó a su fin sin datos («Últimos ajustes…»). */
  stalled: boolean;
  /** Las cinco completas (con datos): toca disolver. */
  done: boolean;
  /** Cuándo terminó cada estación (ms), para las pruebas y para medir. */
  ends: number[];
}

export function startPace(cfg: PaceConfig, at = 0): PaceState {
  return { index: 0, start: at, duration: cfg.expectedMs / cfg.stations, base: 0, fast: false, stalled: false, done: false, ends: [] };
}

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const isLast = (s: PaceState, cfg: PaceConfig) => s.index === cfg.stations - 1;

/** Relleno (0–1) de la estación en curso en el instante `now`: lineal desde `base` hasta el tramo entero; la última,
 *  sin datos, como mucho `stallFill`. */
export function stationFill(s: PaceState, cfg: PaceConfig, now: number): number {
  if (s.done) return 1;
  if (s.stalled) return cfg.stallFill;
  const t = s.duration > 0 ? clamp01((now - s.start) / s.duration) : 1;
  const raw = s.base + (1 - s.base) * t;
  return isLast(s, cfg) && !s.fast ? Math.min(raw, cfg.stallFill) : raw;
}

/** El estado en el instante `now`, sabiendo cuándo llegó el análisis (`arrivedAt`, o null si aún no). */
export function advance(prev: PaceState, cfg: PaceConfig, now: number, arrivedAt: number | null): PaceState {
  const s: PaceState = { ...prev, ends: [...prev.ends] };
  for (;;) {
    if (s.done) return s;
    // llega el análisis durante la estación en curso (o en la espera final): lo que queda, a ritmo rápido
    if (arrivedAt !== null && !s.fast && arrivedAt <= now && (s.stalled || arrivedAt <= s.start + s.duration)) {
      const left = s.start + s.duration - arrivedAt;   // lo que le quedaba a su ritmo
      s.base = stationFill(s, cfg, arrivedAt);
      s.start = arrivedAt;
      s.duration = s.stalled ? cfg.fastMs : Math.min(cfg.fastMs, Math.max(0, left));
      s.fast = true;
      s.stalled = false;
      continue;
    }
    if (s.stalled) return s;
    const end = s.start + s.duration;
    if (now < end) return s;
    if (isLast(s, cfg)) {
      if (s.fast) { s.ends.push(end); s.done = true; return s; }
      s.stalled = true;                              // sin datos al final de la última: espera en el 95 %
      continue;
    }
    s.ends.push(end);
    s.index += 1;
    s.start = end;
    s.base = 0;
    s.duration = s.fast ? cfg.fastMs : cfg.expectedMs / cfg.stations;
  }
}
