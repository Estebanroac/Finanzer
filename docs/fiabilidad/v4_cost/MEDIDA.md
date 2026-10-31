> Medida en vivo del 30-oct, mismo día. Antes = ad178cb9 (worktree desechable); después = `rediseno/v4-cost`. Las 543
> empresas del universo con `tools/universe_scan.py --no-pdf` (cachés `2026-10-30-cost-antes` y `-despues`). Las 18 con
> el P/E ≤ 0 se volvieron a analizar tras pasar su PEG de «sin dato» a n.s. Generado con
> `backend/tools/v4_cost_medida.py`.
>
> Lectura:
> - los cambios de **calidad** vienen de la confianza (baja ↔ media), que se mueve con el precio por la dependencia de
>   Ke o por la convergencia de los múltiplos; la calidad cruda no cambia;
> - **LEN** es deriva entre los dos escaneos: su EV/EBITDA pasa de 12,89x a 12,87x y cruza un tramo; es la única con
>   cambio de nivel sin cambio de PEG ni de BPA;
> - **ECHO** queda con el precio no concluyente: antes su único componente de Valoración evaluable era el PEG de la
>   fuente (1,33) con el P/E negativo.

# Revisión de COST: antes y después (543 empresas)

## Hallazgo 2 · BPA «sin dato» con ≥ 4 ejercicios de beneficio en EDGAR
- Antes: **53**; después: **44**; recuperadas: 9.

| Empresa | Motivo antes | Crecimiento del BPA después |
|---|---|---|
| AZO | menos de 4 ejercicios anuales de BPA | 4.8% |
| CLX | menos de 4 ejercicios anuales de BPA | n.s. |
| COST | menos de 4 ejercicios anuales de BPA | 13.6% |
| FERG | menos de 4 ejercicios anuales de BPA | -1.3% |
| FFIV | menos de 4 ejercicios anuales de BPA | 30.8% |
| PH | menos de 4 ejercicios anuales de BPA | 21.1% |
| RJF | menos de 4 ejercicios anuales de BPA | 13.8% |
| RMD | menos de 4 ejercicios anuales de BPA | 19.6% |
| SNDK | menos de 4 ejercicios anuales de BPA | n.s. |

Siguen «sin dato» (por motivo):

- el BPA cambia de signo en el periodo: CAGR no definido: 25 (AIG, APD, BMY, BTI, CNC, CRL, DLTR, ECHO, EL, ES, GIS, HPE, IVZ, KEY, KHC, LYV, MMM, MRNA, NRG, OMC, SONY, SWK, TFC, TSN, WTW)
- el BPA medio de una mitad del ciclo no es positivo (pérdidas): no hay tasa de crecimiento: 9 (BA, COP, DVN, EXE, FCX, HAL, MGM, OXY, VRTX)
- menos de 4 ejercicios anuales de BPA: 5 (CSCO, HDB, MUFG, SMFG, TM)
- el BPA de operaciones continuadas cambia de signo en el periodo: CAGR no definido: 2 (IP, LYB)
- negativo en todos los ejercicios de la ventana (BPA de −$1.62 por acción a −$0.37 por acción): la tasa no se calcula, pero es una señal, no un dato ausente: 1 (BE)
- sin BPA positivo en ejercicios consecutivos para el promedio de ciclo: 1 (MRVL)
- negativo en todos los ejercicios de la ventana (BPA de −$7.03 por acción a −$1.62 por acción): la tasa no se calcula, pero es una señal, no un dato ausente: 1 (TTWO)

## Hallazgo 2 · PEG
- Cambia el PEG en **253**; cambia su tramo (o pasa a n.s.) en **198**.

