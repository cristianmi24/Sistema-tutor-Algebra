import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Alert, Badge, Button, Card, PageHeader, Select, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";
import { asText } from "@/lib/text";

import { type TutorRule, tutorApi, tutorQueryKeys } from "../tutorApi";

function Condition({ node, depth = 0 }: { node: unknown; depth?: number }) {
  if (typeof node !== "object" || node === null) return <code>{String(node)}</code>;
  const obj = node as Record<string, unknown>;
  if (Array.isArray(obj.all) || Array.isArray(obj.any)) {
    const items = (obj.all ?? obj.any) as unknown[];
    const word = obj.all ? "Y" : "O";
    return (
      <ul style={{ margin: 0, paddingLeft: depth ? 16 : 0, listStyle: "none" }}>
        {items.map((item, i) => (
          <li key={i}>
            {i > 0 && <strong className="text-caption">{word} </strong>}
            <Condition node={item} depth={depth + 1} />
          </li>
        ))}
      </ul>
    );
  }
  if (obj.not) {
    return (
      <span>
        <strong className="text-caption">NO </strong>
        <Condition node={obj.not} depth={depth + 1} />
      </span>
    );
  }
  const subject = obj.evidence ? `evidencia ${asText(obj.evidence)}` : obj.posterior ? `P(${asText(obj.posterior)})` : obj.need_support !== undefined ? "P(necesita apoyo)" : obj.previous_state !== undefined ? "estado anterior" : "condición";
  const ops: Record<string, string> = { is: "=", in: "∈", eq: "=", ne: "≠", gt: ">", gte: "≥", lt: "<", lte: "≤" };
  const spec = (obj.need_support ?? obj.previous_state) as Record<string, unknown> | string | number | undefined;
  const entries = Object.entries(typeof spec === "object" && spec !== null ? spec : obj).filter(([k]) => k in ops);
  const rendered = entries.length ? entries.map(([k, v]) => `${ops[k]} ${JSON.stringify(v)}`).join(" ") : typeof spec !== "object" && spec !== undefined ? `= ${String(spec)}` : "";
  return (
    <span>
      {subject} <code>{rendered}</code>
    </span>
  );
}

function Action({ actions }: { actions: Record<string, unknown> }) {
  return (
    <div className="ds-inline-actions">
      {actions.state !== undefined && <Badge tone="primary">estado {asText(actions.state)}</Badge>}
      {actions.level !== undefined && <Badge tone="secondary">nivel {asText(actions.level)}</Badge>}
      {actions.intervention !== undefined && <Badge tone="info">{asText(actions.intervention)}</Badge>}
      {actions.fading !== undefined && <Badge tone="neutral">fading {asText(actions.fading)}</Badge>}
    </div>
  );
}

export function AdminRulesPage() {
  const queryClient = useQueryClient();
  const rules = useQuery({ queryKey: tutorQueryKeys.rules, queryFn: tutorApi.rules });
  const bayes = useQuery({ queryKey: tutorQueryKeys.bayes, queryFn: tutorApi.bayes });
  const [showBayes, setShowBayes] = useState<string>("accuracy_band");

  const toggle = useMutation({
    mutationFn: (rule: TutorRule) =>
      tutorApi.updateRule(rule.id, {
        code: rule.code,
        name: rule.name,
        description: rule.description,
        priority: rule.priority,
        min_consecutive: rule.min_consecutive,
        conditions: rule.conditions,
        actions: rule.actions,
        is_active: !rule.is_active,
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: tutorQueryKeys.rules }),
  });

  const activeBayes = bayes.data?.find((b) => b.is_active) ?? bayes.data?.[0];
  const table = activeBayes?.likelihoods[showBayes];

  return (
    <>
      <PageHeader
        eyebrow="Motor adaptativo"
        title="Reglas pedagógicas e inferencia"
        description="Las reglas se evalúan por prioridad; la primera que se cumple decide. La inferencia bayesiana solo aporta probabilidades a sus condiciones."
      />
      <div className="ds-stack">
        {toggle.isError && <Alert tone="error">{errorMessage(toggle.error)}</Alert>}
        <Card title="Reglas (SI … ENTONCES)" description="Legibles para desarrolladores y expertos pedagógicos. Cada cambio queda auditado y versionado.">
          {rules.isPending && <Skeleton height="8rem" />}
          {rules.isError && <Alert tone="error">{errorMessage(rules.error)}</Alert>}
          {rules.data && (
            <div className="ds-table-wrap">
              <table className="ds-table">
                <thead>
                  <tr>
                    <th>Prioridad</th>
                    <th>Regla</th>
                    <th>SI</th>
                    <th>ENTONCES</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.data.map((rule) => (
                    <tr key={rule.id} style={{ opacity: rule.is_active ? 1 : 0.55 }}>
                      <td className="tabular">{rule.priority}</td>
                      <td>
                        <strong>{rule.name}</strong>
                        <span className="text-caption" style={{ display: "block" }}>
                          {rule.code} · v{rule.version}
                          {rule.min_consecutive > 1 ? ` · confirmar ×${rule.min_consecutive}` : ""}
                        </span>
                        {rule.description && <p className="text-caption">{rule.description}</p>}
                      </td>
                      <td>
                        <Condition node={rule.conditions} />
                      </td>
                      <td>
                        <Action actions={rule.actions} />
                      </td>
                      <td>
                        <Button
                          size="sm"
                          variant={rule.is_active ? "ghost" : "secondary"}
                          onClick={() => {
                            toggle.mutate(rule);
                          }}
                        >
                          {rule.is_active ? "Desactivar" : "Activar"}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card
          title="Inferencia bayesiana (auxiliar)"
          description={activeBayes ? `Configuración "${activeBayes.name}" v${activeBayes.version}. Priors y verosimilitudes definidas por el equipo pedagógico; sin entrenamiento.` : "Sin configuración en base de datos: se usa la de respaldo."}
          actions={
            activeBayes && (
              <Select
                label={<span className="visually-hidden">Evidencia</span>}
                value={showBayes}
                onChange={(e) => {
                  setShowBayes(e.target.value);
                }}
              >
                {Object.keys(activeBayes.likelihoods).map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </Select>
            )
          }
        >
          {bayes.isPending && <Skeleton height="6rem" />}
          {activeBayes && (
            <div className="ds-stack">
              <div className="ds-inline-actions">
                {Object.entries(activeBayes.priors).map(([state, p]) => (
                  <Badge key={state} tone="neutral">
                    P({state}) = {p.toFixed(2)}
                  </Badge>
                ))}
              </div>
              {table && (
                <div className="ds-table-wrap">
                  <table className="ds-table" aria-label={`P(${showBayes} | estado)`}>
                    <thead>
                      <tr>
                        <th>Estado</th>
                        {Object.keys(Object.values(table)[0] ?? {}).map((v) => (
                          <th key={v}>{v}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(table).map(([state, values]) => (
                        <tr key={state}>
                          <td>{state}</td>
                          {Object.values(values).map((p, i) => (
                            <td key={i} className="tabular">
                              {p.toFixed(2)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
