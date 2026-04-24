"""
快速验证 DeepSeek V4 效果，对比 V3
运行: python test_model.py
"""
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
import os, time

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)

PROMPT_EXPLAIN = """You are an English learning assistant. Explain the following English text for a Chinese learner.
ALL output must be in Chinese only — do NOT use English in any field except the IPA line and the example sentence itself.

Output in this EXACT format (no extra text):

【词性】<词性，用中文，如：形容词、动词>
【IPA】/<IPA transcription>/
【谐音】<用"汉字(拼音)"格式逐音节标注，如：伊(yi)-费(fei)-默(mo)-热(re)，拼音不标声调>
【核心含义】<一句中文简短解释>
【语法要点】<一条关键语法说明，纯中文>
【例句】<一个英文例句> → <中文翻译>"""

TEST_WORD = "ephemeral"

def test(model: str):
    print(f"\n{'='*50}")
    print(f"模型: {model}")
    print(f"{'='*50}")
    t0 = time.time()
    try:
        r = client.chat.completions.create(
            model=model,
            max_tokens=600,
            messages=[
                {"role": "system", "content": PROMPT_EXPLAIN},
                {"role": "user", "content": TEST_WORD},
            ],
        )
        elapsed = time.time() - t0
        print(r.choices[0].message.content)
        print(f"\n⏱ 耗时: {elapsed:.1f}s | tokens: {r.usage.total_tokens}")
    except Exception as e:
        print(f"❌ 失败: {e}")

if __name__ == "__main__":
    print(f"测试词: {TEST_WORD}")
    test("deepseek-v4")
    test("deepseek-chat")   # V3 对比
