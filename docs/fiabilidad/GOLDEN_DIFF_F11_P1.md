# F11 · Paso 1 (cables sueltos): cambios y golden (4-nov-2026)

Rama `fiabilidad/f11-medir`. Hallazgos de `revision-nu-nflx-2026-11-04.md`, medidos en `F11_MEDIDA_2026-11-04.md`. El
usuario dio el visto bueno («Sí, paso 1») a corregir en origen el primer bloque del orden propuesto: lo que el motor ya
calcula bien pero no llega a donde se usa. Sin push.

## Qué cambia

| Hallazgo | Arreglo en origen | Archivos |
|---|---|---|
| T7 · fila «Precio de mercado» con la ayuda de la puntuación de atractivo (todas) | La fila usa la clave `share_price`, como la ficha del precio desde la v4.1. Arregla el PDF y el «?» de la web v2, que leen la definición por la clave | `lib/display.py` |
| T7 · «DCF: supuestos y fiabilidad» sin DCF (108) | El título es «Coste del capital» cuando el DCF «No aplica» | `lib/pdf_v2/chapters.py` |
| T7 · metodología escrita a mano (80 citan el DCF inverso sin aplicarlo; Damodaran como referencia y a la vez excluido) | La metodología nombra el método intrínseco del tipo (DCF, valor justificado sobre libros o su modelo intrínseco), cita las tasas base solo si el DCF inverso aplica y, con referencia de pares, dice que la referencia es la mediana de pares (fuente y fecha incluidas) | `lib/pdf_v2/methodology.py` |
| T7 · persistencia anclada en el margen neto «No aplica» (bancos) | Un subtipo sin margen neto ancla la Rentabilidad en su ROE de cada ejercicio (`archetype_metrics.roe_by_year`, de los balances); sin él, no se mide. Nunca con una métrica «No aplica» | `lib/persistence.py`, `lib/archetype_metrics.py`, `main.py` |
| T3 · la alerta «Caída pronunciada» no salta en ninguna empresa | La regla leía `max_drawdown_1y`, que nada rellenaba desde que la caída vive en el contexto de mercado. Las alertas se rehacen con la caída de 1 año cuando llega el contexto. No puntúa (D5 intacto: el contexto se calcula después del veredicto) | `main.py` |
| T3 · cobertura «Alta» con el riesgo de crédito sin medir (12 bancos) | `coverage_dimension` no pasa de «media» con la variable crítica de su tipo sin medir, aunque no puntúe. Motivo traducido: «Falta medir el riesgo de crédito, la variable clave de este tipo de empresa.» | `lib/valuation_confidence.py`, `lib/plain_language.py`, `main.py` |
| N1 · ROTE implícito de una etapa frente a un justificado de dos (9) | Con el justificado en dos etapas, el retorno implícito se despeja con el mismo modelo (forma cerrada) y su sensibilidad mueve el retorno de la etapa alta: a ±0 da el justificado. La banda compara el implícito con el retorno estable que supone el modelo (el de la industria). El de una etapa queda en `implied.single`. Textos de la web, el PDF y el pre-mortem | `lib/archetype_metrics.py`, `lib/display.py`, `lib/premortem.py` |
| T4 · crecimiento puntuado por encima de su propia cota (13) | Desde una base anómala baja, la tasa de punta a punta ya sobrestima el crecimiento (cota superior). La regresión que la supera arrastra años de crecimiento más antiguos y se acota. Si no se acota, el rótulo de la puntuación dice la ventana real («regresión FY2021–FY2026»). Si se acota, la cifra es el CAGR de 3 años y el rótulo de siempre es correcto | `lib/historical_metrics.py`, `lib/financial_ratios.py`, `lib/display.py`, `main.py` |

NU con los datos del 4-nov: ROTE terminal implícito del 22,1 % (el revisor da 22,4 % ± 0,5 pp), banda «muy exigente»
(frente al 12,8 % de su industria). La sensibilidad a ±0 da 2,538x = el P/TBV justificado, y el modelo devuelve el
múltiplo de mercado (4,817x).

## Golden (local, panel, PDF v2 y muestras forzadas)

