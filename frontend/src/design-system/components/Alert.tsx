import { clsx } from "clsx";
import { AlertTriangle, CheckCircle2, Cpu, type LucideIcon, UserRound, XCircle } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

/**
 * `info`    → mensajes e intervenciones del SISTEMA.
 * `teacher` → intervenciones del DOCENTE (siempre visualmente distintas del sistema).
 */
export type AlertTone = "info" | "success" | "warning" | "error" | "teacher";

const ICONS: Record<AlertTone, LucideIcon> = {
  info: Cpu,
  success: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
  teacher: UserRound,
};

const SOURCE_LABEL: Record<AlertTone, string> = {
  info: "Mensaje del sistema",
  success: "Confirmación",
  warning: "Aviso",
  error: "Error",
  teacher: "Mensaje del docente",
};

export interface AlertProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  tone?: AlertTone;
  title?: ReactNode;
}

export function Alert({ tone = "info", title, className, children, ...rest }: AlertProps) {
  const Icon = ICONS[tone];
  const live = tone === "error" || tone === "warning" ? "assertive" : "polite";
  return (
    <div role={tone === "error" ? "alert" : "status"} aria-live={live} className={clsx("ds-alert", `ds-alert--${tone}`, className)} {...rest}>
      <Icon className="ds-alert__icon" size={20} aria-hidden="true" />
      <div>
        <span className="visually-hidden">{SOURCE_LABEL[tone]}: </span>
        {title !== undefined && <p className="ds-alert__title">{title}</p>}
        {children !== undefined && <div className="ds-alert__body">{children}</div>}
      </div>
    </div>
  );
}
