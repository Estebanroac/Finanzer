# Inventario del modelo de Finanzer

> Generado por `backend/tools/model_inventory.py` desde el código (commit `ed0306e5`), la config (`backend/config/*.toml`) y una muestra medida: el escaneo del universo del 2026-10-29 (`ESCANEO_2026-10-29.json`) (543 empresas: MAD 333, CIC 60, FIN 52, CRE 41, UTI 28, REIT 28, PRE 1). No editar a mano. Lo escrito a mano está marcado como *juicio* (la fórmula y la referencia de cada componente, la propuesta de tipos objetivo y las candidatas a simplificar).

Arquetipos: **MAD** = MATURE, **CRE** = GROWTH_PROFITABLE, **CIC** = CYCLICAL, **PRE** = GROWTH_PRE_PROFIT, **FIN** = FINANCIAL, **REIT** = REIT, **UTI** = UTILITY. En la tabla de aplicabilidad, **A** = aplica (se registra, con o sin dato), **ns** = solo como no significativo, **–** = no aplica (no se registra o se registra como «no aplica»), **?** = el arquetipo no está en la muestra.

## 1. Resumen numérico

- **47 variables que puntúan** (componentes de la cobertura de las 5 categorías): **1 universales** (aplican a los 7 arquetipos), **10 casi universales** (a 5 o 6: las apagan las listas «no aplica»), **34 específicas** (a 4 o menos; casi todas, a uno solo) y **2 muertas** (se registran pero no aplican a ningún arquetipo de la muestra: «D/E bancario» (Solidez Financiera), «P/B» (Solidez Financiera)).
- **2 ajustes que puntúan fuera de la cobertura** (bonos y topes que no cuentan como componente: Forward P/E, tope por ROIC − WACC…), medidos en el desglose de la muestra.
- **158 ramas por arquetipo o subtipo en el código** (comparaciones `archetype == …`, `subtype == …`) en 12 archivos; las que más: `backend/lib/display.py` 42, `backend/main.py` 36, `backend/lib/financial_ratios.py` 35, `backend/lib/alert_interpretations.py` 11, `backend/lib/archetype_metrics.py` 11, `backend/lib/display_charts.py` 10.
- **64 entradas «no aplica»** por arquetipo en `sectors.archetypes.not_applicable` (FIN 20, REIT 19, PRE 10, CIC 4, UTI 11, MAD 0, CRE 0) y 1 por subtipo; las leen 104 sitios del código.
- **80 ajustes de umbral por sector** en 11 sectores (`sectors.score_thresholds.overrides`), todos marcados PROVISIONAL.
- **725 claves de config leídas** en 1330 sitios (lecturas, alertas, veredicto, confianza; §4).

Por arquetipo: cuántas variables puntúan en cada uno y cuántas son solo suyas.

| Arquetipo | Empresas en la muestra | Variables que aplican | Universales | Casi universales | Específicas | Solo suyas |
|---|---:|---:|---:|---:|---:|---:|
| MATURE | 333 | 23 | 1 | 10 | 12 | 0 |
| GROWTH_PROFITABLE | 41 | 23 | 1 | 10 | 12 | 0 |
| CYCLICAL | 60 | 20 | 1 | 10 | 9 | 0 |
| GROWTH_PRE_PROFIT | 1 | 18 | 1 | 6 | 11 | 7 |
| FINANCIAL | 52 | 14 | 1 | 5 | 8 | 7 |
| REIT | 28 | 13 | 1 | 3 | 9 | 5 |
| UTILITY | 28 | 15 | 1 | 9 | 5 | 2 |

## 2. Tipos de empresa: los de hoy frente a la lista cerrada objetivo

Objetivo (decisión del usuario, 28-oct-2026): **empresa general**, **banco**, **aseguradora**, **REIT**, **utility**, **sin beneficios aún**.

| Tipo de hoy | Reglas de `classify.py` que lo deciden (línea) | Empresas en el universo | Iría a (*juicio*) | Por qué |
|---|---|---:|---|---|
| MATURE | `por_defecto` (582), `ciclica_condicional_estable` (571), `excepcion_financiera` (445), `red_de_pagos` (452) | 333 | empresa general | es el caso por defecto; sus herramientas son las generales |
| GROWTH_PROFITABLE | `crecimiento_rentable` (561) | 41 | empresa general | no tiene herramienta propia (`not_applicable` vacío, «provisional» desde la fase 3): solo cambia la etiqueta |
| CYCLICAL | `historia_ciclica` (520), `industria_ciclica` (531), `industria_ciclica_condicional` (538) | 60 | empresa general | lo que cambia es el MÉTODO (ciclo medio, normalizados), no la contabilidad: una opción de normalización de cualquier empresa |
| GROWTH_PRE_PROFIT | `pre_beneficio_con_crecimiento` (492) | 1 | sin beneficios aún | se queda: sin beneficio, los múltiplos de beneficio y el Altman no tienen sentido |
| FINANCIAL · banco | `industria_banco` (427) | 26 | banco | se queda (balance = producto) |
| FINANCIAL · aseguradora | `industria_aseguradora` (439) | 16 | aseguradora | se queda; hoy comparte TODAS las herramientas del banco |
| FINANCIAL · conglomerado | `industria_aseguradora` (434) | 1 | aseguradora | subtipo de aseguradora (BRK-B): o aseguradora, o empresa general con su negocio asegurador como segmento |
| FINANCIAL · financiera | `financiera_ambigua` (466), `credito_con_balance` (463) | 9 | banco | prestamistas de Credit Services y financieras ambiguas: contabilidad de banco |
| REIT | `industria_reit` (474) | 28 | REIT | se queda (FFO) |
| UTILITY | `industria_utility` (479) | 28 | utility | se queda (base regulada, FCF negativo por diseño) |

**Qué sobra o se solapa** (*juicio*, con las cifras de arriba):

- **Sobran como tipos 3 de 7 arquetipos**: GROWTH_PROFITABLE (sin ninguna herramienta propia: su lista «no aplica» está vacía y puntúa exactamente con las de MATURE), CYCLICAL (cambia el método —ciclo medio, P/FCF y EV/EBITDA normalizados, sin P/E ni PEG— no la contabilidad) y MATURE, que es la «empresa general». Los tres se pueden fundir en uno: la normalización del ciclo pasa a ser una propiedad medida (la historia de EDGAR ya decide `historia_ciclica`) que cualquier empresa puede tener.
- **FINANCIAL es dos tipos con un solo juego de herramientas**: banco y aseguradora comparten la solidez bancaria, el D/E bancario, el P/B y P/TBV justificados y la estabilidad del ROE; solo los distingue el margen neto (F9 · R4: no aplica al banco). La lista objetivo los separa: la aseguradora necesitará su ratio combinado o su resultado técnico, hoy inexistentes.
- **Subtipos que se solapan**: «conglomerado» (aseguradora con ≥ 50 % de ingresos no aseguradores, BRK-B) y «financiera» (Credit Services con balance y financieras ambiguas) no tienen herramienta propia: el primero es una aseguradora, el segundo un banco.
- **Excepciones dentro de un tipo que ya son reglas generales**: las redes de pago y las gestoras dentro de Financial Services ya son MATURE (empresa general); las industrias de circulante negativo y de Altman referencial (§5.4) son lecturas por modelo de negocio, no tipos.
- Con la propuesta, el universo queda en: empresa general (3 tipos de hoy), banco (2 tipos de hoy), aseguradora (2 tipos de hoy), REIT (1 tipos de hoy), utility (1 tipos de hoy), sin beneficios aún (1 tipos de hoy).

## 3. Variables que puntúan

Una fila por componente de la cobertura (`CategoryCoverage.comp`, `not_sig`, `derived_comp`). **Banda**: la clave de puntos y su umbral en config con su valor. **Origen del umbral**: PROVISIONAL si el TOML lo marca así, «calibrado» si su comentario cita la muestra con que se fijó. **Fórmula** y **referencia**: *juicio* (META).

### Solidez Financiera

