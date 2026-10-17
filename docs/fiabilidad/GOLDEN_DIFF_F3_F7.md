# Diff de los golden, causa por causa (de la fase 3 a la 7)

> Golden anteriores: `d0ab47c` (F3 T1b, parada 1b). Regenerados con el código de `354e7eb`, con la aprobación del
> usuario (2026-10-17: "Apruebo regenerar los golden del panel y local y las muestras forzadas del contrato, con el
> diff explicado causa por causa").

## Cómo se atribuye

- Se pasó el motor (juegos panel y local, análisis normalizado y texto del PDF) por cada uno de los 85 commits que tocan código, configuración o fixtures desde `d0ab47c`, uno detrás de otro.
- Cada diferencia se atribuye al commit que la introduce. La regla del plan es un commit por causa.
- En el commit base, el resultado coincide con los golden en los 43 tickers (0 diferencias). Así se valida el método.
- 51 commits cambian la salida; los otros 34 no la tocan (herramientas, tests y textos fuera del informe).
- Columnas:
  - **Tickers:** los que cambian en algún campo;
  - **Campos:** valores del JSON que cambian;
  - **Líneas PDF:** líneas del texto del informe añadidas o quitadas;
  - **Cambios de veredicto:** niveles de calidad y precio (con la puntuación), confianza y arquetipo.
- La explicación de cada causa está en el documento de su fase:
  - F3: F3_T2_PARADA2, F3_T7_PARADA3 y RECON §7.22;
  - F4: F4_PARADA;
  - F5: F5_PARADA;
  - F6: F6_PARADA;
  - F7: F7_CALIBRACION y registro #36.

## Por commit

| Commit | Causa | Tickers | Campos | Líneas PDF | Cambios de veredicto |
|---|---|---|---|---|---|
| `dc62a83` | F3: historia de EDGAR con operaciones discontinuadas e ingresos de contratos con clientes (T2) | 35 | 410 | 0 | — |
| `b07983c` | F3: historia por acción de EDGAR ajustada por splits y sin errores de escala (T2) | 6 | 23 | 0 | — |
| `9ea8193` | F3: clasificador por la historia real: ciclicidad, crecimiento rentable y subtipos financieros (T2, D4) | 36 | 3447 | 1479 | CAT (panel) confianza media → baja<br>CAT (panel) arquetipo MATURE → CYCLICAL<br>KO (panel) precio muy exigente → exigente (25 → 35)<br>KO (panel) confianza alta → media<br>KO (panel) arquetipo MATURE → CYCLICAL<br>MSFT (panel) arquetipo MATURE → GROWTH_PROFITABLE<br>NVDA (panel) arquetipo MATURE → GROWTH_PROFITABLE<br>NVO (panel) confianza alta → media<br>NVO (panel) arquetipo MATURE → GROWTH_PROFITABLE<br>TM (panel) calidad media → sólida (61 → 67)<br>TM (panel) precio atractivo → razonable (65 → 61)<br>TM (panel) arquetipo CYCLICAL → MATURE<br>TSM (panel) arquetipo MATURE → GROWTH_PROFITABLE |
| `0ca5937` | F3: nota de crecimiento estructural en las cíclicas que también crecen con beneficio (T2, §1.1 paso 6) | 8 | 81 | 9 | — |
| `ddd7796` | F3: motivo concreto de la confianza baja de la clasificación: frontera o ciclicidad sin medir (T2) | 36 | 221 | 133 | NFLX (panel) confianza alta → media<br>TM (panel) confianza media → baja |
| `4516eae` | F3: la serie por acción se corta en las rupturas del capital (T2) | 21 | 68 | 20 | PLTR (panel) arquetipo MATURE → GROWTH_PROFITABLE |
| `0f121bc` | F3: alerta de posible cíclica medida con la historia en FINANCIAL, REIT y UTILITY (T2) | 1 | 31 | 12 | — |
| `9e76d50` | F3: split entre taxonomías en la historia del BPA (T2) | 1 | 1 | 0 | — |
| `0fe8ef0` | F3: un episodio de caída de ventas es ciclo solo si el margen operativo cae (apalancamiento operativo) (T2) | 3 | 885 | 390 | KO (panel) precio exigente → muy exigente (35 → 25)<br>KO (panel) confianza media → alta<br>KO (panel) arquetipo CYCLICAL → MATURE<br>TM (panel) confianza baja → media |
| `f8e5750` | F3: una sola estructura de DCF para el directo y el inverso (T3, §8.2) | 7 | 882 | 621 | NVDA (panel) confianza media → alta |
| `fa9a156` | F3: el DCF descuenta FCF − SBC siempre que haya SBC del mismo periodo (T3, §8.4) | 23 | 2331 | 1431 | V (panel) precio muy exigente → exigente (25 → 30) |
| `19def27` | F3: DCF inverso conectado con las tasas base como referencia principal (T3, D3, §2 y §8) | 36 | 2468 | 1014 | AAPL (panel) precio exigente → muy exigente (35 → 10)<br>AAPL (panel) confianza media → alta<br>ASML (panel) precio exigente → muy exigente (40 → 20)<br>ASML (panel) confianza baja → media<br>CAT (panel) precio exigente → muy exigente (40 → 20)<br>CAT (panel) confianza baja → media<br>CRWD (panel) precio exigente → muy exigente (31 → 5)<br>CRWD (panel) confianza media → alta<br>FCX (panel) precio exigente → muy exigente (42 → 28)<br>MSFT (panel) precio razonable → exigente (50 → 35)<br>MU (panel) precio exigente → muy exigente (35 → 20)<br>PLD (panel) confianza media → alta<br>PLTR (panel) precio exigente → muy exigente (35 → 10)<br>PLTR (panel) confianza media → alta<br>TSM (panel) precio razonable → exigente (54 → 39)<br>UL (panel) confianza media → alta<br>FCX (local) precio exigente → muy exigente (39 → 15)<br>FCX (local) confianza media → alta |
| `d71f0a2` | F3: la falta de un segundo método ya no contrae la confianza (T3, D3, opción 3 de RECON §7.17) | 3 | 101 | 117 | DUK (panel) confianza media → alta<br>NEE (panel) confianza media → alta<br>SNOW (panel) confianza media → alta<br>SNOW (local) confianza media → alta |
| `b120c33` | F3: el crecimiento que exige el precio, visible en la web y en el PDF y vigilado por el guardián (T3, §2.2) | 36 | 217 | 688 | — |
| `e2b4c3b` | F3: financieras: ROTE ajustado por AT1 y ROTE / ROE implícitos con banda y sensibilidad (T4, §1.4, §3, §8.8) | 6 | 495 | 236 | BAC (panel) precio razonable → exigente (46 → 42)<br>PGR (panel) precio atractivo → razonable (65 → 58) |
| `afae76a` | F3: el ROTE / ROE que descuenta el precio, visible y vigilado por el guardián (T4, §3) | 6 | 70 | 135 | — |
| `381c863` | F3: crecimiento sobre el perímetro homogéneo tras un cambio de perímetro (T5, §4) | 2 | 407 | 285 | UL (panel) confianza alta → media |
| `e353392` | F3: crecimiento de ciclo medio de pico a pico con 10+ ejercicios (T5, §4) | 7 | 1538 | 1031 | SHEL (panel) calidad media → sólida (64 → 76)<br>XOM (panel) calidad sólida → excelente (72 → 82)<br>XOM (panel) precio exigente → razonable (39 → 48)<br>XOM (panel) confianza media → baja |
| `57e8d46` | F3: con el BPA o el FCF base <= 0, Crecimiento se mide con los ingresos y no se excluye (T5, §4) | 5 | 313 | 190 | AMZN (panel) confianza media → alta |
| `afdd1d8` | F3: interanual frente a CAGR a 3 años: mezcla declarada en el DCF si difieren más de 10 pp (T5, §4) | 36 | 569 | 336 | TSM (panel) precio exigente → razonable (39 → 50) |
| `ceac134` | F3: lecturas por modelo de negocio: circulante estructural, Altman referencial y avisos del Piotroski (T6, §5) | 36 | 642 | 352 | AMZN (panel) calidad sólida → media (68 → 60)<br>UL (panel) calidad sólida → excelente (76 → 81) |
| `4ae7705` | F3: la deuda de la financiera cautiva sale de la deuda industrial (T6, §8.6) | 1 | 323 | 238 | — |
| `51201e2` | F3: lecturas de calidad que informan: DuPont, margen FCF con tendencia, regla de 40, SBC y cobertura ampliada (T6) | 30 | 1678 | 918 | — |
| `d2a6adc` | F3: PEG a 3 años en GROWTH_PROFITABLE (T6, §1.3) | 5 | 213 | 127 | — |
| `3f4be83` | F3: método intrínseco donde faltaba: flujo de mantenimiento con FCF − SBC <= 0 y P/B frente al ROE regulado en utilities (T7) | 4 | 502 | 508 | AMZN (panel) precio exigente → muy exigente (40 → 20)<br>DUK (panel) confianza alta → media<br>NEE (panel) precio razonable → exigente (50 → 42)<br>NEE (panel) confianza alta → media |
| `c8ab2fe` | F3: los CAGR por acción de la historia cuentan años de calendario, no puntos (T7, destapado en NOW) | 2 | 17 | 10 | — |
| `8a58618` | F3: financiera cautiva sin desglose estructurado (DE): se dice, no se separa (T7, revisión externa) | 1 | 1 | 3 | — |
| `6912ded` | F3: el subtipo financiero como etiqueta visible y servidor de replay para la comprobación visual (T7) | 6 | 126 | 18 | — |
| `1c3dbad` | F3: el P/E aplica a bancos y aseguradoras (T4, registro #14 y F3_DISENO §1.4) | 6 | 1510 | 574 | BAC (panel) precio exigente → razonable (42 → 46)<br>BCS (panel) precio razonable → atractivo (54 → 65)<br>HSBC (panel) precio exigente → razonable (42 → 46) |
| `9155044` | F3: el margen de intereses del banco, visible aparte de los ingresos netos que puntúan (T4, §1.4; mapa) | 4 | 215 | 123 | — |
| `784b7eb` | F3: cobertura de intereses con FFO en REIT: (FFO + intereses) / intereses (T6, petición del usuario, mapa) | 29 | 42 | 16 | — |
| `1f12e33` | F4: por encima de "excelente", la calidad exige persistencia (T1, PLAN §4.1) | 36 | 1660 | 112 | — |
| `122cbb4` | F4: la confianza responde a causas reales (T2, PLAN §4.2) | 35 | 948 | 521 | NFLX (panel) confianza media → alta<br>NVO (panel) confianza media → alta<br>FCX (local) confianza alta → media |
| `a0aa922` | F4: aviso de frontera entre niveles (T2; mapa, efecto frontera de NVO) | 36 | 136 | 111 | — |
| `6578a63` | F3: el ciclo medio no se divide dos veces por las acciones (revisión de código de la fase 3, hallazgo 1) | 2 | 18 | 32 | — |
| `583f112` | F3: los ejercicios se cuentan por la diferencia de fechas de cierre (revisión de código de la fase 3, hallazgo 2) | 1 | 7 | 2 | — |
| `9fecbf3` | F3: el tramo de tamaño de las tasas base se mide en USD (revisión de código de la fase 3, hallazgo 4) | 26 | 38 | 0 | — |
| `bc4fa89` | F4: pre-mortem en el informe, "Esta lectura sería errónea si…" (T3, PLAN §4.3) | 36 | 378 | 471 | — |
| `e5baf6e` | F4: el resumen de la confianza cita el motivo real del techo (T2) | 16 | 24 | 70 | — |
| `ea2926b` | F4: las alertas del DCF y de la cobertura usan las bandas del score (mapa, bandas paralelas) | 1 | 14 | 6 | — |
| `71b5184` | F4: deuda neta/EBITDA y beta con una sola fuente de umbrales (mapa, bandas paralelas) | 36 | 559 | 43 | — |
| `92a279e` | F4: la ventana de persistencia se ancla en el último ejercicio con dato y se completa con los estados (revisión externa, SAN) | 7 | 61 | 11 | — |
| `309ed32` | F5: contexto de mercado y lectura conductual, aparte y sin puntuar (T2–T4, PLAN §2.2–§2.3; D5) | 36 | 7278 | 1469 | — |
| `76316bf` | F5: revisión de código de la fase 5 (hallazgos 1–10) | 30 | 98 | 107 | — |
| `b586299` | F6: el anexo técnico dice qué fuente aportó cada campo | 36 | 84 | 135 | — |
| `a83fe4e` | F6: el respaldo anual de EDGAR en el anexo con el nombre del dato, no su código | 2 | 2 | 9 | — |
| `9b7bbc4` | F6: sin trimestres de Yahoo, el corte pasa al último 10-Q de EDGAR (BRK-B) | 36 | 580 | 172 | — |
| `0d86c00` | F6: valor en libros del nuevo corte y anexo sin códigos ni repeticiones (revisión F6, hallazgos 3, 4 y 9) | 36 | 54 | 122 | — |
| `21e8341` | F7: REIT: FFO / activos totales sustituye a FFO / patrimonio contable (decisión del usuario) | 3 | 180 | 181 | O (panel) calidad sólida → media (70 → 59)<br>PLD (panel) calidad excelente → sólida (85 → 79)<br>O (local) calidad sólida → media (70 → 59) |
| `4412a49` | F7: aseguradoras y conglomerados se valoran sobre el beneficio operativo, sin las ganancias de su cartera | 2 | 183 | 136 | — |
| `354e7eb` | F7: revisión de aseguradoras y REIT (hallazgos A–K): P/E operativo coherente en todo el análisis | 36 | 331 | 291 | — |

## Resultado neto (golden anterior → nuevo)

Cambios de nivel, puntuación de calidad o precio, confianza o arquetipo entre los golden de `d0ab47c` y los nuevos:

- AAPL (panel) precio: exigente 35 → muy exigente 10
- AAPL (panel) confianza: media → alta 
- AMT (panel) calidad: sólida 79 → sólida 75
- AMZN (panel) calidad: sólida 68 → media 60
- AMZN (panel) precio: exigente 42 → muy exigente 20
- AMZN (panel) confianza: media → alta 
- ASML (panel) calidad: excelente 91 → excelente 90
- ASML (panel) precio: exigente 40 → muy exigente 20
- ASML (panel) confianza: baja → media 
- BAC (panel) calidad: sólida 71 → sólida 74
- BCS (panel) precio: razonable 58 → atractivo 65
- BRK-B (panel) precio: exigente 42 → exigente 35
- CAT (panel) calidad: excelente 88 → excelente 84
- CAT (panel) precio: exigente 42 → muy exigente 20
- CAT (panel) arquetipo: MATURE → CYCLICAL 
- CRWD (panel) calidad: media 56 → media 55
- CRWD (panel) precio: exigente 31 → muy exigente 5
- CRWD (panel) confianza: media → alta 
- DUK (panel) precio: razonable 54 → razonable 46
- FCX (panel) calidad: sólida 79 → sólida 72
- FCX (panel) precio: exigente 42 → muy exigente 28
- HSBC (panel) precio: exigente 42 → razonable 46
- KO (panel) calidad: excelente 82 → excelente 81
- MSFT (panel) precio: razonable 50 → exigente 35
- MSFT (panel) arquetipo: MATURE → GROWTH_PROFITABLE 
- MU (panel) calidad: excelente 92 → excelente 90
- MU (panel) precio: exigente 35 → muy exigente 20
- NEE (panel) precio: razonable 50 → exigente 42
- NFLX (panel) calidad: excelente 100 → excelente 93
- NVDA (panel) calidad: excelente 95 → excelente 93
- NVDA (panel) precio: razonable 54 → razonable 55
- NVDA (panel) confianza: media → alta 
- NVDA (panel) arquetipo: MATURE → GROWTH_PROFITABLE 
- NVO (panel) precio: atractivo 70 → atractivo 80
- NVO (panel) arquetipo: MATURE → GROWTH_PROFITABLE 
- O (panel) calidad: sólida 70 → media 59
- PG (panel) calidad: excelente 81 → excelente 85
- PGR (panel) calidad: excelente 84 → excelente 83
- PGR (panel) precio: atractivo 65 → razonable 61
- PLD (panel) calidad: excelente 85 → sólida 79
- PLD (panel) confianza: media → alta 
- PLTR (panel) calidad: excelente 100 → excelente 95
- PLTR (panel) precio: exigente 35 → muy exigente 10
- PLTR (panel) confianza: media → alta 
- PLTR (panel) arquetipo: MATURE → GROWTH_PROFITABLE 
- SHEL (panel) calidad: media 64 → sólida 76
- SNOW (panel) precio: muy exigente 28 → muy exigente 20
- SNOW (panel) confianza: media → alta 
- TM (panel) calidad: media 61 → sólida 70
- TM (panel) precio: atractivo 65 → razonable 54
- TM (panel) arquetipo: CYCLICAL → MATURE 
- TSM (panel) calidad: excelente 100 → excelente 99
- TSM (panel) precio: razonable 54 → razonable 46
- TSM (panel) arquetipo: MATURE → GROWTH_PROFITABLE 
- UL (panel) calidad: sólida 75 → excelente 81
- UL (panel) precio: razonable 54 → razonable 46
- V (panel) precio: muy exigente 25 → exigente 30
- XOM (panel) calidad: sólida 72 → excelente 82
- XOM (panel) precio: exigente 39 → razonable 48
- XOM (panel) confianza: media → baja 
- FCX (local) calidad: sólida 79 → sólida 72
- FCX (local) precio: exigente 39 → muy exigente 24
- NFLX (local) calidad: excelente 100 → excelente 93
- O (local) calidad: sólida 70 → media 59
- SNOW (local) precio: muy exigente 28 → muy exigente 20
- SNOW (local) confianza: media → alta 

## Lectura

- **Ningún cambio de veredicto queda sin causa.** Los niveles se mueven en commits de método con su decisión registrada:
  - clasificación por la historia real (`9ea8193`, `0fe8ef0`);
  - DCF inverso con tasas base (`19def27`);
  - FCF − SBC (`fa9a156`);
  - ciclo medio (`e353392`);
  - método intrínseco donde faltaba (`3f4be83`);
  - P/E en bancos y aseguradoras (`1c3dbad`);
  - confianza por causas reales (`122cbb4`);
  - REIT FFO/activos (`21e8341`).
- **Los commits con miles de campos y ningún cambio de nivel añaden bloques nuevos al análisis**, sin mover la puntuación:
  - lecturas de calidad (`51201e2`);
  - contexto de mercado (`309ed32`, que D5 deja sin puntuar);
  - persistencia (`1f12e33`);
  - pre-mortem (`bc4fa89`);
  - procedencia en el anexo (`b586299`).
- **El P/E operativo de las aseguradoras** (`4412a49`, `354e7eb`) cambia la puntuación de precio de BRK-B (42 → 35) y PGR, sin cambiar su nivel. `354e7eb` toca los 36 del panel por la invariante y textos comunes del PDF, no por los veredictos.
- **Las muestras forzadas del contrato** (`tests/golden/forzados`) salen del juego local modificado (`contract_forced.py`). Cambian por las mismas causas que los golden de local.
