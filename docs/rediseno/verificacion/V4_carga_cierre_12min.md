# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T09:14:59. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 724.6 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 435 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.146 s (n = 1131) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -66.8 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.105 s; tenencia máx. 8.325 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1131 | 0 | 0 | 0.036 | 0.146 | 1.914 |
| analysis_cold | 10 | 0 | 0 | 3.468 | 4.899 | 4.899 |
| page | 1528 | 0 | 0 | 0.005 | 0.089 | 0.259 |
| pdf | 139 | 0 | 0 | 0.11 | 0.305 | 0.953 |
| peers | 1440 | 0 | 0 | 0.003 | 0.046 | 0.14 |
| prices | 1131 | 0 | 0 | 0.1 | 0.171 | 7.084 |
| scenario | 331 | 0 | 0 | 0.004 | 0.056 | 0.162 |
| search | 210 | 0 | 0 | 0.143 | 0.326 | 0.599 |
| segments | 1131 | 0 | 0 | 0.001 | 0.019 | 0.413 |
| sparklines | 397 | 0 | 0 | 0.006 | 0.043 | 6.149 |
| trending | 397 | 0 | 0 | 0.009 | 0.031 | 0.089 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 4.73 s.
- Primer análisis de cada empresa: AAPL 4.73 s (200), JPM 3.38 s (200), O 4.05 s (200), NEE 4.66 s (200), XOM 3.3 s (200), PLTR 3.37 s (200), RIVN 3.39 s (200), BCS 4.47 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 21.1, 'cards': 0, 'listo': 0}.
- Memoria: pico del calentamiento 328.0 MB; al empezar la carga 328.0 MB; pico de la carga 434.6 MB (picos por separado: RSS 434.6 MB, huella física 395.3 MB).

Turnos de análisis: 1288 de usuarios y 136 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 131 | 26.12 |
| data_fetcher._data_cache | 154 | 11.7 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.87 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 1.75 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.39 |
| analysis_queue._summaries | 64 | 0.31 |
| universe._state | 4 | 0.29 |
| peers._caps | 131 | 0.02 |
