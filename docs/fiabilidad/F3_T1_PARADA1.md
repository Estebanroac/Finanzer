# F3 · Punto de parada 1 (T0–T1): definiciones de D2, historia larga, moneda del crecimiento y tasas base

> Fase 3 del plan de fiabilidad (método por tipo de negocio). Rama `fiabilidad/f3-metodo` (worktree
> `../finanzer_next-f3`), desde `main` = `b2f1972` + el prompt revisado (`3d52202`). **Nada del motor cambia en T1:**
> es una propuesta con datos. Medidas del 2026-10-16 (Nueva York, 21:00–23:30).

## 0. Resumen y lo que te pido

| | Valor | Comando |
|---|---|---|
| Suite y guardián (T0) | **3660 passed, 4 skipped** | `../../finanzer_next/.venv313/bin/python -m pytest tests -q` |
| F1 (T0) | **1290/1411 (91.4%)**, igual que el cierre de la 2b | `tests/edgar_verify.py --whatif --out <dir>` |
| Panel (T0) | 37 tickers (36 analizados + SPY 422); **18 con un solo método de precio**; 5 con arquetipo distinto del esperado (CAT, PLTR, NVDA, CRWD, TSM) | `tests/panel_run.py --mode replay --out <dir>` |
| EDGAR en producción | **desactivado** (`data_provenance.edgar.status = "desactivado"` en JNJ; `/api/health` = `01336e2`) | `curl https://finanzer.app/api/analysis/JNJ` |
| Efecto de las definiciones propuestas (what-if) | **1 cambio de nivel en 36:** BRK-B calidad excelente → sólida (81 → 76) | `tests/f3_t1_whatif.py <dir>` |
| F1 proyectado con las definiciones aprobadas | **≈ 96%** (estimación; se mide en T1b) | §5 |

**Decisiones que te pido** (cada una con mi recomendación):

1. **Definición de cada campo** (§1): capex, beneficio operativo (EBIT), EBIT de bancos, ingresos de bancos y de
   BRK-B, caja de bancos y aseguradoras. Y la deuda, ya decidida en la 2b, como referencia de F1.
2. **Qué campos pasan a EDGAR como fuente principal** (D2, §1.2). Recomiendo: **EBIT**, **ingresos de BRK-B y de
   bancos de EE. UU.** y **capex de las empresas con financiera cautiva**. El resto sigue con Yahoo verificado.
3. **Moneda del crecimiento** (§3): recomiendo **la moneda de los estados**, con el efecto divisa declarado aparte.
4. **Fuente de las tasas base** (§4): **necesito tu permiso para descargar un PDF** (no lo he descargado).

Y una cosa que solo puedes hacer tú: **`SEC_EDGAR_USER_AGENT` en Render.** Sin ella, el primer deploy de la fase
(T1b) no se hace (prompt, "Hechos").

## 1. Definiciones de D2

### 1.1 Campo a campo

Evidencia: `tests/edgar_verify.py` (filas fuera de tolerancia del T0) y la caché de companyfacts de la 2a (valores
anuales citados del 10-K/20-F vigente).

