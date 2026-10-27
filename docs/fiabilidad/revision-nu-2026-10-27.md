# Revisión externa del informe PDF de NU (27-oct-2026)

Traída por el usuario («me informan esto del nuevo informe de pdf»). PDF de 19 páginas generado con el motor nuevo
(`rediseno/v4-f8`). Texto tal cual lo recibimos:

---

Ya lo revisé (19 páginas). En resumen: **la herramienta está mejor, pero este veredicto en concreto no es fiable.** Varias de las correcciones de la auditoría ya están aplicadas y funcionan, pero Nu es un caso nuevo (banco de mercado emergente) que deja ver huecos que la muestra anterior no tenía.

## Lo que mejoró: correcciones aplicadas que funcionan

| Corrección de la auditoría | Cómo aparece en el informe de NU | Valoración |
|---|---|---|
| E1 · piso al coste del patrimonio | «Ke 7,39% = piso Rf + 0,5 × ERP, porque el CAPM da 6,97%» | Funciona y queda explicado |
| E1 · prueba de sensibilidad al Ke | «Confianza baja: el nivel de precio cambia con ±1 pp de coste del capital» | Funciona, y aquí acierta |
| E11 · la confianza también contrae la calidad | «Contrae la calidad de 80 a 76» | Funciona |
| E11 · saturación | «Excelente» pasa de ≥ 80 a ≥ 85 | Aplicado |
| Banco · solidez como caja negra | Ahora desglosa el 10/10: ROA 4,36%, ROE 27,2%, capitalización 16% | Parcial: ver el punto 6 abajo |
| Referencia por región | Usa bancos grandes de **mercados emergentes** de Damodaran (455 empresas), no bancos de EE. UU. | Buena decisión |
| M6 · IFRS | Usa `ifrs-full` de EDGAR como respaldo | Parcial |
| Honestidad sobre los datos | «El 20-F no desglosa segmentos en XBRL», «EDGAR trae 7 ejercicios», «los rivales aún no estaban listos» | Bien: dice lo que no tiene en lugar de inventarlo |

## Lo que falla, por orden de impacto

**1. No hay prima de riesgo país. Este error cambia el veredicto.**
- **El problema:** el Ke de 7,39% es el de un banco estadounidense, pero Nu presta en reales y pesos mexicanos a consumidores de Brasil, México y Colombia. El piso que añadiste está calibrado para EE. UU. y no sustituye a la prima de riesgo país, que en Brasil está en el orden de 3 pp según las tablas de Damodaran (conviene confirmar la cifra en su actualización de julio).
- **Efecto aun con la misma beta de 0,40:** con un Ke de alrededor de 9,7%, el P/B justificado baja de 4,68x a unos 3,4x. Frente al 5,34x al que cotiza, la acción pasa de «razonable» a **muy exigente**.
- **Con una beta realista:** su volatilidad es de 46%, 3,6 veces la del S&P. Con un Ke de alrededor de 12%, el P/B justificado queda en unos 2,6x, la mitad del precio.
- **El matiz que corre en sentido contrario:** el Gordon de una sola etapa con g = 2,5% subvalora a un banco cuyo valor en libros crece 33,6% anual. Hace falta un modelo de dos etapas. Los dos errores no se compensan de forma predecible.

**2. Presenta la beta como fortaleza el mismo día que la acción se desploma.** Pone «Perfil defensivo — Beta 0,40: útil para reducir la volatilidad de una cartera» en la lista de **fortalezas**, mientras su propia sección de mercado muestra una volatilidad de 46,1% y una caída máxima de −38%. Sus propias noticias del 26 y 27 de octubre reportan caídas de alrededor del 20% tras la victoria de Lula. Es la parte narrativa de E1 que no se corrigió, y para una decisión es la más peligrosa.

**3. Contradicciones internas: la conciliación entre fuentes (M5) no está implementada.**

| Dato | Una parte del informe | Otra parte del informe |
|---|---|---|
| P/B | 5,34x (portada y resumen) | 4,55x (tabla de múltiplos) |
| CAGR de ingresos a 3 años | 52,3% | 48,8% según su propia tabla (4,79 → 15,77) |
| Crecimiento del último ejercicio | 28,5% | +37,0% en la tabla histórica |
| Ingresos | TTM $13,17B | FY2025 $15,77B, mayor que el TTM pese a que la empresa crece: son definiciones distintas |
| Industria | «Bancos regionales» (encabezado) | «Grandes bancos de mercados emergentes» (referencia) |
| EV/EBITDA | «No aplica» | Muestra 69,37x en la columna de industria |

La del P/B no es menor. Con el 4,55x de su propia tabla, NU estaría al 97% del P/B justificado, es decir, **en precio**, no con prima. La lectura cambia según cuál de las dos cifras use.

**4. El margen neto se compara con definiciones distintas.** El 27,4% de Nu se calcula sobre ingresos brutos, que incluyen intereses cobrados, y se compara con el 41% de bancos que reportan sobre ingresos netos. Eso le resta −2 puntos sin fundamento. En un banco, el margen neto sobre «ingresos» no debería puntuar.

**5. Sigue la plantilla en un banco.** Aparece «La cobertura de intereses (0,77x) es críticamente baja». En la auditoría estaba como pendiente en JPM y sigue igual.

**6. Falta el riesgo principal de este negocio: el crédito.** Nu es sobre todo un prestamista de tarjeta de crédito sin garantía en Brasil. No aparecen:
- morosidad a 90 días;
- coste del riesgo;
- provisiones sobre cartera;
- cobertura de la morosidad.

El informe concluye «0 riesgos». Además, la «capitalización 16%» es patrimonio sobre activos, no capital regulatorio (Basilea).

**7. Errores menores.**
- **Tasa libre de riesgo:** Rf de 5,29%, cuando el bono a 10 años cerró en 5,00% el 26 de octubre según YCharts. Conviene revisar qué serie está tomando.
- **«Posible cíclica»:** la marca por la desaceleración normal de un hipercrecimiento (de +182% a +37%), no por un ciclo.
- **Estabilidad del ROE:** la penaliza como «beneficio poco recurrente» cuando lo que mide es el paso de pérdidas a ganancias.

## Comparación con la auditoría

Si aplico la rúbrica solo a este informe, sale en torno a **70/100**. JPM, el banco comparable de la muestra anterior, estaba algo por debajo con los mismos criterios. La mejora es real pero modesta. Las reglas nuevas funcionan; lo que limita la nota es que Nu activa tres huecos que JPM no tenía: mercado emergente, banco de alto crecimiento e inconsistencias entre fuentes.

**Qué decide:** la prima de riesgo país. Es una regla del mismo tipo que el piso del Ke (suma la prima según dónde opera la empresa, no según su domicilio legal) y es la que convierte este informe de engañoso en utilizable. Damodaran publica la tabla dos veces al año. La conciliación del P/B y del crecimiento va en segundo lugar.

Con un informe no puedo medir si la herramienta mejoró en conjunto. Para eso conviene volver a correr los 26 de la muestra original y compararlos uno por uno.

Fuentes: [YCharts – 10 Year Treasury Rate](https://ycharts.com/indicators/10_year_treasury_rate)