| Variable | Fórmula | Referencia | Banda (config) | Origen del umbral | MAD | CRE | CIC | PRE | FIN | REIT | UTI | Alcance | Peso medido (empresas · \|ajuste\| medio · % que mueve) | «No aplica» | Condición en el código | Dónde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Altman Z** | altman | modelo (zona del Z por SIC) | `solidez.altman_points` = [3, -1, -3] | fijado a mano / modelo | A | A | A | – | – | – | – | específica | 352 · 2.6 · 100% | `altman` | — | backend/lib/financial_ratios.py:2029, backend/lib/financial_ratios.py:2033 |
| **Cobertura de intereses** | interest_coverage | absoluta (bandas propias de utility) | `solidez.coverage_points` = [3, 1, 0, -2, -3]; `solidez.coverage_bounds` = [10, 5, 3, 1.5] | fijado a mano / modelo | A | A | A | A | – | A | A | casi universal | 489 · 1.8 · 83% | `interest_coverage` | — | backend/lib/financial_ratios.py:2067, backend/lib/financial_ratios.py:2069 |
| **Current ratio** | current_ratio | absoluta | `solidez.current_points` = [4, 2, 0, -2, -4]; `solidez.current_bounds` = [2, 1.5, 1, 0.8] | fijado a mano / modelo | A | A | A | A | – | – | – | específica | 411 · 1.9 · 63% | `current_ratio` | — | backend/lib/financial_ratios.py:2037, backend/lib/financial_ratios.py:2039 |
| **D/E** | de | sector (× umbral D/E del sector) | `solidez.de_mitigated_points` = -2; `solidez.de_points` = [5, 2, 0, -2]; `solidez.de_mults` = [0.5, 1.3, 1.6]; `solidez.de_severe_points` = -5 | fijado a mano / modelo | A | A | A | – | – | – | – | específica | 306 · 2.8 · 88% | `de` | not _de_info and archetype != REIT | backend/lib/financial_ratios.py:2064 |
| **D/E bancario** | de | absoluta (sectors.financials.benchmarks) | `solidez_financial.de_points` = [3, 2, 0, -2] | fijado a mano / modelo | – | – | – | – | – | – | – | muerta | — | `de` | — | backend/lib/financial_ratios.py:2240 |
| **Deuda neta/EBITDA** | net_debt_to_ebitda | absoluta (bandas de REIT o de utility) | `solidez.reit_nde_points` = [4, 2, 0, -2, -4]; `solidez.reit_nde_bounds` = [5, 6.5, 7.5, 9]; `solidez.utility_nde_points` = [4, 2, 0, -2, -4]; `solidez.utility_nde_bounds` = [4.5, 5.5, 6.5, 7.5] | PROVISIONAL | – | – | – | – | – | A | A | específica | 56 · 2.2 · 75% | — | archetype in (REIT, UTILITY) | backend/lib/financial_ratios.py:2062 |
| **P/B** | pb | absoluta (sectors.financials.benchmarks) | `solidez_financial.pb_points` = [2, 1, 0, -1] | fijado a mano / modelo | – | – | – | – | – | – | – | muerta | — | — | archetype != FINANCIAL | backend/lib/financial_ratios.py:2242 |
| **Runway** | runway | absoluta | `solidez.runway_points` = [6, 2, -2, -6]; `solidez.runway_bounds` = [3, 2, 1] | fijado a mano / modelo | – | – | – | A | – | – | – | específica | 1 · 6.0 · 100% | — | archetype == GROWTH_PRE_PROFIT | backend/lib/financial_ratios.py:2035 |
| **Salud bancaria** | financial_health | absoluta (sectors.financials.benchmarks) | `solidez_financial.health_multiplier` = 1.4; `solidez_financial.health_offset` = 4 | fijado a mano / modelo | – | – | – | – | A | – | – | específica | 52 · 7.0 · 100% | — | — | backend/lib/financial_ratios.py:2239 |
### Rentabilidad

| Variable | Fórmula | Referencia | Banda (config) | Origen del umbral | MAD | CRE | CIC | PRE | FIN | REIT | UTI | Alcance | Peso medido (empresas · \|ajuste\| medio · % que mueve) | «No aplica» | Condición en el código | Dónde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **FFO / activos** | FFO / activos totales | absoluta (quintiles de 24 REIT, fase 7) | `rentabilidad.reit_ffo_assets_points` = [6, 3, 0, -3, -6]; `rentabilidad.reit_ffo_assets_bounds` = [0.09, 0.07, 0.06, 0.05] | calibrado | – | – | – | – | – | A | – | específica | 20 · 3.8 · 85% | — | archetype == REIT | backend/lib/financial_ratios.py:3113 |
| **Margen FCF − SBC** | fcf_minus_sbc | absoluta | `rentabilidad.gpp_fcf_margin_points` = [5, 3, 0, -3, -5]; `rentabilidad.gpp_fcf_margin_bounds` = [0.2, 0.1, 0, -0.1] | fijado a mano / modelo | – | – | – | A | – | – | – | específica | 1 · 0.0 · 0% | — | archetype == GROWTH_PRE_PROFIT | backend/lib/financial_ratios.py:3167, backend/lib/financial_ratios.py:3173 |
| **Margen FFO** | FFO / ingresos | absoluta (PROVISIONAL) | `rentabilidad.reit_ffo_margin_points` = [5, 3, 0, -3, -5]; `rentabilidad.reit_ffo_margin_bounds` = [0.6, 0.5, 0.4, 0.25] | PROVISIONAL | – | – | – | – | – | A | – | específica | 20 · 2.7 · 70% | — | archetype == REIT | backend/lib/financial_ratios.py:3115 |
| **Margen bruto** | gross_margin | absoluta (PROVISIONAL) | `rentabilidad.gpp_gross_margin_points` = [5, 3, 0, -3, -5]; `rentabilidad.gpp_gross_margin_bounds` = [0.75, 0.65, 0.5, 0.35] | PROVISIONAL | – | – | – | A | – | – | – | específica | 1 · 3.0 · 100% | — | archetype == GROWTH_PRE_PROFIT | backend/lib/financial_ratios.py:3139, backend/lib/financial_ratios.py:3143 |
| **Margen neto** | net_margin | industria (pp frente a Damodaran; si no, absoluta) | `rentabilidad.net_margin_points` = [3, 2, 0, -2, -3]; `rentabilidad.net_margin_bounds` = [0.2, 0.1, 0.05]; `rentabilidad.net_margin_vs_industry_pp` = [0.12, 0.04, -0.03] | fijado a mano / modelo | A | A | A | – | A | – | A | casi universal | 488 · 1.6 · 67% | `net_margin` | — | backend/lib/financial_ratios.py:2471 |
| **Margen operativo** | operating_margin | industria (pp frente a Damodaran; si no, absoluta). PRE: absoluta propia | `rentabilidad.gpp_operating_margin_points` = [5, 3, 0, -3, -5]; `rentabilidad.gpp_operating_margin_bounds` = [0, -0.1, -0.2, -0.3]; `rentabilidad.operating_margin_points` = [5, 3, 1, -1, -3, -5]; `rentabilidad.operating_margin_bounds` = [0.3, 0.2, 0.1, 0.05] | calibrado | A | A | A | A | – | – | A | casi universal | 463 · 2.4 · 100% | `operating_margin` | archetype == GROWTH_PRE_PROFIT | backend/lib/financial_ratios.py:2470, backend/lib/financial_ratios.py:3147, backend/lib/financial_ratios.py:3153 |
| **Mejora del margen operativo** | margen operativo FY − FY anterior (pp) | propia (interanual) | `rentabilidad.gpp_opm_change_points` = [4, 2, 0, -2, -4]; `rentabilidad.gpp_opm_change_bounds` = [0.05, 0.02, 0, -0.03] | fijado a mano / modelo | – | – | – | A | – | – | – | específica | 1 · 4.0 · 100% | — | archetype == GROWTH_PRE_PROFIT | backend/lib/financial_ratios.py:3157, backend/lib/financial_ratios.py:3162 |
| **ROA** | roa | sector (roa_high / roa_low) | `rentabilidad.roa_points` = [4, 2, 0, -2, -4] | fijado a mano / modelo | A | A | A | – | A | – | A | casi universal | 513 · 1.4 · 46% | — | — | backend/lib/financial_ratios.py:2469 |
| **ROE** | roe | sector (roe_high / roe_low) | `rentabilidad.roe_points` = [6, 4, 2, -2, -4, -6] | fijado a mano / modelo | A | A | A | – | A | – | A | casi universal | 479 · 3.8 · 100% | — | — | backend/lib/financial_ratios.py:2468 |
| **ROIC−WACC** | roic_wacc_spread | absoluta (diferencial en pp) | `rentabilidad.spread_points` = [3, 2, 1, -1, -3]; `rentabilidad.spread_bounds` = [0.1, 0.03, 0, -0.03] | fijado a mano / modelo | A | A | A | – | – | – | A | específica | 436 · 2.2 · 100% | `roic_wacc` | — | backend/lib/financial_ratios.py:2473, backend/lib/financial_ratios.py:2476, backend/lib/financial_ratios.py:2480 |
### Valoración

