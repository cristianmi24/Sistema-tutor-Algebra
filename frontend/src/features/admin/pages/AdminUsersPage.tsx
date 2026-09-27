import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, Badge, Button, Card, Field, PageHeader, Select, Skeleton } from "@/design-system/components";
import { passwordSchema } from "@/features/auth/password";
import { errorMessage } from "@/lib/api";

import { adminApi, adminQueryKeys } from "../api";

const schema = z.object({
  email: z.email("Correo inválido."),
  password: passwordSchema,
  role: z.enum(["TEACHER", "RESEARCHER", "ADMIN"]),
  institution_code: z.string().optional(),
  groups: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

const ROLE_LABEL: Record<string, string> = { STUDENT: "Estudiante", TEACHER: "Docente", RESEARCHER: "Investigador/a", ADMIN: "Admin" };

export function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [roleFilter, setRoleFilter] = useState<string>("");
  const params = { role: roleFilter || undefined, page_size: 50 };
  const users = useQuery({ queryKey: adminQueryKeys.users(params), queryFn: () => adminApi.users(params) });
  const institutions = useQuery({ queryKey: adminQueryKeys.institutions, queryFn: adminApi.institutions });

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "", role: "TEACHER", institution_code: "", groups: "" },
  });
  const create = useMutation({
    mutationFn: (values: FormValues) =>
      adminApi.createUser({
        email: values.email,
        password: values.password,
        role: values.role,
        ...(values.institution_code ? { institution_code: values.institution_code } : {}),
        group_assignments: (values.groups ?? "")
          .split(",")
          .map((g) => g.trim())
          .filter(Boolean)
          .map((g) => {
            const [grade, group] = g.split("-");
            return { grade: (grade ?? "7") as "7" | "8" | "9", group_code: group ?? "A" };
          }),
      }),
    onSuccess: () => {
      form.reset();
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
  const anonymize = useMutation({
    mutationFn: (id: string) => adminApi.anonymize(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
  const toggle = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "ACTIVE" | "DISABLED" }) => adminApi.setUserStatus(id, status),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  return (
    <>
      <PageHeader eyebrow="Administración" title="Usuarios" description="Cuentas de docentes, investigadores y administradores. Los estudiantes se registran con consentimiento." />
      <div className="ds-grid" style={{ gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)" }}>
        <Card
          title="Cuentas"
          actions={
            <Select
              label={<span className="visually-hidden">Filtrar por rol</span>}
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
              }}
            >
              <option value="">Todos los roles</option>
              <option value="STUDENT">Estudiantes</option>
              <option value="TEACHER">Docentes</option>
              <option value="RESEARCHER">Investigadores</option>
              <option value="ADMIN">Administradores</option>
            </Select>
          }
        >
          {users.isPending && <Skeleton height="8rem" />}
          {users.isError && <Alert tone="error">{errorMessage(users.error)}</Alert>}
          {anonymize.isError && <Alert tone="error">{errorMessage(anonymize.error)}</Alert>}
          {users.data && (
            <div className="ds-table-wrap">
              <table className="ds-table">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Rol</th>
                    <th>Identificador</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {users.data.items.map((u) => (
                    <tr key={u.id}>
                      <td className="tabular">{u.display_code}</td>
                      <td>{ROLE_LABEL[u.role] ?? u.role}</td>
                      <td>{u.email ?? u.username ?? "—"}</td>
                      <td>
                        <Badge tone={u.status === "ACTIVE" ? "success" : u.status === "DISABLED" ? "error" : "warning"}>{u.status}</Badge>
                      </td>
                      <td>
                        <Button
                          size="sm"
                          variant={u.status === "DISABLED" ? "secondary" : "ghost"}
                          onClick={() => {
                            toggle.mutate({ id: u.id, status: u.status === "DISABLED" ? "ACTIVE" : "DISABLED" });
                          }}
                        >
                          {u.status === "DISABLED" ? "Reactivar" : "Deshabilitar"}
                        </Button>{" "}
                        {!u.username?.startsWith("anon-") && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              if (window.confirm(`¿Anonimizar ${u.display_code}? Se eliminan sus datos personales de forma irreversible; sus registros de investigación quedan con el código.`)) {
                                anonymize.mutate(u.id);
                              }
                            }}
                          >
                            Anonimizar
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-caption">Total: {users.data.total}</p>
            </div>
          )}
        </Card>
        <Card title="Nueva cuenta de personal">
          <form
            className="ds-stack"
            noValidate
            onSubmit={form.handleSubmit((values) => {
              create.mutate(values);
            })}
          >
            <Field label="Correo" type="email" error={form.formState.errors.email?.message} {...form.register("email")} />
            <Field label="Contraseña inicial" type="password" autoComplete="new-password" error={form.formState.errors.password?.message} {...form.register("password")} />
            <Select label="Rol" {...form.register("role")}>
              <option value="TEACHER">Docente</option>
              <option value="RESEARCHER">Investigador/a</option>
              <option value="ADMIN">Administrador/a</option>
            </Select>
            <Select label="Institución" {...form.register("institution_code")}>
              <option value="">Sin institución (solo ADMIN/investigación global)</option>
              {institutions.data?.map((i) => (
                <option key={i.code} value={i.code}>
                  {i.name}
                </option>
              ))}
            </Select>
            <Field label="Grupos del docente" hint="Formato grado-grupo separados por coma: 7-A, 8-B" {...form.register("groups")} />
            {create.isError && <Alert tone="error">{errorMessage(create.error)}</Alert>}
            {create.isSuccess && <Alert tone="success">Cuenta creada: {create.data.display_code}</Alert>}
            <Button type="submit" loading={create.isPending} leadingIcon={<UserPlus size={16} aria-hidden />}>
              Crear cuenta
            </Button>
          </form>
        </Card>
      </div>
    </>
  );
}
