function VerdictBadge({ verdict }) {
  const normalized = (verdict || "UNVERIFIED").toUpperCase();

  const styles = {
    TRUE: "bg-green-100 text-green-800 border-green-200",
    FALSE: "bg-red-100 text-red-800 border-red-200",
    MISLEADING: "bg-yellow-100 text-yellow-800 border-yellow-200",
    UNVERIFIED: "bg-gray-100 text-gray-700 border-gray-200",
  };

  return (
    <span
      className={`inline-block px-5 py-2 rounded-full border text-lg font-bold ${
        styles[normalized] || styles.UNVERIFIED
      }`}
    >
      {normalized}
    </span>
  );
}

export default VerdictBadge;