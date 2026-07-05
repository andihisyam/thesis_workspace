type WaitingStateProps = {
  title: string;
  detail: string;
};

export default function WaitingState({ title, detail }: WaitingStateProps) {
  return (
    <div className="waiting-state" role="status" aria-live="polite">
      <span className="waiting-spinner" aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
    </div>
  );
}
