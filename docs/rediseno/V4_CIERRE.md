# Cierre de la v4 (`rediseno/v4-f8`)

Pasada final oficial sobre `rediseno/v4-f8`, con F8, F9 y la v4 fusionadas (27–28 oct 2026). La pre-pasada sobre la v4
sin F8 está en [`V4_PREPASADA.md`](V4_PREPASADA.md). Sin push, sin merge a `main` y sin despliegue.

## 1. Qué incluye la v4

La web nueva vive en `/v2`, junto a la actual, que no cambia: `/` y `/stock/{T}` siguen como en `main`, salvo lo
aceptado en §3. La sirve el mismo backend desde `frontend/out`, con la API en el mismo origen.

- **Portada (`/v2`).**
  - El buscador.
  - Un cintillo de valores que avanza solo. Se para con el ratón encima o con el foco del teclado, se arrastra, cierra
    el bucle con una copia y respeta «reducir movimiento».
  - Las listas (más negociados, los que más suben y los que más bajan) y los filtros por periodo y sector.
  - Mini-gráficas por valor.
  - Las tendencias se calculan en una cola de fondo compartida con los análisis.
- **Pantalla de carga.** Anillo, «Analizando», el nombre corto y el ticker, cinco estaciones al mismo ritmo y el paso
  para lectores de pantalla. Muestra un error en menos de 2 s si la fuente falla y tiene «Volver a intentarlo». Del
  análisis en caché se entra directo.
- **El análisis, en nueve secciones con ruta propia** (`/v2/{T}/{sección}`):
  1. La empresa
  2. Cómo gana dinero
  3. La acción
  4. Calidad
  5. Cuánto vale
  6. Rivales
  7. Riesgos
  8. Actualidad
  9. Conclusión

  Cabecera fija con el precio, la variación del día, la conclusión y las tres puntuaciones con sus escalas. Cada
  sección: su lectura, sus cifras clave, todo su detalle a la vista (nada plegado; el desglose de las puntuaciones,
  fijo en «La empresa») y el paso a la siguiente. Tema claro y oscuro sin parpadeo, móvil a 375 px, accesibilidad AA.
- **PDF nuevo** (`/api/v2/pdf/{T}`, reportlab con el sistema visual de la web):
  - una portada de una página: identidad, conclusión, puntuaciones, gráfica de precio y cifras clave;
  - un índice con enlaces y marcadores;
  - los capítulos de la web;
  - la metodología y el anexo técnico;
  - cada página llena, sin huecos.

Lo que se hizo en cada etapa está en los registros: E1 a E5 y P8 en `docs/rediseno/*_REGISTRO.md`, V4b en
`verificacion/V4b_*`. Los arreglos de esta pasada, en §2.1.

## 2. Resultados de la pasada final

Sobre `rediseno/v4-f8` desde 2c39b9cd (F9 y el carrusel fusionados), con los arreglos de esta pasada (§2.1).

- **Qué se corrió sobre qué:** las suites y V3 a V5 corrieron antes del arreglo de 1024 (791683dd), que solo toca
  la tabla de rivales entre 1024 y 1279 px. V1 corrió con él.
- **Navegadores:** Chromium (Chrome y Edge) y WebKit (Safari, iPhone y iPad). Firefox queda fuera del alcance (§5).

| Verificación | Resultado |
|---|---|
| **Backend** (`pytest`) | **6.028 pasadas**, 8 saltadas, 0 fallidas |
| **Vitest** | **142** |
| **`npm run check`** (literales, contrato con 46 salidas, vocabulario) | en verde |
| **e2e:v2** contra el build (4 proyectos) | **871 pasadas, 0 fallidas**, con los arreglos (antes de ellos: 863/0) |
| **e2e:perf** contra el build | **3 de 3**. INP p75: 32 ms (Chromium ×4), 48 ms (móvil ×4) y 32 ms (WebKit) |
| **V1** · panel sin red: Chromium y WebKit × 1440, 1024, 768 y 375 × claro y oscuro (37 tickers del replay y la portada) | **6.112 de 6.112 páginas correctas** (608 tests): consola, excepciones, red, simetría (también dentro de tarjetas y tablas), letra ≥ 12 px y axe sin infracciones graves. A 1024 salió un desbordamiento, arreglado antes de la corrida final (§2.1). `verificacion/V1_matriz_cierre.md` (las columnas de Firefox salen «sin ejecutar»: fuera del alcance). **NU e ITUB en vivo** (backend real, mismas 8 combinaciones × 2 temas): **32 de 32 tests, 320 páginas** |
| **V2** · fuentes reales: NU, ITUB, VZ, PLD, AMZN, MC.PA y JPM, con coherencia web ↔ PDF de la portada | **7 de 7**: todos los endpoints 200 (y los 422 esperados del escenario). 70/70 páginas sin errores. Coherencia web ↔ PDF de la portada: **0 fallos y 0 avisos**. `verificacion/V2_oficial_tablas.md`, `V2_coherencia_portada.md` |
| **V3** · fuentes caídas (9 fallos y sin fallo × portada, historia y 9 secciones × 4 proyectos) | **438 de 440**. Los 2 fallos (portada con Yahoo caído, en WebKit) se arreglaron (§2.1); con el arreglo, los 40 casos de la portada pasan |
| **V4** · pantalla de carga (`carga.spec`, 4 proyectos ×3) | **72 de 72** |
| **V4** · carga y memoria con fuentes reales (20 usuarios, 4 análisis a la vez, como Render) | **12 min: todos los criterios en verde.** Cifra definitiva, con el rendimiento fusionado y el precalentado en el calentamiento: 0 5xx de 8.147 peticiones; p95 del análisis en caché 0,131 s; espera máx. de un usuario 1,9 s; pico **388 MB** (< 450); 2.ª mitad +14,1 MB (< 25). No es una fuga (§2.3). La de la pasada (pico 435 MB) llevaba el precalentado dentro de la carga (nota de §2.3). `verificacion/V4_carga_arnes_12min.md` |
| **V5** · producción simulada | La portada de la web actual, idéntica a `main` en los 4 tamaños. `/stock/AAPL` difiere solo en la línea de sector e industria (diferencia aceptada, §3). `produccion.spec` 49/49, con `robots.txt`. CSP 20/20 |
| **Lighthouse** (build servido por el backend) | Ver la tabla de abajo. Accesibilidad, buenas prácticas y SEO a 100 en todas |
| **Firefox** | Fuera del alcance por decisión del usuario (§5) |

