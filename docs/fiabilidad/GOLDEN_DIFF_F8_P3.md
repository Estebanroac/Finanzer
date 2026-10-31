# GOLDEN_DIFF · F8 P3 (presentación)

P3 no cambia ningún veredicto, ninguna puntuación ni la confianza. Aquí van los cambios de golden de cada punto, con
su causa. Evidencia y arreglo: `F8_P3_REGISTRO.md`.

## 1 · ROE no significativo con patrimonio ≤ 0

Ningún golden cambia: ninguna empresa del panel ni del juego local tiene patrimonio ≤ 0. Verificado en vivo con MCD.

## 2 · Valor justo redondeado, rango del bloque central y margen de seguridad

Cambia solo la presentación (`display`) de los golden con DCF: panel AAPL, ASML, CAT, CRWD, DOW, FCX, JNJ, KO, MC.PA,
MSFT, MU, NFLX, NVDA, NVO, PG, PLTR, SHEL, TSM, UL, V y XOM; local FCX, NFLX y V. Comprobado que el diff no toca nada
fuera de `display`: ni valor, ni upside, ni puntuación, ni confianza, ni veredicto.

| Cambio | Ejemplo |
|---|---|
| Valor justo a dos cifras significativas (fila, gráfico y frases que lo citan) | AAPL $116.08 → $120; KO $63.52 → $64 |
| Rango del bloque central de la tabla, declarado (texto de la fila y gráfico) | AAPL «rango $88–$160 … (mínimo y máximo, no un p10–p90)» |
| Margen de seguridad a la unidad | AAPL −195.45% → −195% |
| Margen de seguridad «No significativo» con DCF de fiabilidad baja | CAT −193.69% y DOW −309.40% → «No significativo» con el motivo |

**Causa:** auditoría P3. Un margen con dos decimales sobre un DCF que el informe declara no fiable, y un valor justo al
céntimo, transmiten una precisión que el modelo no tiene.

## 3 · Una sola ventana de fuerza relativa (1 año, la regla de la tabla de rentabilidades)

Cambian `market_context.relative_strength` y su presentación (`display`) en los golden con ETF de sector. Son 35 del
panel y 6 del juego local, más 4 muestras forzadas, en el JSON y en el texto del PDF. Comprobado que el diff no toca nada
fuera de `market_context` y `display`: ni puntuación, ni confianza, ni veredicto.

| Cambio | Ejemplo (panel, 14-oct-2026) |
|---|---|
| Ventanas «6M» y «1A» por días naturales en lugar de 126 y 252 sesiones | `params.windows_sessions [126, 252]` → `params.windows ["6M", "1A"]` |
| La ventana de 1 año empieza el mismo día que la de la tabla | MSFT: inicio 2025-10-13 → 2025-10-14; +4,7 % frente a +34,2 % → +4,8 % frente a +36,0 % |
| Etiqueta de la tabla | «… (12 meses)» → «… (1 año)» |

La ventana de 6 meses ya coincidía (182 días naturales y 126 sesiones dan el mismo inicio en estos datos).

**Causa:** auditoría P3. Dos cifras distintas, las dos «a 12 meses», para la misma comparación.

## 4 · Nota del Piotroski condicionada al dato de la empresa

Cambian `business_model.piotroski_caveat` y el texto de la tarjeta del Piotroski (`display`, JSON y PDF). Afecta a
panel AMZN, CRWD, KO, MSFT, PG, PLTR, SNOW y UL, al juego local SNOW y a las 3 muestras forzadas de SNOW. Comprobado que
el diff no toca nada más: ni puntuación, ni confianza, ni veredicto.

| Cambio | Empresas |
|---|---|
| La nota desaparece: su current ratio no la justifica | AMZN 1,18x, CRWD 1,57x, KO 1,30x, MSFT 1,23x, PLTR 7,23x; SNOW 0,94x, que empeora frente a su historia |
| La nota cita su dato y se quita la frase genérica de los márgenes | PG 0,68x, UL 0,79x |

En el PDF v2 de CRWD, al acortarse el texto, el informe pasa de 22 a 21 páginas (solo cambian los números de página
del índice y de los pies).

**Causa:** auditoría P3. La nota afirmaba un capital circulante negativo en empresas con current ratio > 1.

## 5 · Etiquetas coherentes: β de CB y crecimiento de MRNA

- **β:** cambia el texto del motivo del P/B y del P/TBV justificados en panel BRK-B y PGR, las dos con beta de su
  industria. Va en el JSON (`score.breakdown.Valoración.adjustments[].reason` y `details[]`, y en `display`, que los
  cita) y en el texto de los dos PDF: «β ajustada 0.48» → «β de la industria 0.48, sin Blume»; BRK-B, 0,67. Los
  ajustes, los puntos y la beta no cambian.
- **Puntuación por categoría:** campo nuevo `score_txt` en las categorías de la portada y del desglose de todos los
  golden («12 / 20» o «no concluyente»). En la muestra forzada `SNOW_no_concluyente`, el tono de la categoría no
  concluyente del desglose pasa a neutro. Ningún golden del panel tiene una categoría no concluyente, así que ningún
  PDF cambia por esto. Verificado en vivo con MRNA.

Comprobado que el diff no toca ninguna puntuación, ajuste, confianza ni veredicto.

**Causa:** auditoría P3. Etiquetas que se contradecían dentro del mismo informe.

## 6 · Clasificación del anexo: una sola etiqueta y frases completas

Cambia el anexo técnico de panel HSBC y RIVN, las dos únicas con avisos de clasificación, en el JSON y en el texto de
los dos PDF: dos entradas «Clasificación» pasan a una con frases completas. En el PDF nuevo de HSBC, el resto del anexo
se recoloca. Nada más cambia.

**Causa:** repaso de redacción de E2b (etiqueta repetida y frase en minúscula).
