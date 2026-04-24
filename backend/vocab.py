"""
生词本 CRUD + SM-2 调度 + CEFR A1/A2 盲点过滤
"""
import json
import datetime
from pathlib import Path
from config import VOCAB_PATH

# ── CEFR A1/A2 高频词（约1500词），在此列表内的不入库 ──────────────────────
_A1_A2: set[str] = {
    # A1 核心
    "a","an","the","and","or","but","if","in","on","at","to","of","for","with",
    "is","are","was","were","be","been","being","have","has","had","do","does",
    "did","will","would","can","could","should","may","might","shall","must",
    "i","you","he","she","it","we","they","me","him","her","us","them",
    "my","your","his","its","our","their","mine","yours","hers","ours","theirs",
    "this","that","these","those","what","who","which","where","when","why","how",
    "not","no","yes","ok","okay","please","thank","thanks","sorry","hello","hi",
    "bye","goodbye","good","bad","big","small","new","old","first","last",
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "here","there","now","then","today","tomorrow","yesterday","always","never",
    "very","also","so","just","about","up","out","more","some","any","all",
    "get","got","go","went","come","came","see","saw","say","said","know","knew",
    "think","thought","want","like","need","make","made","take","took","give",
    "gave","find","found","use","used","look","looked","work","worked","call",
    "called","try","tried","ask","asked","feel","felt","become","became","leave",
    "left","put","mean","meant","keep","kept","let","begin","began","show",
    "showed","hear","heard","play","played","run","ran","move","moved","live",
    "lived","write","wrote","sit","sat","stand","stood","lose","lost","pay",
    "paid","meet","met","set","learn","learned","change","changed","lead","led",
    "read","spend","spent","grow","grew","open","opened","walk","walked","win",
    "won","buy","bought","wait","waited","send","sent","build","built","stay",
    "stayed","fall","fell","cut","reach","reached","help","helped","stop",
    "stopped","turn","turned","start","started","hand","place","case","fact",
    # A2 扩展
    "able","about","above","across","after","again","age","ago","agree","air",
    "already","although","always","animal","another","answer","anything","area",
    "arrive","art","away","back","ball","bank","because","before","behind",
    "between","book","both","boy","bring","broke","brother","brought","brown",
    "business","busy","care","carry","caught","center","certain","child","children",
    "choose","city","class","clean","clear","close","clothes","color","colour",
    "computer","continue","control","cook","copy","count","country","cover","create",
    "cross","dark","daughter","day","dead","decide","deep","describe","different",
    "difficult","direction","discover","done","door","down","draw","dream","drive",
    "drop","during","each","early","easy","either","end","enjoy","enough","enter",
    "even","evening","ever","every","example","face","fact","fall","family","far",
    "fast","father","feet","few","fight","finish","fire","food","form","free",
    "friend","front","full","fun","game","girl","give","glad","glass","great",
    "green","ground","group","grow","guess","half","happen","happy","hard","head",
    "heart","heavy","high","hold","home","hope","hour","house","hundred","idea",
    "important","include","inside","instead","interest","into","job","kind","large",
    "later","laugh","less","life","light","long","love","low","main","matter",
    "member","mind","minute","miss","money","month","morning","most","mother",
    "music","name","near","next","nice","night","north","nothing","notice","number",
    "often","once","only","order","other","outside","over","own","page","part",
    "past","people","perhaps","person","phone","picture","plan","point","possible",
    "power","prepare","pretty","problem","program","pull","push","quite","real",
    "reason","receive","remember","rest","return","right","road","same","school",
    "second","seem","short","side","simple","since","sister","slow","soon","south",
    "space","speak","special","stand","start","state","step","still","story",
    "student","study","sure","system","talk","teacher","team","tell","than","thing",
    "through","time","told","together","top","town","tree","true","turn","type",
    "under","understand","until","usually","visit","voice","warm","watch","water",
    "week","well","west","white","whole","word","world","year","young","zero",
    "color","colour","centre","center","favourite","favorite","organisation",
    "organization","programme","program","travelling","traveling",
}