**Lighthouse** (rendimiento; accesibilidad, buenas prácticas y SEO a 100 en todas):

| Página | Escritorio | Móvil |
|---|---|---|
| `/v2` | 100 | 96 |
| `/v2/AAPL` | 100 (era 97, con CLS 0,104: §2.1) | 90 |
| `/v2/AAPL/valor` | 100 | 90 |

### 2.1 Fallos de presentación de esta pasada, arreglados con su test

| Fallo | Causa | Arreglo y test |
|---|---|---|
| **V3, portada con Yahoo caído en WebKit (tableta y móvil): «Failed to load resource: The network connection was lost»** | La portada sondeaba las tendencias cada 5 s (`market.trending.poll_s`), lo mismo que el keep-alive de uvicorn (`timeout_keep_alive` = 5 s). El sondeo reutilizaba la conexión justo cuando el servidor la cerraba. Chromium reintenta; WebKit no | `poll_s` a 4 s, como el de los rivales, y el primer reintento del cliente también a 4 s. `test_poll_keepalive.py`: cada sondeo, menor que el keep-alive. Reproducido en WebKit 1 de 4 veces; con el arreglo, 0 de 24 (3160c4c5) |
| **V1 a 1024 px: la tabla de rivales desbordaba su caja** (AAPL 981 en 974, AMT 989 en 974) | 11 columnas con 12 px de relleno lateral por celda. Se apila por debajo de 1024 (`stack-md`); a 1024 se pinta entera y no cabía | Entre 1024 y 1279 px, relleno lateral de 8 px: cabe sin apilar. `v1-regresiones.spec`: AAPL, NVDA y BRK-B a 1024, con la tabla completa (rojo en el build anterior). Medidas AAPL, JPM, BRK-B, MC.PA, PLD y NVDA (791683dd) |
| **V1 (el test): BAC y ASML pasaban de los 300 s** | El test esperaba la gráfica de precio con un selector que ya no existe (`price-chart`; hoy `price-chart-full`, solo en «La acción»): 2 × 30 s perdidos en cada test | El selector de hoy; la gráfica de BAC aparece en 0,85 s (9c78e762) |
| **Lighthouse, `/v2/AAPL` en escritorio: CLS 0,104** | Mientras llegaba el fragmento de la sección (carga diferida), el paso a la siguiente sección quedaba a la vista bajo «Cargando la sección…» y el contenido lo empujaba | El hueco de carga ocupa la pantalla. `saltos.spec.ts`: la suma de saltos al cargar cuatro secciones, < 0,02 (antes 0,074; ahora 0). Lighthouse en escritorio: 100 (6c26eab4) |

Con la v4 se fusionaron también:

- **V1 a 1024 px** (6d176f98): el escritorio estrecho, donde las marcas de las escalas pasan a leyenda.
- **El test del carrusel V6b**, que espera por estado (e85a0db0).

### 2.2 Para el PM (motor)

1. **La memoria sube con F8 y F9.** Pico de 435 MB con 20 usuarios. Tras el trabajo de memoria (`V4_VERIFICACION.md`
   §2) era de ~335 MB, y el objetivo era ≤ 380 MB, un 25 % de margen frente a los 512 MB de Render. Hoy el margen es
   del 15 %. La caché más grande es la de EDGAR (26 MB, 131 entradas), con más series por emisor desde F9 (R3: series
   FY; R6: crédito). El resto son transitorios de análisis y PDF concurrentes, que el proceso devuelve (§2.3).
   Recalibrarlo en Render es de E6 (§6).
2. **El análisis en frío es más lento.** En la V2 con fuentes reales: p50 de 6,7 s y p95 de 10,5 s, frente a 2,4 y
   8,5 s en la V2 del 18-oct, y rivales hasta completar en p50 140 s (antes 76 s). En la carga, el análisis en frío da
   p50 4,4 s. Nada falla (0 5xx). No está medido por pieza: la explicación probable son las llamadas nuevas a EDGAR de
   F8 y F9. Medido y resuelto después: punto 5.
