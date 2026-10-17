# F7 · Calibración histórica (estudio, no ajuste) y revisión de parámetros

> Fase 7 del plan de fiabilidad (PLAN_FIABILIDAD §4, puntos 2 y 3). Rama `fiabilidad/f7-calibracion`, que sale de
> `fiabilidad/f6-infra` (worktree `../finanzer_next-f3`). **Nada subido.** Hecha bajo la delegación del usuario
> (registro #29). El plan dice que este estudio "termina con un informe y decisiones del usuario": las decisiones
> están en §6. **No se ha cambiado ningún umbral del motor con él.**
>
> **Versión 2**, tras la revisión independiente (§9). La primera versión tenía una fuga de información futura: los
> precios de cada fecha venían ajustados por splits posteriores (WMT a un tercio de su precio). También tenía
> ejercicios mal construidos. Esos fallos hacían salir validada a H3a. Esta versión los corrige y añade dos
> comprobaciones de robustez.

## 0. Resumen

| Hipótesis (fijadas antes de correr: `3ef8c8f`) | Regla prerregistrada | Robustez (empresa × año; neto de sector × año) |
|---|---|---|
| H1 · Calidad "excelente" anticipa que el ROE se mantenga (a 3 años, ≥ 75% del propio) | −3.8 pp (IC 90%: −12.2 a +3.9): **no concluyente** | no |
| H2 · Calidad "excelente" anticipa menor caída máxima a 3 años | +3.8 pp en mediana (IC 90%: +0.7 a +7.6), signo en las 4 mitades: **validada** | **no**: empresa × año −0.8 a +9.2; neto de sector × año +0.6 pp (−0.1 a +3.5) |
| H3a · Precio "muy exigente" anticipa peor rentabilidad frente al S&P 500 a 1 año | −9.2 pp (IC 90%: −12.9 a +0.7): **no concluyente** | no |
| H3b · Lo mismo a 3 años | +2.3 pp (IC 90%: −12.7 a +10.7): **no concluyente** | no |

Lectura de analista:

- **Ninguna escala anticipa de forma robusta lo que pasará con la cotización.** Con la regla fijada, la calidad "excelente" sale con menor caída (H2). Pero el efecto se explica casi entero por el sector y el año: las financieras de 2012–2014 pesan mucho en el contraste. Neto de sector y año, queda en +0.6 pp.
- **"Muy exigente" va unos 8–9 pp por detrás del índice a 1 año** en la mediana, con el signo en las cuatro mitades. Pero son 66 casos de 30 empresas y el IC toca el 0. Es una señal débil, no una regla demostrada.
- **La app no promete rentabilidades:** ningún texto dice que la acción vaya a batir al mercado (comprobado), y el estudio respalda esa prudencia. Calidad y precio describen el negocio y lo que el precio exige hoy; no son previsiones.
- **La persistencia relativa del ROE no se valida** (H1). El nivel sí persiste (§3, exploratorio), pero es casi mecánico: el nivel de calidad ya refleja el ROE de partida.

## 1. Diseño

**Muestra:** 100 empresas de EE. UU. fuera del panel, 11 sectores (lista en `tests/calibracion_datos.py`). Se pierden
dos por la tabla de la SEC (EQR y AVB) y siete ejercicios de DIS (cambio de CIK en 2019). El resultado son **965
análisis de 98 empresas**, una vez por ejercicio de 2012 a 2021.

**Fecha de cada análisis (D):** el día siguiente al 10-K que presentó el ejercicio, siempre que llegara en los 120
días tras el cierre. El motor ve lo que se sabía ese día:

- **Estados:** construidos desde los hechos XBRL de EDGAR presentados hasta D, con las filas de Yahoo, ejercicios anuales de verdad y sin las reexpresiones posteriores.
- **Cotización:** el cierre de D tal como se veía ese día, sin los splits ni las escisiones posteriores. Las acciones salen de la portada del 10-K.
- **Series:** dos años hasta D de la empresa, del S&P 500 y del ETF de su sector, en la misma base.
- **EDGAR:** cortado en D.
- **Rf:** ^TNX de D, entre 0.54% y 3.23% en la muestra.

**Motor:** el real (`_compute_analysis`) en replay, sin cambios (`tests/calibracion_ejecutar.py`).

**Resultados medidos después de D:**

- rentabilidad total (cierre ajustado) frente a SPY a 1 y 3 años;
- caída máxima a 3 años;
- ROE del ejercicio (el conocido en D) y de 3 ejercicios después.

**Regla de decisión** (fijada antes): muestras de entrenamiento y prueba por periodo (2012–2016 / 2017–2021) y por
empresa (mitades alternas), con IC del 90% por bootstrap por empresa. "Validada" exige el signo en las cuatro mitades
y un IC que excluya 0.

**Robustez** (añadida tras la revisión): bootstrap de dos vías, que remuestrea empresas y años y recoge el choque
común de cada año, y la métrica neta de la mediana de su sector y año. Una hipótesis es "robusta" si está validada y
además las dos comprobaciones excluyen 0.

## 2. Resultados por nivel (descriptivo)

| Escala | Nivel | n | ROE persistente (≥ 75%) | Caída máx. 3 años (mediana) | Frente al S&P 500, 1 año (mediana) | Ídem, 3 años |
|---|---|---|---|---|---|---|
| Calidad | excelente | 419 | 70.8% | −30.4% | +1.4% | +0.1% |
| | sólida | 309 | 75.9% | −29.7% | +0.3% | −2.2% |
| | media | 163 | 72.9% | −31.7% | −2.7% | −9.1% |
| | débil | 74 | 80.8% | −36.4% | +3.6% | +2.5% |
| Precio | atractivo | 334 | 65.9% | −30.7% | −1.3% | −1.6% |
| | razonable | 361 | 76.9% | −29.6% | +2.1% | −4.5% |
| | exigente | 167 | 80.2% | −31.2% | +0.3% | −4.6% |
| | muy exigente | 66 | 76.7% | −34.2% | −8.1% | −0.6% |

Sin precio: 37 casos, en los que la valoración no fue evaluable. Precio sin contraer por la confianza: "muy
exigente", −4.4% a 1 año; "atractivo", +1.1%. "Atractivo" no se distingue de "razonable".

## 3. Exploratorio (añadido tras ver H1; no decide)

La medida de H1 compara el ROE con el propio, así que castiga a los ROE altos por la reversión a la media. El nivel:

| Calidad | n | ROE del ejercicio (mediana) | ROE 3 años después (mediana) | 3 años después ≥ 15% |
|---|---|---|---|---|
| excelente | 319 | 25.8% | 28.0% | 72.7% |
| sólida | 216 | 16.6% | 20.7% | 62.0% |
| media | 103 | 10.2% | 12.7% | 42.7% |
| débil | 52 | −0.1% | 10.3% | 36.5% |

Es casi mecánico: la escala parte de ROE distintos. No demuestra que la escala aporte algo más allá del ROE de hoy;
solo que la rentabilidad alta tiende a seguir siendo alta.

## 4. Bandas de REIT y utilities (F4_PARADA §5)

`tests/calibracion_bandas.py`: 26 REIT y 25 utilities de EE. UU., unos 350 empresa-año cada grupo (2012–2025; hechos
de EDGAR de hoy y precio de Yahoo del cierre de cada ejercicio, sin los splits posteriores). El criterio se fijó
antes de mirar: la mediana en el tramo neutro o en uno contiguo, y ningún tramo extremo con más del 40%.

| Arquetipo | Métrica | Mediana | Reparto por tramo | Veredicto | Lectura |
|---|---|---|---|---|---|
| UTILITY | deuda neta/EBITDA | 5.1x | 37 / 26 / 24 / 8 / 5% | bien centrada | "PROVISIONAL" fuera del comentario de config |
| UTILITY | cobertura de intereses | 2.9x | 24 / 43 / 22 / 6 / 5% | bien centrada | ídem |
| UTILITY | rentabilidad por dividendo | 3.4% | 5 / 22 / 46 / 25 / 3% | bien centrada | ídem |
| REIT | P/FFO | 17.2x | 18 / 22 / 28 / 20 / 12% | bien centrada | ídem |
| REIT | FFO/ingresos | 53.7% | 40 / 17 / 18 / 21 / 4% | en el límite (tramo alto 40%) | se mantiene |
| REIT | deuda neta/EBITDA | 5.3x | 40 / 39 / 12 / 7 / 2% | en el límite (tramo bajo 40%) | sigue PROVISIONAL: parte de la cola baja es deuda que el estudio no capta (los REIT la etiquetan de muchas formas) |
| REIT | FFO/patrimonio contable | 15.2% | **82%** / 12 / 4 / 2 / 1% | **satura** | decisión del usuario (§6) |
| REIT | dividendos/FFO | 0.60 | 78 / 13 / 5 / 5% | satura | es una prueba de cobertura del dividendo, no un ranking: se mantiene |

FFO/patrimonio contable da +6 al 82% de los REIT: es un bono casi constante. Recalibrarlo por quintiles no lo arregla.
O (Realty Income) pasaría de +6 a −6 porque emite acciones por encima del valor contable, y eso le agranda el
patrimonio. La métrica premia el apalancamiento y los activos viejos y amortizados, no la calidad.

## 5. Límites del estudio

- **Supervivencia:** son empresas que existen hoy. Las que quebraron o fueron absorbidas no están, y eso favorece a la muestra (más a "débil").
- **No es point-in-time** en:
  - la prima de riesgo (4.20% de octubre de 2026);
  - las medianas y umbrales sectoriales de config;
  - las tasas base (1984–2020);
  - el sector y la industria de hoy (TGT no tiene sector en la búsqueda: sin referencias sectoriales);
  - sin Finnhub.

  Esto **sí cambia de nivel a observaciones concretas**. Los niveles son bandas absolutas, y con una prima de 4.20% y Rf de 0.5–3%, el coste del capital de 2012–2016 sale bajo y la valoración, más "atractiva": el 45% de 2012 frente al 24% de 2016–17. Es una de las razones para no sacar conclusiones del precio con este estudio.
- **Estados desde EDGAR:**
  - EBIT aproximado (beneficio antes de impuestos + gastos financieros) donde el emisor no etiqueta el operativo;
  - sin desglose de partidas inusuales;
  - el patrimonio del ordinario sin restar preferentes.
- **Dependencia:** las ventanas de 3 años se solapan y los choques de mercado son comunes. Por eso se añadió el bootstrap de dos vías.
- **Tamaño:** solo 66 casos "muy exigente", de 30 empresas.
- **Prerregistro:** las hipótesis y la regla están en `3ef8c8f`, anterior a la primera corrida del motor sobre esta muestra en esta sesión. Git solo prueba el orden de los commits, no que no se mirara antes. Después se corrigieron las entradas (EBIT y deuda en `df1fdf5`, antes del primer análisis; precios y ejercicios tras la revisión, con los veredictos ya vistos). La regla de decisión no se cambió; la robustez se añadió aparte.

## 6. Decisiones para el usuario

1. **REIT, FFO/patrimonio contable** (rentabilidad):
   - (a) retirarla de la puntuación y dejarla informativa;
   - (b) sustituirla por FFO / activos totales, que no depende de cómo se financia;
   - (c) dejarla.

   Recomendación del operador: **(b)**, recalibrada con esta muestra.
2. **Escala de precio:** ninguna regla cambia. El estudio no sostiene que "atractivo" o "muy exigente" anticipen la rentabilidad. La app ya no lo dice y no debe empezar a decirlo.
3. **Escala de calidad:** ninguna regla cambia. Se presenta como descripción de la solidez y la rentabilidad del negocio, no como señal de inversión, y así se presenta hoy.
4. **Repetir el estudio** con una muestra mayor (Russell 1000 con las empresas desaparecidas) y con la prima de riesgo de cada fecha (histórico de Damodaran, requiere su descarga), para que la escala de precio sea evaluable.

## 7. Revisión mensual de parámetros (punto 2 del plan)

`config/review.toml` guarda la fuente, la fecha del dato, la de consulta y la cadencia de cada parámetro de mercado.
`tests/revision_parametros.py` dice qué toca revisar, con las cadencias mensuales en meses de calendario y un aviso de
dato antiguo. A 17-oct-2026:

- **Vigentes (7):** prima de riesgo y Rf (próxima publicación de Damodaran, 1-nov-2026), spreads y betas de sector (enero de 2027), tasas base, y P/E y P/E adelantado del S&P 500.
- **Vigente con dato antiguo (1):** EV/EBITDA del S&P 500, con mediana de 1T-2025; no hay una pública más reciente.
- **Sin fuente (2):** las medianas y los umbrales sectoriales, PROVISIONALES. Esperan los datos por industria de Damodaran y el permiso de descarga del usuario (F4_PARADA §5).

La vigilancia semanal (punto 1) ya estaba activa: tarea `finanzer-vigilancia-semanal`, sábados a las 09:00.

## 8. Reproducir

```
cd finanzer_next/backend
SEC_EDGAR_USER_AGENT="…" ../.venv313/bin/python tests/calibracion_datos.py --out ~/Downloads/finanzer_calibracion
../.venv313/bin/python tests/calibracion_generar.py --data ~/Downloads/finanzer_calibracion
../.venv313/bin/python tests/calibracion_ejecutar.py --data ~/Downloads/finanzer_calibracion
../.venv313/bin/python tests/calibracion_analizar.py --data ~/Downloads/finanzer_calibracion --out resultados.md
SEC_EDGAR_USER_AGENT="…" ../.venv313/bin/python tests/calibracion_bandas.py --data ~/Downloads/finanzer_calibracion --out bandas.md
```

Los datos, unos 100 MB, están en `~/Downloads/finanzer_calibracion`, fuera del repo. La versión 1 se conserva al
lado: `resultados_v1.md`, `resultados_v1/` y `observaciones_v1.json`.

## 9. Revisión independiente (y qué cambió)

| Hallazgo | Arreglo | Efecto |
|---|---|---|
| 1. El precio de D venía ajustado por los splits y escisiones posteriores (yfinance ajusta siempre). WMT a un tercio, GE ×4.8: 218 observaciones | Precio, serie, máximo, mínimo y dividendos multiplicados por el factor de los splits posteriores a D (`split_factor_after`) | H3a: de validada a **no concluyente** |
| 2. El bootstrap solo por empresa ignora el choque común de cada año | Bootstrap de dos vías como robustez (no cambia la regla) | ninguna hipótesis es robusta |
| 3. H2 depende de la mezcla de sectores | Métrica neta de sector × año como robustez | H2 neta: +0.6 pp, IC con 0 |
| 4. Ejercicios no anuales (BMY, CVS) y duplicados de 52/53 semanas; D de un 10-K posterior | Ejercicios por flujos anuales, un cierre por ejercicio, 10-K en ≤ 120 días | 965 observaciones (antes 968), sin duplicados |
| 5. El sesgo de la prima y de las medianas sí cambia el nivel | §5 reescrito | — |
| 6. Deuda de los REIT con etiquetas solapadas (deuda > pasivo) | Una etiqueta de total, nunca por encima del pasivo | REIT deuda neta/EBITDA, en el límite: sigue PROVISIONAL |
| 7. Desajuste de splits en las bandas | Mismo arreglo | Ninguna banda cambia de veredicto |
| 8. ROE de partida reexpresado; lectura del exploratorio exagerada | ROE conocido en D; §3 matizado | — |
| 9. El prerregistro no es verificable con git | Declarado en §5 | — |
| 10. Cadencia mensual que se desplaza; un dato antiguo salía "vigente" | Meses de calendario y aviso de dato antiguo | EV/EBITDA del S&P 500 marcado |
| 11. TGT sin sector | Declarado | — |
