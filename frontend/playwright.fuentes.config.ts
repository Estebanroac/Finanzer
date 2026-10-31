import { defineConfig, devices } from "@playwright/test";

// Verificación de la v4 (V2 · fuentes reales): contra un backend real ya en marcha (FR_BASE), sin servidor propio.
export default defineConfig({
  testDir: "./e2e/fuentes-reales",
  timeout: 20 * 60_000,
  workers: Number(process.env.FR_WORKERS || 2),
  use: { baseURL: process.env.FR_BASE || "http://127.0.0.1:8771" },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
});
