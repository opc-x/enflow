#!/usr/bin/env python3
"""
infra-model-eval — 场景化多模型测评工具
用法:
    python eval.py                        # 测所有模型 + 所有场景
    python eval.py --scenario explain     # 只测 explain 场景
    python eval.py --model gpt-4o        # 只测指定模型
    python eval.py --scenario explain --model gpt-4o,deepseek-chat
"""
import argparse, json, os, sys, time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

from scenarios import SCENARIOS

# ── 模型注册表 ────────────────────────────────────────────────────────────
MODELS = [
    {"id": "gpt-4o",          "label": "GPT-4o",          "base_url": "https://api.openai.com/v1",  "key_env": "OPENAI_API_KEY",   "reasoning": False},
    {"id": "gpt-4o-mini",     "label": "GPT-4o-mini",     "base_url": "https://api.openai.com/v1",  "key_env": "OPENAI_API_KEY",   "reasoning": False},
    {"id": "gpt-4.1",         "label": "GPT-4.1",         "base_url": "https://api.openai.com/v1",  "key_env": "OPENAI_API_KEY",   "reasoning": False},
    {"id": "gpt-4.1-mini",    "label": "GPT-4.1-mini",    "base_url": "https://api.openai.com/v1",  "key_env": "OPENAI_API_KEY",   "reasoning": False},
    {"id": "deepseek-chat",   "label": "DeepSeek V3",     "base_url": "https://api.deepseek.com",   "key_env": "DEEPSEEK_API_KEY", "reasoning": False},
    {"id": "deepseek-v4-pro", "label": "DeepSeek V4-pro", "base_url": "https://api.deepseek.com",   "key_env": "DEEPSEEK_API_KEY", "reasoning": True},
]

# ── 工具函数 ──────────────────────────────────────────────────────────────
def get_client(model_cfg: dict) -> OpenAI | None:
    key = os.environ.get(model_cfg["key_env"], "")
    if not key:
        return None
    return OpenAI(api_key=key, base_url=model_cfg["base_url"])


def run_one(client: OpenAI, model_id: str, system: str, user: str,
            max_tokens: int, is_reasoning: bool) -> dict:
    effective_max = max_tokens * 6 if is_reasoning else max_tokens
    t0 = time.time()
    r = client.chat.completions.create(
        model=model_id,
        max_tokens=effective_max,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    elapsed = time.time() - t0
    msg = r.choices[0].message
    content = (msg.content or "").strip()
    reasoning = getattr(msg, "reasoning_content", None)
    return {
        "content":          content,
        "reasoning_chars":  len(reasoning) if reasoning else 0,
        "elapsed_s":        round(elapsed, 1),
        "total_tokens":     r.usage.total_tokens,
        "finish_reason":    r.choices[0].finish_reason,
    }


def sep(char="=", n=60): return char * n


# ── 主逻辑 ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="逗号分隔的场景 id，默认全部")
    parser.add_argument("--model",    help="逗号分隔的模型 id，默认全部")
    parser.add_argument("--save",     action="store_true", default=True,
                        help="保存结果到 results/ 目录（默认开启）")
    args = parser.parse_args()

    wanted_scenarios = set(args.scenario.split(",")) if args.scenario else None
    wanted_models    = set(args.model.split(","))    if args.model    else None

    scenarios = [s for s in SCENARIOS if not wanted_scenarios or s["id"] in wanted_scenarios]
    models    = [m for m in MODELS    if not wanted_models    or m["id"] in wanted_models]

    if not scenarios:
        print("没有匹配的场景"); sys.exit(1)
    if not models:
        print("没有匹配的模型"); sys.exit(1)

    all_results = {"timestamp": datetime.now().isoformat(), "runs": []}
    report_lines = [f"# Model Eval Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]

    for scenario in scenarios:
        print(f"\n{sep()}")
        print(f"  场景: {scenario['name']}  [{scenario['id']}]")
        print(sep())
        report_lines.append(f"\n## 场景: {scenario['name']}\n")

        for case in scenario["cases"]:
            print(f"\n  输入: 「{case}」")
            print(f"  {sep('-', 56)}")
            report_lines.append(f"\n### 输入: `{case}`\n")

            for model_cfg in models:
                client = get_client(model_cfg)
                label = model_cfg["label"]

                if not client:
                    print(f"  [{label}] ⚠️  缺少 {model_cfg['key_env']}，跳过")
                    continue

                print(f"\n  [{label}]")
                try:
                    res = run_one(
                        client, model_cfg["id"],
                        scenario["system"], case,
                        scenario["max_tokens"], model_cfg["reasoning"],
                    )
                    output = res["content"] if res["content"] else "(空输出)"
                    print(output)
                    meta = f"  ⏱ {res['elapsed_s']}s | tokens: {res['total_tokens']}"
                    if res["reasoning_chars"]:
                        meta += f" | 推理: {res['reasoning_chars']} chars"
                    print(meta)

                    report_lines.append(f"**{label}** ⏱{res['elapsed_s']}s / {res['total_tokens']} tokens\n")
                    report_lines.append(f"```\n{output}\n```\n")

                    all_results["runs"].append({
                        "scenario": scenario["id"],
                        "case": case,
                        "model": model_cfg["id"],
                        "model_label": label,
                        **res,
                    })

                except Exception as e:
                    print(f"  ❌ {e}")
                    report_lines.append(f"**{label}** ❌ `{e}`\n")

    # ── 保存结果 ──────────────────────────────────────────────────────────
    if args.save:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_path = results_dir / f"{ts}.json"
        json_path.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))

        md_path = results_dir / f"{ts}.md"
        md_path.write_text("\n".join(report_lines), encoding="utf-8")

        print(f"\n{sep()}")
        print(f"  结果已保存:")
        print(f"    {json_path}")
        print(f"    {md_path}")


if __name__ == "__main__":
    main()
