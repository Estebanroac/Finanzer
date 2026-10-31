# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T08:42:48. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.6 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 377 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.48 s (n = 280) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 89.3 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.965 s; tenencia máx. 5.438 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 280 | 0 | 0 | 0.018 | 0.48 | 4.536 |
| analysis_cold | 10 | 0 | 0 | 1.827 | 2.168 | 2.168 |
| page | 377 | 0 | 0 | 0.002 | 0.034 | 0.071 |
| pdf | 40 | 0 | 0 | 0.084 | 0.216 | 0.515 |
| peers | 932 | 0 | 0 | 0.002 | 0.019 | 0.055 |
| prices | 280 | 0 | 0 | 0.063 | 0.146 | 1.835 |
| scenario | 83 | 0 | 0 | 0.002 | 0.023 | 0.042 |
| search | 55 | 0 | 0 | 0.127 | 0.271 | 0.355 |
| segments | 280 | 0 | 0 | 0.001 | 0.137 | 2.747 |
| trending | 97 | 0 | 0 | 0.001 | 0.003 | 0.05 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.85 s.
- Primer análisis de cada empresa: AAPL 2.85 s (200), JPM 1.66 s (200), O 1.76 s (200), NEE 1.78 s (200), XOM 1.56 s (200), PLTR 1.67 s (200), RIVN 1.68 s (200), BCS 1.89 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 66.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 320.6 MB; al empezar la carga 320.6 MB; pico de la carga 377.2 MB (picos por separado: RSS 363.6 MB, huella física 377.2 MB).

Turnos de análisis: 338 de usuarios y 82 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 103 | 26.64 |
| data_fetcher._data_cache | 160 | 11.59 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 1.25 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.28 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
