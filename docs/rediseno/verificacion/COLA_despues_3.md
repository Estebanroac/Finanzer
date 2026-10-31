# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T15:16:19. Backend: finanzer_next-v4cola/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.2 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 414 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.494 s (n = 330) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -0.0 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 5.032 s; tenencia máx. 7.974 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 330 | 0 | 0 | 0.031 | 0.494 | 6.88 |
| analysis_cold | 10 | 0 | 0 | 2.23 | 4.576 | 4.576 |
| page | 442 | 0 | 0 | 0.004 | 0.101 | 0.233 |
| pdf | 47 | 0 | 0 | 0.098 | 0.384 | 0.586 |
| peers | 271 | 0 | 0 | 0.003 | 0.061 | 0.119 |
| prices | 330 | 0 | 0 | 0.1 | 0.321 | 1.189 |
| scenario | 101 | 0 | 0 | 0.004 | 0.05 | 0.145 |
| search | 62 | 0 | 0 | 0.166 | 0.363 | 0.48 |
| segments | 330 | 0 | 0 | 0.001 | 0.025 | 0.175 |
| sparklines | 112 | 0 | 0 | 0.005 | 0.083 | 1.957 |
| trending | 112 | 0 | 0 | 0.007 | 0.023 | 0.052 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 3.14 s.
- Primer análisis de cada empresa: AAPL 3.14 s (200), JPM 2.51 s (200), O 2.57 s (200), NEE 2.83 s (200), XOM 2.46 s (200), PLTR 2.23 s (200), RIVN 2.15 s (200), BCS 3.14 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 106.1, 'cards': 90, 'listo': 49}.
- Memoria: pico del calentamiento 356.7 MB; al empezar la carga 345.0 MB; pico de la carga 414.2 MB (picos por separado: RSS 414.2 MB, huella física 399.3 MB).

Turnos de análisis: 395 de usuarios y 135 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 138 | 29.97 |
| data_fetcher._data_cache | 186 | 16.76 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.87 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 1.86 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.41 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 217 | 0.04 |
