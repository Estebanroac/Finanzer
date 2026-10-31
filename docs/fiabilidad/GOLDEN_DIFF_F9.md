# GOLDEN_DIFF · F9 coherencia (R3 y R6)

Cambios de golden de `fiabilidad/f9-coherencia` frente a 21d76d63 (rediseno/v4-f8 con P3), con su causa. Evidencia y
arreglo: `F9_COHERENCIA_REGISTRO.md`. Efecto aislado de esta rama; el combinado con R1/R1b de E2a (Ke de NU), en la
fusión.

## Veredictos

**Ningún texto de veredicto cambia.** Cambian tres puntuaciones:

| Golden | Cambio | Causa |
|---|---|---|
| BCS | Precio 58 → 55 (crudo 60 → 55; sigue «razonable») | R3, P/B con el balance del corte: 0.73x (patrimonio del FY2025) → 0.87x (el de la tabla), 102 % del justificado: el ajuste del P/B frente a ROE pasa de +2 a 0 |
| HSBC | Calidad 67 → 66 (sigue «sólida») | R3, serie FY de EDGAR con un solo concepto (`ProfitLoss` en toda la serie): la estabilidad del ROE pasa de σ 1.9 a 2.1 pp (+3 → +1) y la cobertura de Calidad de ganancias de +1 a 0; el crecimiento de ingresos a 3 años, de 9.8 % (Yahoo) a 10.5 % (EDGAR, `RevenueAndOperatingIncome`), sube de +1 a +3 |
| PGR | Calidad 83 → 78 (sigue «sólida»); confianza media → baja | R3, P/B con el balance del corte: 4.09x → 3.61x. El P/B justificado (Gordon) la ve ahora «barata» (+19 %) y el P/B frente al sector, «cara»: la convergencia pasa a baja, la confianza también, y la regla de E11 contrae la calidad de 83 a 78 |

## R3 · Una sola verdad por cifra

| Cambio | Golden |
|---|---|
| P/B y P/TBV del modelo con el balance del corte (`archetype_metrics.pb`, `ptbv`, `pb_basis`, `ptbv_basis`, `implied`, ratios frente al justificado, ajustes de Valoración, pre-mortem, convergencia) | bancos, aseguradoras y utilities: JPM (panel y local), BAC, BCS, HSBC, PGR, BRK-B, DUK, NEE |
| Tangible del ordinario del balance del corte (`data_provenance.ordinary.tangible_common`) | todos los que tienen la fila en el trimestre |
| Serie FY de ingresos y beneficio neto de EDGAR (`yearly_financials`, crecimientos, márgenes de la historia corta, DuPont, margen FCF, clasificación) | DUK, NEE, XOM (ingresos; diferencias de 2–10 % con Yahoo), HSBC (ingresos y beneficio); en los demás EDGAR ya coincidía a menos del 2 % y la serie no cambia. `data_provenance.edgar.primary.series` y `reconciliation` en todos |
| Una definición por serie en la historia de 10 años (el concepto del último ejercicio manda) | HSBC (beneficio: `ProfitLoss` en todos los años), AMT (beneficio 2016–2018), AMZN (capex 2016), PLD (capex 2016–2018) |
| Banco IFRS sin las comisiones (NIIF 15) como ingresos: la historia de 10 años los deja sin dato con el motivo; la serie se queda con la fuente | BCS |
| Crecimiento en la moneda de los estados en el gráfico histórico (`growth_currency.yearly`, interanual y CAGR) y en la lectura («en JPY, moneda de sus estados») | ASML, BCS, NVO, TM, TSM, UL |
| Gráfico histórico con la regla del motor (log-lineal con base anómala, `cagr_note`) y la lectura y la alerta lo dicen | NVDA, RIVN (y la marca `growth_basis.revenue_cagr` en todos) |
| Título del cuadro de cifras con su periodo (`figures_title`) y periodo de la escalera de márgenes (`margin_ladder.period`) | todos |
| Industria: la referencia dice el cruce con la del perfil (`benchmark.industry.profile_differs`) | todos (marca); texto en los que difieren |
| «No aplica» vacía la columna de la industria | los que tienen una fila «No aplica» con referencia (NU en vivo: EV/EBITDA) |
| Tarjetas del resumen con la precisión de las cifras clave (dos decimales) y su etiqueta; Regla de 40 de la cifra clave con la de la tarjeta | todos; etiqueta: los de beneficio normalizado; Regla de 40: RIVN, SNOW |
| Texto del PDF: lo anterior (cifras, títulos, notas) y recolocación de páginas | todos los PDF |

## R6 · Riesgo de crédito en bancos

| Cambio | Golden |
|---|---|
| `credit_risk` (medido) y sus filas en la tabla de solidez | JPM (panel y local), BAC, BCS, HSBC |
| «Capitalización» → «Patrimonio / activos … (no es capital regulatorio)» en el detalle de la solidez del banco | JPM, BAC, BCS, HSBC, PGR, BRK-B |
| `summary.alert_counts.unmeasured` (null en los golden: ningún banco del panel queda sin medir; NU en vivo, sí) | todos |

Ningún banco del panel queda «no medido»: la advertencia y la salvedad de la cuenta solo se ven en vivo (NU) y en los
tests.

## Fusión en `rediseno/v4-f8` (f5507270)

Desde 21d76d63, v4-f8 había recibido `rediseno/v4` (pre-pasada V4, marcas de las escalas y el comprobador de
coherencia web ↔ PDF de la portada de E2b): nada del motor ni de los golden. La fusión entra sin conflictos.

- **Golden:** regenerados sobre la fusión, idénticos a los de `fiabilidad/f9-coherencia`. Ningún cambio fuera de lo de
  arriba.
- **Fixtures del frontend:** exportadas del replay de la fusión, idénticas (solo el orden de dos claves de BCS).
- **Comprobador de portada de E2b** (`tests/test_coherencia_portada.py`): pasa con R3 y R6. Él compara la portada
  web con la del PDF; `test_coherencia_f9.py`, cada cifra del informe entero.

---

# GOLDEN_DIFF · F9 motor (R1, R2b, R1b, R1c, R5, R2, R4 y R7)

Revisión y plan en main (77edb5a0): `docs/fiabilidad/revision-nu-2026-10-27.md` y
`docs/superpowers/plans/2026-10-27-fiabilidad-revision-nu.md`. Rama `fiabilidad/f9-motor`, desde `rediseno/v4-f8`
(21d76d63). Evidencia en vivo: `docs/fiabilidad/f8_evidencia/f9_antes` (código de 21d76d63) frente a la de cada
corrección.

## R1 · Prima de riesgo país en el Ke

**Verificado con NU en vivo** (corrida «f9_antes»):

- El Ke era 7,39 %: el piso Rf + 0,5 × ERP, porque el CAPM daba 6,97 % (β 0,40).
- No había prima de riesgo país. NU presta en reales y pesos y su sede operativa en EDGAR es Brasil, aunque está
  constituida en Caimán.
- El P/B justificado era 4,68x y el precio «razonable» (45).

