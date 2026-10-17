# Rediseño de la experiencia de Finanzer — especificación de diseño

*2026-10-17 · Diseñado con el usuario en sesión de brainstorming (planificador). Sustituye a `docs/rediseno/PLAN_REDISENO.md`,
que el usuario consideró simplista. Maquetas aprobadas: `docs/rediseno/maquetas/` (abrir en el navegador).*

## 1. Propósito

El motor de análisis ya es fiable (fases 0–7 del plan de fiabilidad: datos verificados contra la SEC, método por
tipo de empresa, incertidumbre honesta). La presentación no está a su altura: 9 pestañas, 36 desplegables, jerarquía
débil, espacio mal usado, sin gráficas de precio, PDF sin interactividad.

Objetivo, en palabras del usuario: *"un modelo serio e interactivo de cómo, con información confiable y de manera
agradable, entender una acción y una empresa"*. No se parte del esqueleto actual: **los datos y el motor se conservan;
la forma de mostrarlos se diseña desde cero.**

## 2. Decisiones del usuario

| # | Decisión | Elegido |
|---|---|---|
| 1 | Público | **Los dos, con capas:** primera lectura clara para cualquiera; profundidad de analista a un clic, sin cambiar de página |
| 2 | Cómo empieza la historia | **Con la empresa:** qué hace, cómo gana dinero; después calidad, precio, riesgos y contexto. La conclusión cierra la historia (y está siempre visible en la cabecera) |
| 3 | Forma del producto | **Una historia y sus capítulos:** página principal que cuenta la empresa completa; cada capítulo con su página de profundidad |
| 4 | Interacciones de la primera versión | **Las cuatro:** precio en el tiempo, escenarios de valor, comparar con rivales, historia financiera |
| 5 | Tono visual | **B · claro institucional** (fondo papel, tinta oscura, verde profundo de marca), **sin neón ni brillos** en ningún color |
| 6 | Estructura de la página | **Barra de capítulos arriba y capítulos a lo ancho**, texto y visual alternados |
| 7 | Capítulo "La empresa" | **Datos estructurados oficiales (EDGAR) + frases generadas por el motor**; hueco reservado para una descripción en prosa futura. El resumen con IA del 10-K **no** se hace por ahora |
| 8 | Rivales | **Automáticos y editables:** 4–5 de la misma industria SEC (código SIC) y tamaño parecido; el usuario quita o añade |
| 9 | Alcance | Página de empresa + **PDF** + **portada con buscador** + **modo oscuro opcional** + **móvil al mismo nivel** |
| 10 | Enfoque de construcción | **Web nueva desde cero en el mismo proyecto, en paralelo** (`/v2`), sobre el backend actual ampliado; la web actual intacta hasta el cambio |
| 11 | Puntuaciones | **Ninguna puntuación sin su escala y su base** (bandas reales del motor, cómo se calcula al pasar el ratón) |
| 12 | Nombres técnicos | **Se conservan todos** (ROIC, ROCE, EV/EBITDA, WACC, Altman Z, Piotroski…), siempre junto a su lectura en lenguaje llano; tooltips con explicación, fórmula, rangos de referencia y "Tu valor" |
| 13 | Precio en móvil | **Elemento principal de la cabecera móvil**, claramente más grande que el resto |
| 14 | Empresas populares | **Dinámicas según la actividad real del mercado**, no fijas |
| 15 | Protección | **Prototipo/diseño aprobado antes de implementar** y nada de la web actual se toca hasta el cambio final (E6) |

