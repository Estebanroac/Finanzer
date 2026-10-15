# Prompt del operador — Fase 1: Lo visible hoy

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`.

---

Eres el **operador de la fase 1 del plan de fiabilidad de Finanzer**. Objetivo: que **ningún informe diga algo falso
ni se vea roto** (propiedad F3). Y no solo arreglar los casos conocidos: cerrar la **clase** de error con un
guardián automático, para que no vuelva a aparecer.

## 1. Contexto (lee esto antes de tocar nada)

En este orden:

1. `docs/fiabilidad/BITACORA.md`: estado, decisiones D1–D8, mapa de pendientes (filas con fase 1) y registros #5 y #6.
2. `docs/PLAN_FIABILIDAD.md`: §0, §2.3 (sesgos del usuario: el texto no debe empujar ni anclar), §4 fase 1 y §5
   (protocolo de revisión).
3. `docs/fiabilidad/F0_LINEA_BASE.md`, sección F3: el inventario que esta fase cierra.
4. `backend/tests/README.md` (sección del panel), `backend/tests/invariants.py`, `backend/tests/panel_run.py`.
5. Los generadores de texto: `backend/lib/display.py`, `plain_language.py`, `alert_interpretations.py` y
   `pdf_report.py`.

Hechos que debes tener presentes:

- **Estado de git:** `main` local = `0f798c8` (merge de la fase 0), **13 commits por delante** de `origin/main`
  (`9e78f3b`, que es producción). **Pushear `main` redespliega producción** con la fase 0 y la 1 juntas. Solo se
  pushea con un "ok, pushea" explícito del usuario.
- Suite de referencia: `cd backend && ../.venv313/bin/python -m pytest tests` → hoy **1538 passed, 1 skipped, 2
  xfailed**.
- El **panel** (31 tickers, `tests/fixtures/panel`) es la vara. `panel_run --mode replay` y `--mode live` con
  `--compare` contra la corrida de la fase 0 (`~/Downloads/finanzer_f0_panel_2026-10-14/`).
- La clave de Finnhub está en el Llavero (`finanzer-finnhub`); `capture_fixtures.py --render-sim` la lee sola. En
  esta fase no se recaptura nada.
- La web y el PDF comparten la capa `lib/display.py`: un texto corregido ahí cambia los dos. Si tocas
  `frontend/src`, hay que reconstruir `frontend/out` (`cd frontend && NODE_ENV=production npm run build`) y
  commitearlo (Render no compila el frontend).

**Decisiones del usuario que aplican (no las reabras):**

- **D1 = anexo técnico.** Los códigos internos (`MATURE`, `por_defecto`, `industria_banco`, `pe_implausible`…)
  salen de las páginas que lee el usuario y se reúnen en un **anexo final del PDF rotulado "Detalle técnico para
  auditoría"**. En el resto del informe, solo lenguaje llano. La web no muestra códigos.
- **D8:** se retiran los juegos `prod` y `muestra` (fixtures y golden); `local` se queda. Va **en un commit propio,
  el primero de la fase**.
- El invariante `growth_texts_cite_the_scored_figure` se ajusta para aceptar el signo expresado con el verbo ("se
  contraen un 5.0%"). Hoy falla con xfail estricto en XOM y DOW.
- El **texto** que presenta la cota del crecimiento de ciclo medio (−5% / +10%) como dato medido se corrige en esta
  fase. El **método** del tope es de la fase 3: no lo toques.

## 2. Diagnóstico ya hecho por el planificador (verifícalo, no lo des por cierto)

**PLTR, "con EBIT negativo y caja neta" con un EBIT de +$2.63B.** La causa es de lógica, no de texto:
`financial_ratios.interest_coverage_state(ic, net_debt)` deduce "EBIT < 0" del **signo de la cobertura**. Una
cobertura negativa también sale cuando el **gasto financiero neto es negativo** (la empresa cobra más intereses de
los que paga, típico con mucha caja), con el EBIT positivo. Finnhub da `interestCoverage` = −1.53 para PLTR.
Consecuencias que debes comprobar:

- `display.read_coverage` (≈ línea 163) imprime el texto falso.
- `validate.py` (≈ línea 454) anula la cobertura como "no significativa" con un motivo falso, y la Solidez de PLTR
  se puntúa sin ella.
- Mira también CRWD (la misma regla salta en la línea base); allí el EBIT GAAP podría ser negativo de verdad.

El estado de la cobertura tiene que decidirse con **el signo del EBIT de los estados** (`operating_income`) y **el
signo del gasto financiero**, no con el signo del cociente. Los casos: EBIT > 0 y gasto ≤ 0 → "sin carga financiera
neta" (la deuda no es un riesgo); EBIT < 0 y caja neta → no significativa (como hoy); EBIT < 0 y deuda neta →
riesgo (como hoy). Esto **cambia la puntuación** de las empresas afectadas: es esperado y debe salir explicado en el
diff de golden.

## 3. Tareas, en orden

### T0. D8: retirar `prod` y `muestra` (commit propio)
- Crea la rama `fiabilidad/f1-visible` desde `main` local.
- Retira fixtures y golden de `prod` y `muestra`. Revisa los tests que los usan (`test_muestra.py`, la regresión, el
  determinismo, `conftest.py`, `fixture_backend.py`). Lo que siga teniendo valor se reescribe contra el panel; lo
  que solo existía por esos juegos se elimina, y anotas cuál y por qué.
- **La cobertura no puede bajar:** cada invariante de `test_muestra.py` sigue existiendo en `invariants.py` o se
  justifica su retirada.
- Suite en verde. Commit `F1: D8, retira los juegos prod y muestra`.

### T1. Diseño del guardián narrativo → **PUNTO DE PARADA 1**
El guardián comprueba que **cada afirmación del informe es verdad según el dato estructurado**. Propón el diseño
**antes** de implementarlo:

- **Enfoque.** Compara al menos estas dos opciones:
  (a) a posteriori: patrones sobre el texto ya generado (PDF y `display`), cada uno con su predicado sobre el
  análisis;
  (b) en origen: los generadores de texto devuelven la frase junto con la afirmación estructurada que hace
  (p. ej. `("EBIT negativo", operating_income < 0)`) y el guardián verifica esos predicados.
  Lo esperable es (b) donde sea viable, con (a) como red de seguridad; justifica tu elección.
- **Catálogo mínimo de afirmaciones** (amplíalo con lo que encuentres en los generadores):
  1. "EBIT negativo" / "resultado operativo negativo" ⇔ `operating_income < 0`.
  2. "caja neta" ⇔ `net_debt < 0`; "deuda neta" ⇔ `net_debt > 0`.
  3. "en máximos / en mínimos de 52 semanas" ⇔ posición en el rango ≥ / ≤ el umbral de config.
  4. "recompras" / "retiró un X% de las acciones" ⇔ acciones a la baja con esa cifra; "diluyó" ⇔ acciones al alza.
  5. Crecimiento: "crecen / se contraen un X%" ⇔ signo y cifra del valor que puntúa. Si el valor está en la cota
     del modelo, el texto **debe decirlo**.
  6. "superior / inferior al sector", "+N% vs sector" ⇔ signo de la brecha y cifra.
  7. Veredicto, nivel de calidad, nivel de precio y confianza en el texto ⇔ los campos `verdict` / `quality` /
     `price_attractiveness` / `confidence`.
  8. Arquetipo nombrado en la prosa ⇔ `classification.archetype`.
  9. Cifras de las tarjetas KPI y de las métricas citadas ⇔ el valor redondeado del campo.
  10. Ninguna métrica "no aplica" citada con cifra en la narrativa.
  11. Ninguna palabra en inglés (lista cerrada y ampliable: STRONG, GOOD, WEAK, MATURE, CYCLICAL, N/A en prosa…) ni
      ningún código interno fuera del anexo técnico.
- **Alcance:** los 31 del panel en replay y el texto que consume la web (`display`).
- **Prueba de que detecta:** como en `test_invariants_detectan.py`, cada predicado con una violación inyectada que
  debe hacerlo fallar.

**Detente y presenta el diseño y el catálogo para su aprobación.**

### T2. Guardián en rojo
Implementa el guardián aprobado **sin arreglar nada todavía**. Debe fallar en los casos conocidos: PLTR (EBIT),
JPM/BAC/PGR/BRK-B ("STRONG"), códigos internos en 30/30, la cota del ciclo medio (XOM, DOW, FCX, MU, ASML). Lo que
encuentre de nuevo va a una lista. Marca los fallos actuales con xfail estricto por predicado y ticker, para que
cada arreglo los vaya convirtiendo en XPASS. Commit.

### T3. Arreglos de texto y lógica (un commit por causa)
1. Estado de la cobertura de intereses (§2 de este prompt). Test unitario de los tres casos + PLTR del panel.
2. "STRONG" y cualquier otra palabra en inglés que encuentre el guardián: la etiqueta se traduce en la capa de
   presentación, no en el motor (`financial_ratios` puede seguir usando sus códigos).
3. D1: anexo técnico "Detalle técnico para auditoría" al final del PDF, con lo que hoy sale en "Clasificación
   (detalle técnico)" y similares. Ningún código fuera del anexo.
4. Cota del ciclo medio: cuando el crecimiento que puntúa esté en la cota, el texto lo dice en lenguaje llano
   (p. ej. "crecimiento de ciclo medio acotado al mínimo que admite el modelo (−5% anual)"). Mismo criterio en la
   web.
5. Invariante `growth_texts_cite_the_scored_figure`: aceptar el signo expresado con el verbo. Quita los 2 xfail.
6. Todo lo nuevo que haya encontrado el guardián: arréglalo si es de texto; si es de método, **no lo arregles**:
   llévalo al mapa de pendientes con su fase y detente si cambia el alcance.

### T4. Maquetación del PDF
1. Página 2: el panel "Composición de las dos puntuaciones" ocupa el mismo ancho que el resto, sin recortar las
   cifras del margen derecho, sin hueco encima y sin que "Lectura del análisis" se le monte encima.
2. **Comprobación geométrica automática** en los 31 del panel: extrae las cajas de texto con pypdfium2 y verifica
   que (a) todo texto queda dentro del área útil de la página y (b) no hay líneas de bloques distintos que se
   solapen. Con su propia prueba de que detecta (una página sintética con solapamiento debe fallar).
3. Revisión visual en PNG de las páginas 1 y 2 de un ticker por grupo del panel (9 PDF).

### T5. Golden y panel → **PUNTO DE PARADA 2**
- `diff_golden.py` del panel y de `local`: cada diferencia atribuida a **una** causa de T3/T4. Cambios de puntuación
  esperados solo por la cobertura de intereses (PLTR y las que el diagnóstico confirme).
- `panel_run --mode replay --compare <corrida F0 replay>`: tabla de cambios de arquetipo / nivel / confianza.
- **Detente.** Presenta el diff explicado, la tabla de cambios y los PNG de la revisión visual. **No regeneres
  golden sin la aprobación del usuario.**

### T6. Web
Comprueba en la web, con el backend local sirviendo `frontend/out`, que PLTR (cobertura), JPM ("STRONG") y XOM
(cota) muestran el texto corregido. Verifica también si la barra de 52 semanas de la web sigue con la lectura de
precio (curva en U) frente a la "solo posición" del PDF (pendiente de RECON §7.14): solo verificar y anotar.
*Recordatorio:* `preview_start` no puede leer `~/Downloads`; lanza el backend con Bash en segundo plano.

### T7. Deploy → **PUNTO DE PARADA 3**
- Merge de `fiabilidad/f1-visible` en `main` local. Suite en verde sobre `main`.
- **Pide el "ok, pushea" al usuario.** Recuérdale que el push sube la fase 0 y la 1 juntas (13 + N commits) y que
  el rollback es `9e78f3b`.
- Tras el push: espera al deploy de Render y corre `panel_run --mode live --compare <corrida F0 live>` contra
  finanzer.app (concurrencia ≤ 3). Las diferencias deben ser las esperadas de T5 más el ruido de Rf y precio.
  Anótalo en `docs/DEPLOY_VERIFICATION.md` (sección nueva, con el sello de build, la hora y el rollback).

### T8. Cierre
- RECON §7.19 "Fase 1 del plan de fiabilidad". Bitácora: entrada con la plantilla, estado, fila de la fase 1 y
  mapa de pendientes al día.
- Métricas F3 de cierre frente a la línea base: contradicciones, palabras en inglés, códigos fuera del anexo,
  defectos de maquetación (todo debe quedar en 0) y fallos del guardián.
- Detente y presenta el cierre para su aprobación.

## 4. Fuera del alcance (no lo hagas aunque parezca fácil)

- Cualquier cambio de **método**: arquetipos (CAT, PLTR, TSM…), el tope −5%/+10%, el DCF, la saturación de la
  calidad, el efecto frontera de NVO, D3. Son de las fases 3 y 4.
- **P/FFO visible en la web**: es una mejora, no un defecto. Muévelo en el mapa de pendientes a "mejoras, después de
  la fase 4" (decisión del planificador).
- Datos y fuentes (EDGAR, Yahoo frente a Render, JNJ sin Altman): fase 2.

## 5. Reglas que no se rompen

- Test antes que el arreglo: el guardián y cada test nuevo fallan antes y pasan después.
- **Una causa por commit** (prefijo `F1:`). Ningún golden se regenera sin la aprobación del usuario y sin el diff
  explicado causa por causa.
- **No pushees** sin un "ok, pushea" explícito. No hagas merge a `origin`. No toques Render.
- No tomes decisiones de método ni reabras D1/D8. Si algo exige una decisión nueva, añádela a la bitácora como D9…
  y detente.
- Si el código contradice este prompt o la bitácora, manda el código: verifica, repórtalo y sigue solo si no cambia
  el alcance.
- Toda afirmación de "hecho" o "pasa" va con el comando que la demuestra y su salida.
- Al cerrar la sesión, aunque quede a medias, deja tu entrada en la bitácora.

## 6. Definición de terminado de la fase 1

- [ ] D8 aplicada en su propio commit, sin pérdida de cobertura de tests.
- [ ] Guardián narrativo aprobado, implementado y con su prueba de que detecta; 0 fallos en los 31 del panel.
- [ ] Cobertura de intereses decidida por el signo del EBIT y del gasto financiero; PLTR correcto.
- [ ] 0 palabras en inglés y 0 códigos internos fuera del anexo técnico (D1); anexo presente.
- [ ] Cota del ciclo medio dicha como cota en el PDF y en la web; invariante ajustado, 0 xfail.
- [ ] Página 2 corregida y comprobación geométrica en verde en los 31.
- [ ] Golden con el diff explicado y aprobado.
- [ ] Deploy con "ok, pushea", verificación en producción en DEPLOY_VERIFICATION y rollback identificado.
- [ ] RECON §7.19, bitácora y métricas F3 de cierre; aprobación del usuario citada literalmente.
