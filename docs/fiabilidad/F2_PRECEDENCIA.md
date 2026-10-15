# F2a · T4 — Precedencia de fuentes (propuesta, sin implementar)

> Fase 2a del plan de fiabilidad. **Es un diseño:** no hay código en el motor. Los datos que lo respaldan están en
> [F2_EDGAR_DIAGNOSTICO.md](F2_EDGAR_DIAGNOSTICO.md) (T2) y [F2_DISCREPANCIAS.md](F2_DISCREPANCIAS.md) (T3).
> D2 sigue abierta: este documento da los dos escenarios para que el usuario decida. D7 ya está decidida (emisores
> registrados en la SEC); aquí está su diseño.

## 1. Principio del conjunto de periodo coherente

**Regla.** Todos los campos que salen de los estados en un análisis pertenecen al mismo corte (`as_of`): la fecha de
cierre del último periodo con estados completos (trimestre, semestre o ejercicio, según el emisor).

- Si una fuente ya tiene un periodo más nuevo y las demás no, **avanzan todas o ninguna**.
- Ninguna fuente sustituye un campo de un periodo con el valor de otro periodo.
- Lo que no es de los estados (precio, capitalización, beta, dividendo indicado) lleva su propia fecha y se declara
  como tal.

**Por qué hace falta: casos medidos en T3.**

| Caso | Qué pasa hoy | Medida |
|---|---|---|
| JNJ (BPA) | Finnhub ya incluye el 3T-2026, del 8-K del 13-oct. Los estados de Yahoo y de EDGAR llegan a junio | Finnhub en vivo (15-oct): BPA TTM **6.5886** = TTM de junio en EDGAR (8.62) − 3T-2025 (2.12) + 3T-2026 (0.09). El motor sustituye el BPA si difiere más de un 2%, así que mezcla el P/E de septiembre con estados de junio. El 3T solo existe en un 8-K, sin datos estructurados: el corte no puede avanzar (§1.1) |
| MU (BPA) | Finnhub 74.21 frente a 44.24 de EDGAR al 2026-05-28 | 74.21 es el BPA del FY que termina el 2026-09-03, un periodo posterior al de los estados del pipeline |
| BAC (BPA) | Finnhub 4.509 | No coincide con ningún TTM de EDGAR (junio: 4.33 diluido, 4.40 básico; con el 3T del 8-K del 14-oct: 4.18, o 4.35 ajustado). Es una fuente sin periodo identificable |
| DUK (balance) | En la fase 0, Render recibió de Yahoo el balance al 31-mar y local el del 30-jun | Los dos existen en EDGAR (caja 2,140 y 673 millones de USD): no es un dato falso, es un **corte distinto** |
| BCS (acciones) | Acciones de los estados a 2025-12-31 frente a acciones de la cotización de hoy | Factor implícito 4.154 frente a 4 oficial: el desfase son 3.9 puntos de recompras |

**Cómo se implementaría (2b):**

1. **Dónde vive:** `data_provenance.as_of`, con el periodo de cada campo de los estados (`period_end`, `period_type`).
   Ya hay una parte en `data_provenance.ttm` (los trimestres usados).
2. **Comprobación:** una nueva regla en `validate.py`, `periodo_incoherente`. Si un campo de los estados trae otro
   `period_end`, se descarta y queda el del corte. Se registra en `data_validation` con el aviso visible
   "dato de otro periodo descartado".
3. **Finnhub:** sus métricas TTM (`epsTTM` y compañía) solo entran si se puede demostrar que son del mismo corte.
   Es decir, si casan con lo que da el corte a ±2%. Si no casan, no entran: es la regla de hoy, pero al revés.
4. **Avance del corte:** cuando Yahoo o EDGAR publican el trimestre nuevo, el corte avanza con **todos** los campos.
   En el escenario EDGAR principal, el corte lo marca el último 10-Q/6-K con XBRL.
5. **Un 8-K no avanza el corte.** El comunicado de resultados (8-K, apartado 2.02) no trae datos estructurados, así
   que ningún campo se adelanta al corte vigente por él, venga de la fuente que venga (§1.1).

