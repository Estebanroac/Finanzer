# Diff de los golden · Rediseño E2a (datos del motor)

*Operador E2a, 17-oct-2026. Rama `rediseno/e2a-datos-motor` (worktree `../finanzer_next-e2a`). **Aprobado por el PM
por delegación del usuario (ver «Aprobación»).** Commits `1b51ab9`,
`b514e67`, `cfe937c`, `7125abe` (golden regenerado en su commit) y `a5ee945`, `80ec2c5`, `d03c445`, `f1379d3`, `77a18c4`,
`25d0b00`, `0bdd9bb`, `5e19425`, `2c1b6fb`, `8e7c7b6` (claves aditivas, regeneradas tras la aprobación en el commit
de la Task 11).*

## Resumen en lenguaje llano

- **Cambian tres textos, corregidos donde nacen (en el motor):** (A) la diferencia entre el ROIC y el WACC se escribe en
  puntos porcentuales («spread de +88.4 pp», antes «+88.4%»); (B) la frase «En la frontera con «exigente»…» empieza
  con mayúscula cuando va sola; (C) la bolsa sale con su nombre («Nasdaq», «NYSE», «Euronext París») en vez del
  código del proveedor («NMS», «NYQ», «PAR»). Las cifras son las mismas: solo cambia cómo se escriben.
- **Los 8 tickers de verificación tienen por fin noticias en las pruebas (D):** se grabaron sus titulares reales de
  Finnhub, así que en la web actual y en el PDF de esos 8 aparece el bloque «Titulares recientes», como ya pasa en
  producción. No es un cambio del motor y las noticias no puntúan.
- **Aparecen datos nuevos, sin tocar nada de lo que había (E):** la ficha oficial de la empresa en la SEC, la variación
  del día, la historia de 10 ejercicios, los valores de cada criterio de Piotroski, los supuestos del DCF para los
  escenarios, los próximos resultados, el resumen/imagen/idioma de cada titular y `display.extended` para `/v2`.
- **Ningún veredicto cambia:** 0 cambios en calidad, precio, niveles, confianza, veredicto, Piotroski, Altman y DCF en
  los 42 análisis (36 del panel —SPY se rechaza— y 6 del juego local). Las claves nuevas no cambian ninguna línea del
  PDF.

Regla de la etapa: **ninguna cifra ni veredicto existente cambia.** El golden solo puede cambiar por (a) claves nuevas
aditivas y (b) los tres textos corregidos en origen (T1–T2). Cada diferencia se clasificó con un auditor automático
(normaliza solo la causa del commit y compara: lo que no queda igual es un bug); en cada commit, **0 diferencias sin
explicar**, también en el texto del PDF.

## Por commit

