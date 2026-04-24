from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os, time

load_dotenv(Path(__file__).parent / ".env")

PROMPT = """You are an English learning assistant. Explain the following English text for a Chinese learner.
ALL output must be in Chinese only — do NOT use English in any field except the IPA line and the example sentence itself.

Output in this EXACT format (no extra text):

【词性】<词性，用中文，如：形容词、动词>
【IPA】/<IPA transcription>/
【谐音】<用"汉字(拼音)"格式逐音节标注，如：伊(yi)-费(fei)-默(mo)-热(re)，拼音不标声调>
【核心含义】<一句中文简短解释>
【语法要点】<一条关键语法说明，纯中文>
【例句】<一个英文例句> → <中文翻译>"""

TEST_WORD = "ephemeral"

MODELS = [
    ("DeepSeek V4-pro", "deepseek-v4-pro",  "https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    ("DeepSeek V3",     "deepseek-chat",     "https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    ("GPT-4o",          "gpt-4o",            "https://api.openai.com/v1", "OPENAI_API_KEY"),
    ("GPT-4o-mini",     "gpt-4o-mini",       "https://api.openai.com/v1", "OPENAI_API_KEY"),
]

for label, model, base_url, key_env in MODELS:
    api_key = os.environ.get(key_env, "")
    if not api_key:
        print(f"\n{'='*55}")
        print(f"  {label}")
        print(f"{'='*55}")
        print(f"⚠️  跳过：.env 里没有 {key_env}")
        continue

    client = OpenAI(api_key=api_key, base_url=base_url)
    print(f"\n{'='*55}")
    print(f"  {label}  ({model})")
    print(f"{'='*55}")
    t0 = time.time()
    try:
        r = client.chat.completions.create(
            model=model, max_tokens=600,
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user",   "content": TEST_WORD},
            ],
        )
        print(r.choices[0].message.content)
        print(f"\n⏱ {time.time()-t0:.1f}s | tokens: {r.usage.total_tokens}")
    except Exception as e:
        print(f"❌ {e}")
