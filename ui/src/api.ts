const BASE = "http://127.0.0.1:8765";

async function post<T>(path: string, body: object): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} failed: ${r.status}`);
  return r.json();
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path} failed: ${r.status}`);
  return r.json();
}

export interface VocabStats {
  total: number; not_mastered: number; learning: number;
  mastered: number; due_today: number; streak: number; today_new: number;
}

export interface VocabEntry {
  word: string; translation: string; correct_count: number;
  wrong_count: number; seen_count: number; next_review_time: string;
}

export interface ExplainResult {
  explain: string; pronounce: string; phonetic_xieyin: string;
}

export const api = {
  convert:  (text: string) =>
    post<{ result: string }>("/convert", { text }),

  translate: (text: string, context_sentence = "") =>
    post<{ translation: string; text_type: string }>("/translate", { text, context_sentence }),

  explain:  (text: string, context_sentence = "") =>
    post<ExplainResult>("/explain", { text, context_sentence }),

  judge: (word: string, translation: string, user_answer: string) =>
    post<{ correct: boolean; feedback: string }>("/vocab/review/judge", { word, translation, user_answer }),

  stats:    () => get<VocabStats>("/vocab/stats"),
  due:      () => get<VocabEntry[]>("/vocab/due"),

  review:   (word: string, correct: boolean) =>
    post<{ next_review_time: string }>("/vocab/review", { word, correct }),
};
