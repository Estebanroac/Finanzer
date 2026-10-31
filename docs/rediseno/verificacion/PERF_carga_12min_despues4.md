# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T13:10:21. Backend: finanzer_next-perf/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 724.9 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 374 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.229 s (n = 1106) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 2.6 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.119 s; tenencia máx. 9.831 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1106 | 0 | 0 | 0.038 | 0.229 | 4.61 |
| analysis_cold | 10 | 0 | 0 | 1.941 | 3.525 | 3.525 |
| page | 1498 | 0 | 0 | 0.005 | 0.088 | 0.199 |
| pdf | 138 | 0 | 0 | 0.105 | 0.321 | 1.532 |
| peers | 1467 | 0 | 0 | 0.004 | 0.042 | 0.322 |
| prices | 1106 | 0 | 0 | 0.1 | 0.168 | 3.767 |
| scenario | 327 | 0 | 0 | 0.003 | 0.055 | 0.093 |
| search | 211 | 0 | 0 | 0.137 | 0.327 | 0.908 |
| segments | 1106 | 0 | 0 | 0.001 | 0.019 | 0.151 |
| sparklines | 392 | 0 | 0 | 0.005 | 0.05 | 1.875 |
| trending | 392 | 0 | 0 | 0.011 | 0.039 | 0.102 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 2.95 s.
- Primer análisis de cada empresa: AAPL 2.95 s (200), JPM 1.64 s (200), O 2.16 s (200), NEE 2.09 s (200), XOM 1.66 s (200), PLTR 1.57 s (200), RIVN 1.6 s (200), BCS 2.35 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 18.1, 'cards': 0, 'listo': 0}.
- Memoria: pico del calentamiento 311.5 MB; al empezar la carga 311.5 MB; pico de la carga 374.1 MB (picos por separado: RSS 371.5 MB, huella física 374.1 MB).

Turnos de análisis: 1262 de usuarios y 140 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 132 | 26.23 |
| data_fetcher._data_cache | 154 | 11.69 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.89 |
| finnhub_fallback._cache | 96 | 2.54 |
| price_history._chart_cache | 16 | 1.98 |
| trending._state | 7 | 0.68 |
| sparklines._cache | 120 | 0.67 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.31 |
| universe._state | 4 | 0.29 |
| peers._caps | 131 | 0.02 |