### 1.1 Resultados publicados y aún no incorporados

Entre el comunicado de resultados (8-K) y el 10-Q pasan de 2 a 6 semanas. En ese hueco, el análisis usa el corte
anterior, y lo dice.

- **Aviso visible:** **"La empresa publicó resultados el <fecha>; este análisis aún no los incorpora."**
  - **PDF:** en la portada, bloque de avisos, junto a la fecha de los datos.
  - **Web:** en `StockHeader`, como nota bajo la fecha.
  - **API:** `data_provenance.pending_results = {"date": "2026-10-13", "form": "8-K", "items": "2.02", "accn": ...,
    "as_of": "2026-06-28"}`.
- **Detección, por orden:**
  1. **EDGAR `submissions`** (la misma descarga que ya hace D7, en caché diaria): hay un 8-K con el apartado `2.02`
     (*Results of Operations*), o un 10-Q/10-K/20-F/6-K, presentado **después** del corte y con `reportDate`
     posterior al `as_of`. Es la fuente principal: oficial, y con la fecha exacta.
     - Medido hoy: JNJ, 8-K del 2026-10-13 con apartados "2.02,9.01"; BAC, 8-K del 2026-10-14; JPM, 8-K del
       2026-10-13. En los tres el corte es junio.
  2. **Fecha de resultados del proveedor** (calendario de Finnhub o `earningsDate` de Yahoo) para los emisores sin
     8-K: los 20-F publican sus resultados por 6-K, sin apartado 2.02. El aviso dice entonces "según el calendario
     de resultados".
- **Qué no hace:**
  - no mezcla periodos;
  - no baja la confianza: el dato del corte es correcto, solo que no es el último;
  - deja de mostrarse cuando el corte avanza.

## 2. Precedencia por campo

Hay dos escenarios. "Principal" es la fuente que se usa; "respaldo", la que entra si la principal no tiene el dato
**del mismo corte**. "Identidad" es la comprobación contable que se hace siempre, con la acción si no cuadra.

### 2.1 Campos de los estados

