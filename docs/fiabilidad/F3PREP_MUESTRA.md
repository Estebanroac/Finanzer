# Preparación de la fase 3 · Muestra del DCF inverso y del ROTE implícito sobre el panel

*Operador F3prep, 2026-10-15, rama `fiabilidad/f3-prep` (desde `main` = `8ed57a0`). **Es una muestra para el
planificador, no un cambio del motor:** `lib/reverse_dcf.py` y `lib/bank_implied.py` no están conectados a nada y
ninguna salida de la app cambia. Especificación: `F3_DISENO_METODO.md` §2 y §3.*

**Cómo se generó** (sin red, replay de los fixtures `panel`, capturados con `--render-sim` el 14-oct-2026 tras el
cierre; BCS el 15-oct):

```bash
cd backend && ../.venv313/bin/python tests/f3prep_muestra.py
```

Las entradas del DCF inverso son **las del DCF directo del motor** para cada ticker (FCF base, acciones, WACC, deuda
neta): el script lo comprueba reproduciendo al céntimo el valor razonable que publicó el motor antes de calcular g\*
(un `assert` por ticker). Estructura del inverso: g\* en los años 1–5, convergencia lineal al 2.5% terminal en los
años 6–10, Gordon y puente al equity con la deuda neta. Bisección entre −20% y +60%.

## 1. Crecimiento que exige el precio (g\*) frente al logrado

Columnas:
- **g\***: crecimiento anual del FCF por acción que exige el precio.
- **CAGR FCF 3a (motor)**: la fila "Crecimiento FCF…" que ya puntúa Crecimiento: por acción si aplica la regla de
  dilución o en REIT, FCF − SBC en pre-beneficio; las cíclicas no la tienen.
- **Banda**: `classify_implied_growth` con ± 5 pp, **sin tasas base** (las aporta la fase 3).
- **g del DCF directo (decay → step)**: el crecimiento que usa el DCF directo, su tipo de decaimiento y el g\*
  equivalente en la estructura del inverso (g\* con precio = valor razonable del motor).
- **g\* con FCF − SBC**: la misma resolución con la base de §2.2, donde la base del DCF es el FCF TTM.

