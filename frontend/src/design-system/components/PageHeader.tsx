import type { ReactNode } from "react";

export interface PageHeaderProps {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="ds-page-header">
      <div>
        {eyebrow !== undefined && <p className="ds-page-header__eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description !== undefined && <p className="ds-page-header__description">{description}</p>}
      </div>
      {actions !== undefined && <div>{actions}</div>}
    </div>
  );
}
