# Diff de los golden · emparejamiento tolerante de ADR en `industry_bench.firm` (E2b)

*Operador E2b, 17-oct-2026. Rama `rediseno/e2b-segmentos-rivales-tendencias`, commit propio del arreglo del motor
(el de este documento). **Aprobado por el PM por delegación del usuario.** Cita del usuario (delegación de las
aprobaciones de la etapa en el PM): "recuerda, que esto se autoapruebe. confío plenamente en ti".*

**Resultado: los golden NO cambian.** `tests/diff_golden.py --env panel` → `Resultado: sin diferencias` (37 tickers);
`tests/diff_golden.py --env local` → `Resultado: sin diferencias` (6). No se regeneró nada (tampoco las muestras forzadas
del contrato, que salen del juego local).

## 1. Causa

| # | Commit | Causa | Qué cambia en la salida |
|---|---|---|---|
| E2b-1 | (este) | `industry_bench.firm`, para un ADR que no empareja por nombre legal y país exactos, prueba un nombre **tolerante** (`lenient_name`: sin sufijos de EDGAR como `/ON/` o `/UK` ni letras sueltas: "BP p.l.c." de Damodaran = "BP PLC" de EDGAR) y el país tras la última coma (`country_key`: "Ontario, Canada" → "Canada"). Solo con **coincidencia única**: si dos empresas de Damodaran del mismo país comparten nombre tolerante con distinta clasificación, no empareja (sería una conjetura). | La industria de referencia de un ADR que antes salía por el mapa de la industria de Yahoo y ahora sale de la clasificación de la propia empresa en Damodaran; el texto `benchmark.industry.classified` ("nombre legal tolerante (ADR)") |

Función compartida, nada copiado: `tools/build_universe.py` llama a `industry_bench.firm` (antes llevaba su propia
versión tolerante, solo para el universo). El universo regenerado es **idéntico** byte a byte al anterior (530/543 con
industria).

## 2. Por ticker

### Golden (panel y local)

Ningún ticker afectado: todos los ADR del panel (ASML, BCS, HSBC, NVO, SHEL, TM, TSM, UL) ya emparejaban por nombre
legal exacto o por símbolo, y V usa el mercado amplio (su arquetipo contradice al sector). Comprobado en los golden:
ningún ticker tenía `classified` = mapa de Yahoo.

### Fuera del juego de pruebas (análisis en vivo, mismo día, antes y después del cambio)

| Ticker | País (análisis) | Industria antes → después | Cómo antes → después | Comprobación en la lista de Damodaran (`config/damodaran_firms.tsv.gz`, indname) | Veredicto antes → después |
|---|---|---|---|---|---|
| **BP** | United Kingdom | Oil/Gas (Integrated), europe → **igual** | mapa de Yahoo → nombre legal tolerante (ADR) | "BP p.l.c." · United Kingdom · Oil/Gas (Integrated) · Europe (`bp p l c\|United Kingdom`; único con nombre tolerante "bp" en el Reino Unido) | Calidad débil · precio atractivo (44/85, alta) → **igual** |
| RY | Canada | Bank (Money Center), global → igual | nombre legal (ADR) → igual | `royal bank of canada\|Canada` | Calidad excelente · precio exigente → igual |
| TD | Canada | Bank (Money Center), global → igual | nombre legal (ADR) → igual | `toronto dominion bank\|Canada` | Calidad sólida · precio razonable → igual |
| ENB | Canada | Oil/Gas Distribution, global → igual | nombre legal (ADR) → igual | `enbridge\|Canada` | Calidad media · precio muy exigente → igual |
| CNQ | Canada | Oil/Gas (Production and Exploration), global → igual | nombre legal (ADR) → igual | `canadian natural resources\|Canada` | Calidad excelente · precio razonable → igual |
| BN | Canada | mercado amplio → igual (su arquetipo contradice al sector: no usa industria) | — | `brookfield\|Canada` (Investments & Asset Management) | Calidad débil · precio razonable → igual |
| ARM | United Kingdom | Semiconductor (mapa de Yahoo), europe → igual | mapa de Yahoo → igual | **No figura** en la lista de Damodaran (salió a bolsa en 2023): no empareja, correcto | Calidad excelente · precio muy exigente → igual |

Los canadienses ya emparejaban en el análisis porque el país del perfil llega normalizado ("Canada"); el arreglo de
`country_key` les sirve a quien llame con el país de EDGAR tal cual (la herramienta del universo). En BP la industria
coincide con la del mapa de Yahoo, así que solo cambia el texto de cómo se clasificó.

## 3. Tests

`tests/test_industry_bench.py`: nombre tolerante y país (`lenient_name`, `country_key`); BP por nombre tolerante, RY
con la provincia delante, ARM sin fila, el camino exacto intacto (BCS) y una empresa de EE. UU. que no empareja por
nombre; y la **unicidad**: dos empresas del Reino Unido con el mismo nombre tolerante y distinta industria no emparejan.