| Campo | Escenario A: EDGAR principal | Escenario B: EDGAR solo verificación | Regla de periodo | Identidad | Si no cuadra |
|---|---|---|---|---|---|
| Ingresos | EDGAR (`revenue`, tabla T2) → Yahoo | Yahoo → EDGAR | TTM del corte; 20-F sin interinos: FY | Ingresos ≥ beneficio bruto ≥ 0 | Aviso; en bancos, "ingresos totales" no tiene etiqueta estándar: Yahoo con nota de definición (BCS, HSBC) |
| Beneficio bruto | EDGAR → Yahoo | Yahoo | TTM | Bruto ≤ ingresos | Sin dato si falta (17 emisores no lo presentan: no aplica) |
| Beneficio operativo | **EDGAR `OperatingIncomeLoss`** → Yahoo marcado "estimado" | Yahoo, marcado "estimado" si EDGAR difiere > 2% | TTM | EBIT ≤ beneficio bruto | Yahoo **construye** su "Operating Income": 21 de 67 comparaciones fuera, 16 sin ningún valor equivalente en los estados (KO, PLD, AMT, NEE, DUK, FCX, CRWD, UL). Mostrar el de EDGAR, o el de Yahoo con la etiqueta "estimado por la fuente" |
| Beneficio neto | EDGAR (atribuido al accionista ordinario) → Yahoo | Yahoo → EDGAR | TTM | BPA × acciones medias = beneficio del ordinario (±2%) | Si no cuadra por AT1/preferentes (BCS: 7,172 frente a 6,175 millones de GBP), el ROE y el BPA usan el del ordinario |
| D&A | EDGAR → Yahoo | Yahoo | TTM | — | NFLX y MSFT: Yahoo suma amortizaciones con etiqueta propia (NFLX: contenidos). En A, la D&A de EDGAR cambia el EBITDA de NFLX y su nivel de precio (§3) |
| Gastos financieros | EDGAR → Yahoo | Yahoo | TTM | Cobertura = EBIT / intereses | NEE y CAT sin etiqueta estándar: Yahoo |
| Flujo de operaciones | EDGAR → Yahoo | Yahoo | TTM (los 10-Q traen el acumulado del año) | FCF = OCF − capex | 100% dentro de tolerancia en T3: las dos fuentes valen |
| Capex | EDGAR (PP&E) → Yahoo | Yahoo | TTM | — | **Definición:** Yahoo suma activos en arrendamiento (CAT), software (CRWD, SNOW) e intangibles (NVO, ASML). Decidir qué capex quiere el motor (propuesta: PP&E + software capitalizado; sin intangibles adquiridos) |
| Dividendos pagados | EDGAR (al ordinario) → Yahoo | Yahoo | TTM | DPA × acciones ≈ dividendos pagados (±10%) | BCS: Yahoo incluye los cupones AT1 (1,254 + 997 = 2,251 millones de GBP). El payout usa el del ordinario |
| Activo, pasivo, patrimonio | EDGAR → Yahoo | Yahoo | Balance a la fecha del corte | Activo = pasivo + patrimonio (+ minoritarios) ±1% | 100% dentro de tolerancia en T3 |
| Caja | EDGAR (caja + inversiones a corto plazo) → Yahoo | Yahoo | Balance del corte | Caja ≤ activo | Definición distinta en bancos (BCS: caja en bancos centrales) y aseguradoras (PGR) |
| Deuda total | EDGAR (largo plazo + parte corriente + papel comercial) **+ los arrendamientos que manda la regla de §2.3** | Yahoo, con los arrendamientos rehechos con la regla de §2.3 | Balance del corte | Deuda coherente con el EBITDA (§2.3) | Yahoo suma arrendamientos operativos de US GAAP en 10 de las 15 discrepancias y la deuda subordinada de un banco en 2 (BCS, HSBC); en UL ya suma los arrendamientos IFRS, como pide la regla |
| Utilidades retenidas | EDGAR → Yahoo | Yahoo → **EDGAR si Yahoo no la da** | Balance del corte | — | JNJ: Yahoo sin dato y EDGAR 169 mil millones. Con B + respaldo, el Altman de JNJ vuelve |
| Acciones (para el BPA) | EDGAR: acciones medias diluidas del periodo | Yahoo | Mismo periodo que el beneficio | BPA × acciones = beneficio (±2%) | — |
| Acciones (capitalización) | Cotización: acciones de hoy de la clase que cotiza | Igual | Fecha del precio | Acciones de los estados × factor oficial ≈ acciones de la cotización (±2%) | Factor ADR **oficial** de una tabla con fuente y fecha (T2 §5), nunca el implícito; el desfase se muestra como "recompras desde el cierre" |

### 2.2 Por acción y mercado

| Campo | Principal | Respaldo | Regla | Identidad | Si no cuadra |
|---|---|---|---|---|---|
| BPA (TTM) | Derivado del corte: beneficio del ordinario / acciones medias diluidas | EDGAR (`EarningsPerShareDiluted`, mismo corte) | Mismo corte que los estados; **Finnhub no sustituye** | BPA × acciones ≈ beneficio del ordinario | Aviso de periodo si Finnhub difiere; nunca se cambia de periodo |
| Dividendo por acción | **Anual indicado** (último declarado × frecuencia) en la moneda y la clase del precio | Pagado TTM de EDGAR | Indicado: fecha de la última declaración | **Identidad del dividendo en los dos sentidos** (ver abajo) | Sin dato y aviso |
| Precio, capitalización, 52 semanas | Cotización (Yahoo) | Finnhub | Fecha de la cotización | Capitalización = precio × acciones de la clase | — |
| Beta | **Propia**: 2 años semanal frente al S&P 500 (§5) | Finnhub, como comprobación | Fecha del precio | \|propia − Finnhub\| ≤ 0.5 | Aviso de beta discrepante |

**Identidad del dividendo: magnitudes equivalentes, en los dos sentidos.**

**El fallo de hoy.** El control de la fase 1 compara el yield **indicado** (Finnhub: el último dividendo declarado
anualizado) con lo **pagado en los últimos 12 meses** sobre la capitalización. Son dos ventanas distintas. Cuando hay
una subida, el pagado va por detrás y el control anula un dato bueno.