**Regla.** Ke = Rf + β·ERP + λ·CRP, y después los pisos de E1, sobre el Ke con la prima (`lib/country_risk.py`,
`valuation.country_risk`).

- **CRP: lo que una economía añade sobre EE. UU.,** máx(0, ERP_x − ERP_EE.UU.).
  - Los datos son de A. Damodaran, `ctryprem.xlsx`, actualización del 5 de enero de 2026, la última publicada; la de
    julio no ha salido.
  - Van en `config/country_risk.toml`, que genera `tools/gen_country_risk.py`.
  - Nuestra ERP ya es la implícita de EE. UU., que incluye su 0,23 %: Brasil suma 3,01 pp, Reino Unido y Francia
    0,55, Japón 0,68, y Alemania, Países Bajos y EE. UU. 0.
- **Ponderación por dónde opera** (decisión del PM, «(b) ampliada»), según la geografía de los ingresos del último
  anual en XBRL:
  - un país identificado usa su prima;
  - una región con nombre usa la media de Damodaran de esa región: Europe, EMEA, Latin America, Asia-Pacific o
    Emerging Markets;
  - un cubo vago («Non-US», «Other Countries») o varias regiones sin media publicada («Asia Pacific and Africa») queda
    **sin atribuir**: aporta 0 y se declara;
  - si países y regiones con nombre cubren menos del 80 % de los ingresos, se usa la **sede operativa** de EDGAR
    (o, sin la SEC, el país de la ficha), nunca el domicilio legal. El aviso del no atribuido se mantiene.
- **λ = 1.** La ponderación por ingresos ya mide la exposición. Un λ por empresa necesitaría la exposición media de
  cada país, que no hay gratis, y la contaría dos veces.
- **Revisión:** la tabla está en `review.toml` con las demás de Damodaran (5-ene-2027).

**NU con la regla** (corrida «f9_r1»):

- Ke de 7,39 % a **9,98 %** (CAPM 6,97 % + Brasil 3,01 pp; el piso ya no manda).
- P/B justificado de 4,68x a **3,06x**.
- Precio de 45 «razonable» a **35 «exigente»**.
- La confianza pasa de baja a **media**: el veredicto ya no cambia con ±1 pp de Ke.

**Prima por empresa con su fuente** (en vivo; `tools/f9_tabla_crp.py f9_antes f9_r1 …`):

| Empresa | Fuente de la prima | Prima país | Detalle | Ke (antes → después) | Precio (antes → después) | Confianza |
|---|---|---|---|---|---|---|
| NU | sede | 3.01 pp | prima de riesgo país 3.01 pp (Brasil, sede operativa; Damodaran, enero de 2026) | 7.39 % → **9.98 %** | 45 razonable → **35 exigente** | baja → **media** |
| ITUB | sede | 3.01 pp | prima de riesgo país 3.01 pp (Brasil, sede operativa; Damodaran, enero de 2026) | 7.39 % → **9.98 %** | 58 razonable → **52 razonable** | baja |
| ASML | país y región | 0.49 pp | prima de riesgo país 0.49 pp (ingresos por geografía: China 29%, Taiwán 26%, Korea 25%; Damodaran, enero de 2026) | 10.19 % → **10.68 %** | 35 exigente | baja |
| SAP | país y región (no atribuido 8%) | 0.60 pp | prima de riesgo país 0.60 pp (ingresos por geografía: Rest of EMEA 30%, Rest of APJ 10%, Japón 4%; Damodaran, enero de 2026); el 8% de los ingresos no tiene país identificado («Rest of Americas») | 9.40 % → **10.00 %** | 31 exigente | media |
| TM | sede | 0.68 pp | prima de riesgo país 0.68 pp (Japón, sede operativa; Damodaran, enero de 2026) | 11.42 % → **12.10 %** | 31 exigente | media |
| SHEL | sede (no atribuido 44%) | 0.55 pp | prima de riesgo país 0.55 pp (Reino Unido, sede operativa; Damodaran, enero de 2026); el 44% de los ingresos no tiene país identificado («Asia Oceania And Africa», «Other Americas») | 7.39 % | 62 razonable | baja |
| MC.PA | sede | 0.55 pp | prima de riesgo país 0.55 pp (Francia, sede operativa; Damodaran, enero de 2026) | 9.23 % → **9.77 %** | 55 razonable | baja |
| BCS | sede | 0.55 pp | prima de riesgo país 0.55 pp (Reino Unido, sede operativa; Damodaran, enero de 2026) | 10.19 % → **10.74 %** | 60 razonable | baja |
| HSBC | sede | 0.55 pp | prima de riesgo país 0.55 pp (Reino Unido, sede operativa; Damodaran, enero de 2026) | 8.84 % → **9.39 %** | 48 razonable → **45 razonable** | baja |
| TSM | país y región (no atribuido 2%) | 0.18 pp | prima de riesgo país 0.18 pp (ingresos por geografía: China 9%, Europe Middle East and Africa 3%, Taiwán 8%; Damodaran, enero de 2026); el 2% de los ingresos no tiene país identificado («Other Countries») | 10.74 % → **10.92 %** | 31 exigente | media |
| NVO | sede (no atribuido 21%) | 0.00 pp | prima de riesgo país 0.00 pp (Dinamarca, sede operativa; Damodaran, enero de 2026); el 21% de los ingresos no tiene país identificado («Eucan») | 9.53 % | 62 razonable | baja |
| KO | sede (no atribuido 60%) | 0.00 pp | prima de riesgo país 0.00 pp (Estados Unidos, sede operativa; Damodaran, enero de 2026); el 60% de los ingresos no tiene país identificado («Non-US») | 7.95 % | 30 exigente | alta |
| AAPL | sede (no atribuido 48%) | 0.00 pp | prima de riesgo país 0.00 pp (Estados Unidos, sede operativa; Damodaran, enero de 2026); el 48% de los ingresos no tiene país identificado («Other Countries») | 9.56 % | 10 muy exigente | alta |

**Golden: 5 de 43 cambian.** Solo en el precio, por el Ke con la prima. Ningún golden cambia la calidad ni la
confianza.

| Golden | Prima | Precio |
|---|---|---|
| JPM (panel y local) | +0,39 pp, regiones con nombre: EMEA 13 %, Asia Pacific 8 %, Latin America 2 % | 46 → 42, de **razonable a exigente** |
| BCS | +0,55 pp, sede Reino Unido | 58 → 55 |
| DOW | +1,14 pp: EMEA e India 31 %, Latin America 11 %, Asia Pacific 18 % | 55 → 50 |
| TSM | +0,18 pp: China 9 %, Taiwán 8 %, EMEA 3 % | 40 → 35 |

En el resto la prima es 0, por sede en EE. UU. o en un país Aaa, o no cambia el precio mostrado: ASML, CAT, MU, NVDA,
HSBC, MC.PA y TM.

## R2b · Beta de abajo hacia arriba de la tabla regional de Damodaran

**Verificado con NU en vivo** («f9_antes» y «f9_r1»):

