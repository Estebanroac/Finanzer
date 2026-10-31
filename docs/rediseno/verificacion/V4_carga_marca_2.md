# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-31T00:31:41. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.0 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ❌ | 460 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.352 s (n = 356) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -19.0 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 4.498 s; tenencia máx. 12.272 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 356 | 0 | 0 | 0.035 | 0.352 | 6.444 |
| analysis_cold | 10 | 0 | 0 | 2.069 | 4.814 | 4.814 |
| page | 475 | 0 | 0 | 0.004 | 0.082 | 0.196 |
| pdf | 48 | 0 | 0 | 0.105 | 0.537 | 4.26 |
| peers | 232 | 0 | 0 | 0.004 | 0.056 | 0.096 |
| prices | 356 | 0 | 0 | 0.099 | 0.183 | 0.921 |
| scenario | 105 | 0 | 0 | 0.003 | 0.074 | 0.109 |
| search | 64 | 0 | 0 | 0.136 | 0.327 | 0.766 |
| segments | 356 | 0 | 0 | 0.001 | 0.025 | 0.241 |
| sparklines | 119 | 0 | 0 | 0.005 | 0.055 | 1.556 |
| trending | 119 | 0 | 0 | 0.008 | 0.018 | 0.069 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 5.9 s.
- Primer análisis de cada empresa: AAPL 5.9 s (200), JPM 3.86 s (200), O 4.15 s (200), NEE 3.8 s (200), XOM 3.33 s (200), PLTR 3.16 s (200), RIVN 3.47 s (200), BCS 4.81 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 133.2, 'cards': 90, 'listo': 48}.
- Memoria: pico del calentamiento 395.3 MB; al empezar la carga 395.3 MB; pico de la carga 459.5 MB (picos por separado: RSS 459.5 MB, huella física 372.1 MB).

Turnos de análisis: 422 de usuarios y 126 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 134 | 31.26 |
| data_fetcher._data_cache | 190 | 17.18 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.82 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| finnhub_fallback._cache | 96 | 0.24 |
| peers._caps | 248 | 0.04 |
