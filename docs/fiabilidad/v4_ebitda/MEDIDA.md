> Medida en vivo del 30-oct. Después = `rediseno/v4-ebitda` con la regla del corte y la de cada ejercicio sobre las 543
> empresas del universo (`tools/universe_scan.py --no-pdf`, caché `2026-10-30-ebitda3-despues`). Antes = 46a9b78f
> (worktree desechable) solo en las afectadas y en 20 de control (`-ebitda2-antes`). Generado con
> `backend/tools/v4_ebitda_medida.py`. Entre los dos escaneos del «después», Yahoo dio el desglose del D&A a 14 empresas
> menos (436 frente a 422 sin desglose); las afectadas no cambian.

# El D&A del EBITDA sin amortizaciones de activos operativos recurrentes (543 empresas)

Estado de la amortización de intangibles del D&A de la fuente (data_provenance.edgar.primary.da):

- sin desglose: **436**
- respaldado: **81**
- no_verificable: **23**
- excluido: **3**

## Quitada del EBITDA (sin respaldo en EDGAR y > materialidad de N1): 3

| Empresa | Amortización de la fuente (B) | Respaldo en EDGAR (B) | Quitada (B) | % de los ingresos |
|---|---|---|---|---|
| KDP | 0.71 | 0.23 | 0.48 | 2.4% |
| NFLX | 17.53 | 0.00 | 17.53 | 35.2% |
| TTWO | 1.17 | 0.03 | 1.13 | 17.0% |

## No verificable con respaldo medido (por debajo de la materialidad; no se toca): 12

MTD (1.2%), INTU (0.8%), ISRG (0.8%), TPR (0.6%), HAS (0.5%), VTR (0.5%), CIEN (0.4%), IRM (0.4%), WELL (0.4%), NKE (0.1%), KEYS (0.1%), COR (0.0%)

## Antes (46a9b78f) y después: 23 empresas (las afectadas y las de control)

| Empresa | Margen EBITDA | EV/EBITDA | Precio | Calidad |
|---|---|---|---|---|
| AMD | 23.0% → 23.0% | 85.6x → 85.6x | exigente 35 → exigente 35 | sólida 67 → sólida 67 |
| AON | 31.2% → 31.2% | 14.7x → 14.7x | razonable 50 → razonable 50 | sólida 74 → sólida 74 |
| APTV | 10.1% → 10.1% | 7.3x → 7.3x | razonable 46 → razonable 46 | media 60 → media 60 |
| AVGO | 57.9% → 57.9% | 30.9x → 30.9x | muy exigente 28 → muy exigente 28 | excelente 97 → excelente 97 |
| AVY | 16.5% → 16.5% | 11.3x → 11.3x | razonable 45 → razonable 45 | sólida 65 → sólida 65 |
| BR | 22.0% → 22.0% | 14.0x → 14.0x | razonable 50 → razonable 50 | sólida 82 → sólida 82 |
| BRO | 32.9% → 32.9% | 13.3x → 13.3x | razonable 62 → razonable 62 | sólida 76 → sólida 76 |
| COR | 1.2% → 1.2% | 17.5x → 17.5x | razonable 61 → razonable 61 | media 62 → media 62 |
| EMR | 28.6% → 28.6% | 19.3x → 19.3x | exigente 38 → exigente 38 | media 59 → media 59 |
| GNRC | 14.3% → 14.3% | 20.2x → 20.2x | exigente 42 → exigente 42 | media 64 → media 64 |
| HII | 8.1% → 8.1% | 13.5x → 13.5x | exigente 31 → exigente 31 | sólida 70 → sólida 70 |
| IBM | 25.9% → 25.9% | 16.4x → 16.4x | exigente 35 → exigente 35 | sólida 75 → sólida 75 |
| INTC | 21.6% → 21.6% | 30.1x → 30.1x | exigente 35 → exigente 35 | débil 42 → débil 42 |
| IR | 24.8% → 24.8% | 17.6x → 17.6x | exigente 32 → exigente 32 | sólida 72 → sólida 72 |
| KDP (afectada) | 22.5% → 20.2% | 17.3x → 19.3x | razonable 52 → razonable 52 | media 47 → media 47 |
| MCHP | 28.7% → 28.7% | 32.0x → 32.0x | razonable 50 → razonable 50 | media 58 → media 58 |
| MRVL | 29.9% → 29.9% | 62.9x → 62.9x | exigente 35 → exigente 35 | sólida 74 → sólida 74 |
| NFLX (afectada) **cambia de nivel** | 67.3% → 32.1% | 7.9x → 16.6x | atractivo 69 → razonable 58 | excelente 88 → excelente 88 |
| NVS | 38.7% → 38.7% | 15.4x → 15.4x | exigente 40 → exigente 40 | sólida 68 → sólida 68 |
| PWR | 9.8% → 9.8% | 26.9x → 26.9x | exigente 35 → exigente 35 | excelente 85 → excelente 85 |
| TRGP | 32.8% → 32.8% | 15.8x → 15.8x | muy exigente 15 → muy exigente 15 | media 60 → media 60 |
| TTWO (afectada) | 17.5% → 0.5% | 31.0x → 1035.7x | exigente 30 → exigente 30 | media 48 → media 48 |
| WTW | 26.2% → 26.2% | 12.8x → 12.8x | razonable 45 → razonable 45 | sólida 76 → sólida 76 |

Cambian de nivel: **1** (NFLX).

## Filas anuales: ejercicios con la amortización quitada del EBITDA: 5 empresas

- HAS: 2023 0.45 B, 2022 0.56 B
- LITE: 2024 0.03 B
- NFLX: 2025 16.42 B, 2024 15.30 B, 2023 14.20 B, 2022 14.03 B
- TTWO: 2026 0.39 B, 2025 0.27 B, 2024 0.21 B, 2023 0.18 B
- VRSK: 2022 0.07 B

Cíclicas entre ellas (EV/EBITDA normalizado con el EBITDA medio anual): HAS.

## EV/EBITDA mostrado como «> 100x» (EBITDA casi nulo): 12

ARM, AXON, CARR, CRWD, DDOG, GILD, P, PANW, PLTR, SHOP, TSLA, TTWO

## Invariante ebitda_sin_amortizacion_operativa

no_evaluable: 384, ok: 107, no_aplica: 52. Violaciones: ninguna.