- E1 hizo lo que debía: la beta propia (1,16 ajustada) se descarta por R² 0,17 < 0,20 y error estándar 0,27 > 0,25.
- Pero la de abajo hacia arriba salía siempre de la tabla de EE. UU.: «Banks (Regional)», 0,40, para un banco
  brasileño. Damodaran publica la misma tabla para Europa y para los mercados emergentes, donde los bancos regionales
  tienen 0,60.

**Regla** (decisión del PM): la de abajo hacia arriba usa la tabla de la región donde opera la empresa, con la misma
exposición que la prima de riesgo país (`country_risk.beta_region`):

- **emergentes** si la sede operativa o más del 50 % de los ingresos identificados (países y regiones con nombre)
  están en emergentes;
- si no, **Europa** con la misma regla;
- si no, **EE. UU.**

**Datos.** `config/betas_regional.toml`, generado por `tools/gen_regional_betas.py` desde `betaEurope.xls` y
`betaemerg.xls` (enero de 2026). Tiene las mismas columnas que la de EE. UU.: la beta media apalancada para las
financieras y la βU corregida por caja, que se reapalanca, para el resto. Su revisión, con las demás tablas de
Damodaran, es el 5-ene-2027.

**Detalles:**

- «Asia» y «EMEA» mezclan desarrollados y emergentes: no cuentan para ningún grupo.
- De Asia cuentan como emergentes los países de `emerging_asia`: China, India, Corea, Taiwán, el Sudeste Asiático y el
  sur de Asia.
- Japón, Singapur, Hong Kong y Australia quedan en la tabla de EE. UU.
- La beta propia y la de la fuente no cambian. Si la industria no está en la tabla regional, se usa la de EE. UU. y se
  declara.

**En vivo** («f9_r1» frente a «f9_r2b»):

| Empresa | Tabla | β | Ke | Precio | Confianza |
|---|---|---|---|---|---|
| NU | emergentes (sede Brasil) | 0,40 → **0,60** | 9,98 → **10,84 %** | 35 exigente (igual) | media |
| ITUB | emergentes (sede Brasil) | 0,40 → **0,60** | 9,98 → **10,84 %** | 52 → **48** razonable | baja |
| NVO | Europa (sede Dinamarca) | 1,01 → **1,19** | 9,53 → **10,30 %** | 62 → **58** razonable | baja |
| SHEL | Europa (sede Reino Unido) | 0,33 → **0,47** | 7,39 → **7,82 %** (ya no es el piso) | 62 (igual) | baja |
| CB | Europa (sede operativa en Zúrich) | 0,48 → **0,56** | 7,39 → **7,66 %**: el CAPM ya supera el piso y el veredicto no depende de Ke | 55 → **58** razonable | baja → **media** |

Las que pasan los filtros con su beta propia (ASML, SAP, MC.PA, BCS, HSBC, TSM y AAPL) no cambian. TM (sede en Japón)
sigue con la tabla de EE. UU.

**Caso límite: CB.** Chubb tiene la sede operativa en Zúrich según EDGAR, pero la mayor parte de sus ingresos está en
EE. UU. No tiene geografía de ingresos en XBRL, así que manda la sede, como dice la regla. Con geografía, la mayoría
identificada decidiría.

**Golden: 1 de 43 cambia.** No hay ninguna empresa con sede en emergentes en el panel.

- **NVO** (Europa): precio de 62 a **58**, razonable; la cruda pasa de 75 a 65.
- **SHEL y UL** (Europa) cambian la beta, pero no el veredicto.

**Test que cambia.** `test_f8_referencia.test_e1_audit_cases`: CB ya no queda en el piso de medio mercado, porque su
CAPM lo supera. Ahora se comprueba que su Ke no queda por debajo del piso (la intención de E1); XOM sigue en el piso
y dependiente de Ke.

## R1b · P/B justificado en dos etapas cuando el valor en libros crece mucho

**Verificado con NU en vivo:**

- El valor en libros crece un 33,6 % anual (CAGR de 3 años).
- El P/B justificado era el Gordon de una etapa, (ROE − g)/(Ke − g), con g = 2,5 %: supone que el valor en libros
  crece al 2,5 % desde hoy.

**Regla** (supuestos del PM del 27-oct; `archetype_metrics.apply_two_stage`, `valuation.pb_two_stage`). Si el CAGR
de 3 años del valor en libros supera el 20 %, el P/B y el P/TBV justificados pasan al modelo de dos etapas de
Damodaran:

- **Etapa alta**, 5 años: g₁ = mín(crecimiento observado, ROE × retención). La retención es 1 − reparto. Sin
  dividendo, 100 %; sin reparto conocido, el tope es el ROE.
- **Etapa estable**: la g de siempre, con el **ROE de la industria regional de Damodaran** (la referencia del
  análisis) y un reparto coherente, 1 − g / ROE estable. Mantener un ROE alto para siempre es el supuesto que la
  auditoría criticó en el DCF.
- **Sin ROE de la industria**: una etapa, declarado.
- **La fórmula** usa la misma convención que la de una etapa: el beneficio de cada año es el ROE sobre el valor en
  libros del año anterior. Con g₁ = g y el mismo ROE da exactamente el Gordon de una etapa (test).
- **La lectura dice los supuestos**: «dos etapas: 5 años con crecimiento del X %, después ROE de la industria
  (Y %) y g 2,5 %».

**NU, paso a paso** (en vivo, «f9_r1b»):

| Paso | Valor |
|---|---|
| Ke | Rf 5,29 % + β 0,60 (Banks Regional, tabla de emergentes; R2b) × ERP 4,20 % = CAPM 7,83 %; + prima país Brasil 3,01 pp (R1) = **10,84 %**. El piso (7,39 %) ya no manda. |
| P/B justificado | Una etapa, 2,75x. **Dos etapas, 1,89x**: 5 años con g₁ = 25,4 % (ROE 25,4 % × retención 100 %, sin dividendo; el observado de 33,6 % se acota al ROE); después ROE de los bancos grandes de emergentes, 11,0 %. |
| P/TBV justificado | 2,09x (ROTE 27,9 %). |
| P/B de mercado | **5,32x** (Yahoo), el **281 %** del justificado. P/TBV 5,84x, el 280 %. Con el 4,55x de la tabla de múltiplos sería el 241 %: en los dos casos, «Caro». La conciliación del P/B es de R3. |
| Valoración | Bloque P/B y P/TBV −4 (los dos «Caro»). Bloque de múltiplos 0: P/E frente al sector −4 (17,0x frente a 9,1x), forward P/E +3 (compresión de 17x a 11x). Total 6/20, **precio crudo 30**. |
| Veredicto | Confianza **media**: la estabilidad es media por la alerta de posible cíclica (la revisa R7). Contrae el precio hacia 50: **35, exigente**. Calidad 80, sólida. **«Calidad sólida · precio exigente»**. |

**Por qué no sale «muy exigente», como estimaba la revisión:**

- El forward P/E (11x) compensa el P/E en el bloque de múltiplos.
- La confianza media contrae el 30 hacia 50. Sin contracción, el 30 queda en el límite entre «exigente» y «muy
  exigente».