| Ticker | Arquetipo | Precio | FCF/acc. base | WACC | Deuda neta/acc. | g* | Estado | CAGR FCF 3a (motor) | Banda | g del DCF directo (decay → step) | Upside DCF directo | g* con FCF − SBC (SBC/ingresos) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AAPL | MATURE | 342.96 | 9.37 | +9.70% | 1.50 | **+20.0%** | ok | -3.9% | exigente | +1.8% step → +1.8% | -63% | +22.0% (3% de ingr.) |
| MSFT | MATURE | 533.69 | 9.02 | +9.60% | -2.67 | **+28.7%** | ok | +4.0% | exigente | +16.1% linear → +12.8% | -56% | +32.8% (4% de ingr.) |
| KO | MATURE | 91.78 | 3.32 | +7.23% | 6.32 | **+7.7%** | ok | -17.8% | exigente | +3.7% step → +3.7% | -23% | +8.1% (1% de ingr.) |
| PG | MATURE | 156.53 | 6.52 | +7.48% | 10.80 | **+6.3%** | ok | +3.2% | en_precio | +2.0% step → +2.0% | -24% | +6.9% (1% de ingr.) |
| JNJ | MATURE | 253.91 | 9.22 | +7.04% | 11.73 | **+6.6%** | ok | +4.0% | en_precio | +5.6% step → +5.6% | -6% | +7.7% (1% de ingr.) |
| V | MATURE | 391.43 | 11.19 | +8.87% | 5.36 | **+16.7%** | ok | +6.5% | exigente | +10.9% step → +10.9% | -27% | +17.5% (2% de ingr.) |
| O | REIT | 55.17 | 4.40 | +7.59% | 32.37 | **+2.3%** | ok | +3.3% | en_precio | no aplica (no_aplica) | — | +2.4% (1% de ingr.) |
| PLD | REIT | 130.57 | 5.51 | +9.27% | 36.49 | **+15.0%** | ok | +6.4% | exigente | no aplica (no_aplica) | — | +15.8% (2% de ingr.) |
| AMT | REIT | 179.40 | 8.50 | +7.89% | 92.75 | **+11.6%** | ok | +27.4% | barata | no aplica (no_aplica) | — | +12.3% (2% de ingr.) |
| NEE | UTILITY | 78.37 | 1.46 | +7.46% | 51.45 | **+28.6%** | ok | — | sin_contraste | no aplica (no_aplica) | — | — |
| DUK | UTILITY | 119.64 | -5.48 | +6.70% | 117.39 | **—** | no_aplica | — | — | no aplica (no_aplica) | — | — |
| XOM | CYCLICAL | 177.06 | 9.16 | +7.01% | 7.73 | **+0.5%** | ok | — | sin_contraste | -5.0% step → -5.0% | -30% | — |
| FCX | CYCLICAL | 69.61 | 2.54 | +9.91% | 4.37 | **+16.1%** | ok | — | sin_contraste | +4.5% step → +4.5% | -50% | — |
| CAT | MATURE | 748.98 | 19.57 | +10.35% | 83.61 | **+24.7%** | ok | +13.0% | exigente | +4.4% step → +4.4% | -73% | — |
| MU | CYCLICAL | 914.13 | 2.62 | +13.29% | -17.36 | **—** | fuera_de_rango (superior) | — | — | +10.0% step → +10.0% | -94% | — |
| DOW | CYCLICAL | 29.19 | 2.32 | +7.17% | 21.72 | **+2.5%** | ok | — | sin_contraste | -5.0% step → -5.0% | -64% | — |
| PLTR | MATURE | 200.97 | 1.40 | +11.25% | -3.83 | **+52.6%** | ok | +108.6% | barata | +27.3% exponential → +19.6% | -78% | +59.1% (14% de ingr.) |
| NVDA | MATURE | 221.30 | 5.26 | +12.96% | -1.00 | **+31.5%** | ok | +186.2% | barata | +30.0% exponential → +21.6% | -38% | +32.7% (2% de ingr.) |
| CRWD | MATURE | 249.29 | 1.49 | +9.86% | -4.10 | **+51.1%** | ok | +17.4% | exigente | +23.6% linear → +18.4% | -79% | fuera_de_rango |
| RIVN | GROWTH_PRE_PROFIT | 12.95 | -2.41 | +13.00% | 0.03 | **—** | no_aplica | — | — | no aplica (no_aplica) | — | no_aplica |
| SNOW | GROWTH_PRE_PROFIT | 335.08 | 3.38 | +10.64% | 1.19 | **+42.9%** | ok | — | sin_contraste | +28.7% exponential → +20.6% | -67% | no_aplica |
| TSM | MATURE | 430.00 | 6.95 | +9.28% | -15.32 | **+27.9%** | ok | +22.1% | exigente | +17.1% linear → +13.6% | -51% | +27.9% (0% de ingr.) |
| ASML | CYCLICAL | 1650.00 | 24.51 | +12.54% | -16.64 | **+40.2%** | ok | — | sin_contraste | +10.0% step → +10.0% | -77% | — |
| NVO | MATURE | 38.12 | 1.69 | +11.31% | 3.29 | **+16.6%** | ok | -21.5% | exigente | +23.1% linear → +18.1% | +9% | — |
| NFLX | MATURE | 70.57 | 2.68 | +10.89% | 1.24 | **+17.3%** | ok | +69.8% | barata | +12.6% step → +12.6% | -22% | +18.1% (1% de ingr.) |
| AMZN | MATURE | 254.08 | -0.23 | +10.48% | 6.19 | **—** | no_aplica | — | — | no aplica (no_significativo) | — | no_aplica |
| SPY | — | — | — | — | — | — | rechazado por el motor (422) | — | — | — | — | — |

### Lectura para el planificador

