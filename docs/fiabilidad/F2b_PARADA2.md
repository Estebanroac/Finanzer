# Fase 2b · Punto de parada 2 (T8): medida final

Rama `fiabilidad/f2b-corregir` (worktree `../finanzer_next-f2b`), sin push. Fecha: 2026-10-16.

## 0. Lo que te toca

1. **Aprobar los golden de T6 y T7** con el diff causa por causa del §3. Hasta tu aprobación no se ha regenerado nada.
2. **Decisión abierta (no la tomo yo):** referencia de la herramienta F1 para el beneficio neto. Desde T7 el motor usa
   el beneficio del ordinario, como manda F2_PRECEDENCIA §2.1, pero `edgar_verify` lo compara con el de los
   propietarios (`NetIncomeLoss`, `ProfitLossAttributableToOwnersOfParent`). Hay dos opciones:
   - **(a)** Dejarla así: 6 filas quedan "fuera (definición)": PG, JPM, BAC, DUK, BCS y HSBC.
   - **(b)** Cambiar el concepto de referencia de la herramienta al del ordinario: es reclasificar, y por eso no lo he
     hecho.
3. **Pregunta de alcance:** F2_PRECEDENCIA §2.1 (escenario B) pide marcar el EBIT de Yahoo como "estimado por la
   fuente" cuando difiere más de un 2% del de EDGAR. Son 21 filas, de KO, PLD, AMT, NEE, DUK, FCX, CRWD, UL y V. No
   estaba en el prompt de la 2b y no está hecho. Mi propuesta: llevarlo a la fase 3 con la definición del EBIT.
4. **"ok, pushea"** cuando lo veas bien. Tras el deploy, las comprobaciones del §7.
5. **Render:** falta `SEC_EDGAR_USER_AGENT` en las variables de entorno. Sin ella, EDGAR queda "no disponible" (nota,
   sin techo) y no hay respaldo, factor de portada ni componentes de la deuda.

## 1. F1: dato correcto frente a SEC EDGAR

Comando: `../.venv313/bin/python tests/edgar_verify.py --whatif --out <dir>`. Las tolerancias y la clasificación de
causas son las de la 2a, sin cambios.

| Medida | Dentro de tolerancia |
|---|---|
| Línea base (2a) | 90.0% |
| Parada 1 (T3) | 90.9% |
| **Hoy, sin el arreglo de la herramienta** (`--sin-as-of`) | **1276/1411 (90.4%)** |
| **Hoy, con el arreglo** (`db4db68`, emparejamiento TTM frente a TTM) | **1284/1411 (91.0%)** |
| Ratios recalculados con EDGAR (con el arreglo) | 185/216 (85.6%) |

- **Objetivo del plan (≥ 95%): no se alcanza.** Para llegar faltan 57 filas.
- **El arreglo de la herramienta** cambia 12 filas, y todas pasan a dentro: son flujos del corte que el pipeline toma
  en TTM (respaldo de EDGAR o corte trimestral) y que la herramienta comparaba con el FY.
  - BCS: D&A, dividendos, intereses y flujo de operaciones.
  - HSBC: capex, dividendos y flujo de operaciones.
  - V y DUK: dividendos y payout.
  - JNJ: utilidades retenidas a 2026-06-30.
  - Ninguna fila pasa de dentro a fuera.
- **Por qué baja de 90.9% a 90.4% sin el arreglo:** por las 6 filas del beneficio del ordinario (§0, punto 2).

### 1.1 Filas cuya definición cierra la fase 3 por D2 (no cuentan como dentro)

| Grupo | Filas fuera |
|---|---|
| Capex (activos en arrendamiento, software, intangibles) | 20 |
| Ingresos de bancos | 6 |
| Caja de bancos y aseguradoras | 5 |
| EBIT bancario | 0 (sin dato comparable) |
| **Total** | **31** |

### 1.2 El resto (96 filas fuera) y dónde se cierra

