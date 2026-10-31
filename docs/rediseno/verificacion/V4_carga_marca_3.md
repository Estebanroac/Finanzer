# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-31T00:41:41. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.8 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 428 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.241 s (n = 363) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -49.5 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 3.483 s; tenencia máx. 6.045 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 363 | 0 | 0 | 0.03 | 0.241 | 3.896 |
| analysis_cold | 10 | 0 | 0 | 2.028 | 2.614 | 2.614 |
| page | 483 | 0 | 0 | 0.004 | 0.09 | 0.238 |
| pdf | 49 | 0 | 0 | 0.095 | 0.202 | 0.535 |
| peers | 231 | 0 | 0 | 0.004 | 0.058 | 0.096 |
| prices | 363 | 0 | 0 | 0.098 | 0.202 | 1.323 |
| scenario | 108 | 0 | 0 | 0.003 | 0.063 | 0.117 |
| search | 64 | 0 | 0 | 0.103 | 0.264 | 0.88 |
| segments | 363 | 0 | 0 | 0.001 | 0.026 | 0.994 |
| sparklines | 120 | 0 | 0 | 0.005 | 0.054 | 1.534 |
| trending | 120 | 0 | 0 | 0.008 | 0.036 | 0.053 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.49 s.
- Primer análisis de cada empresa: AAPL 2.49 s (200), JPM 1.79 s (200), O 2.01 s (200), NEE 1.76 s (200), XOM 1.99 s (200), PLTR 1.39 s (200), RIVN 1.88 s (200), BCS 2.16 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 121.5, 'cards': 90, 'listo': 46}.
- Memoria: pico del calentamiento 368.6 MB; al empezar la carga 348.0 MB; pico de la carga 427.8 MB (picos por separado: RSS 427.8 MB, huella física 400.2 MB).

Turnos de análisis: 430 de usuarios y 109 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 138 | 27.38 |
| data_fetcher._data_cache | 178 | 16.07 |
| price_history._cache | 64 | 3.28 |
| yf_adapter._stmt_cache | 336 | 2.82 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 0.81 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.35 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 185 | 0.03 |
