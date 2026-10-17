# Rediseño · Etapa E1: sistema visual y página-historia — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir en `/v2` (solo en local) el sistema visual aprobado y la página-historia de 9 capítulos de una empresa, con los datos que ya calcula el motor, sin tocar el comportamiento de la web actual.

**Architecture:** Una ruta nueva `src/app/v2/[[...symbol]]` del mismo proyecto Next.js, con su propio layout y su hoja de estilos con ámbito (`.fz2`), que consume el mismo `GET /api/analysis/{symbol}` que la web actual. La lógica de presentación (escalas, modelo de capítulos, rentabilidades) vive en funciones puras en `src/v2/lib/` con tests unitarios; los componentes en `src/v2/components/`. Única adición al backend: un endpoint aditivo `GET /api/v2/prices/{symbol}` que expone la serie de precios que el motor ya descarga.

**Tech Stack:** Next.js 16.1.7 (App Router, export estático en producción), React 19.2.3, TypeScript 5, CSS con ámbito (sin Tailwind en `/v2`), Lightweight Charts (TradingView, Apache-2.0) para la gráfica de precio, Vitest + Testing Library (unitarios), Playwright + axe-core (navegador, simetría, capturas, accesibilidad); backend FastAPI/Python 3.13.4 (`.venv313`), pytest.

**Especificación:** `docs/superpowers/specs/2026-10-17-rediseno-experiencia-design.md`. **Maquetas aprobadas:** `docs/rediseno/maquetas/` (abrir en el navegador; son la referencia visual de cada componente).

## Global Constraints

- **Protección (decisión 15):** la web actual no cambia de comportamiento. Solo se permiten estos cambios en archivos compartidos, todos aditivos: `backend/tools/gen_frontend_config.py` y `frontend/src/lib/generated/backendConfig.ts` (nueva exportación `SCORE_BANDS`), `backend/main.py` (un endpoint nuevo bajo `/api/v2/`), `frontend/scripts/check-analysis-literals.mjs` (añadir `/v2` al ámbito), `frontend/package.json` (dependencias de test y scripts). Ningún golden cambia. No se commitea `frontend/out`.
- **Trabajo aislado:** worktree `../finanzer_next-e1`, rama `rediseno/e1-sistema-historia` desde `main`. Sin push, sin merge, sin deploy. Nada se sube sin un "ok, pushea" explícito del usuario.
- **Colores claro:** papel `#F7F6F2`, superficie `#FFFFFF`, línea `#E2E0DA`, tinta `#1B1D1F`, texto 2 `#3A3D40`, texto 3 `#6B6F73`, bien/marca `#16794A`, atención `#B07D1A`, mal `#B4532A`, neutro `#ECEAE4`.
- **Colores oscuro:** fondo `#16181B`, superficie `#1E2124`, línea `#2C3035`, tinta `#E8E6E1`, texto 2 `#C9C7C1`, texto 3 `#8F949A`, bien `#4F9E74`, atención `#C49A45`, mal `#C8775A`, neutro `#262A2E`.
- **Sin neón:** ningún `box-shadow` con color de marca, ningún `filter: drop-shadow`/`glow`, ningún color fuera de los tokens.
- **Tipografía:** Geist (`var(--font-geist)`, ya cargada en el layout raíz); título de capítulo 24, subtítulo 17, lectura 14 / 1.6, etiqueta 10 en versalitas con `letter-spacing: .12em`; cifras `font-variant-numeric: tabular-nums`.
- **Espaciado:** solo 0, 4, 8, 12, 16, 24, 32, 48 px (`--s1`…`--s7`). Rejilla de 12 columnas; capítulos en 2 columnas iguales; tarjetas en filas de igual alto.
- **Escalas:** toda puntuación con su escala y su base; las bandas salen de `backend/config/thresholds.toml` (`[score.quality] bands = [80, 65, 45]`, `[score.price] bands = [65, 45, 30]`) vía el generador, nunca escritas a mano.
- **Nombres técnicos** siempre junto a su lectura en lenguaje llano.
- **Sin literales de análisis** en `/v2` (lo comprueba `check-analysis-literals.mjs`): ningún número como operando de `<`, `<=`, `>`, `>=` (salvo 0), ni en `===`/`!==` (salvo 0 y 1), ni arrays de dos o más números.
- **Precio en móvil:** elemento principal de la cabecera móvil, 24 px, peso 700.
- **Tickers de verificación:** AAPL, JPM, O, NEE, XOM, PLTR, RIVN, BCS (todos en `backend/tests/fixtures/panel/`).
- **Servidor de datos local:** `backend/tests/replay_server.py --env panel --port 8767` (sin red).

## File Structure

```
backend/
  lib/prices_v2.py                 NUEVO  serializa company/market/sector de price_history para la web
  main.py                          +endpoint GET /api/v2/prices/{symbol} (aditivo)
  tools/gen_frontend_config.py     +SCORE_BANDS (aditivo)
  tests/test_prices_v2.py          NUEVO
frontend/
  package.json                     +devDeps (vitest, @testing-library/*, jsdom, @playwright/test, @axe-core/playwright) +dep lightweight-charts +scripts test/e2e
  vitest.config.ts                 NUEVO
  playwright.config.ts             NUEVO
  scripts/check-analysis-literals.mjs  +SCOPE src/app/v2 y src/v2
  scripts/export-v2-fixtures.mjs   NUEVO  exporta JSON de análisis del replay para los tests
  src/lib/generated/backendConfig.ts   regenerado (+SCORE_BANDS)
  src/app/v2/layout.tsx            NUEVO  layout de /v2 con ámbito .fz2 y tema
  src/app/v2/v2.css                NUEVO  tokens, rejilla y componentes de /v2
  src/app/v2/[[...symbol]]/page.tsx        NUEVO
  src/app/v2/[[...symbol]]/StoryPageClient.tsx NUEVO
  src/v2/lib/theme.ts              NUEVO  tema claro/oscuro (preferencia guardada)
  src/v2/lib/scale.ts              NUEVO  modelo de escala de una puntuación
  src/v2/lib/story.ts              NUEVO  modelo de los 9 capítulos desde el análisis
  src/v2/lib/returns.ts            NUEVO  rentabilidad por periodo y base 100
  src/v2/lib/prices.ts             NUEVO  cliente del endpoint de precios
  src/v2/components/TopBar.tsx, CompanyHeader.tsx, ScoreScale.tsx, ChapterBar.tsx,
                    Chapter.tsx, KeyFigures.tsx, PriceChart.tsx, ChapterVisual.tsx  NUEVOS
  src/v2/__fixtures__/*.json       NUEVOS (8 tickers)
  src/v2/**/*.test.ts(x)           NUEVOS (Vitest)
  e2e/v2/*.spec.ts                 NUEVOS (Playwright)
```

---

### Task 0: Worktree y herramientas de test

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`, `frontend/playwright.config.ts`, `frontend/src/v2/lib/smoke.test.ts`

**Interfaces:**
- Produces: scripts `npm run test:v2` (Vitest) y `npm run e2e:v2` (Playwright); alias `@/` → `src/`.

- [ ] **Step 1: Crear el worktree y la rama**

```bash
cd /Users/joseestebanroa/Downloads/finanzer_next
git worktree add ../finanzer_next-e1 -b rediseno/e1-sistema-historia main
cd ../finanzer_next-e1/frontend
npm ci
```
Expected: `node_modules` instalado en el worktree (sin enlaces simbólicos: Turbopack falla con enlaces).

- [ ] **Step 2: Instalar dependencias de test y la librería de gráficas (versiones exactas)**

```bash
npm install --save-dev --save-exact vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @playwright/test @axe-core/playwright
npm install --save-exact lightweight-charts
npx playwright install chromium
```
Expected: `package.json` con versiones sin `^`. Anota en el registro de la sesión la versión instalada de `lightweight-charts` (el código de este plan usa la API v5: `chart.addSeries(LineSeries, …)`; si se instaló una v4, usa `chart.addLineSeries(…)` en Task 6).

- [ ] **Step 3: Añadir los scripts a `frontend/package.json`** (dentro de `"scripts"`, sin tocar los existentes)

```json
"test:v2": "vitest run src/v2",
"e2e:v2": "playwright test e2e/v2"
```

- [ ] **Step 4: Crear `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: {
    environment: "jsdom",
    include: ["src/v2/**/*.test.{ts,tsx}"],
    setupFiles: [],
  },
});
```

- [ ] **Step 5: Crear `frontend/playwright.config.ts`**

```ts
import { defineConfig, devices } from "@playwright/test";

