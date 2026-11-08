# Prueba hacia atrás del motor · segundo corte (5-nov-2024) · resultados (medido el 7-nov-2026)

Reglas: `PRUEBA_HACIA_ATRAS_2024_PREREGISTRO.md` (commit `fb462f11`, anterior a cualquier captura), que remite punto por
punto al de 2025. Datos: `archivo-historico/evidencias-de-pruebas/hacia_atras_2024-11-05/` (`empresas_410.csv`,
`metricas.json`, `metricas_a.csv`, `c123_tal_cual.json`, `datos_reales/`, `config_2024/`, corridas `corridas/{A,B,A14,C}`,
fixtures al corte, registros del corte). Pp = puntos porcentuales frente al SPDR del sector. **Decide el control (300).**

## Lo primero: un fallo de los datos de este corte invalida parte de la prueba

Yahoo solo sirve hoy los **cuatro últimos ejercicios anuales** (2022–2025). Cortados al 5-nov-2024 quedan dos o tres, y
el motor necesita cuatro para medir el crecimiento (ingresos, BPA y caja libre). Resultado: **261 de las 287 empresas del
control analizadas pierden la categoría «Crecimiento»** (en el corte de 2025 fueron 18 de 293). Una corrida real en
noviembre de 2024 habría tenido 2020–2023. No depende de los resultados: se ve en la cobertura de cada análisis.

| Lo que mide | ¿Afectado? | Por qué |
|---|---|---|
| L1 y L2 (líneas base) | **No** | salen de EDGAR y del precio al corte |
| C1 · etiqueta de precio de C (regla L1 del motor) | **Poco** | el precio de C no depende de la confianza ni de la cobertura (F16) |
| (a) precio de A, B y A14 | **Sí** | cobertura baja → confianza baja → el precio se contrae hacia «razonable» |
| (b) confianza de A, B y A14 | **Sí** | todas salen «baja»: no hay alta ni media que comparar |
| (c) alertas rojas de A, B y A14 | **Sí, en parte** | la calidad sin crecimiento cambia algunas alertas |
| C2 · alerta de valoración extrema | **Sí** | su lectura se contrae con la confianza: 22 alertas en vez de unas 49 |
| C3 · consistencia | **Sí** | la cobertura baja deja a casi todas en «mixta» (269 de 287) |
| (d) estimaciones y (e) lectura conductual | **Sí** | el crecimiento del DCF parte de la misma historia corta |

Abajo van las cifras tal cual salen; lo afectado lleva la marca †. La corrección posible y la decisión, al final.

## Veredicto en una tabla (control)

| Criterio | Resultado | ¿Cumple? | ¿Válido? |
|---|---|---|---|
| (a) A: barata − cara ≥ 5 pp y mejor que L1 y L2 | +3,0 pp (IC95 −10,4 a +16,4); L1 +2,5; L2 −8,6 | No (< 5 pp) | **No** (sesgado) |
| (b) A: acierto alta > media > baja | todas «baja» (59 %, n = 162) | No evaluable | **No** |
| (c) A: alertas ≥ 2 × sin alerta | 66,7 % frente a 52,7 % (× 1,27) | No | En parte |
| C1: D(C) frente a L1 y L2 | C +1,2 pp (IC −10,5 a +13,4); L1 +2,5; L2 −8,6 | (sin regla) | **Sí** |
| C2: caída ≥ 40 % con alerta frente a sin ella | 22,7 % (5 de 22) frente a 15,8 % (42 de 265) | (sin regla) | **No** (n reducido) |
| C3: acierto por consistencia | consistente 60 % (15) · mixta 51 % (172) | (sin regla) | **No** |

**Lo que sí se puede leer ya, sin depender del fallo:** la separación por precio de 2025 **no se repite** en este
periodo. Ni el P/E relativo (L1: +2,5 pp, frente a +11,7 en 2025) ni la etiqueta de C (+1,2 pp) separan barata de cara
a 12 meses; a 6 meses las dos son negativas (−3,6 y −3,4 pp). Todos los intervalos cruzan el cero con mucho margen. La
caja libre (L2) vuelve a fallar, y más (−8,6 pp). Fue un año en el que lo caro siguió subiendo (las caras de L2: +7,9 pp).

## Cobertura

