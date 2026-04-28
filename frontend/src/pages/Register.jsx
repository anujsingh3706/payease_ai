// frontend/src/pages/Register.jsx
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { UserPlus } from "lucide-react";
import toast from "react-hot-toast";
import { authAPI } from "../services/api";

export default function Register() {
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm();
  const navigate = useNavigate();

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      const res = await authAPI.register(data);
      toast.success("Account created! 🎉 Your account number: " + res.data.account_number);
      navigate("/login");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f0f1a] flex items-center justify-center p-4">
      <div className="w-full max-w-md fade-in">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-primary flex items-center justify-center font-black text-white text-3xl mx-auto mb-4 glow">P</div>
          <h1 className="text-3xl font-black text-white">Create Account</h1>
          <p className="text-muted mt-1">Join PayEase AI Banking</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {[
              { name: "full_name",     label: "Full Name",      type: "text",     placeholder: "Rahul Sharma",        rules: { required: true, minLength: 3 } },
              { name: "email",         label: "Email",          type: "email",    placeholder: "rahul@example.com",   rules: { required: true } },
              { name: "phone_number",  label: "Mobile Number",  type: "tel",      placeholder: "9876543210",          rules: { required: true, pattern: /^[6-9]\d{9}$/ } },
              { name: "password",      label: "Password",       type: "password", placeholder: "Min 8 chars, 1 uppercase, 1 number, 1 special", rules: { required: true, minLength: 8 } },
              { name: "city",          label: "City",           type: "text",     placeholder: "Mumbai",              rules: {} },
              { name: "state",         label: "State",          type: "text",     placeholder: "Maharashtra",         rules: {} },
            ].map(({ name, label, type, placeholder, rules }) => (
              <div key={name}>
                <label className="label">{label}</label>
                <input
                  className="input"
                  type={type}
                  placeholder={placeholder}
                  {...register(name, rules)}
                />
                {errors[name] && (
                  <p className="text-red-400 text-xs mt-1">
                    {name === "phone_number" ? "Enter valid 10-digit Indian mobile number" : `${label} is required`}
                  </p>
                )}
              </div>
            ))}

            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
              {loading
                ? <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                : <><UserPlus size={18} /> Create Account</>
              }
            </button>
          </form>

          <p className="text-center text-muted text-sm mt-5">
            Already have an account?{" "}
            <Link to="/login" className="text-primary hover:underline font-medium">Sign In</Link>
          </p>
        </div>
      </div>
    </div>
  );
}