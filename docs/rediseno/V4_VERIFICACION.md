# Verificación de la v4 — parte que no depende de E3

Plan: `docs/superpowers/plans/2026-10-18-rediseno-v4-verificacion.md`. Rama `rediseno/e4-portada`, en paralelo con E3.

Encargo del PM (2026-10-18): la corrección previa, **V3** (fuentes caídas), **V4** (carga y memoria) y **V5** (producción
simulada). V1, V2, V6 y V7 y las páginas de profundidad se completan cuando E3 y E5 estén fusionados (ver §6).

## 0. Corrección previa: el e2e ya no reescribe archivos versionados (0976fb2)

- `screens.spec` y `home-screens.spec` escriben en `frontend/test-results/capturas/`, que está ignorada y que Playwright
  vacía en cada pasada.
- `npm run capturas:etapa -- <etapa> [prefijo]` copia las capturas de la última pasada a
  `docs/rediseno/capturas-<etapa>/`.
- `frontend/.gitignore` incluye `/test-results/` y `/playwright-report/`.

## 1. V3 · Fuentes caídas (0fe5fc1)

### Batería

- **Fallos:** `backend/tests/faults.py` define ocho fallos sobre el replay, que se aplican y se deshacen.
- **Pytest** (`backend/tests/test_faults.py`): por cada fallo, y sin fallo, todos los endpoints de AAPL.
- **e2e** (`npm run e2e:fallos`, `frontend/e2e/fallos/`): la portada y la historia de AAPL, en escritorio y móvil.
  - Comprueba que no hay errores de consola, excepciones ni respuestas 5xx, que la simetría está en verde y que el
    motivo de cada fallo aparece en la página.
  - El fallo se cambia en caliente con `POST /__replay/fault`, que solo existe en el servidor de replay; `main.py` no lo
    tiene.
  - Va aparte de `e2e:v2`, con un solo worker.
  - **Para las páginas de E3:** `V2_PAGES=empresa,negocio,accion,calidad,valor,rivales,riesgos,actualidad,conclusion
    npm run e2e:fallos` recorre también `/v2/AAPL/{página}`.

### Resultado (sin 5xx en ningún caso)

`analysis`, `prices`, `segments`, `peers`, `trending`, `scenario` y `search` son los endpoints `/api/v2/*`; `pdf` es
`/api/pdf`. `/api/v2/pdf` entra solo en la batería cuando E5 esté fusionado.

| Fallo | analysis | prices | segments | peers | trending | scenario | search | pdf | Lo que dice la página |
|---|---|---|---|---|---|---|---|---|---|
| Ninguno | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | — |
| Yahoo caído | **404** | 200 | 200 | 200 | 200 | 200 | 200 | 404 | Análisis: «No se pudieron obtener los datos de AAPL: la fuente de datos de mercado no responde ahora mismo…». Portada: «No hay tendencias ahora mismo. No se pudieron calcular las tendencias: Yahoo no devolvió cotizaciones del universo (6 de 6 lotes fallidos).» Búsqueda: la base local sigue respondiendo |
| Yahoo 401 (plan B) | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | Igual que sin fallo: los fixtures del panel ya se capturaron con el 401 simulado |
| EDGAR sin User-Agent | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | Ficha, 10 años, segmentos y marcas de resultados: «Sin User-Agent de la SEC (variable SEC_EDGAR_USER_AGENT): verificación oficial no disponible» |
| EDGAR agota el presupuesto | 200 (2.6 s) | 200 | 200 | 200 | 200 | 200 | 200 | 200 | «EDGAR no respondió a tiempo» (ficha, 10 años y segmentos); «sin marcas de resultados: EDGAR no respondió a tiempo» (gráfica) |
| Finnhub sin clave | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | «Sin noticias recientes» |
| Finnhub 429 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | «Sin noticias recientes» |
| Serie de precios vacía | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | Gráfica de referencia: «Sin la serie de AAPL: Yahoo no devolvió la serie de precios (2 intentos). Como referencia, el S&P 500 y XLK en el mismo periodo.» |
| ETF del sector caído | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | Gráfica sin la línea del sector (`sector.reason`: «Yahoo no respondió (2 intentos)») |

- Pytest: **11 pasadas** (9 casos más «EDGAR lento no cuelga el análisis» y «el conmutador deshace cada fallo»), 45 s.
- `e2e:fallos`: **36/36** (9 casos × 2 páginas × 2 tamaños) con `next dev` y también contra el build servido por el
  backend.
