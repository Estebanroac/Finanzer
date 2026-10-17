# F3 · Punto de parada 1b (T1b): capa de datos, primer deploy de la fase

> Fase 3 del plan de fiabilidad. Rama `fiabilidad/f3-metodo` (worktree `../finanzer_next-f3`). Implementa lo aprobado
> en la parada 1 (registro #25). **Nada subido.** Medidas del 2026-10-16 (Nueva York, 21:00–23:00).

## 0. Resumen

| | T0 | Ahora | Comando |
|---|---|---|---|
| F1, con las definiciones aprobadas | 91.4% (1290/1411) | **94.9% (1339/1411)** | `tests/edgar_verify.py --whatif --out <dir>` |
| F1, sin cambiar las definiciones de la herramienta | 91.4% | 93.5% (1319/1411) | `tests/edgar_verify.py --sin-definiciones-f3 --out <dir>` |
| Cambios de nivel en el panel (37) | — | **1:** BRK-B calidad excelente → sólida | `tests/panel_run.py --mode replay --compare <T0>` |
| Suite (sin golden) | 3663 passed | todo en verde salvo los golden y las muestras forzadas del contrato | `pytest tests -q --ignore=tests/test_regression.py` |
| Golden | — | **66 cambian** (análisis + PDF de los dos juegos): pendientes de tu aprobación (§3) | `pytest tests/test_regression.py` |
| Latencia en frío (local, red real, mediana de 12) | 3.06 s | **3.05 s** | `tests/perfil_local.py --red-local …` (§4) |

**Lo que te pido:**

1. aprobar los golden, causa por causa (§3);
2. el EBITDA (§5, decisión nueva, no la tomo yo);
3. poner **`SEC_EDGAR_USER_AGENT` en Render**. Sin ella no hay deploy (requisito del prompt). Hoy producción sigue
   con EDGAR desactivado;
4. el "ok, pushea" del primer deploy de la fase.

## 1. Qué se hizo (un commit por decisión, tests antes)

| Commit | Qué | Tipo |
|---|---|---|
| `d34c858` | **EBIT de EDGAR como fuente principal:** el resultado operativo que presenta el emisor, en el corte y en las filas anuales. Bancos: no aplica. Sin el periodo en EDGAR (20-F sin trimestres: TSM, NVO, ASML, TM, SHEL), el de la fuente sin verificar | de fondo |
| `7685a1b` + `a997ee2` | **Ingresos de EDGAR** en aseguradoras y conglomerados (BRK-B: sin ganancias de inversión) y en bancos de EE. UU. (ingresos netos totales). El arreglo normaliza la industria como el clasificador ("Insurance—Diversified") | de fondo |
| `5043eca` | **Capex de EDGAR con financiera cautiva** (CAT: sin el equipo que arrienda Cat Financial). El FCF se recalcula | de fondo |
| `84fc641` | **Historia anual larga** (10+ ejercicios): ingresos, EBIT, beneficio, BPA y acciones diluidos, OCF y capex, encadenando etiquetas (ASC 606) y, en ingresos y BPA, el cambio de norma de TM (declarado). Caché en memoria LRU de 64 emisores por tipo y semáforo de lecturas grandes (1 a la vez). El juego f2b se amplía con la historia desde la caché local de la 2a | de fondo |
| `0d48d11` | **Arreglo destapado:** el cambio de perímetro (2b) marcaba reexpresiones de 2015–2017 fuera de la serie del motor. **Ya pasaba en producción:** el companyfacts vivo trae toda la historia | de fondo |
| `090f38b` | **Arreglo destapado:** el "último informe anual" de un componente de la deuda (2b) buscaba hacia atrás sin límite (BAC: deuda subordinada de 2012; ASML: arrendamiento operativo de 2023). Latente en producción | de fondo |
| `3b16823` | **Crecimiento en la moneda de los estados:** interanual, CAGR y ciclo medio sin el tipo de cambio; `growth_currency` declara las dos cifras y el efecto divisa. La valoración sigue en dólares | de fondo |
| `78fa695`, `0f85a69` | **Herramienta F1** con las definiciones aprobadas (capex, caja, ingresos de utilities, deuda de la regla). Mismas tolerancias y causas; `--sin-definiciones-f3` reproduce la medida anterior | herramienta |

Ninguna protección provisional nueva.

## 2. F1: 94.9%, a 2 filas del 95%

Por campo (dentro / comparables), T0 → ahora:

| Campo | T0 | Ahora | Por qué |
|---|---|---|---|
| Beneficio operativo (TTM y FY) | 47/68 | **68/68** | EBIT de EDGAR |
| Capex TTM | 19/23 | **23/23** | Definición (software e intangibles) y CAT |
| Capex FY0/FY1 | 42/58 | 53/58 | Ídem. Quedan JNJ (Yahoo +8% y +40%, sin componente que lo explique), DOW y otros |
| Ingresos (TTM y FY) | 79/98 | 90/98 | BRK-B y bancos de EE. UU. de EDGAR; utilities con su concepto. Quedan BCS (sin etiqueta estándar de "total income"), XOM (sin etiqueta de "ventas de explotación": −2 a −3%), JPM (−2.3%) y O (periodo) |
| Deuda total | 16/25 | 18/25 | Deuda de la regla frente a la de la regla. Quedan bancos IFRS (BCS, HSBC), UL, O (hipotecas), AMZN (−2.7%), AAPL y NEE (1–1.5%) |
| Caja | 22/31 | 22/31 | Bancos y aseguradoras con su caja reportada, más KO, V y NVDA, a los que les faltan los valores negociables del corte en el extracto de la 2a |

**Las 72 filas que siguen fuera:**

| Causa | Filas |
|---|---|
| Definición | 33 |
| Fuente errónea | 25 |
| Periodo | 13 |
| Unidad + factor ADR | 2 |

Las mayores:

- dividendo indicado frente al declarado: 15 filas, por diseño de la 2b;
- caja de financieras: 6;
- bancos IFRS (BCS, HSBC): sin etiquetas estándar;
- D&A de NFLX (contenidos) y MSFT: definición, sin decidir.

No toqué tolerancias ni causas para llegar al 95%. Lo que falta tiene destino:

- definición del D&A y del EBITDA: §5;
- bancos IFRS: T4;
- el resto: casos de fuente documentados.

## 3. Golden: diff causa por causa · **aprobación que te pido**

Panel (37) frente a T0, solo lo que mueve puntuaciones (el resto es procedencia: `data_provenance.edgar.primary`,
`.history`, `growth_currency`, `fields.*.source`):

| Ticker | Cambio | Causa |
|---|---|---|
| **BRK-B** | **calidad 81 → 71 (excelente → sólida)** | Ingresos sin ganancias de inversión: CAGR de ingresos a 3 años **20.6% → 7.1%** (Crecimiento 20 → 12) |
| KO | calidad 85 → 82 (Solidez 19 → 17) | EBIT reportado (14,854 frente a 15,941 de Yahoo, que excluía otros cargos operativos): cobertura de intereses más baja |
| PLD | calidad 82 → 85 (Solidez 12 → 14); precio 46 → 50 | EBIT reportado (5,029 frente a 3,532: PLD incluye las ganancias de promoción): cobertura de intereses más alta |
| CAT | precio 39 → 42; DCF −65.8% → −57.1% | Capex sin el equipo arrendado de Cat Financial: FCF más alto |
| NVO | calidad 88 → 85 (Crecimiento 17 → 15); DCF +59.3% → +41.9% | Crecimiento en DKK (6.4% interanual frente a 11.1% en USD; CAGR 20.4% frente a 23.1%) |
| TSM | DCF −59.3% → −56.6% | Crecimiento en TWD (CAGR 18.9% frente a 17.1% en USD) |
| **UL** | **precio 46 → 54** (nivel sin cambio); DCF −44.9% → −54.4% | Crecimiento en EUR (CAGR −5.6% frente a −3.4% en USD). Con él, el DCF deja de conciliar con el precio y **sale del score**: antes restaba como "claramente cara". Es el caso de un solo método (D3): el DCF inverso de T3 lo resuelve |
| TM | calidad 59 → 61; precio 65 → 69; DCF +12.8% → +49.3% | Crecimiento en JPY (CAGR 10.9% frente a 7.0% en USD: el yen se depreció). El supuesto de §3 de la parada 1 (tipo de cambio sin tendencia) pesa aquí; lo anoto para T3 (sensibilidad) |
| JNJ | sin cambio de puntuación | El perímetro ya no declara la reexpresión del FY2021, fuera de su serie |
| BAC, ASML | sin cambio de puntuación | La deuda deja de traer componentes de 2012 y 2023 |
| JPM (juego local) | crecimiento de ingresos 7.3% → 2.8% | Ingresos netos totales de EDGAR. Yahoo quitaba la ganancia de 2024 por las acciones de Visa (test de la rama bancaria actualizado con la cifra de EDGAR) |

Con tu aprobación:

- `tests/diff_golden.py --regenerate --yes` (los dos juegos);
- `tests/contract_forced.py --write`;
- la suite en verde.

## 4. Latencia y memoria (local, red real, frente al código de T0)

`tests/perfil_local.py --red-local HD PEP MCD LOW COST TGT` (los 6 de la 2b), con EDGAR activo (User-Agent del
Llavero), alternando el código de T0 (checkout principal) y el de T1b, dos rondas cada uno:

| | T0 | T1b |
|---|---|---|
| En frío, red real (12 análisis) | 2.77–3.56 s, **mediana 3.06 s** | 2.93–3.81 s, **mediana 3.05 s** |
| En caliente | 0.001–0.003 s | 0.001–0.003 s |
| RSS máximo del proceso (12 en replay + 12 PDF + 6 en red) | 252 / 266 MB | 256 / 257 MB |

- **Sin penalización medible.** La historia ya llegaba con la descarga de la 2b: T1b solo conserva más conceptos.
- El pico de memoria de leer un companyfacts grande (80–116 MB, F3_T1_PARADA1 §2.2) queda acotado a uno a la vez por
  el semáforo.
- **En Render**, tras el deploy, hay que mirar el log de memoria; te pediré que me lo muestres.

## 5. Decisión nueva que no tomo yo: el EBITDA

Con el EBIT de EDGAR, el EBITDA sigue siendo el de Yahoo: su EBIT con lo no operativo y sus ajustes, más la D&A.
En KO, Yahoo construye un EBIT 1,087 millones más alto que el reportado, y su EBITDA lo arrastra. Lo usan:

- EV/EBITDA;
- deuda neta / EBITDA;
- la regla de deuda de la 2b;
- el FFO de los REIT (EBITDA − EBIT = D&A).

| Opción | Qué es |
|---|---|
| (a) **EBITDA = EBIT reportado + D&A** | Recomendada. Coherente con el EBIT aprobado; el FFO de los REIT no cambia, porque la D&A es la misma |
| (b) EBITDA de Yahoo | Como hoy, declarado como "de la fuente" |

La D&A de NFLX (con o sin amortización de contenidos) y la de MSFT son la misma pregunta de definición. Recomiendo
cerrarlas a la vez, en el T3 (DCF).

## 6. Tras tu aprobación (registro #27)

### 6.1 Golden de T1b: regenerados

Commit `2d56466`. Después, los dos `diff_golden.py` salen sin diferencias y `pytest tests -q` da "3701 passed,
1 skipped".

### 6.2 EBITDA = EBIT que presenta el emisor + D&A (`76747c8`) · **diff que te pido aprobar**

- Las **ratios** (EV/EBITDA, deuda neta / EBITDA) ya se calculaban así (`financial_ratios`: EBIT + D&A) con el EBIT de
  EDGAR. Por eso **no cambian**.
- Lo que cambia:
  - la **cifra de EBITDA mostrada**, que era la de Yahoo, en 20 análisis. Por ejemplo: KO 19,831 → 15,888;
    AMZN 188,438 → 155,861 (Yahoo sumaba otros ingresos); NVDA 233,894 → 201,266; MSFT 212,433 → 198,685;
    CRWD 437 → 200 millones;
  - las **filas anuales**, y con ellas el EV/EBITDA de ciclo medio de las cíclicas. TM pasa de 7.8x a 9.5x (el
    EBITDA medio de Yahoo para TM era 53.4 frente a 43.5 billones de JPY con el EBIT que presenta) y su **precio
    baja de 69 a 65**, sin cambio de nivel. MU, FCX y ASML se mueven menos de 1x;
  - el EBITDA de RIVN y SNOW (pre-beneficio): −2,139 → −2,714 y −813 → −984 millones;
  - **FFO anual de los REIT** = beneficio + D&A, la misma definición que el TTM. Con el nuevo EBITDA, "EBITDA − EBIT
    de Yahoo" dejaba de ser la D&A. En el panel coincide con lo anterior en O, PLD y AMT (sin cambios).
- **Cambios de nivel en el panel: ninguno.** Los golden de este cambio están **sin regenerar** hasta tu aprobación
  (`pytest tests/test_regression.py` → "50 failed"; el resto de la suite, en verde salvo las muestras forzadas del
  contrato).

### 6.3 Tasas base: tabla oficial completa (`97c8c6b`)

- **Fuente:** Mauboussin y Callahan, *The Impact of Intangibles on Base Rates* (Morgan Stanley, Counterpoint Global,
  23-jun-2021), Exhibit 3, pp. 6–8. Russell 3000, 1984–2020, crecimiento nominal.
- **Qué trae:** mediana, media y desviación del CAGR de ventas a 1, 3, 5 y 10 años, por 7 tramos de ventas
  (en USD de 2020) y 5 industrias de Fama-French (más el total), con el número de observaciones.
- Extraída por programa a `config/base_rates.toml`. **Integridad comprobada:** los tramos suman el universo y las
  industrias suman el total en cada horizonte (test).
- Es lo que pide F3_DISENO §8.1 (tramo de tamaño, horizonte de 10 años). Los dos PDF de febrero y mayo de 2026 solo
  traían dos histogramas.
- **Limitación, de los propios autores:** la distribución no es normal (cola a la derecha). Las bandas del DCF
  inverso (cuántas desviaciones son "exigente" o "excepcional") se calibran y se te presentan en la T3.
- El paso de industria a código SIC (Fama-French, de la biblioteca de Kenneth French) también es de la T3.
