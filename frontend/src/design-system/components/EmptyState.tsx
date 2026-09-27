import type { ReactNode } from "react";

export interface EmptyStateProps {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="ds-empty">
      {icon !== undefined && (
        <div className="ds-empty__icon" aria-hidden="true">
          {icon}
        </div>
      )}
      <h3 className="ds-empty__title">{title}</h3>
      {description !== undefined && <p>{description}</p>}
      {action}
    </div>
  );
}