- Dos de ellos están marcados como fallo esperado (ver el hallazgo 7).

### Fallos que encontró y su arreglo en origen

1. **Yahoo caído se presentaba como un símbolo inexistente** («No data found for AAPL», 404).
   - Arreglo: `yf_adapter` recuerda el fallo de conexión del plan B (`unreachable`) y `data_fetcher` marca
     `source_unavailable`.
   - El análisis responde con el mismo 404 (la web actual no cambia) pero con el motivo: «la fuente de datos de mercado
     no responde ahora mismo».
2. **Motivos de EDGAR ilegibles o falsos:**
   - con el tiempo agotado salía «TimeoutError: », porque el error de `concurrent.futures` no trae mensaje;
   - los segmentos decían «presupuesto agotado (3 s)» con un presupuesto de 8 s: ahora el mensaje usa el de quien llama;
   - la ficha anteponía «EDGAR no respondió:» también cuando EDGAR estaba desactivado;
   - las marcas de la gráfica decían «(Unavailable)».
3. **Motivos de la serie de precios y de las tendencias con nombres de excepción** (`SourceDown: …`, `RuntimeError: …`).
   Ahora dicen «Yahoo no devolvió la serie de precios (2 intentos)» y «Yahoo no devolvió cotizaciones del universo (6 de
   6 lotes fallidos)»; el error técnico va al log.
4. **«La acción» sin serie de precios:** una línea suelta en un visual vacío, que además rompía la simetría (el visual se
   estiraba 126 px). Ahora la gráfica dibuja el S&P 500 y el sector como referencia, con el motivo en una línea, más
   baja y sin la tabla de rentabilidades.
5. **Error de hidratación en todas las páginas de /v2** (mío, de E4). `useId` daba ids distintos en el HTML y en el
   cliente (la página se carga con `next/dynamic`). Lo destapó la comprobación de la consola; ahora `SearchBox` usa ids
   fijos.
6. **Motivo de las tendencias con dos paréntesis seguidos.** Ahora la portada lo muestra como una frase.
7. **Para E3:** con Yahoo caído, `/v2/AAPL` muestra «Failed to analyze AAPL: 404» (en inglés y sin el motivo).
   - Causa: `StoryPageClient` pide el análisis con `analyzeStock` de `@/lib/api` (la web actual), que solo usa el motivo
     del backend con el 422.
   - Arreglo listo sin tocar archivos de E3: `src/v2/lib/analysis.ts`, con `fetchAnalysisV2` y sus tests. Da el motivo
     del backend en español, «No hay datos de X: comprueba el ticker…» para un símbolo inexistente y «No se pudo
     contactar con el servidor…» sin red.
   - **E3 solo tiene que cambiar la importación en `StoryPageClient`.** Mientras tanto, la prueba e2e lo marca como
     fallo esperado (`test.fail`); cuando E3 lo cambie, pasará y habrá que quitar la marca.

**Observación para el PM (no arreglada).** Cuando un capítulo trae menos de 3 cifras, `story.ts` (E1) lo completa con
filas «— / Sin dato». Pasa en el capítulo de Riesgos de O y NEE y, con la serie de precios vacía, en «La acción».
- Quitar ese relleno rompe la simetría en datos degradados: el ajuste de `Chapter` y `fit`, de E1 y E3, no compensa la
  columna más corta.
- Lo revertí. Si se quiere quitar, hace falta un cambio de E3 en el ajuste.

## 2. V4 · Carga y memoria

### Herramientas

- `backend/tools/load_server.py`: `main.py` real con la web compilada, más la medida de cada turno de `_ANALYSIS_SLOTS`
  (usuario o fondo, espera y tenencia) en `GET /__load/slots`. Solo es una herramienta de medida.
- `backend/tools/load_test.py` (comando completo en su cabecera):
  - **Mezcla:** visita a una empresa (HTML, análisis, gráfica y segmentos), escenario, rivales hasta que estén
    (repitiendo la consulta), portada con tendencias, búsqueda, PDF, y 10 empresas nuevas sin caché.
  - **Cliente:** `curl_cffi.requests.AsyncSession`. `httpx` no está en el entorno y no se instaló nada.
  - **Memoria:** macOS no aplica `ulimit -v` («setrlimit failed: invalid argument»; `RLIMIT_AS` no se puede fijar) y
    `psutil` no está, así que se mide con `ps` (RSS) y con `footprint` (huella física, que incluye la memoria
    comprimida: el RSS de macOS baja de golpe cuando el sistema comprime). El criterio usa la mayor de las dos.
  - **Calentamiento:** el primer análisis de las 8 empresas de verificación y el precalentado diario de tendencias (30
    análisis en la cola de fondo).
  - **Claves:** se leen del Llavero en el mismo comando y solo pasan del entorno al proceso. Los informes solo dicen si
    están presentes (sí/sí).

