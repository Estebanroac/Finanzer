# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T11:20:24. Backend: finanzer_next-perf/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 724.8 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 431 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.303 s (n = 1149) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -24.8 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.084 s; tenencia máx. 7.528 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1149 | 0 | 0 | 0.036 | 0.303 | 2.493 |
| analysis_cold | 10 | 0 | 0 | 2.692 | 5.578 | 5.578 |
| page | 1553 | 0 | 0 | 0.005 | 0.081 | 0.19 |
| pdf | 142 | 0 | 0 | 0.11 | 0.617 | 1.782 |
| peers | 1405 | 0 | 0 | 0.004 | 0.048 | 0.184 |
| prices | 1149 | 0 | 0 | 0.102 | 0.181 | 3.37 |
| scenario | 335 | 0 | 0 | 0.004 | 0.05 | 0.143 |
| search | 220 | 0 | 0 | 0.174 | 0.547 | 1.459 |
| segments | 1149 | 0 | 0 | 0.001 | 0.019 | 0.167 |
| sparklines | 404 | 0 | 0 | 0.005 | 0.049 | 2.802 |
| trending | 404 | 0 | 0 | 0.01 | 0.03 | 0.079 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.42 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.92 s.
- Primer análisis de cada empresa: AAPL 3.92 s (200), JPM 6.67 s (200), O 5.53 s (200), NEE 4.07 s (200), XOM 2.97 s (200), PLTR 2.44 s (200), RIVN 2.58 s (200), BCS 4.32 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 21.1, 'cards': 0, 'listo': 0}.
- Memoria: pico del calentamiento 296.6 MB; al empezar la carga 289.9 MB; pico de la carga 430.9 MB (picos por separado: RSS 430.9 MB, huella física 416.6 MB).

Turnos de análisis: 1309 de usuarios y 141 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 132 | 26.44 |
| data_fetcher._data_cache | 154 | 11.7 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.86 |
| finnhub_fallback._cache | 96 | 2.55 |
| price_history._chart_cache | 16 | 1.98 |
| trending._state | 7 | 0.68 |
| sparklines._cache | 120 | 0.6 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.31 |
| universe._state | 4 | 0.29 |
| peers._caps | 131 | 0.02 |
