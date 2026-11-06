# Prueba hacia atrás del motor · resultados (corte 5-nov-2025, medido el 6-nov-2026)

Reglas: `PRUEBA_HACIA_ATRAS_2025_PREREGISTRO.md` (commit `c65d36cd`, anterior a cualquier corrida). Datos y CSV:
`archivo-historico/evidencias-de-pruebas/hacia_atras_2025-11-05/` (`empresas_410.csv`, `metricas_a.csv`,
`metricas.json`, `datos_reales/*.csv`, corridas `corridas/{A,B,A14}`, fixtures al corte, registros del corte).
Pp = puntos porcentuales de rendimiento frente al SPDR del sector. **Decide el control (300).**

## Veredicto en una tabla (control)

| Criterio | Resultado del motor A | ¿Cumple? |
|---|---|---|
| (a) Precio a 12 m: barata − cara ≥ 5 pp y mejor que L1 y L2 | **+11,8 pp** (IC95 +2,1 a +21,5); L1 +11,7 pp; L2 +4,3 pp | **Sí, por 0,13 pp sobre L1: empate práctico** |
| (b) Confianza: acierto alta > media > baja | alta 40 % (n = 5) · media 58 % · baja 56 % | No |
| (c) Alertas rojas: frecuencia ≥ 2 × sin alerta | 63,6 % frente a 56,7 % (× 1,12) | No |
| (d) Estimaciones | crecimiento conservador (mediana −1,3 pp en maduras); caja muy dispersa | (informativo) |
| (e) Lectura conductual | «caída sin explicar» siguió cayendo (−12,8 pp, 3 de 10 rebotaron) | (informativo) |

**Regla de decisión (§8):** el motor A supera literalmente a L1 y a L2 en (a), así que la regla fijada no obliga a
simplificar la valoración. Pero la ventaja sobre la regla simple de P/E relativo es de 0,13 pp con intervalos de
±10 pp, y a 6 meses L1 gana con claridad (+8,8 pp frente a +1,1). Lectura honesta: **la etiqueta de precio del motor
separa barata de cara, pero no mejor que un P/E relativo a su sector.**

## Cobertura

401 de 410 analizadas al corte por las tres versiones, sin un solo acceso a datos no grabados. Faltan 9:
EA, WBD, CTRA, DAY y HOLX (deslistadas: Yahoo ya no tiene su historia y no hay otra fuente gratuita y fiable; Stooq
exige pasar una verificación anti-bots), IBN (sin estados en EDGAR), EME y TTE (la herramienta de segmentos no
reproduce su propia corrida) y GSK (Yahoo no dio el tipo de cambio GBP en la captura). Con veredicto y rendimiento a 12
meses: 292 del control y 105 de las 110. El sesgo de supervivencia queda en 5 empresas (4 compradas con prima).

## (a) Precio · rendimiento relativo medio a 12 meses (y 6)

| Muestra | Método | Barata (n) | Cara (n) | D 12 m | IC95 12 m | D 6 m | Spearman 12 m |
|---|---|---|---|---|---|---|---|
| Control | **A (actual)** | +6,3 (49) | −5,5 (138) | **+11,8** | +2,1 / +21,5 | +1,1 | 0,23 |
| Control | B (5-nov-2026, sin F13) | +3,9 (49) | −5,2 (143) | +9,0 | −0,5 / +19,4 | −1,3 | 0,22 |
| Control | A14 (sin F15) | +5,0 (51) | −5,4 (140) | +10,4 | +0,9 / +19,6 | +0,6 | 0,22 |
| Control | L1 · P/E relativo | +1,4 (102) | −10,3 (93) | +11,7 | +4,0 / +19,3 | **+8,8** | 0,17 |
| Control | L2 · FCF yield | +2,9 (92) | −1,4 (84) | +4,3 | −4,9 / +13,2 | −5,7 | 0,07 |
| 110 | A | +10,7 (19) | +1,0 (49) | +9,8 | −3,2 / +22,6 | +8,5 | 0,16 |
| 110 | B | +9,2 (19) | +1,0 (50) | +8,2 | −3,8 / +20,3 | +7,9 | 0,17 |
| 110 | L1 | +9,4 (31) | −1,4 (33) | +10,8 | −0,5 / +22,6 | +10,1 | 0,13 |
| 110 | L2 | +6,1 (32) | +23,1 (46) | −17,0 | −59,9 / +9,7 | −3,7 | −0,02 |

