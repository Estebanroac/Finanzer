# Rediseño · Etapa E3: páginas de profundidad e interacciones — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir las 9 páginas de profundidad de `/v2` (spec §3.3) y las cuatro interacciones (spec §3.4: precio en el tiempo, escenarios, rivales, historia financiera), de modo que **toda** la información de la web actual esté en `/v2`, visible, simétrica y legible, sin ningún desplegable salvo el anexo técnico.

**Architecture:** Mismo proyecto Next.js y misma ruta catch-all `src/app/v2/[[...symbol]]`: `/v2/{T}` es la historia y `/v2/{T}/{capitulo}` su página de profundidad (export estático compatible: el cliente lee la URL). Componentes compartidos nuevos en `src/v2/components/depth/` (índice en píldoras, tabla técnica, tooltip de métrica con hoja inferior en móvil, metodología, anexo). Cada página es un componente en `src/v2/pages/` que solo **compone** datos del contrato (`display`, `display.extended`, endpoints `/api/v2/*`): ninguna cifra ni lectura se calcula en el navegador, salvo las rentabilidades de la serie (ya en E1) y el formato. Única ampliación del backend: el escenario gana el margen de caja, los preajustes por tipo de empresa, "qué exige el precio" con los supuestos del usuario y la sensibilidad (Task 7).

**Tech Stack:** Next.js 16 / React 19 / TypeScript, CSS con ámbito `.fz2` (tokens de E1), Lightweight Charts v5, Vitest + Testing Library, Playwright + axe; backend Python para la Task 7.

**Referencias:** spec `docs/superpowers/specs/2026-10-17-rediseno-experiencia-design.md` §3.3–3.4 y §5 revisada (lectura 16/17 px, mínimo 12 px, zoom); maquetas `docs/rediseno/maquetas/2-paginas-de-profundidad.html` y `4-parte-tecnica-y-tooltips.html`; registros `E1_REGISTRO.md`, `E2A_REGISTRO.md`, `E2B_REGISTRO.md` (en sus ramas).

## Global Constraints

- **Nada se pierde:** cada dato que muestra hoy la web actual (`/stock`, sus 9 pestañas y sus 36 desplegables) aparece en `/v2` (historia o profundidad). Lo prueba la Task 12, automáticamente.
- **Nada plegado** salvo "Detalle técnico para auditoría" (un único `<details>` en toda la web).
- **Sin cálculo en el navegador:** las lecturas, tonos, bandas y textos vienen del motor; el cliente solo formatea y compone. El guardián `check-analysis-literals.mjs` cubre `src/v2` entero (añade `src/v2/pages` a su `SCOPE`).
- **Diseño (E1 y spec §5 revisada):** simetría y cero huecos (el test de simetría con huecos internos de E1 se aplica a todas las páginas), mínimo 12 px, lectura 16 px (17 en móvil), tablas 15 px, zoom permitido y página usable al 200 %, sin neón, contraste AA en claro y oscuro.
- **Nombres técnicos siempre** (ROIC, ROCE, EV/EBITDA, WACC, Altman Z, Piotroski…) con su lectura llana debajo; tooltip "?" por métrica con qué mide, fórmula, rangos del motor y "Tu valor".
- **El escenario nunca cambia el veredicto** y lo calcula el motor (endpoint), no una copia en el navegador.
- **Golden:** solo cambia por las claves aditivas del escenario (Task 7), con `docs/fiabilidad/GOLDEN_DIFF_E3.md`; ninguna cifra ni veredicto existente cambia. Aprobación del PM por delegación del usuario.
- **Sin push, sin merge a `main`, sin deploy.**

## File Structure

