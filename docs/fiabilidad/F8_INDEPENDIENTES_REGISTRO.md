# F8 · Correcciones independientes de la Fase A (auditoría externa del 26-oct-2026) — Registro

Rama `fiabilidad/f8-independientes` (worktree `../finanzer_next-f8b`), desde `fiabilidad/f8-auditoria` en a0e824f5.
Plan: `docs/superpowers/plans/2026-10-26-fiabilidad-auditoria-externa.md`. Auditoría:
`docs/fiabilidad/auditoria-externa-2026-10-26.txt`. Cambios de veredicto: `GOLDEN_DIFF_F8_independientes.md`.

Esta rama hace, en paralelo a la cadena de valoración de la sesión «Rediseño E2a» (E1 → E4+E5 → E2 → E8 → E9 → E11),
las correcciones que no dependen de ella: E3 (FFO de REIT), E6 (frescura de los estados), E10 (Altman por SIC), la
historia de 10 años con EDGAR en cascada (hueco P2 «FCF histórico») y el símbolo de Finnhub de BRK-B. No toca Ke, beta,
WACC, el DCF ni su fiabilidad, la puntuación de rentabilidad ni la regla de confianza.

**Estado (27-oct-2026): las cinco correcciones están cerradas**, cada una con su commit y la suite completa en verde
(la última, 5.662 tests correctos):

| Corrección | Commit | Resultado |
|---|---|---|
| E3 · FFO según Nareit (PLD, O) | 2e6a9031 | aprobado por el PM |
| E3 · participadas materiales → «sin dato» | ce6d37f2 | SPG sin dato; PLD y O sin cambios |
| E6 · frescura de los estados | 3a575d14 | AMZN y BA desfasados; cobertura «media» |
| E10 · Altman por SIC y exclusiones | 596bafc9 | aprobado; financiera cautiva → referencial en el commit «E10 bis» |
| Historia de 10 años en cascada | 092ac02d | los 9 casos; **seguimiento: BPA de ciclo medio de SHEL** |
| BRK-B en Finnhub | — | no se reproduce, no se toca |
| BPA de ciclo medio (medias de las mitades) | commit «F8 · BPA de ciclo medio» (el siguiente a 8712bc80) | SHEL +52,3 % → +9,2 % |

La sección «Estado al pausar» (bajo E6) es histórica: describe la pausa del 26-oct.

Evidencia propia: datos reales del 26-oct-2026 (SEC EDGAR, Finnhub gratuito y Yahoo), descargados con las claves del
Llavero en el entorno del proceso (nunca impresas ni escritas). Los importes van en millones de USD salvo que se diga.

---

## E3 · FFO según Nareit (REIT: PLD y O)

### Evidencia

**El hallazgo se reproduce.** El motor calculaba `FFO = beneficio neto + D&A` (`financial_ratios.funds_from_operations`
recibía `gains_on_sale`, pero nadie lo rellenaba). PLD, TTM al 30-jun-2026: beneficio 4.202 + D&A 2.738 = **6.940**;
P/FFO 17,7x.

Lo que publica PLD (comunicados de resultados en los 8-K del 21-ene-2026 y del 16-jul-2026, en miles de USD):

| | Ejercicio 2025 | 6 meses 2026 | 6 meses 2025 | TTM al 2T-2026 |
|---|---:|---:|---:|---:|
| Beneficio neto de los accionistas comunes | 3.322.349 | 2.041.320 | 1.161.225 | 4.202.444 |
| + D&A inmobiliaria | 2.538.805 | 1.369.208 | 1.270.885 | 2.637.128 |
| − Ventas de otras inversiones inmobiliarias (sin promociones ni terrenos) | −684.854 | −302.015 | −82.771 | −904.098 |
| ± Minoritarios | −47.819 | −24.093 | −35.746 | −36.166 |
| + Parte de las participadas | 551.044 | 283.340 | 284.358 | 550.026 |
| **FFO Nareit** | **5.679.525** | **3.367.760** | **2.597.951** | **6.449.334** |
| Core FFO (excluye además las ganancias de promociones y terrenos) | 5.561.300 | 2.999.620 | 2.752.013 | 5.808.907 |

- Frente al FFO Nareit publicado (6.449), el motor estaba un **+7,6 %** por encima; frente al Core FFO (5.809), un
  **+19,5 %**. Lo que omitía (904 de ventas) lo compensaba en parte con lo que el XBRL no da (550 de participadas).
- La auditoría estimaba 7,14 $/acción frente a un Core FFO de «unos 6 $»: con los datos de hoy, 7,24 $ (6.940 / 958
  millones de acciones diluidas) frente a 6,06 $ de Core FFO y 6,73 $ de FFO Nareit.
- PLD **no usa** los conceptos estándar que cita la auditoría desde 2019: etiqueta sus ventas con conceptos propios
  (`pld:GainsOnOtherDispositionsOfInvestmentsInRealEstateNet`, `pld:GainsOnDispositionsOfDevelopmentPropertiesAndLandNet`)
  que companyfacts no publica (comprobado en la instancia XBRL de su 10-Q del 2T-2026 y de su 10-K de 2025). Además,
  repite la cifra de promociones en una nota con otro concepto (`pld:NetGainsOnDispositions…`): sumar por el nombre
  en la instancia contaría dos veces.
- **Muestra de 35 REIT de EE. UU.** (companyfacts del 26-oct): la cascada estándar existe en la mayoría
  (`GainLossOnSaleOfProperties` 9, `GainsLossesOnSalesOfInvestmentRealEstate` 7, `GainLossOnDispositionOfAssets1` 7…;
  deterioros: `ImpairmentOfRealEstate` 15), pero PLD, SPG, VTR, KIM, FRT, VICI, CCI y CUBE no tienen ninguno vigente
  (no venden o usan conceptos propios).
