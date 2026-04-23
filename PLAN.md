# PLAN — AI Input Pad 重构执行计划

> 本文件供 AI agent 落地执行参考。执行前请确认环境就绪（见"前置条件"），按阶段顺序执行，每阶段完成后验收再进入下一阶段。

---

## 目标

将原 Windows 单文件 tkinter 版本（`ai_input.py`）重构为：

- **后端**：Python FastAPI，跑在本地 `localhost:8765`，提供 AI 调用和生词本管理
- **UI**：Tauri v2 + React + TypeScript，跨平台原生窗口，负责全局快捷键和所有界面
- **平台支持**：macOS 13+（Apple Silicon）、Windows 11

---

## 技术选型（已定）

| 层 | 技术 | 理由 |
|----|------|------|
| UI 框架 | **Tauri v2 + React + TypeScript** | Tauri 官方模板和社区案例以 React 为主，生态最全 |
| 后端 | **Python FastAPI** | 原有 AI/vocab 逻辑直接迁移，成本最低 |
| 进程模型 | **两进程，用户无感知** | Tauri 启动时拉起 FastAPI 子进程，退出时一并 kill |
| 键盘模拟 | **enigo crate（Rust）** | 跨平台，Mac/Win 均可模拟 Cmd+C/V 和 Ctrl+C/V |
| 快捷键 | **CmdOrCtrl+Alt+I / CmdOrCtrl+Alt+T** | Mac=Cmd+Option，Win=Ctrl+Alt，物理键相同，无系统冲突 |

**Windows 开发环境**：必须用 **PowerShell 或 Windows Terminal 原生环境**，禁止在 WSL2 内运行任何本项目进程。WSL2 的 Linux 内核无法注册 Windows 全局热键、无法可靠操作 Windows 剪贴板，会导致核心功能完全失效。

## 前置条件

执行 agent 开始前请确认：

- [ ] Python 3.11+，`pip` 可用
- [ ] Node.js 20+，`pnpm` 可用
- [ ] Rust 工具链（`rustup`）已安装，`cargo` 可用
- [ ] macOS：Xcode Command Line Tools 已安装
- [ ] Windows：Visual Studio C++ Build Tools 已安装（**在 PowerShell 中确认，不是 WSL2**）
- [ ] OpenAI API Key 已准备好（用于填入 `backend/config.py`）

---

## 目录结构（目标）

```
app-ai-input/
├── backend/
│   ├── main.py            # FastAPI 入口，挂载所有路由
│   ├── ai.py              # OpenAI 调用封装（translate / explain / pronounce / blind_spot）
│   ├── vocab.py           # 生词本 CRUD + SM-2 复习逻辑
│   ├── config.py          # 运行时配置（从环境变量或 config.local.py 读取）
│   ├── config.example.py  # 配置模板，提交到 git
│   └── requirements.txt
├── ui/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── windows/
│   │   │   ├── InputPad.tsx       # 输入框窗口
│   │   │   ├── TranslatePop.tsx   # 翻译弹窗
│   │   │   ├── ExplainPop.tsx     # 解释弹窗
│   │   │   ├── PronounPop.tsx     # 发音弹窗
│   │   │   ├── ReviewSession.tsx  # 复习弹窗
│   │   │   └── StatsView.tsx      # 进展弹窗
│   │   ├── api.ts                 # 封装所有后端 HTTP 调用
│   │   └── styles/
│   │       └── global.css
│   ├── src-tauri/
│   │   ├── src/
│   │   │   └── main.rs            # Tauri 入口：注册快捷键、管理后端子进程
│   │   ├── Cargo.toml
│   │   └── tauri.conf.json
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── README.md
└── PLAN.md
```

---

## API 契约

后端监听 `http://localhost:8765`，所有请求体和响应体均为 JSON。

### AI 端点

| 方法 | 路径 | 请求体 | 响应体 |
|------|------|--------|--------|
| POST | `/translate` | `{"text": str}` | `{"translation": str, "text_type": "word"\|"phrase"\|"sentence"\|"paragraph"}` |
| POST | `/explain` | `{"text": str}` | `{"result": str}` |
| POST | `/pronounce` | `{"text": str}` | `{"result": str}` |

### 生词本端点

| 方法 | 路径 | 请求体 | 响应体 |
|------|------|--------|--------|
| GET | `/vocab/stats` | — | `{"total": int, "not_mastered": int, "learning": int, "mastered": int, "due_today": int, "streak": int, "today_new": int}` |
| GET | `/vocab/due` | — | `[{word, translation, seen_count, correct_count, ...}]` |
| POST | `/vocab/review` | `{"word": str, "correct": bool}` | `{"next_review_time": str}` |
| POST | `/vocab/add` | `{"word": str, "translation": str}` | `{"added": bool}` |

---

## 阶段一：后端 FastAPI

### 1.1 初始化

```bash
mkdir backend && cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi uvicorn openai
pip freeze > requirements.txt
```

### 1.2 config.py