const REPLAY_PORT = 8767;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  use: { baseURL: "http://localhost:3000" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { ...devices["Pixel 7"], viewport: { width: 375, height: 812 } } },
  ],
  webServer: [
    {
      command: `cd ../backend && ../.venv313/bin/python tests/replay_server.py --env panel --port ${REPLAY_PORT}`,
      port: REPLAY_PORT,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: `NEXT_PUBLIC_API_URL=http://localhost:${REPLAY_PORT} npx next dev -p 3000`,
      port: 3000,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
```
Nota: el `.venv313` está en el checkout principal; si en el worktree no existe, usa la ruta absoluta `/Users/joseestebanroa/Downloads/finanzer_next/.venv313/bin/python`.

- [ ] **Step 6: Test de humo `frontend/src/v2/lib/smoke.test.ts`**

```ts
import { describe, it, expect } from "vitest";

describe("entorno de tests de /v2", () => {
  it("ejecuta TypeScript con jsdom", () => {
    expect(typeof document).toBe("object");
  });
});
```

- [ ] **Step 7: Ejecutar**

Run: `npm run test:v2`
Expected: `1 passed`.

- [ ] **Step 8: Comprobar que la web actual sigue igual**

Run: `npm run check`
Expected: sale sin error (contrato y literales de la web actual intactos).

- [ ] **Step 9: Commit**

```bash
git add package.json package-lock.json vitest.config.ts playwright.config.ts src/v2/lib/smoke.test.ts
git commit -m "E1: herramientas de test de /v2 (Vitest, Playwright, axe) y Lightweight Charts"
```

---

### Task 1: Bandas de las puntuaciones en la configuración generada

**Files:**
- Modify: `backend/tools/gen_frontend_config.py` (función `render`)
- Regenerate: `frontend/src/lib/generated/backendConfig.ts`
- Test: `backend/tests/test_frontend_config_sync.py` (existente), `frontend/src/v2/lib/bands.test.ts`

**Interfaces:**
- Produces: `SCORE_BANDS` exportado desde `@/lib/generated/backendConfig`:
  `{ quality: { bands: readonly number[]; labels: readonly string[] }, price: { bands: readonly number[]; labels: readonly string[] } }`, con `bands` en orden descendente (≥) y `labels` de mejor a peor, exactamente como `[score.quality]` y `[score.price]` de `thresholds.toml`.

- [ ] **Step 1: Test que falla `frontend/src/v2/lib/bands.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { SCORE_BANDS } from "@/lib/generated/backendConfig";

describe("SCORE_BANDS (generado desde thresholds.toml)", () => {
  it("trae las bandas y rótulos de calidad del motor", () => {
    expect(SCORE_BANDS.quality.labels).toEqual(["excelente", "sólida", "media", "débil"]);
    expect(SCORE_BANDS.quality.bands.length).toBe(SCORE_BANDS.quality.labels.length - 1);
  });
  it("trae las bandas y rótulos de precio del motor", () => {
    expect(SCORE_BANDS.price.labels).toEqual(["atractivo", "razonable", "exigente", "muy exigente"]);
    expect(SCORE_BANDS.price.bands.length).toBe(SCORE_BANDS.price.labels.length - 1);
  });
});
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `cd frontend && npx vitest run src/v2/lib/bands.test.ts`
Expected: FAIL (`SCORE_BANDS` no exportado).

- [ ] **Step 3: Añadir la exportación al generador** — en `render()` de `backend/tools/gen_frontend_config.py`, antes del `return`, lee las bandas y añádelas al final de la cadena devuelta:

```python
    q, p = cfg("thresholds.score.quality"), cfg("thresholds.score.price")
    score_bands = (
        "\n/** Bandas de las dos puntuaciones (thresholds.toml [score.quality] y [score.price]):\n"
        " *  `bands` de mayor a menor (≥), `labels` de la mejor a la peor. Rediseño /v2. */\n"
        "export const SCORE_BANDS = {\n"
        f"  quality: {{ bands: {_q(q['bands'])}, labels: {_q(q['labels'])} }},\n"
        f"  price: {{ bands: {_q(p['bands'])}, labels: {_q(p['labels'])} }},\n"
        "} as const;\n"
    )
```
y cambia el `return f"""…"""` por `return f"""…""" + score_bands` (el texto existente no cambia). Si `cfg("thresholds.score.quality")` no resuelve, localiza la clave real con `grep -n "score.quality" backend/lib/settings.py backend/config/schema.toml` y usa esa ruta.

- [ ] **Step 4: Regenerar y comprobar sincronía**

Run:
```bash
cd ../backend && ../.venv313/bin/python tools/gen_frontend_config.py && ../.venv313/bin/python tools/gen_frontend_config.py --check && ../.venv313/bin/python -m pytest tests/test_frontend_config_sync.py -q
```
Expected: `sincronizado` y el test pasa.

- [ ] **Step 5: Ejecutar el test de Vitest**

Run: `cd ../frontend && npx vitest run src/v2/lib/bands.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ../backend/tools/gen_frontend_config.py src/lib/generated/backendConfig.ts src/v2/lib/bands.test.ts
git commit -m "E1: bandas de calidad y precio en la configuración generada (SCORE_BANDS)"
```

---

### Task 2: Ruta /v2, layout con ámbito, tokens y tema claro/oscuro

**Files:**
- Create: `frontend/src/app/v2/layout.tsx`, `frontend/src/app/v2/v2.css`, `frontend/src/app/v2/[[...symbol]]/page.tsx`, `frontend/src/app/v2/[[...symbol]]/StoryPageClient.tsx`, `frontend/src/v2/lib/theme.ts`, `frontend/src/v2/components/TopBar.tsx`
- Modify: `frontend/scripts/check-analysis-literals.mjs` (array `SCOPE`)
- Test: `frontend/src/v2/lib/theme.test.ts`, `frontend/e2e/v2/shell.spec.ts`

**Interfaces:**
- Produces: `type Theme = "light" | "dark"`; `readTheme(): Theme`; `writeTheme(t: Theme): void`; componente `TopBar({ symbol, theme, onToggleTheme })`; la página lee el símbolo de la URL `/v2/{SYMBOL}` y llama a `analyzeStock(symbol)` de `@/lib/api`.

- [ ] **Step 1: Test que falla `frontend/src/v2/lib/theme.test.ts`**

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { readTheme, writeTheme } from "./theme";

describe("tema de /v2", () => {
  beforeEach(() => localStorage.clear());
  it("por defecto es claro", () => {
    expect(readTheme()).toBe("light");
  });
  it("recuerda el oscuro", () => {
    writeTheme("dark");
    expect(readTheme()).toBe("dark");
  });
  it("no falla si el almacenamiento lanza", () => {
    const orig = Storage.prototype.getItem;
    Storage.prototype.getItem = () => { throw new Error("bloqueado"); };
    expect(readTheme()).toBe("light");
    Storage.prototype.getItem = orig;
  });
});
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `npx vitest run src/v2/lib/theme.test.ts`
Expected: FAIL (módulo no existe).

- [ ] **Step 3: Implementar `frontend/src/v2/lib/theme.ts`**

```ts
export type Theme = "light" | "dark";
const KEY = "finanzer.v2.theme";

export function readTheme(): Theme {
  try {
    return localStorage.getItem(KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function writeTheme(t: Theme): void {
  try {
    localStorage.setItem(KEY, t);
  } catch {
    /* sin almacenamiento: el tema dura la sesión */
  }
}
```

- [ ] **Step 4: Ejecutar el test**

Run: `npx vitest run src/v2/lib/theme.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Crear `frontend/src/app/v2/v2.css`** (todo bajo `.fz2`; el fondo cubre la página para no heredar el oscuro de `globals.css`)

```css
.fz2 {
  --paper: #F7F6F2; --surface: #FFFFFF; --line: #E2E0DA; --line-soft: #EEECE6;
  --ink: #1B1D1F; --text-2: #3A3D40; --text-3: #6B6F73;
  --good: #16794A; --warn: #B07D1A; --bad: #B4532A; --neutral: #ECEAE4;
  --good-bg: #E8F2EC; --warn-bg: #F6EDD7; --bad-bg: #F7E6DD;
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 24px; --s6: 32px; --s7: 48px;
  --radius: 10px; --max: 1280px;
  min-height: 100vh; background: var(--paper); color: var(--ink);
  font-family: var(--font-geist), system-ui, sans-serif; font-size: 14px; line-height: 1.6;
}
.fz2[data-theme="dark"] {
  --paper: #16181B; --surface: #1E2124; --line: #2C3035; --line-soft: #262A2E;
  --ink: #E8E6E1; --text-2: #C9C7C1; --text-3: #8F949A;
  --good: #4F9E74; --warn: #C49A45; --bad: #C8775A; --neutral: #262A2E;
  --good-bg: #22332A; --warn-bg: #3A3220; --bad-bg: #3A2820;
}
.fz2 * { box-sizing: border-box; }
.fz2 .num { font-variant-numeric: tabular-nums; }
.fz2 .eyebrow { font-size: 10px; letter-spacing: .12em; text-transform: uppercase; color: var(--text-3); }
.fz2 .wrap { max-width: var(--max); margin: 0 auto; padding: 0 var(--s5); }
.fz2 .surface { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.fz2 .tone-good { color: var(--good); } .fz2 .tone-warn { color: var(--warn); }
.fz2 .tone-bad { color: var(--bad); } .fz2 .tone-neutral { color: var(--text-2); }
.fz2 .pill { display: inline-block; border-radius: 999px; padding: 2px var(--s2); font-size: 11px; font-weight: 600; }
.fz2 .pill.good { background: var(--good-bg); color: var(--good); }
.fz2 .pill.warn { background: var(--warn-bg); color: var(--warn); }
.fz2 .pill.bad { background: var(--bad-bg); color: var(--bad); }
.fz2 .pill.neutral { background: var(--neutral); color: var(--text-2); }
/* Barra general */
.fz2 .topbar { background: var(--surface); border-bottom: 1px solid var(--line); }
.fz2 .topbar .wrap { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: var(--s4); height: 56px; }
.fz2 .brand { font-weight: 700; color: var(--good); text-decoration: none; }
.fz2 .topbar .actions { display: flex; justify-content: flex-end; gap: var(--s2); }
.fz2 .btn { background: var(--surface); color: var(--ink); border: 1px solid var(--line); border-radius: 8px; padding: var(--s1) var(--s3); font: inherit; cursor: pointer; }
.fz2 .btn:focus-visible, .fz2 a:focus-visible { outline: 2px solid var(--good); outline-offset: 2px; }
.fz2 .search { width: 360px; max-width: 100%; background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: var(--s1) var(--s3); color: var(--ink); font: inherit; }
@media (prefers-reduced-motion: reduce) { .fz2 * { transition: none !important; animation: none !important; } }
@media (max-width: 767px) { .fz2 .wrap { padding: 0 var(--s4); } .fz2 .search { display: none; } }
```

- [ ] **Step 6: Crear `frontend/src/app/v2/layout.tsx`**

```tsx
import "./v2.css";

export default function V2Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
```
(El elemento `.fz2` con `data-theme` lo pone `StoryPageClient`, que conoce el tema del usuario.)

- [ ] **Step 7: Crear `frontend/src/v2/components/TopBar.tsx`**

```tsx
"use client";
import Link from "next/link";
import { pdfUrl } from "@/lib/api";
import type { Theme } from "@/v2/lib/theme";

export default function TopBar({ symbol, theme, onToggleTheme }: {
  symbol: string | null; theme: Theme; onToggleTheme: () => void;
}) {
  return (
    <header className="topbar">
      <div className="wrap">
        <Link className="brand" href="/v2">Finanzer</Link>
        <input className="search" placeholder="Buscar empresa o ticker…" aria-label="Buscar empresa o ticker" />
        <div className="actions">
          <button className="btn" onClick={onToggleTheme} aria-pressed={theme === "dark"}>
            {theme === "dark" ? "Modo claro" : "Modo oscuro"}
          </button>
          {symbol && <a className="btn" href={pdfUrl(symbol)}>Descargar PDF</a>}
        </div>
      </div>
    </header>
  );
}
```
(El buscador funcional llega en E4; en E1 es el campo visual.)

- [ ] **Step 8: Crear `frontend/src/app/v2/[[...symbol]]/page.tsx`** (mismo patrón de export estático que `/stock`)

```tsx
import StoryPageClient from "./StoryPageClient";

export async function generateStaticParams() {
  return [{ symbol: [] }];
}

export default function V2StockPage() {
  return <StoryPageClient />;
}
```

- [ ] **Step 9: Crear `frontend/src/app/v2/[[...symbol]]/StoryPageClient.tsx`** (versión inicial; Task 5 añade los capítulos)

```tsx
"use client";
import { useEffect, useState } from "react";
import { analyzeStock, type StockAnalysis } from "@/lib/api";
import { readTheme, writeTheme, type Theme } from "@/v2/lib/theme";
import TopBar from "@/v2/components/TopBar";

function symbolFromPath(): string | null {
  const parts = window.location.pathname.split("/").filter(Boolean);
  return parts.length > 1 ? decodeURIComponent(parts[1]).toUpperCase() : null;
}

export default function StoryPageClient() {
  const [theme, setTheme] = useState<Theme>("light");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [data, setData] = useState<StockAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTheme(readTheme());
    const s = symbolFromPath();
    setSymbol(s);
    if (s) analyzeStock(s).then(setData).catch((e: Error) => setError(e.message));
  }, []);

  const toggle = () => {
    const t: Theme = theme === "dark" ? "light" : "dark";
    setTheme(t);
    writeTheme(t);
  };

  return (
    <div className="fz2" data-theme={theme}>
      <TopBar symbol={symbol} theme={theme} onToggleTheme={toggle} />
      <main className="wrap" aria-busy={!data && !error}>
        {error && <p role="alert">{error}</p>}
        {!error && !data && <p className="eyebrow">Analizando {symbol ?? ""}…</p>}
        {data && <h1 data-testid="company-name">{data.profile.name}</h1>}
      </main>
    </div>
  );
}
```

- [ ] **Step 10: Añadir `/v2` al guardián de literales** — en `frontend/scripts/check-analysis-literals.mjs`, añade al final del array `SCOPE`:

```js
  "src/app/v2",
  "src/v2/lib",
  "src/v2/components",
```

- [ ] **Step 11: Test de navegador `frontend/e2e/v2/shell.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test("la página /v2 de AAPL carga el nombre de la empresa en tema claro", async ({ page }) => {
  await page.goto("/v2/AAPL");
  await expect(page.getByTestId("company-name")).toHaveText("Apple Inc.", { timeout: 30_000 });
  const bg = await page.locator(".fz2").evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).toBe("rgb(247, 246, 242)");
});

