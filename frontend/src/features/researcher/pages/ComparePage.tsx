import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { Alert, Card, PageHeader, Select, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";
import { asText } from "@/lib/text";

import { TRIGGER_LABEL, researchApi, researchQueryKeys } from "../api";

const DIMENSION_LABEL: Record<string, string> = {
  contexto: "Contexto",
  estrategia: "Estrategia (registros)",
  representación: "Representación",
  ayuda: "Ayuda",
  reacción: "Reacción",
  intervención_docente: "Intervención docente",
  trayectoria: "Trayectoria",
  cierre: "Cierre",
};

function render(value: unknown): string {
  if (Array.isArray(value)) return value.length ? value.map((v) => asText(v)).join(" → ") : "—";
  if (value && typeof value === "object")
    return Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.map((x) => asText(x)).join(", ") || "—" : asText(v)}`)
      .join("\n");
  return asText(value);
}

export function ComparePage() {
  const [params, setParams] = useSearchParams();
  const a = params.get("a") ?? "";
  const b = params.get("b") ?? "";
  const episodes = useQuery({ queryKey: researchQueryKeys.episodes({}), queryFn: () => researchApi.episodes() });
  const comparison = useQuery({ queryKey: researchQueryKeys.compare(a, b), queryFn: () => researchApi.compare(a, b), enabled: Boolean(a && b && a !== b) });

  const selector = (key: "a" | "b", value: string) => (
    <Select
      label={`Episodio ${key.toUpperCase()}`}
      value={value}
      onChange={(e) => {
        const next = new URLSearchParams(params);
        next.set(key, e.target.value);
        setParams(next);
      }}
    >
      <option value="">Selecciona…</option>
      {episodes.data?.map((ep) => (
        <option key={ep.id} value={ep.id}>
          {ep.participant_code} · {ep.task_code} · {TRIGGER_LABEL[ep.trigger] ?? ep.trigger} · {new Date(ep.created_at).toLocaleDateString("es-CO")}
        </option>
      ))}
    </Select>
  );

  return (
    <>
      <PageHeader eyebrow="Investigación" title="Comparar episodios" description="Lectura lado a lado de los registros. No se generan conclusiones automáticas." />
      <div className="ds-stack">
        <Card>
          <div className="ds-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
            {selector("a", a)}
            {selector("b", b)}
          </div>
        </Card>
        {comparison.isPending && a && b && <Skeleton height="10rem" />}
        {comparison.isError && <Alert tone="error">{errorMessage(comparison.error)}</Alert>}
        {comparison.data && (
          <Card title="Comparación" description={comparison.data.note}>
            <div className="compare-grid" role="table" aria-label="Comparación de episodios">
              <div className="compare-grid__head" role="columnheader">
                Dimensión
              </div>
              <div className="compare-grid__head" role="columnheader">
                A · {comparison.data.a.participant_code} · {comparison.data.a.task_code}
              </div>
              <div className="compare-grid__head" role="columnheader">
                B · {comparison.data.b.participant_code} · {comparison.data.b.task_code}
              </div>
              {Object.entries(comparison.data.dimensions).map(([key, pair]) => (
                <div key={key} role="row" style={{ display: "contents" }}>
                  <strong role="rowheader">{DIMENSION_LABEL[key] ?? key}</strong>
                  <pre role="cell">{render(pair.a)}</pre>
                  <pre role="cell">{render(pair.b)}</pre>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
