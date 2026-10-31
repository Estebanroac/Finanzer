# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T03:27:44. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.4 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 340 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.372 s (n = 295) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 5.8 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.72 s; tenencia máx. 2.75 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 295 | 0 | 0 | 0.016 | 0.372 | 2.754 |
| analysis_cold | 10 | 0 | 0 | 1.509 | 2.253 | 2.253 |
| page | 398 | 0 | 0 | 0.002 | 0.053 | 0.138 |
| pdf | 40 | 0 | 0 | 0.082 | 0.227 | 0.353 |
| peers | 910 | 0 | 0 | 0.002 | 0.027 | 0.106 |
| prices | 295 | 0 | 0 | 0.066 | 0.255 | 2.8 |
| scenario | 83 | 0 | 0 | 0.002 | 0.031 | 0.063 |
| search | 57 | 0 | 0 | 0.095 | 0.266 | 0.32 |
| segments | 295 | 0 | 0 | 0.001 | 0.044 | 2.662 |
| trending | 103 | 0 | 0 | 0.001 | 0.003 | 0.026 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.58 s.
- Primer análisis de cada empresa: AAPL 2.58 s (200), JPM 1.65 s (200), O 1.58 s (200), NEE 1.57 s (200), XOM 1.53 s (200), PLTR 1.45 s (200), RIVN 1.61 s (200), BCS 2.04 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 60.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 273.1 MB; al empezar la carga 262.7 MB; pico de la carga 340.3 MB (picos por separado: RSS 289.9 MB, huella física 340.3 MB).

Turnos de análisis: 353 de usuarios y 84 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 72 | 25.14 |
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
