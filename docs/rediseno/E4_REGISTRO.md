# Rediseño · E4 (parte 1): cola compartida, portada y build servido por el backend — registro parcial

Rama `rediseno/e4-portada` (worktree `../finanzer_next-e4`), creada desde `rediseno/v4` en 5d4dc91. Plan:
`docs/superpowers/plans/2026-10-18-rediseno-e4-portada-movil-oscuro.md`.

Encargo del PM: **solo las Tasks 1, 2 y 5**. Las Tasks 3 (móvil al mismo nivel) y 4 (modo oscuro completo) se harán
cuando E3 tenga las páginas de profundidad. Este registro se completará entonces (Task 6).

Gobierno:
- Sin push, sin merge y sin deploy. Aprobaciones del PM por delegación del usuario.
- `frontend/out` **no se commitea**. Se compiló para las pruebas de la Task 5 y se restauró a la versión de la rama; se
  regenera en E6 (ver §5.4).

## 1. Commits

| Task | Commit | Qué |
|---|---|---|
| 1 | 305fbd3 | Cola de análisis compartida (`user` > `prewarm`) y tarjetas de tendencias con la calidad y el precio del motor |
| 2 | fd3f0ee | Portada: buscador funcional, tendencias con el motor y tarjetas de confianza; `/api/v2/search` |
| 5 | (este commit) | Ruta SPA `/v2` en el backend; portada e historia en fragmentos separados; e2e contra el build; Lighthouse; registro |

## 2. Task 1 — cola compartida y tarjetas con el motor

### La cola: `backend/lib/analysis_queue.py`

Es la cola de rivales de E2b generalizada.
- **Un solo hilo** con dos prioridades: `USER` (rivales pedidos y orden de sus candidatos) y `PREWARM` (tarjetas de
  tendencias). Un trabajo `USER` adelanta a todo el precalentado pendiente; dentro de cada prioridad, por orden de
  llegada.
- **Sin análisis duplicados.** Si un símbolo espera como `PREWARM` y un usuario lo pide, se vuelve a encolar como `USER`.
  La entrada antigua se descarta al salir. Con un solo hilo, nunca hay dos análisis del mismo símbolo a la vez.
- **Caché compartida.** El resumen compacto `summary()` y su LRU son los mismos para rivales y tendencias; `peers`
  reexporta `summary` y `reference`.
- **Configuración** en `[analysis_queue]` de `market.toml` y `schema.toml`: `summary_ttl_s`, `summary_cache_max`,
  `max_queue` (trabajos de usuarios), `max_prewarm_queue`, `fail_ttl_s` y `busy_wait_s`. Estas claves salen de `[peers]`.
- **`reset()`** detiene el hilo y un análisis en vuelo ya no escribe en la caché nueva (carrera de los tests). Lo mismo
  en `trending.reset()`, con un contador de generación.

### Rivales

`peers.py` usa la cola con prioridad `user`. **Las respuestas de `/api/v2/peers` no cambian.**

### Tendencias: `trending.get()`

- **`engine` por tarjeta:** `{status, quality: {score, level}, price_score: {score, level}, reason} | null`, leído de
  la LRU.
  - `status` vale `listo`, `analizando`, `en_cola` o `fallo`.
  - `quality` y `price_score` solo vienen con `listo`; `reason`, el motivo, solo con `fallo` (revisión del PM).
  - `null` cuando el símbolo no está analizado ni en marcha: se agotó el cupo, la cola está llena o el análisis caducó.
- **`poll_s`** (`[trending] poll_s = 5`) en todas las respuestas.
- **Cambio de `/api/v2/trending`: aditivo** (cada item gana `engine` y la respuesta gana `poll_s`). **Aprobado por el PM.**
- **Precalentado.** Tras calcular las listas, y en cada consulta mientras falten, los símbolos de las tres listas sin
  resumen se encolan como `prewarm`:
  - como mucho `[trending] prewarm_max = 30` al día (fecha de Nueva York) y cada uno una sola vez al día, para que un
    análisis que falla no se repita cada 10 minutos;
  - de uno en uno y solo sin usuarios esperando turno (`BUSY`, como los rivales);
  - siempre por detrás de cualquier rival pedido.
  - El cupo vive en la memoria del proceso: tras un reinicio de Render vuelve a empezar.

