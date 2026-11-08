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

Todo está en la rama `fiabilidad/f16-precio-l1`, que **no está fusionada en `main`**: Render no la despliega. Pasos
para llevarla a producción:

1. El usuario la prueba en el simulador.
2. Da el «ok, pushea».
3. Se fusiona con `main`.
