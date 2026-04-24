import "./styles/theme.css";
import InputPad from "./windows/InputPad";
import TranslatePop from "./windows/TranslatePop";
import ReviewSession from "./windows/ReviewSession";
import StatsView from "./windows/StatsView";

type View = "input" | "translate" | "review" | "stats";

export default function App() {
  const view = (window.location.pathname.replace(/^\/+|\/+$/g, "") || "input") as View;

  if (view === "input") return (
    <InputPad
      onStats={() => window.open("/stats", "_blank")}
      onReview={() => window.open("/review", "_blank")}
    />
  );

  if (view === "translate") {
    return <TranslatePop />;
  }

  if (view === "review") return <ReviewSession />;
  if (view === "stats")  return <StatsView onReview={() => window.open("/review", "_blank")} />;

  return <div style={{ padding: 20, color: "#888" }}>加载中…</div>;
}