3. **NU: «EDGAR no respondió a tiempo»** en su historia de 10 años, en la V2 con 3 empresas a la vez. Es el
   presupuesto de EDGAR bajo concurrencia. La página lo dice con su motivo (V3 cubre ese caso).
4. **Cifras clave de la web frente a la portada del PDF:** ya coinciden en valor, precisión y etiqueta (R3). Siguen
   siendo conjuntos distintos: la web lleva precio, capitalización y beta; el PDF, crecimiento a 3 años y EV/EBITDA.
   Es una decisión de diseño, no una contradicción.
5. **Resuelto después: memoria y análisis en frío** (rama `rendimiento/v4f8-memoria`, fusionada en 9be21f3b; detalle
   en [`RENDIMIENTO_V4F8.md`](RENDIMIENTO_V4F8.md)). Tres corridas de 12 min por lado, alternadas:

   | Medida | Antes (461e9266) | Después |
   |---|---|---|
   | Pico de memoria (corridas) | 435, 386 y 452 MB | 384, 360 y 374 MB |
   | Pico de memoria (mediana) | 435 MB | **374 MB** (objetivo ≤ 380) |
   | Análisis en frío en la V2, p50 (3 a la vez) | 4,58 y 4,38 s | **2,99 y 3,79 s** (objetivo ≤ 4) |
   | Análisis en frío en la carga, p50 | 2,65–3,47 s | 1,94–2,52 s |

   - **Mismo resultado:** golden idénticos byte a byte y ninguna cifra distinta. Las comprobaciones en vivo, antes
     frente a ahora, dan el mismo JSON (segmentos 29 de 29 y EDGAR 27 de 27).
   - **Causas:**
     - los segmentos de la prima de riesgo país (F9 · R1) iban en serie en cada análisis, con otra descarga de
       submissions;
     - la caché de EDGAR descargaba la misma clave varias veces a la vez;
     - las instancias XBRL pendientes de los bancos estaban enteras en memoria (C: 48 MB de pico; HSBC: 45);
     - las notas de texto de las instancias NIIF ocupaban memoria aunque nadie las leyera (BCS: 39 MB);
     - las 16 columnas de filings de JPM se leían enteras, aunque solo se usan 6.
   - **NU** (punto 3): 0 fallos de EDGAR en 4 V2 y 6 cargas.
   - **Rivales** (punto 2): su tiempo lo marcan las capitalizaciones de Finnhub (límite gratuito) y la cola de fondo,
     no EDGAR. El «76 s» del 18-oct era la mediana de otras 51 empresas.
   - **Para E6** (§6): probar `MALLOC_ARENA_MAX=2` en Render.

### 2.3 Memoria por minuto (carga de 12 min)

Cifra definitiva, la que va a E6: una carga de 12 min sobre la punta con el rendimiento fusionado y el arnés
arreglado (a4d0f0b0), con el precalentado de las tendencias otra vez en el calentamiento
([`V4_carga_arnes_12min.md`](verificacion/V4_carga_arnes_12min.md)). `tools/memoria_por_minuto.py`, máximo de RSS y
huella física (la carga empieza en el minuto 1,4):

| Minuto | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MB | 325 | **388** | 388 | 374 | 362 | 373 | 341 | 343 | 343 | 351 | 351 | 357 | 357 | 357 |

- **Todos los criterios en verde:** 0 5xx de 8.147 peticiones; p95 del análisis en caché 0,131 s; espera máxima de un
  usuario 1,9 s (tenencia máxima 7,3 s); 2.ª mitad +14,1 MB (< 25).
- **El pico (388 MB) es la llegada de los 20 usuarios**, en los primeros 40 s de la carga. El calentamiento, con el
  precalentado dentro, llega a 340 MB.
- **No es una fuga:** primera mitad −7,8 MB/min; segunda, +3,2 MB/min, entre 341 y 357 MB, y plana en 357 MB los
  tres últimos minutos.
- **Una sola corrida:** el pico varía unos ±40 MB entre corridas del mismo código. Las tres de E2a sobre la misma
  rama dieron 384, 360 y 374 MB (§2.2, punto 5).
- **Frente a Render:** 124 MB de margen sobre 512 MB.
- **Precalentado:** 90 tarjetas (30 por lista desde P8) y 38 con análisis: el cupo diario de 30 más las que ya estaban
  analizadas. Tardó 67 s.

**Nota sobre las cargas anteriores** (las mías de esta pasada, `V4_carga_cierre*.md`, y las `PERF_*` de E2a). El
arnés leía las tarjetas con la forma de antes de P8b (`lists[lista]`; desde P8b, `lists[periodo][lista]`). Veía 0
tarjetas, dejaba de esperar a los ~20 s y los ~30 análisis del precalentado caían dentro de la carga medida. Pasaba
igual en el antes y en el después, así que las comparaciones siguen valiendo. Las cifras absolutas de esas cargas
llevan el precalentado dentro. La anterior de esta sección (pico 435 MB a los 7 min, 2.ª mitad −66,8 MB) era una de
ellas.

### 2.4 Portada rápida (rama `rediseno/v4f8-portada-rapida`)

