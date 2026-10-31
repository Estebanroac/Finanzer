# Diff de los golden · V7 · textos del motor (revisión de lector nuevo)

*Sesión E4, 18-oct-2026. Rama `rediseno/e4-portada`. **Aprobado por el PM por delegación del usuario (ver
«Aprobación»).** Un commit por causa (M1–M7 de `docs/rediseno/verificacion/V7_lector_nuevo.md`), con el golden
regenerado en el commit de cada causa.*

## Resumen en lenguaje llano

Un lector nuevo encontró frases del informe que **decían algo falso**, **mezclaban periodos**, **usaban etiquetas que
contradecían su número**, **enseñaban la mecánica interna** o **mezclaban inglés y español**. Se corrigen donde nacen,
en el motor, así que las ven a la vez la web actual, `/v2` y los dos PDF: es una mejora de fiabilidad también para la
web actual. **Ningún veredicto ni cifra cambia:** solo cambian textos.

Cada causa se audita con un comparador automático:
- frente al golden, ningún campo numérico cambia, solo textos;
- 0 diferencias en los campos de veredicto: `quality.{score, level}`, `price_attractiveness.{score, score_raw,
  level}`, `confidence.level`, `verdict.{text, confidence}`, `score.total`, `piotroski_f.score`, `altman_z.z_score`,
  `dcf.fair_value` y `classification.archetype`.

## Por causa

| Causa | Commit | Tickers (panel · local) | Campos | Líneas PDF actual (+/−, panel · local; `git diff`) | Líneas PDF nuevo | Cambios de veredicto |
|---|---|---|---|---|---|---|
| M1 · el % del DCF dice lo que dice la frase | d97fe55 | 15 de 37 · 2 de 6 | 89 · 12 | +99/−92 · +12/−12 | 15 tickers (35 frases) | 0 |
| M2 · cada cifra con su periodo | 6e4f2fd | 33 de 37 · 5 de 6 | 765 · 113 | +580/−537 · +88/−81 (casi todo reflujo) | 33 tickers | 0 |
| M3 · etiquetas coherentes con el número | ca7259c | 36 de 37 · 6 de 6 | 192 · 33 | +154/−152 · +26/−26 | 36 tickers | 0 |
| M4 · sin mecánica interna en los textos del lector | 0b83184 | 36 de 37 · 6 de 6 | 570 · 86 | +508/−433 · +64/−57 (casi todo reflujo) | 36 tickers | 0 |
| M5 · nombres que dicen qué puntúa | e8fa669 | 28 de 37 · 5 de 6 | 112 · 19 | +111/−68 · +24/−17 | 22 tickers | 0 |
| M6 · arquetipos en positivo y etiquetas en español | 4f86cec | 36 de 37 · 6 de 6 | 1352 · 198 | +724/−660 · +110/−99 | 36 tickers | 0 |
| M7 · rentabilidad total del mercado y periodo real de la serie | de05dbe | 0 de 37 · 0 de 6 (no toca el análisis) | 0 | 0 | 0 | 0 |
| M5 bis · una sola verdad del DCF (revisión del PM) | eb02c65 | 36 de 37 · 6 de 6 | 72 · 13 | +127/−115 · +18/−17 | 36 tickers | 0 |
| P · puntuación del motor (revisión del PM) | e310768 | 36 de 37 · 6 de 6 | 2558 · 419 | +757/−756 · +115/−115 | 36 tickers (+897/−874) | 0 |
| N · industrias y sectores en español (revisión del PM) | b317174 | 36 de 37 · 6 de 6 | 649 · 107 | +163/−100 · +36/−25 | 36 tickers (+647/−570) | 0 |

### M1 · el porcentaje del DCF dice lo que dice la frase (afirmación falsa)

- **Qué fallaba.** El upside es (valor − precio) / precio. Con el valor por debajo del precio, las frases decían «el
  precio excede en 66 % el valor intrínseco» o «el precio está un 28 % por encima del valor». Ese 66 % es cuánto está
  el valor por debajo del precio; el precio excede al valor en precio / valor − 1. En AAPL, $343 frente a $116, el
  precio lo excede en un 195 %, no en un 66 %.
