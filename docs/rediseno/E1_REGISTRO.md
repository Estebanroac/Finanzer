# Registro de la etapa E1 — sistema visual y página-historia (`/v2`)

*Operador E1 · 2026-10-17 · rama `rediseno/e1-sistema-historia` (worktree `../finanzer_next-e1`, desde `main` c1538a1) ·
sin push, sin merge, sin deploy.*

**Estado:** Tasks 0–8 hechas y verificadas. **E1 APROBADA por el usuario el 2026-10-17. Literal: «aprobado».**
Después de la aprobación, dos rondas de pulido pedidas por el PM (sesión planificadora) sobre dd98288 (desviaciones
22–28). **E1 cerrada.** Rama sin push ni merge; E2 empieza con su propio plan y prompt. Parada intermedia (Task 4): el usuario respondió *«si muy bien. pero esto es ensayo, no? recuerda lo que
te dije de los espacios muertos»* → se confirmó que es ensayo (solo local) y se eliminaron los espacios muertos de la
cabecera (commit 675dc01); a partir de ahí, «sin huecos muertos» se convirtió en un test automático (Task 7).

## Commits de la rama (`git log c1538a1..HEAD`)

| Task | Commit | Mensaje |
|---|---|---|
| 0 | e92d3b9 | herramientas de test de /v2 (Vitest, Playwright, axe) y Lightweight Charts |
| 1 | 68768ed | bandas de calidad y precio en la configuración generada (SCORE_BANDS) |
| 2 | 97ded2f | ruta /v2 con layout propio, tokens claro/oscuro y barra general |
| 3 | 89b7014 | fixtures de 8 tickers y modelo de escala de las puntuaciones |
| 4 | 4975a8c | cabecera con precio, puntuaciones con escala y desglose, y confianza |
| — | fb02336 | registro de la etapa (borrador) y capturas de la parada intermedia |
| 4 | 675dc01 | cabecera sin espacios muertos (conclusión visible y tarjetas alineadas por filas) |
| 5 | b906d0d | historia de 9 capítulos con barra fija, capítulos a lo ancho y cifras clave |
| 6 | 4b885dc | endpoint aditivo de serie de precios y gráfica de precio con rangos y S&P 500 |
| 7 | cb432ef | tests de simetría, capturas de 8 tickers (claro/oscuro, escritorio/móvil) y accesibilidad |
| spec | b717f0b | escala tipográfica revisada de la spec (mín. 12 px, lectura 16/17, rem) y zoom permitido |
| 7–8 | cd11897 | cabeceras de fila en las tablas, cifras de Rivales sin repetir la tabla y Lighthouse |
| 8 | f1f8829 | registro de la etapa y verificación de la web actual intacta |
| usuario | b8a63bf | retoques del usuario a la cabecera, huecos internos de tarjetas y zoom de texto |
| 8 | dd98288 | registro actualizado tras los retoques |
| 8 | 33512a7 | aprobación literal del usuario |
| PM | 9dffcc1 | pulido del PM (desgloses visibles, cifras en filas, gráfica en español, lectura a 15 px) |
| 8 | e4d0e6d | registro de la ronda de pulido |
| PM | bfc05e3 | últimos detalles (tabla del capítulo 1, márgenes y ejes de la gráfica, chips de móvil) |
| 8 | (este commit) | cierre de E1 |

## Versiones instaladas (exactas, sin `^`)

- `lightweight-charts` **5.2.1** (API v5: `chart.addSeries(LineSeries, …)`; licencia Apache-2.0, se conserva el logo de
  atribución de TradingView en la gráfica).
- `vitest` 4.1.12 · `@vitejs/plugin-react` 6.1.2 · `jsdom` 29.1.1 · `@testing-library/react` 16.3.3 ·
  `@testing-library/jest-dom` 7.0.1 · `@playwright/test` 1.64.1 (Chromium 1248) · `@axe-core/playwright` 4.14.0.
- Lighthouse 12.8.2 (vía `npx`, no queda en `package.json`).

## Verificación (salida literal)

**Web actual intacta** — el `git diff` de Task 8 contra el punto de partida de la rama (`main...HEAD`; `main` avanzó
durante la etapa con F6/F7 y la spec, así que `git diff main` a secas mezcla esos commits):

```
$ git diff main...HEAD --stat -- frontend/src/components frontend/src/app/stock frontend/src/app/page.tsx \
    frontend/src/app/layout.tsx frontend/src/app/globals.css frontend/src/lib/api.ts frontend/out \
    backend/lib/display.py backend/lib/pdf_report.py backend/tests/golden
(vacío)
```

Archivos compartidos tocados (todos los permitidos por el plan, aditivos): `backend/tools/gen_frontend_config.py` y
`frontend/src/lib/generated/backendConfig.ts` (+`SCORE_BANDS`), `backend/main.py` (+1 endpoint `/api/v2/prices`),
`frontend/scripts/check-analysis-literals.mjs` (+3 rutas al ámbito), `frontend/package.json`/`package-lock.json`
(dependencias de test, `lightweight-charts` y scripts `test:v2`/`e2e:v2`). Nuevos: `backend/lib/prices_v2.py`,
`backend/tests/test_prices_v2.py`, `frontend/{vitest,playwright}.config.ts`, `frontend/scripts/export-v2-fixtures.mjs`,
`frontend/src/{app/v2,v2}`, `frontend/e2e/v2`. `frontend/out` no se tocó. Ningún golden cambió
(`git status --short backend/tests/golden` vacío tras la suite).

