import { clsx } from "clsx";
import { CircleAlert } from "lucide-react";
import { type InputHTMLAttributes, type ReactNode, forwardRef, useId } from "react";

export interface FieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  label: ReactNode;
  hint?: ReactNode;
  error?: string | undefined;
  id?: string;
}

/** Campo de formulario accesible: label, ayuda y error enlazados por aria-describedby. */
export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field({ label, hint, error, id, className, ...rest }, ref) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  const describedBy = [hint !== undefined ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;

  return (
    <div className={clsx("ds-field", className)}>
      <label htmlFor={inputId} className="ds-field__label">
        {label}
      </label>
      <input ref={ref} id={inputId} className="ds-input" aria-invalid={error ? true : undefined} aria-describedby={describedBy} {...rest} />
      {hint !== undefined && (
        <p id={hintId} className="ds-field__hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="ds-field__error" role="alert">
          <CircleAlert size={14} aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  );
});
