"""
CMU Pronouncing Dictionary + ARPAbet → 谐音
对外接口：get_xieyin(word) → "伊(yi)-费(fei)-默(mo)-勒(le)"
每个英语音节 → 一个汉字(拼音)，括号内只含标准普通话拼音
"""
import re
import pronouncing

VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
          "IH", "IY", "OW", "OY", "UH", "UW"}

SPECIAL_XIEYIN = {
    "you're": "优(you)-儿(er)",
    "youre": "优(you)-儿(er)",
    "your": "优(you)-儿(er)",
}

# (首辅音, 元音) → (汉字, 拼音)
# 首辅音 None = 无辅音起头
SYLLABLE_MAP: dict[tuple, tuple[str, str]] = {
    # ── 无辅音起头 ──────────────────────────
    (None, "IH"): ("伊", "yi"),
    (None, "IY"): ("伊", "yi"),
    (None, "EH"): ("哎", "ai"),
    (None, "EY"): ("诶", "ei"),
    (None, "AE"): ("哎", "ai"),
    (None, "AH"): ("啊", "a"),
    (None, "AA"): ("啊", "a"),
    (None, "AO"): ("哦", "o"),
    (None, "AW"): ("奥", "ao"),
    (None, "AY"): ("爱", "ai"),
    (None, "OW"): ("哦", "o"),
    (None, "OY"): ("哦", "o"),
    (None, "UW"): ("乌", "wu"),
    (None, "UH"): ("屋", "wu"),
    (None, "ER"): ("哦", "er"),
    # ── B ─────────────────────────────────
    ("B",  "IH"): ("比", "bi"),
    ("B",  "IY"): ("比", "bi"),
    ("B",  "EH"): ("贝", "bei"),
    ("B",  "EY"): ("贝", "bei"),
    ("B",  "AE"): ("拜", "bai"),
    ("B",  "AH"): ("巴", "ba"),
    ("B",  "AA"): ("巴", "ba"),
    ("B",  "AO"): ("博", "bo"),
    ("B",  "AW"): ("宝", "bao"),
    ("B",  "AY"): ("拜", "bai"),
    ("B",  "OW"): ("博", "bo"),
    ("B",  "UW"): ("布", "bu"),
    ("B",  "UH"): ("布", "bu"),
    ("B",  "ER"): ("博", "bo"),
    # ── CH ────────────────────────────────
    ("CH", "IH"): ("奇", "qi"),
    ("CH", "IY"): ("奇", "qi"),
    ("CH", "EH"): ("切", "qie"),
    ("CH", "EY"): ("彻", "che"),
    ("CH", "AE"): ("查", "cha"),
    ("CH", "AH"): ("恰", "qia"),
    ("CH", "AA"): ("恰", "qia"),
    ("CH", "AO"): ("乔", "qiao"),
    ("CH", "AW"): ("巢", "chao"),
    ("CH", "AY"): ("柴", "chai"),
    ("CH", "OW"): ("秋", "qiu"),
    ("CH", "UW"): ("出", "chu"),
    ("CH", "ER"): ("澈", "che"),
    # ── D ─────────────────────────────────
    ("D",  "IH"): ("迪", "di"),
    ("D",  "IY"): ("迪", "di"),
    ("D",  "EH"): ("得", "de"),
    ("D",  "EY"): ("得", "de"),
    ("D",  "AE"): ("达", "da"),
    ("D",  "AH"): ("达", "da"),
    ("D",  "AA"): ("大", "da"),
    ("D",  "AO"): ("多", "duo"),
    ("D",  "AW"): ("道", "dao"),
    ("D",  "AY"): ("代", "dai"),
    ("D",  "OW"): ("多", "duo"),
    ("D",  "UW"): ("都", "du"),
    ("D",  "ER"): ("德", "de"),
    # ── F ─────────────────────────────────
    ("F",  "IH"): ("非", "fei"),
    ("F",  "IY"): ("非", "fei"),
    ("F",  "EH"): ("费", "fei"),
    ("F",  "EY"): ("费", "fei"),
    ("F",  "AE"): ("法", "fa"),
    ("F",  "AH"): ("弗", "fu"),
    ("F",  "AA"): ("法", "fa"),
    ("F",  "AO"): ("佛", "fo"),
    ("F",  "AW"): ("福", "fu"),
    ("F",  "AY"): ("飞", "fei"),
    ("F",  "OW"): ("佛", "fo"),
    ("F",  "UW"): ("福", "fu"),
    ("F",  "ER"): ("佛", "fo"),
    # ── G ─────────────────────────────────
    ("G",  "IH"): ("给", "gei"),
    ("G",  "IY"): ("吉", "ji"),
    ("G",  "EH"): ("格", "ge"),
    ("G",  "EY"): ("给", "gei"),
    ("G",  "AE"): ("嘎", "ga"),
    ("G",  "AH"): ("嘎", "ga"),
    ("G",  "AA"): ("嘎", "ga"),
    ("G",  "AO"): ("戈", "ge"),
    ("G",  "AW"): ("高", "gao"),
    ("G",  "AY"): ("盖", "gai"),
    ("G",  "OW"): ("哥", "ge"),
    ("G",  "UW"): ("古", "gu"),
    ("G",  "ER"): ("哥", "ge"),
    # ── HH ────────────────────────────────
    ("HH", "IH"): ("嗨", "hai"),
    ("HH", "IY"): ("嗨", "hai"),
    ("HH", "EH"): ("嘿", "hei"),
    ("HH", "EY"): ("嘿", "hei"),
    ("HH", "AE"): ("哈", "ha"),
    ("HH", "AH"): ("哈", "ha"),
    ("HH", "AA"): ("哈", "ha"),
    ("HH", "AO"): ("豪", "hao"),
    ("HH", "AW"): ("豪", "hao"),
    ("HH", "AY"): ("嗨", "hai"),
    ("HH", "OW"): ("荷", "he"),
    ("HH", "UW"): ("乎", "hu"),
    ("HH", "ER"): ("额", "e"),
    # ── JH ────────────────────────────────
    ("JH", "IH"): ("基", "ji"),
    ("JH", "IY"): ("基", "ji"),
    ("JH", "EH"): ("杰", "jie"),
    ("JH", "EY"): ("杰", "jie"),
    ("JH", "AE"): ("贾", "jia"),
    ("JH", "AH"): ("家", "jia"),
    ("JH", "AA"): ("扎", "zha"),
    ("JH", "AO"): ("爵", "jue"),
    ("JH", "AW"): ("交", "jiao"),
    ("JH", "AY"): ("佳", "jia"),
    ("JH", "OW"): ("乔", "qiao"),
    ("JH", "UW"): ("居", "ju"),
    ("JH", "ER"): ("扎", "zha"),
    # ── K ─────────────────────────────────
    ("K",  "IH"): ("克", "ke"),
    ("K",  "IY"): ("克", "ke"),
    ("K",  "EH"): ("克", "ke"),
    ("K",  "EY"): ("克", "ke"),
    ("K",  "AE"): ("卡", "ka"),
    ("K",  "AH"): ("卡", "ka"),
    ("K",  "AA"): ("卡", "ka"),
    ("K",  "AO"): ("科", "ke"),
    ("K",  "AW"): ("考", "kao"),
    ("K",  "AY"): ("凯", "kai"),
    ("K",  "OW"): ("柯", "ke"),
    ("K",  "UW"): ("库", "ku"),
    ("K",  "ER"): ("克", "ke"),
    # ── L ─────────────────────────────────
    ("L",  "IH"): ("里", "li"),
    ("L",  "IY"): ("里", "li"),
    ("L",  "EH"): ("勒", "le"),
    ("L",  "EY"): ("勒", "le"),
    ("L",  "AE"): ("拉", "la"),
    ("L",  "AH"): ("勒", "le"),
    ("L",  "AA"): ("拉", "la"),
    ("L",  "AO"): ("罗", "luo"),
    ("L",  "AW"): ("劳", "lao"),
    ("L",  "AY"): ("来", "lai"),
    ("L",  "OW"): ("罗", "luo"),
    ("L",  "UW"): ("路", "lu"),
    ("L",  "ER"): ("勒", "le"),
    # ── M ─────────────────────────────────
    ("M",  "IH"): ("米", "mi"),
    ("M",  "IY"): ("米", "mi"),
    ("M",  "EH"): ("默", "mo"),
    ("M",  "EY"): ("梅", "mei"),
    ("M",  "AE"): ("马", "ma"),
    ("M",  "AH"): ("默", "mo"),
    ("M",  "AA"): ("马", "ma"),
    ("M",  "AO"): ("莫", "mo"),
    ("M",  "AW"): ("毛", "mao"),
    ("M",  "AY"): ("迈", "mai"),
    ("M",  "OW"): ("摩", "mo"),
    ("M",  "UW"): ("木", "mu"),
    ("M",  "ER"): ("默", "mo"),
    # ── N ─────────────────────────────────
    ("N",  "IH"): ("尼", "ni"),
    ("N",  "IY"): ("尼", "ni"),
    ("N",  "EH"): ("呢", "ne"),
    ("N",  "EY"): ("呢", "ne"),
    ("N",  "AE"): ("纳", "na"),
    ("N",  "AH"): ("纳", "na"),
    ("N",  "AA"): ("纳", "na"),
    ("N",  "AO"): ("诺", "nuo"),
    ("N",  "AW"): ("闹", "nao"),
    ("N",  "AY"): ("乃", "nai"),
    ("N",  "OW"): ("诺", "nuo"),
    ("N",  "UW"): ("奴", "nu"),
    ("N",  "ER"): ("呢", "ne"),
    # ── P ─────────────────────────────────
    ("P",  "IH"): ("皮", "pi"),
    ("P",  "IY"): ("皮", "pi"),
    ("P",  "EH"): ("配", "pei"),
    ("P",  "EY"): ("配", "pei"),
    ("P",  "AE"): ("帕", "pa"),
    ("P",  "AH"): ("普", "pu"),
    ("P",  "AA"): ("帕", "pa"),
    ("P",  "AO"): ("博", "po"),
    ("P",  "AW"): ("泡", "pao"),
    ("P",  "AY"): ("派", "pai"),
    ("P",  "OW"): ("坡", "po"),
    ("P",  "UW"): ("铺", "pu"),
    ("P",  "ER"): ("普", "pu"),
    # ── R ─────────────────────────────────
    ("R",  "IH"): ("热", "re"),
    ("R",  "IY"): ("热", "re"),
    ("R",  "EH"): ("热", "re"),
    ("R",  "EY"): ("热", "re"),
    ("R",  "AE"): ("热", "re"),
    ("R",  "AH"): ("热", "re"),
    ("R",  "AA"): ("热", "re"),
    ("R",  "AO"): ("热", "re"),
    ("R",  "AW"): ("热", "re"),
    ("R",  "AY"): ("热", "re"),
    ("R",  "OW"): ("热", "re"),
    ("R",  "UW"): ("热", "re"),
    ("R",  "ER"): ("热", "re"),
    # ── S ─────────────────────────────────
    ("S",  "IH"): ("斯", "si"),
    ("S",  "IY"): ("斯", "si"),
    ("S",  "EH"): ("塞", "sai"),
    ("S",  "EY"): ("塞", "sai"),
    ("S",  "AE"): ("萨", "sa"),
    ("S",  "AH"): ("萨", "sa"),
    ("S",  "AA"): ("萨", "sa"),
    ("S",  "AO"): ("索", "suo"),
    ("S",  "AW"): ("骚", "sao"),
    ("S",  "AY"): ("赛", "sai"),
    ("S",  "OW"): ("索", "suo"),
    ("S",  "UW"): ("苏", "su"),
    ("S",  "ER"): ("瑟", "se"),
    # ── SH ────────────────────────────────
    ("SH", "IH"): ("式", "shi"),
    ("SH", "IY"): ("式", "shi"),
    ("SH", "EH"): ("舍", "she"),
    ("SH", "EY"): ("舍", "she"),
    ("SH", "AE"): ("沙", "sha"),
    ("SH", "AH"): ("沙", "sha"),
    ("SH", "AA"): ("沙", "sha"),
    ("SH", "AO"): ("哨", "shao"),
    ("SH", "AW"): ("哨", "shao"),
    ("SH", "AY"): ("晒", "shai"),
    ("SH", "OW"): ("哨", "shao"),
    ("SH", "UW"): ("殊", "shu"),
    ("SH", "ER"): ("舍", "she"),
    # ── T ─────────────────────────────────
    ("T",  "IH"): ("提", "ti"),
    ("T",  "IY"): ("提", "ti"),
    ("T",  "EH"): ("特", "te"),
    ("T",  "EY"): ("特", "te"),
    ("T",  "AE"): ("塔", "ta"),
    ("T",  "AH"): ("塔", "ta"),
    ("T",  "AA"): ("塔", "ta"),
    ("T",  "AO"): ("托", "tuo"),
    ("T",  "AW"): ("陶", "tao"),
    ("T",  "AY"): ("太", "tai"),
    ("T",  "OW"): ("托", "tuo"),
    ("T",  "UW"): ("图", "tu"),
    ("T",  "ER"): ("特", "te"),
    # ── V ─────────────────────────────────
    ("V",  "IH"): ("维", "wei"),
    ("V",  "IY"): ("维", "wei"),
    ("V",  "EH"): ("维", "wei"),
    ("V",  "EY"): ("维", "wei"),
    ("V",  "AE"): ("瓦", "wa"),
    ("V",  "AH"): ("瓦", "wa"),
    ("V",  "AA"): ("瓦", "wa"),
    ("V",  "AO"): ("沃", "wo"),
    ("V",  "AW"): ("唯", "wei"),
    ("V",  "AY"): ("唯", "wei"),
    ("V",  "OW"): ("沃", "wo"),
    ("V",  "UW"): ("乌", "wu"),
    ("V",  "ER"): ("沃", "wo"),
    # ── W ─────────────────────────────────
    ("W",  "IH"): ("威", "wei"),
    ("W",  "IY"): ("威", "wei"),
    ("W",  "EH"): ("威", "wei"),
    ("W",  "EY"): ("威", "wei"),
    ("W",  "AE"): ("挖", "wa"),
    ("W",  "AH"): ("挖", "wa"),
    ("W",  "AA"): ("挖", "wa"),
    ("W",  "AO"): ("沃", "wo"),
    ("W",  "AW"): ("窝", "wo"),
    ("W",  "AY"): ("挥", "hui"),
    ("W",  "OW"): ("窝", "wo"),
    ("W",  "UW"): ("乌", "wu"),
    ("W",  "ER"): ("沃", "wo"),
    # ── Y ─────────────────────────────────
    ("Y",  "IH"): ("伊", "yi"),
    ("Y",  "IY"): ("伊", "yi"),
    ("Y",  "EH"): ("耶", "ye"),
    ("Y",  "EY"): ("耶", "ye"),
    ("Y",  "AE"): ("呀", "ya"),
    ("Y",  "AH"): ("呀", "ya"),
    ("Y",  "AA"): ("呀", "ya"),
    ("Y",  "AO"): ("哟", "yo"),
    ("Y",  "AW"): ("哟", "yo"),
    ("Y",  "AY"): ("耶", "ye"),
    ("Y",  "OW"): ("哟", "yo"),
    ("Y",  "UW"): ("优", "you"),
    ("Y",  "UH"): ("优", "you"),
    ("Y",  "ER"): ("耶", "ye"),
    # ── Z ─────────────────────────────────
    ("Z",  "IH"): ("兹", "zi"),
    ("Z",  "IY"): ("兹", "zi"),
    ("Z",  "EH"): ("泽", "ze"),
    ("Z",  "EY"): ("泽", "ze"),
    ("Z",  "AE"): ("扎", "za"),
    ("Z",  "AH"): ("扎", "za"),
    ("Z",  "AA"): ("扎", "za"),
    ("Z",  "AO"): ("佐", "zuo"),
    ("Z",  "AW"): ("找", "zhao"),
    ("Z",  "AY"): ("宰", "zai"),
    ("Z",  "OW"): ("佐", "zuo"),
    ("Z",  "UW"): ("祖", "zu"),
    ("Z",  "ER"): ("泽", "ze"),
    # ── ZH ────────────────────────────────
    ("ZH", "IH"): ("之", "zhi"),
    ("ZH", "IY"): ("之", "zhi"),
    ("ZH", "EH"): ("者", "zhe"),
    ("ZH", "EY"): ("者", "zhe"),
    ("ZH", "AE"): ("炸", "zha"),
    ("ZH", "AH"): ("炸", "zha"),
    ("ZH", "AA"): ("炸", "zha"),
    ("ZH", "AO"): ("着", "zhuo"),
    ("ZH", "AW"): ("找", "zhao"),
    ("ZH", "AY"): ("宅", "zhai"),
    ("ZH", "OW"): ("着", "zhuo"),
    ("ZH", "UW"): ("主", "zhu"),
    ("ZH", "ER"): ("者", "zhe"),
    # ── TH ────────────────────────────────
    ("TH", "IH"): ("斯", "si"),
    ("TH", "IY"): ("斯", "si"),
    ("TH", "EH"): ("斯", "si"),
    ("TH", "EY"): ("斯", "si"),
    ("TH", "AE"): ("萨", "sa"),
    ("TH", "AH"): ("萨", "sa"),
    ("TH", "AA"): ("萨", "sa"),
    ("TH", "AO"): ("索", "suo"),
    ("TH", "AW"): ("骚", "sao"),
    ("TH", "AY"): ("赛", "sai"),
    ("TH", "OW"): ("索", "suo"),
    ("TH", "UW"): ("苏", "su"),
    ("TH", "ER"): ("瑟", "se"),
    # ── DH ────────────────────────────────
    ("DH", "IH"): ("则", "ze"),
    ("DH", "IY"): ("则", "ze"),
    ("DH", "EH"): ("则", "ze"),
    ("DH", "EY"): ("则", "ze"),
    ("DH", "AE"): ("扎", "za"),
    ("DH", "AH"): ("则", "ze"),
    ("DH", "AA"): ("扎", "za"),
    ("DH", "AO"): ("着", "zhuo"),
    ("DH", "AW"): ("找", "zhao"),
    ("DH", "AY"): ("宅", "zhai"),
    ("DH", "OW"): ("着", "zhuo"),
    ("DH", "UW"): ("主", "zhu"),
    ("DH", "ER"): ("者", "zhe"),
    # ── NG ─ 音节末尾鼻音，不单独成音节，忽略 ──────
}


