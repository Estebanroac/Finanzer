# F5prep — Muestra para el planificador: serie de precios, beta propia y señales técnicas

> Rama `fiabilidad/f5-prep` (worktree `../finanzer_next-f5prep`, desde `main` = `8ed57a0`), **sin push ni merge**.
> Módulos **aislados**: `backend/lib/price_series.py` y `backend/lib/market_signals.py`. No los importa el motor,
> la web ni el PDF (lo comprueba `test_modules_are_isolated_from_the_engine`). **Ninguna salida de la app cambia**:
> 0 golden tocados.
>
> Captura: 36 tickers el **2026-10-15 a las 16:30 de Nueva York** (después del cierre), en una sola sesión, en
> serie (concurrencia 1, pausa de 1 s entre tickers), yfinance 1.7.0, `history(period="5y", auto_adjust=True)`.
> Fixtures en `backend/tests/fixtures/prices/` (2.5 MB, 48 series: 36 empresas + ^GSPC + 11 ETF). Las tablas
> salen de `backend/tests/f5prep_muestra.py` (replay sin red).

## 0. Resumen

- Las 36 series en estado `ok`: sin huecos frente al calendario de ^GSPC, sin saltos de split sin ajustar y las
  tres series de cada ticker acaban en la misma sesión (2026-10-15). RIVN tiene 1237 sesiones porque salió a bolsa
  en noviembre de 2021 (historia corta, no hueco).
- **Contraste independiente** en AAPL, JPM, XOM, NVO y PLTR: las 9 señales (momentum, tendencia y pendiente,
  volatilidad, drawdown de 1 y 3 años con sus fechas, fuerza relativa de 6 y 12 meses, volumen z, rango de 52
  semanas, beta cruda y R²) recalculadas con numpy y bucles de Python, sin reusar el módulo: coinciden con una
  tolerancia relativa de **1e-9**, y las fechas de pico y valle son idénticas.
- **Beta frente a la 2a:** (a) el método de la 2a, copiado tal cual de `beta_ref.py` (f8f13df), sobre la misma serie
  da la misma beta en los 31 tickers comunes (tolerancia 1e-12); (b) frente a los números que dejó la 2a (11:44,
  intradía), diferencia **mediana 0.004, máxima 0.011** (SNOW): solo cambia la última de 104 semanas (intradía
  frente a cierre).
- **Beta propia frente a Finnhub:** diferencia mediana **0.30**; 15 de 31 difieren más de 0.3 y 8 más de 0.5. Los
  mismos órdenes que midió la 2a. **BCS 1.25 frente a 1.64** y **NVO 1.11 frente a 1.96** (Finnhub en ADR).
- **Latencia:** 0.60 s por ticker (mediana) para las tres series en frío; 0.23 s solo la de la empresa. Cabe en
  un análisis (hoy 3–46 s). Propuesta: caché diaria (abajo).
- Pruebas: `pytest tests/test_price_series.py tests/test_market_signals.py` → 142 passed; suite completa en el
  registro (`F5PREP_REGISTRO.md`).

## 1. Señales de los 36

Definiciones (parámetros en `config/market.toml`; ninguna puntúa):

- **Momentum 12-1:** P(t−21) / P(t−252) − 1 (Jegadeesh y Titman, 1993; Asness, Moskowitz y Pedersen, 2013).
- **Tendencia:** precio frente a la media de 200 sesiones (MM200) y pendiente de la MM200 en 21 sesiones (Faber,
  2007; Moskowitz, Ooi y Pedersen, 2012). Régimen: alcista (por encima y subiendo), bajista (por debajo y bajando),
  lateral (el resto).
- **Volatilidad 1a:** desviación de las rentabilidades diarias logarítmicas de 252 sesiones, anualizada (√252).
- **Drawdown:** mayor caída desde un máximo previo dentro de 1 y 3 años, con fechas de pico y valle.
- **Fuerza relativa (FR):** rentabilidad de la empresa menos la del ETF de su sector, en 126 y 252 sesiones
  comunes. ETF de `sector_profiles` (`sector_info.sector_etf`).
- **Volumen z:** (media de 5 sesiones − media de las 90 anteriores) / desviación de esas 90 (Gervais, Kaniel y
  Mingelgrin, 2001); la referencia no se solapa con la ventana reciente.