test("el conmutador cambia a oscuro", async ({ page }) => {
  await page.goto("/v2/AAPL");
  await page.getByRole("button", { name: "Modo oscuro" }).click();
  await expect(page.locator(".fz2")).toHaveAttribute("data-theme", "dark");
});
```

- [ ] **Step 12: Ejecutar**

Run: `npm run test:v2 && npx playwright test e2e/v2/shell.spec.ts --project=desktop && npm run check`
Expected: Vitest en verde; 2 tests de Playwright PASS; `npm run check` sin error.

- [ ] **Step 13: Commit**

```bash
git add src/app/v2 src/v2/lib/theme.ts src/v2/lib/theme.test.ts src/v2/components/TopBar.tsx e2e/v2/shell.spec.ts scripts/check-analysis-literals.mjs
git commit -m "E1: ruta /v2 con layout propio, tokens claro/oscuro y barra general"
```

---

### Task 3: Fixtures de los 8 tickers y modelo de escala de una puntuación

**Files:**
- Create: `frontend/scripts/export-v2-fixtures.mjs`, `frontend/src/v2/__fixtures__/{AAPL,JPM,O,NEE,XOM,PLTR,RIVN,BCS}.json`, `frontend/src/v2/lib/scale.ts`
- Test: `frontend/src/v2/lib/scale.test.ts`

**Interfaces:**
- Consumes: `SCORE_BANDS` (Task 1).
- Produces:
  ```ts
  type ScaleKind = "quality" | "price";
  interface ScaleSegment { label: string; from: number; to: number; widthPct: number; tone: "good" | "warn" | "bad" | "neutral" }
  interface ScaleModel { kind: ScaleKind; score: number | null; level: string | null; segments: ScaleSegment[]; pinPct: number | null }
  function buildScale(kind: ScaleKind, score: number | null, level: string | null): ScaleModel
  ```
  Segmentos ordenados de peor (izquierda, 0) a mejor (derecha, 100); `widthPct` suma 100.

- [ ] **Step 1: Script `frontend/scripts/export-v2-fixtures.mjs`**

```js
#!/usr/bin/env node
// Exporta el análisis completo de los 8 tickers de verificación desde el servidor de replay
// (backend/tests/replay_server.py --env panel --port 8767) a src/v2/__fixtures__/.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "src/v2/__fixtures__");
const BASE = process.env.REPLAY_URL || "http://localhost:8767";
const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];

fs.mkdirSync(OUT, { recursive: true });
for (const t of TICKERS) {
  const res = await fetch(`${BASE}/api/analysis/${t}`);
  if (!res.ok) throw new Error(`${t}: HTTP ${res.status}`);
  fs.writeFileSync(path.join(OUT, `${t}.json`), JSON.stringify(await res.json(), null, 1));
  console.log(`ok ${t}`);
}
```

- [ ] **Step 2: Exportar los fixtures** (en otra terminal, levanta el replay)

```bash
cd ../backend && ../.venv313/bin/python tests/replay_server.py --env panel --port 8767 &
cd ../frontend && node scripts/export-v2-fixtures.mjs
```
Expected: `ok AAPL` … `ok BCS` y 8 archivos en `src/v2/__fixtures__/`.

- [ ] **Step 3: Test que falla `frontend/src/v2/lib/scale.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { buildScale } from "./scale";

describe("buildScale", () => {
  it("calidad 79: cuatro tramos con las bandas del motor y la marca en 79", () => {
    const m = buildScale("quality", 79, "sólida");
    expect(m.segments.map((s) => s.label)).toEqual(["débil", "media", "sólida", "excelente"]);
    expect(m.segments.map((s) => s.widthPct)).toEqual([45, 20, 15, 20]);
    expect(m.pinPct).toBe(79);
    expect(m.segments.reduce((a, s) => a + s.widthPct, 0)).toBe(100);
  });
  it("precio 10: muy exigente a la izquierda, atractivo a la derecha", () => {
    const m = buildScale("price", 10, "muy exigente");
    expect(m.segments.map((s) => s.label)).toEqual(["muy exigente", "exigente", "razonable", "atractivo"]);
    expect(m.segments.map((s) => s.widthPct)).toEqual([30, 15, 20, 35]);
    expect(m.segments[0].tone).toBe("bad");
    expect(m.segments[3].tone).toBe("good");
  });
  it("sin puntuación: sin marca", () => {
    expect(buildScale("quality", null, null).pinPct).toBeNull();
  });
});
```

- [ ] **Step 4: Ejecutar y ver que falla**

Run: `npx vitest run src/v2/lib/scale.test.ts`
Expected: FAIL (módulo no existe).

- [ ] **Step 5: Implementar `frontend/src/v2/lib/scale.ts`** (sin literales de corte: todo sale de `SCORE_BANDS`)

```ts
import { SCORE_BANDS } from "@/lib/generated/backendConfig";

export type ScaleKind = "quality" | "price";
export type ScaleTone = "good" | "warn" | "bad" | "neutral";
export interface ScaleSegment { label: string; from: number; to: number; widthPct: number; tone: ScaleTone }
export interface ScaleModel { kind: ScaleKind; score: number | null; level: string | null; segments: ScaleSegment[]; pinPct: number | null }

const FULL = 100;

/** Tono de cada tramo, del peor (índice 0) al mejor (último). */
function toneFor(index: number, count: number): ScaleTone {
  if (index === 0) return "bad";
  if (index === count - 1) return "good";
  return index === 1 ? "warn" : "neutral";
}

export function buildScale(kind: ScaleKind, score: number | null, level: string | null): ScaleModel {
  const { bands, labels } = SCORE_BANDS[kind];
  // bands: de mayor a menor (≥); labels: de mejor a peor. Se recorren de peor a mejor.
  const cuts = [...bands].reverse();            // ascendente
  const names = [...labels].reverse();           // de peor a mejor
  const edges = [0, ...cuts, FULL];
  const segments: ScaleSegment[] = names.map((label, i) => ({
    label,
    from: edges[i],
    to: edges[i + 1],
    widthPct: edges[i + 1] - edges[i],
    tone: toneFor(i, names.length),
  }));
  return { kind, score, level, segments, pinPct: score === null ? null : Math.min(Math.max(score, 0), FULL) };
}
```
Nota: `[0, ...cuts, FULL]` no es un array de números literales (solo el `0`), así que pasa el guardián de literales.

- [ ] **Step 6: Ejecutar**

Run: `npx vitest run src/v2/lib/scale.test.ts && npm run check`
Expected: PASS (3 tests) y `check` sin error.

- [ ] **Step 7: Commit**

```bash
git add scripts/export-v2-fixtures.mjs src/v2/__fixtures__ src/v2/lib/scale.ts src/v2/lib/scale.test.ts
git commit -m "E1: fixtures de 8 tickers y modelo de escala de las puntuaciones"
```

---

### Task 4: Cabecera de empresa con escalas y desglose (maqueta 2c)

**Files:**
- Create: `frontend/src/v2/components/ScoreScale.tsx`, `frontend/src/v2/components/CompanyHeader.tsx`
- Modify: `frontend/src/app/v2/v2.css` (añadir estilos de cabecera), `frontend/src/app/v2/[[...symbol]]/StoryPageClient.tsx`
- Test: `frontend/src/v2/components/CompanyHeader.test.tsx`

**Interfaces:**
- Consumes: `buildScale` (Task 3); `StockAnalysis` de `@/lib/api` (`profile`, `price`, `display.cover.quality`, `display.cover.price`, `display.cover.categories`, `display.confidence`).
- Produces: `CompanyHeader({ analysis }: { analysis: StockAnalysis })`; `ScoreScale({ model, question, base, breakdown })`.

- [ ] **Step 1: Test que falla `frontend/src/v2/components/CompanyHeader.test.tsx`**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CompanyHeader from "./CompanyHeader";
import AAPL from "@/v2/__fixtures__/AAPL.json";
import type { StockAnalysis } from "@/lib/api";

describe("CompanyHeader (AAPL)", () => {
  it("muestra precio, las dos puntuaciones con su escala y la confianza", () => {
    render(<CompanyHeader analysis={AAPL as unknown as StockAnalysis} />);
    expect(screen.getByTestId("price").textContent).toMatch(/^\$\d/);
    const q = screen.getByTestId("score-quality");
    expect(q.textContent).toContain("/ 100");
    expect(q.querySelectorAll("[data-segment]").length).toBe(4);
    expect(screen.getByTestId("score-price").querySelectorAll("[data-segment]").length).toBe(4);
    expect(screen.getByTestId("confidence").textContent?.length).toBeGreaterThan(0);
  });
  it("el desglose de calidad lista sus categorías con puntos sobre 20", () => {
    render(<CompanyHeader analysis={AAPL as unknown as StockAnalysis} />);
    const rows = screen.getByTestId("breakdown-quality").querySelectorAll("tr[data-cat]");
    expect(rows.length).toBe(4);
  });
});
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `npx vitest run src/v2/components/CompanyHeader.test.tsx`
Expected: FAIL (componentes no existen).

- [ ] **Step 3: Implementar `frontend/src/v2/components/ScoreScale.tsx`**

```tsx
import type { ScaleModel } from "@/v2/lib/scale";

export interface BreakdownRow { name: string; score: number; max: number }

