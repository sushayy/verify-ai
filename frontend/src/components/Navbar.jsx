import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
        <Link to="/" className="text-xl font-bold text-gray-900">
          Verify AI
        </Link>

        <div className="flex items-center gap-5">
          {user ? (
            <>
              <Link
                to="/submit"
                className="text-gray-600 hover:text-gray-900"
              >
                Submit Claim
              </Link>

              <Link
                to="/dashboard"
                className="text-gray-600 hover:text-gray-900"
              >
                Dashboard
              </Link>

              <Link
                to="/history"
                className="text-gray-600 hover:text-gray-900"
              >
                History
              </Link>

              <span className="text-gray-500 text-sm">
                {user.name}
              </span>

              <button
                type="button"
                onClick={handleLogout}
                className="bg-gray-900 text-white px-4 py-2 rounded-lg"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="text-gray-600 hover:text-gray-900"
              >
                Login
              </Link>

              <Link
                to="/signup"
                className="bg-gray-900 text-white px-4 py-2 rounded-lg"
              >
                Sign Up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
