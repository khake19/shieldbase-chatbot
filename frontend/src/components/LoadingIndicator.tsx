interface LoadingIndicatorProps {
  stage?: string | null;
}

export function LoadingIndicator({ stage }: LoadingIndicatorProps) {
  return (
    <div className="loading-indicator">
      <div className="loading-content">
        <div className="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
        {stage && <div className="processing-stage">{stage}</div>}
      </div>
    </div>
  );
}
