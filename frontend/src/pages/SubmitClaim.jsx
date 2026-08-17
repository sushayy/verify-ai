import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitClaim } from "../api/claims";

function SubmitClaim() {
  const navigate = useNavigate();

  const [claimText, setClaimText] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");

    const cleanedClaim = claimText.trim();

    if (!cleanedClaim) {
      setError("Please enter a claim before submitting.");
      return;
    }

    try {
      setSubmitting(true);

      const claim = await submitClaim(cleanedClaim);

      navigate(`/dashboard/${claim.claim_id}`);
    } catch (err) {
      console.error("Claim submission failed:", err);

      if (err.response?.status === 400) {
        setError("Please enter a valid claim and try again.");
      } else if (err.response?.status === 401) {
        setError("Your session has expired. Please log in again.");
      } else {
        setError(
          "Unable to submit the claim. Please try again."
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="max-w-3xl mx-auto px-6 py-16">
      <div className="mb-8">
        <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          New Verification
        </p>

        <h1 className="mt-2 text-4xl font-bold text-gray-900">
          Verify a Claim
        </h1>

        <p className="mt-3 text-gray-600 leading-7">
          Enter a factual statement below and submit it to the
          Verify AI verification system.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded-xl p-6"
      >
        <label
          htmlFor="claimText"
          className="block text-sm font-semibold text-gray-700 mb-2"
        >
          Claim
        </label>

        <textarea
          id="claimText"
          rows="8"
          value={claimText}
          onChange={(event) => setClaimText(event.target.value)}
          disabled={submitting}
          placeholder="Example: Canberra is the capital city of Australia."
          className="w-full border border-gray-300 rounded-lg px-4 py-3 text-gray-900 resize-y focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
        />

        <div className="mt-2 flex justify-between text-sm text-gray-500">
          <span>Text claims only</span>
          <span>{claimText.length} characters</span>
        </div>

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        <div className="mt-6 flex justify-end">
          <button
            type="submit"
            disabled={submitting}
            className="bg-gray-900 text-white px-6 py-3 rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Submitting..." : "Verify Claim"}
          </button>
        </div>
      </form>
    </main>
  );
}

export default SubmitClaim;   