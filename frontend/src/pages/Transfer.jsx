// frontend/src/pages/Transfer.jsx
import { useState } from "react";
import { useForm } from "react-hook-form";
import { ArrowLeftRight, ShieldCheck, AlertTriangle } from "lucide-react";
import toast from "react-hot-toast";
import { txnAPI, aiAPI } from "../services/api";

const MODES = [
  { value: "imps", label: "IMPS", sub: "Instant · Free · Max ₹5L" },
  { value: "neft", label: "NEFT", sub: "30 min · ₹2-₹25 · Max ₹5L" },
  { value: "rtgs", label: "RTGS", sub: "Instant · Min ₹2L" },
];

export default function Transfer() {
  const [loading,      setLoading]      = useState(false);
  const [fraudResult,  setFraudResult]  = useState(null);
  const [step,         setStep]         = useState(1); // 1=form, 2=fraud-check, 3=success
  const [txnResult,    setTxnResult]    = useState(null);
  const [mode,         setMode]         = useState("imps");

  const { register, handleSubmit, getValues, formState: { errors } } = useForm();

  const handleFraudCheck = async (data) => {
    setLoading(true);
    try {
      const res = await aiAPI.checkFraud({
        amount:            parseFloat(data.amount),
        transfer_mode:     mode,
        to_account_number: data.to_account_number,
      });
      setFraudResult(res.data);
      setStep(2);
    } catch {
      toast.error("Fraud check failed. Proceed carefully.");
      setStep(2);
    } finally {
      setLoading(false);
    }
  };

  const handleTransfer = async () => {
    if (fraudResult?.action === "BLOCK") {
      toast.error("Transaction blocked by fraud system");
      return;
    }
    setLoading(true);
    const data = getValues();
    try {
      const res = await txnAPI.fundTransfer({
        to_account_number: data.to_account_number,
        amount:            parseFloat(data.amount),
        mpin:              data.mpin,
        description:       data.description,
        transfer_mode:     mode,
      });
      setTxnResult(res.data);
      setStep(3);
      toast.success("Transfer successful! 🎉");
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Transfer failed");
    } finally {
      setLoading(false);
    }
  };

  const riskColor = {
    LOW: "green", MEDIUM: "yellow", HIGH: "yellow", CRITICAL: "red"
  };

  return (
    <div className="max-w-xl space-y-6 fade-in">
      <div>
        <h1 className="text-2xl font-black text-white">Fund Transfer</h1>
        <p className="text-muted mt-1">NEFT · RTGS · IMPS with AI fraud protection</p>
      </div>

      {/* Step 1 — Form */}
      {step === 1 && (
        <div className="card space-y-5">
          {/* Transfer Mode */}
          <div>
            <label className="label">Transfer Mode</label>
            <div className="grid grid-cols-3 gap-2">
              {MODES.map(m => (
                <button key={m.value} type="button"
                  onClick={() => setMode(m.value)}
                  className={`p-3 rounded-xl border text-left transition-all
                    ${mode === m.value
                      ? "border-primary bg-primary/20 text-white"
                      : "border-border text-muted hover:border-primary/50"}`}>
                  <p className="font-bold text-sm">{m.label}</p>
                  <p className="text-xs mt-0.5 opacity-70">{m.sub}</p>
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit(handleFraudCheck)} className="space-y-4">
            <div>
              <label className="label">Destination Account Number</label>
              <input className="input" placeholder="16-digit account number"
                {...register("to_account_number", { required: true, minLength: 14, pattern: /^\d+$/ })} />
              {errors.to_account_number && <p className="text-red-400 text-xs mt-1">Valid account number required</p>}
            </div>

            <div>
              <label className="label">Amount (₹)</label>
              <input className="input" type="number" step="0.01" placeholder="1000"
                {...register("amount", { required: true, min: 1, max: 1000000 })} />
              {errors.amount && <p className="text-red-400 text-xs mt-1">Valid amount required</p>}
            </div>

            <div>
              <label className="label">Transaction MPIN</label>
              <input className="input" type="password" maxLength={6} placeholder="6-digit MPIN"
                {...register("mpin", { required: true, minLength: 6, maxLength: 6, pattern: /^\d+$/ })} />
            </div>

            <div>
              <label className="label">Description (Optional)</label>
              <input className="input" placeholder="Rent, salary, etc."
                {...register("description")} />
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              {loading
                ? <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                : <><ShieldCheck size={18}/> Check & Proceed</>
              }
            </button>
          </form>
        </div>
      )}

      {/* Step 2 — Fraud Result */}
      {step === 2 && fraudResult && (
        <div className="space-y-4">
          <div className={`card border-${riskColor[fraudResult.risk_level]}-500/30 bg-${riskColor[fraudResult.risk_level]}-500/5`}>
            <div className="flex items-center gap-3 mb-4">
              {fraudResult.action === "BLOCK"
                ? <AlertTriangle size={24} className="text-red-400" />
                : <ShieldCheck   size={24} className="text-green-400" />
              }
              <div>
                <p className="font-bold text-white">AI Fraud Analysis</p>
                <p className="text-muted text-sm">Risk Level: <span className={`font-bold text-${riskColor[fraudResult.risk_level]}-400`}>{fraudResult.risk_level}</span></p>
              </div>
              <div className="ml-auto text-right">
                <p className="text-2xl font-black text-white">{(fraudResult.fraud_score * 100).toFixed(0)}%</p>
                <p className="text-xs text-muted">Fraud Score</p>
              </div>
            </div>

            {/* Score bar */}
            <div className="w-full bg-gray-700 rounded-full h-2 mb-3">
              <div className={`h-2 rounded-full bg-gradient-to-r ${fraudResult.fraud_score < 0.3 ? "from-green-500 to-green-400" : fraudResult.fraud_score < 0.6 ? "from-yellow-500 to-yellow-400" : "from-red-500 to-red-400"}`}
                   style={{ width: `${fraudResult.fraud_score * 100}%` }} />
            </div>

            <p className="text-sm text-gray-300">{fraudResult.message}</p>

            {fraudResult.reasons?.length > 0 && (
              <ul className="mt-3 space-y-1">
                {fraudResult.reasons.map((r, i) => (
                  <li key={i} className="text-sm text-yellow-400 flex items-center gap-2">
                    <span>⚠️</span> {r}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* MPIN for final confirm */}
          <div className="card space-y-4">
            <p className="font-semibold text-white">Confirm Transfer</p>
            <div className="bg-surface rounded-xl p-4 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted">To Account</span><span className="text-white font-medium">{getValues("to_account_number")}</span></div>
              <div className="flex justify-between"><span className="text-muted">Amount</span><span className="text-white font-bold">₹{Number(getValues("amount")).toLocaleString("en-IN")}</span></div>
              <div className="flex justify-between"><span className="text-muted">Mode</span><span className="text-white">{mode.toUpperCase()}</span></div>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className="btn-outline flex-1">Go Back</button>
              <button
                onClick={handleTransfer}
                disabled={loading || fraudResult?.action === "BLOCK"}
                className={`flex-1 flex items-center justify-center gap-2 font-semibold px-5 py-2.5 rounded-xl transition-all
                  ${fraudResult?.action === "BLOCK"
                    ? "bg-red-900/40 text-red-400 cursor-not-allowed"
                    : "btn-primary"}`}>
                {loading
                  ? <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  : fraudResult?.action === "BLOCK" ? "🚫 Blocked" : "✅ Transfer Now"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 3 — Success */}
      {step === 3 && txnResult && (
        <div className="card text-center space-y-4 border-green-500/30 bg-green-500/5">
          <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto">
            <ShieldCheck size={32} className="text-green-400" />
          </div>
          <h2 className="text-xl font-black text-white">Transfer Successful!</h2>
          <div className="bg-surface rounded-xl p-4 space-y-2 text-sm text-left">
            <div className="flex justify-between"><span className="text-muted">Ref Number</span><span className="text-white font-mono">{txnResult.transaction_ref}</span></div>
            <div className="flex justify-between"><span className="text-muted">Amount Sent</span><span className="text-white font-bold">₹{Number(txnResult.amount).toLocaleString("en-IN")}</span></div>
            <div className="flex justify-between"><span className="text-muted">Charges</span><span className="text-muted">₹{txnResult.charges}</span></div>
            <div className="flex justify-between"><span className="text-muted">New Balance</span><span className="text-green-400 font-bold">₹{Number(txnResult.new_balance).toLocaleString("en-IN")}</span></div>
          </div>
          <button onClick={() => { setStep(1); setFraudResult(null); setTxnResult(null); }} className="btn-primary w-full">
            Make Another Transfer
          </button>
        </div>
      )}
    </div>
  );
}