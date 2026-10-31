# Rendimiento de la v4 con F8 y F9 (`rendimiento/v4f8-memoria`)

Encargo del PM (28-oct-2026), tras la pasada final de E2b (`V4_CIERRE.md` §2.2 y §2.3 en 461e9266):

- **Objetivos:** pico de memoria ≤ 380 MB en la carga de 12 min y análisis en frío con p50 ≤ 4 s.
- **Restricción:** golden idénticos byte a byte y ninguna cifra distinta.

La rama sale de 461e9266. No hay push, ni merge, ni stash.

## 1. Resultado

Carga de 12 min (`tools/load_test.py`, 20 usuarios, fuentes reales). Tres corridas por lado: hoy, con la misma herramienta, el mismo build y la misma máquina, alternando. La primera del «antes» es la de E2b.

| Medida | Antes (461e9266) | Después (esta rama) | Objetivo |
|---|---|---|---|
| Pico de memoria (máx. de RSS y huella física) | 435 / 386 / 452 MB: **mediana 435** | 384 / 360 / 374 MB: **mediana 374** | ≤ 380 MB |
| Análisis en frío, p50 | 3,47 / 2,79 / 2,65 s | 2,52 / 2,20 / 1,94 s | — |
| Análisis en frío, p95 | 4,90 / 3,50 / 3,61 s | 5,00 / 3,01 / 3,53 s | — |
| Todos los criterios de la carga en verde | 1 de 3 (452 MB > 450; +32,5 MB en la 2.ª mitad) | **3 de 3** | — |

V2 (los 7 tickers de la V2 oficial, 3 a la vez, servidor nuevo en cada corrida, antes y después alternados):

| Medida | Antes | Después | Objetivo |
|---|---|---|---|
| Análisis en frío, p50 | 4,58 / 4,38 s | **2,99 / 3,79 s** | ≤ 4 s |
| Análisis en frío, p95 | 5,17 / 4,64 s | 4,33 / 6,50 s | — |
| Rivales hasta completar, p50 | 112 / 120 s | 108 / 136 s | (ver §4) |

Prueba controlada, sin la aleatoriedad de la carga: 42 análisis típicos de rivales, uno tras otro en un proceso, alternando antes y después dos veces.

| Medida | Antes | Después |
|---|---|---|
| RSS al final | 436 / 469 MB | 418 / 451 MB (−18 MB en las dos parejas) |
| Tiempo total | 261 / 263 s | 232 / 230 s (−11 %) |

- **Mismo resultado:**
  - `diff_golden` (panel y local), `pdf_v2_golden` y `contract_forced` regenerados en el orden de siempre: ningún archivo de golden cambia (byte a byte).
  - Backend: 6.031 pasadas, 0 fallidas.
- **Comprobaciones en vivo, versión de antes frente a la nueva, JSON entero:**
  - segmentos: 29 de 29 empresas;
  - `sec_edgar.fetch` (hechos, pendientes, filings, ficha, país, portada y cautiva): 15 de 15 y 12 de 12;
  - lectores XBRL: 6 de 6 instancias reales.
- **Variación:** con la misma carga, el pico varía ±40 MB entre corridas (`V4_VERIFICACION.md` §2: el mismo código del «antes» dio 386 y 452 MB). Por eso hay tres corridas por lado.

Informes en `verificacion/`:

- cargas de 12 min: `PERF_carga_12min_antes`, `_antes2`, `_despues2`, `_despues3` y `_despues4` (`.json` y `.md`);
- V2: `PERF_V2_{antes,despues}_{1,2}.json`.

`PERF_carga_12min_despues` (431 MB) es anterior a los cambios 6 y 7 (§2): no cuenta en la tabla.

## 2. Qué se cambió (un commit por cambio)

| # | Commit | Causa medida | Cambio | Efecto medido |
|---|---|---|---|---|
| 1 | 16ddd2be | — | Herramientas: `tools/perf_frio.py` (cada petición y fase de un análisis en frío; `PERF_BACKEND` mide el «antes»), `tools/perf_identidad.py`, pieza «portada» en `memory_profile.py` | — |
| 2 | 2e0e3615 | La caché de EDGAR descargaba la misma clave tantas veces como llamadas a la vez (`company_tickers.json` ×4 con 4 análisis en frío) | Una descarga por clave; la espera detrás de otro es cola perdonada (como `Budget.turn`) | Menos peticiones al ritmo de la SEC (0,12 s cada una, compartido) |
| 3 | d3f8eb83 | F9 · R1 puso `segments.build` (geografía para la prima de riesgo país) en serie en cada análisis: otra descarga de submissions, índice, instancia y etiquetas (0,6–2 s; JPM 1,0 de 5,6 s) | La lista de anuales sale de `sec_edgar.submissions` (misma respuesta); descarga anticipada en segundo plano en cuanto EDGAR termina, que `build` toma | JPM: segmentos 1,0 → 0,16 s; 7 tickers en serie: p50 2,63 → 1,97 s |
| 4 | 779fda6f | `pead` pedía `/stock/earnings` en serie al final | En paralelo con el ETF, los titulares y el calendario (pead lo lee de la caché) | −0,16 a −0,35 s por análisis |
| 5 | 16fb8bf3 | Las notas de texto de las instancias NIIF (BCS: una de 8,6 M de caracteres) se construían en memoria aunque no se leyeran | `sec_edgar.xbrl_top_elements`: no guarda el texto de los hechos que no se leen | BCS segmentos 39 → 1 MB de pico; instancia 23 → 1 MB |
| 6 | 0b99ecca | La instancia pendiente (10-Q/6-K que companyfacts aún no trae) se tenía entera en memoria: C 48 MB, HSBC 45, BCS 26; en la carga, los escalones de memoria coinciden con esos rivales en la cola de fondo | A un archivo temporal, con las reglas de `_get` | C, HSBC y BCS: ~3 MB |
| 7 | 6d1836c4 | El JSON de submissions de los bancos que emiten folletos a diario (JPM: 16 columnas de 26.501 filings) | Solo las 6 columnas de `filings.recent` que se leen | JPM 22 → 11,5 MB de pico |

