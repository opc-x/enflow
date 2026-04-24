# PLAN — 执行计划

> 回答 How。AI agent 的操作手册。按阶段顺序执行，每阶段末尾跑验收 checklist 再继续。
> 架构决策见 DESIGN.md，背景决策见 CONTEXT.md。

---

## 前置条件

- [ ] Python 3.11+，`pip` 可用
- [ ] Node.js 20+，`pnpm` 可用
- [ ] Rust（`rustup`）已安装
- [ ] macOS：Xcode CLI Tools 已安装
- [ ] Windows：VS C++ Build Tools 已安装（PowerShell，非 WSL2）
- [ ] `.env` 已配置（DEEPSEEK_API_KEY，参考 `.env.example`）

---

## Phase 1：Backend

### 1.1 初始化

```bash
mkdir backend && cd backend
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn openai python-dotenv
pip freeze > requirements.txt
```

### 1.2 config.py

从 `.env` 读取，支持环境变量覆盖：

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
MODEL            = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
VOCAB_PATH       = Path(os.environ.get("VOCAB_PATH", "~/ai-input/vocab.json")).expanduser()
AUTO_CLOSE_MS    = int(os.environ.get("AUTO_CLOSE_MS", "12000"))
```

### 1.3 prompts.py

从 `eval/scenarios.yaml` 的 system 字段提取，这是唯一 prompt 来源：

- `PROMPT_CONVERT`：中英混输转英文
- `PROMPT_TRANSLATE_WORD/PHRASE/SENTENCE/PARAGRAPH`：翻译四种粒度
- `PROMPT_EXPLAIN_PRONOUNCE`：解释+发音合并（单次调用）

### 1.4 phonetics.py

CMU Pronouncing Dictionary + 音素→拼音映射表。
对外接口：`get_xieyin(word: str) -> str`，返回如 `"伊(yi)-费(fei)-默(mo)-热(re)"`。

```bash
pip install pronouncing  # CMU dict Python 封装
```

音素映射表内置在文件里（IH→伊yi, F→费fei, EH→默mo...），不调 AI。

### 1.5 vocab.py

- `load_vocab() / save_vocab()`：读写 `VOCAB_PATH`
- `is_blind_spot(word: str) -> bool`：查 A1+A2 词汇集合，不在里面就是盲点词
- `add_to_vocab(word, translation)`：判断盲点后写入
- `compute_stats(vocab) -> dict`
- `next_interval_days(correct_count) -> int`：SM-2 间隔 [1,3,7,14,30]
- `review_word(word, correct) -> datetime`：更新复习时间

A1+A2 词汇集合内置（约1500词），从 CEFR wordlist 导入。

### 1.6 ai.py

```python
from openai import OpenAI
from config import DEEPSEEK_API_KEY, MODEL
import prompts

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def call(system: str, user: str, max_tokens: int = 800) -> str: ...
def convert(text: str) -> str: ...
def translate(text: str) -> dict: ...          # 含 text_type
def explain_pronounce(text: str) -> dict: ...  # 含 explain, pronounce, phonetic_xieyin
```

`explain_pronounce` 流程：
1. 调 AI，用 `PROMPT_EXPLAIN_PRONOUNCE`
2. 调 `phonetics.get_xieyin(text)`
3. 用 CMU 谐音替换 AI 输出的【谐音】行
4. 返回合并结果

### 1.7 main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

@app.post("/convert")
@app.post("/translate")
@app.post("/explain")
@app.get("/vocab/stats")
@app.get("/vocab/due")
@app.post("/vocab/review")
```

### Phase 1 验收 ✅

```bash
python main.py  # 启动

# 逐一测试，全部通过才算完成：
curl -X POST http://127.0.0.1:8765/convert \
  -H "Content-Type: application/json" \
  -d '{"text":"我想 book a meeting"}'
# 期望：{"result":"I want to book a meeting."}

curl -X POST http://127.0.0.1:8765/translate \
  -d '{"text":"ephemeral"}'
# 期望：{"translation":"短暂的","text_type":"word"}

curl -X POST http://127.0.0.1:8765/explain \
  -d '{"text":"ephemeral"}'
# 期望：explain/pronounce 字段存在，phonetic_xieyin 是"汉字(拼音)"格式，无非拼音内容

curl http://127.0.0.1:8765/vocab/stats
# 期望：返回 JSON 含 total/due_today/streak 等字段
```

---

## Phase 2：Tauri 初始化

```bash
pnpm create tauri-app ui --template react-ts
cd ui
pnpm install
pnpm add @tauri-apps/plugin-global-shortcut \
         @tauri-apps/plugin-clipboard-manager \
         @tauri-apps/plugin-shell \
         @tauri-apps/api
```

`src-tauri/Cargo.toml` 添加：

```toml
tauri                           = { version = "2", features = ["tray-icon"] }
tauri-plugin-global-shortcut    = "2"
tauri-plugin-clipboard-manager  = "2"
tauri-plugin-shell              = "2"
enigo                           = "0.2"
```

### Phase 2 验收 ✅

```bash
pnpm tauri dev  # 能启动，无编译错误
```

---

## Phase 3：Tauri main.rs

职责：全局快捷键 + 子进程管理 + 剪贴板/粘贴模拟

