import { type InputHTMLAttributes, type ReactNode, forwardRef, useId } from "react";

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "type"> {
  label: ReactNode;
  error?: string | undefined;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox({ label, error, ...rest }, ref) {
  const id = useId();
  return (
    <div className="ds-field">
      <label htmlFor={id} className="ds-checkbox">
        <input ref={ref} id={id} type="checkbox" aria-invalid={error ? true : undefined} {...rest} />
        <span>{label}</span>
      </label>
      {error && (
        <p className="ds-field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
});
