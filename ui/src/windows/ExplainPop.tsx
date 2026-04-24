import { useState, useEffect } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { api, ExplainResult } from "../api";

interface Props { word: string; contextSentence: string; translation: string; }

export default function ExplainPop({ word, contextSentence, translation }: Props) {
  const [tab, setTab] = useState<"explain" | "pronounce">("explain");
  const [data, setData] = useState<ExplainResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.explain(word, contextSentence)
      .then(setData)
      .catch(e => setError(String(e)));
  }, [word]);

  const renderFields = (text: string) =>
    text.split("\n").map((line, i) => {
      const isHeader = line.startsWith("【");
      const isBullet = line.startsWith("⚡");
      return (
        <div key={i} style={{
          marginBottom: isHeader ? 6 : 2,
          color: isBullet ? "var(--amber)" : "var(--fg)",
          fontSize: isHeader ? 14 : 13,
        }}>
          {line}
        </div>
      );
    });

  return (
    <div onClick={() => getCurrentWindow().hide()}
      style={{ height: "100%", display: "flex", flexDirection: "column", padding: "10px 14px" }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 16, fontWeight: 600 }}>{word}</span>
        <span className="muted" style={{ fontSize: 12 }}>{translation}</span>
      </div>
      <div className="divider" style={{ marginTop: 8 }} />

      {/* Tabs */}
      <div onClick={e => e.stopPropagation()}
        style={{ display: "flex", gap: 2, margin: "8px 0" }}>
        {(["explain", "pronounce"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ fontSize: 12, background: tab === t ? "var(--blue)" : "var(--bg2)" }}>
            {t === "explain" ? "📖 解释" : "🔊 发音"}
          </button>
        ))}
      </div>

      {/* Content */}
      <div onClick={e => e.stopPropagation()} style={{ flex: 1, overflowY: "auto" }}>
        {!data && !error && <div className="muted">加载中…</div>}
        {error && <div style={{ color: "var(--red)" }}>{error}</div>}
        {data && renderFields(tab === "explain" ? data.explain : data.pronounce)}
      </div>

      <div className="dim" style={{ fontSize: 11, textAlign: "right", marginTop: 6 }}>
        点击任意处关闭
      </div>
    </div>
  );
}
