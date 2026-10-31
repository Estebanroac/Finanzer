# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-31T00:20:20. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.8 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 444 MB | < 450 MB |
| p95 de /api/analysis en caché | ❌ | 2.986 s (n = 272) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 1.0 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 7.583 s; tenencia máx. 13.878 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 272 | 0 | 0 | 0.035 | 2.986 | 12.175 |
| analysis_cold | 10 | 0 | 0 | 3.904 | 8.792 | 8.792 |
| page | 361 | 0 | 0 | 0.004 | 0.083 | 0.185 |
| pdf | 38 | 0 | 0 | 0.09 | 0.292 | 7.377 |
| peers | 358 | 0 | 0 | 0.004 | 0.058 | 0.136 |
| prices | 272 | 0 | 0 | 0.098 | 0.186 | 2.5 |
| scenario | 82 | 0 | 0 | 0.003 | 0.031 | 0.06 |
| search | 48 | 0 | 0 | 0.534 | 1.239 | 1.856 |
| segments | 272 | 0 | 0 | 0.001 | 0.019 | 0.086 |
| sparklines | 89 | 0 | 0 | 0.005 | 0.105 | 5.211 |
| trending | 89 | 0 | 0 | 0.01 | 0.032 | 0.069 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 6.16 s.
- Primer análisis de cada empresa: AAPL 6.16 s (200), JPM 4.11 s (200), O 4.08 s (200), NEE 4.03 s (200), XOM 3.5 s (200), PLTR 2.92 s (200), RIVN 3.37 s (200), BCS 4.45 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 148.5, 'cards': 90, 'listo': 48}.
- Memoria: pico del calentamiento 400.1 MB; al empezar la carga 400.1 MB; pico de la carga 443.9 MB (picos por separado: RSS 443.9 MB, huella física 383.9 MB).

Turnos de análisis: 328 de usuarios y 125 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 1.49 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 132 | 32.1 |
| data_fetcher._data_cache | 186 | 16.84 |
| price_history._cache | 64 | 3.3 |
| yf_adapter._stmt_cache | 336 | 2.82 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 1.79 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.39 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 217 | 0.04 |
