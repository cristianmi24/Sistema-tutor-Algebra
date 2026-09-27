import { clsx } from "clsx";
import type { HTMLAttributes, ReactNode } from "react";

export interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  interactive?: boolean;
  as?: "div" | "section" | "article";
}

export function Card({ title, description, actions, interactive = false, as: Tag = "section", className, children, ...rest }: CardProps) {
  const hasHeader = title !== undefined || description !== undefined || actions !== undefined;
  return (
    <Tag className={clsx("ds-card", interactive && "ds-card--interactive", className)} {...rest}>
      {hasHeader && (
        <header className="ds-card__header">
          <div>
            {title !== undefined && <h3 className="ds-card__title">{title}</h3>}
            {description !== undefined && <p className="ds-card__description">{description}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </Tag>
  );
}