### Resultados (fuentes reales, 20 usuarios, 4 análisis concurrentes como en Render)

| Criterio | 5 min (`V4_carga_5min`) | 12 min (`V4_carga_12min`) | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ 0 de 2.526 peticiones | ✅ 0 de 7.734 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ 433 MB | ✅ 430 MB | < 450 MB |
| p95 de `/api/analysis` en caché | ✅ 0,46 s (n = 306) | ✅ 0,10 s (n = 1.185) | < 2 s |
| Memoria estable en la segunda mitad | ❌ +97 MB (ver nota) | ✅ −8,4 MB | < 25 MB |
| La cola no retrasa a un usuario más que otro análisis | ✅ espera máx. 1,36 s ≤ tenencia máx. 4,24 s | ✅ 1,22 s ≤ 7,33 s; espera p95 de un usuario: 0,0 s | espera ≤ tenencia |

- **Nota sobre la prueba de 5 minutos.** La subida es una excursión por la concurrencia (análisis nuevos y PDF a la
  vez), no una fuga: en la de 12 minutos la memoria oscila entre 330 y 430 MB sin tendencia (gráfica de la serie en el
  JSON). Python no devuelve al sistema la memoria de un pico, así que la huella marca el máximo de concurrencia.
- **Arranque en frío:** proceso nuevo → primera respuesta de la portada en 0,62 s; HTML de `/v2/AAPL` en 0,001 s;
  primer análisis de AAPL en 2,8 s. El precalentado de tendencias tarda unos 60–70 s en dejar las 30 tarjetas en
  «listo».
- **Margen.** El pico (430 MB) quedaba a 20 MB del objetivo y a 80 MB de los 512 MB de Render. El PM pidió un margen
  del 25 % (≤ 380 MB con la misma carga): ver «Memoria: de 430 a ~335 MB».

### Memoria: de 430 a ~335 MB (encargo del PM: ≤ 380 MB con la misma carga)

**Referencia de `main`** (`V4_carga_main_12min`): el mismo arnés contra el backend de main, con la mezcla de lo que
existe allí (`--mix legacy`: portada, empresa, análisis, PDF y búsqueda). Pico de 317 MB en 12 min, sin 5xx.

**Perfil por pieza** (`tools/memory_profile.py`, `V4_memoria_perfil`; cada pieza con un servidor nuevo, sobre ~117 MB
en reposo):

| Pieza | Aporta |
|---|---|
| 1 análisis en frío / 4 a la vez | +35 / +84 MB |
| Gráfica de 5 años (8 empresas) | +30 MB |
| Segmentos XBRL (8 empresas) | +43 MB |
| Tendencias: descarga del universo / con su precalentado (30 análisis) | +33 / +229 MB |
| Rivales de AAPL (su análisis y 5 rivales) | +116 MB |
| PDF actual (2) / PDF nuevo (2) / PDF nuevo (4 a la vez) | +110 / +132 / +195 MB |

**Qué ocupa de verdad** (`/__load/caches`, huella en memoria de cada caché; `tracemalloc` tras 30 análisis):
- **Las cachés suman unos 50–65 MB** al final de la carga. La mayor es la de EDGAR (43 MB, hechos de 32 emisores);
  después, `data_fetcher` (11 MB) y el resto, menos de 4 MB cada una.
- **La memoria Python viva tras 30 análisis es de ~106 MB**, pero la huella del proceso crece ~230 MB. El resto son
  transitorios que el proceso ya no devuelve (fragmentación). Sin EDGAR, esos 30 análisis dejan 181 MB en lugar de
  ~300: EDGAR es la pieza que más pesa.
- **Varianza.** Con la misma carga, el pico varía ±40 MB entre corridas (la huella física de macOS incluye la memoria
  comprimida, que depende del resto del sistema). Por eso cada opción se mide al menos tres veces.

**Cambios** (ninguna cifra cambia: `diff_golden` sin diferencias en el panel y en local; cada uno con su test):

