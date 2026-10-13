# Finanzer — Evaluación y Rediseño del Motor de Análisis

Oct 9, 2026 · Esteban Roa

## Propósito y alcance

Este documento es la **especificación de evaluación y rediseño** del motor de análisis fundamental de Finanzer. Sirve como manual para ejecutar los cambios en Claude Code; aquí no se modifica el modelo, se define *qué* cambiar, *por qué* desde el criterio financiero, y *cómo* abordarlo.

**Cómo leerlo.** Cada sección es autónoma. El diagnóstico (Sección 1) se apoya en el caso real de Netflix (NFLX, informe al 9-oct-2026), pero cada fallo se describe como patrón general, no como anécdota: lo que con Netflix se ve leve, con un banco o una empresa cíclica rompe el análisis.

**Principio rector.** El objetivo no es un modelo que acierte en Netflix, sino uno **adaptativo** (comportamiento distinto según sector y tipo de activo), **sostenible** (reglas y umbrales separados del código, actualizables sin reescribir) y **certero** (que no esconda sus contradicciones ni trate la ausencia de dato como señal).

> Método: el modelo consume dos fuentes gratuitas (Yahoo Finance + otra de alta cobertura). Todo el rediseño asume **cero gasto adicional en APIs**; la capa de noticias/sentimiento se construye con lo ya disponible.

## Sección 1 — Diagnóstico del modelo actual

### Qué es hoy

Finanzer es, en su forma actual, un **scorer de calidad fundamental de régimen único**: toma ratios estándar (TTM y último ejercicio, fuente Yahoo Finance), los compara contra umbrales fijos y una mediana sectorial fija, y suma puntos en cinco categorías (Solidez, Rentabilidad, Valoración, Calidad de Ganancias, Crecimiento) hasta un total sobre 100. Añade capa institucional (Altman Z, Piotroski F), un DCF multietapa con WACC por CAPM, número de Graham, y un bloque de alertas.

### Qué hace bien

- **Cobertura y consistencia.** Produce un informe completo, legible y reproducible por ticker, con lectura automática por banda. Es un cimiento sólido.
- **Datos de mercado correctos.** Precio, capitalización y rango de 52 semanas coinciden con fuentes de hoy. El pipeline de ingesta funciona.
- **Buenas métricas base.** Altman Z, Piotroski, ROIC−WACC y PEG son indicadores que las casas serias efectivamente usan. La materia prima es buena.

### Los fallos (patrón general, ilustrado con NFLX)

**Fallo 1 — El score esconde su propia contradicción.** El informe da 99/100 ("excelente") y a la vez marca la acción como sobrevalorada −50% por DCF. La valoración saca 19/20 apoyándose solo en múltiplos *relativos* (PEG, EV/EBITDA, Forward P/E, GARP); el DCF **no resta nada** al score y aparece aislado en "riesgos". *Patrón:* el motor tiene dos sistemas de valoración que pueden contradecirse y uno no toca el puntaje. Un usuario no técnico se queda con el 99.

**Fallo 2 — La ausencia de dato se cuenta como incumplimiento.** En Piotroski, "sin dilución de acciones → sin datos históricos → No cumple". Eso convirtió un potencial 7/9 en 6/9 por *falta de dato*, no por fallo real. *Patrón:* dato faltante tratado como señal negativa. Esto ensucia todos los análisis, no solo NFLX, y es peor en empresas con menor cobertura de datos.

**Fallo 3 — Medianas sectoriales fijas (hardcoded).** El modelo compara contra P/E 18x, ROE 12%, margen 12% como constantes. Toda la columna "brecha vs sector" se mide contra un número inventado, no contra comparables reales. *Patrón:* con un banco (P/B, no P/E), un REIT (P/AFFO), o un SaaS sin ganancias, estas constantes no solo son imprecisas: apuntan a la métrica equivocada.

**Fallo 4 — Ganancias no normalizadas.** El beneficio TTM de NFLX incluye ~$2.8B de una comisión de ruptura no recurrente que infla EPS y comprime el P/E artificialmente. El modelo lo toma como ganancia ordinaria. *Patrón:* sin detección de ítems no recurrentes, todo múltiplo basado en beneficio queda distorsionado — crítico en cíclicas y en años con eventos extraordinarios.

**Fallo 5 — Grid de sensibilidad mal centrado.** La tabla de sensibilidad del DCF (WACC 11.3%–15.3% × crecimiento 11%–21%) no contiene **ningún** escenario que alcance el precio de mercado ($70): el máximo del grid es $54. *Patrón:* cuando el grid entero queda por debajo del precio, el problema es el centrado del rango o el WACC (13.3%, alto por beta 1.61), no que el mercado esté 50% equivocado. El valor terminal aporta solo 42% (bajo frente al 60–75% típico), señal de que el descuento aplasta la cola.

