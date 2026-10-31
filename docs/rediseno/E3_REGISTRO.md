# Registro de la etapa E3 — páginas de profundidad e interacciones (`/v2/{T}/{capítulo}`)

*Operador E3 · 2026-10-17/18 · rama de integración `rediseno/v4` (worktree `../finanzer_next-v4`, desde
`rediseno/e2a-datos-motor` con E2b fusionada; E2a reintegrada al cerrar su registro) · plan
`docs/superpowers/plans/2026-10-18-rediseno-e3-profundidad-e-interaccion.md` (main 57263bd) · sin push, sin merge a
`main`, sin deploy. `rediseno/e5-pdf` no se fusionó (lo hará el PM).*

**Estado:** Tasks 0–13 hechas. Las nueve páginas de profundidad, el panel de escenarios calculado por el motor, el
comparador de rivales, «nada se pierde» automática y las pruebas de diseño de E1 sobre la profundidad, en verde.
El golden solo gana las claves aditivas del escenario (`docs/fiabilidad/GOLDEN_DIFF_E3.md`). Pendiente de la
aprobación del PM (delegada por el usuario).

## Commits (`git log --first-parent b41f50b~1..HEAD`)

| Task | Commit | Mensaje |
|---|---|---|
| 0 | b41f50b | fusión de E2b sobre E2a; puertos de Playwright por variable de entorno (`E2E_PORT`, `REPLAY_PORT`) |
| 0 | 5d4dc91 | CORS de desarrollo para localhost en cualquier puerto (`next dev` en 3001 junto a E2a) |
| 1 | 5ebb2a9 | rutas `/v2/{T}/{capítulo}` sin repetir el análisis al navegar (`pushState` + `sessionStorage` 5 min) |
| 2 | c54a5f1 | componentes de profundidad: píldoras, sección, tabla técnica, tooltip «?», metodología y anexo |
| 3 | 666f1c5 | La empresa |
| 4 | 73a138c | Cómo gana dinero |
| 5 | 9f3545b | La acción |
| 6 | 6960bd2 | Calidad |
| 7 | 766967b | Cuánto vale (backend del escenario + panel) |
| 8 | 1abb56d | Rivales |
| 9 | 8230edd | Riesgos |
| 10 | c44f8a9 | Actualidad |
| 11 | a27a3d6 | Conclusión |
| 1, 13 | 9779a83 | pruebas de las nueve páginas y arreglos que encontraron |
| 12 | 91df6df | «nada se pierde» (8 tickers) y lo que faltaba en `/v2` |
| 13 | ea11378 | CSS de la profundidad acotado a `.depth`; axe y zoom 200 % en la profundidad |
| 13 | 1904352 | tabla técnica apilada en móvil, capturas y Lighthouse |
| 0 | 394e252 | reintegra E2a (9380a8c: golden con los datos nuevos, titulares que nombran a la empresa, registro) |
| 7 | 203b086 | golden con las claves aditivas del escenario sobre el de E2a; `GOLDEN_DIFF_E3.md` |
| 13 | 4b96e78 | registro y capturas rehechas tras la reintegración |
| PM | 328d3b3 | fusión de E5 (PDF nuevo) con los datos de E2; «Descargar PDF» → `/api/v2/pdf` |
| PM | 051dab5 | revisiones del PM: huecos internos, títulos, Piotroski, fondo papel desde el primer byte |
| PM | (este) | capturas rehechas y registro de los encargos del PM |

## Lo que hay en cada página

Todas: `PillIndex` (píldoras con la sección activa), secciones en rejilla simétrica, «Metodología» al pie. Un dato
ausente es **una línea** (`p.missing[data-missing]`: título y motivo), nunca una caja vacía.

| Página | Píldoras | Contenido (todo del motor) |
|---|---|---|
| La empresa | Ficha · Clasificación · Cifras clave | ficha EDGAR, arquetipo con su motivo y notas, insignia sin fuente oficial, KPI (con «?») |
| Cómo gana dinero | Segmentos · Márgenes · Historia de 10 años · Estados anuales | `/api/v2/segments`: concepto en español, cobertura («Comisiones · cubren el 38 %» en BCS), eje principal, secundario y **todos los `others`** en tarjetas, `dropped_axes` en líneas con su motivo, conciliación; escalera y flujo de resultados; historia de 10 años interactiva (teclado y clic); **estados anuales** con variación y CAGR (la tabla «Histórico» de la web actual, a la vista) |
| La acción | Gráfica · Rentabilidad por periodo · Rango de 52 semanas · Señales | gráfica con cursor (fecha, cierre, volumen), panel de volumen, eventos, 1S–5A, base 100 frente al S&P 500 y el ETF del sector; rentabilidades (las únicas cuentas del cliente: sobre la serie); rango con distancia al máximo; señales «Contexto: no puntúa» |
| Calidad | Rentabilidad · Solidez · (Evaluación institucional) · Crecimiento · Calidad de ganancias · Piotroski · Altman · Desglose · Historia | tablas técnicas (nombre técnico, significado, «?», empresa, referencia, brecha, lectura), escalas con los cortes de cada tramo, estructura del balance con %, pista de caja, Piotroski 3×3, Altman, tarjeta institucional de bancos |
| Cuánto vale | Escenarios · Qué exige el precio · Múltiplos · DCF y sensibilidad · Graham · Metodología | **panel de escenarios** (abajo), DCF inverso con papel y método, múltiplos con su papel en el veredicto y el desglose de Valoración, DCF con escala de valor razonable, fiabilidad, composición, WACC desglosado, sensibilidad del informe con bandas, Graham, enlace al pre-mortem |
| Rivales | Comparador · Frente a la referencia · Metodología | **comparador** (abajo) y la comparativa completa con la referencia (grupos, lectura y frase del motor) |
| Riesgos | Pre-mortem · Alertas · Lo que no sabemos | pre-mortem completo, alertas por grupo con recuento (grupo vacío: una línea), dimensiones de la confianza y sus motivos sin repetir, cobertura |
| Actualidad | Noticias · Próximos resultados · Señales · Lectura conductual | noticias 3×2 (enlace externo `noopener noreferrer`), fecha de resultados anunciada/estimada con su base, PEAD con su lectura y fuente, señales, lectura conductual |
| Conclusión | Veredicto · Confianza · Qué vigilar · Informe · Metodología | puntos del resumen ejecutivo, composición de las dos puntuaciones (barras y ajustes con signo), fichas del resumen con «?», confianza, destacados, advertencias, pre-mortem, **Descargar PDF** (el actual hasta E5) y el **anexo** «Detalle técnico para auditoría» (el único `<details>` de la web) |

### Escenarios (Task 7): calculados por el motor

- `scenario_inputs` gana `revenue`, `fcf_margin`, `archetype`, `bounds` (crecimiento, descuento, terminal y margen;
  el margen entre 0.5 y 1.5 veces el propio, `[scenario] margin_rel_min/max`), `presets` y `reverse` (insumos del
  DCF inverso del informe).
- `POST /api/v2/scenario` acepta `fcf_margin` (FCF = ingresos × margen) y devuelve además `implied_growth` (el mismo
  `reverse_dcf.implied_growth` con los supuestos del usuario) y `sensitivity` (pasos de `[valuation.grid]` centrados
  en los supuestos).
- Tests (`tests/test_scenario.py`): con los supuestos base, valor = DCF del informe, crecimiento implícito = el del DCF
  inverso y sensibilidad = la del informe celda a celda (25); monotonía; presets dentro de los rangos.
- UI: presets Pesimista/Base/Optimista, cuatro controles (deslizador + número, teclado), petición con espera de
  250 ms y cancelación de la anterior, valor por acción, diferencia con el precio, barras, «Qué exige el precio» con
  los supuestos del usuario, sensibilidad coloreada frente al precio y la frase fija «Los escenarios son para
  explorar: no cambian el veredicto». Sin DCF (bancos, REIT…): una línea con el motivo del motor.
- Comprobado en AAPL: base $116.08 = DCF del informe; optimista $236.71; crecimiento implícito 15.6 % (21.6 % los 5
  primeros) = el del informe.

### Rivales (Task 8)

Empresa arriba resaltada (`company`), rivales con calidad, precio, P/E, EV/EBITDA, ROIC, margen neto, crecimiento de
ingresos (3 años), deuda/equity y capitalización; sondeo cada `poll_s` con esqueleto por fila; fila de error con su
motivo; quitar (×) y añadir con el buscador (`?symbols=`, como mucho `max_symbols`); «Volver a los propuestos»; nota
con menos de 3. Backend (aditivo, fuera del golden): el resumen de cada rival trae `revenue_growth` (la fila de su
página), la respuesta trae `max_symbols` y la lista elegida a mano avisa con menos de 3 («menos de 3 comparables
elegidos»). Tests en `test_peers.py`.

## Verificación (salidas, rama integrada 203b086)

