# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T15:06:15. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 185.0 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 421 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.434 s (n = 374) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -32.6 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 6.736 s; tenencia máx. 7.548 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 374 | 0 | 0 | 0.028 | 0.434 | 8.746 |
| analysis_cold | 10 | 0 | 0 | 2.541 | 6.282 | 6.282 |
| page | 497 | 0 | 0 | 0.004 | 0.098 | 0.207 |
| pdf | 48 | 0 | 0 | 0.103 | 0.583 | 2.295 |
| peers | 202 | 0 | 0 | 0.003 | 0.072 | 0.154 |
| prices | 374 | 0 | 0 | 0.103 | 0.243 | 1.999 |
| scenario | 111 | 0 | 0 | 0.003 | 0.056 | 0.134 |
| search | 63 | 0 | 0 | 0.18 | 0.392 | 0.438 |
| segments | 374 | 0 | 0 | 0.001 | 0.037 | 0.157 |
| sparklines | 123 | 0 | 0 | 0.005 | 0.04 | 2.355 |
| trending | 123 | 0 | 0 | 0.007 | 0.031 | 0.053 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.55 s.
- Primer análisis de cada empresa: AAPL 3.55 s (200), JPM 4.15 s (200), O 3.44 s (200), NEE 3.89 s (200), XOM 2.71 s (200), PLTR 2.35 s (200), RIVN 2.05 s (200), BCS 3.54 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 88.0, 'cards': 90, 'listo': 48}.
- Memoria: pico del calentamiento 401.9 MB; al empezar la carga 341.8 MB; pico de la carga 421.3 MB (picos por separado: RSS 421.3 MB, huella física 405.5 MB).

Turnos de análisis: 440 de usuarios y 140 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 134 | 30.77 |
| data_fetcher._data_cache | 194 | 17.56 |
| price_history._cache | 64 | 3.33 |
| yf_adapter._stmt_cache | 336 | 2.85 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| finnhub_fallback._cache | 96 | 0.51 |
| segments._cache | 64 | 0.39 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 238 | 0.04 |