从原 `ai_input.py` 顶部常量迁移，支持环境变量覆盖：

```python
import os, pathlib

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL          = os.environ.get("AI_MODEL", "gpt-4o-mini")
VOCAB_PATH     = pathlib.Path(os.environ.get(
    "VOCAB_PATH",
    pathlib.Path.home() / "ai-input" / "vocab.json"
))
AUTO_CLOSE_MS  = int(os.environ.get("AUTO_CLOSE_MS", "12000"))
```

`config.example.py` 内容相同但 `OPENAI_API_KEY = "sk-..."` 留空，加入 `.gitignore`：`config.py`（不提交真实 key）。

### 1.3 ai.py

从 `ai_input.py` 提取以下函数，保持逻辑不变：

- `call_api(system_prompt, text, max_tokens) -> str`
- `detect_text_type(text) -> str`
- `get_trans_prompt(text) -> str`
- 所有 `PROMPT_*` 常量

### 1.4 vocab.py

从 `ai_input.py` 提取：

- `load_vocab()` / `save_vocab()`
- `add_to_vocab(word, translation)` — 注意：原版有 bug，`add_to_vocab` 里的过滤逻辑（正则过滤代码符号）只在 `ai_input.py` 主版本里有，`_write_ai_input.py` 里没有，以主版本为准
- `compute_stats(vocab)`
- `next_interval_days(correct_count)`
- SM-2 review update 逻辑（从 `_review_result` 中提取）

### 1.5 main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

# 挂载路由（见 API 契约）

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
```

### 1.6 验收

```bash
python main.py
curl -X POST http://localhost:8765/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "我想 book a flight"}'
# 期望返回 {"translation": "...", "text_type": "sentence"}

curl http://localhost:8765/vocab/stats
# 期望返回统计 JSON
```

---

## 阶段二：Tauri 项目初始化

### 2.1 创建项目

```bash
# 使用官方 React + TypeScript 模板
pnpm create tauri-app ui --template react-ts
cd ui
pnpm install
```

### 2.2 安装 Tauri 插件

```bash
pnpm add @tauri-apps/plugin-global-shortcut \
         @tauri-apps/plugin-clipboard-manager \
         @tauri-apps/plugin-shell \
         @tauri-apps/api
```

对应 `src-tauri/Cargo.toml` 添加：

```toml
[dependencies]
tauri          = { version = "2", features = ["tray-icon"] }
tauri-plugin-global-shortcut    = "2"
tauri-plugin-clipboard-manager  = "2"
tauri-plugin-shell              = "2"
enigo          = "0.2"   # 跨平台键盘/鼠标模拟（用于 Ctrl+C/V、Cmd+C/V）
```

### 2.3 tauri.conf.json 关键配置

```json
{
  "app": { "windows": [] },
  "bundle": {
    "active": true,
    "targets": "all",
    "resources": { "../backend/dist/ai_input_server": "." }
  },
  "plugins": {
    "global-shortcut": {},
    "shell": { "open": false, "sidecar": true }
  }
}
```

**进程管理策略：**
- 开发模式：手动先启动 `python backend/main.py`，再 `pnpm tauri dev`
- 生产打包：用 PyInstaller 将 FastAPI 打成单文件可执行，配置为 Tauri sidecar，Tauri 负责启停

---

## 阶段三：Tauri 主进程（main.rs）

### 3.1 职责

- 启动 Python FastAPI sidecar（生产模式）或跳过（开发模式手动启动）
- 注册全局快捷键：
  - `CmdOrCtrl+Alt+I` → 显示 InputPad 窗口
  - `CmdOrCtrl+Alt+T` → 触发划词翻译流程
- 管理多窗口（按需创建，不共用同一个 webview）
- 系统托盘：右键菜单含「学习进展」「开始复习」「退出」

> **快捷键说明**：Tauri 的 `CmdOrCtrl` 在 Mac 上映射为 `Cmd`，在 Windows 上映射为 `Ctrl`。最终效果：
> - Mac：`Cmd+Option+I` / `Cmd+Option+T`
> - Windows：`Ctrl+Alt+I` / `Ctrl+Alt+T`
> 两个平台物理按键位置相同，无系统级冲突。

### 3.2 划词翻译流程（main.rs 中处理）

```
CmdOrCtrl+Alt+T 触发
  → 用 enigo 模拟 Cmd+C（Mac）/ Ctrl+C（Win）
  → tokio::time::sleep(150ms)
  → 读剪贴板（tauri-plugin-clipboard-manager）
  → 若内容非空且与上次不同
      → 创建/显示 TranslatePop 窗口
      → 通过 Tauri event 将文本传给前端
      → 前端发起 POST /translate
```

> **Mac 权限**：`enigo` 在 Mac 上需要「辅助功能」授权，App 首次运行时引导用户在系统设置中开启。Windows 无需额外权限。

### 3.3 输入框粘贴流程（main.rs 中处理）

```
前端 InputPad 按 Enter
  → 前端调用 POST /translate → 拿到英文结果
  → 前端通过 Tauri invoke 调用 Rust 命令 `paste_text(text)`
  → Rust：写入剪贴板 + enigo 模拟 Cmd+V（Mac）/ Ctrl+V（Win）
  → InputPad 窗口关闭
