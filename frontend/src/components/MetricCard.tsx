type MetricCardProps = {
  label: string;
  value: string;
  tone?: "primary" | "accent";
};

export default function MetricCard({
  label,
  value,
  tone = "primary"
}: MetricCardProps) {
  return (
    <div className={`metric-card metric-card-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
