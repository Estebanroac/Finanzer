# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T00:57:56. 20 usuarios durante 12.0 min (carga medida: 728.5 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 430 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.097 s (n = 1185) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -8.4 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.224 s; tenencia máx. 7.327 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1185 | 0 | 0 | 0.017 | 0.097 | 6.143 |
| analysis_cold | 10 | 0 | 0 | 1.539 | 3.644 | 3.644 |
| page | 1636 | 0 | 0 | 0.002 | 0.062 | 0.23 |
| pdf | 154 | 0 | 0 | 0.096 | 0.218 | 0.495 |
| peers | 1309 | 0 | 0 | 0.002 | 0.033 | 0.113 |
| prices | 1185 | 0 | 0 | 0.066 | 0.13 | 1.972 |
| scenario | 370 | 0 | 0 | 0.001 | 0.044 | 0.098 |
| search | 249 | 0 | 0 | 0.073 | 0.235 | 0.449 |
| segments | 1185 | 0 | 0 | 0.001 | 0.012 | 5.332 |
| trending | 451 | 0 | 0 | 0.001 | 0.005 | 0.058 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 7.36 s.
- Primer análisis de cada empresa: AAPL 7.36 s (200), JPM 1.73 s (200), O 2.14 s (200), NEE 1.62 s (200), XOM 1.91 s (200), PLTR 1.56 s (200), RIVN 1.56 s (200), BCS 1.73 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 60.2, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 353.6 MB; al empezar la carga 353.6 MB; pico de la carga 429.9 MB (picos por separado: RSS 404.8 MB, huella física 429.9 MB).

Turnos de análisis: 1357 de usuarios y 123 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**
