"""
DeepSeek API 调用封装。所有 prompt 来自 prompts.py，此文件不内联任何 prompt。
"""
import re
import asyncio
from openai import AsyncOpenAI
from config import DEEPSEEK_API_KEY, MODEL
import prompts
from phonetics import get_xieyin

client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

_TRANSLATE_PROMPTS = {
    "word":      prompts.PROMPT_TRANSLATE_WORD,
    "phrase":    prompts.PROMPT_TRANSLATE_PHRASE,
    "sentence":  prompts.PROMPT_TRANSLATE_SENTENCE,
    "paragraph": prompts.PROMPT_TRANSLATE_PARAGRAPH,
}

_CONTRACTIONS = {
    "you're": {
        "expanded": "you are",
        "translation": "你是 / 你正在",
        "ipa": "/jʊr/（快读也常弱化成 /jər/）",
        "xieyin": "优(you)-儿(er)",
        "grammar": "这是 you are 的缩写，后面通常接形容词、名词或现在分词。",
        "example": "You're right. → 你是对的。",
        "note": "先发“优”，结尾用轻短的儿化音收住，不要读成“屋”。",
    },
    "i'm": {
        "expanded": "I am",
        "translation": "我是 / 我正在",
        "ipa": "/aɪm/",
        "xieyin": "爱(ai)-姆(mu)",
        "grammar": "这是 I am 的缩写，口语中比 I am 更自然。",
        "example": "I'm ready. → 我准备好了。",
        "note": "结尾 /m/ 双唇闭合收音，不要加很重的“木”。",
    },
    "can't": {
        "expanded": "cannot",
        "translation": "不能",
        "ipa": "/kænt/",
        "xieyin": "看(kan)-特(te)",
        "grammar": "这是 cannot 的缩写，表示不能或不可能。",
        "example": "I can't go. → 我不能去。",
        "note": "词尾 /t/ 很轻，重点和 can 区分开。",
    },
    "don't": {
        "expanded": "do not",
        "translation": "不 / 不要",
        "ipa": "/doʊnt/",
        "xieyin": "东(dong)-特(te)",
        "grammar": "这是 do not 的缩写，用于一般现在时否定或祈使句否定。",
        "example": "Don't worry. → 别担心。",
        "note": "中间是双元音 /oʊ/，词尾 /t/ 轻收。",
    },
}


async def _call(system: str, user: str, max_tokens: int = 800) -> str:
    r = await client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return r.choices[0].message.content.strip()


def _detect_type(text: str) -> str:
    text = text.strip()
    words = text.split()
    if len(words) <= 1:
        return "word"
    if len(words) <= 5 and not text.endswith((".", "!", "?")):
        return "phrase"
    if "\n" in text or len(words) > 40:
        return "paragraph"
    return "sentence"


def _lookup_contraction(text: str) -> dict | None:
    key = text.strip().lower().replace("’", "'")
    key = re.sub(r"^[^a-z']+|[^a-z']+$", "", key)
    return _CONTRACTIONS.get(key)


def _replace_xieyin_line(ai_output: str, cmu_xieyin: str) -> str:
    """把 AI 输出的【谐音】行替换为 CMU 谐音"""
    if not cmu_xieyin:
        return ai_output
    return re.sub(r"【谐音】.*", f"【谐音】{cmu_xieyin}", ai_output)


async def convert(text: str) -> str:
    return await _call(prompts.PROMPT_CONVERT, text, max_tokens=80)


async def translate(text: str, context_sentence: str = "") -> dict:
    text_type = _detect_type(text)
    if text_type == "word":
        contraction = _lookup_contraction(text)
        if contraction:
            return {"translation": contraction["translation"], "text_type": "word"}

    user_msg = text
    if context_sentence:
        user_msg = f"{text}\n[context: {context_sentence}]"
    result = await _call(_TRANSLATE_PROMPTS[text_type], user_msg, max_tokens=150)
    return {"translation": result, "text_type": text_type}


async def explain_pronounce(text: str, context_sentence: str = "") -> dict:
    contraction = _lookup_contraction(text)
    if contraction:
        explain = (
            "【词性】缩约形式\n"
            f"【IPA】{contraction['ipa']}\n"
            f"【谐音】{contraction['xieyin']}\n"
            f"【核心含义】{contraction['expanded']}，{contraction['translation']}\n"
            f"【语法要点】{contraction['grammar']}\n"
            f"【例句】{contraction['example']}"
        )
        pronounce = (
            f"【IPA】{contraction['ipa']}\n"
            f"【谐音】{contraction['xieyin']}\n"
            "【重音】单音节词，正常语流中通常不重读\n"
            f"⚡【发音陷阱】{contraction['note']}\n"
            f"【记忆口诀】看到缩写先还原成 {contraction['expanded']}，再按口语快读处理。"
        )
        return {
            "explain": explain,
            "pronounce": pronounce,
            "phonetic_xieyin": contraction["xieyin"],
        }

    user_msg = text
    if context_sentence:
        user_msg = f"{text} [context: {context_sentence}]"

    # 并发调 explain 和 pronounce，同时获取 CMU 谐音
    explain_task  = _call(prompts.PROMPT_EXPLAIN,   user_msg, max_tokens=800)
    pronounce_task = _call(prompts.PROMPT_PRONOUNCE, text,     max_tokens=600)
    explain_raw, pronounce_raw = await asyncio.gather(explain_task, pronounce_task)

    # CMU 谐音替换（仅单词有效）
    xieyin = get_xieyin(text) if _detect_type(text) == "word" else ""
    explain_final  = _replace_xieyin_line(explain_raw,  xieyin)
    pronounce_final = _replace_xieyin_line(pronounce_raw, xieyin)

    return {
        "explain":        explain_final,
        "pronounce":      pronounce_final,
        "phonetic_xieyin": xieyin,
    }


async def judge(word: str, translation: str, user_answer: str) -> dict:
    user_msg = f"word={word} | standard={translation} | answer={user_answer}"
    raw = await _call(prompts.PROMPT_REVIEW_JUDGE, user_msg, max_tokens=50)

    correct = "verdict: correct" in raw.lower()
    feedback = ""
    m = re.search(r"feedback:\s*(.+)", raw, re.IGNORECASE)
    if m:
        feedback = m.group(1).strip()
    if not feedback and not correct:
        feedback = f"标准答案：{translation}"

    return {"correct": correct, "feedback": feedback}
