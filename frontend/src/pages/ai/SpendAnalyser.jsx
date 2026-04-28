// frontend/src/pages/ai/SpendAnalyser.jsx
import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from "recharts";
import { BarChart3, RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react";
import Loader from "../../components/Loader";
import toast from "react-hot-toast";
import { aiAPI } from "../../services/api";

const COLORS = ["#6366f1","#8b5cf6","#ec4899","#f59e0b","#10b981","#3b82f6","#ef4444","#84cc16","#f97316","#06b6d4","#a855f7"];

export default function SpendAnalyser() {
  const [summary,  setSummary]  = useState(null);
  const [compare,  setCompare]  = useState(null);
  const [tab,      setTab]      = useState("summary");
  const [loading,  setLoading]  = useState(true);
  const [catLoading,setCatLoad] = useState(false);

  useEffect(() => {
    Promise.all([aiAPI.spendSummary(), aiAPI.compareSpend()])
      .then(([s, c]) => { setSummary(s.data); setCompare(c.data); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const categorise = async () => {
    setCatLoad(true);
    try {
      const res = await aiAPI.categoriseAll();
      toast.success(res.data.message);
      const s = await aiAPI.spendSummary();
      setSummary(s.data);
    } catch { toast.error("Failed"); }
    finally { setCatLoad(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader size="lg" text="Analysing your spending..." /></div>;

  const fmt = n => `₹${Number(n||0).toLocaleString("en-IN")}`;

  const pieData = Object.entries(summary?.categories || {}).map(([name, d]) => ({
    name, value: d.amount, pct: d.percentage
  }));

  const barData = Object.entries(compare?.category_comparison || {}).slice(0, 8).map(([name, d]) => ({
    name: name.split(" ")[0], current: d.current, previous: d.previous
  }));

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-black text-white">Spend Analyser</h1>
          <p className="text-muted text-sm mt-1">{summary?.period} · AI-powered categorisation</p>
        </div>
        <button onClick={categorise} disabled={catLoading}
          className="btn-outline text-sm flex items-center gap-2">
          <RefreshCw size={14} className={catLoading ? "animate-spin" : ""} /> Auto-Categorise
        </button>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Spent",    value: fmt(summary?.total_spent),   color: "text-red-400" },
          { label: "Total Received", value: fmt(summary?.total_received), color: "text-green-400" },
          { label: "Net Flow",       value: fmt(summary?.net_flow),       color: summary?.net_flow >= 0 ? "text-green-400" : "text-red-400" },
          { label: "Savings Rate",   value: `${summary?.savings_rate}%`,  color: summary?.savings_rate >= 20 ? "text-green-400" : "text-yellow-400" },
        ].map(s => (
          <div key={s.label} className="card text-center">
            <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
            <p className="text-muted text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1 bg-card rounded-xl border border-border w-fit">
        {["summary","compare","insights"].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all
              ${tab === t ? "bg-primary text-white" : "text-muted hover:text-white"}`}>
            {t}
          </button>
        ))}
      </div>

      {/* Summary Tab */}
      {tab === "summary" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pie Chart */}
          <div className="card">
            <p className="section-title">Spending by Category</p>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                    paddingAngle={3} dataKey="value">
                    {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v) => [fmt(v), ""]}
                    contentStyle={{ background: "#2a2a3e", border: "1px solid #3f3f5c", borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-48 text-muted">No data yet</div>
            )}
          </div>

          {/* Category List */}
          <div className="card">
            <p className="section-title">Category Breakdown</p>
            <div className="space-y-3">
              {pieData.length > 0 ? pieData.map((cat, i) => (
                <div key={cat.name} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-300 flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                      {cat.name}
                    </span>
                    <span className="text-white font-bold">{fmt(cat.value)}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-1.5">
                    <div className="h-1.5 rounded-full transition-all"
                      style={{ width: `${cat.pct}%`, background: COLORS[i % COLORS.length] }} />
                  </div>
                  <p className="text-xs text-muted text-right">{cat.pct}%</p>
                </div>
              )) : <p className="text-muted text-sm text-center py-8">No transactions categorised yet</p>}
            </div>
          </div>
        </div>
      )}

      {/* Compare Tab */}
      {tab === "compare" && (
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <p className="section-title mb-0">Month vs Last Month</p>
              <div className={`flex items-center gap-1.5 text-sm font-bold
                ${compare?.overall_change_pct > 5 ? "text-red-400" : compare?.overall_change_pct < -5 ? "text-green-400" : "text-yellow-400"}`}>
                {compare?.overall_change_pct > 5 ? <TrendingUp size={16}/> : compare?.overall_change_pct < -5 ? <TrendingDown size={16}/> : <Minus size={16}/>}
                {compare?.overall_trend}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData} barCategoryGap="30%">
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#6b7280" }} />
                <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} tickFormatter={v => `₹${v/1000}k`} />
                <Tooltip formatter={v => [fmt(v), ""]}
                  contentStyle={{ background: "#2a2a3e", border: "1px solid #3f3f5c", borderRadius: 8 }} />
                <Bar dataKey="previous" name="Last Month" fill="#4f46e5" radius={[4,4,0,0]} />
                <Bar dataKey="current"  name="This Month" fill="#818cf8" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Insights Tab */}
      {tab === "insights" && (
        <div className="space-y-3">
          {summary?.insights?.map((insight, i) => (
            <div key={i} className="card flex items-start gap-3 fade-in">
              <div className="w-8 h-8 rounded-xl bg-primary/20 flex items-center justify-center shrink-0 text-sm">
                💡
              </div>
              <p className="text-gray-300 text-sm leading-relaxed">{insight}</p>
            </div>
          ))}
          {summary?.top_spend_days?.length > 0 && (
            <div className="card">
              <p className="font-bold text-white mb-3 text-sm">🔥 Top Spending Days</p>
              {summary.top_spend_days.map((d, i) => (
                <div key={i} className="flex justify-between py-2 border-b border-border last:border-0">
                  <span className="text-gray-400 text-sm">{d.date}</span>
                  <span className="text-white font-bold text-sm">{fmt(d.amount)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}