// frontend/tailwind.config.js

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary:  { DEFAULT: "#6366f1", dark: "#4f46e5", light: "#a5b4fc" },
        success:  "#22c55e",
        danger:   "#ef4444",
        warning:  "#f59e0b",
        surface:  "#1e1e2e",
        card:     "#2a2a3e",
        border:   "#3f3f5c",
        muted:    "#6b7280",
      },
      fontFamily: { sans: ["Inter", "sans-serif"] },
      backgroundImage: {
        "gradient-primary": "linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%)",
        "gradient-dark":    "linear-gradient(135deg,#1e1e2e 0%,#2a2a3e 100%)",
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};