export default function ScoreScale({ model, title, question, base, display, breakdown, testId }: {
  model: ScaleModel; title: string; question: string; base: string; display: string;
  breakdown: BreakdownRow[] | null; testId: string;
}) {
  const tone = model.segments.find((s) => model.pinPct !== null && model.pinPct >= s.from && model.pinPct <= s.to)?.tone ?? "neutral";
  return (
    <div className="score surface" data-testid={testId} tabIndex={0} aria-describedby={`${testId}-bd`}>
      <div className="eyebrow">{title} · {question}</div>
      <div className="score-value"><span className={`big num tone-${tone}`}>{display}</span>
        {model.score !== null && <span className="muted"> / 100 · {model.level}</span>}</div>
      <div className="scale" style={{ gridTemplateColumns: model.segments.map((s) => `${s.widthPct}fr`).join(" ") }}>
        {model.segments.map((s) => <div key={s.label} data-segment className={`seg ${s.tone}`} />)}
        {model.pinPct !== null && <span className="pin" style={{ left: `${model.pinPct}%` }} aria-hidden />}
      </div>
      <div className="ticks" style={{ gridTemplateColumns: model.segments.map((s) => `${s.widthPct}fr`).join(" ") }}>
        {model.segments.map((s) => <span key={s.label}>{s.label}</span>)}
      </div>
      <div className="muted base">{base}</div>
      {breakdown && (
        <div className="breakdown surface" id={`${testId}-bd`} role="tooltip" data-testid={`breakdown-${model.kind}`}>
          <table className="num"><tbody>
            {breakdown.map((r) => <tr key={r.name} data-cat><td>{r.name}</td><td>{r.score} / {r.max}</td></tr>)}
          </tbody></table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Implementar `frontend/src/v2/components/CompanyHeader.tsx`**

```tsx
import type { StockAnalysis } from "@/lib/api";
import { buildScale } from "@/v2/lib/scale";
import ScoreScale from "./ScoreScale";

export default function CompanyHeader({ analysis }: { analysis: StockAnalysis }) {
  const cover = analysis.display.cover;
  const q = cover.quality, p = cover.price;
  const qualityCats = cover.categories.flatMap((c) => c.items).filter((i) => i.applicable && i.name !== "Valoración");
  const conf = analysis.display.confidence;
  return (
    <section className="company-header" aria-label="Resumen de la empresa">
      <div className="ident">
        <div className="muted"><b className="name">{analysis.profile.name}</b> · {analysis.symbol} · {analysis.profile.exchange} · {analysis.profile.sector} · {analysis.profile.industry}</div>
        <div className="price-line"><span className="price num" data-testid="price">{analysis.price !== null ? `$${analysis.price.toFixed(2)}` : "—"}</span></div>
      </div>
      <div className="scores">
        <ScoreScale testId="score-quality" model={buildScale("quality", q.score, q.level)} title={q.title} question={q.question}
          display={q.score === null ? "—" : String(q.score)} base={q.note ?? "4 categorías × 20 puntos"}
          breakdown={qualityCats.map((c) => ({ name: c.name, score: c.score, max: c.max }))} />
        <ScoreScale testId="score-price" model={buildScale("price", p.score, p.level)} title={p.title} question={p.question}
          display={p.score === null ? "—" : String(p.score)} base={p.note ?? "Múltiplos frente a la referencia + DCF"}
          breakdown={null} />
        <div className="score surface" data-testid="confidence">
          <div className="eyebrow">Confianza del veredicto · ¿cuánto fiarse?</div>
          <div className="score-value"><span className="big">{conf?.level ?? "—"}</span></div>
          <div className="muted base">{conf?.summary ?? cover.verdict.confidence_text ?? ""}</div>
        </div>
      </div>
    </section>
  );
}
```
Notas: `q.title`, `q.question` y `q.note` vienen del motor (`ScoreBlock`); el texto de respaldo solo se usa si llegan vacíos. La variación del día no existe aún en el análisis: se añade en E2 (dato 1); en E1 no se muestra un hueco por ella.

- [ ] **Step 5: Estilos de cabecera** — añade a `frontend/src/app/v2/v2.css`:

```css
.fz2 .muted { color: var(--text-3); }
.fz2 .company-header { padding: var(--s5) 0; display: grid; gap: var(--s4); }
.fz2 .company-header .name { color: var(--ink); font-size: 17px; }
.fz2 .price { font-size: 24px; font-weight: 700; letter-spacing: -.01em; }
.fz2 .scores { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s4); align-items: stretch; }
.fz2 .score { padding: var(--s3) var(--s4); position: relative; display: flex; flex-direction: column; gap: var(--s1); }
.fz2 .score .big { font-size: 24px; font-weight: 650; }
.fz2 .scale { display: grid; gap: 2px; position: relative; margin-top: var(--s2); }
.fz2 .scale .seg { height: 6px; border-radius: 2px; }
.fz2 .seg.bad { background: var(--bad-bg); } .fz2 .seg.warn { background: var(--warn-bg); }
.fz2 .seg.neutral { background: var(--neutral); } .fz2 .seg.good { background: var(--good-bg); }
.fz2 .scale .pin { position: absolute; top: -4px; width: 2px; height: 14px; background: var(--ink); transform: translateX(-1px); }
.fz2 .ticks { display: grid; font-size: 10px; color: var(--text-3); text-align: center; }
.fz2 .breakdown { display: none; position: absolute; z-index: 5; top: 100%; left: 0; margin-top: var(--s2); padding: var(--s3); min-width: 260px; }
.fz2 .score:hover .breakdown, .fz2 .score:focus-within .breakdown, .fz2 .score:focus .breakdown { display: block; }
.fz2 .breakdown td { padding: var(--s1) 0; border-bottom: 1px solid var(--line-soft); }
.fz2 .breakdown td + td { text-align: right; }
@media (max-width: 767px) {
  .fz2 .scores { grid-template-columns: 1fr; }
}
```
Nota: en el móvil la `.price` mantiene 24 px y peso 700 (decisión 13): es el elemento más grande de la cabecera.

- [ ] **Step 6: Montar la cabecera** — en `StoryPageClient.tsx`, cambia la línea `{data && <h1 …>}` por:

```tsx
        {data && (<>
          <h1 data-testid="company-name" className="sr-only">{data.profile.name}</h1>
          <CompanyHeader analysis={data} />
        </>)}
```
añade `import CompanyHeader from "@/v2/components/CompanyHeader";` y en `v2.css`:
```css
.fz2 .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
```

- [ ] **Step 7: Ejecutar**

Run: `npx vitest run src/v2 && npx playwright test e2e/v2/shell.spec.ts --project=desktop && npm run check`
Expected: todo en verde.

- [ ] **Step 8: Commit**

```bash
git add src/v2/components/ScoreScale.tsx src/v2/components/CompanyHeader.tsx src/v2/components/CompanyHeader.test.tsx src/app/v2
git commit -m "E1: cabecera con precio, puntuaciones con escala y desglose, y confianza"
```

---

### Task 5: Modelo de la historia y los 9 capítulos

**Files:**
- Create: `frontend/src/v2/lib/story.ts`, `frontend/src/v2/components/ChapterBar.tsx`, `frontend/src/v2/components/Chapter.tsx`, `frontend/src/v2/components/KeyFigures.tsx`, `frontend/src/v2/components/ChapterVisual.tsx`
- Modify: `frontend/src/app/v2/v2.css`, `frontend/src/app/v2/[[...symbol]]/StoryPageClient.tsx`
- Test: `frontend/src/v2/lib/story.test.ts`, `frontend/src/v2/components/Chapter.test.tsx`

**Interfaces:**
- Consumes: `StockAnalysis` (`profile`, `price`, `yearly_financials`, `display.cover`, `display.sections.*`, `display.charts.comparison`, `display.confidence`).
- Produces:
  ```ts
  type ChapterId = "empresa" | "negocio" | "accion" | "calidad" | "valor" | "rivales" | "riesgos" | "actualidad" | "conclusion";
  interface KeyFigure { label: string; value: string; tone: "good" | "warn" | "bad" | "neutral" }
  type Visual =
    | { kind: "facts"; rows: Array<{ label: string; value: string }> }
    | { kind: "bars"; rows: Array<{ label: string; score: number; max: number; tone: "good" | "warn" | "bad" | "neutral" }> }
    | { kind: "price"; range52: { pos: number; low: string; high: string; caption: string } | null }
    | { kind: "list"; items: Array<{ title: string; text: string; tone: "good" | "warn" | "bad" | "neutral" }> }
    | { kind: "news"; items: Array<{ date: string | null; source: string | null; headline: string; url: string | null }> }
    | { kind: "verdict"; quality: string; price: string; confidence: string };
  interface ChapterModel { id: ChapterId; index: number; navLabel: string; eyebrow: string; title: string; lead: string; figures: KeyFigure[]; visual: Visual; moreLabel: string }
  const CHAPTER_ORDER: ChapterId[];
  function buildStory(a: StockAnalysis): ChapterModel[]
  ```
  Reglas: siempre 9 capítulos en `CHAPTER_ORDER`; cada uno con `lead` no vacío y `figures` de longitud 3 (si un dato falta, la figura dice "Sin dato" con tono `neutral`, nunca un hueco).

- [ ] **Step 1: Test que falla `frontend/src/v2/lib/story.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { buildStory, CHAPTER_ORDER } from "./story";
import type { StockAnalysis } from "@/lib/api";

const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"] as const;

describe.each(TICKERS)("buildStory(%s)", (t) => {
  it("da 9 capítulos completos, en orden y sin huecos", async () => {
    const a = (await import(`@/v2/__fixtures__/${t}.json`)).default as unknown as StockAnalysis;
    const story = buildStory(a);
    expect(story.map((c) => c.id)).toEqual(CHAPTER_ORDER);
    for (const c of story) {
      expect(c.lead.trim().length, `${t}/${c.id} lead`).toBeGreaterThan(0);
      expect(c.figures.length, `${t}/${c.id} figuras`).toBe(3);
      for (const f of c.figures) expect(f.value.trim().length, `${t}/${c.id}/${f.label}`).toBeGreaterThan(0);
    }
  });
});

describe("buildStory(AAPL) contenido", () => {
  it("el capítulo de calidad trae las 4 categorías y el de conclusión el veredicto", async () => {
    const a = (await import("@/v2/__fixtures__/AAPL.json")).default as unknown as StockAnalysis;
    const s = buildStory(a);
    const cal = s.find((c) => c.id === "calidad")!;
    expect(cal.visual.kind).toBe("bars");
    if (cal.visual.kind === "bars") expect(cal.visual.rows.length).toBe(4);
    expect(s.find((c) => c.id === "conclusion")!.lead).toContain(a.display.cover.verdict.text);
  });
});
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `npx vitest run src/v2/lib/story.test.ts`
Expected: FAIL (módulo no existe).

- [ ] **Step 3: Implementar `frontend/src/v2/lib/story.ts`**

```ts
import type { StockAnalysis, Tone, Row, Kpi } from "@/lib/api";

export type ChapterId = "empresa" | "negocio" | "accion" | "calidad" | "valor" | "rivales" | "riesgos" | "actualidad" | "conclusion";
export type VTone = "good" | "warn" | "bad" | "neutral";
export interface KeyFigure { label: string; value: string; tone: VTone }
export type Visual =
  | { kind: "facts"; rows: Array<{ label: string; value: string }> }
  | { kind: "bars"; rows: Array<{ label: string; score: number; max: number; tone: VTone }> }
  | { kind: "price"; range52: { pos: number; low: string; high: string; caption: string } | null }
  | { kind: "list"; items: Array<{ title: string; text: string; tone: VTone }> }
  | { kind: "news"; items: Array<{ date: string | null; source: string | null; headline: string; url: string | null }> }
  | { kind: "verdict"; quality: string; price: string; confidence: string };
export interface ChapterModel { id: ChapterId; index: number; navLabel: string; eyebrow: string; title: string; lead: string; figures: KeyFigure[]; visual: Visual; moreLabel: string }

export const CHAPTER_ORDER: ChapterId[] = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];
const NAV: Record<ChapterId, string> = {
  empresa: "La empresa", negocio: "Cómo gana dinero", accion: "La acción", calidad: "Calidad", valor: "Cuánto vale",
  rivales: "Rivales", riesgos: "Riesgos", actualidad: "Actualidad", conclusion: "Conclusión",
};
const FIGURES_PER_CHAPTER = 3;
const SIN_DATO: KeyFigure = { label: "—", value: "Sin dato", tone: "neutral" };

export const toVTone = (t: Tone | null | undefined): VTone =>
  t === "pos" ? "good" : t === "warn" ? "warn" : t === "neg" ? "bad" : "neutral";

const fromRow = (r: Row | undefined, label?: string): KeyFigure =>
  r && r.state === "con_dato" ? { label: label ?? r.label, value: r.value, tone: toVTone(r.tone) }
    : { label: label ?? r?.label ?? "—", value: r ? (r.reading || "Sin dato") : "Sin dato", tone: "neutral" };
const fromKpi = (k: Kpi | undefined): KeyFigure =>
  k ? { label: k.label, value: k.state === "con_dato" ? k.value : "Sin dato", tone: "neutral" } : SIN_DATO;
const pad = (fs: KeyFigure[]): KeyFigure[] => {
  const out = fs.slice(0, FIGURES_PER_CHAPTER);
  while (out.length !== FIGURES_PER_CHAPTER) out.push(SIN_DATO);
  return out;
};
const row = (rows: Row[], key: string) => rows.find((r) => r.key === key);
const firstText = (...xs: Array<string | null | undefined>) => xs.find((x) => x && x.trim()) ?? "";

export function buildStory(a: StockAnalysis): ChapterModel[] {
  const d = a.display, cover = d.cover, s = d.sections;
  const kpis = cover.kpis;
  const last = a.yearly_financials.length ? a.yearly_financials[a.yearly_financials.length - 1] : null;
  const verdict = cover.verdict.text;
  const conf = d.confidence;
  const qualityItems = cover.categories.flatMap((c) => c.items).filter((i) => i.applicable && i.name !== "Valoración");
  const market = s.market ?? null;
  const alerts = s.alerts.groups.flatMap((g) => g.items.map((it) => ({ g, it })));
  const comparison = d.charts.comparison.groups.flatMap((g) => g.items);

  const ch = (id: ChapterId, title: string, lead: string, figures: KeyFigure[], visual: Visual, moreLabel: string): ChapterModel => ({
    id, index: CHAPTER_ORDER.indexOf(id) + 1, navLabel: NAV[id], eyebrow: `${CHAPTER_ORDER.indexOf(id) + 1} · ${NAV[id]}`,
    title, lead: lead || verdict, figures: pad(figures), visual, moreLabel,
  });

  return [
    ch("empresa", `Qué es ${a.profile.name}`,
      firstText(`${a.profile.name} opera en ${a.profile.industry} (${a.profile.sector}). ${cover.archetype_label}: ${cover.classification_notes[0] ?? ""}`),
      [fromKpi(kpis.find((k) => k.key === "market_cap")), { label: "Tipo de negocio", value: cover.archetype_label, tone: "neutral" },
       { label: "Bolsa", value: a.profile.exchange, tone: "neutral" }],
      { kind: "facts", rows: [{ label: "En una frase", value: verdict }, { label: "País", value: a.profile.country || "Sin dato" },
        { label: "Moneda de cotización", value: a.profile.currency }] },
      "Ver la empresa en detalle"),
    ch("negocio", "De dónde vienen sus ingresos",
      firstText(s.profitability.intro, s.growth.intro),
      [fromRow(row(s.profitability.rows, "gross_margin")), fromRow(row(s.profitability.rows, "net_margin")),
       last && last.revenue !== null ? { label: `Ingresos ${last.year}`, value: `$${(last.revenue / 1e9).toFixed(1)} mil M`, tone: "neutral" } : SIN_DATO],
      { kind: "facts", rows: s.profitability.figures.map(([label, value]) => ({ label, value })) },
      "Ver segmentos e historia de 10 años"),
    ch("accion", "Cómo se ha movido el precio",
      firstText(market?.rows.find((r) => r.key === "trend")?.text, s.growth.range52?.reading?.text, s.growth.range52?.caption),
      (market?.rows ?? []).slice(0, FIGURES_PER_CHAPTER).map((r) => ({ label: r.label, value: r.value, tone: toVTone(r.tone) })),
      { kind: "price", range52: s.growth.range52 ? { pos: s.growth.range52.pos, low: s.growth.range52.low, high: s.growth.range52.high, caption: s.growth.range52.caption } : null },
      "Ver gráfica completa y rentabilidades"),
    ch("calidad", "Qué tan buena es la empresa",
      firstText(cover.quality.note, s.profitability.intro),
      [fromRow(row(s.profitability.rows, "roic")), fromRow(row(s.profitability.rows, "roe")),
       ...s.institutional.cards.filter((c) => c.key === "piotroski").map((c) => ({ label: c.title, value: c.value, tone: toVTone(c.tone) }))],
      { kind: "bars", rows: qualityItems.map((i) => ({ label: i.name, score: i.score, max: i.max, tone: toVTone(i.tone) })) },
      "Ver rentabilidad, solidez, crecimiento y Piotroski"),
    ch("valor", "Lo que exige el precio",
      firstText(s.valuation.reverse_dcf?.lines[0]?.text, s.valuation.intro),
      s.valuation.rows.filter((r) => r.state === "con_dato").slice(0, FIGURES_PER_CHAPTER).map((r) => fromRow(r)),
      { kind: "list", items: (s.valuation.reverse_dcf?.lines ?? []).map((l) => ({ title: l.label ?? "", text: l.text, tone: toVTone(l.tone) })) },
      "Abrir escenarios de valor"),
    ch("rivales", "Frente a su referencia",
      firstText(d.charts.comparison.note, `Comparada con la mediana ${d.benchmark.vs}: mejor en ${d.charts.comparison.better} de ${d.charts.comparison.total} métricas.`),
      comparison.slice(0, FIGURES_PER_CHAPTER).map((c) => ({ label: c.label, value: c.value_txt, tone: toVTone(c.tone) })),
      { kind: "list", items: comparison.map((c) => ({ title: `${c.label} · ${c.reading}`, text: `${c.value_txt} frente a ${c.bench_txt}`, tone: toVTone(c.tone) })) },
      "Comparar con la referencia"),
    ch("riesgos", "Qué puede salir mal",
      firstText(s.valuation.premortem?.items.join(" "), alerts[0]?.it.reason),
      alerts.slice(0, FIGURES_PER_CHAPTER).map(({ g, it }) => ({ label: it.category, value: it.reason, tone: toVTone(g.tone) })),
      { kind: "list", items: alerts.map(({ g, it }) => ({ title: it.reason, text: it.detail, tone: toVTone(g.tone) })) },
      "Ver todos los riesgos y alertas"),
    ch("actualidad", "Qué está pasando",
      firstText(market?.note, market?.news_note),
      (market?.rows ?? []).slice(FIGURES_PER_CHAPTER).map((r) => ({ label: r.label, value: r.value, tone: toVTone(r.tone) })),
      { kind: "news", items: market?.news ?? [] },
      "Ver todas las noticias y señales"),
    ch("conclusion", "Nuestra lectura",
      firstText(`${verdict}. ${conf?.summary ?? cover.verdict.confidence_text ?? ""}`),
      [{ label: cover.quality.title, value: `${cover.quality.score ?? "—"} / 100`, tone: toVTone(cover.quality.tone) },
       { label: cover.price.title, value: `${cover.price.score ?? "—"} / 100`, tone: toVTone(cover.price.tone) },
       { label: "Confianza", value: conf?.level ?? "—", tone: toVTone(conf?.tone) }],
      { kind: "verdict", quality: cover.quality.level ?? "—", price: cover.price.level ?? "—", confidence: conf?.level ?? "—" },
      "Descargar el informe en PDF"),
  ];
}
```
Los nombres de campos están contrastados con `frontend/src/lib/api.ts` a 2026-10-17 (`Row`, `Kpi`, `CategoryItem`, `Confidence.summary/level/tone`, `charts.comparison.groups[].items[]` con `value_txt`/`bench_txt`/`reading`, `benchmark.vs`, `kpis[].key === "market_cap"`). Si `tsc` señala alguno distinto, el contrato manda: ajusta **este archivo** y vuelve a ejecutar el test.

- [ ] **Step 4: Ejecutar el test del modelo**

Run: `npx vitest run src/v2/lib/story.test.ts`
Expected: PASS en los 8 tickers. Si un ticker deja un capítulo sin `lead` o con una figura vacía, corrige la regla de ese capítulo usando otro campo del `display` (nunca texto inventado) y anótalo.

- [ ] **Step 5: Componentes** — `frontend/src/v2/components/KeyFigures.tsx`:

```tsx
import type { KeyFigure } from "@/v2/lib/story";

export default function KeyFigures({ figures }: { figures: KeyFigure[] }) {
  return (
    <div className="figures" data-sym-row>
      {figures.map((f, i) => (
        <div key={`${f.label}-${i}`} className="figure surface">
          <div className="eyebrow">{f.label}</div>
          <div className={`num fig-value tone-${f.tone}`}>{f.value}</div>
        </div>
      ))}
    </div>
  );
}
```

`frontend/src/v2/components/ChapterVisual.tsx` (la gráfica de precio real entra en Task 6; aquí el rango de 52 semanas):

```tsx
import type { Visual } from "@/v2/lib/story";

export default function ChapterVisual({ visual }: { visual: Visual }) {
  switch (visual.kind) {
    case "facts":
      return <table className="facts num"><tbody>{visual.rows.map((r) => <tr key={r.label}><td>{r.label}</td><td>{r.value}</td></tr>)}</tbody></table>;
    case "bars":
      return <table className="bars num"><tbody>{visual.rows.map((r) => (
        <tr key={r.label}><td>{r.label}</td>
          <td className="bar-cell"><div className="bar-track"><div className={`bar-fill ${r.tone}`} style={{ width: `${(r.score / r.max) * 100}%` }} /></div></td>
          <td>{r.score} / {r.max}</td></tr>))}</tbody></table>;
    case "price":
      return visual.range52 ? (
        <div className="range52">
          <div className="eyebrow">Rango de 52 semanas</div>
          <div className="r52-track"><span className="r52-pin" style={{ left: `${visual.range52.pos * 100}%` }} /></div>
          <div className="r52-ends num"><span>{visual.range52.low}</span><span>{visual.range52.high}</span></div>
          <p className="muted">{visual.range52.caption}</p>
        </div>) : <p className="muted">Sin datos de precio.</p>;
    case "list":
      return <ul className="vlist">{visual.items.map((it, i) => <li key={i} className={`tone-${it.tone}`}><b>{it.title}</b> <span className="muted">{it.text}</span></li>)}</ul>;
    case "news":
      return visual.items.length ? (
        <div className="news" data-sym-row>{visual.items.slice(0, 4).map((n, i) => (
          <a key={i} className="news-card surface" href={n.url ?? undefined} target="_blank" rel="noreferrer">
            <div className="eyebrow">{n.date ?? ""} · {n.source ?? ""}</div><div>{n.headline}</div></a>))}</div>
      ) : <p className="muted">Sin noticias recientes.</p>;
    case "verdict":
      return <table className="facts num"><tbody>
        <tr><td>Calidad</td><td>{visual.quality}</td></tr><tr><td>Precio</td><td>{visual.price}</td></tr><tr><td>Confianza</td><td>{visual.confidence}</td></tr>
      </tbody></table>;
  }
}
```
Nota: `pos` del rango de 52 semanas ya viene del motor entre 0 y 1 (`Range52.pos`); multiplicar por 100 es conversión de unidad, no un umbral.

`frontend/src/v2/components/Chapter.tsx`:

```tsx
import type { ChapterModel } from "@/v2/lib/story";
import KeyFigures from "./KeyFigures";
import ChapterVisual from "./ChapterVisual";

export default function Chapter({ c }: { c: ChapterModel }) {
  const flip = c.index % 2 === 0;
  return (
    <section id={c.id} className={`chapter${flip ? " flip" : ""}`} aria-labelledby={`${c.id}-t`} data-sym-row>
      <div className="col text">
        <div className="eyebrow">{c.eyebrow}</div>
        <h2 id={`${c.id}-t`}>{c.title}</h2>
        <p className="lead">{c.lead}</p>
        <KeyFigures figures={c.figures} />
        <a className="more" href={`#${c.id}`}>{c.moreLabel} →</a>
      </div>
      <div className="col visual surface"><ChapterVisual visual={c.visual} /></div>
    </section>
  );
}
```
(El enlace "→" apunta al ancla del capítulo en E1; en E3 apuntará a su página de profundidad.)

`frontend/src/v2/components/ChapterBar.tsx` (barra fija con capítulo activo):

```tsx
"use client";
import { useEffect, useState } from "react";
import type { ChapterModel } from "@/v2/lib/story";

export default function ChapterBar({ chapters }: { chapters: ChapterModel[] }) {
  const [active, setActive] = useState(chapters[0]?.id);
  useEffect(() => {
    const obs = new IntersectionObserver((entries) => {
      const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (vis[0]) setActive(vis[0].target.id as ChapterModel["id"]);
    }, { rootMargin: "-120px 0px -60% 0px" });
    chapters.forEach((c) => { const el = document.getElementById(c.id); if (el) obs.observe(el); });
    return () => obs.disconnect();
  }, [chapters]);
  return (
    <nav className="chapterbar" aria-label="Capítulos">
      <div className="wrap chapterbar-grid">
        {chapters.map((c) => (
          <a key={c.id} href={`#${c.id}`} aria-current={active === c.id ? "true" : undefined}>{c.navLabel}</a>
        ))}
      </div>
    </nav>
  );
}
```

- [ ] **Step 6: Estilos de capítulos** — añade a `frontend/src/app/v2/v2.css`:

```css
.fz2 .chapterbar { position: sticky; top: 0; z-index: 10; background: var(--surface); border-bottom: 1px solid var(--line); }
.fz2 .chapterbar-grid { display: grid; grid-template-columns: repeat(9, 1fr); text-align: center; }
.fz2 .chapterbar a { padding: var(--s3) 0; color: var(--text-3); text-decoration: none; font-size: 13px; }
.fz2 .chapterbar a[aria-current="true"] { color: var(--ink); font-weight: 650; box-shadow: inset 0 -2px 0 var(--good); }
.fz2 .chapter { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s5); padding: var(--s6) 0; border-bottom: 1px solid var(--line); align-items: stretch; scroll-margin-top: var(--s7); }
.fz2 .chapter.flip .text { order: 2; } .fz2 .chapter.flip .visual { order: 1; }
.fz2 .chapter .col { display: flex; flex-direction: column; gap: var(--s3); }
.fz2 .chapter .visual { padding: var(--s4); justify-content: center; }
.fz2 .chapter h2 { font-size: 24px; font-weight: 650; letter-spacing: -.01em; margin: 0; }
.fz2 .chapter .lead { color: var(--text-2); margin: 0; }
.fz2 .chapter .more { color: var(--good); font-weight: 600; text-decoration: none; margin-top: auto; }
.fz2 .figures { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s2); align-items: stretch; }
.fz2 .figure { padding: var(--s2) var(--s3); display: flex; flex-direction: column; gap: var(--s1); }
.fz2 .fig-value { font-weight: 600; }
.fz2 .facts, .fz2 .bars { width: 100%; border-collapse: collapse; }
.fz2 .facts td, .fz2 .bars td { padding: var(--s2) 0; border-bottom: 1px solid var(--line-soft); }
.fz2 .facts td + td, .fz2 .bars td:last-child { text-align: right; }
.fz2 .bar-cell { width: 55%; padding: 0 var(--s3); }
.fz2 .bar-track { height: 8px; background: var(--neutral); border-radius: 4px; }
.fz2 .bar-fill { height: 8px; border-radius: 4px; }
.fz2 .bar-fill.good { background: var(--good); } .fz2 .bar-fill.warn { background: var(--warn); }
.fz2 .bar-fill.bad { background: var(--bad); } .fz2 .bar-fill.neutral { background: var(--text-3); }
.fz2 .r52-track { position: relative; height: 8px; border-radius: 4px; background: var(--neutral); margin: var(--s2) 0; }
.fz2 .r52-pin { position: absolute; top: -4px; width: 2px; height: 16px; background: var(--ink); }
.fz2 .r52-ends { display: flex; justify-content: space-between; color: var(--text-3); }
.fz2 .vlist { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--s2); }
.fz2 .news { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s2); align-items: stretch; }
.fz2 .news-card { padding: var(--s3); color: var(--ink); text-decoration: none; display: flex; flex-direction: column; gap: var(--s1); }
@media (max-width: 767px) {
  .fz2 .chapterbar-grid { display: flex; overflow-x: auto; gap: var(--s4); }
  .fz2 .chapterbar a { white-space: nowrap; }
  .fz2 .chapter { grid-template-columns: 1fr; }
  .fz2 .chapter.flip .text, .fz2 .chapter.flip .visual { order: 0; }
  .fz2 .figures { grid-template-columns: repeat(2, 1fr); }
  .fz2 .news { grid-template-columns: 1fr; }
}
```

- [ ] **Step 7: Test de componente `frontend/src/v2/components/Chapter.test.tsx`**

```tsx
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import Chapter from "./Chapter";
import { buildStory } from "@/v2/lib/story";
import AAPL from "@/v2/__fixtures__/AAPL.json";
import type { StockAnalysis } from "@/lib/api";

