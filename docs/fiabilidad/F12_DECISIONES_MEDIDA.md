# F12 · Medición de las dos decisiones de F11 (5-nov-2026)

Rama `fiabilidad/f12-decisiones` (worktree `worktrees/finanzer_next-f11`), sobre main 9af7b4b0. **Nada en producción:
espera la revisión del usuario.**

Datos: tres escaneos de las 543 empresas con datos del mismo día.
- `2026-11-05-f12-base`: código de main. Se guardaron además todas las alertas candidatas, con su peso, antes del tope
  de 6.
- `2026-11-05-f12-nuevo`: código F12.
- `2026-11-05-f12-recheck`: BP y HCA otra vez, para atribuir sus cambios.

## D1 · Alerta «Caída pronunciada»

### Dónde caería el peso 66–70 (condición 1)

Las alertas van en tres grupos con su propio tope de 6: banderas rojas, advertencias y fortalezas. La caída es una
**advertencia**. Los riesgos graves de solvencia son **banderas rojas**: no compiten con ella.

| Peso | Grupo | Señal |
|---:|---|---|
| 90 | bandera roja | Riesgo de insolvencia (Altman Z en zona de riesgo) |
| 90 | bandera roja | Runway crítico (< 1 año de caja) |
| 80 | bandera roja | Deterioro estructural del negocio |
| 70 | bandera roja | Quema de caja recurrente (FCF negativo persistente) |
| 68 | bandera roja | Sobrevaloración (P/E) |
| **66–70** | *advertencia* | *la caída con la propuesta inicial* |
| 66 | bandera roja | Apalancamiento alto (riesgo) |
| 64 | bandera roja | Cobertura de intereses crítica o negativa |
| 62 | advertencia | Valoración exigente (P/E): la advertencia de más peso hoy |
| 50 | advertencia | Riesgo de crédito no medido (la variable crítica faltante del tipo, banco) |
| 50 | advertencia | Apalancamiento elevado |
| 46 | advertencia | Cobertura de intereses ajustada |
| 44 | advertencia | Liquidez ajustada o en deterioro; runway ajustado |

Con 66–70, la caída sería la advertencia de más peso de todas: por encima de toda advertencia de solidez financiera y
de «Valoración exigente». Las de solvencia que comparten grupo con ella pesan 44–50.

**Tope fijado: w_max = 44**, el menor peso de las advertencias de solidez financiera. Con empate, la caída queda
detrás porque es el último interpretador. Así nunca saca a una de solvencia, por construcción y no solo en esta
muestra; lo comprueba un test.

### Las dos versiones lado a lado (condición 2)

- **Volatilidad:** z = |caída| ÷ volatilidad anual realizada de la propia acción. El peso va de 34 (z ≤ 1,0) a 44
  (z ≥ 1,5), con el piso de −30 % para que la alerta exista. Distribución de z en el universo: mediana 0,78, p82 = 1,0,
  p98 = 1,35, máximo 1,85. Va implementada en el motor.
- **Lineal:** de 34 a −30 % hasta 44 a −60 %. Simulada sobre las mismas alertas candidatas.

213 empresas caen más de un 30 % en el año. Hoy la alerta ya sale en 205. Las otras 8 tienen el grupo lleno con
advertencias de más peso: CIEN, CSGP, LEN, MPWR, NCLH, NOW, RCL y WAT.

| Versión | Ganan la alerta en el top 6 | Qué sale del top 6 (por tipo) | Solvencia desplazada |
|---|---|---|---|
| Actual (peso fijo 34) | 0 | — | ninguna |
| Propuesta inicial (lineal, tope 70) | 6 | margen neto estrecho ×5 (3 normalizado), volatilidad elevada ×1 | ninguna en esta muestra (sin garantía) |
| Lineal, tope 44 | 5: CIEN, CSGP, LEN, NCLH, NOW | margen neto estrecho ×4 (2 normalizado), volatilidad elevada ×1 | ninguna |
| **Volatilidad, tope 44 (implementada)** | **1: CSGP** | margen neto estrecho ×1 | **ninguna** |

El motor nuevo da lo mismo que la simulación: CSGP gana la alerta, ninguna la pierde, ninguna de solvencia sale y en 28
cambia su posición dentro del grupo.

**Ejemplos (top 6 de advertencias, peso entre paréntesis):**

