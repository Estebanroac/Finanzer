> **SUSTITUIDO (2026-10-17):** el usuario lo consideró simplista. El diseño vigente es
> `docs/superpowers/specs/2026-10-17-rediseno-experiencia-design.md` (maquetas en `docs/rediseno/maquetas/`).
> Se conserva como historial. El prompt `prompts/R1_prototipo.md` también queda sustituido.

# Plan de rediseño de la presentación (web y PDF)

> Planificador, 2026-10-17. Origen: revisión del usuario de finanzer.app tras desplegar las fases 0–7 del plan de
> fiabilidad ("tenemos que tomarnos esto en serio"). El motor ya es fiable; **la presentación no está a su altura**.
> Trazabilidad: este plan + `docs/fiabilidad/BITACORA.md` (fase "R") + prompts en `docs/rediseno/prompts/`.

## 0. Diagnóstico

La web creció por acumulación: cada etapa del motor añadió una pestaña, una tabla o un desplegable. Resultado
(medido en producción el 2026-10-17, AAPL):

- **9 pestañas** y **36 secciones plegadas** dentro de ellas (`<details>` y similares en 7 pestañas). La información
  más valiosa (tabla de solidez, tablas de rentabilidad y valoración, detalle técnico) está detrás de 2–3 clics.
- **Jerarquía débil**: la cabecera de puntuación junta dos indicadores circulares con un bloque de texto amarillo
  pequeño que no se lee; el veredicto compite con todo lo demás.
- **Espacio mal usado**: márgenes grandes vacíos y contenido apretado en columnas estrechas.
- **Faltan datos que un inversor espera ver**: el comportamiento del precio en el tiempo (gráfica y rentabilidades por
  periodo), aunque el backend ya descarga 5 años de precios diarios; el detalle de cada criterio Piotroski (los
  valores, no solo "cumple").
- **Contexto de mercado**: tablas grises y una lista plana de titulares en inglés al final; las noticias existen pero
  no se ven. El tono resulta "triste y deprimente".
- **Crecimiento**: el rango de precio de 52 semanas es un chip gris sin color ni lectura.
- **PDF**: no es interactivo (sin índice con enlaces ni marcadores), huecos en blanco entre secciones, sin gráficas de
  precio.

## 1. Decisiones del usuario (2026-10-17)

| # | Decisión | Elegido |
|---|---|---|
| R-D1 | Navegación | **Informe de una sola página con índice fijo** (scroll-spy) a la izquierda en escritorio y barra superior deslizable en móvil. **Nada plegado**: lecturas, gráficas y tablas siempre visibles. Se retiran las pestañas |
| R-D2 | PDF | **Mismo motor (reportlab), rediseñado** con el sistema visual de la web: índice con enlaces, marcadores, enlaces externos, gráficas y maquetación sin huecos. Se conservan los tests (guardián, geometría, golden de texto) |

| R-D3 | Protección de lo existente | **Prototipo aprobado antes de implementar** (usuario: "me gustaría un prototipo aprobado antes de que implementes los cambios. Para proteger lo que existe"). Hasta esa aprobación: ningún cambio en `frontend/src`, `backend/`, `config/` ni en `frontend/out`; el prototipo vive en su propia rama y worktree, es estático, no se fusiona, no se sube y no se despliega |

Decisiones que tomará el usuario sobre las maquetas (punto de parada de R1): dirección visual, orden de las secciones,
densidad, y tratamiento de las noticias en inglés.

## 2. Principios de diseño

1. **Un informe, no un panel de control.** Se lee de arriba abajo como un buen artículo de análisis: primero la
   conclusión, luego la evidencia, después el detalle. Cada sección sigue la misma gramática: **lectura** (2–3 frases
   en lenguaje llano) → **visual clave** → **tabla completa** → nota de método (pequeña, con su tooltip).
2. **Cero pliegues para información.** Solo pueden quedar como desplegable el anexo técnico (D1) y las notas de
   metodología largas. Si una tabla parece "demasiado", se resuelve con mejor formato (agrupación, columnas, gráficos
   pequeños), no escondiéndola.
3. **Navegar sin buscar.** Índice fijo con la sección activa; cada sección con ancla compartible
   (`/stock/AAPL#valoracion`); "volver arriba"; atajos de teclado opcionales.
4. **Jerarquía visual clara.** Un solo veredicto protagonista; los números grandes solo donde importan; el color
   significa algo (bueno / atención / malo / neutro) y es coherente en toda la página y en el PDF.
5. **Usar el ancho.** Rejilla de 12 columnas con anchura máxima de lectura cómoda para el texto (~70 caracteres) y
   bloques anchos para gráficas y tablas; dos columnas donde el contenido lo permite.
6. **Tono sobrio y vivo, no lúgubre.** Fondo oscuro de marca, pero con superficies diferenciadas, acentos de color con
   significado y gráficas que respiran. Las noticias con tarjeta, fuente, fecha y resumen.
7. **Honestidad intacta.** El rediseño no cambia ninguna cifra ni lectura: el guardián narrativo, las invariantes, el
   contrato de la web y la comprobación geométrica del PDF siguen pasando. Lo técnico (D5) sigue siendo solo contexto.
8. **Rendimiento y accesibilidad.** Carga percibida rápida (esqueletos mientras llega el análisis), contraste AA,
   navegación por teclado, `prefers-reduced-motion`, móvil a 375 px sin scroll horizontal.

## 3. Arquitectura de la información (propuesta para las maquetas)

