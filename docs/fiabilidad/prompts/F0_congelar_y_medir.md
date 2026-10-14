# Prompt del operador — Fase 0: Congelar y medir

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`.

---

Eres el **operador de la fase 0 del plan de fiabilidad de Finanzer**. Tu trabajo es construir la vara de medir con la
que se juzgarán todas las fases siguientes. **En esta fase no se cambia el comportamiento del motor**: solo tests,
herramientas, fixtures, golden y documentación.

## 1. Contexto (lee esto antes de tocar nada)

Lee, en este orden, y no empieces hasta haberlo hecho:

1. `docs/fiabilidad/BITACORA.md`: estado vivo, decisiones y registro de sesiones.
2. `docs/PLAN_FIABILIDAD.md`: §0 (propiedades F1–F5), §1 (diagnóstico), §3 (panel) y §4 fase 0.
3. `backend/tests/README.md`: cómo funcionan los fixtures, los golden, los entornos y el replay sin red.
4. `backend/tests/fixture_backend.py` (constantes `TICKERS`, `ENVS`, `SAMPLE_ENV`, ganchos H1–H4) y
   `backend/tests/capture_fixtures.py`, `diff_golden.py`, `test_muestra.py`.
5. `docs/RECON.md` §7.1 (Yahoo da 401 en Render → plan B permanente), §7.16 y §7.17.

Hechos que debes tener presentes:

- **La app es `finanzer_next`** (FastAPI en `backend/`, Next.js exportado en `frontend/out/`). Render despliega
  `main` automáticamente. Producción es `9e78f3b`; `main` local va 1 commit por delante (`f9d6c30`) **sin push**.
- **Entorno de referencia:** `.venv313` (Python 3.13.4, mismas versiones que producción).
  Suite: `cd backend && ../.venv313/bin/python -m pytest tests` (sin red). Debe estar en verde antes y después.
- **Local ≠ producción.** En local Yahoo `quoteSummary` responde; en Render siempre da 401 y el pipeline cae en
  `_fallback_yfinance` + Finnhub. Una línea base capturada en local sin simular eso **no es la de producción** y no
  sirve como vara. Es el punto más delicado de esta fase.
- Juegos existentes: `fixtures/local` (12), `fixtures/prod` (FCX, JPM, NFLX), `fixtures/muestra` (20, capturada en
  local, sin golden). El endpoint `/api/_capture` de producción fue **retirado** y no debe reabrirse sin aprobación.
- **Finnhub:** la clave `FINNHUB_API_KEY` solo se exporta en una pestaña del panel de terminal, nunca en el chat ni
  en un archivo. El token nunca se guarda en fixtures (el importador ya rechaza patrones de secreto).
- Las llamadas de red desde Bash requieren `dangerouslyDisableSandbox: true`. `preview_start` no puede leer
  `~/Downloads` (permiso de macOS): si necesitas levantar el backend, hazlo con Bash en segundo plano.
- **Producción atiende las peticiones en serie.** Contra finanzer.app, como mucho 4 peticiones concurrentes.

## 2. Objetivo de la fase

Al terminar debe existir:

1. Un **panel de referencia de 31 tickers** congelado en condiciones de producción.
2. Una herramienta **`panel_run`** que corre el panel y produce un resumen comparable entre corridas.
3. La **línea base** de las propiedades F1–F5, con su número de hoy.
4. El **mapa completo de pendientes → fase** en la bitácora.

## 3. Tareas, en orden

### T1. Rama y comprobación inicial
- Crea la rama `fiabilidad/f0-panel` desde `main` local.
- Corre la suite y anota el resultado (pasados, xfail, fallidos). Si no está en verde, **detente y repórtalo**.

### T2. Método de captura fiel a producción → **PUNTO DE PARADA 1**
Diagnostica y **propón** (sin implementar) cómo capturar fixtures que reproduzcan lo que recibe el pipeline en Render:
plan B forzado (quoteSummary con 401 simulado), Finnhub activo y las mismas versiones. Busca primero cómo se
"simuló Render" en la etapa 11b (RECON §7.16: "3.2–4.4 s simulando Render") y reutilízalo si existe.
Compara al menos dos opciones (p. ej. un modo de captura local que fuerce el plan B, o reabrir temporalmente la
captura en producción con token) con pros, contras y riesgos. Valida la opción elegida con un ticker que ya tenga
fixture `prod` (JPM o NFLX): el replay de la captura nueva debe coincidir con `golden/prod` salvo diferencias
explicadas (datos de otra fecha).
**Detente y espera la aprobación del usuario antes de capturar el panel.**

### T3. Panel de 31 tickers
Nuevo juego `panel` (fixtures + golden), sin tocar los juegos existentes:

| Grupo | Tickers |
|---|---|
| Madura | AAPL, MSFT, KO, PG, JNJ |
| Financiera | JPM, BAC, PGR, V, BRK-B |
| REIT | O, PLD, AMT |
| Utility | NEE, DUK |
| Cíclica | XOM, FCX, CAT, MU, DOW |
| Crecimiento rentable | PLTR, NVDA, CRWD |
| Pre-beneficio | RIVN, SNOW |
| ADR / IFRS | TSM, ASML, NVO |
| Casos trampa | NFLX, AMZN, SPY (debe rechazarse con 422) |

- Captura con el método aprobado en T2. Una sola fecha de captura para todos; anota la fecha, el commit y si
  Finnhub participó, en los metadatos de cada fixture.
- Genera los golden del juego `panel` con el motor **tal como está** (describen el comportamiento actual, con sus
  bugs: ver el aviso del README de tests). Es la única regeneración permitida en esta fase y se hace sobre un juego
  nuevo.
- Añade el juego a la regresión y al determinismo (como `local` y `prod`). La suite debe seguir en verde.

### T4. Herramienta `panel_run`
`backend/tests/panel_run.py` (o `backend/tools/`, coherente con lo que ya hay), con:
- `--mode replay` (desde los fixtures del panel, sin red) y `--mode live --base-url https://finanzer.app`
  (o `http://localhost:8000`), con concurrencia limitada (por defecto 3).
