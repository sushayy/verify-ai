import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  getClaimById,
  getClaimStatus,
} from "../api/claims";

import StatusBadge from "../components/StatusBadge";
import VerdictBadge from "../components/VerdictBadge";
import ConfidenceBar from "../components/ConfidenceBar";
import EvidenceCard from "../components/EvidenceCard";

function Dashboard() {
  const { id } = useParams();

  const [data, setData] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(Boolean(id));
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) {
      setLoading(false);
      return;
    }

    let timer;
    let cancelled = false;

    async function checkStatus() {
      try {
        const statusData = await getClaimStatus(id);

        if (cancelled) return;

        const currentStatus =
          statusData.verification_status;

        setStatus(currentStatus);

        if (currentStatus === "completed") {
          const fullResult = await getClaimById(id);

          if (!cancelled) {
            setData(fullResult);
            setLoading(false);
          }

          return;
        }

        if (currentStatus === "failed") {
          setLoading(false);
          return;
        }

        timer = setTimeout(checkStatus, 2000);
      } catch (err) {
        console.error(err);

        if (!cancelled) {
          setError("Unable to load verification status.");
          setLoading(false);
        }
      }
    }

    checkStatus();

    return () => {
      cancelled = true;

      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [id]);

  if (!id) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-16">
        <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">
            Verification Dashboard
          </h1>

          <p className="mt-3 text-gray-600">
            Submit a new claim or choose a previous claim from
            History to view its verification result.
          </p>

          <div className="mt-6 flex justify-center gap-4">
            <Link
              to="/submit"
              className="bg-gray-900 text-white px-5 py-3 rounded-lg"
            >
              Submit Claim
            </Link>

            <Link
              to="/history"
              className="border border-gray-300 px-5 py-3 rounded-lg"
            >
              View History
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-16">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <h1 className="text-xl font-bold text-red-800">
            Unable to load verification
          </h1>

          <p className="mt-2 text-red-700">
            {error}
          </p>
        </div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-16">
        <div className="bg-white border border-gray-200 rounded-xl p-10 text-center">
          <div className="w-12 h-12 mx-auto rounded-full border-4 border-gray-200 border-t-gray-900 animate-spin" />

          <h1 className="mt-6 text-2xl font-bold">
            Verifying your claim
          </h1>

          <p className="mt-2 text-gray-600">
            The verification process is still running.
          </p>

          <div className="mt-4">
            <StatusBadge status={status || "pending"} />
          </div>
        </div>
      </main>
    );
  }

  if (status === "failed") {
    return (
      <main className="max-w-3xl mx-auto px-6 py-16">
        <div className="bg-red-50 border border-red-200 rounded-xl p-8">
          <h1 className="text-2xl font-bold text-red-800">
            Verification Failed
          </h1>

          <p className="mt-3 text-red-700">
            The system could not complete verification for this claim.
          </p>

          <Link
            to="/submit"
            className="inline-block mt-5 bg-gray-900 text-white px-5 py-3 rounded-lg"
          >
            Try Another Claim
          </Link>
        </div>
      </main>
    );
  }

  const claim = data?.claim;
  const report = data?.report;
  const evidence = data?.evidence || [];

  if (!report) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-16">
        <div className="bg-white border border-gray-200 rounded-xl p-8">
          <h1 className="text-2xl font-bold">
            Report not available
          </h1>

          <p className="mt-3 text-gray-600">
            The claim completed, but no verification report was returned.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-12">
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-wide text-gray-500">
          Verification Result
        </p>

        <h1 className="mt-2 text-4xl font-bold text-gray-900">
          Verification Dashboard
        </h1>
      </div>

      <section className="bg-white border border-gray-200 rounded-xl p-6">
        <p className="text-sm font-semibold text-gray-500 uppercase">
          Submitted Claim
        </p>

        <p className="mt-3 text-lg font-medium text-gray-900 leading-7">
          {claim?.claim_text}
        </p>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-5">
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <p className="text-sm font-semibold text-gray-500 mb-4">
            Verdict
          </p>

          <VerdictBadge verdict={report.final_result} />
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <ConfidenceBar score={report.confidence_score} />
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-xl p-6 mt-5">
        <h2 className="text-lg font-bold text-gray-900">
          Reasoning
        </h2>

        <p className="mt-3 text-gray-600 leading-7">
          {report.explanation}
        </p>
      </section>

      <section className="bg-white border border-gray-200 rounded-xl p-6 mt-5">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold text-gray-900">
            Evidence
          </h2>

          <span className="text-sm text-gray-500">
            {evidence.length} source
            {evidence.length === 1 ? "" : "s"}
          </span>
        </div>

        {evidence.length > 0 ? (
          <div className="mt-5 space-y-4">
            {evidence.map((item, index) => (
              <EvidenceCard
                key={item.evidence_id || index}
                evidence={item}
              />
            ))}
          </div>
        ) : (
          <p className="mt-4 text-gray-600">
            No evidence was returned for this claim.
          </p>
        )}
      </section>
    </main>
  );
}

export default Dashboard;