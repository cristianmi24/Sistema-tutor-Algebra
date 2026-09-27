import { clsx } from "clsx";
import type { HTMLAttributes, ReactNode } from "react";

export type BadgeTone = "neutral" | "primary" | "secondary" | "success" | "warning" | "error" | "info" | "teacher";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  /** Icono obligatorio recomendado: los estados no deben comunicarse solo por color. */
  icon?: ReactNode;
}

export function Badge({ tone = "neutral", icon, className, children, ...rest }: BadgeProps) {
  return (
    <span className={clsx("ds-badge", `ds-badge--${tone}`, className)} {...rest}>
      {icon}
      {children}
    </span>
  );
}
