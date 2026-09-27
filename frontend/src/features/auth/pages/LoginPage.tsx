import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { Alert, Button, Card, Field } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { authApi } from "../api";
import { HOME_BY_ROLE, useSession } from "../session-store";

const schema = z.object({
  identifier: z.string().trim().min(3, "Escribe tu usuario o correo."),
  password: z.string().min(1, "Escribe tu contraseña."),
});
type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;

  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { identifier: "", password: "" } });
  const login = useMutation({
    mutationFn: (values: FormValues) => authApi.login(values.identifier, values.password),
    onSuccess: (data) => {
      signIn(data.user, data.access_token);
      const home = HOME_BY_ROLE[data.user.role];
      void navigate(from?.startsWith(home) ? from : home, { replace: true });
    },
  });

  return (
    <Card title="Iniciar sesión" description="Accede con tu usuario o correo institucional.">
      <form
        className="ds-stack"
        noValidate
        onSubmit={form.handleSubmit((values) => {
          login.mutate(values);
        })}
      >
        <Field label="Usuario o correo" autoComplete="username" error={form.formState.errors.identifier?.message} {...form.register("identifier")} />
        <Field
          label="Contraseña"
          type="password"
          autoComplete="current-password"
          error={form.formState.errors.password?.message}
          {...form.register("password")}
        />
        {login.isError && (
          <Alert tone="error" title="No pudimos iniciar sesión">
            {errorMessage(login.error)}
          </Alert>
        )}
        <Button type="submit" size="lg" loading={login.isPending}>
          Entrar
        </Button>
        <p className="text-caption" style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
          <Link to="/forgot-password">¿Olvidaste tu contraseña?</Link>
          <Link to="/register">Crear cuenta de estudiante</Link>
        </p>
      </form>
    </Card>
  );
}