- **Universo**: 543. Capturadas al corte: 523, PARA entre ellas (excluida, ver abajo). **Muestra**: 410; analizadas
  por A, B y A14, 395, sin ningún error.
- **Sin análisis en la muestra (15)**:
  - 12 sin serie de Yahoo, porque dejaron de cotizar: EA y WBD (de las 110) y ANSS, CTRA, DAY, DFS, HES, HOLX, IPG, MRO,
    QRVO y WBA. Cinco se compraron dentro de la ventana; Stooq no se usa (verificación anti-bots).
  - IBN: sin estados en EDGAR, como en 2025.
  - TTE: la herramienta de segmentos no reproduce su propia corrida, como en 2025.
  - **PARA**: hoy su símbolo es otra empresa en Yahoo y en EDGAR (CIK 1826011; precio 0,21 $ al corte). Se excluye.
- **Accesos no grabados (los dos, declarados)**:
  - ARM: el índice de dos 6-K sin datos de estados; su análisis es idéntico en vivo y en el replay.
  - MRNA (solo A y B): `/stock/earnings` de Finnhub, que al corte queda vacío como en 2025.
- **Rendimiento a 12 meses**: 290 del control y 108 de las 110. El sesgo de supervivencia es mayor que en 2025: 12
  empresas de la muestra quedan sin rendimiento, frente a 5.

## (a) y C1 · rendimiento relativo medio a 12 meses (y 6)

| Muestra | Método | Barata (n) | Cara (n) | D 12 m | IC95 12 m | D 6 m | Spearman 12 m |
|---|---|---|---|---|---|---|---|
| Control | A (actual) † | +2,0 (28) | −1,0 (134) | +3,0 | −10,4 / +16,4 | −0,9 | 0,06 |
| Control | B (sin F13) † | −3,0 (35) | −1,1 (139) | −1,9 | −13,7 / +8,7 | −2,3 | 0,06 |
| Control | A14 (sin F15) † | −1,3 (36) | −1,5 (134) | +0,2 | −12,0 / +11,8 | −1,9 | 0,07 |
| Control | **C (regla L1 del motor)** | +0,4 (96) | −0,8 (91) | **+1,2** | −10,5 / +13,4 | −3,4 | 0,05 |
| Control | **L1 · P/E relativo** | +0,8 (95) | −1,7 (90) | **+2,5** | −10,2 / +15,1 | −3,6 | 0,07 |
| Control | **L2 · FCF yield** | −0,7 (84) | +7,9 (83) | **−8,6** | −21,7 / +3,6 | −7,3 | −0,01 |
| 110 | A † | −6,0 (8) | +2,9 (50) | −8,9 | −27,2 / +7,4 | −6,9 | −0,19 |
| 110 | C | −5,7 (27) | +0,5 (35) | −6,2 | −16,7 / +3,8 | −3,1 | −0,13 |
| 110 | L1 | −1,3 (28) | +1,3 (37) | −2,6 | −13,8 / +8,3 | −2,5 | −0,07 |
| 110 | L2 | −4,8 (32) | +9,6 (41) | −14,4 | −25,9 / −3,4 | −4,9 | −0,23 |

† = afectado por el fallo de datos. C reparte por tercios como L1 (96 / 79 / 91). A llama «barata» solo al 10 % del
control (28), menos que en 2025 (49), por la contracción.

## (b), (c), C2 y C3

- **(b)** No evaluable. A, B y A14 dan confianza «baja» a todas (acierto de dirección: 59 % en A, n = 162).
- **(c)** Caída ≥ 25 % en 6 o 12 meses, o recorte de dividendo, con alerta frente a sin alerta:
  - Control: A 66,7 % (156) frente a 52,7 % (131), × 1,27; B × 1,10.
  - 110: A × 1,27.
  - No llega a 2 en ninguna. La tasa de partida es alta: la caída máxima mediana a 12 meses del control fue del 27 %,
    con la caída de abril de 2025 dentro de la ventana.
- **C2** · alerta de valoración extrema. Salta exactamente donde A dice «muy exigente» (22 = 22): la definición se
  mantiene.
  - Caída ≥ 40 % en 12 meses: 22,7 % con alerta (5 de 22) frente a 15,8 % sin ella (42 de 265), × 1,44. En 2025 fue
    34,7 % frente a 14,9 % (× 2,33).
  - La dirección se repite, pero con 22 alertas (la contracción reduce las «muy exigente») el dato es débil: con 5
    casos, un caso más o menos mueve 4,5 pp.
  - Las 110: 1 de 6 frente a 8 de 102.
