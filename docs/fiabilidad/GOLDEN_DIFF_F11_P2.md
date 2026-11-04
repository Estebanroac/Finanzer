# F11 · Paso 2 (N2): una sola definición de ingresos (4-nov-2026)

Rama `fiabilidad/f11-medir`, sobre el paso 1 (a8c996a8). Hallazgo N2 de `revision-nu-nflx-2026-11-04.md`: «Ingresos TTM
menores que los del último ejercicio». Verificado: no es un error de cálculo del TTM, sino dos definiciones. La serie
anual venía de EDGAR (bruta en NU) y el TTM de Yahoo (neta). La medida en el universo (`F11_MEDIDA_2026-11-04.md`)
encontró 35 empresas con discrepancia y dos casos de otra naturaleza (CPT y BBVA, ×120).

## Qué eran, en realidad

| Caso | Empresas | Causa |
|---|---|---|
| Concepto parcial de EDGAR | CPT, BBVA | No es escala ni moneda. CPT (REIT): `RevenueFromContractWithCustomer…` excluye los alquileres (13 M$ frente a 1.574 M$). BBVA: `RevenueAndOperatingIncome` es una partida (0,36 B frente a 44,5 B). La historia, la tabla anual y el crecimiento salían de esa partida |
| Definición distinta y material (> 10 %) en el último ejercicio | NU (+48 %), DEO (+41 %), BF-B (+29 %), WMB (+25 %), BX (+16 %), MO (+16 %), IBKR (−39 %)… | Bruto frente a neto (intereses pagados, impuestos especiales, regalías). La serie de EDGAR y el corte de la fuente, cada uno con la suya |
| Definición distinta no material (2–10 %) | SHEL, XOM, CVX, DE… | No cambia ninguna lectura: sigue la serie de EDGAR (F9 · R3) y la diferencia queda en la conciliación |

## La regla (general, `lib/edgar_primary._one_definition`)

1. **Concepto parcial**: si los ingresos de EDGAR del último ejercicio son menos de la mitad de los de la fuente
   (`fy_series_min_concept_share`), su concepto es una partida y no el total: manda la fuente. Solo en los ingresos
   (`fy_series_total_fields`); el beneficio puede ser legítimamente una fracción de otra definición.
2. **Definición distinta y material** (más de `fy_series_definition_material_rel` = 10 % en el último ejercicio): manda
   la definición **neta**, la menor. No lleva partidas de paso, y es la comparable con las referencias de industria y la
   estándar para bancos (ingresos netos de intereses) y para tabaco y licores (sin impuestos especiales).
   - EDGAR es la bruta (NU, DEO, MO, BF-B…): la fuente en la serie anual, en el corte y en la historia larga.
   - EDGAR es la neta (IBKR, CNQ): el corte pasa a EDGAR con el mismo concepto (FY + acumulado − acumulado anterior) si
     lo tiene; si no, la fuente en todo.
3. Cuando manda la fuente por esta regla, la historia larga de EDGAR de ese campo tampoco se usa (`yf_adapter`): ni
   la tabla de 10 años, ni la regresión del crecimiento robusto, ni la persistencia. La tabla de 10 años dice por qué.
   Nunca dos definiciones del mismo campo en el informe.

**Cambia una decisión anterior.** F9 · R3 dejaba a NU con la serie de EDGAR (bruta) para que coincidiera con la historia
de 10 años. Con F11 · N2, NU usa la definición neta en todo, y la historia de 10 años de los ingresos queda sin dato
con su motivo. Es la definición estándar de los ingresos de un banco.

Primera versión descartada durante el paso: «EDGAR manda si tiene el corte». El escaneo la desmintió con MO: el corte de
EDGAR traía los ingresos con impuestos especiales, y su margen operativo bajaba del 53,6 % al 47 %, otra cifra doble.

## Pruebas y golden

