# Pre-pasada final de la v4 (antes de fusionar F8)

Encargo del PM (2026-10-27): adelantar en `rediseno/v4` lo que no depende del motor mientras las ramas F8 terminan.
Dos cosas: el país del emisor en español y una pre-pasada sobre la v4 actual para cazar fallos ya. Lo que es de
presentación se arregla aquí, con su test. Lo que es del motor se anota para el PM (sección 4). **La pasada oficial
se repite tras fusionar F8.**

Rama `rediseno/v4` desde `feb7de5b`. Commits de esta pre-pasada:

| Commit | Qué |
|---|---|
| `f9158ee4` | El país del emisor en español (tabla de nombres, como las industrias) |
| `44bf9374` | Sin desbordamiento a 375 px: el anexo de HSBC y la cabecera de MC.PA |
| `46c70fd8` | Precio y variación en una línea a dos columnas; solo se parten en el móvil (corrige la regresión de `44bf9374` en tableta) |

## 1. El país del emisor en español (`f9158ee4`)

Antes, «La empresa» decía «País: United States».

- **Arreglo en origen:**
  - `backend/config/names.toml` tiene la tabla `[countries]` (unos 90 nombres de Yahoo: «Taiwan» → «Taiwán»,
    «Netherlands» → «Países Bajos»…), con su entrada en `schema.toml`;
  - `names.country()` la aplica en `display.profile.country`;
  - la web lo lee de ahí (`profileNames`);
  - la ficha de reserva del PDF también usa `display.profile`. El PDF de MC.PA salía en inglés: «Luxury Goods»,
    «Consumer Cyclical» y «France» pasan a «Bienes de lujo», «Consumo cíclico» y «Francia».
- **Tests:**
  - `test_names.py::test_every_country_is_translated`: ningún país de la región ni de las salidas guardadas queda sin
    traducir;
  - `test_panel_cases.py::test_display_profile_in_spanish`;
  - `names.test.ts`;
  - e2e «La empresa: el país en español» (AAPL, TSM y ASML).
- **Salidas guardadas:** regeneradas, con solo la línea del país en las 46 salidas y el PDF de MC.PA.
  `npm run check` en verde.
- **Backend:** 5.611 pasadas y 5 saltadas. El único fallo era el PDF de MC.PA antes de regenerarlo: era el cambio
  buscado.

![TSM: País Taiwán](capturas-v4-prepasada/1-pais-TSM.webp) ![ASML: País Países Bajos](capturas-v4-prepasada/1-pais-ASML.webp)

## 2. Resultados de la pre-pasada

| Prueba | Resultado |
|---|---|
| **V1** · panel sin red: 37 tickers × 10 páginas × 3 navegadores × 3 anchos × 2 temas, y la portada | Chromium y WebKit: **4.584 de 4.584 páginas correctas** tras los arreglos (matriz: `verificacion/V1_matriz_prepasada.md`). Firefox no arranca en este entorno (ver 2.1) |
| **V3** · fuentes caídas, contra el build: 9 fallos y sin fallo, en la portada, la historia y las 9 secciones de AAPL, en 4 proyectos | **440 de 440** |
| **V4** · pantalla de carga (`carga.spec.ts`, 4 proyectos, `--repeat-each=3`, contra el build) | **72 de 72**. La rotación de frases que falló una vez en tableta (bloque 4) no ha vuelto a fallar |
| **V5** · producción simulada | La portada de la web actual, idéntica a `main`. `/stock/AAPL` difiere en una línea: diferencia aceptada por el PM (V7, ver 2.2). `produccion.spec` 48/48 y CSP 20/20 |
| **Lighthouse** · `/v2/AAPL/valor` contra el build | Escritorio: rendimiento 99, accesibilidad 100, buenas prácticas 100, SEO 91. Móvil: rendimiento 90–96, el resto igual (antes, 89 en móvil). El SEO 91 era la falta de `robots.txt`; con él, SEO 100 (ver 4) |
| **e2e:v2** con `next dev` | 801 pasadas y 1 fallida. La fallida era una regresión de mi primer arreglo en tableta, corregida en `46c70fd8` |
| **e2e:v2** contra el build, con los arreglos | **853 pasadas, 0 fallidas** (ver 2.3) |
| **e2e:perf** contra el build | **3 de 3**, dos veces. INP p75: 24 ms (Chromium ×4), 55 ms (móvil ×4) y 30 ms (WebKit) |

