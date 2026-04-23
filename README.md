# AI Input Pad

系统级英文输入辅助工具，面向中文母语学习者。支持中英混合输入转英文、划词翻译、词汇解释、发音指导、生词本和间隔复习。

**支持平台：** macOS 13+（Apple Silicon / Intel）、Windows 11

## 功能概览

| 快捷键 | Mac | Windows | 功能 |
|--------|-----|---------|------|
| `Cmd+Option+I` | ✓ | — | 呼出输入框：中英混合文字 → AI 转地道英文 → 自动粘贴 |
| `Ctrl+Alt+I` | — | ✓ | 同上 |
| `Cmd+Option+T` | ✓ | — | 划词翻译：选中英文 → 弹窗显示中文翻译 |
| `Ctrl+Alt+T` | — | ✓ | 同上 |

翻译弹窗内还有两个按钮：
- **解释** — 词性、IPA、谐音、核心含义、语法要点、例句
- **发音** — IPA、谐音、重音、连读 / 弱读 / 吞音 / 变音提示、记忆口诀

## 生词本与间隔复习

翻译时 AI 自动判断是否为"盲点词"（B2 及以上或用法不显而易见），是则写入本地 `vocab.json`。

复习间隔（类 SM-2）：答对后 1 → 3 → 7 → 14 → 30 天，答错重置为 1 天。

可随时查看学习进展或开始复习（从输入框或托盘菜单进入）。

## 架构

```
用户点击图标
└── Tauri app 启动（主进程）
      └── 自动拉起 Python FastAPI（子进程，后台，用户无感知）

┌──────────────────────────────┐   HTTP/localhost:8765   ┌──────────────────────┐
│  Tauri v2 + React（主进程）   │ ──────────────────────▶│  FastAPI 后端（子进程）│
│  全局快捷键注册                │                        │  POST /translate      │
│  输入框 / 翻译弹窗              │◀────────────────────── │  POST /explain        │
│  生词本 / 复习 / 进展           │                        │  POST /pronounce      │
│  系统托盘                      │                        │  GET  /vocab/stats    │
└──────────────────────────────┘                        │  GET  /vocab/due      │
                                                        │  POST /vocab/review   │
                                                        └──────────────────────┘

退出 Tauri → 自动 kill FastAPI 子进程
```

- **UI**：Tauri v2 + React + TypeScript，负责窗口渲染、全局快捷键、剪贴板操作
- **后端**：Python FastAPI，负责 AI 调用、生词本 CRUD、SM-2 复习逻辑
- 用户只操作一个 app，进程管理由 Tauri 全权负责
- 闲置资源：~75MB RAM，~0% CPU（纯事件驱动）

## 目录结构

```
app-ai-input/
├── backend/
│   ├── main.py            # FastAPI 入口
│   ├── ai.py              # OpenAI 调用封装
│   ├── vocab.py           # 生词本 + SM-2 逻辑
│   ├── config.py          # 配置（不提交 git）
│   ├── config.example.py  # 配置模板
│   └── requirements.txt
├── ui/
│   ├── src/               # React + TypeScript
│   │   ├── windows/       # 各弹窗组件
│   │   └── api.ts         # 后端 HTTP 调用封装
│   ├── src-tauri/         # Tauri 配置 + Rust 入口（进程管理、快捷键、剪贴板）
│   └── package.json
├── README.md
└── PLAN.md
```

## 安装与运行

### 前置依赖

| 依赖 | Mac | Windows |
|------|-----|---------|
| Python 3.11+ | `brew install python` | python.org 下载安装 |
| Node.js 20+ | `brew install node` | nodejs.org 下载安装 |
| pnpm | `npm i -g pnpm` | `npm i -g pnpm` |
| Rust | `curl https://sh.rustup.rs \| sh` | `winget install Rustlang.Rustup` |
| Xcode CLI Tools | `xcode-select --install` | — |

> **Windows 注意**：用 **PowerShell 或 Windows Terminal（原生）** 运行所有命令，不要在 WSL2 里操作。WSL2 无法访问 Windows 全局快捷键和剪贴板，会导致核心功能失效。

### 后端

```bash
cd backend
pip install -r requirements.txt
cp config.example.py config.py   # 填入 OpenAI API Key 和 vocab 路径
python main.py                   # 开发时单独启动验证
```

### UI（开发模式）

```bash
cd ui
pnpm install
pnpm tauri dev    # 自动启动前端 + Tauri，后端需单独跑
```

### 打包（生产）

```bash
cd ui
pnpm tauri build  # 输出 .app（Mac）或 .msi/.exe（Windows）
# 打包后 Tauri 会自动管理 FastAPI 子进程，无需手动启动后端
```

## 配置

编辑 `backend/config.py`：

```python
OPENAI_API_KEY = "sk-..."
MODEL          = "gpt-4o-mini"
VOCAB_PATH     = "~/ai-input/vocab.json"   # 支持 ~ 展开
AUTO_CLOSE_MS  = 12000
```

快捷键在 `ui/src-tauri/tauri.conf.json` 中修改，默认为 `CmdOrCtrl+Alt+I` / `CmdOrCtrl+Alt+T`。

## 遗留文件（Windows 原版）

`ai_input.py`、`run.bat`、`install_startup.bat`、`start.vbs` 是原 Windows tkinter 版本，已被新架构取代，保留仅供参考。
