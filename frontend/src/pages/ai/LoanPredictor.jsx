// frontend/src/pages/ai/LoanPredictor.jsx
import { useState } from "react";
import { useForm } from "react-hook-form";
import { FileText, CheckCircle, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import { aiAPI } from "../../services/api";

const LOAN_TYPES = ["personal","home","vehicle","education","business"];
const EMP_TYPES  = ["salaried","self-employed","business","other"];

export default function LoanPredictor() {
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [applying,setApplying]= useState(false);
  const { register, handleSubmit, getValues } = useForm({
    defaultValues: { loan_type: "personal", employment_type: "salaried", tenure_months: 48, cibil_score: 700 }
  });

  const onPredict = async (data) => {
    setLoading(true);
    try {
      const res = await aiAPI.predictLoan({
        ...data,
        loan_amount:    parseFloat(data.loan_amount),
        monthly_income: parseFloat(data.monthly_income),
        existing_emis:  parseFloat(data.existing_emis || 0),
        years_employed: parseFloat(data.years_employed || 2),
        tenure_months:  parseInt(data.tenure_months),
        cibil_score:    parseInt(data.cibil_score),
      });
      setResult(res.data);
    } catch { toast.error("Prediction failed"); }
    finally { setLoading(false); }
  };

  const onApply = async () => {
    setApplying(true);
    try {
      const data = getValues();
      await aiAPI.applyLoan({
        ...data,
        loan_amount:    parseFloat(data.loan_amount),
        monthly_income: parseFloat(data.monthly_income),
        existing_emis:  parseFloat(data.existing_emis || 0),
        years_employed: parseFloat(data.years_employed || 2),
        tenure_months:  parseInt(data.tenure_months),
        cibil_score:    parseInt(data.cibil_score),
      });
      toast.success("Loan application submitted! 📋");
    } catch { toast.error("Application failed"); }
    finally { setApplying(false); }
  };

  const fmt = n => `₹${Number(n||0).toLocaleString("en-IN")}`;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 fade-in">
      {/* Form */}
      <div>
        <h1 className="text-2xl font-black text-white mb-1">Loan Predictor</h1>
        <p className="text-muted text-sm mb-5">Random Forest AI · SHAP Explanations</p>
        <div className="card space-y-4">
          <form onSubmit={handleSubmit(onPredict)} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Loan Type</label>
                <select className="input" {...register("loan_type")}>
                  {LOAN_TYPES.map(t => <option key={t} value={t} className="bg-surface capitalize">{t.charAt(0).toUpperCase()+t.slice(1)}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Employment</label>
                <select className="input" {...register("employment_type")}>
                  {EMP_TYPES.map(t => <option key={t} value={t} className="bg-surface capitalize">{t.charAt(0).toUpperCase()+t.slice(1)}</option>)}
                </select>
              </div>
            </div>

            {[
              { name: "loan_amount",    label: "Loan Amount (₹)",      placeholder: "500000"  },
              { name: "monthly_income", label: "Monthly Income (₹)",   placeholder: "75000"   },
              { name: "existing_emis",  label: "Existing EMIs/month (₹)", placeholder: "5000" },
              { name: "years_employed", label: "Years Employed",        placeholder: "3"      },
              { name: "tenure_months",  label: "Tenure (months)",       placeholder: "48"     },
              { name: "cibil_score",    label: "CIBIL Score",           placeholder: "700"    },
            ].map(f => (
              <div key={f.name}>
                <label className="label">{f.label}</label>
                <input className="input" type="number" placeholder={f.placeholder} {...register(f.name, { required: true })} />
              </div>
            ))}

            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              {loading ? <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><FileText size={16}/> Predict Eligibility</>}
            </button>
          </form>
        </div>
      </div>

      {/* Result */}
      <div>
        {result ? (
          <div className="space-y-4 fade-in">
            {/* Verdict */}
            <div className={`card text-center border-${result.is_eligible ? "green" : "red"}-500/30 bg-${result.is_eligible ? "green" : "red"}-500/5`}>
              {result.is_eligible
                ? <CheckCircle size={48} className="text-green-400 mx-auto mb-3" />
                : <XCircle    size={48} className="text-red-400 mx-auto mb-3"   />
              }
              <h2 className={`text-2xl font-black ${result.is_eligible ? "text-green-400" : "text-red-400"}`}>
                {result.prediction}
              </h2>
              <p className="text-muted text-sm mt-1">Confidence: <span className="text-white font-bold">{result.confidence}%</span></p>
              <p className="text-gray-400 text-sm mt-2">{result.recommendation}</p>
            </div>

            {/* EMI Breakdown */}
            <div className="card">
              <p className="font-bold text-white mb-3">Loan Details</p>
              {[
                { label: "EMI Amount",     value: fmt(result.emi_amount),     color: "text-primary" },
                { label: "Interest Rate",  value: `${result.interest_rate}% p.a.`, color: "text-white" },
                { label: "Total Payment",  value: fmt(result.total_payment),  color: "text-white" },
                { label: "Total Interest", value: fmt(result.total_interest), color: "text-red-400" },
                { label: "EMI/Income",     value: `${result.emi_to_income_ratio}%`, color: result.emi_to_income_ratio > 50 ? "text-red-400" : "text-green-400" },
              ].map(row => (
                <div key={row.label} className="flex justify-between py-2 border-b border-border last:border-0">
                  <span className="text-muted text-sm">{row.label}</span>
                  <span className={`font-bold text-sm ${row.color}`}>{row.value}</span>
                </div>
              ))}
            </div>

            {/* Rejection Reasons */}
            {result.rejection_reasons?.length > 0 && (
              <div className="card border-red-500/20">
                <p className="font-bold text-red-400 mb-2 text-sm">⚠️ Rejection Reasons</p>
                <ul className="space-y-1">
                  {result.rejection_reasons.map((r,i) => <li key={i} className="text-gray-400 text-sm">• {r}</li>)}
                </ul>
              </div>
            )}

            {/* Apply Button */}
            {result.is_eligible && (
              <button onClick={onApply} disabled={applying} className="btn-primary w-full flex items-center justify-center gap-2">
                {applying ? <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : "📋 Submit Application"}
              </button>
            )}
          </div>
        ) : (
          <div className="card h-64 flex flex-col items-center justify-center gap-3 text-center border-dashed">
            <FileText size={40} className="text-muted opacity-40" />
            <p className="text-muted">Fill the form and click<br/><span className="text-primary">Predict Eligibility</span></p>
          </div>
        )}
      </div>
    </div>
  );
}