El usuario vio que la portada tardaba en enseñar las tarjetas y las mini-gráficas. Detalle y medidas en
[`PORTADA_RAPIDA.md`](verificacion/PORTADA_RAPIDA.md).

**Causa.** La descarga del universo tarda ~28 s: es una petición a Yahoo por valor (543). Eso no depende de los días
pedidos ni mejora con más hilos.

**Arreglos:**

- la última lista buena se guarda en disco y se sirve tras un reinicio;
- el cálculo empieza al arrancar el servidor;
- las mini-gráficas de la vista inicial se descargan en el servidor;
- pasado el TTL, se sirven las mini-gráficas de antes mientras se refrescan;
- las dos descargas de 1D van a la vez;
- la última portada buena se guarda también en el navegador de cada visitante y se enseña al momento con su hora
  («Guardado en este navegador: datos de las 14:05 (Nueva York). Actualizando…») hasta que llega la del servidor.
  Nunca sustituye a una más reciente.

**Resultado (tarjetas / mini-gráficas):**

| Escenario | Tarjetas | Mini-gráficas |
|---|---|---|
| Caliente | 0,01 s | 0,01 s (también con el TTL vencido; antes, 3,2 s las mini-gráficas) |
| Reinicio con la lista en disco | 0,00 s | 0,01 s |
| Visitante que ya vino (la guardada en el navegador) | al momento | al momento |

**Aceptado (decisión del PM, 28-oct): el frío sin nada guardado.** Un arranque sin lista en disco, con un visitante
nuevo, espera la descarga (~28 s). En Render gratuito el disco se borra en cada arranque. Allí, el keep-alive (D6)
mantiene el servicio despierto y el cálculo empieza al arrancar. El caso real es el primer visitante justo tras un
despliegue. Por eso, en E6 (§6), el PM abre `/v2` tras desplegar, antes de avisar al usuario.

### 2.5 Pasada final tras F10 (30-oct, sobre b82aa686)

Entraron F10 completo, el crecimiento desde una base anómala, el margen operativo con una sola verdad, la beta con
semanas completas, el reintento de EDGAR y N5 (cada análisis arranca sus rivales en segundo plano).

| Comprobación | Resultado |
|---|---|
| Backend | **6.489 passed**, 19 skipped |
| vitest · check · tsc · eslint | **149/149** · limpio · limpio · 0 errores (3 avisos `<img>` de la web actual) |
| e2e:v2 contra el build | **878 passed**, 594 skipped, 0 fallos, 0 inestables; F13 aparte contra `next dev`: 1 passed |
| V2 real: NVDA, NU, ITUB, VZ, PLD, AMZN, MC.PA, JPM | Endpoints **8/8**, con los 422 esperados del escenario; páginas **8/8**; coherencia web ↔ PDF de la portada: **0 fallos, 0 avisos**. `verificacion/V2_final_tablas.md`, `V2_final_coherencia_portada.md` |
| Pantalla de carga | `loading_expected_s` 4,12 → **4,81**; `loading_typical_s` → **[1,77; 4,81]** (el pie: «entre 1 y 5 segundos») |
| Carga de 12 min con rivales de fondo (N5) | Todo en verde: 0 5xx de 9.121 peticiones; pico **419 MB**, 93 MB por debajo de los 512 de Render; 2.ª mitad −7,8 MB. `verificacion/V4_carga_final_12min.md` |

**Las omitidas, y por qué ninguna debería correr:**

- **Backend (19):**
  - SPY (ETF, sin display ni confianza): 6;
  - el PDF nuevo de los seis del juego antiguo `local` (sin golden de PDF v2; lo cubre `panel`): 6;
  - las que ya estaban: 6;
  - la coherencia del escaneo, que necesita `FINANZER_SCAN_CACHE`: 1. Corrida aparte, pasa con los escaneos del 29 y
    del 30-oct.
- **e2e:v2.** Las omitidas son por proyecto o capturas a mano.
  - La diferencia con otra corrida de 830 passed y 642 skipped es el modo: sin `E2E_BUILD=1` se omiten los 49 de
    `produccion.spec` y corre F13, que solo vale con `next dev`. Son 48 de diferencia.

**Pantalla de carga.** Dos recorridos de `real_sources.py` (`V2_frio_final` y `V2_frio_final_2`: servidor nuevo, 3 a la
vez), con los 90 análisis 200 que no salieron de la caché:

- **Juntos:** p50 1,77 s, p75 2,20 s y p95 4,81 s.
- **El primero:** tuvo una espera común de ~6 s en sus tres primeros análisis (7,5 s). Es coherente con el reintento de
  EDGAR. Al repetirlos en un proceso nuevo tardaron 2,7–3,2 s.
- **El segundo:** no la tuvo (p95 4,21 s). Juntos, ese caso pesa lo que pesó.
- **Con reintento:** un análisis puede llegar a ~10 s. La quinta estación espera en el 95 % («Últimos ajustes…»), muy
  lejos de `analysis_timeout_s` (120 s).
- **Sin medir:** cuántos análisis reintentaron. `retried` no sale en la procedencia; queda para después de la v4.

**Memoria** (`tools/memoria_por_minuto.py`, máximo de RSS y huella física; la carga empieza en el minuto 4):