- Las dos etapas no lo compensan: al converger a un ROE de industria (11 %) apenas por encima del Ke (10,8 %), crecer
  reteniendo todo crea poco valor y el justificado baja de 2,75x a 1,89x.
- El veredicto ya no depende de Ke: ±1 pp deja el precio en «exigente».

**En vivo, quién la activa** (frente a «f9_r2b»):

- **NU**: P/B justificado de 2,75x a **1,89x**. Precio 35, exigente, sin cambio: el P/B ya era «Caro».
- **CB**: el valor en libros crece un 20,8 %. g₁ = 11,7 % (retención 86 %); su ROE converge a la industria (17,1 %),
  por encima del actual, y el justificado sube de 2,13x a **3,48x**. Precio de 58 a **60**, razonable.
- **JPM** (+10,8 %), **HSBC**, **BCS** e **ITUB** (+6,4 %): una etapa, sin cambio.

**Golden: 1 de 43 cambia.**

- **PGR** (aseguradora, valor en libros +25,3 %): g₁ = 7,1 % (retención 30 %) y ROE de la industria 18,7 %, frente al
  23,6 % actual. P/B justificado de 4,31x a 4,04x y P/TBV de 7,11x a 5,27x. Precio de 58 a **54**, razonable.
- Los bancos del panel (JPM, BAC, BCS, HSBC) y BRK-B (17,9 %) no la activan.

## R1c · La compresión del forward P/E solo puntúa si el histórico la respalda

**Causa.** Pregunta del PM sobre el +3 del forward de NU:

- El control de coherencia de E2 solo protege el lado bajo: un forward que implica muchísimo menos beneficio y
  activaría una bandera de pico falsa.
- El lado alto, el que premia la compresión (hasta +3), no se validaba.

**Regla** (decisión del PM, sin tope fijo):

- La compresión solo puntúa si el crecimiento del BPA que implica el forward (P/E que puntúa ÷ forward − 1) no
  supera el CAGR observado del BPA a 3 años. Es el `eps_cagr_3y` del análisis; con R3, la serie FY única de EDGAR.
- Si lo supera, la compresión se muestra pero no puntúa: «el forward implica más crecimiento que el histórico
  (+X % frente al Y % anual del BPA a 3 años); no puntúa».
- Si no hay CAGR observable (BPA inicial ≤ 0, historia corta), tampoco puntúa, y se declara el implícito y el
  motivo.

**NU** (decisión del PM: no se cambia la regla para salvar el caso, nada de ventanas ad hoc):

- La lectura dice: «Fuerte compresión P/E (17x → 11x forward); el forward implica +55 %, pero no hay histórico de BPA
  de 3 años comparable (BPA inicial <= 0: CAGR no definido); la compresión no puntúa». El BPA inicial ≤ 0 es la
  pérdida de 2022.
- Precio de 35 «exigente» a **28 «muy exigente»** (crudo 20, contraído por la confianza media).

**Quién pierde la compresión en los 69 casos más NU e ITUB:**

| Caso | Compresión | Causa | Precio |
|---|---|---|---|
| **En vivo** («f9_r1b» → «f9_r1c») | | | |
| NU | +3 → 0 | sin CAGR a 3 años (BPA inicial ≤ 0) | 35 exigente → **28 muy exigente** |
| AMZN | +1 → 0 | sin CAGR a 3 años (BPA inicial ≤ 0) | 39 → 35, exigente |
| GOOGL | +3 → 0 | implica +52 % frente al 33 % anual | 39 → 31, exigente |
| MSFT | +3 → 0 | +35 % frente al 23 % | 39 → 35, exigente |
| TSM | +3 → 0 | +55 % frente al 19 % | 31 exigente → **28 muy exigente** |
| UNH | +3 → 0 | +47 % frente al −15 % | 61 → 54, razonable |
| VZ | +3 → 0 | +41 % frente al −7 % | 50 → 45, razonable |
| AWK | +2 → 0 | +14 % frente al 8 % | 35 exigente → **25 muy exigente** |
| BCS | +2 → 0 | +19 % frente al 12 % | 58 → 55, razonable |
| HSBC | +2 → 0 | +31 % frente al 17 % | 45 razonable → **42 exigente** |
| ITUB | +2 → 0 | +24 % frente al 15 % | 48 → 45, razonable |
| LIN | +2 → 0 | +27 % frente al 21 % | 10 → 5, muy exigente |
| AAPL | +1 → 0 | +10 % frente al 7 % | 10, muy exigente (igual) |
| MC.PA | +1 → 0 | +11 % frente al −8 % | 55 → 52, razonable |
| UNP | +1 → 0 | +12 % frente al 2 % | 15 → 10, muy exigente |
| **Golden** | | | |
| TSM | +3 → 0 | +68 % frente al 19 % | 35 exigente → **15 muy exigente** (la confianza sube a media y no contrae) |
| JNJ | +3 → 0 | +34 % frente al 18 % | 28 → 15, muy exigente (confianza de media a alta) |
| NFLX (panel / local) | +3 → 0 | +39 % / +43 % frente al 36 % | 58 → 55 / 60 → 58, razonable |
| AMZN | +3 → 0 | sin CAGR a 3 años | 39 → 31, exigente |
| MSFT | +2 → 0 | +26 % frente al 23 % | sin cambio de veredicto |
| V | +2 → 0 | +33 % frente al 13 % | 25 → 20, muy exigente |
| BAC | +2 → 0 | +16 % frente al 13 % | 52 → 48, razonable |
| HSBC | +2 → 0 | +22 % frente al 17 % | 45 razonable → **39 exigente** |
| AAPL | +1 → 0 | +11 % frente al 7 % | 15 → 10, muy exigente |
| PG | +1 → 0 | +13 % frente al 4 % | sin cambio de veredicto |

**La conservan en vivo**, porque el histórico respalda lo que implica el forward:

| Empresa | Implícito | Observado (anual) |
|---|---|---|
| JPM | +10 % | 18 % |
| KO | +6 % | 12 % |
| LLY | +47 % | 52 % |
| MCD | +12 % | 13 % |
| NVDA | +108 % | 198 % |
| SAP | +28 % | 32 % |
| WMT | +17 % | 24 % |

**Efecto de segundo orden** (golden HSBC, JNJ y TSM):

- Con el precio crudo más bajo, ±1 pp de Ke ya no cambia el nivel, y el veredicto deja de depender de Ke.
- La confianza sube y la calidad deja de contraerse: TSM de 92 a 99, HSBC de 67 a 70.

**Golden: 9 de 43 cambian de veredicto.** Un test cambia: `test_quality_price` (V). Su compresión ya no puntúa y el
bloque de múltiplos pasa de −3 a −4.

### R1c continuo · el forward se acota al crecimiento que respalda el histórico

**Causa.** Revisión del PM sobre la forma binaria: MSFT, GOOGL o AAPL perdían toda la compresión por superar su
histórico en unas décimas. Así, el ruido de un año frente a un CAGR de tres se convertía en un salto de puntos. Que 15
de 36 la perdieran era señal de eso, no de 15 consensos inflados.

**Regla** (decisión del PM, sin parámetros nuevos):

