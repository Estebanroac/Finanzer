# Escaneo del universo con las reglas de cordura (2026-10-29)

> Generado por `backend/tools/universe_scan.py` (commit `5a402820`, rama `rediseno/v4-f8`). No editar a mano: se rehace con `--report-only` desde la caché. Las reglas MIDEN: ninguna puntuación cambió.

## Corrida

- Universo: 543 empresas (`config/universe.tsv`, S&P 500 + ADR); analizadas 543; con análisis 543. Estados: ok 543.
- Análisis real en el proceso (`main._compute_analysis`), sin precalentado ni rivales; PDF nuevo generado en 543 empresas.
- Con EDGAR (fuente oficial registrada): 98%.
- Tiempo mediano por empresa: 2.41 s; duración total: 31.2 min; memoria máxima del proceso 353 MB.
- Límites (compartidos con las demás sesiones): EDGAR ≤ 5 peticiones/s (2832 peticiones), Finnhub ≤ 30/min (83 llamadas; 1659 saltadas: /company-news, /stock/earnings, /calendar/earnings, que las reglas no usan); 1 análisis a la vez, lotes de 20.

- `peso_en_referencia` mide el peso con la capitalización de las empresas del UNIVERSO en esa industria de Damodaran (el agregado de Damodaran tiene más empresas): es una cota superior del peso real.

## Violaciones por regla

Base del escaneo: `rediseno/v4-f8` en `5a402820`. La columna F10 dice qué ronda de F10 corrige cada regla; las violaciones que quedan son lo pendiente del modelo general.

| Regla | Comprobación | Violación | OK | No aplica | No evaluable | % de las evaluadas | F10 | Ejemplos (más graves) |
|---|---|---:|---:|---:|---:|---:|---|---|
| `margen_operativo_unico` | Margen operativo: el enseñado (EDGAR TTM) frente a las piezas de la normalización (Yahoo trimestral) ± 3 pp | 46 | 407 | 80 | 10 | 10% | — | APD, DEO, ECHO, FANG, GILD, GIS, KHC, SKYD |
| `beta_en_rango` | Beta en rango o sustituida | 9 | 534 | 0 | 0 | 2% | — | BTI, SRE, XOM, CVX, VLO, PSX, MPC, CEG |
| `margen_neto_techo` | Margen neto ≤ (operativo + financiero neto) × (1 − t) + tolerancia | 0 | 462 | 81 | 0 | 0% | N1: beneficio no operativo fuera del normalizado |  |
| `ke_sobre_kd` | Ke ≥ Kd + 1 pp | 0 | 471 | 72 | 0 | 0% | — |  |
| `g_terminal_bajo_rf` | g terminal ≤ Rf | 0 | 392 | 151 | 0 | 0% | — |  |
| `capitalizacion` | Capitalización = precio × acciones ± 2 % | 0 | 542 | 0 | 1 | 0% | — |  |
| `roe_patrimonio_negativo` | ROE n.s. si el patrimonio ≤ 0 | 0 | 33 | 509 | 1 | 0% | — |  |
| `peg_crecimiento_no_positivo` | PEG n.s. si el crecimiento del BPA ≤ 0 | 0 | 0 | 468 | 75 | — | — |  |
| `cifra_unica` | Una sola cifra por métrica en display y PDF | 0 | 543 | 0 | 0 | 0% | — |  |
| `peso_en_referencia` | La empresa no pesa más de X % en su referencia de industria | 0 | 494 | 49 | 0 | 0% | N2: la referencia sin la empresa (o mediana de pares) |  |
| `crecimiento_robusto` | El crecimiento puntuado no es un CAGR desde un año anómalo | 0 | 543 | 0 | 0 | 0% | N3: BPA con el método robusto y PEG n.s. con base anómala |  |
| `alertas_coherentes` | Ninguna fortaleza o alerta contradice una cifra mostrada | 0 | 543 | 0 | 0 | 0% | — |  |
| `beta_unica` | Una misma beta en todas las capas | 0 | 543 | 0 | 0 | 0% | — |  |
| `estados_al_dia` | Estados no desfasados sin marca | 0 | 543 | 0 | 0 | 0% | — |  |
| `confianza_cobertura` | Confianza ≤ cobertura | 0 | 543 | 0 | 0 | 0% | — |  |
| `motivo_de_vacio` | Cada «no aplica» o «sin dato» lleva su motivo | 0 | 543 | 0 | 0 | 0% | — |  |