| Variable | Fórmula | Referencia | Banda (config) | Origen del umbral | MAD | CRE | CIC | PRE | FIN | REIT | UTI | Alcance | Peso medido (empresas · \|ajuste\| medio · % que mueve) | «No aplica» | Condición en el código | Dónde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Bloque de múltiplos** | multiples_block | derivado (media de P/E, Forward P/E, P/FCF, EV/EBITDA, PEG) | `valoracion.multiples_block_max_by_members` = [2, 4, 6] | fijado a mano / modelo | A | A | A | A | A | A | A | universal | 541 · 2.2 · 85% | — | — | backend/lib/financial_ratios.py:3038 |
| **Bloque P/B y P/TBV** | pb_block | derivado (media de sus miembros) | `valoracion.multiples_block_max_by_members` = [2, 4, 6] | fijado a mano / modelo | – | – | – | – | A | – | – | específica | 52 · 2.9 · 92% | — | archetype == FINANCIAL | backend/lib/financial_ratios.py:3012 |
| **DCF** | dcf_upside | modelo (valor frente al precio, con su fiabilidad) | `valoracion.dcf_points_high` = [4, 2, 0, -2, -4]; `valoracion.dcf_upside_bounds` = [0.3, 0.1, -0.1, -0.3] | fijado a mano / modelo | A | A | A | A | – | – | – | específica | 393 · 2.5 · 90% | `dcf` | — | backend/lib/financial_ratios.py:3044, backend/lib/financial_ratios.py:3048 |
| **DCF inverso** | reverse_dcf | tasas base (crecimiento implícito frente a comparables); el flujo lo dice el nombre: FFO, FCF, FCF − SBC o el de mantenimiento | `valoracion.dcf_points_high` = [4, 2, 0, -2, -4]; `valoracion.dcf_upside_bounds` = [0.3, 0.1, -0.1, -0.3] | fijado a mano / modelo | A | A | A | – | – | A | – | específica | 48 · 2.7 · 83% | — | — | backend/lib/financial_ratios.py:3040, backend/lib/financial_ratios.py:3046 |
| **EV/EBITDA** | ev_ebitda | industria o sector (× su EV/EBITDA) | `valoracion.ev_ebitda_value_points` = [4, 2, 0, -2, -4]; `valoracion.ev_ebitda_value_mults` = [0.7, 1.2, 1.5]; `valoracion.ev_ebitda_value_mults` = [0.7, 1.2, 1.5] | fijado a mano / modelo | A | A | A | A | – | A | – | casi universal | 453 · 2.6 · 82% | `ev_ebitda` | — | backend/lib/financial_ratios.py:3027 |
| **EV/Ventas** | ev_sales | absoluta (PROVISIONAL) | `valoracion.ev_sales_points` = [4, 2, 0, -2, -4]; `valoracion.ev_sales_bounds` = [5, 10, 15, 25] | fijado a mano / modelo | – | – | – | A | – | – | – | específica | 1 · 4.0 · 100% | — | archetype == GROWTH_PRE_PROFIT | backend/lib/financial_ratios.py:3019 |
| **P/B frente a ROE** | pb_roe | propia (P/B justificado (ROE − g)/(Ke − g)) | `valoracion.financial_pb_points` = [4, 2, 0, -2, -4]; `valoracion.financial_pb_ratio_bounds` = [0.7, 0.9, 1.1, 1.4] | fijado a mano / modelo | – | – | – | – | A | – | – | específica | 52 · 3.2 · 94% | — | archetype == FINANCIAL | backend/lib/financial_ratios.py:3009 |
| **P/B frente al ROE regulado** | pb_roe | propia (P/B justificado con el ROE autorizado por el regulador) | — | — | – | – | – | – | – | – | A | específica | 28 · 3.6 · 96% | — | — | (solo medido) |
| **P/E** | pe | industria o sector (× su P/E) | `valoracion.pe_value_points` = [5, 3, 0, -2, -4]; `valoracion.pe_value_mults` = [0.7, 0.9, 1.1, 1.3]; `valoracion.pe_value_mults` = [0.7, 0.9, 1.1, 1.3] | fijado a mano / modelo | A | A | – | – | A | – | A | específica | 436 · 2.9 · 79% | `pe` | no (is_reit and archetype is None) | backend/lib/financial_ratios.py:3025 |
| **P/FCF** | pfcf | absoluta | `valoracion.pfcf_value_points` = [4, 2, 0, -2, -4]; `valoracion.pfcf_value_bounds` = [12, 18, 25, 35]; `valoracion.pfcf_value_bounds` = [12, 18, 25, 35] | fijado a mano / modelo | A | A | A | A | – | – | – | específica | 413 · 2.2 · 75% | `p_fcf` | no (is_reit and archetype is None) | backend/lib/financial_ratios.py:3026 |
| **P/FFO** | p_ffo | absoluta (contrastada en la fase 7) | `valoracion.reit_pffo_points` = [4, 2, 0, -2, -4]; `valoracion.reit_pffo_bounds` = [12, 16, 20, 25] | calibrado | – | – | – | – | – | A | – | específica | 20 · 2.3 · 80% | — | is_reit | backend/lib/financial_ratios.py:3014 |
| **P/TBV frente a ROTE** | ptbv | propia (P/TBV justificado) | `valoracion.financial_pb_points` = [4, 2, 0, -2, -4]; `valoracion.financial_pb_ratio_bounds` = [0.7, 0.9, 1.1, 1.4] | fijado a mano / modelo | – | – | – | – | A | – | – | específica | 52 · 2.8 · 90% | — | archetype == FINANCIAL | backend/lib/financial_ratios.py:3010 |
| **PEG** | peg | absoluta | `valoracion.peg_points` = [4, 2, 0, -2, -3]; `valoracion.peg_bounds` = [0.8, 1.2, 1.8, 2.5] | fijado a mano / modelo | A | A | – | – | – | – | – | específica | 143 · 2.2 · 75% | `peg` | — | backend/lib/financial_ratios.py:3030, backend/lib/financial_ratios.py:3032 |
| **Regla de 40** | rule_of_40 | absoluta | `valoracion.rule_of_40_points` = [4, 2, 0, -2, -4]; `valoracion.rule_of_40_bounds` = [0.6, 0.4, 0.25, 0.1] | fijado a mano / modelo | – | – | – | A | – | – | – | específica | 1 · 2.0 · 100% | — | archetype == GROWTH_PRE_PROFIT | backend/lib/financial_ratios.py:3020 |
| **Rentabilidad por dividendo** | dividend_yield | absoluta (bandas de utility) | `valoracion.utility_yield_points` = [4, 2, 0, -2, -4]; `valoracion.utility_yield_bounds` = [0.05, 0.04, 0.03, 0.02] | calibrado | – | – | – | – | – | – | A | específica | 28 · 1.0 · 43% | — | archetype == UTILITY | backend/lib/financial_ratios.py:3016 |
### Calidad de Ganancias

| Variable | Fórmula | Referencia | Banda (config) | Origen del umbral | MAD | CRE | CIC | PRE | FIN | REIT | UTI | Alcance | Peso medido (empresas · \|ajuste\| medio · % que mueve) | «No aplica» | Condición en el código | Dónde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Crecimiento del valor en libros** | CAGR 3 años del valor en libros tangible | absoluta | `calidad.financial_bv_growth_points` = [3, 1, -1, -3]; `calidad.financial_bv_growth_bounds` = [0.08, 0.05, 0] | fijado a mano / modelo | – | – | – | – | A | – | – | específica | 51 · 2.3 · 100% | — | archetype == FINANCIAL | backend/lib/financial_ratios.py:3353 |
| **Eficiencia (aprox.)** | gastos no financieros / ingresos | absoluta | `calidad.financial_efficiency_points` = [3, 1, -1, -3]; `calidad.financial_efficiency_bounds` = [0.55, 0.6, 0.65] | fijado a mano / modelo | – | – | – | – | A | – | – | específica | 29 · 2.0 · 100% | — | archetype == FINANCIAL | backend/lib/financial_ratios.py:3351 |
| **Estabilidad del ROE** | desviación típica del ROE anual | absoluta | `calidad.financial_roe_std_points` = [3, 1, -1, -3]; `calidad.financial_roe_std_bounds` = [0.02, 0.04, 0.06] | fijado a mano / modelo | – | – | – | – | A | – | – | específica | 51 · 2.2 · 100% | — | archetype == FINANCIAL | backend/lib/financial_ratios.py:3348, backend/lib/financial_ratios.py:3350 |
| **FCF** | free_cash_flow | signo | `calidad.fcf_points` = [3, -4] | fijado a mano / modelo | A | A | A | – | – | A | – | específica | 461 · 3.1 · 100% | `fcf` | — | backend/lib/financial_ratios.py:3360 |
| **FCF / beneficio neto** | FCF / beneficio neto | absoluta | `calidad.fcf_to_ni_points` = [3, 1, 0, -2]; `calidad.fcf_to_ni_bounds` = [1, 0.7, 0.3] | fijado a mano / modelo | A | A | A | – | – | – | – | específica | 416 · 2.2 · 90% | `fcf_to_ni` | — | backend/lib/financial_ratios.py:3363, backend/lib/financial_ratios.py:3365 |
| **FCF − SBC** | fcf_minus_sbc | signo | `calidad.fcf_points` = [3, -4] | fijado a mano / modelo | – | – | – | A | – | – | – | específica | 1 · 3.0 · 100% | `fcf` | — | backend/lib/financial_ratios.py:3360 |
| **Flujo operativo** | flujo de caja operativo > 0 | signo | `calidad.ocf_points` = [3, -4] | fijado a mano / modelo | A | A | A | A | – | A | A | casi universal | 491 · 3.0 · 100% | `ocf` | — | backend/lib/financial_ratios.py:3359 |
| **Payout sobre FFO** | dividendos / FFO | absoluta | `calidad.reit_ffo_payout_points` = [3, 1, -1, -3]; `calidad.reit_ffo_payout_bounds` = [0.75, 0.85, 0.95] | fijado a mano / modelo | – | – | – | – | – | A | – | específica | 20 · 2.7 · 100% | — | archetype == REIT | backend/lib/financial_ratios.py:3356 |
| **Piotroski F** | piotroski | modelo (9 criterios) | `calidad.fscore_points` = [7, 4, 0, -4, -7] | fijado a mano / modelo | A | A | A | A | – | – | A | casi universal | 463 · 2.9 · 63% | `piotroski` | — | backend/lib/financial_ratios.py:3358 |
### Crecimiento