| Empresa | PEG antes | PEG después | Precio (antes → después) |
|---|---|---|---|
| A | n.s. | 11.37 (propio) | muy exigente 10 → muy exigente 5 |
| ADP | n.s. | 2.60 (propio) | exigente 31 → exigente 31 |
| AJG | n.s. | 13.14 (propio) | razonable 50 → razonable 50 |
| ALGN | n.s. | 3.10 (propio) | razonable 52 → razonable 50 |
| AMZN | 1.41 (fuente) | n.s. | muy exigente 28 → exigente 31 |
| AON | n.s. | 1.49 (propio) | razonable 50 → razonable 50 |
| APD | 2.24 (fuente) | n.s. | exigente 32 → exigente 35 |
| APO | 0.45 (fuente) | n.s. | atractivo 69 → atractivo 65 |
| ARES | n.s. | 94.14 (propio) | muy exigente 16 → muy exigente 16 |
| AZN | n.s. | 0.39 (propio) | muy exigente 24 → muy exigente 24 |
| AZO | 1.34 (fuente) | 4.29 (propio) | exigente 35 → exigente 35 |
| BABA | n.s. | 1.40 (propio) | razonable 50 → razonable 50 |
| BALL | n.s. | 1.37 (propio) | razonable 46 → razonable 50 |
| BAX | 36.68 (fuente) | n.s. | muy exigente 24 → exigente 31 |
| BE | 0.42 (fuente) | n.s. | muy exigente 28 → muy exigente 15 |
| BKR | 1.55 (fuente) | n.s. | razonable 55 → razonable 54 |
| BLK | n.s. | 20.30 (propio) | muy exigente 10 → muy exigente 10 |
| BMY | 17.02 (fuente) | n.s. | razonable 58 → atractivo 65 |
| BP | 0.05 (fuente) | n.s. | atractivo 72 → razonable 62 |
| BR | n.s. | 0.85 (propio) | razonable 50 → razonable 50 |
| BRO | n.s. | 2.16 (propio) | atractivo 72 → atractivo 72 |
| BTI | 1.53 (fuente) | n.s. | razonable 45 → razonable 46 |
| BX | n.s. | 2.27 (propio) | exigente 40 → exigente 40 |
| CASY | n.s. | 1.90 (propio) | muy exigente 10 → muy exigente 10 |
| CBOE | n.s. | 1.28 (propio) | razonable 61 → razonable 61 |
| CCL | 0.99 (fuente) | n.s. | atractivo 75 → atractivo 75 |
| CEG | 3.74 (fuente) | n.s. | muy exigente 20 → muy exigente 20 |
| CHD | n.s. | 1.59 (propio) | exigente 38 → exigente 38 |
| CI | n.s. | 9.10 (propio) | atractivo 90 → atractivo 76 |
| CL | n.s. | 5.18 (propio) | exigente 31 → exigente 31 |
| CLX | 1.11 (fuente) | n.s. | exigente 40 → exigente 40 |
| CMCSA | n.s. | 0.51 (propio) | atractivo 95 → atractivo 100 |
| CME | n.s. | 1.70 (propio) | razonable 45 → razonable 45 |
| CMI | n.s. | 2.42 (propio) | razonable 50 → razonable 50 |
| CNC | 0.83 (fuente) | n.s. | razonable 60 → razonable 60 |
| COHR | 0.92 (fuente) | n.s. | exigente 40 → exigente 35 |
| COIN | 2.35 (fuente) | n.s. | exigente 42 → razonable 45 |
| CPAY | n.s. | 3.69 (propio) | razonable 60 → razonable 58 |
| CRH | n.s. | 5.14 (propio) | exigente 31 → exigente 31 |
| CRL | 0.12 (fuente) | n.s. | exigente 39 → exigente 38 |
| CRM | n.s. | 0.61 (propio) | atractivo 90 → atractivo 90 |
| CRWD | 6.74 (fuente) | n.s. | muy exigente 28 → muy exigente 28 |
| CSCO | 1.00 (fuente) | n.s. | razonable 45 → razonable 45 |
| CTSH | n.s. | 12.53 (propio) | atractivo 76 → atractivo 72 |
| CVNA | 0.15 (fuente) | n.s. | exigente 38 → exigente 35 |
| DASH | 0.81 (fuente) | n.s. | muy exigente 28 → muy exigente 24 |
| DD | 1.72 (fuente) | n.s. | exigente 31 → exigente 31 |
| DDOG | 1.38 (fuente) | n.s. | muy exigente 5 → muy exigente 5 |
| DGX | n.s. | 7.92 (propio) | muy exigente 28 → muy exigente 28 |
| DIS | n.s. | 0.39 (propio) | razonable 55 → razonable 55 |
| DLTR | 1.34 (fuente) | n.s. | atractivo 75 → atractivo 75 |
| DOV | n.s. | 10.62 (propio) | exigente 39 → exigente 35 |
| DVA | n.s. | 0.80 (propio) | atractivo 76 → atractivo 76 |
| EBAY | 1.68 (fuente) | n.s. | muy exigente 28 → exigente 31 |
| ECHO | 1.33 (fuente) | n.s. | razonable 50 → None None |
| ECL | n.s. | 1.71 (propio) | muy exigente 16 → muy exigente 16 |
| EL | 2.12 (fuente) | n.s. | muy exigente 28 → muy exigente 28 |
| ELV | n.s. | 33.20 (propio) | atractivo 70 → razonable 61 |
| ERIE | n.s. | 1.02 (propio) | razonable 60 → razonable 60 |
| FDS | n.s. | 3.42 (propio) | atractivo 75 → razonable 62 |
| FDX | n.s. | 2.75 (propio) | razonable 55 → razonable 54 |
| FERG | 1.47 (fuente) | n.s. | exigente 38 → exigente 38 |
| FFIV | 1.30 (fuente) | 0.88 (propio) | exigente 31 → exigente 35 |
| FIS | 0.20 (fuente) | n.s. | razonable 58 → razonable 58 |
| FISV | 1.83 (fuente) | — | None None → None None |
| FLEX | n.s. | 2.93 (propio) | exigente 42 → exigente 39 |
| FOX | — | 0.82 (propio) | atractivo 69 → atractivo 65 |
| FTV | n.s. | 1.49 (propio) | exigente 42 → razonable 46 |
| GD | n.s. | 2.79 (propio) | atractivo 76 → atractivo 72 |
| GEV | 1.75 (fuente) | n.s. | razonable 50 → razonable 50 |
| GILD | 2.45 (fuente) | n.s. | muy exigente 28 → exigente 31 |
| GIS | 11.74 (fuente) | n.s. | muy exigente 28 → exigente 35 |
| GLW | n.s. | 8.33 (propio) | muy exigente 16 → muy exigente 16 |
| GRMN | n.s. | 1.36 (propio) | muy exigente 16 → muy exigente 20 |
| GWW | n.s. | 6.16 (propio) | muy exigente 5 → muy exigente 5 |
| HII | n.s. | 8.79 (propio) | razonable 58 → razonable 54 |
| HONA | 1.02 (fuente) | n.s. | razonable 45 → exigente 42 |
| HPE | 0.47 (fuente) | n.s. | razonable 55 → razonable 55 |
| HWM | n.s. | 0.90 (propio) | muy exigente 28 → exigente 31 |
| IBM | n.s. | 1.47 (propio) | exigente 35 → exigente 35 |
| ICE | n.s. | 0.78 (propio) | razonable 60 → razonable 60 |
| IDXX | n.s. | 2.24 (propio) | muy exigente 10 → muy exigente 5 |
| IFF | 2.24 (fuente) | n.s. | muy exigente 20 → muy exigente 20 |
| ILMN | 3.58 (fuente) | n.s. | muy exigente 24 → muy exigente 24 |
| INCY | n.s. | 0.25 (propio) | razonable 60 → razonable 60 |
| INFY | n.s. | 3.79 (propio) | razonable 58 → razonable 55 |
| IP | 1.58 (fuente) | n.s. | exigente 38 → exigente 38 |
| IQV | n.s. | 2.94 (propio) | razonable 46 → exigente 42 |
| IVZ | 0.90 (fuente) | n.s. | razonable 52 → razonable 50 |
| JBL | n.s. | 1.59 (propio) | razonable 61 → razonable 61 |
| JCI | n.s. | 1.00 (propio) | muy exigente 5 → muy exigente 10 |
| JNJ | n.s. | 2.34 (propio) | muy exigente 15 → muy exigente 15 |
| KDP | n.s. | 2.43 (propio) | razonable 55 → razonable 52 |
| KHC | 0.99 (fuente) | n.s. | razonable 52 → razonable 50 |
| KKR | 0.41 (fuente) | n.s. | razonable 50 → razonable 46 |
| KLAC | n.s. | 2.70 (propio) | muy exigente 28 → muy exigente 24 |
| KMB | n.s. | 3.47 (propio) | exigente 35 → exigente 35 |
| KO | n.s. | 2.41 (propio) | exigente 31 → exigente 31 |
| LDOS | n.s. | 0.43 (propio) | atractivo 95 → atractivo 95 |
| LIN | n.s. | 1.57 (propio) | muy exigente 16 → muy exigente 16 |
| LOW | n.s. | 3.38 (propio) | razonable 52 → razonable 50 |
| LULU | n.s. | 0.35 (propio) | atractivo 76 → atractivo 76 |
| LYB | 1.53 (fuente) | n.s. | exigente 42 → exigente 42 |
| LYV | 4.64 (fuente) | n.s. | exigente 31 → exigente 42 |
| MA | n.s. | 2.01 (propio) | exigente 35 → exigente 35 |
| MAS | n.s. | 8.42 (propio) | exigente 39 → exigente 35 |
| MCD | n.s. | 1.64 (propio) | razonable 45 → razonable 45 |
| MCK | n.s. | 1.76 (propio) | razonable 55 → razonable 55 |
| MDT | n.s. | 2.44 (propio) | exigente 35 → exigente 31 |
| MKC | n.s. | 1.68 (propio) | razonable 58 → razonable 58 |
| MLM | n.s. | 29.10 (propio) | muy exigente 20 → muy exigente 20 |
| MMM | 1.56 (fuente) | n.s. | muy exigente 25 → muy exigente 25 |
| MO | n.s. | 1.84 (propio) | razonable 50 → razonable 48 |
| MRSH | n.s. | 2.04 (propio) | razonable 54 → razonable 52 |
| NCLH | 1.53 (fuente) | n.s. | razonable 54 → razonable 54 |
| NDAQ | n.s. | 2.66 (propio) | muy exigente 10 → muy exigente 10 |
| NEM | 2.78 (fuente) | n.s. | atractivo 72 → atractivo 85 |
| NFLX | n.s. | 0.49 (propio) | razonable 60 → atractivo 69 |
| NRG | 0.41 (fuente) | n.s. | muy exigente 28 → muy exigente 24 |
| NTAP | n.s. | 8.98 (propio) | razonable 45 → exigente 39 |
| NWS | n.s. | 1.93 (propio) | razonable 52 → razonable 50 |
| NWSA | n.s. | 1.76 (propio) | razonable 55 → razonable 55 |
| OKE | n.s. | 1.24 (propio) | razonable 58 → razonable 55 |
| OMC | 15.97 (fuente) | n.s. | razonable 60 → razonable 62 |
| ORCL | n.s. | 0.86 (propio) | atractivo 75 → atractivo 70 |
| ORLY | n.s. | 2.72 (propio) | muy exigente 28 → muy exigente 15 |
| OTIS | n.s. | 3.27 (propio) | razonable 45 → exigente 42 |
| P | n.s. | 5.11 (propio) | muy exigente 25 → muy exigente 25 |
| PAYX | n.s. | 5.07 (propio) | razonable 45 → exigente 42 |
| PH | 3.11 (fuente) | 1.52 (propio) | muy exigente 15 → muy exigente 28 |
| PHM | n.s. | 39.88 (propio) | razonable 50 → razonable 46 |
| PLTR | 1.70 (fuente) | n.s. | muy exigente 24 → muy exigente 24 |
| PNR | n.s. | 1.64 (propio) | razonable 45 → razonable 45 |
| PPG | n.s. | 0.98 (propio) | razonable 50 → razonable 50 |
| PTC | n.s. | 0.58 (propio) | razonable 50 → razonable 52 |
| PWR | n.s. | 2.62 (propio) | muy exigente 28 → muy exigente 28 |
| PYPL | n.s. | 0.29 (propio) | atractivo 95 → atractivo 100 |
| RCL | 1.25 (fuente) | n.s. | muy exigente 28 → exigente 31 |
| RDDT | 0.65 (fuente) | n.s. | razonable 61 → razonable 58 |
| REGN | n.s. | 8.17 (propio) | muy exigente 28 → muy exigente 24 |
| RJF | 0.79 (fuente) | 0.96 (propio) | razonable 60 → atractivo 65 |
| RMD | 1.35 (fuente) | 1.14 (propio) | razonable 58 → razonable 58 |
| ROL | n.s. | 2.42 (propio) | razonable 48 → razonable 48 |
| RTX | n.s. | 2.65 (propio) | exigente 31 → exigente 38 |
| SAP | n.s. | 9.40 (propio) | exigente 31 → exigente 31 |
| SE | 0.79 (fuente) | n.s. | atractivo 65 → razonable 61 |
| SHOP | 2.34 (fuente) | n.s. | muy exigente 15 → muy exigente 15 |
| SHW | n.s. | 3.07 (propio) | muy exigente 10 → muy exigente 10 |
| SJM | 2.17 (fuente) | n.s. | razonable 61 → razonable 61 |
| SKYD | 2.54 (fuente) | n.s. | exigente 32 → exigente 38 |
| SMCI | n.s. | 0.24 (propio) | atractivo 70 → atractivo 70 |
| SNA | n.s. | 4.13 (propio) | razonable 58 → razonable 55 |
| SNDK | 0.03 (fuente) | n.s. | atractivo 72 → atractivo 72 |
| SOLV | n.s. | 2.22 (propio) | razonable 54 → razonable 54 |
| SONY | 1.68 (fuente) | n.s. | razonable 60 → razonable 60 |
| SPOT | 1.45 (fuente) | n.s. | exigente 40 → exigente 40 |
| STE | n.s. | 1.18 (propio) | razonable 45 → razonable 45 |
| STT | n.s. | 1.48 (propio) | razonable 54 → razonable 54 |
| STZ | 1.66 (fuente) | n.s. | razonable 55 → razonable 55 |
| SWK | 1.39 (fuente) | n.s. | razonable 52 → razonable 52 |
| SYK | n.s. | 2.82 (propio) | razonable 48 → razonable 48 |
| SYY | n.s. | 12.62 (propio) | razonable 45 → exigente 39 |
| T | 1.24 (fuente) | n.s. | razonable 62 → razonable 62 |
| TDY | n.s. | 6.64 (propio) | exigente 38 → muy exigente 20 |
| TGT | n.s. | 1.47 (propio) | razonable 55 → razonable 55 |
| TJX | n.s. | 1.47 (propio) | muy exigente 28 → muy exigente 28 |
| TKO | 1.54 (fuente) | n.s. | razonable 48 → razonable 48 |
| TM | 1.56 (fuente) | n.s. | razonable 46 → razonable 46 |
| TMO | n.s. | 176.70 (propio) | muy exigente 28 → muy exigente 24 |
| TRGP | n.s. | 0.99 (propio) | muy exigente 10 → muy exigente 15 |
| TROW | n.s. | 0.92 (propio) | atractivo 69 → atractivo 69 |
| TSCO | n.s. | 9.12 (propio) | exigente 42 → exigente 39 |
| TSN | 1.04 (fuente) | n.s. | razonable 52 → razonable 50 |
| TTWO | 2.65 (fuente) | n.s. | muy exigente 20 → exigente 30 |
| TWLO | 0.38 (fuente) | n.s. | exigente 31 → muy exigente 28 |
| TXT | n.s. | 1.93 (propio) | razonable 52 → razonable 50 |
| TYL | n.s. | 2.13 (propio) | muy exigente 28 → muy exigente 15 |
| UBER | 5.72 (fuente) | n.s. | razonable 50 → razonable 50 |
| UHS | n.s. | 0.20 (propio) | atractivo 72 → atractivo 72 |
| ULTA | n.s. | 10.49 (propio) | exigente 39 → exigente 35 |
| URI | n.s. | 2.81 (propio) | exigente 39 → exigente 35 |
| V | n.s. | 2.51 (propio) | muy exigente 5 → muy exigente 5 |
| VEEV | n.s. | 2.32 (propio) | exigente 38 → muy exigente 28 |
| VLTO | n.s. | 9.03 (propio) | exigente 31 → muy exigente 28 |
| VMC | n.s. | 1.40 (propio) | exigente 31 → exigente 31 |
| VRSK | n.s. | 11.58 (propio) | exigente 35 → exigente 35 |
| VRSN | n.s. | 2.75 (propio) | muy exigente 15 → muy exigente 15 |
| VST | 0.40 (fuente) | n.s. | razonable 58 → razonable 58 |
| VTRS | 3.49 (fuente) | n.s. | muy exigente 25 → exigente 39 |
| WDAY | 0.59 (fuente) | n.s. | exigente 31 → exigente 35 |
| WM | n.s. | 4.08 (propio) | exigente 42 → exigente 35 |
| WMB | n.s. | 3.45 (propio) | exigente 31 → exigente 31 |
| WMT | n.s. | 1.85 (propio) | muy exigente 10 → muy exigente 5 |
| WTW | 1.27 (fuente) | n.s. | razonable 45 → razonable 45 |
| XYL | n.s. | 0.80 (propio) | razonable 50 → razonable 52 |
| XYZ | 0.59 (fuente) | n.s. | atractivo 65 → razonable 58 |
| YUM | n.s. | 2.93 (propio) | exigente 42 → exigente 39 |
| ZTS | n.s. | 1.27 (propio) | razonable 58 → razonable 58 |

