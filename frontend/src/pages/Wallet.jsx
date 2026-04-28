// frontend/src/pages/Wallet.jsx
import { useEffect, useState } from "react";
import { Wallet as WalletIcon, Send, QrCode, Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import Loader from "../components/Loader";
import { walletAPI, paymentAPI } from "../services/api";

export default function Wallet() {
  const [wallet,  setWallet]  = useState(null);
  const [qr,      setQR]      = useState(null);
  const [tab,     setTab]     = useState("overview"); // overview | send | topup | qr
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const { register, handleSubmit, formState: { errors }, reset } = useForm();

  useEffect(() => {
    walletAPI.getWallet()
      .then(r => setWallet(r.data))
      .finally(() => setLoading(false));
  }, []);

  const fetchQR = async () => {
    setTab("qr");
    if (qr) return;
    try {
      const res = await walletAPI.getQRCode();
      setQR(res.data);
    } catch { toast.error("Failed to generate QR"); }
  };

  const handleUPITransfer = async (data) => {
    setSending(true);
    try {
      const res = await walletAPI.upiTransfer({
        to_upi_id: data.to_upi_id,
        amount:    parseFloat(data.amount),
        mpin:      data.mpin,
        note:      data.note,
      });
      toast.success(`₹${data.amount} sent successfully! 🎉`);
      setWallet(prev => ({ ...prev, balance: res.data.new_balance }));
      reset();
      setTab("overview");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Transfer failed");
    } finally {
      setSending(false);
    }
  };

  const handleRazorpay = async (data) => {
    try {
      const order = await paymentAPI.createOrder({ amount: parseFloat(data.topup_amount) });
      const opts  = {
        key:         order.data.key_id,
        amount:      order.data.amount_paise,
        currency:    "INR",
        name:        "PayEase AI",
        description: "Wallet Top-up",
        order_id:    order.data.order_id,
        handler: async (response) => {
          await paymentAPI.verifyPayment(response);
          toast.success("Wallet topped up! 💰");
          const w = await walletAPI.getWallet();
          setWallet(w.data);
          setTab("overview");
        },
        prefill:  { name: "PayEase User" },
        theme:    { color: "#6366f1" },
      };
      const rzp = new window.Razorpay(opts);
      rzp.open();
    } catch { toast.error("Payment failed"); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader size="lg" /></div>;

  const fmt = n => `₹${Number(n || 0).toLocaleString("en-IN")}`;

  const TABS = [
    { id: "overview", label: "Overview",  icon: WalletIcon },
    { id: "send",     label: "Send Money", icon: Send },
    { id: "topup",    label: "Add Money",  icon: Plus },
    { id: "qr",       label: "My QR Code", icon: QrCode, onClick: fetchQR },
  ];

  return (
    <div className="max-w-xl space-y-6 fade-in">
      <div>
        <h1 className="text-2xl font-black text-white">Wallet & UPI</h1>
        <p className="text-muted mt-1">Instant payments — completely free</p>
      </div>

      {/* Balance Card */}
      <div className="card bg-gradient-to-br from-indigo-600/30 to-purple-600/30 border-indigo-500/30">
        <p className="text-muted text-sm">Wallet Balance</p>
        <p className="text-4xl font-black text-white mt-1">{fmt(wallet?.balance)}</p>
        <p className="text-primary text-sm mt-2 font-medium">{wallet?.upi_id}</p>
        <div className="flex gap-4 mt-3 text-xs text-muted">
          <span>Daily Limit: {fmt(wallet?.daily_limit)}</span>
          <span>•</span>
          <span>Today Spent: {fmt(wallet?.today_spent)}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1 bg-card rounded-xl border border-border">
        {TABS.map(t => (
          <button key={t.id}
            onClick={() => t.onClick ? t.onClick() : setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium flex-1 justify-center transition-all
              ${tab === t.id ? "bg-primary text-white" : "text-muted hover:text-white"}`}>
            <t.icon size={15} /> {t.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === "overview" && (
        <div className="space-y-3">
          {[
            { label: "Daily Limit",    value: fmt(wallet?.daily_limit) },
            { label: "Monthly Limit",  value: fmt(wallet?.monthly_limit) },
            { label: "Today Spent",    value: fmt(wallet?.today_spent) },
            { label: "This Month",     value: fmt(wallet?.month_spent) },
            { label: "Status",         value: wallet?.is_active ? "Active ✅" : "Inactive ❌" },
          ].map(row => (
            <div key={row.label} className="flex justify-between items-center py-3 border-b border-border last:border-0">
              <span className="text-muted text-sm">{row.label}</span>
              <span className="text-white font-semibold text-sm">{row.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Send via UPI */}
      {tab === "send" && (
        <div className="card">
          <p className="font-bold text-white mb-4">Send via UPI</p>
          <form onSubmit={handleSubmit(handleUPITransfer)} className="space-y-4">
            <div>
              <label className="label">UPI ID</label>
              <input className="input" placeholder="9876543210@payease"
                {...register("to_upi_id", { required: true })} />
            </div>
            <div>
              <label className="label">Amount (₹)</label>
              <input className="input" type="number" step="0.01" placeholder="500"
                {...register("amount", { required: true, min: 1, max: 10000 })} />
            </div>
            <div>
              <label className="label">MPIN</label>
              <input className="input" type="password" maxLength={6} placeholder="6-digit MPIN"
                {...register("mpin", { required: true, minLength: 6, maxLength: 6 })} />
            </div>
            <div>
              <label className="label">Note (Optional)</label>
              <input className="input" placeholder="Dinner split"
                {...register("note")} />
            </div>
            <button type="submit" disabled={sending} className="btn-primary w-full flex items-center justify-center gap-2">
              {sending ? <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><Send size={16}/> Send Money</>}
            </button>
          </form>
        </div>
      )}

      {/* Top Up */}
      {tab === "topup" && (
        <div className="card space-y-4">
          <p className="font-bold text-white">Add Money via Razorpay</p>
          <div className="grid grid-cols-3 gap-2">
            {[500, 1000, 2000, 5000, 10000].map(amt => (
              <button key={amt}
                onClick={() => handleRazorpay({ topup_amount: amt })}
                className="btn-outline text-sm py-3">
                ₹{amt.toLocaleString("en-IN")}
              </button>
            ))}
          </div>
          <p className="text-muted text-xs text-center">Secured by Razorpay · Test mode active</p>
        </div>
      )}

      {/* QR Code */}
      {tab === "qr" && (
        <div className="card text-center space-y-4">
          <p className="font-bold text-white">Your Payment QR Code</p>
          {qr ? (
            <>
              <div className="bg-white p-4 rounded-2xl inline-block">
                <img src={qr.qr_code} alt="UPI QR" className="w-48 h-48 mx-auto" />
              </div>
              <p className="text-primary font-semibold">{qr.upi_id}</p>
              <p className="text-muted text-sm">Scan this code to receive payments instantly</p>
            </>
          ) : (
            <Loader size="md" text="Generating QR code..." />
          )}
        </div>
      )}
    </div>
  );
}