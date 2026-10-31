/** v4 (PM; V1 a 375 px, MC.PA): en el móvil las fichas de cifras van de dos en dos y la cifra nunca se parte. Una ficha
 *  cuya cifra no cabe en media fila (o sin cifra) ocupa la fila entera; la que se quedaría sola en su fila, también, para
 *  no dejar el hueco de la pareja. `wide[i]`: la ficha i necesita la fila entera. */
export function tileRows(wide: boolean[]): Array<"full" | "half"> {
  const out: Array<"full" | "half"> = [];
  let open = -1;   // índice de la ficha que espera pareja en su fila
  wide.forEach((w, i) => {
    if (w) {
      if (open >= 0) out[open] = "full";
      out.push("full"); open = -1;
    } else if (open >= 0) { out.push("half"); open = -1; }
    else { out.push("half"); open = i; }
  });
  if (open >= 0) out[open] = "full";
  return out;
}
