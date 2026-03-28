import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from src.code_review_env.models import CodeReviewAction, CodeReviewObservation, CodeReviewState
from src.code_review_env.server.environment import CodeReviewEnvironment
from tasks.task1_syntax import TASK1_INFO, TASK1_SNIPPETS
from tasks.task2_security import TASK2_INFO, TASK2_SNIPPETS
from tasks.task3_quality import TASK3_INFO, TASK3_SNIPPETS

app = FastAPI(title="Code Review Environment", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
env = CodeReviewEnvironment()

class ResetRequest(BaseModel):
    task_id: Optional[str] = "task1"

class StepRequest(BaseModel):
    bugs_found: list = []
    severity: str = "low"
    security_issues: list = []
    suggestions: list = []
    quality_score: float = 0.5
    explanation: str = ""

@app.get("/health")
def health():
    return {"status": "ok", "environment": "code-review-env", "version": "1.0.0"}

@app.post("/reset")
def reset(request: ResetRequest = ResetRequest()):
    return env.reset(task_id=request.task_id or "task1").model_dump()

@app.post("/step")
def step(request: StepRequest):
    try:
        action = CodeReviewAction(bugs_found=request.bugs_found, severity=request.severity,
            security_issues=request.security_issues, suggestions=request.suggestions,
            quality_score=request.quality_score, explanation=request.explanation)
        return env.step(action).model_dump()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state")
def state():
    return env.state().model_dump()

@app.get("/tasks")
def get_tasks():
    return {"tasks": [
        {"task_id": TASK1_INFO["task_id"], "name": TASK1_INFO["name"], "description": TASK1_INFO["description"], "difficulty": TASK1_INFO["difficulty"], "action_schema": TASK1_INFO["action_schema"]},
        {"task_id": TASK2_INFO["task_id"], "name": TASK2_INFO["name"], "description": TASK2_INFO["description"], "difficulty": TASK2_INFO["difficulty"], "action_schema": TASK2_INFO["action_schema"]},
        {"task_id": TASK3_INFO["task_id"], "name": TASK3_INFO["name"], "description": TASK3_INFO["description"], "difficulty": TASK3_INFO["difficulty"], "action_schema": TASK3_INFO["action_schema"]},
    ]}

@app.get("/grader")
def grader():
    result = env.get_last_grader_result()
    if result is None:
        return {"score": 0.0, "passed": False, "feedback": "No episode completed yet.", "details": {}}
    return result

@app.post("/baseline")
def baseline():
    results = {}
    for task_id in ["task1", "task2", "task3"]:
        env.reset(task_id=task_id)
        if task_id == "task1":
            action = CodeReviewAction(bugs_found=["division by zero", "logic error"], severity="medium", suggestions=["add validation"], quality_score=0.4, explanation="Found logic bugs.")
        elif task_id == "task2":
            action = CodeReviewAction(severity="high", security_issues=["SQL injection", "hardcoded credentials"], suggestions=["use parameterized queries"], quality_score=0.2, explanation="Security vulnerabilities found.")
        else:
            action = CodeReviewAction(bugs_found=["no error handling"], severity="high", security_issues=["no input validation"], suggestions=["improve naming", "add docstrings", "optimize complexity", "add error handling", "separate concerns"], quality_score=0.3, explanation="Poor naming, O(n2) complexity, missing error handling, no documentation.")
        env.step(action)
        g = env.get_last_grader_result()
        results[task_id] = {"score": g["score"] if g else 0.0, "passed": g["passed"] if g else False}
    avg = sum(r["score"] for r in results.values()) / len(results)
    return {"baseline_scores": results, "average_score": round(avg, 2), "agent": "rule-based-baseline"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
