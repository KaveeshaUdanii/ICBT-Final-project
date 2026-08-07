import type { HTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  strong?: boolean;
  hoverable?: boolean;
}

export function GlassCard({ children, strong, hoverable = true, className, ...rest }: GlassCardProps) {
  return (
    <div
      className={clsx(
        strong ? "glass-panel-strong" : "glass-card",
        "rounded-3xl",
        hoverable ? "" : "hover:translate-y-0",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
