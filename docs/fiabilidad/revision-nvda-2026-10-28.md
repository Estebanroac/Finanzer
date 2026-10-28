# Revisión externa del informe de NVIDIA (28-oct-2026)

Traída por el usuario («hice un ensayo con nvidia, me dice esto el experto»). Informe generado con `rediseno/v4-f8`
(v4 + F8 + F9). Resumen fiel de la revisión (el texto completo lo tiene el usuario):

**Veredicto del revisor:** mejor que Nu; ≈ 78/100 (NVIDIA original ≈ 70, Nu ≈ 70). Funcionan: prima de riesgo país
(+0,17 pp por geografía, 2 % sin atribuir declarado), par Rf–ERP de la misma fecha (aclara que el 5,29 % de Nu era
correcto), fiabilidad del DCF sin mirar el precio («media» por margen FCF 14,1–46,6 %), Altman por SIC (Z original,
peso +3), la beta alta como advertencia, regresión log-lineal en los ingresos (año inicial anómalo), falsación con
reversión del margen a su mediana de 10 años, tasas base de Lakonishok-Shleifer-Vishny.

**Lo que falla, por impacto:**
1. **Ganancias no operativas en el beneficio normalizado.** Beneficio neto TTM 192,9 B$ frente a operativo 197,6 B$;
   con t ≈ 16 % la operación (más intereses de la caja) explica ≈ 168 B$; el motor solo normaliza 6,5 B$. Margen neto
   normalizado 61,5 % imposible con margen operativo 65,2 % (techo ≈ 55 %). P/E normalizado real ≈ 31x, no 28,4x;
   inflan ROE y margen neto. Propuesta: si margen neto > margen operativo × (1 − t) + 2 pp, normalizar el exceso y
   marcarlo.
2. **NVIDIA se compara consigo misma.** El «−44 % frente a la industria (48,8x)» usa el agregado de semiconductores de
   EE. UU. de Damodaran (suma de capitalizaciones y beneficios) donde NVIDIA pesaba ≈ la mitad en enero. De ahí el +1
   del P/E y la fortaleza «cotiza con descuento». Propuesta: si la empresa pesa > 20 % del agregado, excluirla o usar
   la mediana.
3. **PEG con el crecimiento desde un año valle.** PEG 0,14 «muy atractivo» (+4) con CAGR del BPA a 3 años (198 %)
   desde FY2023, año que el propio informe declara anómalo. Corregido en ingresos (regresión), no en BPA. Usar el
   crecimiento esperado o n.s. con año base anómalo.
4. **El veredicto descansa en votos correlacionados.** El +3 del bloque de múltiplos = P/E +1, forward +1, PEG +1, los
   tres del mismo salto del BPA. Sin sesgos, bloque ≈ 0 y precio ≈ 50. El DCF inverso «muy exigente: 0 % de las
   comparables lo sostuvo» se cita y no afecta a nada: las tasas base deberían al menos bajar la confianza.
5. **Pendientes de la hoja de ruta:** E7 (DCF de tres impulsores; la reversión del margen no entra en la valoración);
   M5 (31 campos de yfinance frente a 1 de EDGAR en la procedencia); rivales «aún no estaban listos» en el PDF por
   segundo informe seguido (tiempos).
6. **Menores:** fortaleza del ROE «amplificado por recompras» con apalancamiento DuPont 1,31 (plantilla); PEAD dice
   trimestre cerrado el 2026-06-30 (el fiscal de NVIDIA cierra a finales de julio); nota de persistencia «por encima de
   80» (¿umbral 85?); motivo de confianza «techo en baja: techo de la confianza» no explica nada.

**Qué decide según el revisor:** los puntos 1 y 2 (baratos y afectan a MSFT, GOOGL, AMZN, ASML, LLY, WMT…).
