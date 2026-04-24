# DESIGN — 做什么

> 回答 What。业务功能、架构、模块边界、接口契约、数据模型。AI agent 按此实现，不自由发挥。
> 更新时机：加功能、改模块边界、API 变化、数据结构变化。

---

## 产品功能清单

| # | 功能 | 触发方式 | 说明 |
|---|------|---------|------|
| 1 | **输入框** | Cmd+Option+I / Ctrl+Alt+I | 弹窗输入中英混合 → AI 转地道英文 → 自动粘贴到光标 |
| 2 | **划词翻译** | Cmd+Option+T / Ctrl+Alt+T | 选中英文 → 弹窗显示中文翻译，12秒自动关 |
| 3 | **解释** | 翻译弹窗点按钮 | 词性/**IPA（主）**/谐音（CMU近似参考）/核心含义/语法要点/例句，结合上下文句子 |
| 4 | **发音** | 解释弹窗 tab 切换 | **IPA（主）**/谐音（CMU近似）/重音/连读/弱读/吞音/发音陷阱/记忆口诀 |
| 5 | **生词自动入库** | 点击"解释"时触发 | A1/A2 词排除，其余入 vocab.json |
| 6 | **间隔复习** | 托盘菜单 / 输入框按钮 | SM-2调度，AI语义判断对错 |
| 7 | **学习进展** | 托盘菜单 / 输入框按钮 | 词数/掌握度/连续天数/今日新词 |
| 8 | **系统托盘** | 后台常驻 | 右键菜单：进展/复习/退出 |

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
| `vocab.py` | 生词本 CRUD + SM-2 + 入库判断 | vocab.json 本地文件 |
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
  body:    { "text": "ephemeral", "context_sentence": "Beauty is ephemeral." }
  returns: { "translation": "短暂的", "text_type": "word" }
  注意：context_sentence 可选，有则传入 prompt 提升解释准确性

POST /explain
  body:    { "text": "ephemeral", "context_sentence": "Beauty is ephemeral." }
  returns: {
    "explain": "【词性】...\n【IPA】...\n...",
    "pronounce": "【IPA】...\n【谐音】...\n...",
    "phonetic_xieyin": "伊(yi)-费(fei)-默(mo)-热(re)"
  }
  注意：phonetic_xieyin 由 phonetics.py（CMU）生成，前端替换 AI 的【谐音】行

POST /vocab/review/judge
  body:    { "word": "ephemeral", "translation": "短暂的", "user_answer": "短暂" }
  returns: { "correct": true, "feedback": "意思正确，标准答案：短暂的" }
  注意：AI 语义判断，非字符串比对。"短暂"和"短暂的"都算对

GET  /vocab/stats
  returns: { "total", "not_mastered", "learning", "mastered", "due_today", "streak", "today_new" }

GET  /vocab/due
  returns: [{ "word", "translation", "correct_count", ... }]

POST /vocab/review
  body:    { "word": "ephemeral", "correct": true }
  returns: { "next_review_time": "2026-05-01T..." }
```

---

## AI 调用设计

### 调用清单（共 4 种）

| 功能 | endpoint | 模型 | 备注 |
|------|----------|------|------|
| 输入转英文 | /convert | deepseek-chat | 用户主动触发 |
| 划词翻译 | /translate | deepseek-chat | 传 context_sentence 提升质量 |
| 解释+发音 | /explain | deepseek-chat | 合并一次调用，传 context_sentence |
| 复习判题 | /vocab/review/judge | deepseek-chat | **语义匹配**，非字符串比对 |

所有 prompt 在 `backend/prompts.py`，经 `eval/scenarios.yaml` 验证通过。

### v2 预留：TTS 音频（Azure Neural TTS）

v1 用 IPA + 文字描述连读/弱读，是无音频约束下的最优解。
v2 接入 Azure TTS（神经网络语音），实现：
- 单词发音播放（自然语调）
- 例句整句播放（真实连读/弱读/吞音）
- 双通道编码（视觉+听觉），记忆强度质的提升

接口预留：`POST /tts { "text": str, "speed": float }` → 返回 base64 音频

### Prompt 位置

```
CLAUDE/CONTEXT/DESIGN/PLAN  → 给 Claude Code（agent）读，构建项目用
backend/prompts.py          → 给 DeepSeek V3 读，驱动业务功能
eval/scenarios.yaml         → 给 infra-model-eval 读，验证 prompt 效果
```

---

## 数据模型

### vocab.json（~/ai-input/vocab.json）

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

### 生词入库判断（vocab.py）

A1/A2 词汇集合（约 1500 词）内置，不在集合里 → 自动入库。
B1 词（despite / whereas 等）也会入库，后续通过复习频次自然淘汰掌握的词。

### SM-2 复习间隔

答对后间隔：1 → 3 → 7 → 14 → 30 天（按 correct_count 索引）
答错：重置为 1 天

### 复习判题

不做字符串比对，调 AI 做语义判断：
- "短暂" = "短暂的" → correct
- "一瞬即逝" = "短暂的" → correct
- "永恒的" = "短暂的" → wrong

---

## 快捷键

| 操作 | Mac | Windows |
|------|-----|---------|
| 输入框 | Cmd+Option+I | Ctrl+Alt+I |
| 划词翻译 | Cmd+Option+T | Ctrl+Alt+T |

Tauri 使用 `CmdOrCtrl+Alt+I/T`，自动适配双平台。

---

## 工程规范（业务侧）

- 所有 prompt 只在 `prompts.py` 定义，其他文件不内联 prompt
- API 只绑 127.0.0.1，不对外暴露
- vocab.json 路径从 config 读，不硬编码
- context_sentence 始终从前端剪贴板上下文提取并传入，不可省略（有则传，无则传空字符串）
- 谐音由 phonetics.py（CMU）生成，AI prompt 中的【谐音】字段仅作格式占位，前端以 CMU 结果覆盖，禁止直接展示 AI 生成的谐音
- IPA 是发音的主要载体，UI 大字显示；谐音是近似辅助，UI 小字标注"近似参考"
- 发音陷阱（⚡【发音陷阱】）：仅当含 th音、词末辅音群、长短元音关键区别时触发，其余省略