### Tests

- `tests/test_analysis_queue.py` (9):
  - un rival adelanta a cinco del precalentado;
  - un `prewarm` adelantado por un usuario se analiza una sola vez;
  - 30 peticiones concurrentes de 3 símbolos dan 3 análisis, sin solapes;
  - estados de un símbolo, fallo recordado, límites por prioridad, espera con usuarios en cola, trabajos en el mismo
    hilo y el hilo no arranca hasta la primera petición.
- `tests/test_trending.py` (+3):
  - `engine` con las cifras del golden;
  - cupo diario y una vez al día;
  - **endpoint con el replay:** descarga capturada y motor en replay (`fixture_backend`). Las tarjetas de las empresas
    del juego de fixtures (MU, NVDA, AAPL, MSFT, AMZN, PLTR) pasan a `listo` con la calidad y el precio del golden; las
    demás, a `fallo`.
- **Contrato** (`test_e2b_contract.py`): `TrendingResponse` con los cinco estados del motor (listo, fallo, analizando,
  en_cola y null). En `api.ts`: `TrendingEngine` (con `reason`), `TrendingItem.engine` y `TrendingResponse.poll_s`.
- **Tests y motor real.** `main` conecta el motor real al importarse. Los fixtures de `test_peers`, `test_trending` y
  `test_e2b_contract` importan `main` antes de sustituirlo; si no, un test podía lanzar análisis reales en segundo plano.

## 3. Task 2 — portada

### Estructura (`src/v2/home/`)

| Archivo | Qué |
|---|---|
| `HomeClient.tsx` | La página |
| `Trending.tsx` | Pestañas y rejilla |
| `TrendCard.tsx` | Tarjeta, escala mini y esqueleto |
| `trendingModel.ts` | Títulos, pie, formatos y cuándo repetir la consulta (con tests) |
| `trust.ts` | Tarjetas de confianza |
| `useTheme.ts` | Tema guardado como estado externo |
| `home.css` | Estilos de la portada |

### Contenido (maqueta 5)

- Titular «Entiende una empresa antes de invertir», entradilla de la maqueta y buscador grande.
- **Tendencias:**
  - tres pestañas con `role="tablist"`, que se manejan con clic, ← →, Inicio y Fin; en el móvil, una fila deslizable;
  - debajo, lo que mide cada lista («Por dinero negociado en la sesión…»);
  - rejilla simétrica `data-sym-row`: 5 × 2 en escritorio, 3 por fila en tableta y 2 en el móvil;
  - cada tarjeta lleva nombre (2 líneas fijas), ticker, precio, variación y la calidad y el precio del motor con su
    escala mini (bandas del motor, `buildScale`). Toda la tarjeta enlaza a `/v2/{T}`;
  - **el mismo esquema en todas las tarjetas** (revisión del PM: las tarjetas sin análisis dejaban medio cuerpo vacío):
    dos filas de escala (Calidad y Precio) y una línea de estado con el enlace.
    - Analizada: cifras, nivel y escala; «Analizada por el motor» · «Ver el análisis →».
    - Analizando o en cola: esqueleto de las dos filas; «Analizando con el motor…» o «En cola para el motor…» ·
      «Abrir el análisis →».
    - Sin análisis: «sin dato» en lugar de la cifra y la escala vacía, del mismo alto. El motivo, en una línea:
      «Sin fixtures en el replay» (el motor del replay no tiene esa empresa), «El motor no pudo analizarla» (un fallo
      real) o «Sin análisis del motor por ahora» (cupo agotado o análisis caducado). Después, «Abrir el análisis →»,
      que lleva a `/v2/{T}`, donde se analiza de nuevo.
    - Las escalas y la línea de estado de tarjetas vecinas caen a la misma altura (e2e).
