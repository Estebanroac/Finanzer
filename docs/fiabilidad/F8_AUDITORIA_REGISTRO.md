# F8 · Registro de la Fase A (auditoría externa del 26-oct-2026)

> Plan: `docs/superpowers/plans/2026-10-26-fiabilidad-auditoria-externa.md`. Auditoría:
> `docs/fiabilidad/auditoria-externa-2026-10-26.txt`. Rama `fiabilidad/f8-auditoria` (worktree e4), desde `a0e824f`.
> Cambios de veredicto, causa por causa: `GOLDEN_DIFF_F8.md`.
>
> Regla del usuario para toda la fase: presupuesto 0. Solo fuentes gratuitas y fiables (EDGAR/XBRL, Damodaran, FDIC,
> Finnhub gratuito y Yahoo como respaldo conciliado). Lo que necesite datos de pago queda «sin dato», declarado.

## Cómo se toma la evidencia

- **Con datos reales:** `backend/tools/f8_evidencia.py --tag <corrida>` analiza en vivo las 26 empresas de la
  auditoría con las claves del Llavero. Guarda cada análisis comprimido en `docs/fiabilidad/f8_evidencia/<corrida>/`;
  `--show` lee de ahí sin red.
  - Corrida «antes»: código de `a0e824f`, 27-oct a las 02:39 UTC.
  - Corrida «e1»: 27-oct a las 03:10 UTC. Las dos son de la noche del 26-oct en Nueva York, después del cierre, con
    los mismos precios.
- **Replay (tests):** las 26 de la auditoría.
  - 12 ya estaban en el panel.
  - 13 se graban para F8 en `backend/tests/fixtures/f8/` (comprimidos, 6 MB; capturados el 27-oct UTC con Render
    simulado y verificados byte a byte contra la corrida en vivo; sin `token=`).
  - LIN queda fuera: el capturador no reproduce la historia de EDGAR de su predecesora (Praxair). Es un fallo del
    capturador, no del motor; queda anotado como pendiente.
- **Afirmaciones §6 y controles de pipeline:** `backend/tests/test_f8_referencia.py`. Cada error de la Fase A añade
  las suyas.

## E1 · Ke y beta con controles de cordura

### Evidencia (antes de tocar)

Reproducido con datos reales en las tres empresas de la auditoría y en NEE:

| Empresa | Beta usada | Ke | Kd | Lo que dice la auditoría |
|---|---|---:|---:|---|
| AWK | propia −0,44 (R² 0,112; Blume 0,04) | 5,14 % | 5,88 % | Ke < Kd; P/B justificado «barata» |
| XOM | media de la industria 0,30 (Oil/Gas Integrated) | 6,25 % | 5,39 % | Ke = Rf + 1,3 pp |
| CB | media de la industria 0,48 (Insurance Prop/Cas.) | 7,00 % | — | P/TBV justificado inflado |
| NEE | media de la industria 0,48 (Power) | 7,00 % | 7,74 % | (no la cita en E1: también Ke < Kd) |

- **Rf:** el del día (^TNX 4,986 % el 26-oct) junto a la ERP implícita de Damodaran del 1-oct (4,20 %), que se
  calculó con un Rf del 5,29 %. Son fechas mezcladas, como dice la auditoría.
- **Fuente de la beta:** 13 de 26 usan la propia y 13 la media de la industria. La regla (R² ≥ 0,10) no se ve en el
  informe.
- **Error estándar:** la regresión propia no lo calculaba (`market_signals.beta`). Calculado ahora, con 104 semanas va
  de 0,10 a 0,42 en el panel. Ejemplos: FCX 0,256 con R² 0,30; PLTR 0,416; MU 0,385.

### Corrección

Reglas en el motor y umbrales en config, sin excepciones por ticker:

- **Error estándar de la beta propia** (`lib/market_signals.py`): √(Σ residuos² / (n − 2) / Σ (r_m − media)²).
- **Una regla visible para la fuente de la beta** (`lib/beta.py`, `market.beta_choice`). El análisis la lleva en
  `beta.rule` y el motivo en `beta.reason`.
  - **Beta propia,** solo si pasa los tres filtros:
    - R² ≥ 0,20;
    - error estándar ≤ 0,25: con 2 × EE ≤ 0,5, el intervalo del 95 % no es más ancho que el umbral de discrepancia
      entre fuentes;
    - beta bruta entre 0,4 y 2,5.

    Si falla alguno, se descarta y el motivo lo dice (`beta.discarded`).
  - **Si no, la de abajo hacia arriba.** Es la βU de la industria de Damodaran: «Unlevered beta corrected for cash»,
    enero de 2026, tabla nueva `[unlevered]` de `config/betas.toml` con 96 industrias.
    - Se reapalanca con la D/E de mercado (deuda financiera / capitalización) y la t de la empresa:
      βL = βU × [1 + (1 − t) × D/E].
    - Entra sin Blume (`beta.relevered`).
    - Las financieras (arquetipo FINANCIAL) no se reapalancan, porque su deuda es materia prima: usan la beta media
      de su industria.
    - Si la D/E de la empresa supera 3 veces la de su industria (`relever_max_de_ratio`), la estructura no es
      comparable. Ocurre con la deuda de una financiera cautiva: TM, 1,20 frente a 0,20, daba β 2,56 y Ke 16 %. En
      ese caso entra la beta media de la industria, declarado. En el panel, el resto queda por debajo de 1,8 veces.
  - **Sin industria en la tabla:** la de la fuente, con el aviso «sin verificar», como antes.
- **Un solo Ke por análisis, con dos pisos** (`cost_of_capital.equity_cost`):
  - Ke = máx(CAPM, Rf + 0,5 × ERP, Kd + 1 pp); el piso de Kd solo con deuda;
  - el mismo Ke va al WACC, al P/B justificado (FINANCIAL y UTILITY) y al DCF del REIT;
  - antes, el P/B justificado calculaba su propio Ke sin piso;
  - el análisis lo publica en `cost_of_equity` (valor, CAPM, piso que manda, Kd, Rf, ERP y fecha).
- **Rf y ERP del mismo día** (`cost_of_capital.capm_rates`, `valuation.capm.pair_as_of`):
  - el Ke, el Kd y el WACC usan el par de Damodaran del 1-oct-2026 (Rf 5,29 %, ERP 4,20 %);
  - el ^TNX del día queda como referencia (`risk_free.market`);
  - si se aleja del par más de 0,5 pp, el análisis avisa de que hay que actualizar el par (hoy está a 0,30 pp:
    sin aviso).
- **Prueba de sensibilidad** (`lib/ke_sensitivity.py`, `valuation.capm.ke_sensitivity_pp` = 1 pp).
  - El análisis se repite con Ke − 1 pp y Ke + 1 pp. El desplazamiento entra en el único Ke, así que lo recogen el
    DCF, el DCF inverso, el spread ROIC − WACC y el P/B justificado.
  - Las repeticiones paran en el veredicto y usan los datos en caché. El análisis en vivo sigue tardando 1,4–3,8 s
    por empresa, igual que antes.
  - Si el nivel de precio cambia, el veredicto es «dependiente de Ke»: la confianza baja un escalón, el precio
    mostrado se recalcula con ella, y el motivo va en la confianza y en la frase del veredicto.
  - Un fallo de la prueba no bloquea el análisis: queda sin dato.
- **Textos del informe** (`lib/display.py`):
  - la nota del WACC dice qué piso manda y con qué CAPM;
  - dice con qué D/E se reapalanca la beta;
  - dice que Rf y prima implícita son del mismo día;
  - el desglose añade la fila del piso;
  - la tarjeta pasa de «Beta del sector» a «Beta de la industria».

### Resultado con datos reales (26 empresas)

Ke y WACC suben unos 0,30 pp en todas por el Rf del par (5,29 % frente a 4,99 %), además de lo que cambie la beta.

