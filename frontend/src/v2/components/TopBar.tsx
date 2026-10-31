"use client";
import Link from "next/link";
import PdfButton from "@/v2/components/PdfButton";
import type { Theme } from "@/v2/lib/theme";
import SearchBox from "@/v2/components/SearchBox";

export default function TopBar({ symbol, theme, onToggleTheme, search = true }: {
  /** Símbolo de un análisis válido ya cargado: solo con él sale «Descargar PDF» (revisión V6, prueba V2: con un ETF,
   *  un ticker inexistente o una empresa deslistada el PDF respondería 422/404). */
  symbol: string | null; theme: Theme; onToggleTheme: () => void;
  /** La portada lleva su propio buscador grande: la barra deja el hueco vacío. */
  search?: boolean;
}) {
  return (<>
    {/* La franja de la barra de estado del iPhone: ver .status-edge en v2.css */}
    <div className="status-edge" aria-hidden="true" />
    <header className="topbar">
      <div className="wrap">
        {/* Marca: el logo en su placa nocturna (la misma forma en los dos temas, en los iconos y en el PDF) y «Finanzer»
            en Manrope 700; el nombre es texto, así que el enlace se llama «Finanzer» para los lectores de pantalla */}
        <Link className="brand" href="/v2">
          {/* eslint-disable-next-line @next/next/no-img-element -- export estático: sin optimizador de imágenes */}
          <img className="brand-logo" src="/brand/finanzer-logo.svg" alt="" width={36} height={36} />
          <span className="brand-word">Finanzer</span>
        </Link>
        {search ? <SearchBox /> : <span className="search-slot" />}
        <div className="actions">
          <button className="btn" onClick={onToggleTheme} aria-pressed={theme === "dark"}>
            {/* Revisión V6 (F25): las dos etiquetas en el HTML y el CSS enseña la del tema que el script del layout puso en
                <html> antes de pintar: sin parpadeo al hidratar (antes salía «Modo oscuro» y cambiaba en oscuro). */}
            <span className="theme-to-light">Modo claro</span><span className="theme-to-dark">Modo oscuro</span>
          </button>
          {symbol && <PdfButton symbol={symbol} />}
        </div>
      </div>
    </header>
  </>);
}