describe("Chapter", () => {
  it("los capítulos pares invierten columnas y cada uno tiene ancla", () => {
    const story = buildStory(AAPL as unknown as StockAnalysis);
    const { container } = render(<>{story.map((c) => <Chapter key={c.id} c={c} />)}</>);
    const sections = container.querySelectorAll("section.chapter");
    expect(sections.length).toBe(9);
    expect(sections[1].classList.contains("flip")).toBe(true);
    expect(sections[0].classList.contains("flip")).toBe(false);
    expect(container.querySelector("#calidad")).not.toBeNull();
  });
});
```

- [ ] **Step 8: Montar la historia** — en `StoryPageClient.tsx`, dentro del bloque `{data && (<>…</>)}`, después de `<CompanyHeader … />`, añade:

```tsx
          {(() => { const story = buildStory(data); return (<>
            <ChapterBar chapters={story} />
            {story.map((c) => <Chapter key={c.id} c={c} />)}
          </>); })()}
```
con los imports `buildStory` de `@/v2/lib/story`, `ChapterBar` y `Chapter` de `@/v2/components/…`. Mueve la `ChapterBar` fuera del `<main className="wrap">` si el `position: sticky` no cubre todo el ancho (debe ir a ancho completo como la barra general).

- [ ] **Step 9: Ejecutar**

Run: `npx vitest run src/v2 && npx playwright test e2e/v2 --project=desktop && npm run check`
Expected: todo en verde.

- [ ] **Step 10: Commit**

```bash
git add src/v2/lib/story.ts src/v2/lib/story.test.ts src/v2/components src/app/v2
git commit -m "E1: historia de 9 capítulos con barra fija, capítulos a lo ancho y cifras clave"
```

---

### Task 6: Serie de precios (endpoint aditivo) y gráfica de precio

**Files:**
- Create: `backend/lib/prices_v2.py`, `backend/tests/test_prices_v2.py`, `frontend/src/v2/lib/returns.ts`, `frontend/src/v2/lib/prices.ts`, `frontend/src/v2/components/PriceChart.tsx`
- Modify: `backend/main.py` (un endpoint nuevo), `frontend/src/v2/components/ChapterVisual.tsx` (caso `price`), `frontend/src/app/v2/v2.css`
- Test: `frontend/src/v2/lib/returns.test.ts`, `frontend/e2e/v2/price.spec.ts`

Alcance en E1 (spec §3.4): rangos 1S–5A y comparación base 100 con S&P 500 y ETF del sector, con su tabla de rentabilidad de precio. Cursor con fecha, volumen, eventos marcados y rentabilidad total con dividendos llegan en E2/E3 (necesitan los datos nuevos de spec §4).

**Interfaces:**
- Produces (backend): `GET /api/v2/prices/{symbol}` →
  `{ symbol: str, as_of: str | null, company: {status, points: [{t: "YYYY-MM-DD", c: float, v: float | null}]}, market: {symbol, status, points: [...]}, sector: {symbol, status, points: [...]} }`;
  `prices_v2.serialize(res: dict | None, symbol: str | None) -> dict` (de un resultado de `price_history.company/market/sector`).
- Produces (frontend): `interface Point { t: string; c: number }`; `type RangeKey = "1S" | "1M" | "3M" | "6M" | "YTD" | "1A" | "3A" | "5A"`; `RANGES: Array<{ key: RangeKey; sessions: number | "ytd" }>`; `sliceRange(points: Point[], key: RangeKey): Point[]`; `rebase(points: Point[]): Point[]` (primer punto = 100); `periodReturn(points: Point[]): number | null`; `fetchPrices(symbol: string): Promise<PricesPayload>`; componente `PriceChart({ symbol })`.

- [ ] **Step 1: Test que falla `backend/tests/test_prices_v2.py`**

```python
import pandas as pd
import prices_v2