| Ticker | Beta antes | Beta E1 | Ke antes | Ke E1 (piso) | Kd E1 | WACC antes → E1 | Nivel con Ke − 1 pp / base / + 1 pp | Veredicto antes (confianza) | Veredicto E1 (confianza) |
|---|---|---|---:|---:|---:|---|---|---|---|
| MSFT | propia 1,09 | propia 1,09 | 9,55 % | 9,85 % | 5,69 % | 9,41 % → 9,71 % | exigente / exigente / exigente | excelente · exigente (media) | excelente · exigente (media) |
| NVDA | propia 1,58 | propia 1,58 | 11,61 % | 11,92 % | 5,69 % | 11,57 % → 11,87 % | atractivo / razonable / razonable **dep.** | excelente · razonable (media) | excelente · razonable (baja) |
| LLY | industria 0,98 | industria 0,96 | 9,10 % | 9,30 % | 5,69 % | 8,88 % → 9,08 % | exigente / exigente / muy exigente **dep.** | excelente · exigente (alta) | excelente · exigente (media) |
| UNH | industria 0,87 | industria 0,87 | 8,64 % | 8,93 % | 5,99 % | 8,01 % → 8,30 % | atractivo / razonable / razonable **dep.** | media · razonable (media) | media · razonable (baja) |
| JPM | propia 1,05 | propia 1,05 | 9,41 % | 9,72 % | — | — | razonable / razonable / exigente **dep.** | excelente · razonable (alta) | excelente · razonable (media) |
| CB | industria 0,48 | industria 0,48 | 7,00 % | 7,39 % (Rf + 0,5 × ERP) | — | — | atractivo / razonable / razonable **dep.** | excelente · razonable (media) | excelente · razonable (baja) |
| AMZN | propia 1,34 | propia 1,34 | 10,63 % | 10,94 % | 5,69 % | 10,33 % → 10,63 % | exigente / exigente / exigente | media · exigente (alta) | media · exigente (alta) |
| MCD | industria 0,92 | industria 0,93 | 8,85 % | 9,18 % | 5,84 % | 7,99 % → 8,30 % | razonable / razonable / razonable | excelente · exigente (media) | excelente · **razonable** (media) |
| GOOGL | propia 1,16 | propia 1,16 | 9,85 % | 10,15 % | 5,69 % | 9,71 % → 10,01 % | exigente / exigente / exigente | excelente · exigente (media) | excelente · exigente (media) |
| VZ | industria 0,63 | industria 0,65 | 7,63 % | 8,02 % | 6,18 % | 6,13 % → 6,44 % | atractivo / atractivo / atractivo | sólida · atractivo (alta) | sólida · atractivo (alta) |
| CAT | propia 1,06 | propia 1,06 | 9,43 % | 9,74 % | 5,69 % | 9,26 % → 9,56 % | exigente / muy exigente / muy exigente **dep.** | excelente · exigente (media) | excelente · exigente (baja) |
| UNP | propia 0,65 | industria 0,92 | 7,73 % | 9,14 % | 5,84 % | 7,22 % → 8,46 % | muy exigente ×3 | sólida · muy exigente (alta) | sólida · muy exigente (alta) |
| KO | industria 0,64 | industria 0,63 | 7,67 % | 7,95 % | 5,69 % | 7,36 % → 7,63 % | exigente / muy exigente / muy exigente **dep.** | excelente · muy exigente (alta) | excelente · muy exigente (media) |
| WMT | industria 0,81 | industria 0,82 | 8,39 % | 8,72 % | 5,69 % | 8,15 % → 8,47 % | muy exigente ×3 | excelente · muy exigente (alta) | excelente · muy exigente (alta) |
| XOM | industria 0,30 | industria 0,29 | 6,25 % | 7,39 % (Rf + 0,5 × ERP) | 5,69 % | 6,13 % → 7,22 % | razonable / exigente / exigente **dep.** | excelente · razonable (baja) | excelente · razonable (baja) |
| KMI | industria 0,67 | industria 0,63 | 7,80 % | 7,92 % | 6,18 % | 6,83 % → 6,99 % | exigente / muy exigente / exigente **dep.** | media · exigente (alta) | media · **muy exigente** (media) |
| NEE | industria 0,48 | industria 0,50 | 7,00 % | 9,04 % (Kd + 1 pp) | 8,04 % | 6,99 % → 8,32 % | exigente ×3 | sólida · razonable (media) | sólida · **exigente** (media) |
| AWK | propia 0,04 | industria 0,40 | 5,14 % | 7,39 % (Rf + 0,5 × ERP) | 6,18 % | 6,00 % → 6,47 % | exigente / muy exigente / muy exigente **dep.** | sólida · exigente (media) | sólida · **muy exigente** (media) |
| PLD | propia 0,82 | propia 0,82 | 8,41 % | 8,72 % | 6,07 % | 7,68 % → 7,97 % | razonable ×3 | sólida · razonable (alta) | sólida · razonable (alta) |
| O | industria 0,62 | industria 0,67 | 7,59 % | 8,08 % | 6,67 % | 6,92 % → 7,33 % | razonable ×3 | media · razonable (media) | media · razonable (media) |
| LIN | industria 0,97 | industria 0,90 | 9,06 % | 9,05 % | 5,69 % | 8,54 % → 8,56 % | muy exigente ×3 | excelente · muy exigente (alta) | excelente · muy exigente (alta) |
| FCX | propia 1,45 | industria 1,08 | 11,09 % | 9,83 % | 5,69 % | 10,41 % → 9,29 % | exigente ×3 | sólida · exigente (media) | sólida · exigente (media) |
| ASML | propia 1,16 | propia 1,16 | 9,87 % | 10,18 % | 5,69 % | 9,85 % → 10,16 % | muy exigente ×3 | excelente · muy exigente (media) | excelente · muy exigente (media) |
| SAP | propia 0,98 | propia 0,98 | 9,11 % | 9,41 % | 5,69 % | 8,89 % → 9,19 % | exigente ×3 | excelente · exigente (alta) | excelente · exigente (alta) |
| MRNA | industria 1,14 | industria 1,09 | 9,77 % | 9,85 % | 6,40 % | 9,74 % → 9,82 % | sin nivel de precio | débil · sin dato (media) | débil · sin dato (media) |
| BA | propia 1,36 | propia 1,36 | 10,69 % | 10,99 % | 8,50 % | 9,84 % → 10,14 % | sin nivel de precio | débil · sin dato (baja) | débil · sin dato (baja) |

**Resumen:**

- Fuente de la beta: 10 propias que pasan los filtros y 16 de su industria.
  - Descartadas: AWK (R² y signo), UNP (R² 0,11) y FCX (error estándar 0,256).
- Pisos: el de medio mercado manda en AWK, XOM y CB; el de Kd + 1 pp, en NEE.
- Nivel de precio: cambia en 4 de 26 (AWK, NEE, KMI y MCD). La causa de cada uno está en `GOLDEN_DIFF_F8.md`; la de
  MCD es la regla de fiabilidad del DCF que mira el precio, y la corrige E8.
- Dependientes de Ke: 10 de 24 con nivel de precio. La confianza baja en 9; XOM ya estaba en baja.
- Afirmación §6 «AWK Ke ≥ Kd»: se cumple, 7,39 % frente a 6,18 %.

### Tests

- `tests/test_f8_e1.py`, 26 tests:
  - error estándar contra la fórmula de MCO;
  - filtros de la beta propia con los casos MSFT, AWK y FCX, beta fuera de rango y caché antigua sin error estándar;
  - reapalancamiento con D/E de mercado, con la D/E de la industria si falta la capitalización, financieras sin
    reapalancar y D/E no comparable (TM);
  - pisos del Ke, Ke único en el WACC y desplazamiento acotado a su contexto;
  - par Rf–ERP y aviso de desfase;
  - prueba de sensibilidad: dependiente, estable, ya en baja y fallo sin bloqueo.
- `tests/test_f8_referencia.py`, 8 tests sobre las 25 del replay:
  - Ke ≥ Kd + 1 pp;
  - Ke ≥ Rf + 0,5 × ERP;
  - β en [0,4; 2,5] o de su industria;
  - g terminal ≤ Rf;
  - un solo Ke y par Rf–ERP con fecha;
  - AWK Ke ≥ Kd;
  - XOM y CB con piso y dependientes de Ke;
  - regla de la beta visible en todas.
- Tests existentes ajustados a la regla nueva, cada uno con su motivo:
  - `test_beta_t6`: la de abajo hacia arriba gana a la de la fuente; DUK reapalancada; la discrepancia se comprueba
    en ASML, porque PLTR tiene EE 0,42;
  - `test_known_bugs` (NFLX: Ke único);
  - `test_cost_of_capital` (par con fecha en el replay);
  - `test_validation` (procedencia de la beta de NFLX);
  - `test_panel_run` y `panel_run.py`: lo que cambia con el día es la lectura de mercado, no el Rf;
  - `test_config_literals`: el «2» de n − 2.
- No regresión de lo que la auditoría da por bueno (§2): no se toca el método por tipo de empresa, Blume en la beta
  propia, la tabla de rating sintético, la tasa efectiva, ni la financiera cautiva en la deuda (CAT, DE). La suite
  completa lo cubre (resultado abajo).

**Resultado de las pruebas:**