| Campo | Filas | Causa y destino |
|---|---|---|
| Resultado operativo | 21 | Yahoo construye su EBIT (KO, PLD, AMT, NEE, DUK, FCX, CRWD, UL, V). Fase 3: definición del EBIT y marca de "estimado" (§0, punto 3) |
| Dividendo por acción | 15 | El motor usa el **indicado** (F2_PRECEDENCIA §2.2, T2) y la herramienta lo compara con el declarado o pagado TTM: definición o periodo. Queda así por diseño; el indicado se verificó en T2 contra los pagos del ADR |
| Ingresos | 13 | BRK-B (Yahoo suma las ganancias de inversión), NEE y DUK (otra etiqueta): fase 3. XOM (−2 a −3%, fuente errónea según la herramienta; causa sin verificar): fase 3. O: periodo |
| Beneficio neto | 10 | 6 del ordinario (§0, punto 2). HSBC FY (definición: la referencia es `ProfitLoss`; causa sin verificar). DOW y CRWD: fuente |
| Deuda total y a largo plazo | 14 | La deuda de la regla de T5 (arrendamientos según el EBITDA) frente al `LongTermDebt` de EDGAR: definición por diseño. AAPL, O, NEE, BAC, PLD: diferencias de 1–8% de la fuente |
| D&A, caja, acciones, intereses y BPA | 23 | Fuente o periodo, caso por caso en el detalle de `resumen.md`. CRWD: split posterior al filing (periodo) |

El detalle fila a fila está en `resumen.md` y `resultado.json`, generados con el comando de arriba.

## 2. Qué cambió en la 2b (T4–T8)

| Tarea | Commits | Qué |
|---|---|---|
| T4 | `104df65`..`08c97a1` | Cliente de EDGAR, respaldo del mismo corte, regla B del factor ADR, D7 |
| T5 | `4f01557`, `4fca871`, `61a964c`, `4960463` | Deuda coherente con el EBITDA, bancos sin ratios de apalancamiento de empresa, Altman X4 |
| T6 | `01324a3`, `c8ae863` | Beta propia o del sector; rango de 52 semanas de la serie; protección 2 retirada |
| T7 | `f762e03`, `8f461cf`, `20fc859`, `a2bb87a`, `7b610a7`, `a435698`, `771d442` | Barrido del mapa: las 29 filas de fase 2 tienen destino (bitácora, mapa) |
| T8 | `db4db68`, `7805de9` | Arreglo de la herramienta F1; web recompilada (insignia de D7 y "(último ejercicio)") |

## 3. Golden: diff causa por causa (T6 y T7, pendientes de tu aprobación)

Cada causa se midió frente a la anterior, exportando cada commit (`git archive`) y repitiendo los 43 análisis en
replay. El punto de partida reproduce los golden aprobados de T4–T5 (`65dde21`): 0 diferencias.

| Causa | Cambios de nivel (veredicto) | Cambios dentro del nivel | Cifras que se mueven |
|---|---|---|---|
| **T6** beta y rango | **BRK-B:** precio razonable → exigente (50 → 42; beta 0.18 → 0.40). **JNJ:** razonable → exigente (45 → 39), confianza alta → media (beta del sector 0.98, antes 0.20; aceptado por ti). **NVO:** razonable → atractivo (58 → 65; beta 1.96 → 0.98). **TM:** razonable → atractivo (61 → 65; beta 0.88 → 0.72). **NFLX** (local y panel): precio 46 → 55, confianza media → alta (beta 1.61 → 0.93) | BCS precio 50 → 58; HSBC 35 → 42; XOM calidad 71 → 72 | La beta en los 43 análisis; el rango de 52 semanas, de la serie |
| **T7** crecimiento interanual | Ningún veredicto | **MU:** confianza baja → media (salen dos incidencias de un dato de Finnhub que ya no entra), precio 40 → 35. **NVO:** PEG trailing 1.89 → 1.50 (crecimiento del BPA del último ejercicio, 6.2% frente al 4.9% de Finnhub), confianza media → alta, precio 65 → 70 | El interanual de ingresos y de BPA en 40 análisis (p. ej., FCX −24.2% → +1.8%; HSBC BPA +108.7% → −3.2%); rótulo "(último ejercicio)" |
| T7 forwardPE | — | — | Solo el texto de la procedencia |
| T7 split del plan B | — | — | Solo la procedencia (CRWD, NFLX, UL) |
| T7 ordinario | — | — | ROE y P/B de BCS (10.0% → 10.5%; 0.72 → 0.87), HSBC, JPM, BAC, DUK, PG, V, PLD |
| T7 perímetro | — | — | Solo `data_provenance.perimeter` |