- Backend: `4361 passed, 1 skipped` (con las muestras del contrato regeneradas; antes de E3, la suite de E2a+E2b).
- Golden: `diff_golden.py --env panel` y `--env local` → `Resultado: sin diferencias` tras regenerar; el diff
  regenerado son **solo altas** en `scenario_inputs` (24 golden, 984 inserciones, 0 borrados, ningún PDF). Detalle
  en `docs/fiabilidad/GOLDEN_DIFF_E3.md`.
- Frontend: `npm run check` → `check-analysis-literals: sin umbrales literales` (ahora cubre `src/v2/pages`) y
  `check-contract: StockAnalysis encaja con 46 salidas del backend`; `tsc --noEmit` limpio; Vitest `77 passed`.
- Playwright (`E2E_PORT=3001 REPLAY_PORT=8768 npx playwright test e2e/v2`, escritorio y móvil): **269 passed, 103
  skipped** (las capturas, que solo corren con `CAPTURE_E3=1`, y las pruebas de un solo proyecto). Incluye:
  - `depth.spec.ts`: 9 páginas × 8 tickers × 2 proyectos: sin errores de consola, cada píldora con su sección y la
    última activa al pulsarla, sin tarjetas vacías, simetría con huecos internos de E1, nada por debajo de 12 px;
    historia → profundidad con **una sola** petición de `/api/analysis` (y vuelta atrás); tooltip «?» con «Tu
    valor», Esc y foco devuelto.
  - `nada-se-pierde.spec.ts` (8 tickers): toda cifra con forma de `/stock/{T}` (9 pestañas y desplegables abiertos)
    está en `/v2`; y cada tooltip del motor de una métrica que el análisis muestra tiene su «?».
  - `depth-design.spec.ts`: axe sin infracciones graves en las 9 páginas (AAPL y JPM, claro y oscuro); 200 % de zoom
    y texto grande sin desbordamiento (AAPL, JPM y BCS).
  - Las de E1/E2a (simetría, legibilidad, axe, noticias, precio, shell) siguen en verde.
- Lighthouse (escritorio, `next dev` con el replay: orientativo), `capturas-e3/lighthouse-AAPL-*.json`:
  Calidad y Cuánto vale **rendimiento 95 · accesibilidad 100**; FCP 0.3 s, LCP 1.6 s, TBT 0 ms, CLS 0.002.
- Capturas: `docs/rediseno/capturas-e3/` — 88 WebP (≤ 300 KB cada una, 18 MB; ver «Peso de las capturas»): por página AAPL, JPM, O y BCS en claro
  escritorio y oscuro móvil; los 8 tickers en Cuánto vale y Rivales (`{página}-{T}-{tema}-{proyecto}.webp`).
- Secretos: `grep -rn "token=" backend/tests/fixtures` vacío.

## «Nada se pierde»: excepciones (para revisión del PM)

Cifra de la web actual que no está en `/v2`, excusada solo si **todas** sus apariciones van tras uno de estos
contextos (`e2e/v2/nada-se-pierde.spec.ts`, `EXCEPTIONS`):

1. «de cada **$1** de ingreso»: etiqueta de la escalera de márgenes, no una cifra.
2. **100 %** tras «Ingresos $X» o «base:»: la base de la escalera y del flujo de resultados.
3. «Otros pasivos **N %**»: la web actual lo calculaba en el navegador (100 − deuda − patrimonio); `/v2` no calcula
   en el navegador y muestra deuda, patrimonio y caja con el % del motor. Si el PM lo quiere, es una clave aditiva
   del motor (cambiaría el golden: fuera del alcance de E3).
4. «Deuda **$00 %**»: lectura pegada de «$0» y «0 %» en la web actual (ambos están en `/v2`).

Alcance de la prueba: compara cifras con forma (con unidad, decimales o moneda); los enteros sueltos (años, recuentos,
«x/20») y el texto no se comparan. Los tooltips cuentan solo para métricas que el análisis muestra (el motor manda
bandas también de métricas que no aplican, p. ej. payout de una empresa sin beneficio).

Lo que la prueba encontró y se añadió a `/v2`: los estados anuales (todas las cifras por ejercicio con variación y
CAGR), la referencia de las filas «no aplica» de los múltiplos, los cortes de las escalas, el % de la estructura del
balance, la distancia al máximo de 52 semanas, la tarjeta institucional de los bancos y los «?» de beta, rango de 52
semanas, categoría, calidad y las fichas del resumen.

## Desviaciones del plan

1. **Presets del escenario**: el plan pedía `[scenario.presets.<ARQUETIPO>]` con desplazamientos (incluido el margen).
   Implementado `[scenario.presets.default]`: pesimista/optimista = los extremos de la tabla de sensibilidad del
   informe (`[valuation.grid]`: crecimiento ±5 pp, WACC ±2 pp) y ±0.5 pp de terminal; el margen no se desplaza.
   Motivo: no hay una fuente por arquetipo para esos números; la rejilla es la regla del propio motor. Añadir un
   arquetipo es una tabla más en config.
2. **Rivales** gana dos claves aditivas en su endpoint (`max_symbols`, `revenue_growth` en el resumen) y una nota
   para la lista elegida; no tocan el análisis ni el golden.
3. **Historia de 10 años**: dibujada con SVG propio accesible (el plan dejaba elegir), con la tabla del año elegido.
4. **CSS**: todo lo de E3 va bajo `.depth` (los nombres genéricos chocaban con la historia de E1: el capítulo «valor»
   de NEE se estiraba 135 px).
5. **Fichas** (`.tiles.flow`): filas que se rellenan (flex) para que una fila incompleta no deje hueco; la
   comprobación de simetría las cubre (`.flow`). La comprobación también detecta ahora el visor alejado en móvil
   (un desbordamiento que `innerWidth` no delata: lo causaba un `.sr-only` absoluto dentro de una tabla con scroll).
6. **Tabla técnica en móvil**: fichas apiladas (empresa, referencia y brecha con su etiqueta) en lugar de cinco
   columnas.
7. Las capturas son del elemento `.depth` (sin la cabecera de la empresa, que ya está en las de E1), comprimidas a WebP.

## Encargos del PM tras el informe

### Fusión de E5 (8b9fb00) — 328d3b3

- Conflictos resueltos en `main.py` (se conservan todos los `/api/v2/*`; `/api/v2/prices` mantiene el cuerpo de E2a
  —serie de 5 años y eventos— dentro de `_prices_v2_payload`, que reutiliza el PDF) y en `schema.toml` (secciones de
  las dos ramas).
- **El PDF nuevo ve los datos de E2**: `/api/v2/pdf` pasa a `build_pdf` los segmentos de `segments.build` (caché por
  filing y presupuesto propio; nunca lanza). Los rivales no: el informe solo los lee de una caché, y esa caché la
  generaliza E4 (`analysis_queue.py`); su bloque sigue en una línea.
- **Golden de texto `panel_pdf_v2` regenerado (aprobado por el PM)**, 36 informes. Revisado el diff entero (líneas
  sin pareja tras quitar la recolocación): solo entran la ficha EDGAR (sede, SIC, constitución, cierre, tipo de
  emisor) en lugar del perfil de Yahoo, la historia de 10 ejercicios, la variación del día, los segmentos de los 8
  capturados, y los textos que ya cambió el golden aprobado de E2a («+88.4 pp», nombre de la bolsa, «En la frontera
  con…»). Sin dato (MC.PA): una línea con el motivo («no presenta estados en la SEC»).
- **Regla de huecos** de `config/pdf.toml` (hueco al pie ≤ 106 pt) con los datos reales: en verde en los 36
  (`test_pdf_v2_panel.py::test_geometry_gaps_and_cover`); no hizo falta recomponer.
- Pruebas ajustadas a los datos de E2: la portada exige la variación del día cuando la hay; los bloques de E2 exigen
  su tabla cuando hay dato y la línea de ausencia cuando no. El guardián quita la cabecera corrida del PDF nuevo al
  leer (una frase de SNOW quedaba partida por un salto de página).
- «Descargar PDF» de la barra y de Conclusión → `/api/v2/pdf/{símbolo}` (`pdfV2Url`), con prueba e2e (200,
  `application/pdf`, `%PDF`). La web actual sigue con `/api/pdf`.

### Revisiones del PM — 051dab5

1. **Hueco interno en las tarjetas de segmentos.** La comprobación de simetría no lo veía: medía el envoltorio
   `.cardslot` (que la tarjeta llena) y no miraba dentro de `.fill`. Ampliada: atraviesa envoltorios de un hijo y,
   en cada `.fill`, marca el hueco al pie o concentrado entre piezas distintas (un reparto uniforme entre filas
   iguales sí vale). Destapó espacio muerto en varias páginas (hasta 559 px en Riesgos de NEE), corregido componiendo:
   rejilla interna compartida (`subgrid`) en segmentos, escalas de solidez, Piotroski, ROIC−WACC/ROCE y próximos
   resultados/PEAD; una columna para pares de prosa muy desiguales (clasificación, WACC y su cálculo, grupos de
   alertas); filas «sin dato» homogéneas en las listas de barras.