- `--out <carpeta>`: escribe `resumen.md` y `resumen.csv`, el JSON de análisis por ticker, el PDF, el texto
  extraído del PDF y el PNG de cada página (pypdfium2; instálalo en `.venv313` si hace falta y anótalo en
  `requirements-test.txt`).
- Columnas mínimas del resumen: ticker, grupo, arquetipo (código y regla), **arquetipo esperado** (tabla de T5),
  calidad (puntuación y nivel), precio (sin ajustar, ajustado y nivel), confianza y sus motivos, estado y
  fiabilidad del DCF, upside del DCF, ruta de datos (`data_provenance.path`), nº de campos de Finnhub, nº de
  intervenciones de `data_validation`, errores, tiempo de respuesta (en `live`), nº de páginas del PDF.
- `--compare <carpeta_anterior>`: añade una sección "cambios" con los tickers cuyo arquetipo, nivel de calidad,
  nivel de precio o confianza cambiaron.
- Tests básicos de la herramienta (que el resumen tenga todas las columnas y que `--compare` detecte un cambio
  inyectado).

### T5. Línea base F1–F5
Corre `panel_run` en `replay` y en `live` contra finanzer.app. Escribe `docs/fiabilidad/F0_LINEA_BASE.md` con:

- **F1 Dato correcto:** aún no medible contra la fuente oficial (eso es la fase 2). Registra lo medible hoy: campos
  rellenados por Finnhub por ticker, intervenciones de validación, campos clave ausentes (p. ej. utilidades
  retenidas en JNJ).
- **F2 Método adecuado:** arquetipo obtenido frente al esperado. Esta es la tabla de expectativas propuesta por el
  planificador; preséntala al usuario para que la valide, **no la tomes como verdad**:

  | Esperado | Tickers |
  |---|---|
  | MATURE | AAPL, MSFT, KO, PG, JNJ, V (pagos: no es banco), NVO, NFLX, AMZN |
  | FINANCIAL | JPM, BAC, PGR, BRK-B (conglomerado: marcar como dudoso) |
  | REIT | O, PLD, AMT |
  | UTILITY | NEE, DUK |
  | CYCLICAL | XOM, FCX, CAT, MU, DOW |
  | "Crecimiento rentable" (hoy no existe → hoy saldrán como discrepancia) | PLTR, NVDA, CRWD |
  | GROWTH_PRE_PROFIT | RIVN, SNOW |
  | A decidir con el usuario (fundición/equipos de semiconductores: ¿cíclica o crecimiento rentable?) | TSM, ASML |
  | Rechazo 422 | SPY |