def _phones_to_syllables(phones: list[str]) -> list[list[str]]:
    """
    最大音首原则：每个元音取前面紧邻的一个辅音作为起头。
    只保留 onset+vowel，忽略尾辅音（韵尾不影响谐音汉字选择）。
    """
    clean = [re.sub(r"\d", "", ph) for ph in phones]
    vowel_positions = [i for i, ph in enumerate(clean) if ph in VOWELS]
    if not vowel_positions:
        return []

    syllables = []
    for vi, vpos in enumerate(vowel_positions):
        if vi == 0:
            # 第一个音节：包含 word-initial 所有辅音 + 元音
            onset_start = 0
        else:
            prev_vpos = vowel_positions[vi - 1]
            consonants_between = vpos - prev_vpos - 1
            # 最大音首：把紧邻前一个辅音分给本音节作 onset
            onset_start = vpos - 1 if consonants_between >= 1 else vpos
        # 只取 onset+vowel，不要 coda
        syllables.append(phones[onset_start : vpos + 1])
    return syllables


def _syllable_to_xieyin(phones: list[str]) -> str:
    """一个音节（音素列表）→ 汉字(拼音)，找不到返回空"""
    vowel = None
    onset: list[str] = []
    found_vowel = False

    for ph in phones:
        base = re.sub(r"\d", "", ph)
        if base in VOWELS:
            vowel = base
            found_vowel = True
        elif not found_vowel:
            onset.append(base)

    if not vowel:
        return ""

    first_onset = onset[0] if onset else None
    result = SYLLABLE_MAP.get((first_onset, vowel)) or SYLLABLE_MAP.get((None, vowel))
    if not result:
        return ""
    hz, py = result
    return f"{hz}({py})"