- BPA forward creíble = BPA TTM × (1 + mín(g implícito, CAGR observado del BPA a 3 años)). La compresión puntúa con el
  P/E forward creíble = P/E que puntúa ÷ (1 + mín(…)).
- Si el consenso está en línea con la historia, nada cambia. Si va por encima, solo cuenta la parte respaldada. Con un
  histórico negativo, el creíble queda por encima del TTM y no hay compresión.
- La comprobación de la peor banda (Etapa 11b) se hace con el creíble.
- **Sin CAGR observable** (NU, AMZN): no puntúa, igual que en la forma binaria.
- **Lectura:** «P/E mejorando (17x → 13x forward creíble); forward 11.0x (implica +55% de BPA); con el crecimiento que
  respalda su histórico (+27% anual del BPA a 3 años), 13.4x».
- La salida lleva `credible_forward_pe` cuando acota. `not_scored` queda solo para el caso sin CAGR.

**En vivo** (`f9_r1b` → `f9_r1c` → `f9_r1cc`; solo las filas que cambian). Columnas: compresión (antes · binario ·
continuo), causa en la forma continua y precio (antes · binario · continuo).

| Caso | Compresión | Causa (continuo) | Precio |
|---|---|---|---|
| NU | 3 · 0 · 0 | implica +55 %; sin CAGR a 3 años | 35 exigente · 28 muy exigente · 28 muy exigente |
| AMZN | 1 · 0 · 0 | implica +10 %; sin CAGR a 3 años | 39 · 35 · 35, exigente |
| GOOGL | 3 · 0 · **3** | +52 % frente al +33 % anual: 20,9x → 23,8x creíble, sigue ≥ 25 % | 39 · 31 · **39**, exigente |
| MSFT | 3 · 0 · 2 | +35 % frente al +23 %: 22,4x → 24,7x | 39 · 35 · 35, exigente |
| TSM | 3 · 0 · 2 | +55 % frente al +19 %: 18,7x → 24,4x | 31 exigente · 28 muy exigente · 28 muy exigente |
| HSBC | 2 · 0 · **2** | +31 % frente al +17 %: 9,2x → 10,2x | 45 razonable · 42 exigente · **45 razonable** |
| AWK | 2 · 0 · 1 | +14 % frente al +8 %: 21,5x → 22,6x | 35 exigente · 25 muy exigente · **35 exigente** |
| BCS | 2 · 0 · 1 | +19 % frente al +12 %: 7,1x → 7,5x | 58 · 55 · **58**, razonable |
| LIN | 2 · 0 · 2 | +27 % frente al +21 %: 26,0x → 27,3x | 10 · 5 · **10**, muy exigente |
| AAPL | 1 · 0 · 1 | +10 % frente al +7 %: 36,3x → 37,2x | 10, muy exigente (igual en los tres) |
| ITUB | 2 · 0 · 0 | +24 % frente al +15 %: 7,9x → 8,6x creíble, **en la peor banda** (> 8,3x = 6,4x × 1,3) | 48 · 45 · 45, razonable |
| UNH | 3 · 0 · 0 | +47 % frente al −15 %: 17,6x → 30,3x, sin compresión | 61 · 54 · 54, razonable |
| VZ | 3 · 0 · 0 | +41 % frente al −7 %: 8,3x → 12,6x, sin compresión | 50 · 45 · 45, razonable |
| MC.PA | 1 · 0 · 0 | +11 % frente al −8 %: 16,1x → 19,4x, sin compresión | 55 · 52 · 52, razonable |
| UNP | 1 · 0 · 0 | +12 % frente al +2 %: 20,8x → 22,9x, sin compresión | 15 · 10 · 10, muy exigente |

**Golden** (558d2f48 → 64b3993b → disco):

| Caso | Compresión | Causa (continuo) | Precio |
|---|---|---|---|
| AMZN | 3 · 0 · 0 | implica +75 %; sin CAGR a 3 años | 39 · 31 · 31, exigente |
| NFLX (panel / local) | 3 · 0 · 3 | +39 % / +43 % frente al +36 %: 19,2x → 19,5x / 18,5x → 19,4x | 58 · 55 · **58** / 60 · 58 · **60**, razonable |
| HSBC | 2 · 0 · 2 | +22 % frente al +17 %: 11,0x → 11,5x | 45 razonable · 39 exigente · **45 razonable** |
| MSFT | 2 · 0 · 2 | +26 % frente al +23 %: 24,2x → 24,8x | 35 exigente en los tres |
| AAPL | 1 · 0 · 1 | +11 % frente al +7 %: 35,3x → 36,8x | 15 · 10 · **15**, muy exigente |
| BAC | 2 · 0 · 1 | +16 % frente al +13 %: 11,0x → 11,3x | 52 · 48 · 50, razonable |
| TSM | 3 · 0 · 2 | +68 % frente al +19 %: 18,9x → 26,6x | 35 exigente · 15 muy exigente · 28 muy exigente |
| JNJ | 3 · 0 · 2 | +34 % frente al +18 %: 22,0x → 25,0x | 28 · 15 · 20, muy exigente |
| PG | 1 · 0 · 0 | +13 % frente al +4 %: 21,0x → 22,8x, sin compresión | 28, muy exigente en los tres |
| V | 2 · 0 · 0 | +33 % frente al +13 %: 24,2x → 28,3x creíble, **en la peor banda** (> 24,6x) | 25 · 20 · 20, muy exigente |

**Cambios de nivel frente al binario:**

- **Vuelven al de antes de R1c:** HSBC, en vivo y en golden (exigente → razonable), y AWK en vivo (muy exigente →
  exigente). Su consenso solo supera la historia en unos puntos, y la parte respaldada basta para su banda.
- **Se quedan como en el binario:** NU y AMZN (sin CAGR), y los que tienen un histórico negativo o plano (UNH, VZ,
  MC.PA, UNP, PG).
- **TSM** baja de exigente a muy exigente frente a antes de R1c: el +68 % (+55 % en vivo) frente al +19 % pesa en la
  forma continua.
- **ITUB y V** quedan en 0 por la peor banda con el creíble.

Tests: `test_f9_r1c` cambia a la forma continua. `test_quality_price` (V) mantiene el bloque en −4, ahora por la peor
banda con el creíble. El test de E3 `CompanyHeader.test.tsx` vuelve a su estado anterior a R1c: AAPL, con el bloque en
−3.

## R5 · La cobertura de intereses y la deuda neta/EBITDA no tienen lectura en bancos ni aseguradoras

**Causa.** Revisión externa de NU, punto 5: «La cobertura de intereses (0,77x) es críticamente baja».

- El score y las alertas ya la excluían en FINANCIAL (`sectors.archetypes.not_applicable`). La lectura de `display`
  no: `read_coverage` se llamaba igual y su frase llegaba a la tabla de solidez, a la introducción y al PDF.
- En vivo (27-oct), NU, JPM, ITUB, HSBC y BCS decían «críticamente baja» (0,3x–0,8x). CB, una aseguradora, decía «la
  deuda es fácilmente servible: cobertura de intereses de 16.5x».