```
$ npm run test:v2            → Test Files 10 passed (10) · Tests 53 passed (53)
$ npm run e2e:v2             → 76 passed, 2 skipped (escritorio + móvil; los skip son las dos pruebas de zoom, solo en escritorio)
    · shell 2×2 · precio 1×2 · simetría 8×2 · accesibilidad 2×2 · capturas 16×2 · legibilidad 8×2
    · zoom de página 200 % (720 px) y texto grande · zoom de texto 200 % (Page.setFontSizes) + simetría completa
$ npm run check              → check-analysis-literals: sin umbrales literales en los componentes de análisis
                               check-contract: StockAnalysis encaja con 46 salidas del backend
$ npx tsc --noEmit           → sin errores
$ gen_frontend_config.py --check → sincronizado
$ pytest tests -q (backend)  → 4161 passed, 1 skipped in 83.65s
```

**Lighthouse** (escritorio, `/v2/AAPL` en `next dev` con el replay: orientativo; la medida definitiva es sobre el build en
E6) — `docs/rediseno/capturas-e1/lighthouse-AAPL.json`: **rendimiento 94 · accesibilidad 100**; FCP 0.3 s, LCP 1.6 s,
TBT 40 ms, **CLS 0.002** (la carga no salta), Speed Index 0.7 s.

**Accesibilidad (axe, WCAG 2 A/AA):** sin infracciones graves ni críticas en claro y oscuro (AAPL, test del plan) y,
además, en los 8 tickers en ambos temas (comprobación con axe tras los últimos cambios).

**Simetría:** 16/16 (8 tickers × escritorio/móvil) y también con el texto al 200 %: filas de igual alto, gaps en la
escala (en rem), sin desbordamiento horizontal, **ningún hueco al pie de una tarjeta** (≤ 4 px), **ningún hueco entre
hijos consecutivos de una tarjeta** (≤ 24 px) y **hueco muerto acotado**
por capítulo (ver desviación 13). Medida final (alto natural texto − visual, px):

```
AAPL  empresa:21 negocio:69 accion:11 calidad:81 valor:4 rivales:26 riesgos:3 actualidad:-12 conclusion:21
JPM   empresa:20 negocio:50 accion:11 calidad:4 valor:22 rivales:67 riesgos:48 actualidad:33 conclusion:21
O     empresa:75 negocio:9 accion:11 calidad:30 valor:17 rivales:67 riesgos:42 actualidad:33 conclusion:21
NEE   empresa:-3 negocio:69 accion:11 calidad:55 valor:-9 rivales:26 riesgos:77 actualidad:33 conclusion:21
XOM   empresa:6 negocio:69 accion:11 calidad:30 valor:22 rivales:11 riesgos:29 actualidad:-12 conclusion:21
PLTR  empresa:6 negocio:43 accion:11 calidad:55 valor:9 rivales:11 riesgos:32 actualidad:33 conclusion:21
RIVN  empresa:23 negocio:84 accion:11 calidad:4 valor:25 rivales:8 riesgos:-9 actualidad:33 conclusion:21
BCS   empresa:20 negocio:50 accion:11 calidad:4 valor:38 rivales:93 riesgos:48 actualidad:33 conclusion:-1
```
(negativo = el texto queda por debajo del visual, máx. 48; positivo = el visual se estira para igualarlo, máx. 96)

## Capturas

`docs/rediseno/capturas-e1/`: 32 capturas de página completa `{TICKER}-{light|dark}-{desktop|mobile}.png` (AAPL, JPM, O,
NEE, XOM, PLTR, RIVN, BCS; escritorio 1440 px, móvil 375 px) y `parada-task4/` (cabecera de la parada intermedia, con la
escala tipográfica anterior).

## Desviaciones respecto al plan (y motivo)

1. **Vitest 4.1.12**, no la última (5.0.5): la 5 exige `@types/node` ≥ 22 y el proyecto tiene `^20` (compartido).
2. **Python del checkout principal** (`/Users/joseestebanroa/Downloads/finanzer_next/.venv313`): el worktree no lo trae.
3. **`symbolFromPath` sin `parts.length > 1`** (el guardián lo marcó): desestructuración, mismo comportamiento.
4. **Aserciones con arrays de números escritas como cadena** (`"45 20 15 20"`, `"100 150"`): el guardián también recorre
   los tests de `/v2`. El guardián no se tocó.
5. **`src/v2/test-setup.ts` con `cleanup()`**: sin `globals` de Vitest, Testing Library no desmonta entre tests.
6. **Cabecera más cerca de la maqueta 2c** (todo del motor): tono del motor en la cifra y el tramo; cortes en las marcas
   («débil <45», «excelente 80+»); **escala de confianza** con los niveles de `[score.price] confidence_factor`
   (`SCORE_BANDS.confidence`, dentro de la misma exportación nueva); desgloses de calidad, precio y confianza con filas y
   frases del `display` (no se recalcula nada: PLTR suma 79/80 y el motor da 95); conclusión siempre visible en la
   cabecera (spec §3.1); tarjetas alineadas por filas (subgrid).
7. **`Range52.pos` viene en 0–100, no 0–1** (el plan lo multiplicaba por 100: el marcador quedaba a 54 000 px). Al final
   el rango de 52 semanas va como cifra clave con la lectura del motor (la maqueta 1 pone solo la gráfica en el capítulo 3).