def get_xieyin(word: str) -> str:
    """
    返回 CMU 谐音，如 "伊(yi)-费(fei)-默(mo)-勒(le)"
    找不到时返回空字符串
    """
    normalized = word.strip().lower().replace("’", "'")
    normalized = re.sub(r"^[^a-z']+|[^a-z']+$", "", normalized)
    if normalized in SPECIAL_XIEYIN:
        return SPECIAL_XIEYIN[normalized]

    phones = pronouncing.phones_for_word(normalized)
    if not phones:
        return ""
    syllables = _phones_to_syllables(phones[0].split())
    parts = [_syllable_to_xieyin(s) for s in syllables]
    parts = [p for p in parts if p]
    return "-".join(parts)


if __name__ == "__main__":
    test_cases = [
        ("ephemeral",     "期望: 伊(yi)-费(fei)-默(mo)-勒(le)"),
        ("resilience",    "期望: 热(re)-兹(zi)-里(li)-恩(en)"),
        ("procrastinate", "期望: 多音节动词"),
        ("particularly",  "期望: 多音节，第2音节重读"),
        ("entrepreneur",  "期望: 法语借词"),
        ("comfortable",   "期望: 3音节"),
        ("worcestershire","期望: 极难发音词"),
        ("serendipity",   "期望: 5音节"),
        ("condescending", "期望: 4音节"),
        ("schedule",      "期望: 斯(si)-克(ke)-杰(jie)"),
        ("meeting",       "期望: 米(mi)-提(ti)"),
        ("the",           "期望: 则(ze)"),
    ]
    print(f"{'单词':<20} {'CMU谐音':<35} 备注")
    print("-" * 80)
    for word, note in test_cases:
        result = get_xieyin(word)
        print(f"{word:<20} {result or '(未收录)':<35} {note}")