### 2.1 V1, en detalle

La primera vuelta tardó 4,1 h con 4 workers, con la máquina cargada: carga media de unos 14, con las suites de
otras ramas en paralelo. En Chromium y WebKit dio 434 pasadas y 22 fallos.

- **6 desbordamientos reales a 375 px**, arreglados (sección 3):
  - HSBC, «Conclusión», en los dos motores y los dos temas;
  - MC.PA, en las 10 páginas, en WebKit y los dos temas.
- **16 tiempos agotados** (300 s por test) en BRK-B, BCS, CAT y CRWD.
  - El test se queda dentro de un `page.evaluate` síncrono de las comprobaciones. Después, la página responde
    (Playwright saca su instantánea), así que el renderizador estuvo parado un rato.
  - Repetidos aparte con 2 workers: los 84 tests de esos tickers y de HSBC y MC.PA dan 82 pasadas. Las 2 que fallan
    son BCS claro a 375, otra vez por tiempo, y repetidas 4 de 4 en verde.
  - Medido en la página quieta (CDP, 5 s): de 0 a 14 ms de trabajo, sin bucles de maquetación ni de animación.
  - **Conclusión:** son del entorno de prueba bajo carga, no de la web. Para la pasada oficial conviene una máquina
    sin otras suites o 2 workers.
- **Firefox:** `browserType.launch` falla con «Could not find profile folder». Pasa también con `TMPDIR` en el
  scratchpad: el sandbox de esta sesión no deja arrancar Firefox. Es la misma limitación de V1 del 18-oct. Habrá que
  correrlo desde una terminal normal:

  ```bash
  REPLAY_PORT=8768 V1_OUT=v1-ff npx playwright test -c playwright.v1.config.ts --project=firefox-1440 --project=firefox-768 --project=firefox-375
  ```

### 2.2 V5: la cabecera de la web actual en español (diferencia aceptada)

`npm run legado:comparar` (el `out` de `main` como base, frente al build de la rama) da la portada idéntica píxel a
píxel en los 4 tamaños. `/stock/AAPL` difiere en una sola línea en los 4 tamaños, la de debajo del nombre:

- en `main`: «Technology · Consumer Electronics · Nasdaq»;
- en v4: «Tecnología · Electrónica de consumo · Nasdaq».

No lo ha cambiado esta pre-pasada. Viene de `b3171746` (V7 · N), que lo hizo a propósito: su mensaje dice que «la
cabecera … de las dos webs» usa el español, y `StockHeader.tsx` usa `profileNames`. Choca con la regla «la web
actual intacta».

**Decisión del PM (2026-10-27): se acepta.** Los nombres en español en `StockHeader` de la web actual son una
excepción aprobada en V7: es la única diferencia aceptada respecto a `main`. En la pasada oficial, `legado:comparar`
dará esta diferencia en `/stock/AAPL` (solo la línea de sector e industria). Cualquier otra diferencia es un fallo.

El país nuevo no afecta a la web actual: `StockHeader` no lo muestra.

### 2.3 e2e:v2 contra el build

**853 pasadas, 0 fallidas** y 571 saltadas, en 11,5 min, con los 4 proyectos: escritorio, tableta, móvil y móvil
WebKit. Entran las de producción simulada, que solo corren contra el build, y las 10 nuevas de `v1-regresiones`. Las
saltadas son las de un solo proyecto («no depende del tamaño») y las de `next dev`.

## 3. Arreglos de presentación

**a) Anexo de HSBC a 375 px (`44bf9374`).** La etiqueta XBRL `ifrs-full:CashFlowsFromUsedInOperatingActivities` no
tiene dónde partirse. Ensanchaba el anexo a 464 px dentro de una caja de 341, y en WebKit desbordaba la página.

- **Arreglo:** `overflow-wrap: anywhere` en los `dd` del anexo y de la metodología.

