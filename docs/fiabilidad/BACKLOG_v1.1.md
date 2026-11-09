# Finanzer · pendientes para la v1.1

Solo anotados, sin implementar (decisión del usuario, 9-nov-2026, al cerrar la 1.0). Los hallazgos nuevos van a esta
lista, no al ciclo de la 1.0.

| # | Pendiente | Origen | Qué hay que hacer |
|---|---|---|---|
| 1 | Las fabricantes de equipos de telecomunicaciones o de redes con margen inestable caen en «madura por defecto» | Informe de CIEN (9-nov-2026): «Clasificada como MATURE por defecto: no es financiera, REIT, pre-beneficio con crecimiento, cíclica ni de crecimiento rentable»; su margen FCF va de −7,1 % a 13,9 % en 5 ejercicios | Revisar la regla de cíclicas (`lib/classify.py`): por qué un margen tan inestable no la marca como cíclica, y si hace falta otra señal además de la historia de 18 ejercicios |
| 2 | La sección «Esta lectura sería errónea si…» solo compara con el crecimiento histórico | Informe de CIEN: compara el 18,6 % anual que exige el precio con el 4,9 % de su historia | Añadir «qué tiene que pasar para justificar el precio» con el guidance de la empresa y la cartera de pedidos (CIEN habla de +30 % de ingresos en el FY27 y de una cartera que crece). Solo fuentes gratuitas y fiables |
| 3 | Comprobar si Lumentum (LITE) sigue sin beneficio en el periodo de los datos | Tabla de rivales de CIEN: LITE «sin nota de valoración: beneficio normalizado de doce meses ≤ 0» | Verificar en EDGAR el beneficio de doce meses al último periodo presentado; si ya es positivo, ver por qué la L1 no lo recoge (periodo antiguo, 10-Q sin leer…) |

## Hallazgos nuevos

| # | Hallazgo | Origen | Qué hay que hacer |
|---|---|---|---|
| 4 | En los REIT, la fila «P/FFO (REIT)» de la tabla de múltiplos lleva todavía la lectura de la rama del sistema anterior («Favorable», «Exigente») junto a la etiqueta de la regla L1 (baja / en línea / alta) | Golden de O, AMT y PLD (9-nov-2026), al cerrar la 1.0 | Decidir si esa fila se rotula como la del P/E de la L1 (mediana de los REIT y etiqueta L1) o si su lectura se queda como lectura sin color |
