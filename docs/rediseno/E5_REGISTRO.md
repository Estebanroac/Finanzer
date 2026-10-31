# E5 · PDF rediseñado: registro

*2026-10-17 · operador de E5. Plan: `docs/superpowers/plans/2026-10-18-rediseno-e5-pdf.md`; spec §3.7 y §5; maqueta 5.*

## Estado

| Task | Estado | Commit |
|---|---|---|
| 0 · Rama | Hecha, con un desvío (ver abajo) | `7aa43f3` (merge de `main`) |
| 1 · Base del documento | Hecha | `95fc748` |
| 2 · Componentes de dibujo | Hecha | `0e61ef7` |
| 3 · Portada, índice y resumen | Hecha | `44b6e67` |
| Retoques del PM (1–4) | Hechos | `793c075` (+ composición en `c72fa96`) |
| 4 · Los nueve capítulos | Hecha | `c72fa96` |
| 5 · Metodología y anexo | Hecha (mismo commit que la Task 4, ver desviación 1) | `c72fa96` |
| 6 · Pruebas completas | Hecha | `39e42ad` |
| 7 · Endpoint | Hecha. **El botón de `/v2` no se ha tocado**: se cablea tras la fusión | `4f82746` |
| Revisión del PM (datos ausentes en una línea, «— —») | Hecha | commit de esta sección |

Sin push, sin merge a `main` y sin deploy. `lib/pdf_report.py` y los golden existentes no se han tocado:
`tests/diff_golden.py --env panel` y `--env local` dan «sin diferencias».

## Qué hay

- **`backend/lib/pdf_v2/`**: módulo nuevo. La web actual y su PDF siguen igual.
  - `theme.py`: tokens claros de §5.
  - `doc.py`: plantillas, índice enlazado, marcadores, «↑ índice», «Página x de y», `Stack` y `FloatGroup`.
  - `parts.py`: escalas, tarjetas, tablas técnicas, gráficas, Piotroski, segmentos y 10 años.
  - `cover.py`: portada, índice y resumen.
  - `chapters.py`: los 9 capítulos, con los mismos títulos y el mismo orden que `story.ts`.
  - `methodology.py`: metodología y anexo.
  - `definitions.py`: significado de cada métrica.
  - `report.py`: `build_pdf(analysis, prices=None, segments=None, peers=None, today=None) -> bytes`.
- **Capítulos (Task 4)**: cada uno abre con su eyebrow, su título y la lectura del motor.
  - **Empresa**: ficha (de `extended.company_profile` o, si falta, de Yahoo con su motivo), cifras clave, clasificación y descripción.
  - **Negocio**: segmentos, 10 años, márgenes y cifras del ejercicio.
  - **Acción**: gráfica de 5 años con la empresa, el S&P 500 y el ETF, rentabilidad por periodo, rango de 52 semanas y señales.
  - **Calidad**: categorías, tablas técnicas con significado, balance y autonomía, modelos, Piotroski y desglose.
  - **Valor**: DCF inverso, múltiplos, valor intrínseco, supuestos y WACC, y la rejilla de sensibilidad.
  - **Rivales**: los rivales en caché o «Rivales: consulta la web…».
  - **Riesgos**: premortem, alertas y confianza.
  - **Actualidad**: noticias con enlace `https` (avisa si están en inglés), próximos resultados y PEAD.
  - **Conclusión**: composición de las dos puntuaciones y «Qué vigilar».
- **Metodología (Task 5)**:
  - Fuentes con enlace: SEC EDGAR (la página del emisor por CIK), Yahoo Finance, Finnhub y A. Damodaran.
  - El periodo de cada dato.
  - Cómo se calculan las dos puntuaciones y la confianza, con las bandas leídas de `thresholds.toml` y no escritas a mano.
  - Modelos y referencias, y el aviso legal.