- **Pie:** «Sesión del {fecha} · Actualizado el {fecha} a las {hora} (Nueva York) · universo: S&P 500 y ADR principales
  ({fecha del universo})». Si el universo está anticuado, se añade el aviso de `note`.
- **Estados:**
  - `calculando`: 10 esqueletos, «Calculando las tendencias del día…» y reintento cada `poll_s`;
  - `sin_dato`: el motivo en una línea y la última lista buena de la sesión del navegador, si la hubo;
  - mientras alguna tarjeta tiene el motor en cola o analizando, la portada vuelve a preguntar cada `poll_s`.
- **Tres tarjetas de confianza** con textos de la metodología del motor, no inventados. Las fuentes están citadas en
  `trust.ts`:
  - datos oficiales: `sec_edgar.py` y `edgar_backup.py`;
  - método por arquetipo: `display.py`, `methodology.models`;
  - confianza y contracción hacia 50: la metodología de la web actual.

### Buscador: `src/v2/components/SearchBox.tsx`

- Combobox de ARIA 1.2: ↑ ↓ para elegir, Enter para abrir y Escape para cerrar.
- Debounce de 200 ms y descarte de las respuestas que llegan tarde.
- Cada resultado muestra **nombre, ticker y bolsa**.
- Enter con un ticker exacto (o con algo que parece un ticker, sin resultados todavía) abre `/v2/{T}`.
- `TopBar.tsx` lo usa en todas las páginas. Es el único cambio en `TopBar`, más una prop `search` para que la portada
  deje el hueco. En el móvil la barra no lleva buscador, como en E1; se usa el de la portada.

### Backend: `GET /api/v2/search` (`lib/search_v2.py`)

- Misma lógica que `/api/search` (base local primero, después Yahoo), con la **bolsa** (`exchange` de Yahoo nombrado
  por `[exchanges]`, al que se añaden MEX, EBS y PNK) y **solo acciones**: un ETF o un fondo llevaría a un 422.
- `/api/search` de la web actual **no cambia**.
- Configuración en `[search]`.
- Respuestas de Yahoo capturadas en `tests/fixtures/search/quotes.json` con `tests/capture_search.py`. El replay las usa.
- Tests en `test_search_v2.py` (6) y contrato `SearchResponse`.

### Pruebas de la portada

- **Playwright** `e2e/v2/home.spec.ts`, en escritorio y móvil:
  - «apple» → opción «Apple Inc. · AAPL · Nasdaq» → ↓ → Enter → `/v2/AAPL` con la empresa cargada;
  - ticker exacto (`jpm` + Enter → `/v2/JPM`);
  - buscador de la barra general (solo escritorio);
  - pestañas con clic y flechas;
  - simetría (`symmetryProblems`) y tarjetas de igual alto (≤ 1 px);
  - estados `calculando` y `sin_dato` (respuesta interceptada);
  - axe en claro y oscuro, con la lista de resultados abierta.
- **Capturas:** `e2e/v2/home-screens.spec.ts` → `docs/rediseno/capturas-e4/portada-{light,dark}-{desktop,mobile}.webp` (comprimidas en la fusión con la v4).
  En el replay solo están analizadas las empresas del juego de fixtures; las demás tarjetas muestran «El motor no pudo
  analizarla». En producción se analizan todas, dentro del cupo.
- **Guardián de literales:** `check-analysis-literals.mjs` incluye `src/v2/home`.

## 4. Desviaciones del plan (decididas por el operador)

1. **La portada no vive en `src/app/v2/page.tsx`.** Next no admite esa página junto a la ruta opcional
   `src/app/v2/[[...symbol]]` (E1), que ya cubre `/v2`, y moverla habría tocado la carpeta de `StoryPageClient` (E3).
   - El `page.tsx` de esa ruta (no `StoryPageClient`) elige portada o historia mediante un componente cliente pequeño,
     `V2Entry.tsx`, con `next/dynamic`, de modo que cada HTML enlaza solo su código.
   - El export genera dos HTML: `out/v2/index.html` (portada) y `out/v2/_/index.html` (historia y páginas de
     profundidad, que leen el símbolo de la URL).
   - `StoryPageClient.tsx` y `Chapter*.tsx` no cambian.