- Backend: 5642 tests pasan y 5 se omiten (suite completa, con golden, PDF v2 y contratos forzados regenerados).
- Frontend:
  - vitest de /v2: 146 pasan (fixtures de /v2 regenerados desde el replay);
  - `tsc`, `npm run check` y lint: sin errores; siguen los 4 avisos antiguos.
- e2e de /v2 contra el build y el replay: 807 pasan y 1 falla, el V6b de la portada (la copia del bucle se pulsa). Es
  el test inestable ya pasado a E3, que también falla en la base; no depende de E1.

### Pendiente y seguimiento

- **TM (y otros emisores no estadounidenses):** la tabla de industrias de EE. UU. de Damodaran pesa mucho a Tesla en
  Auto & Truck (βU 1,31). Damodaran publica gratis las tablas regionales (Europa, Japón, emergentes, global); usar la
  de la región del emisor es una mejora fiable y sin coste. Queda propuesta, no hecha.
- **MCD:** su cambio a «razonable» viene de la fiabilidad del DCF que mira el precio. Se revisa en E8.
- **Par Rf–ERP:** hay que actualizarlo cada mes con Damodaran. El análisis avisa si el ^TNX se aleja más de 0,5 pp.
- **LIN en el replay:** el capturador no reproduce la historia de EDGAR de su predecesora.

## E4 + E5 · Etiquetas e incoherencias de VZ; portada con la métrica normalizada

### Evidencia (antes de tocar)

Con datos reales (corrida «e1», 26-oct):

- **VZ, titular.** «Los ingresos crecen 6,8 %» es el retorno total que puntúa Crecimiento en una madura de dividendo
  alto: dividendo 6,6 % + ingresos por acción 0,2 %. El crecimiento de los ingresos es del 0,33 % (FY2022–FY2025), el
  que usa el DCF. Es un error de mapeo: `display.py` leía el `raw` del ajuste, que es el retorno total.
- **VZ, PEG.** 0,80, «muy atractivo» (+4), con el BPA en −7,1 % anual. Es el PEG de mercado de Yahoo
  (`pegRatio`): supone un crecimiento del BPA del 14 %, que el informe no muestra. En 16 de las 26, el PEG de la fuente
  no cuadra con el crecimiento del BPA del informe.
- **VZ, convergencia.** «Alta: el DCF y los múltiplos coinciden (barata)». La señal de los múltiplos (+0,40) es la
  media de un bloque en el que el P/E lee −1,00 («muy caro», +40 % sobre el sector).
- **VZ, espectro.** El FCF (20,16 mil millones) es OCF − capex. Las compras de licencias, en actividades de inversión,
  no entran. En EDGAR, VZ y TMUS las presentan en `PaymentsToAcquireIntangibleAssets`. VZ: 47,6 (2021, banda C), 3,65,
  5,8, 0,9 y 0,45 mil millones. AT&T no tiene una etiqueta separable: las incluye en adquisiciones.
- **E5, GOOGL y AMZN.** El resumen dice «15,9x beneficios, −46 %» y «20,0x, −40 %». El motor marca ese P/E como no
  fiable (49 % y 24 % no recurrente) y puntúa el normalizado, 31,4x y 26,3x. La portada (`readings.pe`), el resumen,
  la tarjeta del precio y la sección usaban la misma lectura del reportado.

### Corrección

- **Titular** (`financial_ratios.score_crecimiento`, `display.py`, `display_charts.py`, `analysis_queue.py`):
  - el ajuste de retorno total guarda aparte el crecimiento de los ingresos (`revenue_growth`) y el dividendo;
  - las lecturas, la fila «Crecimiento de ingresos», la comparación con la industria y la tabla de rivales citan ese
    crecimiento;
  - el retorno total va en su fila («Retorno total por acción (dividendo + ingresos por acción, 3 años)»), en la
    introducción de Crecimiento y en el resumen; el gráfico de crecimiento lo rotula como retorno total.
- **PEG** (`financial_ratios.peg_not_significant`, `main.py`, `score_valoracion`):
  - n.s. si el crecimiento del BPA del informe es ≤ 0;
  - n.s. si el PEG es el de la fuente y, con el crecimiento del informe, su lectura cambia de tramo (`peg_bounds`,
    los del score: sin umbral nuevo);
  - sin crecimiento del informe (AMZN, TM), el de la fuente se queda;
  - el n.s. no puntúa, no cuenta como dato ausente ni como miembro del bloque, y la tabla da el motivo.
- **Convergencia** (`valuation_confidence`, `thresholds.confidence.convergence_extreme_reading = 1.0`):
  - la señal de los múltiplos guarda la lectura de cada uno en [−1, 1] (los del bloque y los de la rama);
  - si alguno contradice la dirección común con lectura extrema, la convergencia es media, con el múltiplo y su
    lectura en el motivo, traducido al lenguaje llano.
- **Espectro** (`lib/telecom_spectrum.py`, `valuation.telecom_spectrum`, `sec_edgar.HISTORY["spectrum_purchases"]`):
  - solo para la industria «Telecom Services» de Yahoo;
  - FCF de la valoración (P/FCF, FCF yield y DCF) = FCF − media de las compras de espectro de los últimos ejercicios
    de EDGAR. Eran 5 en el commit de E4; son 10 desde el ajuste del PM (abajo, con un mínimo de 5);
  - sin suficientes ejercicios, sin ajuste y declarado («sin dato»): no se suponen ceros;
  - las filas de P/FCF y FCF yield y la base del DCF dicen la resta con sus cifras.
- **E5** (`display.read_pe`): con el P/E reportado no fiable, la lectura es la del normalizado («el mercado paga
  31,4x el beneficio normalizado…») y añade «el P/E reportado (15,9x) no es fiable: el 49 % del beneficio es no
  recurrente». La fila del P/E reportado sigue en la tabla con «No fiable», y el normalizado en la suya.

### Ventana del espectro: 10 años (desviación razonada de la auditoría, decisión del PM del 27-oct)

- **La auditoría pedía 5 años.** Con 5, la media de VZ (11,68 mil millones al año) la domina una sola subasta, la
  banda C de 2021 (45,5 de los 47,6 de ese año), y sobrestima el gasto recurrente.
- **Las subastas son irregulares:** AWS-3 en 2015, mmWave en 2019–20, banda C en 2021 y 3,45 GHz en 2022. Normalizar
  un gasto irregular pide el ciclo completo, el mismo principio que el ciclo medio de las cíclicas.
- **Regla** (`valuation.telecom_spectrum`, `years = 10`, `min_years = 5`):
  - media de los 10 últimos ejercicios con el dato en EDGAR;
  - si hay menos, los que haya, con un mínimo de 5; por debajo, sin dato declarado;
  - un ejercicio sin el dato no se cuenta como cero;
  - el texto dice cuántos años se promedian y cuáles («media de 10 años… EDGAR 2016–2025»).
- **VZ con datos reales** (corrida «e4_espectro10», 27-oct antes de la apertura, mismo precio):
  - media de 6,57 mil millones (FY2016–FY2025);
  - FCF ajustado de 13,59 mil millones, frente a 8,48 con 5 años;
  - P/FCF de 13,1x y FCF yield del 7,6 %;
  - DCF de −18 %, con fiabilidad alta;
  - veredicto «razonable», con confianza baja: convergencia media, y dependiente de Ke, porque con Ke + 1 pp pasa a
    exigente.
- **TMUS** (fuera del conjunto): 3,20 mil millones con 10 años, frente a 3,95 con 5.

### Fixture

`tests/fixtures/f8/f2b/edgar/companyfacts/CIK0000732712.json` (VZ) suma el concepto
`PaymentsToAcquireIntangibleAssets`. Sale del companyfacts de EDGAR del 27-oct, reducido con `sec_edgar.reduce_facts` y
cortado en `filed` ≤ fecha de captura. El resto del archivo no cambia y queda anotado en `metadata.json`. Sin
`token=`.

### Resultado con datos reales (corrida «e4», 27-oct antes de la apertura, mismos precios que «e1»)

