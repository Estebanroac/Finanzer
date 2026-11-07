# F16 · La etiqueta de precio pasa a la regla L1 (§8 de la prueba hacia atrás)

Origen: `PRUEBA_HACIA_ATRAS_2025_RESULTADOS.md`. En el control, el motor y L1 empatan a 12 meses (+11,7 pp los dos) y
L1 gana a 6 meses. Decisión del usuario (6-nov-2026): «Empate: aplicar §8». La valoración se simplifica hacia L1 y el
motor queda para calidad, alertas y lectura. No hay otro ciclo de ajustes de precio.

## Decisiones del usuario (6-nov-2026)

1. **3 niveles**: atractivo (tercio más barato), razonable y exigente (tercio más caro), como se probó. Desaparecen
   «muy atractivo» y «muy exigente».
2. **La confianza no mueve el precio**: sin contracción hacia «razonable». La confianza se sigue mostrando como
   fiabilidad de los datos (y sigue contrayendo la calidad, que no se tocó).
3. **Expectativas golden**: se retiran los rangos de precio. Quedan la calidad, las reglas globales y la confianza
   máxima.

## La regla (la misma que se midió)

- P/E de doce meses = capitalización / beneficio neto atribuible de los **doce meses al último periodo presentado en
  EDGAR** (no al último de Yahoo, que va con retraso).
- Hallazgo de F16: el P/E que ya mostraba el motor difiere más de un 25 % del de L1 en 1 de cada 4 empresas (AMZN 45×
  frente a 35×, CI 21× frente a 11×), porque usa el corte de Yahoo.
- P/E relativo = P/E / mediana del P/E (> 0) de su sector GICS en el universo (543).
- Tercios del P/E relativo en el universo: el tercio bajo es «atractivo», el alto «exigente» y el resto «razonable».
- Beneficio ≤ 0 o sin P/E: «precio sin veredicto», con el motivo.
- Las medianas por sector y los dos cortes viven en `config/precio_l1.toml`, con su fecha. Los genera
  `tools/precio_l1_universo.py` con el P/E que calcula el propio motor en cada empresa del universo (el mismo número
  que se compara después en vivo).
- El DCF, el DCF inverso, los múltiplos frente al sector y los escenarios se siguen calculando y mostrando como
  **lectura**, pero no deciden la etiqueta.

## Verificación (no es un ajuste)

Se corre la prueba hacia atrás con F16 al corte del 5-nov-2025: los cortes salen del motor F16 sobre el universo de
2025. Lo esperado es reproducir L1 (D ≈ +11,7 pp en el control). Si no lo reproduce, se informa y no se toca la regla.

## Verificación al corte del 5-nov-2025 (6-nov-2026)

- Universo de 2025 capturado al corte entero: 543 empresas, 498 con P/E del motor. La referencia que sale de ahí
  (`archivo-historico/evidencias-de-pruebas/hacia_atras_2025-11-05/precio_l1_2025-11-05.toml`) tiene medianas por
  sector a ±1 punto de las de L1 y cortes de 0,83 y 1,21 veces la mediana.
- El P/E del motor coincide con el de L1 en el 97 % de las empresas (±10 %; mediana del cociente 1,00). Hay dos
  diferencias de fuente, no de regla: la capitalización con las acciones de Yahoo (BX, RIO, TKO) y los informes que
  companyfacts no trae (AOS, SPGI).
- Control a 12 meses: F16 da barata − cara = +10,8 pp (IC95 +2,8 / +18,0) y L1 +11,7. A 6 meses, F16 +8,7 y L1 +8,8.
  Reparto: 99 / 85 / 91 en F16 y 102 / 85 / 93 en L1. En las 110: F16 +8,9 y L1 +10,8 a 12 meses.

## En producción (preparado el 6/7-nov-2026, sin push)

- Referencia en vivo: `config/precio_l1.toml` generada con `tools/universe_scan.py` sobre las 543 (6-nov-2026) y
  `tools/precio_l1_universo.py`: 513 con P/E, cortes 0,837 y 1,255; escaneo en
  `archivo-historico/evidencias-de-pruebas/f16_referencia_2026-11-06/`. Refrescar cada mes.
- Efectos colaterales, todos por la regla: sin la dependencia de Ke del precio desaparece ese escalón de confianza
  (BRK-B baja → media, JPM media → alta) y, con él, la contracción de la calidad que dependía de esa confianza (BRK-B
  68 → 71); «Esta lectura sería errónea si…» se redacta con el nuevo nivel; sin P/E, «precio sin veredicto» y el motivo.
