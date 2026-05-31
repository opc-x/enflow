"""vocab.py 单元测试（仅用临时 vocab 文件）"""
import datetime

import pytest
import vocab
from vocab import (
    add_to_vocab,
    compute_stats,
    get_due,
    is_blind_spot,
    load_vocab,
    next_interval_days,
    review_word,
    save_vocab,
    _is_due,
)


class TestIsBlindSpot:
    def test_a1_a2_not_blind(self):
        assert is_blind_spot("the") is False
        assert is_blind_spot("hello") is False

    def test_beyond_a2_is_blind(self):
        assert is_blind_spot("ephemeral") is True

    def test_case_and_whitespace(self):
        assert is_blind_spot("  THE  ") is False
        assert is_blind_spot("  Ephemeral  ") is True


class TestNextIntervalDays:
    @pytest.mark.parametrize(
        "count,expected",
        [(0, 1), (1, 3), (2, 7), (3, 14), (4, 30), (5, 30), (99, 30)],
    )
    def test_intervals(self, count, expected):
        assert next_interval_days(count) == expected


class TestLoadSaveVocab:
    def test_roundtrip(self, vocab_file):
        data = [{"word": "alpha", "seen_count": 1}]
        save_vocab(data)
        assert load_vocab() == data

    def test_missing_file_returns_empty(self, vocab_file):
        assert load_vocab() == []

    def test_corrupt_file_returns_empty(self, vocab_file):
        vocab_file.write_text("{not json", encoding="utf-8")
        assert load_vocab() == []


class TestAddToVocab:
    def test_new_word_fields(self, vocab_file):
        add_to_vocab("ephemeral", "短暂的")
        entries = load_vocab()
        assert len(entries) == 1
        e = entries[0]
        assert e["word"] == "ephemeral"
        assert e["translation"] == "短暂的"
        assert e["seen_count"] == 1
        assert e["correct_count"] == 0
        assert e["wrong_count"] == 0
        assert "first_seen_time" in e
        assert "next_review_time" in e

    def test_duplicate_updates_seen_only(self, vocab_file, monkeypatch):
        fixed = datetime.datetime(2026, 1, 1, 12, 0, 0)

        class FixedDatetime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed

        monkeypatch.setattr(vocab.datetime, "datetime", FixedDatetime)
        add_to_vocab("ephemeral", "短暂的")
        first = load_vocab()[0].copy()
        add_to_vocab("ephemeral", "另一译")
        second = load_vocab()[0]
        assert second["seen_count"] == first["seen_count"] + 1
        assert second["translation"] == first["translation"]
        assert second["last_seen_time"] == fixed.isoformat()

    def test_a1_a2_skipped(self, vocab_file):
        add_to_vocab("the", "定冠词")
        assert load_vocab() == []

    def test_code_symbols_skipped(self, vocab_file):
        add_to_vocab("foo@bar", "x")
        add_to_vocab("arr[]", "x")
        assert load_vocab() == []

    def test_all_caps_abbrev_skipped(self, vocab_file):
        add_to_vocab("HTTP", "超文本")
        add_to_vocab("API", "接口")
        assert load_vocab() == []


class TestReviewWord:
    def _seed(self, vocab_file, word="ephemeral", **kwargs):
        entry = {
            "word": word,
            "translation": "短暂的",
            "first_seen_time": "2026-01-01T00:00:00",
            "last_seen_time": "2026-01-01T00:00:00",
            "seen_count": 1,
            "correct_count": 0,
            "wrong_count": 0,
            "next_review_time": "2020-01-01T00:00:00",
            "note": "",
        }
        entry.update(kwargs)
        save_vocab([entry])

    def test_correct_advances_interval(self, vocab_file):
        self._seed(vocab_file, correct_count=0)
        review_word("ephemeral", correct=True)
        e = load_vocab()[0]
        assert e["correct_count"] == 1
        assert e["wrong_count"] == 0
        days = next_interval_days(1)
        expected = datetime.datetime.fromisoformat(e["last_seen_time"]) + datetime.timedelta(days=days)
        assert datetime.datetime.fromisoformat(e["next_review_time"]).date() == expected.date()

    def test_wrong_resets_one_day(self, vocab_file):
        self._seed(vocab_file, correct_count=2, wrong_count=0)
        review_word("ephemeral", correct=False)
        e = load_vocab()[0]
        assert e["wrong_count"] == 1
        assert e["correct_count"] == 2
        nrt = datetime.datetime.fromisoformat(e["next_review_time"])
        lst = datetime.datetime.fromisoformat(e["last_seen_time"])
        assert (nrt - lst).days == 1

    def test_missing_word_raises(self, vocab_file):
        with pytest.raises(ValueError, match="not found"):
            review_word("nope", correct=True)


class TestComputeStats:
    def test_mastered_learning_not_mastered(self, vocab_file, monkeypatch):
        now = datetime.datetime(2026, 5, 31, 12, 0, 0)
        monkeypatch.setattr(
            vocab.datetime,
            "datetime",
            type(
                "DT",
                (datetime.datetime,),
                {"now": classmethod(lambda cls, tz=None: now)},
            ),
        )
        save_vocab(
            [
                {"word": "a", "correct_count": 3, "seen_count": 5, "last_seen_time": now.isoformat(),
                 "next_review_time": (now + datetime.timedelta(days=7)).isoformat(),
                 "first_seen_time": now.isoformat()},
                {"word": "b", "correct_count": 1, "seen_count": 2, "last_seen_time": now.isoformat(),
                 "next_review_time": (now + datetime.timedelta(days=3)).isoformat(),
                 "first_seen_time": "2020-06-01T00:00:00"},
                {"word": "c", "correct_count": 0, "seen_count": 1, "last_seen_time": now.isoformat(),
                 "next_review_time": (now - datetime.timedelta(days=1)).isoformat(),
                 "first_seen_time": "2020-01-01T00:00:00"},
            ]
        )
        stats = compute_stats(load_vocab())
        assert stats["mastered"] == 1
        assert stats["learning"] == 1
        assert stats["not_mastered"] == 1
        assert stats["total"] == 3
        assert stats["today_new"] == 1
        assert stats["due_today"] >= 1
        assert stats["streak"] >= 1

    def test_bad_dates_do_not_crash(self, vocab_file):
        save_vocab(
            [
                {
                    "word": "bad",
                    "correct_count": 0,
                    "seen_count": 1,
                    "last_seen_time": "not-a-date",
                    "next_review_time": "also-bad",
                    "first_seen_time": "nope",
                }
            ]
        )
        stats = compute_stats(load_vocab())
        assert stats["total"] == 1


class TestGetDue:
    def test_due_when_past(self, vocab_file):
        now = datetime.datetime.now()
        past = (now - datetime.timedelta(days=1)).isoformat()
        entry = {"next_review_time": past}
        assert _is_due(entry, now) is True
        assert get_due([entry])

    def test_bad_date_treated_as_due(self):
        now = datetime.datetime.now()
        assert _is_due({"next_review_time": "broken"}, now) is True
