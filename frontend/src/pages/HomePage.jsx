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
    <div className="min-h-screen flex flex-col justify-center items-center bg-gradient-to-br from-blue-100 to-indigo-200 text-gray-800 px-4">
      <div className="max-w-xl text-center space-y-6">
        <h1 className="text-4xl font-bold">Welcome to DocQuery</h1>
        <p className="text-lg">
          Upload your documents and ask anything related to them. Let the AI assist you!
        </p>
        <div className="flex gap-4 justify-center">
          <button
            onClick={() => navigate("/login")}
            className="bg-blue-600 hover:bg-blue-700 text-white cursor-pointer font-semibold py-2 px-4 rounded-lg shadow"
          >
            Login
          </button>
          <button
            onClick={() => navigate("/signup")}
            className="bg-gray-100 hover:bg-gray-200 text-blue-700 cursor-pointer font-semibold py-2 px-4 rounded-lg shadow"
          >
            Sign Up
          </button>
        </div>
        <button
          onClick={handleGetStarted}
          className="mt-6 bg-green-600 hover:bg-green-700 text-white cursor-pointer font-semibold py-2 px-6 rounded-lg shadow-lg"
        >
          Get Started
        </button>
      </div>
    </div>
  );
}

export default HomePage;
