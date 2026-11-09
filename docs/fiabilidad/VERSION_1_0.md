# Finanzer · versión 1.0 (congelada el 8-nov-2026)

Decisión del usuario, después de las dos pruebas hacia atrás (cortes del 5-nov-2025 y del 5-nov-2024): congelar el
motor como versión 1.0. La próxima prueba será un corte anual nuevo, no más cortes del pasado ahora. Etiqueta git:
`v1.0`, en la rama `fiabilidad/f16-precio-l1`.

## Qué es la 1.0

| Pieza | Regla | Evidencia |
|---|---|---|
| **Precio** | Regla L1: P/E del beneficio normalizado de 12 meses (P/FFO en los REIT) frente a la mediana de su grupo (sector GICS; bancos y aseguradoras entre sí; REIT entre sí), por tercios del universo (`lib/precio_l1.py`, `config/precio_l1.toml`) | Ordena en la dirección correcta en los dos cortes: barata − cara a 12 meses +11,2 pp (2025) y +2,5 pp (2024), en el control |
| **Texto del precio** | «Valoración baja / en línea con / alta frente a su sector». Describe el precio de hoy, no anticipa la rentabilidad | Decisión del usuario (7-nov-2026) |
| **Calidad** | Cuatro categorías de 20 puntos (solidez, rentabilidad, calidad de ganancias, crecimiento), sin contracción por confianza | — |
| **Consistencia** | «Consistente» o «mixta»: coincidencia de métodos y cobertura de datos. No es una probabilidad de acierto | La confianza anterior no ordenó los aciertos en ninguno de los dos cortes |
| **Alertas rojas** | **Ninguna** | Ninguna se confirmó. La de valoración extrema falló el criterio fijado (≥ 1,5 veces, también sin tecnología): × 0,63 en 2024 y × 1,37 con los dos cortes juntos |
| **Lectura de valoración** | Múltiplos, DCF y, si cae en «muy exigente», la valoración extrema. Sin color y sin decidir el nivel | — |
| **Estado del balance** | Altman, EBIT < 0, caja libre negativa, apalancamiento, destrucción de valor y márgenes negativos. Sin color de alerta | — |
| **Aviso de pico** | En las cíclicas, junto a la etiqueta, cuando el beneficio está en la parte alta del ciclo | — |
| **Referencia L1** | `config/precio_l1.toml`, con alarma si tiene más de 35 días o si sus cortes no cambian entre dos actualizaciones | — |

## Cierre de la 1.0 (9-nov-2026): limpieza de presentación

Decisión del usuario: cerrar la 1.0 con una limpieza de presentación del informe, sin tocar ningún cálculo.

| Punto | Antes (CIEN) | Ahora |
|---|---|---|
| Un solo P/E | 54.45x TTM (portada, ficha, tabla de múltiplos, resumen), 50.4x normalizado del motor anterior (desglose y lectura de valoración), 48.8x de la L1 | Solo el P/E normalizado de 12 meses de la L1 (P/FFO en los REIT), con su mediana de grupo. El TTM queda en la tabla de rivales, rotulado «P/E (TTM)». Sin E/P (era su inverso) |
| Una sola nota de precio | «15 · exigente» en rivales, «15/100 · alta» en la conclusión, «24/100» en la lectura | La de la L1 en portada, rivales y conclusión (baja / en línea / alta). La valoración extrema se lee sin número de 0 a 100 |
| Restos del sistema anterior | «Bloque de múltiplos −5 / DCF inverso −2» y «Valoración 3/20» bajo la nota; «en Valoración puntúa el DCF inverso (−2 puntos)»; «aporta −2 puntos a Valoración»; fórmula del bloque en el anexo; «Bloque de múltiplos» en el glosario; metodología con «Alerta roja: solo la de valoración extrema»; Valoración /20 en el desglose por categoría | Fuera. Bajo la nota, sus cifras: múltiplo, mediana de su grupo y tercio del universo |
| Rivales sin nota | «None · —» | «sin nota» y el motivo al pie |
| ROE | «competitivo» en el texto, «Inferior» en la tabla | El texto dice también que queda por debajo de la referencia de su industria |
| Deuda | «Deuda baja» frente a «Deuda / Equity: Muy por encima» | Con el D/E sobre el umbral de su sector: «Deuda neta baja frente al EBITDA», y que frente al patrimonio es alta |
| Frontera del precio | «en la frontera con «razonable»» | «en la frontera con «en línea»» |

