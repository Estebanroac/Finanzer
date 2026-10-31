# F8 · P3 (auditoría externa del 26-oct-2026, «Presentación») — Registro

Rama `fiabilidad/f8-p3` (worktree `../finanzer_next-f8p3`), desde `fiabilidad/f8-auditoria` en 1c8a4178 (con E8 y E9).
No toca la puntuación ni la confianza (E11 es de E2a). Los cambios de golden van en `GOLDEN_DIFF_F8_P3.md`: un archivo
aparte para no chocar con el `GOLDEN_DIFF_F8.md` que E2a edita en su rama.

Evidencia: análisis reales del 27-oct-2026 de MCD, MSFT, CB y MRNA (con el código de esta rama) y golden del panel.

---

## 1 · ROE no significativo con patrimonio ≤ 0 (MCD)

**Evidencia (se reproduce):** MCD tiene un patrimonio de −1.022 millones y un ROE de −859,8 %. Sale con dos decimales en:
la portada (KPI «−859.78%»), las tarjetas del resumen (con una brecha frente a la industria de «−859885%»), la tabla de
rentabilidad, el desglose de la puntuación, el gráfico de rentabilidad y la comparación con la industria. La puntuación
ya lo neutralizaba: ajuste 0, «ROE negativo por patrimonio negativo (recompras) — no penalizado; ROA 14,7 % sólido».

**Arreglo:**
- **Regla M** en `validate.validate_outputs`, la misma de la cobertura de intereses y de la deuda neta/EBITDA: con
  patrimonio ≤ 0, el ROE se anula en `key_metrics` y `ratios` y se marca `ratio_no_significativa` con su motivo. Corre
  después del score, así que **la puntuación no cambia**. La marca no entra en la confianza (`source_ignored_rules`).
- **Presentación:**
  - La portada (KPI) y la tabla de rentabilidad dicen «No significativo» con el motivo.
  - El desglose de la puntuación muestra «n.s.» en lugar de la cifra (el ajuste sigue en 0).
  - El gráfico de rentabilidad lo pinta como no significativo.
  - La comparación con la industria y las tarjetas del resumen dejan de mostrar la cifra y la brecha.
- **Resultado en vivo (MCD):** ninguna salida contiene ya −859,8 % ni la brecha de −859.885 %. La puntuación de
  Rentabilidad sigue en 20/20 y el veredicto no cambia («Calidad excelente · precio razonable»).
- **Golden:** ninguno cambia (ninguna empresa del panel ni del juego local tiene patrimonio ≤ 0).
- **Tests:** `tests/test_p3_presentacion.py` (con patrimonio negativo, no significativo con su motivo; con patrimonio
  positivo, no cambia). Suite completa: 5.690 tests correctos.

---

## 2 · Valor justo redondeado con su rango y margen de seguridad oculto si el DCF es de fiabilidad baja

**Evidencia (se reproduce):**
- El margen de seguridad sale con dos decimales en todos los DCF, también en los de fiabilidad «baja» (la de E8). En
  el panel: CAT «−193.69%» y DOW «−309.40%», con fiabilidad baja.
- El valor justo sale al céntimo: AAPL «$116.08», sobre una tabla de sensibilidad que en su bloque central va de 88 a
  156 $.
- El motor **no tiene un p10–p90**: no hay una distribución de la que sacar percentiles.

**Arreglo** (en la tabla de valor intrínseco del informe, en la web y en las frases que citan el valor):
- **Valor justo a dos cifras significativas** (`numfmt.estimate`): $116.08 → «$120», $7.13 → «$7.1».
- **Rango del bloque central de la tabla de sensibilidad** (`display.dcf_central_range`): el caso base ± una casilla,
  que es la misma ventana con la que E8 mide la dispersión (crecimiento ± 2,5 pp y WACC ± 1 pp). Se declara como lo que
  es: «rango $88–$160 en el bloque central de la tabla de sensibilidad (crecimiento ± 2,5 pp y WACC ± 1 pp; mínimo y
  máximo, no un p10–p90)».
  - Va en el texto de la fila del valor justo y en el gráfico de la web (`charts.valuation.fair_value.central_*`): en
    la leyenda, «Bloque central $88–$160», junto al rango de toda la tabla, que ya se mostraba.
  - La web añade la frase «Valor $120: rango … ».
- **Margen de seguridad:**
  - Con fiabilidad baja, «No significativo» con el motivo: «el DCF es de fiabilidad baja (…): su margen de seguridad
    no es una cifra que leer».
  - Con fiabilidad media o alta, a la unidad: «−195%» en lugar de «−195.45%».
- `central_text` se declara como fragmento en `lib/prose.py` (la web lo cierra) y el motivo del margen, con la
  afirmación `dcf_rel` del guardián.