2. **Etiquetas en mayúsculas** («UNITED STATES») corregidas en origen (`segments._clean_label`): mayúscula inicial por
   palabra; se conservan las siglas de `market.segments.upper_words` (US, UK, EU, EMEA, APAC…), las palabras de enlace
   de `lower_words` van en minúscula y una sigla corta de una sola palabra se deja (FPL, NEER). Test en
   `test_segments.py`.
3. **Títulos en minúscula**: `capFirst` en la web y en el PDF; revisadas las 9 páginas de 6 tickers (ningún título,
   cabecera ni etiqueta empieza en minúscula).
4. **Piotroski**: las pastillas no se parten (`white-space: nowrap`; cede el título); si el detalle solo repite el
   criterio («FY2025: ROA positivo»), queda el periodo junto a los valores. Las frases largas que iban en pastilla
   (nota de cobertura de segmentos, lectura del retorno total de un REIT) pasan a texto con su tono.
5. **Pantalla negra antes de pintar**: el layout de `/v2` declara el fondo papel de `html` y `body` desde el primer
   byte, y el tema oscuro guardado se aplica antes de pintar con un `<style>` propio (sin tocar `<html>`, que rompía la
   hidratación). E4 lo comprobará sobre el build.

Verificación tras los encargos: backend `4711 passed, 1 skipped`; `diff_golden --env panel|local` sin diferencias;
`npm run check` en verde; Vitest 77; Playwright `270 passed, 104 skipped`. Lint: quedan 2 errores
`react-hooks/set-state-in-effect` que vienen de E1 (`Chapter.tsx`, y el `setTheme(readTheme())` de
`StoryPageClient`, que necesita el tema en el render estático); los de E3 están corregidos.

## Retoques del PM tras la aprobación de E3

- **Rutas locales** (349be52): el motivo del replay ya no lleva la ruta («sin fixtures en el replay»);
  `e2e/v2/api-sin-rutas.spec.ts` recorre 50 respuestas de la API del replay (8 tickers: análisis, precios, segmentos,
  rivales hasta que terminan, escenario, búsqueda; tendencias; un símbolo sin captura) y busca rutas de macOS/Linux o
  Windows en cada cadena decodificada.
- **Tablas apiladas** (df0d38a): tabla técnica y desglose con `colgroup` y `table-layout: fixed` (escritorio y
  tableta); prueba de que las columnas caen en el mismo sitio. **«— —»**: un solo «—» en Brecha y la Lectura vacía.
  Esa clase nueva (`breakdown`) chocaba con el desglose emergente de E1 y ocultó las tablas de desglose: lo detectó
  «nada se pierde» y se corrigió en b35954f (`bdtable`).
- **Lint en verde** (b35954f): 0 errores. `StoryPageClient` lee la ruta y el tema de almacenes externos
  (`useSyncExternalStore`) y el análisis entra por promesa; `Chapter.tsx` (E1) mide y reajusta en `useLayoutEffect`,
  el uso previsto de ese hook: excepción justificada en la línea. Quedan 3 avisos de `<img>` de la web actual.
- **Aprobación del golden en GOLDEN_DIFF_E3.md**: no la escribí. Al añadir la cita del usuario que me transmitió el
  PM, el sistema de permisos de la sesión lo bloqueó (no se escribe en nombre del usuario una aprobación recibida de
  otra sesión). Queda para que la añada el PM o el usuario.

## E4 Tasks 3 y 4 (en v4)

**Task 3 · Móvil al mismo nivel** (3c493af):
- Proyectos de Playwright: `desktop`, `mobile` (Pixel 7, Chromium), `mobile-webkit` (iPhone 15, WebKit 27.2 instalado
  con `npx playwright install webkit`) y `tablet` (iPad, 768 px). Toda la batería de `/v2` corre en los cuatro.
- Cabecera compacta en teléfono: las tres puntuaciones en una fila con cifra y escala mini; al tocar, el desglose
  (con la pregunta y la base) en una hoja inferior con fondo, «Cerrar» y Esc. Precio a 32 px con la variación al
  lado (ya lo estaba).
- Barra de capítulos que se desplaza sola al activo; píldoras deslizables sin barra visible; tablas técnicas en
  fichas por métrica (< 768 px); tablas de sensibilidad con desplazamiento propio; gráficas con
  `handleScroll.vertTouchDrag = false`; controles del escenario ≥ 44 px en pantallas táctiles; tooltips como hoja.
- Tableta vertical: capítulos de la historia a una columna hasta 1023 px (a dos columnas en 768 px no se podían
  igualar texto y visual).
- **Zoom en iPhone (diagnóstico):** `/v2` declara `width=device-width, initial-scale=1`, sin `maximum-scale` ni
  `user-scalable`; ningún elemento lleva `touch-action` que impida pellizcar (en todo el código solo hay
  `touch-action: manipulation` en `globals.css`, que permite el zoom) y no hay manejadores de `gesturestart`.
  `e2e/v2/movil.spec.ts` lo comprueba en WebKit en la historia, La acción, Cuánto vale y Calidad. La web actual
  tampoco limita el zoom en su código ni declara `apple-mobile-web-app-capable`: si al usuario no le deja hacer zoom
  al abrirla como icono de la pantalla de inicio, la causa probable es ese modo (`standalone`), no la página; `/v2`
  se abre como página normal con zoom. Queda la prueba en su teléfono cuando pruebe la v4.

**Task 4 · Modo oscuro completo** (b35954f y el commit de este registro):
- Tema: el guardado o, la primera vez, el del sistema (`prefers-color-scheme`). El script del layout de `/v2` lo pone
  en `<html>` (`data-v2theme`) antes de pintar; el fondo y los tokens de `.fz2` salen en su tema desde el primer
  fotograma (la portada de E4 hereda el mismo layout).
- `e2e/v2/oscuro.spec.ts`: sin parpadeo (fondo del primer fotograma, con tema guardado y con el del sistema; lo
  guardado manda después); axe AA en oscuro en la historia y las 9 páginas (AAPL y BCS en escritorio, AAPL en iPhone y
  tableta) y con el tooltip «?», el escenario y la hoja inferior abiertos. Las zonas con desplazamiento propio son
  regiones enfocables con nombre (axe `scrollable-region-focusable`).
- Capturas en `docs/rediseno/capturas-e4/`: historia, Calidad y Cuánto vale en iPhone (WebKit) y tableta, claro y
  oscuro (`CAPTURE_E4=1`).

Verificación: Playwright `499 passed` en los 4 proyectos (313 omitidas: capturas y pruebas de un solo proyecto);
Vitest 78; lint 0 errores; `npm run check` en verde.

## Peso de las capturas (revisión del PM)

Las carpetas `docs/rediseno/capturas-*` sumaban ~214 MB de imágenes (PNG/JPG de 1–5 MB). `npm run capturas:comprimir`
(`frontend/scripts/comprimir-capturas.mjs` con `capturas-lib.mjs`, sharp) las pasa todas a WebP de 1200 px de ancho
como mucho y calidad 70, baja la calidad si alguna pasa de 300 KB y reduce las de página entera muy altas (límite de
WebP de 16 383 px), borra los originales y cambia sus referencias en los `.md`: 235 imágenes, **214 MB → 41 MB**,
ninguna por encima de 300 KB. Las pruebas de captura (E2a, E3, E4) escriben ya comprimido (`e2e/v2/capture.ts`).
Las capturas grandes siguen en el historial de las ramas del rediseño: no se reescribe historia; el PM lo resuelve
al migrar a `main` (squash o filtrado).

## Fusión de `rediseno/e4-portada` (8328af0)

- Conflictos: `TopBar.tsx` conserva el SearchBox de E4 y el enlace del PDF nuevo (`pdfV2Url`); `peers.py`,
  `analysis_queue.py` y `trending.py` con la cola compartida de E4 y el resumen de rivales de E2b (`revenue_growth`,
  `max_symbols`); `playwright.config.ts` con `E2E_BUILD` de E4 y los cuatro proyectos (desktop, mobile, mobile-webkit,
  tablet); `package.json` con los scripts de las dos ramas; `e2e/v2/capture.ts` el de E4 más `captureElement` (las
  capturas de E3 por bloque). `capturas:etapa` comprime al copiar, y las 4 PNG de la portada pasan a WebP.
- `StoryPageClient` pide el análisis con `fetchAnalysisV2` (`src/v2/lib/analysis.ts`): con Yahoo caído enseña el motivo
  del backend en español. El caso `yahoo_down` de `e2e:fallos`, marcado como fallo esperado, pasa a verde y pierde la
  marca.
- Durante la fusión, `next dev` se quedó con el error de compilación de un `package.json` todavía con marcas de
  conflicto: su capa de errores (`nextjs-portal`) tapaba la página y los clics de las pruebas agotaban el tiempo.
  Reiniciar el servidor lo resolvió. No es un fallo del código.