| | Caída / volatilidad / z | Actual | Lineal 44 | Volatilidad 44 |
|---|---|---|---|---|
| **CSGP** | −61,7 % / 50 % / 1,24 | FCF yield bajo (42), DCF no concluyente (40), ROE bajo (40), BPA en descenso (40), EV/EBITDA sobre el mercado (38), margen neto estrecho (36) | **caída (44)** primera; sale margen neto estrecho | **caída (38,9)** quinta; sale margen neto estrecho |
| **CIEN** | −56,6 % / 79 % / 0,71 | P/E exigente (62), FCF yield bajo (42), ROE bajo (40), BPA en descenso (40), EV/EBITDA (38), margen neto estrecho (36) | caída (42,9) segunda; sale margen neto estrecho | sin cambio: la caída es menor que lo que suele moverse |
| **NOW** | −54,6 % / 66 % / 0,82 | P/E exigente (62), **liquidez en deterioro (44)**, prima sobre el valor justo (40), ROE bajo (40), EV/EBITDA (38), margen neto estrecho (36) | caída (42,2) tercera, **detrás de la de liquidez**; sale margen neto estrecho | sin cambio |

Cuando la versión por volatilidad la sube, el texto lo explica: «Es 1.2 veces su volatilidad anual (50%): más de lo
que suele moverse».

**Decidido (usuario, 5-nov-2026): volatilidad.**
- **Volatilidad** (implementada): solo una caída anómala para esa acción sube de peso. CIEN y NOW se mueven un 66–79 %
  al año y su caída está dentro de lo habitual.
- **Lineal:** cuenta lo honda que es la caída, sea cual sea la acción. Cinco empresas ganan la alerta.

## D2 · Validación del forward

### Las 15

| Empresa | Año base (3 a) | ¿Deprimido? (base / mediana, ejercicios) | Respaldo antes → después | ¿Bases distintas? (implícito normalizado / reportado) | Forward P/E | Nota de precio |
|---|---|---|---|---|---|---|
| APH | FY2022 | no (158 %, 10) | +30 % → +30 % | no (+54 % / +57 %) | 2 → 2 | 48 → 48 |
| AZN | FY2022 | no (103 %, 10) | +43 % → +43 % | no (+60 % / +60 %) | 3 → 3 | 28 → 28 |
| DELL | FY2023 | no (72 %, 10) | +36 % → +36 % | no (+83 % / +76 %) | 3 → 3 | 50 → 50 |
| DIS | FY2022 | **sí (45 %, 9)** | +55 % → **+4 %** (FY2017–FY2025) | no | 3 → **0** | 55 → **52** |
| FIX | FY2022 | no (172 %, 10) | +45 % → +45 % | no (+45 % / +45 %) | 3 → 3 | 85 → 85 |
| GOOG | FY2022 | no (149 %, 10) | +33 % → +33 % | **sí (+45 % / −19 %)** | 3 → **0** | 31 → 31 |
| GOOGL | FY2022 | no (149 %, 10) | +33 % → +33 % | **sí (+45 % / −19 %)** | 3 → **0** | 24 → **20** |
| HWM | FY2022 | no (100 %, 10) | +30 % → +30 % | no (+30 % / +30 %) | 2 → 2 | 28 → 28 |
| INCY | FY2022 | no (311 %, 10) | +62 % → +62 % | **sí (+289 % / +341 %)** | 3 → **0** | 30 → 30 |
| JCI | FY2022 | no (90 %, 10) | +32 % → +32 % | **sí (+107 % / +57 %)** | 2 → **0** | 10 → **5** |
| NFLX | FY2022 | no (163 %, 10) | +28 % → +28 % | **sí (+29 % / +9 %)** | 2 → **0** | 54 → **50** |
| NVDA | FY2023 | no (101 %, 10) | +67 % → +67 % | **sí (+125 % / +101 %)** | 3 → **0** | 45 → 45 |
| PTC | FY2022 | no (240 %, 10) | +25 % → +25 % | **sí (+25 % / −12 %)** | 2 → **0** | 52 → **50** |
| SMCI | — | sin juzgar: menos de 5 ejercicios comparables | +23 % → +23 % | no | 2 → 2 | 65 → 65 |
| TDG | — | sin juzgar: menos de 5 ejercicios comparables | +25 % → +25 % | no | 2 → 2 | 50 → 50 |

- **Punto 3** (prueba de coherencia, umbral de 15 pp): salta en 8 de las 15. El forward deja de puntuar y el texto lo
  dice: «normalización o consenso en bases distintas: el forward implica +29% frente al BPA normalizado y +9% frente
  al reportado; la compresión no puntúa».
