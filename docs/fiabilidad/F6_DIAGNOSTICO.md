# Fase 6 · Diagnóstico de infraestructura (solo medir)

*Operador F67prep, 15-oct-2026, rama `fiabilidad/f67-prep` (desde `main` = producción = `8ed57a0`). Plan:
[`../PLAN_FIABILIDAD.md`](../PLAN_FIABILIDAD.md) §4, fase 6 (objetivo: p95 del análisis < 6 s en frío y < 1 s en
caliente; 12 peticiones simultáneas sin cola en serie). **No cambia el motor ni la app**: solo herramientas de
medida en `backend/tests/` y este informe. **No se hizo ninguna prueba de 12 simultáneas contra producción**
(concurrencia máxima 3, fuera de la ventana de 15:55 a 16:45 de Nueva York).*

## Resumen

| Pregunta | Respuesta medida |
|---|---|
| ¿Dónde se va el tiempo de un análisis en frío? | En la **red**, no en la CPU. Un análisis en frío hace **15 peticiones HTTP** casi todas **una tras otra**; en producción tarda 3.1–4.3 s (12/12 tickers fuera del panel). La CPU del motor en replay es de 5–11 ms |
| ¿Y el PDF? | En la **CPU** (reportlab): 50 ms en este Mac, **≈ 1.7 s en Render** con el análisis ya en caché (≈ 34× más lento: instancia de CPU fraccionaria) |
| ¿Por qué los 46–52 s de F0? | **Arranque en frío de Render** (servicio apagado sin tráfico): `/api/health` tardó **42.7 s** a las 13:59:49 del 15-oct; después, 0.3 s. Más la cola de la primera tanda |
| ¿Atiende en serie? | **Sí, confirmado** en código y en medida: los endpoints son `async def` y llaman a código bloqueante sin soltar el bucle de eventos, con un solo proceso de uvicorn. A concurrencia 3 el rendimiento no mejora (33 s frente a 38–39 s) y `/api/health` tarda 2.5 s de mediana si hay un análisis en curso |
| ¿Se cumple hoy el objetivo? | **Sin arranque en frío ni cola, casi**: frío 3.1–4.3 s (< 6 s) y caliente 0.38–0.72 s (< 1 s). Lo rompen el apagado (+43 s), la cola en serie (×N con N peticiones) y que "caliente" solo dura 5 min |

## 1. Desglose del tiempo

### 1.1 CPU local (replay, sin red)

Comando: `cd backend && ../.venv313/bin/python tests/perfil_local.py --out ~/Downloads/finanzer_f6_medida_2026-10-15/perfil_local`
(salida en esa carpeta: `perfil.md`, `perfil.json`). 12 tickers: los 6 de `local` (NFLX, JPM, O, FCX, SNOW, V) y 6 del
panel de arquetipos distintos (AAPL MATURE, BAC FINANCIAL, PLD REIT, NEE UTILITY, XOM CYCLICAL, RIVN GROWTH_PRE_PROFIT).

| | Análisis | PDF |
|---|---|---|
| Tiempo de pared por ticker (mediana de 3, sin perfilador) | **5–11 ms** | **47–59 ms** |
| Primera ejecución del proceso (calentamiento) | 0.13 s | 0.22 s |
| CPU por módulo (cProfile, 12 tickers) | `copy.deepcopy` 44% (stdlib), pandas 22%, built-ins 21%; el motor (`lib/`) < 10% | **reportlab 64%** + built-ins 31% (codificación ASCII85, `breakLines`, anchos de texto) |
| Funciones con más tiempo propio | `deepcopy` (230.902 llamadas), `_deepcopy_dict`, `dict.get` | `_py_asciiBase85Encode` (0.28 s de 1.9 s), `breakLines`, `_py_fp_str` |

- Importar `main` y `pdf_report` en un proceso nuevo: 0.47–0.69 s; memoria de un proceso tras 32 análisis + PDF del
  panel: **≈ 190 MB de pico** (123 MB solo con los imports).
- Lectura: la CPU del motor es despreciable. El PDF usa las versiones Python puras de reportlab (`_py_*`): con
  `reportlab==5.0.1` (fijado en `requirements.txt`) la aceleración en C es el paquete aparte `rl_accel`, que no está
  en `requirements.txt`, y en `.venv313` `reportlab.lib.rl_accel.asciiBase85Encode` resuelve a
  `_py_asciiBase85Encode` (la versión Python). Instalarlo o
  comprimir sin ASCII85 es una mejora posible del PDF, a medir en la fase 6. La memoria es de este Mac en replay;
  en producción, con la red, será algo mayor.

### 1.2 Llamadas externas por análisis (ruta de producción: plan B + Finnhub)

Contadas en el replay del panel (32 tickers; idénticas en todos salvo tipos de cambio):

