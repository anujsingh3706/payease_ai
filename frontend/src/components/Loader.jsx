// frontend/src/components/Loader.jsx
export default function Loader({ size = "md", text = "" }) {
  const s = size === "sm" ? "h-5 w-5" : size === "lg" ? "h-12 w-12" : "h-8 w-8";
  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className={`${s} border-4 border-primary/30 border-t-primary rounded-full animate-spin`} />
      {text && <p className="text-muted text-sm">{text}</p>}
    </div>
  );
}