![Anexo de HSBC a 375 px](capturas-v4-prepasada/2-anexo-HSBC-375.webp)

**b) Cabecera de MC.PA (`44bf9374` y `46c70fd8`).** Con la cotización en euros, «EUR 397.00 −EUR 1.30 (−0.33%)» va
en una pieza sin partir.

- **En el móvil**, a 375 px en WebKit, desbordaba la página en las 10 páginas.
- **En el iPad** medía 361 px dentro de una columna de 268, y se metía bajo la conclusión. Esto no lo detectaba
  ninguna comprobación.

El primer arreglo dejaba partirse la pieza en cualquier ancho, y en el iPad bajaba de línea la variación de AAPL: lo
pilló `news.spec` en tableta. El arreglo final:

- **A dos columnas** (tableta y escritorio): la columna de la identidad mide al menos lo que la cotización
  (`minmax(auto, 1fr)`). Si no caben las dos, cede la conclusión, que se parte en dos líneas.
- **En el móvil** (una columna): la variación pasa debajo del precio solo si la pieza no cabe en el ancho.
- **En la cabecera fija:** siempre una línea; cede el nombre, con puntos suspensivos.

![MC.PA a 375 px en WebKit](capturas-v4-prepasada/3-cabecera-MCPA-375-webkit.webp)
![MC.PA en el iPad](capturas-v4-prepasada/4-cabecera-MCPA-ipad.webp)

**Tests (`e2e/v2/v1-regresiones.spec.ts`):**

- a 375 px, sin desbordamiento en HSBC «Conclusión» y MC.PA «La empresa» y «Conclusión»;
- a dos columnas, MC.PA y AAPL: el precio y la variación en la misma línea, sin pisar la conclusión.

Las dos tandas dan rojo en el build anterior y verde con el arreglo.

Capturas: `node frontend/scripts/capturas-prepasada.mjs http://localhost:8768`, con el build servido por el replay.

## 4. Para el PM: lo que es del motor, o lo que decide el PM

1. **La cabecera de la web actual en español:** aceptada por el PM (ver 2.2).
2. **El anexo repite la etiqueta «Clasificación»** en cada línea del detalle de clasificación
   (`backend/lib/display.py:2665`). La segunda empieza en minúscula: «su historia (11 ejercicios en EDGAR) muestra
   ciclo…», en HSBC. Es redacción del motor: una etiqueta por línea («Clasificación», «Ciclo»…) o una sola lista.
   Además, «Arquetipo FINANCIAL (regla industria_banco)» mezcla identificadores internos con el texto. Es aceptable
   en un anexo de auditoría, pero conviene decidirlo.
   **PM:** ya está corregido en `fiabilidad/f8-p3` (`55ee3909`); entra con la fusión.
3. **`robots.txt`:** ni `main` ni v4 lo tenían. El backend respondía 200 con la página de la SPA, por eso
   Lighthouse marcaba SEO 91. **Hecho, a petición del PM:** `frontend/public/robots.txt` permite todo; no lleva
   sitemap porque no hay. El backend lo sirve tal cual desde `out`, y lo comprueba `produccion.spec`: texto plano,
   `User-agent: *` y `Allow: /`, sin sitemap.
4. **Rivales en el replay:** el replay calcula en segundo plano el análisis de cada rival la primera vez que se pide.
   Bajo carga, eso alarga la página «Rivales» («calculando»), pero no es un fallo. BBUC y CNNE (rivales de BRK-B)
   salen «fallo» porque no tienen fixtures: es la clase (c) ya conocida de E4.

## 5. Para la pasada oficial (tras fusionar F8)

- Repetir lo de la sección 2 sobre la v4 con F8, en una máquina sin otras suites en paralelo (o V1 con
  `V1_WORKERS=2`).
- Firefox: lo corre el PM desde fuera del sandbox, con el comando de 2.1.
- `legado:comparar`: la única diferencia aceptada es la de 2.2.
- Marcas de las escalas en tableta: en `verificacion/V4_marcas_escalas.md`. Al fusionar F8, hay que quitar la
  regla de tableta de `f8-auditoria` (`.fz2 .ticks > span:last-child { justify-self: end; }`).

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