```
frontend/src/app/v2/[[...symbol]]/StoryPageClient.tsx   enruta historia vs profundidad por la URL
frontend/src/v2/lib/routes.ts                 NUEVO  slugs de capítulo y parseo de la URL
frontend/src/v2/components/depth/
  PillIndex.tsx      índice interno en píldoras, fijo bajo la barra de capítulos, con scroll-spy
  TechTable.tsx      tabla técnica (Métrica · Empresa · Referencia · Brecha · Lectura) con "?" por fila
  MetricTip.tsx      tooltip de métrica: popover (escritorio) / hoja inferior (móvil); definición + bandas + "Tu valor"
  Methodology.tsx    metodología al pie, siempre visible
  AuditAnnex.tsx     el único <details> de la web (display.annex)
  Section.tsx        bloque con ancla, eyebrow, título y rejilla simétrica
frontend/src/v2/pages/  Empresa.tsx Negocio.tsx Accion.tsx Calidad.tsx Valor.tsx Rivales.tsx Riesgos.tsx Actualidad.tsx Conclusion.tsx
frontend/src/v2/components/ PriceChartFull.tsx  HistoryChart.tsx  SegmentsChart.tsx  ScenarioPanel.tsx  PeersTable.tsx  PiotroskiGrid.tsx  AltmanGauge.tsx
frontend/e2e/v2/depth-*.spec.ts, nada-se-pierde.spec.ts
backend/lib/scenario.py, config/valuation.toml [scenario.presets], main.py scenario_inputs  (Task 7)
docs/fiabilidad/GOLDEN_DIFF_E3.md, docs/rediseno/E3_REGISTRO.md
```

---

### Task 0: Rama de integración `rediseno/v4`

- [ ] Crea `../finanzer_next-v4` con la rama `rediseno/v4` desde `rediseno/e2a-datos-motor` y fusiona `rediseno/e2b-segmentos-rivales-tendencias` (`git merge --no-ff`). Conflictos esperables: `backend/main.py` (endpoints `/api/v2/*`: conserva todos), `backend/config/market.toml` (secciones nuevas de las dos ramas: conserva todas), `frontend/src/lib/api.ts` (tipos aditivos: conserva todos), fixtures y herramientas de captura. Resuelve con la skill `mattpocock-skills:resolving-merge-conflicts`.
- [ ] Suite completa del backend, `npm run check`, `test:v2`, `e2e:v2` y `diff_golden.py --env panel` sin diferencias respecto al golden de E2a. Commit de la fusión. **Esta rama es la base de E3, E4, E5 y la verificación de la v4.**

---

### Task 1: Rutas de profundidad

**Files:** Create `frontend/src/v2/lib/routes.ts` (+test); Modify `StoryPageClient.tsx`, `ChapterBar.tsx`, `Chapter.tsx`.

**Interfaces:**
```ts
export const CHAPTER_SLUGS = ["empresa","negocio","accion","calidad","valor","rivales","riesgos","actualidad","conclusion"] as const;
export type ChapterSlug = typeof CHAPTER_SLUGS[number];
export function parseV2Path(pathname: string): { symbol: string | null; chapter: ChapterSlug | null };
export function chapterHref(symbol: string, chapter?: ChapterSlug, anchor?: string): string; // "/v2/AAPL/calidad#piotroski"
```
- [ ] Test (Vitest): `/v2/aapl/` → `{AAPL, null}`; `/v2/AAPL/calidad` → `{AAPL, "calidad"}`; capítulo desconocido → `null` (se muestra la historia); `chapterHref` con y sin ancla.
- [ ] `StoryPageClient`: con `chapter` muestra cabecera + barra de capítulos (capítulo activo = el de la URL, enlaces a `/v2/{T}/{slug}`) + la página del capítulo; sin capítulo, la historia (E1). El enlace "… →" de cada capítulo de la historia apunta a su página de profundidad. La navegación entre capítulos no repite la llamada a `/api/analysis` (el análisis se guarda en un estado de nivel superior o en `sessionStorage` por símbolo con su `as_of`; si no está, se pide).
- [ ] Playwright: desde `/v2/AAPL`, clic en "Ver rentabilidad, solidez…" abre `/v2/AAPL/calidad` con la píldora "Rentabilidad" visible y una sola petición a `/api/analysis/AAPL` en total.

---

### Task 2: Componentes de profundidad

**Files:** `frontend/src/v2/components/depth/*.tsx` (+ CSS en `v2.css`, + tests).

