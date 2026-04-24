import { useState } from "react";
import "./styles/theme.css";
import InputPad from "./windows/InputPad";
import TranslatePop from "./windows/TranslatePop";
import ExplainPop from "./windows/ExplainPop";
import ReviewSession from "./windows/ReviewSession";
import StatsView from "./windows/StatsView";

type View = "input" | "translate" | "review" | "stats";
interface ExplainCtx { word: string; context: string; translation: string; }

export default function App() {
  const view = (window.location.pathname.replace("/", "") || "input") as View;
  const [explainCtx, setExplainCtx] = useState<ExplainCtx | null>(null);

  const openExplain = (word: string, context: string, translation: string) =>
    setExplainCtx({ word, context, translation });

  if (view === "input") return (
    <InputPad
      onStats={() => window.open("/stats", "_blank")}
      onReview={() => window.open("/review", "_blank")}
    />
  );

  if (view === "translate") {
    if (explainCtx) return (
      <ExplainPop word={explainCtx.word} contextSentence={explainCtx.context} translation={explainCtx.translation} />
    );
    return <TranslatePop onExplain={openExplain} />;
  }

  if (view === "review") return <ReviewSession />;
  if (view === "stats")  return <StatsView onReview={() => window.open("/review", "_blank")} />;

  return <div style={{ padding: 20, color: "#888" }}>加载中…</div>;
}
