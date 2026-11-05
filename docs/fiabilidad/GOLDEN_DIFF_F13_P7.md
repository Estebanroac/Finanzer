# F13 · Paso 7: perímetro, FFO y conciliación estable (5-nov-2026)

Familia E de la revisión de 110 empresas: escisiones y ventas leídas como declive o como ciclo, y un FFO que cambiaba
entre corridas.

## Medida inicial (paso 6, banco de 110)

| Regla | Empresas | Lo que pasaba de verdad |
|---|---|---|
| `perimetro_corregido` | 6: GE, HON, MMM, NEM, OXY, AMD | Solo **GE** es un error de perímetro. MMM: su CAGR a 3 años ya está en el perímetro reexpresado (−1,6 % es el declive real, sin Solventum). NEM, OXY y AMD: sus caídas no son escisiones (materias primas y semiconductores). HON: cíclica por 2009 y 2019–20; 2019 incluye las escisiones de Resideo y Garrett, pero 2020 (COVID) es una caída real del mismo episodio, así que la clasificación se sostiene |
| `ffo_sin_saltos` | 3: CCI, PSA, VICI | PSA: venta de PS Business Parks dentro del FFO. CCI: discontinuadas (la fibra) dentro del FFO y un CAGR que cruza el cambio. VICI: la provisión CECL de 2022, que ya da el CAGR como «no significativo» (base deprimida) |

## Qué cambia

- **Corte de la historia larga** (`perimeter.detect` → `history_break`, `perimeter.homogeneous_history`). Si una
  reexpresión cambia los ingresos al menos un `thresholds.growth.perimeter_history_break` = 30 %, la historia de EDGAR
  anterior al primer ejercicio reexpresado es otra empresa. Ya no cuenta para la ciclicidad (`classify`) ni para el
  ciclo medio del DCF (`cyclicality.mid_cycle_growth`).
  - **GE ★:** −62 % sin GE HealthCare ni GE Vernova. Salía cíclica por 2009 y 2017, episodios del conglomerado con GE
    Capital. Ahora es «crecimiento rentable»: ingresos por acción +17,5 % al año en FY2022–FY2025 y margen operativo
    del 18 %.
  - Corta también la historia de AIG y CCI, sin efecto: su arquetipo lo decide la industria. HON (−10 %) queda por
    debajo del umbral.
- **FFO sin la venta de participaciones inmobiliarias** (`data.toml [reit_ffo] gains_include`): también el concepto
  estándar `EquityMethodInvestmentRealizedGainLossOnDisposal`, que Nareit excluye. Las ventas de SPG en minoristas usan
  un concepto propio y siguen dentro, como en su FFO Nareit.
- **FFO desde el beneficio continuado** (`archetype_metrics._reit`). Antes, las discontinuadas entraban en el FFO de cada
  ejercicio: CCI 2024, −5,07 B$ de la fibra vendida, daba −6,95 $ por acción.
- **CAGR del FFO por acción sobre el perímetro homogéneo** (`main`, rama REIT). Con el perímetro cambiado dentro de la
  ventana se usan los mismos años homogéneos que en los ingresos (fase 3, T5). Antes, la rama REIT pisaba esa
  corrección con el CAGR a 3 años que cruza el cambio. El texto dice los años reales («CAGR 2 años»).
- **Conciliación estable** (`reit_ffo._reconcile`). Si a EDGAR le falta el flujo de operaciones de un estado
  presentado **después** de su último informe, el estado aún no le ha llegado: se concilia con los demás
  («conciliado_parcial») y la fila del FFO lo dice. Antes el FFO de PLD salía o no según el día, y su confianza pasaba
  de alta a baja en la misma jornada. Un estado antiguo que falte, o uno que no coincida, sigue invalidando el FFO.

## Efecto en las 110 congeladas (paso 6 → 7)

| Empresa | Antes | Después | Nota de precio |
|---|---|---|---|
| GE ★ | media · exigente (baja) | **sólida · muy exigente** (baja) | 35 → 28 (P/FCF 41x, EV/EBITDA 31x, forward 33x) |
| PSA ★ | sólida · exigente (**alta**) | sólida · exigente (**media**) | 30 → 42 |

Cambios en el FFO por acción:

| Empresa | Serie | CAGR |
|---|---|---|
| PSA | 2022: 28,69 $ → 16,55 $ | −18,4 % → −1,9 % |
| CCI | 4,14 / 4,71 / 4,74 / 7,89 (antes con −6,95) | −30,7 % → −6,5 % (2 años homogéneos) |
| AMT | sin India (discontinuada) | −7,1 % → −8,6 % |

Reglas de cordura:

| Regla | Paso 6 | Paso 7 | Lo que queda |
|---|---|---|---|
| `perimetro_corregido` | 6 | 5 | Los cinco casos que la medida no da por errores: MMM, NEM, OXY, AMD y HON. La regla es más amplia que el defecto; afinarla es medida, no motor |
| `ffo_sin_saltos` | 3 | 2 | CCI, porque 2022 está en el perímetro anterior y la regla mira la serie entera, no la ventana homogénea; y VICI (CECL) |

## Lo que queda

- **PLD FY2023:** Finnhub no trae su 10-K de 2023, así que ese ejercicio queda sin FFO. El 10-K de 2024 lo presenta
  como comparativo, pero Finnhub solo da el periodo propio de cada informe. Leerlo de la instancia XBRL de EDGAR es el
  mismo trabajo pendiente que el espectro de AT&T.
- **Base inflada del FFO:** PSA era una base inflada. La prueba general de saltos en la base del CAGR es el paso 12,
  para todos los crecimientos.

Tabla y corridas: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso7_vs_paso6.md` y `paso7/`.

## Golden

Todos los análisis llevan el campo nuevo `data_provenance.perimeter.history_break` (null si no hay corte), así que se
regeneran todos los golden (local, panel, forzados). El único cambio de fondo es **panel AMT**: su FFO ya no incluye
el negocio de India (discontinuado), y el FFO por acción pasa de −7,1 % a −8,6 % anual en 3 años. El retorno total va
de −3,2 % a −4,6 %, y el texto del DCF inverso y el «premortem» lo dicen. El veredicto no cambia. El PDF v2 de AMT se
regenera.

Tests: `tests/test_f13_paso7.py` (6). Suite: 6660 passed.
