import { useState, useEffect, useCallback } from "react";
import { getCurrentWindow, LogicalSize } from "@tauri-apps/api/window";
import { invoke } from "@tauri-apps/api/core";
import { api, ExplainResult } from "../api";

const AUTO_CLOSE_MS = 12000;
const WINDOW_WIDTH = 480;
const BASE_HEIGHT = 140;
const MAX_HEIGHT = 560;

type DetailMode = "explain" | "pronounce";

export default function TranslatePop() {
  const [original, setOriginal] = useState("");
  const [translation, setTranslation] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailMode, setDetailMode] = useState<DetailMode | null>(null);
  const [detailData, setDetailData] = useState<ExplainResult | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  const resize = useCallback((height: number) => {
    getCurrentWindow().setSize(new LogicalSize(WINDOW_WIDTH, Math.min(height, MAX_HEIGHT))).catch(() => {});
  }, []);

  const renderFields = (text: string) =>
    text.split("\n").filter(Boolean).map((line, i) => {
      const isBullet = line.startsWith("⚡");
      return (
        <div key={i} style={{
          marginBottom: 5,
          color: isBullet ? "var(--amber)" : "var(--fg)",
          fontSize: line.startsWith("【") ? 13 : 12,
          lineHeight: 1.35,
        }}>
          {line}
        </div>
      );
    });

  const resizeForContent = useCallback((nextTranslation: string, detailText = "") => {
    const textLen = nextTranslation.length + detailText.length;
    if (detailText) {
      resize(Math.max(300, Math.min(MAX_HEIGHT, 230 + Math.ceil(detailText.length / 34) * 22)));
      return;
    }
    if (textLen > 120 || nextTranslation.includes("\n")) {
      resize(260);
      return;
    }
    if (textLen > 50) {
      resize(190);
      return;
    }
    resize(BASE_HEIGHT);
  }, [resize]);

  const doTranslate = useCallback(async () => {
    const text: string = await invoke("get_pending_translate");
    if (!text) return;
    setOriginal(text);
    setTranslation("");
    setError("");
    setDetailMode(null);
    setDetailData(null);
    setDetailError("");
    setLoading(true);
    resize(BASE_HEIGHT);
    try {
      const res = await api.translate(text);
      setTranslation(res.translation);
      resizeForContent(res.translation);
    } catch (e) {
      setError(String(e));
      resize(180);
    } finally {
      setLoading(false);
    }
  }, [resize, resizeForContent]);

  const openDetail = async (mode: DetailMode) => {
    if (!original || detailLoading) return;
    setDetailMode(mode);
    setDetailError("");
    resize(300);
    if (detailData) {
      const text = mode === "explain" ? detailData.explain : detailData.pronounce;
      resizeForContent(translation, text);
      return;
    }
    setDetailLoading(true);
    try {
      const data = await api.explain(original);
      setDetailData(data);
      const text = mode === "explain" ? data.explain : data.pronounce;
      resizeForContent(translation, text);
    } catch (e) {
      setDetailError(String(e));
      resize(260);
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    resize(BASE_HEIGHT);
    // 挂在 window 上，Rust eval 可以触发重新翻译（窗口复用时）
    (window as unknown as Record<string, unknown>).__reloadTranslate = doTranslate;
    doTranslate();

    const timer = setTimeout(() => getCurrentWindow().hide(), AUTO_CLOSE_MS);
    return () => {
      clearTimeout(timer);
      delete (window as unknown as Record<string, unknown>).__reloadTranslate;
    };
  }, [doTranslate, resize]);

  const close = () => getCurrentWindow().hide();
  const detailText = detailData && detailMode
    ? (detailMode === "explain" ? detailData.explain : detailData.pronounce)
    : "";

  return (
    <div onClick={close} style={{ padding: "10px 14px", cursor: "pointer", height: "100%", overflow: "hidden" }}>
      <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>
        {original.length > 60 ? original.slice(0, 60) + "…" : original}
      </div>
      <div className="divider" />
      <div style={{
        fontSize: 19,
        fontWeight: 600,
        margin: "8px 0",
        color: error ? "var(--red)" : "var(--fg)",
        lineHeight: 1.25,
      }}>
        {loading ? "翻译中…" : error || translation}
      </div>

      {!loading && translation && (
        <div onClick={e => e.stopPropagation()} style={{ display: "flex", gap: 8, marginTop: 6 }}>
          <button
            onClick={() => openDetail("explain")}
            style={{ fontSize: 12, background: detailMode === "explain" ? "var(--blue)" : "var(--bg2)" }}
          >
            📖 解释
          </button>
          <button
            onClick={() => openDetail("pronounce")}
            style={{ fontSize: 12, background: detailMode === "pronounce" ? "var(--blue)" : "var(--bg2)" }}
          >
            🔊 发音
          </button>
        </div>
      )}

      <div onClick={e => e.stopPropagation()} style={{ marginTop: 8, maxHeight: 330, overflowY: "auto" }}>
        {detailLoading && <div className="muted" style={{ fontSize: 12 }}>加载中…</div>}
        {detailError && <div style={{ color: "var(--red)", fontSize: 12 }}>{detailError}</div>}
        {!detailLoading && detailText && renderFields(detailText)}
      </div>

      <div className="dim" style={{ fontSize: 11, marginTop: 6 }}>点击任意处关闭</div>
    </div>
  );
}