| Ticker | PEG antes → E4 | Convergencia antes → E4 | Precio crudo | Veredicto antes (confianza) | Veredicto E4 (confianza) |
|---|---|---|---|---|---|
| MSFT | 1,30 → 1,30 | media → media | 35 → 35 | excelente · exigente (media) | excelente · exigente (media) |
| NVDA | 0,14 → 0,14 | media → media | 65 → 65 | excelente · razonable (baja) | excelente · razonable (baja) |
| LLY | 0,83 → 0,83 | alta → media | 35 → 35 | excelente · exigente (media) | excelente · exigente (baja) |
| UNH | 1,07 → n.s. (BPA ≤ 0) | media → media | 65 → 65 | media · razonable (baja) | media · razonable (media) |
| JPM | 1,41 → n.s. (no cuadra) | alta → alta | 45 → 45 | excelente · razonable (media) | excelente · razonable (media) |
| CB | 2,67 → n.s. (no cuadra) | media → media | 60 → 60 | excelente · razonable (baja) | excelente · razonable (baja) |
| AMZN | 1,44 → 1,44 | alta → alta | 35 → 35 | media · exigente (alta) | media · exigente (alta) |
| MCD | 2,63 → n.s. (no cuadra) | media → baja | 45 → 55 | excelente · razonable (media) | excelente · razonable (media) |
| GOOGL | 0,48 → 0,48 | media → media | 35 → 35 | excelente · exigente (media) | excelente · exigente (media) |
| VZ | 0,80 → n.s. (BPA ≤ 0) | alta → media | 80 → 40 | sólida · atractivo (alta) | sólida · exigente (media) |
| CAT | 1,20 → n.s. (no cuadra) | alta → alta | 15 → 15 | excelente · exigente (baja) | excelente · exigente (baja) |
| UNP | 2,91 → 2,91 | alta → alta | 25 → 25 | sólida · muy exigente (alta) | sólida · muy exigente (alta) |
| KO | 4,21 → n.s. (no cuadra) | alta → alta | 15 → 20 | excelente · muy exigente (media) | excelente · muy exigente (media) |
| WMT | 4,07 → n.s. (no cuadra) | alta → alta | 10 → 10 | excelente · muy exigente (alta) | excelente · muy exigente (alta) |
| XOM | 1,58 → n.s. (no cuadra) | media → media | 40 → 40 | excelente · razonable (baja) | excelente · razonable (baja) |
| KMI | 3,57 → 3,57 | alta → alta | 20 → 20 | media · muy exigente (media) | media · muy exigente (media) |
| NEE | 1,67 → n.s. (no cuadra) | media → media | 35 → 35 | sólida · exigente (media) | sólida · exigente (media) |
| AWK | 2,53 → 2,53 | alta → alta | 20 → 20 | sólida · muy exigente (media) | sólida · muy exigente (media) |
| PLD | 110,08 → n.s. (BPA ≤ 0) | alta → alta | 50 → 50 | sólida · razonable (alta) | sólida · razonable (alta) |
| O | 2,87 → n.s. (BPA ≤ 0) | media → media | 65 → 65 | media · razonable (media) | media · razonable (media) |
| LIN | 1,98 → n.s. (no cuadra) | alta → alta | 10 → 10 | excelente · muy exigente (alta) | excelente · muy exigente (alta) |
| FCX | 3,80 → n.s. (BPA ≤ 0) | media → media | 40 → 40 | sólida · exigente (media) | sólida · exigente (media) |
| ASML | 0,89 → n.s. (no cuadra) | alta → alta | 10 → 10 | excelente · muy exigente (media) | excelente · muy exigente (media) |
| SAP | 1,86 → n.s. (no cuadra) | alta → alta | 30 → 35 | excelente · exigente (alta) | excelente · exigente (alta) |
| MRNA | — → — | no_evaluable → no_evaluable | None → None | débil · sin dato (media) | débil · sin dato (media) |
| BA | 1,49 → 1,49 | no_evaluable → no_evaluable | None → None | débil · sin dato (baja) | débil · sin dato (baja) |

- **Nivel de precio:** cambia en VZ (atractivo → exigente). La causa está en `GOLDEN_DIFF_F8.md`.
- **Confianza:** baja en LLY (convergencia, Forward P/E +1,00) y sube en UNH (sin el PEG deja de depender de Ke).
- **Otros cambios entre corridas que no vienen de E4:** el P/E de LLY pasa de 42,75x a 42,94x porque Yahoo
  actualizó su BPA TTM esa noche (29,92 → 29,79). Su PEG propio pasa de 0,83 a 0,83.
- **§6, afirmaciones de la auditoría:**
  - VZ: el titular cita el 0,33 %;
  - VZ: PEG n.s.;
  - VZ: el P/E «muy caro» impide la convergencia alta;
  - VZ: el FCF resta el espectro;
  - GOOGL: la portada lee 31,4x;
  - AMZN: lee 26,3x (−22 % frente a la industria, no −40 %); en el replay, grabado otro día, es 39,9x.

### Tests

- `tests/test_f8_e4.py`, 15 tests:
  - PEG: casos VZ, UL, KO, AAPL, MSFT y AMZN; tramos del score; el n.s. no cuenta como ausente ni entra en el bloque;
  - convergencia con y sin lectura extrema contraria; lecturas por múltiplo;
  - espectro: media de 5 años, año ausente declarado, solo telecom;
  - E5: lectura del normalizado.
- `tests/test_f8_referencia.py`, 6 afirmaciones y controles nuevos sobre las 25 del replay:
  - titular de VZ;
  - ninguna lectura presenta el retorno total como crecimiento de los ingresos;
  - PEG n.s. con el BPA ≤ 0 (VZ) y ningún PEG con el BPA del informe ≤ 0;
  - ninguna convergencia alta con un múltiplo en lectura extrema contraria;
  - espectro de VZ y de ninguna otra;
  - la portada y el resumen leen el P/E normalizado cuando el reportado no es fiable.
- Ajustados:
  - `test_quality_price`: el PEG de NFLX queda n.s. con su motivo; sigue siendo un componente de Valoración;
  - motivo nuevo de convergencia traducido en `plain_language`;
  - el motivo del PEG n.s. no usa «crece», porque el guardián exige respaldo para esa palabra.
  - `test_pdf_v2_report`: KO ya no parte la nota de calidad entre las páginas 2 y 3 (su resumen es más largo y la nota
    empieza entera en la 3) y pasa a dependiente de Ke. La invariante de «(sigue)» se comprueba en las empresas con
    nota, y el caso «el DCF directo y los múltiplos coinciden» pasa a PG.

**Resultado de las pruebas:**

- Backend: 5659 tests pasan y 5 se omiten. En la suite completa fallaron 4 del PDF v2: 3 de maquetación de KO, ya
  ajustadas, y 1 de tiempo (PGR, 3,16 s con la e2e corriendo a la vez). Repetidos, los dos archivos del PDF v2 pasan
  enteros: 313 tests. Golden, PDF v2 y contratos forzados están regenerados.
- Frontend:
  - vitest de /v2: 146 pasan, con los fixtures regenerados desde el replay;
  - `tsc`, `npm run check` y lint: sin errores; siguen los 4 avisos antiguos.
- e2e de /v2 contra el build y el replay: 789 pasan y 20 fallan por tiempo agotado, con la suite del backend corriendo
  a la vez. Repetidas solas, 19 pasan y 1 se omite.

## E2 · Bandera de pico de beneficio

### Evidencia (antes de tocar)

Con datos reales (corrida «e4», 27-oct):

- **NEE.** Beneficio TTM de 11,64 mil millones (normalizado 11,58: la normalización solo quita 56 millones). FY2023–
  FY2025: 7,31, 6,95 y 6,84 mil millones, con mediana de 6,95, así que el TTM está un 67 % por encima. P/E normalizado
  de 14,9x, «atractivo» (+3) frente a 21x del sector. Forward P/E de 18,7x, un 27 % mayor que el TTM. Las dos
  condiciones de la auditoría se cumplen y el motor no lo detectaba.
- **Control.** NVDA (TTM +156 % sobre la mediana) y LLY (+173 %) cumplen (a), pero sus forward son un 50 % y un 37 %
  menores que el TTM: el mercado sí cree en ese beneficio.
- **Fuentes.** Las de siempre, con presupuesto 0. El forward es el de Yahoo (`forwardEps`, quoteSummary), sin
  consenso de pago. Los ejercicios salen de los estados anuales (`_statements_fy`).

### Corrección

- **`lib/earnings_peak.detect`**, con la regla de la auditoría y umbrales en `valuation.earnings_peak`:
  - (a) TTM > mediana de 3 ejercicios × 1,40;
  - (b) forward P/E > TTM × 1,20. Esto cubre también la otra forma de la auditoría («BPA esperado más de un 20 % por
    debajo», que equivale a un forward P/E un 25 % mayor).
- **Forward de Yahoo solo si es coherente.** El beneficio que implica (beneficio reportado × P/E TTM / forward P/E) no
  puede quedar por debajo de mín(TTM, mediana) / 3.
  - Solo se guarda ese lado: un error de escala hacia abajo activaría (b) por error, y uno hacia arriba nunca pone la
    bandera.
  - Un primer diseño con banda a los dos lados dejaba fuera forwards reales de crecimiento fuerte: MU, con 3,2 veces
    el BPA TTM en el ciclo de memoria, quedaba con bandera solo por (a).
  - Sin forward coherente, la bandera se decide solo con (a) y el motivo lo dice: «puede marcar un crecimiento
    genuino».
