# infra-model-eval

针对 AI Input Pad 业务场景的多模型横向测评工具。

## 用途

在真实业务 prompt 下对比各模型的输出质量、响应速度、token 消耗，帮助选型或调优 prompt。

## 快速开始

```bash
cd infra-model-eval
pip install openai python-dotenv   # 或用项目 venv

# 测所有模型 + 所有场景
python eval.py

# 只测 explain 场景
python eval.py --scenario explain

# 只测指定模型
python eval.py --model gpt-4o,deepseek-chat

# 组合筛选
python eval.py --scenario explain,pronounce --model gpt-4o,gpt-4o-mini,deepseek-chat
```

结果自动保存到 `results/YYYYMMDD_HHMMSS.json` 和 `.md`。

## 已注册模型

| 模型 ID | 说明 | 需要的 env key |
|---------|------|--------------|
| `gpt-4o` | OpenAI 旗舰 | `OPENAI_API_KEY` |
| `gpt-4o-mini` | OpenAI 快速低价 | `OPENAI_API_KEY` |
| `gpt-4.1` | OpenAI 新一代 | `OPENAI_API_KEY` |
| `gpt-4.1-mini` | OpenAI 新一代轻量 | `OPENAI_API_KEY` |
| `deepseek-chat` | DeepSeek V3，快速 | `DEEPSEEK_API_KEY` |
| `deepseek-v4-pro` | DeepSeek V4 推理模型，慢但质量高 | `DEEPSEEK_API_KEY` |

API key 统一放在项目根目录的 `.env` 文件，缺少某个 key 时对应模型自动跳过。

## 测评场景

| 场景 ID | 说明 | 关键评估点 |
|---------|------|---------|
| `explain` | 词汇解释，含 IPA/谐音/语法要点 | IPA 准确性、谐音格式、语法要点有无实际价值 |
| `pronounce` | 发音指导，连读/弱读/记忆口诀 | 谐音质量、条件字段判断 |
| `translate` | 划词翻译（词/短语/句子） | 自然度、是否有多余解释 |
| `convert` | 中英混输转英文 | 流畅度、是否保留原意 |
| `blind_spot` | 词汇盲点 yes/no 判断 | 准确性、是否严格只输出 yes/no |

## 新增模型

在 `eval.py` 的 `MODELS` 列表里追加一条：

```python
{"id": "your-model-id", "label": "展示名", "base_url": "https://...", "key_env": "YOUR_KEY_ENV", "reasoning": False},
```

`reasoning: True` 表示该模型是推理模型（有 reasoning_content 字段），工具会自动放大 max_tokens 以避免输出被截断。

## 新增场景

在 `scenarios.py` 的 `SCENARIOS` 列表里追加一个 dict：

```python
{
    "id":         "my_scenario",
    "name":       "场景显示名",
    "max_tokens": 400,
    "system":     "system prompt ...",
    "cases":      ["测试用例1", "测试用例2"],
}
```

## 结果目录

`results/` 已加入 `.gitignore`，测评结果只保留在本地。