`pytest -q` → "84 failed, 3577 passed, 1 skipped". Los 84 son `test_regression` (42 análisis + 42 PDF): los golden de
T6–T7 sin regenerar. Con tu aprobación: `tests/diff_golden.py --regenerate --yes` en los dos juegos,
`tests/contract_forced.py --write` y la suite en verde.

## 4. Muestreo manual de 5 tickers

En `docs/fiabilidad/F2b_MUESTREO_MANUAL.md`, para el chat de revisión: AAPL, JPM, DUK, TSM y UL. Las cifras del FY0
van lado a lado con el informe anual, con el concepto y el enlace al filing.

- **AAPL:** las 11 cifras casan.
- **JPM** y **DUK:** casan, salvo lo de definición ya explicado.
- **TSM:** casa, salvo las utilidades retenidas: −7.9%, definición según la herramienta (causa sin verificar en el
  20-F).
- **UL:** el resultado operativo de Yahoo es +12.1% (fuente errónea según la herramienta; causa sin verificar en el
  20-F); el capex, +12.3% (definición, uno de los 20 de capex de la fase 3).

## 5. Tiempo del análisis

`tests/perfil_local.py --red-local HD PEP MCD LOW COST TGT`: los 6 tickers de T0, con Render simulado, sin Finnhub y
con EDGAR. Medido a las 20:35 de Nueva York, fuera de la ventana de 15:55–16:45.

| | T0 (antes de la 2b) | Parada 1 | **Hoy** |
|---|---|---|---|
| En frío, red real | 3.85–5.06 s (mediana ≈ 4.2) | 2.82–5.74 s (mediana ≈ 3.6) | **3.09–3.44 s (mediana ≈ 3.2)** |
| En caliente | — | — | 0.002–0.003 s |
| Replay, CPU, por análisis | 0.005–0.012 s | 0.007–0.033 s | 0.013–0.027 s |

EDGAR y la serie de precios van en hilos, en paralelo con los estados, sin penalización medible. Producción sigue con
el bucle bloqueado (fase 6).

## 6. Observaciones nuevas (para la fase 3; no decididas)

- **El interanual de un ADR va en la moneda de la cotización.** UL: +0.5% en USD frente a −3.8% en EUR, porque el
  tipo de cambio entra en el crecimiento. Lo mismo vale para el CAGR. Es una cuestión de método: ¿crecimiento en la
  moneda de los estados?
- **BRK-B en base anual** (movida a la fase 3): Yahoo no trae el 3T-2025 (confirmado en vivo), y completar el corte
  con EDGAR mezclaría dos definiciones de ingresos.
- **MU:** el BPA del último ejercicio crece un +984% (0.70 → 7.59). Es correcto, pero un interanual sobre una base
  deprimida dice poco; el crecimiento que puntúa sigue siendo el CAGR.

## 7. Tras el "ok, pushea"

1. Push de la rama y fusión en `main` (Render despliega `main`).
2. `/api/health`: el commit desplegado.
3. En producción, con concurrencia ≤ 3 y fuera de la ventana de 15:55–16:45 de Nueva York, los casos del prompt:
   - BCS, TSM, NVO, UL y NVDA;
   - PGR (dividendo);
   - JNJ (corte, aviso y Altman);
   - MSFT y AMZN (deuda);
   - XOM (rango);
   - un ticker sin CIK (D7).
