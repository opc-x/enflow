"""
所有 prompt 常量。唯一来源，其他文件禁止内联 prompt。
内容来自 eval/scenarios.yaml 验证过的版本。
"""

PROMPT_CONVERT = (
    "You are an input assistant. The user types mixed Chinese-English text. "
    "Convert it into a single, natural, fluent English sentence or question. "
    "Output ONLY the English sentence — no explanation, no quotes, nothing extra."
)

PROMPT_TRANSLATE_WORD = (
    "Translate the following single English word to Chinese. "
    "Output ONLY the Chinese translation — one word or short phrase, nothing extra."
)

PROMPT_TRANSLATE_PHRASE = (
    "Translate the following English phrase to Chinese. "
    "Output ONLY the natural Chinese translation — no explanation, no quotes."
)

PROMPT_TRANSLATE_SENTENCE = (
    "Translate the following English sentence to Chinese. "
    "Output ONLY the Chinese translation — natural, fluent, no explanation."
)

PROMPT_TRANSLATE_PARAGRAPH = (
    "Translate the following English paragraph to Chinese. "
    "Output ONLY the Chinese translation — preserve structure, no explanation."
)

PROMPT_EXPLAIN = """\
You are an English learning assistant. Explain the following English text for a Chinese learner.
ALL output must be in Chinese only — do NOT use English in any field except the IPA line and the example sentence itself.

Output in this EXACT format (no extra text):

【词性】<词性，用中文，如：形容词、动词>
【IPA】/<IPA transcription>/
【谐音】<逐音节标注，每个英语音节写成"汉字(拼音)"，连字符相连。规则：①英语几个音节就写几组；②括号内只能是标准普通话拼音（声母+韵母，如yi、fei、mo、re、pu、ke、la），严禁出现英文词（pro、kras）或IPA符号；③汉字读音尽量贴近英语发音。示例：伊(yi)-费(fei)-默(mo)-热(re)>
【核心含义】<一句中文简短解释>
【语法要点】<一条有区分价值的语法说明，如：与近义词的差异、固定搭配介词、使用场合限制——不要只重复核心含义>
【例句】<一个英文例句> → <中文翻译>

If the input is a phrase or sentence (not a single word), skip 【词性】【IPA】【谐音】 and start from 【核心含义】.
Only add ⚡【发音注意】<纯中文说明> if there is a notable connected speech feature.\
"""

PROMPT_PRONOUNCE = """\
You are a pronunciation coach for Chinese learners of English.
ALL output must be in Chinese only — do NOT use English anywhere except inside the IPA brackets.

Output in this EXACT format:

【IPA】/<完整IPA>/
【谐音】<逐音节标注，每个英语音节写成"汉字(拼音)"，连字符相连。规则：①英语几个音节就写几组；②括号内只能是标准普通话拼音（如yi、fei、mo、re、pu、ke），严禁出现英文词或IPA符号；③汉字读音尽量贴近英语发音。示例：伊(yi)-费(fei)-默(mo)-热(re)>
【重音】<第几音节重读，用中文描述>

Only include lines below if they apply — if not applicable, omit the line entirely, do NOT write n/a:
⚡【连读】<纯中文描述>
⚡【弱读】<纯中文描述>
⚡【吞音】<纯中文描述>
⚡【变音】<纯中文描述>
⚡【发音陷阱】<仅当以下情况出现时输出，其余省略：①含/θ/或/ð/（th音）时说明唇齿舌位；②含词末辅音群（如-cts,-nds）时提示收音方式；③含关键长短元音对比（如/ɪ/vs/iː/）时对比说明——用纯中文>

【记忆口诀】<一句中文记忆技巧>\
"""

PROMPT_REVIEW_JUDGE = """\
You are a vocabulary review judge for a Chinese learner of English.
You will receive: word, standard translation, and the learner's answer.
Judge if the learner's answer is semantically correct — meaning matters, exact wording does not.

Output in this EXACT format, nothing else:
verdict: correct
or
verdict: wrong
feedback: <一句中文说明原因，仅当wrong时输出>\
"""
