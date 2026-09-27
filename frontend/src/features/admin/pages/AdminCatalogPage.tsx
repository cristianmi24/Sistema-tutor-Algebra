import { useQuery } from "@tanstack/react-query";

import { Alert, Badge, Card, PageHeader, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";
import { asText } from "@/lib/text";

import { tutorApi, tutorQueryKeys } from "../tutorApi";

export function AdminCatalogPage() {
  const tasks = useQuery({ queryKey: tutorQueryKeys.tasks, queryFn: tutorApi.tasks });
  const scaffolds = useQuery({ queryKey: tutorQueryKeys.scaffolds, queryFn: tutorApi.scaffolds });
  return (
    <>
      <PageHeader eyebrow="Catálogo pedagógico" title="Actividades y banco de andamiajes" description="Contenido revisado por el equipo pedagógico. Las ayudas nunca contienen la solución." />
      <div className="ds-stack">
        <Card title="Actividades (tipos A–G)">
          {tasks.isPending && <Skeleton height="6rem" />}
          {tasks.isError && <Alert tone="error">{errorMessage(tasks.error)}</Alert>}
          {tasks.data && (
            <div className="ds-table-wrap">
              <table className="ds-table">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Título</th>
                    <th>Tipo</th>
                    <th>Habilidad</th>
                    <th>Dificultad</th>
                    <th>Grados</th>
                    <th>Regla (privada)</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.data.map((t) => (
                    <tr key={t.id}>
                      <td className="tabular">{t.code}</td>
                      <td>{t.title}</td>
                      <td>
                        <Badge tone="secondary">{t.task_type}</Badge>
                      </td>
                      <td>{t.skill}</td>
                      <td className="tabular">{t.difficulty}</td>
                      <td className="tabular">
                        {t.grade_min}–{t.grade_max}
                      </td>
                      <td>
                        <code>{asText(t.solution.expression)}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card title="Banco de andamiajes" description="Nivel 1 microayuda · 2 orientación · 3 andamiaje · 4 cambio de representación · 5 recuperación.">
          {scaffolds.isPending && <Skeleton height="6rem" />}
          {scaffolds.isError && <Alert tone="error">{errorMessage(scaffolds.error)}</Alert>}
          {scaffolds.data && (
            <div className="ds-table-wrap">
              <table className="ds-table">
                <thead>
                  <tr>
                    <th>Nivel</th>
                    <th>Código</th>
                    <th>Tipo</th>
                    <th>Texto</th>
                    <th>Aplica a</th>
                  </tr>
                </thead>
                <tbody>
                  {scaffolds.data.map((s) => (
                    <tr key={s.id} style={{ opacity: s.is_active ? 1 : 0.55 }}>
                      <td className="tabular">{s.level}</td>
                      <td className="tabular">{s.code}</td>
                      <td>
                        <Badge tone="info">{s.scaffold_type}</Badge>
                      </td>
                      <td>
                        {asText(s.content.text, "")}
                        {Array.isArray(s.content.variants) && <span className="text-caption" style={{ display: "block" }}>{(s.content.variants as string[]).length} variante(s)</span>}
                      </td>
                      <td className="text-caption">{s.applicable_task_types.length ? s.applicable_task_types.join(", ") : "todas"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