- **Anexo**: el detalle técnico del motor y «Rangos de referencia del motor para esta empresa». Este segundo bloque recoge las bandas de cada métrica más su definición.
- **Endpoint (Task 7)**: `GET /api/v2/pdf/{symbol}?sector=` en `backend/main.py`.
  - Usa el mismo semáforo `_ANALYSIS_SLOTS` y el mismo manejo de errores que `/api/pdf`.
  - La serie viene de `_prices_v2_payload`, la función que ya sirve `/api/v2/prices`, sacada a una función propia.
  - Si la serie falla, el informe sale igual y la gráfica dice «la serie de precios no respondió».
  - Nombre del archivo: `Informe Finanzer {TICKER} {AAAA-MM-DD}.pdf`.
  - Probado en `test_pdf_v2_endpoint.py` (3 casos) y en vivo con `tests/replay_server.py` en el puerto 8793: 200, nombre correcto y gráfica con serie.
- **Panel (36 empresas)**:
  - 16–21 páginas por informe.
  - 131–152 KB por informe.
  - Como mucho 0.28 s por informe.
  - Memoria pico ≤ 150 MB.

## Retoques del PM

1. **Nada truncado con «…»**. Ninguna parte recorta un dato: los rótulos y valores largos se parten en líneas y las celdas crecen.
   - `test_pdf_v2_panel.py` falla si aparece «…» en el PDF fuera del texto que ya trae el motor.
   - Los rótulos de estado («No aplica», «Sin dato», «Sin referencia») salen del estado del motor (`display.STATE_LABELS`). Antes las filas de un REIT decían «Sin dato» donde el motor dice «No aplica».
2. **Huecos de la página 2 y de todo el panel**. Se resuelve componiendo, sin estirar nada (`doc.py`). Los límites viven en `config/pdf.toml`, y `pdf_geometry.gaps()` los comprueba en los 36 informes, midiendo todo lo pintado con pdfium.
   - `FloatGroup`: un bloque visual que no cabe pasa a la página siguiente y el texto que lo sigue sube a llenar la página, como una figura flotante en un libro. El orden de lectura se conserva dentro del texto; la figura puede quedar unas líneas más abajo de donde se cita.
   - `Stack`: mantiene juntos un subtítulo y su bloque. Se parte entre elementos, o dentro de una tabla si cada parte conserva al menos 3 filas. Nunca deja un título solo.
   - Un título se lleva siempre consigo 2 líneas de lectura (`keep_lines_after_title`).
   - Máximos medidos en el panel: 102 pt al pie (límite 106, ver desviación 3) y 36 pt entre bloques (límite 48).
3. **Significado bajo cada métrica**. Lo produce un script, `backend/tools/gen_metric_definitions.py`: un lector estricto del objeto `DEFINITIONS` de `frontend/src/lib/tooltips.ts` que genera `backend/assets/metric_definitions.json` (68 claves).
   - **Por qué es lo robusto**:
     - El texto se escribe una sola vez, en el frontend.
     - El PDF no depende de Node ni del frontend al ejecutarse.
     - El lector solo acepta el subconjunto que usa el `.ts`: claves, objetos y cadenas unidas con `+`. Cualquier otra cosa (plantillas, variables) es un error explícito, nunca un dato perdido.
     - `test_metric_definitions.py` falla si el JSON se desincroniza del `.ts` (equivale a `--check`) o si el lector deja de entenderlo.
   - El PDF usa la primera frase (`definitions.meaning`) bajo la métrica y la definición completa en el anexo.
4. **Texto del motor «ejercicios.; en la frontera…» (KO)**: **pendiente en origen**, no se parchea en el PDF. Es la nota de calidad de `display`, que E2a ya cambia. La prueba de elipsis y el golden lo tratan como texto del motor.

## Revisión del PM: un bloque sin dato no reserva su caja

El plan decía, en la Task 2, que la parte ausente «mide lo mismo». Se ha corregido en el plan: **la ausente dice su motivo en una línea** (título del bloque y motivo en texto secundario) y lo que sigue sube a ocupar el sitio.

- **`parts.py`**: `missing_line(title, reason)`. Todas las partes de dibujo sin dato se reducen a esa línea en lugar de una caja gris:
  - `SegmentBars`, `History10`, `PriceChart`, `Range52`, `Piotroski` y `CategoryBars`;
  - `History10` con menos años mide lo que miden sus filas;
  - `SegmentBars` ya no tiene alto mínimo.
