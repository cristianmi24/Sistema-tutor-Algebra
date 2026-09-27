import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Alert, Badge, Card, EmptyState, PageHeader, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { researchApi, researchQueryKeys } from "../api";

export function ResearcherDashboardPage() {
  const participants = useQuery({ queryKey: researchQueryKeys.participants, queryFn: researchApi.participants });
  return (
    <>
      <PageHeader
        eyebrow="Investigación"
        title="Participantes"
        description="Solo participantes con consentimiento efectivo, identificados por código. El sistema registra; la interpretación es tuya."
      />
      <Card>
        {participants.isPending && <Skeleton height="8rem" />}
        {participants.isError && <Alert tone="error">{errorMessage(participants.error)}</Alert>}
        {participants.data?.length === 0 && <EmptyState title="Sin participantes aún" description="Aparecerán cuando haya estudiantes con consentimiento efectivo." />}
        {participants.data && participants.data.length > 0 && (
          <div className="ds-table-wrap">
            <table className="ds-table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Institución</th>
                  <th>Grado</th>
                  <th>Grupo</th>
                  <th>Sesiones</th>
                  <th>Actividades</th>
                  <th>Eventos</th>
                  <th>Episodios</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {participants.data.map((p) => (
                  <tr key={p.student_id}>
                    <td className="tabular">
                      <strong>{p.participant_code}</strong>
                    </td>
                    <td>{p.institution_code}</td>
                    <td>{p.grade}.º</td>
                    <td>{p.group_code ?? "—"}</td>
                    <td className="tabular">{p.sessions}</td>
                    <td className="tabular">{p.tasks_worked}</td>
                    <td className="tabular">{p.interactions}</td>
                    <td className="tabular">
                      <Badge tone={p.episodes ? "primary" : "neutral"}>{p.episodes}</Badge>
                    </td>
                    <td>
                      <Link to={`/researcher/sessions?student=${p.student_id}`}>Sesiones</Link> ·{" "}
                      <Link to={`/researcher/episodes?student=${p.student_id}`}>Episodios</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