8. **`profitability.figures` trae dos parejas por fila**: el plan tomaba solo la primera.
9. **Contenido de los capítulos**: el plan repetía textos (Negocio y Calidad con la misma lectura), ponía fortalezas en
   Riesgos y llenaba visuales con notas de metodología. Se usan otros campos del `display` (nunca texto propio):
   `summary.exec_items`, `cover.highlights`, pre-mortem, escalera de márgenes (`charts.profitability.margin_ladder`;
   en bancos y REIT, sin escalera, su rentabilidad frente a la referencia), múltiplos frente a la referencia
   (`charts.valuation.multiples` + `scored`), alertas sin el grupo de fortalezas. Tests nuevos: lecturas distintas, sin
   fortalezas en Riesgos, ningún «Sin dato» en los 8 tickers.
10. **Endpoint `GET /api/v2/prices/{symbol}?sector=…`**: `_compute_analysis` no tiene caché, así que no se llama desde el
    endpoint (repetiría el análisis). El ETF sale del registro `sector_profiles` a partir de `profile.sector` (que sí está
    en el contrato; `sector_info` no): nunca descarga símbolos arbitrarios. Verificado: mismo ETF que el motor en los 8.
11. **La serie del motor cubre 2 años** (`period=2y`): 3A y 5A se muestran con lo que hay y la leyenda lo dice
    («serie desde dd/mm/aaaa»). La serie larga es el dato 1 de E2.
12. **Gráfica**: ocupa el alto del capítulo (crece; mínimo 9.375rem); leyenda en las celdas de rentabilidad; esqueleto de
    carga con la misma estructura y alto (sin saltos: CLS 0.002); sin arrastre ni pellizco propios (zoom de la página,
    spec §5); `role="group"` (lleva el enlace de atribución de TradingView); se repinta al cambiar de tema.
13. **Sin huecos muertos (preferencia firme del usuario)**: cada capítulo mide, antes de pintar y con los estirados
    desactivados (`data-measure`), el alto natural de sus dos columnas; coloca las cifras clave en el lado que las iguala
    (texto o dentro de la tarjeta del visual, como en la maqueta 1); recorta filas de listas y tablas hasta que el visual
    no sobrepase al texto (el resto vive en la página de profundidad, E3); y devuelve las cifras al texto si con ellas en
    el visual no cabe y volver mejora (funciones puras `src/v2/lib/fit.ts`, con tests). El test de simetría se **amplió**
    con el hueco por capítulo (≤ 48 px en el texto, ≤ 96 px de estirado del visual); no se relajó nada del plan.
14. **Contraste AA**: los colores de la spec en texto pequeño no llegan a 4.5:1 (ámbar `#B07D1A` sobre blanco 3.6:1;
    píldoras 4.1:1). Siguen en los rellenos (barras, escalas, puntos, líneas) y el texto usa variantes de la misma
    familia: claro `--good-ink #157346`, `--warn-ink #845E13`, `--bad-ink #A24B26`; oscuro `#59AC80`, `#C49A45` (igual),
    `#CF8970` (≥ 4.6:1 sobre superficie, papel, neutro y su fondo).
15. **Escala tipográfica revisada** (commit `e6cac38` en `main`, durante la etapa, a petición del usuario): lectura 16
    (móvil 17), tablas 15, subtítulo 19, título de capítulo 28 (móvil 24), cifras de puntuación y precio 32, etiquetas 12
    con `.08em`; todo en `rem`, cortes en `em`. Test nuevo de legibilidad: ningún texto < 12 px, zoom sin bloquear y sin
    desbordamiento a 200 % ni con texto grande del sistema. El plan (14/10 px) quedó superado por la spec.
16. **Móvil**: cifras clave en filas (etiqueta | valor), barra de capítulos deslizable, barra general en dos columnas;
    las tres puntuaciones van apiladas (la cabecera móvil «en una fila» es de E4).
17. **Tablas**: la primera celda de cada fila es `<th scope="row">` (Lighthouse `td-has-header`).

18. **Retoques del usuario a la cabecera** (mensaje del planificador con el literal de la parada intermedia):
    tramos neutros («media», «razonable») en gris visible con token nuevo `--scale-neutral` (claro `#A3A09A`, oscuro
    `#6B7077`); rango del motor también en los tramos intermedios («media 45–65», «exigente 30–45»…), con las marcas en
    dos líneas (nombre / rango) para que los tramos estrechos quepan en móvil; base de cada puntuación al pie de su fila
    compartida (en escritorio). La fila del nombre se ocupa con la **conclusión** (spec §3.1: siempre visible en la
    cabecera) en lugar de KPIs, que ya están en el capítulo 1.
19. **Huecos internos de las tarjetas** (petición del planificador): las cifras clave llevan el valor al pie (los valores
    de una fila quedan alineados) y el test de simetría comprueba el hueco al pie de cada tarjeta de cada fila (≤ 4 px),
    cabecera incluida.
20. **Legibilidad y zoom** (mensaje del planificador; literal del usuario: *«en el teléfono, finanzer no se le puede
    hacer zoom en la versión de app del iphone. es fijo. otra cosa, actualmente se me hace difícil leer en los análisis
    de la app tanto en el teléfono como en la laptop. por lo que el tamaño de la letra es algo a lo que hay que prestarle
    atención»*): ver desviación 15; además `viewport` explícito en `src/app/v2/layout.tsx` (`width: device-width,
    initialScale: 1`, sin `maximumScale` ni `userScalable`), ningún `touch-action` en `/v2`, ancho máximo 74rem (columna
    de lectura ≈ 75 caracteres a 16 px; en móvil, ~44 por el ancho del teléfono) y test de zoom de texto al 200 %
    emulando el tamaño de letra del navegador (CDP `Page.setFontSizes`: así los cortes en `em` reaccionan como en un
    navegador real; con el 200 % la página pasa a una columna) con la simetría completa en verde.
