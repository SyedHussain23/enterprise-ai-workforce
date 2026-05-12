"""
Day 39 — Offline evaluation of stored workflow logs.

Uses LLM-as-judge (OpenAI) to score each stored response on:
  - Relevance   : does the answer address the question?
  - Faithfulness: does the answer stay within known policy facts?
  - Completeness: does the answer cover all aspects of the question?

Run after the system has accumulated responses:
    python scripts/run_evaluation.py [--limit 20] [--company default]

Output: a table + summary saved to logs/eval_report_{timestamp}.json
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from openai import OpenAI
from sqlalchemy import select

from app.core.config import settings
from app.core.logger import get_logger
from app.db.engine import AsyncSessionLocal
from app.db.models.company import Company
from app.db.models.workflow_log import WorkflowLog

logger = get_logger(__name__)

EVAL_PROMPT = """\
You are an expert evaluator for an enterprise AI assistant.
Score the following question-answer pair on three dimensions (each 0–10):

Question: {question}
Answer: {answer}
Source: {source}

Criteria:
- relevance (0-10): Does the answer directly address the question?
- faithfulness (0-10): Is the answer factually grounded and not hallucinated?
- completeness (0-10): Does the answer cover all aspects of the question?

Respond ONLY with valid JSON:
{{"relevance": N, "faithfulness": N, "completeness": N, "overall": N, "reason": "brief explanation"}}
"""

os.makedirs("logs", exist_ok=True)


def llm_evaluate(client: OpenAI, question: str, answer: str, source: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": EVAL_PROMPT.format(question=question, answer=answer, source=source),
            }],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as exc:
        logger.error("eval.llm_failed", error=str(exc))
        return {"relevance": 0, "faithfulness": 0, "completeness": 0, "overall": 0, "reason": str(exc)}


async def fetch_logs(company_slug: str, limit: int) -> list[WorkflowLog]:
    async with AsyncSessionLocal() as db:
        company_result = await db.execute(
            select(Company).where(Company.slug == company_slug)
        )
        company = company_result.scalar_one_or_none()
        if not company:
            print(f"Company '{company_slug}' not found.")
            return []

        result = await db.execute(
            select(WorkflowLog)
            .where(WorkflowLog.company_id == company.id)
            .order_by(WorkflowLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def main(limit: int, company_slug: str) -> None:
    if not settings.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    print(f"\n🔍 Fetching last {limit} workflow logs for company: {company_slug}")
    logs = await fetch_logs(company_slug, limit)

    if not logs:
        print("No logs found. Run the app and ask some questions first.")
        return

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    results = []
    totals = {"relevance": 0, "faithfulness": 0, "completeness": 0, "overall": 0}

    print(f"{'#':<4} {'Agent':<10} {'Rel':>5} {'Faith':>6} {'Comp':>5} {'Overall':>8}  Question")
    print("-" * 80)

    for i, log in enumerate(logs, 1):
        scores = llm_evaluate(client, log.user_input, log.final_answer, log.agent)
        results.append({
            "log_id": str(log.id),
            "agent": log.agent,
            "question": log.user_input,
            "scores": scores,
            "confidence": log.confidence,
            "evaluation_score_stored": log.evaluation_score,
        })
        for k in totals:
            totals[k] += scores.get(k, 0)

        print(
            f"{i:<4} {log.agent:<10} "
            f"{scores.get('relevance',0):>5} "
            f"{scores.get('faithfulness',0):>6} "
            f"{scores.get('completeness',0):>5} "
            f"{scores.get('overall',0):>8}  "
            f"{log.user_input[:40]}"
        )

    n = len(logs)
    averages = {k: round(v / n, 2) for k, v in totals.items()}
    print("\n" + "=" * 80)
    print(f"📊 AVERAGES over {n} responses:")
    print(f"   Relevance:    {averages['relevance']}/10")
    print(f"   Faithfulness: {averages['faithfulness']}/10")
    print(f"   Completeness: {averages['completeness']}/10")
    print(f"   Overall:      {averages['overall']}/10")

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "company": company_slug,
        "total_evaluated": n,
        "averages": averages,
        "results": results,
    }
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"logs/eval_report_{ts}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n✅ Full report saved to {path}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",   type=int, default=20,      help="Number of logs to evaluate")
    parser.add_argument("--company", type=str, default="default", help="Company slug")
    args = parser.parse_args()
    asyncio.run(main(args.limit, args.company))