| Campo | Definición propuesta | Práctica estándar | Concepto XBRL | Qué hace Yahoo (medido) | Filas F1 que explica |
|---|---|---|---|---|---|
| **Capex** | Inversión recurrente en activos del negocio: **PP&E + software capitalizado + intangibles comprados en el curso ordinario**. **Excluye el equipo que una financiera cautiva arrienda a terceros** | Damodaran (reinversión = capex neto; el software capitalizado es reinversión); FCF de las propias empresas (NVO lo define con intangibles). La cautiva es actividad financiera: coherente con sacar su deuda (2b, T5) | `PaymentsToAcquirePropertyPlantAndEquipment` + `PaymentsToDevelopSoftware` / `PaymentsForSoftware` + `PaymentsToAcquireIntangibleAssets`; IFRS: `PurchaseOfPropertyPlantAndEquipment…` + `PurchaseOfIntangibleAssets…`. Fuera: `PaymentsToAcquireEquipmentOnLease` | CAT: suma el equipo arrendado de Cat Financial (FY2025: 2,821 + 1,465 = **4,286** = Yahoo; FY2024: 1,988 + 1,227 = **3,215** = Yahoo). CRWD, SNOW, NVO, ASML, UL, HSBC: suma software o intangibles (es la definición propuesta). JNJ (+8% FY2025, +40% FY2024): sin componente que lo explique en companyfacts; causa sin verificar | 20 (capex TTM y FY) |
| **Beneficio operativo (EBIT)** | **El resultado operativo que presenta la empresa en su cuenta de resultados (GAAP/IFRS), sin ajustes.** Sin subtotal presentado: "sin dato" (no se construye) | Es la cifra auditada y verificable; los "ajustados" exigen juicio y no son comparables entre empresas (CFA, *Financial Reporting and Analysis*) | `OperatingIncomeLoss`; IFRS `ProfitLossFromOperatingActivities` | **Construye el suyo:** KO excluye los "otros cargos operativos" (FY2024: 14,022 frente a **9,992** reportado; la diferencia es el cargo por la contraprestación contingente de fairlife y deterioros); PLD resta las ganancias de promoción que la empresa incluye (3,098 frente a 4,416); NEE, DUK, FCX, CRWD, UL, V y AMT, de −10% a +16% | 21 |
| **EBIT de bancos** | **No aplica.** La cuenta de resultados de un banco no tiene "resultado operativo": su equivalente es el **beneficio antes de provisiones** (ingresos netos − gastos no financieros), que usa la fase 3 (T4) para la eficiencia | Práctica bancaria (PPNR, Fed/CCAR; ratio de eficiencia) | `NoninterestExpense` con los ingresos netos de abajo | Sin dato comparable (0 filas) | 0 |
| **Ingresos de bancos** | **Ingresos netos totales:** margen de intereses + ingresos no financieros (neto del gasto por intereses) | La línea "total net revenue" de los propios bancos; base del ratio de eficiencia | EE. UU.: `RevenuesNetOfInterestExpense` (JPM) o `Revenues` (BAC: 60,096 + 53,001 = **113,097**); IFRS: `RevenueAndOperatingIncome` (HSBC: 68,274) | JPM −2 a −5% (valor sin equivalente en los estados: fuente); BAC +1.6%; **BCS**: "Total income" (~29,100 millones de GBP), sin etiqueta estándar (la herramienta lo comparaba con las comisiones, 11,110: concepto equivocado) | 6 |
| **Ingresos de BRK-B** | **Ingresos sin las ganancias de inversión** (las plusvalías de la cartera no son ventas) | Presentación de la propia empresa ("Total revenues", con las ganancias de inversión debajo) | `Revenues` (FY2025: **371,444**) | **Suma las ganancias de inversión:** 371,444 + 39,078 (`GainLossOnInvestments`) = **410,522** = Yahoo | 3 |
| **Ingresos de utilities** (NEE, DUK) y **de XOM** | Ingresos de explotación totales (regulados y no regulados); en XOM, sin el resultado de participadas ni otros ingresos | Presentación de las empresas | `RegulatedAndUnregulatedOperatingRevenue` (NEE 27,412 = Yahoo; DUK 32,237 = Yahoo); XOM: ventas e ingresos de explotación | **Yahoo es correcto;** la herramienta comparaba con los ingresos "de contratos con clientes" (NEE) o con "ingresos totales y otros" (XOM 332,238). Es un error de concepto **de la herramienta** | 9 |
| **Caja** (no financieras) | **Caja + equivalentes + inversiones a corto plazo + valores negociables corrientes** | La "caja" de la deuda neta (Damodaran; S&P) | `CashAndCashEquivalentsAtCarryingValue` + `ShortTermInvestments` + `MarketableSecuritiesCurrent` / `AvailableForSaleSecuritiesDebtSecuritiesCurrent` | Es la de Yahoo; la herramienta comparaba solo la caja (KO, V, NVDA: NVDA 62,470 frente a 22,443 de caja sola) | 3 |
| **Caja de bancos y aseguradoras** | **No entra en la deuda neta ni en el EV** (la 2b ya saca a los bancos de las ratios de apalancamiento). Se muestra la caja reportada (`CashAndCashEquivalents`) | En un banco la caja es activo operativo (reservas); en una aseguradora respalda las reservas técnicas | `CashAndCashEquivalents` | BCS −10.6%, HSBC −46% (caja en bancos centrales con otra agregación); PGR +524% y BRK-B +610% (Yahoo suma carteras de inversión y letras del Tesoro) | 5 |
| **Deuda** (decidida en la 2b, §2.3) | La de la regla: préstamos y bonos + papel comercial + arrendamientos financieros (IFRS 16, todos); sin arrendamientos operativos de US GAAP; bancos fuera | Ya aprobada | Componentes de `DEBT_PARTS` | — | 14 (la herramienta comparaba con `LongTermDebt`) |