**Fallo 6 — Calidad del negocio y atractivo del precio están fundidos en un número.** "¿Es buena la empresa?" y "¿está cara hoy?" son dos preguntas distintas. NFLX es negocio excelente *y* precio posiblemente caro a la vez. Un solo 99/100 mezcla ambas y confunde la decisión.

> **Lectura honesta:** Netflix es un caso benévolo porque es calidad genuina; los fallos 3 y 4 se ven leves aquí. Con un banco, una minera cíclica o un SaaS pre-beneficio, estos mismos fallos producen veredictos directamente equivocados.

## Sección 2 — Cómo trabajan los modelos serios

Cuatro capas que Finanzer tiene a medias o no tiene. El rediseño de las secciones siguientes se construye sobre ellas.

### 2.1 Valoración adaptativa al tipo de empresa (Damodaran)

La referencia mundial no usa un solo DCF. Usa un **árbol de decisión** que elige el modelo según la empresa:

- ¿Se pueden estimar flujos de caja? Si no → modelo de dividendos.
- ¿La deuda es estable o cambiará? → FCFE (al accionista) vs FCFF (a la firma).
- ¿Las ganancias actuales son positivas y normales? Si no → **normalizar** antes de valorar.
- ¿La empresa sobrevivirá? Si está en problemas → valorar el equity como una opción, o usar valor de liquidación.

*Implicación para Finanzer:* aplicar un único DCF a todo es la raíz del problema de adaptabilidad. El modelo debe **ramificar** antes de valorar.

### 2.2 Modelo de factores (AQR y la escuela cuantitativa)

Las casas cuantitativas no puntúan una acción en abstracto: la miden contra el **universo completo** en varios factores simultáneos — Valor, Momentum, Calidad, Baja Volatilidad, Tamaño. Lo clave: esos factores están **negativamente correlacionados** entre sí (valor y momentum se mueven en contra), y eso es una virtud, no un defecto.

*Implicación:* un escalar (99/100) colapsa factores que tiran en direcciones opuestas y los promedia hacia arriba. Finanzer debería reportar un **vector de factores**, exponiendo las tensiones en vez de ocultarlas.

### 2.3 Métricas por sector, no umbrales universales

| Tipo de empresa | Métrica de valoración correcta | Por qué falla el P/E genérico |
| --- | --- | --- |
| Banco | P/B, no P/E | Ganancias oscilan con provisiones; el "libro" es el motor |
| REIT | P/AFFO (fondos de operación ajustados) | El beneficio neto está distorsionado por depreciación |
| SaaS / growth sin beneficio | EV/Ingresos recurrentes (ARR) | Muchos no tienen ganancias que capitalizar |
| Semiconductora / cíclica | EV/EBITDA ajustado por ciclo | El beneficio de un pico de ciclo engaña |
| Madura / dividendera | P/E, FCF yield, DDM | Aquí sí aplica el enfoque clásico |

Además, en un banco el flujo de caja operativo apunta al revés: si crece el libro de préstamos, el flujo se va negativo — eso es crecimiento, no distress.

### 2.4 Finanzas conductuales cuantificables

No es humo: lo emocional se mide con variables observables.

- **Índice de sentimiento (Baker-Wurgler):** prima dividendo/no-dividendo, volumen de IPOs y su retorno del primer día, proporción emisión de acciones vs deuda. Sentimiento alto → especulativas sobrevaloradas que luego rinden mal.
- **Herding (manada):** se mide con la dispersión transversal de retornos (CSAD). Cuando los retornos individuales se pegan al del mercado, hay pánico de manada.
- **Efecto disposición:** ratio que mide si el mercado vende ganadores y retiene perdedores.
- **Sobre/subreacción (Barberis-Shleifer-Vishny):** el mercado subreacciona a noticias puntuales (resultados) y sobrerreacciona a rachas. NFLX en el 9% de su rango justo antes de reportar es una posible **sobrerreacción medible**, no solo "alerta en mínimos".

*Implicación:* esta capa modula la *confianza* y el *contexto*, no debe mezclarse en el score fundamental.

## Sección 3 — Arquitectura nueva

El modelo actual es un solo paso: ratios → score. La propuesta es un **pipeline de cinco etapas**, donde cada una puede evolucionar por separado.

### El pipeline

