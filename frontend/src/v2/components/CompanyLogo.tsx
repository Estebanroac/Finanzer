"use client";
import { useEffect, useRef, useState } from "react";
import type { CompanyLogoInfo } from "@/lib/api";
import { logoInitials, logoSrc } from "@/v2/lib/logo";
import "./CompanyLogo.css";

export type LogoSize = "sm" | "md" | "lg";
type Status = "loading" | "ok" | "fail";

/** Logotipo de la empresa, como en los brókers: una placa cuadrada de tamaño fijo (reservado desde el principio: nada
 *  salta al cargar). Mientras llega, la placa vacía; si no hay logotipo o la imagen falla, las iniciales (nunca un
 *  hueco ni una imagen rota). El logotipo va sobre fondo blanco con un filo del tema: uno transparente se lee igual en
 *  claro y en oscuro. Decorativo: el nombre y el ticker van siempre al lado. */
export default function CompanyLogo({ symbol, name, logo, size = "md", className, testId = "company-logo" }: {
  symbol: string; name?: string | null; logo?: CompanyLogoInfo | null; size?: LogoSize; className?: string;
  /** null: sin identificador de prueba (la copia solo visual de la cabecera fija) */
  testId?: string | null;
}) {
  const src = logoSrc(symbol, logo);
  // otro símbolo o la versión que trae el análisis: se empieza de nuevo (key)
  return <Plate key={src ?? "-"} src={src} symbol={symbol} initials={logoInitials(name, symbol)} testId={testId}
    className={`co-logo co-logo-${size}${className ? ` ${className}` : ""}`} />;
}

function Plate({ src, symbol, initials, className, testId }: {
  src: string | null; symbol: string; initials: string; className: string; testId: string | null;
}) {
  const [status, setStatus] = useState<Status>(src ? "loading" : "fail");
  const img = useRef<HTMLImageElement>(null);
  // la imagen pudo llegar de la caché del navegador antes de que React atara onLoad y onError
  useEffect(() => {
    const el = img.current;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sincroniza una sola vez con la imagen ya cargada
    if (el?.complete) setStatus(el.naturalWidth > 0 ? "ok" : "fail");
  }, []);
  return (
    <span className={className} data-state={status} data-testid={testId ?? undefined} data-symbol={symbol} aria-hidden="true">
      {status === "fail" && <span className="co-logo-ph">{initials}</span>}
      {src && status !== "fail" && (
        // eslint-disable-next-line @next/next/no-img-element -- export estático: sin optimizador de imágenes (el PNG ya llega a 200 px)
        <img ref={img} src={src} alt="" decoding="async" draggable={false}
          onLoad={() => setStatus("ok")} onError={() => setStatus("fail")} />
      )}
    </span>
  );
}