def _frame():
    idx = pd.to_datetime(["2026-10-14", "2026-10-15", "2026-10-16"])
    return pd.DataFrame({"close": [10.0, 11.0, None], "adj_close": [9.5, 10.5, 12.0],
                         "volume": [100.0, 200.0, 300.0], "split": [0.0, 0.0, 0.0]}, index=idx)


def test_serialize_usa_cierre_ajustado_y_fecha_iso():
    out = prices_v2.serialize({"symbol": "AAPL", "frame": _frame(), "reason": None}, "AAPL")
    assert out["status"] == "ok"
    assert out["points"][0] == {"t": "2026-10-14", "c": 9.5, "v": 100.0}
    assert out["points"][-1]["c"] == 12.0


def test_serialize_sin_serie():
    out = prices_v2.serialize({"symbol": "XYZ", "frame": None, "reason": "sin datos"}, "XYZ")
    assert out == {"symbol": "XYZ", "status": "sin_dato", "reason": "sin datos", "points": []}
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `cd ../backend && ../.venv313/bin/python -m pytest tests/test_prices_v2.py -q`
Expected: FAIL (`ModuleNotFoundError: prices_v2`).

- [ ] **Step 3: Implementar `backend/lib/prices_v2.py`**

```python
"""Rediseño /v2 (E1): serializa para la web la serie diaria que el motor ya descarga (price_history).

No calcula nada de análisis: solo expone fecha, cierre ajustado (o cierre si falta) y volumen."""
from typing import Any, Dict, Optional


def serialize(res: Optional[Dict[str, Any]], symbol: Optional[str]) -> Dict[str, Any]:
    fr = (res or {}).get("frame")
    if fr is None or len(fr) == 0:
        return {"symbol": symbol, "status": "sin_dato", "reason": (res or {}).get("reason") or "sin serie", "points": []}
    close = fr["adj_close"].where(fr["adj_close"].notna(), fr["close"])
    points = [{"t": ts.strftime("%Y-%m-%d"), "c": float(c), "v": (None if v != v else float(v))}
              for ts, c, v in zip(fr.index, close, fr["volume"]) if c == c]
    return {"symbol": symbol or (res or {}).get("symbol"), "status": "ok", "points": points}
```