| Minuto | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MB | 358 | 415 | **419** | 419 | 400 | 386 | 413 | 415 | 387 | 387 | 388 | 388 | 388 | 393 |

- **No es una fuga.** Primera mitad −0,0 MB/min; segunda, −1,8 MB/min, entre 387 y 415 MB.
- **No es comparable** con §2.3 (388 MB) ni con `PORTADA_carga_corta` (372 MB, 3 min). Aquellas no llevaban F10 ni los
  rivales de fondo de N5. Es una sola corrida; el pico varía unos ±40 MB.
- **El precalentado de las tendencias** tardó 240 s (antes, 67): los rivales de los análisis del calentamiento van
  antes. 46 tarjetas con análisis.

### 2.6 Integración final (30-oct): PDF rápido, revisión de COST y ayudas

Sobre ad178cb9, en este orden y sin conflictos de código:

- `rediseno/v4-pdf-rapido` (347244d3; [`PDF_RAPIDO.md`](verificacion/PDF_RAPIDO.md));
- `rediseno/v4-cost` (030c03ef; E2a, [`GOLDEN_DIFF_V4_COST.md`](../fiabilidad/GOLDEN_DIFF_V4_COST.md));
- `rediseno/v4-tips` (07b55da4; E1).

Los únicos conflictos fueron 18 golden de texto del PDF v2, que las dos ramas habían regenerado. Se regeneraron una
vez con el código fusionado (ca4dfa9d): 24 empresas. Solo cambia el texto de los umbrales de v4-tips («Umbrales del
sector (del sector)» → «Umbrales del sector», con la ayuda de la beta) y lo que se recoloca con él. Ninguna cifra. Los
golden del análisis (local y panel) no cambian.

| Comprobación | Resultado |
|---|---|
| Backend | **6.510 passed**, 19 skipped (las mismas de §2.5) |
| vitest · check · tsc · eslint · config sincronizada | **153/153** · limpio · limpio · 0 errores · sí |
| e2e:v2 contra el build | **896 passed**, 600 skipped, 0 fallos; F13 aparte con `next dev`: 1 passed. Las 6 omitidas nuevas son dos tests de v4-tips solo de escritorio |
| V2 real: NVDA, NU, ITUB, VZ, PLD, AMZN, MC.PA, JPM | Endpoints **8/8**, con los 422 esperados del escenario; páginas **8/8**; coherencia web ↔ PDF de la portada: **0 fallos, 0 avisos**. Rivales listos, 3 empresas a la vez: p50 **16 s**, p95 32 s (en §2.5, 112 y 132 s). `verificacion/V2_integracion_tablas.md`, `V2_integracion_coherencia_portada.md` |
| Primer PDF en frío (10 empresas, `PDF_RAPIDO.md`) | p50 31,3 → **11,3 s** |
| Carga corta (3 min, 20 usuarios) | Todo en verde: 0 5xx de 2.318 peticiones. Pico **440 MB**, por debajo de 450 y 72 MB por debajo de los 512 de Render; 2.ª mitad −0,0 MB. `verificacion/V4_carga_integracion_corta.md` |

**Margen de memoria y espera de los usuarios.** En la carga corta de la integración el criterio de la cola se cumplía,
pero con poco margen:

- Espera máxima de un usuario: 6,0 s, frente a una tenencia máxima de 7,4 s.
- Pico de memoria: 440 MB.
- Las dos cosas en el minuto con más turnos de fondo (los rivales de N5, ya de dos en dos, y el precalentado).

**Decisión del PM: el trabajo de fondo, a un turno con usuarios activos** (`rediseno/v4-cola`, f77ea377, fusionada en
4ace6d6c).

- **La regla, en `main._slot`:** un turno de fondo (rivales, precalentado y la descarga de las tendencias) espera si ya
  hay otro de fondo en marcha y hay usuarios esperando o activos. La prioridad no cambia.
- **«Activo»:** un usuario con turno, o que lo soltó hace menos de `data.web.loading_expected_s` (4,81 s, el p95 medido
  de un análisis sin caché). Con la máquina tranquila, los rivales siguen de dos en dos.
- **Tests:** `test_turnos_fondo.py`. Los dos clave fallan sin la regla.

Medida: tres cargas cortas por lado (3 min, 20 usuarios), alternadas. Antes, e36d55ad; después, f77ea377. Con el
servidor de la copia del usuario en reposo y su simulador encendidos: el mismo ruido en los dos lados.
Archivos: `verificacion/COLA_antes_{1,2,3}`, `COLA_despues_{1,2,3}` y `COLA_pdf.json`.

| | Antes | Después |
|---|---|---|
| Pico de memoria | 408 / 421 / 432 MB (mediana 421) | 405 / 413 / 414 MB (mediana **413**; peor caso, **98 MB** de margen en Render) |
| Espera máxima de un usuario | 6,2 / 6,7 / 8,0 s (mediana 6,7) | 3,5 / 4,6 / 5,0 s (mediana **4,6**) |
| Criterios en verde | 2 de 3 (la 3.ª: p95 del análisis en caché, 2,9 s > 2,0) | **3 de 3** |
| Primer PDF, una sola persona (HD, NVDA, KO, JPM) | mediana 8,4 s | mediana 10,5 s |
| Rivales listos, ídem | mediana 10,2 s | mediana 12,5 s |