1. **Fuera de rango: solo MU** (por arriba: exige más de +60%; con el rango abierto saldría ≈ 81%). Su base es el
   FCF de mantenimiento de ciclo (2.96 mil millones, que promedia un ejercicio de −6.1 mil millones) frente a un
   FCF TTM de 26.2 mil millones: en cíclicas, la base decide el resultado. Cerca del límite: **PLTR +52.6%** y
   **CRWD +51.1%**; con FCF − SBC, PLTR +59.1% y **CRWD fuera de rango** (SBC = 23% de los ingresos).
2. **La banda frente al CAGR a 3 años no basta para el crecimiento alto.** PLTR (+108.6%), NVDA (+186.2%) y
   NFLX (+69.8%) salen `barata` porque su CAGR de 3 años parte de una base baja. Los casos por debajo son
   simétricos: KO (−17.8%), AAPL (−3.9%) y NVO (−21.5%) salen `exigente` con g\* moderados. Hacen falta, antes de
   conectar:
   - la tasa base (§2.2, `muy_exigente`): el umbral de config (10%) es **provisional**;
   - el CAGR de 5–10 años **[2b]**;
   - probablemente, también el contraste con los ingresos por acción (§2.2 lo pide; aquí solo está el FCF).
3. **El DCF directo no tiene siempre la estructura del inverso.** Por encima del 15% de crecimiento usa decaimiento
   lineal desde el año 1, y por encima del 25%, exponencial (`decay_linear_above`, `decay_exponential_above`):
   - lineal: MSFT, CRWD, TSM y NVO;
   - exponencial: PLTR, NVDA y SNOW.
   
   Su crecimiento "nominal" no es comparable con g\*. Por ejemplo, el 27.3% exponencial de PLTR equivale a un
   19.6% en la estructura del inverso. La ida y vuelta exacta solo vale en modo `step`. **Decisión de la fase 3:**
   unificar la estructura (F3_DISENO §4 ya pide convergencia en los años 6–10) o declarar la equivalencia.
4. **Tope del DCF directo (`growth_cap` = 50%) frente al límite del inverso (+60%).** Un g\* entre 50% y 60%
   (PLTR, CRWD) no lo reproduce el DCF directo, que lo recorta con un aviso. La ida y vuelta se prueba hasta el 50%.
5. **La base de FCF es la del DCF directo de hoy:**
   - FCF TTM sin restar SBC en MATURE: con FCF − SBC, MSFT sube 4 pp, PLTR 6.5 pp y CRWD sale de rango;
   - mantenimiento de ciclo en CYCLICAL;
   - FCF bruto en SNOW (GROWTH_PRE_PROFIT): con FCF − SBC (negativo) el inverso da `no_aplica`.

   §2.2 pide FCF − SBC "donde aplique": hay que fijar dónde.
6. **Deuda neta.** CAT (+24.7%) carga 83.61 por acción de deuda neta, que incluye la de su financiera cautiva: es el
   mismo sesgo que tiene hoy su DCF directo (upside −73%).
7. **Cíclicas sin contraste:** el motor no calcula el crecimiento del FCF en CYCLICAL (`sin_contraste`).
   - XOM (+0.5%) y DOW (+2.5%) exigen poco;
   - FCX (+16.1%) y ASML (+40.2%), mucho sobre el FCF de mantenimiento.
   
   El contraste de ciclo medio depende de la historia de 10+ ejercicios **[2b]**.
8. **REIT y utilities, solo informativo** (el motor no les aplica DCF). En REIT la base debería ser el FFO/AFFO, no
   el FCF. NEE sale con FCF TTM positivo pese a la regla "negativo por diseño"; DUK, negativo (`no_aplica`).
9. **Sin estados `sin_convergencia`** en el panel: todas las bisecciones convergen en 33 iteraciones (error relativo
   < 1e-8).

## 2. Bancos y aseguradoras: ROTE y ROE implícitos en el precio

`ROTE implícito = P/TBV × (Ke − g) + g` con el Ke (CAPM, beta de Blume) y la g (2.5%) del motor. "Ida y vuelta":
`implied_rote(P/TBV justificado del motor)` devuelve el ROTE del motor (diferencia < 1e-12 en los cinco).