- **Punto 2** (base deprimida): salta en 1 de las 15 (DIS). El respaldo es el menor entre la ventana que empieza
  después de la base y la tasa de la serie larga. En DIS es la larga, +4 % anual FY2017–FY2025.
- **NFLX:** su base FY2022 **no** sale deprimida frente a la mediana de 10 años (163 %). En una empresa que ha crecido
  mucho, los años antiguos bajan la mediana, así que un bache frente a la tendencia no se detecta con la mediana. NFLX
  queda corregida por el punto 3. Si quieres detectar también los baches de las que crecen, la alternativa es comparar
  la base con la tendencia log-lineal de la serie y no con la mediana. No va implementada; es otra decisión.
- **SMCI y TDG:** no tienen 5 ejercicios comparables (en las demás, la serie larga de EDGAR solo se usa con las
  acciones estables). Se quedan con la regla de siempre.
- **Las 6 que siguen marcando `forward_creible`** (APH, AZN, DELL, FIX, HWM, TDG) tienen respaldo propio de 3 años y
  del último ejercicio, sin base deprimida y en la misma base. Es el caso que el usuario decidió no tocar con un tope
  por tipo de empresa. Antes eran 13.

### En el universo

El Forward P/E cambia en 19 empresas, todas por F12:
- **Bases distintas (15):** AMGN, AON, BR, CPAY, CRM, GOOG, GOOGL, INCY, JCI, JNJ, NFLX, NVDA, ORCL, PNR y PTC.
- **Base deprimida (4):** DIS, CMCSA (+10 %), D (+3 %) e IBM (−1 %). Las cuatro con la tasa larga de 10 años.

La nota de precio cambia en 8 por F12:

| Empresa | Nota de precio |
|---|---|
| AMGN | 39 → 40 |
| D | 35 → 31 |
| DIS | 55 → 52 |
| GOOGL | 24 → 20 |
| JCI | 10 → 5 |
| JNJ | 15 → 10 |
| NFLX | 54 → 50 |
| PTC | 52 → 50 |

En las demás, la contracción por confianza absorbe el cambio. Hubo otras 2 que no son de F12; reanalizadas con el
código F12 vuelven a sus valores de partida:
- **BP:** el escaneo la clasificó un momento como cíclica.
- **HCA:** cambió la referencia del P/E.

La inestabilidad de clasificación de BP entre corridas es un asunto aparte, a revisar.

**Requisito de V1** anotado en `docs/modelo/ESPEC_MODELO_GENERAL.md`: los puntos 2 y 3 también dentro del voto único
del beneficio.

## Golden (replay)

Solo NFLX cambia en lo sustancial. El forward pasa de +2 a 0 por bases distintas (+43 % frente a +20 %) y el bloque de
múltiplos de −1 a −2. Eso vuelve el veredicto dependiente del Ke, y en cadena:
- La confianza baja de media a baja.
- La calidad mostrada se contrae de 91 a 85, todavía «excelente».
- El precio pasa de 46 a 45, todavía «razonable».

La caída (−46,0 %, z 1,3) pasa a primera advertencia. JPM y V solo ganan los campos informativos nuevos.

**Golden regenerados** tras elegir la volatilidad (local, panel, PDF y muestras forzadas): 29 empresas. Solo 3 cambian
en lo sustancial:
- **NFLX:** el forward pasa de +2 a 0 y el precio de 46 a 45 («razonable»). La confianza baja de media a baja y la
  calidad de 91 a 85 («excelente»). La caída sube a primera advertencia.
- **NVDA (panel):** el forward pasa de +3 a 0 por bases distintas (+84 % frente a +64 %). El precio baja de 46 a 42 y
  pasa de «razonable» a «exigente».
- **MC.PA (panel):** la caída sube de la cuarta a la segunda advertencia.

Las otras 26 solo ganan los campos informativos (`eps_base_check`, `implied_eps_growth_reported`) o, en MSFT, la frase
«Es 1.1 veces su volatilidad anual».

## Pendiente

1. ~~D1: elegir la versión~~: volatilidad (usuario, 5-nov).
2. **D2:** dar el visto bueno al umbral de 15 pp (8 de las 15 y 15 del universo) y a usar el menor entre ventana
   posterior y tasa larga con base deprimida.
3. Golden regenerados; suite completa; esperar el «ok, pushea».
