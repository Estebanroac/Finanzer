# PDF rápido: el primer PDF y los rivales en frío

Rama `rediseno/v4-pdf-rapido`, desde ad178cb9. El usuario vio que «Descargar PDF» se quedaba cargando mucho rato. Medido
por el PM: análisis de HD en frío, 1,9 s; primer PDF, 28,9 s; segundo, 0,24 s.

## Causa (medida)

`backend/tools/perfil_rivales.py`, HD en un proceso nuevo con fuentes reales. Rivales listos a los **29,1 s**:

| Fase | Tiempo | Detalle |
|---|---|---|
| Análisis de la empresa | 2,9 s | |
| Ranking por tamaño | **16,7 s** | 12 capitalizaciones de Finnhub `profile2`, de una en una con 1,5 s de pausa (`finnhub_min_interval_s`). La red solo pone ~4 s. NVDA, con 20, tardaba 31 s |
| Análisis de los 5 rivales | **8,6 s** | Uno tras otro, en el único hilo de la cola compartida |

**Por qué el PDF tardaba ~30 s.** Espera a los rivales hasta `pdf_wait_s` = 30 s, y casi siempre agotaba esa espera.

**Los 112 s del V2.** Eran lo mismo con 3 empresas a la vez y un solo hilo.

## Arreglo

1. **Capitalizaciones en una sola petición** a Yahoo (`v7/finance/quote`): 0,1–0,5 s en lugar de 16–31 s.
   - Solo cuentan las que vienen en dólares.
   - Las cotizadas en otra moneda quedan sin capitalización. Ya pasaba con Finnhub, que no da las de fuera de EE. UU.
     (medido: MC.PA, KER.PA, RMS.PA, CFR.SW y ADS.DE, ninguna). Se ahorra su pausa.
   - Finnhub solo se usa para las que Yahoo no trae; si Yahoo falla, para todas, como antes.
2. **Un segundo hilo en la cola** (`[analysis_queue] workers = 2`) que solo toma trabajos `user` (rivales).
   - El precalentado de tendencias sigue de uno en uno.
   - La memoria la sigue acotando el turno de análisis compartido con los usuarios (`max_concurrent_analyses` = 4).
3. **«Descargar PDF» dice qué pasa** (`PdfButton`, en la cabecera y en Conclusión).
   - Sigue siendo un enlace al PDF: funciona sin JavaScript y con «abrir en otra pestaña».
   - Al pulsarlo pasa a «Preparando el PDF…», con un indicador.
   - Pasados `loading.delayMs` (300 ms), un aviso fijo abajo dice el motivo: «Preparando el PDF de HD: espera a que
     estén las comparables de su industria. Se descargará solo.».
   - El aviso va en `role="status"` / `aria-live`, en rem, a 14 px.
   - El archivo se descarga solo al llegar. Si falla, el aviso dice el motivo y se puede reintentar. La página no se
     bloquea.

## Hallazgo: Finnhub da los ADR en la moneda de su país

`profile2.marketCapitalization` de un ADR extranjero no viene en dólares:

| ADR | Finnhub | Yahoo (USD) |
|---|---|---|
| MUFG | 38.010 miles de millones (yenes) | 244 |
| IBN | 9.867 (rupias) | 106 |
| HDB | 10.581 (rupias) | 114 |
| RY | 397 (dólares canadienses) | 282 |
| TD | 299 (dólares canadienses) | 206 |
| HSBC | 222 (libras) | 293 |

El ranking anterior comparaba esas cifras con dólares. Con Yahoo, en dólares, cambian los rivales de JPM y NU.
**Aprobado por el PM** como corrección (30-oct).

- **JPM:** antes BAC, RY, TD, WFC, HSBC; ahora BAC, HSBC, RY, WFC, MUFG.
- **NU:** antes BCS, FITB, ING, PNC, USB; ahora IBN, HDB, FITB, BCS, ING (bancos de mercado emergente, su misma región,
  dentro de la banda de tamaño).
- **NVDA:** los mismos cinco, en otro orden (TSM primero).
- **Las otras 7:** idénticas.

## Medida antes y después

`backend/tools/pdf_medida.py` (`PDF_antes_despues.json`, `PDF_mcpa_despues.json`). Diez empresas en frío, cada una en
un proceso nuevo ya arrancado (con la lista de tendencias recuperada, sin volver a descargar el universo), antes y
después alternados por empresa:

| | Antes | Después |
|---|---|---|
| Primer PDF, p50 | 31,3 s | **11,3 s** |
| Rivales listos (desde el análisis), p50 | 44,1 s | **14,1 s** |

- **Primer PDF después, por empresa:** COST 7,2 s; KO 7,4; MC.PA 8,8; PLD 9,2; JPM 10,2; VZ 11,3; NVDA 11,4; AMZN 11,4;
  NU 14,3; HD 19,5.
- **HD:** 9,0 s en el perfil; la diferencia es la variación de Yahoo.
- **MC.PA:** 8,8 s ya con el arreglo de la moneda. Sin él seguía en 31,6 s, por la pausa de Finnhub en sus candidatos
  europeos.
- **Queda para después** (decisión del PM): el análisis de los rivales en paralelo y la variación de Yahoo.

**Cómo se midió.** Las primeras medidas no valen. Cada proceso nuevo descargaba el universo de tendencias (543
peticiones a Yahoo), y tras 20 arranques Yahoo limitó (HTTP 429 y crumb inválido). La herramienta ahora reutiliza la
lista guardada de la portada.

## Comprobaciones

- **Backend:** 6.496 passed, 19 skipped (las mismas 19 de la pasada final). Tests nuevos:
  - capitalizaciones en una petición y Finnhub solo para las que faltan;
  - Yahoo caído;
  - solo dólares;
  - otra moneda sin preguntar a Finnhub;
  - dos rivales a la vez;
  - el precalentado sigue de uno en uno;
  - nunca dos análisis del mismo símbolo.
- **vitest:** 151/151. `pdfDownload.test.ts` cubre el nombre del archivo y los textos.
- **`npm run check`, tsc y eslint:** 0 errores.
- **e2e:v2 contra el build:** 886 passed, 0 fallos. `pdf.spec.ts`: «Preparando…» con su motivo, la página no se bloquea,
  la descarga y el fallo con su motivo; 8/8 en los cuatro proyectos (WebKit, con descarga real).
  - Una primera corrida dio 5 fallos por tiempo en escritorio con el escaneo de E2a en marcha.
  - Solos pasaron, y la suite completa repetida dio 0 fallos.
- **Carga corta de memoria:** pendiente; necesita la máquina sola.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