## Violaciones por arquetipo

Empresas con al menos una violación de cada regla, sobre las empresas del arquetipo (n).

| Arquetipo | n | `margen_operativo_unico` | `beta_en_rango` |
|---|---:|---:|---:|
| CYCLICAL | 60 | 8 | 5 |
| FINANCIAL · aseguradora | 16 |  | 1 |
| FINANCIAL · banco | 26 |  |  |
| FINANCIAL · conglomerado | 1 |  |  |
| FINANCIAL · financiera | 9 |  |  |
| GROWTH_PRE_PROFIT | 1 |  |  |
| GROWTH_PROFITABLE | 41 | 3 |  |
| MATURE | 333 | 33 | 2 |
| REIT | 28 |  |  |
| UTILITY | 28 | 2 | 1 |

## Las 20 más graves

Severidad = peso de la regla (config/invariants.toml) × magnitud (cuánto se pasa del umbral, acotada). Una por empresa y regla.

| # | Empresa | Arquetipo | Regla | Severidad | Qué | Causa probable |
|---:|---|---|---|---:|---|---|
| 1 | APD (Air Products and Chemicals) | MATURE | `margen_operativo_unico` | 15.0 | margen operativo enseñado −4.7% (EDGAR, TTM) frente a 24.8% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (29.6 pp > 3 pp); puntúa en Rentabilidad (-5) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 2 | DEO (Diageo plc) | MATURE | `margen_operativo_unico` | 15.0 | margen operativo enseñado 27.0% (Yahoo, quoteSummary) frente a 11.4% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (15.7 pp > 3 pp); puntúa en Rentabilidad (+3) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 3 | ECHO (EchoStar Corporation) | MATURE | `margen_operativo_unico` | 15.0 | margen operativo enseñado −112.7% (EDGAR, TTM) frente a 7.1% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (119.9 pp > 3 pp); puntúa en Rentabilidad (-5) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 4 | FANG (Diamondback Energy Inc.) | CYCLICAL | `margen_operativo_unico` | 15.0 | margen operativo enseñado 6.4% (EDGAR, TTM) frente a 35.7% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (29.3 pp > 3 pp); puntúa en Rentabilidad (-3) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 5 | GILD (Gilead Sciences Inc.) | MATURE | `margen_operativo_unico` | 15.0 | margen operativo enseñado −8.2% (EDGAR, TTM) frente a 38.5% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (46.7 pp > 3 pp); puntúa en Rentabilidad (-5) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 6 | GIS (General Mills Inc.) | MATURE | `margen_operativo_unico` | 15.0 | margen operativo enseñado −1.1% (EDGAR, TTM) frente a 15.2% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (16.3 pp > 3 pp); puntúa en Rentabilidad (-5) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 7 | KHC (The Kraft Heinz Company) | MATURE | `margen_operativo_unico` | 15.0 | margen operativo enseñado −12.8% (EDGAR, TTM) frente a 17.0% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (29.7 pp > 3 pp); puntúa en Rentabilidad (-5) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 8 | SKYD (Skydance Corporation) | MATURE | `margen_operativo_unico` | 15.0 | margen operativo enseñado 9.3% (Yahoo, quoteSummary) frente a −18.0% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (27.4 pp > 3 pp); puntúa en Rentabilidad (+1) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 9 | SOLV (Solventum Corporation) | MATURE | `margen_operativo_unico` | 15.0 | margen operativo enseñado 25.0% (EDGAR, TTM) frente a 6.3% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (18.7 pp > 3 pp); puntúa en Rentabilidad (+3) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 10 | CRL (Charles River Laboratories International, Inc.) | MATURE | `margen_operativo_unico` | 14.5 | margen operativo enseñado 15.1% (Yahoo, quoteSummary) frente a 0.6% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (14.5 pp > 3 pp); puntúa en Rentabilidad (+1) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 11 | FDXF (FedEx Freight Holding Company, Inc.) | MATURE | `margen_operativo_unico` | 11.9 | margen operativo enseñado −5.8% (Yahoo, quoteSummary) frente a 6.1% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (11.9 pp > 3 pp); puntúa en Rentabilidad (-5) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 12 | HON (Honeywell International) | CYCLICAL | `margen_operativo_unico` | 11.7 | margen operativo enseñado 27.9% (EDGAR, TTM) frente a 16.2% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (11.7 pp > 3 pp); puntúa en Rentabilidad (+1) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 13 | IFF (International Flavors) | MATURE | `margen_operativo_unico` | 10.9 | margen operativo enseñado −2.9% (EDGAR, TTM) frente a 8.0% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (10.9 pp > 3 pp); puntúa en Rentabilidad (-5) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 14 | SJM (The J.M. Smucker Company) | MATURE | `margen_operativo_unico` | 10.7 | margen operativo enseñado 9.0% (EDGAR, TTM) frente a 19.7% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (10.7 pp > 3 pp); puntúa en Rentabilidad (-1) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 15 | BA (The Boeing Company) | CYCLICAL | `margen_operativo_unico` | 10.5 | margen operativo enseñado 4.6% (EDGAR, TTM) frente a −5.9% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (10.5 pp > 3 pp); puntúa en Rentabilidad (-1) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 16 | ALB (Albemarle Corporation) | CYCLICAL | `margen_operativo_unico` | 9.5 | margen operativo enseñado 4.3% (EDGAR, TTM) frente a 13.7% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (9.5 pp > 3 pp); puntúa en Rentabilidad (-3) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 17 | FIX (Comfort Systems USA, Inc.) | GROWTH_PROFITABLE | `margen_operativo_unico` | 8.8 | margen operativo enseñado 7.9% (EDGAR, TTM) frente a 16.7% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (8.8 pp > 3 pp); puntúa en Rentabilidad (+1) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 18 | XYZ (Block, Inc.) | MATURE | `margen_operativo_unico` | 7.8 | margen operativo enseñado 4.7% (EDGAR, TTM) frente a 12.5% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (7.8 pp > 3 pp); puntúa en Rentabilidad (-3) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 19 | ABBV (AbbVie Inc.) | MATURE | `margen_operativo_unico` | 7.7 | margen operativo enseñado 26.2% (EDGAR, TTM) frente a 33.9% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (7.7 pp > 3 pp); puntúa en Rentabilidad (+5) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |
| 20 | INTC (Intel Corporation) | CYCLICAL | `margen_operativo_unico` | 7.7 | margen operativo enseñado −0.1% (EDGAR, TTM) frente a 7.6% de las piezas de la normalización (Yahoo, suma de 4 trimestres) (7.7 pp > 3 pp); puntúa en Rentabilidad (-5) | dos fuentes del mismo margen y periodo: el que se enseña (y puntúa) no es el que usa la normalización |

