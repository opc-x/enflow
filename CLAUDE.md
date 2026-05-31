# enflow (AI Input Pad) — Agent 操作卡

系统级英文输入辅助工具，面向中文母语者：中英混打转地道英文、划词翻译、解释/发音、生词本 + SM-2 间隔复习。平台 macOS 13+ / Windows 11。

## 架构

```
Tauri app（主进程，Rust+React）── 启动时拉起 ──▶ FastAPI（子进程，localhost:8765）
  全局快捷键 / 剪贴板 / 窗口 / 托盘                AI 调用 / 生词本 / 复习
  退出 Tauri → 自动 kill 后端
```

## 模块职责（改前先认人）

| 路径 | 职责 |
|------|------|
| `backend/main.py` | FastAPI 入口 + 全部路由，端口 8765 |
| `backend/ai.py` | DeepSeek API 封装；**禁止内联 prompt** |
| `backend/prompts.py` | 所有 prompt 唯一来源，内容同 `eval/scenarios.yaml` |
| `backend/phonetics.py` | 谐音：CMU 音素库 + 规则映射（非 AI） |
| `backend/vocab.py` | 生词本 CRUD + SM-2 + CEFR A1/A2 盲点过滤（非 AI） |
| `backend/config.py` | 从根目录 `.env` 读配置 |
| `ui/src/` | React + TS：窗口组件 + `api.ts`(后端调用) |
| `ui/src-tauri/` | Rust：进程管理、快捷键、剪贴板 |

## API 端点

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/convert` `/translate` `/explain` | 转换 / 翻译 / 解释+发音 |
| GET | `/vocab/stats` `/vocab/due` | 进展 / 待复习 |
| POST | `/vocab/review` `/vocab/review/judge` | 复习提交 / AI 判分 |

## 命令

| 动作 | 命令 |
|------|------|
| 后端开发 | `cd backend && pip install -r requirements.txt && python main.py` |
| 前端开发 | `cd ui && pnpm install && pnpm tauri dev`（后端需单独跑） |
| 前端单测 | `cd ui && pnpm test`（vitest） |
| 前端 e2e | `cd ui && pnpm playwright test`（用例在 `src/test/e2e`） |
| 打包 | `cd ui && pnpm tauri build`（打包后自动管理后端子进程） |

## 配置

- 全部走根目录 `.env`（gitignored）：`DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL`(默认 deepseek-chat) / `VOCAB_PATH` / `AUTO_CLOSE_MS`
- 快捷键在 `ui/src-tauri/tauri.conf.json`，默认 `CmdOrCtrl+Alt+I`(输入) / `CmdOrCtrl+Alt+T`(翻译)

## 关键决策（详见 CONTEXT.md）

| 选型 | 原因 |
|------|------|
| 模型 DeepSeek V3 | 质量持平 GPT-4.1，价格 1/9，0.5-2s |
| 谐音用 CMU 库非 AI | AI 谐音准确率仅 60-70% |
| 盲点用 CEFR 词频表非 AI | AI 判断不稳（"the"被判盲点），改静态表零延迟 |
| UI 用 Tauri 非 tkinter | tkinter 在 Mac 视觉差；Tauri ~30MB 原生渲染 |

## 文档分工

| 文件 | 答 | 改动时机 |
|------|----|---------|
| `CONTEXT.md` | Why（背景/决策） | 重大决策时，否则勿动 |
| `DESIGN.md` | What（架构/规范） | 加功能/改架构，架构部分勿擅动 |
| `PLAN.md` | How（Phase + 验收） | 起/完成 Phase 时 |

## Agent 行为约束

- 改 prompt 后必须跑 `infra-model-eval` 验证（脚本：`/Users/cuijianchen/gh-projects/infra-model-eval/run.sh`）
- 每个 Phase 完成跑验收 checklist，过了才进下一个
- `.env` 不提交；文档与代码同一 commit
- 遗留 Windows 版（`ai_input.py` `run.bat` `start.vbs` 等）已弃用，仅供参考，勿改

## 状态

- Phase 0（模型验证）已完成；Backend 路由 + 前端组件已就位
- 注意：CONTEXT/old-CLAUDE 中旧路径名 `app-ai-input` = 现 `enflow`，同一项目
