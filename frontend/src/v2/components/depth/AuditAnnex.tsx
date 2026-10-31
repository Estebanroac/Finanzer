import type { Display } from "@/lib/api";

/** "Detalle técnico para auditoría" (título del motor): los códigos internos del análisis. V4b (nada oculto): a la vista,
 *  sin desplegable. */
export default function AuditAnnex({ annex }: { annex: Display["annex"] }) {
  if (!annex.items.length) return null;
  return (
    <div className="annex surface" data-testid="annex">
      <h4>{annex.title}</h4>
      <dl>
        {annex.items.map((i, n) => <div key={`${n}-${i.label}`}><dt>{i.label}</dt><dd>{i.text}</dd></div>)}
      </dl>
    </div>
  );
}