| Cambio | Efecto medido |
|---|---|
| Caché de Finnhub: solo lo que lee `enrich_info` (`metric` y las series de Piotroski de 2 años) | 1,74 MB → <0,1 MB por empresa |
| Descarga del universo de tendencias, lote a lote, en un turno de fondo (`_background_slot`) | no coincide con 4 análisis |
| `/api/v2/pdf` como turno de usuario (`_slot`) y segmentos solo de caché (V6, B9) | el PDF no descarga instancias XBRL en su turno |
| Gráfica y segmentos: 2 descargas a la vez, una por símbolo (V6, B8) | sin descargas duplicadas |
| companyfacts leído concepto a concepto (`reduce_facts_stream`) y lo reducido rehecho en memoria contigua | pico de la lectura −60 % (JPM 43 → 15 MB) |
| Hechos de EDGAR con sus cadenas repetidas compartidas | 1,45 → 0,80 MB por emisor en caché |

**Resultado con el código final** (20 usuarios, mezcla v4, fuentes reales; `V4_fin_*`):

| Corrida | Pico | p95 análisis en caché | 5xx |
|---|---|---|---|
| 5 min (1) | 396 MB | 0,42 s | 0 |
| 5 min (2) | 339 MB | 0,41 s | 0 |
| 5 min (3) | 334 MB | 0,43 s | 0 |
| **12 min** | **335 MB** | 0,07 s | 0 |

Antes: 433 MB (5 min) y 430 MB (12 min). La mediana baja a ~337 MB (−22 %), dentro del objetivo en 3 de 4 corridas.
La corrida (1) pasó de 380 MB: fue la de calentamiento más alto (315 MB) y su memoria no se estabilizó (+27 MB en la
segunda mitad).

**Opciones medidas para bajar más** (decide el PM):

| Opción | Picos (5 min) | p95 | Coste |
|---|---|---|---|
| Nada más (configuración actual) | 396 / 339 / 334 | 0,41–0,43 s | — |
| `[edgar] cache_max_issuers` 32 → 16 | 345 / 330 / 325 | 0,40–0,49 s | más emisores vuelven a descargar su companyfacts (1–8 MB) en el día; si la SEC no responde dentro del presupuesto (3 s), ese análisis sale sin EDGAR |
| `max_concurrent_analyses` 4 → 3 | 426 / 352 (código anterior) | 0,62 / 0,40 s | no baja el pico (lo marca la retención, no la concurrencia) y empeora la latencia: no se recomienda |
| Sin precalentado de tendencias | 384 (una corrida, código anterior) | 0,36 s | las tarjetas de la portada sin calidad ni precio del motor |

**Decisión del PM: configuración actual; EDGAR 32; la medición definitiva será en Render tras la migración (E6).** La
mediana (~337 MB) y la corrida de 12 minutos (335 MB) cumplen el objetivo, y el peor caso (396 MB) deja más de 110 MB
hasta 512. Bajar EDGAR a 16 ahorra poco y arriesga análisis sin EDGAR si la SEC tarda.

### Fallo que encontró y su arreglo en origen

**Cachés por símbolo sin tope.** La memoria crecía con cada empresa distinta y, con el keepalive, el proceso vive días.
Además, el precalentado (30 empresas al día), los rivales y las búsquedas suman empresas nuevas cada día. Estas cachés
guardaban una entrada por símbolo para siempre (la caducidad solo decidía si se usaba):
- `yf_adapter._cache` y `_best_cache` (info y último snapshot bueno, ~0,8 MB en memoria por empresa);
- `finnhub_fallback._cache` (~200 kB serializados por empresa);
- `price_history._cache`.

Arreglo:
- `lib/bounded.py` y topes en TOML: `[yahoo] info_cache_max_symbols = 48`, `[finnhub] cache_max_entries = 96` y
  `[history] cache_max = 64`;
- los topes que ya existían, ajustados al presupuesto medido: `statements_cache_max_entries` de 700 a 336 y
  `[edgar] cache_max_issuers` de 64 a 32 (medidos 1,35 MB de hechos reducidos por emisor, no los ~0,5 que se
  suponían);
- tests en `test_bounded_caches.py`;
- ninguna cifra cambia: solo cuánto se guarda en caché.

Antes del arreglo, la primera prueba de 5 minutos crecía 135–141 MB en la segunda mitad.

## 3. V5 · Producción simulada (`frontend/out` de la rama servido por el backend)

