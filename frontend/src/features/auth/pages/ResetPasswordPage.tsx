import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { Alert, Button, Card, Field } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { authApi } from "../api";
import { passwordSchema } from "../password";

const schema = z
  .object({ password: passwordSchema, confirm: z.string() })
  .refine((v) => v.password === v.confirm, { message: "Las contraseñas no coinciden.", path: ["confirm"] });
type FormValues = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { password: "", confirm: "" } });
  const reset = useMutation({ mutationFn: (values: FormValues) => authApi.resetPassword(token, values.password) });

  if (!token) {
    return (
      <Card title="Restablecer contraseña">
        <div className="ds-stack">
          <Alert tone="warning" title="Enlace incompleto">
            Abre el enlace completo que recibiste por correo o solicita uno nuevo.
          </Alert>
          <Link to="/forgot-password">Solicitar un nuevo enlace</Link>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Restablecer contraseña" description="Elige una contraseña nueva de al menos 10 caracteres.">
      {reset.isSuccess ? (
        <div className="ds-stack">
          <Alert tone="success" title="Contraseña actualizada">
            Ya puedes iniciar sesión con tu nueva contraseña. Las sesiones anteriores se cerraron por seguridad.
          </Alert>
          <Link to="/login">Ir al inicio de sesión</Link>
        </div>
      ) : (
        <form
          className="ds-stack"
          noValidate
          onSubmit={form.handleSubmit((values) => {
            reset.mutate(values);
          })}
        >
          <Field label="Nueva contraseña" type="password" autoComplete="new-password" error={form.formState.errors.password?.message} {...form.register("password")} />
          <Field label="Confirmar contraseña" type="password" autoComplete="new-password" error={form.formState.errors.confirm?.message} {...form.register("confirm")} />
          {reset.isError && <Alert tone="error">{errorMessage(reset.error)}</Alert>}
          <Button type="submit" size="lg" loading={reset.isPending}>
            Guardar contraseña
          </Button>
        </form>
      )}
    </Card>
  );
}
