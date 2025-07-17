import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import toast from "react-hot-toast";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import ButtonLoading from "../components/ButtonLoading";

function LoginPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    setError("");

    const loginData = new URLSearchParams();
    loginData.append("username", formData.username);
    loginData.append("password", formData.password);

    try {
      const response = await axios.post("http://127.0.0.1:8000/api/v1/auth/login", loginData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      localStorage.setItem("access_token", response.data.access_token);
      localStorage.setItem("refresh_token", response.data.refresh_token);

      toast.success(`Welcome ${formData.username}!`);
      setTimeout(() => {
        setLoading(false);
        navigate("/chat");
      }, 1500);
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
      toast.error("Login failed. Check credentials.");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-100 to-sky-300 flex items-center justify-center px-4">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md animate-fade-in-down">
        <h2 className="text-3xl font-bold text-center text-blue-800 mb-6 animate-slide-in">
          Welcome Back
        </h2>

        <form onSubmit={handleSubmit} className="space-y-5">
          <input
            type="text"
            name="username"
            placeholder="Username"
            value={formData.username}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200"
            required
          />

          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              name="password"
              placeholder="Password"
              value={formData.password}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10 transition-all duration-200"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute right-3 top-2.5 text-gray-600 hover:text-blue-600 transition-all duration-150"
              aria-label="Toggle password visibility"
            >
              {showPassword ? (
                <EyeSlashIcon className="w-5 h-5" />
              ) : (
                <EyeIcon className="w-5 h-5" />
              )}
            </button>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          {loading ? (
            <ButtonLoading />
          ) : (<button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-md transition duration-200"
          >
            Login
          </button>)}

          <p className="text-center text-sm text-gray-600">
            Don’t have an account?{" "}
            <span
              onClick={() => navigate("/signup")}
              className="text-blue-600 cursor-pointer hover:underline"
            >
              Sign Up
            </span>
          </p>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