**¿F13 y F14 mejoraron la predicción o solo cambiaron etiquetas?** En el control, D pasa de +9,0 (B) a +10,4 (A14) y a
+11,8 (A, con F15). La mejora va en la buena dirección y por pasos, pero queda muy dentro del ruido (intervalos
solapados de ±10 pp). Las etiquetas apenas se movieron: en neto, 5 «caras» menos y 5 «razonables» más. Respuesta: **cambiaron poco
las etiquetas y la mejora de la predicción no se distingue del azar con 300 empresas.**

El motor es muy asimétrico: llama «cara» al 48 % del control y «barata» al 17 %. L1 reparte por tercios.

## (b) Confianza · acierto de dirección (barata que bate al sector o cara que queda por detrás, a 12 m)

| Muestra | Versión | Alta | Media | Baja |
|---|---|---|---|---|
| Control | A | 40 % (5) | 58 % (98) | 56 % (84) |
| Control | B | 40 % (5) | 54 % (102) | 58 % (85) |
| 110 | A | 50 % (2) | 71 % (24) | 38 % (42) |

No cumple. La confianza alta casi no existe (5 empresas) y media frente a baja no separa en el control. En las 110 sí
separa (71 % frente a 38 %), pero son las empresas ajustadas con información posterior.

## (c) Alertas rojas · caída ≥ 25 % en 6 o 12 meses o recorte de dividendo

| Muestra | Versión | Con alerta | Sin alerta | Cociente |
|---|---|---|---|---|
| Control | A | 63,6 % (129) | 56,7 % (164) | 1,12 |
| Control | B | 60,3 % (141) | 59,2 % (152) | 1,02 |
| 110 | A | 48,8 % (43) | 26,2 % (65) | 1,87 |
| 110 | B | 40,0 % (50) | 31,0 % (58) | 1,29 |

No cumple. La tasa de partida es alta: la caída máxima mediana a 12 meses del control fue del 28 % (S&P 500: −8,9 %,
comprobado con Yahoo). F13–F15 mejoran las alertas (1,02 → 1,12 en el control y 1,29 → 1,87 en las 110), pero sin
llegar a 2. Recortes de guía y de calificación: sin fuente gratuita (pre-registro §6). Sin los 7 recortes de dividendo
dudosos (pagos a cuenta y finales de ADR, BX variable, escisiones), el control queda en 63,6 % frente a 55,5 %: tampoco
cumple.

## (d) Estimaciones (A; error = proyectado − real)

| Arquetipo (control) | Crecimiento: mediana del error / del error absoluto (n) | Caja de 2 trimestres: mediana del error relativo / absoluto (n) |
|---|---|---|
| Madura | −1,3 pp / 4,6 pp (167) | −4 % / 27 % (141) |
| Crecimiento rentable | −3,0 pp / 6,2 pp (26) | −41 % / 49 % (22) |
| Cíclica | −8,0 pp / 9,8 pp (28) | −31 % / 96 % (23) |
| Financiera, REIT, utility | sin crecimiento del DCF (otro método) | — |

El crecimiento del DCF es conservador: las ventas crecieron más de lo proyectado, poco en las maduras y mucho en las
cíclicas. La caja de dos trimestres es muy ruidosa fuera de las maduras.

«Esta lectura sería errónea si…»:
- **Margen** («el margen operativo volviera a su mediana»): se cumplió en 3 de 43 casos del control en los 2
  trimestres siguientes.
- **Deuda** («el EBITDA cayera o la deuda se refinanciara más cara»): no evaluable, porque los datos reales no tienen
  EBITDA trimestral ni coste de la deuda.