- Tests nuevos o reescritos en `tests/test_coherencia_f9.py`:
  - EDGAR neta con el corte: manda EDGAR.
  - EDGAR bruta, con o sin el corte: manda la neta de la fuente.
  - EDGAR neta sin el corte: manda la fuente.
  - Concepto parcial (CPT).
  - Diferencia no material (SHEL).
- `tests/test_f10_cifras_unicas.py`: IVZ y TKO con su corte.
- Suite: **6561 passed, 26 skipped, 0 failed**.
- Golden: **sin cambios**. Ninguna empresa del panel ni del juego local tiene una diferencia material en el último
  ejercicio.

La regla de cordura `una_definicion_ttm_fy` se alinea con la de la corrección: el umbral material y el último ejercicio
de los estados. D y EXE tenían la diferencia en 2023, no en el último ejercicio, y no mezclaban.

## Efecto en el universo

Escaneo de las 543 con este código (caché `2026-11-04-f11-p2b`, 0 errores), frente al del paso 1 (`2026-11-04-f11-p1`):

| Regla | Paso 1 | Paso 2 |
|---|---:|---:|
| `una_definicion_ttm_fy` (N2) | 35 | **0** |
| `cifra_unica` | 3 | **0** (con el tope del paso 1 afinado) |
| `margen_operativo_unico` | 0 | 0 (llegó a 1, MO, con la primera versión) |
| Resto | — | sin cambios atribuibles |

**La regla se aplica a 19 empresas.** Sus cambios, uno por uno:

| Empresa | Calidad | Precio | Por qué |
|---|---|---|---|
| BBVA | 76 → **86** | 46 | **Fallo oculto que desaparece:** con la partida de EDGAR (0,36 B) como «ingresos», el ratio de eficiencia salía en 4.614,6 % y restaba 3. Ahora 37,0 % (+3). Crecimiento 9,0 % → 12,0 % |
| NU | 83 → 80 | 31 → 38 | Ingresos netos (la definición de un banco). El año base 2022 es anómalo (36 % de la mediana) y la serie larga de EDGAR es de otra definición: **crecimiento no significativo** (F10), antes 48,8 %. Cumple el criterio del revisor (no puntúa por encima del 49 %). El precio sube por la confianza «baja», que acerca la nota a 50 |
| IBKR | 78 → 71 | 31 | Lo mismo: crecimiento «no significativo», antes 23,2 % con la serie mezclada |
| MO | 77 → 82 | 48 → 54 | Ingresos sin impuestos especiales en todo (la primera versión le metía los brutos de EDGAR en el corte) |
| ING | 52 → 60 | 50 → 45 | Crecimiento −5,5 % → +6,6 % con una sola definición |
| WMB | 44 → 48 | 42 → 39 | Crecimiento −5,7 % → +2,9 % |
| HAS | 66 → 65 | 38 → 50 | Crecimiento +5,1 % → −7,1 % (la caída real de sus ingresos netos) |
| RJF | 65 → 62 | 65 → 61 | Crecimiento 12,1 % → 8,5 %: «sólida · atractivo» → «media · razonable» |
| BF-B, RSG, DEO, CNQ, APO | ±0–4 | ±0–7 | Crecimiento recalculado con la definición neta. APO: 34,9 %, la cifra de su gráfica |
| CPT, ARES, BX, MUFG, SMFG, TDG | sin cambio de nivel | | Su crecimiento ya no puntuaba o no cambia de banda |

Los demás cambios de precio y confianza entre los dos escaneos son de empresas a las que no se aplica la regla. Son
umbrales cruzados por el mercado entre las dos corridas, como en el paso 1.

**Para el usuario:** NU e IBKR pierden la puntuación de crecimiento («no significativo») porque su base es anómala y la
única serie larga, la de EDGAR, tiene otra definición. Es la consecuencia honesta de no mezclar definiciones. Si se
quisiera puntuarlo, haría falta una serie larga neta de una fuente gratuita, que hoy no existe.
