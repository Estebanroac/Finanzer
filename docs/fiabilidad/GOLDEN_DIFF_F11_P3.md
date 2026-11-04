# F11 · Paso 3 (F3 + F1 + F2): forward creíble, DCF estable al WACC y DCF inverso con tasa base (4-nov-2026)

Rama `fiabilidad/f11-medir`, sobre el paso 2 (e244899d). Visto bueno del usuario: «Sí, paso 3». Los tres van juntos
porque se tocan. Arreglar F1 sin F2 hacía que el DCF inverso votara +2 «barata» en NFLX, y F3 cambia el mismo bloque de
múltiplos que lee la convergencia.

## Qué cambia

| Hallazgo | Arreglo en origen (regla general) | Archivos |
|---|---|---|
| F3 · Forward P/E que suma con un crecimiento no creíble (83 empresas) | El tope de credibilidad del forward (F9 · R1c) era el CAGR del BPA a 3 años. Desde un año de márgenes hundidos (NFLX 2022: +36,5 %) eso es expansión de margen, no crecimiento repetible. Ahora es el **menor entre el CAGR a 3 años y el crecimiento del BPA del último ejercicio**. La puntuación registra `credited_eps_growth`, lo que de verdad acredita | `lib/financial_ratios.py`, `main.py` |
| F3 · PEG con el P/E reportado | Cuando el P/E normalizado puntúa, el PEG usa ese mismo P/E (`peg_basis.pe_basis = "normalizado"`) | `main.py` |
| F1 · DCF que vota «barata» dentro del error del WACC (32) | Si con ±1 escalón de WACC de su propia rejilla (al crecimiento base) el valor queda al otro lado del precio, la dirección la decide el coste de capital, no la empresa. El DCF no puntúa («en precio, sensible al WACC»), cuenta «en precio» en la convergencia, no genera fortaleza ni advertencia de valor, y su lectura es la banda del caso base con «(sensible al WACC)», en tono neutro, como «(fiabilidad baja)» | `lib/valuation_confidence.py` (`dcf_wacc_flips`), `lib/financial_ratios.py`, `lib/alert_interpretations.py`, `lib/display.py`, `main.py` |
| F2 · DCF inverso «barata» contra su propia tasa base (28) | Con historia propia, «barata» exige además que la mayoría de los comparables (`cheap_with_history_base_rate` = 50 %) sostuviera el crecimiento exigido; si no, en precio. Sin historia propia sigue el 75 % de siempre | `lib/reverse_dcf.py`, `config/valuation.toml` |

**Efecto en cadena buscado (T5-c):** el limitador «dependencia del coste de capital» (`ke_sensitivity`) recalcula el
análisis con Ke ± 1 pp. Con F1, un DCF que en ese escenario queda a un escalón de cruzar el precio deja de votar, y el
nivel cambia. Es el limitador que la revisión pedía que se activara: V y JPM lo activan; DUK deja de activarlo.

## Golden

Regenerados tras revisar el diff. Suite: **6561 passed, 26 skipped, 0 failed**.

| Empresa | Cambio | Causa |
|---|---|---|
| NFLX (panel) | Forward +3 → +2: «Fuerte compresión 27x → 20x» → «mejorando 27x → 21x», respaldo +28 % del último ejercicio en vez de +36 % a 3 años. DCF `wacc_sensitive`: «en precio» en la convergencia. PEG 0,61 → 0,73 con el P/E normalizado | F3, F1 |
| NFLX (local) | Además, DCF +1 → 0; confianza baja → media; precio 50 → 46; calidad 85 → 91 (la confianza media la contrae menos) | F1 |
| V (local y panel) | Confianza alta → media: dependencia del Ke (con Ke − 1 pp su DCF deja de votar y pasa de «muy exigente» a «exigente»). Precio 20 → 28 (la contracción hacia 50) | F1 → T5-c |
| JPM | Forward +1 → 0 (BPA +1 % el último ejercicio: sin compresión creíble); bloque 0 → −1; confianza alta → media por la dependencia del Ke | F3 |
| DUK | Forward +2 → +1 (respaldo +11 % frente al +17 % del consenso); precio 48 → 42; confianza baja → media; calidad 64 → 66. **Veredicto: «Calidad media · precio razonable» → «Calidad sólida · precio exigente»** | F3 |
| NEE | Forward +2 → 0 (BPA −3 % el último ejercicio); precio 48 → 45 | F3 |
| MSFT, KO, PG, NVDA, TSM | `peg_basis.pe` con el P/E normalizado (sin cambio de puntos) | F3 |

Tests reescritos con el comportamiento nuevo y su porqué:
- `test_quality_price.py`: V con el limitador; el bloque de múltiplos con el respaldo del último ejercicio.
- `tests/invariants.py`: la gráfica del valor justo acepta «(sensible al WACC)» como acepta «(fiabilidad baja)».
- `tests/guardian.py`: la cabecera y el pie de página no son prosa. Un salto de página dentro de «Duke Energy» se leía
  como «índice Energy», una industria sin traducir.

## Efecto en el universo

Escaneo de las 543 con este código (caché `2026-11-04-f11-p3`, 0 errores), frente al del paso 2 (`2026-11-04-f11-p2b`):

| Regla | Paso 2 | Paso 3 |
|---|---:|---:|
| `voto_estable` (F1) | 28 | **0** |
| `inverso_tasa_base` (F2) | 24 | **0** |
| `forward_creible` (F3) | 82 | **14** |
| Resto | — | sin cambios atribuibles |

**Los 14 que quedan en `forward_creible`** acreditan más de +25 % de BPA, pero los respaldan **a la vez** los 3 años y el
último ejercicio: NVDA (+67 %), INCY, DIS, FIX, AZN, SMCI, DELL, GOOG/GOOGL, JCI, HWM, APH, NFLX (+27,6 %) y TDG. Lo
han demostrado. El 25 % es el listón que la revisión propone para las maduras (AZN, DIS, SMCI, DELL, HWM, JCI y NFLX lo
son). **Decisión del usuario:** endurecerlo para las maduras o dejarlo así. Recomendación: dejarlo. El modelo general
(V1) funde el forward en un solo voto del beneficio, y un tope fijo por tipo de empresa es justo la clase de regla que
el usuario no quiere.

**Notas de precio:** cambian 95. Atribuidas componente a componente:
- F3, forward: 27 (WM, ETN, JPM, HSBC, META, DUK, BKNG…).
- F1/F2, DCF: 25 (NFLX, CME, SPGI, PEP, HUM, AMGN, AON…).
- Limitador del Ke: 12 (VST, HRL, SNA, JBL…).
- Convergencia: 6.
- Mercado entre las dos corridas: 21, sin cambio en ningún componente que puntúe.
- Nuevo trimestre presentado durante el día: 4. FOX y FOXA, de 60 y 50 a 95 y 90: el corte pasó del 30 de junio al
  30 de septiembre y su DCF, de −3 % a +57 %.

**Veredictos:** cambian 26 etiquetas, todas de un escalón. Por ejemplo:
- MSCI: «excelente · muy exigente» → «sólida · exigente».
- VST: «sólida · atractivo» → «media · razonable», por el limitador del Ke.
- META, ETN, WM: «exigente» → «muy exigente», porque el forward ya no acredita el consenso entero.
- HONA, IR, WTW: «exigente» → «razonable», porque su DCF «cara» estaba dentro del error del WACC.

Ninguna nota de calidad cambia por el código. Las que cambian lo hacen por la contracción de la confianza (E11).