2. **«hoy» en los titulares solo si la sesión de las listas es la de hoy** (Nueva York). Un domingo, las listas del
   viernes se titulan «Más negociadas», sin «hoy», y el pie dice de qué sesión son. Es la regla conductual: titular por
   lo que se mide.
3. **Endpoint nuevo `/api/v2/search`** en lugar de cambiar `/api/search`: la bolsa no estaba en la respuesta y la web
   actual no se toca.
4. **Campo del buscador no controlado por React.** Lo que se escribe antes de que la página hidrate (el HTML ya es
   usable) no se pierde; lo detectó el e2e contra el build.
5. **`e2e/v2/shell.spec.ts` («el conmutador cambia a oscuro")** espera a que la página haya pintado el análisis antes de
   pulsar. Con el build, la historia se hidrata un instante después de `load`, porque su código va aparte. Es el único
   cambio en una prueba de E1.

## 5. Task 5 — build de producción servido por el backend

### 5.1 Ruta SPA (`backend/main.py`, `_v2_file` y `serve_v2`)

- `GET|HEAD /v2` y `/v2/{path}`. HEAD hace falta porque el enrutador de Next comprueba `/v2/` con un HEAD: sin él, 405.
- Qué sirve:
  - la portada para `/v2` y `/v2/`;
  - un archivo real dentro de `out/v2` tal cual (las cargas RSC `.txt` de la navegación de Next);
  - la historia (`out/v2/_/index.html`) para todo lo demás (`/v2/{T}`, `/v2/{T}/{capítulo}`).
- Protegida contra el recorrido de rutas como `serve_static`: `../secreto.txt` recibe la historia, nunca un archivo de
  fuera.
- Se registra siempre, antes del comodín, y lee `_frontend_dir` al responder; sin build, 404.
- Tests en `tests/test_v2_serving.py` con un `out/` sintético. Sin `TestClient`: `httpx` no está en el entorno y no se
  instalan dependencias en el venv compartido.

### 5.2 Build y e2e contra el backend

- `npm run build` (Turbopack): el `prebuild` (guardián de literales) pasa con `/v2` incluido. Rutas exportadas: `/`,
  `/stock`, `/v2` y `/v2/_`.
- `E2E_BUILD=1 npx playwright test e2e/v2` (opción nueva de `playwright.config.ts`): sin `next dev`, con `baseURL` en el
  replay, que sirve `out/` y la API en el mismo origen.
- Resultado: **103 pasadas y 3 saltadas, tres veces seguidas**; tras la fusión de E2a y la revisión de las tarjetas,
  **133 pasadas y 3 saltadas** (proyectos `desktop` y `mobile`; WebKit, Firefox y
  tableta son de la Task 3).

### 5.3 La web actual no cambia

Capturas de `/` y `/stock/AAPL` servidas por el backend, con el `out/` de la rama antes y con el build de E4 después
(1440 px, página completa): **idénticas píxel a píxel** (PIL `ImageChops.difference` sin diferencias).

### 5.4 `frontend/out`

No se commitea. Tras las pruebas se restauró a la versión de la rama (`git checkout -- frontend/out`). Commitear el
build de cada rama generaría conflictos en cada fusión; el plan lo regenera en E6.

### 5.5 Lighthouse 12.8.2

Medido sobre el build servido por el backend (replay, fixtures del panel). Los JSON están en `docs/rediseno/capturas-e4/`.

**Primera medida, sin compresión.** Escritorio: 99 y 97 de rendimiento. Móvil: **77 y 76**, por debajo del objetivo,
con un LCP de unos 6,5 s. Dos causas:
- **La portada cargaba también el código de la historia** (Lightweight Charts, unos 200 KB). Un `next/dynamic` en el
  componente de servidor no lo separó; se separó con el componente cliente `V2Entry`. La portada pasa de 775 KB a 580 KB
  de JS sin comprimir.
- **Uvicorn no comprime en local.** **Producción sí:** Cloudflare delante de uvicorn sirve con `content-encoding: br`
  (comprobado en finanzer.app el 2026-10-17). Para medir como allí, el replay acepta `--compress` (gzip, solo
  herramienta de medida; `main.py` no cambia).

**Medida final, con compresión, como en producción:**

| Página | Escritorio (rend. / acc.) | Móvil (rend. / acc.) | LCP móvil |
|---|---|---|---|
| `/v2` | **100 / 100** | **96 / 100** | 2.8 s |
| `/v2/AAPL` | **100 / 100** | **90 / 100** | 3.6 s |
| `/` (web actual, referencia) | 100 / 100 | 95 / 100 | 2.9 s |
| `/stock/AAPL` (web actual, referencia) | 99 / 95 | 90 / 95 | 3.7 s |

- Objetivos (escritorio ≥ 90 / ≥ 95; móvil ≥ 80 / ≥ 95): **cumplidos**.
- Sin compresión, tras la separación del código, el móvil queda en 79 (`/v2`) y 76 (`/v2/AAPL`). Es el límite de la
  medida local, no de producción.
- `/v2/AAPL/valor` **no se ha medido**: la página de profundidad es de E3 y no está en esta rama. Queda para cuando se
  fusione con E3.

## 6. Fusión de E2a (decisión del PM)

A `rediseno/v4`, y por tanto a esta rama, le faltaban los 5 últimos commits de `rediseno/e2a-datos-motor`
(4ac27c6…9380a8c: golden con `extended`, filtro D2 de noticias, capturas y registro). Por eso `npm run check` fallaba
en v4 desde antes de E4.

El PM decidió fusionarlos aquí; E3 hará la misma fusión en v4. La fusión se hizo sin conflictos y **`npm run check`
queda en verde** (`StockAnalysis` encaja con 46 salidas del backend).

`screens.spec.ts` (de E2a) reescribe las capturas versionadas de `capturas-e2a/` en cada pasada del e2e: se restauran
después de cada pasada.

## 7. Verificación

| Comprobación | Resultado |
|---|---|
| Backend `pytest` | **4377 pasadas, 1 saltada** |
| `npm run test:v2` (vitest) | **72/72** |
| `e2e:v2` en `next dev` (escritorio y móvil) | **133 pasadas, 3 saltadas** |
| `e2e:v2` contra el build servido por el backend | **133 pasadas, 3 saltadas** |
| Guardián de literales | sin umbrales literales |
| Contratos v2 (`test_e2b_contract`: segmentos, rivales, tendencias y búsqueda) | en verde |
| `npm run check` | **en verde** (46 salidas), tras la fusión de E2a (§6) |
| Secretos | ningún fixture ni JSON de esta etapa contiene `token=`. Lo usado: Yahoo (búsqueda pública) y el replay; Finnhub y la SEC no se usaron |

## 8. Pendiente para la parte 2 (tras E3)

- Task 3: proyectos `mobile-webkit`, `tablet` y Firefox; repaso de móvil y tableta; zoom en iPhone.
- Task 4: modo oscuro completo y sin parpadeo. Hoy el tema guardado se aplica tras hidratar: en la portada, con
  `useSyncExternalStore`.
- Lighthouse de `/v2/AAPL/valor`.
- Al fusionar con E3, conflictos esperables:
  - `frontend/src/lib/api.ts`: tipos añadidos al final del bloque de tendencias;
  - `e2e/v2/shell.spec.ts`;
  - `playwright.config.ts`.
  - `TopBar.tsx`, `page.tsx` de la ruta y `replay_server.py`: E3 no los había tocado a 9f3545b.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