- **Precio inverso** (10 años): no evaluable a 12 meses.

## (e) Lectura conductual (solo precio, control, A)

- **Caída sin deterioro**:
  - «Caída sin explicar» (10 empresas): −14,3 pp a 6 meses y −12,8 a 12; solo rebotaron 3. Siguieron cayendo, que es
    lo que su texto advierte («no es una señal de compra»).
  - «Sobrerreacción»: ninguna. Necesita la reacción a los últimos resultados, que al corte es «sin dato» porque
    Finnhub gratis solo da los 4 trimestres más recientes.
- **Extrapolación** (17): −14,4 pp a 12 meses. La lectura acertó en la dirección.
- **Anclaje en máximos** (60): +3,7 pp a 12 meses.
- **Momentum 12-1 y fuerza relativa**:
  - A 6 meses ordenan: tercio alto frente a bajo, +6,1 frente a −4,8 pp (fuerza relativa: +6,2 frente a −7,8).
  - A 12 meses no ordenan (el tercio medio es el mejor).

## Desviaciones y límites (todos decididos antes de ver resultados, salvo donde se dice)

- **Pares del universo**: reconstruidos con EDGAR al corte (pre-registrado). P/E y EV/EBITDA medianos del S&P 500 de
  `sectors.toml`: recalculados al corte (24,7× y 16,3×) con los mismos datos. El P/E adelantado de mercado no se usa:
  ninguna empresa tiene P/E adelantado al corte.
- **Damodaran de enero de 2025**: el archivo «1/25» usa sufijo 24 (fecha interna 2025-01-05). Spreads del rating
  sintético de enero de 2025. Rf 4,11 % y ERP 3,73 % (fila nov-2025 de ERPbymonth). Algunos textos fijos del motor
  siguen diciendo «enero de 2026»: es la etiqueta, no los valores.
- **Lo que Yahoo y Finnhub dan sin historia**:
  - Yahoo da los valores de hoy de los periodos antiguos: pueden incluir reexpresiones posteriores.
  - Yahoo registra las escisiones como splits (HON, CMCSA, UL…).
  - Finnhub `/stock/earnings` queda vacío al corte. Sale «PEAD sin dato» en 395 de 401.
- **Recorte de dividendo**: regla literal del pre-registro. La sensibilidad sin los dudosos no cambia (c).
- **Fallos de la herramienta del banco**: las financieras cautivas (CAT, GM, F) necesitaron su companyfacts entero;
  EME y TTE fallan en segmentos y quedan fuera.

## Qué te toca decidir

1. Si das (a) por superado con 0,01 pp sobre L1, como dice la regla literal, o lo tratas como empate y aplicas el §8
   (simplificar hacia L1).
2. (b) y (c) no se cumplen. Con estos datos, la confianza no ordena el acierto y las alertas no doblan la frecuencia de
   caídas. El pre-registro no fija qué hacer en ese caso.

## Corrección del 6-nov-2026 (después de la decisión)

Al implementar F16 apareció un fallo de la capa de corte en dos empresas del control. TM (ADR 1:10) tomaba las
acciones ordinarias de EDGAR en lugar de las equivalentes del ADR, y su capitalización salía ×10. SKYD tomaba 1.000
acciones de la portada de la entidad recién creada. Las dos se recapturaron y se rehicieron las corridas A, B y A14.
Las cifras de arriba ya están corregidas: A pasa de +11,7 a +11,8 pp y supera a L1 por 0,13 pp en lugar de 0,01. El
empate práctico y la decisión no cambian; (b) y (c) siguen sin cumplirse.

## Decisión del usuario (6-nov-2026)

«Empate: aplicar §8». El criterio (a) se trata como empate con L1: la valoración se simplifica hacia L1 (P/E de doce
meses relativo a la mediana de su sector GICS, por tercios) y el motor queda para calidad, alertas y lectura. No se abre
otro ciclo de ajustes de precio.
