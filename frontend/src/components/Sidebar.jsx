// frontend/src/components/Sidebar.jsx
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, CreditCard, ArrowLeftRight, Wallet,
  Bot, ShieldAlert, BarChart3, TrendingUp, FileText,
  LogOut, User, ChevronRight
} from "lucide-react";
import useAuthStore from "../store/authStore";

const NAV = [
  { group: "Main",
    items: [
      { to: "/",          icon: LayoutDashboard, label: "Dashboard"    },
      { to: "/accounts",  icon: CreditCard,      label: "Accounts"     },
      { to: "/transfer",  icon: ArrowLeftRight,  label: "Transfer"     },
      { to: "/wallet",    icon: Wallet,           label: "Wallet & UPI" },
    ]
  },
  { group: "AI Features",
    items: [
      { to: "/ai/chat",         icon: Bot,        label: "AI Chatbot"      },
      { to: "/ai/fraud",        icon: ShieldAlert, label: "Fraud Check"    },
      { to: "/ai/credit",       icon: TrendingUp,  label: "Credit Score"   },
      { to: "/ai/loan",         icon: FileText,    label: "Loan Predictor" },
      { to: "/ai/spend",        icon: BarChart3,   label: "Spend Analyser" },
    ]
  },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate          = useNavigate();

  const handleLogout = () => { logout(); navigate("/login"); };

  return (
    <aside className="w-64 min-h-screen bg-card border-r border-border flex flex-col fixed left-0 top-0 z-30">

      {/* Logo */}
      <div className="px-6 py-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-primary flex items-center justify-center font-black text-white text-lg glow">
            P
          </div>
          <div>
            <p className="font-black text-white text-lg leading-none">PayEase</p>
            <p className="text-xs text-muted">AI Banking</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-5">
        {NAV.map((group) => (
          <div key={group.group}>
            <p className="text-xs font-semibold text-muted uppercase tracking-widest px-3 mb-2">
              {group.group}
            </p>
            <ul className="space-y-1">
              {group.items.map(({ to, icon: Icon, label }) => ( // eslint-disable-line no-unused-vars
                <li key={to}>
                  <NavLink
                    to={to}
                    end={to === "/"}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150
                       ${isActive
                         ? "bg-primary/20 text-primary border border-primary/30"
                         : "text-gray-400 hover:bg-white/5 hover:text-white"}`
                    }
                  >
                    <Icon size={17} />
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="px-3 py-4 border-t border-border">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 cursor-pointer mb-1"
             onClick={() => navigate("/profile")}>
          <div className="w-8 h-8 rounded-full bg-gradient-primary flex items-center justify-center text-sm font-bold text-white">
            {user?.fullName?.[0] || "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white truncate">{user?.fullName}</p>
            <p className="text-xs text-muted truncate">{user?.email}</p>
          </div>
          <ChevronRight size={14} className="text-muted" />
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm text-red-400 hover:bg-red-500/10 transition-all"
        >
          <LogOut size={17} /> Logout
        </button>
      </div>
    </aside>
  );
}