Regenerados con `diff_golden.py --regenerate --yes`, `pdf_v2_golden.py --regenerate` y `contract_forced.py --write`
después de revisar el diff. Suite: **6557 passed, 26 skipped, 0 failed**.

| Cambio | Empresas | ¿Esperado? |
|---|---|---|
| `intrinsic.rows[0].key`: `price` → `share_price` | todas | Sí (T7) |
| `growth_basis.*.capped` y `value_uncapped` (nuevos, nulos salvo si se acota) | todas | Sí (T4) |
| `archetype_metrics.roe_by_year` (nuevo) | financieras | Sí (T7) |
| Alerta «Caída pronunciada en el año» nueva | 11 del panel | Sí (T3) |
| JPM: persistencia de Rentabilidad con el ROE (4 de 5 ejercicios) en lugar del margen neto: **calidad 89 → 88** | JPM | Sí (T7). Su margen neto «No aplica» daba 5 de 5 sin motivo |
| PGR: ROE implícito de dos etapas del 16,6 % (antes 20,1 % de una etapa) frente al 16,4 % de su industria: banda **«barata» → «en precio»**. No puntúa | PGR | Sí (N1): coherente con su P/B justificado de dos etapas |
| NVDA: rótulo «Crecimiento de ingresos a 3 años» → «(regresión FY2021–FY2026)» | NVDA | Sí (T4): la cifra es la de la regresión |
| PDF v2: título «Coste del capital», metodología según el tipo y la referencia, paginación | bancos, aseguradoras, utilities, REIT | Sí (T7) |

Ningún cambio de nivel de precio ni de veredicto en el panel. El único cambio de nota es el de JPM (−1).

## Efecto en el universo

Escaneo de las 543 con este código (caché `2026-11-04-f11-p1`, 18 min, 0 errores), frente al del mismo día con el
código de prod (`2026-11-04-f11`):

| Regla | Prod | Paso 1 | Nota |
|---|---:|---:|---|
| `metodo_citado_aplicable` (T7) | 542 | **0** | |
| `riesgo_critico_medido` (T3) | 12 | **0** | |
| `implicito_mismo_modelo` (N1) | 9 | **0** | |
| `caida_avisada` (T3) | 213 | **0** | Las 8 que quedaban sin la alerta tienen el grupo lleno: 6 advertencias de más peso, con el tope por grupo de siempre. La regla lo distingue. **Decisión pendiente del usuario:** la caída pesa 34, y en CSGP (−62 %), CIEN (−57 %) y NOW (−55 %) cede ante «margen neto estrecho» o «ROE bajo» |
| `cota_aplicada` (T4) | 79 | 64 | Las 13 por encima de su cota, a 0. Quedan 64 de rótulo en el BPA y el FCF: siguen «a 3 años» con una regresión más larga. Va con el paso de crecimiento |
| `cifra_unica` | 0 | 3 → **0** | La primera versión del tope usaba la tasa de punta a punta y la gráfica la regresión de la ventana (APO 43,0 % frente a 34,9 %). El tope usa ahora la regresión de la ventana, la de la gráfica. Reescaneo de NU, CCL, APO, NOW y CSGP (`2026-11-04-f11-p1b`): todas sus reglas del paso 1 en 0 |
| Resto de reglas de F11 | — | sin cambio | Son de los pasos 2–5 |

**Notas y confianza.** No cambia ninguna nota de calidad ni ningún tipo de empresa. Cambian 25 notas de precio y 10
niveles de confianza; atribuidos uno por uno:
- **Del paso 1:** NU y BBVA pasan de confianza «alta» a «media», con el riesgo de crédito sin medir (NU: precio 25 → 31
  por la contracción hacia 50).
- **Del mercado entre las dos corridas** (precio movido 0,1–1 %): umbrales cruzados en la convergencia (DG, EIX, LUV,
  NWSA), en la dependencia del Ke (CB, KDP, PKG, NWSA) o en una banda de múltiplos (CB: P/E normalizado de 11,90x a 11,92x
  cruza su banda y pasa de +3 a 0, precio 69 → 60). Es el precipicio de las bandas fijas que el modelo general (§5)
  propone sustituir por bandas continuas.
- **De los datos:** EXPD presentó su 10-Q durante el día: «estados desfasados» y la cobertura no pasa de «media».
