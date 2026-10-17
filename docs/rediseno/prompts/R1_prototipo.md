> **SUSTITUIDO (2026-10-17)** por la especificación `docs/superpowers/specs/2026-10-17-rediseno-experiencia-design.md`. No usar.

# Prompt del operador — Rediseño R1: inventario, sistema visual y prototipo

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`.

---

Eres el **operador de la etapa R1 del rediseño de Finanzer**. El motor de análisis ya es fiable (fases 0–7 del plan
de fiabilidad, en producción). La presentación no está a su altura. Tu trabajo: entender a fondo lo que existe,
proponer un sistema visual y una arquitectura de la información, y construir un **prototipo navegable que el usuario
apruebe antes de que se toque nada de la app**.

## 1. Regla que manda sobre todo lo demás (R-D3)

El usuario: *"me gustaría un prototipo aprobado antes de que implementes los cambios. Para proteger lo que existe."*

- **No modificas nada de la app**: ni `frontend/src`, ni `frontend/out`, ni `backend/`, ni `config/`, ni tests,
  fixtures o golden. Ni en `main` ni en ninguna rama de trabajo existente.
- Trabajas en un **worktree propio**: `git worktree add ../finanzer_next-r1 -b rediseno/r1-prototipo main`.
- El prototipo es **estático y aislado** (carpeta `prototipo/` en la raíz de tu rama, fuera de `frontend/` y de
  `backend/`): HTML/CSS/JS, o un proyecto Vite/Next propio dentro de `prototipo/` con su propio `package.json`. Lee
  **instantáneas JSON** exportadas, nunca llama a la API de producción en vivo.
- **No se fusiona, no se sube y no se despliega.** Sin excepciones. Se sirve en local para que el usuario lo vea.
- Los worktrees `../finanzer_next-f67prep` (lo usa la tarea programada de vigilancia), `-f3`, `-f2b`, `-f3prep` y
  `-f5prep` no se tocan.

## 2. Contexto (lee antes de diseñar)

**Los documentos del rediseño están sin commitear en la carpeta principal** y no aparecerán en tu worktree: léelos por
su ruta absoluta en `/Users/joseestebanroa/Downloads/finanzer_next/docs/rediseno/`. Tus propios documentos de R1 los
escribes en tu rama (`docs/rediseno/` de tu worktree).

1. **`docs/rediseno/PLAN_REDISENO.md` entero**: diagnóstico, decisiones R-D1 (informe de una sola página con índice
   fijo, nada plegado), R-D2 (el PDF sigue en reportlab, rediseñado) y R-D3, principios §2, arquitectura propuesta §3.
2. **La opinión literal del usuario** (2026-10-17), que es el brief:
   - "La sección contexto del mercado es espantosa. No tengo noticias, demasiado triste y deprimente."
   - "En evaluación institucional me muestra el Piotroski, muy bien los 9 elementos, pero no hay detalle de cada uno."
   - "Histórico: muy bien lo que está, pero falta información del comportamiento del precio, gráficas de
     comportamiento en el tiempo… día tras día, por semana, por mes, por año, por 5 años. Los datos que me dan están
     buenos y los dejaría tal cual."
   - "La sección comparativa, muy buena, me encanta, pero podemos hacerlo en mejor visualización, no tan extensa. No
     cambies la información, cambia el formato."
   - "En crecimiento, el cambio de precio: neutro, sin color, sin información visible. No se transmite bien."
   - "Solidez: bello, me encanta, pero la Tabla de solidez financiera no debe estar oculta."
   - "Rentabilidad: muchas áreas de información importante ocultas… veo ese mismo formato en muchas secciones y no me
     gusta. Es preferible secciones mejor manejables y navegables dentro de la misma sección en lugar de ocultarla.
     Dale foco más de página web, de blog de lectura."
   - "Valoración: excelente también, pero mismo problema… algo más navegable de manera amigable en lugar de un sitio
     con tantas secciones ocultas una dentro de otra y tantos clics."
   - "Hay demasiado espacio que no se usa y todo queda apretado."
   - "La sección donde sale el puntaje: un montón de texto amarillo que no encaja… información valiosa pero mal
     administrada visualmente."
   - "El PDF sigue sin ser interactivo ni visualmente atractivo, demasiados espacios en blanco entre secciones."
3. La app actual: `frontend/src/app/stock/[[...symbol]]/StockPageClient.tsx`, `components/` (`TabsSection.tsx`,
   `SummarySection.tsx`, `StockHeader.tsx`, `charts.tsx`, `ui.tsx`, `InfoTooltip.tsx`) y `components/tabs/*.tsx`;
   el contrato de datos `frontend/src/lib/api.ts` y el bloque `display` que pinta la web y el PDF
   (`backend/lib/display.py`, `display_charts.py`). El PDF: `backend/lib/pdf_report.py`.
4. La identidad actual: verde de marca `#0cc06c`, fondo oscuro, Geist / Geist Mono, tonos semánticos
   (`--pos`, `--warn`, `--neg`). Tooltips con "Rangos de referencia" y "Tu valor" (al usuario le gustan: consérvalos).
5. Skills útiles: `apple-design` y `emil-design-eng` (jerarquía, tipografía, movimiento con moderación),
   `dataviz` (gráficas coherentes y accesibles), `prototype`.

## 3. Tareas

### T1. Inventario de lo que existe → `docs/rediseno/R1_INVENTARIO.md` (en tu rama)
- Recorre la web real con el servidor de replay (`backend/tests/replay_server.py`, sin red, sin producción) para
  AAPL, JPM, O y PLTR. Para **cada pestaña**: cada bloque, cada desplegable (hay 36), cada tabla, gráfica y tooltip;
  qué dato muestra (campo de `display` o del análisis) y cuántos clics cuesta llegar.
- Lo mismo para el PDF (página a página).
- **Nada se pierde:** la lista es el contrato del rediseño. Cada elemento del inventario debe aparecer en la nueva
  arquitectura (§T3) o tener un motivo explícito para fusionarse con otro.

### T2. Sistema visual → `docs/rediseno/R1_SISTEMA_VISUAL.md`
Rejilla, anchuras (texto ~70 caracteres; bloques anchos para gráficas y tablas), escala tipográfica, espaciado,
superficies, color semántico (qué significa cada color y dónde se usa, igual en web y PDF), estados (cumple / no
cumple / no aplica / sin dato), componentes (tarjeta de lectura, tabla, gráfico de precio, gráfico comparativo,
tarjeta de noticia, tarjeta de criterio Piotroski, índice lateral), movimiento (sutil, con
`prefers-reduced-motion`). **Dos direcciones visuales** (p. ej. "editorial" de lectura y "panel denso" más compacto),
ambas dentro de la identidad de marca.

### T3. Arquitectura de la información
Parte de `PLAN_REDISENO.md` §3 y ajústala con el inventario: orden de secciones, qué va en cada una y la gramática
común (lectura → visual clave → tabla completa → nota de método). Integra las alertas en su sección. Solo el anexo
técnico puede quedar plegado.

### T4. Datos para el prototipo (sin tocar la app)
- Exporta instantáneas JSON de AAPL, JPM, O y PLTR desde el replay (análisis completo, incluido `display`).
- **Serie de precios:** desde `backend/tests/fixtures/prices/` (5 años diarios ya capturados). Calcula en el
  prototipo las rentabilidades por periodo (1S, 1M, 3M, 6M, YTD, 1A, 3A, 5A) frente al S&P 500 y al ETF del sector.
- **Datos que aún no existen en el backend** (valores por criterio Piotroski, noticias con resumen e imagen, fecha de
  resultados): usa datos de muestra **marcados visiblemente en el prototipo como "dato de muestra"**, con la forma que
  tendrán. Documenta en `R1_DATOS_NUEVOS.md` cada campo que habrá que añadir en R2 (nombre, fuente, cálculo).

### T5. Prototipo navegable
- Página de informe de una sola página con **índice fijo** (sección activa resaltada al hacer scroll), anclas por
  sección, nada plegado salvo el anexo técnico, para los 4 tickers (selector arriba) y en las **dos direcciones
  visuales** (conmutador visible).
- Resuelve explícitamente cada punto del brief del usuario (§2.2): cabecera de puntuación sin el bloque amarillo,
  gráfica de precio con rangos de 1S a 5A y comparativa con mercado y sector, comparativa compacta (misma
  información, otro formato), rango de 52 semanas con color y lectura, tabla de solidez visible, Piotroski en 9
  tarjetas con sus valores, contexto de mercado con noticias en tarjetas y tono no lúgubre.
- Móvil (375 px) y escritorio (1440 px).
- **PDF:** maquetas de 4 páginas clave (portada, resumen, valoración, precio en el tiempo) en el mismo sistema, como
  imágenes o HTML a tamaño carta, con la propuesta de índice enlazado y marcadores.
- Sírvelo en local para el usuario (si `preview_start` no puede leer `~/Downloads`, lánzalo con Bash en segundo
  plano) y haz capturas de cada sección en las dos direcciones.

### T6. Presentación → **PUNTO DE PARADA**
Presenta al usuario: el enlace local del prototipo, las capturas, el inventario con la comprobación "nada se pierde",
y estas preguntas concretas: dirección visual (A o B, o mezcla), orden de las secciones, densidad, tratamiento de las
noticias en inglés (mostrar el original con su idioma indicado, recomendado; no traducir automáticamente). **Detente.**
Itera sobre el prototipo con sus comentarios hasta un "aprobado" explícito; registra la aprobación literal.

### T7. Cierre de R1
Entrada en `docs/rediseno/R1_REGISTRO.md` de tu rama (el planificador la llevará a la bitácora). Rama sin push, sin
merge. El prompt de R2 (datos nuevos) y R3 (web) lo escribe el planificador con el prototipo aprobado.

## 4. Reglas

- R-D3 por encima de todo: nada de la app se modifica.
- **Ninguna cifra ni lectura inventada.** Todo dato del prototipo sale de las instantáneas o de los fixtures de
  precios; lo que aún no existe, como "dato de muestra" visible.
- Las lecturas en lenguaje llano son las del motor (`display`); si propones otra redacción, márcala como propuesta.
- Accesibilidad: contraste AA, navegación por teclado del índice, texto alternativo en gráficas.
- Toda afirmación de "hecho" va con la evidencia (captura o comando).
- Al cerrar la sesión, deja tu registro aunque quede a medias.

## 5. Definición de terminado

- [ ] Inventario completo de web y PDF, con la comprobación "nada se pierde".
- [ ] Sistema visual con dos direcciones.
- [ ] Prototipo navegable en local (4 tickers, 2 direcciones, móvil y escritorio) y maquetas de 4 páginas del PDF.
- [ ] `R1_DATOS_NUEVOS.md` con los campos que necesitará R2.
- [ ] Aprobación explícita del usuario registrada; rama sin push ni merge; la app intacta (demuéstralo con
      `git -C /Users/joseestebanroa/Downloads/finanzer_next status` y `git diff main --stat -- frontend backend`
      vacío en tu rama).
