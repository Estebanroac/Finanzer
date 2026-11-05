# F11 · Paso 4 (T1 → T2): referencia representativa y convergencia independiente (4-nov-2026)

Rama `fiabilidad/f11-medir`, sobre el paso 3 (146f60e9). Visto bueno del usuario: «Sí, paso 4». T1 va antes que T2: la
convergencia de NU dependía en parte de la referencia equivocada.

## Qué cambia

| Hallazgo | Arreglo en origen (regla general) | Archivos |
|---|---|---|
| T1 · NU contra 19 bancos de todo el mundo | La causa no era la que suponía la revisión. Faltaban las cifras de NU a la fecha del conjunto de Damodaran, así que el motor saltaba a la mediana de pares sin mirar cuánto pesaba NU (≈ 1,6 %). **(a)** Sin cifras, el peso se estima con la capitalización de hoy; si es menor que `self_negligible_weight` (5 %), la referencia es el agregado publicado de su industria y región, con la empresa dentro y dicho. **(b)** La mediana de pares usa solo los pares de la región de la referencia; si son menos de `min_peers`, los de todas las regiones, dicho en la nota | `lib/industry_bench.py`, `lib/self_exclusion.py`, `lib/display.py`, `main.py`, `config/sectors.toml` |
| T1 · NFLX contra una industria que casi no gana | Prueba de representatividad: una columna de rentabilidad de la referencia (ROE, ROIC, margen neto, margen operativo) por debajo del 2 % en valor absoluto (`min_profit_ratio`) sale de la referencia, con su cifra en la nota. Sin ella no hay lectura, alerta ni brecha (antes, +7.870 %) | `main.py` (`_select_benchmark`), `lib/display.py`, `config/sectors.toml` |
| T2 · convergencia «alta» con el mismo ancla | Cada método dice de qué referencia depende su insumo dominante (`anchor`): el ROE estable del P/B justificado en dos etapas y el P/B de la referencia del relativo. Si dos métodos comparten ancla, la convergencia no pasa de «media», con el motivo traducido | `lib/valuation_confidence.py`, `lib/industry_bench.py` (`reference_anchor`), `lib/archetype_metrics.py`, `lib/plain_language.py`, `main.py` |

**Cambia una regla de F10 · N2**, «la referencia nunca incluye a la empresa». Ahora puede incluirla solo si pesa menos
del 5 % y no hay cifras con que restarla, y siempre lo declara. El principio de F10 iba contra las empresas dominantes
(NVIDIA en semiconductores, AAPL), que siguen igual. Restar un 3 % no cambia la referencia, y saltar a pares de otras
regiones sí la estropeaba.

**Queda para el modelo general:** el P/B relativo de un banco sin ajustar por ROE. Hace que todo banco más rentable que
sus pares salga «caro» y confirme al justificado (la segunda causa de T2 que encontró la verificación). Es un cambio de
método, no un cable suelto.

## Golden

Regenerados tras revisar el diff. Suite: **6561 passed, 26 skipped, 0 failed**.

| Empresa | Cambio | Causa |
|---|---|---|
| NFLX | El ROE (0,63 %) y el margen neto (0,48 %) de Entretenimiento sin Netflix salen de la referencia; la nota lo dice | T1 representatividad |
| BCS | Mediana de pares mundiales → agregado publicado de los bancos europeos (pesa un 3 %, sin cifras a la fecha) | T1 (a) |
| HSBC | Pares de todas las regiones → pares europeos: P/B de referencia 1,58 → 1,51, ROE 12,8 % → 15,1 %. Precio 39 → 35 | T1 (b) |
| AAPL, NVO | Pares de su región (EE. UU., Europa) en vez de los de todo el mundo (AAPL: margen neto de los pares 13,4 % → 7,5 %) | T1 (b) |
| JNJ, PGR | Márgenes operativos de referencia ligeramente distintos (columnas completadas con pares de su región) | T1 (b) |

Ningún veredicto del panel cambia.

Tests reescritos con su porqué:
- `test_f10_n2.py`: el agregado con la empresa dentro solo por debajo del peso despreciable.
- `test_pdf_v2_parts.py`: AAPL con pares de EE. UU.
- La nota de representatividad dice su periodo («(TTM)»), como exige el guardián del ROE.

## Efecto en el universo

Escaneo de las 543 (caché `2026-11-04-f11-p4`, 0 errores) frente al del paso 3, y reescaneo de las 52 financieras con
el ancla final (`2026-11-04-f11-p4b` y `p4c`):

| Regla | Paso 3 | Paso 4 |
|---|---:|---:|
| `referencia_representativa` (T1) | 67 | **0** (45 empresas con alguna columna de rentabilidad retirada, dicho; el resto, pares de su región o agregado) |
| `convergencia_independiente` (T2) | 1 | **0** |

**NU, el caso que destapó T1 y T2:**
- Referencia: el agregado de bancos de mercados emergentes, donde pesa un 1,2 % (P/B 0,90x, ROE 11 %), en lugar de 19
  bancos de todo el mundo.
- Convergencia: «alta» → «media». El ROE estable del justificado (agregado global) y el P/B relativo (agregado
  emergente) dependen de la misma industria.
- Confianza «baja», precio 38, «Calidad sólida · precio exigente».

Tal como anticipó la verificación, con la referencia correcta NU sale más cara, no menos.

**Ancla, en dos versiones.** La primera la identificaba por industria y región. El escaneo enseñó que el agregado
global contiene al regional (NU seguía en «alta»): ahora la identifica la industria, sin región ni forma. También pasan a
«media» COF e IBKR. El reescaneo encontró un fallo de la primera versión con referencias de sector, que traen varias
industrias (VYLR: el análisis se caía). Corregido, con su test.

**Notas:** cambian 14 de precio y 9 veredictos, todos de un escalón y todos por la referencia nueva:
- ALLE y Q: agregado con la empresa dentro.
- AZN, RIO y BTI: pares de su región.
- BALL, BKR, UAL y DD: columnas retiradas o completadas.

No cambia ninguna nota de calidad por el código.
