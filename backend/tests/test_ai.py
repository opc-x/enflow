"""ai.py 纯函数与 mock _call 的 async 测试"""
import pytest
import ai
from ai import (
    _detect_type,
    _lookup_contraction,
    _replace_xieyin_line,
    convert,
    explain_pronounce,
    judge,
    translate,
)


class TestDetectType:
    def test_word(self):
        assert _detect_type("hello") == "word"

    def test_phrase(self):
        assert _detect_type("how are you") == "phrase"

    def test_sentence(self):
        assert _detect_type("This is a full sentence.") == "sentence"

    def test_paragraph(self):
        assert _detect_type("one\ntwo\nthree\nfour\nfive\nsix") == "paragraph"
        assert _detect_type(" ".join(["w"] * 41)) == "paragraph"


class TestLookupContraction:
    def test_youre(self):
        c = _lookup_contraction("you're")
        assert c is not None
        assert c["expanded"] == "you are"

    def test_unknown(self):
        assert _lookup_contraction("hello") is None

    def test_strips_punctuation(self):
        assert _lookup_contraction("  can't!  ") is not None


class TestReplaceXieyinLine:
    def test_replaces_line(self):
        raw = "【谐音】旧谐音\n【其他】x"
        out = _replace_xieyin_line(raw, "米(mi)-提(ti)")
        assert "【谐音】米(mi)-提(ti)" in out
        assert "旧谐音" not in out

    def test_empty_xieyin_unchanged(self):
        raw = "【谐音】旧"
        assert _replace_xieyin_line(raw, "") == raw


@pytest.mark.asyncio
class TestAsyncAiMocked:
    async def test_convert(self, monkeypatch):
        async def fake_call(system, user, max_tokens=800):
            return "converted text"

        monkeypatch.setattr(ai, "_call", fake_call)
        assert await convert("hi") == "converted text"

    async def test_translate_word(self, monkeypatch):
        async def fake_call(system, user, max_tokens=800):
            return "翻译结果"

        monkeypatch.setattr(ai, "_call", fake_call)
        result = await translate("hello")
        assert result["text_type"] == "word"
        assert result["translation"] == "翻译结果"

    async def test_translate_contraction_short_circuit(self, monkeypatch):
        called = False

        async def fake_call(*_a, **_k):
            nonlocal called
            called = True
            return "x"

        monkeypatch.setattr(ai, "_call", fake_call)
        result = await translate("you're")
        assert not called
        assert "你是" in result["translation"]

    async def test_explain_contraction(self, monkeypatch):
        async def fake_call(*_a, **_k):
            raise AssertionError("should not call API for contraction")

        monkeypatch.setattr(ai, "_call", fake_call)
        result = await explain_pronounce("you're")
        assert "优(you)-儿(er)" in result["phonetic_xieyin"]
        assert "【谐音】" in result["explain"]

    async def test_explain_word_mocked(self, monkeypatch):
        async def fake_call(system, user, max_tokens=800):
            if "explain" in system.lower() or max_tokens == 800:
                return "【谐音】AI谐音\n【核心含义】测试"
            return "【谐音】AI谐音\n【重音】首"

        monkeypatch.setattr(ai, "_call", fake_call)
        result = await explain_pronounce("meeting")
        assert "米(mi)" in result.get("phonetic_xieyin", "") or "【谐音】" in result["explain"]

    async def test_judge(self, monkeypatch):
        async def fake_call(system, user, max_tokens=800):
            return "verdict: correct\nfeedback: 很好"

        monkeypatch.setattr(ai, "_call", fake_call)
        result = await judge("word", "标准", "用户答")
        assert result["correct"] is True
        assert result["feedback"] == "很好"
