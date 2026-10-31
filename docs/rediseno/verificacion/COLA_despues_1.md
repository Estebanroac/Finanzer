# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T14:56:27. Backend: finanzer_next-v4cola/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.3 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 405 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.758 s (n = 320) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 3.4 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 3.47 s; tenencia máx. 7.512 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 320 | 0 | 0 | 0.031 | 0.758 | 5.414 |
| analysis_cold | 10 | 0 | 0 | 2.551 | 3.565 | 3.565 |
| page | 433 | 0 | 0 | 0.004 | 0.095 | 0.228 |
| pdf | 46 | 0 | 0 | 0.104 | 0.519 | 1.12 |
| peers | 285 | 0 | 0 | 0.002 | 0.062 | 0.115 |
| prices | 320 | 0 | 0 | 0.103 | 0.198 | 1.078 |
| scenario | 97 | 0 | 0 | 0.002 | 0.049 | 0.086 |
| search | 59 | 0 | 0 | 0.13 | 0.291 | 2.193 |
| segments | 320 | 0 | 0 | 0.001 | 0.023 | 0.158 |
| sparklines | 113 | 0 | 0 | 0.004 | 0.067 | 1.968 |
| trending | 113 | 0 | 0 | 0.005 | 0.012 | 0.053 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.84 s.
- Primer análisis de cada empresa: AAPL 2.84 s (200), JPM 2.15 s (200), O 2.64 s (200), NEE 2.01 s (200), XOM 1.61 s (200), PLTR 1.72 s (200), RIVN 1.65 s (200), BCS 2.6 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 130.4, 'cards': 90, 'listo': 48}.
- Memoria: pico del calentamiento 361.3 MB; al empezar la carga 361.1 MB; pico de la carga 405.2 MB (picos por separado: RSS 399.0 MB, huella física 405.2 MB).

Turnos de análisis: 384 de usuarios y 121 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 134 | 33.34 |
| data_fetcher._data_cache | 190 | 17.02 |
| price_history._cache | 64 | 3.34 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.36 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| finnhub_fallback._cache | 96 | 0.2 |
| peers._caps | 217 | 0.04 |
