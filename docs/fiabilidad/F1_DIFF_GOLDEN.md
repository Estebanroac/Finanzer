# Fase 1 — diff de golden explicado causa por causa

Se rellena en T3/T4, un apartado por commit. Los golden **no** se regeneran hasta el punto de parada 2 (T5), con la
aprobación del usuario. Mientras tanto la regresión de golden falla a propósito; el resto de la suite, en verde.

Comandos: `cd backend && ../.venv313/bin/python tests/diff_golden.py --env panel` y `... tests/diff_golden.py`
(juego `local`).

---

## T3.1 — Cobertura de intereses por el signo del EBIT y del resultado financiero

**Causa.** El estado de la cobertura se decidía con el signo del cociente. PLTR cobra más intereses de los que
paga (resultado financiero neto +77.5 M en el último trimestre, +266.4 M TTM; *Net Non Operating Interest Income
Expense* de los estados del plan B), Finnhub da una cobertura de −1.53 y el motor la leía como "EBIT negativo con
caja neta" con un EBIT de +2.63 B.

**Regla nueva** (`financial_ratios.interest_coverage_state`): con EBIT > 0 y cobertura negativa o ausente, el estado
es `sin_carga` si el resultado financiero neto es ≥ 0 **en el TTM y en cada uno de sus 4 trimestres** (un trimestre
atípico no basta: NFLX 2026-03 trae +2.85 B de ingresos financieros y su TTM sale +2.14 B, con los otros tres
trimestres y el anual negativos). Sin esa fila en los estados, se infiere del signo de la cobertura y queda en
`data_provenance` como inferido. No se infirió en ningún ticker del panel ni de `local`.

### Cambios de estado
| Juego | Ticker | Antes | Después |
|---|---|---|---|
| panel | PLTR | `no_significativo` | `sin_carga` |
| resto (29 + 6) | — | sin cambio | sin cambio |

### PLTR (panel): Kd, WACC, DCF y nivel de precio
| Magnitud | Antes | Después | Por qué |
|---|---|---|---|
| Rating sintético | BBB (regla M, tramo de caja neta) | AAA (mejor tramo) | sin carga financiera neta |
| Kd | 6.40% | 5.69% | Rf 5.29% + spread AAA |
| Kd después de impuestos | 5.76% | 5.12% | |
| Peso de la deuda | 0.04% | 0.04% | caja neta: deuda casi nula frente a la capitalización |
| WACC | 11.25181% | 11.25153% | −0.0003 pp: el peso de la deuda es casi cero |
| DCF, valor razonable | 44.22 | 44.22 | sin cambio al céntimo |
| DCF, upside | −78.0% | −78.0% | sin cambio |
| Rejilla de sensibilidad | | ±0.01 en 2 celdas; media 43.8875 → 43.8885 | el WACC base |
| Solidez financiera, fila de cobertura | 0 (no significativa) | +3 (tramo superior) | |
| Solidez financiera, categoría | 20/20 | 20/20 | ya estaba en el tope: la puntuación total no cambia |
| Veredicto / nivel de precio | Calidad excelente · precio exigente | igual | sin cambio |

El nivel de precio **no** cambia.

### Texto (web y PDF de PLTR)
- Resumen, solvencia, lectura y gauge: "con EBIT negativo y caja neta, la cobertura de intereses no es
  significativa: los intereses se pagan con caja" → "sin carga financiera neta: los ingresos financieros cubren los
  gastos financieros y el resultado operativo es positivo".
- Fila de cobertura en solvencia: "—" / "No significativa" → "Sin carga" / "Sin carga financiera".
- Nota del WACC: "Kd 6.40% … BBB … regla M: EBIT < 0 con caja neta" → "Kd 5.69% … AAA … sin carga financiera neta
  (EBIT > 0 e ingresos financieros netos) -> mejor tramo".
- `data_validation` y `data_provenance` de la cobertura: el motivo pasa de "EBIT < 0 con caja neta" a "EBIT > 0 y
  los ingresos financieros superan a los gastos".
- `confidence.dimensions.coverage.coverage` 0.944 → 0.947 y `score_coverage.solidez` 2 → 3 evaluadas: la cobertura
  vuelve a contar como componente evaluado.

### Cambios aditivos en el resto (36 tickers entre panel y `local`)
- `key_metrics.net_interest_income` (nuevo campo; `null` donde falta un trimestre, p. ej. JPM).
- `data_provenance.fields.netInterestIncome` (TTM, suma de 4 trimestres) o
  `data_provenance.ttm.source_fields.netInterestIncome` (por qué no hay TTM).
- `data_provenance.ttm.ttm_fields`: entra `netInterestIncome` y desplaza el orden alfabético de la lista.

Ningún otro campo cambia fuera de PLTR (comprobado filtrando el diff por estos tres campos: salida vacía).
