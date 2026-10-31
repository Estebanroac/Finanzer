# P8 · Portada con cintillo y mini-gráficas

*Sesión E4, 18-oct-2026. Rama `rediseno/e4-portada`. Encargo del PM, con la especificación de la mini-gráfica (maqueta
v4) y de los filtros con sectores (maqueta v6). Sin push ni fusión.*

## Qué cambia para el usuario

- **Buscador central, como antes.** Debajo, en lugar de las tarjetas fijas de tendencias, un **cintillo** a todo el
  ancho que rota solo, con 30 valores de la lista elegida.
- **Cada valor** lleva su ticker, el precio, la variación del periodo (▲/▼, cifras tabulares, verde o teja; en 1D, la
  de la sesión con el cierre oficial, la misma de las listas) y el
  nombre. A la derecha, su **mini-gráfica**. Debajo, tras una línea discontinua, «Calidad N · Precio N» si el motor ya
  la tiene en caché; si no, no lleva esa línea. Toda la tarjeta enlaza a `/v2/{T}`.
- **Filtros centrados.**
  - Fila 1: «Hoy» (o «Última sesión» si la sesión no es la de hoy, como en fin de semana) con «Más negociadas»,
    «▲ Suben más» y «▼ Bajan más»; un separador; «Gráficas» con «1 día · 1 semana · 1 mes · 6 meses».
  - Fila 2: «Sectores» con ocho chips y «Más ▾», un menú con Materiales, Servicios públicos e Inmobiliario.
  - Una sola selección activa entre las listas del día y los sectores. El periodo es independiente: cambia todas las
    gráficas y la variación, no la lista.
- **Línea de contexto** centrada bajo el cintillo, con el botón «Pausar» al lado. Por ejemplo: «Más negociadas ·
  sesión del 16 de octubre de 2026 · gráficas y variación: 1 día, con retraso · universo: S&P 500 y ADR principales ·
  30 valores», o «Tecnología · las más negociadas del sector · sesión del…».

## Mini-gráfica (maqueta v4)

- SVG de 136 × 52 (escala con el contenedor), sin Lightweight Charts. Se carga después del primer pintado y no
  bloquea el buscador.
- **Trazo:** curva Catmull-Rom → Bézier de 1,6 px, uniones y extremos redondeados.
- **Datos reales:** en 1D, las barras de 5 min de la sesión. Los puntos se reducen en el backend con LTTB, como mucho
  60; el eje x es el índice de la barra original.
- **Referencia:** punteada y gris (0,75 px, guiones 1,5/2,5) en el precio de partida: el cierre anterior en 1D y el
  primer cierre en 1S, 1M y 6M. La escala vertical la incluye siempre.
- **Relleno:** degradado vertical del color de la serie, de 0,14 a 0.
- **Último precio:** punto de radio 2,4 con borde del color de la superficie, y halo de radio 5 al 14 %.
- **Color** por el signo de la variación del periodo: `--good` o `--bad` (teja), neutro si es 0. Con los tokens del
  tema también en oscuro.

## Movimiento y accesibilidad

- **Animación:** `transform` CSS sobre dos copias de la lista. La copia que cierra el bucle va `aria-hidden` e `inert`
  (no se lee ni recibe el foco). La velocidad es fija: 4 s por valor.
- **Pausa (WCAG 2.2.2):**
  - se pausa al pasar el ratón y con el foco dentro;
  - el botón visible «Pausar / Reanudar» la para y la reanuda.
- **«Reducir movimiento»:** sin animación ni copia, y sin botón (nada se mueve). Fila deslizable con imán
  (`scroll-snap`).
- **Con el dedo o con el teclado:** al tocar el cintillo, o al llevar el foco a un valor, pasa a fila deslizable y
  conserva lo que se veía. Se puede pasar con el dedo, y el valor con el foco queda a la vista con su marco. «Reanudar»
  vuelve a la animación.
- **Chips:** botones con `aria-pressed` en grupos con nombre. «Más ▾» es un menú: `aria-haspopup`/`aria-expanded`,
  opciones `menuitemradio`; flechas, Escape (el foco vuelve al botón) y clic fuera lo cierran.
