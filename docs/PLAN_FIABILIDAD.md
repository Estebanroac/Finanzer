# Plan de fiabilidad de Finanzer

> **Estado vivo y registro de sesiones:** [`fiabilidad/BITACORA.md`](fiabilidad/BITACORA.md). **Prompts por fase:** [`fiabilidad/prompts/`](fiabilidad/prompts/).

*Redactado el 2026-10-14 a partir de la corrida de 12 tickers en producción (`~/Downloads/finanzer_corrida_2026-10-14/`), de `RECON.md` §6–§7 y de `redesign-spec.md`. Este documento es el mapa: **qué** se hace, **cómo**, **en qué orden**, **cuándo** se puede empezar cada paso y **cómo se revisa**. El código se escribe en otro chat; cada sesión de código lee primero este archivo y la fase que le toca.*

---

## 0. Qué significa "fiable" aquí

Un informe es fiable cuando cumple cinco propiedades. Cada fase de este plan existe para garantizar al menos una:

| # | Propiedad | Pregunta que responde | Cómo se mide |
|---|---|---|---|
| F1 | **Dato correcto** | ¿Los números son los de los estados financieros reales? | % de campos del panel que coinciden con la fuente oficial (SEC EDGAR) dentro de la tolerancia |
| F2 | **Método adecuado** | ¿Se analiza la empresa con las herramientas de su tipo de negocio? | 0 tickers del panel con arquetipo incorrecto según la revisión experta |
| F3 | **Texto fiel al dato** | ¿Cada frase del informe es verdad según los números? | 0 contradicciones detectadas por el guardián narrativo (fase 1) |
| F4 | **Incertidumbre honesta** | ¿El informe dice cuánto sabe y cuánto no? | Confianza y cobertura visibles; la confianza baja cuando de verdad falta información |
| F5 | **Reproducible y estable** | ¿El mismo ticker con los mismos datos da lo mismo, aquí y en producción? | Golden tests local = prod; el veredicto no cambia de un día a otro sin cambio de precio o de datos |

**Regla general:** nunca se mezcla en un mismo paso un arreglo de datos con un cambio de metodología. Si un golden cambia, tiene que poder explicarse con una sola causa.

---

## 1. Diagnóstico de partida (corrida del 2026-10-14)

Muestra: AAPL, JPM, O, XOM, KO, JNJ, NEE, CAT, PLTR, AMZN, TSM, RIVN contra finanzer.app. Los 12 respondieron 200 y generaron PDF.

**Funciona:** ramas por arquetipo (banco por P/B frente a ROE, REIT por P/FFO, utility sin DCF, pre-beneficio sin múltiplos negativos), validación de múltiplos no significativos, moneda del ADR, veredicto en tres capas.

**Fallos por clase:**

