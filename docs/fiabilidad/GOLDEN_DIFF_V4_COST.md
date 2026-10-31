# GOLDEN_DIFF_V4_COST: cambios de golden de la revisión de COST y su causa

Revisión externa del informe de COST con la v4 final (`revision-cost-2026-10-30.md`, ≈ 80/100). Para la v4 entran solo
los fallos baratos y generales: hallazgos 2, 4 y 6. Rama `rediseno/v4-cost`, desde ad178cb9. No se tocan los rivales,
la espera del PDF ni el botón «Descargar PDF» (E2b, `rediseno/v4-pdf-rapido`).

Medida en vivo del mismo día sobre las 543 empresas del universo, antes (ad178cb9) y después:
`docs/fiabilidad/v4_cost/MEDIDA.md`, con `backend/tools/v4_cost_medida.py`.

## Hallazgo 2 · BPA «sin dato» con 10 años de beneficio, y el PEG

**Causa (COST).** No es una regresión de `fiabilidad/f10-crecimiento` ni de la serie del BPA de EDGAR. Yahoo trae el
beneficio de FY2026 (cerrado el 30-ago) pero deja vacíos su BPA diluido y sus acciones diluidas medias. La serie del BPA
empezaba con un hueco y `growth_rate` exige los 4 extremos de la ventana (regla de la etapa 9a), así que salía «menos de 4
ejercicios anuales de BPA». El PEG de 4,99 era el de Yahoo, con un crecimiento de consenso que el informe no mostraba.

**Regla 1, el BPA** (`lib/edgar_backup._apply_fy_eps`):

- un ejercicio sin BPA diluido toma el de EDGAR (`annual_history`: ejercicios enteros, ajustados por splits);
- si el emisor no etiqueta el BPA, beneficio neto ÷ acciones diluidas medias, también de EDGAR;
- nunca sustituye un BPA de Yahoo, y se declara en `data_provenance.edgar.backup.fy`;
- la serie no mezcla bases: en el ejercicio común más reciente, el BPA de EDGAR tiene que cuadrar con el de Yahoo
  (`history_eps_abs_tol`). Si no cuadra, no se completa y se dice. TM: 2,36 en EDGAR frente a 23,60 en Yahoo.

**Regla 2, el PEG** (`main.py`): en todos los arquetipos en que aplica, el PEG es P/E ÷ el crecimiento del BPA que el
informe muestra en Crecimiento, y su rótulo lo nombra: «PEG (BPA a 3 años)» o, en el cíclico, «PEG (BPA de ciclo
medio)». Desaparecen el PEG de la fuente (crecimiento de consenso) y el PEG trailing del motor. Es no significativo,
con su motivo, si:

- el informe no muestra un crecimiento del BPA;
- ese crecimiento es ≤ 0;
- el P/E es ≤ 0 (pérdidas).

Un PEG no significativo no cuenta como componente ausente. Las alertas del PEG hablan del crecimiento del BPA, no del
«previsto».

**Golden** (panel y local):

| Empresa | Antes | Después | Puntuación |
|---|---|---|---|
| AAPL | PEG de la fuente 2,55 | 5,72 (BPA 6,9 % a 3 años) | Igual: los dos, «muy caro». La alerta «PEG elevado» cae porque un PEG > 5 se trata como artefacto (`alerts.peg.artifact_above`, regla anterior) |
| PG | 4,30 | 6,04 (BPA 3,9 %) | Igual, «muy caro» |
| V | 1,90 (panel) / n.s. (local) | 2,49 / 2,45 (BPA 13,4 %) | Tramo del bloque |
| KO | n.s. (la fuente no cuadraba con el informe) | 2,39 (BPA 11,6 %) | Entra en el bloque |
| JNJ | n.s. | 1,64 (BPA 17,9 %) | Precio 20 → 15, mismo nivel |
| NFLX | n.s. | 0,61 (BPA 36,5 %) | Entra en el bloque |
| AMZN | 0,92 de la fuente | n.s.: BPA inicial ≤ 0 | Precio 28 → 24, mismo nivel |
| PLTR, CRWD | 1,49 / 5,60 de la fuente | n.s.: BPA inicial ≤ 0 | — |
| TM | 1,24 de la fuente | n.s.: «menos de 4 ejercicios» | El BPA de EDGAR no cuadra con el de Yahoo y no se mezcla |
| UL, MC.PA | — | n.s.: BPA ≤ 0 (−1,7 %, −8,0 %) | — |

Ningún golden cambia de nivel de calidad ni de precio.

**En el universo** (543 empresas, `v4_cost/MEDIDA.md`):

- cambia el PEG en 253 y su tramo en 198;
- cambia el nivel de precio en 30 (más LEN, deriva entre los dos escaneos);
- cambia la calidad mostrada en 5, solo por la confianza (la calidad cruda no se mueve).

El movimiento está acotado: desde F10 · N4 el PEG es solo una parte del voto único de los múltiplos del BPA. Decisión
del PM (30-oct): la regla completa. Los PEG de la fuente con un crecimiento que el informe no muestra son los datos poco
creíbles que el usuario no quiere. Los cinco casos que más se ven:

| Empresa | PEG antes | PEG después | Precio | Por qué |
|---|---|---|---|---|
| NFLX | n.s. (F8 · E4) | 0,49 propio | razonable 60 → atractivo 69 | La fuente (0,98) suponía un BPA del 18,4 % frente al 36,5 % del informe: era n.s. y no votaba. Con el propio, «muy atractivo», entra en el bloque (+3 → +4); la confianza sube de baja a media y contrae menos |
| TDY | n.s. (F8 · E4) | 6,64 propio | exigente 38 → muy exigente 20 | La fuente (1,40) suponía un BPA del 21,5 %; el del informe es del 4,5 %. Con el propio, «muy caro», entra en el bloque (−1 → −2); la confianza sube a alta y ya no contrae hacia 50 |
| BMY | 17,02 de la fuente | n.s.: el BPA cambia de signo | razonable 58 → atractivo 65 | Un PEG «muy caro» con un crecimiento de consenso que no se ve; sin él, el bloque de 4 múltiplos sube de +3 a +4 |
| BP | 0,05 de la fuente | n.s.: BPA inicial ≤ 0 | atractivo 72 → razonable 62 | Un PEG de 0,05 (crecimiento de consenso de casi el 500 %) puntuaba «muy atractivo»; sin él, el bloque baja de +4 a +3 y la confianza, a baja |
| ECHO | 1,33 de la fuente | n.s.: P/E ≤ 0 | razonable 50 → no concluyente | Era su único componente de Valoración evaluable: un PEG con el P/E negativo. Sin él, el precio no tiene base y lo dice |

## Hallazgo 4 · la contracción del precio hacia 50

**Lo que hacía el código.** Contraía con la confianza previa al escalón de las tasas base (F10 · N4): el escalón no
contraía nunca, apuntara adonde apuntara el veredicto. Los demás limitadores (convergencia, cobertura, fuente,
estabilidad, dependencia de Ke, fuente oficial) vuelven incierto el veredicto y contraen siempre.

**La regla escrita.** Solo contraen los limitadores que contradicen el veredicto o lo vuelven incierto. El escalón de las
tasas base apunta a «caro»:

- con un precio crudo por debajo de 50 no contrae, porque contraer lo acercaría a 50 y lo haría más atractivo (COST);
- con un precio crudo por encima de 50 lo contradice, y entonces sí contrae.

Ese segundo caso faltaba: lo cubre `verdict.price_contraction_basis`. En el escaneo de la puerta no había ninguno; en el
de hoy, uno (TSM, 55 → 54).

**Texto.** La regla se escribe una vez (`display.contraction_text`) y la usan:

- la web (`display.summary.composition.caption`, la metodología de Conclusión);
- el PDF actual y el v2 (introducción de Metodología);
- el PDF v2, además, en el punto «Atractivo del precio», con los ejemplos de cada tipo de limitador.

**Golden.** Cambia el texto de la metodología en las 42 empresas. No cambia ninguna cifra: ningún golden tiene el escalón
con un precio crudo por encima de 50.

## Hallazgo 6 · menores

**Una sola cifra del valor DCF.** COST mostraba «$470» en la fila del valor justo y en el gráfico (`numfmt.estimate`, dos
cifras significativas, F8 · P3), y «$468» en la alerta y en la casilla base de la sensibilidad (`numfmt.whole`). Ahora
usan todos `numfmt.estimate` sobre `dcf.fair_value`: la alerta del DCF, las casillas de la tabla de sensibilidad y los
extremos del gráfico. Contrapartida: dos casillas vecinas pueden coincidir (MC.PA: 226 y 231 → 230).

| Empresa | Ejemplo |
|---|---|
| AAPL | alerta $116 → $120; casillas $119 → $120, $139 → $140 |
| MSFT, XOM, CAT, DOW, NVDA, TSM, ASML, SHEL, MC.PA… | casillas a dos cifras |

El panel de escenarios de la web usa el mismo redondeo (`format.estimateCur`, la réplica de `numfmt.estimate`) en el
valor por acción, la barra y la tabla de sensibilidad. El valor del DCF tiene una sola cifra en toda la web y en el PDF;
la tabla del teléfono ya no necesita una versión sin decimales.

**El Altman referencial no abre Riesgos.** El resumen de Solidez, que abre el capítulo Riesgos del PDF, empezaba por
«Altman Z de 2.86 (zona segura)» aunque el Altman no puntúa en la industria de COST. Con
`business_model.altman_referential`, abre la cobertura de intereses (o la deuda) y el Altman va al final, «solo como
referencia: no puntúa», coherente con su fila. Cambia en CAT, AMZN y TM.

**Margen de seguridad con una precisión razonable.** Fuera de ±100 % (`[dcf_display]
margin_of_safety_shown_bounds`), la fila muestra «< −100%» (o «> +100%») y la cifra exacta va en el detalle. Cambia en:

- AAPL (−197 %), MSFT, FCX, MU, PLTR, CRWD y ASML;
- 110 empresas del universo.

## Fuera de la v4 (para después)

- **Hallazgos 1 y 3** (rentabilidad sobre el capital en los negocios de alta rotación; arrendamientos frente a Damodaran)
  y **5** (rivales): no son baratos y no entran.
- **BPA sin completar con EDGAR.** Siguen «menos de 4 ejercicios»:
  - TM: el BPA de EDGAR no cuadra con el de Yahoo, con un factor 10;
  - CSCO, HDB, MUFG y SMFG.
