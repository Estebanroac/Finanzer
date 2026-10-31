# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T19:36:17. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.5 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 412 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.722 s (n = 329) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -0.5 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 4.048 s; tenencia máx. 6.941 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 329 | 0 | 0 | 0.032 | 0.722 | 5.598 |
| analysis_cold | 10 | 0 | 0 | 2.123 | 4.131 | 4.131 |
| page | 437 | 0 | 0 | 0.003 | 0.092 | 0.279 |
| pdf | 46 | 0 | 0 | 0.103 | 0.509 | 1.884 |
| peers | 284 | 0 | 0 | 0.003 | 0.054 | 0.152 |
| prices | 329 | 0 | 0 | 0.103 | 0.275 | 1.139 |
| scenario | 95 | 0 | 0 | 0.003 | 0.056 | 0.09 |
| search | 58 | 0 | 0 | 0.143 | 0.321 | 0.846 |
| segments | 329 | 0 | 0 | 0.001 | 0.038 | 0.164 |
| sparklines | 108 | 0 | 0 | 0.005 | 0.072 | 1.818 |
| trending | 108 | 0 | 0 | 0.007 | 0.023 | 0.056 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.91 s.
- Primer análisis de cada empresa: AAPL 2.91 s (200), JPM 2.5 s (200), O 2.58 s (200), NEE 2.59 s (200), XOM 2.7 s (200), PLTR 2.27 s (200), RIVN 1.4 s (200), BCS 3.84 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 91.0, 'cards': 90, 'listo': 47}.
- Memoria: pico del calentamiento 354.3 MB; al empezar la carga 349.4 MB; pico de la carga 412.4 MB (picos por separado: RSS 412.4 MB, huella física 392.1 MB).

Turnos de análisis: 393 de usuarios y 163 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 134 | 33.06 |
| data_fetcher._data_cache | 196 | 17.76 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.85 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 1.25 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 184 | 0.03 |
