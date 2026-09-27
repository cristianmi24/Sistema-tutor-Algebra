import { clsx } from "clsx";
import { type ButtonHTMLAttributes, type ReactNode, forwardRef } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading = false, leadingIcon, trailingIcon, className, children, disabled, type = "button", ...rest },
  ref,
) {
  const isDisabled = disabled ?? loading;
  return (
    <button
      ref={ref}
      type={type}
      className={clsx("ds-button", `ds-button--${variant}`, `ds-button--${size}`, className)}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span className="ds-button__spinner" aria-hidden="true" /> : leadingIcon}
      <span>{children}</span>
      {!loading && trailingIcon}
    </button>
  );
});