| Variable | Fórmula | Referencia | Banda (config) | Origen del umbral | MAD | CRE | CIC | PRE | FIN | REIT | UTI | Alcance | Peso medido (empresas · \|ajuste\| medio · % que mueve) | «No aplica» | Condición en el código | Dónde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Crecimiento de ingresos** | revenue_growth | absoluta (MATURE con dividendo ≥ 4 %: retorno total) | `crecimiento.revenue_points` = [5, 3, 1, -1, -4]; `crecimiento.revenue_bounds` = [0.2, 0.1, 0.03] | fijado a mano / modelo | A | A | A | A | A | – | A | casi universal | 511 · 2.0 · 100% | — | no (_reit) | backend/lib/financial_ratios.py:3568 |
| **Crecimiento del BPA** | earnings_growth | absoluta | `crecimiento.eps_points` = [5, 3, 1, -1, -4]; `crecimiento.eps_bounds` = [0.25, 0.12, 0.05] | fijado a mano / modelo | A | A | A | – | A | – | A | casi universal | 413 · 2.9 · 100% | `eps_growth` | — | backend/lib/financial_ratios.py:3578, backend/lib/financial_ratios.py:3580 |
| **Crecimiento del FCF** | CAGR 3 años del FCF (por acción en REIT; FCF − SBC en PRE) | absoluta | `crecimiento.fcf_points` = [4, 2, 0, -3]; `crecimiento.fcf_bounds` = [0.15, 0.05, -0.05] | fijado a mano / modelo | A | A | – | ns | – | A | – | específica | 340 · 2.5 · 80% | `fcf_growth` | — | backend/lib/financial_ratios.py:3578, backend/lib/financial_ratios.py:3580 |
| **Retorno total** | total_return | absoluta (frente al Ke de un REIT) | `crecimiento.reit_total_return_points` = [5, 3, 1, -1, -4]; `crecimiento.reit_total_return_bounds` = [0.1, 0.07, 0.04] | fijado a mano / modelo | – | – | – | – | – | A | – | específica | 19 · 3.2 · 100% | — | _reit | backend/lib/financial_ratios.py:3566 |

### Ajustes que puntúan fuera de la cobertura

Aparecen en el desglose con un ajuste distinto de 0 pero no son un componente de la cobertura: no cuentan en el reescalado ni en «sin dato». Medidos en la muestra (empresas en las que puntúan).

| Categoría | Ajuste | Empresas |
|---|---|---:|
| Valoración | Forward P/E | 164 |
| Rentabilidad | Tope por ROIC − WACC | 42 |

## 4. Lo que cambia una lectura, el veredicto o la confianza sin ser un componente

Cada tabla de la config que el código lee, por lo que mueve, con los módulos que la leen (archivo:primera línea) y cuántas claves. Los valores están en `backend/config/`.

