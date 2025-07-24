// HomePage.jsx
import { useNavigate } from "react-router-dom";
// import { getAuthToken } from "../utils/auth";

function HomePage() {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    const token = getAuthToken();
    if (!token) {
      navigate("/login");
    } else {
      navigate("/chat");
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-gradient-to-br from-slate-100 to-indigo-300 px-4">
      <div className="max-w-xl text-center space-y-6">
        <h1 className="text-5xl font-extrabold text-indigo-600">Welcome to DocQuery</h1>
        <p className="text-lg text-slate-600">
          Upload documents and get instant answers powered by AI.
        </p>
        <div className="flex gap-4 justify-center">
          <button
            onClick={() => navigate("/login")}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-5 rounded-xl shadow-md transition"
          >
            Login
          </button>
          <button
            onClick={() => navigate("/signup")}
            className="bg-white hover:bg-slate-100 text-indigo-700 border border-indigo-300 font-medium py-2 px-5 rounded-xl shadow-md transition"
          >
            Sign Up
          </button>
        </div>
        <button
          onClick={handleGetStarted}
          className="mt-6 bg-violet-500 hover:bg-violet-600 text-white font-medium py-2 px-6 rounded-xl shadow-lg transition"
        >
          Get Started
        </button>
      </div>
    </div>

  );
}

export default HomePage;
