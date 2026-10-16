# F2b · Punto de parada 1 (T1–T3)

> Fase 2b del plan de fiabilidad (corregir). Rama `fiabilidad/f2b-corregir` (worktree `../finanzer_next-f2b`), desde
> `main` = `60f8a69`. Nada pusheado. Medidas del 2026-10-16 (Nueva York 10:35–11:45). Evidencia completa (diff de
> golden íntegro, resumen de `edgar_verify`, panel y perfil) en la carpeta de notas compartida de la sesión,
> `F2b_parada1/`.

## 0. Resumen

| | Antes (T0) | Ahora | Comando |
|---|---|---|---|
| F1 (`edgar_verify.py`, mismas tolerancias y clasificación) | **90.0%** (1,262/1,403) | **90.9%** (1,264/1,391) | `../.venv313/bin/python tests/edgar_verify.py --whatif --out <dir>` |
| Filas "factor ADR" / "unidad + factor ADR" | 4 / 4 | 0 / 2 | ídem |
| Cambios de nivel en el panel (replay, 36) | — | **2**: AMZN precio razonable → exigente; ASML confianza media → baja | `tests/panel_run.py --mode replay --compare <base>` |
| Suite | 3,478 passed, 4 skipped | 3,439 passed, 1 skipped; **82 fallos, todos de golden** (41 análisis + 41 PDF) | `../.venv313/bin/python -m pytest tests -q` |
| Guardián | 0 fallos | 0 fallos (identidad del dividendo nueva) | incluido en la suite |
| Análisis en frío, red local (A/B intercalado, 6 tickers) | mediana ≈ 4.2 s sin los hilos nuevos | mediana ≈ 3.6 s con ellos | `tests/perfil_local.py` y la medida A/B (§5) |

**Lo que pido para seguir:** (1) la regla del factor para emisores fuera de la tabla (§1.2); (2) la fuente del
dividendo (§2.1, recomiendo la (b)); (3) la aprobación de los golden, causa por causa (§4); (4) la variable
`SEC_EDGAR_USER_AGENT` en Render (la pones tú; el valor es el del Llavero `finanzer-sec-ua`).

Commits (prefijo `F2b:`, uno por causa):

| Commit | Causa | Tipo |
|---|---|---|
| `b25aed6` | Factor ADR oficial del depositario (T1) | de fondo |
| `c9b661d` | Dividendo en la moneda y la clase del precio; **retira la protección 1** (T2) | de fondo |
| `0c8d211` | Corte coherente; Finnhub solo entra si casa con el corte (T3) | de fondo |
| `c0b0414` | Aviso de resultados publicados y aún no incorporados, con SEC EDGAR (T3) | de fondo |
| `4c102ee` | Base temporal declarada en el Piotroski (T3) | de fondo |
| `e6364b2` | BPA TTM = suma de los BPA diluidos de los 4 trimestres del corte (T3) | de fondo |
| `5570d8b` | Procedencia del dividend yield (corrección de T2) | de fondo |
| `d984181` | Ratios TTM de Finnhub solo si casan con el corte (T3) | de fondo |
| `0fd5bd3` | Caché de EDGAR solo con los formularios que se usan (T3) | de fondo |

Ninguna protección provisional nueva. La protección 1 (dividend yield "sin dato" por la identidad) está retirada; la
2 (rango de 52 semanas ampliado) se retira en T6.

## 1. T1 · Factor ADR oficial

### 1.1 Hecho

- `config/adr.toml`: ticker → factor, clase, depositario, fuente (20-F y F-6) y fecha de verificación, con los del
  panel (F2_EDGAR_DIAGNOSTICO §5): TSM 5, ASML 1, NVO 1, BCS 4, HSBC 5, SHEL 2, UL 1, TM 10, BRK-B 1/1500.
- `currency.prepare_class` usa el oficial. El implícito pasa a comprobación: más de un 2% de diferencia → nota
  "recompras/emisiones desde el cierre" con la cifra, sin tocar el factor. BCS 4.154 → 4 (−3.7% de acciones desde
  el 31-dic); TM 11.07 → 10.
- Texto visible (portada y cabecera): "cada título cotizado equivale a 4 acciones ordinarias de 25 peniques (factor
  del depositario, JPMorgan). Desde el balance del 2025-12-31 la empresa tiene un 3.7% menos de acciones
  (recompras)".

