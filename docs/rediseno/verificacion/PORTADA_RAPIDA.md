# Portada rápida: tarjetas y mini-gráficas sin esperas

Rama `rediseno/v4f8-portada-rapida`, desde e20de9f8. Medido con el backend real y las fuentes reales el 28-oct (con la
bolsa abierta) con `backend/tools/portada_medida.py`. La herramienta hace lo que la web: pide
`/api/v2/trending?period=1D` cada `poll_s` hasta tener las tarjetas y luego sus mini-gráficas de 1D. La vida de las
mini-gráficas de 1D se acorta a 20 s para medir el TTL vencido.

## Resultado

| Escenario | Antes: tarjetas | Antes: mini-gráficas | Después: tarjetas | Después: mini-gráficas |
|---|---|---|---|---|
| Servidor caliente | 0,01 s | 0,00 s | 0,00 s | 0,00 s |
| Caliente, TTL de 1D vencido | 0,01 s | **3,22 s** | 0,01 s | **0,01 s** |
| Reinicio con la lista guardada | 28,1 s | 4,0 s | **0,00 s** | **0,01 s** |
| Arranque sin nada; el visitante llega a los 20 s | 32,1 s | 5,1 s | **16,1 s** | **0,02 s** |
| Arranque sin nada; el visitante llega al momento | 28,1 s | 4,0 s | 28,1 s | **1,4 s** |

Archivos: `PORTADA_antes_1.json`, `PORTADA_antes_llega20.json`, `PORTADA_despues_con_archivo.json`,
`PORTADA_despues_llega20.json` y `PORTADA_despues_sin_archivo.json`.

**El objetivo de ≤ 8 s en frío solo se cumple con la lista guardada.** Un arranque sin nada no puede tener las
tarjetas antes de que termine la descarga del universo, que tarda unos 28 s. Ver la causa abajo.

## Causa de los 28 s (comprobada)

- **(a) No es el periodo de 190 días.** Un lote de 100 valores tarda lo mismo con 190 días que con 10 (4,5 s frente a
  4,5 s; en otra tanda, 4,0 frente a 3,9). yfinance hace una petición a Yahoo por valor; el universo tiene 543, en 6
  lotes de unos 4,5 s. Una descarga ligera previa para 1D no ganaría nada, así que no se hace.
- **Tampoco lo arreglan más hilos.** 100 valores tardan 5,6 s con 10 hilos, 6,6 s con 20 y 8,9 s con 40, con
  ~1,2 s de CPU. El límite es el ritmo de Yahoo, no la máquina.
- **(b) Sí:** en local el cálculo empezaba con el primer visitante, porque `warm` solo actuaba en Render.
- **(c) Sí:** las mini-gráficas se pedían solo con las listas listas, y en frío no había nada en caché. Además, en 1D
  la barra de 5 min y el cierre anterior se descargaban uno detrás de otro.
- **(d) Sí:** pasado el TTL de 5 min de 1D, el visitante esperaba otra descarga (3,2 s).

## Qué cambia

1. **Lista guardada** (idea 4). La última lista buena y las mini-gráficas de su vista inicial van a
   `backend/.cache/portada.json` (`[trending] snapshot_file`, fuera de git).
   - Tras un reinicio se sirve en la primera petición.
   - Si es de la misma sesión y del mismo universo no se recalcula: dentro de una sesión la lista no cambia y el
     cálculo es el mismo.
   - Si no, se sirve mientras se recalcula, igual que un servidor caliente con la lista del día anterior.
   - Un archivo de otra config o ilegible se ignora.
   - `FINANZER_PORTADA_SNAPSHOT=0` lo apaga; con otra ruta, se usa esa.
2. **El cálculo empieza al arrancar** (idea 3), en el evento startup de `main`, también en local.
3. **Mini-gráficas de la vista inicial descargadas en el servidor** (idea 2), al publicar las listas, con la misma
   petición que hará la web (la puerta comparte la descarga en marcha).
4. **Mini-gráficas caducadas servidas al momento.** Pasado el TTL, la de antes sale marcada `stale` y se refresca en
   segundo plano, una vez por tanda. La web vuelve a pedir una vez las que llegaron así.
5. **En 1D, las dos descargas de cada mini-gráfica a la vez**: las mismas dos peticiones, solapadas.
6. **Web** (idea 5): con la lista guardada, la primera respuesta ya trae tarjetas. El esqueleto solo sale cuando el
   servidor no tiene nada que enseñar.

Lo que no cambia:

- Qué empresas salen en cada lista: el cálculo es el mismo.
- El ritmo de Yahoo: no hay peticiones nuevas; solo se solapan las dos de 1D y se adelanta la de la vista inicial.

## Límite en Render

En el plan gratuito de Render el disco se borra en cada arranque (despliegue o vuelta tras dormir), así que allí la
lista guardada no sirve tras dormir. Lo que sí ayuda en Render:

- el refresco de las mini-gráficas sin esperas;
- las mini-gráficas de la vista inicial descargadas por el servidor;
- las dos descargas de 1D a la vez.

El primer visitante tras despertar el servicio sigue esperando la descarga del universo. Opciones, a decidir:

- un disco persistente de Render, con `FINANZER_PORTADA_SNAPSHOT` apuntando a él;
- guardar la última lista en el navegador (sirve a quien ya visitó la portada).

## Comprobaciones

- Tests nuevos, que fallan antes:
  - `test_trending.py`: archivo de la lista, arranque, mini-gráficas de la vista inicial y cableado de `main`;
  - `test_sparklines.py`: caducadas sin esperar, `dump`/`load` y 1D a la vez. Este último falla con el código de
    antes;
  - `sparklines.test.ts`.
- Suite del backend: 6.054 passed, 8 skipped. La suite no deja archivo de la lista.
- `e2e:v2` contra el build: 874 passed, 0 fallos.
- Carga corta (3 min, `PORTADA_carga_corta.md`): todos los criterios en verde, pico 372 MB y 2.ª mitad +3,3 MB.
  - La de referencia del mismo arnés antes del cambio daba 398 MB.
  - Es una sola corrida por lado y el pico varía ±40 MB, así que solo muestra que no hay una subida visible.
  - `load_test.py` arranca sin la lista guardada para que las cargas sigan siendo comparables.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
