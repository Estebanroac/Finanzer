import { useSyncExternalStore } from "react";

export type Theme = "light" | "dark";
const KEY = "finanzer.v2.theme";
const EVENT = "finanzer:v2-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

function stored(): Theme | null {
  try {
    const v = localStorage.getItem(KEY);
    return v === "dark" || v === "light" ? v : null;
  } catch {
    return null;
  }
}

function system(): Theme {
  try {
    return typeof window.matchMedia === "function" && window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

/** Tema de /v2: el guardado por el usuario (E1) o, la primera vez, el del sistema (E4). El mismo criterio aplica el
 *  script del layout antes de pintar (app/v2/layout.tsx). */
export function readTheme(): Theme {
  return stored() ?? system();
}

export function writeTheme(t: Theme): void {
  try {
    localStorage.setItem(KEY, t);
  } catch {
    /* sin almacenamiento: el tema dura la sesión */
  }
  if (typeof document !== "undefined") document.documentElement.dataset.v2theme = t;   // fondo y tokens antes de React
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENT));
}

function subscribe(cb: () => void): () => void {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  const mq = typeof window.matchMedia === "function" ? window.matchMedia(DARK_QUERY) : null;
  mq?.addEventListener?.("change", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", cb);
    mq?.removeEventListener?.("change", cb);
  };
}

/** El tema como almacén externo: null en el render estático y durante la hidratación (el script del layout ya pintó
 *  con el tema bueno), y el del navegador después. */
export function useTheme(): Theme | null {
  return useSyncExternalStore(subscribe, readTheme, () => null);
}