| Clase | Hallazgo | Propiedad |
|---|---|---|
| Presentación | Página 2 de **todos** los PDF: el panel "Composición" es más estrecho que la página, corta cifras ("-4", "+0"), se solapa con "Lectura del análisis" y deja un hueco grande encima | F3 |
| Texto ≠ dato | PLTR: "con EBIT negativo y caja neta" con EBIT de +$2.63B (margen operativo del 43%). Hipótesis: `interestCoverage` negativo de Finnhub (intereses netos de ingresos) dispara la regla de "EBIT < 0" | F3 |
| Idioma / jerga | JPM: "Salud financiera bancaria de 10/10 (STRONG)". En todos: "MATURE", "por_defecto" en el detalle técnico | F3 |
| Método | PLTR (crecimiento 56–79%) y CAT (maquinaria cíclica) salen como "Madura". No existe el arquetipo "crecimiento rentable" | F2 |
| Método | Calidad saturada en 100 (PLTR, TSM): la escala no distingue lo excelente de lo extraordinario | F2/F4 |
| Método | El DCF tiene fiabilidad baja en AAPL, CAT, PLTR y TSM (−52% a −78%) → un solo método evaluable → el precio nunca llega a "muy exigente" (RECON §7.17) | F2/F4 |
| Método | El DCF de AAPL crece al 1.8% (CAGR de 3 años) cuando los ingresos crecen al 14% interanual: la base de crecimiento castiga a empresas que reaceleran | F2 |
| Bases mezcladas | Piotroski de AAPL: "el flujo operativo no llega al beneficio" (año fiscal), mientras el TTM da OCF/NI = 1.06 en el mismo informe | F1/F3 |
| Dato ausente | JNJ sin Altman (falta el dato de utilidades retenidas en el plan B). AMZN pierde toda la categoría Crecimiento (BPA y FCF iniciales negativos) | F1/F4 |
| Dato a verificar | TSM: P/E TTM 31.7 frente a forward 18.9 (implica un BPA +68%): posible mezcla ADR/ordinaria en el forward de Finnhub | F1 |
| Infraestructura | Producción atiende las peticiones de una en una (llegaron cada 3–4 s). PDF de 20–60 s con carga | F5 |
| Fuente | Yahoo responde 401 en Render → plan B permanente; ningún ticker llega a fuente "alta" (RECON §7.1) | F1 |

Pendientes heredados que siguen abiertos: beta de Finnhub en los ADR (NVO), bases mezcladas cuando el plan B cae a anual (AMZN), cobertura de intereses en utilities, BRK-B como posible cíclica, cuatro copias de umbrales (motor, alertas, PDF, frontend).

---

## 2. Marco experto: qué debe saber hacer el motor

Esta sección fija el criterio con el que se revisa cada fase. Es la vara de medir, no una lista de tareas.

### 2.1 Análisis fundamental: el núcleo (decide calidad y precio)

- **El tipo de negocio determina las métricas.** Damodaran: ningún múltiplo es universal. El banco se mide por ROE frente a coste del capital y P/B; el REIT por FFO/AFFO; la utility por base de activos regulada y dividendo cubierto; la cíclica por ganancias a mitad de ciclo; el crecimiento rentable por crecimiento + márgenes incrementales + reinversión (Rule of 40 en software); el pre-beneficio por caja y runway.
- **La calidad se demuestra con persistencia, no con un año.** ROIC por encima del WACC durante varios años, márgenes estables, conversión de beneficio en caja (OCF/NI ≥ 1 sostenido), dilución baja. Un solo año excelente no es "excelente".
- **El precio se juzga con al menos dos métodos independientes** (intrínseco + relativo). Si discrepan, la respuesta honesta es "no concluyente", no un promedio.
- **El DCF es una herramienta de sensibilidad, no un oráculo.** Su valor está en responder qué crecimiento y qué márgenes descuenta el precio actual (*reverse DCF*), no en producir un precio objetivo.
- **Base temporal única.** TTM con TTM, fiscal con fiscal. Mezclar bases produce contradicciones visibles (el caso del Piotroski de AAPL).

### 2.2 Análisis técnico: contexto, nunca veredicto

Solo entran señales con evidencia académica sólida, y siempre como **contexto que modula la confianza**, nunca como puntuación:

| Señal | Evidencia | Uso en Finanzer |
|---|---|---|
| Momentum 12-1 meses | Jegadeesh-Titman (1993), Asness-Moskowitz-Pedersen (2013): uno de los factores más robustos | "El mercado viene premiando / castigando la acción" |
| Tendencia (precio frente a media de 200 sesiones) | Faber (2007), Moskowitz et al. (2012, time-series momentum) | Régimen: alcista, bajista o lateral |
| Volatilidad realizada y drawdown máximo | Gestión de riesgo estándar | "Cuánto puede caer en un año malo" |
| Fuerza relativa frente al ETF del sector | Extensión del momentum | ¿El problema es la empresa o el sector? |
| Volumen anómalo (z-score) | Gervais-Kaniel-Mingelgrin (2001) | Atención inusual: pánico o euforia |
| Deriva posterior a resultados (PEAD) | Bernard-Thomas (1989) | Contexto en los días posteriores a los resultados |

