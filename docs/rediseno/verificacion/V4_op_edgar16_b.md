# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T03:46:43. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.6 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 324 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.377 s (n = 299) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -4.3 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.117 s; tenencia máx. 3.328 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 299 | 0 | 0 | 0.015 | 0.377 | 1.651 |
| analysis_cold | 10 | 0 | 0 | 1.824 | 2.988 | 2.988 |
| page | 406 | 0 | 0 | 0.002 | 0.044 | 0.159 |
| pdf | 43 | 0 | 0 | 0.081 | 0.16 | 0.342 |
| peers | 898 | 0 | 0 | 0.001 | 0.021 | 0.126 |
| prices | 299 | 0 | 0 | 0.063 | 0.244 | 1.566 |
| scenario | 85 | 0 | 0 | 0.002 | 0.036 | 0.046 |
| search | 59 | 0 | 0 | 0.128 | 0.277 | 0.362 |
| segments | 299 | 0 | 0 | 0.001 | 0.023 | 3.343 |
| trending | 107 | 0 | 0 | 0.001 | 0.003 | 0.024 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.42 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.39 s.
- Primer análisis de cada empresa: AAPL 2.39 s (200), JPM 1.4 s (200), O 1.48 s (200), NEE 1.3 s (200), XOM 1.53 s (200), PLTR 1.56 s (200), RIVN 1.55 s (200), BCS 2.08 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 63.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 251.1 MB; al empezar la carga 244.0 MB; pico de la carga 324.4 MB (picos por separado: RSS 266.5 MB, huella física 324.4 MB).

Turnos de análisis: 360 de usuarios y 82 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 72 | 15.04 |
| data_fetcher._data_cache | 160 | 11.59 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 1.37 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