## Tipos de empresa en el universo

| Arquetipo | Empresas |
|---|---:|
| MATURE | 333 |
| CYCLICAL | 60 |
| FINANCIAL | 52 |
| GROWTH_PROFITABLE | 41 |
| UTILITY | 28 |
| REIT | 28 |
| GROWTH_PRE_PROFIT | 1 |

Subtipos: FINANCIAL · aseguradora 16; FINANCIAL · banco 26; FINANCIAL · conglomerado 1; FINANCIAL · financiera 9.

Regla de clasificación que decidió: `por_defecto` 301; `historia_ciclica` 56; `crecimiento_rentable` 41; `excepcion_financiera` 29; `industria_utility` 28; `industria_reit` 28; `industria_banco` 26; `industria_aseguradora` 17; `financiera_ambigua` 6; `credito_con_balance` 3; `red_de_pagos` 3; `industria_ciclica` 2; `industria_ciclica_condicional` 2; `pre_beneficio_con_crecimiento` 1.

## Por empresa (con alguna violación)

| Empresa | Arquetipo | Violaciones | Reglas | Calidad | Precio | Confianza |
|---|---|---:|---|---:|---:|---|
| BTI | MATURE | 2 | margen_operativo_unico, beta_en_rango | — | 45 | baja |
| ABBV | MATURE | 1 | margen_operativo_unico | — | 10 | alta |
| ACGL | FINANCIAL · aseguradora | 1 | beta_en_rango | — | 60 | baja |
| ALB | CYCLICAL | 1 | margen_operativo_unico | — | 42 | baja |
| APD | MATURE | 1 | margen_operativo_unico | — | 32 | baja |
| APTV | MATURE | 1 | margen_operativo_unico | — | 46 | media |
| BA | CYCLICAL | 1 | margen_operativo_unico | — | — | baja |
| BAX | MATURE | 1 | margen_operativo_unico | — | 24 | baja |
| BEN | MATURE | 1 | margen_operativo_unico | — | 20 | media |
| BF-B | MATURE | 1 | margen_operativo_unico | — | 45 | baja |
| CEG | MATURE | 1 | beta_en_rango | — | 20 | baja |
| CL | MATURE | 1 | margen_operativo_unico | — | 31 | media |
| CMS | UTILITY | 1 | margen_operativo_unico | — | 39 | media |
| CPAY | MATURE | 1 | margen_operativo_unico | — | 60 | baja |
| CRL | MATURE | 1 | margen_operativo_unico | — | 39 | media |
| CVX | CYCLICAL | 1 | beta_en_rango | — | 42 | baja |
| D | UTILITY | 1 | margen_operativo_unico | — | 46 | media |
| DEO | MATURE | 1 | margen_operativo_unico | — | 42 | media |
| DIS | MATURE | 1 | margen_operativo_unico | — | 55 | baja |
| ECHO | MATURE | 1 | margen_operativo_unico | — | 50 | baja |
| EL | MATURE | 1 | margen_operativo_unico | — | 28 | media |
| EW | MATURE | 1 | margen_operativo_unico | — | 15 | alta |
| FANG | CYCLICAL | 1 | margen_operativo_unico | — | 42 | baja |
| FDXF | MATURE | 1 | margen_operativo_unico | — | 42 | baja |
| FIX | GROWTH_PROFITABLE | 1 | margen_operativo_unico | — | 61 | media |
| GILD | MATURE | 1 | margen_operativo_unico | — | 28 | baja |
| GIS | MATURE | 1 | margen_operativo_unico | — | 28 | baja |
| GPN | MATURE | 1 | margen_operativo_unico | — | 35 | baja |
| HON | CYCLICAL | 1 | margen_operativo_unico | — | 55 | baja |
| IFF | MATURE | 1 | margen_operativo_unico | — | 16 | baja |
| INTC | CYCLICAL | 1 | margen_operativo_unico | — | 35 | baja |
| ISRG | GROWTH_PROFITABLE | 1 | margen_operativo_unico | — | 24 | baja |
| KHC | MATURE | 1 | margen_operativo_unico | — | 52 | baja |
| LYB | MATURE | 1 | margen_operativo_unico | — | 42 | media |
| MKC | MATURE | 1 | margen_operativo_unico | — | 58 | media |
| MO | MATURE | 1 | margen_operativo_unico | — | 50 | baja |
| MOS | CYCLICAL | 1 | margen_operativo_unico | — | 50 | baja |
| MPC | CYCLICAL | 1 | beta_en_rango | — | 58 | baja |
| NSC | CYCLICAL | 1 | margen_operativo_unico | — | 38 | baja |
| NXPI | MATURE | 1 | margen_operativo_unico | — | 38 | baja |
| ON | CYCLICAL | 1 | margen_operativo_unico | — | 52 | baja |
| PSX | CYCLICAL | 1 | beta_en_rango | — | 48 | baja |
| SHOP | GROWTH_PROFITABLE | 1 | margen_operativo_unico | — | 15 | media |
| SJM | MATURE | 1 | margen_operativo_unico | — | 61 | media |
| SKYD | MATURE | 1 | margen_operativo_unico | — | 35 | baja |
| SOLV | MATURE | 1 | margen_operativo_unico | — | 54 | media |
| SPGI | MATURE | 1 | margen_operativo_unico | — | 48 | baja |
| SRE | UTILITY | 1 | beta_en_rango | — | 39 | media |
| T | MATURE | 1 | margen_operativo_unico | — | 62 | baja |
| TROW | MATURE | 1 | margen_operativo_unico | — | 69 | media |
| V | MATURE | 1 | margen_operativo_unico | — | 5 | alta |
| VLO | CYCLICAL | 1 | beta_en_rango | — | 50 | baja |
| XOM | CYCLICAL | 1 | beta_en_rango | — | 45 | baja |
| XYZ | MATURE | 1 | margen_operativo_unico | — | 65 | media |