- **NVDA:** subió el trimestral de 0.01 a **0.25** en el 2T de su año fiscal 2027 (10-Q del 2026-07-26). Finnhub da
  1.00 = 0.25 × 4, que es correcto.
- El control lo compara con el pagado TTM (0.13% de yield frente a 0.45%), lo da por más de 2 veces lo pagado y lo
  deja en **"sin dato"**.
- **Está en producción.** En el mapa: corrección de la 2b.

**Diseño:**

1. **Comparar lo mismo con lo mismo.**
   - Dividendo **declarado** por acción de EDGAR (`CommonStockDividendsPerShareDeclared`, o en IFRS
     `DividendsRecognisedAsDistributionsToOwnersPerShare` / `DividendsPaidOrdinarySharesPerShare`) frente al
     **pagado** por acción (dividendos pagados / acciones medias), **en la misma ventana** (el mismo TTM o el mismo
     FY).
   - Así se valida la fuente del dato, y no la diferencia entre indicado y pagado.
2. **Unidad y clase** (el defecto de Finnhub). El indicado se compara con el declarado de EDGAR **del último
   periodo**, anualizado, en la moneda y la clase del precio.
   - Una razón cercana a 100, a 100/factor o a 1/tipo de cambio delata la moneda local por acción ordinaria: BCS
     18.6×, TSM 6.2×, NVO 6.4×.
   - **Corrección, no rechazo:** DPA local × factor oficial × tipo de cambio.
3. **Una subida verificada no se anula.** Si último declarado × frecuencia = indicado (±2%) y el último declarado es
   mayor que el anterior, el indicado se acepta, con la nota "dividendo aumentado el <fecha>".
   - NVDA pasa: 0.25 × 4 = 1.00, y 0.25 > 0.01.
   - El control hacia arriba solo actúa cuando ningún dividendo declarado explica el indicado.
4. **Hacia abajo.** Si el indicado es menos de la mitad del pagado de la misma ventana, se mira si el pagado lleva un
   extraordinario.
   - PGR: 13.50 especial frente a 0.40 ordinario. Se muestra el ordinario con la nota "excluye el extraordinario de
     X".
   - Si no lo lleva, es un **recorte** y se dice.

### 2.3 Deuda coherente con el EBITDA

**Regla.** Un arrendamiento entra en la deuda **si y solo si su coste no está restado del EBITDA**.

| Norma y tipo | Coste en la cuenta de resultados | ¿En el EBITDA? | ¿Pasivo en la deuda? |
|---|---|---|---|
| IFRS 16 (todos los arrendamientos) | Amortización del derecho de uso + intereses | No (está por debajo del EBITDA) | **Sí** |
| US GAAP, arrendamiento financiero | Amortización + intereses | No | **Sí** |
| US GAAP, arrendamiento operativo | Gasto de alquiler lineal, dentro de los gastos operativos | Sí (ya restado) | **No** |

**Dónde se aplica:**

- **Deuda neta** (deuda de la regla − caja) y **deuda neta / EBITDA**.
- **EV** = capitalización + deuda de la regla − caja (+ minoritarios), coherente con el EV/EBITDA.
- **Altman:** X3 (EBIT / activo) y X4 (patrimonio / pasivo) con el mismo criterio.
  - En US GAAP, el pasivo por arrendamiento operativo (en balance desde ASC 842) sale del pasivo de X4, porque su
    alquiler ya está dentro del EBIT de X3.
  - En IFRS 16 el pasivo se queda.
- **FINANCIAL:** la deuda subordinada (y los depósitos o los instrumentos emitidos por la actividad bancaria) **no
  entra en ninguna ratio de apalancamiento de empresa**: ni D/E, ni deuda neta, ni EV. El apalancamiento de un
  banco se mide con capital (fase 3).

**Cuántas discrepancias explica** (T3, deuda total al último balance; 35 tickers, 25 con dato del mismo corte en EDGAR):