- La prueba de la tarjeta sin análisis de la portada (TSLA) necesita un replay recién arrancado. Con horas de pruebas
  encima, el cupo diario de precalentado se agota, el fallo de TSLA caduca y la tarjeta enseña «Sin análisis del motor
  por ahora», que es el comportamiento previsto.
- Verificación: backend `4750 passed, 1 skipped`; `npm run check` en verde; Vitest 93; lint 0 errores (los 3 avisos
  de `<img>` de la web actual); `e2e:v2` 612 pasadas de 920 en los 4 proyectos (308 omitidas: capturas y pruebas de un solo
  proyecto), contando `home.spec` repetido con el replay recién arrancado; `e2e:fallos` con `V2_PAGES` de las 9
  páginas: 396 pasadas.

## V1 · panel completo sin red

- **Alcance.** El panel son 37 tickers (los fixtures del replay), que ya incluyen MC.PA y SPY, así que el total es 37
  y no 37 + MC.PA. Se recorren `/v2/{T}` y sus 9 páginas, en claro y en oscuro, en el build de producción servido por
  el replay (`npm run build`; el replay sirve `frontend/out` y la API en el mismo origen). Sin red: toda petición
  fuera de localhost se corta y se anota. Las únicas fueron imágenes de noticias de cdn.benzinga.com,
  image.cnbcfm.com y static.seekingalpha.com. `frontend/out` se restauró después a la versión de la rama, sin commit,
  como en E4.
- **Herramientas.** `playwright.v1.config.ts` define un proyecto por navegador y ancho (Chromium, WebKit y Firefox ×
  1440, 768 y 375 px; táctil y visor móvil por debajo de 1024 donde el motor lo emula). `e2e/v1/panel.spec.ts` lanza
  un test por ticker × tema que recorre las 10 páginas en una pestaña. Por página comprueba:
  - consola sin errores;
  - sin excepciones;
  - sin peticiones a localhost fallidas o ≥ 400 (salvo el 422 del análisis de SPY);
  - `symmetryProblems` (huecos internos, desbordamiento también dentro de tarjetas y tablas, visor);
  - `smallTexts` (≥ 12 px);
  - axe WCAG 2 A/AA sin infracciones graves ni críticas.

  En SPY, cada página tiene que mostrar el motivo del ETF. Se lanza con `npm run e2e:v1` (repartible con `--project`
  o `--shard`; `V1_TICKERS` y `V1_WORKERS`). `npm run v1:matriz` junta los JSON de `frontend/v1-results/` en
  `docs/rediseno/verificacion/V1_matriz.md`.
- **Firefox no se pudo ejecutar.** El Firefox 157 de Playwright (firefox-1555) no arranca en este macOS 27.0.1:
  «Could not find profile folder», también fuera del sandbox y con TMPDIR, HOME o `XRE_PROFILE_LOCAL_PATH` propios.
  Sus columnas van con «—» en la matriz. Chromium y WebKit sí se ejecutaron.
- **Primera pasada (build anterior a los arreglos):** 404 de 444 pasadas. Los 40 fallos fueron todos de simetría a
  1440 px, en ningún otro tamaño. No hubo ningún fallo de consola, red, axe, letra ni desbordamiento.
  - Calidad, en la historia (ASML, NVDA, TSM: el visual se estira hasta 132 px; MU, NFLX: hueco de 76 px en el
    texto). La nota de cómo sale la puntuación (persistencia por encima de 80, calidad de ganancias) iba en la lectura,
    frente a un visual fijo. Ahora va con las barras, en la nota del visual (`story.ts`).
  - Rivales, en la historia (SNOW: el visual se estira 108 px). Con 3 métricas el visual es corto y la explicación de
    la referencia alargaba la lectura. Ahora va bajo la tabla, que se recorta si la nota la alarga.
  - Cuánto vale, en la historia (MU: 96,3 px, por encima del tope de 96). Las cifras clave no cabían en ningún lado:
    en el texto el visual se estiraba más de lo permitido y, dentro de la tabla, quedaba un hueco en el texto.
    `fit.figuresPlace`: con un visual que se recorta, si en el texto el visual tendría que estirarse más del tope
    (`MAX_VISUAL_STRETCH`, en rem), las cifras van al visual y el ajuste quita filas. Si ni así cabe, vuelven al
    texto, como antes. Probé antes a acortar la lectura del DCF inverso y lo descarté: en AMT, O y PLD empeoraba
    (117 px), porque ya cuadraban con las cifras en el visual.
  - Calidad, en la página (AMZN y TM: hueco de 32 px; BRK-B: 56 px, en «Lo que puntúa en Crecimiento»). Con una sola
    entrada junto a tres filas de crecimiento, la tarjeta corta dejaba un hueco al pie. Ahora, con menos de dos
    entradas en cualquiera de las dos, van una debajo de otra (`SIDE_BY_SIDE_MIN`), y sin componentes no se pinta la
    tarjeta.
  - Empresa, en la página (UL: hueco de 25 px). «P/E reportado (último ejercicio)» se partía en dos líneas y bajaba
    la cifra de las fichas vecinas. Ahora la ficha con una etiqueta de más de 24 caracteres parte más ancha
    (`.tile.wide`, 17rem). En el panel, las de hasta 22 caracteres ya caben en una línea.
- **Tests de los arreglos.**
  - `e2e/v2/v1-regresiones.spec.ts`: los 10 casos a 1440 px, más «ninguna etiqueta de cifra clave en dos líneas»
    en UL.
  - Vitest:
    - en `story.test.ts`, la nota de calidad va al visual (PLTR) y qué es la referencia va bajo la tabla (AAPL);
    - en `fit.test.ts`, `figuresPlace` con el tope.
  - En el backend, `test_pdf_v2_endpoint.py`: SPY recibe su 422 con el motivo, no un informe.
- **Pasada final (build con los arreglos):** **444 de 444 pasadas: 4440 páginas sin fallos** en Chromium y WebKit, a
  los tres anchos y en los dos temas (52 min con 9 workers). Las 2220 páginas de Firefox quedan sin ejecutar.
- **PDF v2 del panel:** `test_pdf_v2_panel.py`, `test_pdf_v2_guardian.py` y `test_pdf_v2_endpoint.py` dan 258
  pasadas antes del test nuevo de SPY. Cubren los 36 informes (geometría, letra ≥ 8 pt, huecos, portada, enlaces,
  peso, tiempo, texto golden, nada cortado con puntos suspensivos y guardián) y SPY rechazado.
- **«Nada se pierde» en todo el panel:** `NADA_TICKERS=panel` da 36 de 36 pasadas. SPY no entra: ninguna de las dos
  webs lo analiza y las dos muestran el motivo.

## Revisión V6 · arreglos del frontend (F1–F25), rivales en el PDF y reinicio del replay

Cada arreglo, con su test (e2e `e2e/v2/v6.spec.ts`, Vitest y backend). Las pruebas del navegador corren en escritorio
salvo las de la hoja inferior, que van en móvil.