- **F3 Texto fiel al dato:** contradicciones encontradas. Haz un primer barrido con comprobaciones simples sobre el
  texto extraído (como mínimo: "EBIT negativo" frente a `operating_income`, "en máximos/mínimos" frente a la
  posición en el rango de 52 semanas, palabras en inglés como "STRONG", códigos internos en mayúsculas como
  "MATURE") y añade los defectos de maquetación visibles en los PNG. Es un inventario, no el guardián (eso es la
  fase 1).
- **F4 Incertidumbre honesta:** distribución de calidad y de precio en el panel (cuántos ≥ 95, cuántos con un solo
  método evaluable, cuántos con DCF de fiabilidad baja).
- **F5 Reproducible:** replay frente a live (qué cambia y por qué: fecha de datos, precio), determinismo (de la
  suite) y latencias del modo live (p50, p95, máximo).

### T6. Mapa de pendientes
Recorre RECON §7.7 a §7.17 y la memoria del proyecto. Cada pendiente abierto va a la tabla "Mapa de pendientes →
fase" de la bitácora con su origen y su fase, o como "descartado" con el motivo. No dejes la fila
"*(resto … lo completa la fase 0)*".

### T7. Cierre → **PUNTO DE PARADA 2**
- RECON: nueva sección §7.18 "Fase 0 del plan de fiabilidad" (qué se capturó, cómo, y la línea base resumida).
- Bitácora: entrada en el registro con la plantilla, "Estado actual" y la fila de la fase 0 actualizados.
- Commits pequeños y descriptivos en `fiabilidad/f0-panel` (prefijo `F0:`). **Sin push y sin merge.**
- Presenta al usuario: la tabla de arquetipos obtenidos frente a esperados, el resumen de F1–F5 y la lista de
  pendientes mapeados. **Detente y espera su aprobación** para cerrar la fase.

## 4. Reglas que no se rompen

- **No cambies el comportamiento del motor** (`backend/lib/`, `backend/main.py`, `config/`, `frontend/`). Si una
  herramienta necesita un gancho nuevo, va en `tests/` como los H1–H4. Si crees que hace falta tocar el motor,
  detente y pregunta.
- **No regeneres** los golden de `local` ni de `prod`. Solo se crean los del juego nuevo `panel`.
- **No pushees, no mergees, no despliegues.** Pushear `main` redespliega producción.
- **No tomes decisiones D1–D7** ni cambies la tabla de arquetipos esperados: propón y detente.
- Si algo no cuadra con este prompt (un archivo que no existe, un comando que falla, una cifra distinta a la de la
  bitácora), **verifica primero y repórtalo** antes de seguir. La bitácora y este prompt pueden estar
  desactualizados; el código manda.
- Toda afirmación de "hecho" o "pasa" va acompañada del comando que la demuestra y su salida.
- Si la sesión termina antes de acabar la fase, deja igualmente la entrada en la bitácora con lo hecho y lo
  pendiente, para que el siguiente chat continúe sin adivinar.

## 5. Definición de terminado de la fase 0

- [ ] Suite en verde en `.venv313`, con el juego `panel` incluido en la regresión y el determinismo.
- [ ] 31 fixtures del panel capturados con el método aprobado; SPY devuelve 422.
- [ ] `panel_run` funciona en `replay` y en `live`, con `--compare` y con tests.
- [ ] `docs/fiabilidad/F0_LINEA_BASE.md` con F1–F5 y la tabla de arquetipos obtenidos frente a esperados.
- [ ] Mapa de pendientes completo en la bitácora.
- [ ] RECON §7.18, entrada en la bitácora, commits en `fiabilidad/f0-panel` sin push.
- [ ] Aprobación del usuario registrada (cita literal) en la bitácora.
