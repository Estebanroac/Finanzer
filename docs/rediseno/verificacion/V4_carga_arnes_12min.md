# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T14:01:47. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 724.1 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 388 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.131 s (n = 1203) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 14.1 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.932 s; tenencia máx. 7.26 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1203 | 0 | 0 | 0.029 | 0.131 | 2.489 |
| analysis_cold | 10 | 0 | 0 | 1.964 | 4.285 | 4.285 |
| page | 1627 | 0 | 0 | 0.004 | 0.084 | 0.222 |
| pdf | 144 | 0 | 0 | 0.103 | 0.218 | 1.103 |
| peers | 1324 | 0 | 0 | 0.003 | 0.051 | 0.114 |
| prices | 1203 | 0 | 0 | 0.101 | 0.172 | 2.332 |
| scenario | 356 | 0 | 0 | 0.003 | 0.061 | 0.272 |
| search | 229 | 0 | 0 | 0.143 | 0.345 | 1.0 |
| segments | 1203 | 0 | 0 | 0.001 | 0.011 | 0.13 |
| sparklines | 424 | 0 | 0 | 0.005 | 0.052 | 2.711 |
| trending | 424 | 0 | 0 | 0.007 | 0.032 | 0.42 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.42 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.86 s.
- Primer análisis de cada empresa: AAPL 2.86 s (200), JPM 1.71 s (200), O 2.24 s (200), NEE 2.71 s (200), XOM 1.59 s (200), PLTR 1.59 s (200), RIVN 1.53 s (200), BCS 2.32 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 66.8, 'cards': 90, 'listo': 38}.
- Memoria: pico del calentamiento 339.8 MB; al empezar la carga 339.8 MB; pico de la carga 388.2 MB (picos por separado: RSS 388.2 MB, huella física 372.7 MB).

Turnos de análisis: 1365 de usuarios y 129 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 132 | 26.93 |
| data_fetcher._data_cache | 154 | 11.64 |
| price_history._cache | 64 | 3.33 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 1.76 |
| sparklines._cache | 120 | 0.71 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.36 |
| analysis_queue._summaries | 64 | 0.31 |
| universe._state | 4 | 0.29 |
| peers._caps | 131 | 0.02 |
