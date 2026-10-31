# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T12:35:54. Backend: finanzer_next-perf-antes/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 727.2 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 386 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.224 s (n = 1158) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 32.5 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.127 s; tenencia máx. 6.727 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1158 | 0 | 0 | 0.038 | 0.224 | 1.898 |
| analysis_cold | 10 | 0 | 0 | 2.791 | 3.496 | 3.496 |
| page | 1568 | 0 | 0 | 0.005 | 0.084 | 0.239 |
| pdf | 142 | 0 | 0 | 0.108 | 0.238 | 1.125 |
| peers | 1395 | 0 | 0 | 0.004 | 0.049 | 0.191 |
| prices | 1158 | 0 | 0 | 0.1 | 0.175 | 3.58 |
| scenario | 338 | 0 | 0 | 0.004 | 0.061 | 0.173 |
| search | 222 | 0 | 0 | 0.123 | 0.328 | 0.9 |
| segments | 1158 | 0 | 0 | 0.001 | 0.019 | 1.18 |
| sparklines | 410 | 0 | 0 | 0.005 | 0.058 | 2.389 |
| trending | 410 | 0 | 0 | 0.008 | 0.032 | 0.079 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.94 s.
- Primer análisis de cada empresa: AAPL 3.94 s (200), JPM 2.88 s (200), O 3.91 s (200), NEE 2.47 s (200), XOM 2.65 s (200), PLTR 2.68 s (200), RIVN 2.82 s (200), BCS 3.66 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 18.1, 'cards': 0, 'listo': 0}.
- Memoria: pico del calentamiento 284.0 MB; al empezar la carga 284.0 MB; pico de la carga 386.5 MB (picos por separado: RSS 386.5 MB, huella física 348.2 MB).

Turnos de análisis: 1318 de usuarios y 118 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 132 | 26.49 |
| data_fetcher._data_cache | 154 | 11.69 |
| price_history._cache | 64 | 3.31 |
| finnhub_fallback._cache | 96 | 3.28 |
| yf_adapter._stmt_cache | 336 | 2.87 |
| price_history._chart_cache | 16 | 1.98 |
| trending._state | 7 | 0.68 |
| sparklines._cache | 120 | 0.65 |
| segments._cache | 64 | 0.39 |
| analysis_queue._summaries | 64 | 0.31 |
| universe._state | 4 | 0.29 |
| peers._caps | 131 | 0.02 |