**No cambia:** el valor, el upside, la puntuación, la confianza ni el veredicto. Solo cambia `display` (comprobado: el
diff de los golden no toca nada fuera de `display`).

**Tests** (`tests/test_p3_presentacion.py`):
- Dos cifras significativas.
- Rango del bloque central de AAPL, con su declaración.
- CAT y DOW: margen «No significativo» con el motivo.
- AAPL: «$120» y «−195%».

Suite completa: 5.693 tests correctos.

---

## 3 · Una sola ventana de fuerza relativa, la de la tabla de rentabilidades

**Evidencia (se reproduce):** la auditoría vio en MSFT «+3,2 % frente a +29,6 %» en un sitio y «+1,0 % frente a
+25,3 %» en otro, los dos «a 12 meses». Son dos reglas distintas:
- la señal de fuerza relativa (`market_signals.relative_strength`) contaba 252 **sesiones** hacia atrás;
- la tabla de rentabilidades de la web y del PDF (`lib/price_returns.py`) cuenta 365 **días naturales** desde la
  última sesión de la empresa, con cierre ajustado.

En vivo, el 27-oct-2026: la tabla da MSFT +1,0 % frente a XLK +27,4 %, y la señal, +2,9 % frente a +30,0 %.

**Arreglo:**
- La señal usa ahora la regla de la tabla: `price_returns.start_of` y `period_return` sobre los cierres de la empresa y
  del ETF, desde la última sesión de la empresa.
- Las ventanas pasan a ser las de la tabla, por su clave: `market.signals.relative_strength.windows = ["6M", "1A"]`
  (antes `windows_sessions = [126, 252]`). La que se muestra es la última (1A), con la etiqueta de la tabla
  (`range_labels`): «Fuerza relativa frente a XLK (1 año)».
- Si una de las dos series no cubre el periodo, esa ventana queda `historia_insuficiente`, como en la tabla.

**Resultado en vivo (MSFT):** la señal da +1,1 % frente a +27,3 %, y la tabla, +1,0 % frente a +27,4 %. La diferencia
que queda (≤ 0,1 pp) no es de regla. La señal se alimenta de la serie de `price_history.peek` y `price_history.sector`,
y la tabla, de `price_history.chart`: son dos descargas distintas, que pueden diferir en la última sesión o en el ajuste
por dividendos. En el replay, SHEL y TM coinciden exactamente. AAPL y otras difieren 1–2 pp porque sus fixtures de las
dos series se grabaron en fechas distintas.

**Pendiente (anotado, fuera de P3):** que la señal y la tabla lean una misma serie descargada una vez.

**No cambia:** la puntuación, la confianza ni el veredicto. La fuerza relativa es informativa: solo cambian
`market_context` y `display`.

**Tests:**
- `tests/test_market_signals.py`: ventanas por días naturales, configuración e historia corta.
- `tests/test_market_context.py`: referencia a 365 días.
- `tests/guardian.py`: usa la última ventana de la configuración.
- `tests/test_p3_presentacion.py`: la señal y la regla de la tabla dan la misma cifra con la misma serie.

---

## 4 · Nota del Piotroski condicionada al dato de la empresa

**Evidencia (se reproduce):** `business_model.piotroski_caveat` dependía solo de la industria. A todas las de
circulante negativo estructural les ponía la misma nota: «En esta industria los criterios de liquidez (current ratio)
y de margen bruto informan poco: el capital circulante negativo y su estructura de márgenes son propios del modelo de
negocio». En el panel salía en 8 empresas y solo en 2 la respaldaba el dato:

| Empresa | Current ratio | ¿Lo justifica el dato? |
|---|---|---|
| PG | 0,68x | sí |
| UL | 0,79x | sí |
| SNOW | 0,94x | no: empeora frente a su historia (`worsening`), no es estructural |
| AMZN | 1,18x | no |
| MSFT | 1,23x | no (el caso de la auditoría) |
| KO | 1,30x | no |
| CRWD | 1,57x | no |
| PLTR | 7,23x | no |

La parte de los márgenes era genérica en todas: no se comprobaba nada de la empresa.

**Arreglo:**
- `piotroski_caveat(cr_ctx, current_ratio)` usa la misma regla que ya decide si el current ratio < 1 se lee como
  estructural en la puntuación y en las alertas (`current_ratio_context.applies`): industria de circulante negativo
  estructural, current ratio < 1 y sin empeorar frente a la mediana de sus ejercicios anteriores.
- El texto cita su dato: «Su current ratio es 0.68x: por debajo de 1, como es propio del modelo de negocio de su
  industria (capital circulante negativo), así que el criterio de mejora de la liquidez informa poco en esta empresa.»
- La frase genérica de los márgenes se quita.

**No cambia:** la puntuación, la confianza ni el veredicto. La nota solo va en el texto de la tarjeta del Piotroski.

