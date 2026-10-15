# F2a · T3 — Discrepancias del pipeline frente a SEC EDGAR (línea base de F1)

> Fase 2a del plan de fiabilidad (medir; no se corrige nada del motor). Medida del 2026-10-15 sobre los fixtures del
> panel ampliado: **36 tickers**. Hay comparación en 35, porque SPY es un ETF sin estados. HSBC, SHEL, UL y TM se
> capturaron ese día tras el cierre de Nueva York. Este porcentaje es la **línea base de la propiedad F1 ("dato
> correcto")** del plan: PLAN §3 pide ≥ 95% para cerrar la fase 2.

## 0. Resumen

- **Línea base F1: 90.0%** de los campos comparables dentro de tolerancia (1,262 de 1,403).
  - EE. UU.: **91.6%** (1,039/1,134). Extranjeros: **82.9%** (223/269).
  - Ratios recalculados con EDGAR: 84.7% (183/216).
- **Sin dato del mismo periodo en EDGAR:** 220 comparaciones. Sobre todo son los TTM de los 20-F sin trimestres (TSM,
  NVO, ASML, TM) y los conceptos sin etiqueta estándar. Quedan fuera del porcentaje.
- **Sin dato en el pipeline con EDGAR disponible:** 24. Ejemplo: las utilidades retenidas de JNJ (169 mil millones de
  USD en EDGAR).
- **Lo que queda fuera** (141 filas de campos más 33 de ratios que solo heredan):

  | Causa | Filas |
  |---|---|
  | **Definición** | 78 |
  | **Fuente errónea** | 41 |
  | Periodo | 14 |
  | Unidad + factor ADR | 4 |
  | Factor ADR | 4 |

  - **Definición** (78): Yahoo y EDGAR miden cosas distintas con el mismo nombre. Ejemplos: deuda con arrendamientos
    o subordinada, capex con intangibles o software, caja con inversiones, cupones AT1, ingresos de un banco.
  - **Fuente errónea** (41): ningún valor de los estados lo explica. La mitad es el beneficio operativo que Yahoo
    construye; el resto, cajas y deudas de Yahoo y el BPA de Finnhub en BAC.
  - **Unidad + factor ADR** (4): todos son el dividendo de Finnhub en la moneda de la línea local.
- **Campos 100% dentro:** activo, pasivo, patrimonio, activo y pasivo corriente, existencias, flujo de operaciones,
  utilidades retenidas (donde las hay) y beneficio bruto.
  - Los débiles: **deuda total (40.0%)**, **dividendo por acción (34.8%)**, **beneficio operativo (55.0% TTM; 74.5%
    anual)** y caja (67.7%).
- **Efecto en el veredicto** (§6):
  - **corregir solo los errores de dato (B): 0 cambios de nivel en 35;**
  - cambiar a EDGAR con la tabla tal cual (A): 1 cambio (NFLX, por la definición de D&A);
  - deuda con la regla de coherencia con el EBITDA: 0 cambios;
  - beta propia: 3 cambios (BRK-B, NVO, NFLX).
- **Casos conocidos** (§4): **confirmados** BCS (peniques, factor y AT1), UL (perímetro y factor), JNJ (BPA de Finnhub
  en vivo y utilidades retenidas), TSM, NVO, el dividendo de los 4 ADR nuevos y la beta de los ADR. **Descartado:**
  NVDA, cuyo dividendo es correcto y lo anula por error la identidad de la fase 1. **Nuevo:** TM, factor 11.07 por
  una capitalización de Yahoo un 9.6% corta.

## 1. Método

**Herramienta:** `backend/tests/edgar_verify.py`. Funciona como replay de los fixtures del panel con envoltorios de
lectura y **no toca el motor**. Para cada ticker:

1. **Captura** lo que usa el pipeline: el `FinancialStatements` que construye `YahooFinanceFetcher.get_financial_data`,
   el `info` de `get_ticker_info` (series anuales `_statements_fy` incluidas) y `data_provenance`.
2. **Busca en EDGAR el mismo periodo.** Usa el extracto de `tests/fixtures/edgar/<T>.json`: companyfacts más los
   filings con XBRL que la API aún no trae, leídos de su instancia (F2_EDGAR_DIAGNOSTICO §6.2).
   - **Flujos en TTM:** FY + acumulado del año − el mismo acumulado del año anterior; los 10-Q y los 6-K traen el
     acumulado.
   - **Flujos anuales:** el FY que termina en el año de la etiqueta de Yahoo.
   - **Saldos:** el balance a la misma fecha, con ±14 días porque Yahoo redondea al fin de mes.
   - **Acciones:** las más recientes de EDGAR (portada o balance).
3. **Deshace la conversión del pipeline** con sus propios tipos (`data_provenance.currency`):
   - saldo, con el tipo de su fecha;
   - ejercicio, con el de su año;
   - TTM, con `ttm_rate` (media de 4 trimestres). En los extranjeros con TTM, el error de esta aproximación es
     ≤ 0.5%.

   Lo que va por acción se compara en la **clase del precio** con el **factor ADR oficial** (T2 §5); BRK-B, en
   clase B (1/1500 de A).
4. **Tolerancias (PLAN §3):**
   - ±1% en estados y acciones;
   - ±2% en BPA y dividendo por acción;
   - ratios recalculados con EDGAR: ±2% relativo o ±0.5 pp.
5. **Clasifica cada discrepancia** buscando qué valor de EDGAR sí coincide:
   - **periodo:** otro corte (FY en lugar de TTM, el trimestre anterior o siguiente) o un split posterior al filing;
   - **definición:** otra etiqueta o combinación, como arrendamientos, cupones AT1, capex con software o
     intangibles, caja con inversiones o beneficio del ordinario. Incluye la búsqueda en todos los conceptos del
     emisor y la de la diferencia exacta (marcada "probable");
   - **perímetro:** el valor anterior a una reexpresión, o el de las operaciones continuadas;
   - **unidad:** ×/÷ 100 o 1000, moneda sin convertir;
   - **factor ADR:** el factor del motor en lugar del oficial;
   - **fuente errónea:** ningún valor de los estados lo explica;
   - **EDGAR falta:** no hay dato del periodo; fuera del porcentaje;
   - **casos comprobados a mano:** van en `MANUAL`, con la evidencia en el propio texto.
6. **Efecto en el veredicto:** `--whatif` repite el análisis sustituyendo en `info` los campos fuera de tolerancia
   por el valor de EDGAR, convertido con los mismos tipos y el factor oficial.
   - **A:** todos los campos fuera de tolerancia (EDGAR como fuente, con la tabla de conceptos tal cual).
   - **B:** solo los errores de dato (fuente, unidad, factor, periodo); las diferencias de definición se quedan.

**Qué no cubre:**
- los campos de mercado (precio, capitalización, 52 semanas), que no son de EDGAR;
- el BPA futuro (estimaciones);
- las magnitudes derivadas del motor (normalización, FFO).

La beta se mide aparte (§5) con `backend/tests/beta_ref.py`.

```bash
cd finanzer_next/backend
python3 tests/edgar_diag.py                                   # extractos (caché en tests/fixtures/edgar/raw)
../.venv313/bin/python tests/edgar_verify.py --whatif --out <dir>     # resultado.json + resumen.md
../.venv313/bin/python tests/beta_ref.py --out <dir>
```

## 2. Línea base F1: % dentro de tolerancia

Campos de los estados del último corte, series anuales (FY0 y FY1), por acción y acciones. Los ratios van aparte (§0). "Fuera" incluye todas las causas; "EDGAR falta" no cuenta.


### 2.1 Por campo
| Campo | Dentro de tolerancia | Fuera | Causas de las que quedan fuera |
|---|---|---|---|
| capex | 19/24 (79.2%) | 5 | 5 definición |
| capital_expenditure (FY0/FY1) | 42/58 (72.4%) | 16 | 14 definición, 2 fuente errónea |
| cash | 21/31 (67.7%) | 10 | 5 definición, 5 fuente errónea |
| current_assets | 23/23 (100.0%) | 0 | — |
| current_assets (FY0/FY1) | 54/54 (100.0%) | 0 | — |
| current_liabilities | 23/23 (100.0%) | 0 | — |
| current_liabilities (FY0/FY1) | 54/54 (100.0%) | 0 | — |
| depreciation | 22/26 (84.6%) | 4 | 2 definición, 2 fuente errónea |
| diluted_eps (FY0/FY1) | 62/64 (96.9%) | 2 | 2 periodo |
| dividend_per_share | 8/23 (34.8%) | 15 | 7 definición, 4 periodo, 4 unidad + factor ADR |
| dividends_paid | 21/23 (91.3%) | 2 | 2 definición |
| eps | 21/27 (77.8%) | 6 | 4 definición, 1 fuente errónea, 1 periodo |
| gross_profit | 11/11 (100.0%) | 0 | — |
| gross_profit (FY0/FY1) | 28/28 (100.0%) | 0 | — |
| interest_expense | 20/24 (83.3%) | 4 | 2 fuente errónea, 1 periodo, 1 definición |
| inventories | 14/14 (100.0%) | 0 | — |
| long_term_debt | 17/23 (73.9%) | 6 | 4 definición, 2 fuente errónea |
| net_income | 29/31 (93.5%) | 2 | 1 fuente errónea, 1 definición |
| net_income (FY0/FY1) | 67/69 (97.1%) | 2 | 2 definición |
| operating_cash_flow | 31/31 (100.0%) | 0 | — |
| operating_cash_flow (FY0/FY1) | 70/70 (100.0%) | 0 | — |
| operating_income | 11/20 (55.0%) | 9 | 8 fuente errónea, 1 definición |
| operating_income (FY0/FY1) | 35/47 (74.5%) | 12 | 8 fuente errónea, 3 definición, 1 periodo |
| ordinary_shares (FY0/FY1) | 59/66 (89.4%) | 7 | 4 factor ADR, 3 periodo |
| retained_earnings | 28/28 (100.0%) | 0 | — |
| retained_earnings (FY0/FY1) | 62/64 (96.9%) | 2 | 2 definición |
| revenue | 23/30 (76.7%) | 7 | 4 definición, 2 fuente errónea, 1 periodo |
| revenue (FY0/FY1) | 56/67 (83.6%) | 11 | 8 definición, 3 fuente errónea |
| shares_outstanding | 29/33 (87.9%) | 4 | 3 fuente errónea, 1 periodo |
| stockholders_equity (FY0/FY1) | 70/70 (100.0%) | 0 | — |
| total_assets | 31/31 (100.0%) | 0 | — |
| total_assets (FY0/FY1) | 70/70 (100.0%) | 0 | — |
| total_debt | 10/25 (40.0%) | 15 | 13 definición, 2 fuente errónea |
| total_equity | 31/31 (100.0%) | 0 | — |
| total_liabilities | 30/30 (100.0%) | 0 | — |
| total_liabilities (FY0/FY1) | 60/60 (100.0%) | 0 | — |

### 2.2 Por ticker
| Ticker | Dentro de tolerancia | Fuera | Causas de las que quedan fuera |
|---|---|---|---|
| AAPL | 48/49 (98.0%) | 1 | 1 definición |
| AMT | 40/44 (90.9%) | 4 | 3 fuente errónea, 1 definición |
| AMZN | 41/42 (97.6%) | 1 | 1 definición |
| ASML | 31/32 (96.9%) | 1 | 1 definición |
| BAC | 30/33 (90.9%) | 3 | 3 fuente errónea |
| BCS | 24/35 (68.6%) | 11 | 7 definición, 2 factor ADR, 1 unidad + factor ADR, 1 periodo |
| BRK-B | 22/26 (84.6%) | 4 | 4 definición |
| CAT | 40/44 (90.9%) | 4 | 3 definición, 1 periodo |
| CRWD | 35/45 (77.8%) | 10 | 4 definición, 4 periodo, 2 fuente errónea |
| DOW | 36/41 (87.8%) | 5 | 4 definición, 1 fuente errónea |
| DUK | 38/43 (88.4%) | 5 | 3 definición, 2 fuente errónea |
| FCX | 39/41 (95.1%) | 2 | 1 fuente errónea, 1 definición |
| HSBC | 22/32 (68.8%) | 10 | 9 definición, 1 unidad + factor ADR |
| JNJ | 41/44 (93.2%) | 3 | 2 fuente errónea, 1 definición |
| JPM | 28/32 (87.5%) | 4 | 2 fuente errónea, 1 definición, 1 periodo |
| KO | 44/48 (91.7%) | 4 | 3 fuente errónea, 1 definición |
| MSFT | 47/50 (94.0%) | 3 | 2 definición, 1 periodo |
| MU | 46/50 (92.0%) | 4 | 3 definición, 1 periodo |
| NEE | 35/43 (81.4%) | 8 | 6 definición, 2 fuente errónea |
| NFLX | 43/44 (97.7%) | 1 | 1 definición |
| NVDA | 45/48 (93.8%) | 3 | 2 definición, 1 fuente errónea |
| NVO | 27/30 (90.0%) | 3 | 3 definición |
| O | 27/29 (93.1%) | 2 | 1 periodo, 1 fuente errónea |
| PG | 45/47 (95.7%) | 2 | 1 definición, 1 periodo |
| PGR | 33/35 (94.3%) | 2 | 1 fuente errónea, 1 definición |
| PLD | 30/37 (81.1%) | 7 | 5 fuente errónea, 1 periodo, 1 definición |
| PLTR | 44/44 (100.0%) | 0 | — |
| RIVN | 46/48 (95.8%) | 2 | 1 definición, 1 fuente errónea |
| SHEL | 39/43 (90.7%) | 4 | 2 fuente errónea, 1 definición, 1 unidad + factor ADR |
| SNOW | 42/45 (93.3%) | 3 | 3 definición |
| TM | 19/22 (86.4%) | 3 | 2 factor ADR, 1 fuente errónea |
| TSM | 27/29 (93.1%) | 2 | 2 definición |
| UL | 34/46 (73.9%) | 12 | 5 fuente errónea, 5 definición, 1 unidad + factor ADR, 1 periodo |
| V | 34/39 (87.2%) | 5 | 4 definición, 1 periodo |
| XOM | 40/43 (93.0%) | 3 | 3 fuente errónea |

### 2.3 Por arquetipo
| Arquetipo | Dentro de tolerancia | Fuera | Causas de las que quedan fuera |
|---|---|---|---|
| CYCLICAL | 250/272 (91.9%) | 22 | 10 definición, 8 fuente errónea, 2 factor ADR, 1 periodo, 1 unidad + factor ADR |
| FINANCIAL | 159/193 (82.4%) | 34 | 22 definición, 6 fuente errónea, 2 periodo, 2 unidad + factor ADR, 2 factor ADR |
| GROWTH_PRE_PROFIT | 88/93 (94.6%) | 5 | 4 definición, 1 fuente errónea |
| MATURE | 595/649 (91.7%) | 54 | 31 definición, 13 fuente errónea, 9 periodo, 1 unidad + factor ADR |
| REIT | 97/110 (88.2%) | 13 | 9 fuente errónea, 2 periodo, 2 definición |
| UTILITY | 73/86 (84.9%) | 13 | 9 definición, 4 fuente errónea |

### 2.4 EE. UU. frente a extranjeros
| Origen | Dentro de tolerancia | Fuera | Causas de las que quedan fuera |
|---|---|---|---|
| EE. UU. | 1039/1134 (91.6%) | 95 | 50 definición, 33 fuente errónea, 12 periodo |
| extranjero | 223/269 (82.9%) | 46 | 28 definición, 8 fuente errónea, 4 unidad + factor ADR, 4 factor ADR, 2 periodo |

### 2.5 Por tipo de dato
| Tipo | Dentro de tolerancia | Fuera | Causas de las que quedan fuera |
|---|---|---|---|
| acciones | 29/33 (87.9%) | 4 | 3 fuente errónea, 1 periodo |
| estado (último corte) | 415/479 (86.6%) | 64 | 38 definición, 24 fuente errónea, 2 periodo |
| por acción | 29/50 (58.0%) | 21 | 11 definición, 5 periodo, 4 unidad + factor ADR, 1 fuente errónea |
| serie anual (FY0, FY1) | 789/841 (93.8%) | 52 | 29 definición, 13 fuente errónea, 6 periodo, 4 factor ADR |

### 2.6 Causas (todas las filas fuera, ratios incluidos)
| Causa | Filas |
|---|---|
| definición | 78 |
| fuente errónea | 41 |
| hereda | 33 |
| periodo | 14 |
| unidad + factor ADR | 4 |
| factor ADR | 4 |

## 3. Las discrepancias por causa, con ejemplos

| Causa | Qué es | Ejemplos medidos |
|---|---|---|
| **Definición** (78) | Las dos fuentes tienen la cifra, pero miden cosas distintas | **Deuda:** Yahoo suma arrendamientos operativos de US GAAP (10 de EE. UU.; F2_PRECEDENCIA §2.3) o deuda subordinada de banco (BCS, HSBC). **Capex:** Yahoo suma activos en arrendamiento (CAT), software (CRWD, SNOW) o intangibles (NVO, ASML, HSBC, UL). **Caja:** con inversiones a corto plazo (KO, V) o caja en bancos centrales (BCS, HSBC). **AT1:** dividendos de BCS con cupones (1,254 + 997 = 2,251 millones de GBP). **D&A:** con amortización de contenidos (NFLX) o con etiqueta propia (MSFT). **Ingresos de bancos sin etiqueta estándar** (BCS, HSBC). **Ingresos de utilities:** NEE y DUK con `RegulatedAndUnregulatedOperatingRevenue` |
| **Fuente errónea** (41) | Ningún valor de los estados lo explica | **Beneficio operativo construido por Yahoo**, 16 filas: KO, PLD, AMT, NEE, DUK, FCX, CRWD y UL (KO 2024: 14,020 frente a 9,992; PLD TTM 3,532 frente a 5,029). **Capex anual de JNJ** (2024: 6,207 frente a 4,424, aunque el TTM cuadra). **Ingresos de XOM** (−2% a −3%) **y JPM**. **Cajas y deudas de Yahoo:** caja de BAC, PGR, NVDA, DOW y UL; deuda a largo plazo de BAC y PLD; deuda total de O y DUK. **Gastos financieros y D&A:** SHEL, UL y NEE. **BPA de Finnhub en BAC:** 4.509, que no es ningún TTM de EDGAR. **Acciones de Yahoo:** RIVN, PLD y TM |
| **Periodo** (14) | El valor es de otro corte | **Dividendo indicado de Finnhub con una subida** posterior al último trimestre de EDGAR (MSFT, JPM, CAT, PG: probable). **MU:** BPA de Finnhub del FY que termina en septiembre frente a estados de mayo. **Splits y consolidaciones** que Yahoo ya aplica a años anteriores (CRWD 4:1, UL 8 por 9). **BCS:** acciones de hoy frente al cierre. **Otros cortes** (O, PLD: el TTM de Yahoo coincide con el del trimestre anterior; probable) |
| **Unidad + factor ADR** (4) | Moneda local por acción ordinaria leída como USD por ADR | El dividendo de Finnhub de BCS, HSBC, SHEL y UL (peniques). TM, TSM y NVO tienen el mismo defecto (§4), pero sus filas caen en "EDGAR falta" porque su TTM no existe en EDGAR |
| **Factor ADR** (4) | Acciones del balance divididas por el factor implícito del motor en lugar del oficial | BCS (4.154 frente a 4) y TM (11.07 frente a 10), en las series de acciones FY0 y FY1 |
| **EDGAR falta** (220, fuera del %) | No hay dato del periodo | TTM de los 20-F sin interinos; beneficio operativo que el emisor no presenta (JNJ, bancos); balances sin clasificar (bancos, aseguradoras, REIT); utilidades retenidas de UL (otra partida de reservas) |

**Perímetro.** No queda ninguna discrepancia por perímetro: los ingresos de UL y de JNJ que usa el pipeline ya
coinciden con los reexpresados de EDGAR (UL 2024: 52,479 millones de EUR; el original del 20-F de 2024 era 60,761).
El perímetro está confirmado en EDGAR (F2_EDGAR_DIAGNOSTICO §6.4), pero Yahoo ya lo trae al día.

**Factor ADR en el resto:** TSM 5.00003, ASML 1.003 (no aplicado), NVO 1.007 (no aplicado), HSBC 5.012, SHEL 2.0004 y
UL 1.012 (no aplicado). Todos dentro de ±0.25%, salvo los no aplicados, que no tienen efecto.

## 4. Casos conocidos: confirmados o descartados con datos

| Caso (mapa de la bitácora) | Veredicto | Datos |
|---|---|---|
| **BCS: dividendo en peniques** | **Confirmado** (unidad + factor ADR) | Finnhub `dividendIndicatedAnnual` = 11.5: son **peniques por acción ordinaria**, y el motor los toma como dólares por ADR. En dólares por ADR, el indicado es 0.115 GBP × 4 × 1.342 = 0.62 USD: una diferencia de **18.6×**. Frente al pagado de EDGAR (dividendos 1,254 millones de GBP / acciones medias), la diferencia es de 25.5×. La identidad de la fase 1 ya lo anula ("sin dato"); en el what-if B, BCS no cambia de nivel |
| **BCS: factor 4.154 frente a 4** | **Confirmado; la causa es un desfase de fechas**, no un factor distinto | Factor oficial 4 (20-F de 2026-02-10 y F-6EF de 2025-11-20). El motor divide las acciones del balance de Yahoo a 2025-12-31 (13,845 millones; la portada del 20-F dice 13,867) entre las de la cotización de hoy (capitalización / precio = 3,333 millones de ADS = 13,331 millones de ordinarias). La diferencia son las **recompras de 2026**: la media del 1S-2026 en el 6-K ya es 13,645 millones. **Efecto medido:** las series de acciones del balance (FY0 y FY1) quedan un 3.85% por debajo. El BPA anual cuadra exacto con el factor 4 (Yahoo ya lo da por ADR), así que el P/E no se ve afectado |
| **BCS: AT1** | **Confirmado en dividendos y BPA; efecto pequeño en el ROE** | **Dividendos pagados:** Yahoo da 2,251 millones de GBP = 1,254 de dividendos + **997 de cupones AT1** (beneficio de los propietarios − beneficio del ordinario: 7,172 − 6,175). **BPA:** el motor lo deriva como beneficio de los propietarios / acciones = 2.31 GBP por ADR, frente a 1.93 del BPA diluido de EDGAR (**+19.8%**, porque incluye lo que cobran los AT1). **ROE:** 10.0% en el motor; el del accionista ordinario ((beneficio − AT1) / (patrimonio − AT1 de 13,275 millones)) es 10.4%. Numerador y denominador bajan a la vez |
| **UL: perímetro** | **Confirmado** | Ingresos de 2024 reexpresados de 60,761 a **52,479** millones de EUR (−13.6%) por la escisión de helados (The Magnum Ice Cream Company); discontinuadas de 3,798 millones en 2025. **El pipeline ya usa el perímetro nuevo:** los ingresos de Yahoo de 2025 (50,503 millones de EUR) y de 2024 (52,479) coinciden con EDGAR ya reexpresado. Quedan fuera de tolerancia el beneficio operativo, que Yahoo construye a su manera (10,127 frente a 9,037 en 2025), y las acciones de 2024: Yahoo les aplica la consolidación 8 por 9 de la escisión (2,476 × 8/9 = 2,201) |
| **UL: factor 1.012** | **Confirmado: el mismo desfase de recompras que BCS, sin efecto** | Las acciones de los estados a 2025-12-31 (2,179.5 millones) entre las de la cotización (2,153.5 millones; el 6-K a 2026-06-30 dice 2,153.3) dan 1.012. Está dentro de la tolerancia del motor, así que no se aplica: las acciones y el BPA de UL cuadran con EDGAR | Factor oficial 1 (20-F de 2026-03-12 y F-6EF de 2020-11-27, Deutsche Bank) |
| **JNJ: BPA de Finnhub con un trimestre nuevo** | **Confirmado en vivo; no se reproduce en los fixtures** | Fixtures del 14-oct 16:15: BPA del motor 8.62 = TTM de junio en EDGAR. **Finnhub en vivo (15-oct): 6.5886** = 8.62 − 2.12 (3T-2025) + 0.09 (3T-2026, del 8-K del 13-oct con el cargo del talco). Con la regla actual (Finnhub manda si difiere más de un 2%), producción mezcla un BPA a septiembre con estados a junio. Es la regla del corte coherente (F2_PRECEDENCIA §1) |
| **TSM, NVO, NVDA: dividendo** | **TSM y NVO confirmados** (unidad: moneda local por acción ordinaria). **NVDA descartado:** el dato de Finnhub es correcto y lo anula por error la identidad de la fase 1 | **TSM:** 26 = TWD por acción ordinaria. Por ADR en USD: 26 × 5 × 0.0322 = 4.19, es decir, **6.2×**. **NVO:** 11.7 = DKK por acción (DPA de 2025 en EDGAR, `DividendsPaidOrdinarySharesPerShare` = 11.7). En USD: 1.83, es decir, **6.4×**. **NVDA:** 1.00 = 0.25 × 4. NVDA subió el trimestral de 0.01 a **0.25** en el 2T de su año fiscal 2027 (10-Q del 2026-07-26). El TTM pagado (0.28) aún no lo refleja, y la identidad de la fase 1 (yield frente a lo pagado: 0.45% frente a 0.13%) anula un dato bueno: **falso positivo** |
| **JNJ sin utilidades retenidas** | **Confirmado** | El pipeline no tiene `retainedEarnings` (Yahoo plan B: sin dato en el último trimestre ni en FY0/FY1). EDGAR sí: `RetainedEarningsAccumulatedDeficit` = 169 mil millones de USD a 2025-12-28 y 155.8 a 2024-12-29. El Altman de JNJ, hoy "sin dato", se puede calcular |
| **Dividendo de los ADR nuevos** (mapa: "UL habría mostrado 251.70%") | **Confirmado en los 4:** Finnhub da el dividendo de la línea local por acción ordinaria | **HSBC** 55.67, **SHEL** 112.82 y **UL** 164.99 son **peniques** (línea de Londres). **TM** 100 son **yenes**. El motor los lee como dólares por ADR: dividend yield de 58.9%, 109.0%, 255.2% y 52.1%. En USD por ADR serían 3.73, 3.02, 2.21 y 6.48 (EDGAR, pagado del último FY: 3.30, 2.86, 2.29 y 6.16). Los cuatro salen "sin dato" por la identidad de la fase 1. Es el mismo arreglo de origen que BCS, TSM y NVO |
| **TM: factor 11.07 frente a 10** | **Nuevo: fuente errónea de Yahoo** | La capitalización / precio de Yahoo da 1,178 millones de ADR = 11,778 millones de acciones, frente a 13,034 en circulación en el 20-F (2026-03-31). El motor divide 13,033 entre 1,178 y aplica 11.07: **las series de acciones del balance quedan un 9.6% por debajo**. La capitalización de Yahoo también queda un 9.6% por debajo de la que dan las acciones oficiales. En el what-if B (acciones de EDGAR), TM no cambia de nivel |
| **HSBC: AT1 y dividendos** | **Al revés que BCS** | Yahoo da los dividendos al **ordinario** (11,581 millones de USD = `DividendsPaidOrdinaryShares`); el total de EDGAR (13,482) incluye los cupones AT1. El beneficio de Yahoo es el atribuido a la dominante (EDGAR `ProfitLoss` − minoritarios). Deuda: Yahoo suma la subordinada (132,899 frente a 105,027 de títulos de deuda), que con la regla de FINANCIAL queda fuera de las ratios |
| **Beta de Finnhub en los ADR** (mapa: BCS y NVO 1.64) | **Confirmado: la peor beta del panel** | Hoy en los fixtures: BCS 1.64 y **NVO 1.96** (1.64 era el valor de otra fecha), frente a una referencia de 2 años semanal frente al S&P 500 de 1.24 y 1.11. ASML 2.09 frente a 1.24; TSM 0.95 frente a 1.44. Con los 8 ADR, 6 difieren más de 0.3 (HSBC 1.47 frente a 0.77; UL 0.66 frente a −0.01); SHEL y TM no (§5) |
| **Render ≠ local en 7/30 (fase 0)** | **Medido con EDGAR: en 3 casos Render tenía razón, en 2 los dos datos son reales pero de cortes distintos y 2 no se pueden verificar** | Ver §4.1 |

### 4.1 Las 7 diferencias de Yahoo entre Render y local (fase 0), frente a EDGAR

| Ticker | Diferencia (F0) | Render (producción) | Local (fixture) | EDGAR | Quién tiene razón |
|---|---|---|---|---|---|
| PG | Acciones de `fast_info` | 2,324,433,060 | 2,322,672,312 | Portada del 10-K: **2,324,433,060** (2026-07-31) | **Render** (local no existe en EDGAR) |
| MSFT | Acciones de los estados | 7,428,434,704 | 7,427,000,000 | Portada a 2026-04-23: 7,428,434,704; balance a 2026-06-30: 7,427,000,000 | Los dos son reales; **local** es el corte más reciente |
| DUK | Balance trimestral | Al 31-mar (caja 2,140 millones) | Al 30-jun (caja 673 millones) | Los dos existen | Los dos son reales; **local** es el corte más reciente (el 10-Q del 2T es del 2026-08-04) |
| CAT | Acciones diluidas trimestrales (BPA) | BPA 23.25 | BPA 23.45 | BPA diluido TTM a 2026-06-30: **23.22** | Los dos dentro de ±2%; **Render** más cerca (0.1% frente a 1.0%) |
| NVDA | Balance del Altman | X4 (patrimonio / pasivo) **3.177**; Z 12.85 | X4 1.723; Z 11.33 | FY2026: patrimonio 157,293 / pasivo 49,510 = **3.177** | **Render.** Al fixture local le falta el pasivo total del FY ("sin dato" en T3) y el Altman usa otro. Zona segura en los dos casos; sin cambio de nivel |
| NEE | Acciones diluidas trimestrales (normalización) | Beneficio normalizado 9,031 millones | 9,068 millones | Dato derivado; EDGAR trae las acciones medias diluidas trimestrales | No verificable directamente (es una magnitud del motor) |
| PLD | Trimestres con resultado operativo | — | — | Hoy solo difiere el precio (fase 0: recapturado, igual) | Sin diferencia de datos |

## 5. Beta

`backend/tests/beta_ref.py`: 2 años de rendimientos semanales frente a ^GSPC (precios hasta el 2026-10-15), frente a
la beta que usa hoy el motor (Finnhub en los 35).

- Diferencia mediana **0.30**; 17 de 35 difieren más de 0.3 y 10 más de 0.5. Correlación 0.81.
- **ADR:** 6 de 8 difieren más de 0.3:
  - NVO 1.96 frente a 1.11;
  - ASML 2.09 frente a 1.24;
  - HSBC 1.47 frente a 0.77;
  - UL 0.66 frente a −0.01;
  - TSM 0.95 frente a 1.43;
  - BCS 1.64 frente a 1.25.

  SHEL (0.06 frente a 0.04) y TM (0.88 frente a 0.72) no.
- **Defensivas:** con 2 años semanales salen casi nulas o negativas (JNJ −0.01, DUK −0.12, XOM −0.02, UL −0.01). La
  propuesta lleva un suelo por sector (F2_PRECEDENCIA §5).
- **What-if** con la beta de referencia:
  - **3 cambios de nivel en 35:** BRK-B (precio razonable → exigente), NVO (razonable → atractivo) y NFLX
    (confianza media → alta);
  - WACC hasta ±2.4 pp;
  - HSBC sube 7 puntos de precio (35 → 42) sin cambiar de nivel.

## 6. Efecto en el veredicto

| Escenario | Qué se sustituye | Cambios de nivel | Scores que se mueven ≥ 3 puntos |
|---|---|---|---|
| **B: solo errores de dato** | Fuente errónea, unidad, factor y periodo, por el valor de EDGAR | **0 en 35** | KO calidad 85→82; PLD calidad 82→85 y precio 46→50; DUK calidad 71→74 |
| **A: EDGAR con la tabla de conceptos tal cual** | Además, las diferencias de definición | **1:** NFLX, precio razonable → exigente y confianza media → alta. La D&A de EDGAR no lleva la amortización de contenidos y el EBITDA cae | CAT precio 39→42; RIVN calidad 29→32; y los de B |
| **Deuda con la regla de coherencia con el EBITDA** (F2_PRECEDENCIA §2.3) | Deuda total de 12 tickers de EE. UU. | **0** | DUK +3 y RIVN +3 de calidad; AMZN pasa a caja neta |
| **Beta propia** (§5) | Beta | **3:** BRK-B, NVO, NFLX | WACC hasta ±2.4 pp |

**Lectura.** Hoy, los errores de dato del panel no cambian ningún veredicto. Los riesgos para el veredicto son otros:

- **la beta;**
- **las definiciones** (D&A de NFLX), si se cambia de fuente sin alinearlas;
- **los defectos que el motor ya tapa con "sin dato":** el dividendo de 8 ADR y el falso positivo de NVDA. No cambian
  el nivel, pero quitan una métrica de la puntuación.

## 7. Límites de esta medida

- Es **un día** (fixtures del 14 y el 15-oct). Yahoo cambia según el origen (F0: Render ≠ local en 7/30), así que
  la línea base se repite en vivo en la 2b.
- La conversión del TTM en los extranjeros usa la media de 4 tipos trimestrales: hasta 0.5% de error en BCS, HSBC,
  SHEL y UL.
- **Las clasificaciones marcadas "probable"** coinciden en el valor, pero no se han leído en la nota del filing. Son:
  - las que salen de la búsqueda de la diferencia exacta (MSFT, NVDA, XOM, NEE y DOW);
  - las del dividendo con una subida.
- **"Fuente errónea" quiere decir que no está en los estados** con ninguna etiqueta estándar. Un concepto propio del
  emisor (que la API no publica) podría explicar algún caso (O, DUK; mapa, 2b).

## Anexo. Filas fuera de tolerancia (sin las de ratios que solo heredan)

Generado por `edgar_verify.py` (`resumen.md`). Valores en la moneda de los estados; por acción, en la clase del precio (ADR) con el factor oficial.


| Ticker | Campo | Periodo | Pipeline | EDGAR | Dif. | Fuente | Causa | Detalle |
|---|---|---|---|---|---|---|---|---|
| AAPL | dividend_per_share | ttm 2026-06-30 | 1.08 | 1.05 | +2.9% | finnhub | definición | dividendo anual indicado (último trimestral × 4) frente a pagado TTM |
| MSFT | depreciation | ttm 2026-06-30 | 4.345e+10 | 3.43e+10 | +26.7% | yfinance_statements | definición | Yahoo suma amortizaciones que MSFT etiqueta con un concepto propio; EDGAR solo publica la depreciación (34.3 mil millones en FY2026) |
| MSFT | total_debt | instant 2026-06-30 | 5.683e+10 | 4.029e+10 | +41.0% | yfinance_statements | definición | probable: EDGAR + OperatingLeaseLiabilityNoncurrent (la diferencia coincide al 0.5%) |
| MSFT | dividend_per_share | ttm 2026-06-30 | 3.92 | 3.64 | +7.7% | finnhub | periodo | dividendo indicado con una subida declarada después del último trimestre de EDGAR (+7.7%; probable, no verificable aún en EDGAR) |
| KO | operating_income | ttm 2026-06-30 | 1.594e+10 | 1.485e+10 | +7.3% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.594e+10; fuente yfinance_statements |
| KO | cash | instant 2026-06-30 | 1.637e+10 | 1.353e+10 | +21.0% | yfinance_statements | definición | probable: EDGAR + MarketableSecurities (la diferencia coincide al 0.5%) |
| KO | FY0.operating_income | FY 2025 | 1.491e+10 | 1.376e+10 | +8.3% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.491e+10; fuente yfinance_statements |
| KO | FY1.operating_income | FY 2024 | 1.402e+10 | 9.992e+09 | +40.3% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.402e+10; fuente yfinance_statements |
| PG | total_debt | instant 2026-06-30 | 3.503e+10 | 3.414e+10 | +2.6% | yfinance_statements | definición | deuda con arrendamientos operativos |
| PG | dividend_per_share | ttm 2026-06-30 | 4.354 | 4.259 | +2.2% | finnhub | periodo | dividendo indicado con una subida declarada después del último trimestre de EDGAR (+2.2%; probable, no verificable aún en EDGAR) |
| JNJ | dividend_per_share | ttm 2026-06-30 | 5.36 | 5.24 | +2.3% | finnhub | definición | dividendo anual indicado (último trimestral × 4) frente a pagado TTM |
| JNJ | FY0.capital_expenditure | FY 2025 | 5.217e+09 | 4.832e+09 | +8.0% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 5.217e+09; fuente yfinance_statements |
| JNJ | FY1.capital_expenditure | FY 2024 | 6.207e+09 | 4.424e+09 | +40.3% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 6.207e+09; fuente yfinance_statements |
| JPM | revenue | ttm 2026-06-30 | 1.949e+11 | 1.994e+11 | -2.3% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.949e+11; fuente yfinance_statements |
| JPM | eps | ttm 2026-06-30 | 24.15 | 23.34 | +3.5% | derivado | definición | BPA derivado: beneficio total / acciones de portada |
| JPM | dividend_per_share | ttm 2026-06-30 | 6.6 | 6 | +10.0% | finnhub | periodo | dividendo indicado con una subida declarada después del último trimestre de EDGAR (+10.0%; probable, no verificable aún en EDGAR) |
| JPM | FY1.revenue | FY 2024 | 1.694e+11 | 1.776e+11 | -4.6% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.694e+11; fuente yfinance_statements |
| BAC | cash | instant 2026-03-31 | 2.499e+11 | 2.425e+11 | +3.0% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 2.499e+11; fuente yfinance_statements |
| BAC | long_term_debt | instant 2026-03-31 | 3.008e+11 | 3.26e+11 | -7.7% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.008e+11; fuente yfinance_statements |
| BAC | eps | ttm 2026-06-30 | 4.509 | 4.33 | +4.1% | finnhub | fuente errónea | Finnhub 4.509 no es ningún TTM de EDGAR: a junio 4.33 diluido y 4.40 básico; con el 3T-2026 del 8-K del 14-oct (0.91; ajustado 1.08) en lugar del 3T-2025 (1.06), 4.18 y 4.35 |
| PGR | cash | instant 2026-06-30 | 1.355e+10 | 2.171e+09 | +524.2% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.355e+10; fuente yfinance_statements |
| PGR | dividend_per_share | ttm 2026-06-30 | 0.4 | 13.9 | -97.1% | finnhub | definición | dividendo anual indicado (último trimestral × 4) frente a pagado TTM |
| V | operating_income | ttm 2026-06-30 | 2.919e+10 | 2.7e+10 | +8.1% | yfinance_statements | definición | probable: EDGAR + LossContingencyLossInPeriod (la diferencia coincide al 0.5%) |
| V | cash | instant 2026-06-30 | 1.379e+10 | 1.236e+10 | +11.6% | yfinance_statements | definición | probable: EDGAR + Investments (la diferencia coincide al 0.5%) |
| V | dividend_per_share | ttm 2026-06-30 | 2.68 | 0.67 | +300.0% | finnhub | definición | dividendo indicado = 0.67 × 4 = 2.68. El TTM de EDGAR (0.67) no es fiable: V etiqueta el acumulado del año con el importe de un trimestre |
| V | FY0.operating_income | FY 2025 | 2.656e+10 | 2.399e+10 | +10.7% | yfinance_statements | definición | probable: EDGAR + LossContingencyLossInPeriod (la diferencia coincide al 0.5%) |
| V | FY1.operating_income | FY 2024 | 2.406e+10 | 2.36e+10 | +2.0% | yfinance_statements | periodo | fy 2025 (FY 2025-09-30) |
| BRK-B | revenue | fy 2025 | 4.105e+11 | 3.714e+11 | +10.5% | yfinance_statements | definición | probable: EDGAR + GainLossOnInvestments (la diferencia coincide al 0.5%) |
| BRK-B | cash | instant 2026-06-30 | 3.655e+11 | 4.136e+10 | +783.7% | yfinance_statements | definición | probable: EDGAR + EquitySecuritiesFvNi (la diferencia coincide al 0.5%) |
| BRK-B | FY0.revenue | FY 2025 | 4.105e+11 | 3.714e+11 | +10.5% | yfinance_statements | definición | probable: EDGAR + GainLossOnInvestments (la diferencia coincide al 0.5%) |
| BRK-B | FY1.revenue | FY 2024 | 4.242e+11 | 3.714e+11 | +14.2% | yfinance_statements | definición | probable: EDGAR + EquitySecuritiesFvNiGainLoss, GainLossOnInvestments (la diferencia coincide al 0.5%) |
| O | revenue | ttm 2026-06-30 | 5.97e+09 | 6.055e+09 | -1.4% | yfinance_statements | periodo | ttm 2026-03-31 (FY 2025-12-31 + 89d a 2026-03-31 − 89d a 2025-03-31) |
| O | total_debt | instant 2026-06-30 | 3.118e+10 | 2.925e+10 | +6.6% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.118e+10; fuente yfinance_statements |
| PLD | operating_income | ttm 2026-06-30 | 3.532e+09 | 5.029e+09 | -29.8% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.532e+09; fuente yfinance_statements |
| PLD | interest_expense | ttm 2026-06-30 | 1.019e+09 | 1.049e+09 | -2.9% | yfinance_statements | periodo | ttm 2026-03-31 (FY 2025-12-31 + 89d a 2026-03-31 − 89d a 2025-03-31) |
| PLD | long_term_debt | instant 2026-06-30 | 3.593e+10 | 3.644e+10 | -1.4% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.593e+10; fuente yfinance_statements |
| PLD | eps | ttm 2026-06-30 | 4.393 | 4.49 | -2.2% | derivado | definición | BPA derivado: beneficio total / acciones medias del FY |
| PLD | shares_outstanding | dei | 9.503e+08 | 9.331e+08 | +1.8% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 9.503e+08; fuente yfinance_statements |
| PLD | FY0.operating_income | FY 2025 | 3.414e+09 | 4.358e+09 | -21.7% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.414e+09; fuente yfinance_statements |
| PLD | FY1.operating_income | FY 2024 | 3.098e+09 | 4.416e+09 | -29.8% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.098e+09; fuente yfinance_statements |
| AMT | operating_income | ttm 2026-06-30 | 4.985e+09 | 4.902e+09 | +1.7% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 4.985e+09; fuente yfinance_statements |
| AMT | total_debt | instant 2026-06-30 | 4.498e+10 | 3.719e+10 | +20.9% | yfinance_statements | definición | deuda con arrendamientos operativos |
| AMT | FY0.operating_income | FY 2025 | 4.929e+09 | 4.846e+09 | +1.7% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 4.929e+09; fuente yfinance_statements |
| AMT | FY1.operating_income | FY 2024 | 4.603e+09 | 4.516e+09 | +1.9% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 4.603e+09; fuente yfinance_statements |
| NEE | revenue | ttm 2026-06-30 | 2.87e+10 | 2.63e+10 | +9.1% | yfinance_statements | definición | etiqueta us-gaap:RegulatedAndUnregulatedOperatingRevenue (FY 2025-12-31 + 180d a 2026-06-30 − 180d a 2025-06-30) |
| NEE | operating_income | ttm 2026-06-30 | 8.135e+09 | 8.559e+09 | -5.0% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 8.135e+09; fuente yfinance_statements |
| NEE | depreciation | ttm 2026-06-30 | 7.246e+09 | 6.84e+09 | +5.9% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 7.246e+09; fuente yfinance_statements |
| NEE | dividend_per_share | ttm 2026-06-30 | 2.493 | 2.389 | +4.3% | finnhub | definición | dividendo anual indicado (último trimestral × 4) frente a pagado TTM |
| NEE | FY0.revenue | FY 2025 | 2.741e+10 | 2.58e+10 | +6.2% | yfinance_statements | definición | etiqueta us-gaap:RegulatedAndUnregulatedOperatingRevenue (FY 2025-12-31) |
| NEE | FY1.revenue | FY 2024 | 2.475e+10 | 2.35e+10 | +5.3% | yfinance_statements | definición | etiqueta us-gaap:RegulatedAndUnregulatedOperatingRevenue (FY 2024-12-31) |
| NEE | FY0.operating_income | FY 2025 | 8.02e+09 | 8.28e+09 | -3.1% | yfinance_statements | definición | probable: EDGAR − DisposalGroupNotDiscontinuedOperationGainLossOnDisposal (la diferencia coincide al 0.5%) |
| NEE | FY1.operating_income | FY 2024 | 7.127e+09 | 7.479e+09 | -4.7% | yfinance_statements | definición | probable: EDGAR − DisposalGroupNotDiscontinuedOperationGainLossOnDisposal (la diferencia coincide al 0.5%) |
| DUK | revenue | ttm 2026-06-30 | 3.325e+10 | 3.257e+10 | +2.1% | yfinance_statements | definición | etiqueta us-gaap:RegulatedAndUnregulatedOperatingRevenue (FY 2025-12-31 + 180d a 2026-06-30 − 180d a 2025-06-30) |
| DUK | operating_income | ttm 2026-06-30 | 8.85e+09 | 9.227e+09 | -4.1% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 8.85e+09; fuente yfinance_statements |
| DUK | total_debt | instant 2026-06-30 | 9.221e+10 | 9.124e+10 | +1.1% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 9.221e+10; fuente yfinance_statements |
| DUK | FY0.revenue | FY 2025 | 3.224e+10 | 3.174e+10 | +1.6% | yfinance_statements | definición | etiqueta us-gaap:RegulatedAndUnregulatedOperatingRevenue (FY 2025-12-31) |
| DUK | FY1.revenue | FY 2024 | 3.036e+10 | 3.005e+10 | +1.0% | yfinance_statements | definición | etiqueta us-gaap:RegulatedAndUnregulatedOperatingRevenue (FY 2024-12-31) |
| XOM | revenue | ttm 2026-06-30 | 3.611e+11 | 3.688e+11 | -2.1% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.611e+11; fuente yfinance_statements |
| XOM | FY0.revenue | FY 2025 | 3.239e+11 | 3.322e+11 | -2.5% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.239e+11; fuente yfinance_statements |
| XOM | FY1.revenue | FY 2024 | 3.392e+11 | 3.496e+11 | -3.0% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.392e+11; fuente yfinance_statements |
| FCX | operating_income | ttm 2026-06-30 | 6.19e+09 | 6.923e+09 | -10.6% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 6.19e+09; fuente yfinance_statements |
| FCX | total_debt | instant 2026-06-30 | 1.036e+10 | 9.386e+09 | +10.4% | yfinance_statements | definición | deuda con arrendamientos operativos |
| CAT | capex | ttm 2026-06-30 | 4.575e+09 | 2.871e+09 | +59.4% | yfinance_statements | definición | capex + PaymentsToAcquireEquipmentOnLease |
| CAT | dividend_per_share | ttm 2026-06-30 | 6.52 | 6.16 | +5.8% | finnhub | periodo | dividendo indicado con una subida declarada después del último trimestre de EDGAR (+5.8%; probable, no verificable aún en EDGAR) |
| CAT | FY0.capital_expenditure | FY 2025 | 4.286e+09 | 2.821e+09 | +51.9% | yfinance_statements | definición | capex + PaymentsToAcquireEquipmentOnLease |
| CAT | FY1.capital_expenditure | FY 2024 | 3.215e+09 | 1.988e+09 | +61.7% | yfinance_statements | definición | capex + PaymentsToAcquireEquipmentOnLease |
| MU | long_term_debt | instant 2026-05-31 | 3.052e+09 | 5.14e+09 | -40.6% | yfinance_statements | definición | probable: EDGAR − FinanceLeaseLiabilityNoncurrent (la diferencia coincide al 0.5%) |
| MU | total_debt | instant 2026-05-31 | 6.376e+09 | 5.722e+09 | +11.4% | yfinance_statements | definición | deuda con arrendamientos operativos |
| MU | eps | ttm 2026-05-31 | 74.21 | 44.24 | +67.7% | finnhub | periodo | ttm 2026-08-30 (FY 2026-09-03) |
| MU | dividend_per_share | ttm 2026-05-31 | 0.6 | 0.495 | +21.2% | finnhub | definición | dividendo anual indicado (último trimestral × 4) frente a pagado TTM |
| DOW | cash | instant 2026-06-30 | 3.736e+09 | 3.973e+09 | -6.0% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 3.736e+09; fuente yfinance_statements |
| DOW | long_term_debt | instant 2026-06-30 | 1.608e+10 | 1.715e+10 | -6.2% | yfinance_statements | definición | probable: EDGAR − LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree, AvailableForSaleSecuritiesDebtMaturitiesAfterOneThroughFiveYearsFairValue (la diferencia coincide al 0.5%) |
| DOW | total_debt | instant 2026-06-30 | 1.943e+10 | 1.791e+10 | +8.5% | yfinance_statements | definición | deuda con arrendamientos operativos |
| DOW | eps | ttm 2026-06-30 | -1.783 | -1.83 | +2.6% | derivado | definición | BPA derivado: beneficio total / acciones de portada |
| DOW | FY1.capital_expenditure | FY 2024 | 3.065e+09 | 2.94e+09 | +4.3% | yfinance_statements | definición | probable: EDGAR + PaymentsToAcquireBusinessesNetOfCashAcquired (la diferencia coincide al 0.5%) |
| NVDA | cash | instant 2026-07-31 | 6.247e+10 | 2.244e+10 | +178.3% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 6.247e+10; fuente yfinance_statements |
| NVDA | total_debt | instant 2026-07-31 | 3.835e+10 | 3.337e+10 | +14.9% | yfinance_statements | definición | probable: EDGAR + OperatingLeaseLiabilityNoncurrent (la diferencia coincide al 0.5%) |
| NVDA | dividend_per_share | ttm 2026-07-31 | 1 | 0.28 | +257.1% | finnhub | definición | dividendo anual indicado (último trimestral × 4) frente a pagado TTM |
| CRWD | operating_income | ttm 2026-07-31 | -1.195e+08 | -1.33e+08 | +10.1% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da -1.195e+08; fuente yfinance_statements |
| CRWD | net_income | ttm 2026-07-31 | 5.846e+07 | 4.5e+07 | +29.9% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 5.846e+07; fuente yfinance_statements |
| CRWD | capex | ttm 2026-07-31 | 4.94e+08 | 4.079e+08 | +21.1% | yfinance_statements | definición | capex + PaymentsToDevelopSoftware |
| CRWD | total_debt | instant 2026-07-31 | 8.202e+08 | 7.462e+08 | +9.9% | yfinance_statements | definición | deuda con arrendamientos operativos |
| CRWD | FY0.diluted_eps | FY 2026 | -0.1625 | -0.65 | +75.0% | yfinance_statements | periodo | split 4:1 posterior al filing (Yahoo ya lo aplica) |
| CRWD | FY1.diluted_eps | FY 2025 | -0.02 | -0.06 | +66.7% | yfinance_statements | periodo | split 3:1 posterior al filing (Yahoo ya lo aplica) |
| CRWD | FY0.capital_expenditure | FY 2026 | 3.709e+08 | 3.021e+08 | +22.8% | yfinance_statements | definición | capex + PaymentsToDevelopSoftware |
| CRWD | FY1.capital_expenditure | FY 2025 | 3.138e+08 | 2.549e+08 | +23.1% | yfinance_statements | definición | capex + PaymentsToDevelopSoftware |
| CRWD | FY0.ordinary_shares | FY 2026 | 1.013e+09 | 2.546e+08 | +298.1% | yfinance_statements | periodo | split 4:1 posterior al filing (Yahoo ya lo aplica) |
| CRWD | FY1.ordinary_shares | FY 2025 | 9.915e+08 | 2.492e+08 | +297.8% | yfinance_statements | periodo | split 4:1 posterior al filing (Yahoo ya lo aplica) |
| RIVN | total_debt | instant 2026-06-30 | 5.353e+09 | 4.444e+09 | +20.5% | yfinance_statements | definición | deuda con todos los arrendamientos |
| RIVN | shares_outstanding | dei | 1.448e+09 | 1.362e+09 | +6.3% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.448e+09; fuente yfinance_statements |
| SNOW | capex | ttm 2026-07-31 | 5.977e+07 | 5.798e+07 | +3.1% | yfinance_statements | definición | capex + PaymentsToAcquireIntangibleAssets |
| SNOW | FY0.capital_expenditure | FY 2026 | 1.047e+08 | 1.016e+08 | +3.1% | yfinance_statements | definición | capex + PaymentsToAcquireIntangibleAssets |
| SNOW | FY1.capital_expenditure | FY 2025 | 7.571e+07 | 4.628e+07 | +63.6% | yfinance_statements | definición | capex + PaymentsToDevelopSoftware |
| TSM | FY0.retained_earnings | FY 2025 | 4.641e+12 | 5.039e+12 | -7.9% | yfinance_statements | definición | utilidades no asignadas: sin la reserva legal ni la especial, que RetainedEarnings de la 20-F sí incluye (diferencia 398 mil millones de TWD) |
| TSM | FY1.retained_earnings | FY 2024 | 3.562e+12 | 3.873e+12 | -8.0% | yfinance_statements | definición | utilidades no asignadas: sin la reserva legal ni la especial, que RetainedEarnings de la 20-F sí incluye (diferencia 398 mil millones de TWD) |
| ASML | FY0.capital_expenditure | FY 2025 | 1.631e+09 | 1.574e+09 | +3.7% | yfinance_statements | definición | capex + PaymentsToAcquireIntangibleAssets |
| NVO | interest_expense | fy 2025 | 4.207e+09 | 6.778e+09 | -37.9% | yfinance_statements | definición | etiqueta ifrs-full:InterestExpense (FY 2025-12-31) |
| NVO | FY0.capital_expenditure | FY 2025 | 9.011e+10 | 6.014e+10 | +49.8% | yfinance_statements | definición | capex + PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities |
| NVO | FY1.capital_expenditure | FY 2024 | 5.131e+10 | 4.716e+10 | +8.8% | yfinance_statements | definición | capex + PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities |
| NFLX | depreciation | ttm 2026-06-30 | 1.767e+10 | 3.724e+08 | +4644.3% | yfinance_statements | definición | Yahoo suma la amortización de contenidos (≈17 mil millones), que NFLX etiqueta con un concepto propio; EDGAR solo publica la D&A de inmovilizado |
| AMZN | total_debt | instant 2026-03-31 | 2.099e+11 | 1.228e+11 | +70.9% | yfinance_statements | definición | deuda total etiquetada + arrendamientos operativos |
| BCS | revenue | ttm 2026-06-30 | 3.075e+10 | 1.138e+10 | +170.3% | yfinance_statements | definición | ingresos totales del banco (margen de intereses + comisiones + resto); EDGAR no los etiqueta: RevenueFromContractsWithCustomers son solo comisiones |
| BCS | dividends_paid | fy 2025 | 2.251e+09 | 1.254e+09 | +79.5% | yfinance_statements | definición | con cupones AT1 (beneficio de los propietarios − del accionista ordinario) |
| BCS | cash | instant 2026-06-30 | 2.459e+11 | 2.751e+11 | -10.6% | yfinance_statements | definición | el valor está en EDGAR con otra etiqueta: CashAndBankBalancesAtCentralBanks |
| BCS | total_debt | instant 2026-06-30 | 1.379e+11 | 1.268e+11 | +8.7% | yfinance_statements | definición | deuda con pasivos subordinados |
| BCS | eps | ttm 2026-06-30 | 2.314 | 1.932 | +19.8% | derivado | definición | BPA derivado: beneficio total / acciones actuales (capitalización / precio × factor oficial) |
| BCS | dividend_per_share | ttm 2026-06-30 | 8.568 | 0.3363 | +2447.4% | finnhub | unidad + factor ADR | ×100 (peniques/céntimos) y por acción ordinaria (sin ×4) |
| BCS | shares_outstanding | dei | 3.333e+09 | 3.467e+09 | -3.9% | yfinance_statements | periodo | acciones de hoy tras las recompras (capitalización / precio = 13,331 millones de ordinarias) frente a la portada del 20-F a 2025-12-31 (13,867); la media del 1S-2026 ya es 13,645. El factor 4.154 del motor sale de este desfase |
| BCS | FY0.revenue | FY 2025 | 2.914e+10 | 1.111e+10 | +162.3% | yfinance_statements | definición | ingresos totales del banco (margen de intereses + comisiones + resto); EDGAR no los etiqueta: RevenueFromContractsWithCustomers son solo comisiones |
| BCS | FY1.revenue | FY 2024 | 2.623e+10 | 1.071e+10 | +144.9% | yfinance_statements | definición | ingresos totales del banco (margen de intereses + comisiones + resto); EDGAR no los etiqueta: RevenueFromContractsWithCustomers son solo comisiones |
| BCS | FY0.ordinary_shares | FY 2025 | 3.333e+09 | 3.467e+09 | -3.9% | yfinance_statements | factor ADR | factor del motor 4.154 en vez del oficial 4 |
| BCS | FY1.ordinary_shares | FY 2024 | 3.467e+09 | 3.605e+09 | -3.8% | yfinance_statements | factor ADR | factor del motor 4.154 en vez del oficial 4 |
| HSBC | net_income | ttm 2026-06-30 | 2.549e+10 | 2.601e+10 | -2.0% | yfinance_statements | definición | beneficio atribuido a la dominante (ProfitLoss − minoritarios) |
| HSBC | capex | fy 2025 | 4.661e+09 | 1.447e+09 | +222.1% | yfinance_statements | definición | capex + PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities |
| HSBC | dividends_paid | fy 2025 | 1.158e+10 | 1.348e+10 | -14.1% | yfinance_statements | definición | el valor está en EDGAR con otra etiqueta: DividendsPaidOrdinaryShares |
| HSBC | cash | instant 2026-06-30 | 2.278e+11 | 4.243e+11 | -46.3% | yfinance_statements | definición | el valor está en EDGAR con otra etiqueta: CashAndBankBalancesAtCentralBanks |
| HSBC | total_debt | instant 2026-06-30 | 1.329e+11 | 1.05e+11 | +26.5% | yfinance_statements | definición | deuda con pasivos subordinados |
| HSBC | dividend_per_share | ttm 2026-06-30 | 55.67 | 3.75 | +1384.5% | finnhub | unidad + factor ADR | Finnhub 55.67 = peniques por acción ordinaria (línea de Londres), leído como USD por ADR. En USD por ADR: 0.5567 GBP × 1.34 × 5 ≈ 3.73 (DPA pagado de 2025 en EDGAR: 0.66 USD × 5 = 3.30) |
| HSBC | FY0.net_income | FY 2025 | 2.228e+10 | 2.313e+10 | -3.7% | yfinance_statements | definición | beneficio atribuido a la dominante (ProfitLoss − minoritarios) |
| HSBC | FY1.net_income | FY 2024 | 2.398e+10 | 2.5e+10 | -4.1% | yfinance_statements | definición | beneficio atribuido a la dominante (ProfitLoss − minoritarios) |
| HSBC | FY0.capital_expenditure | FY 2025 | 4.661e+09 | 1.447e+09 | +222.1% | yfinance_statements | definición | capex + PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities |
| HSBC | FY1.capital_expenditure | FY 2024 | 3.886e+09 | 1.344e+09 | +189.1% | yfinance_statements | definición | capex + PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities |
| SHEL | interest_expense | ttm 2026-06-30 | 5.134e+09 | 5.064e+09 | +1.4% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 5.134e+09; fuente yfinance_statements |
| SHEL | depreciation | ttm 2026-06-30 | 2.287e+10 | 2.511e+10 | -8.9% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 2.287e+10; fuente yfinance_statements |
| SHEL | long_term_debt | instant 2025-12-31 | 4.219e+10 | 6.652e+10 | -36.6% | yfinance_statements | definición | probable: préstamos a largo plazo (66,515 millones de USD, que en IFRS incluyen arrendamientos) sin la parte no corriente de los arrendamientos (≈ 24,300 = 28,933 de arrendamientos totales − la corriente). SHEL solo etiqueta el total |
| SHEL | dividend_per_share | ttm 2026-06-30 | 112.8 | 2.836 | +3877.7% | finnhub | unidad + factor ADR | Finnhub 112.82 = peniques por acción ordinaria (Londres). En USD por ADR: 1.1282 GBP × 1.34 × 2 ≈ 3.02 (EDGAR: 1.432 USD × 2 = 2.86) |
| UL | operating_income | fy 2025 | 1.013e+10 | 9.037e+09 | +12.1% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.013e+10; fuente yfinance_statements |
| UL | interest_expense | fy 2025 | 1.098e+09 | 1.024e+09 | +7.2% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.098e+09; fuente yfinance_statements |
| UL | capex | fy 2025 | 1.591e+09 | 1.417e+09 | +12.3% | yfinance_statements | definición | capex + PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities |
| UL | cash | instant 2026-06-30 | 5.871e+09 | 6.048e+09 | -2.9% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 5.871e+09; fuente yfinance_statements |
| UL | long_term_debt | instant 2025-12-31 | 2.409e+10 | 2.57e+10 | -6.2% | yfinance_statements | definición | el valor está en EDGAR con otra etiqueta: NoncurrentPortionOfNoncurrentBondsIssued |
| UL | total_debt | instant 2025-12-31 | 2.76e+10 | 2.604e+10 | +6.0% | yfinance_statements | definición | deuda con arrendamientos (IFRS 16) |
| UL | dividend_per_share | fy 2025 | 146 | 2.028 | +7097.1% | finnhub | unidad + factor ADR | Finnhub 164.99 = peniques por acción ordinaria (Londres). En USD por ADR: 1.6499 GBP × 1.34 ≈ 2.21 (EDGAR: 2.03 EUR × 1.13 = 2.29) |
| UL | FY0.operating_income | FY 2025 | 1.013e+10 | 9.037e+09 | +12.1% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.013e+10; fuente yfinance_statements |
| UL | FY1.operating_income | FY 2024 | 1.028e+10 | 8.829e+09 | +16.4% | yfinance_statements | fuente errónea | ningún valor de EDGAR (periodo, etiqueta, unidad, factor) da 1.028e+10; fuente yfinance_statements |
| UL | FY0.capital_expenditure | FY 2025 | 1.591e+09 | 1.417e+09 | +12.3% | yfinance_statements | definición | capex + PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities |
| UL | FY1.capital_expenditure | FY 2024 | 1.614e+09 | 1.381e+09 | +16.9% | yfinance_statements | definición | capex + PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities |
| UL | FY1.ordinary_shares | FY 2024 | 2.201e+09 | 2.476e+09 | -11.1% | yfinance_statements | periodo | consolidación de acciones con la escisión de helados (8 por 9: 2,452 millones a 2025-06-30 → 2,180 a 2025-12-31); Yahoo la aplica a 2024 (2,476 × 8/9 = 2,201) |
| TM | shares_outstanding | dei | 1.178e+09 | 1.303e+09 | -9.6% | yfinance_statements | fuente errónea | Yahoo: capitalización / precio = 1,178 millones de ADR = 11,778 millones de acciones, frente a 13,034 en circulación en el 20-F (2026-03-31) y en la portada. De ahí el factor implícito 11.07 frente al oficial 10 |
| TM | FY0.ordinary_shares | FY 2026 | 1.178e+09 | 1.303e+09 | -9.6% | yfinance_statements | factor ADR | factor del motor 11.07 en vez del oficial 10 |
| TM | FY1.ordinary_shares | FY 2025 | 1.179e+09 | 1.305e+09 | -9.6% | yfinance_statements | factor ADR | factor del motor 11.07 en vez del oficial 10 |
