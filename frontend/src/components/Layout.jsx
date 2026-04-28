// frontend/src/components/Layout.jsx
import Sidebar from "./Sidebar";
import { Toaster } from "react-hot-toast";

export default function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-[#0f0f1a]">
      <Sidebar />
      <main className="ml-64 flex-1 p-6 max-w-6xl">
        {children}
      </main>
      <Toaster
        position="top-right"
        toastOptions={{
          style: { background: "#2a2a3e", color: "#e2e8f0", border: "1px solid #3f3f5c" },
          success: { iconTheme: { primary: "#22c55e", secondary: "#2a2a3e" } },
          error:   { iconTheme: { primary: "#ef4444", secondary: "#2a2a3e" } },
        }}
      />
    </div>
  );
}