- **Misma plantilla, deuda neta/EBITDA:** CB decía «La posición de caja supera a la deuda total (caja neta)». Su caja
  y su deuda son reservas y cartera, y la métrica ya no aplicaba en el score.

**Corrección:**

- Si el componente no aplica al arquetipo, no hay lectura. La fila queda «No aplica», con el motivo, como el current
  ratio.
- Motivos nuevos en `classify.WHY_NOT_APPLICABLE_KEY`:
  - Cobertura de intereses: «el gasto por intereses es parte del negocio (el coste de los depósitos o de la
    financiación de su cartera), no el servicio de una deuda; su solidez se mide por el capital».
  - Deuda neta/EBITDA: «su caja y su deuda son parte del negocio (depósitos, reservas técnicas, cartera) y no tiene
    EBITDA».

**Verificado en vivo** (`f9_r5`, display reconstruido con el código nuevo): JPM, BAC, NU y CB quedan sin ninguna de
las tres frases. Las filas de cobertura y deuda neta/EBITDA quedan en «No aplica».

**Golden:** los datos del replay de los bancos no traen el gasto por intereses, así que las frases no salían ahí. El
test `test_f9_r5` reconstruye la vista de JPM con las cifras en vivo de JPM (0,83x) y de CB (16,5x, caja neta).

**Resto de frases de plantilla revisadas con JPM, BAC, NU y CB:**

| Frase | Dónde | Destino |
|---|---|---|
| «Margen neto sólido — De cada dólar vendido quedan 27 centavos… por encima de la media de su sector» (NU, BAC; JPM normalizado) | alertas | **R4**: en NU contradice la comparación (27,4 % frente al 41 %, inferior) |
| «Perfil defensivo — Beta 0.40» (NU) y 0.48 (CB), con la beta de Yahoo anterior a R2b; la vista y el Ke usan 0,60 y 0,56 | alertas | **R2**: las alertas leen `ratios["beta"]`, no la beta final |
| «Podría ser cíclica: su crecimiento de ingresos oscila 31.3 puntos» (NU) | clasificación | **R7** |
| «Capitalización sólida (16.0% ≥ 6%)» | salud bancaria | **R6** (independientes, ya fusionado en v4-f8) |
| «el BPA crece más rápido que los ingresos: márgenes en expansión, apalancamiento operativo o recompras» (JPM, BAC, CB) | crecimiento | se queda: es genérica, pero no falsa en un banco |

## R2 · Una sola beta en todas las capas y «Sensibilidad baja al mercado» solo con la beta propia

**Causa.** El revisor vio «Perfil defensivo — Beta 0.40» en NU.

- **Por qué 0,40.** La regresión propia de NU da 1,24 en bruto (1,16 ajustada), pero falla los filtros de E1: R² 0,17
  < 0,20 y error estándar 0,27 > 0,25. Cae a la beta de abajo hacia arriba de Banks (Regional) de EE. UU., 0,40, y con
  R2b a la tabla de emergentes, 0,60.
- **El defecto real.** Las alertas leían `ratios["beta"]`, calculado al principio del análisis con la beta de Yahoo,
  antes de la tabla regional, del reapalancamiento y de Blume. NU: alerta 0,40 con un Ke de β 0,60. CB: 0,48 frente a
  0,56. KO: 0,64 frente a 0,63. MSFT: la lectura y la tarjeta decían «beta 1.13» (bruta) con un Ke de β 1,09.
- **La afirmación.** «Se mueve menos que el mercado y tiende a amortiguar las caídas» habla de volatilidad, y la beta
  no la mide. NU tiene una volatilidad de 46,2 % frente al 12,7 % del S&P 500.

**Regla** (decisión del PM, opción a, sin parámetros nuevos):

- **Una sola beta**, la del Ke (`key_metrics.beta_ke` = la propia con Blume, o la de la industria tal cual). La leen
  las alertas, la lectura del bloque de beta, la tarjeta («Beta ajustada (Blume)» o «Beta de la industria»), la serie
  del gráfico y `ratios`. La bruta solo aparece rotulada en el detalle del WACC.
- **Fortaleza «Sensibilidad baja al mercado — β propia 0.55»**, con el texto «β propia 0.55 (R² 0.34): sus
  movimientos dependen poco del mercado». Requisitos: la beta propia que pasa E1 (`beta_source == "propia"`) y por
  debajo de `beta_low`. Nunca con la de la industria.
- **La lectura «Defensiva»** sigue la misma regla. Con la beta de la industria, la lectura es «Beta baja» (neutra):
  «beta 0.60 de su industria: la propia de la acción no pasa los filtros de la regresión, así que no mide su
  sensibilidad al mercado».
- **Sin condición de volatilidad.** La sección de Mercado no clasifica la volatilidad, y el texto nuevo no afirma nada
  sobre ella.

**En vivo (`f9_r1cc` → `f9_r2`): la fortaleza queda en 0 de 36.**

| Empresa | Antes | Ahora | Por qué |
|---|---|---|---|
| NU, ITUB | Perfil defensivo — Beta 0.40 | — · Beta baja (0,60) | beta de la industria (emergentes); la de la alerta era la de Yahoo |
| CB | Beta 0.48 | — · Beta baja (0,56) | beta de la industria |
| VZ, KO, XOM, KMI, NEE, AWK, O | Beta 0.30–0.67 | — · Beta baja | beta de la industria |
| PLD | Beta 0.72 (bruta) | — · De mercado (0,82) | propia (R² 0,21), pero con Blume pasa de beta_low |
| HSBC | Beta 0.77 (bruta) | — · De mercado (0,84) | ídem (R² 0,22) |
| SHEL | — | lectura Beta baja (0,47) | beta de la industria |

En las 13, ninguna capa muestra una beta distinta de la del Ke.

**Test:** `test_f9_r2::test_one_beta_in_every_layer` recorre los 43 golden. Falla si `key_metrics.beta_ke`,
`ratios.beta`, `price_history.beta`, las alertas o la lectura de la beta difieren de `wacc.beta`. Antes del arreglo
fallaba en AAPL: `ratios` 1,05 (bruta) frente a 1,03 del Ke.

## R4 · El margen neto de un banco no puntúa

**Causa.** Revisión externa de NU, punto 4. El 27,4 % de NU se calcula sobre ingresos brutos, con los intereses
cobrados, y se comparaba con el 41 % de bancos que reportan ingresos netos: −2 puntos sin fundamento. Además, una
fortaleza decía «Margen neto sólido — De cada dólar vendido quedan 27 centavos… por encima de la media de su sector»,
cuando la comparación lo da inferior.

**Regla** (decisión del PM: solo bancos):

- Hay una lista de «no aplica» por subtipo de FINANCIAL (`sectors.archetypes.not_applicable_subtype`, con
  `banco = ["net_margin"]`). La leen `classify.not_applicable(…, subtype)`, el score (`score_rentabilidad`), las
  alertas (`Ctx.na`) y `display.na_keys`.
