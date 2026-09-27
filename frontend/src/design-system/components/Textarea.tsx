import { clsx } from "clsx";
import { CircleAlert } from "lucide-react";
import { type ReactNode, type TextareaHTMLAttributes, forwardRef, useId } from "react";

export interface TextareaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id"> {
  label: ReactNode;
  hint?: ReactNode;
  error?: string | undefined;
  id?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea({ label, hint, error, id, className, ...rest }, ref) {
  const autoId = useId();
  const areaId = id ?? autoId;
  const hintId = `${areaId}-hint`;
  const errorId = `${areaId}-error`;
  const describedBy = [hint !== undefined ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={clsx("ds-field", className)}>
      <label htmlFor={areaId} className="ds-field__label">
        {label}
      </label>
      <textarea ref={ref} id={areaId} className="ds-input ds-textarea" aria-invalid={error ? true : undefined} aria-describedby={describedBy} {...rest} />
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