**Fuera:** figuras chartistas, Fibonacci, osciladores sueltos (RSI/MACD como señal de compra). No tienen evidencia fuera de muestra que justifique ponerlas en un informe que se presenta como fiable.

### 2.3 Finanzas conductuales: dos frentes

**Frente 1, el mercado** (qué sesgo puede estar moviendo el precio):
- Sobrerreacción y reversión a 3–5 años (De Bondt-Thaler, 1985): caídas extremas sin deterioro fundamental.
- Subreacción a noticias y resultados (PEAD): el precio tarda en incorporar sorpresas.
- Anclaje al máximo de 52 semanas (George-Hwang, 2004): cerca del máximo, el mercado subestima las buenas noticias.
- Extrapolación y efecto manada: valoraciones extremas sostenidas por crecimiento pasado (el caso de PLTR con P/E 174).

**Frente 2, el usuario** (el informe no debe explotar sus sesgos, sino protegerlo de ellos):
- **Anclaje:** no mostrar nunca un "precio objetivo" único; siempre un rango con su supuesto.
- **Exceso de confianza:** confianza y cobertura visibles junto al veredicto, no en letra pequeña.
- **Efecto marco (framing):** el mismo dato con el mismo color y el mismo tono, sea bueno o malo. Nada de "¡oportunidad!".
- **Sesgo de confirmación:** cada informe incluye "Qué tendría que pasar para que esta lectura sea errónea" (pre-mortem).
- **Aversión a la pérdida y recencia:** mostrar el drawdown histórico y la volatilidad junto a la rentabilidad, no solo lo positivo.
- **Tasas base:** "de las empresas con este perfil, X% ..." solo cuando se haya calibrado con datos propios (fase 6). Antes, no se inventan.

**Regla de oro (ya en el spec, se mantiene):** la capa técnica y conductual **modula la confianza y aporta contexto**; nunca suma ni resta en calidad ni en precio hasta validarla fuera de muestra (fase 6).

---

## 3. El panel de referencia (la vara fija de toda revisión)

Hoy los golden cubren 6 tickers + fixtures sueltos. Para medir fiabilidad hace falta un **panel fijo de 30 tickers** que cubra cada arquetipo y cada trampa conocida. Se congela (fixtures local + prod) una vez y se recaptura solo con aprobación.

| Grupo | Tickers | Qué pone a prueba |
|---|---|---|
| Madura | AAPL, MSFT, KO, PG, JNJ | Caso base; recompras; patrimonio pequeño (ROE > 100%) |
| Financiera | JPM, BAC, PGR, V, BRK-B | Banco, aseguradora, pagos (¿es financiera?), conglomerado con clases A/B |
| REIT | O, PLD, AMT | Retail, industrial, torres (deuda alta) |
| Utility | NEE, DUK | FCF negativo por diseño, cobertura de intereses |
| Cíclica | XOM, FCX, CAT, MU, DOW | Energía, minería, maquinaria, memoria, química |
| Crecimiento rentable | PLTR, NVDA, CRWD | Arquetipo que hoy no existe; saturación de la calidad |
| Pre-beneficio | RIVN, SNOW | Runway, múltiplos negativos |
| ADR / IFRS | TSM, ASML, NVO | Moneda, ratio ADR, beta de Finnhub, filas IFRS |
| Casos trampa | NFLX (partida extraordinaria), AMZN (FCF negativo por capex), SPY (debe rechazarse) | Normalización, bases, validación de entrada |

**Tolerancias de verificación externa** (fase 2):
- Ingresos, beneficio neto, OCF, capex, deuda, caja, acciones: **±1%** frente al 10-K/10-Q/20-F.
- Ratios derivados (márgenes, ROE, ROIC, D/E): **±2% relativo**, o ±0.5 pp en porcentajes pequeños.
- Precio y capitalización: **±0.5%** frente al cierre del día.
- BPA: **±2%**, comparando siempre la misma clase de acción y el mismo ADR.

