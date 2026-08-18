import { Link } from "react-router-dom";

function Home() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-20">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Evidence-Based Claim Verification
        </p>

        <h1 className="mt-4 text-5xl font-bold text-gray-900">
          Verify information with evidence
        </h1>

        <p className="mt-6 text-lg text-gray-600 leading-8">
          Verify AI helps users submit factual claims and review
          evidence-based verification results, confidence scores,
          explanations and supporting sources.
        </p>

        <div className="mt-8 flex gap-4">
          <Link
            to="/signup"
            className="bg-gray-900 text-white px-5 py-3 rounded-lg font-medium"
          >
            Get Started
          </Link>

          <Link
            to="/login"
            className="bg-white border border-gray-300 px-5 py-3 rounded-lg font-medium"
          >
            Login
          </Link>
        </div>
      </div>
    </main>
  );
}

export default Home;