**Interfaces:**
```ts
PillIndex({ items: Array<{ id: string; label: string }> })            // sticky bajo la barra de capítulos; activo por scroll-spy
Section({ id, eyebrow, title, children })                              // ancla + cabecera; scroll-margin para no quedar tapada
TechTable({ rows: Row[]; refLabel: string; tooltips: Display["tooltips"]; caption?: string })
MetricTip({ metricKey: string; label: string; value: string; bands?: MetricBands })
Methodology({ items: Array<{ label: string; text: string }> })
AuditAnnex({ annex: Display["annex"] })
```
- **TechTable** (maqueta 4): columna Métrica = nombre técnico en negrita + significado debajo (`definitionFor(row.key, row.label).title` y su `description` acortada a la primera frase, de `src/lib/tooltips.ts`, que ya existe y no tiene umbrales); Empresa (`row.value`, color por `row.tone`); Referencia (`row.bench`, con `refLabel`: "Mediana del sector (Tecnología)" o "Mercado"); Brecha (`row.gap`); Lectura (`row.reading` en pastilla del tono). Filas sin dato: "Sin dato" con `row.text` como motivo, nunca vacías. Encabezados `<th scope="col">`, primera celda `<th scope="row">`.
- **MetricTip**: botón "?" accesible (`aria-label="Qué es {label}"`), abre un popover anclado en escritorio y una **hoja inferior** en móvil (< 768 px; con foco atrapado, cierre con Esc, toque fuera y botón "Cerrar"). Contenido: título y descripción, fórmula (`Definition.formula`, en Geist Mono), "Rangos de referencia" de `display.tooltips[key].tables` con la banda donde cae "Tu valor" resaltada (la banda la marca el motor con el tono de la fila: localízala por `label === row.reading`; **no** comparando números en el cliente), nota (`MetricBands.note`) y `Definition.tip`.
- **AuditAnnex**: `<details>` con `display.annex.items`; es el único de la web (lo comprueba un test: `document.querySelectorAll("details").length === 1` en cada página de profundidad que lo tiene y 0 en la historia).
- [ ] Tests (Vitest) de cada componente con el fixture de AAPL; Playwright: "?" del ROIC abre el tooltip con "Tu valor" en la banda "Muy superior"; en móvil se abre como hoja inferior y Esc la cierra; axe sin infracciones graves con el tooltip abierto.

---

### Tasks 3–11: las nueve páginas

Cada página: `PillIndex` con sus secciones → `Section`s en rejilla simétrica (2 columnas iguales o 3 tarjetas por fila, nunca huecos) → `Methodology` al pie (fuentes, periodo de cada cifra, cálculo, origen de las referencias: textos de `display.methodology`, `sections.*.note`, `market.source`, `benchmark.ref`) → `AuditAnnex` donde aplique. Un test de Playwright por página: carga sin errores de consola en los 8 tickers, cada píldora salta a su sección, simetría y mínimo 12 px en verde. Un commit por página.

**Task 3 · La empresa** — píldoras: Ficha · Clasificación · Cifras clave. Ficha EDGAR completa (`extended.company_profile`, con su fuente); clasificación (`cover.archetype_label`, `classification.reason`, `cover.classification_notes`, insignia "Sin fuente oficial" si `official_source_badge`); cifras clave (`cover.kpis` completos); `profile.description` si existe (en su idioma, marcado). Sin EDGAR (MC.PA): la ficha dice su motivo y la rejilla se recompone sin hueco.

**Task 4 · Cómo gana dinero** — píldoras: Segmentos · Márgenes · Historia de 10 años. Segmentos (`/api/v2/segments`): barras horizontales del último año + tabla por año (3 ejercicios) + nota de conciliación (si `reconciles: false`: "Los segmentos suman X % más/menos que los ingresos consolidados: eliminaciones entre segmentos") + geográfico (`secondary`) al lado + **los demás ejes (`others`, p. ej. productos de AAPL: iPhone, Service, Mac…)** en pestañas o tarjetas del mismo alto; en la historia (capítulo 2) se muestra el eje más informativo para "cómo gana dinero": productos/servicios si existen, si no el de negocio, y el geográfico como segundo visual; los ejes descartados (`dropped_axes`) no se muestran; sin desglose: el motivo y la rejilla sin hueco. Márgenes (`sections.profitability.figures` y `results_flow` de `charts`). **Historia de 10 años** (interacción, spec §3.4): `HistoryChart` con barras de ingresos, beneficio neto y FCF y líneas de márgenes (Lightweight Charts o SVG propio accesible); clic/teclado en un año muestra sus cifras en una tabla al lado; incluye acciones diluidas y deuda si `history_10y` las trae (si no, la nota lo dice). Moneda de los estados indicada.

