# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T21:20:23. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.6 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 437 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 1.081 s (n = 333) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 4.7 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 4.721 s; tenencia máx. 9.581 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 333 | 0 | 0 | 0.032 | 1.081 | 7.532 |
| analysis_cold | 10 | 0 | 0 | 2.71 | 4.116 | 4.116 |
| page | 444 | 0 | 0 | 0.003 | 0.085 | 0.289 |
| pdf | 47 | 0 | 0 | 0.097 | 0.403 | 1.02 |
| peers | 265 | 0 | 0 | 0.003 | 0.053 | 0.11 |
| prices | 333 | 0 | 0 | 0.102 | 0.2 | 1.037 |
| scenario | 100 | 0 | 0 | 0.003 | 0.061 | 0.096 |
| search | 59 | 0 | 0 | 0.173 | 0.453 | 1.47 |
| segments | 333 | 0 | 0 | 0.001 | 0.022 | 0.277 |
| sparklines | 111 | 0 | 0 | 0.005 | 0.052 | 1.995 |
| trending | 111 | 0 | 0 | 0.007 | 0.013 | 0.07 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 4.25 s.
- Primer análisis de cada empresa: AAPL 4.25 s (200), JPM 1.99 s (200), O 2.61 s (200), NEE 2.29 s (200), XOM 3.3 s (200), PLTR 2.05 s (200), RIVN 2.07 s (200), BCS 3.38 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 106.2, 'cards': 90, 'listo': 49}.
- Memoria: pico del calentamiento 388.7 MB; al empezar la carga 388.7 MB; pico de la carga 436.7 MB (picos por separado: RSS 436.7 MB, huella física 406.1 MB).

Turnos de análisis: 398 de usuarios y 145 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 129 | 33.48 |
| data_fetcher._data_cache | 184 | 16.65 |
| price_history._cache | 64 | 3.09 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 1.48 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.37 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 217 | 0.04 |
