# GOLDEN_DIFF_F10_BETA_SEMANAS: la beta propia solo con semanas completas

Rama `fiabilidad/f10-beta-semanas`, que sale de `rediseno/v4-f8` en be9a0ea3. Pedido del PM del 29-oct, tras el escaneo
de comprobación de `fiabilidad/f10-margen-op`.

## El caso

MSCI, en dos pasadas del mismo día:

| | Puerta (be9a0ea3) | Comprobación (bee72b5a) |
|---|---|---|
| R² de la beta propia | 0,202 | 0,199 |
| Filtro (R² ≥ 0,20) | la pasa | no la pasa |
| Beta | 0,87 (propia) | 0,49 (sector) |
| WACC | 8,8 % | 7,4 % |
| DCF | −34 % | −10 % |
| Precio | 10 «muy exigente» | 40 «exigente» |
| Calidad | excelente | sólida |

La causa era la última semana de la regresión (W-FRI, la del 30-oct). Seguía abierta: su «cierre» era el precio de
la última sesión, que se movía con la hora.

## La regla (`market_signals.beta`)

- La semana de la última sesión, de cualquiera de las dos series, se descarta siempre. Así no entra un precio intradía,
  y el resultado no depende de la hora del día.
- Las 104 semanas son las 104 últimas completas.
- En fin de semana también se descarta la semana recién cerrada. Es el precio de que la regla no dependa de la hora: la
  ventana va una semana por detrás.

## Tests

- **Nuevos** (`test_market_signals.py`):
  - la semana de la última sesión no entra;
  - mover el precio de la sesión en curso no cambia la beta;
  - una sesión más de la misma semana tampoco.
- **Contraste independiente** (`ind_beta`) y **método de la 2a** (`beta_2a`): aplican la misma regla.
- **Números que dejó la 2a:** se midieron con su última semana abierta. Para que la ventana vuelva a ser la suya, el
  test añade a las dos series una sesión de la semana siguiente, con el mismo cierre, y su última semana queda
  completa.

## Golden

- **Todas las betas propias cambian en milésimas**, porque la ventana se desplaza una semana: AAPL 1,035 → 1,041, KO
  0,406 → 0,415, JPM 1,058 → 1,062.
- **Ninguna cambia de método** (propia o de sector).
- **TSM:**
  - solo tiene 105 semanas de historia, y con la regla quedan 103 observaciones;
  - el DCF cruza un tramo («claramente cara» −4 → «cara» −2);
  - el precio pasa de 35 a 42, y sigue en «exigente».
- **BRK-B:** el motivo de su descarte ya no incluye «beta 0,40 fuera de [0,4; 2,5]» (su beta queda dentro). Sigue
  descartada por R².

## En el universo (`tools/f10_beta_semanas_medida.py`)

Las mismas series para las dos reglas: una descarga por empresa, solo Yahoo. Son las 543, el 29-oct por la noche, con
la semana del 30-oct abierta.

- **|Δ beta ajustada|:** mediana 0,003, percentil 90 0,010, máximo 0,033.
- **Cambian de método 4**, y todas por el filtro de R²:

| Empresa | R² antes → ahora | Beta usada | Calidad | Precio |
|---|---|---|---|---|
| MSCI | 0,199 → 0,202 | sector → propia | sólida 82 → excelente 88 | exigente 40 → muy exigente 10 |
| XYL | 0,162 → 0,236 | sector → propia | sólida 82 → excelente 86 | razonable 45 → razonable 50 |
| A | 0,200 → 0,199 | propia → sector | = | = |
| CSX | 0,201 → 0,200 | propia → sector | = | = |

- **Los niveles se midieron con el análisis completo de las 4 empresas**, con las dos reglas, una pasada detrás de la
  otra: v4-f8 tiene la regla de antes.
- **XYL** no estaba en el filo: su semana abierta tenía un movimiento grande.
- **Tres de las cuatro siguen a ±0,002 del corte:** es la propuesta post-v4 del filtro continuo
  (`ESPEC_MODELO_GENERAL.md`, §9 c).
