# Prompt del operador — Fase 2a: Verdad de datos (medir)

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`.

---

Eres el **operador de la fase 2a del plan de fiabilidad de Finanzer**. La fase 2 asegura que **los números son los de
los estados financieros reales** (propiedad F1). Se parte en dos:

- **2a (este prompt): medir.** Ampliar el panel a emisores extranjeros, comparar los datos actuales contra la fuente
  oficial (SEC EDGAR) y diseñar las reglas de precedencia de fuentes. **No se corrige ningún dato del motor.**
- **2b (otro prompt, lo escribe el planificador con tus resultados): corregir.**

## 1. Contexto (lee esto antes de tocar nada)

En este orden:

1. `docs/fiabilidad/BITACORA.md`: estado, decisiones y **todas las filas del mapa con fase 2** (incluidas las de
   BCS, la revisión externa F1 y la prioridad de JNJ).
2. `docs/PLAN_FIABILIDAD.md`: §0, §3 (panel y tolerancias), §4 fase 2 y §5 (protocolo, con el punto 11).
3. `docs/fiabilidad/F0_LINEA_BASE.md` (F1 y F5) y `docs/RECON.md` §7.18–§7.19.
4. El camino de los datos: `backend/lib/yf_adapter.py` (plan B), `finnhub_fallback.py`, `currency.py`, `ttm.py`,
   `validate.py`, `data_fetcher.py` y el bloque de ingesta de `backend/main.py`.
5. `backend/tests/README.md`, `fixture_backend.py`, `capture_fixtures.py` (`--render-sim`), `panel_run.py`.

Hechos que debes tener presentes:

- **Producción:** `8ed57a0` (fase 1 + documentación). Rollback de código: `9e78f3b`. `main` local = `origin/main`.
- Producción **se apaga sin tráfico** (Render): la primera petición tarda. Despiértala antes de medir.
- La API **no expone el commit desplegado**: `/build-stamp.json` es el hash del contrato de la web, no del código.
- La clave de Finnhub está en el Llavero (`finanzer-finnhub`).
- **Decisiones del usuario (no las reabras):**
  - **D2 = verificar y luego decidir.** EDGAR no alimenta el motor en esta fase. Produces un informe de discrepancias
    y con él el usuario decide si EDGAR pasa a ser la fuente principal de los estados.
  - **D7 = registradas en la SEC.** El universo fiable son los emisores con CIK en EDGAR (10-K de EE. UU. y 20-F de
    extranjeros con ADR). Las demás se analizarán con un aviso visible ("sin fuente oficial para verificar") y la
    confianza limitada a "baja"; no se rechazan. **En la 2a solo se diseña y se mide; se implementa en la 2b.**

## 2. Conocimiento de dominio que necesitas (verifícalo en la fuente, no lo des por cierto)

**SEC EDGAR, API XBRL (gratuita):**
- `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`: todos los hechos XBRL de un emisor.
  `https://www.sec.gov/files/company_tickers.json`: ticker → CIK (incluye los ADR que presentan 20-F).
- **Exige un `User-Agent` con nombre y correo de contacto** y como máximo **10 peticiones por segundo**. No inventes
  el contacto ni uses el correo del usuario sin preguntar: **pide al usuario el texto exacto** y guárdalo en el
  Llavero (`finanzer-sec-ua`), igual que la clave de Finnhub. Nunca en el repo ni en el chat.
- Taxonomías: `us-gaap` (10-K/10-Q) e `ifrs-full` (20-F). `dei` trae datos de portada como
  `EntityCommonStockSharesOutstanding` con su fecha.
- **Los periodos trimestrales de los 10-Q son acumulados** (el 2.º trimestre trae 3 meses **y** 6 meses): elige por
  `start`/`end`. **El 4.º trimestre no se publica**: se deriva como el año fiscal menos los 9 meses.
- **Los emisores extranjeros (20-F) no publican trimestres en XBRL** (sus semestrales van por 6-K sin XBRL). Con EDGAR
  solo tendrás sus cifras **anuales**. Esto condiciona el TTM de BCS, UL, TSM, NVO, ASML, HSBC, SHEL y TM.
- Un mismo periodo aparece en **varios filings** (reexpresiones). Para cada periodo, el valor vigente es el del filing
  más reciente (`filed`). Anota cuándo difiere del original.
- Un mismo concepto contable tiene **varias etiquetas posibles** (p. ej. ingresos: `Revenues`,
  `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet`; en bancos, otras). Hace falta una tabla
  de conceptos con alternativas ordenadas, por taxonomía.
- **El factor ADR no está en XBRL.** Sale del contrato de depósito (formulario F-6) o de la web del banco depositario
  (BNY Mellon, Citi, JPMorgan, Deutsche Bank). Hay que construir una tabla del panel con **fuente y fecha** de cada
  factor.