- **FFO del emisor como referencia gratuita: no existe.** Finnhub gratuito no tiene FFO (`/stock/metric`: 130
  métricas, ninguna de FFO; `/stock/earnings` da el BPA GAAP: PLD 1,13 $ en el 2T-2026). El 8-K de resultados solo
  lleva XBRL de portada (11 KB); el FFO va en el comunicado en HTML y el suplemento son imágenes JPG. Se omite y se
  declara.

### Arreglo

`lib/reit_ffo.py` (nuevo), con las reglas en `config/data.toml [reit_ffo]`:

- **FFO (Nareit) = beneficio neto + D&A − ganancias (+ pérdidas) por venta de inmuebles + deterioros de inmuebles.**
- **Fuente de los ajustes: el estado de flujos tal como lo presentó el emisor** en su 10-K y sus 10-Q (Finnhub
  `/stock/financials-reported`, gratuito; son las cifras del filing de la SEC, con sus conceptos estándar o propios).
  Es el estado completo, así que una partida que no aparece vale 0. Las partidas se reconocen por el nombre del
  concepto con expresiones regulares de config (`*_include` / `*_exclude`), no por ticker.
- **Promociones y terrenos:** Nareit (2018) deja al emisor incluir o no esas ganancias (activos accesorios). Se quedan
  dentro, como en el FFO Nareit que publica PLD (solo su Core las excluye).
- **EDGAR concilia:** el flujo de operaciones de cada estado usado (ejercicio, acumulado y acumulado del año anterior)
  debe estar en companyfacts, o en los filings que aún no trae, y coincidir a ±2 %. Si no, «sin dato». Así EDGAR valida
  también la moneda y el periodo.
- **Sin el estado presentado no hay FFO Nareit** («sin dato» con su motivo): companyfacts no dice si falta alguna
  partida propia del emisor (SPG tiene una de sus dos líneas de ventas con concepto propio), así que no sirve de
  respaldo sin dar un FFO incompleto.
- **TTM** como en `sec_edgar.flow_ttm`: ejercicio + acumulado del año − acumulado del año anterior. Serie anual
  (`archetype_metrics._reit`): el mismo ajuste en cada ejercicio; un ejercicio sin su 10-K en la fuente queda sin dato.
- **AFFO = FFO − rentas lineales − capex recurrente** (mejoras de inmuebles en explotación, comisiones de alquiler y
  obras de inquilinos), con la fórmula y las cifras visibles. Si el estado no separa el capex recurrente, «sin dato».
- **Participadas y minoritarios:** Nareit suma la parte de la D&A de las participadas y resta la de los minoritarios;
  el XBRL no separa ninguna de las dos. Se avisa si el resultado de participadas, o la parte de los minoritarios en el
  beneficio (beneficio consolidado del estado presentado − el de los accionistas), pesa al menos un 5 % del FFO.
- **Web y PDF:** dos filas nuevas en la tabla de múltiplos del REIT, «FFO según Nareit (por acción)» y «AFFO (por
  acción)», con la fórmula, las cifras, el periodo, lo que no incluye y la falta de referencia del emisor, o con el
  motivo del «sin dato». El texto del crecimiento por acción dice la definición nueva.
- P/FFO, payout sobre FFO, cobertura con FFO, FFO/activos y el DCF inverso sobre FFO leen el FFO nuevo (se sustituye
  una vez, tras clasificar el arquetipo y antes de todo lo que lo lee).

### Resultado con datos reales (TTM al 30-jun-2026)

| REIT | FFO antes | FFO Nareit (motor) | Publicado por el emisor | Diferencia | P/FFO antes → ahora |
|---|---:|---:|---:|---:|---|
| PLD | 6.940 | 6.035 (6,21 $/acc.) | Nareit 6.449 · Core 5.809 | −6,4 % · +3,9 % | 17,7x → 20,3x |
| O | 3.810 | 3.975 (4,20 $/acc.) | FFO 3.957 (3.860,3 + 1.990,2 − 1.893,4) | **+0,5 %** | 14,2x → 13,6x |
| SPG | 6.479 | 3.530 (9,29 $/acc.) | FFO de la sociedad operativa 4.762 | ver abajo | 12,5x → 22,9x |

- **PLD:** dentro del ±10 % que pide la auditoría (§6), frente al Nareit y frente al Core. Lo que falta es lo que el
  XBRL no da (participadas +550, minoritarios −36 y la D&A no inmobiliaria +101); se declara.
- **O:** antes −3,7 %, ahora +0,5 %. Sus ventas (190) y deterioros (356) se compensaban.
- **SPG (fuera de la muestra de la auditoría): límite de la fuente.** Su FFO suma «nuestra parte de la D&A de
  participadas» (Klépierre, TRG…: 811,7 en 2025 y 322,4 en el primer semestre de 2026), que el XBRL no separa. El
  motor queda un −25 % por debajo y avisa de las participadas. Antes estaba un +36 % por encima, por una ganancia de
  2.887 en el 4T-2025 por la toma de control de participadas. **Decidido (27-oct):** «sin dato»; ver abajo.
- **AMT (fuera de la muestra):** su FFO Nareit publicado es 5.279,5 (2022), 4.610,0 (2023), 5.233,2 (2024) y 4.160,9
  (2025). Su línea «pérdidas por venta y deterioros inmobiliarios» (684,3 / 732,8 / 91,6 / 83,5) coincide con la
  partida que suma el motor (`RestructuringCostsAndAssetImpairmentCharges`: 684,3 / 739,9 / 96,6 / 83,0). Las
  diferencias anuales (2025 +12 %, 2024 −14 %) son de lo que el XBRL no separa: la parte de los minoritarios
  (−450,7 en 2025) y las operaciones discontinuadas (+1.334,5 en 2024, India). **Límite conocido:** el aviso de
  minoritarios mira su parte del beneficio (114 millones TTM, 2 % del FFO) y no capta su parte de la D&A; en AMT no
  salta.
