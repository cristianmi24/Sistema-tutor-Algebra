import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { Alert, Button, Card, Field } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { authApi } from "../api";

const schema = z.object({ email: z.email("Escribe un correo válido.") });
type FormValues = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: "" } });
  const forgot = useMutation({ mutationFn: (values: FormValues) => authApi.forgotPassword(values.email) });

  return (
    <Card title="Recuperar contraseña" description="Te enviaremos un enlace temporal; nunca tu contraseña.">
      {forgot.isSuccess ? (
        <div className="ds-stack">
          <Alert tone="success" title="Revisa tu correo">
            Si la cuenta existe, recibirás un correo con instrucciones en los próximos minutos.
          </Alert>
          <Link to="/login">Volver al inicio de sesión</Link>
        </div>
      ) : (
        <form
          className="ds-stack"
          noValidate
          onSubmit={form.handleSubmit((values) => {
            forgot.mutate(values);
          })}
        >
          <Field label="Correo" type="email" autoComplete="email" error={form.formState.errors.email?.message} {...form.register("email")} />
          {forgot.isError && <Alert tone="error">{errorMessage(forgot.error)}</Alert>}
          <Button type="submit" size="lg" loading={forgot.isPending}>
            Enviar enlace
          </Button>
          <Link to="/login">Volver al inicio de sesión</Link>
        </form>
      )}
    </Card>
  );
}