### 1.2 EDGAR como fuente principal, campo a campo (D2)

| Campo | ¿EDGAR principal? | Gana | Cuesta | Efecto (what-if) |
|---|---|---|---|---|
| **EBIT** | **Sí** (10-K/10-Q y 20-F con semestrales en XBRL). Sin dato del corte en EDGAR (20-F sin trimestres: TSM, NVO, ASML, TM): el de Yahoo, marcado "estimado por la fuente", como hoy | La cifra reportada; cierra 21 filas | Nada nuevo: la descarga ya la hace la 2b | KO calidad 85 → 82; PLD 82 → 85 y precio 46 → 50; AMT 79 → 75. **Sin cambios de nivel** |
| **Ingresos de BRK-B** | **Sí** | Quita las plusvalías de cartera de las ventas, el crecimiento y la ciclicidad (F3_DISENO §1.4) | — | **BRK-B calidad excelente → sólida (81 → 76)**: el único cambio de nivel |
| **Ingresos de bancos de EE. UU.** | **Sí** (`RevenuesNetOfInterestExpense` / `Revenues`) | Definición estable para el crecimiento bancario (T4) | — | Sin cambios (diferencias de 2–5%) |
| **Ingresos de bancos IFRS** | **No:** sin etiqueta estándar para "total income" en BCS. Yahoo, verificado con margen de intereses + comisiones ≤ ingresos | — | — | — |
| **Capex** | **Sí, por componentes**, solo donde Yahoo mezcla la cautiva (CAT; y DE, F, GM si entran). El resto: Yahoo verificado con la suma de componentes | Saca la actividad financiera del FCF industrial | Una lista de componentes por taxonomía | CAT precio 39 → 42, sin cambio de nivel |
| Caja, ingresos (resto), deuda | **No** (Yahoo, con la definición alineada y verificada por EDGAR; la deuda, como en la 2b) | — | — | — |

**El what-if** (`tests/f3_t1_whatif.py`) sustituye, en lo que lee el pipeline, los valores fuera de tolerancia
(TTM, FY0 y FY1) por los de EDGAR con la definición propuesta. Resultado completo: 31 tickers sin cambios; los 5 de la
tabla con cambios de puntuación; **1 cambio de nivel** (BRK-B).

## 2. Historia larga (10+ ejercicios)

### 2.1 Qué hay

**La historia ya llega con la descarga de la 2b.** `lib/sec_edgar.reduce_facts` conserva **todos los periodos** de los
conceptos que usa (no solo 4 ejercicios); `edgar.fy_backup_years = 4` limita lo que el **respaldo** completa, no lo
que se guarda. Para la fase 3 hay que **añadir conceptos** (BPA diluido y acciones medias diluidas, que hoy no están
en `CONCEPTS`) y encadenar las etiquetas que cambian con los años (ASC 606 en 2018).

Ejercicios anuales distintos en companyfacts (`tests/f3_t1_depth.py`; el primer concepto de la lista que tiene cada
ejercicio):

