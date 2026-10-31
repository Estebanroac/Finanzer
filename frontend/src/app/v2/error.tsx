"use client";
import Link from "next/link";
import { useEffect } from "react";

/** Revisión V6 (F6): un fallo al pintar /v2 (datos que ningún componente esperaba) no deja la página en blanco ni con
 *  el error de Next en inglés: lo dice en el estilo de /v2, con «Reintentar» y «Volver a la portada». */
export default function V2Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.warn("v2: error al pintar la página", error); }, [error]);
  return (
    <div className="fz2">
      <main className="wrap">
        <div className="load-error" data-testid="v2-error">
          <h1>Algo falló al mostrar esta página</h1>
          <p role="alert">Los datos de esta empresa llegaron de una forma que la página no supo pintar. Vuelve a intentarlo; si sigue igual, prueba con otra empresa.</p>
          <p className="load-error-actions">
            <button type="button" className="btn" onClick={reset}>Reintentar</button>
            <Link className="btn ghost" href="/v2">Volver a la portada</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