1. **CLASIFICAR** — Detectar sector y tipo de negocio (financiero, REIT, growth-sin-beneficio, cíclico, maduro). Carga el perfil de métricas y umbrales que corresponde. *Nada se puntúa antes de saber qué es.*
2. **NORMALIZAR** — Detectar y limpiar ítems no recurrentes (comisiones de ruptura, cargos únicos, ganancias por venta de activos). Marcar cobertura de datos; ausencia ≠ cero.
3. **VALORAR** — Ramificar según clasificación (árbol Damodaran): elegir DCF-FCFF, FCFE, DDM, EV/Revenue o valor de opción. El DCF reporta además qué % aporta el valor terminal y si el grid de sensibilidad contiene el precio de mercado.
4. **PUNTUAR** — Vector de factores (Valor, Calidad, Crecimiento, Solidez, Momentum) + dos números separados: **Calidad del negocio** y **Atractivo del precio**. Nunca un solo escalar.
5. **CONTEXTUALIZAR** — Capa conductual y de noticias: sentimiento, posición en rango, proximidad a resultados, señal de sobre/subreacción. Modula la *confianza*, no el score fundamental.

### Regla de confianza (clave)

Cuando dos métodos de valoración divergen mucho (p. ej. múltiplos dicen "barata", DCF dice "cara"), eso **baja la confianza del veredicto** y se reporta explícitamente. La divergencia es información, no algo que esconder.

```
confianza = f(
    convergencia_entre_metodos,    # DCF vs multiplos vs Graham
    cobertura_de_datos,            # % de inputs disponibles
    calidad_de_fuente,             # flags de anomalia en ingesta
    estabilidad_del_sector         # ciclicas penalizan confianza
)
```

### Sostenibilidad: separar datos de reglas

Lo que hace mantenible un modelo es que los **umbrales, pesos y medianas vivan en configuración**, no en el código. Hoy están incrustados.

```
/config
  sectors.yaml        # por sector: metricas validas, pesos, umbrales
  factor_weights.yaml # pesos de cada factor en el vector
  thresholds.yaml     # bandas de lectura (ej. ROE > X = excelente)
/engine
  classify.py  normalize.py  value.py  score.py  context.py
/data
  sector_medians.py   # calcula medianas sobre comparables REALES, periodico
```

Las medianas sectoriales dejan de ser constantes (`P/E 18x`) y pasan a calcularse sobre un conjunto de comparables real, refrescado periódicamente.

## Sección 4 — Capa sectorial

Es el cambio de mayor impacto: **clasificar antes de puntuar**. Resuelve de raíz los fallos 3 y 4.

### El clasificador

```python
def classify_asset(fundamentals, profile):
    """Devuelve el 'arquetipo' que decide metricas, modelo de
    valoracion y umbrales. El sector GICS es insuficiente solo:
    hay que mirar el perfil economico real."""
    sector = profile.get('gics_sector')

    # 1. Financieros: el balance ES el negocio
    if sector in ('Financials',) or profile.get('is_bank'):
        return 'FINANCIAL'          # -> P/B, ROE, CAR, NIM; nada de FCF

    # 2. Inmobiliario de renta
    if sector == 'Real Estate' and profile.get('is_reit'):
        return 'REIT'              # -> P/AFFO, FFO yield, NAV

    # 3. Growth sin beneficio sostenido
    if (fundamentals.net_margin_ttm < 0 or
        fundamentals.eps_ttm <= 0) and fundamentals.rev_growth_3y > 0.15:
        return 'GROWTH_PRE_PROFIT'  # -> EV/Sales, Rule of 40, ARR

    # 4. Ciclica: beneficio depende de la fase del ciclo
    if profile.get('industry') in CYCLICAL_INDUSTRIES or \
       earnings_volatility(fundamentals) > CYCLE_THRESHOLD:
        return 'CYCLICAL'          # -> EBITDA normalizado por ciclo

    # 5. Por defecto: madura, enfoque clasico
    return 'MATURE'                # -> P/E, FCF yield, DCF-FCFF, DDM
```

### Qué métricas activa cada arquetipo

| Arquetipo | Valoración primaria | Métricas clave | Qué NO usar |
| --- | --- | --- | --- |
| FINANCIAL | P/B vs ROE | NIM, CAR (Basel), coste del riesgo, eficiencia | FCF, EV/EBITDA |
| REIT | P/AFFO | FFO/AFFO, ocupación, NAV, apalancamiento | P/E sobre beneficio neto |
| GROWTH_PRE_PROFIT | EV/Sales, Rule of 40 | ARR, crecimiento, margen bruto, burn/runway | P/E, número de Graham |
| CYCLICAL | EV/EBITDA normalizado | Margen mid-cycle, ROIC a través del ciclo | P/E de un solo año |
| MATURE | DCF-FCFF + P/E | FCF yield, cobertura, ROIC−WACC | — (enfoque clásico aplica) |