- **Capítulos**: un bloque sin dato no lleva subtítulo más caja. Es una sola línea:
  - «Ingresos por segmento · sin desglose oficial: …»;
  - «Historia de 10 ejercicios · sin dato: …»;
  - «Precio en 5 años · gráfica no disponible: …» y «Rentabilidad por periodo · sin dato: …»;
  - «Rivales de la misma industria · consulta la web: …»;
  - «Noticias · sin noticias recientes: …» y «Próximos resultados · sin fecha anunciada: …»;
  - la ficha EDGAR ausente usa el respaldo de Yahoo solo con los campos que hay, sin filas «Sin dato»; si no hay ninguno, una línea.
- **Variación del día**: ya era una línea de texto secundario junto al precio, sin caja reservada. No cambia.
- **Portada sin serie de precios**: la gráfica es una línea, y el contexto del precio lo da el rango de 52 semanas del motor, que no depende de la serie. Así la portada no acaba en hueco (MC.PA del panel: 148 pt → dentro del límite).
- **Composición**:
  - Si nada de lo que sigue a un bloque visual cabe al pie, el bloque se parte entre sus piezas antes que dejar el hueco, y nunca deja un título solo (`FloatGroup`).
  - El rótulo de un grupo de alertas («Fortalezas»…) no queda solo al pie.
- **Tabla de múltiplos sin referencia**: una sola raya en Brecha (más la de Referencia) y la Lectura vacía. La pastilla solo sale cuando el motor da una lectura. Lo mismo en la tabla de tres columnas y en la comparación con la mediana de la referencia.
- **Pruebas**:
  - `test_pdf_v2_parts.py`: la ausente ocupa una línea, y la presente, más de tres.
  - `test_pdf_v2_panel.py::test_absent_e2_blocks_take_one_line`: en los 36 del panel.
  - La tabla sin referencia tiene exactamente 2 rayas.
  - La regla de huecos pasa en las 36 empresas.

## Datos de E2 preparados

Cada interfaz acepta el dato o su ausencia. No se inventa nada.

| Dato (E2) | Dónde | Sin dato |
|---|---|---|
| `display.extended.price_change` | Portada, junto al precio | «Variación del día: sin dato — el análisis aún no trae el cierre anterior» (o su `reason`) |
| Serie de `/api/v2/prices` (`c` y el ajustado `a` de E2a) | Gráfica de 1 año (portada) y de 5 años (cap. 3) | Una línea con el motivo; en la portada, debajo, el rango de 52 semanas del motor. Con serie corta: «la serie empieza el …» |
| `display.extended.company_profile` | Ficha del cap. 1 | Ficha de Yahoo + motivo |
| `display.extended.history_10y` | `History10` (cap. 2) | Cabecera fija + años que haya + `reason` |
| `/api/v2/segments` (forma de E2b) | `SegmentBars` (cap. 2) | «Sin desglose oficial por segmento» + `reason` |
| `display.extended.piotroski_values` | Piotroski «actual frente a anterior» (cap. 4) | El detalle del motor |
| Rivales de E2b (`peers=`) | Cap. 6 | «Rivales: consulta la web…» y la comparación con la referencia de su industria |
| `display.extended.news` y `next_earnings` | Cap. 8 | Noticias de `market.news`; «Sin fecha anunciada» + motivo |

**Series de 5 años en vivo: pendientes de E2a.** Hoy el replay trae 2 años, así que la gráfica de 5 años dice «la serie empieza el …». Con el ajustado de E2a no cambia nada del PDF.

## Desviaciones y decisiones (para el PM)

