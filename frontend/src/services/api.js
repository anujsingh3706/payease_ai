// frontend/src/services/api.js
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

import axios from "axios";

// ── Axios Instance ────────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

// ── Request Interceptor — attach JWT token ────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor — handle 401 ────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.clear();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ═════════════════════════════════════════════════════════════════════════════
// AUTH
// ═════════════════════════════════════════════════════════════════════════════
export const authAPI = {
  register:       (data)  => api.post("/api/v1/auth/register", data),
  login:          (data)  => api.post("/api/v1/auth/login",    data),
  getProfile:     ()      => api.get("/api/v1/auth/profile"),
  updateProfile:  (data)  => api.put("/api/v1/auth/profile",  data),
  submitKYC:      (data)  => api.post("/api/v1/auth/kyc",     data),
  setMPIN:        (data)  => api.post("/api/v1/auth/mpin/set",data),
  verifyMPIN:     (data)  => api.post("/api/v1/auth/mpin/verify", data),
  changePassword: (data)  => api.post("/api/v1/auth/change-password", data),
};

// ═════════════════════════════════════════════════════════════════════════════
// ACCOUNTS
// ═════════════════════════════════════════════════════════════════════════════
export const accountAPI = {
  getAccounts:      ()      => api.get("/api/v1/accounts/"),
  getBalance:       ()      => api.get("/api/v1/accounts/balance"),
  getMiniStatement: (limit) => api.get(`/api/v1/accounts/statement?limit=${limit||10}`),
  getTransactions:  (params)=> api.get("/api/v1/accounts/transactions", { params }),
  getBeneficiaries: ()      => api.get("/api/v1/accounts/beneficiaries"),
  addBeneficiary:   (data)  => api.post("/api/v1/accounts/beneficiaries", data),
  deleteBeneficiary:(id)    => api.delete(`/api/v1/accounts/beneficiaries/${id}`),
};

// ═════════════════════════════════════════════════════════════════════════════
// TRANSACTIONS
// ═════════════════════════════════════════════════════════════════════════════
export const txnAPI = {
  fundTransfer:  (data) => api.post("/api/v1/transactions/transfer", data),
  getCharges:    ()     => api.get("/api/v1/transactions/charges"),
};

// ═════════════════════════════════════════════════════════════════════════════
// WALLET
// ═════════════════════════════════════════════════════════════════════════════
export const walletAPI = {
  getWallet:      () => api.get("/api/v1/wallet/"),
  upiTransfer:    (data) => api.post("/api/v1/wallet/transfer", data),
  getQRCode:      () => api.get("/api/v1/wallet/qr-code"),
};

// ═════════════════════════════════════════════════════════════════════════════
// PAYMENTS
// ═════════════════════════════════════════════════════════════════════════════
export const paymentAPI = {
  createOrder: (data) => api.post("/api/v1/payments/create-order", data),
  verifyPayment:(data)=> api.post("/api/v1/payments/verify", data),
};

// ═════════════════════════════════════════════════════════════════════════════
// DASHBOARD
// ═════════════════════════════════════════════════════════════════════════════
export const dashboardAPI = {
  getDashboard: () => api.get("/api/v1/dashboard/"),
};

// ═════════════════════════════════════════════════════════════════════════════
// AI ENDPOINTS
// ═════════════════════════════════════════════════════════════════════════════
export const aiAPI = {
  // Chatbot
  chat:           (data) => api.post("/api/v1/ai/chat/",        data),
  quickHelp:      ()     => api.get("/api/v1/ai/chat/quick-help"),

  // Fraud
  checkFraud:     (data) => api.post("/api/v1/ai/fraud/check",  data),
  getFlagged:     ()     => api.get("/api/v1/ai/fraud/my-flagged"),

  // Credit
  getCreditScore: ()     => api.get("/api/v1/ai/credit/score"),
  manualCredit:   (data) => api.post("/api/v1/ai/credit/score/manual", data),
  creditHistory:  ()     => api.get("/api/v1/ai/credit/score/history"),

  // Loan
  predictLoan:    (data) => api.post("/api/v1/ai/loan/predict", data),
  applyLoan:      (data) => api.post("/api/v1/ai/loan/apply",   data),
  getLoans:       ()     => api.get("/api/v1/ai/loan/applications"),
  emiCalc:        (p)    => api.get("/api/v1/ai/loan/emi-calculator", { params: p }),

  // Spend
  spendSummary:   ()     => api.get("/api/v1/ai/spend/summary"),
  compareSpend:   ()     => api.get("/api/v1/ai/spend/compare"),
  categoriseAll:  ()     => api.post("/api/v1/ai/spend/categorise-all"),
};

export default api;