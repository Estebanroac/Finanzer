# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T15:01:15. Backend: finanzer_next-v4cola/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.7 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 413 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 1.146 s (n = 330) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 4.2 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 4.632 s; tenencia máx. 7.423 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 330 | 0 | 0 | 0.034 | 1.146 | 6.927 |
| analysis_cold | 10 | 0 | 0 | 2.727 | 4.26 | 4.26 |
| page | 442 | 0 | 0 | 0.003 | 0.082 | 0.263 |
| pdf | 47 | 0 | 0 | 0.099 | 0.365 | 0.768 |
| peers | 268 | 0 | 0 | 0.003 | 0.065 | 0.264 |
| prices | 330 | 0 | 0 | 0.103 | 0.242 | 1.384 |
| scenario | 101 | 0 | 0 | 0.002 | 0.047 | 0.088 |
| search | 61 | 0 | 0 | 0.156 | 0.343 | 0.569 |
| segments | 330 | 0 | 0 | 0.001 | 0.034 | 0.613 |
| sparklines | 112 | 0 | 0 | 0.004 | 0.025 | 1.815 |
| trending | 112 | 0 | 0 | 0.007 | 0.013 | 0.036 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.37 s.
- Primer análisis de cada empresa: AAPL 3.37 s (200), JPM 1.96 s (200), O 2.18 s (200), NEE 2.18 s (200), XOM 2.21 s (200), PLTR 1.44 s (200), RIVN 1.56 s (200), BCS 2.92 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 84.8, 'cards': 90, 'listo': 49}.
- Memoria: pico del calentamiento 347.6 MB; al empezar la carga 326.6 MB; pico de la carga 412.6 MB (picos por separado: RSS 412.6 MB, huella física 406.5 MB).

Turnos de análisis: 395 de usuarios y 204 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 134 | 29.71 |
| data_fetcher._data_cache | 184 | 16.66 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.82 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 1.46 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 217 | 0.04 |
