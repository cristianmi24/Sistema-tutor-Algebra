import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, Badge, Button, Card, Checkbox, Field, PageHeader, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { adminApi, adminQueryKeys } from "../api";

const schema = z.object({
  code: z.string().regex(/^[A-Z0-9_-]{2,32}$/, "Código en mayúsculas, sin espacios."),
  name: z.string().trim().min(2, "Nombre requerido."),
  city: z.string().trim().optional(),
  requireGuardian: z.boolean(),
  retention_days: z
    .string()
    .optional()
    .refine((v) => !v || (/^\d+$/.test(v) && Number(v) >= 30 && Number(v) <= 3650), "Entre 30 y 3650 días."),
});
type FormValues = z.infer<typeof schema>;

export function AdminInstitutionsPage() {
  const queryClient = useQueryClient();
  const institutions = useQuery({ queryKey: adminQueryKeys.institutions, queryFn: adminApi.institutions });
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { code: "", name: "", city: "", requireGuardian: true, retention_days: "1095" },
  });
  const create = useMutation({
    mutationFn: (values: FormValues) =>
      adminApi.createInstitution({
        code: values.code,
        name: values.name,
        country: "CO",
        ...(values.city ? { city: values.city } : {}),
        consent_policy: { required_parties: values.requireGuardian ? ["STUDENT", "GUARDIAN"] : ["STUDENT"] },
        ...(values.retention_days ? { retention_days: Number(values.retention_days) } : {}),
      }),
    onSuccess: () => {
      form.reset();
      void queryClient.invalidateQueries({ queryKey: adminQueryKeys.institutions });
    },
  });

  return (
    <>
      <PageHeader eyebrow="Administración" title="Instituciones" description="Cada institución define su política de consentimiento y su retención de datos." />
      <div className="ds-grid" style={{ gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)" }}>
        <Card title="Registradas">
          {institutions.isPending && <Skeleton height="6rem" />}
          {institutions.isError && <Alert tone="error">{errorMessage(institutions.error)}</Alert>}
          {institutions.data && (
            <div className="ds-table-wrap">
              <table className="ds-table">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Nombre</th>
                    <th>Consentimiento requerido</th>
                    <th>Retención</th>
                  </tr>
                </thead>
                <tbody>
                  {institutions.data.map((i) => (
                    <tr key={i.id}>
                      <td className="tabular">{i.code}</td>
                      <td>{i.name}</td>
                      <td>
                        {((i.consent_policy.required_parties as string[] | undefined) ?? ["STUDENT"]).map((p) => (
                          <Badge key={p} tone="neutral" style={{ marginRight: 4 }}>
                            {p}
                          </Badge>
                        ))}
                      </td>
                      <td className="tabular">{i.retention_days ? `${i.retention_days} días` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card title="Nueva institución">
          <form
            className="ds-stack"
            noValidate
            onSubmit={form.handleSubmit((values) => {
              create.mutate(values);
            })}
          >
            <Field label="Código" placeholder="IE-NORTE" error={form.formState.errors.code?.message} {...form.register("code")} />
            <Field label="Nombre" error={form.formState.errors.name?.message} {...form.register("name")} />
            <Field label="Ciudad" {...form.register("city")} />
            <Field label="Retención (días)" inputMode="numeric" error={form.formState.errors.retention_days?.message} {...form.register("retention_days")} />
            <Checkbox label="Requerir autorización de acudiente para menores" {...form.register("requireGuardian")} />
            {create.isError && <Alert tone="error">{errorMessage(create.error)}</Alert>}
            <Button type="submit" loading={create.isPending}>
              Crear institución
            </Button>
          </form>
        </Card>
      </div>
    </>
  );
}
