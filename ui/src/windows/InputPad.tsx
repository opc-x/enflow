import { useState, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { api } from "../api";

export default function InputPad({ onStats, onReview }: {
  onStats: () => void; onReview: () => void;
}) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState("输入中英混合  →  Enter 转换    Esc 关闭");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = async () => {
    if (!text.trim() || loading) return;
    setLoading(true);
    setStatus("处理中...");
    try {
      const { result } = await api.convert(text);
      await invoke("paste_text", { text: result });
      await getCurrentWindow().hide();
      setText("");
      setStatus("输入中英混合  →  Enter 转换    Esc 关闭");
    } catch (e) {
      setStatus(`出错: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
      <div className="muted" style={{ fontSize: 12 }}>{status}</div>
      <input
        ref={inputRef}
        autoFocus
        value={text}
        disabled={loading}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => {
          if (e.key === "Enter") submit();
          if (e.key === "Escape") getCurrentWindow().hide();
        }}
        placeholder="输入中英混合文字..."
      />
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onStats} style={{ fontSize: 12 }}>📊 学习进展</button>
        <button onClick={onReview} style={{ fontSize: 12 }}>🔁 开始复习</button>
      </div>
    </div>
  );
}
