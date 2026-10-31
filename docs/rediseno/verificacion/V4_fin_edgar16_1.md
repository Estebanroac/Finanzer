# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T04:14:06. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.9 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 345 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.493 s (n = 244) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -8.1 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.757 s; tenencia máx. 8.224 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 244 | 0 | 0 | 0.026 | 0.493 | 2.884 |
| analysis_cold | 10 | 0 | 0 | 3.04 | 5.376 | 5.376 |
| page | 318 | 0 | 0 | 0.002 | 0.052 | 0.227 |
| pdf | 37 | 0 | 0 | 0.096 | 0.247 | 1.236 |
| peers | 982 | 0 | 0 | 0.002 | 0.01 | 0.147 |
| prices | 244 | 0 | 0 | 0.065 | 0.503 | 4.221 |
| scenario | 74 | 0 | 0 | 0.002 | 0.03 | 0.05 |
| search | 51 | 0 | 0 | 0.167 | 0.742 | 1.099 |
| segments | 244 | 0 | 0 | 0.001 | 0.154 | 2.378 |
| trending | 74 | 0 | 0 | 0.001 | 0.002 | 0.035 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.67 s.
- Primer análisis de cada empresa: AAPL 2.67 s (200), JPM 1.55 s (200), O 1.47 s (200), NEE 1.48 s (200), XOM 1.33 s (200), PLTR 1.63 s (200), RIVN 1.55 s (200), BCS 2.37 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 117.2, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 297.1 MB; al empezar la carga 297.1 MB; pico de la carga 345.2 MB (picos por separado: RSS 316.1 MB, huella física 345.2 MB).

Turnos de análisis: 299 de usuarios y 79 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 65 | 14.75 |
| data_fetcher._data_cache | 160 | 11.2 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 1.49 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