| Comprobación | Resultado |
|---|---|
| `/` y `/stock/AAPL` idénticas a `main` (escritorio 1440 y móvil 375) | ✅ **idénticas píxel a píxel**. `npm run legado:base` con el `out` de `main`, luego `npm run build` y `npm run legado:comparar` (`maxDiffPixels: 0`). Reproducible tras fusionar E3 y E5 |
| Recarga directa en una URL profunda (`/v2/AAPL/valor`, `/v2/AAPL/valor/`, `/v2/JPM/calidad`, `/v2/BRK-B`) | ✅ 200, HTML de la historia, y la página carga la empresa (`e2e/v2/produccion.spec.ts`, solo con `E2E_BUILD=1`) |
| Rutas maliciosas | ✅ 404 sin servir nada (ver la lista debajo) |
| `e2e:v2` completo contra el build | ✅ 149 pasadas, 3 saltadas (también las 16 de producción simulada); `e2e:fallos` contra el build: 36/36 |
| Lighthouse | Medido en E4 sobre el build (`docs/rediseno/capturas-e4/`): `/v2` 100/100 (escritorio) y 96/100 (móvil); `/v2/AAPL` 100/100 y 90/100. Tras fusionar la v4: `/v2/AAPL/valor` 100/100 (escritorio) y 89/100 (móvil) (`verificacion/lighthouse-v2-AAPL-valor-*.json`) |

**Rutas maliciosas probadas:**
- crudas, con un uvicorn real (`backend/tests/test_v2_serving.py`): `/v2/%2e%2e/…`, `/v2/..%2f..%2fbackend/main.py`,
  `/v2/%2e%2e/%2e%2e/backend/main.py`, `/v2/AAPL/%2e%2e/%2e%2e/…` y `/v2/../…`;
- con el navegador: `..%2f`, `..%5c`.

**Fallo que encontró: los recorridos de ruta recibían la historia (200).** No se servía ningún archivo de fuera de
`out/v2`, pero el PM pide 404. `_v2_file` rechaza ahora cualquier segmento `..` o salida de `out/v2` (uvicorn ya ha
decodificado `%2e%2e` y `%2f`) y responde 404 sin servir nada. Los navegadores normalizan `%2e%2e` antes de enviar; por
eso las rutas crudas se prueban por HTTP con `http.client`.

## 4. Verificación final de esta parte

| Comprobación | Resultado |
|---|---|
| Backend `pytest` | 4393 pasadas, 1 saltada |
| `npm run test:v2` | 77/77 |
| `npm run check` | en verde (46 salidas) |
| `e2e:v2` con `next dev` | 133 pasadas, 19 saltadas (las de producción simulada solo corren contra el build) |
| `e2e:v2` contra el build | 149 pasadas, 3 saltadas |
| `e2e:fallos` con `next dev` y contra el build | 36/36 y 36/36 |
| Tras fusionar la v4 y V6 | `pytest` 4.819 pasadas; `e2e:v2` contra el build 316 pasadas; `e2e:fallos` con las 9 páginas 198/198; `legado:comparar` 4/4; `e2e/legado/csp.spec.ts` 10/10 |
| Secretos | ningún informe ni fixture contiene `token=`; las claves solo constan como presentes (sí/no) |

## 4 bis. V6 · arreglos del backend

Los hallazgos de la revisión de código y seguridad del PM (B1–B17 y la cabecera F23) están arreglados con su test:
`verificacion/V6_arreglos_backend.md`.

## 5. Para E3 (sin tocar sus archivos)

- `StoryPageClient`: usar `fetchAnalysisV2` de `@/v2/lib/analysis` (hallazgo 7 de §1). Después, quitar el `test.fail`
  de `e2e/fallos/fuentes-caidas.spec.ts`.
- Al fusionar:
  - `npm run e2e:fallos` con `V2_PAGES=…` (las 9 páginas);
  - `npm run legado:base` / `legado:comparar`;
  - Lighthouse de `/v2/AAPL/valor`.
- `PriceChart` (E2a): E3 exportó sus utilidades. El modo de referencia solo cambia su rama sin serie de la empresa.

## 6. Pendiente (cuando E3 y E5 estén fusionados)

- V1 (panel completo × páginas × navegadores × tamaños × temas).
- V2 (fuentes reales en 38+ tickers y casos raros).
- V3 extendida a las 9 páginas y a `/api/v2/pdf`.
- V6 (revisión de código y seguridad).
- V7 (lector nuevo).
- `docs/rediseno/V4_VERIFICACION.md` completo.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
