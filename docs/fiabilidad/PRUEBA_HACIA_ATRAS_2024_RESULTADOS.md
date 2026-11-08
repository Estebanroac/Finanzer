# Prueba hacia atrás del motor · segundo corte (5-nov-2024) · resultados (medido el 7-nov-2026)

Reglas: `PRUEBA_HACIA_ATRAS_2024_PREREGISTRO.md` (commit `fb462f11`, anterior a cualquier captura), que remite punto por
punto al de 2025, más su **desviación 1** (commit `ade6a5a2`). Datos: `archivo-historico/evidencias-de-pruebas/
hacia_atras_2024-11-05/`. Lo «corregido» está en `corridas/`, `metricas.json`, `empresas_410.csv`, `c123.json`,
`c2_criterio.json` y `fixtures_relleno/`; lo «tal cual», en `corridas_tal_cual/` y `*_tal_cual.*`. Pp = puntos
porcentuales frente al SPDR del sector. **Decide el control (300).**

## La desviación 1, en breve

Yahoo solo sirve hoy los cuatro últimos ejercicios anuales (2022–2025). Cortados al 5-nov-2024 quedaban dos o tres, y
el motor necesita cuatro para medir el crecimiento. En el control, 261 de 287 análisis perdían «Crecimiento», frente a
18 de 293 en 2025. Corrección decidida por el usuario: completar los ejercicios 2020–2021 con SEC EDGAR presentado antes
del corte.

- Cada campo se rellena solo si coincide con Yahoo en el ejercicio común (±3 % o ±5 %).
- **Orden de los hechos**: el script se escribió y se ejecutó antes de commitear la desviación. Se commiteó sin
  cambios (sha256 en el pre-registro).
- **Alcance**: 507 de 523 empresas reciben uno o dos ejercicios. No se pudo con 16:
  - sin historia en EDGAR: AMTM, BLK, GEV, PARA, SOLV y SW;
  - sin el ejercicio anterior: ARM, BG, DEO, GEHC y VLTO;
  - con cinco o más años ya: MUFG, RY, SMFG y TM;
  - VMRK, sin ningún campo que coincida.
- **Comprobaciones**:
  - Los valores coinciden con los publicados: KO 2020 (ingresos 33.014 M, BPA 1,79, caja libre 8.667 M) y AAPL FY2021
    (365.817 M, BPA 5,61).
  - El BPA de TSM se rechaza: Yahoo lo da por ADR y EDGAR por acción.
  - La fecha añadida más reciente es el 31-oct-2021.
- **Resultado**: pierden «Crecimiento» 33 de 287 (2025: 18). La cobertura queda alta / media / baja en 20 / 213 / 54
  (2025: 57 / 201 / 35). Los balances no se completan, por eso sigue algo por debajo de 2025.
- **El precio de C no dependía del fallo**: la referencia L1 construida al corte sale idéntica antes y después.

## Veredicto (control)

| Criterio | Tal cual | Corregido | ¿Cumple (corregido)? |
|---|---|---|---|
| (a) A: barata − cara ≥ 5 pp y mejor que L1 y L2 | +3,0 pp | **−2,3 pp** (IC −15,5 a +10,4) | **No** |
| (b) A: acierto alta > media > baja | todas «baja» | sin «alta»; media 60 % (87) · baja 57 % (91) | **No** (no ordena) |
| (c) A: alertas ≥ 2 × sin alerta | × 1,27 | × 1,21 (65,4 % frente a 54,2 %) | **No** |
| C1: D(C) frente a L1 y L2 | C +1,2 · L1 +2,5 · L2 −8,6 | **igual** | (informa) |
| C2: caída ≥ 40 % ≥ 1,5 × con alerta, también sin tecnología | × 1,44 (n = 22) | **× 0,63** (n = 54); sin tec × 0,55 | **No** |
| C2, los dos cortes juntos | — | **× 1,37**; sin tec × 1,33 | **No** |
| C3: acierto por consistencia | 60 % (15) frente a 51 % (172) | 55 % (97) frente a 48 % (90) | (informa) |

**Lectura**:

- **Precio.** La L1 ordena en la dirección correcta en los dos cortes, aunque en 2024 con poca separación: +11,2 pp en
  2025 (tras corregir SMFG) y +2,5 pp en 2024. El motor anterior (A) no: −2,3 pp en 2024. La decisión de 2025 (precio =
  L1) se mantiene.
