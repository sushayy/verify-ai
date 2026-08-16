import { Link } from "react-router-dom";

function Navbar() {
  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
        <Link to="/" className="text-xl font-bold text-gray-900">
          Verify AI
        </Link>

        <div className="flex gap-5">
          <Link to="/submit" className="text-gray-600 hover:text-gray-900">
            Submit Claim
          </Link>

          <Link to="/dashboard" className="text-gray-600 hover:text-gray-900">
            Dashboard
          </Link>

          <Link to="/history" className="text-gray-600 hover:text-gray-900">
            History
          </Link>

          <Link to="/login" className="text-gray-600 hover:text-gray-900">
            Login
          </Link>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