| Grupo | Tickers | Lectura con la regla |
|---|---|---|
| Yahoo suma **arrendamientos operativos** de US GAAP, que la regla excluye | **10:** MSFT, PG, AMT, FCX, MU, DOW, NVDA, CRWD, RIVN, AMZN | La diferencia es el pasivo por arrendamiento operativo (en MSFT y NVDA, su parte no corriente). Con la regla, la deuda correcta es la de EDGAR sin ellos |
| **Deuda subordinada** en un banco | **2:** BCS, HSBC | BCS: 126,837 + 11,098 de subordinada = 137,935 millones de GBP de Yahoo. HSBC: 132,899 de Yahoo frente a 105,027 de títulos de deuda. Con la regla de FINANCIAL, fuera de las ratios |
| **IFRS 16: arrendamientos en la deuda**, como pide la regla | **1:** UL | Yahoo 27,600 millones de EUR = préstamos 26,038 + arrendamientos 1,326 (dentro de ±1%). Es la deuda de la regla; EDGAR solo difiere porque los préstamos etiquetados no llevan los arrendamientos. En SHEL los préstamos etiquetados ya los llevan (probable: el largo plazo de Yahoo, 42,190, es 66,515 menos ≈ 24,300 de arrendamientos no corrientes) y la deuda total de Yahoo cuadra exacta (73,080) |
| Sin explicar con datos de la misma fecha | **2:** O (+6.2%), DUK (+1.1%) | Ningún arrendamiento ni etiqueta de EDGAR al 30-jun da el valor de Yahoo. Hipótesis anotadas para la 2b (abajo) |
| Total | **13 de 15** explicadas por la regla | XOM ya no es una discrepancia: era un fallo de la herramienta (no sumaba `DebtCurrent`), corregido |

**La regla también cambia la deuda donde Yahoo y EDGAR coinciden pero falta el arrendamiento financiero:**

| Ticker | Arrendamiento financiero | Efecto |
|---|---|---|
| **MSFT** | **66.6 mil millones de USD** | La deuda pasa de 56.8 (Yahoo) a 106.9; el D/E de 0.13 a 0.24 |
| AMZN | 13.3 mil millones | La deuda pasa de 209.9 (Yahoo, con 91.6 de arrendamientos operativos) a 136.1; la deuda neta / EBITDA, de 0.44 a −0.05 |
| O | 0.11 mil millones | Menor |
| RIVN | 0.10 mil millones | Menor |
| AMT | 0.01 mil millones | Menor |

**Verificación: solo pasivos ya en balance, sin arrendamientos firmados y aún no iniciados.** La herramienta lee
`FinanceLeaseLiability` o `FinanceLeaseLiabilityCurrent` + `FinanceLeaseLiabilityNoncurrent`: son conceptos de
balance. Se comprobó en los tickers donde el arrendamiento financiero pesa más del 20% de la deuda de la regla (MSFT
62%, MU 47%) y en AMZN:

| Ticker | Valor usado | Comprobación | Arrendamientos no iniciados (excluidos) |
|---|---|---|---|
| MSFT | 66,594 millones de USD (10-K, 2026-06-30) | = pagos futuros 89,686 − intereses implícitos 23,092 (tabla de vencimientos, solo arrendamientos iniciados) | **329.1 mil millones**, "primarily for datacenters", solo en el texto de la nota; en XBRL solo se etiqueta su plazo (`LesseeFinanceLeaseLeaseNotYetCommencedTermOfContract1`), sin importe |
| AMZN | 13,325 millones (10-Q, 2026-03-31) | = corriente + no corriente = pagos − intereses | 137,214 millones en la tabla de compromisos ("Leases not yet commenced"), aparte de los pasivos por arrendamiento financiero (16,660 con intereses) |
| MU | 2,670 millones (10-Q, 2026-05-28) | = corriente + no corriente; ya dentro de `LongTermDebtAndCapitalLeaseObligations` | Van en las obligaciones de compra (nota 10 del 10-K de 2026-10-09: "executed but have not yet commenced"), no en el pasivo |

Ningún valor usado incluye arrendamientos no iniciados: **la herramienta y las cifras no cambian.** Los demás con
arrendamientos financieros pesan ≤ 10% de la deuda (AMZN 10%, RIVN 2%, O y AMT < 1%).