Preferencias de diseño permanentes del usuario: **simetría y ningún espacio muerto** ("todo en su debido lugar, sin
inconsistencias de espacio"); nada de neón; producto "bien producido".

## 3. Arquitectura de la información

### 3.1 Elementos fijos (todas las páginas de empresa)

- **Barra general:** marca, buscador, conmutador de modo oscuro, "Descargar PDF".
- **Cabecera de empresa:** nombre, ticker, bolsa, sector e industria; **precio** y variación del día; tres bloques con
  escala (maqueta `2c`):
  - **Calidad del negocio** · "¿es buena la empresa?" · `79 / 100 · sólida` · barra con las bandas del motor
    (débil < 45 · media 45–65 · sólida 65–80 · excelente ≥ 80, `config/thresholds.toml [score.quality]`) y marca del
    valor · base: "4 categorías × 20 puntos".
  - **Atractivo del precio** · "¿está cara hoy?" · bandas del motor (muy exigente < 30 · exigente 30–45 · razonable
    45–65 · atractivo ≥ 65, `[score.price]`) · base: "múltiplos frente a la referencia + DCF; acercado a 50 si la
    confianza es baja".
  - **Confianza del veredicto** · baja / media / alta · motivo en una frase.
  - Al pasar el ratón o tocar: desglose del cálculo (p. ej. 20 + 20 + 13 + 10 = 63 / 80 → 79 / 100) y enlace a la
    metodología.
- **Barra de capítulos** fija, 9 entradas de igual ancho, con el capítulo activo marcado.

### 3.2 La página-historia (maqueta `1`)

Nueve capítulos a lo ancho, en **dos columnas iguales** (texto | visual), alternando el lado. Gramática de cada
capítulo: etiqueta de capítulo → título → lectura (2–3 frases del motor) → visual clave → 3 cifras clave →
"Ver el capítulo completo →".

| # | Capítulo | Lectura y visual clave | Página de profundidad |
|---|---|---|---|
| 1 | La empresa | Qué es (industria SEC, país, tamaño, ejercicio fiscal) + la frase del veredicto | Ficha completa |
| 2 | Cómo gana dinero | Ingresos por segmento, márgenes | Segmentos e historia financiera de 10 años |
| 3 | La acción | Gráfica de precio vs S&P 500, posición en 52 semanas, rentabilidad y caída máxima | Gráfica completa (1S–5A), rentabilidad por periodo, eventos |
| 4 | Calidad | 4 categorías con barras, ROIC, ROCE, Piotroski | Rentabilidad · Solidez · Crecimiento · Calidad de ganancias · Piotroski · Altman · Historia de 10 años |
| 5 | Cuánto vale | Múltiplos frente a referencia; "el precio exige crecer X% anual"; los dos métodos | Escenarios · Qué exige el precio · Múltiplos · DCF y sensibilidad · Graham · Metodología |
| 6 | Rivales | Tabla compacta frente a 4–5 rivales | Comparador editable |
| 7 | Riesgos | Pre-mortem y principales alertas | Todos los riesgos y alertas |
| 8 | Actualidad | Noticias en tarjetas, próximos resultados, momentum (contexto, no puntúa) | Noticias y señales técnicas (D5: solo contexto) |
| 9 | Conclusión | Veredicto completo, confianza, qué vigilar | Descarga del PDF |

### 3.3 Páginas de profundidad (maquetas `2` y `4`)

- Se mantienen cabecera y barra de capítulos; debajo, **índice interno del capítulo en píldoras** (saltos a anclas).
- **Todo visible**, en rejilla simétrica. Ningún desplegable salvo el anexo técnico.
- **Tabla técnica** en cada capítulo de métricas: Métrica (nombre técnico en negrita + significado debajo) · Empresa ·
  Referencia (sector o mercado, dicho) · Brecha · Lectura (pastilla de color).
- **Tooltip "?"** por métrica (hoja inferior en móvil): nombre técnico y qué mide, fórmula, rangos de referencia del
  motor (`display.tooltips`) y **"Tu valor"** resaltado en su banda, nota de analista cuando aplique.
- **Metodología** al pie de cada página, siempre visible (fuentes, periodo de cada cifra, cálculo, origen de las
  referencias).
- **Detalle técnico para auditoría** (D1): único desplegable de toda la web.

### 3.4 Interacciones

| Interacción | Especificación |
|---|---|
| Precio en el tiempo | Rangos 1S, 1M, 3M, 6M, YTD, 1A, 3A, 5A; comparación base 100 con S&P 500 y ETF del sector; cursor con fecha y precio; volumen; eventos marcados (resultados, dividendos, splits); tabla de rentabilidad por periodo (precio y total con dividendos) frente a mercado y sector. Librería de series financieras (p. ej. Lightweight Charts de TradingView, licencia Apache-2.0; a confirmar en E1) |
| Escenarios de valor | Preajustes Pesimista / Base / Optimista; 4 controles: crecimiento años 1–5, crecimiento a largo plazo, WACC, margen de caja; rangos acotados por tipo de empresa. Resultado: valor por acción, diferencia con el precio, barra valor-vs-precio, "qué exige el precio" y tabla de sensibilidad. **Lo calcula el motor** (endpoint), no una copia en el navegador. **Nunca cambia el veredicto** |
| Rivales | Propuesta automática (§4, dato 7); quitar/añadir con buscador; tabla compacta (calidad, precio, múltiplos, crecimiento); los rivales cargan progresivamente |
| Historia financiera | Ingresos, márgenes, FCF, deuda y acciones, 10 años; clic en un año para ver sus cifras |

### 3.5 Portada (maqueta `5`)

Titular ("Entiende una empresa antes de invertir"), buscador grande, **tendencias del mercado** en tres pestañas
— *Más negociadas hoy* (volumen en dólares) · *Mayores subidas* · *Mayores caídas* — con fecha, hora y universo de
actualización; cada tarjeta muestra la calidad y el precio del motor. Tres tarjetas de confianza (datos oficiales,
método por tipo de empresa, honestidad con la incertidumbre).

Criterio conductual: las listas se titulan por lo que miden (nunca "las mejores") para no alimentar el efecto
manada; la calidad y el precio del motor junto a cada una permiten distinguir negocio de ruido.

### 3.6 Móvil

Cabecera compacta con el **precio como elemento principal** (32 px, negrita; ver §5) y la variación al lado; las tres
puntuaciones en una fila; barra de capítulos deslizable; capítulos en una columna; gráficas táctiles; tarjetas en pares
simétricos; tooltips como hoja inferior.

### 3.7 PDF (maqueta `5`)

Mismo sistema visual en tamaño carta, motor reportlab (decisión previa R-D2): portada con escalas, gráfica de precio y
claves; **índice enlazado**; **marcadores** del lector; "↑ índice" en cada página; enlaces a noticias y fuentes; un
capítulo por sección con lectura, rejilla de categorías y tabla técnica; anexo de metodología y detalle técnico. Sin
huecos: hueco máximo entre bloques definido en E5 y comprobado automáticamente.

## 4. Datos nuevos (backend)

| # | Dato | Fuente | Si falta |
|---|---|---|---|
| 1 | Serie de precios por rango y rentabilidad por periodo (precio y total) vs S&P 500 y ETF del sector; eventos | Serie diaria ya descargada (`lib/price_series.py`); dividendos/splits de la misma fuente; fechas de resultados de los filings de EDGAR | Sin gráfica, con aviso |
| 2 | Ficha: industria SIC, país, sede, cierre fiscal, empleados | EDGAR (submissions) | "Sin dato" por campo |
| 3 | Ingresos por segmento con historia | EDGAR (hechos con dimensión de segmento en las instancias XBRL) | "Sin desglose oficial"; ingresos totales |
| 4 | Historia financiera de 10 años | EDGAR (la fase 3 conserva 10+ ejercicios) | Los años disponibles, dicho |
| 5 | Piotroski con valores por criterio (año actual vs anterior) | Motor (ya los calcula) | — |
| 6 | Escenarios (endpoint) | DCF unificado de la fase 3 | — |
| 7 | Rivales: mismo SIC (si < 3 candidatos, industria más general), tamaño parecido; 5 propuestos | EDGAR + motor (análisis de cada rival, en caché) | Aviso si < 3 comparables |
| 8 | Noticias enriquecidas: titular, resumen, imagen, medio de origen, fecha, idioma original | Finnhub `company-news` (ya conectado) | "Sin noticias recientes" |
| 9 | Próximos resultados | Calendario de Finnhub o ritmo de filings ("fecha estimada") | "Sin fecha anunciada" |
| 10 | Tendencias de la portada | Cálculo diario propio tras el cierre sobre S&P 500 + ADR principales (misma descarga de precios que funciona en Render) | Última lista buena con su fecha |

Reglas: toda frase nueva pasa por el **guardián narrativo**; límites de la SEC (≤ 10 peticiones/s con User-Agent) y de
Finnhub (≤ 60/min); caché de todo; **carga progresiva por capítulos** con esqueletos (sin pantallas en blanco ni saltos
de maquetación). El plan gratuito de Render (D6) se mantiene: la primera carga de una empresa nueva puede tardar.

## 5. Sistema visual (maqueta `3`)

- **Color (claro):** papel `#F7F6F2`, superficie `#FFFFFF`, línea `#E2E0DA`, tinta `#1B1D1F`, texto secundario
  `#3A3D40`/`#6B6F73`; bien/marca `#16794A`, atención `#B07D1A`, mal `#B4532A`, neutro `#ECEAE4`.
- **Color (oscuro, opcional):** fondo `#16181B`, superficie `#1E2124`, línea `#2C3035`, tinta `#E8E6E1`; bien
  `#4F9E74`, atención `#C49A45`, mal `#C8775A`. Mismos significados, tonos apagados.
- **Tipografía y legibilidad (revisado 2026-10-17 por petición del usuario: "se me hace difícil leer… el tamaño de la
  letra es algo a lo que hay que prestarle atención"):** Geist (marca). Escritorio: lectura **16 / 1.6**, tablas 15,
  subtítulo 19, título de capítulo 28, cifra de puntuación 32, precio 32. Móvil: lectura **17 / 1.6** (cuerpo de iOS),
  tablas 15, subtítulo 19, título de capítulo 24, **precio 32 en negrita** (sigue siendo el elemento principal).
  **Mínimo absoluto 12 px** en todo (etiquetas en versalitas 12 con `letter-spacing: .08em`; ningún texto de 10 u 11).
  Línea de lectura de 60–75 caracteres. Texto secundario solo en `--text-2`/`--text-3` con contraste ≥ 4.5:1 sobre su
  fondo. Todos los tamaños en `rem` (base 16 px): la página respeta el tamaño de texto del sistema y el zoom del
  navegador sin romper la rejilla. Cifras tabulares.
- **Zoom:** el zoom con los dedos nunca se bloquea (sin `maximum-scale`, sin `user-scalable=no`, sin `touch-action` que
  lo impida); la página sigue usable y sin desbordamiento horizontal a 200 % de zoom (WCAG 1.4.4).
- **Rejilla:** 12 columnas; capítulos en 2 columnas iguales; tarjetas en filas de 2, 3 o 4 de **igual alto**.
- **Espaciado:** una sola escala (4 · 8 · 12 · 16 · 24 · 32 · 48).
- **Siempre:** color con significado; toda puntuación con escala y base; toda cifra con su periodo; contraste AA;
  movimiento sutil con "reducir movimiento".
- **Nunca:** brillos/neón; información de valor en desplegables; huecos o filas desparejas; color decorativo; cifras sin
  escala, base o periodo.

## 6. Construcción

Enfoque: **web nueva en el mismo repositorio**, en paralelo a la actual, sobre el backend existente ampliado.

| Etapa | Contenido | Aprobación |
|---|---|---|
| E1 · Sistema y página-historia | Tokens, componentes, gráfica de precio, página-historia con los 9 capítulos y los datos que ya existen; ruta `/v2`, solo en local | Revisión del usuario con 8 empresas |
| E2 · Datos nuevos | §4 completo | Diff de golden explicado y aprobado |
| E3 · Profundidad e interactividad | 9 páginas de profundidad, escenarios, comparador de rivales, gráfica completa, Piotroski en tarjetas, tablas técnicas y tooltips | Revisión por página |
| E4 · Portada, móvil y oscuro | §3.5, §3.6, modo oscuro completo | Revisión en el teléfono del usuario |
| E5 · PDF | §3.7 | Revisión de 4 PDF |
| E6 · Cambio | `/v2` pasa a principal; la antigua queda de respaldo y después se retira | "ok, pushea" |

Cada etapa: prompt de operador en `docs/rediseno/prompts/`, worktree propio, un commit por causa, nada se sube sin
"ok, pushea", bitácora al día. `/v2` solo se publica (oculta) cuando el usuario quiera probarla en su teléfono.

## 7. Verificación

1. **Fiabilidad intacta:** guardián narrativo, invariantes y contrato de datos en verde; ninguna cifra ni lectura cambia
   por el rediseño.
2. **Capturas automáticas** por capítulo de AAPL, JPM, O, NEE, XOM, PLTR, RIVN y BCS, en claro/oscuro y
   escritorio/móvil, comparadas en cada cambio.
3. **Test de simetría** sobre la página real: falla si una fila de tarjetas tiene alturas desiguales, si hay un espacio
   fuera de la escala o si algo se sale de la rejilla. Equivalente en el PDF con hueco máximo entre bloques.
4. **Accesibilidad y rendimiento:** contraste AA, ningún texto por debajo de 12 px, zoom con los dedos permitido y
   página usable a 200 % de zoom y con el texto grande del sistema, navegación por teclado, Lighthouse ≥ 90 (rendimiento y accesibilidad,
   escritorio); carga progresiva sin saltos.
5. **Revisión externa** al cierre: 2–3 personas que no conozcan la app; se anota dónde se pierden.

## 8. Fuera de alcance (por ahora)

- Resumen del negocio con IA a partir del 10-K (decisión 7): el capítulo deja el hueco preparado.
- Plan de pago de Render (D6).
- Señales técnicas en el score (D5: solo contexto).

## 9. Puntos a confirmar durante la construcción

- Librería de gráficas (E1): Lightweight Charts u otra con licencia libre; criterio: series financieras, rendimiento,
  accesibilidad.
- Disponibilidad real del desglose por segmento en EDGAR para los 8 tickers de verificación (E2); si falta en alguno,
  aplica "sin desglose oficial".
- Calendario de resultados en el plan actual de Finnhub (E2); si no, "fecha estimada" por ritmo de filings.
- Tamaño del universo de tendencias y coste diario de su cálculo en Render (E2).
