import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Alert, Badge, Card, PageHeader, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { researchApi, researchQueryKeys } from "../api";
import { MemoEditor } from "../components/MemoEditor";

export function MemosPage() {
  const memos = useQuery({ queryKey: researchQueryKeys.memos({}), queryFn: () => researchApi.memos() });
  return (
    <>
      <PageHeader
        eyebrow="Investigación"
        title="Memos analíticos"
        description="Observación, interpretación, preguntas emergentes, contradicciones, casos negativos, categorías posibles y muestreo teórico."
      />
      <div className="activity__two">
        <Card title="Mis memos">
          {memos.isPending && <Skeleton height="8rem" />}
          {memos.isError && <Alert tone="error">{errorMessage(memos.error)}</Alert>}
          {memos.data?.length === 0 && <p className="text-muted">Aún no has escrito memos.</p>}
          <div className="ds-stack">
            {memos.data?.map((m) => (
              <details key={m.id} className="question">
                <summary>
                  <strong>{m.title}</strong> <span className="text-caption">{new Date(m.updated_at).toLocaleDateString("es-CO")}</span>{" "}
                  {m.participant_code && <Badge tone="neutral">{m.participant_code}</Badge>}{" "}
                  {m.possible_category && <Badge tone="primary">{m.possible_category}</Badge>}{" "}
                  {m.tags.map((t) => (
                    <Badge key={t} tone="secondary">
                      #{t}
                    </Badge>
                  ))}
                </summary>
                {m.episode_id && (
                  <p className="text-caption">
                    <Link to={`/researcher/episodes/${m.episode_id}`}>Ver episodio</Link>
                  </p>
                )}
                <MemoEditor memo={m} />
              </details>
            ))}
          </div>
        </Card>
        <Card title="Nuevo memo general">
          <MemoEditor />
        </Card>
      </div>
    </>
  );
}