---

## 4. Las fases

Cada fase tiene: **objetivo**, **qué** se hace, **cómo** (método), **cuándo empezar** (puerta de entrada), **criterio de terminado** y **revisión**. Ninguna fase empieza sin que la anterior haya pasado su revisión y tenga la aprobación explícita del usuario.

### Fase 0 — Congelar y medir (cimientos)

- **Objetivo:** poder medir cualquier cambio contra una verdad fija. Sin esto, nada de lo que sigue es verificable.
- **Qué:**
  1. Ampliar fixtures y golden al panel de 30 (local + prod), en una rama propia.
  2. Script `panel_run` que corre el panel y genera una tabla resumen (arquetipo, calidad, precio, confianza, DCF, fuente) más los PDF y su texto. Es lo mismo que la corrida del 2026-10-14, pero repetible.
  3. Registrar las métricas de partida: las cinco propiedades F1–F5 con su número de hoy.
- **Cuándo empezar:** ahora. No depende de nada.
- **Terminado cuando:** el panel corre en local en replay sin red, y la tabla de partida está guardada en `docs/`.
- **Revisión:** el usuario revisa la tabla de partida y confirma que el panel representa bien sus casos de uso.

### Fase 1 — Lo que el usuario ve mal hoy (rápido, visible)

- **Objetivo:** que ningún PDF diga algo falso ni se vea roto. Ataca F3.
- **Qué:**
  1. Maquetación de la página 2 (panel "Composición": ancho, recorte, solapamiento, hueco).
  2. Texto de PLTR "EBIT negativo": diagnosticar el origen (hipótesis: `interestCoverage` de Finnhub) y que la regla use el EBIT de los estados, no el signo de la ratio.
  3. Inglés y códigos internos: "STRONG" y todo literal en inglés; "MATURE"/"por_defecto" solo en un anexo técnico explícito o en ningún lado (decisión D1).
  4. **Guardián narrativo:** test que recorre el texto del informe del panel y comprueba cada afirmación con predicado contra el dato estructurado ("EBIT negativo" ⇒ `operating_income < 0`; "en máximos" ⇒ posición ≥ 90%; "recompras" ⇒ acciones a la baja; etc.). Así se cierra la **clase** de error, no solo el caso PLTR.
  5. Prueba visual automática: render PNG de todas las páginas del panel con comprobación de que ningún texto se sale de su caja (reportlab permite medir el `wrap`).
- **Cómo:** arreglo puntual + test que falla antes y pasa después (TDD). Golden: solo cambian textos.
- **Cuándo empezar:** tras la fase 0.
- **Terminado cuando:** 0 contradicciones del guardián en los 30 tickers; las 30×8 páginas revisadas sin recortes; golden con diff solo de texto.
- **Revisión:** el usuario mira 4 PDF (uno por grupo) en PNG. Deploy permitido al terminar esta fase.

### Fase 2 — Verdad de datos (fuente oficial)

- **Objetivo:** dejar de depender de que Yahoo/Finnhub acierten. Ataca F1, que es la propiedad de la que dependen todas las demás.
- **Qué:**
  1. **SEC EDGAR (XBRL `companyfacts`) como fuente de referencia** de los estados de las empresas que presentan ante la SEC (10-K/10-Q; 20-F para ADR con taxonomía IFRS). Es gratuita y oficial: solo pide un User-Agent identificado y un máximo de 10 peticiones por segundo. Cubre la mayoría del panel.
  2. **Modo verificación primero, no sustitución:** un job compara campo a campo Yahoo/Finnhub frente a EDGAR para el panel y produce un informe de discrepancias con las tolerancias de §3.
  3. Según el informe: EDGAR como fuente primaria de estados para emisores SEC, Yahoo para precio/mercado y Finnhub como respaldo (decisión D2).
  4. Base temporal única: cada métrica declara su base (TTM o FY) y el motor rechaza combinar bases sin etiquetarlo (cierra el caso del Piotroski de AAPL y el de AMZN márgenes FY / P/E TTM).
  5. Casos concretos: utilidades retenidas de JNJ, forward P/E de TSM (¿ADR u ordinaria?), beta de Finnhub en los ADR (NVO).