- **Por qué sube el primer PDF:** el usuario que acaba de pedir su análisis o su PDF cuenta como activo 4,81 s, así que
  en esos segundos sus propios rivales van de uno en uno.
- **Decisión del PM:** aceptado. El uso real es casi siempre de una persona; 10,5 s, con el aviso del botón, está bien,
  y lo que importa para subir es el margen de memoria.
- **Para después de la v4:** la ventana 0 («activo» = con turno o esperándolo). Quitaría casi toda la subida con una
  persona y, bajo carga, conservaría casi toda la protección. Hay que medirla con otras seis cargas alternadas.

### 2.7 Cierre de la integración (31-oct): pase móvil y EBITDA de NFLX

Sobre 46a9b78f (§2.6), sin conflictos de código:

- `rediseno/v4-movil` (aad96e84; E1, pase móvil de /v2), en 8f060e39 y f6001325;
- `rediseno/v4-ebitda` (5f4eb206; E2a, [`GOLDEN_DIFF_V4_EBITDA.md`](../fiabilidad/GOLDEN_DIFF_V4_EBITDA.md)), en
  07988eaa. El D&A del EBITDA sale de EDGAR sin amortizaciones de activos operativos recurrentes (NFLX sumaba la de su
  contenido), y EV/EBITDA > 100x se muestra acotado.

Golden y fixtures, regenerados una vez (31d4c988):

- **PDF v2 de NFLX:** solo se repagina. Las dos ramas cambiaban su texto; ninguna cifra ni frase cambia.
- **Fixture v2 de BCS:** la nota de la provisión, con el texto sin jerga de movil.
- **Sin cambios:** los golden del análisis (local y panel) y las muestras forzadas.

| Comprobación | Resultado |
|---|---|
| Backend | **6.531 passed**, 19 skipped (las mismas de §2.5) |
| vitest · check · tsc · eslint · config sincronizada | **153/153** · limpio · limpio · 0 errores · sí |
| e2e:v2 contra el build | **910 passed**, 614 skipped, 0 fallos; F13 con `next dev`: 1 passed. Las 14 omitidas nuevas son `movil-rejilla.spec`, que solo corre por debajo de 768 px |
| V2 real: NVDA, NU, ITUB, VZ, PLD, AMZN, MC.PA, JPM y **NFLX** | Endpoints **9/9**, con los 422 esperados del escenario; páginas **9/9**; coherencia web ↔ PDF de la portada: **0 fallos, 0 avisos**. Rivales, 3 empresas a la vez: p50 20 s, p95 36 s. `verificacion/V2_cierre_v4_tablas.md`, `V2_cierre_v4_coherencia_portada.md` |
| NFLX con fuentes reales | Margen EBITDA **32,1 %**, EV/EBITDA 16,6x; precio **58 «razonable»**, calidad 88 «excelente» |
| Tres cargas cortas (3 min, 20 usuarios) | Todas en verde y 0 5xx. Picos **448 / 444 / 412 MB** (mediana 444; 64 MB de margen en Render en el peor caso). Espera máxima de un usuario 4,4 / 4,7 / 4,1 s, por debajo de la tenencia (7,3 / 7,3 / 6,9). `verificacion/V4_carga_cierre_v4_corta{,_2,_3}.md` |

**El pico de memoria, frente a §2.6.** La mediana sube de 413 MB (tres cargas con la cola, f77ea377) a 444 MB.

- **Sin diferencia por análisis.** Con el método determinista (los mismos 12 análisis, 4 a la vez, en un solo proceso,
  `tools/perf_frio.py --mem`), antes de ebitda (f6001325) dan 313 y 321 MB, y después (31d4c988), 321 y 321 MB. v4-ebitda
  no añade memoria por análisis, y v4-movil es casi toda web.
- **Dentro de la variación conocida.** La diferencia de las cargas cabe en los ±40 MB entre corridas: la tercera de este
  cierre dio 412 MB.
- **Sin descartar del todo.** Para descartarla del todo harían falta tres cargas alternadas por lado.
- **El margen frente a Render** sigue por encima de 60 MB en el peor caso, y el criterio de la cola se cumple en las tres.

### 2.8 Última rama (31-oct): color en las barras de posición

`rediseno/v4-color-barras` (a926ecac; E1, aprobada por el usuario), fusionada en f7d011e2 sobre e550fe37. Partía de
ese mismo commit: sin conflictos.

- **Color de las barras de posición, en la web y en el PDF v2.** El escenario da `upside_reading`
  (`display.read_upside`).
- **Tarjetas del carrusel compactas en el móvil.** Solo las tarjetas: los chips, el periodo y la línea de contexto,
  como estaban.

Golden y fixtures ya coinciden con el código fusionado (E1 los regeneró sobre la misma base), así que no hubo que
regenerar nada:

- análisis local y panel, sin diferencias;
- PDF v2, sin diferencias;
- muestras forzadas, al día;
- reexportar las fixtures de /v2 no cambia ninguna.