1. **Tasks 4 y 5 en un solo commit (`c72fa96`)**. Comparten la composición (`doc.py`: `Stack`/`FloatGroup`), y la metodología se apoya en las mismas piezas (`heading_block`, `sub`, `link`). Separarlas dejaba un commit intermedio que no compone. Los retoques del PM sobre las partes van aparte (`793c075`).
2. **Rama**: `rediseno/v4` no existía. `rediseno/e5-pdf` sale de `rediseno/e1-sistema-historia` con `main` fusionado. El conflicto en `main.py` se resolvió conservando `/api/v2/prices` y el arranque de keepalive.
3. **Límite al pie: 106 pt** (antes 100). Es lo más que puede dejar la composición: un título de capítulo con sus 2 líneas de lectura que no cabe y pasa entero a la página siguiente. Cuenta exacta: 24 pt antes + eyebrow y título 35.5 + 8 pt después + 2 líneas de 15.23 = 98 pt, más lo que deja tras de sí lo último pintado (≤ 8 pt). El 100 salía de una cuenta aproximada (≈ 94 pt). Tras la revisión del PM, V acaba la página 17 con 102 pt: la metodología necesita 98 pt y quedan 97. Probé a calcular el corte del título con su alto exacto, pero empeoraba otras tres páginas (105 pt), así que lo descarté. Los bloques visuales no dejan ese hueco, porque los rellena el texto que les sigue.
4. **Límite entre bloques de 48 pt**. La escala de espaciado llega a 24 pt antes de un capítulo, y el panel mide 36 pt como mucho.
5. **2 líneas tras un título**: es la regla tipográfica habitual contra viudas y huérfanas.
6. **Exención del guardián para el glosario**: el guardián narrativo, aplicado al texto de `pdf_v2`, exime una palabra clave (p. ej. «dilución») cuando aparece dentro de una definición de `tooltips.ts`. Para decidirlo usa la misma prueba de vecindad que ya usa con el PDF. Una definición no afirma nada de la empresa, y en la web va en el tooltip, que el guardián tampoco lee.
7. **Portadas sin desglose compacto**: 1 de 36 (SNOW). Su portada no cabe ni con la gráfica a 100 pt, así que las escalas pierden su desglose, que repiten los capítulos 4 y 5. No encoge (la prueba lo prohíbe).
8. Siguen vigentes las desviaciones aprobadas de las Tasks 1–3: notas de las puntuaciones al resumen, base fija, β/σ en Symbol, cifras alineadas a la derecha y «↑ índice» al pie.
9. **El golden de texto de `pdf_v2`** (`tests/golden/panel_pdf_v2/`, 36 archivos) es nuevo y aparte del golden del PDF actual, que no cambia. Se regenera con `tests/pdf_v2_golden.py --regenerate` cuando un cambio del PDF nuevo es intencionado.

## Pruebas

- **pdf_v2** (`tests/test_pdf_v2_*.py` + `test_metric_definitions.py`): **348 en verde** (~43 s). Cubren:
  - Geometría y huecos con `config/pdf.toml` en los 36 del panel.
  - Letra ≥ 8 pt y portada a escala 1.0.
  - ≥ 4 enlaces `https` externos y 14 marcadores.
  - Peso, tiempo y memoria.
  - Golden de texto.
  - Ausencia de «…».
  - Contenido: cada token con cifra del PDF actual está en el nuevo, en 8 tickers. Las únicas excepciones son los números de sección 01–07.
  - Guardián.
  - Definiciones.
  - Endpoint.
- **Suite completa** (`cd backend/tests && pytest -q`): **4520 passed, 4 skipped**. Los 4 saltados son de contrato del frontend, por falta de Node o de `node_modules`.
- **`tests/diff_golden.py --env panel` y `--env local`**: «sin diferencias».

## Capturas

`docs/rediseno/capturas-e5/` contiene todas las páginas, generadas con `pypdfium2` a 2× (71 PNG, regeneradas tras la revisión del PM):

- AAPL: `AAPL-p1..p20.png` (20 páginas)
- JPM: `JPM-p1..p17.png` (17 páginas)
- O: `O-p1..p17.png` (17 páginas)
- BCS: `BCS-p1..p17.png` (17 páginas)

Se regeneran con:

```
cd backend && ../.venv313/bin/python tests/pdf_v2_capturas.py AAPL JPM O BCS
```

## Qué queda para después de la fusión (E2a + E2b en `rediseno/v4`)

- Cablear el botón de `/v2` a `/api/v2/pdf/{symbol}`.
- Comprobar con datos reales de E2: `extended`, segmentos, rivales y las series de 5 años con ajustado. Las interfaces ya están probadas con dato y sin él.
- Regenerar el golden de `pdf_v2` y las capturas.
- Motor (en origen, no en el PDF): la nota de KO «ejercicios.; en la frontera…».

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
