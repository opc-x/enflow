/**
 * 组件单元测试 — mock Tauri API，真实 fetch 调 backend（需后端运行）
 * 覆盖：InputPad / TranslatePop / ReviewSession / StatsView / ExplainPop
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ── mock api.ts 让组件测试与网络隔离 ─────────────────────────────────────────
vi.mock("../api", () => ({
  api: {
    convert:   vi.fn(),
    translate: vi.fn(),
    explain:   vi.fn(),
    judge:     vi.fn(),
    stats:     vi.fn(),
    due:       vi.fn(),
    review:    vi.fn(),
  },
}));

import { api } from "../api";
import InputPad     from "../windows/InputPad";
import ReviewSession from "../windows/ReviewSession";
import StatsView     from "../windows/StatsView";
import ExplainPop   from "../windows/ExplainPop";

// ── InputPad ─────────────────────────────────────────────────────────────────
describe("InputPad", () => {
  const onStats  = vi.fn();
  const onReview = vi.fn();

  beforeEach(() => vi.clearAllMocks());

  it("渲染输入框和两个按钮", () => {
    render(<InputPad onStats={onStats} onReview={onReview} />);
    expect(screen.getByPlaceholderText(/输入中英混合/)).toBeInTheDocument();
    expect(screen.getByText(/学习进展/)).toBeInTheDocument();
    expect(screen.getByText(/开始复习/)).toBeInTheDocument();
  });

  it("Enter 触发 convert 并调 paste_text", async () => {
    const { invoke } = await import("@tauri-apps/api/core");
    (api.convert as ReturnType<typeof vi.fn>).mockResolvedValue({ result: "I want to book a meeting." });

    render(<InputPad onStats={onStats} onReview={onReview} />);
    const input = screen.getByPlaceholderText(/输入中英混合/);
    await userEvent.type(input, "我想 book a meeting");
    await userEvent.keyboard("{Enter}");

    await waitFor(() => expect(api.convert).toHaveBeenCalledWith("我想 book a meeting"));
    await waitFor(() => expect(invoke).toHaveBeenCalledWith("paste_text", { text: "I want to book a meeting." }));
  });

  it("空输入 Enter 不触发 convert", async () => {
    render(<InputPad onStats={onStats} onReview={onReview} />);
    await userEvent.keyboard("{Enter}");
    expect(api.convert).not.toHaveBeenCalled();
  });

  it("点击学习进展按钮触发 onStats", async () => {
    render(<InputPad onStats={onStats} onReview={onReview} />);
    await userEvent.click(screen.getByText(/学习进展/));
    expect(onStats).toHaveBeenCalled();
  });

  it("convert 失败时显示错误状态", async () => {
    (api.convert as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("network error"));
    render(<InputPad onStats={onStats} onReview={onReview} />);
    const input = screen.getByPlaceholderText(/输入中英混合/);
    await userEvent.type(input, "test");
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(screen.getByText(/出错/)).toBeInTheDocument());
  });
});

// ── ReviewSession ─────────────────────────────────────────────────────────────
describe("ReviewSession", () => {
  beforeEach(() => vi.clearAllMocks());

  it("无待复习词时显示完成状态", async () => {
    (api.due as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    render(<ReviewSession />);
    await waitFor(() => expect(screen.getByText(/没有待复习/)).toBeInTheDocument());
  });

  it("显示当前词并接受答案输入", async () => {
    (api.due as ReturnType<typeof vi.fn>).mockResolvedValue([{
      word: "ephemeral", translation: "短暂的",
      correct_count: 0, wrong_count: 0, seen_count: 1, next_review_time: "",
    }]);
    (api.judge as ReturnType<typeof vi.fn>).mockResolvedValue({ correct: true, feedback: "" });
    (api.review as ReturnType<typeof vi.fn>).mockResolvedValue({ next_review_time: "2026-04-27" });

    render(<ReviewSession />);
    await waitFor(() => expect(screen.getByText("ephemeral")).toBeInTheDocument());

    const input = screen.getByPlaceholderText(/中文翻译/);
    await userEvent.type(input, "短暂");
    await userEvent.keyboard("{Enter}");

    await waitFor(() => expect(api.judge).toHaveBeenCalledWith("ephemeral", "短暂的", "短暂"));
    await waitFor(() => expect(api.review).toHaveBeenCalledWith("ephemeral", true));
    await waitFor(() => expect(screen.getByText(/正确/)).toBeInTheDocument());
  });

  it("答错时显示标准答案和feedback", async () => {
    (api.due as ReturnType<typeof vi.fn>).mockResolvedValue([{
      word: "ephemeral", translation: "短暂的",
      correct_count: 0, wrong_count: 0, seen_count: 1, next_review_time: "",
    }]);
    (api.judge as ReturnType<typeof vi.fn>).mockResolvedValue({
      correct: false, feedback: "永恒的与短暂的意思相反",
    });
    (api.review as ReturnType<typeof vi.fn>).mockResolvedValue({ next_review_time: "2026-04-25" });

    render(<ReviewSession />);
    await waitFor(() => screen.getByText("ephemeral"));

    await userEvent.type(screen.getByPlaceholderText(/中文翻译/), "永恒的");
    await userEvent.keyboard("{Enter}");

    await waitFor(() => expect(screen.getByText(/错误/)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText(/永恒的与短暂的意思相反/)).toBeInTheDocument());
  });

  it("多词复习：答完第一词后显示下一词", async () => {
    (api.due as ReturnType<typeof vi.fn>).mockResolvedValue([
      { word: "ephemeral",  translation: "短暂的", correct_count: 0, wrong_count: 0, seen_count: 1, next_review_time: "" },
      { word: "resilience", translation: "韧性",   correct_count: 0, wrong_count: 0, seen_count: 1, next_review_time: "" },
    ]);
    (api.judge as ReturnType<typeof vi.fn>).mockResolvedValue({ correct: true, feedback: "" });
    (api.review as ReturnType<typeof vi.fn>).mockResolvedValue({ next_review_time: "2026-04-28" });

    render(<ReviewSession />);
    await waitFor(() => screen.getByText("ephemeral"));

    await userEvent.type(screen.getByPlaceholderText(/中文翻译/), "短暂");
    await userEvent.keyboard("{Enter}");
    await waitFor(() => screen.getByText(/正确/));

    await userEvent.click(screen.getByText(/下一个/));
    await waitFor(() => expect(screen.getByText("resilience")).toBeInTheDocument());
  });
});

// ── StatsView ─────────────────────────────────────────────────────────────────
describe("StatsView", () => {
  const onReview = vi.fn();
  beforeEach(() => vi.clearAllMocks());

  it("展示全部统计字段", async () => {
    (api.stats as ReturnType<typeof vi.fn>).mockResolvedValue({
      total: 42, not_mastered: 20, learning: 15, mastered: 7,
      due_today: 5, streak: 3, today_new: 2,
    });
    render(<StatsView onReview={onReview} />);
    await waitFor(() => expect(screen.getByText(/42 个词/)).toBeInTheDocument());
    expect(screen.getByText(/新增.*个生词/)).toBeInTheDocument();
    expect(screen.getByText(/5 个词/)).toBeInTheDocument();
    expect(screen.getByText(/3 天/)).toBeInTheDocument();
  });

  it("due_today > 0 时显示复习按钮", async () => {
    (api.stats as ReturnType<typeof vi.fn>).mockResolvedValue({
      total: 10, not_mastered: 5, learning: 3, mastered: 2,
      due_today: 3, streak: 1, today_new: 0,
    });
    render(<StatsView onReview={onReview} />);
    await waitFor(() => screen.getByText(/开始复习/));
    await userEvent.click(screen.getByText(/开始复习/));
    expect(onReview).toHaveBeenCalled();
  });

  it("due_today = 0 时不显示复习按钮", async () => {
    (api.stats as ReturnType<typeof vi.fn>).mockResolvedValue({
      total: 5, not_mastered: 0, learning: 2, mastered: 3,
      due_today: 0, streak: 7, today_new: 0,
    });
    render(<StatsView onReview={onReview} />);
    await waitFor(() => screen.getByText(/5 个词/));
    expect(screen.queryByText(/开始复习/)).not.toBeInTheDocument();
  });

  it("连续3天以上显示暖色", async () => {
    (api.stats as ReturnType<typeof vi.fn>).mockResolvedValue({
      total: 1, not_mastered: 1, learning: 0, mastered: 0,
      due_today: 0, streak: 5, today_new: 0,
    });
    render(<StatsView onReview={onReview} />);
    await waitFor(() => {
      const el = screen.getByText(/5 天/);
      expect(el).toHaveStyle({ color: "var(--amber)" });
    });
  });
});

// ── ExplainPop ────────────────────────────────────────────────────────────────
describe("ExplainPop", () => {
  beforeEach(() => vi.clearAllMocks());

  const mockExplainData = {
    explain:   "【词性】形容词\n【IPA】/ɪˈfem.ər.əl/\n【谐音】伊(yi)-费(fei)-默(mo)-啊(a)\n【核心含义】短暂的\n【语法要点】常搭配beauty/life\n【例句】Beauty is ephemeral. → 美丽是短暂的。",
    pronounce: "【IPA】/ɪˈfem.ər.əl/\n【谐音】伊(yi)-费(fei)-默(mo)-啊(a)\n【重音】第二音节\n【记忆口诀】记住伊费默啊",
    phonetic_xieyin: "伊(yi)-费(fei)-默(mo)-啊(a)",
  };

  it("默认显示解释 tab", async () => {
    (api.explain as ReturnType<typeof vi.fn>).mockResolvedValue(mockExplainData);
    render(<ExplainPop word="ephemeral" contextSentence="" translation="短暂的" />);
    await waitFor(() => expect(screen.getByText(/形容词/)).toBeInTheDocument());
    expect(screen.getByText(/核心含义/)).toBeInTheDocument();
  });

  it("切换到发音 tab 显示重音和口诀", async () => {
    (api.explain as ReturnType<typeof vi.fn>).mockResolvedValue(mockExplainData);
    render(<ExplainPop word="ephemeral" contextSentence="" translation="短暂的" />);
    await waitFor(() => screen.getByText(/解释/));

    await userEvent.click(screen.getByText(/发音/));
    await waitFor(() => expect(screen.getByText(/第二音节/)).toBeInTheDocument());
    expect(screen.getByText(/记住伊费默啊/)).toBeInTheDocument();
  });

  it("API 失败时显示错误信息", async () => {
    (api.explain as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("DeepSeek timeout"));
    render(<ExplainPop word="ephemeral" contextSentence="" translation="短暂的" />);
    await waitFor(() => expect(screen.getByText(/DeepSeek timeout/)).toBeInTheDocument());
  });

  it("单词和翻译显示在 header", async () => {
    (api.explain as ReturnType<typeof vi.fn>).mockResolvedValue(mockExplainData);
    render(<ExplainPop word="ephemeral" contextSentence="Beauty is ephemeral." translation="短暂的" />);
    expect(screen.getByText("ephemeral")).toBeInTheDocument();
    expect(screen.getByText("短暂的")).toBeInTheDocument();
  });
});