- **Ahora.** «El valor intrínseco estimado ($116.08) está un 66 % por debajo del precio ($342.96)», con las dos
  cifras. Afecta a la lectura del DCF (`display.read_upside`: «Prima» y «Sobrevalorada») y a las alertas
  (`alert_interpretations._dcf`).
- **«Margen de seguridad».** Sale de la prosa de la alerta («habría colchón entre el precio y el valor estimado…»).
- **Las frases con el valor por encima del precio** («un 12 % por encima del precio», «potencial teórico de +12 %»)
  ya eran correctas y no cambian.
- **Graham.** Correcto: su margen es (Graham − precio) / Graham y las frases dicen cuánto cotiza por encima o por
  debajo de ese número.
- **Guardián.** El predicado `dcf_upside` comprueba el % de cada frase:
  - «el valor está un N % por debajo del precio» debe ser |upside|, con upside negativo;
  - «el precio excede en N %», «está un N % por encima del valor» o «prima de N % sobre el valor» debe ser precio /
    valor − 1.
  - Tests en `test_guardian_detecta.py`: la frase vieja de AAPL falla y la nueva pasa. Guardián del panel en verde.

### M2 · cada cifra de la prosa con su periodo, en el mismo renglón

- **Qué fallaba.** El lector veía cifras de periodos distintos sin saberlo:
  - el ROE de 119.9 % de la ficha (TTM) y el de 151.9 % del DuPont (FY2025) de AAPL;
  - en PLTR, 27.3 %, 23.6 % y 33.4 % de crecimiento en el mismo bloque;
  - el margen FCF − SBC de 41.0 % (TTM) junto al de 31.7 % (FY2025);
  - el ROE normalizado de 17.5 % de JPM junto al de 18.0 % de la ficha.
- **Ahora**, cada cifra lleva su periodo al lado:
  - ROE: «el ROE (TTM) de 119.9 %», «ROE excepcional — 119.9 % (TTM)», «ROE de FY2025: 151.9 % = margen neto…».
    Con el beneficio normalizado: «ROE normalizado elevado — 17.5 % (TTM, sin partidas no recurrentes)». Sin 4
    trimestres consecutivos: «(último ejercicio)». La salud financiera de los bancos: «ROE normalizado (TTM)
    excelente (17.5 % ≥ 12 %)».
  - Crecimientos a 3 años con su ventana: «crece 6.9 % anual en 3 años (FY2022–FY2025)». En las alertas, la ventana
    va en el detalle («anual en tres años (FY2022–FY2025, CAGR)») y el titular sigue con «(3 años)»: el titular va a
    la portada del PDF, y con la ventana la de MC.PA se encogía por debajo del 85 % (`test_pdf_geometry`).
  - La alerta de PLTR decía «los ingresos crecen 27.3 %»: es el crecimiento **por acción** (32.9 % agregado ajustado
    por un 4.4 % anual de acciones nuevas). Ahora dice «ingresos por acción».
  - Clasificación: «23.6 % anual a 3 años (FY2022–FY2025; acciones diluidas medias; desde la ruptura del capital de
    FY2021)». Es la misma ventana que el 27.3 %, pero con las acciones diluidas medias de EDGAR en lugar de las
    acciones al cierre de Yahoo: por eso difieren, y ahora se ve.
  - Historia propia del DCF inverso y del pre-mortem: «33.4 % anual en 7 años (FY2018–FY2025)».
  - Regla de 40: «crecimiento de ingresos por acción 27.3 % (anual, FY2022–FY2025) + margen FCF − SBC 41.0 % (TTM)».
  - Coste de la SBC: «el 13.6 % de los ingresos (TTM)… el margen FCF (TTM) baja del 54.6 % al 41.0 %». El 31.7 % de
    FY2025 ya llevaba su ejercicio.
- **Campos nuevos (texto, sin cifras):**
  - `growth_basis.revenue_window`;
  - `classification.inputs.growth_profitable.window_3y` / `window_5y`;
  - `reverse_dcf.main.own_growth.window`.
  No hay otros cambios no textuales.
- **PDF.** Las líneas del PDF actual cambian sobre todo por reflujo: una frase más larga empuja el resto del párrafo.
- **De paso.** `test_config_literals` vigilaba `_compute_analysis`, que desde el commit de la moneda solo envuelve a
  `_compute_analysis_body`: ahora vigila el cuerpo (sin literales nuevos; la excepción del 3 de los CAGR sigue
  haciendo falta).
