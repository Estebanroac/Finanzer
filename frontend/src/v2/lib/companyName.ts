import { COMPANY_NAMES as C } from "@/lib/generated/backendConfig";

/** P8 (el cintillo): el nombre corto de la empresa, sin forma jurídica final («Apple Inc.» → «Apple», «Tesla, Inc.» →
 *  «Tesla», «Home Depot (The)» → «Home Depot»). La misma regla que backend/lib/names.py `company`, con sus datos de
 *  names.toml (generados); companyName.test.ts comprueba que da lo mismo que el backend. Nunca vacío. */
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&");
const alt = (xs: readonly string[]) => [...xs].sort((a, b) => b.length - a.length).map(esc).join("|");
const STATE = new RegExp(C.edgarState);
const CI = new RegExp(`,?\\s+(?:${alt(C.suffixesCi)})$`, "i");
const CS = new RegExp(`,?\\s+(?:${alt(C.suffixes)})$`);
const COMMA = new RegExp(`,\\s*(?:${alt(C.afterComma)})$`);
const TAIL = /\s*\((?:The|Class [ABC])\)$|\s+Class [ABC]$/;
const EXCEPTIONS: Record<string, string> = C.exceptions;

export function companyShort(name: string | null | undefined): string | null {
  if (!name || !name.trim()) return name ?? null;
  const raw = name.trim();
  if (Object.hasOwn(EXCEPTIONS, raw)) return EXCEPTIONS[raw];   // V6b (E9): sin claves del prototipo («constructor»)
  let n = raw.replace(STATE, "").trim();
  for (;;) {
    const prev = n;
    for (const rx of [TAIL, CI, CS, COMMA]) n = n.replace(rx, "").replace(/[ ,]+$/, "");
    if (n === prev) break;
  }
  return n || raw;
}