**Tests:**
- `tests/test_p3_presentacion.py`:
  - con dato que la justifica, la nota sale y cita su cifra;
  - no sale con 1,23, con 7,2, empeorando ni en una industria sin circulante negativo estructural;
  - en el panel, solo PG y UL la llevan.
- `tests/test_business_model.py`, adaptado a la nueva firma.

---

## 5 · Etiquetas coherentes: β de CB y crecimiento de MRNA

### β de CB

**Evidencia (se reproduce, en vivo el 27-oct-2026):**
- El motivo del P/B y del P/TBV justificados decía «(Ke 7.4% con β ajustada 0.48, g 2.5%)».
- La nota del Ke y la tabla del WACC decían «β media de la industria 0.48 [Damodaran, enero de 2026; sin Blume: es una
  media de industria]».
- La beta de CB es la de su industria (`beta.source = "sector"`), que entra ya ajustada, sin Blume.
- En el panel les pasa lo mismo a PGR (aseguradora, como CB: el mismo «Ke 7.4% con β 0.48») y a BRK-B (0,67).

**Arreglo** (`financial_ratios`, motivo del P/B y del P/TBV justificados):
- La etiqueta dice qué beta entra: «β ajustada» solo si se aplicó Blume (`archetype_metrics.beta_raw` no es None).
- Si no, dice «β de la industria 0.48, sin Blume».
- El valor no cambia.

**Resultado en vivo (CB):** «(Ke 7.4% con β de la industria 0.48, sin Blume, g 2.5%)», coherente con la nota del Ke.

### Crecimiento de MRNA

**Evidencia (se reproduce, en vivo):**
- Crecimiento de MRNA tiene 6 puntos, pero no es concluyente: 1 de 3 componentes con dato (cobertura 33 %).
- Por eso queda fuera de la calidad («Calidad calculado sobre 3 de 4 categorías (Crecimiento no concluyente)»).
- Aun así, la portada del PDF nuevo (`pdf_v2/cover.py`) y la cabecera web (`CompanyHeader`) mostraban «6 / 20».
- También lo mostraban las barras del capítulo «Qué tan buena es la empresa» (`ChapterVisual`) y la tabla del desglose
  (`BreakdownTable`), que lo seguía de «no concluyente».
- Las barras de categorías del PDF nuevo y el desglose del PDF ya decían «no concluyente» / «n/c».

**Arreglo:**
- El motor fija cómo se muestra la puntuación de cada categoría (`display.category_score_txt`). El campo `score_txt` va
  en `cover.categories[].items[]` y en `sections.institutional.breakdown.categories[]`: «12 / 20» si es concluyente y
  «no concluyente» si no.
- Lo usan la portada del PDF nuevo y, en la web, la cabecera (desgloses de calidad y precio), las barras del capítulo
  (barra vacía) y la tabla del desglose (su texto «No concluyente (cobertura 33 %): excluida …» en lugar de los puntos).
- En el desglose, el tono de una categoría no concluyente pasa a neutro, como ya era en la portada.

**Resultado en vivo (MRNA, PDF nuevo):** la portada y el resumen dicen «Crecimiento · no concluyente». Ninguna salida
enseña los 6 puntos de una categoría que no cuenta.

**No cambia:** la puntuación, la confianza ni el veredicto, ni el valor de ninguna beta. Solo cambian textos.

**Tests** (`tests/test_p3_presentacion.py`):
- PGR y BRK-B dicen «β de la industria … sin Blume»; BAC y JPM (beta propia) siguen con «β ajustada».
- `category_score_txt` y la muestra forzada `SNOW_no_concluyente`: «no concluyente» y tono neutro en la portada y en el
  desglose.

---

## 6 · Clasificación del anexo: una sola etiqueta y frases completas (repaso de E2b)

**Evidencia (se reproduce):** en el anexo técnico (`display.annex`), cada línea del detalle de la clasificación llevaba
su propia etiqueta «Clasificación». La segunda empezaba en minúscula, porque los avisos de `classify` están escritos
para ir dentro de otra frase. En el panel, HSBC:
- «Clasificación: Arquetipo FINANCIAL (…) (banco)»
- «Clasificación: su historia (11 ejercicios en EDGAR) muestra ciclo: …»

A RIVN le pasa lo mismo, con «Posible cíclica: …».

**Arreglo:**
- Una sola entrada «Clasificación» con el arquetipo y sus avisos unidos por `prose.sentences`. Cada frase lleva
  mayúscula inicial y su punto, también tras un paréntesis: «(banco). Su historia …».
- `prose.py` declara los textos del anexo (`.annex.items[].text`) como frase.

**Tests:**
- `prose.sentences` (mayúscula, punto tras paréntesis, vacío).
- HSBC, RIVN y AAPL: una sola «Clasificación» y cada frase con mayúscula y punto.
