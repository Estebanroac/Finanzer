> Medida en vivo del 29-oct, mismo día. Antes = be9a0ea3, en un worktree desechable; después = `fiabilidad/f10-margen-op`
> con los cuatro puntos del Plan (perímetro, solo se recorta lo nombrable, etiquetas estándar de EDGAR, SKYD declarada)
> y la corrección de la regla 1 (VRSN). Son 186 empresas que la regla puede tocar más 20 de control, y además NVDA, FIS,
> OXY, UBER, TWLO, UL, ABBV y VRSN, con `tools/universe_scan.py --no-pdf`. Las 27 empresas cuyo filing pendiente no se
> pudo leer en el escaneo largo (D, CMS…) se volvieron a analizar. Generado con `backend/tools/f10_margen_op_medida.py`.

# Margen operativo con una sola verdad: antes y después (206 empresas)

- Cambia el nivel de calidad en **4**: APTV, DEO, HON, IFF.
- Cambia el nivel de precio en **4**: D, DLR, FIX, WEC.
- Cambia alguna puntuación (calidad, precio, Rentabilidad o el margen operativo) en 42.

| Empresa | Calidad | Precio | Rentabilidad | Margen operativo que puntúa (antes → después) | Beneficio normalizado (B$) |
|---|---|---|---|---|---|
| ALB | media 46 → media 46 | exigente 42 → exigente 42 | 0 → 0 | Margen operativo 4.27% (-3) → Margen operativo normalizado 4.83% (-1) | 0.09 → 0.09 |
| ALGN | sólida 69 → sólida 71 | razonable 52 → razonable 52 | 12 → 14 | Margen operativo 13.23% (-1) → Margen operativo normalizado 14.98% (+1) | 0.46 → 0.46 |
| AMAT | sólida 84 → sólida 84 | exigente 35 → exigente 35 | 20 → 20 | Margen operativo 29.64% (+1) → Margen operativo normalizado 30.50% (+3) | 9.50 → 9.50 |
| APD | débil 16 → débil 22 | exigente 32 → exigente 32 | 2 → 6 | Margen operativo -4.71% (-5) → Margen operativo normalizado 14.04% (+1) | 1.69 → 1.69 |
| APTV | sólida 65 → media 60 | razonable 46 → razonable 46 | 6 → 4 | Margen operativo 6.47% (+1) → Margen operativo normalizado 7.08% (+1) | 0.59 → 0.59 |
| BA | débil 29 → débil 24 | None None → None None | 5 → 1 | Margen operativo 4.63% (-1) → Margen operativo normalizado -1.24% (-5) | -6.79 → -4.65 |
| BDX | media 59 → media 61 | razonable 46 → razonable 46 | 4 → 6 | Margen operativo 11.51% (-1) → Margen operativo normalizado 13.99% (+1) | 1.67 → 1.67 |
| BEN | media 49 → media 49 | muy exigente 20 → muy exigente 24 | 0 → 2 | Margen operativo 9.71% (-1) → Margen operativo normalizado 12.23% (+1) | 0.67 → 0.83 |
| BF-B | sólida 80 → sólida 80 | razonable 45 → razonable 45 | 20 → 20 | Margen operativo 25.36% (+1) → Margen operativo normalizado 28.68% (+3) | 0.83 → 0.83 |
| CMS | débil 32 → débil 35 | exigente 39 → exigente 39 | 0 → 2 | Margen operativo 13.77% (-3) → Margen operativo normalizado 20.16% (-1) | 1.33 → 1.33 |
| CRL | media 60 → media 58 | exigente 39 → exigente 39 | 2 → 0 | Margen operativo 15.11% (+1) → Margen operativo normalizado 9.43% (-1) | 0.04 → 0.04 |
| D | media 49 → media 51 | razonable 46 → exigente 42 | 2 → 4 | Margen operativo 21.06% (-1) → Margen operativo normalizado 23.66% (+1) | 2.87 → 2.13 |
| DEO | sólida 66 → media 64 | exigente 42 → exigente 42 | 17 → 15 | Margen operativo 27.04% (+3) → Margen operativo 11.37% (+1) | 1.73 → 1.73 |
| DLR | media 54 → media 53 | muy exigente 20 → exigente 32 | 1 → 1 | — → — | 1.04 → 1.04 |
| ENB | débil 39 → débil 41 | muy exigente 20 → muy exigente 20 | 2 → 4 | Margen operativo 15.22% (-1) → Margen operativo normalizado 15.48% (+1) | 4.79 → 4.79 |
| FANG | débil 42 → débil 42 | exigente 42 → exigente 42 | 6 → 6 | Margen operativo 6.37% (-3) → Margen operativo normalizado 28.83% (+1) | 3.89 → 4.06 |
| FCX | sólida 67 → sólida 65 | razonable 45 → razonable 45 | 19 → 17 | Margen operativo 26.76% (+3) → Margen operativo normalizado 24.61% (+1) | 2.46 → 2.46 |
| FDX | sólida 67 → sólida 69 | razonable 55 → razonable 55 | 10 → 12 | Margen operativo 5.77% (-1) → Margen operativo normalizado 6.16% (+1) | 4.72 → 4.72 |
| FDXF | débil 19 → débil 27 | exigente 42 → exigente 42 | 0 → 6 | Margen operativo -5.77% (-5) → Margen operativo normalizado 11.73% (+1) | 1.02 → 1.02 |
| FIX | excelente 91 → excelente 91 | razonable 61 → atractivo 65 | 20 → 20 | Margen operativo 7.89% (+1) → Margen operativo normalizado 16.67% (+3) | 1.63 → 1.63 |
| GILD | media 50 → media 54 | muy exigente 28 → muy exigente 28 | 3 → 6 | Margen operativo -8.20% (-5) → Margen operativo normalizado 25.76% (+5) | 4.68 → 4.68 |
| GIS | media 45 → media 50 | muy exigente 28 → muy exigente 28 | 2 → 6 | Margen operativo -1.13% (-5) → Margen operativo normalizado 15.16% (+3) | 1.74 → 1.74 |
| GPN | débil 40 → débil 40 | exigente 35 → exigente 35 | 0 → 0 | Margen operativo 12.81% (-1) → Margen operativo normalizado 10.09% (-3) | -1.25 → -1.25 |
| HON | sólida 65 → media 63 | razonable 55 → razonable 55 | 16 → 15 | Margen operativo 27.85% (+1) → Margen operativo normalizado 16.55% (-1) | 3.89 → 3.98 |
| IFF | débil 44 → media 48 | muy exigente 16 → muy exigente 20 | 0 → 0 | Margen operativo -2.92% (-5) → Margen operativo 7.36% (-3) | 0.27 → 0.27 |
| INTC | débil 42 → débil 42 | exigente 35 → exigente 35 | 0 → 0 | Margen operativo -0.14% (-5) → Margen operativo normalizado 7.55% (-3) | -11.05 → -11.05 |
| IQV | media 56 → media 59 | razonable 46 → razonable 46 | 12 → 14 | Margen operativo 12.82% (-1) → Margen operativo normalizado 13.42% (+1) | 1.48 → 1.48 |
| ISRG | excelente 100 → excelente 100 | muy exigente 24 → muy exigente 24 | 20 → 20 | Margen operativo 28.37% (+3) → Margen operativo normalizado 32.19% (+5) | 3.31 → 3.30 |
| KHC | media 53 → media 53 | razonable 52 → razonable 52 | 0 → 0 | Margen operativo -12.76% (-5) → Margen operativo normalizado 2.59% (-3) | -0.09 → -0.09 |
| KO | sólida 79 → sólida 79 | exigente 35 → exigente 31 | 20 → 20 | Margen operativo 29.63% (+3) → Margen operativo 29.63% (+3) | 14.32 → 14.25 |
| LYB | débil 29 → débil 29 | exigente 42 → exigente 42 | 0 → 0 | Margen operativo 3.09% (-3) → Margen operativo normalizado 7.28% (-1) | 0.97 → 0.97 |
| MDT | sólida 80 → sólida 80 | exigente 31 → exigente 35 | 10 → 10 | Margen operativo 18.08% (+3) → Margen operativo 18.08% (+3) | 5.23 → 5.23 |
| MKC | sólida 68 → sólida 65 | razonable 58 → razonable 58 | 10 → 10 | Margen operativo 13.43% (-1) → Margen operativo normalizado 15.95% (+1) | 1.16 → 0.98 |
| MOS | débil 35 → débil 35 | razonable 50 → razonable 50 | 0 → 0 | Margen operativo -1.39% (-5) → Margen operativo normalizado 2.93% (-3) | -0.21 → -0.21 |
| NEE | media 49 → media 49 | exigente 30 → exigente 35 | 6 → 6 | Margen operativo 30.03% (+3) → Margen operativo 30.03% (+3) | 10.39 → 10.85 |
| RIO | sólida 72 → sólida 70 | razonable 46 → razonable 46 | 20 → 20 | Margen operativo 28.05% (+3) → Margen operativo 25.91% (+3) | 10.54 → 12.10 |
| SBUX | media 52 → media 55 | muy exigente 10 → muy exigente 10 | 5 → 7 | Margen operativo 7.77% (-3) → Margen operativo normalizado 9.99% (-1) | 2.51 → 2.67 |
| SKYD | media 53 → media 53 | exigente 35 → exigente 35 | 4 → 6 | Margen operativo 9.35% (+1) → Margen operativo normalizado 5.04% (-1) | 1.30 → 5.96 |
| SOLV | media 54 → media 49 | razonable 54 → razonable 54 | 15 → 11 | Margen operativo 24.98% (+3) → Margen operativo normalizado 7.33% (-1) | 0.21 → 0.21 |
| WDAY | sólida 68 → sólida 68 | exigente 35 → exigente 31 | 9 → 9 | Margen operativo 10.68% (-3) → Margen operativo 10.68% (-3) | 1.25 → 1.20 |
| WDC | sólida 77 → sólida 77 | exigente 35 → exigente 35 | 20 → 20 | Margen operativo 39.41% (+5) → Margen operativo normalizado 33.94% (+3) | 4.19 → 4.19 |
| WEC | media 52 → media 52 | razonable 45 → exigente 39 | 10 → 10 | Margen operativo 22.84% (+1) → Margen operativo 22.84% (+1) | 1.69 → 1.63 |

