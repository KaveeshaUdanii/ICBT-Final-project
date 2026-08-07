import type { InputHTMLAttributes, LabelHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import clsx from "clsx";

export function Field({
  label,
  children,
  hint,
  ...rest
}: { label: string; children: ReactNode; hint?: string } & LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label className="flex flex-col gap-1.5 text-sm" {...rest}>
      <span className="font-medium text-[var(--text-secondary)]">{label}</span>
      {children}
      {hint && <span className="text-xs text-[var(--text-muted)]">{hint}</span>}
    </label>
  );
}

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={clsx("glass-input rounded-xl px-3.5 py-2.5 text-sm", className)} {...rest} />;
}

export function Textarea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={clsx("glass-input rounded-xl px-3.5 py-2.5 text-sm", className)} {...rest} />;
}

export function Select({ className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={clsx("glass-input rounded-xl px-3.5 py-2.5 text-sm", className)} {...rest}>
      {children}
    </select>
  );
}
