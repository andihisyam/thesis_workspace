type PageHeaderProps = {
  title: string;
  description: string;
  badge?: string;
};

export default function PageHeader({
  title,
  description,
  badge
}: PageHeaderProps) {
  return (
    <header className="page-header">
      <div>
        {badge ? <span className="badge">{badge}</span> : null}
        <h2>{title}</h2>
        <p className="muted">{description}</p>
      </div>
    </header>
  );
}