- **Guardián.** Dos reglas nuevas:
  - `periodo_roe`: un ROE con cifra en la prosa lleva «(TTM», «último ejercicio» o «FY…» al lado. No aplica a las
    gráficas, que rotulan aparte, ni al ROE hipotético del DCF inverso («con un ROE del 21.6 %»).
  - `ventana_crecimiento`: la ventana citada en un crecimiento a 3 años es la de los estados.
  - Tests: `test_guardian_detecta.py::test_roe_and_growth_say_their_period` y
    `test_quality_readings.py::test_rule_of_40_and_sbc_cost_say_their_period`.

### M3 · etiquetas coherentes con el número

- **«FCF estable (-3.9%)».** El tramo del score (entre −5 % y +5 %) se llamaba «estable» aunque el FCF cayera.
  - Ahora la palabra sigue al signo: «FCF en ligero descenso (-3.9%)».
  - Hasta −2 % (la tolerancia de lo plano del motor) sigue siendo «estable».
  - Los puntos del tramo no cambian.
- **KPI «En rango» sin referencia.** Sin cifra con la que comparar, la tarjeta dice «Sin referencia» (AAPL: ROE,
  FCF yield y crecimiento).
- **La deuda con vocabulario de deuda.** En la comparativa con la industria, Deuda / Equity se leía con las
  palabras de un múltiplo de precio («descuento profundo», «prima elevada»). Ahora dice «muy por debajo», «por
  debajo», «en línea», «por encima» o «muy por encima» (`read_vs_sector(level=True)`). Los tonos no cambian.
- **Piotroski en su categoría.** La alerta «Fortaleza financiera excepcional — Piotroski 8/9» estaba en
  «Crecimiento». Pasa a «Solidez financiera», como su texto.
- **Cobertura reconciliada.**
  - El score dejaba la cobertura «sin dato» y la lectura decía «el EBIT cubre 40.7 veces». La lectura usa los
    intereses pagados del estado de flujos, porque la cuenta de resultados no separa el gasto por intereses.
  - Ahora lo dice así: «Cobertura con los intereses pagados en FY2023 (estado de flujos): la cuenta de resultados no
    separa el gasto por intereses, así que el score deja la cobertura sin dato y esta cifra solo informa: …».
  - El texto viejo decía «del último ejercicio», pero el ejercicio con intereses pagados era FY2023 (AAPL) o FY2022
    (PLTR). Ahora se nombra.
- **Cobertura, más casos.**
  - Las cifras llevan su periodo: «el EBIT (TTM)», o «(último ejercicio)» sin 4 trimestres.
  - Por encima de `coverage_display_max` (100, en config) se lee «más de 100 veces» (PLTR decía «526930.4 veces»).
  - Un EBIT negativo «no cubre los intereses» (CRWD decía «cubre −5.0 veces»).
- **Guardián.**
  - Reglas `etiqueta_signo` («estable» con una caída mayor que la tolerancia) y `kpi_sin_referencia`.
  - `vs_bench` reconoce «por encima» y «por debajo».
  - Invariante: la deuda de la comparativa no se lee con «descuento» ni «prima».
  - Test `test_labels_follow_the_number`.

### M4 · sin mecánica interna en los textos del lector

- **Bloque de múltiplos.**
  - Antes: «promedio de los ajustes reescalados a ±1 (…) = −0.53 × 6 (máximo con 5 miembros) = −3.2».
  - Ahora: «media de las lecturas de 5 múltiplos en una escala de −1 a +1 (P/E −0.50, …): −0.53, que suma −3.2 puntos
    de un máximo de ±6».
  - La fórmula (× máximo con N miembros, redondeo) va al anexo técnico («Fórmula del bloque»), desde un campo nuevo
    `formula` de la fila del bloque. Es el único cambio no textual de esta causa: un campo nuevo, sin cifras que
    cambien.
- **«grid».** «El grid completo (68.77–218.01) no contiene el precio (342.96)» pasa a «la tabla de sensibilidad del
  DCF (de $68.77 a $218.01) no contiene el precio ($342.96)», con la moneda. Igual en:
  - «el precio está en el grid pero fuera del caso base ±1» → «… dentro de la tabla de sensibilidad del DCF, pero
    fuera de las casillas que rodean al caso base»;
  - «Grid asimétrico» → «Tabla asimétrica».
- **Tipo sin riesgo.** «Rf: ^TNX no disponible (sin cotización): valor de config» pasa a «el rendimiento del bono del
  Tesoro de EE. UU. a 10 años no está disponible (sin cotización): se usa el valor de referencia del modelo, 5.29 %».
  Con cotización: «Rf: rendimiento del bono del Tesoro de EE. UU. a 10 años, <fecha de la cotización>».
- **Ajuste por confianza.**
  - «Contrae el atractivo del precio hacia 50 (factor 1.0): sin ajustar 15 → ajustado a 15» desaparece cuando no
    ajusta nada.
  - Cuando ajusta: «Contrae el atractivo del precio hacia 50: de 30 a 35».
  - La nota del precio: «ajustado de 30 a 35 por confianza media» (antes «sin ajustar 30 → ajustado a
    35…»).
- **Web `/v2` (página Cuánto vale, presentación de E3).**
  - Las etiquetas de los múltiplos («P/E: en el bloque de múltiplos») iban pegadas sin espacio: el texto se leía
    «…múltiplosForward P/E». Ahora van separadas.
  - La nota de metodología de los escenarios ya no cita «endpoint /api/v2/scenario».
- **Guardián.** Regla `mecanica_interna` sobre la prosa y el PDF fuera del anexo: «grid», «config», «endpoint», «^TNX»,
  «máximo con N miembros», «(factor …» y «sin ajustar N». Test `test_reader_texts_without_internal_mechanics`.

### M5 · nombres que dicen qué puntúa de verdad

- **Qué fallaba.** La cabecera y el desglose decían «DCF (upside) −66 % … −4», mientras otro bloque decía que el DCF
  directo no concilia y no se usa: lo que puntuaba era el DCF inverso.
- **Ahora** la fila del DCF se llama según lo que puntúa:
  - «DCF inverso (lo que exige el precio)» con su lectura («muy exigente», «barata»), no el −66 % del directo
    (AAPL, MSFT, SHEL…);
  - «DCF directo (valor frente al precio)», con su +16 %, cuando el directo es fiable y puntúa (XOM);
  - «DCF directo: descartado, no puntúa» con fiabilidad baja y sin inverso;
  - «DCF directo: no puntúa · No significativo» cuando el FCF − SBC no lo permite (SNOW).
  - La fila lleva `key: "dcf"`, así que el código ya no la busca por su nombre. Es el único cambio no textual: un
    campo nuevo.
  - Los puntos no cambian.
- **P/B de los bancos.** «P/B: informativo, no puntúa» aparecía junto a «Bloque P/B y P/TBV −2». El que puntúa es el
  P/B frente a su ROE; el informativo es el P/B frente a la industria, y ahora se llama así (JPM, BAC, HSBC…). Cada
  bloque tiene un único criterio: el P/B justificado por la rentabilidad.
- **Guardián.** Regla `nombre_puntua`:
  - una fila que puntúa con el DCF inverso se llama «DCF inverso…»;
  - una fila del DCF que no puntúa lo dice en el nombre.
  - Test `test_scoring_names_say_what_scores`.

#### Una sola verdad del DCF (AAPL) · revisión del PM

- **Pregunta del PM.** La tarjeta «Atractivo del precio» mostraba «DCF (upside) −4» como fila que puntúa, y la
  confianza decía que el DCF no es evaluable. ¿Puntúa o no?
- **La real: el −4 puntúa, y es del DCF inverso.** El DCF directo no puntúa ni cuenta para la convergencia. Números del
  replay del panel:
  - DCF directo: valor razonable $116.08 frente a $342.96 de precio (−66 %). Fiabilidad **baja**: la tabla de
    sensibilidad (de $68.77 a $218.01) no contiene el precio. **No puntúa** y en la convergencia es «no evaluable:
    DCF (fiabilidad baja)».
  - DCF inverso: el precio exige un crecimiento «muy exigente» → **−4** en Valoración. Ocupa el sitio del directo como
    método intrínseco (fase 3, T3).
  - Valoración = base 10 − 3 (bloque de 5 múltiplos: P/E −2, Forward P/E +1, P/FCF −4, EV/EBITDA −2, PEG −3, que
    puntúan a través del bloque) − 4 (DCF inverso) = **3/20** → atractivo del precio **15/100** («muy exigente»).
    Confianza alta, factor 1.0: no contrae (15 → 15).
  - Convergencia **alta**: el DCF inverso (−1.00, cara) y los múltiplos (−0.53, cara) coinciden (distancia 0.47 <
    0.6); el directo queda fuera.
- **Lo que fallaba era el nombre**, no la cifra: antes de M5 la fila se llamaba «DCF (upside) · −66 %» y llevaba el
  −4 del inverso. Desde M5 (e8fa669) se llama «DCF inverso (lo que exige el precio) · muy exigente −4». La v4
  (fusión de prueba hasta 0b83184, M4) y los fixtures de `frontend/src/v2/__fixtures__` (E2a) son anteriores a M5:
  por eso aún se ve «DCF (upside)» allí. Al fusionar M5 y regenerar los fixtures, desaparece.
- **Ahora las tres piezas lo cuentan igual** (commit de esta sección):
  - Tarjeta y PDF (composición del precio): «Bloque de múltiplos · 5 múltiplos −3» y «DCF inverso (lo que exige el
    precio) · muy exigente −4».
  - «Confianza del veredicto», texto del veredicto (`verdict_text`, el que usa P1 de E3): «confianza alta: DCF
    inverso y los múltiplos coinciden».
  - «Confianza del veredicto», línea de la sección 01 de la web y del PDF (`display.confidence.summary`), antes
    «alta. La calidad del negocio no se contrae.»; ahora: «Confianza del veredicto: alta. El DCF directo, de
    fiabilidad baja, no puntúa ni cuenta para la convergencia; en Valoración puntúa el DCF inverso (−4 puntos). La
    calidad del negocio no se contrae.»
  - Tabla de dimensiones: «DCF directo −66 % (cara, no evaluable) · DCF inverso −1.00 (cara) · múltiplos frente al
    sector −0.53 (cara)…», y «El DCF directo no concilia con el precio…» (antes «DCF» a secas).
  - De paso, el resumen ejecutivo («CONFIANZA DEL VEREDICTO») decía siempre «Contrae el atractivo del precio hacia
    50», también con factor 1.0. Ahora solo lo dice cuando contrae, con las cifras; si no, «No contrae el atractivo
    del precio ni la calidad».
- **Guardián.** Regla `una_verdad`, con el DCF directo de fiabilidad baja:
  - la tarjeta no lo presenta como fila que puntúa;
  - la línea de confianza dice que no puntúa;
  - si puntúa el inverso, la línea de confianza da la misma cifra que la tarjeta.
  - Test `test_one_truth_about_the_dcf`.
- **Golden.** 36 de 37 · 6 de 6 tickers, solo textos (la tabla de dimensiones y, con DCF de fiabilidad baja, la línea
  de confianza). PDF actual +127/−115 · +18/−17; PDF nuevo +509/−464 en 36 tickers (reflujo incluido). 0 cambios
  de veredicto.

### M6 · arquetipos definidos en positivo, etiquetas en español y sin duplicados

- **Arquetipos en positivo.**
  - Antes, «Madura: no es un banco ni una aseguradora, ni un REIT, ni una empresa en crecimiento sin beneficio, ni
    cíclica, ni de crecimiento rentable».
  - Ahora: «Madura: negocio establecido que se valora sobre todo por la caja que genera hoy; sus ingresos por acción
    crecen un 4.7 % anual en 3 años (FY2022–FY2025), por debajo del 15 % del crecimiento rentable; en 19 ejercicios
    su historia no muestra ciclo (Consumer Electronics)». Si caen, dice «caen» (UL).
  - El REIT: «REIT: sociedad inmobiliaria cotizada que reparte casi todo su beneficio y se mide por sus fondos de
    operación (FFO); industria REIT - Retail».
  - Cada arquetipo tiene su definición en positivo en config (`sectors.archetypes.definitions`) y en el análisis
    (`classification.definition`, campo nuevo de texto), para que la presentación (E3) la muestre donde quiera.
- **Traducción de las etiquetas del motor** (nombres de filas del desglose y motivos):

  | Antes | Ahora |
  |---|---|
  | Cash Flow Operativo | Flujo de caja operativo |
  | Free Cash Flow | Flujo de caja libre |
  | FCF / Net Income | FCF / beneficio neto |
  | Current Ratio | Liquidez corriente |
  | Crecimiento Ingresos 3Y, Crecimiento EPS 3Y, Crecimiento FCF 3Y | Crecimiento de ingresos, del BPA o del FCF «a 3 años» (en las cíclicas, «de ciclo medio», que es lo que puntúa) |
  | EPS moderado, sólido… | BPA moderado, sólido… |
  | P/E vs Sector, EV/EBITDA vs Sector, ROIC vs WACC | P/E frente al sector, EV/EBITDA frente al sector, ROIC frente al WACC |
  | PEG Ratio | PEG |
  | Premium (39.3x vs 34.3x) | Prima (39.3x frente a 34.3x) |
  | FCF > Net Income, FCF sólido vs ganancias | FCF mayor que el beneficio neto, FCF sólido frente al beneficio |
  | Margen Neto, Margen Operativo, Cobertura Intereses, Solidez Bancaria | en minúscula y con «de» |
  | compañías growth | compañías de crecimiento |
  | EPS (cifras del ejercicio) | BPA |

  - Las filas de crecimiento se buscan por su comienzo (`financial_ratios.by_prefix`), no por el nombre exacto.
  - La fila sin cifra «FCF / beneficio neto: No significativo» sigue sin rotularse «normalizado», como antes.
- **Rango de 52 semanas sin repetir.**
  - La posición («cotiza en el 95 % del rango…») ya la dice la lectura: la leyenda queda en «Precio actual $342.96.».
  - Que es contexto de mercado lo dice el eje: la nota de tramos queda en «Tramos: mínimos, parte baja, zona media,
    parte alta y máximos.».
- **Corrección de M2.**
  - Las ventanas de EDGAR tomaban el año de la fecha de cierre. Un ejercicio de 52/53 semanas que cierra en la
    primera semana de enero es del año anterior: JNJ decía «FY2023–FY2025» para 3 años y ahora dice
    «FY2022–FY2025» (`cyclicality.fy_label`).
  - El crecimiento rentable pone cada ventana junto a su cifra: «16.2 % anual en 3 años (FY2023–FY2026) y 15.0 % a 5
    (FY2021–FY2026), sobre acciones diluidas medias». Antes, la ventana de 3 años iba detrás del 5.
- **Guardián.**
  - `ventana_crecimiento` acepta también la ventana de EDGAR de la clasificación, que puede diferir de la de los
    estados de Yahoo.
  - Regla `anglicismo`: «Cash Flow», «Net Income», «EPS», «Premium», «PEG/Current Ratio», «3Y» y «compañías
    growth» en la prosa y el PDF fuera del anexo. «Ratio combinado» (término español de seguros) y los nombres propios
    («Piotroski F-Score», «Altman Z-Score») quedan fuera. Test `test_engine_labels_in_spanish`.

### M7 · rentabilidad total del mercado con dividendos, y el periodo real de la serie

- **Qué fallaba.** En «Rentabilidad por periodo» (`/v2/{T}/accion`) y en la tabla de la gráfica de la portada, la
  columna del S&P 500 «con dividendos» repetía la de precio (+72,0 % a 5 años). El índice ^GSPC no reparte
  dividendos: su cierre ajustado es el de precio.
- **Ahora**, `/api/v2/prices` lleva la rentabilidad total del mercado:
  - sale del cierre ajustado de SPY, el ETF que replica el índice, en la escala del índice desde su primera sesión;
  - el símbolo está en config: `market.history.market_total_return_symbol = "SPY"`, o `^SP500TR`;
  - el `c` de cada punto sigue siendo el índice (rentabilidad de precio) y el `a` es la rentabilidad total;
  - el mercado lleva `total_status`, `total_symbol` y `total_note`, y la nota bajo la tabla lo dice: «S&P 500 con
    dividendos: rentabilidad total de SPY, el ETF que replica el índice (cierre ajustado por dividendos); el índice
    solo mide el precio».
- **Resultado (AAPL, replay del panel).** En la serie entera (5 años), el S&P 500 sube un 70,7 % de precio y un
  82,5 % con dividendos; antes las dos columnas decían lo mismo.
- **Sin la serie de SPY.** `total_status: "sin_dato"` con el motivo, y la web dice «Sin dato» en la columna con
  dividendos, nunca la de precio con esa etiqueta (`seriesReturns`). Si el índice cae y se usa SPY como respaldo, su
  cierre ajustado ya lleva dividendos.
- **El periodo real.** La página citaba como fuente de la tabla la serie de las señales («cierre ajustado por
  dividendos y splits, 2 años»), pero las tablas de 3A y 5A salen de la serie de la gráfica, de 5 años.
  - El payload lleva `source`: «Serie diaria de Yahoo Finance de 5 años (del 2021-10-18 al 2026-10-16): …».
  - La metodología muestra las dos fuentes con su nombre: «Serie de la gráfica y las rentabilidades» y «Serie de las
    señales» (esta sí es de 2 años).
- **Coste.** Una descarga más por proceso: SPY, con la misma caché y el mismo turno acotado que la gráfica. El
  payload no crece: la serie de SPY no se envía, solo cambia el `a` del índice.
- **Golden.** Ni el análisis ni los PDF cambian, así que no hay diff.
- **Tests.**
  - `test_prices_v2.py`: rentabilidad total desde SPY con sesiones que faltan, SPY caído, SPY como respaldo del
    índice, y el endpoint con `source` y la descarga de SPY.
  - `chartEvents.test.ts`: «Sin dato» sin la serie con dividendos.
- **Páginas de E3.** Toca `Accion.tsx`, `PriceChart.tsx`, `lib/prices.ts` y `lib/chartEvents.ts`; en M4, `Valor.tsx`.

### P · puntuación del motor: uniones sin «.;» y frases con su punto

- **Qué fallaba (KO).** La nota de calidad unía dos frases con «; » sin quitar el punto de la primera y no cerraba la
  segunda: «…FCF positivo en 3 de 5 ejercicios.; en la frontera con «sólida» (a 2 puntos): … cambiaría el nivel». En
  general, el mismo campo acababa unas veces en punto y otras no (en la tabla de señales de mercado, 83 de 277 filas
  con punto), y las webs y los PDF no podían saber si cerrarlo.
- **En el origen.** `lib/prose.py` declara una sola vez qué es cada texto de `display`:
  - **frase**: acaba en «.», «)», «»», «…», «?» o «!». El generador la cierra al final de `build_display`
    (`close_sentences`).
  - **etiqueta**: nombre, valor, lectura corta, título o rango; también todo texto de 3 palabras o menos.
  - **titular**: titular corto que encabeza un detalle (alertas, «Qué vigilar», veredicto).
  - **fragmento**: va dentro de otra frase que cierra quien la compone (modelos de la metodología, puntos del
    pre-mortem, motivo de «Sin noticias recientes:»).
  - **externo**: noticias y ficha de la SEC.
- **Uniones.** `join_clauses` quita el punto de cada parte antes del «; » y cierra el conjunto. La usan la nota de
  calidad y la del precio. KO, ahora: «…FCF positivo en 3 de 5 ejercicios; en la frontera con «sólida» (a 2 puntos):
  un cambio pequeño en los datos o en los supuestos cambiaría el nivel.»
- **Consumidores.** Cierran solo lo que llega sin cerrar, para no producir «..»:
  - PDF nuevo: rango de 52 semanas (`chapters.py`, con `_dot`);
  - web actual: `charts.tsx`, `GrowthTab.tsx` e `InstitutionalTab.tsx`, con `closeSentence` de `src/lib/prose.ts`.
  - Ninguna página de E3 cambia.
- **Guardián** (web y PDF, anexo incluido):
  - `puntuacion_doble`: ningún «.;», «;.» ni «..» en los textos del panel ni en el texto de los dos PDF;
  - `frase_sin_cierre`: cada frase declarada acaba en su puntuación, y un texto de 4 palabras o más sin declarar
    en `lib/prose.py` falla.
  - Tests: `test_prose.py`, `test_punctuation_of_the_whole_panel` y el e2e `e2e/v2/puntuacion.spec.ts`. Este recorre la
    web actual (9 pestañas) y las 10 páginas de `/v2` de KO, AAPL, JPM, O, TM y RIVN.
- **Golden.** 36 de 37 · 6 de 6 tickers. Cambian 2558 · 419 campos, casi todos por el punto final de lecturas, filas,
  motivos del desglose y criterios de Piotroski. PDF actual +757/−756 · +115/−115; PDF nuevo +897/−874. Ningún campo
  numérico cambia y hay 0 cambios de veredicto.

### N · industrias y sectores en español

- **Qué fallaba.** La prosa y las fichas usaban el nombre de la fuente:
  - «The Coca-Cola Company opera en Beverages—Non-Alcoholic (Consumer Defensive)»;
  - «industria REIT - Retail»;
  - «…no muestra ciclo (Consumer Electronics)»;
  - «Referencia: industria «Computers/Peripherals»»;
  - la cabecera de los dos PDF y de las dos webs: «Technology · Consumer Electronics».
- **Tablas de traducción en config.** `config/names.toml`, que lee `lib/names.py`:
  - las 96 industrias de Damodaran de `config/industries.toml`, todas las regiones, incluido «Total Market (without
    financials)» → «Mercado total (sin financieras)»;
  - los 11 sectores de Yahoo y los 11 sectores GICS del universo;
  - las industrias de Yahoo (lista completa, no solo las del panel). Yahoo las escribe con raya o con guion, y
    `lib/names.py` normaliza las dos formas.
  - Sin traducción, se usa el original: el análisis nunca se bloquea.
- **Dónde se usa el español:**
  - cabecera de los dos PDF y de las dos webs: «Consumo defensivo · Bebidas sin alcohol»;
  - «opera en bebidas sin alcohol (consumo defensivo)» (capítulo «empresa» de `/v2` y del PDF nuevo);
  - ficha de `/v2` sin EDGAR;
  - notas de clasificación: «Banco por su industria (Bancos diversificados)», «industria REIT de locales comerciales»;
  - referencia de la comparativa: «industria «Ordenadores y periféricos»»;
  - fuentes de la referencia de mercado.
  - `display.profile` lleva el sector y la industria en español; el perfil de la fuente (`profile`) no cambia y el
    clasificador sigue usándolo.
- **El original, solo en la metodología y en el anexo.** Nuevo apartado del anexo, «Nombres originales de las fuentes».
  AAPL: «Industria de referencia: Computers/Peripherals, Damodaran; perfil de Yahoo Finance: industria Consumer
  Electronics, sector Technology». La metodología del PDF nuevo conserva «industria «Computers/Peripherals»».
- **Fuera del encargo.** La industria SIC de la ficha oficial de la SEC («3674 · Semiconductors & Related Devices») es
  el texto de la SEC y sigue en inglés.
- **Tests y guardián:**
  - `test_names.py`: ninguna industria del universo (84 de Damodaran, 11 sectores GICS), de `industries.toml` ni del
    perfil de los tickers del panel y del juego local queda sin traducción;
  - regla `industria_en_ingles`: detecta un nombre original en la prosa, las fichas y el texto de los PDF hasta la
    metodología. No marca los nombres propios («NextEra Energy», «Taiwan Semiconductor») ni la ficha SIC;
  - `test_industry_names_in_spanish`, `src/v2/lib/names.test.ts` y el e2e `e2e/v2/nombres.spec.ts` (KO en las dos
    webs).
- **Páginas de E3.** `CompanyHeader.tsx` y `lib/story.ts` leen el nombre en español con `profileNames` y, sin él (un
  análisis en caché anterior), el de la fuente. La web actual también lo usa (`StockHeader.tsx`).
- **Golden.** 36 de 37 · 6 de 6 tickers. Cambian 649 · 107 campos, solo textos, y se añade `display.profile`. PDF actual
  +163/−100 · +36/−25; PDF nuevo +647/−570 (incluido el anexo nuevo). 0 cambios de veredicto.

## Aprobación

Aprobado por el PM (sesión planificadora) por delegación del usuario, 2026-10-18. Literal del PM: «Ningún veredicto
cambia (compruébalo como siempre). Cambian textos, así que el golden cambia: `docs/fiabilidad/GOLDEN_DIFF_V7.md` con un
commit por causa. Lo apruebo yo por delegación; regenéralo.»