| # | Arreglo | Test |
|---|---|---|
| F1 | La rentabilidad por periodo (de precio y total), la base 100 y las marcas de eventos las calcula el backend: `lib/price_returns.py` (config `[price_returns]`). Hay una sola implementación para `/api/v2/prices` (`ranges`; `returns` en cada serie; `chart` por periodo con `{i0, values}` alineados al calendario de cada serie, y `marks`) y para el PDF nuevo (`parts.period_returns` y `chart_window` la usan; el golden del PDF no cambia). Manda la regla del PDF: días naturales, y un periodo no cubierto queda sin dato. La web solo pinta (`returns.ts`, `chartEvents.ts`, `PriceChart*`, `Accion`); el guardián añade la regla «sin cálculos» en esos archivos (`PAINT_ONLY`: ni ×, ÷, %, `Math.*` ni `toFixed`). | `test_price_returns.py` (20, con «la web y el PDF enseñan las mismas cifras» en 12 tickers del panel), `returns.test.ts`, `guardian.test.ts` |
| F2 | Error de carga con «Reintentar» (vuelve a pedir) y «Volver a la portada», y cancelación al desmontar | e2e F2 |
| F3, F24 | Noticias: solo enlaces `http(s)` (si no, `<article>` sin enlace), imagen con `alt=""` y «(se abre en una pestaña nueva)» para lectores de pantalla | `news.test.ts`, e2e F24 |
| F4, F5 (rivales) | Quitar y añadir con actualización funcional; el sondeo reintenta un 5xx o una caída de conexión con espera creciente; el buscador usa `searchV2` con espera, cancelación y contador de secuencia; sin `listbox` sin opciones | e2e F4, F5 |
| F5 (moneda) | Precio de la cabecera en la moneda de la cotización (MC.PA en EUR) | e2e F5 |
| F6 | `parseV2Path`: `decodeURIComponent` en try/catch y símbolo validado con `TICKER_LIKE`. Si no es válido, «Ticker no válido» sin pedir el análisis. `app/v2/error.tsx` propio, con «Reintentar» y la portada | `routes.test.ts`, e2e F6 (dos) |
| F7 | `document.title` por empresa y capítulo (`useDocumentTitle`: Next lo pisa al hidratar y se vuelve a poner), y el foco al título de la página al cambiar de capítulo | e2e F7 |
| F8 | Hoja inferior («?» y desglose de la puntuación en móvil): modal, con Tab atrapado, el fondo sin desplazamiento y el foco devuelto al cerrar (tocando fuera, con Escape o con «Cerrar»). El popover de escritorio no atrapa Tab | e2e F8 (tres) |
| F11 | `SearchBox`: escribir desmarca la opción; Enter solo usa los resultados de lo escrito ahora; cancela la búsqueda anterior; no hay `listbox` sin opciones | e2e F11 |
| F12 | `v2/lib/http.ts`: caché en el módulo con TTL (precios 10 min, segmentos 30 min, rivales 10 min; solo los rivales ya calculados) y cancelación por consumidor (`AbortSignal`) en cada efecto | `http.test.ts`, e2e F12 (una petición de precios entre la historia y la acción) |
| F13 | Cada página de profundidad y las dos gráficas van en su propio fragmento (`v2/lib/lazy.tsx`: `React.lazy` con su esqueleto del mismo alto, `PriceChartParts.tsx`). Con `next/dynamic` anidado dentro del de `V2Entry`, `next dev` (Turbopack) precargaba en el HTML un fragmento que nunca genera (404 en la consola, solo en desarrollo); con `React.lazy` sigue pasando en `next dev` (el `dynamic()` de `V2Entry`, de E4, declara el grupo). En el build no falta ningún fragmento: por eso `e2e:fallos` corre contra el build (`E2E_BUILD=1`), como el V1 | e2e F13 (`next dev`), `produccion.spec` «sin fragmentos que falten» (build) |
| F14 | sessionStorage con versión, como mucho 5 empresas y purga de lo caducado (y de lo de otra versión); si está lleno, se vacía lo propio y se reintenta | `analysisCache.test.ts` |
| F15 | Guardas ante datos raros: segmentos sin listas o sin importes, series vacías, fechas rotas, rivales a medias | e2e F15 (tres modos, las 10 páginas, sin excepciones ni límite de error) |
| F16 | Portada: el sondeo para con `document.hidden` y sigue al volver; los fallos esperan cada vez más (5, 10, 20… s, como mucho 60) | e2e F16 (reloj simulado) |
| F17 | Escenario: cancelación al desmontar, el `detail` del 422 tal cual, y el color de las celdas y el tono del resultado decididos por el motor (`display.sensitivity_band`, la regla de la sensibilidad del informe; refactor sin cambios en el golden) | `test_scenario.py`, e2e F17 |
| F18 | Errores en español, sin «Failed to fetch», «HTTP 500» ni el código entre paréntesis | `http.test.ts`, `analysis.test.ts`, `companyData.test.ts` |
| F21 | Periodos: grupo de botones con `aria-pressed` (antes, un `tablist` a medias); el nombre accesible es el texto visible | e2e F21, `price.spec` |
| F23 | El desglose de la puntuación se cierra con Escape (escritorio) | e2e F23 |
| V2 (PM) | «Descargar PDF» de la barra solo con un análisis válido cargado: no mientras carga ni con un error (SPY, un ETF: 422; ZZZZZ, inexistente: 404; SIVB, deslistada: 404), con lo que el PDF ya no respondería 422/404 | e2e: los tres casos sin botón, y AAPL sin botón mientras carga y con él al cargar |
| F25 | Botón de tema sin parpadeo: las dos etiquetas van en el HTML y el CSS enseña la del tema que el script puso en `<html>` antes de pintar (`TopBar.tsx`, el cambio que pide V6) | e2e F25 |

- **Rivales en el PDF nuevo:** `peers.cached_for` lee la caché compartida sin encolar nada y `_pdf_v2_build` se la
  pasa al informe. Sin rivales en caché, el informe lo dice en una línea («consulta la web»), y un fallo leyendo la
  caché no lo tumba. Tests en `test_peers.py` y `test_pdf_v2_endpoint.py`.
- **Replay reproducible:** `POST /__replay/reset` deja la cola compartida, los rivales y las tendencias como recién
  arrancados y quita el fallo activo. El replay tiene un cupo de precalentado propio (`--prewarm-max`, 10 000 por
  defecto), que sobrevive a los reinicios de las tendencias, también a los de los fallos. El `globalSetup` de
  Playwright lo llama al empezar cada pasada (`playwright.config.ts`, `.v1`, `.fallos`). Test en
  `test_replay_reset.py`.
- **Verificación tras V6:**
  - backend `4776 passed, 1 skipped`; `diff_golden --env panel` y `--env local` sin diferencias; sin `token=` en los
    fixtures;
  - Vitest 108, lint 0 errores (los 3 avisos de `<img>` de la web actual), `npm run check` en verde;
  - `e2e:v2` en `next dev`: 644 pasadas y 0 fallos en los 4 proyectos (420 omitidas: capturas, pruebas de un solo
    proyecto y las de V6, de escritorio o de móvil); `produccion.spec` contra el build: 12 pasadas;
  - `e2e:fallos` con `V2_PAGES` de las 9 páginas, contra el build (`E2E_BUILD=1`): 395 de 396. El fallo fue una conexión
    perdida en WebKit (tableta) en la portada con Yahoo caído; al repetirlo, 10 de 10 en WebKit;
  - **V1 repetido sobre la versión arreglada: 444 de 444, 4440 páginas sin fallos** (Chromium y WebKit, matriz
    actualizada); «nada se pierde» en el panel: 36 de 36.
- **Para el PM:**
  - MC.PA cotiza en EUR y el motor trata sus cifras en EUR, pero las formatea con «$» (`numfmt.money`): KPI de
    precio y capitalización, variación del día, etc. Arreglarlo cambia el golden de MC.PA. La web ya enseña el precio
    de la cabecera en EUR.
  - `/api/v2/prices` pasa de unos 260 KB a unos 360 KB sin comprimir (la base 100 de los 8 periodos). Con GZip en el
    backend (middleware, de la sesión de E4) bajaría mucho.

## V7 · lectura de un usuario nuevo: presentación (P2–P6)

Encargo del PM (`docs/rediseno/verificacion/V7_lector_nuevo.md`, sección «Presentación»). P1 espera a M5 de E4 y a la
fusión de `rediseno/e4-portada`. Ningún veredicto cambia; `diff_golden` (panel y local) sin diferencias.

| # | Arreglo | Prueba |
|---|---|---|
| P6 | Buscar por nombre + Enter abre el primer resultado (antes, solo un ticker exacto) | `search.test.ts`, e2e P6 |
| P6 | «Descargar el informe en PDF →» del capítulo 9 descarga el PDF (antes llevaba a /conclusion) | e2e P6 |
| P6 | Cabecera compacta en las 9 páginas de profundidad: nombre, precio, conclusión y las tres puntuaciones en una línea; las escalas con su desglose, solo en la historia (móvil: 386 → 207 px; escritorio: 434 → 128 px) | e2e P6 (escritorio y móvil) |
| P5 | Capítulo 6 «Frente a sus rivales»: la empresa y tres rivales con su calidad y su precio (`usePeers`, la misma cola que el comparador), «Ver comparador de rivales →»; «agregado» en lugar de «mediana» (web y PDF); las cifras destacan una métrica mejor y una peor | `story.test.ts`, e2e P5 |
| P5 | P/E fuera de rango (> `market.peers.pe_meaningful_max`, 200x): «n. s.» con su motivo, en el comparador y en el PDF | `test_peers.py`, e2e P5 (SNOW con P/E 4366x) |
| P5 | Tabla de rivales del PDF con la fila de la empresa («· esta empresa») | `test_pdf_v2_endpoint.py` |
| P5 | Si la tabla del capítulo 6 no cabe junto al texto, el ajuste quita rivales de uno en uno (MC.PA: 55 px de hueco) | historia de los 36 a 1440 px |
| P4 | Capítulo 2: lectura y barras desde los segmentos de la SEC (producto si el emisor lo publica, geografía en la segunda línea: `segments.summary`, en `/api/v2/segments`); sin segmentos, la lectura de rentabilidad y la escalera de márgenes. El DuPont sale de Negocio (ya estaba en Calidad, web y PDF) | `test_segments.py`, e2e P4 (AAPL, sin segmentos, DuPont) |
| P4 | El visual del capítulo 2 son filas que el ajuste recorta desde el final: los segmentos (producto o eje principal), la geografía y los márgenes. Con pocos segmentos (NEE, PLTR) el visual ya no queda corto, y con muchos (BCS) ya no sobra | e2e `symmetry.spec`, y la historia de los 36 a 1440 px |
| P4 | PDF, capítulo 2: la misma lectura que la web y el desglose por producto con importes (`segments.product_view`; AAPL: iPhone 50 % · $209.59B…). Lo que cubren los segmentos («Comisiones · cubren el 38 %…») va en la línea de la fuente, sin una línea más, y sustituye a «difieren un 0 %» | `test_segments.py` |
| P3 | «?» en las etiquetas del bloque superior (categorías, filas del precio, dimensiones de la confianza) y en las cifras del capítulo 3 (momentum, tendencia, rango de 52 semanas, demás señales) y en el ETF del sector de la gráfica (XLK…). En el móvil, la hoja de cada puntuación añade «Qué es cada fila». 23 definiciones nuevas en `tooltips.ts` (categorías, DCF inverso, bloque P/B, confianza, señales de mercado, ETF del sector, ROTE) | `terms.test.ts`, `CompanyHeader.test.tsx`, e2e P3 |
| P3 | PDF: glosario de una página al final (26 términos de `pdf.glossary.keys`, título y primera frase de `metric_definitions.json`), enlazado en el índice (en el hueco de «Resumen», ver las decisiones del PM) y en los marcadores. Empieza en una página propia | `test_pdf_v2_glossary.py` (36 de 36 en una página), `test_pdf_v2_panel.py` |
| P2 | «Banderas rojas del modelo: 0» en lugar de «Riesgos 0» (historia y página), con la aclaración de que no quiere decir que no haya riesgos | e2e P2 |
| P2 | Riesgos: bloque «Concentración de los ingresos» con el mayor segmento y la geografía que cae, como hechos, enlazado a Negocio | e2e P2 |

