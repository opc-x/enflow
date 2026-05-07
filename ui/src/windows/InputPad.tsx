import { useState, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { api } from "../api";

export default function InputPad({ onStats, onReview }: {
  onStats: () => void; onReview: () => void;
}) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState("Enter 转换  Esc 关闭  ✦T 划词翻译");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const submitAfterCompose = useRef(false);
  const composeFallbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const submit = async () => {
    if (!text.trim() || loading) return;
    setLoading(true);
    setStatus("处理中...");
    try {
      const { result } = await api.convert(text);
      await invoke("paste_text", { text: result });
      setText("");
      setStatus("Enter 转换  Esc 关闭  ✦T 划词翻译");
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
          if (e.key === "Enter") {
            if (e.nativeEvent.isComposing) {
              submitAfterCompose.current = true;
              // Fallback: some IMEs (e.g. Sougou V-mode) never fire compositionEnd
              // on Enter. Submit anyway after 500ms.
              if (composeFallbackTimer.current) clearTimeout(composeFallbackTimer.current);
              composeFallbackTimer.current = setTimeout(() => {
                if (!submitAfterCompose.current) return;
                submitAfterCompose.current = false;
                submit();
              }, 500);
            } else {
              submit();
            }
          }
          if (e.key === "Escape") getCurrentWindow().hide();
        }}
        onCompositionEnd={() => {
          if (!submitAfterCompose.current) return;
          submitAfterCompose.current = false;
          if (composeFallbackTimer.current) {
            clearTimeout(composeFallbackTimer.current);
            composeFallbackTimer.current = null;
          }
          setTimeout(submit, 10);
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
