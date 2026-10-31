# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T13:32:34. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.8 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 440 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.933 s (n = 379) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -0.0 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 6.001 s; tenencia máx. 7.37 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 379 | 0 | 0 | 0.032 | 0.933 | 8.012 |
| analysis_cold | 10 | 0 | 0 | 2.695 | 4.889 | 4.889 |
| page | 503 | 0 | 0 | 0.004 | 0.091 | 0.278 |
| pdf | 51 | 0 | 0 | 0.094 | 0.834 | 1.695 |
| peers | 192 | 0 | 0 | 0.004 | 0.077 | 0.158 |
| prices | 379 | 0 | 0 | 0.101 | 0.237 | 1.132 |
| scenario | 114 | 0 | 0 | 0.003 | 0.054 | 0.09 |
| search | 63 | 0 | 0 | 0.154 | 0.311 | 0.394 |
| segments | 379 | 0 | 0 | 0.001 | 0.036 | 0.139 |
| sparklines | 124 | 0 | 0 | 0.004 | 0.055 | 1.793 |
| trending | 124 | 0 | 0 | 0.006 | 0.013 | 0.075 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.41 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.08 s.
- Primer análisis de cada empresa: AAPL 3.08 s (200), JPM 1.85 s (200), O 2.36 s (200), NEE 2.94 s (200), XOM 2.81 s (200), PLTR 1.86 s (200), RIVN 2.57 s (200), BCS 3.2 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 82.1, 'cards': 90, 'listo': 48}.
- Memoria: pico del calentamiento 400.1 MB; al empezar la carga 396.1 MB; pico de la carga 440.0 MB (picos por separado: RSS 440.0 MB, huella física 348.7 MB).

Turnos de análisis: 448 de usuarios y 134 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.146 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 134 | 30.51 |
| data_fetcher._data_cache | 192 | 17.37 |
| price_history._cache | 64 | 3.33 |
| yf_adapter._stmt_cache | 336 | 2.84 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.68 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.39 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| finnhub_fallback._cache | 96 | 0.05 |
| peers._caps | 217 | 0.04 |