- **Golden del PDF nuevo (`panel_pdf_v2`) regenerado**, 36 de 36. Cambian solo: la lectura del capítulo 2 (los
  segmentos; sin ellos, la lectura de rentabilidad) y su desglose (producto en lugar del eje principal donde el
  emisor lo publica aparte: AAPL y RIVN), «agregado» en el capítulo de rivales, el glosario (página nueva al final) y su entrada en el índice,
  y lo que se desplaza con ello (números de página, cabeceras de tabla repetidas al partirse en otra página).
- **Contrato:** las muestras de `test_e2b_contract.py` llevan ahora el `summary` de los segmentos, igual que el endpoint,
  y un rival y una empresa con el P/E «n. s.» (`note`).
- **Ajuste de la historia con visuales que llegan tarde** (rivales, segmentos): tras el ajuste, un `ResizeObserver`
  vuelve a ajustar el capítulo si el visual o la lectura cambian de alto.
- **Verificación tras V7 (P2–P6):**
  - backend `4819 passed, 1 skipped`; `diff_golden --env panel` y `--env local` sin diferencias; sin `token=` en los
    fixtures;
  - Vitest 112, lint 0 errores (los 3 avisos de `<img>` de la web actual), `npm run check` en verde;
  - `e2e:v2` en `next dev` con el replay recién arrancado: 662 pasadas y 0 fallos en los 4 proyectos (466 omitidas); tras
    las decisiones del PM y P1 (los «?»), 664 y 0 (468 omitidas), backend `4819 passed, 1 skipped`, Vitest 113;
  - historia a 1440 px en los 36 del panel, con los segmentos y los rivales ya cargados: simetría sin problemas (36 de
    36; prueba temporal, retirada).

### Decisiones del PM sobre V7 (P2–P6 aprobados en 5779ae5)

1. **La nota de calidad de KO en la página 3.** El PM dijo: «Relajar el test es aceptar el síntoma». La causa era la
   fila nueva del índice: el glosario era la entrada 13 en 3 columnas, así que añadía una fila de unos 23 pt. Con ella
   la nota «NOTA · CALIDAD» entera pasaba a la página 3, separada del resumen al que pertenece; antes empezaba en la 2
   y terminaba en la 3.
   - **Arreglo en origen:** el índice deja de enlazar «Resumen 2». El resumen empieza justo debajo, en la misma
     página, así que esa entrada no llevaba a nada que no se viera ya; sigue en los marcadores del PDF. El glosario
     ocupa su hueco: 12 entradas, 4 filas, el mismo alto que antes de V7.
   - Compactar el relleno de las filas no bastaba: en MC.PA, MU, NFLX, TSM y UL la nota seguía pasando entera a la
     página 3.
   - Ahora la página 2 termina exactamente donde terminaba antes de V7 en los 36 del panel (comparado con el golden
     anterior).
   - El test original está restaurado: la nota empieza en la página 2.
   - Captura de KO, páginas 1–3: `docs/rediseno/capturas-e3/V7_KO_p1-3.webp`.
2. **Geometría.** El PM pidió que la exención sea «una regla general: la página anterior a un capítulo que empieza
   página nueva, no una excepción del glosario».
   - `ChapterHeading(new_page=True)`, a través de `heading_block(..., new_page=True)`, empieza página y lo declara en
     las palabras clave del PDF (`pagina_nueva_<clave>=<página>`).
   - `pdf_geometry.gaps` no mide el hueco al pie de la página anterior a cada una de esas páginas.
   - `test_pdf_v2_panel` comprueba que el glosario es hoy el único capítulo que lo declara.
3. **P1, en parte.** El PM pidió: «si P1 depende de M1–M7, espera; si no, adelántalo».
   - **Hecho:** los «?» de las tres puntuaciones. Usan las definiciones de `tooltips.ts` (`quality`, `price`,
     `confidence`) y están en la cabecera completa y en la compacta. Pruebas: Vitest y e2e P1.
   - **Espera a M5:** la línea bajo «Confianza del veredicto» («el DCF directo descartado no puntúa»). El motor lo
     confirma: un DCF de fiabilidad baja ni puntúa ni cuenta en la convergencia. Pero en AAPL la misma tarjeta enseña
     hoy «DCF (upside) −4» como fila que puntúa. La línea contradiría esa fila hasta que M5 cambie esos nombres.
   - El popover del «?» se desplaza ahora con `left`, no con `transform`: el desbordamiento de la página se calcula
     con la posición sin transformar, y la tarjeta de la confianza, la de la derecha, ensanchaba la página 68 px.
4. **Filas partidas entre páginas** (PM, tras aprobar a389397 y 408597e). El PM señaló que en la página 3 de KO el
   texto aparece «arriba sin etiqueta, desconectado de todo», y pidió:
   - descartado KeepTogether: «dejaría un hueco al pie de la 2»;
   - la parte de una fila que pasa a la página siguiente repite la etiqueta con «(sigue)»; la de la página anterior
     conserva la suya;
   - test: «ninguna página empieza con texto de la columna de valor sin su etiqueta en la columna izquierda».
   Lo hecho:
   - **`parts.LabeledTable`** hace eso en las filas del resumen y en todas las tablas `data_table` (anexo,
     metodología, ficha, desglose). También cubre la página que empieza a mitad de un grupo de filas con la etiqueta
     solo en la primera, como las bandas de una métrica en el anexo. Una fila de más de dos páginas dice «(sigue)» una
     sola vez en cada parte.
   - **Comprobación:** `pdf_geometry.headless_page_starts` mira la primera línea de cada página, o la siguiente si la
     primera es una cabecera de tabla repetida. Falla si empieza en la columna del valor. Con `LabeledTable`
     desactivado, señala los 7 casos del panel.
   - **Pruebas:** `test_no_page_starts_with_a_value_without_its_label`, en los 36 del panel; KO y la fila larga en
     `test_pdf_v2_report.py`.
   - **Golden:** solo gana esas 7 etiquetas «(sigue)», sin mover páginas, en 6 empresas: KO, MU y NFLX (nota de
     calidad); FCX y NFLX (desglose); BCS y TM (bandas del anexo).
   - La captura de KO está actualizada.
   - Fuera de esto: el «.;» de la nota de KO es texto del motor y va a E4. «El precio excede en 31 %» es M1 y llega con
     la fusión.
5. **P1 en el PDF (opción C).** Cita del PM: «La portada no cambia: el desglose y la gráfica son más valiosos ahí
   que una línea explicativa larga, y en las opciones A y B alguna portada pierde algo. La línea va completa en la
   fila «CONFIANZA DEL VEREDICTO» del resumen (página 2), que es su sitio natural en un documento».
   - Esa fila es ahora exactamente `display.confidence.summary`, el mismo texto que enseña la web: la tarjeta (sin la
     primera frase, que repite el nivel) y Conclusión (entero).
   - La tarjeta de confianza de la portada lleva el `verdict_text` de M5 bis. AAPL dice «DCF inverso y los múltiplos
     coinciden». «El DCF y los múltiplos coinciden» solo queda donde el directo es fiable y puntúa: JNJ, KO, NVO, PG,
     TSM y V.
   - Test: `test_confidence_row_is_the_engine_summary`, en AAPL, KO, XOM y O.
   - El tiempo del informe en `test_pdf_v2_panel` mide ahora solo la composición, sin la lectura de los fixtures. En
     AAPL la lectura y el análisis del 10-K de los segmentos eran unos 3 s de los 3,3 s, y el informe 0,26 s.
