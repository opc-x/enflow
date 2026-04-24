# CONTEXT — 为什么这么做

> 回答 Why。供 AI agent 和未来的自己理解决策背景。只记结论和因果，不记过程。

---

## 问题是什么

中文母语者在英文工作环境中有两个高频痛点：

1. **输入摩擦**：脑子里是中文，打出来要地道英文，来回切换输入法+翻译工具打断思路
2. **学习低效**：阅读时遇到生词，查完就忘，没有复习机制

现有工具（翻译 App、词典）都是独立的，没有系统级集成，每次都要切换上下文。

---

## 用户是谁

- 中文母语，成人，英文工作环境（读写为主）
- 每天大量打字，高频查词
- 想学英文，但不想专门坐下来"学"，要嵌入工作流
- 同时用 Mac（M1，macOS Sequoia）和 Windows 11

---

## 核心诉求（按优先级）

1. 中英混打 → 自动转地道英文，直接粘贴，不打断输入节奏
2. 划词翻译 → 弹窗显示，不用切换 App
3. 顺手学 → 翻译时自动记录生词，间隔复习
4. 跨平台一致 → Mac 和 Win 体验相同，快捷键一样

---

## 关键技术决策

### AI 模型：DeepSeek V3（deepseek-chat）
- 经过 infra-model-eval 完整测评（见 `eval/scenarios.yaml`）
- 在发音重音准确率上与 GPT-4.1 持平，语法要点质量略好
- 价格是 GPT-4o 的 1/9，速度更快（0.5-2s）
- 淘汰原因：GPT-4o-mini（格式字段缺失）、GPT-4.1-nano（格式不稳定）、DeepSeek V4-pro（40s延迟不可接受）

### 谐音：CMU 音素库 + 规则映射（非 AI 生成）
- AI 生成谐音准确率约 60-70%，音节数量和拼音格式均不稳定
- 英语音素 → 汉语拼音是确定性映射，用数据库 100% 准确
- 工具：CMU Pronouncing Dictionary + 自建音素-拼音映射表

### 盲点判断：CEFR 词频表（非 AI 判断）
- 原设计用 AI 判断每个词是否是盲点，每次翻译额外调一次 API
- AI 判断不稳定（测评发现 "the" 被判为 yes 的 bug）
- 改用静态词频表（CEFR A1/A2 词汇约 1500 词），不在列表里的自动入库
- 零 API 调用，零延迟，100% 确定性

### explain + pronounce：合并为单次调用
- 原设计两个按钮各触发一次 API
- 合并：一次调用返回解释和发音，前端用 tab 切换展示
- 减少用户等待次数

### UI 框架：Tauri v2 + React（非 tkinter）
- 原版 tkinter 在 Mac 上无原生字体、无圆角、Segoe UI 缺失
- Tauri：原生窗口，Mac/Win 各自 native 渲染，bundle 体积小（~30MB vs Electron ~200MB）
- 全局快捷键和键盘模拟（enigo crate）在 Rust 层处理，跨平台一致

### 快捷键：CmdOrCtrl+Alt+I / CmdOrCtrl+Alt+T
- Mac：Cmd+Option+I / T，Windows：Ctrl+Alt+I / T，物理键位相同
- 经过系统级冲突排查，两平台均无占用

### 进程模型：两进程，用户无感知
- Tauri 启动时自动拉起 Python FastAPI（sidecar），退出时一并 kill
- 用户只点一个 App 图标，闲置内存约 75MB，CPU 约 0%

---

## 试过但淘汰的方案

| 方案 | 淘汰原因 |
|------|---------|
| tkinter UI | Mac 上视觉效果差，字体/窗口系统问题 |
| `keyboard` Python 库 | Mac 需要辅助功能权限且不稳定，改用 Tauri + enigo |
| AI 生成谐音 | 准确率不足，改用 CMU 数据库 |
| AI 盲点判断 | 不稳定，改用 CEFR 词频表 |
| DeepSeek V4-pro | 推理模型，延迟 40s，实时场景不可用 |
| GPT-4o-mini | explain 场景格式字段缺失 |
| WSL2 运行 | 无法访问 Windows 系统级热键和剪贴板 |

---

## v1 边界

**包含：**
- 输入框（中英混打转英文）
- 划词翻译弹窗
- 解释+发音合并弹窗（tab 切换）
- 生词本自动入库（CEFR 判断）
- SM-2 间隔复习
- 学习进展统计
- 系统托盘

**不包含（v1 砍掉）：**
- 音频 TTS（只显示 IPA+谐音，不播放）
- 云同步（vocab.json 本地文件）
- iOS / Android
- 多语言 UI
