import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitClaim, uploadUrlClaim, uploadPdfClaim } from "../api/claims";

const TABS = [
  { id: "text", label: "Text" },
  { id: "url", label: "URL" },
  { id: "pdf", label: "Upload PDF" },
];

function SubmitClaim() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("text");
  const [claimText, setClaimText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleTabChange(tabId) {
    setMode(tabId);
    setError("");
  }

  function handleFileChange(event) {
    const selected = event.target.files?.[0];
    if (selected && selected.type !== "application/pdf") {
      setError("Only PDF files are allowed.");
      setFile(null);
      return;
    }
    setError("");
    setFile(selected || null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    try {
      setSubmitting(true);
      let claim;

      if (mode === "text") {
        const cleaned = claimText.trim();
        if (!cleaned) {
          setError("Please enter a claim before submitting.");
          setSubmitting(false);
          return;
        }
        claim = await submitClaim(cleaned);
      } else if (mode === "url") {
        const cleaned = url.trim();
        if (!cleaned) {
          setError("Please enter a URL before submitting.");
          setSubmitting(false);
          return;
        }
        claim = await uploadUrlClaim(cleaned);
      } else {
        if (!file) {
          setError("Please choose a PDF file before submitting.");
          setSubmitting(false);
          return;
        }
        claim = await uploadPdfClaim(file);
      }

      navigate(`/dashboard/${claim.claim_id}`);
    } catch (err) {
      console.error("Claim submission failed:", err);
      if (err.response?.status === 400) {
        setError(err.response.data?.error || "Please check your input and try again.");
      } else if (err.response?.status === 401) {
        setError("Your session has expired. Please log in again.");
      } else if (err.response?.status === 429) {
        setError("Too many submissions. Please wait a minute and try again.");
      } else {
        setError("Unable to submit the claim. Please try again.");
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
          Enter a claim, paste a link, or upload a PDF to verify it against
          the Verify AI system.
        </p>
      </div>

      <div className="flex gap-2 mb-4">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => handleTabChange(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border ${
              mode === tab.id
                ? "bg-gray-900 text-white border-gray-900"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded-xl p-6"
      >
        {mode === "text" && (
          <>
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
              <span>Text claim</span>
              <span>{claimText.length} characters</span>
            </div>
          </>
        )}

        {mode === "url" && (
          <>
            <label
              htmlFor="claimUrl"
              className="block text-sm font-semibold text-gray-700 mb-2"
            >
              Article or page URL
            </label>
            <input
              id="claimUrl"
              type="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              disabled={submitting}
              placeholder="https://example.com/article"
              className="w-full border border-gray-300 rounded-lg px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
            />
            <p className="mt-2 text-sm text-gray-500">
              The page's main text content will be extracted and verified.
            </p>
          </>
        )}

        {mode === "pdf" && (
          <>
            <label
              htmlFor="claimFile"
              className="block text-sm font-semibold text-gray-700 mb-2"
            >
              PDF file
            </label>
            <input
              id="claimFile"
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              disabled={submitting}
              className="w-full border border-gray-300 rounded-lg px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
            />
            <p className="mt-2 text-sm text-gray-500">
              {file ? file.name : "Max file size 10MB. PDF only."}
            </p>
          </>
        )}

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
