import { defineConfig, devices } from "@playwright/test";

// V4b · 3 (sin lag, medido): rendimiento contra el build de producción (frontend/out, `npm run build`) servido por el
// replay, como en producción. Chromium con la CPU 4 veces más lenta (portátil modesto; la ralentización la pone la
// prueba con CDP) en escritorio y en móvil, y WebKit (sin ralentización: no la permite). Umbrales en la config
// (backend/config/data.toml [web] perf_*). En serie: las medidas no compiten por la CPU.
const REPLAY_PORT = Number(process.env.REPLAY_PORT || 8767);
const PYTHON = "/Users/joseestebanroa/Downloads/finanzer_next/.venv313/bin/python";

export default defineConfig({
  testDir: "./e2e/perf",
  timeout: 300_000,
  workers: 1,
  use: { baseURL: `http://localhost:${REPLAY_PORT}` },
  projects: [
    { name: "chromium-x4", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "chromium-movil-x4", use: { ...devices["Pixel 7"], viewport: { width: 375, height: 812 } } },
    { name: "webkit", use: { ...devices["Desktop Safari"], viewport: { width: 1440, height: 900 } } },
  ],
  webServer: [{
    command: `cd ../backend && ${PYTHON} tests/replay_server.py --env panel --port ${REPLAY_PORT}`,
    port: REPLAY_PORT,
    reuseExistingServer: true,
    timeout: 120_000,
  }],
});