**Bancos europeos con AT1:** los instrumentos AT1 cuentan como patrimonio (`OtherEquityInstruments` en IFRS) y sus
cupones se pagan desde el beneficio. Para ROE/ROTE del accionista ordinario: beneficio − cupones AT1 − minoritarios,
sobre patrimonio − AT1 − minoritarios (− fondo de comercio e intangibles en el tangible). El "dividendo pagado" del
estado de flujos puede incluir los cupones AT1.

**Cambios de perímetro** (escisiones y ventas de negocios): aparecen como operaciones discontinuadas
(`IncomeLossFromDiscontinuedOperations…`, `ProfitLossFromDiscontinuedOperations` en IFRS) y como saltos de ingresos
sin causa orgánica. Caso del panel: UL (helados/Magnum; verifica la fecha y cómo reexpresan los años previos).

## 3. Tareas, en orden

### T0. Rama, commit desplegado visible y contacto SEC
- Rama `fiabilidad/f2a-medir` desde `main`.
- **Commit desplegado:** `/api/health` devuelve también el commit, leído de `RENDER_GIT_COMMIT` (Render la define
  sola) o `null` en local. Test unitario. Es el único cambio de código de producción de la 2a, y se despliega en el
  punto de parada 2 si el usuario lo aprueba.
- Pide al usuario el texto del `User-Agent` para la SEC y guárdalo en el Llavero.

### T1. Panel ampliado a emisores extranjeros
Añade al juego `panel`, con `--render-sim` y Finnhub, **después del cierre** de Nueva York y en una sola sesión:

| Ticker | Por qué | Arquetipo esperado (propuesta del planificador) |
|---|---|---|
| HSBC | Banco, reporta en USD, ADR = 5 acciones, AT1 | FINANCIAL |
| SHEL | Energía, reporta en USD, ADR = 2 acciones | CYCLICAL |
| UL | Reporta en EUR, ADR = 1, escisión reciente | MATURE |
| TM | Reporta en JPY, ADR = 10 acciones, año fiscal a marzo | CYCLICAL |

BCS ya está en el panel. **Verifica cada factor ADR** en la fuente del depositario antes de darlo por bueno: los de la
tabla son la referencia del planificador, no la verdad. Golden de los nuevos con el motor tal como está (describen el
comportamiento actual, con sus defectos). Suite, guardián e invariantes en verde, o con xfail estricto si un ticker
nuevo destapa un fallo conocido.

### T2. Diagnóstico de EDGAR → **PUNTO DE PARADA 1**
Herramienta en `backend/tests/` (no en el motor) que, para cada ticker del panel:
- resuelve el CIK (o "sin CIK" → caso D7), la taxonomía y los formularios disponibles;
- para **cada campo que consume el motor** (haz la lista desde `FinancialStatements`, `key_metrics` y las entradas de
  `ttm.py`, `normalize.py`, Piotroski, Altman y WACC), encuentra el concepto XBRL y su unidad, o "sin concepto";
- registra los periodos disponibles (anual, trimestral, acumulado), las reexpresiones y la latencia local de la
  descarga (y el tamaño del JSON).

Entrega `docs/fiabilidad/F2_EDGAR_DIAGNOSTICO.md` con: la cobertura por campo y por ticker, la **tabla de conceptos
propuesta** (campo → alternativas `us-gaap` → alternativas `ifrs-full` → signo y unidad), los huecos (qué campos no da
EDGAR para quién) y la **tabla de factores ADR** con fuente y fecha.
**Detente y preséntalo.**

### T3. Informe de discrepancias (la medida de F1)
Herramienta de verificación (en `tests/`, sin tocar el motor) que compara, para cada ticker y campo del panel, el valor
que usa hoy el pipeline (replay de los fixtures) con el de EDGAR para **el mismo periodo**:
- en la **moneda de los estados** (deshaz la conversión con los tipos de `data_provenance.currency`) y por acción en
  la **misma clase de acción**;
- con las tolerancias de PLAN §3 (±1% estados; ±2% relativo en ratios; ±2% BPA);
- clasificando cada discrepancia por causa: **unidad** (peniques, miles), **periodo** (TTM frente a anual, trimestre
  distinto), **definición** (AT1, minoritarios, operaciones discontinuadas, arrendamientos), **perímetro**, **factor
  ADR**, **fuente errónea** (Yahoo o Finnhub dan un valor que no existe en los estados), **EDGAR falta**.

