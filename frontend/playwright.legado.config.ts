import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

// Verificación de la v4 (V5): la web actual frente a main, siempre sobre lo que sirve el backend (el replay sirve
// frontend/out y la API en el mismo origen). Ver e2e/legado/web-actual.spec.ts.
const REPLAY_PORT = Number(process.env.REPLAY_PORT || 8767);
export default defineConfig({
  ...base,
  testDir: "./e2e/legado",
  testIgnore: [],
  workers: 1,
  use: { ...base.use, baseURL: `http://localhost:${REPLAY_PORT}` },
  webServer: Array.isArray(base.webServer) ? base.webServer.slice(0, 1) : base.webServer,
  snapshotPathTemplate: ".legacy-snapshots/{arg}-{projectName}{ext}",
});
