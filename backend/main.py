from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ai
import vocab as vocab_module

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ─────────────────────────────────────────────────────────────

class ConvertReq(BaseModel):
    text: str

class TranslateReq(BaseModel):
    text: str
    context_sentence: str = ""

class ExplainReq(BaseModel):
    text: str
    context_sentence: str = ""

class JudgeReq(BaseModel):
    word: str
    translation: str
    user_answer: str

class ReviewReq(BaseModel):
    word: str
    correct: bool


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/convert")
async def convert(req: ConvertReq):
    result = await ai.convert(req.text)
    return {"result": result}


@app.post("/translate")
async def translate(req: TranslateReq):
    result = await ai.translate(req.text, req.context_sentence)
    # 翻译后不入库；入库在用户点"解释"时触发（/explain）
    return result


@app.post("/explain")
async def explain(req: ExplainReq):
    result = await ai.explain_pronounce(req.text, req.context_sentence)
    # 点解释时触发生词入库
    translation = ""
    if result.get("explain"):
        import re
        m = re.search(r"【核心含义】(.+)", result["explain"])
        if m:
            translation = m.group(1).strip()
    if translation:
        vocab_module.add_to_vocab(req.text, translation)
    return result


@app.post("/vocab/review/judge")
async def review_judge(req: JudgeReq):
    result = await ai.judge(req.word, req.translation, req.user_answer)
    return result


@app.get("/vocab/stats")
def vocab_stats():
    v = vocab_module.load_vocab()
    return vocab_module.compute_stats(v)


@app.get("/vocab/due")
def vocab_due():
    v = vocab_module.load_vocab()
    return vocab_module.get_due(v)


@app.post("/vocab/review")
def vocab_review(req: ReviewReq):
    try:
        next_time = vocab_module.review_word(req.word, req.correct)
        return {"next_review_time": next_time.isoformat()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8765, reload=False)
