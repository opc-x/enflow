import { useState, useEffect } from "react";
import { api, VocabStats } from "../api";

export default function StatsView({ onReview }: { onReview: () => void }) {
  const [stats, setStats] = useState<VocabStats | null>(null);

  useEffect(() => { api.stats().then(setStats); }, []);

  if (!stats) return <div style={{ padding: 20 }} className="muted">加载中…</div>;

  const total = stats.total || 1;
  const bars = [
    { ratio: stats.not_mastered / total, color: "var(--red)" },
    { ratio: stats.learning / total,     color: "var(--amber)" },
    { ratio: stats.mastered / total,     color: "var(--green)" },
  ];

  return (
    <div style={{ padding: "16px 20px" }}>
      <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>📊 学习进展</div>
      <div className="divider" />

      {/* 今日 */}
      <div style={{ marginTop: 12, marginBottom: 4 }} className="muted" >今日</div>
      <div>新增 <span style={{ color: "var(--fg)", fontWeight: 600 }}>{stats.today_new}</span> 个生词</div>
      <div style={{ color: stats.streak >= 3 ? "var(--amber)" : "var(--muted)", marginTop: 4 }}>
        🔥 连续学习 {stats.streak} 天
      </div>

      <div className="divider" style={{ margin: "12px 0" }} />

      {/* 掌握度 */}
      <div className="muted" style={{ marginBottom: 6 }}>共 {stats.total} 个词</div>
      <div style={{ display: "flex", height: 10, borderRadius: 5, overflow: "hidden", background: "var(--bg2)" }}>
        {bars.map((b, i) => b.ratio > 0 && (
          <div key={i} style={{ flex: b.ratio, background: b.color }} />
        ))}
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 6, fontSize: 12 }}>
        <span style={{ color: "var(--red)" }}>🔴 未掌握 {stats.not_mastered}</span>
        <span style={{ color: "var(--amber)" }}>🟡 学习中 {stats.learning}</span>
        <span style={{ color: "var(--green)" }}>🟢 已掌握 {stats.mastered}</span>
      </div>

      <div className="divider" style={{ margin: "12px 0" }} />

      {/* 复习 */}
      <div style={{ color: stats.due_today > 0 ? "var(--amber)" : "var(--muted)" }}>
        今日待复习 {stats.due_today} 个词
      </div>
      {stats.due_today > 0 && (
        <button onClick={onReview} style={{ marginTop: 8, fontSize: 12 }}>
          ▶ 开始复习
        </button>
      )}
    </div>
  );
}