def load_vocab() -> list:
    if not VOCAB_PATH.exists():
        return []
    try:
        return json.loads(VOCAB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_vocab(vocab: list) -> None:
    VOCAB_PATH.parent.mkdir(parents=True, exist_ok=True)
    VOCAB_PATH.write_text(json.dumps(vocab, ensure_ascii=False, indent=2), encoding="utf-8")


def is_blind_spot(word: str) -> bool:
    """CEFR A1/A2 以外的词视为盲点，静态判断，不调 AI"""
    return word.lower().strip() not in _A1_A2


def add_to_vocab(word: str, translation: str) -> None:
    """写入生词本，重复则更新 seen_count"""
    import re
    word = word.strip()
    if not word or not is_blind_spot(word):
        return
    # 过滤代码符号、纯大写缩写
    if re.search(r'[@{}()\[\]<>;=]', word):
        return
    if re.match(r'^[A-Z_][A-Z0-9_]{2,}$', word):
        return

    vocab = load_vocab()
    now = datetime.datetime.now().isoformat()
    for entry in vocab:
        if entry.get("word", "").lower() == word.lower():
            entry["seen_count"] = entry.get("seen_count", 1) + 1
            entry["last_seen_time"] = now
            save_vocab(vocab)
            return

    vocab.append({
        "word": word,
        "translation": translation,
        "first_seen_time": now,
        "last_seen_time": now,
        "seen_count": 1,
        "correct_count": 0,
        "wrong_count": 0,
        "next_review_time": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
        "note": "",
    })
    save_vocab(vocab)


# ── SM-2 ──────────────────────────────────────────────────────────────────────
_INTERVALS = [1, 3, 7, 14, 30]

def next_interval_days(correct_count: int) -> int:
    return _INTERVALS[min(correct_count, len(_INTERVALS) - 1)]


def review_word(word: str, correct: bool) -> datetime.datetime:
    """更新复习记录，返回下次复习时间"""
    vocab = load_vocab()
    now = datetime.datetime.now()
    for entry in vocab:
        if entry.get("word", "").lower() == word.lower():
            if correct:
                entry["correct_count"] = entry.get("correct_count", 0) + 1
                days = next_interval_days(entry["correct_count"])
            else:
                entry["wrong_count"] = entry.get("wrong_count", 0) + 1
                days = 1
            next_time = now + datetime.timedelta(days=days)
            entry["next_review_time"] = next_time.isoformat()
            entry["last_seen_time"] = now.isoformat()
            save_vocab(vocab)
            return next_time
    raise ValueError(f"word '{word}' not found in vocab")


def compute_stats(vocab: list) -> dict:
    now = datetime.datetime.now()
    today = now.date().isoformat()
    total = len(vocab)
    not_mastered = learning = mastered = due_today = today_new = 0
    seen_dates: set[str] = set()

    for e in vocab:
        try:
            seen_dates.add(datetime.datetime.fromisoformat(e["last_seen_time"]).date().isoformat())
        except Exception:
            pass

        cc = e.get("correct_count", 0)
        sc = e.get("seen_count", 1)
        if cc >= 3:
            mastered += 1
        elif sc >= 2 and cc / max(sc, 1) >= 0.5:
            learning += 1
        else:
            not_mastered += 1

        try:
            if datetime.datetime.fromisoformat(e["next_review_time"]) <= now:
                due_today += 1
        except Exception:
            due_today += 1

        if e.get("first_seen_time", "")[:10] == today:
            today_new += 1

    streak = 0
    check = now.date()
    while check.isoformat() in seen_dates:
        streak += 1
        check -= datetime.timedelta(days=1)

    return dict(total=total, not_mastered=not_mastered, learning=learning,
                mastered=mastered, due_today=due_today, streak=streak, today_new=today_new)


def get_due(vocab: list) -> list:
    now = datetime.datetime.now()
    return [e for e in vocab if _is_due(e, now)]


def _is_due(entry: dict, now: datetime.datetime) -> bool:
    try:
        return datetime.datetime.fromisoformat(entry["next_review_time"]) <= now
    except Exception:
        return True