6. **Paneles fuera de la barra de capítulos** (PM). La regla: «el panel nunca ocupa la zona de la barra fija, ni por
   delante ni por detrás». Antes, el «?» de «Crecimiento» en la cabecera de AAPL abría el panel por debajo y la barra
   quedaba encima de él (`capturas-e3/V7_tip_barra_antes.webp`). Ahora abre por encima
   (`V7_tip_barra_despues.webp`).
   - **Un solo componente, `Floating`.** Lo usan el panel de los «?» (`MetricTip`) y el desglose de las tres
     puntuaciones (`ScoreScale`). Va en un portal dentro de `.fz2` y se coloca con `@floating-ui/react-dom` 2.1.9
     (`flip`, `shift`, `size`).
   - **Escritorio y tablet.** El panel se ancla al «?» o a la tarjeta, abajo o arriba según quepa, y se desplaza en
     horizontal si hace falta. El área válida es el viewport menos la barra, medida en vivo, menos 8 px.
     - Si no cabe entero, toma el alto disponible y se desplaza por dentro.
     - Si no queda sitio útil (menos de 48 px), se oculta hasta que lo haya.
     - Con scroll: se cierra si el ancla entra bajo la barra o sale de la pantalla; si no, se recoloca.
   - **Móvil (< 768 px).** Hoja inferior con el fondo atenuado, título, «Cerrar», Escape y gesto hacia abajo. La hoja
     y el fondo empiezan bajo la barra, que sigue visible y despejada. Si la barra está aún en su sitio y la hoja
     quedaría por debajo del 60 % de la pantalla, la página se desplaza antes hasta que la barra queda pegada arriba.
   - **El desglose de una tarjeta y sus «?».** Mientras está abierto el «?» de una fila, el desglose de esa tarjeta se
     aparta. Después sigue apartado hasta que el ratón o el foco salen de la tarjeta, como con Escape (F23).
     - El hover se relee del navegador (`:hover`) con cada movimiento y con el scroll.
     - En una tableta táctil no hay hover (`(hover: hover)`): el desglose sale al tocar, porque el toque enfoca la
       tarjeta.
   - **Textos.** El desglose de la calidad dice «La calidad suma cuatro categorías de 20 puntos y se expresa sobre
     100. Excelente desde 80, sólida desde 65, media desde 45; débil por debajo.» El del precio, en la versión que
     aprobó el PM: «El atractivo del precio parte de 10 sobre 20 y suma lo que dicen los múltiplos y el DCF; se expresa
     sobre 100 y, cuanto menor es la confianza, más se acerca a 50. Atractivo desde 65, razonable desde 45, exigente
     desde 30; muy exigente por debajo.» Las cifras salen de la config, con `backendConfig.ts` generado:
     categorías, máximo, escala, bandas y neutro.
     - Ya no aparecen «Bandas del motor», «reescaladas» ni «factor».
     - En el «?» de las categorías, «se reescala sobre las demás» pasa a «se calcula con las demás». Ese diccionario
       (`tooltips.ts`) es compartido, así que el cambio llega también a la web actual y al glosario del PDF.
   - **Mayúsculas.** «Solidez financiera» y «Calidad de ganancias», en `[score.category_labels]` (thresholds.toml).
     - Las claves del motor no cambian. `display` da `key`, la clave, y `name`, cómo se escribe.
     - La web busca por `key`: la página Calidad y los «?».
     - El guardián pasa. En los 120 golden (panel, local y `panel_pdf_v2`) solo cambian esos dos textos y aparece el
       campo `key`; ningún campo de puntuación, veredicto, DCF ni alerta. El PDF actual también los escribe así.
   - **Tests:**
     - `e2e/v2/paneles.spec.ts`, en los 4 proyectos con AAPL, JPM y PLTR. Abre cada «?» de la historia y de
       /calidad: el panel queda entero dentro del viewport y sin cruzarse con la barra, también tras 120 y 240 px de
       scroll. En móvil es hoja. También comprueba el desglose de las tres tarjetas.
     - En Vitest, el texto exacto del PM.
     - En el backend, `test_category_labels_only_change_how_categories_are_written`.
     - Los specs de antes que buscaban el panel dentro de su componente lo buscan ahora en el portal: `v7` P3 y la hoja
       de `movil`.
7. **Error al cargar el análisis** (PM: «un 404 de `/api/analysis/{T}` deja la página en "ANALIZANDO …" para
   siempre»).
   - **Reproducción.** En el servidor de desarrollo, `/v2/HD/` contra el replay ya enseñaba el error en menos de un
     segundo, también al llegar desde el buscador. La espera infinita viene de otro sitio: la petición no tenía límite
     de tiempo, y el backend real analiza en el momento un ticker que no está en caché.
   - **Arreglo.**
     - `fetchAnalysisV2` espera como mucho `data.toml [web] analysis_timeout_s` (120 s; llega a `backendConfig.ts`
       generado). Agotado el plazo, dice «está tardando más de lo normal».
     - Cualquier error lleva al mismo estado (`LoadError`): 404, 422, 5xx, sin red o fuera de plazo. Enseña el ticker,
       el motivo en lenguaje claro (el `detail` del backend si se entiende) y dos acciones: «Volver a intentarlo» y
       «Buscar otra empresa», que enfoca un buscador dentro del propio estado, porque en el móvil la barra superior no
       lleva buscador.
   - **Backend real.** ZZZZZ responde 404 «No data found for ZZZZZ» y la web lo dice como «No hay datos de ZZZZZ:
     comprueba el ticker». Un ticker válido que no está en caché se analiza (200). En el replay, el mismo caso da 404
     «HD: sin fixtures en el replay» y cae en el mismo estado de error.
   - **Precarga.** La de `bg-home.webp` sale del layout raíz y pasa a la portada de la web actual, la única que la
     usa. Va en el `<head>` igual que antes, y /v2 y /stock ya no avisan de una precarga sin usar.
   - **Tests:** `e2e/v2/carga.spec.ts`, en los 4 proyectos. El 404 del replay, un 503 y el 404 de un ticker
     inexistente sacan el estado de error en menos de 2 s, sin errores sin capturar ni el aviso de precarga. También
     prueba el plazo agotado (con el reloj de Playwright) y el reintento. En Vitest, el plazo y la cancelación. Captura:
     `capturas-e3/V4_carga_error.webp`.
8. **Pantalla de carga.** La primera versión (9d78dc3) seguía la estructura de `AnalyzeOverlay` de la web actual. El
   PM y el usuario aprobaron después una maqueta propia con un ritmo nuevo, y es la que queda.
   - **Composición, centrada bajo la barra superior.**
     - El anillo con el logo y su giro lento (6 s y 9 s), con trazos finos de la marca y sin brillos.
     - «ANALIZANDO».
     - El nombre corto a 2 rem con el ticker en gris a 1,25 rem; sin nombre, solo el ticker.
     - Una tarjeta de 520 px como máximo: la estación en negrita (1,125 rem) con «Paso N de 5», la frase de lo que
       se hace (1 rem), la barra de cinco tramos (6 px) y sus etiquetas (0,8125 rem; 0,75 rem en el móvil, a dos
       líneas si hace falta).
     - Un pie con lo que suele tardar.
     - Claro y oscuro con los tokens de la v4. Al cambiar de estación, el título y la frase hacen un fundido de
       0,18 s.
   - **Nombre corto.** Es la regla del cintillo (P8, `names.company`). Sus datos de `names.toml` se generan en
     `backendConfig.ts` y `src/v2/lib/companyName.ts` los aplica. `companyName.test.ts` comprueba que da lo mismo que
     el backend en las muestras que el backend calcula al generar.
   - **Ritmo** (`src/v2/lib/loadingPace.ts`, puro, con Vitest). Las cinco estaciones duran lo mismo:
     - `d = T_est / 5`, con cada tramo llenándose de forma lineal.
     - `T_est` = `data.toml [web] loading_expected_s` = 4,12 s. Es el p95 de un análisis sin caché medido con
       fuentes reales en V2 (`verificacion/V2_api_frio.json`: backend real en local con Yahoo, SEC EDGAR y Finnhub,
       43 empresas; p50 2,44 s, p75 3,22 s, p95 4,12 s). Primero era el p75; el PM pidió el p95, para que la espera
       en la última estación solo le toque al 5 % más lento. Son medidas en local: se recalibra en Render (E6).
     - **Si llega antes,** la estación en curso termina en 180 ms, o en lo que le quedaba si es menos, y las que
       faltan duran 180 ms cada una.
     - **Si tarda más,** la quinta se llena a su ritmo hasta el 95 % y espera ahí con «Últimos ajustes…», hasta que
       llegan los datos o hasta el tiempo agotado (estado de error).
     - **Sin reestimación.** La versión con `max(T_est, transcurrido × 1,25)` no podía actuar antes de la última (al
       entrar en la quinta han pasado 0,8·T, y 0,8·T × 1,25 = T). El PM la quitó, junto con `loading_growth`.
   - **Pie.** «Suele tardar entre 2 y 5 segundos la primera vez; después, al instante.» Son el p50 y el p95 de la
     misma medida, redondeados hacia fuera, con las cifras en config.
   - **Igual que antes.**
     - Con caché (menos de 300 ms) no aparece.
     - Un error sale enseguida.
     - Al terminar hay una pausa de 0,32 s y una disolución de 0,62 s, y la página se monta después: una sola capa.
     - `role="status"` con la estación y «Paso N de 5».
     - Con «reducir movimiento», nada gira ni se funde, y las estaciones cambian a saltos, sin llenado.
     - Todo en rem, con 12 px como mínimo.
   - **Foco.** El panel de un «?» recibe el foco en el mismo render en que se abre. Con carga, el Tab de la prueba F8
     en el móvil llegaba antes y salía de la hoja.
   - **Tests.**
     - `loadingPace.test.ts`: datos a 0,5·T (las que faltan, 180 ms), a T (cada una d ± 1 fotograma), a 1,5·T (cuatro
       de d; en la quinta, d hasta el 95 % y la espera), una estación que empieza tarde sigue durando d, el llenado
       lineal y que la barra no salta.
     - `carga.spec.ts`: la composición, el nombre corto, 12 px, 520 px y los 16 px del móvil, el ritmo medido con el
       replay retenido (cambios de estación cada d ± 120 ms y la espera del 95 % con «Últimos ajustes…»), la caché
       sin pantalla, reducir movimiento, el error con la pantalla a la vista y el buscador con el nombre corto.
     - Capturas: `V4_carga_escritorio.webp`, `V4_carga_oscuro.webp` y `V4_carga_movil.webp`.
