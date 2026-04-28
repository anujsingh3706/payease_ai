// frontend/src/pages/Dashboard.jsx
import { useEffect, useState } from "react";
import { Wallet, ArrowUpRight, ArrowDownLeft, TrendingUp, AlertTriangle, Activity } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import StatCard from "../components/StatCard";
import Loader   from "../components/Loader";
import { dashboardAPI } from "../services/api";
import useAuthStore from "../store/authStore";

const CHART_DEMO = [
  { month: "Aug", spent: 18000 }, { month: "Sep", spent: 22000 },
  { month: "Oct", spent: 17000 }, { month: "Nov", spent: 25000 },
  { month: "Dec", spent: 20000 }, { month: "Jan", spent: 15000 },
];

export default function Dashboard() {
  const { user }   = useAuthStore();
  const [data, setData]   = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardAPI.getDashboard()
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader size="lg" text="Loading dashboard..." />
    </div>
  );

  const fmt = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

  return (
    <div className="space-y-6 fade-in">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">
            Good {new Date().getHours() < 12 ? "Morning" : new Date().getHours() < 17 ? "Afternoon" : "Evening"}, {user?.fullName?.split(" ")[0]} 👋
          </h1>
          <p className="text-muted mt-1">Here's your financial overview</p>
        </div>
        <div className="text-right text-sm text-muted">
          {new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}
        </div>
      </div>

      {/* Balance Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Account Balance"    value={fmt(data?.account_balance)}    icon={Wallet}       color="primary" sub={`A/C: ${data?.account_number?.slice(-4).padStart(data?.account_number?.length, '*')}`} />
        <StatCard title="Wallet Balance"     value={fmt(data?.wallet_balance)}     icon={Activity}     color="green"   sub={data?.upi_id} />
        <StatCard title="Spent This Month"   value={fmt(data?.this_month_spent)}   icon={ArrowUpRight}  color="red"    />
        <StatCard title="Received This Month" value={fmt(data?.this_month_received)} icon={ArrowDownLeft} color="yellow" />
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Transactions", value: data?.total_transactions   || 0, color: "text-blue-400" },
          { label: "Pending",            value: data?.pending_transactions || 0, color: "text-yellow-400" },
          { label: "Flagged",            value: data?.flagged_transactions || 0, color: "text-red-400" },
        ].map(s => (
          <div key={s.label} className="card text-center">
            <p className={`text-3xl font-black ${s.color}`}>{s.value}</p>
            <p className="text-muted text-sm mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Chart + Recent Transactions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Spend Chart */}
        <div className="lg:col-span-2 card">
          <p className="section-title">Spending Trend</p>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={CHART_DEMO}>
              <defs>
                <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}   />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" stroke="#6b7280" tick={{ fontSize: 12 }} />
              <YAxis stroke="#6b7280" tick={{ fontSize: 12 }} tickFormatter={v => `₹${v/1000}k`} />
              <Tooltip
                contentStyle={{ background: "#2a2a3e", border: "1px solid #3f3f5c", borderRadius: 10 }}
                formatter={(v) => [`₹${v.toLocaleString("en-IN")}`, "Spent"]}
              />
              <Area type="monotone" dataKey="spent" stroke="#6366f1" strokeWidth={2} fill="url(#spendGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Recent Transactions */}
        <div className="card">
          <p className="section-title">Recent Transactions</p>
          <div className="space-y-3">
            {data?.recent_transactions?.length ? data.recent_transactions.map((t, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-border last:border-0">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm
                  ${t.type === "credit" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                  {t.type === "credit" ? "↓" : "↑"}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{t.description || t.type}</p>
                  <p className="text-xs text-muted">{t.date}</p>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-bold ${t.type === "credit" ? "text-green-400" : "text-red-400"}`}>
                    {t.type === "credit" ? "+" : "-"}{fmt(t.amount)}
                  </p>
                  {t.is_flagged && <span className="text-xs text-red-400">⚠️ Flagged</span>}
                </div>
              </div>
            )) : (
              <div className="text-center py-8 text-muted">
                <Activity size={32} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm">No transactions yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Flagged Alert */}
      {data?.flagged_transactions > 0 && (
        <div className="card border-red-500/30 bg-red-500/5 flex items-center gap-4">
          <AlertTriangle size={24} className="text-red-400 shrink-0" />
          <div>
            <p className="font-semibold text-red-400">
              {data.flagged_transactions} Flagged Transaction{data.flagged_transactions > 1 ? "s" : ""}
            </p>
            <p className="text-muted text-sm">Our AI fraud system flagged suspicious activity. Review them now.</p>
          </div>
        </div>
      )}
    </div>
  );
}