| Comprobación | Resultado |
|---|---|
| Backend | **6.531 passed**, 19 skipped (las mismas de §2.7) |
| vitest · check · tsc · eslint · config sincronizada | **153/153** · limpio · limpio · 0 errores · sí |
| e2e:v2 contra el build | **930 passed**, 634 skipped, 0 fallos; F13 con `next dev`: 1 passed. Las 20 omitidas nuevas son `color-barras.spec` en los dos proyectos WebKit (solo Chromium: los colores calculados) |
| V2 real: NVDA + 7 y NFLX | Endpoints **9/9**, con los 422 esperados; páginas **9/9**; coherencia web ↔ PDF de la portada: **0 fallos, 0 avisos**. NFLX sin cambios: margen EBITDA 32,1 %, precio 58 «razonable», calidad 88. `verificacion/V2_cierre_v4_color_tablas.md`, `V2_cierre_v4_color_coherencia_portada.md` |
| Carga corta (3 min, 20 usuarios) | Todo en verde: 0 5xx de 2.146 peticiones. Pico **437 MB**, dentro de la horquilla de §2.7 (412–448); 2.ª mitad +4,7 MB. Espera máxima de un usuario 4,7 s, frente a una tenencia de 9,6 s. `verificacion/V4_carga_cierre_v4_color.md` |

**Esta V2, más lenta que la de §2.7.** Análisis p50 4,1 s (antes, 2,4 s) y rivales p50 28 s (antes, 20 s). La rama solo
toca en el backend el tema del PDF y `scenario.upside_reading` (36 líneas), así que es la variación de las fuentes
(Yahoo, EDGAR), no el código.

### 2.9 Rutas de E6, cintillo, etiquetas y marca (31-oct)

Encima de 79810091, en este orden y sin conflictos:

- `rediseno/v4-cintillo` (fbd74ece, E1): el cintillo de la portada en continuo, también en pantallas táctiles;
- `migracion/rutas` (de43a3fa): E6 · paso 2, las rutas de transición (`/` y `/{T}` a la v4; la web actual en
  `/clasica` y `/stock/{T}`, con el aviso «Prueba la nueva versión →»);
- `rediseno/v4-etiquetas` (96433ca8, E1): la portada móvil sin los rótulos «Listas» y «Sectores»;
- `marca/usuario` (3990ad74, E1): la marca elegida por el usuario. Logo en su placa nocturna en los dos temas, Manrope,
  favicon, manifiesto e iconos, en la web y en el PDF v2. `/manifest.webmanifest` se sirve como
  `application/manifest+json`.

Con el cintillo continuo, el test E6 de la raíz no podía hacer clic en una tarjeta en movimiento. Ahora pasa el ratón por
encima, el cintillo se para y abre la tarjeta, como `home.spec` (43d96307).

| Comprobación | Resultado |
|---|---|
| Backend | **6.539 passed**, 19 skipped (las mismas de §2.7) |
| vitest · check · tsc · eslint · config sincronizada | **153/153** · limpio · limpio · 0 errores · sí |
| e2e:v2 contra el build | **968 passed**, 648 skipped, 0 fallos (con `marca.spec`) |
| V2 real: NVDA + 7 y NFLX | Endpoints **9/9**; páginas **9/9**; coherencia web ↔ PDF de la portada: **0 fallos, 0 avisos**. Rivales p50 24 s, p95 36 s. `verificacion/V2_marca_tablas.md`, `V2_marca_coherencia_portada.md` |
| Carga corta (3 min, 20 usuarios), 3 corridas por lado, alternadas | 0 5xx en las seis. Detalle abajo |
| `legado:comparar` | La web actual cambia el logo (§3, aceptado por el PM); el resto, como antes |

**MC.PA a 375 px** (la V1 corta del paso 4 de E6). En las cifras clave, «EUR 397.00» y su «?» no cabían en una línea:
la ficha pasaba a dos líneas y la cifra de la vecina bajaba 34 px. Venía del pase móvil (c6f3d780), no de la marca. Lo
arregla `rediseno/v4-mcpa` (2fa726a7, E1), fusionada en 89cda40d: la cifra nunca se parte, el «?» va con la etiqueta y,
en el móvil, una cifra que no cabe en media fila ocupa la fila entera. Comprobado así:

- vitest 156/156;
- e2e:v2 contra el build: 974 passed, 0 fallos;
- V1 a 375 contra el backend real (las 8 de la V1 corta, Chromium y WebKit): 36/36.

**Carga corta, antes (43d96307) y después de la marca:**

| Corrida | Peticiones | Pico | 2.ª mitad | p95 del análisis en caché | Espera máx. de un usuario / tenencia |
|---|---|---|---|---|---|
| marca 1 | 1.891 | 444 MB | +1,0 MB | **3,0 s** ❌ | 7,6 / 13,9 s |
| antes 1 | 2.261 | **463 MB** ❌ | +0,9 MB | 0,22 s | 4,5 / 6,4 s |
| marca 2 | 2.240 | **460 MB** ❌ | −19,0 MB | 0,35 s | 4,5 / 12,3 s |
| antes 2 | 2.200 | **455 MB** ❌ | −55,6 MB | 0,57 s | 4,6 / 6,9 s |
| marca 3 | 2.274 | 428 MB | −49,5 MB | 0,24 s | 3,5 / 6,0 s |
| antes 3 | 2.239 | **454 MB** ❌ | −71,2 MB | 0,54 s | 4,7 / 6,7 s |

