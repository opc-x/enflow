# AI Input Pad — Agent Context

AI agent 进入此项目目录时自动读取本文件。无需用户重复说明背景。

## 三个核心文件，必须先读

| 文件 | 回答什么 | 优先级 |
|------|---------|-------|
| `CONTEXT.md` | 为什么做，关键决策依据 | 先读 |
| `DESIGN.md` | 做什么，架构和模块设计 | 再读 |
| `PLAN.md` | 怎么做，执行步骤和验收标准 | 执行时读 |

## 当前状态

- 阶段：设计完成，后端和 UI 尚未实现
- 下一步：按 PLAN.md Phase 1 开始实现 backend/

## 快速关键信息

- 主语言：Python（后端）+ TypeScript/React（前端）+ Rust（Tauri 层）
- AI 模型：DeepSeek V3（`deepseek-chat`），API key 在 `.env`
- 跨平台：macOS M1 + Windows 11
- 测评工具：`~/gh-projects/infra-model-eval/`（独立项目）
- 验证过的 prompt：`eval/scenarios.yaml`

## Agent 执行规范

- 每完成一个 PLAN.md 阶段，跑对应验收 checklist
- prompt 改动后必须跑 `infra-model-eval` 验证
- 不改 CONTEXT.md 和 DESIGN.md，除非用户明确要求
- `.env` 不提交，key 从环境变量读