**O y DUK, para la 2b:**

- **DUK (+1.1%, 970 millones de USD).** DUK solo etiqueta sus arrendamientos en el 10-K, no en los 10-Q. A
  2025-12-31 tenía 1,271 millones de arrendamientos operativos (1,033 no corrientes) y 576 de financieros.
  - **Hipótesis:** Yahoo suma el arrendamiento operativo no corriente (≈ 1,000 millones), el mismo patrón que MSFT y
    NVDA. La herramienta no lo ve al 30-jun por falta de la etiqueta trimestral.
  - Con la regla, sobra ese operativo y faltan los 576 de arrendamiento financiero.
  - **En la 2b:** cuando el arrendamiento solo está en el FY, usar el del último 10-K con un aviso de fecha.
- **O (+6.2%, 1,930 millones de USD).** Su deuda en EDGAR es notas 25,092 + préstamos 2,760 + papel comercial 1,400
  = 29,252 millones; Yahoo, 31,180.
  - **Hipótesis por orden:**
    1. hipotecas o disposiciones de la línea de crédito que O etiqueta con conceptos propios (la API no los
       publica);
    2. pasivos ligados a arrendamientos: intangibles de arrendamientos por debajo de mercado 1,457 + pasivos por
       arrendamiento 528 = 1,985 (+2.9% sobre la diferencia).
  - **En la 2b:** leer el balance del 10-Q del 2T (línea "mortgages payable" y la línea de crédito) para decidirlo.

**Efecto en el veredicto** (what-if con la deuda de la regla en los 12 tickers de EE. UU. donde cambia): **ningún
cambio de nivel**. Calidad: DUK +3, RIVN +3, MSFT +1; precio sin cambios. En los emisores IFRS, Yahoo ya da la deuda
de la regla (UL, SHEL), y en TSM, NVO y TM no hay balance de EDGAR del mismo corte (20-F sin interinos).

## 3. Los dos escenarios de D2

| | **A. EDGAR fuente principal de los estados** | **B. EDGAR solo verificación** |
|---|---|---|
| **Qué gana** | Elimina las 41 filas de "fuente errónea" de T3 (sobre todo el EBIT construido por Yahoo, el capex anual de JNJ y el BPA de Finnhub) y los errores de unidad y de factor. Las reexpresiones y el perímetro quedan al día (UL y JNJ ya vienen reexpresados). Sin la dependencia de Yahoo bloqueado en Render (plan B) para los estados | Cambio pequeño. Lo que hoy cuadra (90% de los campos) sigue igual. Los errores de dato se detectan y se corrigen o se avisan sin cambiar de fuente |
| **Qué cuesta** | **Latencia:** 1 descarga por emisor (mediana 0.42 s, 3.6 MB; máximo 0.91 s, 8 MB), más ~0.5–1.4 s y 1–15 MB por cada filing que companyfacts aún no trae (12 de 35 hoy; §3.1). Con caché diaria por CIK, el coste por análisis es casi nulo después del primero | Una descarga por análisis (o caché diaria) solo para verificar: la misma latencia, pero fuera del camino crítico si se hace en segundo plano |
| **Cobertura** | Los campos principales en 35/35. Los huecos son definiciones (bancos, extensiones propias; T2 §4): esas celdas necesitan el respaldo de Yahoo | Igual que hoy |
| **20-F sin trimestres** | TSM, NVO, TM y ASML solo tienen ejercicios en XBRL: el TTM sería el último FY, de 3 a 15 meses de antigüedad (TM: FY a marzo, más de 6 meses de retraso). Hace falta un respaldo de Yahoo trimestral **con el principio de §1** (el corte avanza entero). BCS, HSBC, SHEL y UL sí tienen semestrales en 6-K | Sin cambio: Yahoo trimestral como hoy, verificado contra el FY de EDGAR |
| **Riesgo** | **Definiciones:** cambiar de fuente sin alinear las definiciones cambia veredictos. What-if A de T3: NFLX pasa de precio "razonable" a "exigente" porque la D&A de EDGAR no lleva la amortización de contenidos. La tabla de conceptos (T2 §3) tiene que llevar la definición que quiere el motor, campo a campo | Los errores que no se pueden corregir (sin dato oficial) solo se avisan |
| **Efecto en el veredicto (T3)** | What-if A: 1 cambio de nivel en 35 (NFLX) | What-if B (solo errores de dato): **0 cambios de nivel en 35**; los scores se mueven ≤ 4 puntos (KO, PLD, DUK) |
| **Trabajo en 2b** | Grande: cliente EDGAR en el camino del análisis, lector de instancias, tabla de conceptos por definición, corte coherente, respaldos | Medio: verificación en segundo plano, identidades nuevas y factor oficial |

