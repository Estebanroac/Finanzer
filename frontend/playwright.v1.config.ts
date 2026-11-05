import { defineConfig, devices } from "@playwright/test";

// Verificación V1 de la v4: el panel completo sin red, en el build de producción tal como lo sirve el backend (el
// replay sirve frontend/out y la API en el mismo origen; antes, `npm run build`). Un proyecto por navegador y tamaño
// (3 × 4); cada test recorre la historia y las 9 páginas de un ticker en un tema. `npm run e2e:v1`, repartido con
// --shard o --project; la matriz sale de `node scripts/v1-matriz.mjs` (docs/rediseno/verificacion/V1_matriz.md).
const REPLAY_PORT = Number(process.env.REPLAY_PORT || 8767);
const PYTHON = "/Users/joseestebanroa/Downloads/Finanzer/finanzer_next/.venv313/bin/python";

// 1024 (cierre de la v4): el escritorio estrecho, donde las marcas de las escalas pasan a leyenda (scaleFit.ts).
const SIZES = {
  1440: { viewport: { width: 1440, height: 900 } },
  1024: { viewport: { width: 1024, height: 768 } },
  768: { viewport: { width: 768, height: 1024 } },
  375: { viewport: { width: 375, height: 812 } },
} as const;
// Táctil y visor móvil donde el motor lo emula (Chromium y WebKit); Firefox no admite isMobile.
const touch = (w: number) => (w < 1024 ? { isMobile: true, hasTouch: true } : {});

const projects = ([1440, 1024, 768, 375] as const).flatMap((w) => [
  { name: `chromium-${w}`, use: { ...devices["Desktop Chrome"], ...SIZES[w], ...touch(w) } },
  { name: `webkit-${w}`, use: { ...devices["Desktop Safari"], ...SIZES[w], ...touch(w) } },
  { name: `firefox-${w}`, use: { ...devices["Desktop Firefox"], ...SIZES[w] } },
]);

export default defineConfig({
  globalSetup: "./e2e/global-setup.ts",
  testDir: "./e2e/v1",
  timeout: 300_000,
  workers: Number(process.env.V1_WORKERS || 4),
  reporter: [["line"]],
  use: { baseURL: `http://localhost:${REPLAY_PORT}` },
  projects,
  webServer: [{
    command: `cd ../backend && ${PYTHON} tests/replay_server.py --env panel --port ${REPLAY_PORT}`,
    port: REPLAY_PORT,
    reuseExistingServer: true,
    timeout: 120_000,
  }],
});