### ROCE como métrica de contraste (MATURE y CYCLICAL)

Se añade **ROCE** junto al ROIC existente, solo en los arquetipos MATURE y CYCLICAL. En FINANCIAL y REIT no se calcula: el capital empleado no tiene sentido económico en esos balances.

```python
def roce(income_stmt, balance):
    """Return on Capital Employed, antes de impuestos."""
    capital_employed = balance.total_assets - balance.current_liabilities
    if not capital_employed or capital_employed <= 0:
        return None                      # ausencia, no cero
    return income_stmt.ebit / capital_employed
```

**Lectura:** ROCE y ROIC miden lo mismo con distinto denominador. El valor está en la **divergencia**: si `|ROCE − ROIC|` es grande, suele indicar caja excedente elevada (infla el capital empleado) o tasa impositiva atípica. El informe muestra ambos y marca la divergencia cuando supera el umbral definido en `thresholds.yaml`. En CYCLICAL se reporta además el ROCE promedio a través del ciclo, no solo el del último año.

**Criterio de aceptación:** ROCE aparece en el informe para MATURE y CYCLICAL, nunca para FINANCIAL ni REIT; capital empleado ≤ 0 o datos ausentes producen "sin dato", no 0%.

### Normalización de ganancias (resuelve el fallo 4)

```python
def normalize_earnings(income_stmt):
    """Quita items no recurrentes antes de calcular multiplos."""
    ni = income_stmt.net_income
    one_offs = sum([
        income_stmt.get('unusual_items', 0),      # ej. breakup fee NFLX
        income_stmt.get('gain_on_sale', 0),
        income_stmt.get('impairments', 0),         # suma de vuelta
        income_stmt.get('restructuring', 0),
    ])
    normalized = ni - income_stmt.get('unusual_items', 0) \
                    - income_stmt.get('gain_on_sale', 0)
    return {
        'reported': ni,
        'normalized': normalized,
        'one_off_pct': abs(one_offs) / ni if ni else None,  # flag si alto
    }
```

> **Criterio financiero:** si `one_off_pct` supera ~10–15%, el P/E reportado no es fiable y el informe debe decirlo. El caso NFLX (~$2.8B sobre ~$11B ≈ 25%) habría disparado esta alerta.

## Sección 5 — Capa conductual

El mercado es emocional; esta capa lo vuelve medible **sin coste adicional de API**. Regla de oro: **modula la confianza y el contexto, nunca el score fundamental ni una señal de compra/venta** (hasta validarla con datos históricos propios).

### Señales conductuales con los datos que ya tienes

Con precio, volumen y rango (ya disponibles en Yahoo Finance) se construyen señales reales sin pagar nada:

```python
def behavioral_signals(price_hist, fundamentals, news=None):
    signals = {}

    # 1. Posicion en rango 52s (ya lo tienes, pero como SENAL)
    pos = (price - low_52w) / (high_52w - low_52w)
    signals['range_position'] = pos          # NFLX = 0.09

    # 2. Sobre/subreaccion: desviacion del precio vs su media
    #    movil, normalizada por volatilidad (z-score de retorno)
    signals['overreaction_z'] = (ret_5d - ret_mean) / ret_std

    # 3. Momentum (factor AQR): retorno 12m excluyendo ultimo mes
    signals['momentum_12_1'] = price_hist.ret(252) - price_hist.ret(21)

    # 4. Spike de volumen: panico o euforia reciente
    signals['volume_z'] = (vol_5d - vol_mean_90d) / vol_std_90d

    # 5. Proximidad a resultados (subreaccion esperada)
    signals['days_to_earnings'] = next_earnings_date - today

    return signals
```

### Lectura conductual (ejemplo NFLX)

> Posición en rango 9% + resultados en 11 días + beta 1.61 → el motor debería leer: *"posible sobrerreacción a la baja antes de catalizador; alta incertidumbre, veredicto fundamental con confianza reducida hasta el reporte."* Hoy solo dice "en mínimos, alerta".

### Noticias recientes — sin gastar de más

Tu segunda API (de las gratuitas famosas: **Finnhub**, **Alpha Vantage** o **Financial Modeling Prep**) muy probablemente **ya incluye un endpoint de noticias** en el plan que usas:

