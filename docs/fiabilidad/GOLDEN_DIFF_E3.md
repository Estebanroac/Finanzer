# Diff de los golden · escenarios del usuario (E3, Task 7)

*Operador E3, 17-oct-2026. Rama `rediseno/v4`. Regla de la etapa: los golden solo cambian con las claves aditivas del
escenario. **Aprobación: el PM, por delegación del usuario** (pendiente de su revisión en el informe de la etapa).*

**Resultado: solo claves nuevas bajo `scenario_inputs`; ningún valor existente cambia.** El veredicto, las
puntuaciones, el DCF del informe y su sensibilidad salen idénticos.

## 1. Causa

| # | Commit | Causa | Qué cambia en la salida |
|---|---|---|---|
| E3-1 | Task 7 (Cuánto vale) | `lib/scenario.extend` añade a `scenario_inputs` lo que el panel de escenarios necesita para no calcular nada en el navegador: `revenue`, `fcf_margin` (FCF base / ingresos), `archetype`, `bounds` (rangos de crecimiento, descuento, terminal y margen; el margen entre `margin_rel_min` 0.5 y `margin_rel_max` 1.5 veces el propio, `config/valuation.toml [scenario]`), `presets` (pesimista y optimista = los extremos de la tabla de sensibilidad del informe, `[valuation.grid]`, más ±0.5 pp de terminal, `[scenario.presets.default]`) y `reverse` (los insumos del DCF inverso del informe: flujo por acción, deuda neta por acción, tasa y terminal) | 23 claves nuevas por ticker con escenario (`status = "ok"`); nada en los que no lo tienen (bancos, aseguradoras, sin FCF) |

El endpoint `/api/v2/scenario` (no entra en los golden) devuelve además `implied_growth` (el mismo
`reverse_dcf.implied_growth` del informe con los supuestos del usuario) y `sensitivity` (la tabla con los pasos de
`[valuation.grid]` centrada en esos supuestos). Tests en `tests/test_scenario.py`: con los supuestos base, el valor es
el DCF del informe, el crecimiento implícito es el del DCF inverso y la sensibilidad coincide celda a celda con la del
informe (25 celdas).

## 2. Cómo se aisló

El golden del HEAD de `rediseno/v4` aún no incluye los datos nuevos de E2a (su golden regenerado está en
`rediseno/e2a-datos-motor`, que se reintegra al cerrar E2a), así que `diff_golden.py` ya mostraba diferencias antes de
este cambio. Se compararon las dos salidas `--full`: la del HEAD sin el cambio del backend (`git stash -- backend`) y
la del árbol con el cambio.

| Juego | Tickers | Con claves nuevas | Diferencia entre las dos salidas |
|---|---|---|---|
| panel | 37 | 21 | solo líneas `scenario_inputs.{revenue, fcf_margin, archetype, bounds.*, presets.*, reverse.*}: ∅ → valor`; en cada ticker el recuento de cambios sube exactamente 23 (p. ej. 336 → 359) |
| local | 6 | 3 | ídem (336 → 359) |

Ejemplo (AAPL): `archetype "MATURE"`, `bounds.growth [-0.10, 0.50]`, `bounds.discount [0.05, 0.16]`,
`bounds.terminal [0.00, 0.03]`, `bounds.fcf_margin [0.1317, 0.3952]`.

## 3. Regeneración (tras reintegrar E2a)

Con `rediseno/e2a-datos-motor` (9380a8c, su golden ya regenerado) fusionada en `rediseno/v4`, el diff frente al golden
de E2a es exactamente el de la sección 2 y nada más:

- `diff_golden.py --env panel --full`: 21 tickers con cambios; **todas** las líneas son altas `∅ → valor` bajo
  `scenario_inputs.{revenue, fcf_margin, archetype, bounds.*, presets.*, reverse.*}` (0 líneas que no sean altas);
  ningún cambio en el texto del PDF.
- `--env local`: ídem en 3 tickers.
- Regenerados con `--regenerate --yes` (panel y local): `git diff --stat` = 24 archivos `.json`, **984 inserciones,
  0 borrados**; ningún `.pdf.txt` cambia. Después, `diff_golden.py --env panel|local` → `Resultado: sin diferencias`.
- Muestras forzadas del contrato (`tests/contract_forced.py --write`, salen del juego local): solo `V_caja_neta`
  gana las mismas claves aditivas (41 inserciones).
- `npm run check` → `check-contract: StockAnalysis encaja con 46 salidas del backend`.
