# AI Input Pad — Agent 操作卡

AI agent 进入此目录自动读取。无需用户重复说明背景。

## 核心文件

| 文件 | 职责 | 更新时机 |
|------|------|---------|
| `CONTEXT.md` | Why — 调研、背景、决策依据 | 重大决策时 |
| `DESIGN.md` | What — 业务澄清、技术架构、工程规范 | 加功能/改架构时 |
| `PLAN.md` | How — Phase 列表 + 验收标准 | 开始/完成 Phase 时 |

## 当前状态

- 阶段：Phase 0（模型验证）进行中，设计文件已完成
- 下一步：正式关闭 Phase 0，进入 Phase 1 Backend 实现
- 最近决策：模型选 DeepSeek V3，谐音改 CMU 数据库，blind_spot 改 CEFR 词频表

## 路径索引

```
/Users/cuijianchen/gh-projects/app-ai-input/
├── CONTEXT.md
├── DESIGN.md
├── PLAN.md
├── eval/scenarios.yaml     ← 验证过的生产 prompt
├── backend/                ← 待建，Phase 1
├── ui/                     ← 待建，Phase 4
└── .env                    ← API keys（gitignored）
```

- AI 测评工具：`/Users/cuijianchen/gh-projects/infra-model-eval/run.sh`
- 脚手架模板：`/Users/cuijianchen/gh-projects/infra-scaffold/`

## 技术栈

- 后端：Python FastAPI，localhost:8765
- 前端：Tauri v2 + React + TypeScript
- 系统层：Rust（enigo，快捷键 + 粘贴模拟）
- AI 模型：DeepSeek V3（`deepseek-chat`），key 在 `.env`
- 平台：macOS M1 + Windows 11

## Agent 行为约束

- 不修改 CONTEXT.md，除非用户明确要求
- 不修改 DESIGN.md 架构部分，除非用户明确要求
- 每个 Phase 完成后跑验收 checklist，通过才进下一个
- prompt 改动后必须跑 infra-model-eval 验证
- `.env` 不提交 git
- 文档和代码同一个 commit 提交