**Task 5 · La acción** — píldoras: Gráfica · Rentabilidad por periodo · Rango de 52 semanas · Señales. `PriceChartFull`: la de E1/E2a a todo el ancho con **cursor** (fecha y precio al pasar/tocar: `subscribeCrosshairMove`), **volumen** en un panel inferior (histograma), eventos marcados con leyenda, rangos 1S–5A, base 100 con S&P 500 y ETF del sector. Tabla de rentabilidad por periodo (1S, 1M, 3M, 6M, YTD, 1A, 3A, 5A) × (empresa precio, empresa total, S&P 500, sector). Rango de 52 semanas (`growth.range52`, con zonas y lectura). Señales (`sections.market.rows` con su texto, `status_note`, `source`) con la etiqueta "Contexto: no puntúa".

**Task 6 · Calidad** — píldoras: Rentabilidad · Solidez · Crecimiento · Calidad de ganancias · Piotroski · Altman · Historia de 10 años. `TechTable` con `sections.profitability.rows` (+ `divergence_note`, `roce_reading`, `quality_readings`), `solvency.rows` (+ `balance`, `quality_readings`, gauges y runway de `charts.solvency`), `growth.rows` (+ `eps_vs_revenue_note`, `score_components`, `charts.growth`); calidad de ganancias (las filas correspondientes y su categoría en `institutional.breakdown`); **Piotroski 3 × 3** (`PiotroskiGrid`, maqueta 2: nombre, Cumple/No cumple/Sin dato, valores `extended.piotroski_values` con "FY24 → FY25" o "vs beneficio neto", y la frase llana); Altman (`charts.institutional.altman` con su zona); desglose de la puntuación por categoría (`institutional.breakdown`); enlace a la historia de 10 años (Task 4, sin duplicarla).

**Task 7 · Cuánto vale** — píldoras: Escenarios · Qué exige el precio · Múltiplos · DCF y sensibilidad · Graham · Metodología.
- **Backend (primero, TDD):**
  - `scenario_inputs` gana `revenue` (la base del FCF: ingresos TTM o del ejercicio, la misma que usa el motor), `fcf_margin` base (= fcf / revenue) y `archetype`.
  - `config/valuation.toml [scenario.presets.<ARQUETIPO>]` con `pessimistic`/`optimistic` como desplazamientos sobre la base (p. ej. crecimiento ∓ pp, WACC ± pp, terminal ∓ pp, margen ∓ pp) y límites por arquetipo donde difieran de `[scenario]`; documenta en el comentario de dónde sale cada número (rango histórico de Damodaran o regla del motor), sin inventar.
  - `scenario.run` acepta `fcf_margin` (FCF = revenue × margen), devuelve además `implied_growth` (con `reverse_dcf.implied_growth` y los mismos WACC y terminal del usuario) y `sensitivity` (5 × 5: crecimiento ± `sens_growth_step` y WACC ± `sens_discount_step` alrededor de los supuestos del usuario, con el mismo `dcf_multi_stage`).
  - Tests: con los supuestos base, `fair_value` = el del motor (ya existe) **y** `implied_growth` = el de `reverse_dcf` del análisis; la sensibilidad es monótona (más crecimiento → más valor; más WACC → menos valor); preajustes dentro de los límites.
  - Golden: claves aditivas en `scenario_inputs` → `GOLDEN_DIFF_E3.md` (aprobación del PM).
- **UI (`ScenarioPanel`, maqueta 2):** preajustes Pesimista / Base / Optimista; 4 controles (crecimiento años 1–5, crecimiento a largo plazo, WACC, margen de flujo de caja) como `input type="range"` con su número editable al lado, accesibles por teclado; cada cambio pide `/api/v2/scenario` con *debounce* (250 ms) y cancela la petición anterior; resultado: valor por acción, diferencia con el precio, barra valor-vs-precio, "Qué exige el precio" con los supuestos del usuario, tabla de sensibilidad coloreada según supere o no el precio, y la frase fija "Los escenarios son para explorar: no cambian el veredicto". Si el DCF no es significativo para la empresa (banco, REIT, pre-beneficio): el panel lo dice con el motivo del motor y la rejilla se recompone sin hueco.
- Resto: qué exige el precio (`valuation.reverse_dcf`, completo, con `role` y `method`); múltiplos (`TechTable` con `valuation.rows`, `market_note`, `reference_note`, `normalization_note`); DCF y sensibilidad del informe (`valuation.sensitivity`, `wacc_breakdown`, `dcf_params`, `dcf_reliability*`, `ke_note`, `wacc_note`, `dcf_missing`); Graham y valor intrínseco (`valuation.intrinsic`); pre-mortem enlazado a Riesgos.