### 3.1 Escenario A: filings recientes que companyfacts aún no trae

T2 §6.2: hoy faltan en companyfacts 12 filings con XBRL (2 de 20-F, 4 de 6-K semestrales y 6 de 10-Q de EE. UU.).
Si EDGAR es la fuente principal, cada análisis tiene que detectarlo y leerlo.

1. **Detección.** Se compara la lista de filings de `submissions` (formularios 10-K, 10-Q, 20-F, 40-F y 6-K con
   `isXBRL = 1`) con los números de filing que aparecen en los hechos de companyfacts. Un filing presentado después
   del último que está en companyfacts y que no aparece en él es un **filing pendiente**. Sale gratis: `submissions`
   ya se descarga para D7 y para §1.1. Implementado en la herramienta de la 2a como `edgar.missing_filings`.
2. **Lectura.**
   - Se lee el `index.json` del filing para encontrar la instancia XBRL (`<x>_htm.xml`).
   - Se descarga la instancia y se leen sus hechos **sin dimensiones**, con la misma forma que companyfacts:
     contexto (periodo) + unidad + valor (`edgar.parse_instance`).
   - Se funde con companyfacts: en un mismo periodo, manda el filing más reciente.
3. **Coste medido** (los 12 filings de hoy):

   | Paso | Coste |
   |---|---|
   | `index.json` | mediana 0.16 s, máximo 0.78 s |
   | Instancia | 1.2–15.1 MB (mediana 5.3 MB); 0.2–0.5 s de descarga |
   | Lectura | ≤ 0.13 s con 15 MB (HSBC) |
   | **Total por filing pendiente** | **~0.5–1.4 s** |

   Se paga una vez: el resultado se guarda en la caché del CIK hasta que companyfacts lo incorpore.
4. **Mientras tanto** (si la lectura falla o supera el presupuesto de tiempo del análisis, por ejemplo 3 s):
   - el corte se queda en el último periodo de companyfacts, entero (§1), con el aviso **"Estados oficiales de
     <periodo>; el filing <formulario> del <fecha> está pendiente de incorporar"**;
   - si Yahoo ya tiene ese periodo, **no** se mezclan fuentes para adelantarlo: o avanza todo con la instancia, o no
     avanza.

**Recomendación del operador** (la decisión es del usuario):

- **B ahora**, con tres correcciones puntuales que no necesitan cambiar de fuente: el dividendo en los dos sentidos,
  el factor ADR oficial y el corte coherente para Finnhub.
- Con **EDGAR como respaldo** solo para las partidas que Yahoo no da: utilidades retenidas de JNJ y D&A de BCS.
- **A más adelante**, campo a campo, cuando la tabla de definiciones esté cerrada (fase 3: deuda con o sin
  arrendamientos, capex, EBIT bancario).

El dato que lo apoya: con B, el veredicto no cambia en ningún ticker, y el 10% fuera de tolerancia es
sobre todo de definición (78 de 141 filas), no de dato erróneo.

## 4. D7: emisores sin CIK

**Decidido:** se analizan, con un aviso visible y la confianza limitada a "baja".

