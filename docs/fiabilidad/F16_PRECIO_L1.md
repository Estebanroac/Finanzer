# F16 · La etiqueta de precio pasa a la regla L1 (§8 de la prueba hacia atrás)

Origen: `PRUEBA_HACIA_ATRAS_2025_RESULTADOS.md`. En el control, el motor y L1 empatan a 12 meses (+11,7 pp los dos) y
L1 gana a 6 meses. Decisión del usuario (6-nov-2026): «Empate: aplicar §8». La valoración se simplifica hacia L1 y el
motor queda para calidad, alertas y lectura. No hay otro ciclo de ajustes de precio.

## Decisiones del usuario (6-nov-2026)

1. **3 niveles**: atractivo (tercio más barato), razonable y exigente (tercio más caro), como se probó. Desaparecen
   «muy atractivo» y «muy exigente».
2. **La confianza no mueve el precio**: sin contracción hacia «razonable». La confianza se sigue mostrando como
   fiabilidad de los datos (y sigue contrayendo la calidad, que no se tocó).
3. **Expectativas golden**: se retiran los rangos de precio. Quedan la calidad, las reglas globales y la confianza
   máxima.

## La regla (la misma que se midió)

- P/E de doce meses = capitalización / beneficio neto atribuible de los **doce meses al último periodo presentado en
  EDGAR** (no al último de Yahoo, que va con retraso).
- Hallazgo de F16: el P/E que ya mostraba el motor difiere más de un 25 % del de L1 en 1 de cada 4 empresas (AMZN 45×
  frente a 35×, CI 21× frente a 11×), porque usa el corte de Yahoo.
- P/E relativo = P/E / mediana del P/E (> 0) de su sector GICS en el universo (543).
- Tercios del P/E relativo en el universo: el tercio bajo es «atractivo», el alto «exigente» y el resto «razonable».
- Beneficio ≤ 0 o sin P/E: «precio sin veredicto», con el motivo.
- Las medianas por sector y los dos cortes viven en `config/precio_l1.toml`, con su fecha. Los genera
  `tools/precio_l1_universo.py` con el P/E que calcula el propio motor en cada empresa del universo (el mismo número
  que se compara después en vivo).
- El DCF, el DCF inverso, los múltiplos frente al sector y los escenarios se siguen calculando y mostrando como
  **lectura**, pero no deciden la etiqueta.

## Verificación (no es un ajuste)

Se corre la prueba hacia atrás con F16 al corte del 5-nov-2025: los cortes salen del motor F16 sobre el universo de
2025. Lo esperado es reproducir L1 (D ≈ +11,7 pp en el control). Si no lo reproduce, se informa y no se toca la regla.

## Verificación al corte del 5-nov-2025 (6-nov-2026)

- Universo de 2025 capturado al corte entero: 543 empresas, 498 con P/E del motor. La referencia que sale de ahí
  (`archivo-historico/evidencias-de-pruebas/hacia_atras_2025-11-05/precio_l1_2025-11-05.toml`) tiene medianas por
  sector a ±1 punto de las de L1 y cortes de 0,83 y 1,21 veces la mediana.
- El P/E del motor coincide con el de L1 en el 97 % de las empresas (±10 %; mediana del cociente 1,00). Hay dos
  diferencias de fuente, no de regla: la capitalización con las acciones de Yahoo (BX, RIO, TKO) y los informes que
  companyfacts no trae (AOS, SPGI).
- Control a 12 meses: F16 da barata − cara = +10,8 pp (IC95 +2,8 / +18,0) y L1 +11,7. A 6 meses, F16 +8,7 y L1 +8,8.
  Reparto: 99 / 85 / 91 en F16 y 102 / 85 / 93 en L1. En las 110: F16 +8,9 y L1 +10,8 a 12 meses.

## En producción (preparado el 6/7-nov-2026, sin push)

