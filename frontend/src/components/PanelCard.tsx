import { ReactNode } from "react";

type PanelCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

export default function PanelCard({
  title,
  subtitle,
  children
}: PanelCardProps) {
  return (
    <section className="panel-card">
      <div className="panel-card-header">
        <div>
          <h3>{title}</h3>
          {subtitle ? <p className="muted">{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}