```

### 3.4 进程生命周期

```rust
// 伪代码结构
fn main() {
    let sidecar = start_python_sidecar_if_production();
    
    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .setup(|app| {
            register_hotkeys(app);
            setup_tray(app);
            Ok(())
        })
        .on_window_event(|event| { /* 处理窗口关闭 */ })
        .run(tauri::generate_context!())
        .expect("error running tauri app");
    
    // Tauri 退出后 sidecar 自动随之终止（子进程）
}
```

---

## 阶段四：前端 UI

### 4.1 api.ts

封装所有后端调用，统一错误处理：

```typescript
const BASE = "http://127.0.0.1:8765";

export async function translate(text: string): Promise<{ translation: string; text_type: string }> { ... }
export async function explain(text: string): Promise<{ result: string }> { ... }
export async function pronounce(text: string): Promise<{ result: string }> { ... }
export async function getVocabStats(): Promise<VocabStats> { ... }
export async function getVocabDue(): Promise<VocabEntry[]> { ... }
export async function reviewWord(word: string, correct: boolean): Promise<void> { ... }
```

### 4.2 窗口组件

每个弹窗作为独立 Tauri 窗口或单一 webview 路由，根据实际情况选择：

- **InputPad**：560×110，屏幕居中偏上（1/3 处）
  - 输入框 + 状态文字 + 「进展」「复习」按钮
  - Enter 提交，Esc 关闭
- **TranslatePop**：500×200，屏幕居中
  - 原文（截断）+ 翻译结果 + 「解释」「发音」按钮
  - 12 秒自动关闭，点击关闭，Esc 关闭
  - 点「解释」/「发音」时取消自动关闭
- **ExplainPop / PronounPop**：520×320，弹出时取消父窗口自动关闭
- **ReviewSession**：480×220，逐词卡片 + 输入 + 确认
- **StatsView**：420×340，进度条 + 各项统计

### 4.3 样式规范

深色主题，所有窗口统一：

```css
--bg-primary:   #1e1e1e;
--bg-secondary: #2d2d2d;
--fg-primary:   #ffffff;
--fg-muted:     #888888;
--accent-red:   #e05252;
--accent-amber: #e0a030;
--accent-green: #4caf50;

font-family: -apple-system, "Segoe UI", sans-serif;  /* 平台自适应 */
```

---

## 阶段五：打包与自启动

### 打包 Python 后端

```bash
cd backend
pip install pyinstaller
pyinstaller --onefile --name ai_input_server main.py
# 输出：backend/dist/ai_input_server（Mac）/ ai_input_server.exe（Win）
```

将产物路径配置到 `tauri.conf.json` 的 `bundle.resources`，Tauri 打包时一并打入。

### macOS

- 打包：`pnpm tauri build` → 输出 `.app`
- 安装：拖入 `/Applications`
- 开机自启：系统设置 → 通用 → 登录项 → 添加该 `.app`
- 首次运行：系统会弹出辅助功能授权弹窗（`enigo` 需要），引导用户在「系统设置 → 隐私与安全性 → 辅助功能」中开启

### Windows（PowerShell 原生环境，非 WSL2）

- 打包：`pnpm tauri build` → 输出 `.msi` 或 `.exe`
- 安装：双击 `.msi` 安装
- 开机自启：安装包写入注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`（在 tauri.conf.json 中配置）
- 无需额外权限

---

## 已知 Bug（从原版迁移时修复）

1. `_capture_and_trans` 里 `keyboard.release("z")` 但热键已改为 `ctrl+alt+a` → **新版由 enigo 处理，此 bug 消除**
2. Mac 上 `ctrl+c/v` 应为 `cmd+c/v` → **新版 main.rs 按平台分支处理**
3. `VOCAB_PATH` 写死 Windows 路径 → **新版 config.py 用 `pathlib.Path.home()` 默认路径**
4. 字体 `Segoe UI` Mac 上不存在 → **新版 CSS 用 `-apple-system` fallback**
5. 原版 `show_translation` 旧代码在主线程 `time.sleep` → **新版架构中无此问题**

---

## 不做的事（范围边界）

- 不做云同步（vocab.json 保持本地文件）
- 不做 iOS / Android
- 不做多语言 UI（界面固定中文）
- 不做音频 TTS（发音只显示 IPA 和谐音，不播放）
- FastAPI 不对外网暴露，只绑定 127.0.0.1

---

## 执行顺序建议

```
阶段一（后端）→ 验收 API → 阶段二（Tauri 初始化）
→ 阶段三（main.rs 快捷键 + 粘贴）→ 阶段四（前端 UI）→ 阶段五（打包）
```

阶段一可以独立完成并完整测试，不依赖 UI。