**Verificación (antes del push).** Las 410 empresas del corte del 5-nov-2025 (110 + control 300), con el reloj congelado,
con la v1.0 (`844f51f8`) y con el cierre: en las 402 con análisis, **0 diferencias** en puntuaciones, etiquetas, veredicto,
consistencia, clasificación y en todo el análisis salvo la presentación. Solo cambian la presentación, el texto de la
frontera (29) y las alertas de lectura, como estaba previsto:
- 248 señales del P/E anterior salen de la lectura de valoración;
- 78 valoraciones extremas, sin el número;
- 36 «Deuda baja» reescritas.

Evidencias en `archivo-historico/evidencias-de-pruebas/cierre_v1_0_2026-11-09/`.

**Pruebas cambiadas.** Todas son de texto o de presentación. Tres afirmaban un número que el informe mostraba, y su cálculo
no cambió:
- el ajuste del bloque de múltiplos de V (−4) y de AAPL (−5): dejan de mostrarse, y las pruebas exigen que sigan en
  `score.breakdown`;
- el P/E del resumen de NVDA: pasa de 31.3x (P/E normalizado del motor anterior) a 31.0x (P/E de la regla L1).

Las 8 empresas sin análisis del corte (CTRA, DAY, EA, EME, HOLX, IBN, TTE y WBD, sin fixtures) son las mismas con la
v1.0, con el cierre y en la corrida F16c.

Suite: backend 6803 en verde y web 172; guardián del build correcto.

**Versiones de los datos con que se congela**

| Dato | Versión |
|---|---|
| Referencia de la L1 (`config/precio_l1.toml`) | 7-nov-2026, 514 empresas con P/E de 543, cortes 0,839 / 1,190 |
| Universo (`config/universe.tsv`) | 543 empresas |
| Industrias, betas y riesgo país (Damodaran) | enero de 2026 (5-ene-2026) |
| Prima implícita y Rf del par (Damodaran) | 1-nov-2026 |
| Tasas base de crecimiento (Mauboussin y Callahan) | 2021 (23-jun-2021) |
| Estados financieros | SEC EDGAR y Yahoo Finance en vivo, en cada análisis |

Pendiente de la v1.1, sin implementar: `BACKLOG_v1.1.md`.

## Lo que queda congelado

- No se cambian las reglas de precio, calidad, consistencia ni alertas hasta la próxima prueba.
- Sí se arreglan:
  - errores que rompen un análisis (como el 500 de MRNA, `5435acc6`);
  - fallos de datos;
  - el refresco mensual de `config/precio_l1.toml`.
- Cada arreglo se registra.

## Próxima prueba

- **Corte anual nuevo**: 5-nov-2026, medido a 6 y 12 meses (mayo y noviembre de 2027).
- **Reglas**: las mismas del pre-registro de 2025 y de 2024. El universo y la muestra de control se fijan en esa fecha.
- **Ventaja**: el corte se captura *en vivo* ese día, así que no hacen falta reconstrucciones (la desviación 1 de 2024
  nació de que Yahoo ya no sirve los ejercicios antiguos).

## Documentos

- Pre-registros y resultados:
  - `PRUEBA_HACIA_ATRAS_2025_PREREGISTRO.md` y `PRUEBA_HACIA_ATRAS_2025_RESULTADOS.md` (con la corrección de SMFG);
  - `PRUEBA_HACIA_ATRAS_2024_PREREGISTRO.md` (con su desviación 1) y `PRUEBA_HACIA_ATRAS_2024_RESULTADOS.md`.
- Cambios del motor: `F16_PRECIO_L1.md` (F16, F16 bis, Fase 1 y comprobaciones antes del push).
- Evidencias: `archivo-historico/evidencias-de-pruebas/hacia_atras_2025-11-05/` y `hacia_atras_2024-11-05/`.

## Estado de la entrega

- **La 1.0 está en producción desde el 9-nov-2026.** `main` = `844f51f8`, por avance rápido, con el «ok, pushea» del
  usuario; la etiqueta `v1.0` se subió en ese commit.
- **El cierre (limpieza de presentación) está en la rama `fiabilidad/f16-precio-l1`, sin push.** Pasos para llevarlo a
  producción:
  1. El usuario lo prueba.
  2. Da el «ok, pushea».
  3. Se fusiona con `main`.
  4. Se decide la etiqueta: mover `v1.0` o crear `v1.0.1`.
