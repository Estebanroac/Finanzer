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