- **Móvil (≤ 640 px):**
  - las dos filas de chips se deslizan en horizontal dentro de su fila, no la página;
  - el periodo va en su propia fila, centrado y siempre entero a la vista (en la maqueta de móvil se perdía);
  - objetivos táctiles de 44 px.
- **Sector escaso:** con menos de `min_sector_items` (6) valores con cotización, el chip sale deshabilitado
  (`aria-disabled`), con su motivo en el título. No se oculta ni deja hueco.

## Backend

**`GET /api/v2/sparklines?symbols=A,B,…&period=1D|1S|1M|6M`** (`lib/sparklines.py`)

- **Entrada:** como mucho 40 símbolos, con la misma regla de símbolos que el resto de `/v2`, y un periodo de config.
  Si no se cumple, 422. Los símbolos se normalizan (BRK.B → BRK-B) y se quitan los repetidos.
- **Por símbolo:**
  - los puntos reducidos con LTTB (≤ 60) como [índice, cierre], con `n` barras;
  - `ref` y su base («cierre anterior» o «primer cierre»), el último precio y la variación del periodo;
  - las fechas del primer y del último punto;
  - o `sin_dato` con su motivo.
- **Intervalos de Yahoo** (config `market.sparklines.periods`): 1D = 5m/1d, más una descarga diaria de 5 días para el
  cierre anterior; 1S = 30m/5d; 1M = 1d/1mo; 6M = 1d/6mo.
- **Caché** por (símbolo, periodo), acotada con `lib/bounded.py` (`cache_max` 600). Vida de 5 min en 1D y de 1 h en el
  resto. Solo se guardan las series buenas.
- **Concurrencia:** las descargas pasan por la puerta acotada que ya existía para las descargas perezosas de `/v2`
  (`price_history._chart_gate`: 2 a la vez, una por clave, y el fallo recordado 60 s). No hay precalentado: toda
  descarga la pide un usuario, así que nunca compite con un precalentado.
- **Yahoo caído:** cada valor sale sin gráfica y con el motivo («Yahoo no respondió (ConnectionError)»). Nunca un 5xx.

**Listas por sector** (`lib/trending.py`)

- `compute()` devuelve también `sectors`: por clave GICS en inglés, los `top_n` de más volumen en dólares. Cada fila
  tiene la misma forma que las demás y lleva además `sector`. Junto a ella va `sector_status`, con la etiqueta en
  español (de config), el número de valores, si está disponible y por qué no.
- Sale de la misma descarga del universo: ninguna llamada nueva a Yahoo.
- Los empates se deshacen por símbolo.
- **`top_n` pasa de 10 a 30** (el cintillo rota unos 30 valores).
  - El precalentado sigue con su cupo de 30 al día, en el orden de la portada: son las 30 más negociadas, la lista con
    la que abre.
  - Las tarjetas de sector muestran «Calidad · Precio» si el resumen ya está en caché.

**Sector de los ADR, en origen**

- Los 40 ADR del universo no tenían `gics_sector`.
- `config/market.toml` declara `[universe.adr_sectors]`, una tabla explícita y documentada de símbolo → sector GICS.
- `tools/build_universe.py` la aplica al generar el TSV. El nuevo `--sectors-only` la reaplica sin red al archivo
  actual (mismos valores y fecha).
- Se regeneró así: solo cambia la columna de sector de los 40 ADR, comprobado columna a columna.
- Test: ningún valor del universo queda sin sector, y la tabla cubre todos los ADR de `market.universe.adrs` con
  claves GICS.

## Medidas

**Mini-gráficas, 30 valores × 4 periodos, Yahoo en vivo (local):**

| Periodo | En frío | En caché | Respuesta (gzip) | Con gráfica |
|---|---|---|---|---|
| 1D (barras + cierre diario) | 2,58 s | 0,03 ms | 32,1 KB (9,1 KB) | 30 de 30 |
| 1S | 1,03 s | 0,03 ms | 32,0 KB (9,5 KB) | 30 de 30 |
| 1M | 0,88 s | 0,03 ms | 15,3 KB (4,3 KB) | 30 de 30 |
| 6M | 0,91 s | 0,03 ms | 31,6 KB (10,7 KB) | 30 de 30 |