| Grupo | Tickers | Ejercicios |
|---|---|---|
| EE. UU. con historia completa | AAPL, AMT, AMZN, ASML (20-F en US GAAP), CAT, DUK, JNJ, KO, MSFT, NFLX, NVDA, PG; MU | **19** (2007–2025); MU 18 |
| EE. UU. con huecos de concepto | BAC y JPM (sin EBIT, como corresponde a un banco); PGR (sin EBIT); BRK-B y V (BPA en otra etiqueta: por clase de acción); XOM (acciones diluidas solo 3; la serie sigue en el CIK antiguo); O y PLD (REIT: sin EBIT o capex estándar) | 10–19 según el campo |
| Jóvenes (historia corta por naturaleza) | CRWD, PLTR, SNOW, RIVN, DOW | **7–9** |
| IFRS | TSM 10, HSBC 11, UL 11, SHEL 11 (sin EBIT ni capex estándar), BCS 8, **NVO 7**, **TM 6** (IFRS desde el FY2020; antes, 13 años en US GAAP) | 6–11 |

Consecuencias para T2: en ingresos, **3 no llegan a 8 ejercicios** (NVO 7, TM 6, RIVN 7) y **5 están en 8–9** (PLTR, SNOW, BCS, CRWD, DOW). Para los de menos de 8 el diseño ya prevé la regla
de industria con confianza baja (F3_DISENO §1.2). TM puede encadenar US GAAP (2008–2020) e IFRS (2021–), con el cambio
de norma declarado; propongo hacerlo solo para ingresos y BPA, que no cambian de definición de forma material.

### 2.2 Coste medido (las 3 empresas con más hechos del panel)

`tests/f3_t1_mem.py CIK` (descarga en vivo con el User-Agent del Llavero; proceso nuevo por empresa):

| Empresa | JSON | Descarga (gzip) | Lectura + reducción | Pico de memoria (tracemalloc) | RSS del proceso, aumento | Extracto reducido | Solo anual |
|---|---|---|---|---|---|---|---|
| JPM (CIK 19617) | 8.0 MB | 0.31 s (0.54 MB) | 0.18 s | 42.9 MB | +116 MB | 313 KB | 81 KB |
| BAC (CIK 70858) | 6.9 MB | 0.51 s (0.48 MB) | 0.16 s | 37.0 MB | +89 MB | 303 KB | 70 KB |
| CAT (CIK 18230) | 5.9 MB | 0.57 s (0.38 MB) | 0.14 s | 31.7 MB | +81 MB | 437 KB | 148 KB |

- **En frío:** 0.45–0.75 s (descarga + lectura), **dentro del presupuesto de 3 s** de la 2b. **En caliente:** caché en
  memoria (0.002–0.003 s por análisis, medido en la 2b).
- **Memoria:** el proceso de la app pesa **118 MB** tras importar `main` (medido en local). La lectura de un
  companyfacts grande suma un pico transitorio de **80–116 MB**. Con 512 MB en Render (límite histórico del plan
  gratuito: compruébalo en tu panel), **una** lectura a la vez cabe con margen; **tres lecturas en frío simultáneas**
  (concurrencia 3) podrían rozar el límite.
- **Disco efímero:** tras cada reinicio o deploy, la primera petición de cada empresa vuelve a descargar (0.45–0.75 s).
  **No hace falta caché en disco.**

**Propuesta de caché (T1b):**

1. Caché en memoria del **extracto reducido** (ya existe), con **LRU de 64 empresas** (≤ 30 MB con los tamaños medidos).
2. **Un semáforo de 1** para la lectura de companyfacts: dos análisis en frío no leen 8 MB a la vez. El segundo
   espera ~0.2 s.
3. Medir el pico en Render tras el deploy de T1b (log de memoria que me muestres) antes de construir T2 encima.

## 3. Moneda del crecimiento

**Hoy:** el crecimiento de un ADR se mide en dólares. UL: **+0.5%** en USD frente a **−3.8%** en EUR (F2b_PARADA2 §6);
el tipo de cambio entra en el crecimiento.