- **Rango 52s:** posición del cierre de hoy entre el mínimo y el máximo de 252 sesiones, **incluida la de hoy**
  (criterio de la fase 1). Usa cierres ajustados, no máximos y mínimos intradía: puede diferir algo del rango
  que publica Yahoo.

Fuera, por PLAN §2.2: RSI, MACD, figuras chartistas y Fibonacci (lo comprueba un test).

| Ticker | Serie | Momentum 12-1 | Precio vs MM200 | Pendiente MM200 (21 s.) | Régimen | Volatilidad 1a | Drawdown 1a (pico → valle) | Drawdown 3a | ETF | FR 6m | FR 12m | Volumen z | Rango 52s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AAPL | ok | +34.7% | +17.2% | +2.2% | alcista | +24% | -14% (2025-12-02 → 2026-01-20) | -33% | XLK | +5.3% | +3.4% | -0.43 | 99% |
| MSFT | ok | -3.7% | +24.4% | +0.9% | alcista | +32% | -34% (2025-10-28 → 2026-06-25) | -34% | XLK | +4.1% | -29.2% | -0.54 | 98% |
| KO | ok | +33.6% | +15.0% | +2.5% | alcista | +19% | -8% (2026-02-27 → 2026-04-22) | -16% | XLP | +16.0% | +27.3% | -0.33 | 100% |
| PG | ok | +1.5% | +7.1% | +0.6% | alcista | +20% | -16% (2026-02-27 → 2026-06-03) | -21% | XLP | +3.5% | -4.2% | 0.09 | 74% |
| JNJ | ok | +43.2% | +4.6% | +2.6% | alcista | +20% | -11% (2026-03-02 → 2026-05-08) | -14% | XLV | -12.7% | +9.1% | 0.77 | 74% |
| JPM | ok | +17.1% | +5.1% | +0.8% | alcista | +22% | -15% (2026-01-06 → 2026-03-27) | -24% | XLF | +2.3% | +7.8% | 0.14 | 67% |
| BAC | ok | +18.1% | -5.6% | +0.2% | lateral | +23% | -20% (2026-08-12 → 2026-10-14) | -28% | XLF | -9.4% | -0.0% | 1.73 | 30% |
| PGR | ok | -3.9% | +2.6% | -0.1% | lateral | +27% | -16% (2025-10-14 → 2026-05-29) | -30% | XLF | -1.8% | -10.8% | 0.42 | 53% |
| V | ok | +7.3% | +18.2% | +1.1% | alcista | +22% | -17% (2026-01-06 → 2026-03-27) | -20% | XLF | +20.4% | +10.2% | -0.11 | 100% |
| BRK-B | ok | +4.8% | +6.5% | +0.2% | alcista | +15% | -9% (2025-11-28 → 2026-04-22) | -15% | XLF | +3.7% | +0.5% | -0.20 | 94% |
| O | ok | +2.0% | -8.1% | +0.0% | lateral | +17% | -19% (2026-03-02 → 2026-10-07) | -19% | VNQ | -9.5% | -6.3% | 0.98 | 18% |
| PLD | ok | +19.5% | -6.8% | +0.5% | lateral | +21% | -15% (2026-07-16 → 2026-10-15) | -31% | VNQ | -7.1% | +7.5% | 0.41 | 30% |
| AMT | ok | -2.6% | +4.6% | -0.0% | lateral | +28% | -16% (2026-06-05 → 2026-07-06) | -28% | VNQ | +5.8% | -4.7% | 1.19 | 70% |
| NEE | ok | -2.3% | -8.5% | -0.3% | bajista | +21% | -22% (2026-04-30 → 2026-09-28) | -24% | XLU | -3.8% | +2.5% | -0.71 | 17% |
| DUK | ok | -4.6% | -3.0% | +0.1% | lateral | +16% | -14% (2026-03-16 → 2026-09-24) | -14% | XLU | +2.9% | +2.8% | -0.25 | 39% |
| XOM | ok | +49.7% | +16.4% | +3.6% | alcista | +26% | -20% (2026-03-30 → 2026-06-29) | -20% | XLE | -2.7% | +1.5% | -0.80 | 97% |
| FCX | ok | +66.7% | +8.7% | +4.2% | alcista | +47% | -24% (2026-02-25 → 2026-03-20) | -46% | XLB | +4.3% | +53.2% | -0.95 | 76% |
| CAT | ok | +49.7% | -8.4% | +3.0% | lateral | +40% | -31% (2026-06-30 → 2026-10-15) | -34% | XLI | -3.5% | +29.9% | 0.04 | 41% |
| MU | ok | +395.8% | +30.3% | +13.0% | alcista | +80% | -39% (2026-06-25 → 2026-07-29) | -58% | XLK | +79.0% | +363.3% | -0.71 | 72% |
| DOW | ok | +44.0% | -6.4% | +1.9% | lateral | +43% | -35% (2026-03-30 → 2026-07-01) | -62% | XLB | -22.6% | +26.5% | -1.01 | 46% |
| PLTR | ok | -3.0% | +31.4% | +0.6% | alcista | +58% | -48% (2025-11-03 → 2026-06-25) | -48% | XLK | +15.7% | -23.6% | -0.52 | 92% |
| NVDA | ok | +19.1% | +7.3% | +2.5% | alcista | +37% | -20% (2025-10-29 → 2026-03-30) | -37% | XLK | -15.0% | -14.1% | -0.94 | 70% |
| CRWD | ok | +97.5% | +52.8% | +9.7% | alcista | +54% | -37% (2025-11-10 → 2026-02-24) | -44% | XLK | +109.2% | +65.0% | -0.53 | 82% |
| RIVN | ok | +16.1% | -17.9% | -2.8% | bajista | +69% | -43% (2025-12-19 → 2026-05-19) | -66% | XLY | -19.7% | +1.7% | -0.42 | 5% |
| SNOW | ok | +37.4% | +43.5% | +5.3% | alcista | +62% | -56% (2025-11-03 → 2026-04-10) | -56% | XLK | +108.7% | +4.0% | -0.05 | 86% |
| TSM | ok | +42.6% | +7.5% | +4.5% | alcista | +39% | -22% (2026-06-30 → 2026-07-29) | -37% | XLK | -7.9% | +9.1% | 0.14 | 70% |
| ASML | ok | +64.0% | +5.5% | +4.7% | alcista | +46% | -22% (2026-06-30 → 2026-07-29) | -45% | XLK | -6.9% | +34.6% | 0.06 | 68% |
| NVO | ok | -22.7% | -11.2% | -1.8% | bajista | +46% | -44% (2026-01-26 → 2026-03-27) | -75% | XLV | -24.8% | -53.9% | -0.37 | 18% |
| NFLX | ok | -37.1% | -12.5% | -3.3% | bajista | +37% | -46% (2025-10-21 → 2026-10-02) | -50% | XLC | -27.8% | -39.6% | -0.41 | 10% |
| AMZN | ok | +13.7% | +5.0% | +1.1% | alcista | +34% | -22% (2025-11-03 → 2026-02-13) | -31% | XLY | +5.2% | +20.2% | -0.49 | 66% |
| SPY | ok | +14.8% | +7.0% | +1.4% | alcista | +13% | -9% (2026-01-27 → 2026-03-30) | -19% | SPY | +0.0% | +0.0% | -1.09 | 95% |
| BCS | ok | +26.9% | -8.0% | +0.1% | lateral | +31% | -26% (2026-02-03 → 2026-03-20) | -26% | XLF | -8.8% | +8.8% | 0.57 | 42% |
| HSBC | ok | +57.8% | +3.0% | +3.0% | alcista | +27% | -16% (2026-02-26 → 2026-03-20) | -22% | XLF | -1.4% | +42.5% | 0.72 | 71% |
| SHEL | ok | +38.5% | +21.2% | +3.4% | alcista | +23% | -18% (2026-04-07 → 2026-06-26) | -18% | XLE | -4.0% | -8.6% | -0.03 | 100% |
| UL | ok | -5.9% | +4.7% | -0.3% | lateral | +24% | -25% (2026-02-13 → 2026-04-02) | -25% | XLP | +7.0% | -15.2% | -0.27 | 56% |
| TM | ok | +0.2% | -4.0% | -1.0% | bajista | +26% | -33% (2026-02-13 → 2026-06-25) | -35% | XLY | -6.6% | +2.5% | -0.70 | 31% |

