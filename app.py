import os
import sqlite3
import time
import uuid
import json
import re

from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Client

# Load environment variables
load_dotenv()
GROQ_KEY = os.environ.get("GROQ_API_KEY")
client = Client(api_key=GROQ_KEY)

app = FastAPI()
DB = os.path.join(os.path.dirname(__file__), "interviews.db")


def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


class CreateInterview(BaseModel):
    candidate_name: str
    candidate_email: str
    college_name: str
    course: str


# ✅ Fixed startup import
@app.on_event("startup")
def startup():
    import db_init   # absolute import, since db_init.py is in same folder
    db_init.init_db()


@app.post("/interviews")
def create_interview(payload: CreateInterview):
    conn = get_conn()
    cur = conn.cursor()
    interview_id = str(uuid.uuid4())
    now = int(time.time())

    cur.execute(
        "INSERT INTO candidates (name,email,started_at) VALUES (?,?,?)",
        (payload.candidate_name, payload.candidate_email, now),
    )
    candidate_id = cur.lastrowid

    cur.execute(
        "INSERT INTO interviews (id,candidate_id,status,created_at,current_question_idx) VALUES (?,?,?,?,?)",
        (interview_id, candidate_id, "in_progress", now, 0),
    )

    conn.commit()
    conn.close()
    return {"interview_id": interview_id}


@app.get("/questions/{idx}")
def get_question(idx: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM questions ORDER BY difficulty, id LIMIT 1 OFFSET ?",
        (idx,),
    )
    q = cur.fetchone()
    conn.close()
    if not q:
        raise HTTPException(status_code=404, detail="No question")
    return dict(q)


def simple_rule_eval(question_row, response_text):
    qtype = question_row["qtype"]
    expected = question_row["expected_answer"] or ""
    score, details = 0.0, {}

    if qtype == "formula":
        a = re.sub(r"\s+", "", response_text.lower())
        e = re.sub(r"\s+", "", expected.lower())
        if e and a == e:
            score = 5.0
            details["match"] = "exact"
        else:
            funcs = re.findall(r"([A-Z]{2,})\(", expected.upper())
            hit = sum(1 for f in funcs if f.lower() in response_text.lower())
            score = min(5.0, (hit / max(1, len(funcs))) * 4.0)
            details["func_hits"] = hit
    elif qtype in ("explain", "task"):
        score = 0.0
        details["note"] = "no rule-based score"

    return score, details


def llm_score(question_text, expected_answer, candidate_answer):
    if not GROQ_KEY:
        return None, {"error": "no_groq_key"}

    prompt = f"""
You are an interviewer. Score the candidate's answer from 0 (poor) to 5 (excellent).
Question: {question_text}
Model answer: {expected_answer}
Candidate answer: {candidate_answer}

Return JSON only: {{"score": number, "rationale": "short explanation"}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_output_tokens=250,
            temperature=0.0,
        )
        text = response.choices[0].message["content"].strip()
        m = re.search(r'"?score"?\s*[:=]\s*([0-9]+(\.[0-9]+)?)', text)
        score = float(m.group(1)) if m else None
        return score, {"raw": text}
    except Exception as e:
        return None, {"error": str(e)}


@app.post("/responses")
def submit_response(
    interview_id: str = Form(...),
    question_id: int = Form(...),
    response_text: str = Form(...),
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM questions WHERE id=?", (question_id,))
    q = cur.fetchone()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    qd = dict(q)

    rule_score, rule_details = simple_rule_eval(qd, response_text)
    llm_score_val, llm_details = llm_score(
        qd["text"], qd["expected_answer"] or "", response_text
    )

    if llm_score_val is None:
        final_score = rule_score if rule_score > 0 else 3.0
    else:
        if qd["qtype"] == "formula":
            final_score = round((0.7 * rule_score + 0.3 * llm_score_val), 2)
        else:
            final_score = round(llm_score_val, 2)

    evaluator = {"rule": rule_details, "llm": llm_details}
    response_id = str(uuid.uuid4())
    now = int(time.time())

    cur.execute(
        "INSERT INTO responses (id,interview_id,question_id,response_text,score,evaluator_details,created_at) VALUES (?,?,?,?,?,?,?)",
        (
            response_id,
            interview_id,
            question_id,
            response_text,
            final_score,
            json.dumps(evaluator),
            now,
        ),
    )

    conn.commit()
    conn.close()
    return {"response_id": response_id, "score": final_score, "evaluator": evaluator}


# ✅ Unified Endpoint: Final Report
@app.get("/final_report/{interview_id}")
def final_report(interview_id: str):
    """Return both Q&A details and performance summary in one call."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.id as question_id,
               q.text as question,
               q.expected_answer as correct_answer,
               r.response_text as your_answer,
               r.score
        FROM responses r
        JOIN questions q ON r.question_id = q.id
        WHERE r.interview_id = ?
        ORDER BY r.created_at ASC
        """,
        (interview_id,),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No responses found for this interview")

    qa_list = [dict(r) for r in rows]
    avg_score = round(sum(r["score"] for r in qa_list) / len(qa_list), 2)

    # ✅ Fixed syntax error in qa_text
    qa_text = "\n".join(
        [
            f"Q: {r['question']}\nYour Answer: {r['your_answer']}\nCorrect Answer: {r['correct_answer']}\nScore: {r['score']}\n"
            for r in qa_list
        ]
    )

    prompt = f"""
You are an interview evaluator. Analyze the following Q&A session and give:
1. A short summary of performance
2. Candidate strengths
3. Candidate weaknesses

Q&A session:
{qa_text}

Return JSON only in this format:
{{
  "summary_text": "short summary",
  "strengths": "list of strengths",
  "weaknesses": "list of weaknesses"
}}
"""

    summary = {"summary_text": "N/A", "strengths": "N/A", "weaknesses": "N/A"}
    if GROQ_KEY:
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": prompt}],
                max_output_tokens=400,
                temperature=0.2,
            )
            text = response.choices[0].message["content"].strip()
            parsed = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            summary = parsed
        except Exception as e:
            summary["error"] = str(e)

    return {
        "interview_id": interview_id,
        "overall": avg_score,
        "summary_text": summary.get("summary_text", "N/A"),
        "strengths": summary.get("strengths", "N/A"),
        "weaknesses": summary.get("weaknesses", "N/A"),
        "questions": qa_list,
    }