- **El p95 de 3,0 s de la primera corrida es la red, no la marca.** En esa misma corrida también iban lentos el análisis
  en frío (p95 8,8 s) y la búsqueda (p50 0,53 s), que dependen de Yahoo y EDGAR. Las dos siguientes de la marca dan
  0,35 y 0,24 s. La marca no toca el análisis en el backend: solo el tema del PDF y un tipo MIME.
- **El pico pasa de 450 MB en 4 de las 6, y en las tres sin la marca.** Medianas: 444 MB con la marca y 455 MB sin ella.
  En §2.7 la horquilla era 412–448. Queda por encima de los 512 de Render un margen de 49 MB o más.

`verificacion/V4_carga_marca{,_2,_3}.md` y `V4_carga_premarca_{1,2,3}.md`.

## 3. Diferencias aceptadas respecto a `main`

La web actual (`/clasica` desde E6, antes `/`, y `/stock/{T}`) es la de `main` píxel a píxel (`legado:comparar`, en escritorio, tableta, móvil y
móvil WebKit), con estas diferencias aceptadas:

- **`/stock/{T}`: sector e industria en español** en la línea bajo el nombre («Tecnología · Electrónica de consumo ·
  Nasdaq» en lugar de «Technology · Consumer Electronics · Nasdaq»). Viene de V7 (`b3171746`, «la cabecera … de las
  dos webs»). El PM la aceptó el 27-oct.
- **La marca nueva también en la web actual** (§2.9). Llega con la marca que eligió el usuario el 31-oct. El PM la aceptó el 31-oct (una sola marca en las dos webs). Afecta al logo de
  `/clasica`, al de la barra de `/stock/{T}` (el buscador se desplaza 11 px a la derecha) y al de la pantalla de carga,
  además del favicon. El resto de la página es idéntico a `main` (`legado:comparar`: solo cambian esas zonas).

Los datos que comparten las dos webs (el análisis del backend) son los del motor con F8 y F9. Sus cambios y su causa
están en los diff de golden (§4).

En el despliegue entran, además, cosas que no existen en `main`:

- `robots.txt`: permite todo, sin sitemap;
- `/v2` y la API `/api/v2/*` (análisis, precios, segmentos, rivales, tendencias, escenario y PDF);
- los cambios de configuración del motor de F8 y F9.

## 4. El motor: F8 y F9

- **F8**: fiabilidad del motor tras la auditoría de 26 empresas: piso del Ke, sensibilidad de ±1 pp, contracción por
  confianza, «excelente» desde 85, referencia regional y honestidad de datos.
  - Fusión, conflictos y comprobaciones en vivo: [`F8_FUSION_REGISTRO.md`](../fiabilidad/F8_FUSION_REGISTRO.md).
  - Las 26 empresas, del informe original al corregido: en ese mismo registro.
  - Cambios de golden de la fusión: [`GOLDEN_DIFF_F8_FUSION.md`](../fiabilidad/GOLDEN_DIFF_F8_FUSION.md).
- **F9**: la revisión externa del informe de NU.
  - Ke con prima de riesgo país (R1) y beta de abajo hacia arriba por región (R2b).
  - P/B justificado en dos etapas (R1b) y forward acotado al histórico (R1c).
  - Una sola beta (R2) y ninguna cobertura de intereses en bancos (R5). El margen neto de un banco no puntúa (R4).
  - Una sola verdad por cifra en la web y el PDF (R3) y riesgo de crédito medido en bancos (R6).
  - Errores menores (R7).
  - Cambios y causas: [`GOLDEN_DIFF_F9.md`](../fiabilidad/GOLDEN_DIFF_F9.md).
  - Tabla de cierre (NU y las 26, antes y después, en vivo): su última sección.
  - **Resumen:** NU pasa de «razonable» (45) a «muy exigente» (20). En las 26 cambian de nivel JPM (precio: razonable
    → exigente), TSM (exigente → muy exigente) y BCS (calidad: media → sólida).

## 5. Navegadores

**Firefox: fuera del alcance por decisión del usuario (28-oct).** Navegadores cubiertos: **Chromium** (Chrome y Edge)
y **WebKit** (Safari, iPhone y iPad), en V1, e2e:v2, V3, V4 y V5.

## 6. Pendiente para después

- **Fase B:** E7 y P2.
- **Fase C:** el subconjunto con presupuesto 0 (solo fuentes gratuitas y fiables).
- **Umbrales de crédito con FRED** (R6): hoy, riesgo de crédito medido con XBRL y FDIC.
- **E6, recalibrar la carga en Render:** la medida de memoria y la cola (`V4_VERIFICACION.md` §2) se hicieron en
  local. Hay que repetirlas en el plan de Render con F8 y F9 dentro.
- **E6, precalentar la portada tras cada despliegue:** el PM abre `/v2` y espera a ver las tarjetas (~30 s) antes de
  avisar al usuario. En Render gratuito el disco se borra al desplegar: el primer visitante esperaría la descarga del
  universo (§2.4).

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