| Ticker | Precio | Ke | g | P/TBV | ROTE motor | ROTE implícito | P/TBV justif. | ida y vuelta | P/B | ROE motor | ROE implícito | P/TBV con ROTE implícito −2 / −1 / +1 / +2 pp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JPM | 335.28 | +9.59% | +2.5% | 3.20x | +20.5% | **+25.2%** | 2.54x | exacta | 2.46x | +15.7% | +19.9% | 2.92x / 3.06x / 3.34x / 3.49x |
| BAC | 51.39 | +10.06% | +2.5% | 1.73x | +14.7% | **+15.5%** | 1.61x | exacta | 1.19x | +10.1% | +11.5% | 1.46x / 1.59x / 1.86x / 1.99x |
| PGR | 213.46 | +7.33% | +2.5% | 4.09x | +37.3% | **+22.2%** | 7.21x | exacta | 4.09x | +37.3% | +22.2% | 3.67x / 3.88x / 4.29x / 4.50x |
| BRK-B | 526.35 | +7.19% | +2.5% | 1.88x | +11.2% | **+11.3%** | 1.85x | exacta | 1.57x | +9.3% | +9.9% | 1.45x / 1.66x / 2.09x / 2.30x |
| BCS | 22.84 | +11.28% | +2.5% | 0.81x | +10.1% | **+9.6%** | 0.87x | exacta | 0.73x | +9.0% | +8.9% | 0.59x / 0.70x / 0.93x / 1.04x |

### Lectura para el planificador

- **JPM:** el precio descuenta un ROTE sostenido del 25.2%, frente al 20.5% que obtiene: cotiza por encima de su
  justificado (3.20x frente a 2.54x).
- **BAC** (15.5% frente a 14.7%) y **BRK-B** (11.3% frente a 11.2%): en precio.
- **BCS:** 9.6% con el Ke del motor (11.28%). El ejemplo de §3 (Ke 11.0%) da 9.4%: el test lo reproduce
  (0.09385). Frente al 10.1% contable, que no está ajustado por AT1 **[2b]**.
- **PGR:** el precio descuenta un 22.2% frente a un ROE del 37.3%. En una aseguradora ese ROE es de un año bueno
  del ciclo de suscripción, así que la lectura necesita el ROE medio (fase 3, subtipo aseguradora). P/TBV = P/B
  porque los datos no traen intangibles.
- La sensibilidad de ±2 pp da la frase de §3. Por ejemplo, en BCS: "con un ROTE del 11.6% se justificaría 1.04x".

## 3. Pruebas (resumen; detalle en `F3PREP_REGISTRO.md`)

- **Ida y vuelta con el DCF directo** (`tests/test_reverse_dcf.py`), en **KO, JNJ, XOM, AAPL y PG**:
  - las entradas del golden reproducen al céntimo el DCF del motor (modo `step`);
  - para 9 crecimientos de −15% a +50%, el valor del DCF directo tomado como precio devuelve g con error < 1e-8;
  - las tasas año a año coinciden con las del DCF directo;
  - el valor razonable publicado por el motor devuelve el crecimiento que usó (< 1e-4, por el redondeo al
    céntimo).
- **Contraste independiente:** otro cálculo escrito aparte (vector de tasas explícito, factores de descuento
  acumulados) y otro método de raíz (secante), en 3 casos:
  - (FCF 5, WACC 9%, g 2.5%, precio 120);
  - (FCF 2, WACC 10%, g 3%, deuda neta 10, precio 60);
  - el caso analítico de Gordon (precio = 1.02 / 0.06 ⇒ g\* = 2% exacto).

  Coincide con error < 1e-8.
- **ROTE:**
  - el ejemplo de BCS de §3 da 9.385%;
  - la ida y vuelta es exacta en JPM, BAC y BCS (ROTE y ROE);
  - los casos `no_aplica` (Ke ≤ g, múltiplo ≤ 0) están cubiertos.
