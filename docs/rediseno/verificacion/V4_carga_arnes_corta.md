# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T13:48:00. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 187.1 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 398 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.804 s (n = 140) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 12.2 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.907 s; tenencia máx. 6.532 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 140 | 0 | 0 | 0.043 | 0.804 | 1.47 |
| analysis_cold | 10 | 0 | 0 | 1.849 | 2.371 | 2.371 |
| page | 181 | 0 | 0 | 0.005 | 0.068 | 0.151 |
| pdf | 22 | 0 | 0 | 0.106 | 0.169 | 0.206 |
| peers | 607 | 0 | 0 | 0.003 | 0.031 | 0.079 |
| prices | 140 | 0 | 0 | 0.1 | 1.954 | 2.246 |
| scenario | 39 | 0 | 0 | 0.003 | 0.024 | 0.178 |
| search | 26 | 0 | 0 | 0.142 | 0.367 | 0.587 |
| segments | 140 | 0 | 0 | 0.001 | 0.034 | 0.196 |
| sparklines | 41 | 0 | 0 | 0.008 | 1.026 | 1.893 |
| trending | 41 | 0 | 0 | 0.015 | 0.017 | 0.051 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 2.73 s.
- Primer análisis de cada empresa: AAPL 2.73 s (200), JPM 1.69 s (200), O 2.23 s (200), NEE 3.12 s (200), XOM 2.05 s (200), PLTR 1.86 s (200), RIVN 1.81 s (200), BCS 2.43 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 72.9, 'cards': 90, 'listo': 38}.
- Memoria: pico del calentamiento 325.3 MB; al empezar la carga 325.3 MB; pico de la carga 397.7 MB (picos por separado: RSS 397.7 MB, huella física 343.5 MB).

Turnos de análisis: 180 de usuarios y 40 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 105 | 33.94 |
| data_fetcher._data_cache | 86 | 6.17 |
| finnhub_fallback._cache | 96 | 3.54 |
| price_history._cache | 54 | 2.76 |
| yf_adapter._stmt_cache | 257 | 2.21 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.69 |
| trending._state | 7 | 0.68 |
| segments._cache | 42 | 0.29 |
| universe._state | 4 | 0.29 |
| analysis_queue._summaries | 34 | 0.17 |
| peers._caps | 125 | 0.02 |