- En un banco, el margen neto no puntúa (cobertura «no aplica»), no genera alerta y no se compara con la industria. La
  fila dice «No aplica a bancos: sus ingresos no tienen una definición común (con los intereses cobrados o netos de los
  pagados)…».
- La tarjeta de portada muestra el ROA en su lugar. Una tarjeta «no aplica» con cifra rompía la regla del guardián
  `no_aplica_con_cifra`.
- Las aseguradoras y los conglomerados lo conservan, porque su margen sobre primas e ingresos es comparable entre
  ellas. Los ingresos y su crecimiento no cambian.

**En vivo** (`f9_r2` → `f9_r4`):

| Empresa | Subtipo | Ajuste del margen | Rentabilidad | Calidad | Alerta de margen |
|---|---|---|---|---|---|
| NU | banco | −2 → no aplica | 18 → 20 | 80 → 81 | ya no aparece |
| ITUB | banco | −2 → no aplica | 16 → 18 | 74 → 76 | — |
| BCS | banco | −2 → no aplica | 8 → 10 | 64 → 66 | — |
| JPM | banco | 0 → no aplica | 18 | 89 | «Margen neto normalizado sólido» ya no aparece |
| BAC | banco | 0 → no aplica | 12 | 67 | «Margen neto sólido» ya no aparece |
| HSBC | banco | 0 → no aplica | 12 | 67 | — |
| CB | aseguradora | 0 (sin cambio) | 18 | 81 | — |

Ningún nivel cambia.

**Golden:** 1 de 43 cambia un campo del veredicto (BCS, calidad 66 → 68), sin cambio de nivel.

## R7 · Errores menores: Rf, «posible cíclica» y estabilidad del ROE

**1. El Rf: 5,29 % frente al 5,00 % del bono del día.** Verificado en vivo (27-oct):

- El 5,29 % es el Tesoro a 10 años del par Rf–ERP de Damodaran, a 1 de octubre de 2026. Su ERP (4,20 %) se calculó con
  ese mismo Rf, la misma fecha (F8 · E1).
- El ^TNX del 27-oct da 4,99 %. La diferencia de 0,30 pp está por debajo del aviso `pair_drift_warning` (0,5 pp), así
  que el modelo no tenía que avisar.
- **El defecto era de rotulado:** la nota decía «Rf 5.29%» a secas, y el revisor la comparó con el bono del día.
  Ahora dice «Rf 5.29% [Tesoro de EE. UU. a 10 años del par Rf–ERP de Damodaran, 1 de octubre de 2026; bono a 10 años
  (^TNX) el 27 de octubre de 2026: 4.99%]», en la nota del Ke de bancos y en la del WACC (`display._rf_txt`).

**2. «Posible cíclica» exige caídas.** El criterio de la oscilación del crecimiento de ingresos (σ > 15 pp) marcaba la
desaceleración normal de un hipercrecimiento. NU pasó de +182 % a +37 % sin ningún año a la baja (σ 31 pp). Ahora ese
criterio solo cuenta si algún año los ingresos caen. El del margen operativo, alrededor de su tendencia, no cambia.

**3. La estabilidad del ROE no mide el paso de pérdidas a ganancias.**

- NU tuvo pérdidas en 2019–2022 y beneficio desde 2023. Su σ incluía la pérdida de 2022 y la puntuaba «ROE volátil:
  beneficio poco recurrente» (−3).
- **Es un paso solo si la historia anual de EDGAR no tiene ningún ejercicio con beneficio antes de la última pérdida**,
  y la ventana es «pérdidas, luego beneficios». Entonces la σ se mide desde el paso a beneficios y se dice («ROE algo
  volátil (3 ejercicios desde el paso a beneficios)»). Con menos de 3 ejercicios con beneficio queda «no
  significativa»: no resta ni cuenta en la cobertura.
- **Una pérdida después de años con beneficio es volatilidad y cuenta.** Primera versión, descartada: con solo la
  ventana de 4 años, BRK-B (pérdida contable en 2022, beneficio en 2021) se leía como paso y su calidad subía de 67 a
  74. La historia larga lo distingue. Sin ella, la σ es la de siempre.

**En vivo (`f9_r4` → `f9_r7`):** solo cambia NU.

- «Posible cíclica» desaparece.
- Estabilidad del ROE: −3 → −1.
- Calidad: 81 → 83, sólida.
- La confianza sube de media a alta (ya no hay techo por estabilidad), así que el precio deja de contraerse hacia 50:
  28 → 20, «muy exigente» igual.

ITUB, BCS, HSBC, JPM, BAC y CB no cambian.

## Fusión de f9-motor en `rediseno/v4-f8` (sobre fc2220ea, que ya tiene f9-coherencia)

**Conflictos de código:** los tres son de parámetros contiguos y se conservan los dos lados.

- `archetype_metrics.compute` y `_financial` reciben `ordinary` (R3: balance del corte para el P/B y el P/TBV) y
  `history_fy` (R7: historia de EDGAR para el paso de pérdidas a ganancias).
- `main.py` pasa los dos.
- `display.py` lee el crecimiento con la moneda y el ajuste log-lineal (R3) y la beta del Ke (R2).
- Este documento junta las dos partes.

**Golden: 11 de 43 cambian de veredicto frente a fc2220ea.** Son los de f9-motor (R1, R1b, R1c, R4 y R7) más tres
casos en los que los datos de R3 pasan por las reglas del motor. Frente a f9-motor sola, cambian 3:

| Golden | Cambio | Causa |
|---|---|---|
| BCS | calidad 68 → 71; confianza baja → media; precio 55 → 58, razonable | R3: P/B con el balance del corte (0,73x → 0,87x). La convergencia de métodos cambia, la confianza sube a media y la calidad deja de contraerse |
| HSBC | calidad 67 → 69; precio 45 razonable → **39 exigente**; confianza baja → media | R3: P/B 1,63x → 1,87x (−4 en P/B frente a ROE). La serie FY de EDGAR sube el crecimiento de ingresos (9,8 % → 10,5 %, +2) y la σ del ROE (1,9 → 2,0 pp, +3 → +1) |
| PGR | calidad 83 → 78; precio 54 → 58; confianza media → baja | R3: P/B 4,09x → 3,61x mejora sus múltiplos. Los métodos divergen más, la confianza baja y la calidad se contrae |

**Test de datos (E3):** `src/v2/lib/confidence.test.ts`.

- BCS ya no contrae la calidad (confianza media). El caso «contrae el precio y la calidad» pasa a NEE (confianza baja).
- BCS queda con su propia frase: «de 60 a 58. La calidad del negocio no se contrae».

**Test de datos (E3):** `e2e/v2/puntuacion.spec.ts`. La nota que une «por confianza…; en la frontera con…» se probaba
en JPM (46, a 2 puntos de «exigente»). Con R1 y R1c, JPM queda en 42 «exigente», fuera de la frontera. El caso pasa a
TM, con «por confianza media; en la frontera con «muy exigente»».

**Suites sobre la fusión:** backend 6028 correctos; vitest 142; e2e:v2 862 correctos más el caso de TM, que pasa 7 de 7
al repetirlo. lint: los 5 avisos antiguos.