- **Memoria de la caché:** 703 KB para las 120 series (5,9 KB por serie). Con el tope de 600 entradas, como mucho
  unos 3,4 MB.
- **Captura de las fixtures para el replay:** 327 símbolos, todos los de las listas y los sectores. Unos 10 s por
  periodo en lotes de 40.

**`/api/v2/trending` con los sectores:**

| Respuesta | Sin comprimir | gzip |
|---|---|---|
| Antes (3 listas × 10) | 5,8 KB | 1,8 KB |
| 3 listas × 30 | 16,9 KB | 4,2 KB |
| Con sectores (3 × 30 + 11 × 30) | 76,3 KB | 17,3 KB |

**Lighthouse 12.8.2 de `/v2`** (build servido por el backend del replay, con la compresión gzip de V4; JSON en
`docs/rediseno/capturas-p8/`):

| Portada | Rendimiento | Accesibilidad | LCP | CLS | TBT |
|---|---|---|---|---|---|
| Escritorio | **100** | **100** | 0,8 s | 0,026 | 0 ms |
| Móvil | **91** | **100** | 3,5 s | 0 | 0 ms |

Objetivos de E4 (escritorio ≥ 90 / ≥ 95; móvil ≥ 80 / ≥ 95): cumplidos. Antes del cintillo, E4 medía 100 / 100 y
96 / 100.

## Pruebas

- **Backend.**
  - `tests/test_sparklines.py`:
    - validación y 422 (sin símbolos, periodo, regla de símbolos, tope de 40);
    - LTTB (extremos, pico y valle);
    - reducción en el backend;
    - referencia de 1D y de 1M;
    - última sesión en 1D;
    - Yahoo caído (sin 5xx);
    - símbolo ausente;
    - caché con TTL y acotada;
    - replay: las 30 más negociadas con gráfica en los 4 periodos, y su variación de 1D igual a la de las tendencias.
  - `tests/test_trending.py`: listas por sector con datos ficticios, empates por símbolo, sector escaso y vacío,
    `engine` en las tarjetas de sector, y sectores con la descarga capturada (ADR incluidos).
  - `tests/test_universe.py`: ningún símbolo sin sector.
- **Replay.**
  - `tests/fixtures/sparklines/*.json`, de `tests/capture_sparklines.py`, conectadas en `tests/replay_server.py`.
  - El fallo `yahoo_down` también tumba las mini-gráficas.
- **Frontend.**
  - `sparklines.test.ts`: curva, escala con referencia, eje x por índice, sin serie y serie plana.
  - `tickerModel.test.ts`: selección, chips y «Más», línea de contexto, «Hoy», variación por periodo y línea del motor.
- **e2e** (`e2e/v2/home.spec.ts`, en 4 proyectos):
  - pausa con el ratón y con el botón, y la copia `inert`;
  - «reducir movimiento»;
  - cambio de periodo, de lista y de sector, con el menú «Más»;
  - teclado: chips, menú y foco en los valores;
  - sin desplazamiento horizontal y periodo visible y táctil a 375 px;
  - sector escaso, simetría, calculando, sin dato y Yahoo caído para las mini-gráficas;
  - axe en claro y oscuro.
  - Se ajustaron las e2e de capturas, fuentes caídas y rutas de la API.
- **Resultados.**
  - Backend: 5160 tests en verde. Los golden no cambian: P8 no toca el análisis.
  - Frontend: `npm run check`, `tsc`, `eslint` y 104 tests de vitest en verde.
  - e2e de `/v2` contra el build: 665 en verde, 0 fallos (279 omitidas por proyecto). Las de la portada y las capturas:
    74 en verde.
  - e2e de fuentes caídas: 71 de 72 a la primera. «yahoo_down · /v2» falló una vez en mobile-webkit y no se reprodujo
    al repetirla 15 veces (4 + 12), todas en verde.