- **Alerta de valoración extrema.** **No se confirma fuera de muestra.** En 2024 las que tenían la alerta cayeron un
  40 % o más **menos** que el resto: 11,1 % frente a 17,6 %. Juntando los dos cortes, el cociente (× 1,37) no llega al
  × 1,5 fijado.
- **Confianza y alertas del motor anterior.** Siguen sin ordenar.

## (a) y C1 · rendimiento relativo medio a 12 meses (y 6), corregido

| Muestra | Método | Barata (n) | Cara (n) | D 12 m | IC95 12 m | D 6 m | Spearman 12 m | D 12 m tal cual |
|---|---|---|---|---|---|---|---|---|
| Control | A (actual) | −4,1 (34) | −1,9 (144) | **−2,3** | −15,5 / +10,4 | −4,2 | 0,06 | +3,0 |
| Control | B (sin F13) | −4,2 (34) | −1,8 (140) | −2,4 | −14,2 / +9,9 | −2,1 | 0,08 | −1,9 |
| Control | A14 (sin F15) | −5,2 (34) | −1,9 (145) | −3,3 | −15,5 / +8,2 | −3,7 | 0,06 | +0,2 |
| Control | **C (regla L1 del motor)** | +0,4 (96) | −0,8 (91) | **+1,2** | −10,5 / +13,4 | −3,4 | 0,05 | +1,2 |
| Control | **L1 · P/E relativo** | +0,8 (95) | −1,7 (90) | **+2,5** | −10,2 / +15,1 | −3,6 | 0,07 | +2,5 |
| Control | **L2 · FCF yield** | −0,7 (84) | +7,9 (83) | **−8,6** | −21,7 / +3,6 | −7,3 | −0,01 | −8,6 |
| 110 | A | −11,7 (8) | +3,5 (54) | −15,2 | −34,7 / +2,3 | −11,0 | −0,17 | −8,9 |
| 110 | C | −5,7 (27) | +0,5 (35) | −6,2 | −16,7 / +3,8 | −3,1 | −0,13 | −6,2 |
| 110 | L1 | −1,3 (28) | +1,3 (37) | −2,6 | −13,8 / +8,3 | −2,5 | −0,07 | −2,6 |
| 110 | L2 | −4,8 (32) | +9,6 (41) | −14,4 | −25,9 / −3,4 | −4,9 | −0,23 | −14,4 |

Con la corrección, A sube la confianza y contrae menos. Llama «muy exigente» a 54 del control (antes 22), y su
separación empeora. Fue un año en el que lo caro siguió subiendo (caras de L2: +7,9 pp).

## C2 · la alerta de valoración extrema, con el criterio del usuario

Criterio: la caída máxima ≥ 40 % en 12 meses debe ser al menos 1,5 veces más frecuente con alerta que sin ella, en el
total y también fuera de tecnología (GICS Information Technology). Se mide en el control.

| Corte | Con alerta | Sin alerta | Cociente | Sin tecnología: con / sin | Cociente | ¿Cumple? |
|---|---|---|---|---|---|---|
| 2025 (F1p, verificada) | 17 / 49 = 34,7 % | 37 / 244 = 15,2 % | × 2,29 | 9 / 34 = 26,5 % · 23 / 214 = 10,7 % | × 2,46 | Sí |
| 2024 corregido | 6 / 54 = 11,1 % | 41 / 233 = 17,6 % | **× 0,63** | 3 / 40 = 7,5 % · 28 / 204 = 13,7 % | × 0,55 | **No** |
| Los dos juntos | 23 / 103 = 22,3 % | 78 / 477 = 16,4 % | **× 1,37** | 12 / 74 = 16,2 % · 51 / 418 = 12,2 % | × 1,33 | **No** |

- **Comprobaciones de la definición**: la alerta salta exactamente donde A dice «muy exigente» (54 = 54). En todo el
  universo de 2024, a título informativo: 11 de 91 (12,1 %) frente a 69 de 431 (16,0 %).
- **Base de 2025**: aquí sale 15,2 % sin alerta (37 de 244). El 14,9 % que cita el texto de la alerta usaba otro
  denominador; la conclusión no cambia.

## (b), (c) y C3, corregido

