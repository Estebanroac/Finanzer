import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

// Verificación de la v4 (V3 · fuentes caídas): las pruebas de e2e/fallos activan un fallo en el servidor de replay
// (POST /__replay/fault, backend/tests/faults.py) y recorren las páginas. Comparten ese estado: un solo worker y en
// orden. Mismos puertos, proyectos y modo de build (E2E_BUILD=1) que playwright.config.ts.
export default defineConfig({
  globalSetup: "./e2e/global-setup.ts",
  ...base,
  testDir: "./e2e/fallos",
  testIgnore: [],
  workers: 1,
  fullyParallel: false,
  timeout: 90_000,
});