- **AFFO:** PLD 4.519 (sus partidas: rentas lineales con amortización de contratos 650; comisiones y obras de
  inquilinos y mejoras de inmuebles 866); O 3.809 frente a 4.068 publicado (−6,4 %: O suma otras partidas a su AFFO).
  AMT y SPG: «sin dato», porque su estado de flujos no separa el capex recurrente.

**Para el PM:** los umbrales de P/FFO (`thresholds.score.valoracion.reit_pffo_bounds`, mediana 17,2x en la fase 7) y
de FFO/activos se calibraron con el FFO antiguo (BN + D&A). No los toco: recalibrarlos es una decisión aparte.

### Tests

- `tests/test_reit_ffo.py` (14 tests): reconocimiento de partidas (PLD, O, SPG, AMT, IRM y exclusiones), TTM con los
  filings de PLD, conciliación (coincide / no coincide / falta EDGAR / falta la fuente), corte de ejercicio, AFFO sin
  capex recurrente, avisos de participadas y de minoritarios, sustitución en `ratios` y `key_metrics`, y serie anual.
  Incluye la afirmación de la auditoría: **PLD a ±10 % del FFO Nareit publicado**.
- Tests atados a los juegos `local` y `panel` (ramas de REIT, payout sobre FFO, crecimiento por acción, DCF inverso
  sobre FFO, rentabilidad sobre FFO): lo que depende del FFO se comprueba en los juegos que lo tienen
  (`conftest.reit_ffo_envs`: al menos uno). En `local`, capturado sin Finnhub, se comprueba el «sin dato» con su
  motivo. Las cifras de O pasan a las del FFO Nareit (por acción +3,6 % anual; antes −0,1 %).
- No regresión: primera pasada completa del backend con 5.605 tests correctos y 9 fallos, todos de REIT por el
  cambio de definición. Los 9 están corregidos y verificados: 574 tests correctos en los ficheros afectados
  (`test_archetype_branches`, `test_cost_of_capital`, `test_normalize`, `test_quality_price`, `test_pdf_v2_panel`,
  `test_reit_ffo` y `test_regression`). La última pasada completa, tras el aviso de minoritarios, se interrumpió por
  la pausa del usuario (26-oct): **hay que repetirla al retomar**. Solo cambian los golden de REIT (local O; panel O,
  PLD y AMT) y su texto del PDF v2.
- Replay: `/stock/financials-reported` grabado en los fixtures de O, PLD y AMT del panel (`tests/capture_finnhub_f8.py`;
  solo lo presentado hasta la captura de cada ticker).

### Participadas materiales: FFO «sin dato» (decisión del PM, 27-oct-2026)

- **Regla:** si el resultado de participadas pesa al menos `data.reit_ffo.ffo_jv_material_pct` = 10 % del FFO
  calculado, el FFO según Nareit es «sin dato» (no un FFO con aviso), con el motivo «tiene participadas materiales cuyo
  FFO no se puede ajustar con los datos públicos estructurados» y las cifras (resultado de participadas, su peso y el
  umbral). El AFFO, el P/FFO, el payout sobre FFO y el FFO/activos quedan sin dato y no puntúan; puntúa el resto de
  métodos. En la portada, el P/FFO y el payout sobre FFO dicen ese motivo.
- **Serie anual:** la misma regla en cada ejercicio, con el resultado de participadas de su 10-K. Si deja sin dato el
  CAGR del FFO por acción, el motivo es el de las participadas.
- Entre el 5 % (`equity_method_material_share`) y el 10 % sigue el aviso. El aviso de minoritarios no cambia.
- **FFO publicado por el emisor:** no se muestra. No hay fuente gratuita y estructurada (Finnhub gratuito no lo da y el
  8-K de resultados no lleva XBRL), así que la referencia sigue declarada como ausente.
- **Resultado en vivo (27-oct-2026, TTM al 30-jun-2026):**

  | REIT | Participadas / FFO calculado | FFO | P/FFO | Veredicto antes → ahora |
  |---|---:|---|---|---|
  | SPG | 448,7 / 3.526 = 12,7 % | **sin dato** | 22,9x → sin dato | precio 25 «muy exigente», confianza alta → 39 «exigente», confianza media (un solo método evaluable) |
  | PLD | 467,7 / 6.035 = 7,8 % | 6.035 con aviso (=) | 20,3x (=) | sin cambio |
  | O | 0,3 % | 3.975 (=) | 13,6x (=) | sin cambio |

  En SPG, la serie anual pierde 2025 (participadas 504,1, el 15,3 %); 2024 sigue.
- **Tests** (`tests/test_reit_ffo.py`): `test_participadas_materiales_dan_sin_dato` (SPG con sus cifras del TTM; por
  debajo del umbral, FFO con aviso) y `test_participadas_materiales_en_la_serie_anual`. PLD y O del panel no cambian
  (golden). En el golden local/O solo cambia el motivo del P/FFO y del payout de la portada (sin clave de Finnhub).

---

## Símbolo de Finnhub para BRK-B en métricas, calendario y sorpresas — **no se reproduce: no se toca**

### Evidencia (Finnhub gratuito, 26-oct-2026)

Se pidió usar `BRK.B` (`finnhub_fallback.provider_symbol`) también en `/stock/metric`, `/calendar/earnings` y
`/stock/earnings`, como ya se hace en los titulares desde la V4b. Se consultaron las dos formas:

| Símbolo | `/stock/metric` | `/stock/earnings` (último) | `/calendar/earnings` (2S-2026) |
|---|---|---|---|
| `BRK-B` | 126 métricas; β 0,082; P/E 13,65; BPA TTM 59.668,8; capitalización 1.170.675 | `BRK.A`, 2T-2026: real 9.038,3 frente a 7.594,6 | `BRK.A`, 2-nov-2026 |
| `BRK.B` | idénticas | idéntico | idéntico |

Finnhub normaliza las acciones de clase en esos tres servicios: el guion, el punto e incluso la otra clase devuelven
lo mismo (comprobado también con BF-B/BF.B/BF-A, LEN-B/LEN.B, HEI-A/HEI.A y MOG-A/MOG.B). Las cifras por acción de BRK
son de la acción A con cualquiera de los dos símbolos. Solo `/company-news` distingue (con `BRK-B` no devuelve
titulares), y ese ya usa `BRK.B`.

### Decisión

No se cambia: con `BRK.B` no cambiaría ninguna cifra. El riesgo real, que las cifras por acción de Finnhub vengan por
acción A, ya lo cubre el motor: con los estados reexpresados a la clase que cotiza, las cifras por acción de Finnhub
no se usan (`finnhub_fallback.enrich_info`, etapa 11b; y su BPA TTM solo entra si casa con el del corte, fase 2b). La nota de
`config/data.toml [finnhub] class_share_separator` queda como estaba. La nueva llamada de E3
(`/stock/financials-reported`) usa `provider_symbol`, por coherencia con los titulares.

---

## E6 · Frescura de los estados (AMZN y BA)

### Evidencia

**El hallazgo se reproduce** (análisis real del 26-oct-2026):

| | Corte del análisis | Último 10-Q en EDGAR | Días desde el cierre del corte | Cobertura | Confianza |
|---|---|---|---:|---|---|
| AMZN | TTM al 31-mar-2026 (Yahoo) | 10-Q al 30-jun-2026, presentado el 31-jul-2026 (0001018724-26-000026) | 209 | alta | alta |
| BA | TTM al 31-mar-2026 (Yahoo) | 10-Q al 30-jun-2026, presentado el 28-jul-2026 (0001628280-26-050038) | 209 | alta (16 componentes, 13 con dato) | baja (por otras dimensiones) |

El motor ya lo detectaba (`data_provenance.pending_results`: «la empresa publicó resultados el 31 de julio de 2026;
este análisis aún no los incorpora»), pero no actuaba: la cobertura seguía en «alta».

**¿Se puede usar EDGAR para todo el corte?** Hoy no. Se probó el `recut` de la fase 6 (que pasa el corte al último
trimestre de EDGAR cuando Yahoo no tiene trimestres) sobre estos cortes TTM desfasados, parcheado en memoria:

- **BA:** se descarta, porque al corte de EDGAR del 30-jun le faltan caja, inventario, deuda a largo plazo, SBC y deuda
  total con las definiciones del análisis.
- **AMZN:** no encuentra corte.

Sustituir el corte entero por EDGAR es la medida M5 de la Fase C (EDGAR como fuente principal con conciliación). Aquí
se aplica la otra opción de la auditoría: marcar «desfasado».

### Arreglo (27-oct-2026)

- **`edgar_backup.staleness(corte, filings, hoy)`** → `data_provenance.staleness`:
  - «desfasado»: EDGAR tiene un 10-Q/10-K/20-F/40-F (o un 6-K con XBRL) de un periodo posterior al corte (más allá de
    `report_date_tolerance_days`). Guarda el filing (formulario, periodo, fecha y número) y los días desde el cierre
    del corte.
  - «al_dia» o «sin_dato» (sin corte o sin los filings de EDGAR, como MC.PA).
  - Un 8-K de resultados no desfasa, porque no trae estados; lo sigue avisando `pending_results`.
  - El filtro de filings con estados se comparte con `pending_results` (`sec_edgar.with_statements` y
    `newer_statements`).
- **Cobertura:** si está desfasado y han pasado más de `data.edgar.stale_coverage_days` = 100 días desde el cierre del
  corte, `coverage_dimension(..., staleness=)` no pasa de «media», con su motivo. Nunca sube: una cobertura «baja»
  sigue «baja» (BA).
- **Aviso de la portada (web y PDF):** «Estados desfasados: cifras al 31 de marzo de 2026 (209 días); la SEC ya tiene
  el 10-Q al 30 de junio de 2026». Ocupa el lugar del aviso de resultados pendientes, que contaba lo mismo con menos.
  Cabe en una línea: UL, con cuatro notas sobre la antigüedad de sus estados, se salía de la portada (geometría del
  PDF).
- **Motivo de la confianza** (`plain_language`): «Hay estados más recientes en la SEC (10-Q al 30 de junio de
  2026)». En el anexo técnico va el detalle (corte, días y formulario).
- No toca la regla de confianza (E11): solo la dimensión de cobertura.

### Resultado

- **En vivo (27-oct-2026):**
  - **AMZN:** desfasado, 209 días, 10-Q del 30-jun (0001018724-26-000026). Cobertura alta → **media**.
  - **BA:** desfasado, 209 días, 10-Q del 30-jun (0001628280-26-050038). Cobertura **baja**, que ya lo era (Valoración
    excluida), con el motivo añadido.
- **Panel:** desfasados AMZN (197 días a la fecha de captura), BAC (197), MU (136; el 10-K del 3-sep-2026) y UL (288;
  el 6-K con XBRL del 1S-2026). Su cobertura pasa de alta a media. Los demás quedan «al día» y MC.PA en «sin dato»
  (sin EDGAR).
- **Para el PM (E11, no lo toco):** la confianza de AMZN sigue en **«alta»** con la cobertura en «media», porque la
  regla de confianza lo permite. La auditoría pedía que unos estados desfasados no dieran confianza alta; eso lo
  decide la regla de E11.

### Tests