- Vista y PDF: la nota del precio cita P/E, mediana del sector, cociente y tercio (guardián: predicado `price_l1`);
  la metodología explica la regla; la web muestra 3 tramos (exigente < 34, razonable, atractivo ≥ 67).
- Suite: 6783 pasados; web: 173; guardián de build.sh en verde.

### Veredicto de precio del panel, antes y con F16

| Empresa | Antes | F16 | P/E | Veces la mediana |
|---|---|---|---|---|
| AAPL | muy exigente | exigente | 38.8x | 1.35 |
| AMT | razonable | atractivo | 24.6x | 0.74 |
| AMZN | muy exigente | razonable | 20.3x | 1.06 |
| ASML | entre exigente y muy exigente | exigente | 58.4x | 2.03 |
| BAC | entre razonable y exigente | atractivo | 11.2x | 0.78 |
| BCS | razonable | atractivo | 7.2x | 0.51 |
| BRK-B | exigente | razonable | 13.1x | 0.92 |
| CAT | entre exigente y muy exigente | exigente | 31.7x | 1.27 |
| CRWD | muy exigente | exigente | 4268.7x | 148.58 |
| DOW | razonable | sin veredicto | — | beneficio de doce meses ≤ 0: el P/E no tiene sentido |
| DUK | exigente | razonable | 18.0x | 0.87 |
| FCX | entre razonable y exigente | exigente | 33.9x | 1.67 |
| HSBC | exigente | razonable | 12.4x | 0.87 |
| JNJ | muy exigente | razonable | 29.1x | 0.97 |
| JPM | exigente | razonable | 14.0x | 0.98 |
| KO | exigente | exigente | 27.6x | 1.29 |
| MC.PA | razonable | sin veredicto | — | sin estados de SEC EDGAR |
| MSFT | exigente | razonable | 29.6x | 1.03 |
| MU | entre exigente y muy exigente | atractivo | 12.2x | 0.42 |
| NEE | entre razonable y exigente | razonable | 17.6x | 0.85 |
| NFLX | exigente | exigente | 21.5x | 1.31 |
| NVDA | muy exigente | razonable | 27.7x | 0.96 |
| NVO | atractivo | atractivo | 10.8x | 0.36 |
| O | atractivo | razonable | 41.2x | 1.24 |
| PG | entre exigente y muy exigente | razonable | 23.1x | 1.08 |
| PGR | razonable | atractivo | 10.6x | 0.74 |
| PLD | razonable | razonable | 29.5x | 0.89 |
| PLTR | muy exigente | exigente | 160.1x | 5.57 |
| RIVN | razonable | sin veredicto | — | beneficio de doce meses ≤ 0: el P/E no tiene sentido |
| SHEL | atractivo | razonable | 11.3x | 0.86 |
| SNOW | exigente | sin veredicto | — | beneficio de doce meses ≤ 0: el P/E no tiene sentido |
| SPY | — | — | — | — |
| TM | razonable | atractivo | 8.8x | 0.46 |
| TSM | exigente | exigente | 40.8x | 1.42 |
| UL | razonable | atractivo | 12.9x | 0.60 |
| V | muy exigente | exigente | 32.5x | 2.28 |
| XOM | entre razonable y exigente | exigente | 22.2x | 1.68 |

## F16 bis · Integridad de los datos de la L1 (7-nov-2026)

Origen: «Fase 1 bis · integridad de datos que afecta a la L1 (sin reglas nuevas de valoración)». La regla de tercios no
cambia; cambia con qué datos se calcula. Evidencias: `archivo-historico/evidencias-de-pruebas/f16bis_2026-11-07/` (en
vivo) y `hacia_atras_2025-11-05/` (`corridas/F16c*`, `precio_l1_2025-11-05_f16bis.toml`,
`f16bis_cambios_tercio_corte.json`).

### Qué cambia

1. **Beneficio normalizado.** La L1 usa el beneficio atribuible de doce meses al último periodo de EDGAR sin las
   operaciones discontinuadas y sin las partidas no recurrentes; la mediana del grupo se calcula con la misma base. Si
   el corte de los estados del motor es ese periodo, se restan las partidas que normaliza el motor; si es otro, los
   cargos y ventas no recurrentes que EDGAR declara para esos doce meses (`sec_edgar.charges_ttm`), con la misma prueba
   de recurrencia (`normalize.recurrence`: si se repiten, solo el exceso sobre su promedio; nunca un cargo «fantasma»
   cuando el del año es menor que el promedio) y después de impuestos.
