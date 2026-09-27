import { clsx } from "clsx";
import { CircleAlert } from "lucide-react";
import { type ReactNode, type SelectHTMLAttributes, forwardRef, useId } from "react";

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> {
  label: ReactNode;
  hint?: ReactNode;
  error?: string | undefined;
  id?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select({ label, hint, error, id, className, children, ...rest }, ref) {
  const autoId = useId();
  const selectId = id ?? autoId;
  const hintId = `${selectId}-hint`;
  const errorId = `${selectId}-error`;
  const describedBy = [hint !== undefined ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={clsx("ds-field", className)}>
      <label htmlFor={selectId} className="ds-field__label">
        {label}
      </label>
      <select ref={ref} id={selectId} className="ds-input" aria-invalid={error ? true : undefined} aria-describedby={describedBy} {...rest}>
        {children}
      </select>
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