- **Finnhub** → `company-news` (gratis) y `news-sentiment` (sentimiento ya calculado).
- **Alpha Vantage** → `NEWS_SENTIMENT` (sentimiento + relevancia por ticker, gratis).
- **FMP** → `stock_news` (gratis en tier básico).

```python
def news_context(ticker, api):
    raw = api.company_news(ticker, days=7)   # endpoint YA incluido
    return {
        'count_7d': len(raw),
        'sentiment_mean': mean([n.sentiment for n in raw]),  # si lo da la API
        'headlines_top3': top_by_relevance(raw, 3),          # para el informe
    }
```

> **Presupuesto:** si tu segunda API es cualquiera de las tres, el coste adicional es **cero** — ya pagas (o usas gratis) el plan que incluye noticias. Solo si quisieras sentimiento de redes/analistas en tiempo real habría que evaluar un tier pago, y mi recomendación es **no hacerlo todavía**: primero exprime lo gratis. *(Confírmame el nombre de la segunda API y cierro el endpoint exacto.)*

### Visión conductual más allá de los modelos

Además de las métricas, el informe puede incluir un párrafo de **lectura de psicología de mercado** generado a partir de las señales: narrar si el activo está en zona de capitulación, euforia o indiferencia, y qué sesgo domina (aversión a la pérdida, anclaje al máximo histórico, efecto manada). Es cualitativo, pero anclado en los números de arriba — no opinión suelta.

## Sección 6 — Plan de implementación priorizado

Seis cambios en orden de impacto. Cada uno con su criterio de aceptación para Claude Code.

| # | Cambio | Impacto | Esfuerzo | Criterio de aceptación |
| --- | --- | --- | --- | --- |
| 1 | **Clasificar antes de puntuar** | Muy alto | Medio | Todo ticker pasa por `classify_asset()`; un banco nunca recibe lectura de FCF ni P/E como métrica primaria |
| 2 | **Arreglar datos faltantes** | Alto | Bajo | Ausencia de dato se excluye del cálculo y se reporta cobertura; nunca cuenta como "No cumple" |
| 3 | **Normalizar ganancias** | Alto | Bajo | Si `one_off_pct > 15%`, el informe marca el P/E como no fiable y muestra P/E normalizado |
| 4 | **Separar calidad de precio** | Alto | Medio | El informe muestra dos números distintos; ningún escalar único los funde |
| 5 | **DCF que admite su contradicción** | Medio | Medio | Si DCF y múltiplos divergen, baja la confianza; si el grid no contiene el precio, lo advierte |
| 6 | **Capa conductual + noticias** | Medio | Medio-alto | Panel conductual separado del score; noticias de 7 días en el informe, coste $0 |

### Secuencia recomendada

Los cambios 2 y 3 son **quick wins**: bajo esfuerzo, arreglan bugs que ensucian todos los análisis. Hacerlos primero. El cambio 1 es el estructural y habilita todo lo demás; abordarlo en segundo lugar pero reservando tiempo. Los cambios 4–6 construyen sobre esa base.

### Orden de trabajo en Claude Code

1. Extraer umbrales y medianas a `/config/*.yaml` (sin cambiar lógica aún) — prepara el terreno.
2. Parche de datos faltantes (cambio 2) + normalización (cambio 3).
3. Clasificador (cambio 1) con dos arquetipos primero (MATURE, FINANCIAL), luego ampliar.
4. Separar calidad/precio en el render del informe (cambio 4).
5. Regla de confianza en el DCF (cambio 5).
6. Capa conductual y noticias (cambio 6).

## Apéndice — Supuestos no resueltos y riesgos del rediseño

Dos debilidades que este rediseño **no** resuelve y que conviene tener presentes:

**1. Calidad de la fuente de datos.** Todo el pipeline sigue dependiendo de Yahoo Finance y la segunda API, que arrastran errores y revisan cifras retroactivamente. Un modelo serio necesita una **capa de validación de entrada** (detección de anomalías: ratios imposibles, saltos inexplicables, campos nulos) *antes* de calcular. Sin esto, el mejor motor del mundo produce basura con datos malos. No está en los seis cambios; debería ser el séptimo.

**2. Sobreajuste de la capa conductual.** Es la más difícil de volver predictiva sin engañarse. El riesgo real es construir señales que explican bien el pasado y fallan en vivo. Mitigación: tratarla como **contexto que modula la confianza**, no como señal de entrada/salida, hasta validarla contra tu propio histórico con separación estricta train/test.
