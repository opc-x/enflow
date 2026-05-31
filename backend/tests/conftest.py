"""pytest 配置：backend 模块路径 + 测试环境变量（不依赖真实 .env）。"""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-pytest-fake-key")
os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-chat")

import pytest  # noqa: E402


@pytest.fixture
def vocab_file(tmp_path, monkeypatch):
    """将 config / vocab 的 VOCAB_PATH 指向临时文件，禁止读写真实生词本。"""
    path = tmp_path / "vocab.json"
    import config
    import vocab as vocab_module

    monkeypatch.setattr(config, "VOCAB_PATH", path)
    monkeypatch.setattr(vocab_module, "VOCAB_PATH", path)
    return path
