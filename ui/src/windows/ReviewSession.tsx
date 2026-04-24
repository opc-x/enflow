import { useState, useEffect } from "react";
import { api, VocabEntry } from "../api";

export default function ReviewSession() {
  const [due, setDue] = useState<VocabEntry[]>([]);
  const [idx, setIdx] = useState(0);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<{ correct: boolean; feedback: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    api.due().then(list => {
      setDue(list);
      if (list.length === 0) setDone(true);
    });
  }, []);

  const current = due[idx];

  const submit = async () => {
    if (!answer.trim() || loading) return;
    setLoading(true);
    try {
      // 步骤1: 语义判题
      const judgeRes = await api.judge(current.word, current.translation, answer);
      setResult(judgeRes);
      // 步骤2: 更新 SM-2
      await api.review(current.word, judgeRes.correct);
    } catch (e) {
      setResult({ correct: false, feedback: String(e) });
    } finally {
      setLoading(false);
    }
  };

  const next = () => {
    setResult(null);
    setAnswer("");
    if (idx + 1 >= due.length) setDone(true);
    else setIdx(idx + 1);
  };

  if (done) return (
    <div style={{ padding: 24, textAlign: "center" }}>
      <div style={{ fontSize: 32, marginBottom: 12 }}>🎉</div>
      <div style={{ fontSize: 16 }}>
        {due.length === 0 ? "没有待复习的词" : `本次复习 ${due.length} 个词，完成！`}
      </div>
    </div>
  );

  if (!current) return <div style={{ padding: 20 }} className="muted">加载中…</div>;

  return (
    <div style={{ padding: "16px 20px" }}>
      {/* 进度 */}
      <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
        {idx + 1} / {due.length}
      </div>

      {/* 单词 */}
      <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 16 }}>{current.word}</div>

      {/* 答案输入 */}
      {!result ? (
        <>
          <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
            输入中文意思（不会就留空直接回车）
          </div>
          <input
            autoFocus
            value={answer}
            onChange={e => setAnswer(e.target.value)}
            onKeyDown={e => e.key === "Enter" && submit()}
            placeholder="中文翻译…"
            style={{ marginBottom: 10 }}
          />
          <button onClick={submit} disabled={loading}>
            {loading ? "判断中…" : "确认"}
          </button>
        </>
      ) : (
        <>
          {/* 结果 */}
          <div style={{
            fontSize: 18, fontWeight: 600, marginBottom: 8,
            color: result.correct ? "var(--green)" : "var(--red)"
          }}>
            {result.correct ? "✅ 正确" : "❌ 错误"}
          </div>
          <div style={{ marginBottom: 4 }}>
            标准答案：<span style={{ color: "var(--amber)" }}>{current.translation}</span>
          </div>
          {result.feedback && (
            <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
              {result.feedback}
            </div>
          )}
          <button onClick={next}>下一个 →</button>
        </>
      )}
    </div>
  );
}