| Pieza | Diseño |
|---|---|
| **Cómo se decide** | `company_tickers.json` de la SEC, en caché diaria. Ticker → CIK, con la regla de sucesión (XOM: CIK nuevo sin historia → predecesor). **Sin CIK** o **CIK sin `companyfacts`** (SPY: 404) → "sin fuente oficial". Un ETF o un fondo sigue rechazándose antes, como hoy |
| **Estado intermedio** | Con CIK, pero el último filing anual tiene más de 15 meses o la API va por detrás (§6.2 de T2) → "verificado con el FY X" (nota informativa, sin tope de confianza) |
| **Aviso** | Texto: **"Sin fuente oficial para verificar: el emisor no presenta estados en la SEC (EDGAR). Las cifras son de proveedores de datos y no se han contrastado."** |
| **Dónde se muestra** | PDF: portada, bajo el veredicto (bloque de avisos), y en el anexo técnico (fila "Fuente oficial: no"). Web: insignia en `StockHeader` junto a la confianza, con el tooltip del texto. API: `data_provenance.official_source = {"registered": false, "cik": null, "reason": ...}` |
| **Tope de confianza** | En `valuation_confidence`, una dimensión nueva `fuente_oficial`, que aplica `capped_from` hasta "baja" igual que los topes que ya existen. El texto de la confianza dice el motivo |
| **Panel** | Ningún ticker del panel ampliado es D7 (36/36 con CIK; SPY se rechaza antes). Para probarlo hace falta un caso sin CIK en la 2b: una acción solo de Europa (p. ej. un ticker `.DE` o `.PA`) |

## 5. Beta

**Datos de T3** (35 tickers del panel; beta de referencia de 2 años con rendimientos semanales frente a ^GSPC, sobre
la beta que usa hoy el motor, que es la de Finnhub):

- Diferencia mediana **0.30**; 17 de 35 difieren más de 0.3 y 10 más de 0.5. Correlación 0.81.
- **ADR:** Finnhub les da betas mucho más altas que su comportamiento frente al S&P 500 en dólares:
  - NVO 1.96 frente a 1.11;
  - ASML 2.09 frente a 1.24;
  - HSBC 1.47 frente a 0.77;
  - UL 0.66 frente a −0.01;
  - BCS 1.64 frente a 1.25;
  - TSM, al revés: 0.95 frente a 1.43.
  - SHEL (0.06 frente a 0.04) y TM (0.88 frente a 0.72) sí cuadran.

  Es coherente con una beta de Finnhub calculada sobre otro mercado u otro horizonte (no documentado).
- **Defensivas:** Finnhub da betas mayores que las de 2 años:
  - AMT 0.89 frente a 0.06;
  - DUK 0.33 frente a −0.12;
  - O 0.66 frente a 0.17;
  - JNJ 0.20 frente a −0.01.

  Las de 2 años semanales salen casi nulas o negativas en utilities, REIT y energía (XOM −0.02): son ruidosas con
  104 observaciones.
- **Efecto:**
  - el WACC se mueve hasta ±2.4 pp: NVO de 11.3% a 9.2%, PLTR de 11.3% a 13.6%, AMT de 7.9% a 6.4%;
  - **3 cambios de nivel en 35:** BRK-B (precio razonable → exigente), NVO (razonable → atractivo) y NFLX (confianza
    media → alta).

**Propuesta (opción recomendada).** Una beta propia, calculada con la serie de precios que la fase 5 también
necesita. Con ella, el what-if de T3 da **3 cambios de nivel en 35**: BRK-B, NVO y NFLX (arriba).

1. **Estimación:** 2 años semanales frente al S&P 500, para todos. Los ADR cotizan en dólares y el inversor del
   motor es en dólares, así que es la beta del CAPM que usa el WACC.
2. **Ajuste:** Blume, como hoy. Si R² < 0.1 o hay menos de 52 semanas, **beta del sector** (tabla en `config/`),
   no la cruda. Esto evita las betas negativas de DUK, JNJ y XOM.
3. **Comprobación:** Finnhub como contraste. Si \|propia − Finnhub\| > 0.5, aviso "beta discrepante entre fuentes" y
   la confianza lo registra.
4. **Mientras no esté (2b):** la beta de Finnhub en los ADR con aviso, porque es la peor medida, en 6 de 8 ADR fuera
   de ±0.3.

Las cifras salen de `backend/tests/beta_ref.py` y del what-if de T3. La beta no se lleva al motor en la 2a.
