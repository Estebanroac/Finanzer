# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T04:36:32. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.9 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 334 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.425 s (n = 278) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -10.1 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.134 s; tenencia máx. 8.854 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 278 | 0 | 0 | 0.02 | 0.425 | 1.634 |
| analysis_cold | 10 | 0 | 0 | 1.668 | 2.019 | 2.019 |
| page | 372 | 0 | 0 | 0.002 | 0.048 | 0.089 |
| pdf | 39 | 0 | 0 | 0.085 | 0.187 | 0.24 |
| peers | 938 | 0 | 0 | 0.002 | 0.024 | 0.095 |
| prices | 278 | 0 | 0 | 0.064 | 0.144 | 1.349 |
| scenario | 81 | 0 | 0 | 0.002 | 0.036 | 0.057 |
| search | 56 | 0 | 0 | 0.08 | 0.229 | 0.309 |
| segments | 278 | 0 | 0 | 0.001 | 0.036 | 3.192 |
| trending | 94 | 0 | 0 | 0.001 | 0.003 | 0.043 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 6.07 s.
- Primer análisis de cada empresa: AAPL 6.07 s (200), JPM 4.34 s (200), O 3.54 s (200), NEE 3.69 s (200), XOM 3.56 s (200), PLTR 3.29 s (200), RIVN 3.53 s (200), BCS 4.19 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 135.2, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 263.8 MB; al empezar la carga 257.6 MB; pico de la carga 334.1 MB (picos por separado: RSS 326.2 MB, huella física 334.1 MB).

Turnos de análisis: 335 de usuarios y 81 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 104 | 27.49 |
| data_fetcher._data_cache | 160 | 11.59 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 0.9 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