| Mueve | Tabla de config | Claves | La leen |
|---|---|---:|---|
| puntuación (bandas y puntos) | `thresholds.score.calidad` | 14 | display.py:859, financial_ratios.py:3198 |
| puntuación (bandas y puntos) | `thresholds.score.category` | 4 | financial_ratios.py:31, main.py:2146, persistence.py:193, verdict.py:53 |
| puntuación (bandas y puntos) | `thresholds.score.category_labels` | 1 | display.py:36 |
| puntuación (bandas y puntos) | `thresholds.score.coverage` | 3 | financial_ratios.py:32 |
| puntuación (bandas y puntos) | `thresholds.score.crecimiento` | 11 | display.py:3235, financial_ratios.py:705 |
| puntuación (bandas y puntos) | `thresholds.score.rentabilidad` | 29 | display.py:261, financial_ratios.py:822, main.py:669 |
| puntuación (bandas y puntos) | `thresholds.score.solidez` | 19 | alert_interpretations.py:38, display.py:315, display_charts.py:21, financial_ratios.py:1811 |
| puntuación (bandas y puntos) | `thresholds.score.solidez_financial` | 6 | financial_ratios.py:2116 |
| puntuación (bandas y puntos) | `thresholds.score.valoracion` | 28 | alert_interpretations.py:257, display.py:956, display_charts.py:166, financial_ratios.py:956 |
| veredicto (bandas de calidad y precio, contracción, persistencia) | `thresholds.quality_persistence` | 1 | persistence.py:192 |
| veredicto (bandas de calidad y precio, contracción, persistencia) | `thresholds.score.border_points` | 1 | verdict.py:34 |
| veredicto (bandas de calidad y precio, contracción, persistencia) | `thresholds.score.price` | 6 | display.py:1825, financial_ratios.py:3814, verdict.py:103 |
| veredicto (bandas de calidad y precio, contracción, persistencia) | `thresholds.score.quality` | 6 | display.py:1824, financial_ratios.py:3810, persistence.py:194, verdict.py:74 |
| veredicto (bandas de calidad y precio, contracción, persistencia) | `thresholds.score.total` | 1 | persistence.py:193, verdict.py:56 |
| confianza (convergencia, cobertura, fuente, fiabilidad del DCF) | `thresholds.confidence` | 15 | valuation_confidence.py:179 |
| confianza (convergencia, cobertura, fuente, fiabilidad del DCF) | `thresholds.dcf_reliability` | 13 | main.py:1841, valuation_confidence.py:101 |
| fortalezas y alertas | `thresholds.alerts` | 84 | alert_interpretations.py:37, display.py:792, display_charts.py:394 |
| lecturas del informe que no puntúan | `base_rates` | 6 | base_rates.py:24 |
| lecturas del informe que no puntúan | `market.context` | 20 | display.py:1278, market_context.py:80, price_history.py:165 |
| lecturas del informe que no puntúan | `market.signals` | 20 | market_context.py:425, market_signals.py:54 |
| lecturas del informe que no puntúan | `thresholds.pdf` | 13 | display.py:31, display_charts.py:22, financial_ratios.py:671, pdf_report.py:32, vs_reference.py:21 |
| lecturas del informe que no puntúan | `thresholds.quality_readings` | 5 | quality_readings.py:91 |
| lecturas del informe que no puntúan | `thresholds.roce` | 3 | archetype_metrics.py:602, display.py:2065 |
| tipo de empresa y excepciones | `sectors.archetypes` | 35 | classify.py:59, cyclicality.py:182, edgar_backup.py:62, edgar_primary.py:48, persistence.py:117, segments.py:657 |
| tipo de empresa y excepciones | `sectors.business_model` | 7 | business_model.py:22 |
| tipo de empresa y excepciones | `sectors.financials` | 3 | financial_ratios.py:57 |
| referencias (sector, industria, mercado) | `industries` | 7 | industry_bench.py:130, self_exclusion.py:86 |
| referencias (sector, industria, mercado) | `sectors.benchmarks` | 12 | financial_ratios.py:29, industry_bench.py:123, main.py:135 |
| referencias (sector, industria, mercado) | `sectors.score_thresholds` | 3 | financial_ratios.py:716 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `betas` | 6 | beta.py:54, industry_bench.py:228 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `betas_regional` | 1 | beta.py:55 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `country_risk` | 1 | country_risk.py:38 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `market.beta_choice` | 11 | beta.py:127, country_risk.py:186 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `thresholds.growth` | 3 | alert_interpretations.py:669, cyclicality.py:195, historical_metrics.py:141, main.py:1118 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `thresholds.normalization` | 14 | main.py:1716, normalize.py:105 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.archetypes` | 3 | archetype_metrics.py:31, display.py:890, main.py:1195 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.bank_implied` | 5 | archetype_metrics.py:137, bank_implied.py:51 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.capm` | 15 | archetype_metrics.py:52, cost_of_capital.py:54, display.py:2412, ke_sensitivity.py:31, main.py:921, market_signals.py:220 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.country_risk` | 2 | country_risk.py:46 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.dcf` | 13 | archetype_metrics.py:189, financial_ratios.py:24, main.py:1824, reverse_dcf.py:30, reverse_reading.py:55 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.earnings_peak` | 5 | earnings_peak.py:40 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.graham` | 1 | financial_ratios.py:1212 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.grid` | 4 | financial_ratios.py:25, scenario.py:203 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.models` | 18 | display.py:2717, display_charts.py:539, financial_ratios.py:26 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.pb_two_stage` | 3 | archetype_metrics.py:90 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.peg` | 1 | financial_ratios.py:976, main.py:1310 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.reverse_dcf` | 12 | main.py:2077, market_context.py:517, premortem.py:48, reverse_dcf.py:38, reverse_reading.py:54 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.scenario` | 12 | scenario.py:23 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.shareholder` | 1 | main.py:1421 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.synthetic_rating` | 9 | cost_of_capital.py:126 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.tax` | 3 | cost_of_capital.py:109, financial_ratios.py:1560, normalize.py:304 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.telecom_spectrum` | 4 | telecom_spectrum.py:22 |
| métodos (normalización, crecimiento, coste de capital, DCF, modelos) | `valuation.wacc` | 4 | cost_of_capital.py:202, financial_ratios.py:23 |

## 5. Reglas especiales

### 5.1 «No aplica» por arquetipo y por subtipo (config)

| Clave | MAD | CRE | CIC | PRE | FIN | REIT | UTI | Subtipos | La leen |
|---|---|---|---|---|---|---|---|---|---|
| `altman` |  |  |  | – | – | – | – |  | alert_interpretations.py:571, display_charts.py:534, financial_ratios.py:1816, main.py:990 (+4) |
| `current_ratio` |  |  |  |  | – | – | – |  | alert_interpretations.py:543, display.py:3318, display.py:1617, financial_ratios.py:1816 |
| `dcf` |  |  |  |  | – | – | – |  | main.py:990, main.py:1833, main.py:992 |
| `de` |  |  |  |  | – |  | – |  | display.py:1630, financial_ratios.py:2127, financial_ratios.py:1816, financial_ratios.py:3651 |
| `eps_growth` |  |  |  | – |  | – |  |  | alert_interpretations.py:719, display.py:1752, display.py:2807, display.py:3343 (+3) |
| `ev_ebitda` |  |  |  |  | – |  | – |  | alert_interpretations.py:185, financial_ratios.py:2625 |
| `fcf` |  |  |  |  | – |  | – |  | alert_interpretations.py:625, archetype_metrics.py:373, display.py:2688, display_charts.py:477 (+1) |
| `fcf_growth` |  |  | – |  | – |  | – |  | financial_ratios.py:3417 |
| `fcf_to_ni` |  |  |  |  | – | – | – |  | alert_interpretations.py:648, financial_ratios.py:3203 |
| `forward_pe` |  |  | – | – |  | – |  |  | financial_ratios.py:2625 |
| `garp` |  |  |  |  | – | – | – |  | financial_ratios.py:2625 |
| `graham` |  |  |  | – | – | – |  |  | display.py:3350, main.py:990, main.py:992, main.py:1789 |
| `gross_margin` |  |  |  |  | – | – |  |  | alert_interpretations.py:395, display_charts.py:198 |
| `interest_coverage` |  |  |  |  | – |  |  |  | alert_interpretations.py:494, display.py:1639, financial_ratios.py:1816 |
| `net_debt_ebitda` |  |  |  |  | – |  |  |  | alert_interpretations.py:428, display.py:1643 |
| `net_margin` |  |  |  | – |  | – |  | banco | alert_interpretations.py:394, display.py:1851, display_charts.py:198, financial_ratios.py:2315 (+1) |
| `ocf` |  |  |  |  | – |  |  |  | display.py:2687, financial_ratios.py:3203 |
| `operating_margin` |  |  |  |  | – | – |  |  | display_charts.py:198, financial_ratios.py:2309, main.py:1666 |
| `p_fcf` |  |  |  |  | – | – | – |  | alert_interpretations.py:212, display.py:1744, display.py:3358, financial_ratios.py:2625 |
| `pe` |  |  | – | – |  | – |  |  | alert_interpretations.py:131, display.py:1742, display.py:2113, display.py:2273 (+5) |
| `peg` |  |  | – | – | – | – | – |  | alert_interpretations.py:233, financial_ratios.py:2625 |
| `piotroski` |  |  |  |  | – | – |  |  | alert_interpretations.py:739, financial_ratios.py:3203, main.py:990, main.py:1604 (+1) |
| `roa` |  |  |  | – |  | – |  |  | financial_ratios.py:3103 |
| `roce` |  |  |  |  | – | – |  |  | archetype_metrics.py:578, main.py:990, main.py:992 |
| `roe` |  |  |  | – |  | – |  |  | alert_interpretations.py:325, display.py:1748, display.py:3314, financial_ratios.py:3103 |
| `roic_wacc` |  |  |  | – | – | – |  |  | alert_interpretations.py:367, display.py:1750, display.py:3316, display_charts.py:324 (+6) |

### 5.2 Ramas por arquetipo o subtipo en el código

| Archivo | Ramas | Arquetipos que nombra | Funciones (ramas) |
|---|---:|---|---|
| `backend/lib/display.py` | 42 | REIT 16, FIN 8, UTI 8, PRE 8, CIC 5, subtipo:banco 1 | `build_display` 33, `band_tooltips` 4, `na_keys` 2, `_metric_claims` 2, `_shown_archetype_label` 1 |
| `backend/main.py` | 36 | CIC 11, REIT 9, FIN 9, PRE 3, CRE 2, UTI 2, subtipo:banco 1 | `_compute_analysis_body` 36 |
| `backend/lib/financial_ratios.py` | 35 | REIT 12, PRE 10, FIN 7, UTI 4, CIC 2, MAD 1 | `score_solidez_financiera` 9, `score_valoracion` 9, `score_calidad_ganancias` 6, `score_crecimiento` 4, `calculate_score_v2` 4, `score_solidez_financiera_financial` 2 … |
| `backend/lib/alert_interpretations.py` | 11 | REIT 3, PRE 3, CIC 2, UTI 2, FIN 1 | `_leverage` 2, `_growth` 2, `_fcf` 2, `_ev_ebitda` 1, `_coverage` 1, `__init__` 1 … |
| `backend/lib/archetype_metrics.py` | 11 | CIC 3, FIN 2, PRE 2, subtipo:banco 1, REIT 1, UTI 1, subtipo:aseguradora 1, subtipo:conglomerado 1 | `compute` 5, `growth_values` 2, `_implied_reading` 1, `roce` 1, `_financial` 1, `yearly_financials` 1 |
| `backend/lib/display_charts.py` | 10 | FIN 3, REIT 3, PRE 2, UTI 1, CIC 1 | `build_charts` 8, `comparison` 2 |
| `backend/lib/classify.py` | 4 | CIC 2, FIN 1, subtipo:conglomerado 1 | `out` 2, `not_applicable` 1, `classify` 1 |
| `backend/lib/premortem.py` | 4 | UTI 2, FIN 2, REIT 1 | `_debt_item` 3, `_margin_item` 1 |
| `backend/lib/valuation_confidence.py` | 2 | CIC 2 | `dcf_reliability` 1, `stability_dimension` 1 |
| `backend/lib/market_context.py` | 1 | CIC 1, PRE 1 | `behavioral` 1 |
| `backend/lib/persistence.py` | 1 | FIN 1 | `measure` 1 |
| `backend/lib/validate.py` | 1 | FIN 1 | `_rule_growth` 1 |

<details><summary>Todas las ramas (archivo:línea, función, condición)</summary>

- `backend/lib/alert_interpretations.py:182` · `_ev_ebitda` · `ctx.archetype == CYCLICAL`
- `backend/lib/alert_interpretations.py:446` · `_leverage` · `ctx.archetype == REIT`
- `backend/lib/alert_interpretations.py:462` · `_leverage` · `ctx.archetype == UTILITY`
- `backend/lib/alert_interpretations.py:514` · `_coverage` · `ctx.archetype == UTILITY`
- `backend/lib/alert_interpretations.py:678` · `_growth` · `ctx.archetype == REIT`
- `backend/lib/alert_interpretations.py:79` · `__init__` · `self.archetype == FINANCIAL`
- `backend/lib/alert_interpretations.py:592` · `_runway` · `ctx.archetype == GROWTH_PRE_PROFIT`
- `backend/lib/alert_interpretations.py:636` · `_fcf` · `ctx.archetype == GROWTH_PRE_PROFIT`
- `backend/lib/alert_interpretations.py:676` · `_growth` · `ctx.archetype == CYCLICAL`
- `backend/lib/alert_interpretations.py:631` · `_fcf` · `ctx.archetype == GROWTH_PRE_PROFIT`
- `backend/lib/alert_interpretations.py:845` · `_signal_claims` · `ctx.archetype == REIT`
- `backend/lib/archetype_metrics.py:275` · `_implied_reading` · `subtype == 'banco'`
- `backend/lib/archetype_metrics.py:511` · `growth_values` · `archetype == CYCLICAL`
- `backend/lib/archetype_metrics.py:521` · `growth_values` · `archetype == FINANCIAL`
- `backend/lib/archetype_metrics.py:537` · `compute` · `archetype == FINANCIAL`
- `backend/lib/archetype_metrics.py:540` · `compute` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/archetype_metrics.py:542` · `compute` · `archetype == REIT`
- `backend/lib/archetype_metrics.py:544` · `compute` · `archetype == CYCLICAL`
- `backend/lib/archetype_metrics.py:546` · `compute` · `archetype == 'UTILITY'`
- `backend/lib/archetype_metrics.py:596` · `roce` · `archetype == CYCLICAL`
- `backend/lib/archetype_metrics.py:198` · `_financial` · `subtype in ('aseguradora', 'conglomerado')`
- `backend/lib/archetype_metrics.py:380` · `yearly_financials` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/classify.py:182` · `not_applicable` · `archetype == FINANCIAL`
- `backend/lib/classify.py:432` · `classify` · `ins['subtype'] == 'conglomerado'`
- `backend/lib/classify.py:399` · `out` · `arch != CYCLICAL`
- `backend/lib/classify.py:411` · `out` · `arch != CYCLICAL`
- `backend/lib/display.py:1171` · `na_keys` · `archetype == 'FINANCIAL'`
- `backend/lib/display.py:1513` · `build_display` · `archetype == 'FINANCIAL'`
- `backend/lib/display.py:1647` · `build_display` · `archetype == 'CYCLICAL'`
- `backend/lib/display.py:1675` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:1848` · `build_display` · `archetype == 'FINANCIAL'`
- `backend/lib/display.py:1998` · `build_display` · `archetype == 'FINANCIAL'`
- `backend/lib/display.py:3047` · `build_display` · `archetype == 'FINANCIAL'`
- `backend/lib/display.py:3283` · `band_tooltips` · `archetype == 'REIT'`
- `backend/lib/display.py:3284` · `band_tooltips` · `archetype == 'UTILITY'`
- `backend/lib/display.py:3337` · `band_tooltips` · `archetype == 'GROWTH_PRE_PROFIT'`
- `backend/lib/display.py:1173` · `na_keys` · `archetype == 'GROWTH_PRE_PROFIT'`
- `backend/lib/display.py:1619` · `build_display` · `archetype == 'GROWTH_PRE_PROFIT'`
- `backend/lib/display.py:1626` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:1855` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:2002` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:2119` · `build_display` · `archetype == 'FINANCIAL'`
- `backend/lib/display.py:2255` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:2605` · `build_display` · `archetype in ('REIT', 'GROWTH_PRE_PROFIT')`
- `backend/lib/display.py:2655` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:2724` · `build_display` · `archetype in ('REIT', 'UTILITY')`
- `backend/lib/display.py:2847` · `build_display` · `classification.get('subtype') == 'banco'`
- `backend/lib/display.py:3049` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:1343` · `_shown_archetype_label` · `archetype == 'FINANCIAL'`
- `backend/lib/display.py:1783` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:1860` · `build_display` · `archetype == 'UTILITY'`
- `backend/lib/display.py:2006` · `build_display` · `archetype == 'UTILITY'`
- `backend/lib/display.py:2026` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:2648` · `build_display` · `archetype in ('REIT', 'GROWTH_PRE_PROFIT')`
- `backend/lib/display.py:2810` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:3051` · `build_display` · `archetype == 'UTILITY'`
- `backend/lib/display.py:3316` · `band_tooltips` · `archetype == 'FINANCIAL'`
- `backend/lib/display.py:1640` · `build_display` · `archetype == 'UTILITY'`
- `backend/lib/display.py:1644` · `build_display` · `archetype == 'REIT'`
- `backend/lib/display.py:1645` · `build_display` · `archetype == 'UTILITY'`
- `backend/lib/display.py:1865` · `build_display` · `archetype == 'GROWTH_PRE_PROFIT'`
- `backend/lib/display.py:2010` · `build_display` · `archetype == 'GROWTH_PRE_PROFIT'`
- `backend/lib/display.py:2728` · `build_display` · `archetype == 'GROWTH_PRE_PROFIT'`
- `backend/lib/display.py:109` · `_metric_claims` · `arch == 'CYCLICAL'`
- `backend/lib/display.py:109` · `_metric_claims` · `arch != 'CYCLICAL'`
- `backend/lib/display.py:1872` · `build_display` · `archetype == 'CYCLICAL'`
- `backend/lib/display.py:2014` · `build_display` · `archetype == 'CYCLICAL'`
- `backend/lib/display.py:2046` · `build_display` · `archetype in ('REIT', 'UTILITY')`
- `backend/lib/display_charts.py:416` · `build_charts` · `archetype == 'GROWTH_PRE_PROFIT'`
- `backend/lib/display_charts.py:472` · `build_charts` · `archetype == 'FINANCIAL'`
- `backend/lib/display_charts.py:374` · `build_charts` · `archetype == 'UTILITY'`
- `backend/lib/display_charts.py:374` · `build_charts` · `archetype == 'REIT'`
- `backend/lib/display_charts.py:414` · `build_charts` · `archetype == 'GROWTH_PRE_PROFIT'`
- `backend/lib/display_charts.py:446` · `build_charts` · `archetype == 'REIT'`
- `backend/lib/display_charts.py:590` · `comparison` · `D.get('archetype') == 'CYCLICAL'`
- `backend/lib/display_charts.py:302` · `build_charts` · `D.get('archetype') == 'FINANCIAL'`
- `backend/lib/display_charts.py:586` · `comparison` · `D.get('archetype') != 'REIT'`
- `backend/lib/display_charts.py:352` · `build_charts` · `archetype == 'FINANCIAL'`
- `backend/lib/financial_ratios.py:1997` · `score_solidez_financiera` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/financial_ratios.py:2034` · `score_solidez_financiera` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/financial_ratios.py:2042` · `score_solidez_financiera` · `archetype in (REIT, UTILITY)`
- `backend/lib/financial_ratios.py:2130` · `score_solidez_financiera_financial` · `archetype == FINANCIAL`
- `backend/lib/financial_ratios.py:2241` · `score_solidez_financiera_financial` · `archetype != FINANCIAL`
- `backend/lib/financial_ratios.py:2630` · `score_valoracion` · `archetype == CYCLICAL`
- `backend/lib/financial_ratios.py:2672` · `score_valoracion` · `archetype == FINANCIAL`
- `backend/lib/financial_ratios.py:2714` · `score_valoracion` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/financial_ratios.py:2739` · `score_valoracion` · `archetype == UTILITY`
- `backend/lib/financial_ratios.py:3008` · `score_valoracion` · `archetype == FINANCIAL`
- `backend/lib/financial_ratios.py:3015` · `score_valoracion` · `archetype == UTILITY`
- `backend/lib/financial_ratios.py:3018` · `score_valoracion` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/financial_ratios.py:3224` · `score_calidad_ganancias` · `archetype == FINANCIAL`
- `backend/lib/financial_ratios.py:3246` · `score_calidad_ganancias` · `archetype == REIT`
- `backend/lib/financial_ratios.py:3299` · `score_calidad_ganancias` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/financial_ratios.py:3346` · `score_calidad_ganancias` · `archetype == FINANCIAL`
- `backend/lib/financial_ratios.py:3355` · `score_calidad_ganancias` · `archetype == REIT`
- `backend/lib/financial_ratios.py:3425` · `score_crecimiento` · `archetype == REIT`
- `backend/lib/financial_ratios.py:3635` · `calculate_score_v2` · `archetype == FINANCIAL`
- `backend/lib/financial_ratios.py:3695` · `calculate_score_v2` · `archetype == REIT`
- `backend/lib/financial_ratios.py:1888` · `score_solidez_financiera` · `archetype == REIT`
- `backend/lib/financial_ratios.py:2063` · `score_solidez_financiera` · `archetype != REIT`
- `backend/lib/financial_ratios.py:2624` · `score_valoracion` · `archetype == REIT`
- `backend/lib/financial_ratios.py:2626` · `score_valoracion` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/financial_ratios.py:3428` · `score_crecimiento` · `archetype == MATURE`
- `backend/lib/financial_ratios.py:3697` · `calculate_score_v2` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/financial_ratios.py:2043` · `score_solidez_financiera` · `archetype == REIT`
- `backend/lib/financial_ratios.py:2045` · `score_solidez_financiera` · `archetype == REIT`
- `backend/lib/financial_ratios.py:3360` · `score_calidad_ganancias` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/financial_ratios.py:3749` · `calculate_score_v2` · `archetype == REIT`
- `backend/lib/financial_ratios.py:690` · `growth_metric` · `archetype == CYCLICAL`
- `backend/lib/financial_ratios.py:1980` · `score_solidez_financiera` · `archetype == UTILITY`
- `backend/lib/financial_ratios.py:3545` · `score_crecimiento` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/financial_ratios.py:2055` · `score_solidez_financiera` · `archetype == REIT`
- `backend/lib/financial_ratios.py:3555` · `score_crecimiento` · `archetype == GROWTH_PRE_PROFIT`
- `backend/lib/market_context.py:504` · `behavioral` · `arch not in ('CYCLICAL', 'GROWTH_PRE_PROFIT')`
- `backend/lib/persistence.py:96` · `measure` · `archetype == FINANCIAL`
- `backend/lib/premortem.py:113` · `_debt_item` · `arch in ('UTILITY', 'REIT')`
- `backend/lib/premortem.py:99` · `_margin_item` · `arch == 'FINANCIAL'`
- `backend/lib/premortem.py:111` · `_debt_item` · `arch == 'FINANCIAL'`
- `backend/lib/premortem.py:114` · `_debt_item` · `arch == 'UTILITY'`
- `backend/lib/validate.py:265` · `_rule_growth` · `arch == FINANCIAL`
- `backend/lib/valuation_confidence.py:157` · `dcf_reliability` · `archetype == 'CYCLICAL'`
- `backend/lib/valuation_confidence.py:318` · `stability_dimension` · `archetype == 'CYCLICAL'`
- `backend/main.py:864` · `_compute_analysis_body` · `archetype == REIT`
- `backend/main.py:983` · `_compute_analysis_body` · `archetype == REIT`
- `backend/main.py:1236` · `_compute_analysis_body` · `archetype == REIT`
- `backend/main.py:1266` · `_compute_analysis_body` · `archetype == GROWTH_PRE_PROFIT`
- `backend/main.py:1293` · `_compute_analysis_body` · `archetype == 'GROWTH_PROFITABLE'`
- `backend/main.py:1370` · `_compute_analysis_body` · `archetype == FINANCIAL`
- `backend/main.py:906` · `_compute_analysis_body` · `archetype == FINANCIAL`
- `backend/main.py:919` · `_compute_analysis_body` · `archetype == FINANCIAL`
- `backend/main.py:937` · `_compute_analysis_body` · `archetype not in (FINANCIAL, REIT)`
- `backend/main.py:941` · `_compute_analysis_body` · `archetype != FINANCIAL`
- `backend/main.py:1014` · `_compute_analysis_body` · `archetype == FINANCIAL`
- `backend/main.py:1075` · `_compute_analysis_body` · `archetype == FINANCIAL`
- `backend/main.py:1075` · `_compute_analysis_body` · `classification.get('subtype') == 'banco'`
- `backend/main.py:1168` · `_compute_analysis_body` · `archetype == CYCLICAL`
- `backend/main.py:1172` · `_compute_analysis_body` · `archetype == CYCLICAL`
- `backend/main.py:1187` · `_compute_analysis_body` · `archetype == CYCLICAL`
- `backend/main.py:1284` · `_compute_analysis_body` · `archetype == REIT`
- `backend/main.py:1339` · `_compute_analysis_body` · `archetype == 'GROWTH_PROFITABLE'`
- `backend/main.py:1845` · `_compute_analysis_body` · `archetype == CYCLICAL`
- `backend/main.py:2025` · `_compute_analysis_body` · `archetype == FINANCIAL`
- `backend/main.py:2246` · `_compute_analysis_body` · `_arch == 'UTILITY'`
- `backend/main.py:1213` · `_compute_analysis_body` · `archetype == REIT`
- `backend/main.py:1285` · `_compute_analysis_body` · `archetype == CYCLICAL`
- `backend/main.py:1810` · `_compute_analysis_body` · `archetype == CYCLICAL`
- `backend/main.py:1814` · `_compute_analysis_body` · `archetype != CYCLICAL`
- `backend/main.py:1822` · `_compute_analysis_body` · `archetype != CYCLICAL`
- `backend/main.py:1834` · `_compute_analysis_body` · `archetype == GROWTH_PRE_PROFIT`
- `backend/main.py:1942` · `_compute_analysis_body` · `archetype == CYCLICAL`
- `backend/main.py:2027` · `_compute_analysis_body` · `archetype == REIT`
- `backend/main.py:2075` · `_compute_analysis_body` · `archetype == 'UTILITY'`
- `backend/main.py:2257` · `_compute_analysis_body` · `_arch == FINANCIAL`
- `backend/main.py:2058` · `_compute_analysis_body` · `archetype == CYCLICAL`
- `backend/main.py:2086` · `_compute_analysis_body` · `archetype == REIT`
- `backend/main.py:945` · `_compute_analysis_body` · `archetype == REIT`
- `backend/main.py:2041` · `_compute_analysis_body` · `archetype != GROWTH_PRE_PROFIT`
- `backend/main.py:2037` · `_compute_analysis_body` · `archetype == CYCLICAL`

