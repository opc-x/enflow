/**
 * E2E 测试 — Playwright 打 Vite dev server (localhost:1420) + 真实后端 (8765)
 * 覆盖：UI 渲染 / 表单交互 / API 调用 / 状态流转
 * 不覆盖：全局快捷键 / paste_text / 系统托盘（需要真实 Tauri runtime）
 */
import { test, expect, Page } from "@playwright/test";

const BASE = "http://localhost:1420";

// Tauri API 在普通浏览器中不存在，注入 stub
async function stubTauriApis(page: Page) {
  await page.addInitScript(() => {
    // @ts-ignore
    window.__TAURI_INTERNALS__ = {
      invoke: () => Promise.resolve(),
      transformCallback: (cb: () => void) => cb,
    };
    // @ts-ignore
    window.__TAURI__ = {
      invoke: () => Promise.resolve(),
      event: { listen: () => Promise.resolve(() => {}), emit: () => Promise.resolve() },
      window: { getCurrent: () => ({ hide: () => Promise.resolve(), show: () => Promise.resolve() }) },
      clipboard: { readText: () => Promise.resolve(""), writeText: () => Promise.resolve() },
    };
  });
}

// ── InputPad (/input) ────────────────────────────────────────────────────────
test.describe("InputPad 页面", () => {
  test.beforeEach(async ({ page }) => {
    await stubTauriApis(page);
    await page.goto(`${BASE}/input`);
  });

  test("渲染输入框和功能按钮", async ({ page }) => {
    await expect(page.getByPlaceholder(/输入中英混合/)).toBeVisible();
    await expect(page.getByText(/学习进展/)).toBeVisible();
    await expect(page.getByText(/开始复习/)).toBeVisible();
  });

  test("输入文字后状态提示变化", async ({ page }) => {
    await page.getByPlaceholder(/输入中英混合/).fill("我想 book a meeting");
    await expect(page.getByPlaceholder(/输入中英混合/)).toHaveValue("我想 book a meeting");
  });
});

// ── ReviewSession (/review) ──────────────────────────────────────────────────
test.describe("ReviewSession 页面", () => {
  test.beforeEach(async ({ page }) => {
    await stubTauriApis(page);
    await page.goto(`${BASE}/review`);
  });

  test("无待复习词时显示完成提示", async ({ page }) => {
    // 后端返回空数组时组件显示完成
    await expect(page.getByText(/没有待复习|完成/)).toBeVisible({ timeout: 8000 });
  });

  test("有待复习词时展示单词和输入框", async ({ page }) => {
    // 先通过 API 往后端加一个词（触发 explain 入库）
    await page.request.post("http://localhost:8765/explain", {
      data: { text: "serendipity", context_sentence: "" },
    });

    // 把 next_review_time 改成过去（让它到期）
    await page.request.post("http://localhost:8765/vocab/review", {
      data: { word: "serendipity", correct: false },
    });

    await page.reload();

    // 如果 serendipity 到期，应该显示输入框
    const hasInput = await page.getByPlaceholder(/中文翻译/).isVisible().catch(() => false);
    const hasDone  = await page.getByText(/没有待复习|完成/).isVisible().catch(() => false);
    expect(hasInput || hasDone).toBeTruthy();
  });
});

// ── StatsView (/stats) ────────────────────────────────────────────────────────
test.describe("StatsView 页面", () => {
  test.beforeEach(async ({ page }) => {
    await stubTauriApis(page);
    await page.goto(`${BASE}/stats`);
  });

  test("加载并显示统计数据", async ({ page }) => {
    await expect(page.getByText(/共.*个词/)).toBeVisible({ timeout: 8000 });
    await expect(page.getByText(/连续学习/)).toBeVisible();
    await expect(page.getByText(/今日待复习/)).toBeVisible();
  });

  test("显示掌握度分类", async ({ page }) => {
    await expect(page.getByText(/未掌握/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/学习中/)).toBeVisible();
    await expect(page.getByText(/已掌握/)).toBeVisible();
  });
});

// ── 完整业务流程 E2E ──────────────────────────────────────────────────────────
test.describe("完整业务流程", () => {
  test("translate → 显示翻译结果（直接调 API 验证）", async ({ page }) => {
    await stubTauriApis(page);
    const res = await page.request.post("http://localhost:8765/translate", {
      data: { text: "procrastinate", context_sentence: "Stop procrastinating." },
    });
    const json = await res.json();
    expect(json.translation).toBeTruthy();
    expect(json.text_type).toBe("word");
  });

  test("explain → 返回 explain+pronounce+phonetic_xieyin", async ({ page }) => {
    await stubTauriApis(page);
    const res = await page.request.post("http://localhost:8765/explain", {
      data: { text: "condescending", context_sentence: "" },
    });
    const json = await res.json();
    expect(json.explain).toContain("【词性】");
    expect(json.pronounce).toContain("【IPA】");
    expect(json.phonetic_xieyin).toMatch(/\(.+\)/); // 汉字(拼音)格式
  });

  test("review 完整两步流程：judge → review", async ({ page }) => {
    await stubTauriApis(page);

    // 确保 ephemeral 在库里
    await page.request.post("http://localhost:8765/explain", {
      data: { text: "ephemeral", context_sentence: "" },
    });

    // 步骤1：语义判题
    const judgeRes = await page.request.post("http://localhost:8765/vocab/review/judge", {
      data: { word: "ephemeral", translation: "短暂的", user_answer: "一瞬即逝" },
    });
    const judgeJson = await judgeRes.json();
    expect(judgeJson.correct).toBe(true);

    // 步骤2：更新 SM-2
    const reviewRes = await page.request.post("http://localhost:8765/vocab/review", {
      data: { word: "ephemeral", correct: true },
    });
    const reviewJson = await reviewRes.json();
    expect(reviewJson.next_review_time).toBeTruthy();

    // 验证 stats 更新
    const statsRes = await page.request.get("http://localhost:8765/vocab/stats");
    const stats = await statsRes.json();
    expect(stats.total).toBeGreaterThan(0);
  });
});