**TM, corrección a la 2a.** El 9.6% de TM **no es un error de Yahoo** (la 2a lo clasificó "fuente errónea"). El 6-K
del 2026-08-04 da, a 2026-06-30, 14,594,987,460 acciones emitidas y 2,753,153,800 en autocartera (11,842 millones en
circulación, tras amortizar 1,200 millones recompradas a Toyota Industries), y el de 2026-10-05, 63.8 millones más
recompradas en agosto–septiembre: 11,778 millones, lo que da Yahoo (1,177.8 millones de ADR × 10). El factor 11.07
salía del balance a 2026-03-31. Es el mismo desfase de fechas que BCS, y el factor oficial lo resuelve; la
capitalización de Yahoo es correcta. La fila de `edgar_verify` sigue "fuera" (compara con la portada del 20-F a
marzo) y su causa real es "periodo"; no reclasifico la herramienta (regla de la fase).

### 1.2 Emisores fuera de la tabla · **decisión que te pido**

| Opción | Qué hace | A favor | En contra |
|---|---|---|---|
| **A (la del prompt, implementada como propuesta)** | Implícito ajustado a la fracción simple más cercana (n o 1/n, n ≤ 100) si está a ≤ 2%, declarado "factor deducido de las acciones, sin verificar con el depositario"; si no, el implícito tal cual con aviso | Sin red ni tabla | **Falla en el caso TM:** con una recompra grande, 11.07 se ajustaría a 11 (el oficial es 10), y a menos del 2% no hay aviso |
| **B (recomendada, para T4)** | El factor de la portada del 20-F leído de EDGAR (`dei:Security12bTitle`, "each representing N shares"; página R1 del filing, ≈ 20 KB, una vez por CIK y en caché); A solo si EDGAR no lo da | Es la fuente oficial, para cualquier ADR registrado en la SEC | Una petición más la primera vez (dentro del presupuesto de 3 s); un emisor sin CIK (D7) sigue con A |

Con B, la tabla de `config/adr.toml` queda como caché verificada a mano del panel. Lo que elijas lo implemento en
T4 (la lectura de EDGAR vive allí).

## 2. T2 · Dividendo corregido en origen (protección 1 retirada)

### 2.1 Fuente · **decisión que te pido** (recomiendo la b)

USD por título cotizado al año (panel, fixtures del 14 y 15-oct). (a) = Finnhub de la línea local × factor oficial
× tipo de cambio de contado; (b) = pagos del propio ADR en la serie de precios (suma del último ciclo de pagos
ordinarios).

| Ticker | Finnhub (línea local) | (a) | (b) | EDGAR, pagado por ADR (USD) | Yield con (b) |
|---|---|---|---|---|---|
| BCS | 11.5 GBp | 0.61 | 0.62 | 0.45 (TTM a jun.) | 2.71% |
| TSM | 26 TWD | 4.04 | 3.85 | sin dato del periodo | 0.90% |
| NVO | 11.7 DKK | 1.75 | 1.85 | sin dato del periodo | 4.86% |
| UL | 164.99 GBp | 2.19 | 2.22 | 2.26 (FY 2025) | 3.44% |
| HSBC | 55.67 GBp | 3.69 | 3.75 | 3.75 (TTM a jun.) | 3.97% |
| SHEL | 112.82 GBp | 2.99 | 3.02 | 2.84 (TTM a jun.) | 2.92% |
| TM | 100 JPY | 6.33 | — (Yahoo trae un solo pago en 2 años) | sin dato del periodo | 3.30% con (a) |
| ASML | 7.78 EUR | 8.68 | 9.06 | sin dato del periodo | 0.55% |

- (a) y (b) coinciden a ±5% donde existen las dos.
- **(a) necesita saber la moneda de la línea local, que Finnhub no declara:** HSBC y SHEL presentan en USD y su línea
  de Finnhub está en peniques; UL presenta en EUR y su línea, en peniques. Haría falta una tabla a mano de líneas.
- **(b) ya está en la unidad del precio** (USD por ADR, neto del depositario, al tipo de cambio de cada pago) y sale
  de la misma descarga que T6 necesita para el rango y la beta (0.6–0.9 s en paralelo con los estados).
- **Recomendación: (b)** para las líneas extranjeras y, si los pagos faltan (TM), (a) solo si cuadra con lo pagado en
  los estados; para las domésticas, el declarado de la fuente (último declarado × frecuencia) verificado con último
  pago × frecuencia (±25%: admite una subida declarada y aún no pagada, MSFT 3.92 frente a 3.64).

### 2.2 Identidad con magnitudes equivalentes, en los dos sentidos

