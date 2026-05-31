"""phonetics.py 单元测试"""
import phonetics
from phonetics import (
    SYLLABLE_MAP,
    get_xieyin,
    _phones_to_syllables,
    _syllable_to_xieyin,
)


class TestGetXieyin:
    def test_meeting_multisyllable(self):
        assert get_xieyin("meeting") == "米(mi)-提(ti)"

    def test_special_your(self):
        assert get_xieyin("your") == "优(you)-儿(er)"

    def test_special_youre_apostrophe(self):
        assert get_xieyin("you're") == "优(you)-儿(er)"

    def test_unknown_word_empty(self):
        assert get_xieyin("zzzzqxnotaword") == ""

    def test_punctuation_and_case_normalized(self):
        assert get_xieyin("  Meeting!!!  ") == get_xieyin("meeting")

    def test_ephemeral_nonempty(self):
        result = get_xieyin("ephemeral")
        assert result
        assert "-" in result


class TestPhonesToSyllables:
    def test_maximal_onset_split(self):
        # M IY1 T IH0 NG → 米-提；两元音间 T 归后音节 onset
        phones = "M IY1 T IH0 NG".split()
        syllables = _phones_to_syllables(phones)
        assert len(syllables) == 2
        assert any("T" in "".join(s) for s in syllables[1:])

    def test_no_vowel_returns_empty(self):
        assert _phones_to_syllables(["P", "T", "K"]) == []


class TestSyllableToXieyin:
    def test_hits_syllable_map(self):
        # (M, IH) → 米(mi)
        out = _syllable_to_xieyin(["M1", "IH0"])
        assert out == "米(mi)"
        assert SYLLABLE_MAP.get(("M", "IH")) == ("米", "mi")

    def test_no_vowel_returns_empty(self):
        assert _syllable_to_xieyin(["P", "T"]) == ""