</details>

### 5.3 Ajustes de umbral por sector

| Sector | `current_ratio_low` | `debt_equity_high` | `fcf_yield_high` | `fcf_yield_low` | `net_margin_low` | `operating_margin_low` | `p_fcf_high` | `pe_overvalued_mult` | `roa_high` | `roa_low` | `roe_high` | `roe_low` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| technology |  | 0.8 |  |  | 0.1 | 0.15 | 35 | 1.4 | 0.15 |  | 0.22 | 0.1 |
| utilities |  | 1.5 |  |  | 0.08 | 0.12 | 18 | 1.2 | 0.035 | 0.015 | 0.1 | 0.05 |
| financials |  | 10 |  |  | 0.15 | 0.2 |  | 1.25 | 0.012 | 0.008 | 0.12 | 0.06 |
| healthcare |  |  |  |  | 0.08 | 0.12 | 30 | 1.35 |  |  | 0.18 | 0.08 |
| consumer_cyclical | 1.2 |  |  |  | 0.04 | 0.06 |  | 1.3 |  |  | 0.18 | 0.08 |
| consumer_defensive |  | 1.2 |  |  | 0.06 | 0.1 |  | 1.25 |  |  | 0.2 | 0.1 |
| energy |  | 0.5 | 0.1 | 0.05 | 0.05 | 0.08 | 12 | 1.2 | 0.06 |  | 0.12 | 0.05 |
| real_estate |  | 2 |  |  | 0.15 | 0.25 |  | 1.3 | 0.03 | 0.01 | 0.08 | 0.03 |
| industrials |  | 0.8 |  |  | 0.05 | 0.08 |  | 1.3 |  |  | 0.15 | 0.08 |
| materials |  | 0.6 |  |  | 0.06 | 0.1 |  | 1.25 | 0.06 |  | 0.12 | 0.05 |
| communication |  | 1 |  |  | 0.1 | 0.15 |  | 1.35 |  |  | 0.15 | 0.08 |
| market |  |  |  |  |  |  |  |  |  |  |  |  |