21. **Riesgos y Actualidad**: con la columna más estrecha, Riesgos de los bancos sin alertas quedaba corto; se añaden al
    final de su lista las filas de solidez con dato del motor (p. ej. payout) y la nota del pre-mortem; la lectura
    conductual de mercado pasa de la lectura de Actualidad a su visual.

22. **Cabecera, pulido del PM (A)**: el desglose compacto va siempre visible en las tres tarjetas (calidad: las 4
    categorías x/20; precio: los ajustes con signo de `summary.composition.price`, la Valoración x/20 y, si hubo, el
    ajuste por confianza raw → score; confianza: sus 4 dimensiones). Base y lista comparten la última fila del subgrid y
    la lista reparte el alto sobrante entre sus filas: con una nota de 3 líneas en Precio (JPM), Calidad ya no deja un
    bloque de ~60 px vacío. El detalle largo sigue al pasar el ratón. Fila de identidad en dos columnas (identidad |
    conclusión) para que un nombre largo no deje vacía la derecha. Test: hueco entre hijos consecutivos de una tarjeta
    ≤ 24 px (además del hueco al pie ≤ 4 px).
23. **Cifras clave como filas (etiqueta | valor)** en vez de tres tarjetas en fila (maqueta 1): con etiquetas y valores del
    motor de 1 a 3 líneas, tres tarjetas de igual alto dejaban 19–45 px vacíos dentro de las más cortas, y alinear los
    valores solo movía el hueco. En filas, cada una mide lo que su contenido. Reequilibrio: Calidad usa la primera frase
    de «Creación de valor» (el ROCE ya va en las cifras); en bancos y REIT, «Cómo gana dinero» suma a su tabla las cifras
    financieras que no están en las cifras clave.
24. **Gráfica (B)**: eje en español (`localization.locale = "es-ES"`, `tickMarkFormatter` y `timeFormatter` propios con
    meses en español: «Ene», «Abr», «13 Oct»; `src/v2/lib/chartTime.ts`, con tests); texto del eje a 12 px; en móvil
    cada chip de rentabilidad en dos líneas (nombre / cifra). **Licencia**: el paquete npm no trae el NOTICE; el README de
    lightweight-charts 5.2.1 dice que la licencia «requires specifying TradingView as the product creator» y pide añadir
    el «attribution notice» del archivo NOTICE y un enlace a https://www.tradingview.com/ en la página (el
    `attributionLogo` cumple solo la parte del enlace). NOTICE oficial de v5.2.1 (repositorio de TradingView):
    «TradingView Lightweight Charts™ / Copyright (с) 2025 TradingView, Inc. https://www.tradingview.com/». Se desactiva
    `attributionLogo` (tapaba la línea de precio) y el pie de la tarjeta dice «Gráfica: TradingView Lightweight Charts™
    · Copyright (с) 2025 TradingView, Inc.» con enlace a tradingview.com: cumple aviso y enlace.
25. **Lectura a 15 px (C)**: el detalle de las listas (Riesgos, Actualidad, Conclusión), las notas bajo tablas y barras y
    el detalle al pasar el ratón pasan de 13 a 15 px (tamaño de tabla de la spec); 12–13 px queda solo para etiquetas.
26. **Capítulo 1 (D)**: la fila «En una frase» repetía la conclusión de la cabecera y del capítulo 9; ahora es «Por qué
    es «Madura»» (o el tipo que toque) con `cover.classification_notes[0]`, en fila apilada (rótulo encima, texto a todo
    el ancho).
27. Medidas tras el pulido: Lighthouse 94/100, CLS 0.002; axe sin infracciones graves en los 8 tickers (claro y oscuro).

28. **Últimos detalles del PM**: la fila «Por qué es «X»» ocupa todo el ancho de la tarjeta (la celda no puede ser
    flex o el colSpan deja de funcionar) y las etiquetas de las tablas etiqueta | valor van a su ancho natural (el valor no
    se parte mientras quepa); gráfica con márgenes de escala y `entireTextOnly` (ninguna etiqueta del eje de precios
    cortada; revisado en RIVN, PLTR, NEE y BCS en 1M, 1A y 5A, escritorio y móvil), ejes a 13 px en móvil, chips de
    rentabilidad solo con el nombre y el periodo en la cabecera («1A · base 100 · cierre ajustado»).

## Para el planificador

- **Conflicto trivial al fusionar con `main` actual** (`git merge-tree`): `backend/main.py`, porque `main` añadió el
  arranque de `keepalive` justo antes de `@app.get("/api/health")`, el mismo sitio del endpoint `/api/v2/prices`. Se
  resuelve conservando los dos bloques. No se ha fusionado nada (regla de la etapa).
- La spec revisada (`e6cac38`) ya está aplicada en `/v2`; el plan de E1 sigue con la escala antigua.
- En el replay no hay noticias (Finnhub sin titulares): el capítulo 8 lo dice y muestra las lecturas de mercado; en
  producción aparecerán las tarjetas de noticias.
- Pendiente de datos de E2: variación del día en la cabecera, serie de 5 años, segmentos, rivales SIC, Piotroski con
  valores, noticias enriquecidas.
