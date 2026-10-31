# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T12:57:41. Backend: finanzer_next-perf-antes/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 724.3 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ❌ | 452 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.142 s (n = 1150) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -2.4 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.13 s; tenencia máx. 7.507 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1150 | 0 | 0 | 0.037 | 0.142 | 2.635 |
| analysis_cold | 10 | 0 | 0 | 2.653 | 3.613 | 3.613 |
| page | 1555 | 0 | 0 | 0.005 | 0.077 | 0.217 |
| pdf | 142 | 0 | 0 | 0.109 | 0.198 | 0.607 |
| peers | 1413 | 0 | 0 | 0.004 | 0.051 | 0.155 |
| prices | 1150 | 0 | 0 | 0.099 | 0.174 | 3.583 |
| scenario | 337 | 0 | 0 | 0.004 | 0.045 | 0.137 |
| search | 220 | 0 | 0 | 0.148 | 0.376 | 1.068 |
| segments | 1150 | 0 | 0 | 0.001 | 0.018 | 0.521 |
| sparklines | 405 | 0 | 0 | 0.005 | 0.044 | 3.033 |
| trending | 405 | 0 | 0 | 0.011 | 0.023 | 0.07 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 3.43 s.
- Primer análisis de cada empresa: AAPL 3.43 s (200), JPM 2.88 s (200), O 3.31 s (200), NEE 2.69 s (200), XOM 2.45 s (200), PLTR 2.46 s (200), RIVN 2.15 s (200), BCS 3.44 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 18.1, 'cards': 0, 'listo': 0}.
- Memoria: pico del calentamiento 342.8 MB; al empezar la carga 342.8 MB; pico de la carga 452.5 MB (picos por separado: RSS 452.5 MB, huella física 395.0 MB).

Turnos de análisis: 1310 de usuarios y 140 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 132 | 26.24 |
| data_fetcher._data_cache | 154 | 11.7 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.87 |
| finnhub_fallback._cache | 96 | 2.58 |
| price_history._chart_cache | 16 | 1.98 |
| trending._state | 7 | 0.68 |
| sparklines._cache | 120 | 0.67 |
| segments._cache | 64 | 0.39 |
| analysis_queue._summaries | 64 | 0.31 |
| universe._state | 4 | 0.29 |
| peers._caps | 131 | 0.02 |