`tests/test_freshness_e6.py` (8 tests). Además, `contract_forced.py --write` (las muestras forzadas llevan `staleness`):
- AMZN desfasado con la cobertura capada.
- Al día cuando el corte es el último 10-Q.
- Un 8-K no desfasa.
- Desfasado reciente (86 días): sin capar.
- Tolerancia de fechas (28-jun frente a 30-jun).
- Sin EDGAR: «sin_dato».
- La cobertura baja a «media» y nunca sube.
- El aviso sustituye al de resultados pendientes.

### Estado al pausar (26-oct-2026, petición del usuario vía PM)

- **E3: terminada**, en su commit. Pendiente al retomar: repetir la suite completa.
- **BRK-B: cerrado sin cambios** (no se reproduce; arriba).
- **E6: en curso, sin código en la rama.** Hechos: la evidencia (arriba) y el diseño. El diseño:
  - `edgar_backup.staleness(corte, filings, hoy)`: un 10-Q/10-K (o un 6-K con XBRL) con periodo posterior al corte
    (± tolerancia) marca «desfasado»; con más de `data.edgar.stale_coverage_days` = 100 días desde el cierre, además
    `coverage_capped`. Se llama en `yf_adapter._apply_edgar` y queda en `info["_staleness"]` y en `data_provenance`.
  - `valuation_confidence.coverage_dimension(..., staleness=)` baja «alta» a «media», con su motivo.
  - `display.data_notices` cambia el aviso de resultados pendientes por el de estados desfasados.

  Los tests ya escritos están fuera de la rama (`test_freshness_e6.py`, en el scratchpad de la sesión: se recrean al
  retomar).
- **E10: por empezar.** Diseño:
  - SIC de EDGAR (`_edgar.profile.sic`): SIC 2000–3999 usa el Z original y el resto el Z''; sin SIC, por sector, como
    hoy, y se dice.
  - Excluidos: 4610–4619, 4911, 4922–4924, 4931–4932, 4939–4941, 4961, 4991 y 6000–6799. Quedan «no aplica», con el
    sustituto informativo (deuda neta/EBITDA y cobertura, sin puntos).
  - Sin reequilibrar puntos ni tocar el peso (instrucción del PM).
  - Casos: KMI y UNH quedan excluidos; FCX y UNP pasan al Z''; ASML pasa al Z original.
- **Historia de 10 años: por empezar.** Evidencia y diseño:
  - Cobertura actual (10 ejercicios): LLY sin margen ni capex; NEE sin capex; VZ con capex en 3 de 10; V, SHEL y
    BRK-B sin BPA; JNJ, DOW, BRK-B y SHEL sin margen; TM con 6 de 10 y sin capex.
  - Cascada de capex con relevo verificado: `PaymentsToAcquireOtherPropertyPlantAndEquipment` (LLY) y
    `PaymentsToAcquireOtherProductiveAssets` (VZ desde 2017; coincide con `PaymentsToAcquireProductiveAssets` en 2017 y
    2018, y antes era una partida menor). Solo toman el relevo si coinciden con el concepto principal en un ejercicio
    común o si son el único que usa el emisor.
  - BPA diluido de operaciones continuadas (SHEL) solo si cuadra con beneficio / acciones diluidas (±2 % y medio
    céntimo; cuadra en los 11 ejercicios).
  - Resultado operativo sin alternativa: LLY, DOW, BRK-B y JNJ no lo presentan, así que «sin dato» con su motivo.
    NEE y TM presentan el capex con conceptos propios: «sin dato».
  - La persistencia no se mide sobre un concepto que EDGAR no tiene, y ese campo no se rellena con Yahoo.

---

## E10 · Altman por SIC y exclusiones con sustituto

### Evidencia

Antes, el modelo salía del sector de Yahoo: «basic materials», «industrials» y «energy» usaban el Z original, y el
resto el Z''. Así, FCX (minería) y UNP (ferrocarril) usaban el Z original, y ASML (maquinaria), las farmacéuticas y los
semiconductores el Z''. KMI (midstream) y UNH (aseguradora de salud), clasificadas como maduras, puntuaban con el
Altman. SIC de los casos (submissions de EDGAR, 26-oct-2026): KMI, WMB, ET, EPD y TRGP 4922; OKE 4923; LNG 4924;
MPLX 4610; UNP 4011; CAT 3531; ASML 3559; FCX 1000; UNH 6324; WM y RSG 4953.

### Arreglo

- **`config/valuation.toml [models.altman]`:**
  - `original_sic = [[2000, 3999]]`: con el SIC del emisor en EDGAR, las manufacturas usan el Z original y el resto
    el Z''.
  - Sin SIC (emisor sin EDGAR, como MC.PA), por sector como antes, y se declara.
  - `altman_z.model_basis` dice de dónde sale la variante («por el SIC del emisor en SEC EDGAR: 3559,
    manufacturas»), y la tarjeta lo muestra. Sin la descripción del SIC, que EDGAR da en inglés (guardián).
- **Exclusiones:** `excluded_sic` (4610–4619, 4911, 4922–4924, 4931–4932, 4939–4941, 4961, 4991 y 6000–6799), cada
  rango con su motivo (`excluded_sic_reasons`).
  - El Altman queda «no aplica» (`business_model.altman_excluded` → `_na["altman"]` en la solidez): no puntúa ni
    cuenta, y **sin reequilibrar pesos** (instrucción del PM; el peso es de E11).
  - La tarjeta da el sustituto informativo, sin puntos propios: deuda neta/EBITDA y cobertura de intereses. Los dos
    ya puntúan en la solidez por su vía.
  - WM y RSG (4953) no se excluyen.
- `altman_points` y los coeficientes no se tocan.

### Resultado