- **(b)** Ninguna sale «alta». Acierto de dirección con la etiqueta de A: media 59,8 % (n = 87) y baja 57,1 % (n = 91).
  En B, media 65,1 % y baja 56,0 %. En las 110 el orden se invierte (47 % frente a 54 %). No ordena.
- **(c)** Caída ≥ 25 % en 6 o 12 meses, o recorte de dividendo:
  - A: 65,4 % con alerta (156) frente a 54,2 % sin ella (131), × 1,21.
  - B: × 1,04.
  - C, con su única alerta: 51,9 % (54) frente a 62,2 % (233), × 0,83.
  - La caída máxima mediana del control a 12 meses fue del 27 %.
- **C3** · acierto de dirección con la etiqueta de C:
  - Control: consistente 54,6 % (n = 97) frente a mixta 47,8 % (n = 90).
  - 110: 42,4 % (33) frente a 55,2 % (29).
  - Ninguna diferencia es estable.

## Cobertura

- **Universo**: 543. Capturadas al corte: 523, PARA entre ellas (excluida). **Muestra**: 410; analizadas por A, B y
  A14, 395, sin ningún error.
- **Sin análisis en la muestra (15)**:
  - 12 sin serie de Yahoo, porque dejaron de cotizar: EA y WBD (de las 110) y ANSS, CTRA, DAY, DFS, HES, HOLX, IPG, MRO,
    QRVO y WBA. Cinco se compraron dentro de la ventana; Stooq no se usa (verificación anti-bots).
  - IBN, sin estados en EDGAR.
  - TTE, la herramienta de segmentos no reproduce su corrida.
  - PARA: hoy su símbolo es otra empresa en Yahoo y en EDGAR (CIK 1826011).
- **Accesos no grabados, declarados**: ARM (índice de dos 6-K sin datos de estados; análisis idéntico) y MRNA
  (`/stock/earnings` de Finnhub, vacío al corte).
- **Rendimiento a 12 meses**: 290 del control y 108 de las 110. Sesgo de supervivencia: 12 empresas de la muestra sin
  rendimiento (2025: 5).

## Desviaciones y límites

- **Desviación 1**: el relleno con EDGAR (arriba).
- **Damodaran de enero de 2024** (enlace «1/24», archivos con sufijo 23).
  - Rf 4,28 % y ERP 4,06 %.
  - **La lista de empresas de enero de 2024 no está en el archivo de NYU.** Se usa la de enero de 2023, la última
    anterior al corte. 20 empresas quedan sin industria, AMZN entre ellas.
  - Los spreads salen de `bondspreads23` («Spread 2024»), porque `ratings23` no está.
  - «Eastern Europe & Russia» se reetiqueta como «Eastern Europe», sin tocar cifras.
  - Los textos fijos del motor dicen «enero de 2026»: es la etiqueta, no los valores.
- **Mercado al corte**: P/E mediano del S&P 500 24,8× y EV/EBITDA 16,8×, con EDGAR y el cierre del corte. El P/E
  adelantado no se usa.
- **Capturas**:
  - Cautivas (CAT, F y GM) con el companyfacts entero de su financiera.
  - `FACTS_SINCE` según el corte.
  - TEL, CDW, WRB y CINF con el companyfacts completo, que el replay vuelve a cortar por fecha de presentación.
- **Un fallo real de C**: MRNA daba un error 500 en `classify.py`, al construir el texto de «pérdidas con ventas en
  caída» con tres ejercicios. Arreglado en `5435acc6`, con prueba; solo cambia las empresas que daban el error.
- **Yahoo**: los dividendos de julio a diciembre de 2025 tienen huecos en 10 empresas. Se corrigieron con EDGAR y
  llevan la marca de rendimiento infravalorado.
- **Corte de 2025**: corregido el factor de ADR de SMFG (ver su informe). L1 del control pasa de +11,67 a +11,20 pp; la
  decisión no cambia.

## Decisiones del usuario (7-nov-2026)

- **Precio**: se mantiene la L1, porque ordena bien en los dos cortes. El texto de la etiqueta dirá «frente a su
  sector» y no sugerirá rendimiento futuro.
- **Congelar como versión 1.0.** La próxima prueba será un corte anual nuevo; no más cortes ahora.
- **C2 no cumple el criterio.** Queda por decidir qué se hace con la alerta roja de valoración extrema antes de
  congelar.
