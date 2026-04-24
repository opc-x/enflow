# DESIGN — 做什么

> 回答 What。架构、模块边界、接口契约、数据模型。AI agent 按此实现，不自由发挥。

---

## 系统架构

```
用户
  │
  ▼
Tauri App（主进程，UI + 系统集成）
  │  启动时拉起，退出时 kill
  ▼
FastAPI Server（子进程，localhost:8765）
```

**两进程，用户无感知。** Tauri 负责窗口/快捷键/剪贴板/粘贴模拟，FastAPI 负责 AI 调用和数据。

---

## 模块清单

### Backend（Python FastAPI）

| 文件 | 职责 | 关键约束 |
|------|------|---------|
| `main.py` | 路由入口，CORS 配置 | 只绑 127.0.0.1:8765 |
| `prompts.py` | 所有 prompt 常量 | 唯一 prompt 来源，禁止在其他文件写 prompt |
| `ai.py` | DeepSeek API 调用封装 | 调用 prompts.py，不内联 prompt |
| `phonetics.py` | 谐音生成（CMU数据库，非AI） | 英语音素 → 汉语拼音规则映射 |
| `vocab.py` | 生词本 CRUD + SM-2 + CEFR判断 | vocab.json 本地文件 |
| `config.py` | 从 .env 读配置 | 无硬编码 key |

### Frontend（Tauri + React）

| 文件/目录 | 职责 |
|----------|------|
| `src-tauri/main.rs` | 全局快捷键、子进程管理、剪贴板模拟 |
| `src/api.ts` | 所有 HTTP 调用封装，统一错误处理 |
| `src/windows/InputPad.tsx` | 输入框窗口 |
| `src/windows/TranslatePop.tsx` | 翻译弹窗 |
| `src/windows/ExplainPop.tsx` | 解释+发音合并弹窗（tab切换） |
| `src/windows/ReviewSession.tsx` | 复习弹窗 |
| `src/windows/StatsView.tsx` | 学习进展弹窗 |

---

## API 契约

所有请求/响应均为 JSON，服务在 `http://127.0.0.1:8765`。

```
POST /convert
  body:    { "text": "我想 book a meeting" }
  returns: { "result": "I want to book a meeting." }

POST /translate
  body:    { "text": "ephemeral" }
  returns: { "translation": "短暂的", "text_type": "word" }

POST /explain
  body:    { "text": "ephemeral" }
  returns: {
    "explain": "【词性】...\n【IPA】...\n...",
    "pronounce": "【IPA】...\n【谐音】...\n...",
    "phonetic_xieyin": "伊(yi)-费(fei)-默(mo)-热(re)"  ← CMU 生成，替换 AI 谐音
  }

GET  /vocab/stats
  returns: { "total", "not_mastered", "learning", "mastered", "due_today", "streak", "today_new" }

GET  /vocab/due
  returns: [{ "word", "translation", "correct_count", ... }]

POST /vocab/review
  body:    { "word": "ephemeral", "correct": true }
  returns: { "next_review_time": "2026-05-01T..." }
```

**注意**：`/explain` 返回的 `phonetic_xieyin` 由 `phonetics.py`（CMU数据库）生成，覆盖 AI 在 explain prompt 中生成的谐音字段。前端展示时用此字段替换 【谐音】行。

---

## AI 调用设计

### 调用清单（共 3 种，不是 5 种）

| 功能 | endpoint | prompt | 模型 | 备注 |
|------|----------|--------|------|------|
| 输入转英文 | /convert | PROMPT_CONVERT | deepseek-chat | 用户主动触发 |
| 划词翻译 | /translate | PROMPT_TRANSLATE_* | deepseek-chat | 自动触发 |
| 解释+发音 | /explain | PROMPT_EXPLAIN_PRONOUNCE | deepseek-chat | 合并为一次调用 |

**已移除**：
- ~~blind_spot AI判断~~ → 改用 CEFR 词频表（`vocab.py` 静态判断）
- ~~explain 和 pronounce 分两次~~ → 合并为一次，前端 tab 切换

### prompt 位置

所有 prompt 在 `backend/prompts.py`，经 `eval/scenarios.yaml` 验证通过。

---

## 数据模型

### vocab.json（本地，~/ai-input/vocab.json）

```json
[
  {
    "word": "ephemeral",
    "translation": "短暂的",
    "first_seen_time": "2026-04-24T10:00:00",
    "last_seen_time": "2026-04-24T10:00:00",
    "seen_count": 1,
    "correct_count": 0,
    "wrong_count": 0,
    "next_review_time": "2026-04-25T10:00:00",
    "note": ""
  }
]
```

### SM-2 间隔

答对后间隔：1 → 3 → 7 → 14 → 30 天（按 correct_count 索引）
答错：重置为 1 天

### CEFR 盲点判断

`vocab.py` 内置 A1+A2 词汇集合（约 1500 词）。
翻译完成后：word 不在集合里 → 自动入库。
不调 AI，不增加延迟。

---

## 快捷键

| 操作 | Mac | Windows |
|------|-----|---------|
| 输入框 | Cmd+Option+I | Ctrl+Alt+I |
| 划词翻译 | Cmd+Option+T | Ctrl+Alt+T |

Tauri 使用 `CmdOrCtrl+Alt+I/T`，自动适配双平台。

---

## Prompt 与 Markdown 文件的关系

```
CLAUDE.md / CONTEXT.md / DESIGN.md / PLAN.md
    → 给 Claude Code（AI agent）读
    → 目的：让 agent 理解项目，正确执行任务

backend/prompts.py
    → 给 DeepSeek V3（业务 AI 模型）读
    → 目的：驱动业务功能

eval/scenarios.yaml
    → 给 infra-model-eval（测试工具）读
    → 目的：验证 prompts.py 效果

三者内容对应，但载体和受众不同。
prompts.py 是 scenarios.yaml 中 system prompt 的生产版本。
```