- **Capturas** en `docs/rediseno/capturas-p8/`: escritorio y móvil, en claro y oscuro (WebP; el cintillo, detenido
  en su primera posición para la captura).

## Archivos

- **Backend:**
  - `lib/sparklines.py` (nuevo), `lib/trending.py`, `main.py` (endpoint);
  - `config/market.toml` y `config/schema.toml`, `config/universe.tsv`, `tools/build_universe.py`;
  - `tests/capture_sparklines.py` y sus fixtures, `tests/replay_server.py`, `tests/faults.py`;
  - tests.
- **Frontend:**
  - `src/v2/home/TickerStrip.tsx`, `Sparkline.tsx` y `tickerModel.ts` (nuevos);
  - `src/v2/lib/sparklines.ts` (nuevo);
  - `HomeClient.tsx`, `home.css` y `src/lib/api.ts` (tipos);
  - se retiran `Trending.tsx` y `TrendCard.tsx`, las tarjetas fijas.

## Retoques tras la revisión del PM (P8 aprobado en e7cfa4d)

- **Tarjetas sin análisis en caché** (f8859de). TSLA y META no tenían línea inferior y su tarjeta tenía un hueco.
  Ahora llevan la misma línea con «Ver análisis →», en el color de enlace y del mismo tamaño. Test e2e: todas las
  tarjetas miden el mismo alto y tienen su línea inferior.
- **Nombres coherentes** (8ffa0ea). El universo lleva `display_name` sin la forma jurídica final: «Apple Inc.» pasa a
  «Apple» y «Tesla, Inc.» a «Tesla». La regla y las excepciones están en `config/names.toml [company]`; por ejemplo,
  «The Coca-Cola Company» pasa a «Coca-Cola» y «TOYOTA MOTOR CORP/» a «Toyota». El nombre legal no cambia. Test sobre
  todo el universo: ningún nombre termina en forma jurídica ni queda vacío.
- **Buscador en móvil** (este commit). En pantallas estrechas (< 48em) el texto de ayuda es «Empresa o ticker»; en
  escritorio se queda el largo. Test e2e en los cuatro dispositivos: el texto de ayuda cabe en el campo.
- Capturas de `capturas-p8/` al día con los tres retoques.

## P8b · listas en el periodo elegido, sin botón «Pausar» y carrusel desplazable

Rama `rediseno/p8b-portada`, desde la v4 (d79a2aa). Solo la portada y su backend.

- **Listas en el periodo (f9aae5c).** El usuario vio «Bajan más · 6 meses» con PLTR ▲27 %, DDOG ▲95 % o P ▲85 %: la lista
  salía de la variación del día y la tarjeta enseñaba la de 6 meses.
  - Ahora las listas y los sectores se calculan en cada periodo (1D, 1S, 1M, 6M). La variación es el cierre ajustado de
    la última sesión frente al de hace 1, 5, 21 o 126 sesiones (`lib/period_change.py`). Las mini-gráficas usan esa
    misma función, así que el % de la tarjeta es el que ordena la lista.
  - «Suben más» solo trae valores que suben y «Bajan más» solo los que bajan; si no llegan a 30, la línea de contexto
    lo dice.
  - «Más negociadas» y los sectores ordenan por el volumen medio diario en dólares del periodo.
  - Las etiquetas pasan a «Listas» y «Periodo» (uno solo para las listas y las gráficas). La línea de contexto dice,
    por ejemplo, «Bajan más en 6 meses (del 17-abr-2026 al 16-oct-2026) · …».
  - **Medidas** de la descarga del universo (543 símbolos, lotes de 100), proceso aparte:
    - 5 días: 18 s y pico de RSS +48 a +50 MB;
    - 6 meses: 18 s y pico de RSS +39 a +49 MB.
    - El Python retenido con los marcos enteros: 4,9 MB frente a 8,1 MB. El backend solo guarda listas compactas y las
      variaciones.
    - Conclusión: la memoria no sube de forma apreciable.
  - La descarga usa `start` = hoy − `history_days` (190 días naturales) en lugar de `period="6mo"`: con «6mo» Yahoo trae
    126 o 127 sesiones según el valor, y la variación de 6M necesita 127.