| Fuente | Por análisis |
|---|---|
| Yahoo `quoteSummary` | 2 (responden 401 al instante desde Render; el bloqueo se recuerda 10 min) |
| Yahoo `search` | 1 |
| Yahoo `fundamentals-timeseries` (sonda de moneda) | 1 |
| yfinance: estados anuales y trimestrales (`income_stmt`, `balance_sheet`, `cashflow` y sus trimestrales) | 6 estados (9 accesos; yfinance reutiliza el objeto) |
| yfinance `fast_info` (cotización) | 1 (2 peticiones a `chart`) |
| Finnhub `/stock/metric` | 1 |
| Tipos de cambio | 0 (1 en TSM, ASML, NVO y BCS) |
| Rf (^TNX) | 1 cada 24 h por proceso (el replay la congela) |

Traza real desde este Mac (`perfil_local.py --red-local HD PEP MCD`, Render simulado, sin Finnhub): **15
peticiones HTTP** por análisis en frío, de 0.25 a 1.8 s cada una, **casi todas en serie** (solo 2 de las 8 de
estados se solapan); 1.7 s de preparación de la sesión (cookie y crumb) antes de la primera. Total: 7.0–8.8 s en la
primera pasada (14:10 NY) y 3.1–3.7 s en la segunda (14:14 NY): la red de Yahoo varía ×2 en minutos. CPU del proceso
en frío: 0.14–0.19 s. **Los estados (8 de las 15 peticiones) son ≈ 45–55% del tiempo de red.**

### 1.3 Red estimada en producción

Medida directa (`tests/medir_concurrencia.py`, 12 tickers fuera del panel, despierto, en serie):

| | Mediana | Rango | Lectura |
|---|---|---|---|
| `/api/analysis` en frío | 3.67–3.74 s | 3.14–4.33 s | ≈ 0.3 s de ida y vuelta + ≈ 3.4 s de servicio, casi todo red |
| `/api/analysis` en caliente (segunda petición) | 0.48–0.56 s | 0.38–0.72 s | ≈ 0.2 s de servicio (serializar ~100 KB de JSON) |
| `/api/pdf` en caliente | 1.96–2.0 s | 1.70–3.01 s | ≈ 1.7 s de CPU de reportlab |
| `/api/health` (despierto) | 0.26–0.30 s | — | ida y vuelta a Render a través de Cloudflare |

Desde Render la red a Yahoo es más rápida que desde este Mac (3.4 s frente a 3.1–8.8 s). El PDF en frío = análisis
en frío + PDF ≈ 5.1 s de servicio.

### 1.4 Cola

Con N peticiones a la vez, cada una espera el servicio de las anteriores (ver §2). En la corrida de la semana 0
(32 tickers del panel, concurrencia 3, servidor despierto): `/api/analysis` p50 6.66 s, p95 11.59 s, máx 14.56 s;
`/api/pdf` p50 7.73 s, p95 11.98 s. Es ≈ 2–3 × el servicio en serie: **la diferencia es cola**. F0 (14-oct) añadía el
arranque en frío: p95 45.9 s, máx 52.5 s.

### 1.5 Qué se cachea hoy y qué se pierde cuando Render se apaga

Todo es memoria del proceso: **se pierde entero** al apagarse (sin tráfico) y en cada deploy.

| Caché | Dónde | TTL |
|---|---|---|
| Datos del ticker (estados + cotización) | `yf_adapter._cache` | **300 s** (60 s si viene degradado) |
| Último snapshot bueno | `yf_adapter._best_cache` | 24 h |
| Perfil / estados de `FinancialDataService` | `data_fetcher.SimpleCache` (500 entradas) | 30 / 60 min |
| Finnhub | `finnhub_fallback._cache` | 300 s |
| Rf (^TNX) | `cost_of_capital._RF_CACHE` | 24 h |
| Bloqueo de quoteSummary | `yf_adapter._qs_blocked_until` | 600 s |
| Sesión y crumb de Yahoo | `yf_adapter._session`, `_crumb` | proceso |

Consecuencia: **"en caliente" dura 5 minutos** (el primer TTL que expira, `get_ticker_info`, se llama siempre al
principio). Una segunda consulta del mismo ticker a los 6 minutos vuelve a ser fría (3–4 s), aunque los estados no
hayan cambiado en un trimestre.

## 2. Por qué producción atiende en serie

**En el código** (`backend/main.py`, solo lectura):
- `main.py:1521-1524`: `@app.get("/api/analysis/{symbol}") async def analyze_stock(...): return _compute_analysis(symbol)`.
- `main.py:1527-1534`: `async def download_pdf(...)` llama a `_compute_analysis(symbol)` y a `build_report(...)`.
- `_compute_analysis` (`main.py:281`) es **síncrono y bloqueante**: yfinance, `curl_cffi` (`yf_adapter._session.get`),
  `urllib` (Finnhub) y reportlab. Ningún `await`, `run_in_threadpool` ni `asyncio.to_thread`.