9. **«motor» fuera de /v2 y del PDF nuevo** (PM). Solo en los textos que ve el lector de /v2 y del PDF nuevo; la web
   actual no se toca.
   - **/v2.**
     - «Estados anuales del motor» → «Estados anuales». No dice «(SEC)», como proponía el PM, porque los estados salen
       de Yahoo (`data_provenance.path`: `plan_b_yfinance`) y EDGAR solo los verifica; en BCS van convertidos desde
       libras.
     - «Advertencias del motor» → «Advertencias del análisis».
     - Los rivales: «calidad y precio de Finanzer» (con «con análisis de Finanzer» la nota pasaba a dos líneas y el
       ajuste del capítulo quitaba un rival), «Rivales propuestos por Finanzer…; cada uno con su análisis de
       Finanzer» y «Finanzer no pudo analizarla».
     - En el resto, «el análisis»: escenarios, Riesgos, Conclusión, Actualidad y la nota de Negocio. El rótulo de los
       escenarios dice «lo calcula Finanzer con tus supuestos».
   - **PDF nuevo.** La columna del desglose, «Lectura del motor» → «Lectura del análisis». En el golden solo cambia esa
     cabecera (90 líneas en 36 PDF). La metodología conserva «Rangos de referencia del motor», porque allí se explica
     cómo funciona.
   - **Reglas.**
     - `npm run check` (`scripts/check-v2-wording.mjs`): recorre el código de /v2 sin comentarios. La portada
       (`src/v2/home`, «Analizada por el motor»…) queda como pendiente de P8b.
     - e2e `vocabulario.spec.ts`: el texto visible de la historia y de las 9 páginas de AAPL, JPM y PLTR, sin la
       metodología.
     - `paneles.spec.ts`: el texto de cada «?» abierto.
     - Backend, `test_pdf_v2_guardian.py`: el PDF nuevo de los 36 del panel fuera de METODOLOGÍA–ANEXO, con una
       prueba de que la regla ve el caso.
     - No cuentan «Motor» con mayúscula (Toyota Motor, Motor Vehicles) ni «motor de creación de valor» (otro sentido,
       en una alerta del backend que también lee la web actual).
10. **«El DCF directo y los múltiplos coinciden»** (PM: «nombra siempre de qué DCF se habla»). El cambio está en el
    origen, `verdict.confidence_phrase`: «el DCF» → «el DCF directo». El inverso ya se nombraba así.
    - **Golden.** Cambian 41 archivos, y solo en ese texto, comprobado por script: `verdict.confidence_text` y `full`,
      `display.confidence.verdict_text`, `display.cover.verdict` y la línea del resumen que lo cita, en 12 empresas
      del panel y 2 locales, más el texto de los dos PDF.
    - **Maquetación.** Con la frase más larga, en NVDA el texto pasa una línea a la página siguiente, con las mismas
      22 páginas. En la portada de KO y de PG la tarjeta de confianza ocupa dos líneas y la gráfica de precio queda un
      poco más baja, con un tramo menos en el eje. No se pierde nada.
    - **La web actual** también lo dice así, porque el veredicto es del backend.
    - **Tests:** `test_confidence_row_is_the_engine_summary[KO]`, y los de `confidence_phrase` actualizados.
11. **V6b: hallazgos de la revisión de código y seguridad del delta final** (E4,
    `verificacion/V6b_delta_final.md`). Los de E3, con el arreglo que propone el informe y su test.
    - **E1, MEDIO, «?» en escritorio.**
      - Tab o Shift+Tab en el borde del panel lo cierra y devuelve el foco al «?».
      - El panel se cierra cuando el foco se va fuera de él y de su «?» (`focusout`).
      - Escape y Tab solo cuentan con el foco en el panel o en su «?».
      - Abrir otro «?» cierra el anterior.
      - Pruebas: e2e `v6b.spec.ts` y F8 de `v6.spec` actualizado.
    - **E2, MEDIO.** El gesto de cerrar la hoja solo empieza con la hoja arriba del todo (`scrollTop` 0). Prueba:
      Vitest `v6b.test.tsx`.
    - **E3.** Al cerrar la hoja de un «?» con el gesto, el foco vuelve al «?». Prueba: Vitest.
    - **E4.** Hoja o panel lo decide quien abre (prop `sheet` de `Floating`), no la media query en cada render.
      Prueba: Vitest.
    - **E5.** El desglose que sale al pasar el ratón se cierra con Escape aunque el foco esté fuera. Prueba: e2e.
    - **E6.** En el móvil, la tarjeta se abre con su botón «Ver detalle: …» (`aria-expanded`, `aria-controls`):
      cubre la tarjeta, sin ocupar fila de la rejilla, y los «?» quedan encima. La tarjeta ya no es enfocable en el
      móvil, y al cerrar la hoja el foco vuelve a ese botón. Pruebas: e2e y F8 actualizado.
    - **E7.** El sondeo de rivales tiene tope, `data.toml [web] peers_poll_max_s` = 600 s; en V2, completarlos tardó
      p95 128 s. Se pausa con la pestaña oculta. Pasado el tope, lo dice. Prueba: e2e con el reloj de Playwright.
    - **E8.** «Bajan en el último ejercicio» lleva el rango solo con `prev_fy`. Prueba: Vitest.
    - **E9.** `Object.hasOwn` en las excepciones de nombres. Prueba: Vitest («constructor», «__proto__»).
    - **E10.** El estado del puntero de la tarjeta va en una sola actualización (y ninguna si nada cambia), y
      `onClose` está memorizado.
    - **E11.** La portada pide `/api/v2/trending?period=` solo del periodo que enseña, cosa que E4 dejó hecha en el
      backend. Lo de otros periodos se conserva (`mergeTrending`) y F16 intercepta `**/api/v2/trending*`. Pruebas:
      Vitest y e2e.
12. **SHEL, «Riesgos» en la historia** (e2e:v1: «el visual se estira 111px»).
    - **Causa.** El ajuste del capítulo quitaba la fila larga de solidez porque el visual pasaba al texto en unos 16 px
      (un hueco admisible). Con una sola fila, el texto le sacaba 112 px y superaba lo que el visual puede estirarse
      (96).
    - **Arreglo en origen** (`fit.shouldUndoTrim`, `Chapter`): si un recorte pasa de un hueco admisible (≤ 48 px) a un
      estiramiento mayor de 96 px, se deshace y el ajuste termina.
    - **Pruebas:** Vitest en `fit.test.ts`; la simetría de SHEL en claro y oscuro, en verde.
- **Pendiente:** la fusión de `rediseno/e4-portada` y la pasada final del cierre esperan al aviso de E4
  (M1–M7 y GZip).

## Pendiente / para el PM

- Aprobar el golden de E3 (solo `scenario_inputs`, `GOLDEN_DIFF_E3.md`) y las 4 excepciones de «nada se pierde».
- Los rivales en el PDF nuevo esperaban la caché compartida de E4, que ya está en la v4 con esta fusión: falta conectarlos.
- Si E2a añade commits después de 9380a8c, volver a fusionar y repetir `npm run check`, `diff_golden` y la suite e2e.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
