// frontend/src/components/StatCard.jsx
export default function StatCard({ title, value, sub, icon: Icon, color = "primary", trend }) {
  const colors = {
    primary: "from-indigo-600/20 to-purple-600/20 border-indigo-500/30",
    green:   "from-green-600/20  to-emerald-600/20  border-green-500/30",
    red:     "from-red-600/20    to-rose-600/20      border-red-500/30",
    yellow:  "from-yellow-600/20 to-orange-600/20    border-yellow-500/30",
  };
  const iconColors = {
    primary: "text-indigo-400", green: "text-green-400",
    red: "text-red-400",        yellow: "text-yellow-400",
  };
  return (
    <div className={`card bg-gradient-to-br ${colors[color]} fade-in`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-muted text-sm mb-1">{title}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
          {sub && <p className="text-muted text-xs mt-1">{sub}</p>}
          {trend && (
            <p className={`text-xs mt-1 font-medium ${trend > 0 ? "text-green-400" : "text-red-400"}`}>
              {trend > 0 ? "↑" : "↓"} {Math.abs(trend)}% vs last month
            </p>
          )}
        </div>
        {Icon && (
          <div className={`p-3 rounded-xl bg-white/5 ${iconColors[color]}`}>
            <Icon size={22} />
          </div>
        )}
      </div>
    </div>
  );
}