Los umbrales por defecto (`sectors.score_thresholds.default`) y las medianas por sector (`sectors.benchmarks.sectors`, 11 sectores) son PROVISIONALES («fijados a mano en versiones anteriores», cabecera de `sectors.toml`). La referencia de industria de Damodaran (`config/industries.toml`) ya los sustituye en los márgenes y en P/E y EV/EBITDA; el ROE, el ROA y el D/E siguen con los del sector.

### 5.4 Listas de industrias y excepciones

| Lista | Qué hace | Entradas | La leen |
|---|---|---:|---|
| `sectors.archetypes.cyclical_industries` | industrias cíclicas siempre | 27 | classify.py:526, classify.py:529 |
| `sectors.archetypes.cyclical_conditional_industries` | cíclicas condicionales (si hay reversión) | 2 | classify.py:526 |
| `sectors.archetypes.utility_industries` | utilities reguladas | 4 | classify.py:478 |
| `sectors.archetypes.financial_mature_industries` | financieras que son MATURE | 3 | classify.py:444 |
| `sectors.archetypes.payment_network_industries` | redes de pago (MATURE si activos/ingresos ≤ 3) | 1 | classify.py:449 |
| `sectors.business_model.negative_working_capital_industries` | circulante negativo estructural: el current ratio no puntúa | 15 | business_model.py:22 |
| `sectors.business_model.altman_referential_industries` | Altman referencial (no vota) | 9 | business_model.py:43 |
| `sectors.business_model.captive_finance_segment_patterns` | financiera cautiva por segmentos: Altman referencial | 2 | business_model.py:76 |
| `sectors.financials.sector_names` | sectores tratados como financieros | 10 | financial_ratios.py:57 |

### 5.5 No significativo, referencial e informativo

Componentes que pueden salir **no significativos** (no cuentan en la cobertura, tienen su línea en el desglose): **Altman Z** (Solidez Financiera), **Cobertura de intereses** (Solidez Financiera), **Current ratio** (Solidez Financiera), **ROIC−WACC** (Rentabilidad), **DCF** (Valoración), **PEG** (Valoración), **Estabilidad del ROE** (Calidad de Ganancias), **Crecimiento del BPA** (Crecimiento), **Crecimiento del FCF** (Crecimiento).

