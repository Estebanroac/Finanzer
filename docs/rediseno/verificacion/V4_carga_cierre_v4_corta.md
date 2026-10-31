# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T19:26:23. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.7 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 448 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.593 s (n = 335) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -5.3 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 4.429 s; tenencia máx. 7.333 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 335 | 0 | 0 | 0.034 | 0.593 | 6.191 |
| analysis_cold | 10 | 0 | 0 | 2.453 | 4.663 | 4.663 |
| page | 452 | 0 | 0 | 0.004 | 0.083 | 0.231 |
| pdf | 45 | 0 | 0 | 0.106 | 0.483 | 3.81 |
| peers | 263 | 0 | 0 | 0.004 | 0.058 | 0.129 |
| prices | 335 | 0 | 0 | 0.1 | 0.19 | 0.961 |
| scenario | 103 | 0 | 0 | 0.003 | 0.038 | 0.094 |
| search | 60 | 0 | 0 | 0.135 | 0.35 | 0.411 |
| segments | 335 | 0 | 0 | 0.001 | 0.026 | 0.159 |
| sparklines | 117 | 0 | 0 | 0.005 | 0.07 | 1.978 |
| trending | 117 | 0 | 0 | 0.007 | 0.033 | 0.056 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.61 s.
- Primer análisis de cada empresa: AAPL 2.61 s (200), JPM 2.24 s (200), O 2.38 s (200), NEE 2.45 s (200), XOM 2.25 s (200), PLTR 2.45 s (200), RIVN 4.11 s (200), BCS 2.76 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 84.8, 'cards': 90, 'listo': 48}.
- Memoria: pico del calentamiento 395.6 MB; al empezar la carga 395.6 MB; pico de la carga 448.1 MB (picos por separado: RSS 448.1 MB, huella física 358.3 MB).

Turnos de análisis: 398 de usuarios y 146 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 132 | 32.17 |
| data_fetcher._data_cache | 186 | 16.82 |
| price_history._cache | 64 | 3.34 |
| yf_adapter._stmt_cache | 336 | 2.83 |
| finnhub_fallback._cache | 96 | 2.08 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 196 | 0.03 |
