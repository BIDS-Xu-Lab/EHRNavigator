"""LLM-as-Judge for the DrugEHRQA / MIMIC-III QA benchmark.

Given a REFERENCE (gold) answer and a MODEL answer, an LLM decides whether the
model conveys the same factual value(s). Judged by value and meaning, not surface
form. Returns "CORRECT" / "INCORRECT" plus a short reason.

Usage:
    import llm_judge
    verdict, reason = llm_judge.judge_answer(question, gold, pred)

    # or score a list of records [{"question","gold","pred"}, ...]
    acc, results = llm_judge.score(records)

Env: OPENAI_API_KEY (required), OPENAI_MODEL (default gpt-4o).
"""
import os
from dotenv import load_dotenv
import openai

JUDGE_PROMPT = """You are a strict grader for a medical question-answering benchmark built on the MIMIC-III database. For one question you are given a REFERENCE answer (the gold value computed from the
database) and a MODEL answer. Decide whether the model answer conveys the SAME factual value(s) as the reference.
Judge by value and meaning, not surface form:
  - Ignore case, whitespace, punctuation, and units formatting: '20 MG' = '20mg' = '20 milligrams';
    'PO' = 'oral' when clearly the same route.
  - Treat numerically equal values as equal: '4.0' = '4'; '12.34' = '12.3' only if the reference
    itself is given to that precision.
  - For a set of values, order does not matter, but EVERY reference value must be present.

Mark CORRECT only if the model answer contains the reference value(s) and no contradicting or spurious extra value. Mark INCORRECT if any reference value is missing or wrong, if the model added values not in the reference, if the model abstained, or if it answered with an explanation but no actual value. When unsure whether two values are truly the same, mark INCORRECT — do not give the benefit of the doubt.

Respond with EXACTLY two lines and nothing else:
VERDICT: CORRECT
REASON: <one short clause>

User:
QUESTION: {question}
REFERENCE ANSWER: {gold}
MODEL ANSWER: {pred}

Is the model answer correct?
"""


def judge_answer(question: str, gold: str, pred: str, model: str = None) -> tuple[bool, str]:
    """Return (is_correct, reason) for a single (question, gold, pred)."""
    load_dotenv()
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
    client = openai.OpenAI()  # reads OPENAI_API_KEY from environment
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            question=question, gold=gold, pred=pred)}],
        temperature=0,
        max_tokens=64,
    )
    out = resp.choices[0].message.content.strip()

    verdict, reason = "INCORRECT", ""
    for line in out.splitlines():
        if line.upper().startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip().upper()
        elif line.upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()
    return verdict.startswith("CORRECT"), reason


def score(records: list[dict], model: str = None) -> tuple[float, list[dict]]:
    """Score a list of {"question","gold","pred"} dicts. Returns (accuracy, results)."""
    results = []
    for r in records:
        ok, reason = judge_answer(r["question"], r["gold"], r["pred"], model=model)
        results.append({**r, "correct": ok, "reason": reason})
    acc = sum(x["correct"] for x in results) / len(results) if results else 0.0
    return acc, results


if __name__ == "__main__":
    ok, reason = judge_answer(
        question="What dose of aspirin was prescribed?",
        gold="81 mg",
        pred="The patient received aspirin 81mg.",
    )
    print(f"CORRECT={ok} | {reason}")
