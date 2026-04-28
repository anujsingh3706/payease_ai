// frontend/src/App.jsx  ← FINAL CLEAN VERSION
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import useAuthStore  from "./store/authStore";
import Layout        from "./components/Layout";
import Login         from "./pages/Login";
import Register      from "./pages/Register";
import Dashboard     from "./pages/Dashboard";
import Transfer      from "./pages/Transfer";
import Wallet        from "./pages/Wallet";
import AIChatbot     from "./pages/ai/AIChatbot";
import CreditScore   from "./pages/ai/CreditScore";
import LoanPredictor from "./pages/ai/LoanPredictor";
import SpendAnalyser from "./pages/ai/SpendAnalyser";

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1 } } });

function Protected({ children }) {
  const { isLoggedIn } = useAuthStore();
  return isLoggedIn ? children : <Navigate to="/login" replace />;
}

function FraudPage() {
  return (
    <div className="card max-w-md text-center py-12 space-y-3">
      <div className="text-5xl">🛡️</div>
      <h2 className="text-xl font-black text-white">Fraud Detection</h2>
      <p className="text-muted text-sm">
        Real-time fraud check is built into the <strong className="text-white">Fund Transfer</strong> page.
        Every transaction is automatically scored before processing.
      </p>
      <a href="/transfer" className="btn-primary inline-block mt-3">Go to Transfer →</a>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/*" element={
            <Protected>
              <Layout>
                <Routes>
                  <Route path="/"           element={<Dashboard />}    />
                  <Route path="/transfer"   element={<Transfer />}     />
                  <Route path="/wallet"     element={<Wallet />}       />
                  <Route path="/ai/chat"    element={<AIChatbot />}    />
                  <Route path="/ai/fraud"   element={<FraudPage />}    />
                  <Route path="/ai/credit"  element={<CreditScore />}  />
                  <Route path="/ai/loan"    element={<LoanPredictor />}/>
                  <Route path="/ai/spend"   element={<SpendAnalyser />}/>
                  <Route path="*"           element={<Navigate to="/" />} />
                </Routes>
              </Layout>
            </Protected>
          } />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}