- [ ] **Step 4: Ejecutar el test**

Run: `../.venv313/bin/python -m pytest tests/test_prices_v2.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Endpoint aditivo en `backend/main.py`** — inmediatamente antes de `@app.get("/api/health")`, añade (usa los mismos módulos que el contexto de mercado; localiza con `grep -n "import price_history\|from price_history\|sector_profiles" main.py` cómo se importan y respétalo):

```python
@app.get("/api/v2/prices/{symbol}")
def prices_v2_endpoint(symbol: str):
    """Rediseño /v2 (E1): serie diaria de la empresa, del S&P 500 y del ETF de su sector. Aditivo: la web actual no lo usa."""
    import price_history
    import prices_v2
    from sector_profiles import get_sector_profile
    sym = symbol.upper()
    comp = price_history.company(sym)
    mkt = price_history.market()
    analysis_sector = None
    try:
        analysis_sector = _compute_analysis(sym).get("profile", {}).get("sector")
    except Exception:
        analysis_sector = None
    etf = get_sector_profile(analysis_sector or "").sector_etf
    sec = price_history.sector(etf) if etf else None
    company = prices_v2.serialize(comp, sym)
    as_of = company["points"][-1]["t"] if company["points"] else None
    return {"symbol": sym, "as_of": as_of, "company": company,
            "market": prices_v2.serialize(mkt, (mkt or {}).get("symbol")),
            "sector": prices_v2.serialize(sec, etf)}
```
Si `_compute_analysis` está cacheado (búscalo con `grep -n "_analysis_cache\|lru_cache" main.py`), esta llamada no repite el análisis; si no lo está, sustituye esa parte por la lectura del sector que ya use `market_context` y anótalo.

- [ ] **Step 6: Comprobar contra el replay y que la suite del backend sigue igual**

Run:
```bash
../.venv313/bin/python tests/replay_server.py --env panel --port 8767 &
sleep 8 && curl -s localhost:8767/api/v2/prices/AAPL | ../.venv313/bin/python -c "import json,sys; d=json.load(sys.stdin); print(d['company']['status'], len(d['company']['points']), d['market']['status'], d['sector']['symbol'])"
../.venv313/bin/python -m pytest tests -q -x
```
Expected: `ok <n> ok XLK` con `n` > 0, y la suite completa en verde **sin golden modificados** (`git status --short backend/tests/golden` vacío). Si el replay no sirve la serie (estado `sin_dato`), engancha `price_history` a `backend/tests/fixtures/prices/` en `tests/fixture_backend.py` (solo tests) y anótalo.

- [ ] **Step 7: Test que falla `frontend/src/v2/lib/returns.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { sliceRange, rebase, periodReturn, type Point } from "./returns";

const pts: Point[] = Array.from({ length: 300 }, (_, i) => ({
  t: new Date(Date.UTC(2025, 0, 1 + i)).toISOString().slice(0, 10), c: 100 + i,
}));

describe("returns", () => {
  it("1S toma las últimas 5 sesiones (+1 de base)", () => {
    expect(sliceRange(pts, "1S").length).toBe(6);
  });
  it("YTD empieza en el primer día del año del último punto", () => {
    const r = sliceRange(pts, "YTD");
    expect(r[0].t.startsWith(pts[pts.length - 1].t.slice(0, 4))).toBe(true);
  });
  it("rebase pone el primer punto en 100", () => {
    expect(rebase([{ t: "a", c: 50 }, { t: "b", c: 75 }]).map((p) => p.c)).toEqual([100, 150]);
  });
  it("periodReturn es la variación entre el primero y el último", () => {
    expect(periodReturn([{ t: "a", c: 50 }, { t: "b", c: 75 }])).toBeCloseTo(0.5);
    expect(periodReturn([])).toBeNull();
  });
});
```

- [ ] **Step 8: Implementar `frontend/src/v2/lib/returns.ts`**

```ts
export interface Point { t: string; c: number }
export type RangeKey = "1S" | "1M" | "3M" | "6M" | "YTD" | "1A" | "3A" | "5A";

const SESSIONS_PER_WEEK = 5;
const SESSIONS_PER_MONTH = 21;
const SESSIONS_PER_YEAR = 252;

export const RANGES: Array<{ key: RangeKey; sessions: number | "ytd" }> = [
  { key: "1S", sessions: SESSIONS_PER_WEEK },
  { key: "1M", sessions: SESSIONS_PER_MONTH },
  { key: "3M", sessions: SESSIONS_PER_MONTH * 3 },
  { key: "6M", sessions: SESSIONS_PER_MONTH * 6 },
  { key: "YTD", sessions: "ytd" },
  { key: "1A", sessions: SESSIONS_PER_YEAR },
  { key: "3A", sessions: SESSIONS_PER_YEAR * 3 },
  { key: "5A", sessions: SESSIONS_PER_YEAR * 5 },
];

export function sliceRange(points: Point[], key: RangeKey): Point[] {
  if (!points.length) return [];
  const r = RANGES.find((x) => x.key === key)!;
  if (r.sessions === "ytd") {
    const year = points[points.length - 1].t.slice(0, 4);
    const i = points.findIndex((p) => p.t.startsWith(year));
    return points.slice(Math.max(i - 1, 0));
  }
  return points.slice(Math.max(points.length - r.sessions - 1, 0));
}

export function rebase(points: Point[]): Point[] {
  if (!points.length) return [];
  const base = points[0].c;
  return points.map((p) => ({ t: p.t, c: (p.c / base) * 100 }));
}

export function periodReturn(points: Point[]): number | null {
  if (!points.length) return null;
  return points[points.length - 1].c / points[0].c - 1;
}
```
Nota: las constantes de sesiones son convenciones de calendario bursátil (no umbrales de análisis); van con nombre y sin arrays de números, así que pasan el guardián.

- [ ] **Step 9: Ejecutar**

Run: `cd ../frontend && npx vitest run src/v2/lib/returns.test.ts && npm run check`
Expected: PASS (4 tests) y `check` sin error.

- [ ] **Step 10: Cliente `frontend/src/v2/lib/prices.ts`**

```ts
import type { Point } from "./returns";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.port === "3000" ? "http://localhost:8000" : "");

export interface SeriesPayload { symbol: string | null; status: string; reason?: string; points: Array<Point & { v: number | null }> }
export interface PricesPayload { symbol: string; as_of: string | null; company: SeriesPayload; market: SeriesPayload; sector: SeriesPayload }

export async function fetchPrices(symbol: string): Promise<PricesPayload> {
  const res = await fetch(`${API_BASE}/api/v2/prices/${encodeURIComponent(symbol)}`);
  if (!res.ok) throw new Error(`precios ${symbol}: HTTP ${res.status}`);
  return res.json();
}
```

- [ ] **Step 11: Componente `frontend/src/v2/components/PriceChart.tsx`** (API v5 de Lightweight Charts; colores leídos de los tokens CSS para respetar claro/oscuro)

```tsx
"use client";
import { useEffect, useRef, useState } from "react";
import { createChart, LineSeries, type IChartApi } from "lightweight-charts";
import { fetchPrices, type PricesPayload } from "@/v2/lib/prices";
import { RANGES, sliceRange, rebase, periodReturn, type RangeKey } from "@/v2/lib/returns";

const css = (el: Element, v: string) => getComputedStyle(el).getPropertyValue(v).trim();
const pct = (x: number | null) => (x === null ? "Sin dato" : `${x >= 0 ? "+" : "−"}${Math.abs(x * 100).toFixed(1)}%`);