- **Solo donde el P/E puntúa** (no en FINANCIAL, REIT, CYCLICAL ni GROWTH_PRE_PROFIT).
- **Con bandera** (`main.py`, `score_valoracion`):
  - el P/E del score (y el E/P) es la media del P/E sobre la mediana y el forward; sin forward fiable, solo el primero;
  - el componente del P/E lleva el motivo completo y `earnings_peak: true`, y no se rotula «normalizado»;
  - el Forward P/E mide su compresión frente al TTM, no frente al P/E de la bandera, porque si no contaría el forward
    dos veces.
- **Textos:**
  - la lectura del P/E (portada y sección) es la del P/E que puntúa, con el TTM en la nota. NEE: «el mercado paga 21,8x
    un beneficio sin su pico, un +4 % frente a la referencia de su industria (21,0x); no 14,8x (TTM): beneficio
    atípico, un 67 % sobre su mediana de 3 años y forward P/E un 27 % mayor»;
  - el resumen lleva la forma corta («…; no 14,8x, con un beneficio TTM atípico»), y el detalle va en la sección y en
    el desglose;
  - las alertas lo rotulan «P/E sin el pico del beneficio»;
  - el periodo es el real: sin 4 trimestres consecutivos (UL), «último ejercicio», no «TTM». El guardián lo exige
    (`base_ttm`).
- **PDF v1, portada.** La de UL ya estaba al 0,867 de escala (mínimo 0,85). Con la nota de frontera del precio, que
  se suma a la de calidad, bajaba a 0,827. Las tarjetas de la portada llevan ahora la frontera sin su explicación
  genérica («En la frontera con «exigente» (a 2 puntos)»), que es igual en todos los informes y sigue completa en el
  resto. Con eso, UL queda en 0,864 y la página 2 en 0,871.

### Resultado con datos reales (corrida «e2», 27-oct antes de la apertura, mismos precios que «e4»)

- **Bandera:** solo NEE, con las dos condiciones. P/E del score de 14,9x a 21,8x; precio crudo de 35 a 30. Sigue
  «exigente», nivel al que la llevó E1 por el piso Kd + 1 pp.
- **Sin bandera, (a) sin (b):** NVDA y LLY. O y ASML no se miden (REIT y cíclica). GOOGL cumple (b) sin (a), porque
  la normalización ya le quitó el pico.
- **Sin cambios en las otras 25.**
- **§6 «bandera de pico en NEE»:** se cumple con datos reales. En el replay, grabado a mediados de octubre, el TTM de
  NEE queda un 31 % sobre la mediana: no llega al umbral. Por eso la afirmación de NEE va en `tests/test_f8_e2.py`, con
  sus cifras del 26-oct, y el replay comprueba las reglas en las 25.

### Tests

- `tests/test_f8_e2.py`, 7 tests:
  - NEE con las dos condiciones y su P/E;
  - NVDA sin bandera (el mercado cree en el nivel);
  - sin forward, solo (a) y declarado;
  - forward incoherente fuera;
  - umbral y casos sin datos;
  - el score usa el P/E de la bandera y la compresión frente al TTM;
  - config igual a la regla de la auditoría.
- `tests/test_f8_referencia.py`, control de pipeline sobre las 25:
  - sin (b) con forward fiable, nunca hay bandera;
  - con bandera, el componente y la lectura usan el P/E de la bandera y lo declaran;
  - NVDA y LLY cumplen (a) sin bandera.
- Ajustados por el periodo real y la portada del PDF v1: `test_f8_e2` (base anual sin «TTM»).

**Resultado de las pruebas:**

- Backend: 5677 tests pasan y 5 se omiten, con golden, PDF v2 y contratos forzados regenerados.
- Frontend:
  - vitest de /v2: 146 pasan;
  - `tsc`, `npm run check` y lint: sin errores; siguen los 4 avisos antiguos.
- e2e de /v2 contra el build y el replay: 808 pasan, 0 fallan.

## E8 · Fiabilidad del DCF por los insumos, no por el precio

### Evidencia (antes de tocar)

- **Regla vigente** (`valuation_confidence.dcf_reliability`): «baja» si la tabla de sensibilidad no contiene el precio
  y «media» si el precio queda fuera del bloque central.
- **Datos reales** (corrida «e8_antes»): MSFT, GOOGL, LIN, WMT, CAT, FCX y ASML tienen fiabilidad baja por eso, y su
  DCF «caro» no puntúa. La auditoría lo describe así.
- **Simetría.** Un DCF que ve barata una empresa y cae dentro de la tabla puntúa entero: VZ, con 5 años de espectro, y
  UNH.

### Corrección

- **`dcf_reliability`**, cuatro criterios de la auditoría; cada uno que falla resta un escalón desde «alta»:
  - (1) valor terminal > 75 % (> 85 %: baja, como antes);
  - (2) dispersión del bloque central de la tabla > 2,5 veces, o un valor ≤ 0. Desviación razonada, en
    `GOLDEN_DIFF_F8.md`: la tabla completa restaba en 30 de 33;
  - (3) coeficiente de variación del margen FCF de 5 ejercicios de EDGAR (`fcf_margin_stability`, con
    `history_10y`) > 0,33, es decir, una desviación típica mayor que un tercio de la media; o media ≤ 0. Sin 5
    ejercicios, no se evalúa y se dice en `criteria.notes`;
  - (4) banderas de datos: beta sin verificar (la de la fuente) o sin beta, y pico de beneficio (E2), un escalón entre
    todas. Los estados desfasados de E6 (otra rama) bajan la cobertura y entran por la confianza (E11), no aquí.
- **Se mantiene:** el FCF de entrada marcado o inferido da «baja», y una cíclica no pasa de «media».
- **Se informa sin efecto:** `grid_contains_price` y `central_contains_price`. La alerta del DCF sigue diciendo si el
  precio cae en la tabla.
- **El análisis guarda las cifras de cada criterio** (`criteria`).
- **Textos.** «El DCF no concilia con el precio bajo ningún supuesto razonable; no se usa en el score» pasa a «DCF de
  fiabilidad baja: no se usa en el score», y el DCF inverso sustituye al directo porque este «tiene fiabilidad baja».
  La distancia al precio la dice la convergencia.
- **PDF v1:** el resumen de la página 2 lleva la frontera en forma corta, como la portada desde E2. Con JNJ en la
  frontera de «exigente», no cabía (0,833).
- **Alerta del DCF de fiabilidad baja.** Cita el primer motivo «(y N motivos más)»; todos van en la línea «Fiabilidad
  del DCF» del informe. Con los tres motivos de DOW, el PDF v2 dejaba un hueco de 106 pt al pie de la página 16 y
  empujaba la tabla de la confianza a la siguiente.
- **Redacción más corta de los motivos (2) y (3)** («con crecimiento ± 2,5 pp y WACC ± 1 pp el valor va de…»;
  «variación 1,21 > 0,33»). La evidencia «e8» se tomó antes de estos dos cambios de redacción, que no mueven ninguna
  cifra ni ningún veredicto.

### Resultado con datos reales

Corridas «e8_antes» y «e8», seguidas, el 27-oct después de la apertura. Los precios difieren menos de un 0,4 %.

| Ticker | Fiabilidad del DCF antes → E8 | Motivo E8 | DCF | Veredicto antes (confianza, crudo) | Veredicto E8 |
|---|---|---|---:|---|---|
| MSFT | baja → alta | — | -60 % | exigente (media, 35) | exigente (media, 35) |
| NVDA | alta → media | margen FCF inestable | +2 % | razonable (baja, 60) | razonable (media, 60) |
| LLY | media → alta | — | -26 % | exigente (baja, 35) | exigente (baja, 30) |
| UNH | media → alta | — | +69 % | razonable (media, 65) | atractivo (media, 75) |
| MCD | alta → alta | — | -35 % | razonable (media, 45) | razonable (media, 45) |
| GOOGL | baja → alta | — | -81 % | exigente (media, 35) | exigente (media, 35) |
| VZ | alta → media | bloque central disperso | -19 % | razonable (baja, 45) | razonable (media, 50) |
| CAT | baja → baja | el FCF de entrada es inferido; empresa cíclica: el FCF depende de la fase del ciclo | -64 % | exigente (baja, 15) | exigente (baja, 15) |
| UNP | baja → alta | — | -60 % | muy exigente (alta, 25) | muy exigente (alta, 15) |
| KO | alta → media | margen FCF inestable | -31 % | muy exigente (media, 20) | exigente (alta, 30) |
| WMT | baja → alta | — | -76 % | muy exigente (alta, 15) | muy exigente (alta, 15) |
| XOM | media → media | empresa cíclica: el FCF depende de la fase del ciclo | -8 % | razonable (baja, 40) | razonable (baja, 40) |
| KMI | alta → media | bloque central disperso | -38 % | muy exigente (media, 20) | exigente (alta, 30) |
| LIN | baja → alta | — | -78 % | muy exigente (alta, 10) | muy exigente (alta, 10) |
| FCX | baja → media | margen FCF inestable; empresa cíclica: el FCF depende de la fase del ciclo | -73 % | exigente (media, 40) | exigente (media, 40) |
| ASML | baja → media | margen FCF inestable; empresa cíclica: el FCF depende de la fase del ciclo | -68 % | muy exigente (media, 10) | muy exigente (media, 20) |
| SAP | media → alta | — | -34 % | exigente (alta, 35) | exigente (media, 25) |