| Commit | Causa | Tickers | Campos | Líneas PDF (±) | Cambios de veredicto |
|---|---|---|---|---|---|
| `1b51ab9` (T1·A) | El spread ROIC − WACC es una diferencia de porcentajes: se escribe en puntos porcentuales («+88.4 pp», no «+88.4%»). Solo la unidad; la cifra es la misma | panel: 23 de 37 (AAPL, MSFT, KO, PG, JNJ, V, NEE, DUK, XOM, FCX, CAT, MU, DOW, NVDA, TSM, ASML, NVO, NFLX, AMZN, SHEL, UL, TM, MC.PA) · local: 3 de 6 (NFLX, FCX, V) | `alerts.{strengths,red_flags}[].reason`, `score.breakdown.Rentabilidad.{adjustments[].reason, adjustments[].value, details[]}`, `display.{charts.profitability.spread.text, readings.roic_wacc_spread.text, readings.pe.text, cover.highlights[].text, sections.profitability.{intro, rows[].text}, sections.valuation.intro, sections.alerts.groups[].items[].reason, sections.institutional.breakdown.categories[].items[].{reason,value}, summary.exec_items[].text}` | panel 335 · local 57 | 0 |
| `b514e67` (T1·B) | La frase de frontera de nivel empieza con mayúscula cuando va sola («En la frontera con «exigente»…»); a mitad de frase (tras «; » o entre paréntesis) sigue en minúscula | panel: 11 de 37 (KO, PG, JNJ, JPM, V, PLD, NEE, DUK, FCX, UL, MC.PA) · local: 2 de 6 (JPM, FCX) | `quality.border.text`, `price_attractiveness.border.text`, `display.cover.{quality,price}.note`, `display.summary.composition.price.note` | panel 24 · local 4 | 0 |
| `cfe937c` (T2·C) | Nombre de la bolsa en lugar del código del proveedor (NMS/NasdaqGS → «Nasdaq», NYQ → «NYSE», PAR → «Euronext París»); el código se conserva en la clave aditiva `profile.exchange_code` | panel: 36 de 37 (todos menos SPY, rechazado) · local: 6 de 6 (texto solo en NFLX; en JPM, O, FCX, SNOW y V el código ya era «NYSE»: solo la clave aditiva) | `profile.exchange`, `display.charts.price_card.exchange` · aditiva: `profile.exchange_code` | panel 72 · local 2 | 0 |
| `7125abe` (T8·D) | **Datos de entrada nuevos, no un cambio del motor:** los fixtures de los 8 tickers de verificación graban por primera vez los titulares de Finnhub (`/company-news`, hasta la hora de la captura de cada ticker) y el calendario de resultados hacia delante. La web actual y el PDF enseñan los 5 titulares que ya enseñan en producción | panel: 8 de 37 (AAPL, JPM, O, NEE, XOM, PLTR, RIVN, BCS) · local: 0 | `market_context.news.{items, total, days, reason}`, `display.sections.market.{news, news_note}` | panel 76 (8 por ticker; RIVN 20: el bloque mueve un salto de página) | 0 |
| D2 (revisión del PM) | **Solo titulares que nombran a la empresa.** Finnhub pone el ticker en `related` de noticias generales del mercado; ahora un titular entra solo si el titular o el resumen nombran a la empresa (ticker como palabra o su nombre corto sin sufijos societarios; listas en config). `total` cuenta los relevantes y la nota dice «que mencionan a la empresa» | panel: 8 de 37 (AAPL, JPM, O, NEE, XOM, PLTR, RIVN, BCS) · local: 0 | `market_context.news.{items, total}`, `display.sections.market.{news, news_note}`, `display.extended.news` | panel 58 (solo el bloque «Titulares recientes») | 0 |
| E1 `a5ee945`, `8e7c7b6` (T3) | Aditiva: ficha del emisor en EDGAR (SIC, sede, constitución, cierre fiscal, tipo de emisor), de la misma respuesta de submissions | panel 36 (35 con ficha; MC.PA `sin_dato` «el emisor no presenta en la SEC»; estados de EE. UU. con su nombre: «Delaware», «Cupertino, California») · local 6 | `company_profile`, `data_provenance.edgar.profile` | 0 | 0 |
| E2 `80ec2c5` (T4) | Aditiva: variación del día frente al cierre anterior (serie de la misma sesión) | panel 36 · local 6 | `price_change` | 0 | 0 |
| E3 `d03c445`, `2c1b6fb` (T5) | Aditiva: historia de 10 ejercicios desde la historia anual de EDGAR (sin red adicional), en la moneda de los estados | panel 36 (29 con 10 ejercicios; 2 con 9, 2 con 8, 2 con 7, dicho en `reason`; MC.PA `sin_dato`; ningún hueco entre ejercicios en el panel: `gap_before` falso en todas las filas) · local 6 | `history_10y` | 0 | 0 |
| E4 `f1379d3` (T6) | Aditiva: Piotroski con el valor actual y el de comparación de cada criterio (los estados y la puntuación, iguales) | panel 36 · local 6 | `piotroski_f.details.*.{cur, prev, unit, compare}` | 0 | 0 |
| E5 `77a18c4` (T7) | Aditiva: los supuestos exactos del DCF del motor para los escenarios del usuario (con ellos, el mismo valor) | panel 36 (21 `ok`; 15 `sin_dato` con el motivo del DCF: bancos, REIT, no significativo…) · local 6 | `scenario_inputs` | 0 | 0 |
| E6 `25d0b00`, `0bdd9bb` (T8) | Aditiva: próximos resultados (anunciados o estimados) y resumen, imagen propia, categoría, fecha y hora e idioma de cada titular | panel 36 (`next_earnings`: 11 anunciadas, 18 estimadas, 7 sin fecha) · local 6 | `market_context.next_earnings`, `market_context.news.items[].{summary, image, category, datetime, lang}` | 0 | 0 |
| E7 `5e19425` (T10) | Aditiva: los datos nuevos formateados para `/v2` (solo datos; la frase de los próximos resultados, declarada al guardián) | panel 36 · local 6 | `display.extended` | 0 | 0 |

### Detalle por causa