SPY frente a sí mismo (sin sector) da FR 0: es el caso trampa del panel, no un dato.

## 2. Beta propia frente a Finnhub (y frente a la referencia de la 2a)

Beta propia: MCO de 104 rentabilidades **semanales** (cierre ajustado del viernes) frente a **^GSPC**, cruda y
ajustada por Blume con los coeficientes de `valuation.capm` (0.67 × β + 0.33), con R² y nº de semanas. ADR:
frente al S&P 500 con el precio del ADR en dólares (perspectiva del inversor en dólares, la del CAPM del
motor). Finnhub: `beta.raw` del golden del panel (`data_provenance.fields.beta.source` = finnhub). HSBC, SHEL,
UL y TM aún no tienen golden.

| Ticker | Propia cruda | Propia Blume | R² | Semanas | Finnhub (golden) | Fuente | Propia − Finnhub | Ref. 2a | Propia − 2a |
|---|---|---|---|---|---|---|---|---|---|
| AAPL | 1.06 | 1.04 | 0.30 | 104 | 1.11 | finnhub | -0.05 | 1.05 | +0.003 |
| MSFT | 1.13 | 1.09 | 0.30 | 104 | 1.06 | finnhub | +0.06 | 1.13 | +0.001 |
| KO | 0.12 | 0.41 | 0.01 | 104 | 0.29 | finnhub | -0.18 | 0.11 | +0.006 |
| PG | 0.24 | 0.49 | 0.05 | 104 | 0.39 | finnhub | -0.15 | 0.24 | +0.006 |
| JNJ | -0.00 | 0.33 | 0.00 | 104 | 0.20 | finnhub | -0.20 | -0.01 | +0.005 |
| JPM | 1.09 | 1.06 | 0.45 | 104 | 1.04 | finnhub | +0.05 | 1.09 | +0.000 |
| BAC | 1.15 | 1.10 | 0.40 | 104 | 1.20 | finnhub | -0.05 | 1.15 | -0.004 |
| PGR | 0.44 | 0.62 | 0.07 | 104 | 0.23 | finnhub | +0.20 | 0.43 | +0.005 |
| V | 0.77 | 0.84 | 0.30 | 104 | 0.83 | finnhub | -0.06 | 0.76 | +0.002 |
| BRK-B | 0.40 | 0.60 | 0.14 | 104 | 0.18 | finnhub | +0.22 | 0.40 | +0.004 |
| O | 0.17 | 0.44 | 0.02 | 104 | 0.66 | finnhub | -0.49 | 0.16 | +0.005 |
| PLD | 0.74 | 0.83 | 0.22 | 104 | 1.31 | finnhub | -0.57 | 0.74 | +0.004 |
| AMT | 0.06 | 0.37 | 0.00 | 104 | 0.89 | finnhub | -0.82 | 0.06 | +0.002 |
| NEE | 0.25 | 0.50 | 0.03 | 104 | 0.63 | finnhub | -0.38 | 0.25 | +0.000 |
| DUK | -0.12 | 0.25 | 0.01 | 104 | 0.33 | finnhub | -0.45 | -0.12 | +0.003 |
| XOM | -0.02 | 0.32 | 0.00 | 104 | 0.18 | finnhub | -0.20 | -0.02 | +0.002 |
| FCX | 1.67 | 1.45 | 0.30 | 104 | 1.37 | finnhub | +0.30 | 1.67 | -0.003 |
| CAT | 1.07 | 1.05 | 0.25 | 104 | 1.59 | finnhub | -0.52 | 1.07 | -0.006 |
| MU | 2.51 | 2.01 | 0.29 | 104 | 2.37 | finnhub | +0.14 | 2.52 | -0.010 |
| DOW | 0.60 | 0.73 | 0.05 | 104 | 0.45 | finnhub | +0.15 | 0.59 | +0.007 |
| PLTR | 2.47 | 1.98 | 0.26 | 104 | 1.63 | finnhub | +0.84 | 2.47 | -0.003 |
| NVDA | 1.85 | 1.57 | 0.48 | 104 | 2.25 | finnhub | -0.40 | 1.85 | -0.001 |
| CRWD | 1.63 | 1.42 | 0.24 | 104 | 1.14 | finnhub | +0.49 | 1.64 | -0.008 |
| RIVN | 1.04 | 1.03 | 0.08 | 104 | 1.62 | finnhub | -0.58 | 1.05 | -0.005 |
| SNOW | 1.49 | 1.33 | 0.13 | 104 | 1.34 | finnhub | +0.15 | 1.50 | -0.011 |
| TSM | 1.43 | 1.29 | 0.45 | 104 | 0.95 | finnhub | +0.48 | 1.44 | -0.004 |
| ASML | 1.24 | 1.16 | 0.27 | 104 | 2.09 | finnhub | -0.85 | 1.24 | -0.004 |
| NVO **←** | 1.11 | 1.08 | 0.10 | 104 | 1.96 | finnhub | -0.85 | 1.11 | +0.005 |
| NFLX | 0.92 | 0.95 | 0.15 | 104 | 1.61 | finnhub | -0.68 | 0.92 | +0.003 |
| AMZN | 1.48 | 1.32 | 0.44 | 104 | 1.52 | finnhub | -0.04 | 1.48 | -0.002 |
| SPY | 1.00 | 1.00 | 1.00 | 104 | — | — | — | — | — |
| BCS **←** | 1.25 | 1.16 | 0.41 | 104 | 1.64 | finnhub | -0.39 | 1.24 | +0.004 |
| HSBC | 0.77 | 0.85 | 0.23 | 104 | — | — | — | — | — |
| SHEL | 0.04 | 0.36 | 0.00 | 104 | — | — | — | — | — |
| UL | -0.01 | 0.32 | 0.00 | 104 | — | — | — | — | — |
| TM | 0.72 | 0.81 | 0.15 | 104 | — | — | — | — | — |