**Task 8 · Rivales** — píldoras: Comparador · Frente a la referencia. `PeersTable`: la empresa arriba resaltada y sus rivales (`/api/v2/peers`, sondeo cada `poll_s` mientras haya `en_cola`/`analizando`, con esqueleto por fila del mismo alto); columnas: calidad (x/100 y nivel), precio (x/100 y nivel), P/E, EV/EBITDA, ROIC, margen neto, crecimiento de ingresos, deuda/equity (claves de `summary.metrics`; la que falte: "Sin dato"); quitar (×) y añadir con el buscador (`searchStocks`, máx. 5) → `?symbols=`; estado de error por fila con su motivo; nota si hay menos de 3 comparables. Frente a la referencia: `charts.comparison` completo (grupos, mejor en X de Y, `note`, `market_note`).

**Task 9 · Riesgos** — píldoras: Pre-mortem · Alertas · Lo que no sabemos. Pre-mortem completo (`valuation.premortem`); alertas por grupo con recuento (`alerts.counts`, `alerts.groups`: categoría, motivo, detalle); confianza y cobertura (`confidence.reasons`, `confidence.dimensions`, `cover.coverage_notes`, `cover.confidence_reasons`).

**Task 10 · Actualidad** — píldoras: Noticias · Próximos resultados · Señales · Lectura conductual. Noticias (`extended.news`, 2 × 3, mismas tarjetas que la historia, "En inglés", enlace externo con `rel="noopener noreferrer"`), `news_note`; próximos resultados (`extended.next_earnings` con "anunciada"/"estimada" y su base); PEAD (`market.pead_note`); señales técnicas (contexto, no puntúa); lectura conductual (`market.behavioral`).

**Task 11 · Conclusión** — píldoras: Veredicto · Confianza · Qué vigilar · Informe. Veredicto completo (`cover.verdict.full`, `summary` del display: `exec_items`, composición de las puntuaciones con sus barras y ajustes con signo), confianza (`confidence.plain`, `dimensions`), qué vigilar (`cover.highlights`, alertas de "advertencia", pre-mortem resumido), botón de descarga del PDF (el actual hasta E5; en E5 pasa al nuevo).

---

### Task 12: "Nada se pierde" (prueba automática)

**Files:** Create `frontend/e2e/v2/nada-se-pierde.spec.ts`.

- [ ] Para cada uno de los 8 tickers: abre la web actual `/stock/{T}` (servida por `next dev` con el replay) y **expande todas las pestañas y todos los desplegables** (recorre los botones de pestaña y los `[aria-expanded="false"]`/`<details>`); recoge el texto visible y extrae los **tokens con cifra** (regex de números con su unidad: `-?\$?[\d.,]+(%|x| pp| mil M|B|T)?`, normalizados: signo menos tipográfico, separadores). Después abre `/v2/{T}` y las 9 páginas `/v2/{T}/{capitulo}` (con los tooltips "?" abiertos uno a uno en la página de Calidad y Valor), y recoge sus tokens.
- [ ] Assert: todo token de la web actual está en la unión de `/v2`, salvo una lista de excepciones **justificada** en el propio test (p. ej. cifras que la web actual repetía con otro redondeo o etiquetas de interfaz como "1/9"). Cada excepción con su motivo; el PM la revisa.
- [ ] Assert: cada clave de `display.tooltips` del análisis tiene un "?" en alguna página de `/v2`.

---

### Task 13: Verificación, capturas y registro

- [ ] Todas las pruebas de diseño de E1 (simetría con huecos internos, 12 px, zoom 200 %, axe, sin desbordamiento) aplicadas a las 9 páginas de profundidad × 8 tickers × claro/oscuro × escritorio/móvil.
- [ ] Capturas en `docs/rediseno/capturas-e3/` (por página: AAPL, JPM, O y BCS en claro escritorio y oscuro móvil; los 8 en la de Valor y la de Rivales).
- [ ] Rendimiento: Lighthouse de `/v2/AAPL/calidad` y `/v2/AAPL/valor` (escritorio, `next dev`: orientativo).
- [ ] `docs/rediseno/E3_REGISTRO.md` y `GOLDEN_DIFF_E3.md`; informe al PM. Sin push ni merge.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
