# Bitácora del plan de fiabilidad

> **Lee esto primero en cada chat nuevo.** Es el estado vivo del trabajo. El plan (qué, cómo y por qué) está en
> [`../PLAN_FIABILIDAD.md`](../PLAN_FIABILIDAD.md). El historial técnico detallado está en [`../RECON.md`](../RECON.md) §7.
> Los prompts de cada fase están en [`prompts/`](prompts/).

## Cómo se usa este archivo

- **Al empezar una sesión:** lee "Estado actual", la fila de la fase en curso y las últimas 3 entradas del registro.
- **Al terminar una sesión** (aunque se quede a medias), **añade una entrada al registro** con la plantilla del
  final y actualiza "Estado actual" y la tabla de fases. Una sesión que no deja entrada no ocurrió.
- **Nunca borres entradas.** Si algo resultó falso, añade una entrada nueva que lo corrija y enlace a la anterior.
- Dos tipos de chat: **planificación** (no toca código; decide fases y revisa) y **operador** (escribe código de
  una fase). El operador no salta de fase ni toma decisiones D# por su cuenta: las propone y se detiene.

## Estado actual

| Campo | Valor |
|---|---|
| Fase en curso | **Fase 0 — Congelar y medir** (🛑 validación con Finnhub superada; espera visto bueno para capturar el panel, registro #4) |
| Rama de trabajo | `fiabilidad/f0-panel` (creada desde `main` local `f9d6c30`; sin commits propios todavía) |
| Producción | `9e78f3b` (etapas 11b + 9c), verificado el 2026-10-13. Rollback: `a6482f9` |
| `main` local | `f9d6c30` (informe de deploy), **1 commit por delante de origin, sin push** (pushear redespliega) |
| Último cierre de sesión | 2026-10-14 · operador F0 (ver registro #4) |
| Bloqueos | Visto bueno del usuario a la validación (condición 1) antes de capturar el panel |

## Fases

| Fase | Estado | Rama | Commits | Aprobada por el usuario | Deploy |
|---|---|---|---|---|---|
| 0 Congelar y medir | 🛑 T2 validada, espera T3 | `fiabilidad/f0-panel` | — | — | no aplica |
| 1 Lo visible hoy | 🔒 espera F0 | — | — | — | — |
| 2 Verdad de datos (EDGAR) | 🔒 espera F1 | — | — | — | — |
| 3 Método por arquetipo | 🔒 espera F2 | — | — | — | — |
| 4 Escalas y confianza | 🔒 espera F3 | — | — | — | — |
| 5 Técnica y conductual | 🔒 espera F4 | — | — | — | — |
| 6 Infraestructura | 🔒 diagnóstico en F2 | — | — | — | — |
| 7 Vigilancia / calibración | 🔒 vigilancia tras F0 | — | — | — | — |

Leyenda: ⏳ pendiente · 🔧 en curso · 🛑 detenida esperando al usuario · ✅ cerrada · 🔒 bloqueada por puerta

## Decisiones (D1–D7 del plan, §6)

| # | Tema | Estado | Decidido | Fecha |
|---|---|---|---|---|
| D1 | Códigos internos en el PDF | abierta | — | — |
| D2 | Papel de SEC EDGAR | abierta | — | — |
| D3 | Precio con un solo método (RECON §7.17) | abierta | — | — |
| D4 | Arquetipo "crecimiento rentable" | abierta | — | — |
| D5 | Capa técnica en el score | abierta | — | — |
| D6 | Infraestructura | abierta | — | — |
| D7 | Universo de empresas | abierta | — | — |
| D8 | `golden/prod` ya no representa producción (base anual frente a TTM; registro #2): ¿retirarlo o sustituirlo por el juego `panel`? | abierta (decidir al cerrar F0) | — | — |

Decisiones nuevas que surjan en una sesión: se añaden aquí como D8, D9… con estado "abierta" y el operador se detiene.

**D8 — contexto para decidir (operador F0, 2026-10-14).** Los fixtures `prod` (capturados en Render el 11-oct con
`/api/_capture`) no traen estados trimestrales, así que con el código actual su replay se calcula en base **anual**,
mientras que prod calcula hoy en **TTM** (`data_provenance.ttm.basis` anual → ttm en JPM y NFLX). `golden/prod`
describe un camino que producción ya no recorre. Opciones (sin decidir): (a) congelarlo como histórico y sacarlo de
la regresión; (b) mantenerlo en la regresión como caso "plan B sin trimestrales" (sigue siendo una ruta posible si
Yahoo deja de servir los trimestrales), renombrado para que no se lea como "producción"; (c) sustituirlo por el
juego `panel` (que ya contiene los 6 tickers) y borrarlo. La fase 0 no lo toca: la regla prohíbe regenerarlo.

## Mapa de pendientes → fase

Siembra inicial (2026-10-14). **La fase 0 completa este mapa** recorriendo todos los pendientes abiertos de RECON
§7.x y asignando cada uno a una fase, o marcándolo como descartado con su motivo.

| Pendiente | Origen | Fase |
|---|---|---|
| Maquetación página 2 del PDF (panel "Composición" recortado/solapado) | corrida 2026-10-14 | 1 |
| PLTR "EBIT negativo" con EBIT +$2.63B | corrida 2026-10-14 | 1 |
| "STRONG" en JPM; "MATURE"/"por_defecto" en el PDF | corrida 2026-10-14 | 1 (D1) |
| Piotroski FY frente a TTM (AAPL) / bases mezcladas plan B (AMZN) | corrida + memoria 11b | 2 |
| JNJ sin Altman (utilidades retenidas) | corrida 2026-10-14 | 2 |
| TSM forward P/E 18.9 frente a TTM 31.7 (¿ADR/ordinaria?) | corrida 2026-10-14 | 2 |
| Beta de Finnhub en ADR (NVO 1.64 frente a 0.59) | memoria 11b | 2 |
| Yahoo 401 en Render, fuente nunca "alta" | RECON §7.1 | 2 / 6 |
| PLTR, NVDA, CRWD sin arquetipo propio | corrida 2026-10-14 | 3 (D4) |
| CAT, DOW como "Madura"; TSM `ciclica_condicional_estable` | corrida 2026-10-14 | 3 |
| Crecimiento del DCF (CAGR 3a frente a interanual, AAPL) | corrida 2026-10-14 | 3 |
| Precio con un solo método evaluable | RECON §7.17 | 3 (D3) |
| Cobertura de intereses en utilities | memoria 11b | 3 |
| BRK-B posible cíclica / conglomerado | RECON §7.16 | 3 |
| AMZN sin categoría Crecimiento (base ≤ 0) | corrida 2026-10-14 | 3 |
| Calidad saturada en 100 (PLTR, TSM, NFLX, V) | corrida + RECON 7.14 | 4 |
| Producción atiende en serie; PDF de 20–60 s; JPM 46.1 s en frío (14-oct, 14:28) | corrida 2026-10-14 + F0 | 6 (D6) |
| Etapa 10 del spec: capa conductual + noticias | redesign-spec §5 | 5 |
| Rf y prima de riesgo con revisión mensual | RECON §7.13 | 7 |
| Fecha de resultados no se lee en ninguna ruta (bug f): necesaria para PEAD | RECON §7.7 | 5 |
| Crecimiento de Finnhub sospechoso (FCX −24.2% frente a +1.8% en estados): desde 9b ya no puntúa (el DCF y Crecimiento usan el CAGR de los estados), pero se muestra como dato "(interanual)" | RECON §7.7 / §7.15 | 2 |
| Plan B sin `lastSplitFactor` (un estado sin ajustar por split anularía la comparación de acciones) | RECON §7.7 | 2 |
| Forward EPS sin fuente en prod (Finnhub da forward P/E, no BPA) | RECON §7.7 / §7.5 | 2 |
| Crecimiento bancario con "Total Revenue": medirlo con margen de intereses neto o ingresos netos | RECON §7.8 | 3 |
| Bandas paralelas: alinear las de las alertas (cobertura, DCF, beta, DN/EBITDA) con las del score; "cuatro copias de umbrales" | RECON §7.9 / §7.14 / PLAN §1 | 4 |
| Benchmarks y medianas sectoriales PROVISIONALES sin fuente (market P/E 23x, ROE 20%/8%, D/E 1.0x…; forward market 18.9x) | RECON §7.14 / §7.16 | 4 |
| Bandas de REIT (DN/EBITDA ≤5.0x…) y de utilities (cobertura ≥3.5x…) PROVISIONALES, sin muestra | RECON §7.14 / 61212c1 | 4 |
| MATURE de dividendo alto (≥ 4%): Crecimiento como retorno total, propuesto sin aplicar (faltaba fixture; el panel trae KO, PG, JNJ, DOW) | RECON §7.11 / §7.14 | 3 |
| SBC en MATURE (> 5% de ingresos): propuesto sin aplicar (faltaba fixture; el panel trae PLTR, CRWD, SNOW, NVDA) | RECON §7.14 | 3 |
| Techo de la calidad cuando la lectura tiene señales en contra (NFLX 100 con P/E no fiable y DCF por debajo) | RECON §7.12 / §7.13 (a) | 4 |
| Confianza "alta" con convergencia solo "media" (V local 0.80) | RECON §7.13 (c) | 4 |
| Número de Graham calculado en REIT con BPA deprimido por la depreciación (se muestra, no vota) | RECON §7.13 (b) | 3 |
| Barra de 52 semanas en la web con lectura de precio (curva en U) frente a "solo posición" del PDF: verificar si sigue | RECON §7.14 | 1 |
| Mejoras aprobadas: P/FFO visible en la web | memoria (backlog) | 1 |
| Mejoras aprobadas: DuPont del ROE, margen FCF con tendencia, Rule of 40 (crecimiento rentable) | memoria (backlog) | 3 (D4) |
| `golden/prod` en base anual mientras prod calcula en TTM | F0 (registro #2) | D8 |
| `muestra` capturada por quoteSummary sin Finnhub: no representa producción | F0 (registro #2) | 0 (la sustituye `panel`) |
| Descartado — resuelto: `yearly_financials` vacío en prod (9b: Histórico desde los estados anuales) | RECON §7.7 | — |
| Descartado — resuelto: normalización de partidas no recurrentes (C1, etapa 7) | RECON §7.7 | — |
| Descartado — resuelto: financieras con el YoY de los estados (G2 → política `crecimiento_financiera_estados`, visible en JPM prod) | RECON §7.8 | — |
| Descartado — resuelto en la etapa 8: impuesto efectivo, WACC mostrado = usado, celdas del grid recortadas, sin suelo terminal | RECON §7.9 | — |
| Descartado — resuelto: crecimiento muy negativo en cíclicas (ciclo medio, etapas 6 y 9a) | RECON §7.9 | — |
| Descartado — resuelto: D/E de financieras en la UI y V clasificada como financiera (9b; V = MATURE por red de pagos) | RECON §7.9 | — |
| Descartado — resuelto en las etapas 6–8: regresiones de §7.10 (ramas REIT, FINANCIAL, GROWTH_PRE_PROFIT, ciclo medio, base anómala) | RECON §7.10 | — |
| Descartado — resuelto: crecimiento por acción generalizado (etapa 7) y DCF de mantenimiento en cíclicas (etapa 8) | RECON §7.11 | — |
| Descartado — resuelto en F0: TTM en prod sin verificar (prod calcula en TTM; validado el 14-oct, registro #4) | RECON §7.12 / §7.13 | — |
| Descartado — resuelto: motivos de la confianza en lenguaje llano (9b, `plain_language.py`) | RECON §7.14 | — |
| Descartado — obsoleto: PDF de revisión desde los fixtures de prod (lo sustituye `panel_run`) | RECON §7.14 | — |
| Descartado — resuelto: golden de la 9b sin regenerar (18a6a0c) | RECON §7.15 | — |
| Descartado — resuelto en la 11b: clase de acciones BRK-B, filas IFRS, plan B "degradado" con reintentos | RECON §7.16 | — |
| Descartado — resuelto en la 11b: TSM en TWD, BRK-B P/E 0.0087, SPY analizado, DCF negativo de NEE, "CYCLICAL" y "$-8" en la prosa | memoria (deploy 9b) | — |
| Descartado — sin efecto material: SNOW con deuda neta en local y caja neta en prod (peso de la deuda 2%) | RECON §7.13 | — |

## Registro de sesiones

<!-- Plantilla (copiar al final, numerar en orden):

### #N · AAAA-MM-DD · <planificación | operador> · Fase X
- **Objetivo de la sesión:**
- **Hecho:** (con hashes de commit)
- **Verificación:** (comandos ejecutados y resultado: suite, golden, panel, PDF)
- **Decisiones tomadas por el usuario:** (cita literal de la aprobación)
- **Abierto / siguiente paso:**
- **Archivos tocados:**
- **Avisos para el siguiente chat:** (gotchas, cosas a no repetir)
-->

### #1 · 2026-10-14 · planificación · antes de la fase 0
- **Objetivo de la sesión:** evaluar el motor en producción y definir el plan de fiabilidad.
- **Hecho:** corrida de 12 tickers (AAPL, JPM, O, XOM, KO, JNJ, NEE, CAT, PLTR, AMZN, TSM, RIVN) contra
  finanzer.app: los 12 en 200. Salida en `~/Downloads/finanzer_corrida_2026-10-14/` (PDF, JSON de análisis, texto
  extraído, PNG por página). Redactados `docs/PLAN_FIABILIDAD.md`, esta bitácora y `prompts/F0_congelar_y_medir.md`.
  Sin cambios de código. Sin commit.
- **Verificación:** resultados resumidos en PLAN_FIABILIDAD §1.
- **Decisiones tomadas por el usuario:** "un solo plan" — PLAN_FIABILIDAD sustituye al plan anterior y absorbe lo
  que quedaba (la etapa 10 pasa a ser la fase 5). RECON sigue siendo el historial. El código se hace en otro chat.
- **Abierto / siguiente paso:** abrir un chat de operador con `prompts/F0_congelar_y_medir.md`.
- **Archivos tocados:** `docs/PLAN_FIABILIDAD.md`, `docs/fiabilidad/BITACORA.md`,
  `docs/fiabilidad/prompts/F0_congelar_y_medir.md` (los tres sin commitear).
- **Avisos para el siguiente chat:** `main` local tiene `f9d6c30` sin push: no pushear sin orden (redespliega).
  Producción atiende en serie: no lanzar más de 12 peticiones paralelas contra finanzer.app.

### #2 · 2026-10-14 · operador · Fase 0 (T1–T2, detenida en el punto de parada 1)
- **Objetivo de la sesión:** T1 (rama y suite) y T2 (método de captura fiel a producción), hasta el punto de parada 1.
- **Hecho:**
  - T1: rama `fiabilidad/f0-panel` creada desde `main` local (`f9d6c30`). Sin commits.
  - T2, diagnóstico: la "simulación de Render" de la etapa 11b **no quedó como herramienta**; solo existe el test
    unitario `test_plan_b_is_not_retried_and_quote_summary_block_is_remembered` (monkeypatch de un 401). El juego
    `muestra` se capturó en local **por quoteSummary (200), sin plan B y sin Finnhub**: no representa producción.
  - T2, prototipo (fuera de `backend/`, sin commitear): `docs/fiabilidad/f0_t2_prototipo/render_sim_proto.py`
    (captura con Render simulado) y `compare.py` (diff de dos análisis con la procedencia de Finnhub). Evidencia en
    `f0_t2_prototipo/evidencia/` (análisis de prod en vivo de JPM y NFLX del 14-oct y los simulados).
  - T2, propuesta (pendiente de aprobación):
    - **Opción A (recomendada): captura local con Render simulado.** Sobre `fb.record` se añaden dos ganchos en
      `tests/`: S1, `quoteSummary` responde 401 con el cuerpo de prod ("Invalid Crumb"), y S2, `yfinance.Ticker.info`
      devuelve `{}` (en prod solo trae `trailingPegRatio`; el plan B solo lee `beta`). Todo lo demás (fast_info,
      estados anuales y trimestrales, sonda de moneda, tipos de cambio, búsqueda y Finnhub) va a la red real, con
      `.venv313` (mismas versiones que prod) y la clave de Finnhub exportada solo en la pestaña de terminal del
      usuario. Pros: no toca producción ni despliega, repetible, graba todo lo que consume el código actual.
      Riesgos: la IP residencial podría recibir algo distinto que la de Render en los endpoints sin crumb (no
      observado en JPM), y si Yahoo cambia en Render la simulación no se entera. Mitigación: `panel_run --mode live`
      compara cada vez contra finanzer.app (T4/T5).
    - **Opción B: reabrir `/api/_capture` en producción con token.** Datos reales de Render, pero exige desplegar
      (pushear `main` redespliega y arrastra `f9d6c30`), gestionar `CAPTURE_TOKEN` en Render, reescribir el endpoint
      (el de `e0be7d4` no graba trimestrales, moneda, tipos de cambio ni búsqueda), cargar un servidor que atiende en
      serie y volver a retirarlo. Descartada salvo orden expresa.
    - Opción C (solo corridas en vivo, sin fixtures): no reproducible; no sirve de vara.
- **Verificación:**
  - Suite antes de empezar: `cd backend && ../.venv313/bin/python -m pytest tests -q` → **597 passed, 1 skipped,
    0 xfail** (19.5 s).
  - Prototipo sin Finnhub: `.venv313/bin/python render_sim_proto.py <out> JPM NFLX` → los dos por
    `plan_b_yfinance`, quoteSummary `[401, 401]` como en prod, replay **idéntico byte a byte**, 0 accesos no grabados.
  - Contra `https://finanzer.app/api/analysis/{JPM,NFLX}` del mismo día (2 peticiones, 200 en 4.6 s y 3.8 s): en JPM
    **todas** las diferencias (51 de 649 campos) se explican por Finnhub ausente en local (beta, forward P/E, PEG,
    dividendo, crecimiento) y por la tasa libre de riesgo (prod usa ^TNX en vivo; los fixtures congelan la de config
    por diseño). Estados, precio, arquetipo, calidad y nivel de precio coinciden. En NFLX el nivel de precio cambia
    (exigente 42 → razonable 46), atribuible a los 11 campos de Finnhub; **sin verificar hasta repetir con Finnhub**.
- **Decisiones tomadas por el usuario:** ninguna todavía.
- **Abierto / siguiente paso:**
  1. El usuario, en su pestaña de terminal con `FINNHUB_API_KEY` exportada, corre el prototipo con Finnhub sobre JPM
     y NFLX; el operador compara con prod en vivo del mismo día (debe quedar solo la diferencia de Rf).
  2. Aprobación del método (A o B). Con A: llevar S1/S2 a `tests/` (p. ej. `capture_fixtures.py --env panel
     --render-sim`) y seguir con T3.
- **Archivos tocados:** `docs/fiabilidad/BITACORA.md` (esta entrada), `docs/fiabilidad/f0_t2_prototipo/` (nuevo).
  Nada en `backend/`. Sin commits.
- **Avisos para el siguiente chat:**
  - **`golden/prod` ya no representa producción:** prod calcula hoy en base **TTM** (lee los trimestrales), pero los
    fixtures `prod` del 11-oct no tienen trimestrales y su golden sale en base **anual** (`data_provenance.ttm.basis`
    anual → ttm en JPM y NFLX). Por eso la validación de T2 se hizo contra prod en vivo y no contra `golden/prod`.
    No se regenera (lo prohíbe la fase); lo sustituye el juego `panel`.
  - `backend/tests/README.md` lista 6 tests xfail de bugs conocidos, pero hoy hay 0 xfail: tabla desactualizada.
  - Los fixtures siempre usan la Rf de config; el modo `live` siempre diferirá en Rf frente al `replay` (F5).
  - La sesión se abrió en `finanzer_complete_v3`; el repo de trabajo es `~/Downloads/finanzer_next` (rutas absolutas).

### #3 · 2026-10-14 · operador · Fase 0 (T2 aprobada con condiciones; validación con Finnhub pendiente)
- **Objetivo de la sesión:** aplicar la aprobación de la opción A y validarla con Finnhub antes de capturar el panel.
- **Decisiones tomadas por el usuario:** "Apruebo la opción A, con estas condiciones: 1. Primero valida la captura
  con Finnhub de JPM y NFLX contra producción en vivo. Si queda alguna diferencia que no sea la Rf (en especial el
  nivel de precio de NFLX), detente y explícala antes de capturar el panel. 2. Lleva S1 y S2 a backend/tests/ como
  modo de capture_fixtures.py (p. ej. --render-sim). Saca los scripts del prototipo de docs/ (la evidencia puede
  quedarse). 3. Metadatos de cada fixture: render simulado (S1, S2), si Finnhub participó y Rf congelada. 4. En
  panel_run --mode live, separa en su propia sección las diferencias que vienen solo de la Rf. 5. Respeta el límite
  de Finnhub (60 peticiones por minuto) al capturar los 31 tickers. 6. Registra en la bitácora la decisión D8
  (abierta): qué hacer con golden/prod, que ya no representa producción. Corrige la tabla de xfail del README de
  tests."
- **Hecho (sin commits todavía):**
  - Condición 2: `fixture_backend.render_sim()` (S1, S2 y Finnhub a ≤ 1 petición cada 1.1 s ≈ 55/min, condición 5),
    constantes `PANEL_ENV`, `PANEL_GROUPS`, `PANEL_TICKERS`; `capture_fixtures.py --render-sim [--dir]` y
    `--env panel` (exige `--render-sim` y `FINNHUB_API_KEY`). Prototipo borrado de `docs/`; queda `evidencia/`.
  - Condición 3: metadatos nuevos `render_simulation` (S1, S2), `risk_free.frozen`, `yahoo.http_statuses`
    (además de `finnhub.participated`).
  - Condición 6: D8 ya la había añadido el chat de planificación; se quitó la fila duplicada que añadí y se dejó
    el párrafo de contexto con las opciones. README de tests: tabla de bugs conocidos corregida (0 xfail, 8 tests
    ya corregidos y en qué etapa) y sección "Captura con Render simulado".
- **Verificación:** `capture_fixtures.py --render-sim --dir <scratch> JPM` → `http=[401, 401, 200, 200]`,
  `path=plan_b_yfinance`, replay idéntico; `--env panel` sin `--render-sim` o sin clave → error explícito. Suite:
  `597 passed, 1 skipped` (17.3 s).
- **Abierto / siguiente paso:** el usuario corre en su pestaña (con la clave exportada)
  `cd ~/Downloads/finanzer_next/backend && ../.venv313/bin/python tests/capture_fixtures.py --render-sim --dir ../docs/fiabilidad/f0_t2_prototipo/captura_fh JPM NFLX`;
  el operador compara contra finanzer.app del mismo día separando las diferencias que solo vienen de la Rf
  (condición 1). Si queda algo más, se detiene y lo explica. Después: T3.
- **Archivos tocados:** `backend/tests/fixture_backend.py`, `backend/tests/capture_fixtures.py`,
  `backend/tests/README.md`, `docs/fiabilidad/BITACORA.md`, `docs/fiabilidad/f0_t2_prototipo/` (scripts fuera).
- **Avisos para el siguiente chat:** la bitácora la editan dos chats a la vez (planificación y operador): releerla
  justo antes de escribir y no duplicar filas.

### #4 · 2026-10-14 · operador · Fase 0 (T2: validación con Finnhub superada)
- **Objetivo de la sesión:** condición 1 de la aprobación: validar la captura con Finnhub de JPM y NFLX contra
  producción en vivo antes de capturar el panel.
- **Hecho:**
  - La clave de Finnhub vive en Render, no en el Mac; los comandos con `!` del chat abren un shell sin variables
    exportadas (cuatro capturas salieron sin Finnhub y se borraron). Solución: la clave se guardó en el **Llavero de
    macOS** (servicio `finanzer-finnhub`) con un diálogo de macOS en el que la pegó el usuario; las capturas la leen
    con `FINNHUB_API_KEY=$(security find-generic-password -s finanzer-finnhub -w)`, sin imprimirla ni escribirla.
  - `capture_fixtures.py --render-sim` ahora **se niega** a capturar sin clave (salvo `--sin-finnhub`).
  - Captura de validación en `docs/fiabilidad/f0_t2_prototipo/evidencia/captura_render_sim_finnhub/` (JPM, NFLX):
    `http=[401, 401, 200, 200]`, `path=plan_b_yfinance`, `degraded=False`, `finnhub=True` (12 y 11 campos), replay
    idéntico, sin secretos (`grep -rlE "token=|apikey"` vacío).
- **Verificación** (prod en vivo a las 14:28 del 14-oct, guardada en `evidencia/prod_live_*_1428.json`):
  - Arquetipo, calidad, nivel y puntuación de precio, confianza y veredicto **idénticos** en los dos. NFLX:
    "razonable 46" en ambos: la diferencia de la sesión #2 (exigente 42) venía solo de Finnhub.
  - Diferencias restantes: JPM 42 campos (7 solo por la Rf: config 5.29% frente a ^TNX 5.194%), NFLX 75 (27 solo
    por la Rf). El resto viene **del precio intradía** (JPM 333.66 → 333.77; NFLX 70.295 → 70.25) y su arrastre
    (capitalización, múltiplos, pesos del WACC).
  - Prueba: replay con el precio y la Rf de prod → **0 diferencias** en JPM y en NFLX (tolerancia relativa 1e-6).
  - Latencia de prod: JPM 46.1 s en frío (servidor en serie), NFLX 3.3 s.
- **Decisiones tomadas por el usuario:** no rotar la clave de Finnhub (quedó visible en una captura de pantalla del
  chat): "no lo quiero cambiar. deja esa api."
- **Abierto / siguiente paso:** visto bueno a la validación (además de la Rf queda el precio intradía, explicado y
  probado) → T3, captura de los 31 con `--env panel --render-sim`. Propuesta para la condición 4: `panel_run --mode
  live` separa dos secciones, "solo Rf" y "solo precio intradía", con el mismo método (replay con la Rf y el precio
  de prod); lo que quede fuera de ambas es diferencia real.
- **Archivos tocados:** `backend/tests/capture_fixtures.py`, `docs/fiabilidad/BITACORA.md`,
  `docs/fiabilidad/f0_t2_prototipo/evidencia/`.
- **Avisos para el siguiente chat:** no pedir al usuario que exporte variables ni que use `!` para secretos; usar
  el Llavero. Responder siempre en español.

