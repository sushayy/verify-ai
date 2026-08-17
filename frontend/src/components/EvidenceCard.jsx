function EvidenceCard({ evidence }) {
  const stanceStyles = {
    supporting: "bg-green-100 text-green-700",
    contradicting: "bg-red-100 text-red-700",
    neutral: "bg-gray-100 text-gray-700",
  };

  const stance = evidence.stance || "neutral";

  const reliability =
    evidence.reliability_score !== undefined &&
    evidence.reliability_score !== null
      ? Math.round(Number(evidence.reliability_score) * 100)
      : null;

  return (
    <div className="border border-gray-200 rounded-xl p-5 bg-white">
      <div className="flex flex-col sm:flex-row sm:justify-between gap-4">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900">
            {evidence.source_name || "Evidence Source"}
          </h3>

          <p className="mt-2 text-gray-600 leading-6">
            {evidence.extracted_text || "No evidence text available."}
          </p>

          {reliability !== null && (
            <p className="mt-2 text-sm text-gray-500">
              Reliability: {reliability}%
            </p>
          )}

          {evidence.url && (
            <a
              href={evidence.url}
              target="_blank"
              rel="noreferrer"
              className="inline-block mt-3 text-sm font-semibold text-blue-600 hover:underline"
            >
              View source
            </a>
          )}
        </div>

        <div>
          <span
            className={`inline-block px-3 py-1 rounded-full text-sm font-semibold capitalize ${
              stanceStyles[stance] || stanceStyles.neutral
            }`}
          >
            {stance}
          </span>
        </div>
      </div>
    </div>
  );
}

export default EvidenceCard;