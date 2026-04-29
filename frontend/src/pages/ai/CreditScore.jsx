// frontend/src/pages/ai/CreditScore.jsx
import { useEffect, useState } from "react";
import { TrendingUp, RefreshCw } from "lucide-react";
import { RadialBarChart, RadialBar, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from "recharts";
import toast from "react-hot-toast";
import Loader from "../../components/Loader";
import { aiAPI } from "../../services/api";

export default function CreditScore() {
  const [score,     setScore]   = useState(null);
  const [history,   setHistory] = useState([]);
  const [loading,   setLoading] = useState(true);
  const [refreshing,setRefresh] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [scoreRes, histRes] = await Promise.all([
          aiAPI.getCreditScore(),
          aiAPI.creditHistory()
        ]);
        setScore(scoreRes.data);
        setHistory(histRes.data.history || []);
      } catch { toast.error("Failed to fetch credit score"); }
      finally { setLoading(false); }
    };
    load();
  }, []);

  const handleRefresh = async () => {
    setRefresh(true);
    try {
      const [scoreRes, histRes] = await Promise.all([
        aiAPI.getCreditScore(),
        aiAPI.creditHistory()
      ]);
      setScore(scoreRes.data);
      setHistory(histRes.data.history || []);
    } catch { toast.error("Failed to fetch credit score"); }
    finally { setRefresh(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader size="lg" text="Analysing your credit profile..." /></div>;

  const gradeColor = {
    EXCELLENT: "#22c55e", "VERY GOOD": "#86efac", GOOD: "#fbbf24",
    FAIR: "#f97316", POOR: "#ef4444", "VERY POOR": "#b91c1c"
  };
  const color = gradeColor[score?.grade] || "#6366f1";

  const gaugeData = [{ value: score?.credit_score - 300, fill: color }];

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Credit Score</h1>
          <p className="text-muted mt-1">CIBIL-style AI credit analysis</p>
        </div>
        <button onClick={handleRefresh} disabled={refreshing}
          className="btn-outline flex items-center gap-2 text-sm">
          <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Score Gauge */}
        <div className="card text-center">
          <p className="text-muted text-sm mb-2">Your Credit Score</p>
          <div className="relative h-48">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart cx="50%" cy="70%" innerRadius="60%" outerRadius="90%"
                data={gaugeData} startAngle={180} endAngle={0}>
                <RadialBar dataKey="value" cornerRadius={10} background={{ fill: "#2a2a3e" }} />
              </RadialBarChart>
            </ResponsiveContainer>
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-center">
              <p className="text-4xl font-black text-white">{score?.credit_score}</p>
              <p className="text-sm font-bold mt-0.5" style={{ color }}>{score?.grade}</p>
            </div>
          </div>
          <div className="flex justify-between text-xs text-muted mt-2 px-4">
            <span>300 Poor</span><span>900 Excellent</span>
          </div>
          <p className="text-gray-400 text-sm mt-3 px-2">{score?.description}</p>
        </div>

        {/* Factors */}
        <div className="space-y-3">
          <div className="card">
            <p className="font-semibold text-green-400 mb-3 text-sm">✅ Positive Factors</p>
            {score?.positive_factors?.length ? score.positive_factors.map((f, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <span className="text-gray-300 text-sm">{f.factor}</span>
                <span className="text-green-400 text-xs font-bold">+{f.impact}</span>
              </div>
            )) : <p className="text-muted text-sm">Keep transacting to build history</p>}
          </div>
          <div className="card">
            <p className="font-semibold text-red-400 mb-3 text-sm">⚠️ Areas to Improve</p>
            {score?.negative_factors?.length ? score.negative_factors.map((f, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <span className="text-gray-300 text-sm">{f.factor}</span>
                <span className="text-red-400 text-xs font-bold">-{f.impact}</span>
              </div>
            )) : <p className="text-muted text-sm">No major negative factors 🎉</p>}
          </div>
        </div>

        {/* Tips + Chart */}
        <div className="space-y-3">
          <div className="card">
            <p className="font-semibold text-white mb-3 text-sm">💡 Improvement Tips</p>
            <ul className="space-y-2">
              {score?.improvement_tips?.map((t, i) => (
                <li key={i} className="text-gray-400 text-sm leading-relaxed">{t}</li>
              ))}
            </ul>
          </div>

          {history.length > 0 && (
            <div className="card">
              <p className="font-semibold text-white mb-3 text-sm">📈 6-Month Trend</p>
              <ResponsiveContainer width="100%" height={120}>
                <LineChart data={history}>
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#6b7280" }} />
                  <YAxis domain={[550, 900]} tick={{ fontSize: 10, fill: "#6b7280" }} />
                  <Tooltip contentStyle={{ background: "#2a2a3e", border: "1px solid #3f3f5c", borderRadius: 8 }} />
                  <Line type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={2} dot={{ fill: "#6366f1", r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}