- **En vivo (27-oct-2026):**
  - **KMI:** no aplica (SIC 4922), con el sustituto «deuda neta/EBITDA 4.16x y cobertura de intereses 3.91x».
    Solidez 1/20 por liquidez y deuda. Calidad media.
  - **UNH:** no aplica (SIC 6324), con el sustituto «1.61x y 5.57x». Solidez 9/20.
  - **UNP:** Z'' 4,54, zona segura.
  - **ASML:** Z original 12,09, zona segura.
  - **FCX:** Z'' 2,46, zona gris (antes Z original 3,29, segura).
- **Panel:** cambian de variante AAPL, KO, PG, JNJ, MU, NVDA, TSM, ASML, NVO, UL y TM (al Z original), y FCX y SHEL
  (al Z''). Cambian de zona y de veredicto:
  - **AAPL:** Z'' 2,32 gris → Z 13,27 segura. Solidez 10 → 20, calidad 75 → 87: **sólida → excelente**. El Z''
    castigaba su patrimonio contable, que las recompras dejan bajo; el Z original lo mide con la capitalización.
  - **SHEL** (SIC 1311, extracción): Z 2,53 gris → Z'' 3,23 segura. Solidez 11 → 19, calidad 76 → 86: **sólida →
    excelente**.
  - **FCX:** segura → gris. Solidez 20 → 17, calidad 72 → 69, sin cambio de nivel.
  - **TM** (SIC 3711): Z'' 2,67 segura → **Z 1,59, zona de riesgo**. Solidez 19 → 7, calidad 70 → 55: **sólida →
    media**. Ver la decisión pendiente.

### Para el PM (decisión): TM y la financiera cautiva

El Z original de TM sale en zona de riesgo porque su balance consolidado incluye Toyota Financial Services: sus
préstamos a clientes y la deuda que los financia entran en X4 (capitalización / pasivo total) y en X5 (ventas /
activo). Es el límite conocido del Z en fabricantes con financiera cautiva. En US GAAP, el motor ya separa la deuda de
la cautiva (CAT: Cat Financial, `captive`). En IFRS (20-F de TM) no la detecta con datos estructurados gratuitos.

Opciones (no aplico ninguna sin tu visto bueno):
- **(a)** Dejarlo así, con la regla de la auditoría.
- **(b)** Altman «referencial» (no puntúa) cuando el emisor consolida una financiera cautiva, detectada en US GAAP o
  por un segmento financiero en el XBRL. Afectaría también a CAT.
- **(c)** Restar la deuda de la cautiva del pasivo de X4 cuando se detecta, como ya se hace con los arrendamientos.
  Solo funciona en US GAAP, así que TM seguiría igual.

También: SHEL (1311) y XOM (2911) son dos petroleras integradas y quedan en variantes distintas, porque el SIC lo elige
el propio emisor.

### Decisión del PM (27-oct-2026): opción (b), financiera cautiva por segmentos → Altman referencial

- **Detección** (`business_model.captive_finance`), una sola función con dos fuentes primarias:
  - La deuda de la cautiva que ya separa `lib/debt.py` en el XBRL (US GAAP; CAT: Cat Financial).
  - Si no la hay, los segmentos de negocio del último informe anual: `lib/segments.build`, el extractor de
    `/api/v2/segments`, que lee el XBRL del 10-K o 20-F, así que vale en US GAAP y en IFRS. Hace falta un segmento de
    servicios financieros con al menos `captive_finance_segment_min_pct` = 5 % de los ingresos, en los ejes de
    segmentos de negocio (`captive_finance_segment_axes`), con «financ» o «credit» en el nombre.
  - Los segmentos no traen los activos por segmento, así que solo se usan los ingresos.
- **Si se activa:** el Altman se muestra y **no puntúa** (referencial). Lleva el texto del PM, la evidencia (segmento y
  peso) y el sustituto informativo de los excluidos.
- **Si no hay segmentos:** opción (a). El Altman puntúa y la tarjeta declara el límite: «sin los segmentos del emisor no
  se puede comprobar si consolida una financiera cautiva». Pasa con NFLX (su 10-K no desglosa en XBRL) y MC.PA (sin
  SEC).
- Nada de proxies por industria ni por nombre.
- **Coste:** los segmentos se piden solo si el Altman aplica y la deuda del XBRL no ha detectado ya la cautiva. La
  primera vez por informe anual cuestan 2–3 s (lectura de la instancia XBRL); después salen de la caché por filing.
- **Replay:** `fixture_backend` sirve los segmentos desde `tests/fixtures/segments`.
- **Verificación con datos reales (SEC, 27-oct-2026):** TM «Financial Services Business» 9,7 %; CAT «Financial
  Products» 6,2 % (además, Cat Financial en la deuda del XBRL); F «Ford Credit» 7,1 %; GM «GM Financial» 9,2 %; DE
  «Financial Services» 13,6 %. Los cinco quedan referenciales. AAPL, SHEL, FCX, XOM y AMZN no tienen segmento
  financiero y no cambian.
- **Golden:**
  - **TM:** referencial. Solidez 7 → 13, calidad 55 → 62 (media, =).
  - **CAT:** referencial. Solidez 20 → 15, calidad 84 → 78: **excelente → sólida**. El Z original de 4,88 ya no
    puntúa.
- **SHEL y XOM** quedan en variantes distintas porque el SIC lo elige el emisor (1311 extracción frente a 2911 refino).
  Es la regla de la auditoría, y queda declarada.

### Coherencia del denominador (comprobación del PM, 27-oct-2026)

En Solidez, un Altman «referencial» (`CategoryCoverage.not_sig`) y uno «no aplica» (`comp(..., na=)`) se tratan
**igual**: ninguno entra en los componentes (ni en el numerador ni en el denominador de la cobertura), ninguno suma ni
resta, y la categoría conserva su base neutra (10) y su máximo (20), que el resto puede alcanzar (10 + 4 + 5 + 3).
Comprobado con dos perfiles:

| | Altman seguro | Altman en riesgo | No aplica | Referencial | Sin dato |
|---|---:|---:|---:|---:|---:|
| liquidez 1,6, D/E 0,5, cobertura 9 | 20 | 12 | 18 | 18 | 20 |
| liquidez 0,8, D/E 1,5, cobertura 2 | 10 | 0 | 4 | 4 | 1 |

«Sin dato» sigue otra regla, la de cobertura de la etapa 5: reescala los demás componentes a su rango y los amplifica
en los dos sentidos. No penaliza, porque queda entre el peor y el mejor valor posible del dato ausente. No hace falta
cambiar nada: TM y CAT no se recalculan. Lo fija `test_referencial_y_no_aplica_puntuan_igual`. El peso del Altman es de
E11.

**Coste de los segmentos para la pantalla de carga (E6):** la primera vez por informe anual del emisor, el análisis
espera 2–3 s más (TM 2,8 s, CAT 2,6 s, F 2,9 s, GM 1,9 s, DE 2,3 s, medidos el 27-oct-2026). Después salen de la caché
por filing (`market.segments.segments_ttl_s`). Solo cuando el Altman aplica y el XBRL no ha detectado ya la cautiva.

### Tests

`tests/test_altman_sic.py`, 29 tests más 14 de la cautiva y 2 de coherencia:
- TM, CAT, F, GM y DE detectados por segmentos; CAT también por la deuda del XBRL.
- AAPL, SHEL, FCX, un segmento financiero por debajo del 5 % y un eje de producto: sin cautiva.
- Sin segmentos: no se sabe.
- Referencial en Solidez; sin segmentos, el Altman puntúa.
- El texto de la tarjeta.

Los 29 de E10:
- Variante por SIC en los 9 casos.
- Sin SIC: por sector, y se declara.
- 10 SIC excluidos y 7 no excluidos.
- La solidez sin el Altman no reequilibra: los demás componentes puntúan igual.
- El texto del sustituto.

`test_pdf_v2_parts`: la escala de calidad de AAPL lee su golden (87 excelente) en lugar de fijar 75.

---

## Historia de 10 años con EDGAR en cascada (capex, margen operativo y BPA)

### Evidencia (companyfacts completo, 26-oct-2026; ventana 2016–2025)

| | Margen operativo | BPA | Capex |
|---|---|---|---|
| LLY | 0 / 10 | 10 | **0 / 10** (usa `PaymentsToAcquireOtherPropertyPlantAndEquipment`, 2007–2025) |
| NEE | 10 | 10 | 0 / 10 (conceptos propios) |
| VZ | 10 | 10 | **3 / 10** (`PaymentsToAcquireOtherProductiveAssets` desde 2017) |
| V | 10 | 0 / 10 (por clase) | 10 |
| SHEL | 0 / 10 | **0 / 10** (solo `DilutedEarningsLossPerShareFromContinuingOperations`) | 10 |
| BRK-B | 0 / 10 (hasta 2012) | 0 / 10 (por acción A equivalente) | 10 |
| JNJ | 0 / 10 (hasta 2014) | 10 | 10 |
| DOW | 0 / 9 | 9 | 9 (9 ejercicios: DOW Inc. desde 2019) |
| TM | **6 / 10** (US GAAP hasta el FY2020) | 10 | 0 / 10 (conceptos propios) |

Además, `persistence.merge_history` completaba con Yahoo el resultado operativo y el capex que EDGAR no tiene. Con
Yahoo (4 ejercicios) y una ventana de 5, la persistencia medía sobre la definición del proveedor y contaba el resto
como «no cumple».

### Arreglo

- **Relevo de conceptos** (`sec_edgar.HISTORY_RELAY`), con tres reglas:
  - Entra si es el único concepto del emisor (LLY).
  - Entra si coincide con la serie en el último ejercicio común, y entonces solo para los ejercicios posteriores
    (VZ: igual que `PaymentsToAcquireProductiveAssets` en 2018; su partida menor anterior a 2017 no entra).
  - El BPA de operaciones continuadas entra en cada ejercicio solo si cuadra con beneficio / acciones diluidas
    (±2 % o medio céntimo). Con operaciones discontinuadas no cuadra, y ese ejercicio no entra.
- **Cambio de norma verificado** (`HISTORY_CROSS_VERIFIED`): el resultado operativo, el beneficio, el flujo operativo
  y el capex de la otra taxonomía completan los ejercicios anteriores solo si coinciden ±2 % en un ejercicio común.
  - TM, FY2020: resultado operativo −1,8 % y beneficio −1,9 %, así que se completan.
  - TM, flujo operativo: −33 %, porque la NIIF reclasifica la financiera. No se completa y se dice.
  - Tolerancias en `data.edgar.history_relay_rel_tol` y `history_eps_abs_tol`.
- **Sin dato con su motivo:**
  - `annual_history.reason` cuando el emisor no presenta el concepto.
  - `history_10y.field_reasons` cuando falta en toda la ventana: no lo presenta, solo hasta un ejercicio, o la otra
    taxonomía no coincide.
  - La ficha usa ese motivo en cada fila.
  - El anexo técnico declara los relevos («Historia de 10 años: conceptos de relevo»).
- **Persistencia:**
  - `merge_history` ya no completa con Yahoo el resultado operativo ni el capex (`EDGAR_ONLY`).
  - Sin resultado operativo, Rentabilidad mide el margen neto y lo dice («sin resultado operativo en la SEC»).
  - Sin capex en la ventana, Calidad de ganancias no hace la prueba del FCF: «sin dato» no es «no cumple».
- **Fixtures:** `tests/capture_history_relay_f8.py` añade a los companyfacts del juego f2b solo los hechos de los
  conceptos de relevo presentados hasta su captura (16-oct-2026): 1.353 hechos.

