# Prompt del operador — Preparación de las fases 2b y 5: serie de precios, beta propia y señales técnicas (módulos aislados)

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`. **Trabaja en un worktree aparte**: en paralelo hay otro operador
> en la rama `fiabilidad/f2a-medir`.

---

Eres el **operador de F5prep** del plan de fiabilidad de Finanzer. Construyes, **aislados y sin conectar a nada**:

1. la ingesta de la **serie diaria de precios** (empresa, S&P 500 y ETF de su sector);
2. la **beta propia** (la usará la fase 2b en lugar de la de Finnhub);
3. las **señales técnicas con evidencia** que usará la fase 5 como contexto (nunca como puntuación).

No tocas `main.py`, `yf_adapter.py`, `finnhub_fallback.py`, `currency.py`, `validate.py`, `verdict.py`,
`display.py`, el PDF, la web, `tests/fixtures/panel/` ni `tests/golden/`. **Ninguna salida de la app cambia.**

## 1. Contexto (lee antes de tocar nada)

**Los documentos de planificación están sin commitear en la carpeta principal** y no aparecerán en tu worktree. Léelos
por su ruta absoluta en `/Users/joseestebanroa/Downloads/finanzer_next/docs/`:

1. `PLAN_FIABILIDAD.md` **§2.2** (qué señales técnicas entran y cuáles no) y §2.3 (la capa conductual modula la
   confianza; nunca suma ni resta puntos).
2. `fiabilidad/BITACORA.md`: las filas de beta (BCS y NVO con 1.64 de Finnhub) y la nota de la 2a sobre su beta de
   referencia (2 años semanales frente al S&P 500; mediana de la diferencia con Finnhub 0.30; cambiaría 3 niveles).
3. `redesign-spec.md` §5 (capa conductual) y `RECON.md` §6.6 y C8 (la app no descarga hoy la serie diaria; riesgo de
   latencia y de bloqueo de Yahoo desde Render).
4. En el código (tu worktree): `backend/lib/cost_of_capital.py` (ajuste de Blume 0.67/0.33 ya existente),
   `backend/lib/sector_profiles.py` (ETF de sector: `sector_info.sector_etf`), `backend/config/` y
   `backend/tests/test_config_literals.py` (ningún literal numérico: todo a `config/*.toml` + `schema.toml`).
5. Si existe en la rama `fiabilidad/f2a-medir`, mira **sin modificarla** cómo calculó la 2a su beta de referencia
   (`git show fiabilidad/f2a-medir:<ruta>`), para que tu función dé **el mismo resultado**.

Hechos: producción y `main` = `8ed57a0`. Suite con `/Users/joseestebanroa/Downloads/finanzer_next/.venv313/bin/python`.

## 2. Tareas

### T0. Worktree
`git worktree add ../finanzer_next-f5prep -b fiabilidad/f5-prep main`.

### T1. `backend/lib/price_series.py` (ingesta, no conectada)
- Serie diaria **ajustada por splits y dividendos** (cierre ajustado y volumen) vía `yfinance` `history`, con
  periodo en config (propuesta: 5 años para cubrir drawdown de 3 años y la beta de 2).
- Para un ticker devuelve la serie de la empresa, la del **S&P 500** (`^GSPC`, o `SPY` si el índice falla; decláralo)
  y la de su **ETF de sector**.
- Robustez: reintentos limitados (config), sin secretos; si falla, estado `sin_dato` con motivo, nunca una serie
  parcial sin avisar. Comprueba huecos (días sin cotización) y saltos > 50% en un día (posible split no ajustado):
  estado `sospechosa` con la fecha.
- **Mide la latencia** local por ticker (las tres series) y anótala: la fase 5 tiene que decidir si cabe en el tiempo
  de un análisis.

### T2. Fixtures de series
- Juego nuevo y separado: `backend/tests/fixtures/prices/` (no toques `panel/`). Captura las series de los 36
  tickers del panel (los 31 + BCS + HSBC, SHEL, UL, TM; si alguno de los 4 últimos aún no está en el panel, captúralo
  igual aquí) **después del cierre de Nueva York**, en una sola sesión, con metadatos (fecha, hora, fuente, versión de
  yfinance).
- Replay sin red, como el resto de fixtures.

### T3. `backend/lib/market_signals.py` (funciones puras sobre la serie)
Solo las de PLAN §2.2, cada una con su referencia en el docstring:

| Señal | Definición | Referencia |
|---|---|---|
| Momentum 12-1 | rentabilidad de 12 meses excluyendo el último mes | Jegadeesh y Titman (1993); Asness, Moskowitz y Pedersen (2013) |
| Tendencia | precio frente a la media de 200 sesiones y pendiente de esa media | Faber (2007); Moskowitz, Ooi y Pedersen (2012) |
| Volatilidad realizada | desviación de rentabilidades diarias de 1 año, anualizada | estándar |
| Drawdown máximo | 1 año y 3 años, con fechas de pico y valle | estándar |
| Fuerza relativa | rentabilidad de 6 y 12 meses frente al ETF de su sector | extensión del momentum |
| Volumen anómalo | z-score del volumen medio de 5 sesiones frente a 90 | Gervais, Kaniel y Mingelgrin (2001) |
| Posición en el rango de 52 semanas | desde la serie (incluye el precio de hoy, criterio de la fase 1) | — |
| **Beta** | 2 años de rentabilidades **semanales** frente al S&P 500 (regresión MCO), cruda y ajustada por **Blume** con los coeficientes ya existentes en config; con su R² y nº de observaciones | práctica estándar (Bloomberg) |

- **Fuera:** RSI, MACD, figuras chartistas, Fibonacci (sin evidencia fuera de muestra; PLAN §2.2).
- Cada función devuelve el valor, su estado (`ok`, `sin_dato`, `historia_insuficiente`) y los parámetros usados.
- Para ADR: la beta frente al S&P 500 (perspectiva del inversor en dólares). Anótalo en el docstring.

### T4. Pruebas
- **Contraste independiente** en 5 tickers: cada señal calculada otra vez con un método escrito aparte (pandas
  directo, sin reusar tus funciones). Coincidencia dentro de tolerancia numérica.
- **Beta frente a la referencia de la 2a:** si la 2a dejó su beta de referencia calculada, tus betas deben coincidir
  con las suyas (mismas fechas y fuente) en los tickers comunes.
- Casos límite: historia corta (IPO reciente), serie con hueco, split sin ajustar inyectado, volumen cero.
- Suite completa en verde, **0 golden cambiados**, `test_config_literals` en verde.

### T5. Muestra para el planificador
`docs/fiabilidad/F5PREP_MUESTRA.md` (en tu rama):
- tabla de las señales de los 36 tickers;
- **beta propia frente a Finnhub** (de los fixtures del panel), con la diferencia; señala BCS y NVO;
- latencia medida por ticker y total (¿cabe en un análisis? propuesta para la fase 5: caché diaria);
- 3 lecturas de ejemplo en lenguaje llano **sin recomendación** (p. ej. "cotiza un 18% por encima de su media de 200
  sesiones; en el último año cayó hasta un 32% desde su máximo"), para que el planificador vea el tono.

### T6. Cierre → **PUNTO DE PARADA**
- Commits pequeños con prefijo `F5prep:`. **Sin push ni merge.**
- Tu entrada de sesión en `docs/fiabilidad/F5PREP_REGISTRO.md` de tu rama (no edites la bitácora: la edita el
  operador de la 2a; el planificador la llevará).
- Presenta la muestra, el contraste independiente y la comparación de betas. **Detente.**

## 3. Reglas que no se rompen

- **Nada conectado al motor ni al score.** Si algo parece requerirlo, detente y pregunta.
- Ningún literal numérico en las funciones; parámetros en config + schema.
- No edites archivos que pueda tocar el operador de la 2a (lista en la cabecera).
- Respeta a Yahoo: concurrencia baja (≤ 3) y pausas; nada de bucles agresivos.
- Toda afirmación de "hecho" o "pasa" va con el comando que la demuestra y su salida.

## 4. Definición de terminado

- [ ] `price_series.py` y `market_signals.py` con estados explícitos y parámetros en config.
- [ ] Fixtures de series de los 36 en `tests/fixtures/prices/` con metadatos; replay sin red.
- [ ] Contraste independiente en 5 tickers y betas coherentes con la referencia de la 2a.
- [ ] Suite en verde, 0 golden cambiados.
- [ ] `F5PREP_MUESTRA.md` y `F5PREP_REGISTRO.md`; rama sin push.