- **Subida verificada:** NVDA 1.00 = 0.25 × 4, nota "dividendo aumentado el 2026-06-04 (de 0.01 a 0.25 USD por
  pago)". Yield 0.45% (antes "sin dato").
- **Extraordinario separado:** PGR 0.40, nota "excluye el extraordinario de 13.60 USD pagado el 2026-01-02".
- **Recorte:** se dice ("dividendo recortado el …"); ningún caso en el panel.
- **Lo pagado en los estados frente a lo cobrado** (misma ventana, misma unidad): aviso si sale de [0.5, 2] (ningún
  caso en el panel tras el corte).
- "Sin dato" queda solo si la empresa paga y ninguna fuente cuadra (regla `dividendo_sin_fuente`); no pagadores = 0%.
- Guardián: `identidad_dividendo` compara ahora el indicado con lo cobrado en 12 meses en la misma unidad, exige yield
  = indicado / precio y mantiene el control de payout × E/P salvo subida verificada (umbral sin cambiar: 2.0).

Casos: BCS 2.71% (antes "sin dato"), TSM 0.90%, NVO 4.86%, UL 3.44% (habría sido 251.70%), HSBC 3.97%, SHEL 2.92%,
TM 3.30%, NVDA 0.45%, PGR 0.19%; además **ASML 0.47% → 0.55%** (Finnhub daba EUR leídos como USD: otro caso del
mismo defecto, sin protección hasta hoy).

## 3. T3 · Corte coherente y aviso

- **Corte** (`ttm.find_cut`, F2_PRECEDENCIA §1): el último trimestre con ingresos y beneficio de 4 trimestres
  consecutivos que acaban en él, balance a esa fecha y (si el emisor presenta flujos trimestrales) flujo de
  operaciones de esos trimestres. Antes cada campo tomaba sus 4 trimestres por su cuenta: AMZN y BAC sumaban
  resultados a junio con balance a marzo; ASML, flujos a marzo con resultados a junio. Ahora AMZN, BAC y ASML van
  enteros a marzo; BRK-B y UL, al ejercicio (sin trimestres completos).
- **`periodo_incoherente`** (validate): lo que no es del corte se descarta y lo dice. 8 análisis: ASML (gastos
  financieros, dividendos pagados, beneficios retenidos), BCS y HSBC (flujos y dividendos pagados: Yahoo no da sus
  flujos trimestrales), DUK (dividendos pagados), NVO (gastos financieros), SHEL (deuda a largo plazo). T4 (EDGAR,
  respaldo del mismo corte) recupera lo que EDGAR tenga (los semestrales de BCS, HSBC y SHEL; los 10-Q de DUK).
- **Finnhub invertido:** su BPA TTM solo entra si casa con el del corte (±2%, la misma tolerancia de antes); sus
  ratios TTM (payout, cobertura, rotación, liquidez) tampoco entran sin dato del corte con que casarlas. Un valor
  rechazado se anota y no cuenta como incidencia de la fuente. JNJ, MU (FY de septiembre), BAC (sin periodo
  identificable), AMZN, V, RIVN.
- **BPA TTM** = suma de los BPA diluidos de los 4 trimestres del corte (antes, beneficio / acciones del último
  trimestre). En `edgar_verify`, BAC, DOW, JPM, MU, PLD y TM pasan a "dentro"; BCS baja de +19.8% a +3.2% (AT1).
- **Aviso** «La empresa publicó resultados el <fecha>; este análisis aún no los incorpora»: PDF (portada, bloque de
  avisos junto a la fecha de los estados), web (`StockHeader`) y API (`data_provenance.pending_results`). Por EDGAR
  (10-Q/10-K/20-F/6-K con XBRL posterior al corte, u 8-K 2.02 posterior al filing del corte) y, sin 8-K, por el
  calendario de Finnhub ("según el calendario de resultados"). Panel: JNJ y JPM (8-K del 13-oct), BAC y PGR (14-oct),
  MU (10-K del 9-oct), AMZN (10-Q de julio), UL (6-K semestral), BRK-B, FCX, ASML. No baja la confianza.
