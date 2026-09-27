import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { Alert, Button, Card, Checkbox, Field, Select, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";
import { SimpleMarkdown } from "@/lib/markdown/SimpleMarkdown";

import { type RegisterPayload, authApi, authQueryKeys } from "../api";
import { passwordSchema } from "../password";

const STEPS = ["Datos", "Privacidad", "Términos", "Consentimiento", "Cuenta"] as const;

const dataSchema = z.object({
  identifier: z
    .string()
    .trim()
    .min(3, "Mínimo 3 caracteres.")
    .max(254)
    .refine((v) => v.includes("@") || /^[a-zA-Z0-9._-]+$/.test(v), "Solo letras, números, '.', '-' o '_'."),
  password: passwordSchema,
  institution_code: z.string().min(1, "Elige tu institución."),
  grade: z.enum(["7", "8", "9"], { message: "Elige tu grado." }),
  group_code: z.string().trim().max(16).optional(),
  birth_year: z
    .string()
    .optional()
    .refine((v) => !v || /^\d{4}$/.test(v), "Escribe el año con 4 dígitos."),
});
type DataValues = z.infer<typeof dataSchema>;

/**
 * Registro en 5 pasos: datos mínimos → política de privacidad → términos → consentimiento →
 * creación de cuenta. El clic del estudiante no se asume como consentimiento legal suficiente:
 * si la institución exige acudiente, la cuenta queda en PENDING_CONSENT y se explica claramente.
 */
export function RegisterPage() {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<DataValues | null>(null);
  const [readPrivacy, setReadPrivacy] = useState(false);
  const [readTerms, setReadTerms] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [guardianRef, setGuardianRef] = useState("");

  const institutions = useQuery({ queryKey: authQueryKeys.institutions, queryFn: authApi.institutions });
  const legal = useQuery({ queryKey: authQueryKeys.legalDocuments, queryFn: authApi.legalDocuments });
  const privacy = legal.data?.find((d) => d.kind === "PRIVACY_POLICY");
  const terms = legal.data?.find((d) => d.kind === "TERMS");
  const institution = institutions.data?.find((i) => i.code === data?.institution_code);
  const requiresGuardian = institution?.required_consent_parties.includes("GUARDIAN") ?? false;

  const form = useForm<DataValues>({
    resolver: zodResolver(dataSchema),
    defaultValues: { identifier: "", password: "", institution_code: "", grade: "7", group_code: "", birth_year: "" },
  });

  const register = useMutation({
    mutationFn: (payload: RegisterPayload) => authApi.register(payload),
    onSuccess: () => {
      setStep(4);
    },
  });

  const submitRegistration = () => {
    if (!data || !privacy || !terms) return;
    const versions = { privacy_policy_version: privacy.version, terms_version: terms.version };
    const consents: RegisterPayload["consents"] = [{ party: "STUDENT", ...versions, status: "ACCEPTED" }];
    if (requiresGuardian && guardianRef.trim()) {
      consents.push({ party: "GUARDIAN", ...versions, status: "ACCEPTED", guardian_reference: guardianRef.trim() });
    }
    register.mutate({
      identifier: data.identifier,
      password: data.password,
      institution_code: data.institution_code,
      grade: data.grade,
      ...(data.group_code ? { group_code: data.group_code } : {}),
      ...(data.birth_year ? { birth_year: Number(data.birth_year) } : {}),
      consents,
    });
  };

  return (
    <Card title="Crear cuenta de estudiante" description="Cinco pasos cortos. Puedes volver atrás en cualquier momento.">
      <ol className="ds-steps" aria-label="Progreso del registro">
        {STEPS.map((label, i) => (
          <li key={label} aria-current={i === step ? "step" : undefined} data-done={i < step}>
            {label}
          </li>
        ))}
      </ol>

      {step === 0 && (
        <form
          className="ds-stack"
          noValidate
          onSubmit={form.handleSubmit((values) => {
            setData(values);
            setStep(1);
          })}
        >
          <Field
            label="Usuario o correo institucional"
            hint="Si no tienes correo, elige un usuario. Evita usar tu nombre completo."
            autoComplete="username"
            error={form.formState.errors.identifier?.message}
            {...form.register("identifier")}
          />
          <Field label="Contraseña" type="password" autoComplete="new-password" hint="Al menos 10 caracteres." error={form.formState.errors.password?.message} {...form.register("password")} />
          {institutions.isPending ? (
            <Skeleton height="44px" label="Cargando instituciones" />
          ) : (
            <Select label="Institución" error={form.formState.errors.institution_code?.message} {...form.register("institution_code")}>
              <option value="">Selecciona…</option>
              {institutions.data?.map((i) => (
                <option key={i.code} value={i.code}>
                  {i.name}
                </option>
              ))}
            </Select>
          )}
          <div className="ds-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
            <Select label="Grado" error={form.formState.errors.grade?.message} {...form.register("grade")}>
              <option value="7">7.º</option>
              <option value="8">8.º</option>
              <option value="9">9.º</option>
            </Select>
            <Field label="Grupo" placeholder="A" error={form.formState.errors.group_code?.message} {...form.register("group_code")} />
            <Field label="Año de nacimiento" inputMode="numeric" placeholder="2012" hint="Opcional" error={form.formState.errors.birth_year?.message} {...form.register("birth_year")} />
          </div>
          {institutions.isError && <Alert tone="error">{errorMessage(institutions.error)}</Alert>}
          <Button type="submit" size="lg">
            Continuar
          </Button>
          <Link to="/login">Ya tengo cuenta</Link>
        </form>
      )}

      {step === 1 && (
        <div className="ds-stack">
          {privacy ? <SimpleMarkdown source={privacy.body_markdown} /> : <Skeleton height="200px" label="Cargando política" />}
          <p className="text-caption">Versión {privacy?.version ?? "…"}</p>
          <Checkbox
            label="Leí la política de privacidad y entiendo qué datos se recogen, para qué y quién puede verlos."
            checked={readPrivacy}
            onChange={(e) => {
              setReadPrivacy(e.target.checked);
            }}
          />
          <div className="ds-inline-actions">
            <Button
              variant="secondary"
              onClick={() => {
                setStep(0);
              }}
            >
              Atrás
            </Button>
            <Button
              disabled={!readPrivacy || !privacy}
              onClick={() => {
                setStep(2);
              }}
            >
              Continuar
            </Button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="ds-stack">
          {terms ? <SimpleMarkdown source={terms.body_markdown} /> : <Skeleton height="200px" label="Cargando términos" />}
          <p className="text-caption">Versión {terms?.version ?? "…"}</p>
          <Checkbox
            label="Leí y acepto los términos de uso."
            checked={readTerms}
            onChange={(e) => {
              setReadTerms(e.target.checked);
            }}
          />
          <div className="ds-inline-actions">
            <Button
              variant="secondary"
              onClick={() => {
                setStep(1);
              }}
            >
              Atrás
            </Button>
            <Button
              disabled={!readTerms || !terms}
              onClick={() => {
                setStep(3);
              }}
            >
              Continuar
            </Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="ds-stack">
          <Alert tone="info" title="Tu participación en la investigación">
            Tus producciones se usarán en una investigación educativa identificadas solo con un código (por ejemplo, STU-014). Puedes retirarte
            cuando quieras sin consecuencias en tus clases.
          </Alert>
          <Checkbox
            label="Acepto participar y autorizo el uso de mis datos según la política y los términos que leí."
            checked={accepted}
            onChange={(e) => {
              setAccepted(e.target.checked);
            }}
          />
          {requiresGuardian && (
            <>
              <Alert tone="warning" title="Tu institución requiere autorización de tu acudiente">
                Podrás usar la plataforma desde ya, pero tu información no entrará en la investigación hasta que tu madre, padre o acudiente autorice
                según el protocolo de la institución. Si ya tienes esa autorización, indica su referencia.
              </Alert>
              <Field
                label="Referencia de la autorización del acudiente (opcional)"
                placeholder="p. ej., formato F-03 firmado el 12/03"
                value={guardianRef}
                onChange={(e) => {
                  setGuardianRef(e.target.value);
                }}
              />
            </>
          )}
          {register.isError && (
            <Alert tone="error" title="No pudimos crear la cuenta">
              {errorMessage(register.error)}
            </Alert>
          )}
          <div className="ds-inline-actions">
            <Button
              variant="secondary"
              onClick={() => {
                setStep(2);
              }}
            >
              Atrás
            </Button>
            <Button disabled={!accepted} loading={register.isPending} onClick={submitRegistration}>
              Crear mi cuenta
            </Button>
          </div>
        </div>
      )}

      {step === 4 && register.data && (
        <div className="ds-stack">
          <Alert tone="success" title="¡Cuenta creada!">
            Tu código de participante es <strong className="tabular">{register.data.participant_code}</strong>.
            {register.data.status === "PENDING_CONSENT"
              ? " Ya puedes entrar y trabajar. Tu información se incluirá en la investigación cuando se registre la autorización de tu acudiente."
              : " Ya puedes iniciar sesión."}
          </Alert>
          <Link to="/login">Ir al inicio de sesión</Link>
        </div>
      )}
    </Card>
  );
}