Probado y descartado, porque no mejora lo medido:

- **Soltar los bytes de companyfacts al decodificarlos:** 23,8 → 23,1 MB, el pico está en otra parte.
- **Vaciar la raíz de `iterparse`:** sin efecto; el pico eran las notas de texto (cambio 5).

## 3. Dónde estaba la memoria (cómo se encontró)

- **Un análisis suelto no explica la subida.** El proxy en el proceso (8 análisis calientes y 10 en frío, 4 a la vez) da el mismo pico en el código del 18-oct, en 461e9266 y ahora (272–303 MB). Lo mismo con tracemalloc: AAPL y JPM ~2 MB más que el 18-oct.
- **La carga sube por escalones con los rivales en la cola de fondo.** Cruzando la serie de memoria con los turnos de análisis (`/__load/slots`), la memoria sube a escalones de ~20 MB mientras corren análisis de fondo, uno a uno, y baja cuando paran.
- **Los escalones son empresas concretas.** Analizando 42 rivales típicos uno tras otro y midiendo el RSS después de cada uno:
  - C: +54 MB;
  - JPM: +51 MB;
  - GM: +34 MB;
  - BCS: +22 MB.
- **La causa, pieza a pieza, con tracemalloc dentro de `sec_edgar.fetch`:** las instancias pendientes en memoria (C, HSBC, BCS) y el JSON de submissions de los grandes bancos. Con los cambios 6 y 7:
  - C: +54 → +29 MB;
  - final de la serie de 42: 456 → 420 MB.
- **GM (+34 MB) sigue.** Hace las mismas peticiones que cualquier otra empresa y su pico de tracemalloc no sube: es memoria nativa o fragmentación, sin una pieza a la que atribuirla.

## 4. Para el PM

1. **Memoria.** La mediana del pico baja de 435 a 374 MB (−61 MB) y la peor corrida queda en 384 MB. El margen frente a los 512 MB de Render pasa del 15 % al 25–30 %, aunque la peor corrida queda 4 MB por encima del objetivo.
   - En la prueba controlada el efecto es menor (−18 MB). Parte de lo que se deja de pedir (20–45 MB de pico en C, HSBC, BCS y JPM) ya no lo devolvía el proceso: es fragmentación.
   - Para E6, en Render (Linux): con muchos hilos (EDGAR, contexto de mercado, descargas anticipadas, Yahoo), el malloc de glibc reparte la memoria en una arena por hilo y el RSS crece. `MALLOC_ARENA_MAX=2` en el entorno lo suele bajar bastante. No lo puedo medir en macOS: es una propuesta para medir allí, no un cambio.
2. **Análisis en frío.** Con 3 a la vez y rivales en la cola (V2), p50 de 2,99 y 3,79 s (antes, 4,58 y 4,38). En la carga, 1,94–2,52 s (antes, 2,65–3,47).
3. **Rivales: no es EDGAR.** Su tiempo lo marcan:
   - las capitalizaciones de Finnhub: hasta 20 por empresa, con 1,5 s entre ellas por el límite gratuito de 60/min (`[peers] max_cap_lookups`, `finnhub_min_interval_s`);
   - la cola de fondo, que comparten los rivales de las 3 empresas.

   El «76 s» del 18-oct era la mediana de 51 empresas distintas de estas 7. En las comunes, JPM tardaba 120 s; hoy, 64–88 s. Bajarlo exigiría tocar ese ritmo, que es el límite del plan gratuito: no lo toqué.
4. **NU, «EDGAR no respondió a tiempo».** La causa era el presupuesto de EDGAR con 3 análisis a la vez: todas las peticiones a la SEC van en fila, una cada 0,12 s. Cada análisis hace ahora menos peticiones (submissions una vez, sin claves repetidas en paralelo) y los segmentos van en segundo plano. En las 4 corridas de la V2 y en las 6 cargas de hoy: 0 fallos y 0 errores 5xx.
5. **Observación (no tocada).**
   - **Precalentado de tendencias vacío:** en todas las cargas de hoy (antes y después, también la de E2b) termina en 18–21 s con 0 tarjetas. El 18-oct hacía 30 análisis. La carga de hoy no incluye esos 30 análisis de fondo; si vuelven, el pico subirá.
   - **`/api/v2/segments` sin análisis previo:** pide la info completa de Yahoo solo para saber si la empresa es aseguradora (JPM: 12 peticiones, 4,8 s, +100 MB). En la web siempre va después del análisis, que deja esa info en caché, así que no afecta a la carga.