Incluye explícitamente los casos conocidos y confírmalos o descártalos con datos: BCS (dividendo en peniques, factor
4.154 frente a 4, AT1), UL (perímetro y factor 1.012), JNJ (BPA de Finnhub con un trimestre nuevo frente a estados de
junio), TSM/NVO/NVDA (dividendo), JNJ sin utilidades retenidas, la beta de Finnhub en los ADR (BCS y NVO 1.64), y las
7 de 30 diferencias de Yahoo entre Render y local de la fase 0. Para la beta, compárala con una beta calculada por ti
(2 años semanales frente al S&P 500) como referencia del informe, sin llevarla al motor.

Entrega `docs/fiabilidad/F2_DISCREPANCIAS.md`: % de campos dentro de tolerancia (por campo, por ticker, por
arquetipo, EE. UU. frente a extranjeros), las discrepancias por causa con ejemplos y su **efecto en el veredicto**
(¿cambiaría el nivel de calidad o de precio con el dato de EDGAR?). Ese % es la **línea base de F1**.

### T4. Diseño de precedencia de fuentes → **PUNTO DE PARADA 2**
`docs/fiabilidad/F2_PRECEDENCIA.md`, propuesta (sin implementar) de qué fuente manda para cada campo:
- **Principio del conjunto de periodo coherente:** todos los campos que salen de los estados en un análisis
  pertenecen al mismo corte (`as_of`). Si una fuente ya tiene el trimestre nuevo y otra no, **o avanzan todos o
  ninguno**. Ninguna fuente sustituye un campo de un periodo con el valor de otro periodo (caso JNJ).
- Para cada campo: fuente principal, respaldo, regla de periodo, identidad contable con la que se verifica (como la
  del dividendo, ahora en ambos sentidos) y qué se muestra si no cuadra.
- **Dos escenarios:** con EDGAR como fuente principal de los estados (D2 = principal) y sin ella (D2 = solo
  verificación), con lo que gana y lo que cuesta cada uno según tus datos de T2 y T3 (cobertura, latencia, huecos de
  los 20-F sin trimestres).
- **D7:** cómo se marca un emisor sin CIK (aviso, tope de confianza) y dónde se muestra.
- La **beta**: ¿se calcula la propia con la serie de precios (que la fase 5 también necesita) o se sigue con Finnhub
  con una comprobación? Propón con datos de T3.

**Detente y presenta** el informe de discrepancias (T3) y el diseño (T4). El usuario decidirá D2 con ellos. Pide
también el "ok, pushea" para T0 (commit en `/api/health`) y el panel ampliado (solo tests); son seguros, pero cada
push redespliega.

### T5. Cierre de la 2a
RECON §7.20, bitácora (entrada, estado, fila de la fase 2 con "2a cerrada", mapa: cada fila de fase 2 marcada como
"medida en F2_DISCREPANCIAS" con su causa confirmada, o "no reproducida"). Detente: el prompt de la 2b lo escribe el
planificador.

## 4. Reglas que no se rompen

- **No corrijas datos del motor** en la 2a, aunque el arreglo sea evidente. Anótalo con su causa: es la 2b.
- Las herramientas de diagnóstico y verificación viven en `backend/tests/` (o `backend/tools/`), nunca en el camino del
  análisis en producción.
- Respeta los límites: SEC ≤ 10 peticiones/s con `User-Agent`; Finnhub ≤ 60/min; finanzer.app con concurrencia ≤ 3.
  Cachea en disco las descargas de EDGAR durante la sesión (en el scratchpad o en `tests/fixtures/edgar/`), para no
  repetirlas.
- Ningún secreto (clave de Finnhub, contacto de la SEC) en el repo, los fixtures ni el chat.
- **No pushees** sin un "ok, pushea" explícito. Un commit por causa, con prefijo `F2a:`.
- Si el código o los datos contradicen este prompt o la bitácora, mandan ellos: verifica, repórtalo y sigue solo si
  no cambia el alcance.
- Toda afirmación de "hecho" o "pasa" va con el comando que la demuestra y su salida.
- Al cerrar la sesión, aunque quede a medias, deja tu entrada en la bitácora.

## 5. Definición de terminado de la fase 2a

- [ ] `/api/health` con el commit desplegado (y desplegado si el usuario lo aprueba).
- [ ] Panel con HSBC, SHEL, UL y TM (+ BCS), factores ADR verificados con fuente y fecha, golden y suite en verde.
- [ ] `F2_EDGAR_DIAGNOSTICO.md` con cobertura, tabla de conceptos, huecos y factores ADR.
- [ ] `F2_DISCREPANCIAS.md` con el % dentro de tolerancia (línea base de F1), las causas y su efecto en el veredicto.
- [ ] `F2_PRECEDENCIA.md` con los dos escenarios de D2, el diseño de D7 y la propuesta de beta.
- [ ] RECON §7.20 y bitácora al día; decisión del usuario sobre D2 citada literalmente.