- **Sin botón «Pausar» (WCAG 2.2.2).** El cintillo se detiene al pasar el ratón, al enfocar un valor con el teclado y
  al tocarlo o arrastrarlo; con «reducir movimiento» no se anima. Eso cubre WCAG 2.2.2 (pausar, detener, ocultar) sin
  botón: el usuario lo detiene con cualquier interacción.
- **Carrusel desplazable (este commit).** Antes, el cintillo se movía con un transform CSS y no se podía desplazar con
  el ratón ni con el trackpad. Ahora es un contenedor desplazable de verdad (`overflow-x: auto`, sin barra visible)
  cuyo `scrollLeft` avanza solo con requestAnimationFrame (`src/v2/home/useCarousel.ts`).
  - Bucle infinito: el contenido va duplicado y la posición se reajusta en [0, ancho de una copia], también hacia
    atrás.
  - De forma nativa funcionan el trackpad con dos dedos (deltaX), sin secuestrar la rueda vertical de la página, el
    dedo en móvil y las flechas con el foco (la tarjeta anterior o la siguiente, a la vista).
  - Arrastre con el ratón (pointer events) con inercia suave. Si se arrastra más de 5 px, se cancela el clic: la
    tarjeta no se abre al soltar. Cursor grab/grabbing.
  - Cuándo avanza solo: un solo estado con temporizador de reanudación, que cada gesto cancela y reprograma.
    - Ratón encima: parado.
    - Al sacar el ratón: arranca en el acto. **V4b**: antes a los 1,5 s; el usuario: «que arranque apenas quito el
      mouse». Medido: 13 ms en Chromium y en WebKit.
    - Tras arrastrar: arranca al terminar la inercia, sin espera extra (~1 s desde la velocidad tope).
    - Tras la rueda horizontal, el trackpad o el dedo: arranca al terminar el desplazamiento nativo, con su inercia.
      Donde existe se usa `scrollend`; en Safari, 120 ms sin eventos de scroll. Con el dedo apoyado, parado. Si el
      ratón sigue encima, arranca en cuanto salga.
    - Foco de teclado dentro: parado; al salir el foco, arranca en el acto.
    - Con «reducir movimiento»: nunca arranca solo ni hay inercia, y queda el imán por tarjeta.
    - Al reanudar sigue desde donde esté, sin saltos.
  - **Fallo corregido (prueba del usuario).** El carrusel se quedaba parado para siempre tras desplazarse.
    - Causa: al pulsar para arrastrar, la tarjeta recibía el foco y el estado «foco dentro» no se soltaba.
    - Arreglo: el ratón encima y el foco se leen en vivo en cada fotograma (`:hover` y `:focus-visible`), así que el
      foco que deja un clic no cuenta y no queda ningún indicador puesto.
    - También: la velocidad del arrastre tiene tope (en WebKit, unos eventos muy seguidos la disparaban) y salir con
      el ratón reanuda a los 1,5 s, no a los 3 s.
    - e2e «el cintillo vuelve a arrancar solo»: tras sacar el ratón, tras arrastrar y salir, tras la rueda horizontal y
      salir; y quieto con el ratón encima. Las dos primeras fallaban antes del arreglo.
  - Los bordes izquierdo y derecho llevan un degradado suave (máscara): las tarjetas cortadas se leen como «hay más».
  - e2e: avance y pausa sin botón, con la reanudación a los 3 s; arrastre sin abrir la tarjeta; rueda horizontal y
    bucle hacia atrás; rueda vertical que sigue moviendo la página; sin avance con «reducir movimiento»; foco y
    flechas.
- **Capturas** en `capturas-p8/`: `bajan-6m-antes.webp` (la v4 en d79a2aa: TWLO ▲74 %, MRNA ▲306 % en «Bajan más · 6
  meses») y `bajan-6m-despues.webp` (CHTR ▼53 %, ALB ▼51 %…, del 17-abr-2026 al 16-oct-2026). Las cuatro de la
  portada, al día. Para que sean estables, las capturas emulan «reducir movimiento».

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
