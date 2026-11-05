import { defineConfig, devices } from "@playwright/test";

// Puertos por variable de entorno: dos sesiones pueden probar a la vez (E2a usa los de siempre, 3000/8767; la rama
// v4, por ejemplo, E2E_PORT=3001 REPLAY_PORT=8768).
const REPLAY_PORT = Number(process.env.REPLAY_PORT || 8767);
const E2E_PORT = Number(process.env.E2E_PORT || 3000);
// El entorno virtual de Python vive en el checkout principal (no se copia a los worktrees).
const PYTHON = "/Users/joseestebanroa/Downloads/Finanzer/finanzer_next/.venv313/bin/python";
// Rediseño E4 (Task 5): E2E_BUILD=1 prueba el build de producción tal como lo sirve el backend (frontend/out compilado
// con `npm run build`): sin `next dev`, baseURL = el replay, que sirve out/ y la API en el mismo origen.
const BUILD = process.env.E2E_BUILD === "1";
const replay = {
  command: `cd ../backend && ${PYTHON} tests/replay_server.py --env panel --port ${REPLAY_PORT}`,
  port: REPLAY_PORT,
  reuseExistingServer: true,
  timeout: 120_000,
};

export default defineConfig({
  globalSetup: "./e2e/global-setup.ts",
  testDir: "./e2e",
  // Verificación de la v4 (V3): las pruebas de fuentes caídas cambian el estado del servidor de replay (POST
  // /__replay/fault); van aparte, en serie: `npm run e2e:fallos` (playwright.fallos.config.ts).
  testIgnore: ["**/fallos/**", "**/legado/**", "**/fuentes-reales/**"],
  timeout: 60_000,
  use: { baseURL: `http://localhost:${BUILD ? REPLAY_PORT : E2E_PORT}` },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    // Móvil al mismo nivel (E4 Task 3): Android (Chromium, «mobile»), iPhone (WebKit) y tableta (iPad, 768 px).
    { name: "mobile", use: { ...devices["Pixel 7"], viewport: { width: 375, height: 812 } } },
    { name: "mobile-webkit", use: { ...devices["iPhone 15"] } },
    { name: "tablet", use: { ...devices["iPad Mini"] } },
  ],
  webServer: BUILD ? [replay] : [
    replay,
    {
      command: `NEXT_PUBLIC_API_URL=http://localhost:${REPLAY_PORT} npx next dev -p ${E2E_PORT}`,
      port: E2E_PORT,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