- **Nivel de precio:** cambia en UNH (razonable → atractivo), KO (muy exigente → exigente) y KMI (muy exigente →
  exigente). Las causas están en `GOLDEN_DIFF_F8.md`.
- **UNH es un efecto conocido hasta E7.** Su DCF crece con los ingresos mientras el margen cae (la auditoría lo pone
  en E7). E8 deja de ocultarlo tras la distancia al precio. Sin E7 en este reparto, queda declarado como pendiente.
- **§6, la auditoría:** MSFT, GOOGL, LIN, WMT, CAT, FCX y ASML ya no se descartan por el precio. MSFT, GOOGL, LIN y
  WMT pasan a alta; FCX y ASML, a media; CAT sigue en baja por su FCF inferido y por ser cíclica.

### Tests

- `tests/test_f8_e8.py`, 6 tests:
  - el precio nunca cambia el nivel;
  - cada criterio resta un escalón y dos dan baja;
  - valores ≤ 0;
  - el margen exige 5 ejercicios;
  - techo de media en las cíclicas;
  - config igual a la de la auditoría.
- `tests/test_f8_referencia.py`: ningún motivo de la fiabilidad habla del precio, y MSFT, GOOGL y WMT no tienen
  fiabilidad baja (LIN no está en el replay).
- Ajustados:
  - `test_cost_of_capital`: reglas nuevas; DOW es el caso de fiabilidad baja en el PDF; V tiene fiabilidad alta;
  - `test_guardian_detecta` y el guardián: el texto del DCF inverso;
  - `test_pdf_v2_report`: PLD es el caso del DCF inverso y KO el del directo, porque AAPL ya usa el directo;
  - `plain_language`: el motivo «no evaluable: DCF (fiabilidad baja)» se traduce sin citar el nivel, porque el guardián
    pide respaldo para «fiabilidad baja».
- Frontend:
  - la fixture DOW se suma a las de /v2 (`scripts/export-v2-fixtures.mjs`) como caso del DCF directo descartado;
  - `src/v2/lib/confidence.test.ts` usa DOW en lugar de AAPL.

**Resultado de las pruebas:**

- Backend: 5684 tests pasan y 5 se omiten.
- Frontend: `tsc`, `npm run check` y lint sin errores (siguen los 4 avisos antiguos). En vitest pasan 145 de 146.
- e2e de /v2: 802 pasan y 6 fallan.
  - 3 son inestables: V6b de la portada, la pantalla de carga y el sondeo de rivales. Repetidas, pasan.
  - 3 son de E3: v7 P1, P2 y P3.
- **Pendiente de E3: 1 test de vitest y 3 e2e.** Son `src/v2/components/CompanyHeader.test.tsx` (P3) y
  `e2e/v2/v7.spec.ts` (P1, P2 y P3). Los cuatro fijan el estado de AAPL con el DCF directo descartado (la línea de
  confianza, el «?» del DCF inverso en el desglose y «Banderas rojas: 0»). Con E8, el DCF de AAPL puntúa con fiabilidad
  alta. No se tocan porque son ficheros de E3: basta con apuntarlos a DOW, que ya está en las fixtures de /v2 y en el
  replay del panel. Se avisa al PM.

## E8 (ajuste del PM, 27-oct) · Criterio (5): crecimiento proyectado con el margen en caída

### Por qué

- **E8 sin el criterio (5).** El DCF de UNH (+69 %) pasaba a puntuar con fiabilidad alta y la empresa salía
  «atractiva». La auditoría (p. 4) pone a UNH entre los veredictos no utilizables: el DCF crece al 11,35 % mientras el
  margen neto cae del 6,2 % al 2,7 %.
- **El motor de crecimiento de tres impulsores (E7) es de la Fase B.** Hasta entonces, E8 tiene que reconocer que ese
  DCF no es fiable, con datos y sin mirar el precio.

### Regla (`valuation_confidence.margin_deterioration`, `thresholds.dcf_reliability`)

- **Medida:** margen operativo TTM (el neto si no hay operativo) frente a la mediana de los 5 últimos ejercicios de
  EDGAR (`history_10y`). Se mide la caída relativa y cuántos de los 4 últimos cambios anuales son bajadas.
- **Se activa** con g del DCF ≥ 0, caída ≥ 20 % (`margin_drop_min`) y al menos 3 bajadas (`margin_drop_downs`). Resta
  un escalón, con el texto «el DCF proyecta crecimiento con el margen en caída (…); supuesto no verificado hasta el DCF
  de tres impulsores».
- **Con una caída ≥ 40 %** (`margin_drop_low_mult` × 20 %), la fiabilidad pasa a baja directamente.

### Calibración: 69 casos (las 26 en vivo de la corrida «e8b» y los 43 golden)

- **Con un umbral del 30 %**, solo UNH cumple las tres condiciones (−42 %), pero el doble (60 %) la dejaba en «media».
- **Con un 20 %** sigue saltando solo UNH, y su caída supera el doble (40 %): baja.
- **El siguiente caso con 3 bajadas y g ≥ 0** cae un 6 % (XOM). TM (−26 %, 3 bajadas) no tiene DCF y JNJ (−19 %) tiene
  2 bajadas. Las empresas con margen estable no se acercan.
- **Aprobado por el PM:** 20 %, 3 de 4 bajadas, g ≥ 0, y baja directa desde el 40 %.

