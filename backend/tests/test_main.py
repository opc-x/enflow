"""main.py FastAPI 路由测试（mock ai，临时 vocab）"""
import pytest
from fastapi.testclient import TestClient

import ai
import main
import vocab as vocab_module


@pytest.fixture
def client(vocab_file):
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def mock_ai(monkeypatch):
    async def fake_convert(text):
        return f"converted:{text}"

    async def fake_translate(text, context_sentence=""):
        return {"translation": f"tr:{text}", "text_type": "word"}

    async def fake_explain(text, context_sentence=""):
        return {
            "explain": f"【核心含义】{text} meaning\n【谐音】placeholder",
            "pronounce": "【谐音】placeholder",
            "phonetic_xieyin": "米(mi)",
        }

    async def fake_judge(word, translation, user_answer):
        return {"correct": True, "feedback": "ok"}

    monkeypatch.setattr(ai, "convert", fake_convert)
    monkeypatch.setattr(ai, "translate", fake_translate)
    monkeypatch.setattr(ai, "explain_pronounce", fake_explain)
    monkeypatch.setattr(ai, "judge", fake_judge)


class TestConvertRoute:
    def test_convert(self, client):
        r = client.post("/convert", json={"text": "你好"})
        assert r.status_code == 200
        assert r.json() == {"result": "converted:你好"}


class TestTranslateRoute:
    def test_translate(self, client):
        r = client.post("/translate", json={"text": "hello"})
        assert r.status_code == 200
        body = r.json()
        assert body["translation"] == "tr:hello"
        assert body["text_type"] == "word"


class TestExplainRoute:
    def test_explain_and_vocab_insert(self, client, vocab_file):
        r = client.post("/explain", json={"text": "ephemeral"})
        assert r.status_code == 200
        body = r.json()
        assert "explain" in body
        assert "pronounce" in body
        entries = vocab_module.load_vocab()
        assert len(entries) == 1
        assert entries[0]["word"] == "ephemeral"


class TestVocabRoutes:
    def test_stats(self, client, vocab_file):
        vocab_module.save_vocab(
            [
                {
                    "word": "ephemeral",
                    "translation": "x",
                    "seen_count": 1,
                    "correct_count": 0,
                    "wrong_count": 0,
                    "first_seen_time": "2026-05-31T00:00:00",
                    "last_seen_time": "2026-05-31T00:00:00",
                    "next_review_time": "2020-01-01T00:00:00",
                }
            ]
        )
        r = client.get("/vocab/stats")
        assert r.status_code == 200
        stats = r.json()
        for key in ("total", "not_mastered", "learning", "mastered", "due_today", "streak", "today_new"):
            assert key in stats

    def test_due(self, client, vocab_file):
        vocab_module.save_vocab(
            [
                {
                    "word": "ephemeral",
                    "translation": "x",
                    "seen_count": 1,
                    "correct_count": 0,
                    "wrong_count": 0,
                    "first_seen_time": "2026-01-01T00:00:00",
                    "last_seen_time": "2026-01-01T00:00:00",
                    "next_review_time": "2020-01-01T00:00:00",
                }
            ]
        )
        r = client.get("/vocab/due")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_review_ok(self, client, vocab_file):
        vocab_module.save_vocab(
            [
                {
                    "word": "ephemeral",
                    "translation": "短暂的",
                    "seen_count": 1,
                    "correct_count": 0,
                    "wrong_count": 0,
                    "first_seen_time": "2026-01-01T00:00:00",
                    "last_seen_time": "2026-01-01T00:00:00",
                    "next_review_time": "2020-01-01T00:00:00",
                }
            ]
        )
        r = client.post("/vocab/review", json={"word": "ephemeral", "correct": True})
        assert r.status_code == 200
        assert "next_review_time" in r.json()

    def test_review_not_found_404(self, client):
        r = client.post("/vocab/review", json={"word": "nonexistent", "correct": True})
        assert r.status_code == 404
