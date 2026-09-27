import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { Alert, Badge, Card, PageHeader, Skeleton } from "@/design-system/components";
import { useSession } from "@/features/auth/session-store";
import { Timeline } from "@/features/shared/Timeline";
import { errorMessage } from "@/lib/api";
import { asText } from "@/lib/text";

import { TRIGGER_LABEL, researchApi, researchQueryKeys } from "../api";
import { MemoEditor } from "../components/MemoEditor";

export function EpisodeDetailPage() {
  const { episodeId = "" } = useParams();
  const { user } = useSession();
  const isResearcher = user?.role === "RESEARCHER";
  const episode = useQuery({ queryKey: researchQueryKeys.episode(episodeId), queryFn: () => researchApi.episode(episodeId) });
  if (episode.isPending) return <Skeleton height="12rem" />;
  if (episode.isError) return <Alert tone="error">{errorMessage(episode.error)}</Alert>;
  const e = episode.data;
  const task = e.context.task as Record<string, unknown> | null;
  const summary = e.summary;

  return (
    <>
      <PageHeader
        eyebrow={`Episodio · ${e.participant_code ?? ""}`}
        title={e.task_title ?? "Episodio"}
        description={asText(task?.prompt, "")}
        actions={
          isResearcher && (
            <Link to={`/researcher/compare?a=${e.id}`} className="ds-button ds-button--secondary ds-button--md">
              Comparar con otro episodio
            </Link>
          )
        }
      />
      <div className="ds-stack">
        <Card title="Contexto" description="Registro automático del sistema.">
          <div className="ds-inline-actions">
            <Badge tone="info">{TRIGGER_LABEL[e.trigger] ?? e.trigger}</Badge>
            <Badge tone="neutral">{e.status === "OPEN" ? "abierto" : `cerrado: ${e.close_reason ?? "—"}`}</Badge>
            <Badge tone="secondary">{asText(task?.task_type)}</Badge>
            <span className="text-caption">
              {e.interaction_count} eventos · {asText(summary.duration_seconds)} s · ayudas {((summary.help_levels_sequence as number[] | undefined) ?? []).join(" → ") || "ninguna"} ·
              aceptadas {asText(summary.help_accepted)} · rechazadas {asText(summary.help_rejected)}
            </span>
          </div>
          <p className="text-caption" style={{ marginTop: "var(--space-2)" }}>
            {asText(summary.note, "")}
          </p>
        </Card>
        <div className="activity__two">
          <Card title="Trayectoria">
            <Timeline steps={e.timeline} />
          </Card>
          <div className="ds-stack">
            <Card title="Memos de este episodio" description="Tus categorías permanecen separadas de las clasificaciones del sistema.">
              {e.memos.length === 0 && <p className="text-muted">Aún no hay memos.</p>}
              {e.memos.map((m) => (
                <details key={m.id} className="question">
                  <summary>
                    <strong>{m.title}</strong> <span className="text-caption">{m.researcher_code}</span>
                    {m.possible_category && (
                      <Badge tone="primary" style={{ marginLeft: 8 }}>
                        {m.possible_category}
                      </Badge>
                    )}
                  </summary>
                  {isResearcher ? <MemoEditor memo={m} /> : <p>{m.observation}</p>}
                </details>
              ))}
            </Card>
            {isResearcher && (
              <Card title="Nuevo memo">
                <MemoEditor episodeId={e.id} participantCode={e.participant_code} />
              </Card>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