## Niveles
- Cambia el nivel de calidad en **5**: FDS, NFLX, RJF, SYY, WM.
- Cambia el nivel de precio en **31**: AMZN, BAX, BMY, BP, COIN, EBAY, ECHO, ELV, FDS, FTV, GILD, GIS, HONA, HWM, IQV, LEN, NFLX, NTAP, OTIS, PAYX, RCL, RJF, SE, SYY, TDY, TTWO, TWLO, VEEV, VLTO, VTRS, XYZ.

| Empresa | Calidad | Precio | PEG | Crecimiento del BPA |
|---|---|---|---|---|
| AMZN | sólida 65 → sólida 65 | muy exigente 28 → exigente 31 | 1.41 (fuente) → n.s. | — → — |
| BAX | débil 38 → débil 38 | muy exigente 24 → exigente 31 | 36.68 (fuente) → n.s. | — → — |
| BMY | sólida 68 → sólida 71 | razonable 58 → atractivo 65 | 17.02 (fuente) → n.s. | — → — |
| BP | media 45 → media 46 | atractivo 72 → razonable 62 | 0.05 (fuente) → n.s. | — → — |
| COIN | media 59 → media 59 | exigente 42 → razonable 45 | 2.35 (fuente) → n.s. | — → — |
| EBAY | sólida 70 → sólida 70 | muy exigente 28 → exigente 31 | 1.68 (fuente) → n.s. | — → — |
| ECHO | débil 16 → débil 16 | razonable 50 → None None | 1.33 (fuente) → n.s. | — → — |
| ELV | media 62 → media 62 | atractivo 70 → razonable 61 | n.s. → 33.20 (propio) | 0.5% → 0.5% |
| FDS | excelente 85 → sólida 80 | atractivo 75 → razonable 62 | n.s. → 3.42 (propio) | 6.6% → 6.6% |
| FTV | sólida 75 → sólida 75 | exigente 42 → razonable 46 | n.s. → 1.49 (propio) | 20.8% → 20.8% |
| GILD | media 54 → media 54 | muy exigente 28 → exigente 31 | 2.45 (fuente) → n.s. | 23.0% → 23.0% |
| GIS | media 50 → media 50 | muy exigente 28 → exigente 35 | 11.74 (fuente) → n.s. | — → — |
| HONA | sólida 76 → sólida 76 | razonable 45 → exigente 42 | 1.02 (fuente) → n.s. | — → — |
| HWM | excelente 96 → excelente 96 | muy exigente 28 → exigente 31 | n.s. → 0.90 (propio) | 48.4% → 48.4% |
| IQV | media 59 → media 59 | razonable 46 → exigente 42 | n.s. → 2.94 (propio) | 11.1% → 11.1% |
| LEN | media 48 → media 48 | muy exigente 25 → exigente 35 | n.s. → n.s. | -20.2% → -20.2% |
| NFLX | sólida 82 → excelente 88 | razonable 60 → atractivo 69 | n.s. → 0.49 (propio) | 36.5% → 36.5% |
| NTAP | sólida 76 → sólida 81 | razonable 45 → exigente 39 | n.s. → 8.98 (propio) | 3.1% → 3.1% |
| OTIS | sólida 65 → sólida 65 | razonable 45 → exigente 42 | n.s. → 3.27 (propio) | 5.7% → 5.7% |
| PAYX | sólida 76 → sólida 76 | razonable 45 → exigente 42 | n.s. → 5.07 (propio) | 4.4% → 4.4% |
| RCL | sólida 69 → sólida 69 | muy exigente 28 → exigente 31 | 1.25 (fuente) → n.s. | — → — |
| RJF | media 63 → sólida 65 | razonable 60 → atractivo 65 | 0.79 (fuente) → 0.96 (propio) | — → 13.8% |
| SE | sólida 78 → sólida 78 | atractivo 65 → razonable 61 | 0.79 (fuente) → n.s. | — → — |
| SYY | media 64 → sólida 66 | razonable 45 → exigente 39 | n.s. → 12.62 (propio) | 1.8% → 1.8% |
| TDY | sólida 76 → sólida 80 | exigente 38 → muy exigente 20 | n.s. → 6.64 (propio) | 4.5% → 4.5% |
| TTWO | media 48 → media 48 | muy exigente 20 → exigente 30 | 2.65 (fuente) → n.s. | — → — |
| TWLO | sólida 66 → sólida 66 | exigente 31 → muy exigente 28 | 0.38 (fuente) → n.s. | — → — |
| VEEV | excelente 91 → excelente 98 | exigente 38 → muy exigente 28 | n.s. → 2.32 (propio) | 21.9% → 21.9% |
| VLTO | sólida 84 → sólida 84 | exigente 31 → muy exigente 28 | n.s. → 9.03 (propio) | 3.2% → 3.2% |
| VTRS | débil 30 → débil 30 | muy exigente 25 → exigente 39 | 3.49 (fuente) → n.s. | — → — |
| WM | media 64 → sólida 66 | exigente 42 → exigente 35 | n.s. → 4.08 (propio) | 7.5% → 7.5% |
| XYZ | media 64 → media 62 | atractivo 65 → razonable 58 | 0.59 (fuente) → n.s. | — → — |

## Hallazgo 4 · el escalón de las tasas base
- Con escalón: 82; contrae ahora (precio crudo > 50): **1** TSM.

## Hallazgo 6 · margen de seguridad acotado
- Se muestra acotado en **110**.