|propia − Finnhub|: mediana 0.30, > 0.3 en 15 de 31, > 0.5 en 8.
|propia − ref. 2a|: mediana 0.0037, máx. 0.0113 (31 tickers).

Lecturas para la 2b (sin decidir nada aquí):

- **BCS y NVO**, las dos con 1.64 / 1.96 de Finnhub: la propia da 1.25 y 1.11. El 1.64 de BCS no se reproduce con
  2 años semanales frente al S&P 500 (R² 0.41, bien determinada).
- **R² < 0.1** (el mercado explica menos del 10% de los movimientos semanales) en 14 de 36: KO, PG, JNJ, PGR, O,
  AMT, NEE, DUK, XOM, DOW, RIVN, SHEL, UL y NVO (0.098). Son las betas casi nulas o negativas (JNJ −0.00, DUK −0.12,
  XOM −0.02, UL −0.01). F2_PRECEDENCIA §5 propone en esos casos la beta del sector: este módulo devuelve el R² y
  el nº de semanas para aplicarlo; la sustitución no se hace aquí.
- **UL:** la escisión de Magnum (2025-12-08) aparece en Yahoo como un "split" de 0.888 el 2025-12-09; el cierre
  ajustado cae un 7.0% el día 8 y sube un 2.8% el 9. Entra en la ventana de la beta (1 semana de 104) y en el
  drawdown de 1 año no es el valle. `price_series` lista los eventos de split de Yahoo como información
  (`splits`); un ratio no entero es la pista de una escisión.