- FastAPI ejecuta las funciones `async def` **en el bucle de eventos** (las `def` normales irían a su pool de hilos).
  Un `async def` con código bloqueante congela el bucle: mientras dura un análisis, el proceso no atiende nada más,
  ni siquiera `/api/health`.
- Arranque: no hay `render.yaml` ni `Procfile` en el repo; el comando de arranque está en el panel de Render
  (**[no verificable desde aquí]**). La cabecera `x-render-origin-server: uvicorn` y la medida (abajo) indican **un
  solo proceso de uvicorn**. El paralelismo interno (`ThreadPoolExecutor` de 4 en `data_fetcher`, de 3 en
  `yf_adapter`) solo acelera dentro de una petición y, según la traza de §1.2, apenas se usa.

**En la medida** (`tests/medir_concurrencia.py`, dos rondas de 12 tickers cada una, 14:09 y 14:12 NY; salida en
`~/Downloads/finanzer_f6_medida_2026-10-15/ronda{1,2}/`):

| | Ronda 1 | Ronda 2 |
|---|---|---|
| 6 tickers en serie (concurrencia 1): tiempo total | 38.1 s | 39.0 s |
| Otros 6 a concurrencia 3: tiempo total | **33.6 s** | **33.0 s** |
| Análisis en frío: mediana en serie → a concurrencia 3 | 3.74 → 7.14 s | 3.67 → 7.74 s |
| Análisis en caliente | 0.56 → 3.60 s | 0.48 → 3.64 s |
| PDF en caliente | 2.00 → 5.69 s | 1.96 → 4.56 s |
| Suma de latencias en serie → concurrencia 3 | 38.1 → 100.7 s (×2.6) | 38.4 → 98.5 s (×2.6) |
| `/api/health` cada segundo durante la ronda en serie | — | **12/12 por encima de 1 s**; mediana 2.54 s, máx 3.45 s (despierto y sin análisis: 0.3 s) |

- A concurrencia 3, **el trabajo total no se reparte**: la ronda dura lo mismo (−12/−15%, lo que ahorra solapar la
  ida y vuelta de red del cliente) y cada petición tarda ≈ 3 × su servicio. Las tres primeras peticiones frías de
  la ronda 1 tardaron 3.8, 7.0 y 10.3 s: 1, 2 y 3 servicios, la cola exacta.
- La sonda de `/api/health` es la prueba directa del bucle bloqueado: una petición trivial espera a que termine el
  análisis en curso. Con dos procesos, alguna sonda habría caído en el proceso libre.

### 2.1 Estimación de 12 simultáneas (no ejecutada)

Servicio medido: análisis en frío S ≈ 3.4 s, PDF en frío ≈ 5.1 s, ida y vuelta 0.3 s. Validación del modelo: a
concurrencia 3 predice 3.7 / 7.1 / 10.5 s y se midió 3.8 / 7.0 / 10.3 s.

| Escenario (12 análisis en frío a la vez, servidor despierto) | p50 | p95 | Máximo | Base |
|---|---|---|---|---|
| **Hoy**: un proceso, bucle bloqueado (cola en serie) | ≈ 22 s | ≈ 39 s | ≈ 41 s | k-ésimo = k × 3.4 + 0.3 |
| Hoy, 12 PDF en frío | ≈ 33 s | ≈ 59 s | ≈ 62 s | k × 5.1 + 0.3 |
| Hoy con el servicio apagado | +43 s a todas | | | arranque medido 42.7 s |
| 2 procesos (`--workers 2`) | ≈ 12 s | ≈ 20 s | ≈ 21 s | ⌈12/2⌉ × 3.4; memoria ≈ 2 × 190 MB, cabe en 512 MB |
| 4 procesos | ≈ 7 s | ≈ 10 s | ≈ 10.5 s | ⌈12/4⌉ × 3.4; ≈ 760 MB: **no cabe en 512 MB** |
| Código bloqueante fuera del bucle (hilos) | ≈ 4–7 s | | | la red de 12 análisis se solapa; cota de CPU: 12 × ~0.2–0.5 s a la CPU actual. **Sin medir**: depende de que Yahoo tolere ~180 peticiones a la vez |
| Hilos, 12 PDF | ≈ 20 s de CPU de reportlab en total | | | el PDF es CPU (1.7 s cada uno): los hilos no lo arreglan; sí más CPU |

Diseño de la prueba real (para un entorno de pruebas o tras D6, **nunca contra finanzer.app**):
`tests/medir_concurrencia.py --base-url http://<staging> --concurrency 12 --c3 <12 tickers fuera del panel>`; contra
`finanzer.app` la herramienta se niega a pasar de 3.