- **Pendientes para E2, a corregir en origen (en el motor, con su diff de golden; no se parchean en /v2):**
  - el código de bolsa «NMS» debe mostrarse como «Nasdaq» (y, en general, los códigos de Yahoo —NYQ, NMS…— con su
    nombre); hoy `/v2` muestra `profile.exchange` tal cual llega del motor;
  - textos del motor que empiezan en minúscula (p. ej. la nota de Precio de JPM: «en la frontera con «exigente»…»);
  - «spread de +88.4%» en Calidad y Conclusión (ROIC − WACC): es una diferencia de porcentajes y debe decir «pp».

## Qué se ve en cada capítulo (8 tickers)

### AAPL — Apple Inc.

| Capítulo | Lectura (inicio) | Cifras clave | Visual (filas del modelo; el capítulo enseña las que caben) |
|---|---|---|---|
| 1. La empresa | Apple Inc. opera en Consumer Electronics (Technology). Los ingresos están prácticamente pl… | Market cap: $5.01T · Tipo de negocio: Madura · Bolsa: NMS | facts: 5 |
| 2. Cómo gana dinero | ROE 151.9% = margen neto 26.9% × rotación de activos 1.16 × apalancamiento 4.87; frente a … | Flujo de caja operativo: $146.72B · Flujo de caja libre: $136.68B · EPS: $8.72 | ladder: 5 |
| 3. La acción | Cotiza en el 95% del rango de 52 semanas, en la zona de máximos. Con beta 1.05, la acción … | Momentum 12-1: +34.3% · Tendencia (200 sesiones): Alcista · Rango de 52 semanas: En máximos de 52 semanas | price: serie |
| 4. Calidad | Destaca en Rentabilidad (20/20) y Calidad de Ganancias (20/20). Con un ROIC de 98.0% frent… | ROIC: 97.99% · ROCE (EBIT / capital empleado): 68.72% · Piotroski F-Score: 8/9 | bars: 4 |
| 5. Cuánto vale | El precio actual exige que el FCF − SBC por acción crezca un 15.6% anual durante 10 años (… | ATRACTIVO DEL PRECIO: 15 / 100 · muy exigente · Crecimiento que exige el precio (DCF inverso): Muy exigente · Fiabilidad del DCF: baja | compare: 7 |
| 6. Rivales | Comparada con la mediana de su industria, es mejor en 5 de 8 métricas. Referencia: industr… | Mejor que la referencia: 5 de 8 · EV/EBITDA: 29.94x · Prima elevada · P/B: 46.55x · Prima elevada | compare: 8 |
| 7. Riesgos | Altman Z de 2.32 (zona gris). A vigilar: EV/EBITDA alto — 29.9x. | Riesgos: 0 · Advertencias: 4 · Altman Z-Score: 2.32 | list: 8 |
| 8. Actualidad | Contexto de mercado: no puntúa en la calidad ni en el precio. Describe cómo se ha movido l… | Caída máxima: −13.8% · Fuerza relativa frente a XLK (12 meses): +4.8 pp · Volumen (últimas 5 sesiones): z = −0.5 | news: sin titulares → 7 lecturas de mercado |
| 9. Conclusión | Calidad sólida · precio muy exigente (confianza alta: DCF inverso y los múltiplos coincide… | Calidad: 75 / 100 · sólida · Precio: 15 / 100 · muy exigente · Confianza: Alta | list: 4 |

### JPM — JPMorgan Chase & Co.

| Capítulo | Lectura (inicio) | Cifras clave | Visual (filas del modelo; el capítulo enseña las que caben) |
|---|---|---|---|
| 1. La empresa | JPMorgan Chase & Co. opera en Banks—Diversified (Financial Services). Los ingresos crecen … | Market cap: $890.37B · Tipo de negocio: Banco · Bolsa: NYQ | facts: 5 |
| 2. Cómo gana dinero | El ROE de 18.0% es excepcional para su sector (sector: 6.0% competitivo, 12.0% rango alto)… | Ingresos: $194.91B · Beneficio neto: $63.63B · EPS: $23.34 | compare: 4 |
| 3. La acción | Cotiza en el 64% del rango de 52 semanas, en la zona media. Con beta 1.09, la acción se mu… | Momentum 12-1: +16.1% · Tendencia (200 sesiones): Alcista · Rango de 52 semanas: Zona media del rango | price: serie |
| 4. Calidad | Destaca en Rentabilidad (20/20) y Calidad de Ganancias (19/20). | ROE: 18.00% · ROA: 1.27% · Salud financiera (sector financiero): 10/10 | bars: 4 |
| 5. Cuánto vale | El precio descuenta un ROTE sostenido del 25.7%; el banco obtiene un 20.0% en el último ej… | ATRACTIVO DEL PRECIO: 45 / 100 · razonable · ROTE que descuenta el precio: Muy exigente · P/E (TTM): 14.37x | compare: 5 |
| 6. Rivales | Comparada con la mediana de su industria, es mejor en 2 de 4 métricas. Referencia: industr… | Mejor que la referencia: 2 de 4 · P/B: 2.52x · Prima elevada · P/E (TTM): 14.37x · En línea | compare: 4 |
| 7. Riesgos | Salud financiera bancaria de 10/10 (sólida). A vigilar: Sin alertas relevantes. | Riesgos: 0 · Advertencias: 0 · Salud financiera (sector financiero): 10/10 | list: 2 |
| 8. Actualidad | Contexto de mercado: no puntúa en la calidad ni en el precio. Describe cómo se ha movido l… | Caída máxima: −15.5% · Fuerza relativa frente a XLF (12 meses): +5.8 pp · Volumen (últimas 5 sesiones): z = 0.1 | news: sin titulares → 6 lecturas de mercado |
| 9. Conclusión | Calidad excelente · precio razonable (confianza alta: el P/B justificado y el P/B del sect… | Calidad: 91 / 100 · excelente · Precio: 45 / 100 · razonable · Confianza: Alta | list: 4 |

### O — Realty Income Corporation

| Capítulo | Lectura (inicio) | Cifras clave | Visual (filas del modelo; el capítulo enseña las que caben) |
|---|---|---|---|
| 1. La empresa | Realty Income Corporation opera en REIT—Retail (Real Estate). El retorno total por acción … | Market cap: $52.20B · Tipo de negocio: REIT · Bolsa: NYQ | facts: 5 |
| 2. Cómo gana dinero | FFO / activos 4.98%: muy bajo (4.98%); Margen FFO 63.8%: excelente (63.8%). | Ingresos: $5.97B · EBITDA: $5.10B · Beneficio operativo: $2.73B | compare: 8 |
| 3. La acción | Cotiza en el 14% del rango de 52 semanas, en la parte baja. Con beta 0.62, la acción amort… | Momentum 12-1: +5.0% · Tendencia (200 sesiones): Lateral · Rango de 52 semanas: Parte baja del rango | price: serie |
| 4. Calidad | Destaca en Calidad de Ganancias (17/20); el punto débil es Rentabilidad (9/20). | FFO / activos: 4.98% · FFO / patrimonio contable (informativo): 9.63% · Margen FFO: 63.8% | bars: 4 |
| 5. Cuánto vale | El precio actual se justifica aunque el FFO por acción caiga un 1.4% anual durante 10 años… | ATRACTIVO DEL PRECIO: 61 / 100 · razonable · Crecimiento que exige el precio (DCF inverso): En precio · P/B: 1.32x | compare: 3 |
| 6. Rivales | Comparada con la mediana de su industria, es mejor en 2 de 4 métricas. Referencia: industr… | Mejor que la referencia: 2 de 4 · EV/EBITDA: 15.63x · En línea · P/B: 1.32x · Descuento profundo | compare: 4 |
| 7. Riesgos | La deuda neta (5.7x EBITDA) está en el rango habitual de un REIT con grado de inversión (h… | Riesgos: 0 · Advertencias: 1 · —: Sin dato | list: 8 |
| 8. Actualidad | Contexto de mercado: no puntúa en la calidad ni en el precio. Describe cómo se ha movido l… | Caída máxima: −18.5% · Fuerza relativa frente a VNQ (12 meses): −6.6 pp · Volumen (últimas 5 sesiones): z = 1.4 | news: sin titulares → 6 lecturas de mercado |
| 9. Conclusión | Calidad media · precio razonable (confianza media: DCF inverso la ve en precio y los múlti… | Calidad: 59 / 100 · media · Precio: 61 / 100 · razonable · Confianza: Media | list: 4 |

### NEE — NextEra Energy Inc.

| Capítulo | Lectura (inicio) | Cifras clave | Visual (filas del modelo; el capítulo enseña las que caben) |
|---|---|---|---|
| 1. La empresa | NextEra Energy Inc. opera en Utilities—Regulated Electric (Utilities). Los ingresos crecen… | Market cap: $163.48B · Tipo de negocio: Utility regulada · Bolsa: NYQ | facts: 5 |
| 2. Cómo gana dinero | ROE 12.5% = margen neto 24.9% × rotación de activos 0.13 × apalancamiento 3.90; frente a F… | Flujo de caja operativo: $13.80B · EPS: $4.45 · Valor en libros / acción: $27.39 | ladder: 5 |
| 3. La acción | Cotiza en el 16% del rango de 52 semanas, en la parte baja. Con beta 0.48, la acción amort… | Momentum 12-1: −1.1% · Tendencia (200 sesiones): Bajista · Rango de 52 semanas: Parte baja del rango | price: serie |
| 4. Calidad | Destaca en Rentabilidad (20/20) y Crecimiento (14/20); el punto débil es Solidez Financier… | ROIC: 4.65% · ROCE (EBIT / capital empleado): 4.79% · Piotroski F-Score: 5/9 | bars: 4 |
| 5. Cuánto vale | El precio descuenta un ROE sostenido del 16.9%; la utility obtuvo un 13.1% de media en 4 e… | ATRACTIVO DEL PRECIO: 46 / 100 · razonable · ROE que descuenta el precio: Exigente · P/E (TTM): 17.61x | compare: 3 |
| 6. Rivales | Comparada con la mediana de su industria, es mejor en 5 de 8 métricas. Referencia: industr… | Mejor que la referencia: 5 de 8 · P/B: 2.86x · Prima moderada · P/E (TTM): 17.61x · Descuento | compare: 8 |
| 7. Riesgos | La deuda neta (6.9x EBITDA) es elevada para una utility; la cobertura de intereses (2.4x) … | Riesgos: 1 · Advertencias: 1 · —: Sin dato | list: 8 |
| 8. Actualidad | Contexto de mercado: no puntúa en la calidad ni en el precio. Describe cómo se ha movido l… | Caída máxima: −21.7% · Fuerza relativa frente a XLU (12 meses): +1.2 pp · Volumen (últimas 5 sesiones): z = −0.8 | news: sin titulares → 6 lecturas de mercado |
| 9. Conclusión | Calidad sólida · precio razonable (confianza media: P/B justificado (ROE regulado) la ve c… | Calidad: 69 / 100 · sólida · Precio: 46 / 100 · razonable · Confianza: Media | list: 4 |

### XOM — Exxon Mobil Corporation

| Capítulo | Lectura (inicio) | Cifras clave | Visual (filas del modelo; el capítulo enseña las que caben) |
|---|---|---|---|
| 1. La empresa | Exxon Mobil Corporation opera en Oil & Gas Integrated (Energy). Los ingresos están práctic… | Market cap: $728.06B · Tipo de negocio: Cíclica · Bolsa: NYQ | facts: 5 |
| 2. Cómo gana dinero | ROE 11.1% = margen neto 8.9% × rotación de activos 0.72 × apalancamiento 1.73; frente a FY… | Flujo de caja operativo: $59.73B · Flujo de caja libre: $30.55B · EPS: $7.77 | ladder: 5 |
| 3. La acción | Cotiza en el 99% del rango de 52 semanas, en la zona de máximos. Con beta 0.30, la acción … | Momentum 12-1: +55.2% · Tendencia (200 sesiones): Alcista · Rango de 52 semanas: En máximos de 52 semanas | price: serie |
| 4. Calidad | Destaca en Solidez Financiera (20/20) y Rentabilidad (19/20). El ROIC (9.9%) supera al WAC… | ROIC: 9.89% · ROCE (EBIT / capital empleado): 11.12% · Piotroski F-Score: 5/9 | bars: 4 |
| 5. Cuánto vale | El precio actual se justifica aunque el FCF de mantenimiento por acción caiga un 0.5% anua… | ATRACTIVO DEL PRECIO: 48 / 100 · razonable · Crecimiento que exige el precio (DCF inverso): En precio · Fiabilidad del DCF: media | compare: 6 |
| 6. Rivales | Comparada con la mediana de su industria, es mejor en 3 de 9 métricas. Referencia: industr… | Mejor que la referencia: 3 de 9 · EV/EBITDA: 11.11x · Prima elevada · P/B: 2.81x · Prima elevada | compare: 8 |
| 7. Riesgos | Altman Z de 4.99 (zona segura); la deuda es fácilmente servible: cobertura de intereses de… | Riesgos: 0 · Advertencias: 2 · Altman Z-Score: 4.99 | list: 8 |
| 8. Actualidad | Contexto de mercado: no puntúa en la calidad ni en el precio. Describe cómo se ha movido l… | Caída máxima: −20.1% · Fuerza relativa frente a XLE (12 meses): +1.2 pp · Volumen (últimas 5 sesiones): z = −0.7 | news: sin titulares → 7 lecturas de mercado |
| 9. Conclusión | Calidad excelente · precio razonable (confianza baja: el DCF y los múltiplos discrepan). | Calidad: 82 / 100 · excelente · Precio: 48 / 100 · razonable · Confianza: Baja | list: 4 |

### PLTR — Palantir Technologies Inc.

| Capítulo | Lectura (inicio) | Cifras clave | Visual (filas del modelo; el capítulo enseña las que caben) |
|---|---|---|---|
| 1. La empresa | Palantir Technologies Inc. opera en Software—Infrastructure (Technology). Los ingresos por… | Market cap: $482.94B · Tipo de negocio: Crecimiento rentable · Bolsa: NMS | facts: 5 |
| 2. Cómo gana dinero | ROE 22.0% = margen neto 36.3% × rotación de activos 0.50 × apalancamiento 1.20. El margen … | Flujo de caja operativo: $3.40B · Flujo de caja libre: $3.36B · EPS: $1.17 | ladder: 5 |
| 3. La acción | Cotiza en el 89% del rango de 52 semanas, en la zona de máximos. Con beta 2.46, la acción … | Momentum 12-1: −2.6% · Tendencia (200 sesiones): Alcista · Rango de 52 semanas: En máximos de 52 semanas | price: serie |
| 4. Calidad | Por encima de 80, la calidad exige persistencia: 99 → 95. Rentabilidad: margen operativo p… | ROCE (EBIT / capital empleado): 18.30% · ROE: 30.86% · Piotroski F-Score: 7/8 | bars: 4 |
| 5. Cuánto vale | El precio actual exige que el FCF − SBC por acción crezca más de un 60% anual: ningún crec… | ATRACTIVO DEL PRECIO: 10 / 100 · muy exigente · Crecimiento que exige el precio (DCF inverso): Muy exigente · Fiabilidad del DCF: baja | compare: 7 |
| 6. Rivales | Comparada con la mediana de su industria, es mejor en 3 de 7 métricas. Referencia: industr… | Mejor que la referencia: 3 de 7 · EV/EBITDA: 177.84x · Prima elevada · P/B: 49.41x · Prima elevada | compare: 7 |
| 7. Riesgos | Altman Z de 11.61 (zona segura); sin carga financiera neta: los ingresos financieros cubre… | Riesgos: 0 · Advertencias: 5 · Altman Z-Score: 11.61 | list: 8 |
| 8. Actualidad | Contexto de mercado: no puntúa en la calidad ni en el precio. Describe cómo se ha movido l… | Caída máxima: −48.2% · Fuerza relativa frente a XLK (12 meses): −20.8 pp · Volumen (últimas 5 sesiones): z = −0.4 | news: sin titulares → 6 lecturas de mercado |
| 9. Conclusión | Calidad excelente · precio muy exigente (confianza alta: DCF inverso y los múltiplos coinc… | Calidad: 95 / 100 · excelente · Precio: 10 / 100 · muy exigente · Confianza: Alta | list: 4 |

### RIVN — Rivian Automotive Inc.

| Capítulo | Lectura (inicio) | Cifras clave | Visual (filas del modelo; el capítulo enseña las que caben) |
|---|---|---|---|
| 1. La empresa | Rivian Automotive Inc. opera en Auto Manufacturers (Consumer Cyclical). Los ingresos por a… | Market cap: $18.75B · Tipo de negocio: Crecimiento sin beneficio · Bolsa: NMS | facts: 5 |
| 2. Cómo gana dinero | ROE −79.9% = margen neto −67.7% × rotación de activos 0.36 × apalancamiento 3.26. El marge… | Flujo de caja operativo: −$1.84B · Flujo de caja libre: −$3.49B · EPS: −$2.58 | ladder: 4 |
| 3. La acción | Cotiza en el 5% del rango de 52 semanas, en la zona de mínimos. Con beta 1.46, la acción a… | Momentum 12-1: +19.0% · Tendencia (200 sesiones): Bajista · Rango de 52 semanas: En mínimos de 52 semanas | price: serie |
| 4. Calidad | El punto débil es Rentabilidad (0/20). | ROCE (EBIT / capital empleado): -29.95% · Piotroski F-Score: 5/9 · Runway: 1.5 | bars: 4 |
| 5. Cuánto vale | EV/Ventas: Barato por ventas (3.1x). | ATRACTIVO DEL PRECIO: 50 / 100 · razonable · P/B: 3.67x · P/S: 3.19x | compare: 5 |
| 6. Rivales | Comparada con la mediana de su industria, es mejor en 0 de 3 métricas. Referencia: industr… | Mejor que la referencia: 0 de 3 · P/B: 3.67x · Prima elevada · Margen operativo: −60.05% · Muy inferior | compare: 3 |
| 7. Riesgos | Runway ajustado: la caja cubre 1.5 años de quema de FCF: tendrá que financiarse. A vigilar… | Riesgos: 0 · Advertencias: 2 · Runway: 1.5 | list: 7 |
| 8. Actualidad | Contexto de mercado: no puntúa en la calidad ni en el precio. Describe cómo se ha movido l… | Caída máxima: −42.5% · Fuerza relativa frente a XLY (12 meses): +3.0 pp · Volumen (últimas 5 sesiones): z = −0.4 | news: sin titulares → 6 lecturas de mercado |
| 9. Conclusión | Calidad débil · precio razonable (confianza media: un solo método de valoración evaluable,… | Calidad: 32 / 100 · débil · Precio: 50 / 100 · razonable · Confianza: Media | list: 4 |

### BCS — Barclays PLC

| Capítulo | Lectura (inicio) | Cifras clave | Visual (filas del modelo; el capítulo enseña las que caben) |
|---|---|---|---|
| 1. La empresa | Barclays PLC opera en Banks—Diversified (Financial Services). Los ingresos crecen 5.2% anu… | Market cap: $76.12B · Tipo de negocio: Banco · Bolsa: NYQ | facts: 5 |
| 2. Cómo gana dinero | El ROE de 10.5% es competitivo en su sector (sector: 6.0% competitivo, 12.0% rango alto). | Ingresos: $41.27B · Beneficio neto: $9.19B · EPS: $2.68 | compare: 4 |
| 3. La acción | Cotiza en el 38% del rango de 52 semanas, en la zona media. Con beta 1.25, la acción ampli… | Momentum 12-1: +26.9% · Tendencia (200 sesiones): Lateral · Rango de 52 semanas: Zona media del rango | price: serie |
| 4. Calidad | Destaca en Calidad de Ganancias (19/20) y Solidez Financiera (14/20). | ROE: 10.49% · ROA: 0.40% · Salud financiera (sector financiero): 7/10 | bars: 4 |
| 5. Cuánto vale | El precio descuenta un ROTE sostenido del 10.1%; el banco obtiene un 10.7% en el último ej… | ATRACTIVO DEL PRECIO: 61 / 100 · razonable · ROTE que descuenta el precio: En precio · P/E (TTM): 8.54x | compare: 5 |
| 6. Rivales | Comparada con la mediana de su industria, es mejor en 2 de 4 métricas. Referencia: industr… | Mejor que la referencia: 2 de 4 · P/B: 0.87x · Descuento · P/E (TTM): 8.54x · Descuento | compare: 4 |
| 7. Riesgos | Salud financiera bancaria de 7/10 (buena). A vigilar: Sin alertas relevantes. | Riesgos: 0 · Advertencias: 0 · Salud financiera (sector financiero): 7/10 | list: 2 |
| 8. Actualidad | Contexto de mercado: no puntúa en la calidad ni en el precio. Describe cómo se ha movido l… | Caída máxima: −26.2% · Fuerza relativa frente a XLF (12 meses): +8.8 pp · Volumen (últimas 5 sesiones): z = 0.6 | news: sin titulares → 6 lecturas de mercado |
| 9. Conclusión | Calidad sólida · precio razonable (confianza media: el P/B justificado y el P/B del sector… | Calidad: 75 / 100 · sólida · Precio: 61 / 100 · razonable · Confianza: Media | list: 4 |

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