- **Cómo:** el job de verificación se escribe y se ejecuta antes de tocar el motor. Los arreglos se hacen de uno en uno, cada uno con su golden explicado.
- **Cuándo empezar:** tras la fase 1 desplegada. Antes conviene una sesión de diagnóstico de EDGAR (cobertura real de las etiquetas XBRL en el panel, latencia desde Render).
- **Terminado cuando:** ≥ 95% de los campos del panel dentro de la tolerancia, y cada excepción documentada con su causa en RECON.
- **Revisión:** el usuario revisa el informe de discrepancias. Muestreo manual de 5 tickers contra el 10-K publicado (lo hace el chat de revisión y lo enseña con las cifras lado a lado).

### Fase 3 — Método por tipo de negocio

- **Objetivo:** cada empresa analizada con sus herramientas. Ataca F2.
- **Qué:**
  1. **Arquetipo nuevo "crecimiento rentable"** (PLTR, NVDA, CRWD): crecimiento por acción, margen incremental, Rule of 40, reinversión; el P/E alto se juzga frente al crecimiento (PEG a varios años, reverse DCF), no frente a la mediana del sector.
  2. **Clasificador de cíclicas:** CAT, DOW, MU deben salir como cíclicas. Revisar la lista de industrias y la regla `ciclica_condicional_estable` (TSM) con criterio: ¿la volatilidad de márgenes en 4 años basta para declarar estabilidad en semiconductores?
  3. **Base de crecimiento del DCF:** cuando el interanual y el CAGR de 3 años divergen mucho (AAPL 14% frente a 1.8%), usar un crecimiento ponderado y declarado, o abrir escenarios. Nunca elegir en silencio el más extremo.
  4. **Reverse DCF:** "el precio actual descuenta un crecimiento del X% durante 10 años". Es el uso correcto del DCF cuando el directo no concilia, y convierte la fiabilidad baja en información útil.
  5. **Decisión §7.17** (precio con un solo método): ver D3.
  6. Pendientes heredados: cobertura de intereses en utilities, BRK-B (conglomerado), AMZN sin categoría de Crecimiento (alternativa: CAGR de ingresos por acción cuando el BPA inicial es ≤ 0).
- **Cómo:** una regla por commit, cada una con test y golden explicado. Revisión experta por arquetipo: para cada uno del panel, una ficha de "cómo lo analizaría un analista" y comparación con lo que hace el motor.
- **Cuándo empezar:** tras la fase 2 (con datos malos no se puede juzgar un método).
- **Terminado cuando:** los 30 tickers con arquetipo aprobado por el usuario; ningún precio con DCF "baja" sin reverse DCF mostrado.
- **Revisión:** tabla de arquetipos del panel con la justificación de cada uno; el usuario aprueba línea a línea.

### Fase 4 — Escalas y confianza honestas

- **Objetivo:** que los números signifiquen lo mismo para todos. Ataca F4.
- **Qué:**
  1. **Saturación de la calidad:** 100 debe ser raro. Opciones: exigir persistencia multianual para las bandas altas, o bandas más exigentes en la parte alta. Objetivo: en el panel, ≤ 2 tickers por encima de 95.
  2. **Confianza calibrada:** revisar que "alta / media / baja" responde a causas reales (métodos que discrepan, cobertura, fuente) y que el texto lo explica en lenguaje llano.
  3. **Pre-mortem en el informe:** "Esta lectura sería errónea si…" (2–3 condiciones derivadas de los datos: por ejemplo, márgenes que vuelven a la media o crecimiento por debajo de lo que descuenta el precio).