## 3. Opciones: qué resuelve cada una y cuánto

| Opción | Qué resuelve | Cuánto (con la medida que lo respalda) | Qué no resuelve |
|---|---|---|---|
| **D6: servicio siempre encendido** (decidida; pendiente de contratar) | El arranque en frío | −42.7 s en la primera petición tras inactividad (medido hoy; F0: 45.9–52.5 s en las tres primeras). Si el plan de pago trae más CPU (en la tabla pública de Render, el gratuito tiene 0.1 CPU y apaga el servicio; el más bajo de pago, 0.5 CPU y no apaga: **verificar en el panel**), el PDF bajaría de ≈ 1.7 s hacia ≈ 0.35 s (proporcional a la CPU; sin medir) | La cola en serie: 12 a la vez siguen siendo ≈ 41 s |
| **Más workers** (`uvicorn --workers N` en el comando de arranque) | La cola entre peticiones | 12 en frío: máx ≈ 41 → 21 s (2) → 10.5 s (4). Memoria ≈ 190 MB por proceso: con 512 MB caben 2 | Cada worker sigue en serie; las cachés no se comparten entre procesos (cada uno calienta la suya); no cambia el tiempo de una petición sola |
| **Ejecutar fuera del bucle de eventos** (endpoints `def` o `run_in_threadpool`) | La cola de las esperas de red (el 90% del análisis en frío) | 12 análisis en frío: ≈ 41 s → ≈ 4–7 s estimado; `/api/health` deja de bloquearse. Replay con 12 hilos sobre 12 tickers: **salidas idénticas** a la serie en 3 de 3 repeticiones (sin red: no prueba las carreras de la sesión de Yahoo, a probar en la fase 6) | El PDF (CPU); el riesgo de estado global compartido (`yf_adapter._session`, `_crumb`, `_qs_blocked_until`, cachés): necesita su test de concurrencia en la fase 6 |
| **Caché persistente de estados** (disco o servicio externo, con TTL hasta el siguiente trimestre) | Las 8 peticiones de estados en cada análisis frío y la pérdida al apagar/desplegar | ≈ 45–55% de la red del frío (traza §1.2): 3.4 s → ≈ 1.5–2 s; "caliente" pasaría de 5 min a un trimestre para los estados (la cotización sigue en vivo) | La cotización, Finnhub y la Rf siguen en cada análisis; **depende de D2** (§4) |
| Paralelizar las descargas dentro de un análisis | La serie interna de §1.2 (solo 2 de 8 estados en paralelo) | Hasta ≈ 1–2 s del frío (estimación sobre la traza, sin medir) | Nada de la cola entre peticiones |

Recomendación del operador (para el planificador): **D6 + ejecutar fuera del bucle** atacan las dos causas medidas
(apagado y cola) sin tocar las fuentes; con eso, el objetivo de 12 simultáneas es alcanzable para el análisis. El PDF
a 12 simultáneas necesita más CPU (plan o reportlab acelerado). La caché persistente es la que acerca el frío al
caliente, pero espera a D2.

## 4. Qué depende de D2

- **No cachear la fuente equivocada.** La caché persistente de estados guardaría lo que hoy viene de Yahoo (plan B).
  Si D2 decide que EDGAR pasa a fuente principal de los estados, lo cacheado sería la fuente que se retira. Además,
  Yahoo da a Render datos distintos que a una IP residencial en 7/30 (F0): una caché persistente congelaría esa
  variación durante un trimestre.
- **La invalidación** depende de la fuente: con EDGAR, la fecha de presentación del 10-Q/10-K/20-F/6-K dice cuándo
  hay periodo nuevo (y `companyfacts` tardó 0.42 s de mediana en la 2a); con Yahoo no hay señal y habría que usar un
  TTL fijo.
- **Las reglas de precedencia** de la 2a (F2_PRECEDENCIA: qué fuente manda y con qué periodo) deciden qué campos se
  cachean juntos (p. ej., no mezclar el BPA TTM de Finnhub con estados de un trimestre anterior: caso JNJ).
- **No dependen de D2**: D6, más workers y sacar el código del bucle de eventos.

## 5. Avisos

- Producción no expone el commit desplegado hasta que se despliegue `356f49c` (2a, T0); `/api/health` responde hoy
  `{"status": "ok"}`.
- Las medidas son de un solo día (15-oct, 13:59–14:14 NY); la red de Yahoo varía ×2 en minutos. Repetir con la
  misma herramienta antes y después de cada cambio de la fase 6 (protocolo §5 del plan: "medición antes y después").
- 12 tickers × 1 consulta a Finnhub por análisis en frío en cada ronda: 24 consultas en total, lejos del límite de 60
  por minuto y fuera de la ventana de la 2a.
