function ConfidenceBar({ score }) {
  const numericScore = Number(score) || 0;

  const percentage = Math.max(
    0,
    Math.min(100, Math.round(numericScore * 100))
  );

  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <span className="text-sm font-semibold text-gray-600">
          Confidence
        </span>

        <span className="text-3xl font-bold text-gray-900">
          {percentage}%
        </span>
      </div>

      <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-gray-900 rounded-full transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export default ConfidenceBar;