## 3. Latencia

Captura local (IP residencial), en frío, en serie, tres series por ticker:

| Ticker | Empresa (s) | ^GSPC (s) | ETF (s) | Total (s) |
|---|---|---|---|---|
| AAPL | 0.27 | 0.82 | 0.21 | 1.30 |
| MSFT | 0.22 | 0.21 | 0.12 | 0.56 |
| KO | 0.32 | 0.22 | 0.23 | 0.77 |
| PG | 0.23 | 0.12 | 0.18 | 0.53 |
| JNJ | 0.28 | 0.14 | 0.20 | 0.63 |
| JPM | 0.24 | 0.13 | 0.31 | 0.69 |
| BAC | 0.21 | 0.15 | 0.12 | 0.49 |
| PGR | 0.22 | 0.25 | 0.12 | 0.60 |
| V | 0.21 | 0.19 | 0.12 | 0.52 |
| BRK-B | 0.29 | 0.13 | 0.11 | 0.53 |
| O | 0.33 | 0.15 | 0.29 | 0.78 |
| PLD | 0.34 | 0.23 | 0.20 | 0.77 |
| AMT | 0.27 | 0.14 | 0.14 | 0.55 |
| NEE | 0.23 | 0.15 | 0.26 | 0.63 |
| DUK | 0.21 | 0.29 | 0.12 | 0.62 |
| XOM | 0.33 | 0.13 | 0.20 | 0.66 |
| FCX | 0.45 | 0.22 | 0.23 | 0.90 |
| CAT | 0.25 | 0.14 | 0.20 | 0.59 |
| MU | 0.24 | 0.13 | 0.24 | 0.61 |
| DOW | 0.18 | 0.12 | 0.13 | 0.44 |
| PLTR | 0.21 | 0.15 | 0.21 | 0.56 |
| NVDA | 0.33 | 0.22 | 0.12 | 0.67 |
| CRWD | 0.18 | 0.12 | 0.14 | 0.44 |
| RIVN | 0.22 | 0.14 | 0.20 | 0.56 |
| SNOW | 0.29 | 0.14 | 0.13 | 0.57 |
| TSM | 0.21 | 0.13 | 0.20 | 0.55 |
| ASML | 0.24 | 0.14 | 0.19 | 0.57 |
| NVO | 0.26 | 0.15 | 0.21 | 0.62 |
| NFLX | 0.21 | 0.28 | 0.18 | 0.67 |
| AMZN | 0.20 | 0.17 | 0.12 | 0.49 |
| SPY | 0.52 | 0.21 | 0.52 | 0.74 |
| BCS | 0.21 | 0.23 | 0.20 | 0.64 |
| HSBC | 0.20 | 0.21 | 0.12 | 0.53 |
| SHEL | 0.34 | 0.20 | 0.20 | 0.75 |
| UL | 0.22 | 0.17 | 0.21 | 0.60 |
| TM | 0.23 | 0.12 | 0.19 | 0.54 |