- Referencia en vivo: `config/precio_l1.toml` generada con `tools/universe_scan.py` sobre las 543 (6-nov-2026) y
  `tools/precio_l1_universo.py`: 513 con P/E, cortes 0,837 y 1,255; escaneo en
  `archivo-historico/evidencias-de-pruebas/f16_referencia_2026-11-06/`. Refrescar cada mes.
- Efectos colaterales, todos por la regla: sin la dependencia de Ke del precio desaparece ese escalón de confianza
  (BRK-B baja → media, JPM media → alta) y, con él, la contracción de la calidad que dependía de esa confianza (BRK-B
  68 → 71); «Esta lectura sería errónea si…» se redacta con el nuevo nivel; sin P/E, «precio sin veredicto» y el motivo.
- Vista y PDF: la nota del precio cita P/E, mediana del sector, cociente y tercio (guardián: predicado `price_l1`);
  la metodología explica la regla; la web muestra 3 tramos (exigente < 34, razonable, atractivo ≥ 67).
- Suite: 6783 pasados; web: 173; guardián de build.sh en verde.

### Veredicto de precio del panel, antes y con F16

| Empresa | Antes | F16 | P/E | Veces la mediana |
|---|---|---|---|---|
| AAPL | muy exigente | exigente | 38.8x | 1.35 |
| AMT | razonable | atractivo | 24.6x | 0.74 |
| AMZN | muy exigente | razonable | 20.3x | 1.06 |
| ASML | entre exigente y muy exigente | exigente | 58.4x | 2.03 |
| BAC | entre razonable y exigente | atractivo | 11.2x | 0.78 |
| BCS | razonable | atractivo | 7.2x | 0.51 |
| BRK-B | exigente | razonable | 13.1x | 0.92 |
| CAT | entre exigente y muy exigente | exigente | 31.7x | 1.27 |
| CRWD | muy exigente | exigente | 4268.7x | 148.58 |
| DOW | razonable | sin veredicto | — | beneficio de doce meses ≤ 0: el P/E no tiene sentido |
| DUK | exigente | razonable | 18.0x | 0.87 |
| FCX | entre razonable y exigente | exigente | 33.9x | 1.67 |
| HSBC | exigente | razonable | 12.4x | 0.87 |
| JNJ | muy exigente | razonable | 29.1x | 0.97 |
| JPM | exigente | razonable | 14.0x | 0.98 |
| KO | exigente | exigente | 27.6x | 1.29 |
| MC.PA | razonable | sin veredicto | — | sin estados de SEC EDGAR |
| MSFT | exigente | razonable | 29.6x | 1.03 |
| MU | entre exigente y muy exigente | atractivo | 12.2x | 0.42 |
| NEE | entre razonable y exigente | razonable | 17.6x | 0.85 |
| NFLX | exigente | exigente | 21.5x | 1.31 |
| NVDA | muy exigente | razonable | 27.7x | 0.96 |
| NVO | atractivo | atractivo | 10.8x | 0.36 |
| O | atractivo | razonable | 41.2x | 1.24 |
| PG | entre exigente y muy exigente | razonable | 23.1x | 1.08 |
| PGR | razonable | atractivo | 10.6x | 0.74 |
| PLD | razonable | razonable | 29.5x | 0.89 |
| PLTR | muy exigente | exigente | 160.1x | 5.57 |
| RIVN | razonable | sin veredicto | — | beneficio de doce meses ≤ 0: el P/E no tiene sentido |
| SHEL | atractivo | razonable | 11.3x | 0.86 |
| SNOW | exigente | sin veredicto | — | beneficio de doce meses ≤ 0: el P/E no tiene sentido |
| SPY | — | — | — | — |
| TM | razonable | atractivo | 8.8x | 0.46 |
| TSM | exigente | exigente | 40.8x | 1.42 |
| UL | razonable | atractivo | 12.9x | 0.60 |
| V | muy exigente | exigente | 32.5x | 2.28 |
| XOM | entre razonable y exigente | exigente | 22.2x | 1.68 |
