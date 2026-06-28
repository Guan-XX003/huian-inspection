import type { ReactNode } from "react";

export function Panel({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h3 className="panel-title">{title}</h3>
          {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function Tag({ children, tone }: { children: ReactNode; tone?: "green" | "red" | "blue" }) {
  return <span className={`tag ${tone ?? ""}`}>{children}</span>;
}

export function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="panel metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