## Las 46 de la puerta (`margen_operativo_unico`)

Después, el margen que se enseña es el de las piezas por construcción (una sola cifra). Lo que queda es la diferencia entre el que puntúa y la fila trimestral de Yahoo (> 3 pp).

| Empresa | Enseñado (EDGAR) | Puntúa | Yahoo trimestral | Diferencia | Cargos operativos fuera | Clase | Piezas de la normalización |
|---|---:|---:|---:|---:|---:|---|---|
| ABBV | 26.2 % | 30.3 % | 33.9 % | 3.6 pp | +2.67 B$ | causa 2: las fuentes no cuadran | EDGAR |
| ALB | 4.3 % | 4.8 % | 13.7 % | 8.9 pp | +0.03 B$ | causa 2: las fuentes no cuadran | EDGAR |
| APD | -4.7 % | 14.0 % | 24.8 % | 10.8 pp | +2.36 B$ | causa 2: las fuentes no cuadran | EDGAR |
| APTV | 4.8 % | 7.1 % | 9.7 % | 2.7 pp | +0.43 B$ | resuelta (cargos fuera) | EDGAR |
| BA | 4.6 % | -1.2 % | -5.9 % | 4.6 pp | -5.42 B$ | causa 2: las fuentes no cuadran | EDGAR |
| BAX | -2.4 % | -2.4 % | 1.8 % | 4.2 pp | +0.00 B$ | causa 2: las fuentes no cuadran | EDGAR |
| BEN | 9.7 % | 12.2 % | 14.0 % | 1.7 pp | +0.24 B$ | resuelta (cargos fuera) | EDGAR |
| BF-B | 25.4 % | 28.7 % | 28.9 % | 0.2 pp | +0.13 B$ | resuelta (cargos fuera) | EDGAR |
| BTI | 39.0 % | 39.0 % | 39.0 % | 0.0 pp | +0.00 B$ | resuelta (cargos fuera) | ejercicio |
| CL | 14.9 % | 14.9 % | 19.3 % | 4.4 pp | +0.00 B$ | causa 2: las fuentes no cuadran | EDGAR |
| CMS | 13.8 % | 20.2 % | 19.6 % | 0.5 pp | +0.57 B$ | resuelta (cargos fuera) | EDGAR |
| CPAY | 43.7 % | 40.6 % | 40.5 % | 0.1 pp | -0.16 B$ | resuelta (cargos fuera) | EDGAR |
| CRL | 0.6 % | 9.4 % | 0.6 % | 8.8 pp | +0.35 B$ | causa 2: las fuentes no cuadran | ejercicio |
| D | 21.1 % | 23.7 % | 28.1 % | 4.5 pp | +0.47 B$ | causa 2: las fuentes no cuadran | EDGAR |
| DEO | 11.4 % | 11.4 % | 11.4 % | 0.0 pp | +0.00 B$ | resuelta (cargos fuera) | ejercicio |
| DIS | 18.4 % | 18.4 % | 15.2 % | 3.2 pp | +0.00 B$ | causa 2: las fuentes no cuadran | EDGAR |
| ECHO | -112.7 % | -59.6 % | 7.1 % | 66.8 pp | +7.78 B$ | causa 2: las fuentes no cuadran | EDGAR |
| EL | 5.2 % | 5.2 % | 11.1 % | 6.0 pp | +0.00 B$ | causa 2: las fuentes no cuadran | EDGAR |
| EW | 22.3 % | 29.2 % | 28.1 % | 1.1 pp | +0.45 B$ | resuelta (cargos fuera) | EDGAR |
| FANG | 6.4 % | 28.8 % | 35.7 % | 6.8 pp | +3.81 B$ | causa 2: las fuentes no cuadran | EDGAR |
| FDXF | 6.1 % | 11.7 % | 6.1 % | 5.6 pp | +0.49 B$ | causa 2: las fuentes no cuadran | ejercicio |
| FIX | 16.7 % | 16.7 % | 16.7 % | 0.0 pp | -0.00 B$ | resuelta (cargos fuera) | EDGAR |
| GILD | -8.2 % | 25.8 % | 38.5 % | 12.7 pp | +10.34 B$ | causa 2: las fuentes no cuadran | EDGAR |
| GIS | -1.1 % | 15.2 % | 15.2 % | 0.0 pp | +2.98 B$ | resuelta (cargos fuera) | EDGAR |
| GPN | 12.8 % | 10.1 % | 9.7 % | 0.4 pp | -0.28 B$ | resuelta (cargos fuera) | EDGAR |
| HON | 16.2 % | 16.5 % | 16.2 % | 0.3 pp | +0.11 B$ | resuelta (cargos fuera) | Yahoo (el corte) |
| IFF | 7.4 % | 7.4 % | 8.0 % | 0.6 pp | +0.00 B$ | resuelta (cargos fuera) | EDGAR |
| INTC | -0.1 % | 7.6 % | 7.6 % | 0.0 pp | +4.38 B$ | resuelta (cargos fuera) | EDGAR |
| ISRG | 28.4 % | 32.2 % | 32.3 % | 0.1 pp | +0.44 B$ | resuelta (cargos fuera) | EDGAR |
| KHC | -12.8 % | 2.6 % | 17.0 % | 14.4 pp | +3.82 B$ | causa 2: las fuentes no cuadran | EDGAR |
| LYB | 3.1 % | 7.3 % | 7.3 % | 0.0 pp | +1.31 B$ | resuelta (cargos fuera) | EDGAR |
| MKC | 13.4 % | 15.9 % | 16.4 % | 0.5 pp | +0.19 B$ | resuelta (cargos fuera) | EDGAR |
| MO | 53.7 % | 59.9 % | 59.9 % | 0.0 pp | +1.28 B$ | resuelta (cargos fuera) | EDGAR |
| MOS | -1.4 % | 2.9 % | 2.7 % | 0.3 pp | +0.53 B$ | resuelta (cargos fuera) | EDGAR |
| NSC | 31.5 % | 31.5 % | 35.8 % | 4.2 pp | +0.00 B$ | causa 2: las fuentes no cuadran | EDGAR |
| NXPI | 33.0 % | 28.9 % | 28.6 % | 0.3 pp | -0.56 B$ | resuelta (cargos fuera) | EDGAR |
| ON | 10.8 % | 13.1 % | 18.0 % | 5.0 pp | +0.14 B$ | causa 2: las fuentes no cuadran | EDGAR |
| SHOP | 13.9 % | 13.9 % | 17.8 % | 3.9 pp | +0.00 B$ | causa 2: las fuentes no cuadran | EDGAR |
| SJM | 9.0 % | 9.0 % | 19.7 % | 10.7 pp | +0.00 B$ | causa 2: las fuentes no cuadran | EDGAR |
| SKYD | -18.0 % | 5.0 % | -18.0 % | 23.1 pp | +6.74 B$ | causa 2: las fuentes no cuadran | ejercicio |
| SOLV | 25.0 % | 7.3 % | 6.3 % | 1.0 pp | -1.47 B$ | resuelta (cargos fuera) | EDGAR |
| SPGI | 47.9 % | 47.9 % | 42.7 % | 5.3 pp | +0.00 B$ | causa 2: las fuentes no cuadran | EDGAR |
| T | 18.3 % | 18.3 % | 21.4 % | 3.1 pp | +0.00 B$ | causa 2: las fuentes no cuadran | EDGAR |
| TROW | 30.8 % | 32.5 % | 34.4 % | 2.0 pp | +0.13 B$ | resuelta (cargos fuera) | EDGAR |
| V | 60.7 % | 62.9 % | 65.6 % | 2.7 pp | +0.99 B$ | resuelta (cargos fuera) | EDGAR |
| XYZ | 4.7 % | 9.1 % | 12.5 % | 3.4 pp | +1.11 B$ | causa 2: las fuentes no cuadran | EDGAR |

Resueltas 23; quedan por las fuentes 23; sin piezas o no aplica 0.