### Resultado (los 9 casos, companyfacts completo)

| | Margen operativo | BPA | Capex | Sin dato, con su motivo |
|---|---|---|---|---|
| LLY | 0 | 10 | **10** (relevo: único concepto) | resultado operativo: no lo presenta |
| NEE | 10 | 10 | 0 | capex: conceptos propios |
| VZ | 10 | 10 | **10** (relevo verificado en 2018) | — |
| V | 10 | 0 | 10 | BPA: por clase de acción |
| SHEL | 0 | **10** (continuadas, cuadra en los 11) | 10 | resultado operativo: no lo presenta |
| BRK-B | 0 | 0 | 10 | resultado operativo: solo hasta 2012; BPA: por acción equivalente |
| JNJ | 0 | 10 | 10 | resultado operativo: solo hasta 2014 |
| DOW | 0 | 9 | 9 | resultado operativo: no lo presenta |
| TM | **10** (US GAAP verificado) | 10 | 0 | capex: conceptos propios; flujo operativo antes de 2021: no coincide entre normas |

### Para el PM: el BPA de ciclo medio de SHEL

Con su BPA ya en la historia, SHEL estrena el «crecimiento del BPA de ciclo medio» (`cyclicality.mid_cycle_growth`,
fase 3). Da un +52,3 % anual «de pico a pico (2015–2022)», porque el método toma el BPA en los picos de **ingresos**,
y 2015 es un pico de ingresos con un BPA hundido (0,29 $, en la caída del petróleo). Crecimiento sube de 12 a 16 y la
calidad de 86 a 91, sin cambio de nivel. El dato es correcto; lo flojo es el método, que no es de esta rama. Propuesta
de seguimiento: medir el BPA de ciclo medio entre años normales del BPA, o exigir que el BPA del pico inicial no sea un
mínimo de su serie. No lo toco.

### Tests

`test_v4b_datos`: el caso de SHEL pasa del BPA (que ya tiene) a su margen operativo (que falta). La ficha dice «EDGAR no
trae X de este ejercicio: <motivo del motor>».

`tests/test_history_cascade.py` (8 tests):
- LLY: relevo como único concepto.
- VZ: relevo verificado, solo para los posteriores.
- Un relevo que no coincide no entra.
- SHEL: BPA de continuadas, por identidad, ejercicio a ejercicio.
- TM: la otra taxonomía solo si coincide; el flujo operativo se rechaza.
- «Sin dato» con su motivo.
- Concepto que se deja de usar (JNJ).
- La persistencia no se completa con Yahoo ni se mide sin capex.

---

## BPA de ciclo medio (destapado por la historia de 10 años; encargo del PM, 27-oct-2026)

### Mecanismo verificado

`cyclicality.mid_cycle_growth` (fase 3, T5) toma los picos de **ingresos** del ciclo, el ejercicio anterior a cada
episodio de caída, y leía el BPA de esos dos años. Un pico de ventas puede ser un valle del BPA. En SHEL, el primer
pico es 2015, con un BPA de 0,30 $ por los deterioros de la caída del petróleo, y el último es 2022 (5,71 $):
(5,71 / 0,30)^(1/7) − 1 = **+52,3 % anual**. Es un fallo de método, no de datos.

### Alternativas medidas (la misma ventana del ciclo, historia real)

| | Pico a pico (antes) | Log-lineal (años positivos) | Medias de las dos mitades (elegido) |
|---|---:|---:|---:|
| SHEL 2015–2022 | +52,3 % | +42,1 % | **+9,2 %** |
| XOM 2014–2022 | +7,2 % | +9,0 % | −1,4 % |
| FCX 2011–2018 | −13,2 % | −14,1 % (5 de 8 años) | sin tasa (media negativa) |
| CAT 2008–2019 | +6,0 % | +4,4 % | −1,4 % |
| MU 2015–2022 | +17,7 % | +8,5 % | +3,5 % |

La pendiente log-lineal sigue arrastrada por los valles del principio (SHEL +42 %) y tiene que descartar las pérdidas.
Las medias de las mitades usan todos los ejercicios del ciclo, **pérdidas incluidas**, que es el concepto clásico de
beneficio de ciclo medio (normalizado), y ningún ejercicio aislado decide.

### Arreglo

- `cyclicality.eps_mid_cycle(hist, p0, p1)`: BPA medio de la primera mitad de los ejercicios del ciclo frente al de la
  segunda, anualizado entre los centros de cada mitad. Con un número impar de ejercicios, el central queda fuera.
- Sin tasa, con su motivo (`eps_reason`), si una mitad tiene menos de `eps_half_min_years` = 2 ejercicios con BPA o si
  su media no es positiva.
- Los picos de ingresos y el crecimiento de ingresos de ciclo medio no cambian.
- El texto de Crecimiento dice el método: «BPA de ciclo medio: media de 2015–2018 frente a la de 2019–2022, pérdidas
  incluidas».

### Tests

`tests/test_mid_cycle_eps.py` (5 tests):
- Sintético con el valle del BPA en el pico de ingresos: antes +33 %, ahora +5,2 %.
- Una mitad con media negativa: sin tasa.
- SHEL y XOM con su historia real.
- FCX sin tasa.

`test_quality_price` lee el texto nuevo, y en FCX comprueba la falta de tasa con su motivo.

**Sin tasa, con su motivo en la ficha:** la sección de Crecimiento ocultaba la fila del BPA que puntúa cuando no había
tasa. Ahora sale «Sin dato» con el motivo de la cobertura. FCX: «el BPA medio de una mitad del ciclo no es positivo
(pérdidas)». TM: «menos de 4 ejercicios anuales de BPA», un caso que ya existía y no se veía.