Además, en `score_solidez_financiera`: el Altman **referencial** (industrias de §5.4 y financiera cautiva) y el D/E **informativo** (REIT, o caja neta); el ROE se sustituye por el ROIC con apalancamiento alto (D/E > umbral del sector); el **tope por ROIC − WACC** (`thresholds.score.rentabilidad.spread_caps`) limita la Rentabilidad.

## 6. Candidatas a simplificar

### 6.1 Variables que votan lo mismo (medido)

Pares de componentes cuyos ajustes se mueven juntos en la muestra (correlación de Pearson de los ajustes, |r| ≥ 0,6, al menos 12 empresas con los dos). «Mismo signo»: empresas en que los dos suman, restan o son 0 a la vez.

| Componente A | Componente B | r | Empresas | Mismo signo |
|---|---|---:|---:|---:|
| Valoración · P/B frente a ROE | Valoración · P/TBV frente a ROTE | 0.82 | 52 | 83% |
| Rentabilidad · ROE | Rentabilidad · ROIC−WACC | 0.81 | 407 | 83% |
| Valoración · DCF inverso | Crecimiento · Retorno total | 0.81 | 19 | 53% |
| Valoración · EV/EBITDA | Valoración · P/FFO | 0.77 | 20 | 50% |
| Valoración · DCF inverso | Valoración · P/FFO | 0.75 | 20 | 70% |
| Rentabilidad · Margen operativo | Rentabilidad · Margen neto | 0.74 | 462 | 60% |
| Crecimiento · Crecimiento del BPA | Valoración · PEG | 0.72 | 68 | 46% |
| Rentabilidad · Margen operativo | Solidez Financiera · Deuda neta/EBITDA | 0.70 | 28 | 50% |
| Rentabilidad · ROE | Rentabilidad · ROA | 0.68 | 479 | 41% |
| Solidez Financiera · Cobertura de intereses | Rentabilidad · ROE | 0.67 | 425 | 77% |
| Solidez Financiera · Cobertura de intereses | Rentabilidad · ROIC−WACC | 0.63 | 435 | 69% |
| Rentabilidad · ROE | Solidez Financiera · Salud bancaria | 0.62 | 52 | 98% |
| Valoración · P/E | Valoración · EV/EBITDA | 0.61 | 352 | 62% |

### 6.2 Duplicadas en la config

Misma hoja y mismo valor en tablas distintas (una sola fuente por concepto evitaría que diverjan):

- `negative_equity_min_roa` = 0.03: `thresholds.score.rentabilidad.negative_equity_min_roa`, `thresholds.alerts.roe.negative_equity_min_roa`
- `neutral` = 50: `thresholds.score.quality.neutral`, `thresholds.score.price.neutral`
- `strong_above` = 0.15: `thresholds.alerts.growth.strong_above`, `thresholds.alerts.eps_growth.strong_above`

Mismos puntos con nombres distintos (la misma escala repetida por arquetipo):

- [4, 2, 0, -2, -4]: `solidez.current_points`, `solidez.reit_nde_points`, `solidez.utility_nde_points`, `rentabilidad.roa_points`, `rentabilidad.gpp_opm_change_points`, `valoracion.reit_pffo_points`, `valoracion.utility_yield_points`, `valoracion.pfcf_value_points`, `valoracion.ev_ebitda_value_points`, `valoracion.financial_pb_points`, `valoracion.ev_sales_points`, `valoracion.rule_of_40_points`
- [5, 3, 0, -3, -5]: `rentabilidad.reit_ffo_margin_points`, `rentabilidad.gpp_gross_margin_points`, `rentabilidad.gpp_operating_margin_points`, `rentabilidad.gpp_fcf_margin_points`
- [3, 1, -1, -3]: `calidad.financial_roe_std_points`, `calidad.financial_efficiency_points`, `calidad.financial_bv_growth_points`, `calidad.reit_ffo_payout_points`
- [5, 3, 1, -1, -4]: `crecimiento.revenue_points`, `crecimiento.eps_points`, `crecimiento.reit_total_return_points`
- [3, 1, 0, -2, -3]: `solidez.coverage_points`, `solidez.utility_coverage_points`
- [3, -4]: `calidad.ocf_points`, `calidad.fcf_points`

### 6.3 Propuestas de simplificación, por impacto (*juicio*, con la evidencia de §3, §6.1 y del escaneo)

- **1 · Una sola referencia por métrica: la industria de Damodaran (sin la propia empresa) en el score, en la fila y en la alerta.** Hoy el ROE y el ROA —el ROE es la variable que más pesa del modelo: ±3,7 de media en 479 empresas— y el D/E se leen contra tablas por sector escritas a mano (PROVISIONALES), las filas contra Damodaran y las alertas contra el sector o contra umbrales absolutos (P/E > 35x, EV/EBITDA > 25x): de ahí las fortalezas y alertas con el tono contrario a su fila del escaneo. Quita `sectors.score_thresholds` (12 sectores, 80 ajustes). La parte «sin la propia empresa» es la N2 de F10.
- **2 · Rentabilidad: de 5 votos (ROE, ROA, margen operativo, margen neto, ROIC − WACC) a 2.** ROIC − WACC (ROE − Ke en banco y aseguradora, el mismo que alimenta su P/B justificado) y un margen frente a la industria. Medido: ROE y ROIC − WACC r = 0,81 (407 empresas), margen operativo y neto 0,76 (462), ROE y ROA 0,67 (479). El ROE ya se cambia por el ROIC con apalancamiento alto y el tope por ROIC − WACC (44 empresas) ya manda.
- **3 · Calidad de ganancias: OCF > 0 y FCF > 0 (dos signos que suman +3 y +3 casi siempre) → FCF / beneficio.** Los dos signos mueven 1.476 y 1.404 puntos en el universo, casi todo en la misma dirección; el cociente FCF / beneficio (o FCF / ingresos sin beneficio, y dividendo / FFO en el REIT, que es el mismo cociente) ya lleva esa información y separa a las empresas.
- **4 · Múltiplos de beneficio: P/E, Forward P/E y PEG → un voto (F10 · N4).** El Forward P/E puntúa como bono FUERA de la cobertura en 174 empresas; el PEG y el crecimiento del BPA, r = 0,73. El P/FFO del REIT y el EV/Ventas del pre-beneficio son el mismo «precio frente a su beneficio del tipo»: un miembro de beneficio por tipo dentro del bloque.
- **5 · Denominador ≤ 0 ⇒ «no significativo» con motivo, en un solo sitio (`CategoryCoverage`).** El 59 % de los 289 vacíos sin motivo del escaneo son ROE y D/E con patrimonio negativo, P/E, P/FCF y EV/EBITDA con beneficio, FCF o EBITDA negativos: hoy cuentan como «sin dato» sin decir por qué y restan cobertura. Una regla general sustituye a las excepciones de cada métrica (ROE con ROA > 3 %, D/E negativo, cobertura con EBIT < 0).
- **6 · Una serie anual única (EDGAR) para la historia de 10 años, el gráfico histórico y el crecimiento.** Las 11 cifras dobles del escaneo son de la historia de 10 años frente al gráfico (o dentro de ella): beneficio atribuido frente a disponible para el accionista común (EIX, IVZ, TKO), un concepto de ingresos parcial (NTAP, −10 %) y ejercicios de transición duplicados (LHX, KDP). Es la M5 de la hoja de ruta, aplicada a todos los bloques.
- **7 · Apalancamiento y cobertura: D/E + deuda neta/EBITDA (bandas de REIT y de utility) + cobertura (bandas de utility) → deuda neta/EBITDA y cobertura frente a su industria.** Quita cuatro juegos de bandas absolutas por tipo (`reit_nde_*`, `utility_nde_*`, `utility_coverage_*`) y la excepción «D/E informativo en REIT»; D/E y cobertura votan juntos (r = 0,80 en la muestra de los fixtures).
- **8 · Tipos: MATURE + GROWTH_PROFITABLE + CYCLICAL → empresa general; FINANCIAL → banco y aseguradora.** GROWTH_PROFITABLE no tiene ninguna herramienta propia; CYCLICAL cambia el método (ciclo medio, normalizados), que puede ser una propiedad medida de cualquier empresa. Quita además las dos variables muertas de la solidez bancaria («D/E bancario» y «P/B», que la lista «no aplica» de FINANCIAL apaga siempre) y deja al pre-beneficio (1 empresa en el universo) como el único tipo sin beneficio.
- **9 · Crecimiento: el método robusto de los ingresos para toda serie (BPA, FCF, FFO por acción) y el retorno total (dividendo + crecimiento por acción) para todos.** La parte del BPA y del PEG es la N3 de F10; generalizarla quita la excepción de MATURE con dividendo ≥ 4 % y el retorno total solo para REIT.

## 7. Cómo se regenera

```bash
cd backend && ../../finanzer_next/.venv313/bin/python tools/model_inventory.py            # muestra: fixtures
cd backend && ../../finanzer_next/.venv313/bin/python tools/model_inventory.py --scan ../docs/modelo/ESCANEO_<fecha>.json
```

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
