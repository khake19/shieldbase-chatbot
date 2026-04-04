interface QuoteCardProps {
  content: string;
}

export function QuoteCard({ content }: QuoteCardProps) {
  // Parse title line and details from between [QUOTE] tags
  const lines = content.split("\n").filter((l) => l.trim());
  const titleLine = lines.find((l) => l.includes("Insurance Quote"));
  const detailLines = lines.filter(
    (l) =>
      l.startsWith("- **") &&
      !l.includes("Monthly Premium") &&
      !l.includes("Annual Premium")
  );
  const monthlyLine = lines.find((l) => l.includes("Monthly Premium"));
  const annualLine = lines.find((l) => l.includes("Annual Premium"));

  const parseDetail = (line: string) => {
    const match = line.match(/\*\*(.+?)\*\*:\s*(.+)/);
    if (match) return { label: match[1], value: match[2] };
    return null;
  };

  const monthly = monthlyLine?.match(/\$[\d,.]+/)?.[0] || "";
  const annual = annualLine?.match(/\$[\d,.]+/)?.[0] || "";

  return (
    <div className="quote-card">
      <div className="quote-card-header">
        <svg
          width="24"
          height="24"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M32 4L8 16v16c0 14.4 10.24 27.84 24 32 13.76-4.16 24-17.6 24-32V16L32 4z"
            fill="#2563eb"
          />
          <path
            d="M28 30l-4-4-2 2 6 6 12-12-2-2-10 10z"
            fill="white"
          />
        </svg>
        <h3>{titleLine?.replace(/\*\*/g, "").trim() || "Insurance Quote"}</h3>
      </div>

      <div className="quote-card-details">
        {detailLines.map((line, i) => {
          const detail = parseDetail(line);
          if (!detail) return null;
          return (
            <div key={i} className="quote-detail-row">
              <span className="quote-detail-label">{detail.label}</span>
              <span className="quote-detail-value">{detail.value}</span>
            </div>
          );
        })}
      </div>

      <div className="quote-card-pricing">
        {monthly && (
          <div className="quote-price-main">
            <span className="quote-price-amount">{monthly}</span>
            <span className="quote-price-period">/month</span>
          </div>
        )}
        {annual && (
          <div className="quote-price-annual">{annual}/year</div>
        )}
      </div>
    </div>
  );
}