| Caso | Margen | Mediana 5 ej. | TTM | Caída | Bajadas (de 4) | g del DCF | ¿Salta? |
|---|---|---:|---:|---:|---:|---:|---|
| vivo:AMZN | operativo | 6,4% | 11,5% | -79,4% | 1 | sin DCF | no |
| vivo:ASML | operativo | 32,8% | 38,5% | -17,4% | 2 | 10,0% | no |
| vivo:AWK | operativo | 35,7% | 36,9% | -3,6% | 1 | sin DCF | no |
| vivo:BA | operativo | -4,6% | 4,6% | — | 2 | sin DCF | no |
| vivo:CAT | operativo | 16,5% | 17,5% | -6,2% | 2 | 0,4% | no |
| vivo:CB | neto | 17,4% | 18,1% | -4,3% | 2 | sin DCF | no |
| vivo:FCX | operativo | 27,2% | 26,8% | 1,7% | 4 | -7,4% | no |
| vivo:GOOGL | operativo | 30,6% | 33,1% | -8,4% | 2 | 12,5% | no |
| vivo:JPM | neto | 31,3% | 32,6% | -4,2% | 2 | sin DCF | no |
| vivo:KMI | operativo | 27,8% | 29,0% | -4,5% | 1 | 4,0% | no |
| vivo:KO | operativo | 25,4% | 29,6% | -16,8% | 3 | 3,7% | no |
| vivo:LIN | operativo | 24,4% | 26,5% | -8,3% | 1 | 0,6% | no |
| vivo:LLY | neto | 21,9% | 33,5% | -53,2% | 1 | 30,0% | no |
| vivo:MCD | operativo | 45,2% | 46,2% | -2,3% | 2 | 5,1% | no |
| vivo:MRNA | operativo | -61,9% | -150,2% | — | 4 | sin DCF | no |
| vivo:MSFT | operativo | 44,6% | 46,8% | -4,8% | 1 | 16,1% | no |
| vivo:NEE | operativo | 31,8% | 30,0% | 5,7% | 1 | sin DCF | no |
| vivo:NVDA | operativo | 54,1% | 65,2% | -20,5% | 2 | 30,0% | no |
| vivo:O | neto | 18,4% | 21,2% | -15,3% | 2 | sin DCF | no |
| vivo:PLD | operativo | 53,8% | 54,7% | -1,6% | 3 | sin DCF | no |
| vivo:SAP | operativo | 20,0% | 27,1% | -35,3% | 3 | 7,6% | no |
| vivo:UNH | operativo | 8,3% | 4,8% | 42,2% | 3 | 11,4% | **sí** (baja: ≥ 40 %) |
| vivo:UNP | operativo | 40,1% | 40,1% | -0,1% | 2 | -0,5% | no |
| vivo:VZ | operativo | 21,3% | 20,5% | 3,5% | 3 | 0,3% | no |
| vivo:WMT | operativo | 4,2% | 4,4% | -4,9% | 2 | 5,3% | no |
| vivo:XOM | neto | 9,6% | 9,1% | 5,8% | 3 | 0,6% | no |
| panel:AAPL | operativo | 30,3% | 33,2% | -9,5% | 1 | 1,8% | no |
| panel:AMT | operativo | 33,5% | 44,8% | -33,8% | 1 | sin DCF | no |
| panel:AMZN | operativo | 6,4% | 11,5% | -79,4% | 1 | sin DCF | no |
| panel:ASML | operativo | 32,8% | 34,8% | -6,0% | 2 | 10,0% | no |
| panel:BAC | neto | 27,0% | 26,3% | 2,5% | 3 | sin DCF | no |
| panel:BCS | neto | 62,4% | 22,3% | 64,3% | 2 | sin DCF | no |
| panel:BRK-B | neto | 24,0% | 22,3% | 6,9% | 3 | sin DCF | no |
| panel:CAT | operativo | 16,5% | 17,5% | -6,2% | 2 | 0,4% | no |
| panel:CRWD | operativo | -6,1% | -2,5% | — | 2 | 23,6% | no |
| panel:DOW | neto | 2,6% | -3,2% | 221,6% | 3 | -5,0% | no |
| panel:DUK | operativo | 24,7% | 27,8% | -12,5% | 1 | sin DCF | no |
| panel:FCX | operativo | 27,2% | 26,8% | 1,7% | 4 | -7,4% | no |
| panel:HSBC | neto | 33,9% | 32,8% | 3,1% | 1 | sin DCF | no |
| panel:JNJ | neto | 26,5% | 21,5% | 19,0% | 2 | 5,6% | no |
| panel:JPM | neto | 31,3% | 32,6% | -4,2% | 2 | sin DCF | no |
| panel:KO | operativo | 25,4% | 29,6% | -16,8% | 3 | 3,7% | no |
| panel:MC.PA | — | — | — | — | — | — | no (sin 5 ejercicios o margen ≤ 0) |
| panel:MSFT | operativo | 44,6% | 46,8% | -4,8% | 1 | 16,1% | no |
| panel:MU | operativo | 26,1% | 65,6% | -151,1% | 1 | 10,3% | no |
| panel:NEE | operativo | 31,8% | 29,8% | 6,3% | 1 | sin DCF | no |
| panel:NFLX | operativo | 20,9% | 29,7% | -42,3% | 1 | 12,6% | no |
| panel:NVDA | operativo | 54,1% | 65,2% | -20,5% | 2 | 30,0% | no |
| panel:NVO | operativo | 42,3% | 43,2% | -2,1% | 1 | 13,4% | no |
| panel:O | neto | 18,4% | 21,2% | -15,3% | 2 | sin DCF | no |
| panel:PG | operativo | 22,2% | 22,7% | -2,1% | 3 | 2,0% | no |
| panel:PGR | neto | 7,0% | 12,8% | -82,8% | 1 | sin DCF | no |
| panel:PLD | operativo | 53,8% | 54,7% | -1,6% | 3 | sin DCF | no |
| panel:PLTR | operativo | 5,4% | 42,8% | -693,8% | 0 | 30,0% | no |
| panel:RIVN | operativo | -129,4% | -60,1% | — | 0 | sin DCF | no |
| panel:SHEL | neto | 6,7% | 8,8% | -31,0% | 2 | 5,3% | no |
| panel:SNOW | operativo | -40,2% | -22,8% | — | 1 | sin DCF | no |
| panel:SPY | — | — | — | — | — | — | no (sin 5 ejercicios o margen ≤ 0) |
| panel:TM | operativo | 9,5% | 7,1% | 26,1% | 3 | sin DCF | no |
| panel:TSM | operativo | 45,7% | 56,0% | -22,6% | 1 | 25,3% | no |
| panel:UL | operativo | 17,4% | 17,9% | -2,8% | 2 | -1,1% | no |
| panel:V | operativo | 64,3% | 60,7% | 5,6% | 2 | 10,9% | no |
| panel:XOM | neto | 9,6% | 9,1% | 5,8% | 3 | 0,6% | no |
| local:FCX | operativo | 27,2% | 26,8% | 1,7% | 4 | -7,4% | no |
| local:JPM | neto | 31,3% | 32,6% | -4,2% | 2 | sin DCF | no |
| local:NFLX | operativo | 20,9% | 29,7% | -42,3% | 1 | 12,6% | no |
| local:O | neto | 18,4% | 21,2% | -15,3% | 2 | sin DCF | no |
| local:SNOW | operativo | -40,2% | -22,8% | — | 1 | sin DCF | no |
| local:V | operativo | 64,3% | 60,7% | 5,6% | 2 | 10,9% | no |

### Resultado

- **Golden:** 0 de 43 cambian. Ninguna empresa del panel ni del juego local cumple las tres condiciones.
- **Con datos reales (corrida «e8b», 27-oct a las 11:31 de Nueva York):** solo salta UNH, con fiabilidad del DCF
  baja.
  - Antes, con E8 sin el criterio (5), era «atractivo» (precio crudo 75).
  - Ahora es **«razonable»**, con confianza media (crudo 65, DCF +67 % que no puntúa).
  - En Valoración puntúa el DCF inverso.

### Tests de E3 apuntados a DOW (autorización del PM, solo tests)

- `src/v2/components/CompanyHeader.test.tsx`:
  - en AAPL ya no puntúa el DCF inverso;
  - un test nuevo con DOW comprueba el «?» del DCF inverso.
- `e2e/v2/v7.spec.ts`:
  - P1, la línea de la confianza, pasa a DOW;
  - P2, «Banderas rojas del modelo: 0», pasa a JPM, porque AAPL tiene ya una bandera roja;
  - P3 comprueba el «?» del DCF inverso en DOW.

### Tests

- `tests/test_f8_e8.py`, 3 tests:
  - UNH con sus cifras reales: baja;
  - caída moderada: −1;
  - sin activarse con margen estable, sin tendencia o con g < 0.
- `tests/test_f8_referencia.py`: UNH con fiabilidad baja y sin «atractivo».

**Resultado de las pruebas:**

- Backend: 5695 tests pasan y 5 se omiten.
- Frontend: vitest 147 de 147; `tsc`, `check` y lint sin errores.
- e2e de /v2: 806 pasan y 2 fallan. Los 2 fallos son los inestables de siempre (V6b de la portada y el sondeo de
  rivales) y pasan al repetirlos. Los de E3 apuntados a DOW y JPM pasan.

## E9 · La rentabilidad mide el capital invertido

### Evidencia (antes de tocar)

Corrida «e8», con datos reales.

| Empresa | ROIC | WACC | Diferencial | Rentabilidad |
|---|---:|---:|---:|---:|
| NEE | 4,6 % | 8,3 % | −3,8 pp | 20/20 |
| AWK | 5,6 % | 6,5 % | −0,9 pp | 19/20 |
| KMI | 6,4 % | 7,0 % | −0,6 pp | 16/20 |

- **VZ** tenía 20/20 con un diferencial de +1,7 pp. Tras E1 ya no destruye valor, pero su ROE (15,2 %) va con un D/E de
  1,59.
- **Los márgenes puntúan con umbrales absolutos.** El 30 % de NEE es «excepcional» y en Power (21,5 %) es 1,4 veces la
  industria. El 4,4 % de WMT es «bajo» y en Retail (General) (6,8 %) es 0,65 veces.

### Corrección (`score_rentabilidad`, `thresholds.score.rentabilidad`)

- **Tope por el diferencial ROIC − WACC:** 10/20 si es < 0; 6/20 si es < −3 pp (`spread_caps`). El desglose lleva la
  fila «Tope por ROIC − WACC» con su motivo. Sin WACC interpretable (FINANCIAL), no hay tope.