```
快捷键 CmdOrCtrl+Alt+I → 显示 InputPad 窗口
快捷键 CmdOrCtrl+Alt+T →
  1. enigo 模拟 Cmd+C (Mac) / Ctrl+C (Win)
  2. sleep 150ms
  3. 读剪贴板
  4. 若有内容变化 → emit 事件给 TranslatePop 窗口

Tauri invoke "paste_text" →
  1. 写剪贴板
  2. enigo 模拟 Cmd+V (Mac) / Ctrl+V (Win)

系统托盘菜单：进展 / 复习 / 退出
```

### Phase 3 验收 ✅

- [ ] 按 CmdOrCtrl+Alt+I 弹出 InputPad 窗口
- [ ] 选中文字按 CmdOrCtrl+Alt+T 弹出 TranslatePop（先用 mock 文字测试）
- [ ] 调用 paste_text 能将文字粘贴到光标位置

---

## Phase 4：前端 React 组件

### api.ts

```typescript
const BASE = "http://127.0.0.1:8765"
export async function convert(text: string): Promise<{result: string}>
export async function translate(text: string): Promise<{translation: string, text_type: string}>
export async function explain(text: string): Promise<{explain: string, pronounce: string, phonetic_xieyin: string}>
export async function getVocabStats(): Promise<VocabStats>
export async function getVocabDue(): Promise<VocabEntry[]>
export async function reviewWord(word: string, correct: boolean): Promise<void>
```

### 组件规格

**InputPad**（560×110，屏幕中偏上）
- 输入框 + 状态文字
- Enter → 调 /convert → invoke paste_text → 关窗口
- Esc → 关窗口
- 按钮：学习进展 / 开始复习

**TranslatePop**（500×200，屏幕中）
- 原文（截断）+ 翻译结果
- 按钮：解释/发音（合并，点后展开 ExplainPop）
- 12秒自动关闭，点击/Esc 关闭

**ExplainPop**（520×360，屏幕中）
- Tab 切换：解释 | 发音
- 解释 tab：渲染【词性】【IPA】【谐音】等字段
- 发音 tab：渲染【IPA】【谐音（CMU）】【重音】等字段
- 点击任意处关闭

**ReviewSession** / **StatsView**：参考原 ai_input.py 逻辑迁移

### 样式规范

```css
--bg:      #1e1e1e
--bg2:     #2d2d2d
--fg:      #ffffff
--muted:   #888888
--green:   #4caf50
--amber:   #e0a030
--red:     #e05252
font: -apple-system, "Segoe UI", sans-serif  /* 平台自适应 */
```

### Phase 4 验收 ✅

- [ ] InputPad：输入中英混合，Enter 后英文出现在上一个聚焦的输入框
- [ ] TranslatePop：选词触发，显示翻译，12秒自动关
- [ ] ExplainPop：tab 切换解释/发音，谐音无非拼音内容
- [ ] 复习流程：显示词→输入中文→对错判断→下一个
- [ ] 进展面板：数据正确展示

---

## Phase 5：打包与自启动

### 打包 Backend（PyInstaller sidecar）

```bash
cd backend
pip install pyinstaller
pyinstaller --onefile --name ai_input_server main.py
```

配置到 `tauri.conf.json` 的 `bundle.resources`，Tauri 自动管理进程。

### macOS

```bash
pnpm tauri build  # 输出 .app
```

- 拖入 /Applications
- 系统设置 → 通用 → 登录项 → 添加
- 首次运行：授权辅助功能权限（enigo 需要）

### Windows（PowerShell 原生）

```bash
pnpm tauri build  # 输出 .msi
```

- 双击安装，自动写入开机自启注册表

### Phase 5 验收 ✅

- [ ] Mac：点击 .app 启动，快捷键正常，功能完整
- [ ] Windows：安装后重启，开机自动运行，功能完整

---

## 测试策略（两步走）

### Step A：后端接口验证（AI agent 可自闭环）

Phase 1 验收 checklist 全部通过即可。
用 curl / httpie 逐接口测试，覆盖正常路径和边界情况：
- 空字符串输入
- 超长文本（>200字）
- 特殊字符（@#$% 等）
- vocab.json 不存在时的初始化

### Step B：UI 集成验证（人工，点一遍）

Phase 3+4 完成后，人工执行以下路径各一次：

```
关键路径 1：输入框
  打开 InputPad → 输入"我想 schedule a call" → Enter → 确认英文粘贴到目标位置

关键路径 2：翻译+解释
  在文本里选中"ephemeral" → 快捷键 → 看翻译弹窗 → 点"解释/发音" → 验证内容和格式

关键路径 3：生词本
  触发 5 次翻译（含盲点词）→ 打开进展面板 → 确认词汇数量正确

关键路径 4：复习
  确保有到期词 → 开始复习 → 走完一轮 → 确认对错更新
```

---

## 最终验收：README

**README 写清楚了 = 产品价值成立。** 最后一步更新 README，能对外讲清楚以下内容才算完成：

- [ ] 这是什么，解决什么问题
- [ ] 怎么安装（Mac + Windows 各一套步骤）
- [ ] 怎么用（快捷键 + 功能说明）
- [ ] 怎么配置（API key + 路径）

README 是最终验收把关，不能通过则说明功能或文档有缺失。