**A · spread en «pp».** Cambia en cinco frases del motor (las tres de `alert_interpretations._spread`, las dos de
`display.read_spread`) y además, por la misma causa, en la nota del P/E con respaldo («ROIC−WACC de +x pp»,
`display.read_pe`) y en los motivos del ajuste ROIC vs WACC de la puntuación (`financial_ratios`, que la web actual y el
PDF muestran en el desglose institucional). Formato único: `numfmt.pp` (signo menos tipográfico, como el resto de
cifras). Ejemplo (AAPL): «Crea mucho valor — spread +88.4%» → «Crea mucho valor — spread +88.4 pp».

**B · frontera con mayúscula.** `verdict.border` devuelve la frase con mayúscula inicial (la nota de Precio de JPM en
`/v2` empezaba en minúscula). Donde `display` la pega tras otra frase («sin ajustar 25 → ajustado a 31 por confianza
media; en la frontera…») o dentro del paréntesis del veredicto ejecutivo, se pasa a minúscula allí (`_lc_first`). En
KO, NEE, DUK y FCX solo cambia `*.border.text` (en la web y el PDF la frase va tras «; »). El guardián compara en
minúsculas: su regla `frontera_nivel` no cambia.

**C · nombre de la bolsa.** `lib/exchanges.py` traduce el código de Yahoo con la tabla `[exchanges]` de
`config/market.toml` (un código desconocido se muestra tal cual y queda en el log). `profile.exchange` pasa a ser el
nombre; el código sigue disponible en `profile.exchange_code` (contrato `api.ts`, aditivo). En el PDF cambia la línea de
cabecera «industria · bolsa» (dos líneas de diff por ticker: la antigua y la nueva).

**D · titulares capturados (fixtures).** Hasta ahora el replay no tenía noticias («sin titulares de Finnhub»), así que
ni la web actual ni el PDF las enseñaban en los golden, aunque en producción sí salen. `tests/capture_finnhub_e2a.py`
graba `/company-news` y `/calendar/earnings` con la clave del Llavero en el entorno del comando (nunca escrita: `grep
token= tests/fixtures` vacío) y el replay los sirve por símbolo y ruta, solo los titulares publicados hasta la captura.
En el PDF aparece el bloque «Titulares recientes» (5 titulares, como en producción) en lugar de la frase «sin
titulares». Ninguna cifra, lectura ni veredicto se mueve (los titulares no puntúan, D5). Este golden se regeneró sin
las claves aditivas de E2a (llegan todas juntas en la Task 11).

**D2 · titulares que nombran a la empresa (revisión del PM de las capturas).** En AAPL el capítulo 8 enseñaba «CPI
Pressures Markets…» y «Reese Witherspoon Buys Back Production Firm…»: Finnhub incluye AAPL en `related` de noticias
del mercado. `market_context.news` filtra ahora por mención (`mention_terms`: «Apple»; «Exxon Mobil», «ExxonMobil» y
«Exxon»; «JPMorgan Chase» y «JPMorgan»; «Realty Income» completo, porque «Realty» sola es palabra común; un ticker de
una letra, como O, solo cuenta como «(O)» o «NYSE: O»). Con el filtro, ningún ticker se queda sin titulares en 7 días
(24–120 relevantes), así que no hace falta ampliar la ventana de `/v2` (`news_days_v2` no se añade). En el PDF solo
cambia el bloque «Titulares recientes» (comprobado quitando el bloque en los dos textos: iguales en los 8).

