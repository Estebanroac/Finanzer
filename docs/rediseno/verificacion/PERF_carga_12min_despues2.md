# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T11:44:31. Backend: finanzer_next-perf/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 723.8 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 384 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.351 s (n = 1128) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -16.4 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.118 s; tenencia máx. 8.403 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1128 | 0 | 0 | 0.037 | 0.351 | 3.408 |
| analysis_cold | 10 | 0 | 0 | 2.517 | 5.004 | 5.004 |
| page | 1525 | 0 | 0 | 0.004 | 0.089 | 0.262 |
| pdf | 140 | 0 | 0 | 0.106 | 0.235 | 0.871 |
| peers | 1434 | 0 | 0 | 0.003 | 0.043 | 0.186 |
| prices | 1128 | 0 | 0 | 0.102 | 0.18 | 3.764 |
| scenario | 332 | 0 | 0 | 0.003 | 0.053 | 0.135 |
| search | 218 | 0 | 0 | 0.142 | 0.367 | 0.521 |
| segments | 1128 | 0 | 0 | 0.001 | 0.019 | 0.144 |
| sparklines | 397 | 0 | 0 | 0.005 | 0.047 | 2.355 |
| trending | 397 | 0 | 0 | 0.008 | 0.028 | 0.079 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 3.58 s.
- Primer análisis de cada empresa: AAPL 3.58 s (200), JPM 2.57 s (200), O 5.2 s (200), NEE 4.75 s (200), XOM 2.39 s (200), PLTR 2.09 s (200), RIVN 4.78 s (200), BCS 3.41 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 21.1, 'cards': 0, 'listo': 0}.
- Memoria: pico del calentamiento 286.8 MB; al empezar la carga 286.8 MB; pico de la carga 383.5 MB (picos por separado: RSS 375.1 MB, huella física 383.5 MB).

Turnos de análisis: 1286 de usuarios y 134 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 132 | 26.91 |
| data_fetcher._data_cache | 154 | 11.6 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.87 |
| finnhub_fallback._cache | 96 | 2.36 |
| price_history._chart_cache | 16 | 1.98 |
| trending._state | 7 | 0.68 |
| sparklines._cache | 120 | 0.61 |
| segments._cache | 64 | 0.39 |
| analysis_queue._summaries | 64 | 0.31 |
| universe._state | 4 | 0.29 |
| peers._caps | 131 | 0.02 |