## Cierre de F9 · NU y las 26 de la auditoría, antes y después (en vivo, 27-oct)

«Antes» es `f9_antes`: rediseno/v4-f8 en 21d76d63, sin F9. «Después» es `f9_fin`: esta fusión, con f9-motor y
f9-coherencia. Las dos corridas se hicieron en vivo con el backend local; la tabla sale de
`tools/f9_tabla_cierre.py f9_antes f9_fin …`. En negrita, los cambios de nivel. Las 10 de la revisión de la prima de
riesgo país van al final. BAC no estaba en `f9_antes`.

| Empresa | Ke | β del Ke | Prima país | Calidad | Precio | Confianza |
|---|---|---|---|---|---|---|
| NU | 7.39 % → 10.84 % | 0.40 → 0.60 | 0.00 % → 3.01 % | 76 → 83 sólida | 45 → 20 razonable → **muy exigente** | baja → alta |
| MSFT | 9.85 % | 1.09 | 0.00 % | 95 excelente | 39 → 35 exigente | media |
| NVDA | 11.92 % → 12.08 % | 1.58 | 0.00 % → 0.17 % | 93 excelente | 58 razonable | media |
| LLY | 9.30 % → 9.49 % | 0.96 | 0.00 % → 0.19 % | 86 excelente | 39 exigente | media |
| UNH | 8.93 % | 0.87 | 0.00 % | 62 media | 61 → 54 razonable | media |
| JPM | 9.72 % → 10.10 % | 1.05 | 0.00 % → 0.39 % | 89 excelente | 46 → 42 razonable → **exigente** | media |
| CB | 7.39 % → 7.66 % | 0.48 → 0.56 | 0.00 % | 81 sólida | 55 → 60 razonable | baja |
| AMZN | 10.94 % → 10.99 % | 1.35 → 1.34 | 0.00 % → 0.06 % | 60 media | 39 → 35 exigente | media |
| MCD | 9.18 % | 0.93 | 0.00 % | 76 sólida | 48 razonable | baja |
| GOOGL | 10.15 % → 10.77 % | 1.16 → 1.15 | 0.00 % → 0.63 % | 100 excelente | 39 exigente | media |
| VZ | 8.00 % | 0.65 → 0.64 | 0.00 % | 59 → 58 media | 50 → 45 razonable | media → baja |
| CAT | 9.75 % → 10.65 % | 1.06 | 0.00 % → 0.92 % | 71 sólida | 30 exigente | baja |
| UNP | 9.14 % | 0.92 | 0.00 % | 71 sólida | 15 → 10 muy exigente | alta |
| KO | 7.95 % | 0.63 | 0.00 % | 79 sólida | 30 exigente | alta |
| WMT | 8.72 % | 0.82 | 0.00 % | 86 excelente | 15 muy exigente | alta |
| XOM | 7.39 % | 0.29 | 0.00 % | 72 sólida | 45 razonable | baja |
| KMI | 7.92 % | 0.63 | 0.00 % | 48 media | 35 exigente | media |
| NEE | 9.04 % | 0.50 | 0.00 % | 49 media | 35 → 30 exigente | media → alta |
| AWK | 7.39 % | 0.41 | 0.00 % | 65 sólida | 35 exigente | media |
| PLD | 8.71 % | 0.81 | 0.00 % | 75 sólida | 40 exigente | alta |
| O | 8.09 % | 0.67 | 0.00 % | 63 media | 58 razonable | baja |
| LIN | 9.05 % → 10.48 % | 0.90 → 1.11 | 0.00 % → 0.55 % | 78 sólida | 10 muy exigente | alta |
| FCX | 9.82 % | 1.08 | 0.00 % | 65 sólida | 42 exigente | baja |
| ASML | 10.19 % → 10.66 % | 1.17 → 1.16 | 0.00 % → 0.49 % | 81 sólida | 35 exigente | baja |
| SAP | 9.40 % → 10.01 % | 0.98 | 0.00 % → 0.60 % | 92 excelente | 31 exigente | media |
| MRNA | 9.85 % | 1.09 | 0.00 % | 31 débil | None None | baja |
| BA | 10.92 % → 11.66 % | 1.34 → 1.36 | 0.00 % → 0.68 % | 29 débil | None None | baja |
| ITUB | 7.39 % → 10.84 % | 0.40 → 0.60 | 0.00 % → 3.01 % | 74 → 76 sólida | 58 → 50 razonable | baja |
| TM | 11.42 % → 12.10 % | 1.46 | 0.00 % → 0.68 % | 55 media | 31 exigente | media |
| SHEL | 7.39 % → 7.82 % | 0.33 → 0.47 | 0.00 % → 0.55 % | 74 sólida | 62 razonable | baja |
| MC.PA | 9.23 % → 9.77 % | 0.94 | 0.00 % → 0.55 % | 74 sólida | 55 → 52 razonable | baja |
| BCS | 10.19 % → 10.74 % | 1.17 | 0.00 % → 0.55 % | 64 → 66 media → **sólida** | 60 → 52 razonable | baja |
| HSBC | 8.84 % → 9.42 % | 0.85 | 0.00 % → 0.55 % | 67 → 66 sólida | 48 → 45 razonable | baja |
| TSM | 10.74 % → 10.90 % | 1.30 → 1.29 | 0.00 % → 0.18 % | 99 excelente | 31 → 28 exigente → **muy exigente** | media |
| NVO | 9.53 % → 10.30 % | 1.01 → 1.19 | 0.00 % | 79 sólida | 62 → 58 razonable | baja |
| AAPL | 9.56 % → 9.55 % | 1.02 | 0.00 % | 85 excelente | 10 muy exigente | alta |

**Lectura:**

- **NU** pasa de «razonable» (45) a **«muy exigente» (20)**:
  - Ke de 7,39 % a 10,84 %, por la prima de Brasil (R1) y la beta de los bancos emergentes (R2b).
  - P/B justificado en dos etapas, que converge al ROE de su industria (R1b): 1,89x frente a 4,52x de mercado (con el
    balance del corte, R3; antes 5,33x frente a 4,68x).
  - Sin compresión del forward, porque no hay CAGR del BPA a 3 años (R1c).
  - La calidad sube de 76 a 83: sin el −2 del margen neto bancario (R4) y sin la penalización por pasar a beneficios
    (R7). Al quitarse la marca de «posible cíclica», la confianza pasa de baja a alta.
- **Cambios de nivel en las 26:**
  - JPM, razonable → exigente: la prima país del 0,39 % (negocio fuera de EE. UU.) baja el P/B justificado de 1,83x a
    1,74x, y el P/B del balance del corte sube de 2,46x a 2,52x: P/B frente a ROE de −2 a −4.
  - TSM, exigente → muy exigente: compresión del forward acotada al +19 % anual de su BPA y prima país.
  - BCS, calidad media → sólida: sin el −2 del margen neto bancario.
- **El resto no cambia de nivel:** la prima país (0,06–0,92 pp en las que venden fuera de EE. UU.) y el forward
  creíble mueven unos puntos.
- **MRNA y BA** siguen sin precio (pérdidas), como antes.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
