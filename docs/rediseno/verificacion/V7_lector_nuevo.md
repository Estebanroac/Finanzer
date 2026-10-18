# V7 · Lectura de un usuario nuevo (PM, 2026-10-18)

Un lector que no conoce Finanzer recorrió la v4 (`rediseno/v4` fa9e870, replay) en 1440 y 390 px para AAPL, JPM y PLTR
con 8 preguntas de inversor, y descargó los PDF. Respondió del todo 4 de 8 preguntas; el resto, parcial, casi siempre
por **jerga sin explicar, cifras de periodos distintos sin decirlo y textos del motor que se contradicen o exponen su
mecánica**. Lo que mejor funciona: el bloque superior (tres preguntas con escala), la rentabilidad por periodo, «lo que
exige el precio» con su tasa base, las páginas 1–2 del PDF y el móvil sin desplazamiento horizontal.

Reparto (cada arreglo en origen, con test; ningún veredicto cambia):

## Motor y textos de `display` (sesión E4, rama `rediseno/e4-portada`; golden con `GOLDEN_DIFF_V7.md`)
| # | Problema (cita) | Arreglo |
|---|---|---|
| M1 | «El precio excede en 66% el valor intrínseco» con $343 vs $116 (es +195 %) | «El valor estimado ($116) está un 66 % por debajo del precio ($343)»; «margen de seguridad» explicado o retirado de la prosa |
| M2 | ROE 119.9 % (Ficha) vs 151.9 % (DuPont); crecimientos 27.3 % / 23.6 % / 33.4 % en el mismo bloque; FCF−SBC 31.7 % vs 41.0 % | Cada cifra de la prosa con su periodo (TTM / FY2025 / 3 años / 7 años) en el mismo renglón |
| M3 | «FCF estable (-3.9%)»; KPI «En rango» sin referencia; deuda «Descuento profundo»; Piotroski bajo «Crecimiento»; «Cobertura: Sin dato» + «el EBIT cubre 40.7 veces» | Etiquetas coherentes con el número: «en descenso», «sin referencia», vocabulario de deuda («muy por debajo de su industria»), categoría correcta, cobertura reconciliada |
| M4 | Mecánica interna expuesta: «-0.53 × 6 (máximo con 5 miembros)», «^TNX no disponible… valor de config», «endpoint /api/v2/scenario», «grid completo (68.77–218.01)», separador pegado «múltiplosForward», «(factor 1.0): sin ajustar 15 → ajustado a 15» | La fórmula al anexo técnico; textos para el lector sin «config/endpoint/grid»; separadores; omitir el ajuste cuando no ajusta |
| M5 | «DCF (upside) −4» en la cabecera mientras otro bloque dice «DCF no concluyente… no se usa en el score»; «P/B informativo: no puntúa» junto a «Bloque P/B y P/TBV −2» | Nombres que digan qué puntúa de verdad («DCF inverso…», «DCF directo: descartado, no puntúa»); un único criterio por bloque |
| M6 | «POR QUÉ ES «MADURA»: No es un banco… ni…» (definición por negación); anglicismos («Cash Flow Operativo», «EPS moderado», «Crecimiento Ingresos 3Y», «compañías growth»); frases duplicadas en el rango de 52 semanas | Definición en positivo de cada arquetipo; pasada de traducción de etiquetas del motor; sin duplicados |
| M7 | S&P 500 «Precio» = «Con dividendos» (+72,0 %): el índice ^GSPC no reparte dividendos; «/accion: serie… 2 años» con tablas de 3A/5A | Rentabilidad total del mercado con una serie con dividendos (SPY ajustado o ^SP500TR, en config) y dicho; texto de la fuente con el periodo real |

## Presentación (sesión E3, rama `rediseno/v4`, tras fusionar lo anterior)
| # | Problema | Arreglo |
|---|---|---|
| P1 | «Confianza alta» junto a «fiabilidad del DCF baja» confunde | Línea fija bajo la confianza (de las definiciones del motor/tooltips): qué significa y que el DCF directo descartado no puntúa; «?» en las tres puntuaciones |
| P2 | «RIESGOS 0» se lee «no hay riesgos» | «Banderas rojas del modelo: 0»; bloque «Concentración» con el mayor segmento y la geografía que cae (datos de segmentos), enlazado a /negocio |
| P3 | Jerga sin definir (FCF − SBC, ROTE, PEAD, Momentum 12-1, XLK…) | «?» en etiquetas del bloque superior y del capítulo 3; glosario de 1 página en el PDF (desde `metric_definitions.json`) |
| P4 | El capítulo 2 «De dónde vienen sus ingresos» abre con el DuPont | Lectura y visual del capítulo 2 desde los segmentos (producto si existe, geografía como segunda línea); el DuPont pasa a Calidad; el PDF con el desglose por producto |
| P5 | Rivales poco visibles; «mediana» vs «agregado»; «mejor en 5 de 8» destacando las dos peores; la tabla de JPM del PDF sin su fila; CRWD P/E 4366x sin aviso | Capítulo 6 con 3 rivales y «Ver comparador de rivales →»; «agregado»; destacar una mejor y una peor; fila de la empresa en el PDF; P/E fuera de rango «n. s.» (umbral en config) |
| P6 | Menores: buscar por nombre + Enter no hace nada; «Descargar el informe en PDF →» lleva a /conclusion; cabecera repetida en subpáginas (móvil larguísimo) | Enter con el primer resultado; enlace al PDF; cabecera compacta en las páginas de profundidad |
