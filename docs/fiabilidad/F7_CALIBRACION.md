# F7 · Calibración histórica (estudio, no ajuste) y revisión de parámetros

> Fase 7 del plan de fiabilidad (PLAN_FIABILIDAD §4, puntos 2 y 3). Rama `fiabilidad/f7-calibracion`, que sale de
> `fiabilidad/f6-infra` (worktree `../finanzer_next-f3`). **Nada subido.** Hecha bajo la delegación del usuario
> (registro #29). El plan dice que este estudio "termina con un informe y decisiones del usuario": las decisiones
> están en §6. **No se ha cambiado ningún umbral del motor con él.**

## 0. Resumen

| Hipótesis (fijadas antes de correr: `3ef8c8f`) | Resultado | Veredicto |
|---|---|---|
| H1 · Calidad "excelente" anticipa que el ROE se mantenga (a 3 años, ≥ 75% del propio) | −6.3 pp frente a "media" + "débil" (IC 90%: −14.0 a +1.0) | **no concluyente** (signo contrario) |
| H2 · Calidad "excelente" anticipa menor caída máxima a 3 años | +5.0 pp en mediana (IC 90%: +1.3 a +8.2); se cumple en las cuatro mitades | **validada** |
| H3a · Precio "muy exigente" anticipa peor rentabilidad frente al S&P 500 a 1 año | −10.3 pp en mediana (IC 90%: −13.0 a −4.3); entre −9.8 y −11.4 en las cuatro mitades | **validada** |
| H3b · Lo mismo a 3 años | −0.2 pp (IC 90%: −14.7 a +6.3) | **no concluyente** |

Lectura de analista:

- La escala de **calidad** acierta en lo que dice ser: un indicador de **riesgo y solidez**. Las "excelente" caen menos en los años siguientes.
- La calidad no predice la rentabilidad bursátil, y la app no lo afirma: ningún texto promete batir al mercado (comprobado).
- La persistencia **relativa** del ROE no se valida. El **nivel** del ROE sí persiste (§3, exploratorio): el 72% de las "excelente" sigue con un ROE ≥ 15% tres años después, frente al 42–44% de "media" y "débil".
- El **precio "muy exigente"** acierta a 1 año: unos 10 puntos peor que el índice.
- A 3 años, y entre "atractivo" y "razonable", la escala de precio **no separa** las rentabilidades. "Atractivo" no debe leerse como una previsión de rentabilidad, y la app no lo hace.

## 1. Diseño

**Muestra:** 100 empresas de EE. UU. fuera del panel, 11 sectores (lista en `tests/calibracion_datos.py`). Se pierden
dos por la tabla de la SEC (EQR y AVB) y parte de DIS (cambio de CIK en 2019). El resultado son **968 análisis de 98
empresas**, una vez por ejercicio de 2012 a 2021.

**Fecha de cada análisis (D):** el día siguiente a la presentación del 10-K del ejercicio. El motor ve lo que se sabía
ese día:

- **Estados:** construidos desde los hechos XBRL de EDGAR presentados hasta D, con las filas de Yahoo y sin las reexpresiones posteriores.
- **Cotización:** el cierre sin ajustar de D y las acciones de la portada del 10-K.
- **Series:** dos años hasta D de la empresa, del S&P 500 y del ETF de su sector.
- **EDGAR:** cortado en D.
- **Rf:** ^TNX de D, entre 0.54% y 3.23% en la muestra.

**Motor:** el real (`_compute_analysis`) en replay, sin cambios (`tests/calibracion_ejecutar.py`).

**Resultados medidos después de D:**

- rentabilidad total (cierre ajustado) frente a SPY a 1 y 3 años;
- caída máxima a 3 años;
- ROE del ejercicio y de 3 ejercicios después (EDGAR de hoy).

**Regla de decisión** (`tests/calibracion_analizar.py`, fijada antes): muestras de entrenamiento y prueba por periodo
(2012–2016 / 2017–2021) y por empresa (mitades alternas). El IC del 90% sale de un bootstrap por empresa (2000
remuestras). "Validada" exige el signo en las cuatro mitades y un IC que excluya 0.

## 2. Resultados por nivel (descriptivo)

| Escala | Nivel | n | ROE persistente (≥ 75%) | Caída máx. 3 años (mediana) | Frente al S&P 500, 1 año (mediana) | Ídem, 3 años |
|---|---|---|---|---|---|---|
| Calidad | excelente | 419 | 70.0% | −30.1% | +1.2% | −0.2% |
| | sólida | 308 | 75.1% | −29.6% | +0.4% | −1.6% |
| | media | 166 | 74.3% | −32.5% | −2.3% | −9.1% |
| | débil | 75 | 83.3% | −36.8% | +2.6% | +1.8% |
| Precio | atractivo | 397 | 68.7% | −29.8% | −0.4% | +0.6% |
| | razonable | 329 | 74.8% | −30.3% | +1.7% | −5.9% |
| | exigente | 139 | 82.8% | −31.4% | +0.5% | −6.3% |
| | muy exigente | 66 | 72.9% | −35.8% | −9.3% | −2.4% |

Sin precio: 37 casos, en los que la valoración no fue evaluable. Precio sin contraer por la confianza: mismo patrón
("muy exigente", −8.1% a 1 año).

## 3. Exploratorio (añadido tras ver H1; no decide)

La medida de H1 compara el ROE con el propio, así que castiga a los ROE altos por la reversión a la media: un ROE del
40% que baja al 28% "no persiste" y uno del 2% que sube al 3% sí. El nivel cuenta otra historia:

| Calidad | n | ROE del ejercicio (mediana) | ROE 3 años después (mediana) | 3 años después ≥ 15% |
|---|---|---|---|---|
| excelente | 331 | 25.4% | 27.9% | 72.2% |
| sólida | 229 | 16.9% | 20.7% | 62.9% |
| media | 108 | 10.3% | 12.9% | 44.4% |
| débil | 59 | 0.1% | 11.1% | 42.4% |

## 4. Bandas de REIT y utilities (F4_PARADA §5)

`tests/calibracion_bandas.py`: 26 REIT y 25 utilities de EE. UU., unos 350 empresa-año cada grupo (2012–2025; hechos de EDGAR de hoy y cierre de Yahoo del último día de cada ejercicio). El
criterio se fijó antes de mirar: la mediana debe caer en el tramo neutro o en uno contiguo, y ningún tramo extremo
puede recoger más del 40%.

| Arquetipo | Métrica | Mediana | Reparto por tramo | Veredicto | Lectura |
|---|---|---|---|---|---|
| UTILITY | deuda neta/EBITDA | 5.1x | 37 / 26 / 24 / 8 / 5% | bien centrada | se quita "PROVISIONAL" del comentario de config |
| UTILITY | cobertura de intereses | 2.9x | 24 / 43 / 22 / 6 / 5% | bien centrada | ídem |
| UTILITY | rentabilidad por dividendo | 3.6% | 13 / 23 / 41 / 22 / 1% | bien centrada | ídem |
| REIT | P/FFO | 16.7x | 19 / 23 / 28 / 18 / 11% | bien centrada | ídem |
| REIT | FFO/ingresos | 54.5% | 41 / 18 / 18 / 19 / 4% | casi (el tramo alto, 41%) | se mantiene |
| REIT | FFO/patrimonio contable | 15.3% | **82%** / 12 / 4 / 2 / 1% | **satura** | decisión del usuario (§6) |
| REIT | dividendos/FFO | 0.60 | 79 / 13 / 3 / 5% | satura | es una prueba de cobertura del dividendo, no un ranking: se mantiene |
| REIT | deuda neta/EBITDA | 5.5x | 34 / 42 / 12 / 9 / 3% | bien centrada | con las etiquetas de deuda de los REIT (O: pagarés y préstamos; otros: importe de los instrumentos). La primera pasada, sin ellas, daba un p10 de 0.56x: datos incompletos, no la banda |

FFO/patrimonio contable da +6 al 82% de los REIT: es un bono casi constante. Recalibrarlo por quintiles no lo arregla.
O (Realty Income) pasaría de +6 a −6 porque emite acciones por encima del valor contable, y eso le agranda el
patrimonio. AMT llegaría arriba por sus recompras. La métrica premia el apalancamiento y los activos viejos y
amortizados, no la calidad del negocio.

## 5. Límites del estudio

- **Supervivencia:** son empresas que existen hoy. Las que quebraron o fueron absorbidas no están, y eso favorece a la muestra (más a "débil").
- **No es point-in-time** en:
  - la prima de riesgo (4.20% de octubre de 2026);
  - las medianas y umbrales sectoriales de config;
  - las tasas base (1984–2020);
  - el sector y la industria de hoy;
  - sin Finnhub.

  El sesgo de la prima es uniforme dentro de cada año: mueve el nivel de la valoración, no el orden.
- **Estados desde EDGAR:**
  - 287 de los 968 análisis usan un EBIT aproximado en su ejercicio (beneficio antes de impuestos + gastos financieros), porque el emisor no etiqueta el operativo;
  - sin desglose de partidas inusuales;
  - el patrimonio del ordinario sin restar preferentes.
- **Dependencia:** las ventanas de 3 años de cohortes consecutivas se solapan y comparten los choques de mercado (2020). El bootstrap por empresa recoge la dependencia dentro de cada empresa, no la común. Los IC son optimistas.
- **Tamaño:** solo 66 casos "muy exigente". H3a es robusto en las cuatro mitades, pero con ese n.

## 6. Decisiones para el usuario

1. **REIT, FFO/patrimonio contable** (rentabilidad):
   - (a) retirarla de la puntuación y dejarla informativa;
   - (b) sustituirla por FFO / activos totales (rentabilidad sobre el activo, que no depende de cómo se financia);
   - (c) dejarla como está.

   Recomendación del operador: **(b)**, recalibrada con esta muestra.
2. **REIT, deuda neta/EBITDA:** hecho por el operador. Repetido con las etiquetas de deuda de los REIT, la banda está bien centrada y no cambia.
3. **Utilities, P/FFO y deuda de los REIT:** "PROVISIONAL" fuera de sus comentarios en `config/thresholds.toml`, citando este estudio. Es un cambio de texto, no de valor, y está hecho.
4. **H1:** ninguna regla cambia. Que la calidad por encima de 80 exija persistencia (F4) mira la historia, no promete el futuro. El estudio no lo contradice: el nivel del ROE persiste.
5. **Precio:** ninguna regla cambia. Si algún día un texto quiere hablar de lo que "suele pasar", solo lo sostiene "muy exigente" a 1 año.

## 7. Revisión mensual de parámetros (punto 2 del plan)

`config/review.toml` guarda la fuente, la fecha del dato, la fecha de consulta y la cadencia de cada parámetro de
mercado. `tests/revision_parametros.py` dice qué toca revisar (`7bbfc6e`). A 17-oct-2026:

- **Vigentes (8):** prima de riesgo y Rf (próxima publicación de Damodaran, 1-nov-2026), spreads y betas de sector (enero de 2027), tasas base, P/E y P/E adelantado del S&P 500, y EV/EBITDA del S&P 500.
- **Sin fuente (2):** las medianas y los umbrales sectoriales, PROVISIONALES. Se sustituyen con los datos por industria de Damodaran, que esperan el permiso de descarga del usuario (F4_PARADA §5).

La vigilancia semanal (punto 1) ya estaba activa: tarea `finanzer-vigilancia-semanal`, sábados a las 09:00, aprobada en
F67prep.

## 8. Reproducir

```
cd finanzer_next/backend
SEC_EDGAR_USER_AGENT="…" ../.venv313/bin/python tests/calibracion_datos.py --out ~/Downloads/finanzer_calibracion
../.venv313/bin/python tests/calibracion_generar.py --data ~/Downloads/finanzer_calibracion
../.venv313/bin/python tests/calibracion_ejecutar.py --data ~/Downloads/finanzer_calibracion
../.venv313/bin/python tests/calibracion_analizar.py --data ~/Downloads/finanzer_calibracion --out resultados.md
SEC_EDGAR_USER_AGENT="…" ../.venv313/bin/python tests/calibracion_bandas.py --data ~/Downloads/finanzer_calibracion --out bandas.md
```

Datos (unos 100 MB) en `~/Downloads/finanzer_calibracion`, fuera del repo: hechos XBRL reducidos, series diarias desde
2009, fixtures, resultados (`resultados/FY*.jsonl`) y observaciones con sus resultados (`observaciones.json`).
