# Rediseño · Etapa E5: el PDF rediseñado — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un informe PDF en tamaño carta con el mismo sistema visual de la v4 (spec §3.7, maqueta 5): portada con escalas, gráfica de precio y claves; índice enlazado; marcadores del lector; "↑ índice" en cada página; enlaces a noticias y fuentes; un capítulo por sección de la historia; metodología y anexo técnico; sin huecos, comprobado automáticamente.

**Architecture:** Módulo nuevo `backend/lib/pdf_v2/` (no se toca `lib/pdf_report.py`: la web actual y su PDF siguen igual hasta E6). Consume **solo** `analysis["display"]` (incluido `display.extended`) y los endpoints de datos de la v4 llamados en proceso (serie de 5 años, segmentos, rivales en caché si existen): ninguna lectura se recalcula. Endpoint `GET /api/v2/pdf/{symbol}` (mismo semáforo que el PDF actual). Geometría y texto con las herramientas ya existentes (`tests/pdf_geometry.py`), ampliadas con el hueco máximo entre bloques.

**Tech Stack:** reportlab (platypus, `BaseDocTemplate`, `PageTemplate`, `TableOfContents`, `bookmarkPage`/`addOutlineEntry`, enlaces internos y externos), Geist embebida (TTF, licencia SIL OFL: incluye el archivo de licencia), gráficas con `reportlab.graphics` (sin matplotlib: memoria de Render), pypdfium2 para las pruebas.

## Global Constraints

- **Mismo contenido que la web, otra forma:** cifras, lecturas, tonos y bandas de `display`; nada recalculado. Las frases que el guardián verifica en el PDF actual se verifican igual en el nuevo (amplía `tests/guardian.py::run` para aceptar el texto de `pdf_v2`).
- **Tipografía legible (preferencia del usuario):** cuerpo 10.5 pt / 1.45, tablas 9.5 pt, títulos de capítulo 18 pt, etiquetas mínimo 8 pt; nada por debajo de 8 pt (prueba automática con los tamaños de fuente de pdfium).
- **Colores de la v4 (claro):** los tokens de la spec §5; sin degradados ni brillos. Las escalas con las bandas de `thresholds.toml` (vía `display`).
- **Sin huecos:** ninguna página termina con más de `max_tail_gap_pt` de hueco salvo la última de un capítulo que empiece página nueva por diseño; entre bloques consecutivos, hueco ≤ `max_block_gap_pt`. Ambos en `config/pdf.toml` (nuevo) y comprobados en la geometría.
- **Enlaces:** índice → capítulos; "↑ índice" → índice; noticias y fuentes (SEC, Finnhub, Damodaran) → URL externas; todos verificados en la prueba.
- Peso del PDF ≤ 1.5 MB; generación ≤ 3 s en local por ticker con el análisis hecho; memoria pico ≤ 150 MB en la generación.
- Sin push, sin merge, sin deploy. Aprobaciones del PM.

---

### Task 0: Rama
- [ ] Worktree `../finanzer_next-e5`, rama `rediseno/e5-pdf` desde `rediseno/v4` (tras su Task 0 de E3). Al final se fusiona en `rediseno/v4` (el PM indica cuándo).

### Task 1: Base del documento
- [ ] `lib/pdf_v2/theme.py` (tokens de color, tamaños, márgenes carta; Geist registrada desde `backend/assets/fonts/Geist-*.ttf` + `OFL.txt`), `lib/pdf_v2/doc.py` (`BaseDocTemplate` con plantillas portada/cuerpo, cabecera con nombre y ticker, pie con página "x de y", fecha de los datos y "↑ índice"; `afterFlowable` que registra títulos en el índice y en los marcadores).
- [ ] Test: un documento con 3 capítulos ficticios tiene índice con 3 entradas enlazadas, 3 marcadores, "↑ índice" en cada página del cuerpo y pasa la geometría.

### Task 2: Componentes de dibujo
- [ ] `lib/pdf_v2/parts.py`: escala de puntuación (tramos con rangos, marca y valor; igual que la cabecera web), tarjeta de cifra, tabla técnica (Métrica en negrita + significado · Empresa · Referencia · Brecha · Lectura en pastilla), barras de categorías, rango de 52 semanas, Piotroski 3 × 3, gráfica de precio (línea base 100 empresa vs S&P 500 vs ETF, 1 año y 5 años, con `reportlab.graphics`), barras de segmentos, mini-historia de 10 años.
- [ ] Tests de cada parte (se dibujan sin error con datos de AAPL y con datos ausentes; la ausente dice su motivo en una línea —título del bloque y motivo en texto secundario— y no reserva su caja: lo que sigue sube a ocupar el sitio; corregido en la revisión del PM de E5, antes decía «mide lo mismo»).

### Task 3: Portada y resumen
- [ ] Portada: identidad, precio y variación, las tres escalas con su base, conclusión, gráfica de precio de 1 año y 6 cifras clave; todo en una página sin encoger por debajo de `MIN_SCALE`.
- [ ] Índice enlazado de los 9 capítulos + metodología + anexo.

### Task 4: Los nueve capítulos
- [ ] Un capítulo por sección de la historia, con lo esencial de su página de profundidad: lectura, visual clave, tabla técnica completa y notas (la misma selección de E3: nada de lo que hoy trae el PDF actual se pierde; prueba en la Task 6). Noticias con enlace; rivales si están en caché (si no, "Rivales: consulta la web", sin hueco); escenarios: el base y la sensibilidad del informe.

### Task 5: Metodología y anexo
- [ ] Metodología completa (fuentes con enlace, periodos, cálculos, referencias), anexo técnico (`display.annex`) y aviso legal actual.

### Task 6: Pruebas
- [ ] Geometría (`pdf_geometry`) ampliada: dentro del área, sin solapes, escala mínima, **hueco máximo entre bloques y al pie de página**, **tamaño mínimo de letra 8 pt**.
- [ ] Contenido: los tokens con cifra del PDF actual (`pdf_report`) de los 8 tickers están en el nuevo (misma técnica que "nada se pierde" de E3, con excepciones justificadas).
- [ ] Enlaces: todos los internos apuntan a una página existente; los externos son `https://`.
- [ ] Guardián sobre el texto del PDF nuevo en el panel completo (37 + MC.PA) en verde.
- [ ] Golden de texto del PDF nuevo: `tests/golden/panel_pdf_v2/<T>.pdf.txt` (nuevo, no toca los existentes).
- [ ] Rendimiento y peso dentro de los límites en los 8 tickers.

### Task 7: Endpoint y cableado
- [ ] `GET /api/v2/pdf/{symbol}` (mismo semáforo y nombre de archivo "Informe Finanzer {T} {fecha}.pdf"); el botón "Descargar PDF" de `/v2` apunta a él. El PDF actual (`/api/pdf`) no cambia.
- [ ] Capturas de cada página (PNG con pypdfium2) de AAPL, JPM, O y BCS en `docs/rediseno/capturas-e5/`; `docs/rediseno/E5_REGISTRO.md`; informe al PM.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