- **C3** · acierto de dirección por consistencia, con la etiqueta de C. Consistente 60 % (n = 15) frente a mixta 51 %
  (n = 172). Con 15 casos no se puede leer.

## Desviaciones y límites

Todos se decidieron antes de ver resultados, salvo donde se dice.

- **Damodaran de enero de 2024** (enlace «1/24», archivos con sufijo 23; «Date updated» 2024-01-05).
  - Rf 4,28 % y ERP 4,06 % (fila nov-2024 de ERPbymonth).
  - **La lista de empresas de enero de 2024 no está en el archivo de NYU** (404). Se usa la de enero de 2023, la última
    anterior al corte, así que no mira el futuro. Quedan 20 empresas sin industria, AMZN entre ellas: su industria
    «Retail (Online)» desaparece en las tablas de 2024.
  - Los spreads del rating salen de `bondspreads23` («Spread 2024»), porque `ratings23` tampoco está. Se comprobó que en
    2025 coincide uno a uno con su `ratings24`.
  - La región «Eastern Europe & Russia» se reetiqueta como «Eastern Europe», sin tocar cifras.
  - Algunos textos fijos del motor dicen «enero de 2026»: es la etiqueta, no los valores.
- **Mercado al corte**: P/E mediano del S&P 500 24,8× (458 empresas) y EV/EBITDA 16,8× (303), con EDGAR y el cierre del
  corte. El P/E adelantado no se usa: no hay consenso al corte.
- **Capturas** (igual que en 2025, más dos arreglos de la herramienta):
  - Cautivas: CAT, F y GM, con el companyfacts entero de su financiera.
  - `FACTS_SINCE` se fija según la fecha de corte (2018 en lugar de 2019). Así se graba el ejercicio más antiguo que el
    motor lee al corte; con el corte de 2025 no cambia nada.
  - TEL, CDW, WRB y CINF necesitaron el companyfacts completo, que el replay vuelve a cortar por fecha de presentación.
    El reducido perdía cargos y ganancias de cartera de años anteriores.
- **Un fallo real de C**: MRNA daba error 500. «Pérdidas con ventas en caída» construía el texto con la caída a tres
  años, y con solo tres ejercicios esa caída no existe.
  - Arreglado en la rama: `5435acc6`, con prueba.
  - C corre con ese arreglo, que solo cambia las empresas que daban el error.
  - **Afecta también a la versión en vivo de la rama.**
- **Yahoo**: los dividendos de julio a diciembre de 2025 tienen huecos en 10 empresas (ACN, ALLE, AON, CB, CBOE, CNQ,
  EG, JCI, RY y TD). Se corrigieron con EDGAR, y llevan la marca de rendimiento infravalorado.
- **Hallado en el corte de 2025 (sin tocar)**: el factor de ADR de SMFG en `al_corte.csv` de 2025 es 1,2176 en lugar de
  0,609, por un split local de 2026. La capitalización, el P/E y la etiqueta L1 de SMFG en 2025 están mal: es una sola
  empresa del control de 2025.

## La corrección posible y lo que te toca decidir

**La corrección**: completar en la capa de corte los ejercicios que Yahoo ya no da (2020 y 2021) con los de EDGAR
presentados antes del corte (ingresos, BPA diluido, beneficio, flujo operativo y capex). Después, repetir A, B, A14 y C.

- Es la única fuente gratuita y fiable para esos años.
- Es una desviación del pre-registro («Yahoo cortado»), decidida **después de ver** estos resultados. Lo que la
  justifica es un hecho objetivo: 91 % de cobertura perdida frente al 6 % de 2025. Se informaría como corrección, igual
  que la de TM y SKYD en 2025.
- No cambia L1, L2 ni la conclusión principal de C1.

Decisiones:

1. **Si se aplica la corrección**, que haría válidos (a), (b), (c), C2 y C3, o se deja este corte solo para C1, L1 y L2.
2. **Con lo ya válido**, la separación por precio de 2025 no se confirma fuera de muestra: L1 +2,5 pp y C +1,2 pp, con
   intervalos de ±12 pp. La decisión de 2025 (precio = L1) no queda respaldada ni refutada. Este periodo no premia
   comprar barato.
