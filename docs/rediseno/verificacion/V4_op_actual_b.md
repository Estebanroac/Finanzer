# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T03:34:00. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 303.9 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 361 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.349 s (n = 290) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -5.3 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.407 s; tenencia máx. 3.85 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 290 | 0 | 0 | 0.014 | 0.349 | 1.657 |
| analysis_cold | 10 | 0 | 0 | 1.684 | 2.021 | 2.021 |
| page | 393 | 0 | 0 | 0.002 | 0.031 | 0.1 |
| pdf | 41 | 0 | 0 | 0.086 | 0.263 | 0.522 |
| peers | 914 | 0 | 0 | 0.001 | 0.013 | 0.093 |
| prices | 290 | 0 | 0 | 0.061 | 0.169 | 1.553 |
| scenario | 84 | 0 | 0 | 0.001 | 0.021 | 0.05 |
| search | 57 | 0 | 0 | 0.088 | 0.264 | 0.296 |
| segments | 290 | 0 | 0 | 0.001 | 0.045 | 2.338 |
| trending | 103 | 0 | 0 | 0.001 | 0.003 | 0.022 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.83 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.41 s.
- Primer análisis de cada empresa: AAPL 2.41 s (200), JPM 1.59 s (200), O 1.49 s (200), NEE 1.45 s (200), XOM 1.72 s (200), PLTR 1.42 s (200), RIVN 1.45 s (200), BCS 1.9 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 57.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 291.0 MB; al empezar la carga 291.0 MB; pico de la carga 361.4 MB (picos por separado: RSS 310.2 MB, huella física 361.4 MB).

Turnos de análisis: 349 de usuarios y 84 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 104 | 42.79 |
| data_fetcher._data_cache | 160 | 11.97 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 1.07 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
