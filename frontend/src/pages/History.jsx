import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getClaims } from "../api/claims";
import StatusBadge from "../components/StatusBadge";

function History() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadClaims() {
      try {
        const result = await getClaims();
        setClaims(result);
      } catch (err) {
        console.error(err);

        setError(
          "Unable to load your verification history."
        );
      } finally {
        setLoading(false);
      }
    }

    loadClaims();
  }, []);

  if (loading) {
    return (
      <main className="max-w-5xl mx-auto px-6 py-16">
        <p className="text-gray-600">
          Loading verification history...
        </p>
      </main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-12">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-gray-500">
            Previous Claims
          </p>

          <h1 className="mt-2 text-4xl font-bold text-gray-900">
            Verification History
          </h1>
        </div>

        <Link
          to="/submit"
          className="bg-gray-900 text-white px-5 py-3 rounded-lg font-medium"
        >
          Submit New Claim
        </Link>
      </div>

      {error && (
        <div className="mt-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
          {error}
        </div>
      )}

      {!error && claims.length === 0 && (
        <div className="mt-8 bg-white border border-gray-200 rounded-xl p-8 text-center">
          <h2 className="text-xl font-bold">
            No claims yet
          </h2>

          <p className="mt-2 text-gray-600">
            Your submitted claims will appear here.
          </p>
        </div>
      )}

      <div className="mt-8 space-y-4">
        {claims.map((claim) => (
          <Link
            key={claim.claim_id}
            to={`/dashboard/${claim.claim_id}`}
            className="block bg-white border border-gray-200 rounded-xl p-5 hover:border-gray-400 transition"
          >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <p className="font-semibold text-gray-900">
                  {claim.claim_text.length > 120
                    ? `${claim.claim_text.slice(0, 120)}...`
                    : claim.claim_text}
                </p>

                <p className="mt-2 text-sm text-gray-500">
                  {claim.submission_date
                    ? new Date(
                        claim.submission_date
                      ).toLocaleString()
                    : "Unknown date"}
                </p>
              </div>

              <StatusBadge
                status={claim.verification_status}
              />
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}

export default History;