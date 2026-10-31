# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T03:58:43. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.5 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 384 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.357 s (n = 289) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 57.6 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.111 s; tenencia máx. 3.72 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 289 | 0 | 0 | 0.017 | 0.357 | 3.602 |
| analysis_cold | 10 | 0 | 0 | 1.627 | 2.982 | 2.982 |
| page | 392 | 0 | 0 | 0.002 | 0.041 | 0.144 |
| pdf | 40 | 0 | 0 | 0.092 | 0.262 | 0.438 |
| peers | 914 | 0 | 0 | 0.001 | 0.013 | 0.06 |
| prices | 289 | 0 | 0 | 0.063 | 0.141 | 1.798 |
| scenario | 87 | 0 | 0 | 0.002 | 0.02 | 0.063 |
| search | 58 | 0 | 0 | 0.122 | 0.561 | 1.123 |
| segments | 289 | 0 | 0 | 0.001 | 0.051 | 2.31 |
| trending | 103 | 0 | 0 | 0.001 | 0.01 | 0.041 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.75 s.
- Primer análisis de cada empresa: AAPL 3.75 s (200), JPM 1.58 s (200), O 1.56 s (200), NEE 1.48 s (200), XOM 1.71 s (200), PLTR 1.6 s (200), RIVN 1.46 s (200), BCS 1.78 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 15.0, 'cards': 30, 'listo': 0}.
- Memoria: pico del calentamiento 265.9 MB; al empezar la carga 265.9 MB; pico de la carga 384.2 MB (picos por separado: RSS 309.6 MB, huella física 384.2 MB).

Turnos de análisis: 347 de usuarios y 54 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 103 | 25.88 |
| data_fetcher._data_cache | 114 | 8.42 |
| price_history._cache | 64 | 3.27 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 0.58 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 47 | 0.19 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