- **Cuándo empezar:** tras la fase 3.
- **Terminado cuando:** la distribución de calidad del panel es razonable (no amontonada arriba) y la revisión experta la valida.
- **Revisión:** histograma de calidad y de precio del panel, antes y después.

### Fase 5 — Capa técnica y conductual (etapa 10 del spec)

- **Objetivo:** contexto de mercado y protección frente a sesgos. Aporta a F4 y a la utilidad, nunca al score.
- **Qué:** las señales de §2.2 (momentum 12-1, tendencia de 200 sesiones, volatilidad, drawdown, fuerza relativa frente al ETF del sector, volumen anómalo, fecha de resultados) y la lectura conductual de §2.3, en un panel separado de la web y del PDF. Noticias de 7 días solo si Finnhub `company-news` es gratuito en el plan actual (verificarlo con la clave).
- **Cómo:** nueva ingesta de la serie diaria (una llamada más por ticker; medir latencia y bloqueo desde Render antes de construir). Frases conductuales con predicados verificables (pasan por el guardián de la fase 1).
- **Cuándo empezar:** tras la fase 4. Puede adelantarse en paralelo a la fase 4 si la fase 6 (infraestructura) ya resolvió la latencia.
- **Terminado cuando:** el panel muestra las señales correctas contra un cálculo de referencia independiente (pandas sobre la misma serie); ninguna señal entra en calidad ni en precio.
- **Revisión:** el usuario revisa 5 lecturas conductuales y comprueba que ninguna suena a recomendación.

### Fase 6 — Infraestructura (en paralelo desde la fase 2)

- **Objetivo:** F5 y tiempos aceptables.
- **Qué:** varios workers o concurrencia real en Render (hoy atiende en serie); caché persistente de estados financieros (cambian trimestralmente: no hace falta descargarlos en cada análisis); PDF por debajo de 10 s en frío; registro de qué fuente aportó cada campo (ya existe `data_provenance`: exponerlo en el anexo).
- **Cuándo empezar:** diagnóstico en la fase 2; implementación cuando la fase 2 decida las fuentes (para no cachear la fuente equivocada).
- **Terminado cuando:** p95 del análisis < 6 s en frío y < 1 s en caliente; 12 peticiones simultáneas sin cola en serie.
- **Revisión:** medición antes y después con la misma corrida de 12 tickers.

### Fase 7 — Calibración y vigilancia continua

- **Objetivo:** saber si el motor acierta, y enterarse cuando deja de hacerlo.
- **Qué:**
  1. **Vigilancia semanal:** tarea programada que corre el panel contra producción, compara con la semana anterior y avisa de cambios de veredicto sin cambio de precio ni de datos (rotura de fuente), de errores y de tiempos.
  2. **Revisión mensual de parámetros:** Rf, prima de riesgo de Damodaran (hoy 4.20%), spreads por rating, medianas sectoriales, con fecha y fuente en la configuración (RECON §7.13 ya lo pide).
  3. **Calibración histórica (estudio, no ajuste):** con los datos point-in-time de EDGAR, comprobar si "calidad excelente" anticipa persistencia del ROIC y menor drawdown, y si "precio muy exigente" anticipa peores rentabilidades relativas a 1–3 años. Muestra de entrenamiento y de prueba separadas. Sirve para validar o retirar reglas, **no** para optimizar umbrales (riesgo de sobreajuste).
- **Cuándo empezar:** la vigilancia, en cuanto exista `panel_run` (fase 0). La calibración, tras la fase 4.
- **Terminado cuando:** nunca: es continua. El estudio de calibración termina con un informe y decisiones del usuario.

---

## 5. Protocolo de revisión de cada paso (definición de terminado)

Todo paso de código, en cualquier fase, pasa esta lista en el chat de código antes de pedir aprobación:

