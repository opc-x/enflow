import { useState, useEffect } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { listen } from "@tauri-apps/api/event";
import { api } from "../api";

const AUTO_CLOSE_MS = 12000;

interface Props { onExplain: (word: string, context: string, translation: string) => void; }

export default function TranslatePop({ onExplain }: Props) {
  const [original, setOriginal] = useState("");
  const [translation, setTranslation] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [textType, setTextType] = useState("word");

  useEffect(() => {
    const unlisten = listen<string>("translate-selected", async (event) => {
      const text = event.payload.trim();
      if (!text) return;
      setOriginal(text);
      setTranslation("");
      setError("");
      setLoading(true);

      try {
        const res = await api.translate(text);
        setTranslation(res.translation);
        setTextType(res.text_type);
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    });

    // 12秒自动关闭
    const timer = setTimeout(() => getCurrentWindow().hide(), AUTO_CLOSE_MS);
    return () => { unlisten.then(f => f()); clearTimeout(timer); };
  }, []);

  const close = () => getCurrentWindow().hide();

  return (
    <div onClick={close} style={{ padding: "12px 14px", cursor: "pointer", height: "100%" }}>
      <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>
        {original.length > 60 ? original.slice(0, 60) + "…" : original}
      </div>
      <div className="divider" />
      <div style={{ fontSize: 20, fontWeight: 600, margin: "10px 0", color: error ? "var(--red)" : "var(--fg)" }}>
        {loading ? "翻译中…" : error || translation}
      </div>

      {!loading && translation && (textType === "word" || textType === "phrase") && (
        <div onClick={e => e.stopPropagation()}
          style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button onClick={() => onExplain(original, "", translation)}>
            📖 解释 / 发音
          </button>
        </div>
      )}

      <div className="dim" style={{ fontSize: 11, marginTop: 8 }}>点击任意处关闭</div>
    </div>
  );
}
