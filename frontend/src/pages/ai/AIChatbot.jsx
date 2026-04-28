// frontend/src/pages/ai/AIChatbot.jsx
import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Zap, RefreshCw } from "lucide-react";
import { aiAPI } from "../../services/api";
import Loader from "../../components/Loader";

export default function AIChatbot() {
  const [messages,  setMessages]  = useState([
    { role: "assistant", content: "👋 Hi! I'm **PayEase AI Assistant** powered by LLaMA3-70B.\n\nI can help you with:\n• Account balance & transactions\n• NEFT/RTGS/IMPS/UPI queries\n• Loan eligibility advice\n• Credit score tips\n• Banking regulations & RBI guidelines\n\nWhat would you like to know?" }
  ]);
  const [input,     setInput]     = useState("");
  const [loading,   setLoading]   = useState(false);
  const [hints,     setHints]     = useState([]);
  const bottomRef  = useRef(null);

  useEffect(() => {
    aiAPI.quickHelp().then(r => setHints(r.data.suggestions?.slice(0, 6)));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg) return;

    const history = messages
      .filter(m => m.role !== "system")
      .map(m => ({ role: m.role, content: m.content }));

    setMessages(prev => [...prev, { role: "user", content: msg }]);
    setInput("");
    setLoading(true);

    try {
      const res = await aiAPI.chat({ message: msg, history });
      setMessages(prev => [...prev, {
        role: "assistant",
        content: res.data.reply,
        meta: { intent: res.data.intent, tokens: res.data.tokens_used }
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Sorry, I'm having trouble connecting. Please try again in a moment."
      }]);
    } finally {
      setLoading(false);
    }
  };

  const formatContent = (text) =>
    text
      .replace(/\*\*(.*?)\*\*/g, "<strong class='text-white'>$1</strong>")
      .replace(/\n/g, "<br/>")
      .replace(/^• /gm, "• ");

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)] max-w-3xl fade-in">

      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-primary flex items-center justify-center glow">
          <Bot size={20} className="text-white" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">PayEase AI Assistant</h1>
          <p className="text-muted text-xs flex items-center gap-1">
            <Zap size={11} className="text-yellow-400" />
            Powered by LLaMA3-70B via Groq · Ultra-fast
          </p>
        </div>
        <button onClick={() => setMessages([messages[0]])} className="ml-auto btn-outline text-sm flex items-center gap-1.5 py-1.5">
          <RefreshCw size={14} /> Clear
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 fade-in ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-sm
              ${msg.role === "user" ? "bg-primary/30 text-primary" : "bg-purple-500/20 text-purple-400"}`}>
              {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className={`max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col gap-1`}>
              <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed
                ${msg.role === "user"
                  ? "bg-primary/20 text-white rounded-tr-sm"
                  : "bg-card border border-border text-gray-300 rounded-tl-sm"}`}
                dangerouslySetInnerHTML={{ __html: formatContent(msg.content) }}
              />
              {msg.meta && (
                <p className="text-xs text-muted px-1">
                  Intent: <span className="text-primary">{msg.meta.intent}</span> · {msg.meta.tokens} tokens
                </p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center">
              <Bot size={16} className="text-purple-400" />
            </div>
            <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1.5 items-center">
                {[0,1,2].map(i => (
                  <div key={i} className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: `${i*0.15}s` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick hints */}
      {messages.length <= 1 && hints.length > 0 && (
        <div className="py-3">
          <p className="text-xs text-muted mb-2">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {hints.map((h, i) => (
              <button key={i} onClick={() => sendMessage(h)}
                className="text-xs bg-card border border-border hover:border-primary/50 text-gray-400 hover:text-white px-3 py-1.5 rounded-full transition-all">
                {h}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="flex gap-3 pt-4 border-t border-border">
        <input
          className="input flex-1"
          placeholder="Ask me anything about your account..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
          disabled={loading}
        />
        <button onClick={() => sendMessage()} disabled={loading || !input.trim()}
          className="btn-primary px-4 flex items-center justify-center">
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}