- **Márgenes frente a la industria de Damodaran** de su referencia (`benchmark.values`, la misma de los múltiplos):
  veces el margen de la industria, con bandas en config. Sin margen de la industria, o con uno ≤ 0, las bandas
  absolutas, declaradas.
  - **Desviación razonada:** el percentil de la auditoría exige la distribución por empresa, que los datos gratuitos
    no traen.
  - **Ajuste del PM (27-oct): en puntos porcentuales, no en ratio.** La ratio se amplificaba con márgenes de industria
    pequeños: UNH pasaba de 9 a 20 con el margen hundido un 42 % (4,8 % frente al 3,0 % de Healthcare Support
    Services, 1,6 veces). Ahora la diferencia es margen − agregado de la industria, con tramos en config
    (`operating_margin_vs_industry_pp` = +15 / +5 / −2 / −8 pp; `net_margin_vs_industry_pp` = +12 / +4 / −3 pp),
    tomados de los cuantiles de 69 casos.
    - Se descartó la ratio con suelo en el denominador: añade un parámetro arbitrario y por encima del suelo se sigue
      amplificando.
    - UNH queda en 15/20 y calidad media. WMT 15; MSFT, NVDA y KO 20. Detalle en `GOLDEN_DIFF_F8.md`.
- **ROE con apalancamiento alto:** con un D/E (contable) por encima de `debt_equity_high` de su sector, puntúa el ROIC
  en el sitio del ROE, con las mismas bandas («ROIC (en lugar del ROE: apalancamiento alto)»), y el motivo cita el ROE
  y el D/E.

### Resultado con datos reales (corridas «e9_antes» y «e9», seguidas)

- **Rentabilidad:** NEE 20 → 6; AWK 19 → 10; KMI 16 → 10; VZ 20 → 14.
- **Calidad:** NEE pasa de sólida a media, VZ de sólida a media, y AMZN y UNH de media a sólida.
- **Ningún nivel de precio cambia.** Detalle por empresa en `GOLDEN_DIFF_F8.md`.
- **§6, la auditoría:** «destruye valor» y «rentabilidad excelente» ya no conviven: el control de pipeline lo comprueba
  en las 25.

### Tests

- `tests/test_f8_e9.py`, 12 tests tras el ajuste. Incluye los casos del PM (UNH, WMT, MSFT, KO y NVDA) y la prueba de
  cordura (margen bajo en industria baja nunca por encima de margen alto en industria alta, a igual diferencia
  relativa). Antes:
  - tope de 6/20 (NEE) y de 10/20 (AWK); sin tope con diferencial positivo o sin WACC;
  - márgenes frente a la industria (NEE en Power, WMT) y bandas absolutas sin dato;
  - ROE → ROIC con D/E alto;
  - config igual a la de la auditoría.
- `tests/test_f8_referencia.py`: con diferencial < 0, Rentabilidad ≤ 10; con < −3 pp, ≤ 6.
- Ajustados por el guardián (`periodo_roe`: una cifra de ROE exige su periodo): el motivo del cambio de ROE por ROIC
  no cita la cifra del ROE. Por `test_coverage`, con D/E alto el sitio es del ROIC también cuando falta el ROE: un dato
  ausente no puntúa distinto de uno presente.

**Resultado de las pruebas:**

- Backend: 5691 tests pasan y 5 se omiten.
- Frontend: vitest 145 de 146; `tsc`, `check` y lint sin errores.
- e2e de /v2: 805 pasan y 3 fallan. El fallo de vitest y los 3 de e2e son los tests de E3 que fijaban AAPL con el DCF
  descartado (pendiente de E8; el PM autorizó apuntarlos a DOW en el ajuste de E8).

## Pendiente anotado para E11 (PM, 27-oct)

- La rama de correcciones independientes cerró E6 en `3a575d14`: los estados desfasados bajan la cobertura a «media»,
  con su motivo. AMZN sigue con confianza «alta» y cobertura «media», porque la regla actual lo permite.
- En E11, «la más baja manda» incluye la cobertura: la confianza final nunca supera a la cobertura, venga de donde
  venga la bajada.
- Debe ser genérico, sin leer `data_provenance.staleness`, para que funcione al fusionar las ramas.
- Test con una cobertura «media» simulada.

## E11 · La más baja manda, contracción de la calidad y saturación

- **Verificado con datos reales** (corrida «e11_antes», en 996cd7be):
  - MRNA tiene cobertura baja y confianza «media»: lo permitía el tope `weak_dimension_cap = "media"`.
  - XOM tiene confianza baja y calidad 79 sin contraer (82 en la auditoría, antes de E9).
  - 13 de 26 tienen calidad de 80 o más (14 en la auditoría) y GOOGL está en 100.
- **Corregido:**
  - **La más baja manda**, sobre las dimensiones evaluadas (la cobertura incluida). Es genérico, como pidió el PM: no
    lee `data_provenance.staleness`. Hay test con una cobertura «media» simulada.
  - **Contracción de la calidad ×0,85** con confianza baja (`verdict.contract_quality`). Es idempotente y la aplica
    también la comprobación de Ke.
  - **«Excelente» desde 85.** Antes de tocarlo se comprobó, como pidió el PM, que E9 y la contracción no bastan: con
    80, «excelente» pasa solo del 47 % al 43 % de 68 casos. Con 85 (p75), el 25 %.
  - **El codo de la persistencia se separa** en `quality_persistence.knee = 80`, para que el cambio sea solo de
    etiqueta.
- **Detalle** (pasaje de la auditoría, distribución antes y después, golden y datos reales) en `GOLDEN_DIFF_F8.md`.
- **Herramienta:** `tools/f8_quality_bands.py`, que saca la distribución de niveles y los cuantiles sin red.
- **El «Pendiente anotado para E11»** de abajo queda resuelto.

## E10 (peso de Altman en el score)

- **Fuente:** Altman, Iwanicz-Drozdowska, Laitinen y Suvas (2017), *Financial Distress Prediction in an International
  Context: A Review and Empirical Analysis of Altman's Z-Score Model*, Journal of International Financial Management
  & Accounting 28(2). La auditoría la cita así: «precisión de alrededor de 0,75». Fuera de la muestra original el
  poder discriminante del Z ronda un AUC de 0,75.
- **Regla, aprobada por el PM:** peso × (2·AUC − 1) = × 0,5, de modo que `altman_points` pasa de [6, −2, −6] a
  [3, −1, −3], el mismo peso que la cobertura de intereses.
  - Está en config con su origen.
  - La neutralidad de «referencial», «no aplica» y «sin dato» no cambia.
  - El runway conserva su peso: no es un modelo estadístico.
- **Solidez en los 69 casos:** en el techo de 20, de 21 a 16. Positivo de 34 a 39, aviso de 7 a 8, negativo de 6 a 5.
  - En calidad solo cambia de nivel PG, de excelente a sólida (85 → 82).
  - En vivo, ningún cambio de nivel.
- **Detalle:** en `GOLDEN_DIFF_F8.md`. Herramienta: `tools/f8_solidez_bands.py`.
- **Lo demás de E10** (variante por SIC, exclusiones de midstream, utilities, REIT y financieras con sustituto) va en
  `fiabilidad/f8-independientes`.

## Pausa del 26-oct (noche): por dónde iba (resuelta el 27-oct: E4+E5 cerrado arriba)

- **E1:** terminado, probado y en su commit, `5d219d84`.
- **Reparto del PM:**
  - esta rama hace E1 → E4+E5 → E2 → E8 → E9 → E11 → P3, más el peso de Altman en la puntuación;
  - E3, E6, E10, la historia de 10 años y BRK-B van a `fiabilidad/f8-independientes`.
- **E4+E5, empezado (commit WIP).**
  - Verificado con datos reales en VZ: el titular «los ingresos crecen 6,8 %» es el retorno total (dividendo 6,6 % +
    ingresos por acción 0,2 %), cuando el crecimiento de los ingresos es 0,33 %, el del DCF; PEG 0,80 «muy atractivo»
    con el BPA en −7,1 % anual; confianza «alta» con el P/E en −1.
  - Hecho: `financial_ratios.py` guarda en el ajuste de retorno total el crecimiento de los ingresos de la base del
    informe (`revenue_growth`) y el dividendo.
  - Falta en E4: que `display.py` (líneas ~1404–1421, 1730–1734 y 2431–2441) cite ese crecimiento en el titular y
    muestre el retorno total en su propia fila; PEG n.s. si el BPA ≤ 0 o no cuadra con el del informe; convergencia con
    misma dirección y ningún múltiplo en lectura extrema contraria; FCF de telecom menos la media de 5 años del
    espectro (solo con datos de EDGAR; si no, sin dato declarado).
  - Falta en E5: portada y resumen con la métrica normalizada cuando el motor marca la reportada como no fiable.
  - Falta después: tests, golden, evidencia «e4» y aviso al PM.
- **Pruebas pendientes del WIP:** ninguna pasada. El cambio solo añade campos al ajuste; la suite no se ha corrido.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
