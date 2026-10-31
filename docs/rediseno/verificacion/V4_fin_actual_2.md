# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T04:20:27. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.5 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 339 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.409 s (n = 304) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -1.2 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.107 s; tenencia máx. 4.833 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 304 | 0 | 0 | 0.02 | 0.409 | 1.884 |
| analysis_cold | 10 | 0 | 0 | 1.764 | 2.517 | 2.517 |
| page | 412 | 0 | 0 | 0.003 | 0.055 | 0.122 |
| pdf | 42 | 0 | 0 | 0.092 | 0.2 | 1.432 |
| peers | 889 | 0 | 0 | 0.002 | 0.019 | 0.126 |
| prices | 304 | 0 | 0 | 0.065 | 0.151 | 1.469 |
| scenario | 87 | 0 | 0 | 0.002 | 0.025 | 0.062 |
| search | 59 | 0 | 0 | 0.089 | 0.257 | 0.277 |
| segments | 304 | 0 | 0 | 0.001 | 0.027 | 3.001 |
| trending | 108 | 0 | 0 | 0.002 | 0.004 | 0.039 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.13 s.
- Primer análisis de cada empresa: AAPL 3.13 s (200), JPM 1.53 s (200), O 1.48 s (200), NEE 1.73 s (200), XOM 1.58 s (200), PLTR 1.41 s (200), RIVN 1.58 s (200), BCS 1.99 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 60.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 269.7 MB; al empezar la carga 269.7 MB; pico de la carga 339.0 MB (picos por separado: RSS 319.2 MB, huella física 339.0 MB).

Turnos de análisis: 364 de usuarios y 83 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 104 | 26.71 |
| data_fetcher._data_cache | 160 | 11.59 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 1.31 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