export default function PriceChart({ symbol }: { symbol: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<PricesPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<RangeKey>("1A");

  useEffect(() => { fetchPrices(symbol).then(setData).catch((e: Error) => setError(e.message)); }, [symbol]);

  useEffect(() => {
    if (!box.current || !data || data.company.status !== "ok") return;
    const root = box.current.closest(".fz2") ?? document.body;
    const chart: IChartApi = createChart(box.current, {
      height: 240, autoSize: true,
      layout: { background: { color: "transparent" }, textColor: css(root, "--text-3"), fontFamily: "inherit" },
      grid: { vertLines: { visible: false }, horzLines: { color: css(root, "--line-soft") } },
      rightPriceScale: { borderVisible: false }, timeScale: { borderVisible: false },
    });
    const add = (pts: PricesPayload["company"]["points"], color: string, width: 1 | 2, dashed: boolean) => {
      const s = chart.addSeries(LineSeries, { color, lineWidth: width, lineStyle: dashed ? 2 : 0, priceLineVisible: false, lastValueVisible: false });
      s.setData(rebase(sliceRange(pts, range)).map((p) => ({ time: p.t, value: p.c })));
    };
    add(data.company.points, css(root, "--good"), 2, false);
    if (data.market.status === "ok") add(data.market.points, css(root, "--text-3"), 1, true);
    if (data.sector.status === "ok") add(data.sector.points, css(root, "--warn"), 1, true);
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [data, range]);

  if (error) return <p className="muted">Sin gráfica de precio: {error}</p>;
  if (!data) return <div className="chart-skeleton" aria-busy="true" />;
  if (data.company.status !== "ok") return <p className="muted">Sin gráfica de precio: {data.company.reason}</p>;
  const comp = periodReturn(sliceRange(data.company.points, range));
  const mkt = data.market.status === "ok" ? periodReturn(sliceRange(data.market.points, range)) : null;
  const sec = data.sector.status === "ok" ? periodReturn(sliceRange(data.sector.points, range)) : null;
  return (
    <div className="pricechart">
      <div className="ranges" role="tablist" aria-label="Periodo">
        {RANGES.map((r) => (
          <button key={r.key} role="tab" aria-selected={range === r.key} className={range === r.key ? "on" : ""} onClick={() => setRange(r.key)}>{r.key}</button>
        ))}
        <span className="legend muted">— {symbol} · ┄ S&amp;P 500 · ┄ {data.sector.symbol ?? "Sector"} (base 100)</span>
      </div>
      <div ref={box} className="chart" data-testid="price-chart" role="img" aria-label={`Precio de ${symbol} en ${range} frente al S&P 500 y al ETF del sector`} />
      <table className="facts num"><tbody>
        <tr><td>{symbol} · {range}</td><td className={comp !== null && comp >= 0 ? "tone-good" : "tone-bad"}>{pct(comp)}</td></tr>
        <tr><td>S&amp;P 500 · {range}</td><td>{pct(mkt)}</td></tr>
        <tr><td>{data.sector.symbol ?? "ETF del sector"} · {range}</td><td>{pct(sec)}</td></tr>
      </tbody></table>
    </div>
  );
}
```

- [ ] **Step 12: Usar la gráfica en el capítulo 3** — en `ChapterVisual.tsx`, el caso `price` recibe el símbolo: cambia la firma a `ChapterVisual({ visual, symbol }: { visual: Visual; symbol: string })`, y el caso `price` a:

```tsx
    case "price":
      return (<>
        <PriceChart symbol={symbol} />
        {visual.range52 && (
          <div className="range52">
            <div className="eyebrow">Rango de 52 semanas</div>
            <div className="r52-track"><span className="r52-pin" style={{ left: `${visual.range52.pos * 100}%` }} /></div>
            <div className="r52-ends num"><span>{visual.range52.low}</span><span>{visual.range52.high}</span></div>
          </div>)}
      </>);
```
importa `PriceChart`, y en `Chapter.tsx` pasa `symbol`: `Chapter({ c, symbol })` → `<ChapterVisual visual={c.visual} symbol={symbol} />`; en `StoryPageClient` pasa `symbol={data.symbol}`. Actualiza `Chapter.test.tsx` para pasar `symbol="AAPL"` (y en ese test, como jsdom no tiene `fetch` al replay, el capítulo 3 mostrará el esqueleto: es correcto).

- [ ] **Step 13: Estilos** — añade a `v2.css`:

```css
.fz2 .pricechart { display: flex; flex-direction: column; gap: var(--s2); }
.fz2 .ranges { display: flex; gap: var(--s1); align-items: center; }
.fz2 .ranges button { background: none; border: 0; color: var(--text-3); padding: var(--s1) var(--s2); font: inherit; font-size: 12px; cursor: pointer; border-radius: 6px; }
.fz2 .ranges button.on { color: var(--ink); font-weight: 650; box-shadow: inset 0 -2px 0 var(--good); }
.fz2 .ranges .legend { margin-left: auto; font-size: 11px; }
.fz2 .chart { height: 240px; width: 100%; }
.fz2 .chart-skeleton { height: 240px; border-radius: var(--radius); background: var(--neutral); }
```

- [ ] **Step 14: Test de navegador `frontend/e2e/v2/price.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test("el capítulo 3 dibuja la gráfica y cambia de periodo", async ({ page }) => {
  await page.goto("/v2/AAPL#accion");
  const chart = page.getByTestId("price-chart");
  await expect(chart.locator("canvas").first()).toBeVisible({ timeout: 30_000 });
  await page.getByRole("tab", { name: "5A" }).click();
  await expect(page.getByRole("tab", { name: "5A" })).toHaveAttribute("aria-selected", "true");
});
```

- [ ] **Step 15: Ejecutar**

Run: `npx vitest run src/v2 && npx playwright test e2e/v2 --project=desktop && npm run check`
Expected: todo en verde.

- [ ] **Step 16: Commit**

```bash
git add ../backend/lib/prices_v2.py ../backend/tests/test_prices_v2.py ../backend/main.py src/v2/lib/returns.ts src/v2/lib/returns.test.ts src/v2/lib/prices.ts src/v2/components src/app/v2 e2e/v2/price.spec.ts
git commit -m "E1: endpoint aditivo de serie de precios y gráfica de precio con rangos y S&P 500"
```

---

### Task 7: Simetría, capturas y accesibilidad

**Files:**
- Create: `frontend/e2e/v2/symmetry.spec.ts`, `frontend/e2e/v2/screens.spec.ts`, `frontend/e2e/v2/a11y.spec.ts`

**Interfaces:**
- Consumes: atributo `data-sym-row` (filas que deben tener hijos de igual alto: `.figures`, `.news`, `.chapter`), variables `--s1…--s7`.

- [ ] **Step 1: Test de simetría `frontend/e2e/v2/symmetry.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];
const SCALE = new Set([0, 4, 8, 12, 16, 24, 32, 48]);

for (const t of TICKERS) {
  test(`simetría y escala de espaciado · ${t}`, async ({ page }) => {
    await page.goto(`/v2/${t}`);
    await page.waitForSelector("section.chapter", { timeout: 30_000 });
    const report = await page.evaluate((scale) => {
      const problems: string[] = [];
      document.querySelectorAll<HTMLElement>("[data-sym-row]").forEach((row, i) => {
        if (getComputedStyle(row).display !== "grid") return;
        const kids = Array.from(row.children) as HTMLElement[];
        const tops = new Map<number, number[]>();
        kids.forEach((k) => { const r = k.getBoundingClientRect(); const top = Math.round(r.top); tops.set(top, [...(tops.get(top) ?? []), Math.round(r.height)]); });
        tops.forEach((hs) => { if (Math.max(...hs) - Math.min(...hs) > 1) problems.push(`fila ${i} (${row.className}): alturas ${hs.join("/")}`); });
        const gap = parseFloat(getComputedStyle(row).rowGap || "0");
        if (!scale.includes(Math.round(gap))) problems.push(`fila ${i}: gap ${gap}px fuera de la escala`);
      });
      if (document.documentElement.scrollWidth > window.innerWidth) problems.push("desbordamiento horizontal");
      return problems;
    }, [...SCALE]);
    expect(report).toEqual([]);
  });
}
```

- [ ] **Step 2: Ejecutar en escritorio y móvil**

Run: `npx playwright test e2e/v2/symmetry.spec.ts`
Expected: 16 tests PASS (8 tickers × 2 proyectos). Si falla, la causa es de maquetación: corrige el CSS (p. ej. `align-items: stretch`, alturas mínimas por rejilla), **nunca** el test.

- [ ] **Step 3: Capturas `frontend/e2e/v2/screens.spec.ts`**

```ts
import { test } from "@playwright/test";

const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];

for (const t of TICKERS) {
  for (const theme of ["light", "dark"] as const) {
    test(`captura ${t} · ${theme}`, async ({ page }, info) => {
      await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
      await page.goto(`/v2/${t}`);
      await page.waitForSelector("section.chapter", { timeout: 30_000 });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `../docs/rediseno/capturas-e1/${t}-${theme}-${info.project.name}.png`, fullPage: true });
    });
  }
}
```

Run: `npx playwright test e2e/v2/screens.spec.ts`
Expected: 32 capturas en `docs/rediseno/capturas-e1/`.

- [ ] **Step 4: Accesibilidad `frontend/e2e/v2/a11y.spec.ts`**

```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

for (const theme of ["light", "dark"] as const) {
  test(`sin infracciones de accesibilidad graves · AAPL · ${theme}`, async ({ page }) => {
    await page.addInitScript((th) => localStorage.setItem("finanzer.v2.theme", th), theme);
    await page.goto("/v2/AAPL");
    await page.waitForSelector("section.chapter", { timeout: 30_000 });
    const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    const serious = res.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
  });
}
```

Run: `npx playwright test e2e/v2/a11y.spec.ts`
Expected: PASS. Si hay contraste insuficiente, ajusta solo el token afectado dentro de la misma familia de color y anótalo para el usuario.

- [ ] **Step 5: Commit**

```bash
git add e2e/v2 ../docs/rediseno/capturas-e1
git commit -m "E1: tests de simetría, capturas de 8 tickers (claro/oscuro, escritorio/móvil) y accesibilidad"
```

---

### Task 8: Verificación de que la web actual no cambió y PARADA E1

**Files:**
- Create: `docs/rediseno/E1_REGISTRO.md`

- [ ] **Step 1: Web actual intacta**

Run:
```bash
cd /Users/joseestebanroa/Downloads/finanzer_next-e1
git diff main --stat -- frontend/src/components frontend/src/app/stock frontend/src/app/page.tsx frontend/src/app/layout.tsx frontend/src/app/globals.css frontend/src/lib/api.ts frontend/out backend/lib/display.py backend/lib/pdf_report.py backend/tests/golden
cd frontend && npm run check && cd ../backend && ../.venv313/bin/python -m pytest tests -q
```
Expected: el `git diff --stat` vacío; `check` sin error; la suite del backend en verde.

- [ ] **Step 2: Rendimiento orientativo** — con el replay y `next dev` levantados, ejecuta Lighthouse sobre `/v2/AAPL` en escritorio:

Run: `npx lighthouse http://localhost:3000/v2/AAPL --preset=desktop --only-categories=performance,accessibility --output=json --output-path=../docs/rediseno/capturas-e1/lighthouse-AAPL.json --chrome-flags="--headless"`
Expected: informe generado; anota las dos notas (en `next dev` el rendimiento es orientativo; la medida definitiva es sobre el build en E6).

- [ ] **Step 3: Registro `docs/rediseno/E1_REGISTRO.md`** con: commits de la rama, versión de `lightweight-charts` instalada, resultados de cada comando de verificación (salida literal), capturas generadas, notas de Lighthouse, desviaciones respecto a este plan y su motivo, y lista de lo que se ve en cada capítulo para los 8 tickers.

- [ ] **Step 4: Commit y PARADA**

```bash
git add ../docs/rediseno/E1_REGISTRO.md
git commit -m "E1: registro de la etapa y verificación de la web actual intacta"
```
**Detente.** Presenta al usuario el enlace local (`http://localhost:3000/v2/AAPL` con el replay levantado) y las capturas. Sin push, sin merge. La etapa E2 empieza solo con su aprobación.

---

## Hoja de ruta E2–E6 (cada etapa tendrá su propio plan detallado)

| Etapa | Contenido (spec §) | Puerta |
|---|---|---|
| **E2 · Datos nuevos** | Spec §4: ficha SEC, segmentos, 10 años, Piotroski con valores, endpoint de escenarios, rivales SIC, noticias enriquecidas, próximos resultados, tendencias diarias; variación del día en la cabecera | Diff de golden explicado y aprobado; guardián para toda frase nueva |
| **E3 · Profundidad e interactividad** | Spec §3.3–3.4: 9 páginas de profundidad (`/v2/{T}/{capitulo}`) con índice en píldoras, tablas técnicas con tooltips "Tu valor", escenarios, comparador editable, Piotroski 3×3, historia de 10 años; metodología y anexo técnico | Revisión del usuario por página |
| **E4 · Portada, móvil y oscuro** | Spec §3.5–3.6: portada con buscador y tendencias en pestañas, móvil al mismo nivel, oscuro completo | Revisión en el teléfono del usuario (`/v2` publicado oculto solo si lo pide) |
| **E5 · PDF** | Spec §3.7: reportlab rediseñado con índice enlazado, marcadores, escalas, gráfica, hueco máximo comprobado | Revisión de 4 PDF |
| **E6 · Cambio** | `/v2` → principal; antigua de respaldo; `frontend/out` recompilado con `npm run build` en el checkout principal; Lighthouse sobre el build | "ok, pushea" |