2. **Grupos.** REIT con P/FFO entre REIT; financieras (arquetipo FINANCIAL: bancos y aseguradoras) solo entre sí; el
   resto por sector GICS. Un grupo con menos de `min_group` = 10 empresas se compara con la mediana de todo el universo
   y se dice (hoy, «Real Estate» no REIT: CBRE y CSGP). Beneficio normalizado ≤ 0: sin etiqueta, con el motivo.
3. **Perímetro.** Fuera las operaciones discontinuadas de los doce meses (3M/Solventum, Honeywell).
4. **Estados antiguos.** Si EDGAR tiene un 10-Q/10-K posterior que companyfacts no trae, el motor lee su instancia
   XBRL; si no dio tiempo, aviso junto a la etiqueta. Si el periodo tiene más de `stale_days` = 120 días frente al
   corte de los estados del análisis y no hay informe que leer (20-F sin trimestres en XBRL), también aviso.
5. **ADR y acciones.** Validación de las 40 empresas con clase o moneda distinta (`adr_validacion.csv`): la
   capitalización de los 9 ADR con factor oficial cuadra con sus estados (desvío máximo 7 %, recompras; Toyota con
   P/E 10,0). Causa encontrada en otro sitio: en emisores us-gaap sin conversión con factor implícito, la cotización
   cuenta otras acciones que el beneficio (unidades de la sociedad operativa en IBKR, BX, TKO, CVNA; fusión posterior
   al periodo en KMB/Kenvue; SWKS). La L1 rehace la capitalización con las acciones del balance **solo si EDGAR lo
   confirma** (promedio diluido del periodo a ±10 %): así no confunde un desdoblamiento que Yahoo aplica hacia atrás
   (NOW, HON al corte), un balance de otro periodo (COF) ni una etiqueta XBRL mal escalada (WAT). IBKR pasa de P/E
   110 a 29.
6. **Estabilidad.** Ver abajo.
7. **Clasificación.** Con pérdidas (también operativas) y ventas que caen más del 30 % (último ejercicio o tres), no es
   madura: GROWTH_PRE_PROFIT (Moderna).
8. **Calidad.** Flujo operativo por debajo del beneficio neto resta 2 en calidad de ganancias (NFLX: −2); la fortaleza
   «BPA en fuerte expansión» usa el crecimiento acotado del PEG (NFLX: 22,6 % en vez de 36,5 %).

### Cambios de tercio frente al beneficio reportado

- Al corte (5-nov-2025): 49 de 495 empresas con etiqueta en las dos bases (lista en `f16bis_cambios_tercio_corte.json`).
  Ninguna pierde la etiqueta por normalizar.
- En vivo (7-nov-2026): 72 de 543 (`cambios_tercio_vivo.tsv`). Referencia nueva en `config/precio_l1.toml`: 514 con
  múltiplo, cortes 0,839 y 1,190; medianas por grupo, mercado 22,1×.

### Efecto en la prueba hacia atrás (control, el que decide)

| Versión | Barata − cara a 12 m | IC 95 % | A 6 m |
|---|---|---|---|
| L1 (referencia) | +11,7 pp | +4,0 / +19,3 | +8,8 |
| F16 | +10,8 pp | +2,8 / +18,0 | +8,7 |
| F16 bis | **+12,8 pp** | +5,2 / +20,8 | +8,5 |

En las 110 empresas de la revisión baja (+6,1 frente a +8,9 de F16 y +10,8 de L1); el control es el que decide.

### Estabilidad: dos corridas el mismo día

Cinco escaneos de las 543 el 7-nov-2026 (`escaneo_r1` … `escaneo_r5`; comparación con `estabilidad.py`):

- R1 frente a R2: un cambio de alerta (SBAC). Causa: EDGAR no respondió a tiempo en R1 (KIM y SBAC) y el EBITDA salió
  de Yahoo. El motor ya lo declaraba («verificación oficial no disponible»).
- R2 frente a R3: ninguna etiqueta ni alerta cambia, pero el P/E de C y DTE sí. Causa: el 10-Q que presentaron el
  5-nov (companyfacts de la SEC va meses por detrás) se leía o no según si cabía en el presupuesto de 3 s de EDGAR.
  **Arreglo en origen**: un informe pendiente sin leer por tiempo cuenta como fallo transitorio de EDGAR y se reintenta
  con su propio presupuesto (`sec_edgar.transient`, `retry_s`), como ya se hacía con companyfacts.
