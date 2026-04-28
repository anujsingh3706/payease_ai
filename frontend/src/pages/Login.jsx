// frontend/src/pages/Login.jsx
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff, LogIn } from "lucide-react";
import toast from "react-hot-toast";
import { authAPI } from "../services/api";
import useAuthStore from "../store/authStore";

export default function Login() {
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm();
  const { login } = useAuthStore();
  const navigate  = useNavigate();

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      const res = await authAPI.login(data);
      login(res.data);
      toast.success(`Welcome back, ${res.data.full_name}! 👋`);
      navigate("/");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f0f1a] flex items-center justify-center p-4">
      <div className="w-full max-w-md fade-in">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-primary flex items-center justify-center font-black text-white text-3xl mx-auto mb-4 glow">
            P
          </div>
          <h1 className="text-3xl font-black text-white">PayEase AI</h1>
          <p className="text-muted mt-1">Smart Digital Banking</p>
        </div>

        {/* Card */}
        <div className="card">
          <h2 className="text-xl font-bold text-white mb-6">Sign In</h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Email Address</label>
              <input
                className="input"
                type="email"
                placeholder="rahul@example.com"
                {...register("email", { required: "Email is required" })}
              />
              {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>}
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input
                  className="input pr-11"
                  type={showPwd ? "text" : "password"}
                  placeholder="Your password"
                  {...register("password", { required: "Password is required" })}
                />
                <button type="button" onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-white">
                  {showPwd ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {errors.password && <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>}
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
              {loading ? (
                <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <><LogIn size={18} /> Sign In</>
              )}
            </button>
          </form>

          <p className="text-center text-muted text-sm mt-5">
            Don't have an account?{" "}
            <Link to="/register" className="text-primary hover:underline font-medium">
              Create Account
            </Link>
          </p>
        </div>

        {/* Demo credentials */}
        <div className="mt-4 card border-yellow-500/20 bg-yellow-500/5">
          <p className="text-yellow-400 text-xs font-semibold mb-1">🧪 Test Account</p>
          <p className="text-muted text-xs">Register first, then login with your credentials</p>
        </div>
      </div>
    </div>
  );
}