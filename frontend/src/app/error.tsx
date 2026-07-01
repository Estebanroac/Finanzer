"use client";

import { useEffect } from "react";

// Route-level error boundary: catches any render/runtime error in a page so the
// user sees a branded fallback instead of the bare white "Application error"
// page (a client-side exception in any component would otherwise blank the app).
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface the real error in the console for debugging.
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-[#09090b] text-center">
      <div className="w-14 h-14 rounded-full bg-[#00d632]/10 border border-[#00d632]/20 flex items-center justify-center mb-5">
        <svg className="w-6 h-6 text-[#00d632]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
      </div>
      <h2 className="text-xl font-semibold text-white mb-2">Algo salió mal</h2>
      <p className="text-sm text-zinc-500 mb-6 max-w-md">
        Ocurrió un error inesperado al mostrar esta página. Puedes reintentar o volver al inicio.
      </p>
      <div className="flex gap-3">
        <button
          onClick={() => reset()}
          className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-white/[0.06] border border-white/[0.1] hover:bg-white/[0.1] transition-colors"
        >
          Reintentar
        </button>
        <a
          href="/"
          className="px-4 py-2 rounded-lg text-sm font-medium text-[#00d632] bg-[#00d632]/10 border border-[#00d632]/20 hover:bg-[#00d632]/15 transition-colors"
        >
          Volver al inicio
        </a>
      </div>
    </div>
  );
}
