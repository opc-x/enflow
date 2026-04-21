# Writer script — run once then delete
import os

content = r'''"""
AI Input Pad — 系统级中英混合输入 + 划词翻译 + 解释 + 发音 + 生词本 + 间隔复习
Ctrl+Alt+Space  -> 呼出输入框（中英混合 -> 英文）
Ctrl+Alt+Z      -> 翻译选中文字（英文 -> 中文弹窗）
"""

import tkinter as tk
import threading
import time
import json
import os
import datetime
import pyperclip
import keyboard
from openai import OpenAI

# ── 配置 ──────────────────────────────────────────────────────────────────
API_KEY       = "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"
HOTKEY_INPUT  = "ctrl+alt+space"
HOTKEY_TRANS  = "ctrl+alt+z"
MODEL         = "gpt-4o-mini"
VOCAB_PATH    = r"C:\Users\DEVTrump\zx-projects\agentic\vocab.json"
AUTO_CLOSE_MS = 12000
# ──────────────────────────────────────────────────────────────────────────

PROMPT_INPUT = (
    "You are an input assistant. The user types mixed Chinese-English text. "
    "Convert it into a single, natural, fluent English sentence or question. "
    "Output ONLY the English sentence — no explanation, no quotes, nothing extra."
)

PROMPT_TRANS_WORD = (
    "Translate the following single English word to Chinese. "
    "Output ONLY the Chinese translation — one word or short phrase, nothing extra."
)
PROMPT_TRANS_PHRASE = (
    "Translate the following English phrase to Chinese. "
    "Output ONLY the natural Chinese translation — no explanation, no quotes."
)
PROMPT_TRANS_SENTENCE = (
    "Translate the following English sentence to Chinese. "
    "Output ONLY the Chinese translation — natural, fluent, no explanation."
)
PROMPT_TRANS_PARAGRAPH = (
    "Translate the following English paragraph to Chinese. "
    "Output ONLY the Chinese translation — preserve structure, no explanation."
)

PROMPT_EXPLAIN = """You are an English learning assistant. Explain the following English text for a Chinese learner.

Output in this EXACT format (no extra text):

【词性】<part of speech in Chinese>
【IPA】/<IPA transcription>/
【谐音】<Chinese syllable approximation, e.g. "康-缪-尼-凯特">
【核心含义】<one short Chinese sentence>
【语法要点】<one key grammar note in Chinese>
【例句】<one natural English example sentence> → <Chinese translation>

If the input is a phrase or sentence (not a single word), skip 【词性】【IPA】【谐音】 and start from 【核心含义】.
Only add ⚡【发音注意】<short note> if there is a notable connected speech feature."""

PROMPT_PRONUNCIATION = """You are a pronunciation coach for Chinese learners of English.

Output in this EXACT format:

【IPA】/<full IPA>/
【谐音】<syllable-by-syllable Chinese approximation>
【重音】<which syllable is stressed>

Only include lines below if they apply:
⚡【连读】<description if sounds link across word boundaries>
⚡【弱读】<description if a word is typically reduced>
⚡【吞音】<description if a sound is dropped>
⚡【变音】<description if a sound changes in context>

【记忆口诀】<a short memorable tip in Chinese>"""

PROMPT_BLIND_SPOT = """You are an English vocabulary judge.
The user is a Chinese adult learning English. They just looked up this word/phrase.

Word/Phrase: {word}
Translation shown: {translation}

Is this likely a vocabulary blind spot (something they don\'t truly know yet)?
Answer ONLY "yes" or "no".
- "yes" if B2 level or above, or has non-obvious usage
- "no" if extremely basic (A1/A2: the, is, I, you, hello, etc.)
- "no" if it\'s a proper noun"""

client = OpenAI(api_key=API_KEY)


def call_api(system_prompt: str, text: str, max_tokens: int = 800) -> str:
    r = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": text},
        ],
    )
    return r.choices[0].message.content.strip()


def detect_text_type(text: str) -> str:
    text = text.strip()
    words = text.split()
    if len(words) <= 1:
        return "word"
    if len(words) <= 5 and not text.endswith((".", "!", "?")):
        return "phrase"
    if "\n" in text or len(words) > 40:
        return "paragraph"
    return "sentence"


def get_trans_prompt(text: str) -> str:
    return {
        "word":      PROMPT_TRANS_WORD,
        "phrase":    PROMPT_TRANS_PHRASE,
        "sentence":  PROMPT_TRANS_SENTENCE,
        "paragraph": PROMPT_TRANS_PARAGRAPH,
    }[detect_text_type(text)]


# ── 生词本 ────────────────────────────────────────────────────────────────
def load_vocab() -> list:
    if not os.path.exists(VOCAB_PATH):
        return []
    try:
        with open(VOCAB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_vocab(vocab: list):
    os.makedirs(os.path.dirname(VOCAB_PATH), exist_ok=True)
    with open(VOCAB_PATH, "w", encoding="utf-8") as f:
        json.dump(vocab, f, ensure_ascii=False, indent=2)


def add_to_vocab(word: str, translation: str):
    try:
        prompt = PROMPT_BLIND_SPOT.format(word=word, translation=translation)
        answer = call_api(prompt, word, max_tokens=5).lower()
        if "yes" not in answer:
            return
        vocab = load_vocab()
        for entry in vocab:
            if entry.get("word", "").lower() == word.lower():
                entry["seen_count"] = entry.get("seen_count", 1) + 1
                entry["last_seen_time"] = datetime.datetime.now().isoformat()
                save_vocab(vocab)
                return
        now = datetime.datetime.now().isoformat()
        nrt = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        vocab.append({
            "word": word, "translation": translation,
            "first_seen_time": now, "last_seen_time": now,
            "seen_count": 1, "next_review_time": nrt,
            "correct_count": 0, "wrong_count": 0, "note": "",
        })
        save_vocab(vocab)
    except Exception:
        pass


# ── SM-2 ──────────────────────────────────────────────────────────────────
REVIEW_INTERVALS = [1, 3, 7, 14, 30]

def next_interval_days(correct_count: int) -> int:
    return REVIEW_INTERVALS[min(correct_count, len(REVIEW_INTERVALS) - 1)]


# ── 统计 ──────────────────────────────────────────────────────────────────
def compute_stats(vocab: list) -> dict:
    now = datetime.datetime.now()
    today_str = now.date().isoformat()
    total = len(vocab)
    not_mastered = learning = mastered = due_today = 0
    seen_dates = set()
    for e in vocab:
        try:
            seen_dates.add(datetime.datetime.fromisoformat(e["last_seen_time"]).date().isoformat())
        except Exception:
            pass
        cc = e.get("correct_count", 0)
        sc = e.get("seen_count", 1)
        if cc >= 3:
            mastered += 1
        elif sc >= 3 and cc / max(sc, 1) >= 0.6:
            learning += 1
        else:
            not_mastered += 1
        try:
            if datetime.datetime.fromisoformat(e["next_review_time"]) <= now:
                due_today += 1
        except Exception:
            due_today += 1
    streak = 0
    check = now.date()
    while check.isoformat() in seen_dates:
        streak += 1
        check -= datetime.timedelta(days=1)
    today_new = sum(1 for e in vocab if e.get("first_seen_time", "")[:10] == today_str)
    return dict(total=total, not_mastered=not_mastered, learning=learning,
                mastered=mastered, due_today=due_today, streak=streak, today_new=today_new)


# ── App ───────────────────────────────────────────────────────────────────
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.input_win = None
        self.trans_win = None
        self._trans_auto_close_id = None

    # ── 输入框 ────────────────────────────────────────────────────────────
    def show_input(self):
        if self.input_win and self.input_win.winfo_exists():
            self.input_win.lift()
            self.entry.focus_force()
            return
        w = self.input_win = tk.Toplevel(self.root)
        w.title("AI Input")
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.configure(bg="#1e1e1e")
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        w.geometry(f"560x110+{(sw-560)//2}+{sh//3}")

        self.input_status = tk.StringVar(value="输入中英混合  →  Enter 翻译    Esc 关闭")
        tk.Label(w, textvariable=self.input_status, fg="#888888", bg="#1e1e1e",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(6, 0))
        self.entry = tk.Entry(w, font=("Segoe UI", 15), bd=0,
                              bg="#2d2d2d", fg="#ffffff", insertbackground="#ffffff",
                              relief="flat")
        self.entry.pack(fill=tk.X, padx=10, pady=(4, 6))
        self.entry.focus_force()
        self.entry.bind("<Return>", self._input_submit)
        self.entry.bind("<Escape>", lambda e: self._close_input())

        btn_frame = tk.Frame(w, bg="#1e1e1e")
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        bs = dict(bg="#2d2d2d", fg="#aaaaaa", font=("Segoe UI", 9),
                  bd=0, relief="flat", cursor="hand2", padx=8, pady=3)
        tk.Button(btn_frame, text="📊 学习进展",
                  command=lambda: self.root.after(0, self.show_stats), **bs).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="🔁 开始复习",
                  command=lambda: self.root.after(0, self.show_review), **bs).pack(side=tk.LEFT, padx=(6,0))

    def _close_input(self):
        if self.input_win and self.input_win.winfo_exists():
            self.input_win.destroy()
        self.input_win = None

    def _input_submit(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.config(state="disabled")
        self.input_status.set("处理中...")
        threading.Thread(target=self._do_input, args=(text,), daemon=True).start()

    def _do_input(self, text):
        try:
            result = call_api(PROMPT_INPUT, text)
            self.root.after(0, lambda: self._input_done(result, None))
        except Exception as e:
            self.root.after(0, lambda: self._input_done(None, str(e)))

    def _input_done(self, result, error):
        if error:
            self.input_status.set(f"出错: {error[:60]}")
            self.entry.config(state="normal")
            return
        self._close_input()
        threading.Thread(target=self._paste, args=(result,), daemon=True).start()

    def _paste(self, text):
        time.sleep(0.2)
        pyperclip.copy(text)
        keyboard.send("ctrl+v")

    # ── 翻译弹窗 ──────────────────────────────────────────────────────────
    def show_translation(self):
        for k in ("ctrl", "alt", "z"):
            keyboard.release(k)
        time.sleep(0.1)
        old = pyperclip.paste()
        keyboard.send("ctrl+c")
        time.sleep(0.25)
        text = pyperclip.paste().strip()
        if not text or text == old:
            return
        threading.Thread(target=self._do_trans, args=(text,), daemon=True).start()

    def _do_trans(self, text):
        try:
            result = call_api(get_trans_prompt(text), text)
            self.root.after(0, lambda: self._show_trans_popup(text, result, None))
            threading.Thread(target=add_to_vocab, args=(text, result), daemon=True).start()
        except Exception as e:
            self.root.after(0, lambda: self._show_trans_popup(text, None, str(e)))

    def _show_trans_popup(self, original, result, error):
        if self.trans_win and self.trans_win.winfo_exists():
            self.trans_win.destroy()
        self._cancel_autoclose()

        w = self.trans_win = tk.Toplevel(self.root)
        w.title("翻译")
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.configure(bg="#1e1e1e")
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        w.geometry(f"500x200+{(sw-500)//2}+{sh//2}")

        orig_short = original if len(original) <= 60 else original[:60] + "..."
        tk.Label(w, text=orig_short, fg="#666666", bg="#1e1e1e",
                 font=("Segoe UI", 9), wraplength=478, justify="left"
                 ).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Frame(w, bg="#333333", height=1).pack(fill=tk.X, padx=12)

        content = result if result else f"出错: {error}"
        fg = "#ffffff" if result else "#ff6b6b"
        tk.Label(w, text=content, fg=fg, bg="#1e1e1e",
                 font=("Segoe UI", 13), wraplength=476, justify="left"
                 ).pack(anchor="w", padx=12, pady=(8, 6))

        btn_frame = tk.Frame(w, bg="#1e1e1e")
        btn_frame.pack(fill=tk.X, padx=12, pady=(0, 6))
        bs = dict(bg="#2d2d2d", fg="#cccccc", font=("Segoe UI", 10),
                  bd=0, relief="flat", cursor="hand2", padx=10, pady=4)

        def on_explain():
            self._cancel_autoclose()
            threading.Thread(target=self._do_explain, args=(original,), daemon=True).start()

        def on_pronunciation():
            self._cancel_autoclose()
            threading.Thread(target=self._do_pronunciation, args=(original,), daemon=True).start()

        tk.Button(btn_frame, text="📖 解释", command=on_explain, **bs).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="🔊 发音", command=on_pronunciation,
                  **bs).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(w, text="点击任意处关闭", fg="#555555", bg="#1e1e1e",
                 font=("Segoe UI", 8)).pack(anchor="e", padx=12, pady=(0, 6))

        self._trans_auto_close_id = w.after(AUTO_CLOSE_MS,
            lambda: w.destroy() if w.winfo_exists() else None)
        w.bind("<Button-1>", lambda e: self._close_trans())
        w.bind("<Escape>", lambda e: self._close_trans())

    def _cancel_autoclose(self):
        if self._trans_auto_close_id:
            try:
                self.root.after_cancel(self._trans_auto_close_id)
            except Exception:
                pass
            self._trans_auto_close_id = None

    def _close_trans(self):
        self._cancel_autoclose()
        if self.trans_win and self.trans_win.winfo_exists():
            self.trans_win.destroy()
        self.trans_win = None

    # ── 解释弹窗 ──────────────────────────────────────────────────────────
    def _do_explain(self, text):
        try:
            result = call_api(PROMPT_EXPLAIN, text, max_tokens=600)
            self.root.after(0, lambda: self._show_content_popup("解释", text, result, error=None))
        except Exception as e:
            self.root.after(0, lambda: self._show_content_popup("解释", text, None, error=str(e)))

    # ── 发音弹窗 ──────────────────────────────────────────────────────────
    def _do_pronunciation(self, text):
        try:
            result = call_api(PROMPT_PRONUNCIATION, text, max_tokens=400)
            self.root.after(0, lambda: self._show_content_popup("发音", text, result, error=None))
        except Exception as e:
            self.root.after(0, lambda: self._show_content_popup("发音", text, None, error=str(e)))

    def _show_content_popup(self, title: str, original: str, result, error):
        w = tk.Toplevel(self.root)
        w.title(title)
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.configure(bg="#1e1e1e")
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        w.geometry(f"520x320+{(sw-520)//2}+{sh//2 - 80}")

        tk.Label(w, text=original[:80], fg="#666666", bg="#1e1e1e",
                 font=("Segoe UI", 9), wraplength=496, justify="left"
                 ).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Frame(w, bg="#333333", height=1).pack(fill=tk.X, padx=12)

        content = result if result else f"出错: {error}"
        fg = "#e8e8e8" if result else "#ff6b6b"
        txt = tk.Text(w, font=("Segoe UI", 11), bg="#1e1e1e", fg=fg,
                      bd=0, relief="flat", wrap=tk.WORD, height=11,
                      padx=12, cursor="arrow")
        txt.insert("1.0", content)
        txt.config(state="disabled")
        txt.pack(fill=tk.BOTH, expand=True, pady=8)

        tk.Label(w, text="点击任意处关闭", fg="#555555", bg="#1e1e1e",
                 font=("Segoe UI", 8)).pack(anchor="e", padx=12, pady=(0, 8))
        w.bind("<Button-1>", lambda e: w.destroy())
        w.bind("<Escape>", lambda e: w.destroy())

    # ── 复习弹窗 ──────────────────────────────────────────────────────────
    def show_review(self):
        vocab = load_vocab()
        now = datetime.datetime.now()
        due = [e for e in vocab if self._is_due(e, now)]
        if not due:
            self._show_msg("复习", "🎉 没有待复习的词了！")
            return
        self._review_session(due, vocab, 0)

    def _is_due(self, entry, now):
        try:
            return datetime.datetime.fromisoformat(entry["next_review_time"]) <= now
        except Exception:
            return True

    def _review_session(self, due, vocab, idx):
        if idx >= len(due):
            self._show_msg("复习完成", f"✅ 本次复习 {len(due)} 个词\n继续加油！")
            return
        entry = due[idx]
        word = entry.get("word", "")
        translation = entry.get("translation", "")

        w = tk.Toplevel(self.root)
        w.title(f"复习 {idx+1}/{len(due)}")
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.configure(bg="#1e1e1e")
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        w.geometry(f"480x220+{(sw-480)//2}+{sh//2 - 80}")

        tk.Label(w, text=f"第 {idx+1} / {len(due)} 词", fg="#888888", bg="#1e1e1e",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(12, 0))
        tk.Label(w, text=word, fg="#ffffff", bg="#1e1e1e",
                 font=("Segoe UI", 20, "bold")).pack(pady=(8, 4))
        tk.Label(w, text="输入中文意思（不会就留空）", fg="#888888", bg="#1e1e1e",
                 font=("Segoe UI", 9)).pack()

        ans_var = tk.StringVar()
        ans_entry = tk.Entry(w, textvariable=ans_var, font=("Segoe UI", 13),
                             bg="#2d2d2d", fg="#ffffff", insertbackground="#ffffff",
                             bd=0, relief="flat")
        ans_entry.pack(fill=tk.X, padx=16, pady=8)
        ans_entry.focus_force()

        def submit(event=None):
            ans = ans_var.get().strip()
            w.destroy()
            correct = bool(ans and (ans in translation or translation in ans or ans == translation))
            self._review_result(word, translation, correct, due, vocab, idx)

        ans_entry.bind("<Return>", submit)
        tk.Button(w, text="确认", command=submit,
                  bg="#3a3a3a", fg="#ffffff", font=("Segoe UI", 11),
                  bd=0, relief="flat", cursor="hand2", padx=16, pady=4).pack(pady=4)

    def _review_result(self, word, translation, correct, due, vocab, idx):
        now = datetime.datetime.now()
        for entry in vocab:
            if entry.get("word", "").lower() == word.lower():
                if correct:
                    entry["correct_count"] = entry.get("correct_count", 0) + 1
                    days = next_interval_days(entry["correct_count"])
                else:
                    entry["wrong_count"] = entry.get("wrong_count", 0) + 1
                    days = 1
                entry["next_review_time"] = (now + datetime.timedelta(days=days)).isoformat()
                entry["last_seen_time"] = now.isoformat()
                break
        save_vocab(vocab)

        w = tk.Toplevel(self.root)
        w.title("结果")
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.configure(bg="#1e1e1e")
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        w.geometry(f"400x160+{(sw-400)//2}+{sh//2 - 60}")

        icon, color, msg = ("✅", "#4caf50", "答对了！") if correct else ("❌", "#ff6b6b", "答错了")
        tk.Label(w, text=f"{icon} {msg}", fg=color, bg="#1e1e1e",
                 font=("Segoe UI", 16, "bold")).pack(pady=(20, 4))
        tk.Label(w, text=f"{word}  →  {translation}", fg="#cccccc", bg="#1e1e1e",
                 font=("Segoe UI", 12)).pack(pady=4)

        def next_word():
            w.destroy()
            self.root.after(100, lambda: self._review_session(due, vocab, idx + 1))

        tk.Button(w, text="下一个 →", command=next_word,
                  bg="#3a3a3a", fg="#ffffff", font=("Segoe UI", 11),
                  bd=0, relief="flat", cursor="hand2", padx=16, pady=4).pack(pady=12)
        w.bind("<Return>", lambda e: next_word())

    # ── 进展可视化 ────────────────────────────────────────────────────────
    def show_stats(self):
        vocab = load_vocab()
        s = compute_stats(vocab)

        w = tk.Toplevel(self.root)
        w.title("📊 学习进展")
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.configure(bg="#1e1e1e")
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        w.geometry(f"420x340+{(sw-420)//2}+{sh//2 - 130}")

        def lbl(text, fg="#cccccc", size=11, bold=False):
            f = ("Segoe UI", size, "bold") if bold else ("Segoe UI", size)
            tk.Label(w, text=text, fg=fg, bg="#1e1e1e", font=f, anchor="w").pack(fill=tk.X, padx=20, pady=2)

        lbl("📊 学习进展", fg="#ffffff", size=14, bold=True)
        tk.Frame(w, bg="#333333", height=1).pack(fill=tk.X, padx=20, pady=6)

        lbl("今日概览", fg="#888888", size=9)
        lbl(f"今日新增  {s['today_new']} 个生词", fg="#ffffff")
        tk.Frame(w, bg="#2a2a2a", height=1).pack(fill=tk.X, padx=20, pady=4)

        lbl("生词掌握度", fg="#888888", size=9)
        lbl(f"共 {s['total']} 词", fg="#aaaaaa")

        total = s["total"] or 1
        bar_outer = tk.Frame(w, bg="#2d2d2d", height=14)
        bar_outer.pack(fill=tk.X, padx=20, pady=4)
        for ratio, color in [
            (s["not_mastered"]/total, "#e05252"),
            (s["learning"]/total,     "#e0a030"),
            (s["mastered"]/total,     "#4caf50"),
        ]:
            w2 = max(int(380 * ratio), 1 if ratio > 0 else 0)
            if w2 > 0:
                tk.Frame(bar_outer, bg=color, width=w2, height=14).pack(side=tk.LEFT)

        lbl(f"🔴 未掌握 {s['not_mastered']}  🟡 学习中 {s['learning']}  🟢 已掌握 {s['mastered']}",
            fg="#aaaaaa", size=10)
        tk.Frame(w, bg="#2a2a2a", height=1).pack(fill=tk.X, padx=20, pady=4)

        due_color = "#f0c040" if s["due_today"] > 0 else "#aaaaaa"
        lbl(f"今日待复习  {s['due_today']} 个词", fg=due_color)
        if s["due_today"] > 0:
            def start_review():
                w.destroy()
                self.root.after(100, self.show_review)
            tk.Button(w, text="▶ 开始复习", command=start_review,
                      bg="#3a3a3a", fg="#ffffff", font=("Segoe UI", 10),
                      bd=0, relief="flat", cursor="hand2", padx=12, pady=3
                      ).pack(anchor="w", padx=20, pady=2)

        tk.Frame(w, bg="#2a2a2a", height=1).pack(fill=tk.X, padx=20, pady=4)
        streak_color = "#f0a030" if s["streak"] >= 3 else "#aaaaaa"
        lbl(f"🔥 连续学习  {s['streak']} 天", fg=streak_color)

        tk.Label(w, text="点击任意处关闭", fg="#555555", bg="#1e1e1e",
                 font=("Segoe UI", 8)).pack(anchor="e", padx=12, pady=(4, 8))
        w.bind("<Button-1>", lambda e: w.destroy())
        w.bind("<Escape>", lambda e: w.destroy())

    # ── 通用消息弹窗 ──────────────────────────────────────────────────────
    def _show_msg(self, title, msg):
        w = tk.Toplevel(self.root)
        w.title(title)
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.configure(bg="#1e1e1e")
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        w.geometry(f"360x120+{(sw-360)//2}+{sh//2}")
        tk.Label(w, text=msg, fg="#ffffff", bg="#1e1e1e",
                 font=("Segoe UI", 12), wraplength=330, justify="center").pack(expand=True)
        w.bind("<Button-1>", lambda e: w.destroy())
        w.bind("<Escape>", lambda e: w.destroy())
        w.after(4000, lambda: w.destroy() if w.winfo_exists() else None)

    # ── 主循环 ────────────────────────────────────────────────────────────
    def run(self):
        keyboard.add_hotkey(HOTKEY_INPUT, lambda: self.root.after(0, self.show_input))
        keyboard.add_hotkey(HOTKEY_TRANS, lambda: self.root.after(0, self.show_translation))
        print("AI Input started")
        print(f"  {HOTKEY_INPUT.upper()} = 输入框")
        print(f"  {HOTKEY_TRANS.upper()} = 翻译选中文字")
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
'''

target = "/mnt/c/Users/DEVTrump/ai-input/ai_input.py"
with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Written: {len(content)} chars to {target}")