**Propuesta:** crecimiento y CAGR **en la moneda de los estados**, con el efecto divisa declarado aparte ("en dólares,
+0.5%, por el euro").

- **Práctica estándar:** el crecimiento operativo no incluye el tipo de cambio. Las empresas lo publican así
  (crecimiento "a tipo de cambio constante" o "subyacente": UL, *underlying sales growth*).
- **Coherencia del DCF:** los flujos y la tasa de descuento, en la misma moneda (Damodaran, *currency consistency*).
  Los flujos se proyectan en la moneda de los estados con su crecimiento y se convierten al tipo de contado. La
  diferencia de inflación entre monedas desarrolladas se declara como supuesto.

## 4. Tasas base · **necesito tu permiso para descargar**

**Fuente original:** Mauboussin, Callahan y Majd, *The Base Rate Book* (Credit Suisse, 2016).

- **No tiene copia oficial localizable hoy:** Credit Suisse ya no existe (UBS) y el sitio de Mauboussin no la lista.
- Las copias que circulan están en blogs personales. **No las uso:** no puedo verificar su procedencia.

**Fuente oficial vigente:** los mismos autores, en Morgan Stanley Investment Management (Counterpoint Global):

| Documento | Fecha | Enlace |
|---|---|---|
| *Bayes and Base Rates: How History Can Guide Our Assessment of the Future* | 10-feb-2026 | página: `morganstanley.com/im/en-us/individual-investor/insights/consilient-observer/bayes-and-base-rates.html`; PDF: `article_bayesandbaserates_ltr.pdf` |
| *Bayes and Base Rates 2.0* (seguimiento) | 13-may-2026 | misma serie |

- Según su resumen, el informe trae las tasas base de crecimiento de ingresos de las empresas cotizadas de EE. UU.
  en 75 años, por horizonte. Es exactamente lo que necesita el F3_DISENO §8.1.
- **El PDF solo se obtiene descargándolo.** La web devuelve 403 a lecturas automáticas y el navegador lo ofrece como
  descarga; al intentarlo te pudo aparecer un diálogo de guardado: no hace falta que lo aceptes.
- **Permiso que te pido:** descargar `article_bayesandbaserates_ltr.pdf` desde `morganstanley.com`. No conozco el
  tamaño: el servidor no lo informa sin descargar.
  - Puedes descargarlo tú y dejarlo en una carpeta que me digas, o autorizarme a hacerlo (y lo mismo con el 2.0).
- **Con el PDF:** extraigo la tabla con página y edición a `config/base_rates.toml` y te la presento antes de usarla.
- **Sin él:** el §8.1 no se puede aplicar. La alternativa sería calcular tasas base propias con EDGAR, pero solo con
  las ~36 empresas del panel, que no son un universo representativo. **No la recomiendo.**

## 5. F1 proyectado

Si la herramienta compara con las definiciones aprobadas (permitido por el prompt, declarado) y el motor usa EDGAR
donde se apruebe:

| Grupo | Filas que pasarían a "dentro" (estimación) |
|---|---|
| EBIT (EDGAR principal) | 21 |
| Deuda de la regla frente a la de la regla | ~12 de 14 |
| Ingresos (BRK-B, NEE, DUK y XOM con el concepto correcto) | ~12 |
| Capex por componentes (CAT y los que suman software o intangibles) | ~14 de 20 |
| Caja de no financieras con su definición | 3 |
| **Total** | **≈ 62 → ≈ 1352/1411 (≈ 96%)** |

Es una **estimación**: la cifra real se mide en T1b, con y sin los cambios de definición. Quedarían fuera, sobre todo:

- el dividendo indicado frente al declarado (15 filas, por diseño de la 2b);
- JPM, JNJ y DOW (fuente, causas sin verificar);
- los ingresos de BCS (sin etiqueta).

## 6. Siguiente paso tras tu decisión

**T1b:**

- las definiciones y EDGAR principal en los campos aprobados, con un commit por decisión y su test antes;
- la historia larga con BPA y acciones;
- la caché LRU con semáforo;
- el crecimiento en la moneda de los estados.

Después: F1 medido, panel frente a T0 y diff de golden para tu aprobación. El deploy, solo con la variable de Render
puesta y tu "ok, pushea".