- **Base temporal:** cada criterio del Piotroski lleva su ejercicio ("FY2025: El flujo operativo no llega al
  beneficio neto", AAPL); la fecha de los estados va en la portada ("Estados financieros a 30 de junio de 2026
  (últimos doce meses)").
- **Cliente de EDGAR** (`lib/sec_edgar.py`): User-Agent solo por `SEC_EDGAR_USER_AGENT`; sin ella se desactiva y lo
  dice. ≤ 8.3 peticiones/s, presupuesto 3 s, cachés por proceso, en un hilo: nunca bloquea. Medido en vivo: 0.35–0.9 s
  (JPM, con 26,392 filings, 0.90 s).

## 4. Golden · diff causa por causa · **aprobación que te pido**

Diff íntegro: `F2b_parada1/golden_panel.txt` (4,480 líneas) y `golden_local.txt` (418) en la carpeta de notas.

| Causa (commit) | Qué cambia en los golden | Análisis | Efecto en el veredicto |
|---|---|---|---|
| Factor oficial (`b25aed6`) | `data_provenance.currency.share_class` (base, implícito, fuente); nota de moneda de los ADR | 41 (solo procedencia en los domésticos) | Ninguno: las series de acciones cambian de nivel, no de ritmo |
| Dividendo (`c9b661d`, `5570d8b`) | `dividend_yield`, `shareholder_yield`, `data_provenance.dividend` y `.price_history`; fila del dividendo; campos de Finnhub en la confianza (−1 a −4) | 41 (valor en 11) | Ninguno |
| Corte coherente (`0c8d211`, `d984181`) | `data_provenance.as_of`, `.ttm.cut`, avisos; AMZN, BAC y ASML a marzo; 8 con campos descartados; ratios de Finnhub sin casar | 41 | **AMZN** precio razonable → exigente (P/E 20.4x con el BPA de Finnhub a junio → 30.4x con el del corte a marzo, 8.36 = EDGAR); **ASML** confianza media → baja (3 campos del ejercicio descartados); AAPL calidad 79 → 75 (la cobertura de 622x de Finnhub ya no entra: AAPL no publica gastos financieros desde 2023); NVO 90 → 88; BCS 75 → 72 |
| BPA trimestral (`e6364b2`) | `pe`, `eps_ttm`, P/E en el score y en el DCF | 41 | Ninguno; P/E −1% a +1% en la mayoría; PLD +23%, TM +21%, BCS +16%, BAC +12% (los que ahora cuadran con EDGAR) |
| Aviso de resultados (`c0b0414`) | `pending_results`, `.edgar`, aviso en portada y cabecera | 41 (aviso en 11) | Ninguno |
| Base temporal (`4c102ee`) | "FY2025: " en los criterios del Piotroski | los que tienen Piotroski | Ninguno |

**AMZN, lo que hay detrás.** Yahoo trae los resultados de junio pero no el balance ni los flujos: el corte coherente
es marzo, y a marzo el BPA TTM es 8.36 (cuadra con EDGAR). El golden usaba el BPA de Finnhub a junio (12.43) con
estados a marzo. En T4, el respaldo de EDGAR del mismo corte (balance y flujos del 10-Q de junio) puede hacer avanzar
el corte entero a junio; entonces se vuelve a medir.

## 5. Tiempo del análisis

- **Replay (CPU, sin red):** análisis 0.007–0.033 s por ticker (T0: 0.005–0.012 s); el PDF igual (≈ 0.05 s).
- **Red real desde este Mac** (Render simulado, sin Finnhub, con EDGAR): medida A/B intercalada en 6 tickers fuera
  del panel (HD, PEP, MCD, LOW, COST, TGT). Sin los hilos nuevos: 3.85–5.06 s (mediana ≈ 4.2 s). Con ellos: 2.82–5.74 s
  (mediana ≈ 3.6 s). EDGAR 0.50–0.72 s y la serie 0.58–0.87 s, en paralelo con los estados: **sin penalización
  medible**. Una primera corrida dio 15–41 s: era la red de Yahoo (búsqueda 8 s, estados 14–16 s, peticiones que ya
  existían), no el código.
- Producción sigue con el bucle bloqueado (F6): los hilos nuevos no lo empeoran, pero tampoco lo arreglan (fase 6).

## 6. Pendiente para después del punto 1 (no hecho)

- T4: respaldo de EDGAR del mismo corte (JNJ utilidades retenidas, BCS y BRK-B D&A, los campos descartados en §3),
  D7 y, si lo apruebas, el factor del 20-F (§1.2 B).
- T5 (deuda coherente con el EBITDA), T6 (beta propia y rango de 52 semanas; retira la protección 2), T7 (barrido del
  mapa), T8 (medida final y despliegue), T9 (cierre).
- La fixture de la serie y la de EDGAR son juegos aparte (`tests/fixtures/history`, `tests/fixtures/f2b`), cortados en
  la fecha de captura de cada ticker; las capturas futuras del panel las llevarán dentro.
