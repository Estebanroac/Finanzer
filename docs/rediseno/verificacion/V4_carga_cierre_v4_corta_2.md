# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T19:31:20. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 185.0 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 444 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 1.112 s (n = 337) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -30.8 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 4.69 s; tenencia máx. 7.296 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 337 | 0 | 0 | 0.031 | 1.112 | 7.036 |
| analysis_cold | 10 | 0 | 0 | 2.263 | 4.368 | 4.368 |
| page | 449 | 0 | 0 | 0.004 | 0.09 | 0.267 |
| pdf | 46 | 0 | 0 | 0.099 | 0.547 | 2.675 |
| peers | 267 | 0 | 0 | 0.004 | 0.065 | 0.127 |
| prices | 337 | 0 | 0 | 0.1 | 0.211 | 1.142 |
| scenario | 101 | 0 | 0 | 0.004 | 0.063 | 0.125 |
| search | 58 | 0 | 0 | 0.14 | 0.348 | 1.068 |
| segments | 337 | 0 | 0 | 0.001 | 0.029 | 0.318 |
| sparklines | 112 | 0 | 0 | 0.005 | 0.051 | 2.082 |
| trending | 112 | 0 | 0 | 0.006 | 0.021 | 0.046 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.79 s.
- Primer análisis de cada empresa: AAPL 2.79 s (200), JPM 1.67 s (200), O 2.32 s (200), NEE 2.26 s (200), XOM 1.98 s (200), PLTR 1.9 s (200), RIVN 1.75 s (200), BCS 2.25 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 78.8, 'cards': 90, 'listo': 48}.
- Memoria: pico del calentamiento 392.2 MB; al empezar la carga 392.2 MB; pico de la carga 444.1 MB (picos por separado: RSS 444.1 MB, huella física 392.8 MB).

Turnos de análisis: 401 de usuarios y 132 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 133 | 33.02 |
| data_fetcher._data_cache | 198 | 17.81 |
| price_history._cache | 64 | 3.32 |
| yf_adapter._stmt_cache | 336 | 2.86 |
| finnhub_fallback._cache | 96 | 2.04 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.39 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 238 | 0.04 |