1. **Test primero:** el test nuevo falla antes del cambio y pasa después.
2. **Suite completa en verde** en `.venv313` (espejo de producción).
3. **Golden:** diff generado y **explicado causa por causa**; el usuario lo aprueba antes de regenerar.
4. **Panel completo** (`panel_run`) en replay local: tabla resumen antes/después adjunta.
5. **Guardián narrativo** en verde (desde la fase 1).
6. **Revisión visual** de los PDF afectados en PNG (al menos uno por arquetipo tocado).
7. **Revisión de código** independiente (skill `code-review`) sobre el diff de la rama.
8. **Aprobación del usuario** explícita. Sin ella no hay push (regla vigente).
9. **Deploy y verificación en producción:** corrida del panel contra finanzer.app; resultado anotado en `docs/DEPLOY_VERIFICATION.md`; rollback identificado.
10. **Registro:** RECON (§7.x nueva) y memoria actualizados.
11. **Revisión externa (al cierre de cada fase):** 2–3 tickers **fuera del panel**, elegidos para estresar la fase
    (otra moneda, otro tipo de negocio), con el PDF de producción contrastado por un analista independiente. El panel
    mide los fallos que ya conocemos; esta revisión busca los que no (origen: BCS, 2026-10-15).

**Revisión entre fases** (en un chat como este, sin código): corrida del panel en producción, comparación con las métricas F1–F5 de la fase 0 y decisión de pasar o no a la siguiente.

---

## 6. Decisiones que necesita el usuario

| # | Decisión | Opciones | Recomendación | Fase |
|---|---|---|---|---|
| D1 | Códigos internos ("MATURE", reglas) en el PDF | (a) quitarlos; (b) dejarlos en un anexo técnico rotulado | (b): ayudan a auditar, pero solo en el anexo | 1 |
| D2 | Papel de SEC EDGAR | (a) solo verificación; (b) fuente primaria de estados para emisores SEC | (b), tras ver el informe de discrepancias en modo (a) | 2 |
| D3 | Precio con un solo método (§7.17) | Las tres opciones de RECON §7.17, o el reverse DCF como segundo método "blando" | Reverse DCF + opción 3 (no contraer cuando la confianza baja solo por falta de segundo método) | 3 |
| D4 | Arquetipo "crecimiento rentable" | Crear arquetipo o ajustar MATURE con reglas de crecimiento | Crear arquetipo: el método de análisis es otro | 3 |
| D5 | Capa técnica en el score | (a) solo contexto; (b) que module el precio | (a) hasta que la fase 7 la valide | 5 |
| D6 | Infraestructura | Plan de Render con más workers, o caché persistente + optimización | Ambas, medir primero | 6 |
| D7 | Universo de empresas | Solo emisores SEC (incluye ADR) o también cotizadas solo fuera de EE. UU. | Solo emisores SEC hasta terminar la fase 2: es donde la verdad de datos se puede garantizar | 2 |

---

## 7. Orden y calendario

Cada fase se mide en sesiones de código, no en fechas, porque cada puerta depende de una aprobación.

```
Fase 0  Congelar y medir          ██          1–2 sesiones   → empieza ya
Fase 1  Lo visible hoy              ██        2 sesiones     → deploy al terminar
Fase 2  Verdad de datos (EDGAR)       ████    3–4 sesiones   → deploy al terminar
Fase 6  Infraestructura               ··████  2 sesiones     (diagnóstico en la 2)
Fase 3  Método por arquetipo              ████  3–4 sesiones
Fase 4  Escalas y confianza                 ██  2 sesiones
Fase 5  Técnica y conductual                  ███  3 sesiones
Fase 7  Vigilancia (desde la 0) · calibración (tras la 4) → continua
```

**Próximo paso concreto:** abrir el chat de código con la fase 0 (panel de 30 + `panel_run` + métricas de partida). Este plan es la referencia de ese chat.