| Ticker | Relevantes (antes → ahora) | Salen de los 5 de la web y el PDF | Entran |
|---|---|---|---|
| AAPL | 63 → 29 | CPI Pressures Markets And Fed Reserve's Move On Interest Rates · Reese Witherspoon Buys Back Production Firm With Mediawan · A $1,000 Investment in This AI Stock Became $22,715… · GlobalFoundries Stock Extends Rally on Chip Deal… | Apple Stock May Be Peaking After Hitting New All-Time Highs · Gene Munster Warns Apple Can Sell Millions of iPhones… · Elon Musk's SpaceX Just Announced Good (and Bad) News to Apple Shareholders · OpenAI Accuses Apple Hire Of Taking 100+ Confidential Files… |
| JPM | 175 → 97 | Chase Brings AI Fraud-Fighting Advice… · Givaudan (SWX:GIVN) Stock Gets Fair Value Bump… · Jim Cramer talks what is driving moves in Big Banks… · Bank of America: Huge Fine Makes Shares Slump · Citi Says the S&P 500 Hits 8,100… | Final Trade: DAL, QQQ, JPM, ASML · This bank has more upside than JP Morgan… · JPMorgan rounds up partners · JPMorgan's Q3 Miss Is Noise, But Tread Carefully · JPMorgan Addresses 'Rogue Agents'… |
| O | 80 → 33 | Citi Says the S&P 500 Hits 8,100… · These 4 High-Yield Dividend Stocks Have Something Yield Traps Don't… | Better High-Yield Dividend Stock: Realty Income vs. MPLX · … Realty Income vs. Kraft Heinz |
| NEE | 53 → 24 | Citi Says the S&P 500 Hits 8,100… · Here's What to Buy After Hot CPI… · Can Renewable Energy Expansion Support CEG's Long-Term Growth? | NextEra Energy (NEE) Earnings Expected to Grow… · Morgan Stanley Maintains Overweight on NextEra Energy… · Governance Settlement And Earnings Expectations… NextEra Energy (NEE) |
| XOM | 87 → 34 | Stock Market Today: Nasdaq Hit As Inflation Runs Hot… · What Did Valero Stock Investors Miss Before The Run? | Chevron vs. ExxonMobil: Which Energy Stock Is a Better Buy in 2026? · ExxonMobil (XOM): Can Its Chemical Recovery Survive… |
| PLTR | 184 → 120 | Sector Update: Tech Stocks Fall Wednesday Afternoon · Michael Burry Says Stocks Could Peak Within 9 Months… | Is Palantir's AIP Platform Fueling Explosive U.S. Commercial Growth? · Palantir's AI Opportunity Could Be Bigger Than Investors Think |
| RIVN | 42 → 27 | Electric vehicle sales in the US are showing signs of life · Tesla to Post Q3 Earnings… | Rivian Expands Collaboration With Redwood Materials… · Rivian spinoff Mind Robotics hires ex-Ford EV chief Doug Field |
| BCS | 32 → 27 | — (los 5 ya nombraban a Barclays) | — (solo cambia la nota) |

Cambios de veredicto de D2: **0** (el auditor no encuentra ninguna diferencia fuera de las rutas de noticias).
**Aprobada por el PM** en su revisión de las capturas: «Golden: cambia la causa D (noticias de los 8). Añade la causa D2
en `GOLDEN_DIFF_E2A.md`, con los titulares que salen y los que entran por ticker, y 0 cambios de veredicto. Queda
aprobada por el PM con esta revisión.»

**E · claves aditivas.** El auditor del diff completo (`diff_golden.py --full` en panel y local, clasificado campo a
campo) da **13 293 diferencias en el panel y 2 157 en el local, todas claves nuevas** de la lista E1–E7, **0 valores
existentes cambiados y 0 líneas de PDF**. Mientras tanto, `tests/test_regression.py` ignora esas claves con la lista
temporal `E2A_ADDITIVE` (y `test_frontend_contract.py` en las muestras forzadas); la Task 11 la retira al regenerar.

## Cambios de veredicto: 0

Comprobado sobre la salida actual frente a los golden, en los 42 análisis (36 del panel —SPY se rechaza— y 6 del
juego local), campo a campo: `quality.score`, `quality.level`, `price_attractiveness.{score, score_raw, level}`,
`confidence.level`, `verdict.text`, `score.total`, `piotroski_f.score`, `altman_z.z_score` y `dcf.fair_value`:
**0 diferencias**.

## Aprobación

Aprobado por el PM (sesión planificadora) por delegación del usuario, 2026-10-17. Literal del usuario: «recuerda, que
esto se autoapruebe. confío plenamente en ti. no me vuelvas a avisar hasta que todo el plan esté 100% hecho». Literal
del PM: «Apruebo el golden de E2a: causas A–D y claves aditivas E; 0 cambios de veredicto verificados de forma
independiente en 43 golden.»

Tras la aprobación (Task 11): retirada la lista temporal `E2A_ADDITIVE` (`test_regression.py` y
`test_frontend_contract.py` vuelven a su versión de `main`), golden regenerado en panel y local y muestras forzadas
reescritas: cambian 46 JSON, **ningún `.pdf.txt`**. El test de equivalencia de los escenarios compara ya contra el golden
(21 tickers con DCF significativo). Suite del backend: 4271 passed, 1 skipped; `npm run check`: el contrato encaja con
las 46 salidas.
