# Diff de los golden · V4 · moneda en el formato del motor

*Sesión E4, 18-oct-2026. Rama `rediseno/e4-portada`. **Aprobado por el PM por delegación del usuario (ver
«Aprobación»).** Golden regenerado en el commit de esta causa.*

## Resumen en lenguaje llano

- **Qué pasaba.** Lo encontró E3: en MC.PA (cotiza en euros), el motor escribía con «$» importes que están en euros:
  precio, capitalización, variación del día, KPI, cifras de los estados y valor razonable. La cabecera de `/v2` ya
  decía «EUR 397.00», pero los textos del motor (web actual, `/v2` y los dos PDF) no.
- **Arreglo en origen.** `lib/numfmt` formatea con la moneda de la cifra. En el análisis, esa moneda es la del precio,
  que también es la de los estados: se convierten a ella cuando difieren. La historia de 10 años de EDGAR conserva la
  moneda de sus estados («GBP 41.27B», como ya hacía). En USD se escribe «$»; en otra moneda, su código delante, como
  la cabecera de `/v2`: «EUR 397.00», «−EUR 1.10», «EUR 195.71B».
- **Unificado también:** la capitalización de los resúmenes de rivales y tarjetas pasa de «195.71B EUR» a «EUR 195.71B».
- **Ninguna cifra ni veredicto cambia.** Solo cambia el símbolo de la moneda, y solo en el emisor que no cotiza en USD.

## Por causa

| Causa | Tickers | Campos | Líneas PDF actual (±) | Líneas PDF nuevo (±) | Cambios de veredicto |
|---|---|---|---|---|---|
| Moneda de los importes del motor (`numfmt` con la moneda del precio) | panel: 1 de 37 (MC.PA) · local: 0 de 6 | 85 (MC.PA) | 45 (MC.PA) | 17 (MC.PA) | 0 |

**Auditor automático.** Normaliza solo esta causa (`«$» → «EUR »`) y compara:
- **Campos:** de los 85, los 85 quedan iguales tras normalizar.
- **PDF actual:** 43 de las 45 líneas quedan iguales tras normalizar. Las otras 2 son un salto de línea: con «EUR» la
  frase de la deuda («deuda EUR 36.73B; sin desglose oficial de arrendamientos…») ocupa más y «(EDGAR no» pasa a la
  línea siguiente. El texto unido es el mismo.
- **PDF nuevo:** las 17 líneas quedan iguales tras normalizar.

**0 diferencias sin explicar.**

**Emisores no USD revisados.**
- ASML, BCS, NVO, TM, TSM y UL cotizan en USD y sus estados se convierten a USD: su «$» ya era correcto y no cambian.
- MC.PA es el único emisor del panel y del juego local cuyo precio no está en USD.

**Campos de MC.PA que cambian** (los 85):
- portada: KPI de precio y capitalización;
- tarjeta de precio y rango de 52 semanas;
- escalera de márgenes y flujo de resultados;
- estructura del balance, gráfica histórica y valores de Piotroski;
- valor razonable, extremos de la rejilla, celdas de la tabla de sensibilidad y su nota;
- filas del valor intrínseco, figuras de rentabilidad, variación del día y la línea del anexo sobre la deuda.

## Cambios de veredicto: 0

Comprobado sobre la salida actual frente a los golden, en los 43 golden (37 del panel y 6 del juego local), campo a
campo, con 0 diferencias:
- `quality.score` y `quality.level`;
- `price_attractiveness.{score, score_raw, level}`;
- `confidence.level`, `verdict.text` y `verdict.confidence`;
- `score.total`, `piotroski_f.score`, `altman_z.z_score` y `dcf.fair_value`;
- `classification.archetype`.

## Web y PDF actuales

- **`/stock/MC.PA`** (servida por el backend con el replay del panel): ningún «$» en la página. Salen en EUR el precio,
  la capitalización, el rango de 52 semanas, el valor razonable y la rejilla («EUR 210 – EUR 872»).
- **PDF actual de MC.PA:** ninguna línea con «$» (44 con «EUR»).
- **Web actual de AAPL y portada:** idénticas píxel a píxel a main (`legado:comparar`, escritorio y móvil).

## Tests

- `tests/test_numfmt_moneda.py`:
  - USD sin cambios;
  - «EUR …» con la moneda del contexto, y la moneda explícita mandando sobre ella (estados en GBP);
  - el análisis no deja su moneda en el hilo, aunque falle (la cola formatea después otros resúmenes);
  - la capitalización de la cola, en el mismo estilo.
- `test_peers.py`: la capitalización de MC.PA empieza por «EUR ».

## Aprobación

Aprobado por el PM (sesión planificadora) por delegación del usuario, 2026-10-18. Literal del PM: «El golden cambia
**solo en el formato de moneda** de los emisores no USD (MC.PA; revisa si hay más en panel y local). Escribe
`docs/fiabilidad/GOLDEN_DIFF_V4_MONEDA.md` con la convención de siempre, con 0 cambios de veredicto (compruébalo como
en E2a). Lo apruebo yo por delegación, así que regenera el golden con esa causa.»
