# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T14:51:38. Backend: finanzer_next-v4f8pr/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 188.0 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 372 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.723 s (n = 140) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 3.3 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.212 s; tenencia máx. 11.393 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 140 | 0 | 0 | 0.023 | 0.723 | 1.449 |
| analysis_cold | 10 | 0 | 0 | 1.823 | 2.961 | 2.961 |
| page | 181 | 0 | 0 | 0.002 | 0.058 | 0.112 |
| pdf | 22 | 0 | 0 | 0.088 | 0.153 | 0.206 |
| peers | 608 | 0 | 0 | 0.001 | 0.039 | 0.318 |
| prices | 140 | 0 | 0 | 0.101 | 2.773 | 3.255 |
| scenario | 39 | 0 | 0 | 0.001 | 0.016 | 0.048 |
| search | 26 | 0 | 0 | 0.185 | 0.399 | 0.598 |
| segments | 140 | 0 | 0 | 0.001 | 0.023 | 0.154 |
| sparklines | 41 | 0 | 0 | 0.005 | 0.983 | 1.911 |
| trending | 41 | 0 | 0 | 0.006 | 0.017 | 0.018 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 6.41 s.
- Primer análisis de cada empresa: AAPL 6.41 s (200), JPM 8.12 s (200), O 8.22 s (200), NEE 5.89 s (200), XOM 5.71 s (200), PLTR 4.75 s (200), RIVN 3.78 s (200), BCS 11.4 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 69.9, 'cards': 90, 'listo': 38}.
- Memoria: pico del calentamiento 334.5 MB; al empezar la carga 334.5 MB; pico de la carga 371.9 MB (picos por separado: RSS 349.6 MB, huella física 371.9 MB).

Turnos de análisis: 180 de usuarios y 40 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 103 | 33.58 |
| data_fetcher._data_cache | 86 | 6.22 |
| finnhub_fallback._cache | 96 | 3.76 |
| price_history._cache | 54 | 2.76 |
| yf_adapter._stmt_cache | 257 | 2.21 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 42 | 0.29 |
| universe._state | 4 | 0.29 |
| analysis_queue._summaries | 34 | 0.17 |
| peers._caps | 123 | 0.02 |