- R4 frente a R5 (con el arreglo): **ninguna diferencia** en las 543 (etiqueta, múltiplo, grupo, alertas, arquetipo) y
  ningún fallo de EDGAR. Prologis: P/FFO 20,2 «razonable» en todas las corridas.

Queda una fuente de variación que no es del cálculo: si la SEC no responde ni al reintento, el análisis sigue con
Yahoo y lo dice.

## Fase 1 · pendientes de la prueba hacia atrás (7-nov-2026)

Sin reglas nuevas de valoración. Decisiones del usuario del mismo día: consistencia solo con coincidencia plena; una
sola alerta roja (las de valoración pasan a la lectura y el ROE negativo al estado del balance); la calidad deja de
contraerse.

1. **Una sola alerta roja** (`lib/alert_groups.py`, `[alerts.valuation_extreme]`): «Riesgo de caída fuerte por
   valoración extrema». Se activa cuando la valoración del motor anterior, que se sigue calculando en paralelo
   (`price_attractiveness.valuation_reading`), cae en «muy exigente». Es la única con evidencia fuera de la muestra: en
   el control al corte del 5-nov-2025 (versión A), 17 de 49 (34,7 %) cayeron un 40 % o más en algún momento de los 12
   meses siguientes, frente al 14,9 % del resto (37 de 248). El texto cita esas cifras y dice que no es una predicción.
2. **Consistencia** (`lib/consistency.py`) en lugar de la confianza: «consistente» si los métodos de valoración
   coinciden del todo (convergencia alta) y la cobertura de datos no es baja; si no, «mixta». Sin nivel alto y sin
   sugerir probabilidad de acierto. La confianza técnica se sigue calculando (la usa la lectura de valoración), pero
   no se muestra ni mueve nada. **La calidad ya no se contrae** (antes, con confianza baja, hacia 50).
3. **Estado del balance**, aparte y sin color de alerta: Altman, EBIT < 0 y cobertura de intereses crítica, caja libre
   negativa, apalancamiento, destrucción de valor, márgenes y ROE negativos. **Lectura de valoración**, aparte y sin
   color: lo de las categorías Valoración y Valor intrínseco (DCF, múltiplos, P/E con pérdidas). El resto de
   advertencias y las fortalezas, como estaban. El reparto se hace antes del tope de 6 por grupo.
4. **Cíclicas**: junto a la etiqueta L1, el aviso de pico de beneficio (condición (a) de `lib/earnings_peak.py`: el
   beneficio de doce meses más de un 40 % por encima de la mediana de sus 3 últimos ejercicios). Antes no se calculaba
   en las cíclicas porque en ellas el P/E no puntúa. MU: «beneficio en la parte alta del ciclo».
5. **Alarma de la referencia** (`precio_l1.reference_alarm`): si `config/precio_l1.toml` tiene más de 35 días
   (`max_age_days`) o si sus cortes no cambian respecto a la actualización anterior (que el archivo guarda en
   `previous_cuts`). Sale como aviso junto a la etiqueta, en `/api/health` (`price_reference.alarm`) y, la de cortes
   repetidos, como error de `tools/precio_l1_universo.py`.

Vista y PDF: la tarjeta «Consistencia» (dos tramos), «Por qué es mixta», los grupos «Estado del balance» y «Lectura
de valoración» en gris, y textos de ayuda y de la portada corregidos (decían que la confianza acerca el precio a 50,
lo que dejó de ser cierto con F16). Los fixtures de la web se regeneraron con el motor actual (no se regeneraban desde
antes de F13): dos pruebas de la web que dependían de datos viejos se ajustaron (la referencia de AAPL es hoy su
industria global, no la mediana de sus pares).

En vivo (escaneo de las 543 del 7-nov-2026, `archivo-historico/evidencias-de-pruebas/fase1_pendientes_2026-11-07/`):
alerta roja en 95 (17,5 %; en el control al corte, 16,5 %); consistencia: 254 consistentes y 289 mixtas; ninguna
calidad contraída; aviso de pico de beneficio en 24 cíclicas (MU, AMD, LRCX, CVX, SHEL, NUE…); sin alarma de la
referencia. Por empresa, de media: 1,3 advertencias, 0,5 del estado del balance y 2,4 de la lectura de valoración.
Suite: 6802 pruebas; web: 172; guardas de build.sh en verde.
