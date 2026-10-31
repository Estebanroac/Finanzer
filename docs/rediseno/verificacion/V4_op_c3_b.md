# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T03:40:20. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.7 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 352 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.397 s (n = 295) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -9.4 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.644 s; tenencia máx. 4.297 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 295 | 0 | 0 | 0.013 | 0.397 | 2.077 |
| analysis_cold | 10 | 0 | 0 | 2.555 | 4.303 | 4.303 |
| page | 400 | 0 | 0 | 0.002 | 0.047 | 0.107 |
| pdf | 41 | 0 | 0 | 0.093 | 0.255 | 1.4 |
| peers | 897 | 0 | 0 | 0.001 | 0.017 | 0.096 |
| prices | 295 | 0 | 0 | 0.06 | 0.152 | 2.056 |
| scenario | 84 | 0 | 0 | 0.001 | 0.028 | 0.052 |
| search | 59 | 0 | 0 | 0.264 | 0.635 | 1.016 |
| segments | 295 | 0 | 0 | 0.001 | 0.066 | 2.461 |
| trending | 105 | 0 | 0 | 0.001 | 0.003 | 0.024 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.83 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.66 s.
- Primer análisis de cada empresa: AAPL 2.66 s (200), JPM 1.94 s (200), O 1.54 s (200), NEE 1.46 s (200), XOM 3.58 s (200), PLTR 1.6 s (200), RIVN 1.32 s (200), BCS 2.65 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 57.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 292.6 MB; al empezar la carga 292.6 MB; pico de la carga 352.3 MB (picos por separado: RSS 290.4 MB, huella física 352.3 MB).

Turnos de análisis: 354 de usuarios y 82 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 104 | 42.7 |
| data_fetcher._data_cache | 160 | 11.97 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 0.98 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
