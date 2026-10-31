# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T01:49:22. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 724.0 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 419 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.129 s (n = 1435) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -7.8 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 3.045 s; tenencia máx. 6.237 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1435 | 0 | 0 | 0.03 | 0.129 | 3.444 |
| analysis_cold | 10 | 0 | 0 | 1.58 | 3.135 | 3.135 |
| page | 1959 | 0 | 0 | 0.004 | 0.082 | 0.202 |
| pdf | 178 | 0 | 0 | 0.1 | 0.249 | 0.701 |
| peers | 933 | 0 | 0 | 0.004 | 0.053 | 0.106 |
| prices | 1435 | 0 | 0 | 0.1 | 0.166 | 1.493 |
| scenario | 422 | 0 | 0 | 0.003 | 0.057 | 0.133 |
| search | 266 | 0 | 0 | 0.114 | 0.3 | 0.749 |
| segments | 1435 | 0 | 0 | 0.001 | 0.015 | 0.257 |
| sparklines | 524 | 0 | 0 | 0.005 | 0.047 | 1.689 |
| trending | 524 | 0 | 0 | 0.008 | 0.017 | 0.068 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.55 s.
- Primer análisis de cada empresa: AAPL 2.55 s (200), JPM 1.72 s (200), O 2.11 s (200), NEE 1.74 s (200), XOM 2.22 s (200), PLTR 1.55 s (200), RIVN 1.56 s (200), BCS 2.33 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 239.9, 'cards': 90, 'listo': 46}.
- Memoria: pico del calentamiento 358.6 MB; al empezar la carga 351.9 MB; pico de la carga 419.3 MB (picos por separado: RSS 419.3 MB, huella física 350.4 MB).

Turnos de análisis: 1631 de usuarios y 91 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 131 | 28.16 |
| data_fetcher._data_cache | 158 | 14.15 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.86 |
| finnhub_fallback._cache | 96 | 2.22 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.37 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 194 | 0.04 |
