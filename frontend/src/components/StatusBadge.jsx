function StatusBadge({ status }) {
  const styles = {
    pending: "bg-gray-100 text-gray-700",
    processing: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };

  const normalized = status || "pending";

  return (
    <span
      className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
        styles[normalized] || styles.pending
      }`}
    >
      {normalized}
    </span>
  );
}

export default StatusBadge;