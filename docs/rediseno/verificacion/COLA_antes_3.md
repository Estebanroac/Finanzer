# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T15:11:06. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 183.9 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 432 MB | < 450 MB |
| p95 de /api/analysis en caché | ❌ | 2.914 s (n = 343) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 0.6 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 8.042 s; tenencia máx. 13.416 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 343 | 0 | 0 | 0.035 | 2.914 | 12.889 |
| analysis_cold | 10 | 0 | 0 | 2.568 | 7.518 | 7.518 |
| page | 458 | 0 | 0 | 0.004 | 0.093 | 0.508 |
| pdf | 44 | 0 | 0 | 0.103 | 0.497 | 2.117 |
| peers | 238 | 0 | 0 | 0.004 | 0.061 | 0.289 |
| prices | 343 | 0 | 0 | 0.101 | 0.306 | 1.653 |
| scenario | 105 | 0 | 0 | 0.003 | 0.056 | 0.287 |
| search | 58 | 0 | 0 | 0.16 | 0.41 | 1.084 |
| segments | 343 | 0 | 0 | 0.001 | 0.039 | 5.387 |
| sparklines | 115 | 0 | 0 | 0.005 | 0.05 | 2.384 |
| trending | 115 | 0 | 0 | 0.007 | 0.026 | 0.044 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.84 s.
- Primer análisis de cada empresa: AAPL 2.84 s (200), JPM 2.12 s (200), O 2.3 s (200), NEE 3.37 s (200), XOM 2.24 s (200), PLTR 2.36 s (200), RIVN 2.11 s (200), BCS 2.75 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 85.2, 'cards': 90, 'listo': 48}.
- Memoria: pico del calentamiento 413.8 MB; al empezar la carga 350.0 MB; pico de la carga 431.7 MB (picos por separado: RSS 418.0 MB, huella física 431.7 MB).

Turnos de análisis: 405 de usuarios y 168 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.845 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 134 | 31.02 |
| data_fetcher._data_cache | 194 | 17.47 |
| price_history._cache | 64 | 3.34 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| finnhub_fallback._cache | 96 | 2.17 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 238 | 0.04 |