Total por ticker (tres series): mediana 0.60 s, máx. 1.30 s, suma 22.7 s. Solo la serie de la empresa: mediana 0.23 s, máx. 0.52 s.

En SPY la empresa y el ETF son la misma descarga (se cuenta en las dos columnas).

**¿Cabe en un análisis?** Sí: +0.6 s en frío sobre un análisis de 3–46 s, y 0.2 s si ^GSPC y el ETF ya están en
caché. **Propuesta para la fase 5:** caché diaria. ^GSPC y los 11 ETF (12 símbolos compartidos por todos los
tickers) se descargan una vez por sesión, después del cierre; la serie de la empresa se guarda hasta el siguiente
cierre. **Sin verificar desde Render** (RECON C8): Yahoo responde 401 a `quoteSummary` desde Render; `history` usa
otro endpoint (`chart`), que el plan B no usa hoy. Hay que medirlo allí antes de construir (fase 6).

## 4. Tres lecturas de ejemplo (tono, sin recomendación)

> **NVO.** Cotiza un 11% por debajo de su media de 200 sesiones, y esa media baja (−1.8% en el último mes). En los
> últimos tres años llegó a caer un 75% desde su máximo. En los últimos 12 meses rindió 54 puntos menos que el ETF
> de salud (XLV).

> **CAT.** Entre hace 12 meses y hace un mes subió un 50%, pero hoy cotiza un 8% por debajo de su media de 200
> sesiones: desde el máximo del 30 de junio cae un 31%, y el punto más bajo de esa caída es la sesión de hoy.

> **KO.** Cotiza en el máximo de su rango de 52 semanas y un 15% por encima de su media de 200 sesiones. Su mayor
> caída del último año fue del 8%. Se mueve poco con el mercado: el S&P 500 explica el 1% de sus movimientos
> semanales (R² 0.01), así que su beta cruda (0.12) dice poco.

## 5. Para decidir (el operador no lo aplica)

1. **Umbral de salto (posible split sin ajustar): 0.8 en lugar de 0.5.** Con la lectura simétrica del "50%" del
   prompt (max(p1/p0, p0/p1) − 1 > 0.5), la caída real de NFLX del 2022-04-20 (−35.1%, resultados) salía
   "sospechosa" y bloqueaba sus señales; un "50%" de un solo sentido no detecta un 2:1 (−50% exacto, menos si ese
   día sube). Con 0.8 se marca una caída ≥ 44% o una subida ≥ 80%: un 2:1 (magnitud 1.0) se detecta con margen y el
   mayor movimiento real de los 36 (NFLX, 0.54) no. Está en `config/market.toml`.
2. **Una serie `sospechosa` no alimenta señales** (devuelven `sin_dato` con el motivo); con `max_missing_days = 0`,
   un solo día sin cotización basta. En los 36 no ocurre; en la fase 5 habría que decidir si un hueco aislado se
   tolera.
3. **Escisiones** registradas como split (UL): hoy solo se listan. ¿Bloquean la beta o el drawdown?
4. **Config en un archivo nuevo** (`config/market.toml`, sección `[market.*]` al final de `schema.toml` y `"market"`
   en `settings.FILES`), para no chocar con la 2b y F3prep en `valuation.toml`. Al fusionar, una línea de
   `settings.py` y el final de `schema.toml` pueden necesitar resolver un conflicto trivial.