| # | Sección | Contenido (todo visible) | Datos nuevos |
|---|---|---|---|
| 1 | **Resumen** | Nombre, precio y variación del día; veredicto en una frase; Calidad y Precio con su nivel; confianza en lenguaje llano; 3–4 claves (fortaleza, a vigilar, contexto); pre-mortem breve | — (rediseño de la cabecera actual) |
| 2 | **Precio en el tiempo** | Gráfica interactiva con rangos 1S / 1M / 3M / 6M / YTD / 1A / 3A / 5A; comparación opcional con S&P 500 y ETF del sector (base 100); volumen; tabla de rentabilidades por periodo (precio y total con dividendos) frente a mercado y sector; caída máxima; posición en el rango de 52 semanas con color y lectura | **Endpoint de serie de precios** (ya descargada en el backend: `price_series`), rentabilidades por periodo |
| 3 | **Valoración** | Lectura; métodos (múltiplos, DCF directo con fiabilidad, DCF inverso "el precio exige…", Graham donde aplique); gráfico de múltiplos frente a referencia; tabla completa; sensibilidad del DCF | — |
| 4 | **Rentabilidad** | Lectura; ROIC vs WACC, ROCE, márgenes y su tendencia; DuPont; tabla completa | — |
| 5 | **Solidez** | Lectura; deuda, cobertura, liquidez; **tabla de solidez visible**; Altman con su lectura | — |
| 6 | **Crecimiento** | Lectura; ingresos, BPA y FCF por acción en el tiempo; perímetro y efecto divisa declarados | — |
| 7 | **Comparativa** | La misma información en formato compacto: gráfico de puntos/barras "empresa frente a referencia" agrupado por familia (valoración, rentabilidad, solidez, crecimiento) con la brecha coloreada; tabla completa debajo, sin pliegue | — |
| 8 | **Evaluación institucional** | Piotroski con **los 9 criterios en tarjetas**: qué mide, valor de este año y del anterior, cumple/no cumple y por qué importa; Altman; salud bancaria en financieras | **Valores por criterio Piotroski** (año actual y anterior) |
| 9 | **Histórico** | Lo actual (se conserva tal cual) + series anuales en gráfica | — |
| 10 | **Contexto de mercado y noticias** | Señales (momentum, tendencia, volatilidad, fuerza relativa) como tarjetas con lectura y color; noticias en tarjetas (fuente real, fecha, resumen, imagen si hay, enlace directo); próxima fecha de resultados; nota conductual con tono neutro | **Noticias enriquecidas** (resumen, imagen, fuente original, URL directa de Finnhub `company-news`), fecha de resultados si existe |
| 11 | **Alertas** | Integradas en la sección que corresponde (no una pestaña aparte), más un resumen en la sección 1 | — |
| 12 | **Anexo técnico** | Único plegable (D1) | — |

El orden es una propuesta: lo decide el usuario sobre las maquetas.

## 4. Etapas

| Etapa | Qué | Entregable | Parada |
|---|---|---|---|
| **R1** | Inventario de la web actual (cada bloque, cada pliegue, cada dato) + arquitectura de la información + sistema visual + **prototipo navegable** con datos reales de 4 tickers (AAPL, JPM, O, PLTR) y del PDF (páginas clave) | `R1_INVENTARIO.md`, `R1_SISTEMA_VISUAL.md`, prototipo **estático y aislado** (rama `rediseno/r1-prototipo`, worktree propio) que lee instantáneas JSON exportadas; no toca la app | **Sí:** el usuario aprueba la dirección visual, el orden y la densidad (2 direcciones visuales para elegir) |
| **R2** | Datos nuevos en el backend: serie de precios por rango, rentabilidades por periodo (precio y total) frente a S&P 500 y sector, valores por criterio Piotroski, noticias enriquecidas, fecha de resultados | Endpoints y campos con tests, guardián para todo texto nuevo, contrato de la web | Diff de golden aprobado |
| **R3** | Web nueva: página de informe con índice, sección por sección, móvil, accesibilidad, esqueletos de carga | Página nueva en producción (la vieja se retira) | **Sí:** revisión visual del usuario en local antes del push |
| **R4** | PDF rediseñado con el mismo sistema: portada, índice con enlaces, marcadores, gráficas de precio y comparativa, sin huecos, enlaces externos | PDF nuevo; comprobación geométrica ampliada (huecos máximos) | **Sí:** revisión del usuario de 4 PDF |
| **R5** | Verificación y despliegue: guardián, invariantes, contrato, geometría, capturas por arquetipo, rendimiento (Lighthouse), revisión externa con 2–3 personas que no conozcan la app | Informe de cierre | "ok, pushea" |

**Ninguna etapa de implementación (R2–R5) empieza sin el prototipo aprobado (R-D3).** El prototipo simula los datos
nuevos (serie de precios desde `tests/fixtures/prices/`, criterios Piotroski y noticias con datos de muestra marcados
como tales) para que el usuario los vea antes de que existan en el backend.

## 5. Criterios de terminado del rediseño

- Ninguna información de valor plegada; anexo técnico como único desplegable.
- Cualquier sección a ≤ 1 clic desde cualquier punto (índice) y enlazable por URL.
- Gráfica de precio con rangos de 1 semana a 5 años y rentabilidades por periodo frente a mercado y sector.
- Piotroski con los 9 criterios y sus valores.
- Noticias visibles en tarjetas con fuente y enlace directo.
- PDF con índice enlazado, marcadores, gráficas y sin huecos mayores que el máximo definido en R1.
- Guardián, invariantes, contrato y geometría en verde; ninguna cifra ni lectura cambia por el rediseño.
- Móvil a 375 px sin scroll horizontal; contraste AA; Lighthouse de rendimiento y accesibilidad ≥ 90 en escritorio.
