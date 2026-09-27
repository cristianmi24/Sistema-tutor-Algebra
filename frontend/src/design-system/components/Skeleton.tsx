import type { CSSProperties } from "react";

export interface SkeletonProps {
  width?: CSSProperties["width"];
  height?: CSSProperties["height"];
  label?: string;
}

export function Skeleton({ width = "100%", height = "1rem", label = "Cargando" }: SkeletonProps) {
  return <span className="ds-skeleton" style={{ width, height }} role="status" aria-label={label} />;
}
